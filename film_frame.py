from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
    RESAMPLE_BILINEAR = Image.Resampling.BILINEAR
except AttributeError:  # Pillow < 9
    RESAMPLE_LANCZOS = Image.LANCZOS
    RESAMPLE_BILINEAR = Image.BILINEAR


@dataclass(frozen=True)
class FrameStyle:
    label: str
    background: tuple[int, int, int]
    text: tuple[int, int, int]
    gradient: tuple[
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
    ] | None = None
    paper_texture: str | None = None
    photo_keyline: tuple[int, int, int] | None = None
    edge_accents: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None


STYLE_PRESETS: dict[str, FrameStyle] = {
    "classic_white": FrameStyle(
        label="白色边框",
        background=(250, 250, 248),
        text=(20, 22, 25),
    ),
    "gallery_black": FrameStyle(
        label="黑色边框",
        background=(16, 17, 19),
        text=(245, 245, 247),
    ),
    "warm_gray": FrameStyle(
        label="银灰边框",
        background=(235, 236, 233),
        text=(28, 29, 31),
    ),
    "polaroid_gold": FrameStyle(
        label="宝丽来金色边框",
        background=(238, 188, 46),
        text=(45, 28, 8),
    ),
    "fuji_limited": FrameStyle(
        label="富士马卡龙相纸",
        background=(248, 229, 232),
        text=(54, 66, 76),
        gradient=(
            (255, 205, 218),
            (205, 229, 255),
            (214, 244, 207),
            (255, 231, 183),
        ),
    ),
    "ivory_cotton": FrameStyle(
        label="象牙棉纸",
        background=(247, 243, 232),
        text=(66, 55, 45),
        paper_texture="cotton",
    ),
    "archive_green": FrameStyle(
        label="档案绿相纸",
        background=(30, 58, 46),
        text=(244, 239, 226),
        paper_texture="matte",
    ),
    "silver_gelatin": FrameStyle(
        label="银盐黑相纸",
        background=(22, 23, 23),
        text=(246, 246, 242),
        photo_keyline=(177, 183, 184),
    ),
    "duotone_edge": FrameStyle(
        label="双色边相纸",
        background=(249, 250, 248),
        text=(34, 37, 39),
        edge_accents=((244, 116, 105), (45, 188, 205)),
    ),
    "blur_background": FrameStyle(
        label="虚化背景",
        background=(20, 20, 20),
        text=(255, 255, 255),
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
    if max_long_edge and image.format == "JPEG":
        # Let libjpeg decode at a reduced DCT scale: faster and far less
        # peak memory for large photos. Never shrinks below the target box.
        image.draft("RGB", (max_long_edge, max_long_edge))
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


@lru_cache(maxsize=128)
def _load_truetype(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size)


def _load_font(size: int, font_path: str | None) -> ImageFont.ImageFont:
    if font_path:
        try:
            return _load_truetype(font_path, size)
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


@lru_cache(maxsize=64)
def _load_rgba_asset(path: str, modified_ns: int, file_size: int) -> Image.Image:
    del modified_ns, file_size
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        return image.convert("RGBA")


def _open_cover_image(path: str | Path | None) -> Image.Image | None:
    if not path:
        return None
    asset_path = Path(path)
    if not asset_path.is_absolute():
        asset_path = Path(__file__).resolve().parent / asset_path
    try:
        resolved_path = asset_path.resolve()
        stat = resolved_path.stat()
        return _load_rgba_asset(str(resolved_path), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None


def _trim_transparent(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def _remove_light_logo_background(image: Image.Image) -> Image.Image:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    if width <= 0 or height <= 0:
        return image

    sample_points = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
    ]
    light_corners = 0
    for x, y in sample_points:
        red, green, blue, alpha = pixels[x, y]
        if alpha > 220 and red > 235 and green > 235 and blue > 235:
            light_corners += 1
    if light_corners < 3:
        return image

    # Zero out the alpha wherever all three channels are near-white,
    # using channel ops instead of a per-pixel Python loop.
    red, green, blue, alpha = image.split()
    light = red.point(lambda v: 255 if v > 238 else 0)
    light = ImageChops.multiply(light, green.point(lambda v: 255 if v > 238 else 0))
    light = ImageChops.multiply(light, blue.point(lambda v: 255 if v > 238 else 0))
    cleaned = image.copy()
    cleaned.putalpha(ImageChops.multiply(alpha, ImageChops.invert(light)))
    return _trim_transparent(cleaned)


def _is_badge_like_logo(image: Image.Image) -> bool:
    width, height = image.size
    if width <= 0 or height <= 0:
        return False
    ratio = width / height
    return 0.72 <= ratio <= 1.35


def _resize_to_fit(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    scale = min(max_width / width, max_height / height, 1.0)
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    if new_size == image.size:
        return image
    return image.resize(new_size, RESAMPLE_LANCZOS)


def _resize_to_cover(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        return Image.new("RGB", (target_width, target_height), (18, 18, 18))
    scale = max(target_width / width, target_height / height)
    resized = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), RESAMPLE_LANCZOS)
    left = max(0, (resized.width - target_width) // 2)
    top = max(0, (resized.height - target_height) // 2)
    return resized.crop((left, top, left + target_width, top + target_height))


def _fast_gaussian_blur(image: Image.Image, radius: float) -> Image.Image:
    """Approximate a large-radius Gaussian blur by blurring a downscaled copy."""
    if radius <= 12:
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    factor = min(8.0, radius / 6.0)
    small_size = (max(1, int(image.width / factor)), max(1, int(image.height / factor)))
    small = image.resize(small_size, RESAMPLE_BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(radius=radius / factor))
    return small.resize(image.size, RESAMPLE_BILINEAR)


def _make_blurred_background(image: Image.Image, width: int, height: int) -> Image.Image:
    background = _resize_to_cover(image, width, height)
    blur_radius = max(16, int(width * 0.028))
    background = _fast_gaussian_blur(background, blur_radius)
    background = ImageEnhance.Brightness(background).enhance(0.58)
    background = ImageEnhance.Contrast(background).enhance(0.92)
    return background.convert("RGB")


def _make_corner_gradient(
    width: int,
    height: int,
    colors: tuple[
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
        tuple[int, int, int],
    ],
) -> Image.Image:
    top_left, top_right, bottom_left, bottom_right = colors
    if width <= 1 or height <= 1:
        return Image.new("RGB", (width, height), top_left)

    # Sample the bilinear surface on a small grid and let Pillow interpolate
    # it back up: same gradient as a per-pixel loop, hundreds of times faster.
    grid_width = min(width, 64)
    grid_height = min(height, 64)
    grid = Image.new("RGB", (grid_width, grid_height))
    pixels = grid.load()
    for y in range(grid_height):
        vertical = y / (grid_height - 1)
        for x in range(grid_width):
            horizontal = x / (grid_width - 1)
            channel_values = []
            for channel in range(3):
                top = top_left[channel] * (1 - horizontal) + top_right[channel] * horizontal
                bottom = bottom_left[channel] * (1 - horizontal) + bottom_right[channel] * horizontal
                channel_values.append(int(round(top * (1 - vertical) + bottom * vertical)))
            pixels[x, y] = tuple(channel_values)
    grid = grid.filter(ImageFilter.GaussianBlur(radius=1))
    return grid.resize((width, height), RESAMPLE_BILINEAR)


def _apply_paper_texture(
    canvas: Image.Image,
    background: tuple[int, int, int],
    texture: str | None,
) -> Image.Image:
    if not texture:
        return canvas

    sample_size = (max(1, canvas.width // 3), max(1, canvas.height // 3))
    if texture == "cotton":
        noise = Image.effect_noise(sample_size, 13).filter(ImageFilter.GaussianBlur(radius=0.45))
        dark = tuple(max(0, channel - 13) for channel in background)
        light = tuple(min(255, channel + 8) for channel in background)
        opacity = 0.22
    else:
        noise = Image.effect_noise(sample_size, 7).filter(ImageFilter.GaussianBlur(radius=0.7))
        dark = tuple(max(0, channel - 7) for channel in background)
        light = tuple(min(255, channel + 7) for channel in background)
        opacity = 0.12

    texture_layer = ImageOps.colorize(noise, dark, light).resize(canvas.size, RESAMPLE_BILINEAR)
    return Image.blend(canvas.convert("RGB"), texture_layer, opacity)


def _draw_frame_details(
    canvas: Image.Image,
    style: FrameStyle,
    content_x: int,
    content_y: int,
    content_width: int,
    content_height: int,
    image_x: int,
    image_y: int,
    image_width: int,
    image_height: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    if style.edge_accents:
        accent_width = max(3, int(image_width * 0.007))
        left_color, right_color = style.edge_accents
        draw.rectangle(
            (content_x, content_y, content_x + accent_width - 1, content_y + content_height - 1),
            fill=left_color,
        )
        draw.rectangle(
            (
                content_x + content_width - accent_width,
                content_y,
                content_x + content_width - 1,
                content_y + content_height - 1,
            ),
            fill=right_color,
        )

    if style.photo_keyline:
        line_width = max(1, int(image_width * 0.0018))
        draw.rectangle(
            (
                image_x - line_width,
                image_y - line_width,
                image_x + image_width + line_width - 1,
                image_y + image_height + line_width - 1,
            ),
            outline=style.photo_keyline,
            width=line_width,
        )


def _paste_photo_with_depth(canvas: Image.Image, photo: Image.Image, x: int, y: int) -> Image.Image:
    radius = max(10, int(photo.width * 0.018))
    shadow_radius = max(12, int(photo.width * 0.022))
    shadow_alpha = Image.new("L", canvas.size, 0)
    shadow_draw = ImageDraw.Draw(shadow_alpha)
    shadow_offset = max(4, int(photo.width * 0.008))
    shadow_draw.rounded_rectangle(
        (x, y + shadow_offset, x + photo.width, y + photo.height + shadow_offset),
        radius=radius,
        fill=150,
    )
    shadow_alpha = _fast_gaussian_blur(shadow_alpha, shadow_radius)
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)

    base = Image.alpha_composite(canvas.convert("RGBA"), shadow)
    mask = Image.new("L", photo.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, photo.width, photo.height), radius=radius, fill=255)
    base.paste(photo.convert("RGBA"), (x, y), mask)
    return base.convert("RGB")


def _size_for_aspect(width: int, height: int, aspect_ratio: tuple[float, float] | None) -> tuple[int, int]:
    if not aspect_ratio:
        return width, height
    ratio_width, ratio_height = aspect_ratio
    if ratio_width <= 0 or ratio_height <= 0:
        return width, height

    base_ratio = ratio_width / ratio_height
    if width > height:
        target_ratio = max(base_ratio, 1 / base_ratio)
    elif height > width:
        target_ratio = min(base_ratio, 1 / base_ratio)
    else:
        target_ratio = base_ratio

    current_ratio = width / height
    if abs(current_ratio - target_ratio) < 0.001:
        return width, height
    if current_ratio > target_ratio:
        return width, max(height, int(round(width / target_ratio)))
    return max(width, int(round(height * target_ratio))), height


def _text_metrics(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int, int, int, int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return left, top, right, bottom, right - left, bottom - top


def _draw_camera_block(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    content_x: int,
    content_width: int,
    content_y: int,
    image_height: int,
    top_border: int,
    bottom_border: int,
    side_border: int,
    photo_width: int,
    logo: str,
    logo_image: Image.Image | None,
    model: str,
    text_align: str,
    logo_fill: tuple[int, int, int],
    model_fill: tuple[int, int, int],
    font_path: str | None,
) -> None:
    logo = logo.strip()
    model = model.strip()
    if not logo and not model and logo_image is None:
        return

    max_width = max(120, int(content_width * 0.42))
    gap = max(8, int(photo_width * 0.012)) if model else 0
    logo_max_width = max(72, int(max_width * (0.48 if model else 1.0)))
    model_max_width = max(72, max_width - logo_max_width - gap)
    logo_bitmap = None
    logo_font = None
    model_font = None
    logo_metrics = (0, 0, 0, 0, 0, 0)
    model_metrics = (0, 0, 0, 0, 0, 0)

    if logo_image is not None:
        cleaned_logo = _remove_light_logo_background(_trim_transparent(logo_image))
        if _is_badge_like_logo(cleaned_logo):
            logo_width_limit = logo_max_width
            logo_height_limit = max(24, int(bottom_border * 0.42))
        else:
            logo_width_limit = max(52, int(logo_max_width * 0.72))
            logo_height_limit = max(20, int(bottom_border * 0.32))
            model_max_width = max(72, max_width - logo_width_limit - gap)
        logo_bitmap = _resize_to_fit(
            cleaned_logo,
            logo_width_limit,
            logo_height_limit,
        )
        logo_metrics = (0, 0, logo_bitmap.width, logo_bitmap.height, logo_bitmap.width, logo_bitmap.height)
    elif logo:
        logo_font = _fit_font(
            draw=draw,
            text=logo,
            max_width=logo_max_width,
            preferred_size=max(22, int(photo_width * 0.034)),
            min_size=max(14, int(photo_width * 0.018)),
            font_path=font_path,
        )
        logo_metrics = _text_metrics(draw, logo, logo_font)
    if model:
        model_font = _fit_font(
            draw=draw,
            text=model,
            max_width=model_max_width if logo_bitmap is not None or logo else max_width,
            preferred_size=max(15, int(photo_width * 0.022)),
            min_size=max(11, int(photo_width * 0.015)),
            font_path=font_path,
        )
        model_metrics = _text_metrics(draw, model, model_font)

    logo_left, logo_top, _logo_right, _logo_bottom, logo_width, logo_height = logo_metrics
    model_left, model_top, _model_right, _model_bottom, model_width, model_height = model_metrics
    has_logo = logo_bitmap is not None or bool(logo)
    gap = gap if has_logo and model else 0
    block_width = logo_width + gap + model_width
    block_height = max(logo_height, model_height)
    if block_width <= 0 or block_height <= 0:
        return

    if text_align == "right":
        block_x = content_x + side_border
    else:
        block_x = content_x + content_width - side_border - block_width
    block_y = content_y + image_height + top_border + (bottom_border - block_height) // 2

    x = block_x
    if logo_bitmap is not None:
        logo_y = block_y + (block_height - logo_height) // 2
        canvas.paste(logo_bitmap, (x, logo_y), logo_bitmap)
        x += logo_width + gap
    elif logo and logo_font:
        logo_y = block_y + (block_height - logo_height) // 2
        draw.text((x - logo_left, logo_y - logo_top), logo, fill=logo_fill, font=logo_font)
        x += logo_width + gap
    if model and model_font:
        model_y = block_y + (block_height - model_height) // 2
        draw.text((x - model_left, model_y - model_top), model, fill=model_fill, font=model_font)


def render_film_frame(
    input_path: str | Path,
    output_path: str | Path,
    film_name: str,
    film_type: str | None = None,
    film_cover_path: str | Path | None = None,
    camera_logo: str | None = None,
    camera_logo_path: str | Path | None = None,
    camera_model: str | None = None,
    show_camera_info: bool = False,
    style_key: str = "classic_white",
    image_align: str = "center",
    text_align: str = "center",
    side_border_ratio: float = 0.055,
    top_border_ratio: float = 0.055,
    blur_background: bool = False,
    output_aspect_ratio: tuple[float, float] | None = None,
    max_long_edge: int | None = 4096,
    font_path: str | None = None,
    jpeg_quality: int = 95,
    jpeg_optimize: bool = True,
) -> Path:
    """Create a bordered image with a larger bottom caption area."""
    if style_key not in STYLE_PRESETS:
        style_key = "classic_white"

    style = STYLE_PRESETS[style_key]
    blur_background = blur_background or style_key == "blur_background"
    image = _open_image(input_path, max_long_edge=max_long_edge)
    width, height = image.size
    cover_image = _open_cover_image(film_cover_path)
    camera_logo_image = _open_cover_image(camera_logo_path) if show_camera_info else None

    side = max(12, int(width * side_border_ratio))
    top = max(12, int(width * top_border_ratio))
    bottom = max(96, int(width * 0.155)) if cover_image else max(72, int(width * 0.135))

    content_width = width + side * 2
    content_height = height + top + bottom
    canvas_width, canvas_height = _size_for_aspect(content_width, content_height, output_aspect_ratio)
    content_x = (canvas_width - content_width) // 2
    content_y = (canvas_height - content_height) // 2
    canvas = (
        _make_blurred_background(image, canvas_width, canvas_height)
        if blur_background
        else (
            _make_corner_gradient(canvas_width, canvas_height, style.gradient)
            if style.gradient
            else Image.new("RGB", (canvas_width, canvas_height), style.background)
        )
    )
    if not blur_background:
        canvas = _apply_paper_texture(canvas, style.background, style.paper_texture)
    min_side = max(8, int(side * 0.35))
    if image_align == "left":
        image_x = content_x + min_side
    elif image_align == "right":
        image_x = content_x + content_width - width - min_side
    else:
        image_x = content_x + (content_width - width) // 2
    image_y = content_y + top
    if blur_background:
        canvas = _paste_photo_with_depth(canvas, image, image_x, image_y)
    else:
        canvas.paste(image, (image_x, image_y))
        _draw_frame_details(
            canvas=canvas,
            style=style,
            content_x=content_x,
            content_y=content_y,
            content_width=content_width,
            content_height=content_height,
            image_x=image_x,
            image_y=image_y,
            image_width=width,
            image_height=height,
        )

    caption = film_name.strip()
    camera_logo_text = (camera_logo or "").strip() if show_camera_info else ""
    camera_model_text = (camera_model or "").strip() if show_camera_info else ""
    if caption or cover_image or camera_logo_text or camera_model_text:
        draw = ImageDraw.Draw(canvas)
        font_path = font_path or find_font_path()
        caption_fill = (255, 255, 255) if blur_background else style.text
        if cover_image:
            cover_max_width = max(52, int(content_width * 0.18))
            cover_max_height = max(46, int(bottom * 0.64))
            cover = _resize_to_fit(cover_image, cover_max_width, cover_max_height)
            gap = max(16, int(width * 0.022))
            text_max_width = max(80, content_width - side * 2 - cover.width - gap)

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
                block_x = content_x + side
            elif text_align == "right":
                block_x = content_x + content_width - side - block_width
            else:
                block_x = content_x + (content_width - block_width) // 2
            block_y = content_y + height + top + (bottom - block_height) // 2

            cover_x = block_x
            cover_y = block_y + (block_height - cover.height) // 2
            canvas.paste(cover, (cover_x, cover_y), cover)

            text_x = cover_x + cover.width + gap
            text_y = block_y + (block_height - text_block_height) // 2
            if caption and title_font:
                draw.text((text_x - title_left, text_y - title_top), caption, fill=caption_fill, font=title_font)
        elif caption:
            preferred_size = max(28, int(width * 0.042))
            min_size = max(16, int(width * 0.024))
            font = _fit_font(
                draw=draw,
                text=caption,
                max_width=content_width - side * 2,
                preferred_size=preferred_size,
                min_size=min_size,
                font_path=font_path,
            )
            left, top_text, _right, _bottom_text, text_width, text_height = _text_metrics(draw, caption, font)
            if text_align == "left":
                x = content_x + side
            elif text_align == "right":
                x = content_x + content_width - side - text_width
            else:
                x = content_x + (content_width - text_width) // 2
            y = content_y + height + top + (bottom - text_height) // 2 - top_text
            draw.text((x - left, y), caption, fill=caption_fill, font=font)

        _draw_camera_block(
            canvas=canvas,
            draw=draw,
            content_x=content_x,
            content_width=content_width,
            content_y=content_y,
            image_height=height,
            top_border=top,
            bottom_border=bottom,
            side_border=side,
            photo_width=width,
            logo=camera_logo_text,
            logo_image=camera_logo_image,
            model=camera_model_text,
            text_align=text_align,
            logo_fill=caption_fill,
            model_fill=caption_fill,
            font_path=font_path,
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="JPEG", quality=jpeg_quality, subsampling=0, optimize=jpeg_optimize)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Add a clean film border to a photo.")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output JPEG path")
    parser.add_argument("--film", default="Kodak Portra 400", help="Film stock text")
    parser.add_argument("--film-type", default="", help="Film type text")
    parser.add_argument("--film-cover", default="", help="Film cover image path")
    parser.add_argument("--camera-logo", default="", help="Camera brand logo text")
    parser.add_argument("--camera-logo-path", default="", help="Camera brand logo image path")
    parser.add_argument("--camera-model", default="", help="Camera model text")
    parser.add_argument("--show-camera-info", action="store_true")
    parser.add_argument("--style", default="classic_white", choices=STYLE_PRESETS.keys())
    parser.add_argument("--image-align", default="center", choices=["left", "center", "right"])
    parser.add_argument("--text-align", default="center", choices=["left", "center", "right"])
    parser.add_argument("--side-border-ratio", type=float, default=0.055)
    parser.add_argument("--top-border-ratio", type=float, default=0.055)
    parser.add_argument("--blur-background", action="store_true")
    parser.add_argument("--aspect-ratio", default="", help="Output aspect ratio, for example 1:1 or 3:2")
    parser.add_argument("--max-long-edge", type=int, default=4096)
    args = parser.parse_args()
    aspect_ratio = None
    if args.aspect_ratio and ":" in args.aspect_ratio:
        ratio_width, ratio_height = args.aspect_ratio.split(":", 1)
        aspect_ratio = (float(ratio_width), float(ratio_height))

    result = render_film_frame(
        input_path=args.input,
        output_path=args.output,
        film_name=args.film,
        film_type=args.film_type,
        film_cover_path=args.film_cover,
        camera_logo=args.camera_logo,
        camera_logo_path=args.camera_logo_path,
        camera_model=args.camera_model,
        show_camera_info=args.show_camera_info,
        style_key=args.style,
        image_align=args.image_align,
        text_align=args.text_align,
        side_border_ratio=args.side_border_ratio,
        top_border_ratio=args.top_border_ratio,
        blur_background=args.blur_background,
        output_aspect_ratio=aspect_ratio,
        max_long_edge=args.max_long_edge,
    )
    print(result)


if __name__ == "__main__":
    main()
