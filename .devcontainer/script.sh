#!/usr/bin/env bash

set -ex


echo '[ -z "${POETRY_ACTIVE}" ] || source $(poetry env info --path)/bin/activate' >> ~/.zshrc

sudo apt-get update
sudo apt-get install -y tpm2-tools

sudo chmod 0666 /dev/tpmrm0