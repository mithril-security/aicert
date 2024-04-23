#!/bin/bash 
set -e

sed -i 's/Types: deb$/& deb-src/' /etc/apt/sources.list.d/debian.sources
apt-get update
apt-get build-dep --assume-yes --no-install-recommends systemd
apt-get install --assume-yes --no-install-recommends libfdisk-dev libtss2-dev

git clone https://github.com/systemd/systemd --depth=1
meson setup systemd/build systemd \
  -D repart=true \
  -D efi=true \
  -D bootloader=true \
  -D ukify=true \
  -D firstboot=true \
  -D blkid=true \
  -D openssl=true \
  -D tpm2=true
BINARIES=(
  bootctl
  systemctl
  systemd-dissect
  systemd-firstboot
  systemd-measure
  systemd-nspawn
  systemd-repart
  ukify
)
ninja -C systemd/build ${BINARIES[@]}
for BINARY in "${BINARIES[@]}"; do
  ln -svf $PWD/systemd/build/$BINARY /usr/bin/$BINARY
  $BINARY --version
done