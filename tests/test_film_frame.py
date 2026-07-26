from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from film_frame import STYLE_PRESETS, render_film_frame


class FilmFrameRenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)
        self.input_path = self.directory / "input.png"
        Image.new("RGB", (320, 200), (72, 126, 184)).save(self.input_path)

    def render(self, name: str, **kwargs) -> Image.Image:
        output_path = self.directory / f"{name}.jpg"
        render_film_frame(
            input_path=self.input_path,
            output_path=output_path,
            film_name="",
            jpeg_quality=100,
            jpeg_optimize=False,
            **kwargs,
        )
        with Image.open(output_path) as image:
            return image.convert("RGB")

    def assert_color_close(
        self,
        actual: tuple[int, int, int],
        expected: tuple[int, int, int],
        tolerance: int = 12,
    ) -> None:
        self.assertTrue(
            all(abs(actual_channel - expected_channel) <= tolerance for actual_channel, expected_channel in zip(actual, expected)),
            f"{actual} is not within {tolerance} of {expected}",
        )

    def test_default_frame_dimensions(self) -> None:
        image = self.render("classic", style_key="classic_white")

        self.assertEqual(image.size, (354, 289))

    def test_square_aspect_ratio(self) -> None:
        image = self.render(
            "square",
            style_key="classic_white",
            output_aspect_ratio=(1, 1),
        )

        self.assertEqual(image.width, image.height)

    def test_unknown_style_matches_classic_white(self) -> None:
        classic = self.render("classic", style_key="classic_white")
        fallback = self.render("fallback", style_key="missing-style")

        self.assertEqual(classic.tobytes(), fallback.tobytes())

    def test_all_style_presets_render(self) -> None:
        for style_key in STYLE_PRESETS:
            with self.subTest(style_key=style_key):
                image = self.render(f"style-{style_key}", style_key=style_key)
                self.assertEqual(image.size, (354, 289))

    def test_silver_gelatin_draws_photo_keyline(self) -> None:
        image = self.render("silver", style_key="silver_gelatin")

        self.assert_color_close(image.getpixel((16, 16)), (177, 183, 184))
        self.assert_color_close(image.getpixel((20, 20)), (72, 126, 184))

    def test_duotone_edge_draws_both_accents(self) -> None:
        image = self.render("duotone", style_key="duotone_edge")
        middle_y = image.height // 2

        self.assert_color_close(image.getpixel((1, middle_y)), (244, 116, 105))
        self.assert_color_close(image.getpixel((image.width - 2, middle_y)), (45, 188, 205))


if __name__ == "__main__":
    unittest.main()
