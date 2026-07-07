from __future__ import annotations

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


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    icon = make_icon()
    icon.save(ASSETS / "icon.png")
    icon.save(
        ASSETS / "icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
