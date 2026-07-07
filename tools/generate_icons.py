from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def make_icon(size: int = 1024) -> Image.Image:
    scale = size / 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    background = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(background)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(25 + 16 * t)
        g = int(112 + 76 * t)
        b = int(185 + 42 * t)
        bg_draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [round(72 * scale), round(72 * scale), round(952 * scale), round(952 * scale)],
        radius=round(220 * scale),
        fill=255,
    )
    image.alpha_composite(Image.composite(background, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask))

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [round(218 * scale), round(252 * scale), round(806 * scale), round(728 * scale)],
        radius=round(68 * scale),
        fill=(0, 31, 62, 80),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(round(24 * scale)))
    image.alpha_composite(shadow)

    draw = ImageDraw.Draw(image)

    # Back photo sheet.
    draw.rounded_rectangle(
        [round(210 * scale), round(220 * scale), round(742 * scale), round(646 * scale)],
        radius=round(58 * scale),
        fill=(215, 241, 255, 255),
    )
    draw.rounded_rectangle(
        [round(245 * scale), round(260 * scale), round(708 * scale), round(610 * scale)],
        radius=round(34 * scale),
        fill=(51, 151, 207, 255),
    )

    # Front photo sheet.
    draw.rounded_rectangle(
        [round(292 * scale), round(308 * scale), round(824 * scale), round(734 * scale)],
        radius=round(58 * scale),
        fill=(255, 255, 255, 255),
    )
    draw.rounded_rectangle(
        [round(330 * scale), round(350 * scale), round(786 * scale), round(694 * scale)],
        radius=round(34 * scale),
        fill=(39, 128, 181, 255),
    )
    draw.ellipse(
        [round(658 * scale), round(394 * scale), round(730 * scale), round(466 * scale)],
        fill=(255, 214, 92, 255),
    )
    draw.polygon(
        [
            (round(330 * scale), round(694 * scale)),
            (round(500 * scale), round(512 * scale)),
            (round(618 * scale), round(632 * scale)),
            (round(718 * scale), round(534 * scale)),
            (round(786 * scale), round(694 * scale)),
        ],
        fill=(35, 195, 150, 255),
    )
    draw.polygon(
        [
            (round(330 * scale), round(694 * scale)),
            (round(506 * scale), round(554 * scale)),
            (round(650 * scale), round(694 * scale)),
        ],
        fill=(23, 158, 132, 255),
    )

    # Download arrow.
    arrow_color = (255, 255, 255, 255)
    accent = (12, 91, 150, 255)
    draw.rounded_rectangle(
        [round(472 * scale), round(154 * scale), round(590 * scale), round(474 * scale)],
        radius=round(44 * scale),
        fill=arrow_color,
    )
    draw.polygon(
        [
            (round(374 * scale), round(430 * scale)),
            (round(688 * scale), round(430 * scale)),
            (round(531 * scale), round(596 * scale)),
        ],
        fill=arrow_color,
    )
    draw.rounded_rectangle(
        [round(386 * scale), round(666 * scale), round(676 * scale), round(742 * scale)],
        radius=round(38 * scale),
        fill=arrow_color,
    )
    draw.rounded_rectangle(
        [round(426 * scale), round(682 * scale), round(636 * scale), round(724 * scale)],
        radius=round(21 * scale),
        fill=accent,
    )

    return image


def make_tiny_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    if size <= 20:
        bg = [1, 1, size - 2, size - 2]
        radius = 4
        stem = [size // 2 - 1, max(3, size // 5), size // 2 + 1, size // 2 + 1]
        head = [(size // 2 - 5, size // 2), (size // 2 + 5, size // 2), (size // 2, size - 5)]
        tray = [size // 2 - 5, size - 4, size // 2 + 5, size - 3]
    elif size <= 32:
        bg = [2, 2, size - 3, size - 3]
        radius = 6
        stem = [size // 2 - 2, size // 5, size // 2 + 2, size // 2 + 2]
        head = [(size // 2 - 8, size // 2), (size // 2 + 8, size // 2), (size // 2, size - 8)]
        tray = [size // 2 - 8, size - 6, size // 2 + 8, size - 4]
    else:
        bg = [3, 3, size - 4, size - 4]
        radius = max(7, size // 5)
        stem = [size // 2 - max(2, size // 13), size // 5, size // 2 + max(2, size // 13), size // 2 + max(3, size // 15)]
        head = [(size // 2 - size // 4, size // 2), (size // 2 + size // 4, size // 2), (size // 2, size - size // 4)]
        tray = [size // 2 - size // 4, size - size // 6, size // 2 + size // 4, size - size // 9]

    draw.rounded_rectangle(bg, radius=radius, fill=(20, 142, 207, 255))
    draw.rounded_rectangle(bg, radius=radius, outline=(101, 221, 241, 255), width=1)
    draw.rectangle(stem, fill=(255, 255, 255, 255))
    draw.polygon(head, fill=(255, 255, 255, 255))
    if size >= 24:
        draw.rounded_rectangle(tray, radius=max(1, size // 18), fill=(255, 255, 255, 255))
        inner = [tray[0] + max(1, size // 12), tray[1] + 1, tray[2] - max(1, size // 12), max(tray[1] + 1, tray[3] - 1)]
        if inner[2] > inner[0]:
            draw.rectangle(inner, fill=(12, 94, 152, 255))

    return image


def make_small_icon(size: int) -> Image.Image:
    if size <= 48:
        return make_tiny_icon(size)

    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        [round(14 * scale), round(14 * scale), round(242 * scale), round(242 * scale)],
        radius=round(54 * scale),
        fill=(27, 143, 205, 255),
    )
    draw.rounded_rectangle(
        [round(24 * scale), round(24 * scale), round(232 * scale), round(232 * scale)],
        radius=round(46 * scale),
        outline=(85, 205, 232, 255),
        width=max(1, round(7 * scale)),
    )

    # Use simple, high-contrast geometry for taskbar/titlebar sizes.
    draw.rounded_rectangle(
        [round(54 * scale), round(64 * scale), round(156 * scale), round(168 * scale)],
        radius=round(17 * scale),
        outline=(213, 245, 255, 255),
        width=max(2, round(12 * scale)),
    )
    draw.rounded_rectangle(
        [round(92 * scale), round(86 * scale), round(202 * scale), round(192 * scale)],
        radius=round(17 * scale),
        outline=(255, 255, 255, 255),
        width=max(2, round(12 * scale)),
    )
    draw.polygon(
        [
            (round(98 * scale), round(190 * scale)),
            (round(137 * scale), round(144 * scale)),
            (round(164 * scale), round(170 * scale)),
            (round(194 * scale), round(136 * scale)),
            (round(204 * scale), round(190 * scale)),
        ],
        fill=(35, 211, 153, 255),
    )
    draw.ellipse(
        [round(178 * scale), round(92 * scale), round(204 * scale), round(118 * scale)],
        fill=(255, 214, 92, 255),
    )
    draw.rounded_rectangle(
        [round(116 * scale), round(36 * scale), round(156 * scale), round(128 * scale)],
        radius=round(16 * scale),
        fill=(255, 255, 255, 255),
    )
    draw.polygon(
        [
            (round(80 * scale), round(118 * scale)),
            (round(192 * scale), round(118 * scale)),
            (round(136 * scale), round(182 * scale)),
        ],
        fill=(255, 255, 255, 255),
    )
    draw.rounded_rectangle(
        [round(92 * scale), round(194 * scale), round(180 * scale), round(218 * scale)],
        radius=round(12 * scale),
        fill=(255, 255, 255, 255),
    )
    draw.rounded_rectangle(
        [round(110 * scale), round(200 * scale), round(162 * scale), round(212 * scale)],
        radius=round(6 * scale),
        fill=(12, 99, 159, 255),
    )

    return image


def save_png_ico(path: Path, images: list[Image.Image]) -> None:
    png_entries: list[tuple[int, int, bytes]] = []
    for image in images:
        output = io.BytesIO()
        image.save(output, format="PNG")
        png_entries.append((image.width, image.height, output.getvalue()))

    offset = 6 + 16 * len(png_entries)
    with path.open("wb") as icon_file:
        icon_file.write(struct.pack("<HHH", 0, 1, len(png_entries)))
        for width, height, png_data in png_entries:
            icon_file.write(
                struct.pack(
                    "<BBBBHHII",
                    width if width < 256 else 0,
                    height if height < 256 else 0,
                    0,
                    0,
                    1,
                    32,
                    len(png_data),
                    offset,
                )
            )
            offset += len(png_data)
        for _, _, png_data in png_entries:
            icon_file.write(png_data)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    icon = make_icon(1024)
    icon.save(ASSETS / "icon.png")
    save_png_ico(
        ASSETS / "icon.ico",
        [
            make_small_icon(16),
            make_small_icon(20),
            make_small_icon(24),
            make_small_icon(32),
            make_small_icon(40),
            make_small_icon(48),
            make_small_icon(64),
            icon.resize((128, 128), Image.Resampling.LANCZOS),
            icon.resize((256, 256), Image.Resampling.LANCZOS),
        ],
    )


if __name__ == "__main__":
    main()
