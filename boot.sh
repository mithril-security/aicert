#!/bin/bash

set -e

./setup-tpm.sh

swtpm socket --tpm2 -t --tpmstate dir=/tmp/tpm --ctrl type=unixio,path=/tmp/swtpm-sock &

if [ "$(whoami)" == "vscode" ]; then
    sudo chown vscode /dev/kvm
fi

echo "127.0.0.1 aicert_worker" | sudo tee -a /etc/hosts

qemu-system-x86_64 \
    -enable-kvm \
    -cpu host \
    -smp 6 \
    -m 4096 \
    -bios /usr/share/qemu/OVMF.fd \
    -drive format=raw,file=local/os_disk.raw \
    -nographic \
    -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:443-:443 \
    -chardev socket,id=chrtpm,path=/tmp/swtpm-sock \
    -tpmdev emulator,id=tpm0,chardev=chrtpm -device tpm-crb,tpmdev=tpm0