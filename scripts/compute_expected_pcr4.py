#!/usr/bin/env python3

from enum import Enum
from hashlib import sha256
import hashlib
import logging
from pathlib import Path
import re
import tempfile
import subprocess
import os
from contextlib import contextmanager
import textwrap

logging.basicConfig(level=logging.INFO)

def run_command(*args, capture_output=True):
    logging.info(f"run: {' '.join(args)}")
    try:
        return subprocess.run(args, text=True, capture_output=capture_output, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        command = ' '.join(args)
        indented_stderr = textwrap.indent(e.stderr, prefix='   ')
        indented_stdout = textwrap.indent(e.stdout, prefix='   ')
        error_message = (
            f"Command '{command}' failed.\n"
            f"Stdout:\n{indented_stdout}"
            f"Stderr:\n{indented_stderr}"
        )

        raise RuntimeError(error_message) from e
@contextmanager
def open_efi_partition_from_os_disk(image_file):
    # if image_file
    if not Path(image_file).is_file():
        raise RuntimeError(f"OS disk image not found at {image_file}")
        
    loopdev = run_command('losetup', '--find', '--show', '--partscan', image_file)
    partitions = run_command('lsblk', '--raw', '--output', 'MAJ:MIN', '--noheadings', loopdev).splitlines()[1:]
    for counter, partition in enumerate(partitions, start=1):
        maj, min = partition.split(':')
        partition_path = f"{loopdev}p{counter}"
        if not os.path.exists(partition_path):
            run_command('mknod', partition_path, 'b', maj, min)

    tmp_dir = tempfile.TemporaryDirectory()
    run_command('mount', '-t', 'vfat', f"{loopdev}p1", tmp_dir.name)
    try:
        yield tmp_dir
    finally:
        run_command('umount', tmp_dir.name)
        tmp_dir.cleanup()
        for i in range(1, len(partitions)+1):
            os.remove(f'{loopdev}p{i}')


def ev_separator_pcr256():
    ev_separator_sha256_hex = "df3f619804a92fdb4057192dc43dd748ea778adc52bc498ce80524c014b81119"
    return bytes.fromhex(ev_separator_sha256_hex)

def ev_efi_action(string: str):
    return sha256(string.encode("ascii")).digest()

def test_compute_authenticode_hash_efi():
    pass

def compute_authenticode_hash_efi(path: str):
    """
    Compute the cryptographic digest of the UEFI application
    """
    try:
        command = ["pesign", "--hash", "-d", "sha256", "-i", path]
        output = subprocess.check_output(command, stderr=subprocess.PIPE).decode()
        hash_match = re.search(r'hash: (\w+)', output)
        if not hash_match:
            raise RuntimeError(f"Could not parse output of pesign tool\n{output}")
        
        hash_hex = hash_match.group(1)
        hash_bytes = bytes.fromhex(hash_hex)
        if len(hash_bytes) != sha256().digest_size:
            raise RuntimeError(f"Invalid sha256 hash\n{hash_bytes}")

        return hash_bytes
            
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to compute Authenticode hash\n{e.stderr.decode()}") from e
    
def extract_kernel_from_uki_to_file(path: str):
    t = tempfile.NamedTemporaryFile()
    command = ["objcopy", "-O", "binary", "-j", ".linux", path, t.name]
    try:
        subprocess.check_call(command, stderr=subprocess.STDOUT)
        return t
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error extracting kernel from UKI: {e.output.decode()}") from e
    

def check_root():
    if os.geteuid() != 0:
        print("You need to have root privileges to run this script.")
        exit(1)


def simulate_pcr_extend(
    hashes,
    initial_pcr=32*b'\0',
):
    """
    Compute the resulting PCR value after multiple PCR_Extend operations starting from a given PCR value (default is 00s)

    Args:
        hashes (list of bytes): A list of SHA-256 hash values (as bytes) that are to be 
            extended into the PCR. Each hash in the list represents a single measurement.
        initial_pcr (bytes, optional): The initial PCR value from which to start 
            the simulation. This is the PCR state before any data has been extended.
            By default, it is a sequence of 00s, which represents a cleared 
            PCR state.

    Returns:
        bytes: The final PCR value after all hashes have been extended into it. 
            This value is the result of consecutively hashing the initial PCR value 
            with each hash in the provided list of hashes.
    """
    # Starting from the expected initial PCR state
    # We replay the event extending the PCR
    # At the end we get the expected PCR value
    current_pcr = initial_pcr
    for e in hashes:
        current_pcr = hashlib.sha256(current_pcr + e).digest()
    return current_pcr

class Target(Enum):
    QEMU = "QEMU (simulation)"
    AZURE_TRUSTED_LAUNCH = "Azure Trusted Launch"


def compute_golden_pcr4(path_to_os_disk_image_file: str, target: Target):
    """
    Compute golden measurement for PCR4

    The PCR4 depends on the target (Qemu, Azure Trusted Launch)
    """
    with open_efi_partition_from_os_disk(path_to_os_disk_image_file) as efi_partition:
        path_to_uki = f"{efi_partition.name}/EFI/BOOT/BOOTX64.EFI"
        logging.info(f"Path to UKI : {path_to_uki}")
        hash_uki = compute_authenticode_hash_efi(path_to_uki)
        with extract_kernel_from_uki_to_file(path_to_uki) as kernel_file:
            hash_kernel = compute_authenticode_hash_efi(kernel_file.name)

    match target:
        case Target.QEMU:
               golden_pcr4 = simulate_pcr_extend([
                    ev_efi_action("Calling EFI Application from Boot Option"),
                    ev_separator_pcr256(),
                    ev_efi_action("Returning from EFI Application from Boot Option"),
                    ev_efi_action("Calling EFI Application from Boot Option"),
                    # EV_EFI_BOOT_SERVICES_APPLICATION with SHA256 authenticode of the UKI PE
                    hash_uki,
                    # EV_EFI_BOOT_SERVICES_APPLICATION with SHA256 authenticode of the linux kernel
                    hash_kernel
                ])
        case Target.AZURE_TRUSTED_LAUNCH:
            golden_pcr4 = simulate_pcr_extend([
                ev_efi_action("Calling EFI Application from Boot Option"),
                ev_separator_pcr256(),
                # EV_EFI_BOOT_SERVICES_APPLICATION with SHA256 authenticode of the UKI PE
                hash_uki,
                # EV_EFI_BOOT_SERVICES_APPLICATION with SHA256 authenticode of the linux kernel
                hash_kernel
            ])
    return golden_pcr4


# if __name__ == "__main__":
#     check_root()

#     IMAGE_FILE = "local/os_disk.raw"
#     TARGET = Target.QEMU
#     TARGET = "azure/trusted-launch"


 
#     print(golden_pcr4.hex())