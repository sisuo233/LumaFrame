from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FramePreset:
    label: str
    frame_size: tuple[int, int]
    photo_size: tuple[int, int]
    side_margin: float
    top_margin: float
    bottom_margin: float

    @property
    def side_border_ratio(self) -> float:
        return self.side_margin / self.photo_size[0]

    @property
    def top_border_ratio(self) -> float:
        return self.top_margin / self.photo_size[0]

    @property
    def bottom_border_ratio(self) -> float:
        return self.bottom_margin / self.photo_size[0]


FRAME_PRESETS = (
    FramePreset("宝丽来经典", (88, 107), (79, 79), 4.5, 5, 23),
    FramePreset("富士 Mini", (54, 86), (46, 62), 4, 4, 20),
    FramePreset("富士 Square", (72, 86), (62, 62), 5, 5, 19),
    FramePreset("富士 Wide", (108, 86), (99, 62), 4.5, 4.5, 19.5),
)
