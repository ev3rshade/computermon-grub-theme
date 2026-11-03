# Computermon Grub Menu

Introducing the Computer-mon GRUB Menu to help you select from the
the collection of Computermons (monsters that fit inside of your 
computer--e.g. os, fw, tools) that you have collected over the years 
of your computer science journey!

## Install (Fedora)

Needs `python3-pillow` and `grub2-tools-extra`.

```sh
python3 build.py
sudo cp -r build/theme/computermon /boot/grub2/themes/
sudo sed -i '/^GRUB_TERMINAL_OUTPUT/d' /etc/default/grub
echo 'GRUB_THEME=/boot/grub2/themes/computermon/theme.txt
GRUB_GFXMODE=1024x768' | sudo tee -a /etc/default/grub
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
```

## Install (Debian/Ubuntu)

Needs `python3-pil` and `grub-common`.

```sh
python3 build.py
sudo cp -r build/theme/computermon /boot/grub/themes/
sudo sed -i '/^GRUB_TERMINAL_OUTPUT/d' /etc/default/grub
echo 'GRUB_THEME=/boot/grub/themes/computermon/theme.txt
GRUB_GFXMODE=1024x768' | sudo tee -a /etc/default/grub
sudo update-grub
```

## Custom icons

Each entry's Computermon is chosen by its `--class` in `grub.cfg`
(e.g. `menuentry "Arch" --class arch`).

By default every Computermon is a star. A custom image for a class replaces its star.

1. Draw pixel art on a transparent background, ideally 26×26 pixels. Smaller art is centred as-is; larger art is trimmed, centred and scaled down to 26×26 pixels, which can lose detail.
2. Save it as `assets/os_icons/<class>.png`, e.g. `assets/os_icons/arch.png`.
3. Rebuild and reinstall (see Install).

### Adding a class

This applies to all entries, custom image or not: an entry only gets an icon if its class is listed in `CLASSES` in `build.py`. Each line sets the star colour, type badge (`LINUX`, `WIN`, `TOOL`, `SYS` or `OS`) and level:

```python
"white": ("#ffffff", "LINUX", 21),
```

With a custom image, the star colour is unused but the badge and level still show.

## Testing

Needs `qemu-kvm` and `edk2-ovmf`.

```sh
python3 build.py --qemu-test
test/run-qemu.sh
```

`run-qemu.sh` boots the theme in a VM with dummy entries from `test/test-grub.cfg`. Rerun `build.py --qemu-test` after every change; `run-qemu.sh` only builds if nothing has been built yet.

`build/` is generated:
- `build/theme/computermon/`: the theme you install
- `build/esp/`: the VM's boot disk (only with `--qemu-test`)

## Font

[Press Start 2P](https://fonts.google.com/specimen/Press+Start+2P) by CodeMan38, licensed under the SIL Open Font License 1.1 (see `assets/OFL.txt`).
