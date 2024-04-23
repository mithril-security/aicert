#!/bin/bash

rm -rf /tmp/tpm
mkdir -p /tmp/tpm

sudo swtpm_setup  --tpm2 --tpmstate /tmp/tpm --create-ek-cert --create-platform-cert
sudo chown --recursive $(whoami) /tmp/tpm

swtpm socket  --tpm2  --tpmstate dir=/tmp/tpm --ctrl type=tcp,port=2322 \
   --server type=tcp,port=2321 \
   --flags not-need-init -d 

# swtpm_bios --tpm2 --tcp localhost:2321

# To mimic Azure AK handle we setup a dummy entry in TPM NVRAM
export TPM2TOOLS_TCTI="swtpm:port=2321"
tpm2_startup -c
filesize=$(stat -c %s sample_vtpm.crt)
tpm2_nvdefine -Co 0x01C101D0 -s "$filesize" -a "ownerread|policywrite|ownerwrite"
tpm2_nvwrite -Co 0x01C101D0 --input=sample_vtpm.crt

mkdir .tpm
cd .tpm
tpm2_createprimary -C o -g sha256 -G ecc -c primary_sh.ctx
tpm2_create -C primary_sh.ctx -g sha256 -G ecc -u eckey.pub -r eckey.priv -a "fixedtpm|fixedparent|sensitivedataorigin|userwithauth|sign|noda"
tpm2_flushcontext -t
tpm2_load -C primary_sh.ctx -u eckey.pub -r eckey.priv -c eckey.ctx
tpm2_evictcontrol -C o -c eckey.ctx 0x81000003
cd ..
swtpm_ioctl -s --tcp :2322