#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f build/esp/EFI/BOOT/BOOTX64.EFI ] || python3 build.py --qemu-test
# Fresh firmware vars every run so stale boot order can't send to PXE first
cp /usr/share/edk2/ovmf/OVMF_VARS.fd build/OVMF_VARS.fd

exec qemu-system-x86_64 \
  -machine q35 -m 512 -enable-kvm \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=build/OVMF_VARS.fd \
  -drive format=raw,file=fat:rw:build/esp \
  -vga std -nic none \
  "$@"
