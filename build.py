#!/usr/bin/env python3
"""Build the computermon GRUB theme from the raw assets.

Output:
  build/theme/computermon/   -> the installable theme (see README.md to install)
  build/esp/                 -> with --qemu-test: EFI system partition tree QEMU boots as a virtual FAT disk
"""
import argparse
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = ROOT / "build"
THEME = OUT / "theme" / "computermon"
ESP = OUT / "esp"
SIDES = ["nw", "n", "ne", "w", "c", "e", "sw", "s", "se"]


def pixel_scale(img, size):
    return img.resize(size, Image.NEAREST)


def load_tiles(src_dir, src_prefix, tile):
    """Downscale each 9-slice tile (nearest-neighbour keeps the pixel art crisp)."""
    return {
        side: pixel_scale(Image.open(src_dir / f"{src_prefix}{side}.png").convert("RGBA"), (tile, tile))
        for side in SIDES
    }


def nine_slice(src_dir, src_prefix, dst_prefix, tile):
    for side, img in load_tiles(src_dir, src_prefix, tile).items():
        img.save(THEME / f"{dst_prefix}{side}.png")


def draw_box(canvas, tiles, x, y, w, h):
    """Paint a 9-slice box onto canvas, stretching edges and centre like GRUB does."""
    t = tiles["nw"].width
    iw, ih = w - 2 * t, h - 2 * t
    for side, (px, py, sw, sh) in {
        "nw": (x, y, t, t), "n": (x + t, y, iw, t), "ne": (x + w - t, y, t, t),
        "w": (x, y + t, t, ih), "c": (x + t, y + t, iw, ih), "e": (x + w - t, y + t, t, ih),
        "sw": (x, y + h - t, t, t), "s": (x + t, y + h - t, iw, t), "se": (x + w - t, y + h - t, t, t),
    }.items():
        piece = pixel_scale(tiles[side], (sw, sh))
        canvas.alpha_composite(piece, (px, py))


def capsule_thumb(width):
    """Orange capsule scrollbar thumb: rounded caps as n/s, one body row as c."""
    height, radius = 40, 10
    mask = Image.new("L", (width, height))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius, fill=255)
    inner = Image.new("L", (width, height))
    ImageDraw.Draw(inner).rounded_rectangle((2, 2, width - 3, height - 3), radius - 2, fill=255)
    shine = Image.new("L", (width, height))
    ImageDraw.Draw(shine).rectangle((6, 6, 9, height - 7), fill=255)
    capsule = Image.new("RGBA", (width, height))
    capsule.paste(INK, mask=mask)
    capsule.paste("#F97535", mask=inner)
    capsule.paste("#FFB07A", mask=shine)
    capsule.crop((0, 0, width, 12)).save(THEME / "thumb_n.png")
    capsule.crop((0, height // 2, width, height // 2 + 1)).save(THEME / "thumb_c.png")
    capsule.crop((0, height - 12, width, height)).save(THEME / "thumb_s.png")


def background():
    """Striped backdrop with the static boxes (feature card, text box, button) baked in.

    Coordinates match the pixel positions in theme.txt, so the theme targets 1024x768.
    """
    w, h = 1024, 768
    bg = Image.new("RGBA", (w, h), "#1A6B7A")
    stripe = Image.new("RGBA", (w, 4), "#1F7787")
    for y in range(0, h, 8):
        bg.alpha_composite(stripe, (0, y))

    card = load_tiles(ASSETS / "menu_box", "selected_", 16)
    draw_box(bg, card, 32, 96, 336, 304)

    text_box = load_tiles(ASSETS / "Progress_bar", "Progress_bar_", 16)
    text_box["c"] = Image.new("RGBA", (16, 16), "#F8F8F8")
    draw_box(bg, text_box, 16, 656, 760, 96)

    button = load_tiles(ASSETS / "Scrollbar_frame", "Scrollbar_", 8)
    draw_box(bg, button, 792, 672, 216, 64)
    bg.save(THEME / "background.png")


# Per GRUB --class: placeholder star colour, type badge, level. Edit freely.
CLASSES = {
    "mizuos": ("#3C9BE8", "OS", 12), "kusaos": ("#3E8E6E", "LINUX", 8), "honouos": ("#F05A5A", "LINUX", 10),
    "recovery": ("#8E8EA0", "TOOL", 1), "efi": ("#8E8EA0", "TOOL", 1),
}
TYPE_COLORS = {"LINUX": "#C08A00", "WIN": "#0078D4", "TOOL": "#3E8E41", "SYS": "#C62828", "OS": "#6A6A88"}
INK = "#484860"
PAPER = "#F8F8F8"

# Icons are 96x32 art pixels. The list shows them at 1x; the left card at 3x.
# They're saved at 3x so GRUB's downscale for the list lands on block centres.
STRIP = (96, 32)
STRIP_SCALE = 3


def creature(cls, color, size):
    """User art from assets/os_icons/<class>.png if present, else a star in the class colour."""
    custom = ASSETS / "os_icons" / f"{cls}.png"
    if custom.exists():
        art = Image.open(custom).convert("RGBA")
        if max(art.size) <= size:
            square = Image.new("RGBA", (size, size))
            square.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
            return square
        art = art.crop(art.getbbox())
        side = max(art.size)
        square = Image.new("RGBA", (side, side))
        square.alpha_composite(art, ((side - art.width) // 2, (side - art.height) // 2))
        return pixel_scale(square, (size, size))
    return star(color, size)


def star(color, size):
    """Five-point pixel star: class-coloured fill, 1px ink outline, a small sparkle."""
    cx, cy = size / 2, size / 2 + 1
    outer, inner = size / 2 - 1.5, size / 5
    points = [
        (cx + r * math.sin(i * math.pi / 5), cy - r * math.cos(i * math.pi / 5))
        for i, r in zip(range(10), [outer, inner] * 5)
    ]
    mask = Image.new("L", (size, size))
    ImageDraw.Draw(mask).polygon(points, fill=255)
    img = Image.new("RGBA", (size, size))
    img.paste(INK, mask=mask.filter(ImageFilter.MaxFilter(3)))
    img.paste(color, mask=mask)
    sparkle = (round(cx - size / 8), round(cy - size / 10))
    img.paste(PAPER, (sparkle[0], sparkle[1], sparkle[0] + 2, sparkle[1] + 2))
    return img


def strip(cls, color, kind, level, font):
    """[creature in a round slot] [type badge / Lv plate with HP bar]"""
    img = Image.new("RGBA", STRIP)
    d = ImageDraw.Draw(img)
    d.fontmode = "1"  # no antialiasing: keep the 8px font on the pixel grid

    d.ellipse((0, 0, 31, 31), fill=(0x48, 0x48, 0x60, 0x60), outline=INK)
    img.alpha_composite(creature(cls, color, 26), (3, 3))

    badge_w = len(kind) * 8 + 4
    d.rectangle((36, 0, 36 + badge_w - 1, 11), fill=TYPE_COLORS[kind], outline=INK)
    d.text((38, 2), kind, font=font, fill=PAPER)

    d.rectangle((35, 13, 95, 31), fill=PAPER, outline=INK)
    d.text((38, 15), f"Lv{level}", font=font, fill=INK)
    d.text((38, 23), "HP", font=font, fill="#F97535")
    d.rectangle((56, 24, 93, 29), fill=INK)
    d.rectangle((57, 25, 92, 28), fill="#58D080")
    return img


def icons():
    """GRUB picks an entry's icon by its --class (first class with a file wins)."""
    (THEME / "icons").mkdir()
    font = ImageFont.truetype(str(ASSETS / "PressStart2P-Regular.ttf"), 8)
    for cls, (color, kind, level) in CLASSES.items():
        art = strip(cls, color, kind, level, font)
        size = (STRIP[0] * STRIP_SCALE, STRIP[1] * STRIP_SCALE)
        pixel_scale(art, size).save(THEME / "icons" / f"{cls}.png")


def add_rivets(prefix):
    """Lighten a 2x2 spot on each corner tile's border so the boxes look bolted on."""
    for side, (x, y) in {"nw": (2, 2), "ne": (12, 2), "sw": (2, 12), "se": (12, 12)}.items():
        path = THEME / f"{prefix}{side}.png"
        tile = Image.open(path)
        r, g, b, a = tile.getpixel((x, y))
        light = (r + (255 - r) * 2 // 5, g + (255 - g) * 2 // 5, b + (255 - b) * 2 // 5, a)
        tile.paste(light, (x, y, x + 2, y + 2))
        tile.save(path)


def widen_left(prefix, item_height, cursor):
    """Add a 16px empty column left of the box, holding a ▶ cursor if requested.

    GRUB draws every box from the same left edge, so idle and selected boxes both
    get the column to keep their borders aligned. The w piece is exactly
    item_height tall so GRUB doesn't stretch the arrow.
    """
    rows = [1, 2, 3, 4, 3, 2, 1]  # triangle widths in 2px units
    mask = Image.new("L", (14, 18))
    d = ImageDraw.Draw(mask)
    for i, width in enumerate(rows):
        d.rectangle((2, i * 2 + 2, width * 2 + 1, i * 2 + 3), fill=255)
    outline = mask.filter(ImageFilter.MaxFilter(5))
    arrow = Image.new("RGBA", mask.size)
    arrow.paste(PAPER, mask=outline)
    arrow.paste(INK, mask=mask)

    for side, height in (("nw", 16), ("w", item_height), ("sw", 16)):
        path = THEME / f"{prefix}{side}.png"
        edge = pixel_scale(Image.open(path), (16, height))
        wide = Image.new("RGBA", (32, height))
        wide.alpha_composite(edge, (16, 0))
        if cursor and side == "w":
            wide.alpha_composite(arrow, (2, (height - arrow.height) // 2))
        wide.save(path)


def solid(name, color):
    Image.new("RGBA", (1, 1), color).save(THEME / name)


def grub_tool(name):
    """Fedora prefixes GRUB tools with grub2-, Debian/Ubuntu with grub-."""
    return shutil.which(f"grub2-{name}") or f"grub-{name}"


def fonts():
    ttf = ASSETS / "PressStart2P-Regular.ttf"
    for size in (8, 16, 24):
        subprocess.run(
            [grub_tool("mkfont"), "-s", str(size), "-o", str(THEME / f"press_start_{size}.pf2"), str(ttf)],
            check=True,
        )


def build_theme():
    shutil.rmtree(THEME, ignore_errors=True)
    THEME.mkdir(parents=True)
    nine_slice(ASSETS / "menu_box", "idle_", "item_", 16)
    nine_slice(ASSETS / "menu_box", "selected_", "select_", 16)
    add_rivets("item_")
    add_rivets("select_")
    widen_left("item_", 32, cursor=False)
    widen_left("select_", 32, cursor=True)
    nine_slice(ASSETS / "Scrollbar_frame", "Scrollbar_", "scrollbar_", 8)
    nine_slice(ASSETS / "Progress_bar", "Progress_bar_", "progress_", 16)
    nine_slice(ASSETS / "Progress_bar", "Progress_bar_", "exp_", 8)
    capsule_thumb(32)
    solid("highlight_c.png", "#F97535")
    background()
    icons()
    fonts()
    shutil.copy(ROOT / "theme.txt", THEME / "theme.txt")
    shutil.copy(ASSETS / "OFL.txt", THEME / "OFL.txt")


def build_esp():
    shutil.rmtree(ESP, ignore_errors=True)
    boot = ESP / "EFI" / "BOOT"
    boot.mkdir(parents=True)
    shutil.copytree(THEME, ESP / "boot" / "grub" / "themes" / THEME.name)
    subprocess.run(
        [
            grub_tool("mkstandalone"),
            "-O", "x86_64-efi",
            "-o", str(boot / "BOOTX64.EFI"),
            f"boot/grub/grub.cfg={ROOT / 'test' / 'test-grub.cfg'}",
        ],
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--qemu-test", action="store_true", help="also build the test ESP for test/run-qemu.sh")
    args = parser.parse_args()
    build_theme()
    print(f"theme: {THEME}")
    if args.qemu_test:
        build_esp()
        print(f"esp:   {ESP}")
