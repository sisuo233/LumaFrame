from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps


try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9
    RESAMPLE_LANCZOS = Image.LANCZOS


@dataclass(frozen=True)
class FrameStyle:
    label: str
    background: tuple[int, int, int]
    text: tuple[int, int, int]
    caption_hint: tuple[int, int, int]


STYLE_PRESETS: dict[str, FrameStyle] = {
    "classic_white": FrameStyle(
        label="白色边框",
        background=(250, 250, 248),
        text=(20, 22, 25),
        caption_hint=(118, 118, 122),
    ),
    "gallery_black": FrameStyle(
        label="黑色边框",
        background=(16, 17, 19),
        text=(245, 245, 247),
        caption_hint=(170, 170, 176),
    ),
    "warm_gray": FrameStyle(
        label="银灰边框",
        background=(235, 236, 233),
        text=(28, 29, 31),
        caption_hint=(130, 130, 134),
    ),
    "polaroid_gold": FrameStyle(
        label="宝丽来金色边框",
        background=(218, 181, 92),
        text=(38, 31, 18),
        caption_hint=(112, 89, 42),
    ),
    "fuji_limited": FrameStyle(
        label="富士限定相纸",
        background=(232, 246, 238),
        text=(22, 72, 55),
        caption_hint=(80, 140, 112),
    ),
}


FONT_CANDIDATES = [
    "assets/fonts/NotoSansSC-Regular.otf",
    "assets/fonts/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/NotoSansSC-VF.ttf",
    "C:/Windows/Fonts/NotoSerifSC-VF.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/microsoftyahei.ttf",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/DroidSansFallback.ttf",
]


def find_font_path(extra_candidates: Iterable[str | Path] | None = None) -> str | None:
    candidates: list[str | Path] = []
    if extra_candidates:
        candidates.extend(extra_candidates)
    candidates.extend(FONT_CANDIDATES)

    base_dir = Path(__file__).resolve().parent
    for candidate in candidates:
        path = Path(candidate)
        if not path.is_absolute():
            path = base_dir / path
        if path.exists():
            return str(path)
    return None


def _open_image(path: str | Path, max_long_edge: int | None) -> Image.Image:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)

    if image.mode in ("RGBA", "LA"):
        base = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        base.paste(image, mask=alpha)
        image = base
    else:
        image = image.convert("RGB")

    if max_long_edge:
        width, height = image.size
        longest = max(width, height)
        if longest > max_long_edge:
            scale = max_long_edge / longest
            size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(size, RESAMPLE_LANCZOS)

    return image


def _load_font(size: int, font_path: str | None) -> ImageFont.ImageFont:
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    preferred_size: int,
    min_size: int,
    font_path: str | None,
) -> ImageFont.ImageFont:
    size = preferred_size
    while size >= min_size:
        font = _load_font(size, font_path)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= max_width:
            return font
        size -= 2
    return _load_font(min_size, font_path)


def _open_cover_image(path: str | Path | None) -> Image.Image | None:
    if not path:
        return None
    cover_path = Path(path)
    if not cover_path.is_absolute():
        cover_path = Path(__file__).resolve().parent / cover_path
    if not cover_path.exists():
        return None
    try:
        image = Image.open(cover_path)
        image = ImageOps.exif_transpose(image)
        return image.convert("RGBA")
    except OSError:
        return None


def _resize_to_fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    scale = min(max_width / width, max_height / height, 1.0)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    if new_size == image.size:
        return image
    return image.resize(new_size, RESAMPLE_LANCZOS)


def _text_metrics(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int, int, int, int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return left, top, right, bottom, right - left, bottom - top


def render_film_frame(
    input_path: str | Path,
    output_path: str | Path,
    film_name: str,
    film_type: str | None = None,
    film_cover_path: str | Path | None = None,
    style_key: str = "classic_white",
    image_align: str = "center",
    text_align: str = "center",
    side_border_ratio: float = 0.055,
    top_border_ratio: float = 0.055,
    max_long_edge: int | None = 4096,
    font_path: str | None = None,
) -> Path:
    """Create a bordered image with a larger bottom caption area."""
    if style_key not in STYLE_PRESETS:
        style_key = "classic_white"

    style = STYLE_PRESETS[style_key]
    image = _open_image(input_path, max_long_edge=max_long_edge)
    width, height = image.size
    cover_image = _open_cover_image(film_cover_path)

    side = max(12, int(width * side_border_ratio))
    top = max(12, int(width * top_border_ratio))
    bottom = max(96, int(width * 0.155)) if cover_image else max(72, int(width * 0.135))

    canvas_width = width + side * 2
    canvas_height = height + top + bottom
    canvas = Image.new("RGB", (canvas_width, canvas_height), style.background)
    min_side = max(8, int(side * 0.35))
    if image_align == "left":
        image_x = min_side
    elif image_align == "right":
        image_x = canvas_width - width - min_side
    else:
        image_x = (canvas_width - width) // 2
    canvas.paste(image, (image_x, top))

    caption = film_name.strip()
    if caption or cover_image:
        draw = ImageDraw.Draw(canvas)
        font_path = font_path or find_font_path()
        if cover_image:
            cover_max_width = max(52, int(canvas_width * 0.18))
            cover_max_height = max(46, int(bottom * 0.64))
            cover = _resize_to_fit(cover_image, cover_max_width, cover_max_height)
            gap = max(16, int(width * 0.022))
            text_max_width = max(80, canvas_width - side * 2 - cover.width - gap)

            title_font = None
            title_left = title_top = title_width = title_height = 0
            if caption:
                title_font = _fit_font(
                    draw=draw,
                    text=caption,
                    max_width=text_max_width,
                    preferred_size=max(22, int(width * 0.033)),
                    min_size=max(14, int(width * 0.018)),
                    font_path=font_path,
                )
                title_left, title_top, _title_right, _title_bottom, title_width, title_height = _text_metrics(
                    draw, caption, title_font
                )

            text_block_width = title_width
            text_block_height = title_height
            block_width = cover.width + (gap + text_block_width if caption else 0)
            block_height = max(cover.height, text_block_height)

            if text_align == "left":
                block_x = side
            elif text_align == "right":
                block_x = canvas_width - side - block_width
            else:
                block_x = (canvas_width - block_width) // 2
            block_y = height + top + (bottom - block_height) // 2

            cover_x = block_x
            cover_y = block_y + (block_height - cover.height) // 2
            canvas.paste(cover, (cover_x, cover_y), cover)

            text_x = cover_x + cover.width + gap
            text_y = block_y + (block_height - text_block_height) // 2
            if caption and title_font:
                draw.text((text_x - title_left, text_y - title_top), caption, fill=style.text, font=title_font)
        elif caption:
            preferred_size = max(28, int(width * 0.042))
            min_size = max(16, int(width * 0.024))
            font = _fit_font(
                draw=draw,
                text=caption,
                max_width=canvas_width - side * 2,
                preferred_size=preferred_size,
                min_size=min_size,
                font_path=font_path,
            )
            left, top_text, _right, _bottom_text, text_width, text_height = _text_metrics(draw, caption, font)
            if text_align == "left":
                x = side
            elif text_align == "right":
                x = canvas_width - side - text_width
            else:
                x = (canvas_width - text_width) // 2
            y = height + top + (bottom - text_height) // 2 - top_text
            draw.text((x - left, y), caption, fill=style.text, font=font)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=95, subsampling=0, optimize=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a clean film border to a photo.")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output JPEG path")
    parser.add_argument("--film", default="Kodak Portra 400", help="Film stock text")
    parser.add_argument("--film-type", default="", help="Film type text")
    parser.add_argument("--film-cover", default="", help="Film cover image path")
    parser.add_argument("--style", default="classic_white", choices=STYLE_PRESETS.keys())
    parser.add_argument("--image-align", default="center", choices=["left", "center", "right"])
    parser.add_argument("--text-align", default="center", choices=["left", "center", "right"])
    parser.add_argument("--side-border-ratio", type=float, default=0.055)
    parser.add_argument("--top-border-ratio", type=float, default=0.055)
    parser.add_argument("--max-long-edge", type=int, default=4096)
    args = parser.parse_args()

    result = render_film_frame(
        input_path=args.input,
        output_path=args.output,
        film_name=args.film,
        film_type=args.film_type,
        film_cover_path=args.film_cover,
        style_key=args.style,
        image_align=args.image_align,
        text_align=args.text_align,
        side_border_ratio=args.side_border_ratio,
        top_border_ratio=args.top_border_ratio,
        max_long_edge=args.max_long_edge,
    )
    print(result)


if __name__ == "__main__":
    main()
