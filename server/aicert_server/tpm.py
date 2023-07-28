#!/usr/bin/python3

import json
import tempfile
import requests
import hashlib
import subprocess
import subprocess
import yaml
import subprocess
from typing import List, Dict, Any


PCR_FOR_MEASUREMENT = 16


def sha256_file(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def tpm_nvread(offset: str) -> bytes:
    return subprocess.run(
        ["tpm2_nvread", "-Co", offset], capture_output=True, check=True
    ).stdout


def tpm_extend_pcr(pcr_index: int, hex_hash_value: str) -> None:
    """
    Extend PCR pcr_index from SHA256 bank with a hash

    >>> hex_hash_value = (
    ...     "0x0000000000000000000000000000000000000000000000000000000000000000"
    ... )
    >>> pcr_index = 15
    >>> tpm_extend_pcr(pcr_index, hex_hash_value)
    """

    subprocess.run(
        ["tpm2_pcrextend", f"{pcr_index}:sha256={hex_hash_value}"], check=True
    )


def tpm_read_pcr(pcr_index: int) -> str:
    """
    Read the value of a PCR at index pcr_index from bank sha256
    returns the hash value of the PCR

    >>> _ = tpm_read_pcr(15)
    """
    tpm2_pcrread = subprocess.run(
        ["tpm2_pcrread", f"sha256:{pcr_index}"],
        capture_output=True,
        check=True,
        text=True,
    )
    pcrread_output = yaml.load(tpm2_pcrread.stdout, Loader=yaml.BaseLoader)
    # The result we get from tpm2_pcrread is something in this format '0x31A6F553CC0F9FC156877E35D35CA63AD9514A67C1B231B73665127CD6867631'
    # This format is not the same as the one output by python hashlib .hexdigest() function
    # so we transform it so that it is in this format '31a6f553cc0f9fc156877e35d35ca63ad9514a67c1b231b73665127cd6867631'
    return pcrread_output["sha256"][str(pcr_index)].lower().removeprefix("0x")


def cert_chain() -> List[bytes]:
    def get_certificate_from_url(url: str):
        req = requests.get(url)
        req.raise_for_status()
        return req.content

    intermediate_cert = get_certificate_from_url(
        "http://crl.microsoft.com/pkiinfra/Certs/BL2PKIINTCA01.AME.GBL_AME%20Infra%20CA%2002(4).crt"
    )
    root_cert = get_certificate_from_url(
        "http://crl.microsoft.com/pkiinfra/certs/AMERoot_ameroot.crt"
    )
    AIK_CERT_INDEX = "0x01C101D0"
    cert = tpm_nvread(AIK_CERT_INDEX)
    cert_chain = [cert, intermediate_cert, root_cert]
    return cert_chain


def test_cert_chain():
    cert_chain()


def quote() -> Dict[str, bytes]:
    """
    Produce a quote attesting all the PCRs from the SHA256 PCR bank

    Quote is signed using the AIK_PUB_INDEX key

    """
    AIK_PUB_INDEX = "0x81000003"
    with (
        tempfile.NamedTemporaryFile() as quote_msg_file,
        tempfile.NamedTemporaryFile() as quote_sig_file,
        tempfile.NamedTemporaryFile() as quote_pcr_file,
    ):
        # fmt:off
        subprocess.run(["tpm2_quote", "--quiet",
                        "--key-context", AIK_PUB_INDEX, 
                        "--pcr-list", "sha256:0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23", 
                        "--message" , quote_msg_file.name, 
                        "--signature", quote_sig_file.name, 
                        "--pcr", quote_pcr_file.name, 
                        "--hash-algorithm", "sha256"], check=True)
        # fmt:on

        quote_msg = quote_msg_file.read()
        quote_sig = quote_sig_file.read()
        quote_pcr = quote_pcr_file.read()

    return {"message": quote_msg, "signature": quote_sig, "pcr": quote_pcr}
