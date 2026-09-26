from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from film_frame import render_film_frame
from frame_presets import FRAME_PRESETS


class FramePresetTests(unittest.TestCase):
    def test_photo_window_uses_center_crop(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            image = Image.new("RGB", (1200, 800), (220, 50, 50))
            ImageDraw.Draw(image).rectangle((200, 0, 999, 799), fill=(30, 90, 180))
            image.save(source)
            output = Path(directory) / "polaroid.png"
            preset = FRAME_PRESETS[0]
            render_film_frame(
                input_path=source,
                output_path=output,
                film_name="",
                side_border_ratio=preset.side_border_ratio,
                top_border_ratio=preset.top_border_ratio,
                bottom_border_ratio=preset.bottom_border_ratio,
                photo_aspect_ratio=preset.photo_size,
                output_aspect_ratio=preset.frame_size,
            )
            with Image.open(output) as result:
                center_y = result.height // 2
                for x in (55, result.width - 55):
                    pixel = result.getpixel((x, center_y))
                    self.assertTrue(all(abs(actual - expected) <= 2 for actual, expected in zip(pixel, (30, 90, 180))))

    def test_preset_geometry(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            Image.new("RGB", (1200, 800), (70, 130, 190)).save(source)
            for preset in FRAME_PRESETS:
                with self.subTest(preset=preset.label):
                    output = Path(directory) / f"{preset.label}.png"
                    render_film_frame(
                        input_path=source,
                        output_path=output,
                        film_name="",
                        style_key="classic_white",
                        side_border_ratio=preset.side_border_ratio,
                        top_border_ratio=preset.top_border_ratio,
                        bottom_border_ratio=preset.bottom_border_ratio,
                        photo_aspect_ratio=preset.photo_size,
                        output_aspect_ratio=preset.frame_size,
                    )
                    with Image.open(output) as image:
                        actual = image.width / image.height
                        expected = preset.frame_size[0] / preset.frame_size[1]
                        self.assertAlmostEqual(actual, expected, delta=0.005)


if __name__ == "__main__":
    unittest.main()
