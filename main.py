from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.utils import platform

from film_frame import FONT_CANDIDATES, STYLE_PRESETS, find_font_path, render_film_frame


APP_FONT = "FilmBorderUIFont"
ANDROID_PICK_IMAGE_REQUEST = 24017
STYLE_BY_LABEL = {style.label: key for key, style in STYLE_PRESETS.items()}
DEFAULT_STYLE_LABEL = STYLE_PRESETS["classic_white"].label
TEXT_ALIGN_BY_LABEL = {
    "文字居中": "center",
    "文字靠左": "left",
    "文字靠右": "right",
}
DEFAULT_TEXT_ALIGN_LABEL = "文字居中"
BASE_DIR = Path(__file__).resolve().parent
FILM_COVER_DIR = BASE_DIR / "assets" / "film_covers"
FILM_INDEX_PATH = FILM_COVER_DIR / "index.json"
FALLBACK_FILM_GROUPS = [
    (
        "Kodak",
        [
            "Kodak Portra 400",
            "Kodak Portra 160",
            "Kodak Portra 800",
            "Kodak Gold 200",
            "Kodak ColorPlus 200",
            "Kodak Ektar 100",
            "Kodak Ultramax 400",
            "Kodak Tri-X 400",
            "Kodak T-MAX 100",
            "Kodak T-MAX 400",
        ],
    ),
    (
        "Fujifilm",
        [
            "Fujifilm 400",
            "Fujifilm C200",
            "Fujifilm 200",
            "Fujifilm Superia X-TRA 400",
            "Fujifilm Pro 400H",
            "Fujifilm Velvia 50",
            "Fujifilm Provia 100F",
        ],
    ),
    (
        "Ilford",
        [
            "Ilford HP5 Plus",
            "Ilford Delta 400",
            "Ilford FP4 Plus",
            "Ilford Pan 100",
            "Ilford Pan 400",
            "Ilford SFX 200",
            "Ilford XP2 Super",
        ],
    ),
    (
        "Cinestill",
        [
            "Cinestill 800T",
            "Cinestill 400D",
            "Cinestill 50D",
            "Cinestill BwXX",
        ],
    ),
    (
        "电影卷",
        [
            "Kodak Vision3 50D",
            "Kodak Vision3 250D",
            "Kodak Vision3 500T",
            "Kodak Vision3 200T",
            "Fujifilm Eterna 250D",
            "Fujifilm Eterna 500T",
            "ORWO NC500",
            "ORWO N75",
        ],
    ),
    (
        "Lomography",
        [
            "Lomography 800",
            "Lomography Color 400",
            "Lomography Color 100",
            "Lomography Color 200",
            "Lomography Purple",
            "Lomography Metropolis",
            "Lomography Redscale XR",
        ],
    ),
    (
        "Revolog",
        [
            "Revolog Kolor",
            "Revolog Tesla",
            "Revolog Streak",
            "Revolog Volvox",
            "Revolog Paper",
        ],
    ),
]
DEFAULT_SIDE_BORDER_RATIO = 0.055
DEFAULT_TOP_BORDER_RATIO = 0.055
MIN_BORDER_RATIO = 0.015
MAX_BORDER_RATIO = 0.16


@dataclass(frozen=True)
class FilmOption:
    label: str
    name: str
    film_type: str
    group: str
    cover_path: str | None = None
    search_text: str = ""


SPECIAL_BRAND_PREFIXES = [
    "Reflx Lab",
    "Yue Crystal",
    "FilmNeverDie",
    "Yes!Star",
]
GROUP_ORDER = [
    "电影卷",
    "Kodak",
    "Fujifilm",
    "Ilford",
    "Polaroid",
    "Lomography",
    "CineStill",
    "Agfa",
    "Adox",
    "Ferrania",
    "Foma",
    "Kentmere",
    "Lucky",
    "ORWO",
    "Reflx Lab",
    "Revolog",
    "Rollei",
    "Shanghai",
    "Yue Crystal",
    "一次成像",
]
MOVIE_FILM_MARKERS = [
    "Vision3",
    "Eterna",
    "CineStill",
    "Double-X",
    " 5203",
    " 5207",
    " 5213",
    " 5219",
    " 5222",
    " 5294",
    " 7294",
    " 8543",
    " 8546",
    " 8547",
    " 8553",
    " 8563",
    " 8573",
    " 8583",
]


def _film_group_name(name: str, film_type: str) -> str:
    for marker in MOVIE_FILM_MARKERS:
        if marker.lower() in name.lower():
            return "电影卷"
    if film_type == "一次成像":
        return "一次成像"
    for prefix in SPECIAL_BRAND_PREFIXES:
        if name.startswith(prefix):
            return prefix
    return name.split(" ", 1)[0] if name else film_type


def _load_asset_film_options() -> list[FilmOption]:
    if not FILM_INDEX_PATH.exists():
        return []

    try:
        raw_items = json.loads(FILM_INDEX_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []

    options: list[FilmOption] = []
    for item in raw_items:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        film_type = str(item.get("film_type") or "胶卷").strip()
        label = str(item.get("display_name") or name).strip()
        cover_file = str(item.get("file") or "").strip()
        cover_path = FILM_COVER_DIR / cover_file if cover_file else None
        if cover_path and not cover_path.exists():
            cover_path = None
        group = _film_group_name(name, film_type)
        search_text = f"{label} {name} {film_type} {group}".lower()
        options.append(
            FilmOption(
                label=label,
                name=name,
                film_type=film_type,
                group=group,
                cover_path=str(cover_path) if cover_path else None,
                search_text=search_text,
            )
        )
    return options


def _fallback_film_options() -> list[FilmOption]:
    options: list[FilmOption] = []
    for group_name, films in FALLBACK_FILM_GROUPS:
        for film in films:
            options.append(
                FilmOption(
                    label=film,
                    name=film,
                    film_type=group_name,
                    group=group_name,
                    search_text=f"{film} {group_name}".lower(),
                )
            )
    return options


def _film_groups_from_options(options: list[FilmOption]) -> list[tuple[str, list[str]]]:
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for option in options:
        grouped[option.group].append(option.label)
    for labels in grouped.values():
        labels.sort(key=str.lower)

    order = {name: index for index, name in enumerate(GROUP_ORDER)}
    group_names = sorted(grouped, key=lambda name: (order.get(name, 999), name.lower()))
    return [(group_name, grouped[group_name]) for group_name in group_names]


def _default_film_label(options: list[FilmOption]) -> str:
    preferred_names = ["Kodak Portra 400", "Kodak Portra 400 01", "Kodak Gold 200"]
    for preferred in preferred_names:
        for option in options:
            if option.label == preferred or option.name == preferred:
                return option.label
    return options[0].label


FILM_OPTIONS = _load_asset_film_options() or _fallback_film_options()
FILM_BY_LABEL = {option.label: option for option in FILM_OPTIONS}
FILM_GROUPS = _film_groups_from_options(FILM_OPTIONS)
DEFAULT_FILM_NAME = _default_film_label(FILM_OPTIONS)


def _font_candidates() -> list[str]:
    preferred = [
        "C:/Windows/Fonts/NotoSansSC-VF.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    return preferred + [str(candidate) for candidate in FONT_CANDIDATES]


def register_font() -> str:
    for candidate in _font_candidates():
        font_path = find_font_path([candidate])
        if not font_path:
            continue
        try:
            LabelBase.register(
                APP_FONT,
                fn_regular=font_path,
                fn_bold=font_path,
                fn_italic=font_path,
                fn_bolditalic=font_path,
            )
            return APP_FONT
        except Exception:
            continue
    return "Roboto"


def image_source(path: Path) -> str:
    return path.resolve().as_posix()


class RoundedSurface(BoxLayout):
    bg_color = ListProperty([1, 1, 1, 1])
    radius = NumericProperty(dp(24))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(*self.bg_color)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._sync_shape, size=self._sync_shape, bg_color=self._sync_color, radius=self._sync_shape)

    def _sync_color(self, *_args):
        self._color.rgba = self.bg_color

    def _sync_shape(self, *_args):
        self._shape.pos = self.pos
        self._shape.size = self.size
        self._shape.radius = [self.radius]
        self.text_size = self.size


class CapsuleButton(Button):
    normal_color = ListProperty([0.08, 0.08, 0.09, 1])
    down_color = ListProperty([0.16, 0.16, 0.17, 1])
    radius = NumericProperty(dp(17))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = [0, 0, 0, 0]
        self.border = [0, 0, 0, 0]
        self.font_size = dp(15)
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self.shorten = True
        self.shorten_from = "right"
        with self.canvas.before:
            self._color = Color(*self.normal_color)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(
            pos=self._sync_shape,
            size=self._sync_shape,
            state=self._sync_state,
            normal_color=self._sync_state,
            down_color=self._sync_state,
            radius=self._sync_shape,
        )

    def _sync_state(self, *_args):
        self._color.rgba = self.down_color if self.state == "down" else self.normal_color

    def _sync_shape(self, *_args):
        self._shape.pos = self.pos
        self._shape.size = self.size
        self._shape.radius = [self.radius]
        self.text_size = self.size


class SearchInput(TextInput):
    bg_color = ListProperty([1, 1, 1, 1])
    radius = NumericProperty(dp(16))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_active = ""
        self.background_color = [1, 1, 1, 0]
        self.foreground_color = [0, 0, 0, 1]
        self.disabled_foreground_color = [0, 0, 0, 1]
        self.hint_text_color = [0.42, 0.42, 0.44, 1]
        self.cursor_color = [0.0, 0.48, 1.0, 1]
        self.selection_color = [0.0, 0.48, 1.0, 0.22]
        self.font_size = dp(16)
        self.halign = "left"
        self.multiline = False
        self.write_tab = False
        self.padding = [dp(16), dp(12), dp(16), dp(10)]
        with self.canvas.before:
            self._color = Color(*self.bg_color)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._sync_shape, size=self._sync_shape, bg_color=self._sync_color, radius=self._sync_shape)

    def _sync_color(self, *_args):
        self._color.rgba = self.bg_color

    def _sync_shape(self, *_args):
        self._shape.pos = self.pos
        self._shape.size = self.size
        self._shape.radius = [self.radius]
        self.text_size = self.size


class FontSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        if app and getattr(app, "font_name", None):
            self.font_name = app.font_name
        self.font_size = dp(15)
        self.color = [0.08, 0.08, 0.09, 1]
        self.halign = "center"
        self.valign = "middle"
        self.padding = [0, 0]
        self.background_normal = ""
        self.background_down = ""
        self.background_color = [0.98, 0.98, 0.985, 1]
        self.bind(size=lambda instance, _value: setattr(instance, "text_size", instance.size))


class CompactDropDown(DropDown):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.max_height = dp(240)
        self.bar_width = dp(4)
        self.scroll_type = ["bars", "content"]


class SoftSpinner(Spinner):
    normal_color = ListProperty([0.945, 0.947, 0.952, 1])
    down_color = ListProperty([0.90, 0.905, 0.915, 1])
    radius = NumericProperty(dp(16))

    def __init__(self, **kwargs):
        kwargs.setdefault("dropdown_cls", CompactDropDown)
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = [0, 0, 0, 0]
        self.color = [0.08, 0.08, 0.09, 1]
        self.font_size = dp(15)
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self.padding = [0, 0]
        self.option_cls = FontSpinnerOption
        with self.canvas.before:
            self._color = Color(*self.normal_color)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(
            pos=self._sync_shape,
            size=self._sync_shape,
            state=self._sync_state,
            normal_color=self._sync_state,
            down_color=self._sync_state,
            radius=self._sync_shape,
        )

    def _sync_state(self, *_args):
        self._color.rgba = self.down_color if self.state == "down" else self.normal_color

    def _sync_shape(self, *_args):
        self._shape.pos = self.pos
        self._shape.size = self.size
        self._shape.radius = [self.radius]
        self.text_size = self.size


class FilmBorderApp(App):
    def build(self):
        self.title = "Film Border"
        self.font_name = register_font()
        self.input_path: Path | None = None
        self.preview_path: Path | None = None
        self.preview_event = None
        self.pending_preview = False
        self.selected_film = DEFAULT_FILM_NAME
        self.side_border_ratio = DEFAULT_SIDE_BORDER_RATIO
        self.top_border_ratio = DEFAULT_TOP_BORDER_RATIO
        self.busy = False

        if platform not in ("android", "ios"):
            Window.size = (430, 760)
        Window.clearcolor = (0.957, 0.957, 0.970, 1)

        root = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16), dp(18), dp(16)],
            spacing=dp(14),
        )

        root.add_widget(self._build_header())
        root.add_widget(self._build_preview())
        root.add_widget(self._build_controls())
        root.opacity = 0
        Clock.schedule_once(lambda *_args: Animation(opacity=1, d=0.28, t="out_quad").start(root), 0)
        return root

    def _build_header(self) -> BoxLayout:
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(70), spacing=dp(2))
        title = self._label("Film Border", font_size=dp(30), bold=True, color=[0.05, 0.05, 0.055, 1])
        subtitle = self._label("打开相册，留下一块干净的胶卷白边", font_size=dp(13), color=[0.42, 0.42, 0.44, 1])
        title.height = dp(39)
        subtitle.height = dp(23)
        title.size_hint_y = None
        subtitle.size_hint_y = None
        header.add_widget(title)
        header.add_widget(subtitle)
        return header

    def _build_preview(self) -> RoundedSurface:
        panel = RoundedSurface(
            orientation="vertical",
            padding=dp(4),
            radius=dp(28),
            bg_color=[0.957, 0.957, 0.970, 1],
            size_hint=(1, 1),
        )
        stage = FloatLayout()
        self.preview_image = Image(
            source="",
            allow_stretch=True,
            keep_ratio=True,
            nocache=True,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            opacity=0,
        )
        self.placeholder = self._label(
            "打开相册后会在这里预览",
            font_size=dp(15),
            color=[0.55, 0.55, 0.58, 1],
        )
        self.placeholder.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        self.placeholder.size_hint = (1, None)
        self.placeholder.height = dp(40)
        stage.add_widget(self.preview_image)
        stage.add_widget(self.placeholder)
        panel.add_widget(stage)
        return panel

    def _build_controls(self) -> RoundedSurface:
        panel = RoundedSurface(
            orientation="vertical",
            padding=[dp(16), dp(15), dp(16), dp(14)],
            spacing=dp(10),
            radius=dp(26),
            bg_color=[1, 1, 1, 0.94],
            size_hint_y=None,
            height=dp(258),
        )

        self.film_button = CapsuleButton(
            text=self.selected_film,
            size_hint_y=None,
            height=dp(52),
            font_name=self.font_name,
            normal_color=[0.945, 0.947, 0.952, 1],
            down_color=[0.90, 0.905, 0.915, 1],
            color=[0.08, 0.08, 0.09, 1],
        )
        self.film_button.bind(on_release=self.open_film_picker)
        panel.add_widget(self.film_button)

        style_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(52), spacing=dp(10))
        self.style_spinner = SoftSpinner(
            text=DEFAULT_STYLE_LABEL,
            values=[style.label for style in STYLE_PRESETS.values()],
            size_hint=(1, 1),
            font_name=self.font_name,
        )
        self.text_align_spinner = SoftSpinner(
            text=DEFAULT_TEXT_ALIGN_LABEL,
            values=list(TEXT_ALIGN_BY_LABEL.keys()),
            size_hint=(1, 1),
            font_name=self.font_name,
        )
        self.style_spinner.bind(text=self._schedule_preview)
        self.text_align_spinner.bind(text=self._schedule_preview)
        style_row.add_widget(self.style_spinner)
        style_row.add_widget(self.text_align_spinner)
        panel.add_widget(style_row)

        button_row = GridLayout(cols=3, spacing=dp(10), size_hint_y=None, height=dp(52))
        album_button = CapsuleButton(
            text="打开相册",
            font_name=self.font_name,
            normal_color=[0.93, 0.935, 0.945, 1],
            down_color=[0.88, 0.885, 0.90, 1],
            color=[0.08, 0.08, 0.09, 1],
        )
        border_button = CapsuleButton(
            text="边框设置",
            font_name=self.font_name,
            normal_color=[0.93, 0.935, 0.945, 1],
            down_color=[0.88, 0.885, 0.90, 1],
            color=[0.08, 0.08, 0.09, 1],
        )
        save_button = CapsuleButton(
            text="保存成片",
            font_name=self.font_name,
            color=[1, 1, 1, 1],
        )
        album_button.bind(on_release=self.choose_photo)
        border_button.bind(on_release=self.open_border_settings)
        save_button.bind(on_release=self.save_current)
        button_row.add_widget(album_button)
        button_row.add_widget(border_button)
        button_row.add_widget(save_button)
        panel.add_widget(button_row)

        self.status_label = self._label("先打开相册选择一张照片。", font_size=dp(12), color=[0.50, 0.50, 0.53, 1])
        self.status_label.size_hint_y = None
        self.status_label.height = dp(26)
        self.status_label.shorten = True
        self.status_label.shorten_from = "right"
        panel.add_widget(self.status_label)
        return panel

    def _label(self, text: str, font_size, color, bold: bool = False) -> Label:
        label = Label(
            text=text,
            font_name=self.font_name,
            font_size=font_size,
            color=color,
            bold=bold,
            halign="left",
            valign="middle",
            size_hint_y=None,
        )
        label.bind(size=lambda instance, _value: setattr(instance, "text_size", instance.size))
        return label

    def _white_popup_content(self, padding, spacing) -> BoxLayout:
        content = BoxLayout(orientation="vertical", padding=padding, spacing=spacing)
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(24)])
        content.bind(
            pos=lambda instance, _value: setattr(content_bg, "pos", instance.pos),
            size=lambda instance, _value: setattr(content_bg, "size", instance.size),
        )
        return content

    def _select_film(self, name: str):
        self.selected_film = name
        self.film_button.text = name
        self._schedule_preview()

    def _current_film_option(self) -> FilmOption:
        return FILM_BY_LABEL.get(self.selected_film, FILM_OPTIONS[0])

    def _select_film_from_popup(self, name: str, popup: Popup):
        self._select_film(name)
        popup.dismiss()

    def _back_to_film_categories(self, popup: Popup):
        popup.dismiss()
        Clock.schedule_once(lambda *_clock_args: self.open_film_picker(), 0)

    def open_film_picker(self, *_args):
        content = self._white_popup_content(padding=[dp(20), dp(18), dp(20), dp(16)], spacing=dp(12))

        title = self._label("选择胶片", font_size=dp(18), color=[0.04, 0.04, 0.05, 1], bold=True)
        title.height = dp(34)
        content.add_widget(title)

        search_box = FloatLayout(size_hint_y=None, height=dp(50))
        search_input = SearchInput(
            hint_text="搜索胶片，例如 Portra / 400 / Vision3",
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            font_name=self.font_name,
        )
        # Some desktop IME/font combinations hide TextInput's own text layer.
        # This label mirrors the value inside the same rounded field.
        search_display = Label(
            text="",
            font_name=self.font_name,
            font_size=dp(16),
            color=[0, 0, 0, 1],
            bold=True,
            halign="left",
            valign="middle",
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            padding=[dp(16), 0],
        )
        search_display.bind(size=lambda instance, _value: setattr(instance, "text_size", instance.size))
        search_input.foreground_color = [0, 0, 0, 0]
        search_box.add_widget(search_input)
        search_box.add_widget(search_display)
        content.add_widget(search_box)

        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(4), scroll_type=["bars", "content"])
        list_content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        list_content.bind(minimum_height=list_content.setter("height"))
        scroll.add_widget(list_content)
        content.add_widget(scroll)

        popup = Popup(
            title="",
            title_size=0,
            separator_height=0,
            background="",
            background_color=[1, 1, 1, 0],
            content=content,
            size_hint=(0.90, None),
            height=dp(520),
            auto_dismiss=True,
        )

        def choose_film(name: str):
            self._select_film(name)
            popup.dismiss()

        def open_group(group_name: str, films: list[str]):
            popup.dismiss()
            Clock.schedule_once(lambda *_clock_args: self.open_film_group_picker(group_name, films), 0)

        def add_option(name: str, on_release):
            selected = name == self.selected_film
            option = CapsuleButton(
                text=name,
                font_name=self.font_name,
                size_hint_y=None,
                height=dp(46),
                normal_color=[0.08, 0.08, 0.09, 1] if selected else [0.945, 0.947, 0.952, 1],
                down_color=[0.16, 0.16, 0.17, 1] if selected else [0.90, 0.905, 0.915, 1],
                color=[1, 1, 1, 1] if selected else [0.05, 0.05, 0.06, 1],
            )
            option.bind(on_release=on_release)
            list_content.add_widget(option)

        def render_categories():
            list_content.clear_widgets()
            label = self._label("按品牌分类", font_size=dp(14), color=[0.36, 0.36, 0.38, 1], bold=True)
            label.height = dp(28)
            list_content.add_widget(label)
            for group_name, films in FILM_GROUPS:
                add_option(
                    f"{group_name}  ·  {len(films)} 款",
                    lambda _button, name=group_name, items=films: open_group(name, items),
                )

        def render_search(_instance=None, value: str = ""):
            raw_query = value.strip()
            search_display.text = value
            query = raw_query.lower()
            if not query:
                render_categories()
                return

            list_content.clear_widgets()
            results = [film for film in FILM_OPTIONS if query in film.search_text]
            label = self._label(
                f"搜索结果 {len(results)}",
                font_size=dp(14),
                color=[0.36, 0.36, 0.38, 1],
                bold=True,
            )
            label.height = dp(28)
            list_content.add_widget(label)

            if not results:
                empty = self._label("没有匹配的胶卷", font_size=dp(14), color=[0.55, 0.55, 0.58, 1], bold=True)
                empty.height = dp(42)
                list_content.add_widget(empty)
                return

            for film in results:
                add_option(film.label, lambda _button, name=film.label: choose_film(name))

        search_input.bind(text=render_search)
        render_categories()
        popup.open()
        Clock.schedule_once(lambda *_clock_args: setattr(search_input, "focus", True), 0.1)

    def open_film_group_picker(self, group_name: str, films: list[str]):
        content = self._white_popup_content(padding=[dp(20), dp(18), dp(20), dp(16)], spacing=dp(12))

        title = self._label(group_name, font_size=dp(18), color=[0.04, 0.04, 0.05, 1], bold=True)
        title.height = dp(34)
        content.add_widget(title)

        scroll = ScrollView(size_hint=(1, 1), bar_width=dp(4), scroll_type=["bars", "content"])
        list_content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        list_content.bind(minimum_height=list_content.setter("height"))

        popup = Popup(
            title="",
            title_size=0,
            separator_height=0,
            background="",
            background_color=[1, 1, 1, 0],
            content=content,
            size_hint=(0.90, None),
            height=dp(500),
            auto_dismiss=True,
        )

        for film_name in films:
            selected = film_name == self.selected_film
            option = CapsuleButton(
                text=film_name,
                font_name=self.font_name,
                size_hint_y=None,
                height=dp(46),
                normal_color=[0.08, 0.08, 0.09, 1] if selected else [0.945, 0.947, 0.952, 1],
                down_color=[0.16, 0.16, 0.17, 1] if selected else [0.90, 0.905, 0.915, 1],
                color=[1, 1, 1, 1] if selected else [0.05, 0.05, 0.06, 1],
            )
            option.bind(on_release=lambda _button, name=film_name: self._select_film_from_popup(name, popup))
            list_content.add_widget(option)

        scroll.add_widget(list_content)
        content.add_widget(scroll)

        footer = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, height=dp(50))
        back_button = CapsuleButton(
            text="返回分类",
            font_name=self.font_name,
            normal_color=[0.90, 0.905, 0.918, 1],
            down_color=[0.84, 0.85, 0.865, 1],
            color=[0.03, 0.03, 0.04, 1],
        )
        back_button.bind(on_release=lambda *_button_args: self._back_to_film_categories(popup))
        footer.add_widget(back_button)
        content.add_widget(footer)
        popup.open()

    def open_border_settings(self, *_args):
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(20), dp(18), dp(20), dp(16)],
            spacing=dp(14),
        )
        with content.canvas.before:
            Color(1, 1, 1, 1)
            content_bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(24)])
        content.bind(
            pos=lambda instance, _value: setattr(content_bg, "pos", instance.pos),
            size=lambda instance, _value: setattr(content_bg, "size", instance.size),
        )

        top_label = self._label("", font_size=dp(16), color=[0.04, 0.04, 0.05, 1], bold=True)
        top_label.height = dp(28)
        top_slider = Slider(
            min=MIN_BORDER_RATIO,
            max=MAX_BORDER_RATIO,
            value=self.top_border_ratio,
            step=0.001,
            size_hint_y=None,
            height=dp(44),
        )

        side_label = self._label("", font_size=dp(16), color=[0.04, 0.04, 0.05, 1], bold=True)
        side_label.height = dp(28)
        side_slider = Slider(
            min=MIN_BORDER_RATIO,
            max=MAX_BORDER_RATIO,
            value=self.side_border_ratio,
            step=0.001,
            size_hint_y=None,
            height=dp(44),
        )

        def update_label(label: Label, prefix: str, value: float):
            label.text = f"{prefix} {value * 100:.1f}%"

        def on_top_change(_slider, value: float):
            self.top_border_ratio = value
            update_label(top_label, "调整上边框", value)
            self._schedule_preview()

        def on_side_change(_slider, value: float):
            self.side_border_ratio = value
            update_label(side_label, "调整左右边框", value)
            self._schedule_preview()

        update_label(top_label, "调整上边框", self.top_border_ratio)
        update_label(side_label, "调整左右边框", self.side_border_ratio)
        top_slider.bind(value=on_top_change)
        side_slider.bind(value=on_side_change)

        content.add_widget(top_label)
        content.add_widget(top_slider)
        content.add_widget(side_label)
        content.add_widget(side_slider)

        button_row = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(52))
        reset_button = CapsuleButton(
            text="重置",
            font_name=self.font_name,
            normal_color=[0.90, 0.905, 0.918, 1],
            down_color=[0.84, 0.85, 0.865, 1],
            color=[0.03, 0.03, 0.04, 1],
        )
        done_button = CapsuleButton(text="完成", font_name=self.font_name, color=[1, 1, 1, 1])
        button_row.add_widget(reset_button)
        button_row.add_widget(done_button)
        content.add_widget(button_row)

        popup = Popup(
            title="",
            title_size=0,
            separator_height=0,
            background="",
            background_color=[1, 1, 1, 0],
            content=content,
            size_hint=(0.88, None),
            height=dp(320),
            auto_dismiss=True,
        )

        def reset_values(*_reset_args):
            top_slider.value = DEFAULT_TOP_BORDER_RATIO
            side_slider.value = DEFAULT_SIDE_BORDER_RATIO

        reset_button.bind(on_release=reset_values)
        done_button.bind(on_release=popup.dismiss)
        popup.open()

    def choose_photo(self, *_args):
        if self.busy:
            return
        if platform == "android":
            self._open_android_gallery()
            return
        self._open_desktop_album_picker()

    def _schedule_preview(self, *_args):
        if not self.input_path:
            return
        if self.busy:
            self.pending_preview = True
            return
        if self.preview_event is not None:
            self.preview_event.cancel()
        self.preview_event = Clock.schedule_once(self._run_scheduled_preview, 0.35)

    def _run_scheduled_preview(self, *_args):
        self.preview_event = None
        self.preview_current()

    def _open_desktop_album_picker(self):
        try:
            import tkinter as tk
            from tkinter import filedialog

            pictures = Path.home() / "Pictures"
            initial_dir = pictures if pictures.exists() else Path.home()

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            selected = filedialog.askopenfilename(
                title="选择照片",
                initialdir=str(initial_dir),
                filetypes=[
                    ("图片", "*.jpg *.jpeg *.png *.webp *.bmp"),
                    ("所有文件", "*.*"),
                ],
            )
            root.destroy()
            if selected:
                self._on_file_selection([selected])
            else:
                self.set_status("没有选择照片。")
        except Exception:
            self._open_desktop_fallback_picker()

    def _open_desktop_fallback_picker(self):
        chooser = FileChooserIconView(
            path=str(Path.home()),
            filters=["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"],
            multiselect=False,
        )
        buttons = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10), padding=[dp(8), dp(6)])
        cancel = CapsuleButton(
            text="取消",
            font_name=self.font_name,
            normal_color=[0.93, 0.935, 0.945, 1],
            down_color=[0.88, 0.885, 0.90, 1],
            color=[0.08, 0.08, 0.09, 1],
        )
        pick = CapsuleButton(text="选择", font_name=self.font_name, color=[1, 1, 1, 1])
        buttons.add_widget(cancel)
        buttons.add_widget(pick)

        content = BoxLayout(orientation="vertical", spacing=dp(6))
        content.add_widget(chooser)
        content.add_widget(buttons)
        popup = Popup(
            title="",
            title_size=0,
            separator_height=0,
            content=content,
            size_hint=(0.94, 0.90),
            auto_dismiss=True,
        )
        cancel.bind(on_release=popup.dismiss)
        pick.bind(on_release=lambda *_args: self._select_from_popup(chooser, popup))
        popup.open()

    def _open_android_gallery(self):
        try:
            from android import activity
            from jnius import autoclass

            self.set_status("正在打开系统相册。")
            activity.bind(on_activity_result=self._on_android_activity_result)

            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            try:
                BuildVersion = autoclass("android.os.Build$VERSION")
                MediaStore = autoclass("android.provider.MediaStore")
                if BuildVersion.SDK_INT >= 33:
                    intent = Intent(MediaStore.ACTION_PICK_IMAGES)
                    intent.setType("image/*")
                else:
                    ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")
                    intent = Intent(Intent.ACTION_PICK, ImagesMedia.EXTERNAL_CONTENT_URI)
                    intent.setType("image/*")
            except Exception:
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType("image/*")
                intent.addCategory(Intent.CATEGORY_OPENABLE)

            PythonActivity.mActivity.startActivityForResult(intent, ANDROID_PICK_IMAGE_REQUEST)
        except Exception as exc:
            self.set_status(f"无法打开系统相册：{exc}")

    def _on_android_activity_result(self, request_code, result_code, intent):
        if request_code != ANDROID_PICK_IMAGE_REQUEST:
            return

        try:
            from android import activity
            from jnius import autoclass

            try:
                activity.unbind(on_activity_result=self._on_android_activity_result)
            except Exception:
                pass

            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK or intent is None:
                self.set_status("没有选择照片。")
                return

            uri = intent.getData()
            if uri is None:
                clip_data = intent.getClipData()
                if clip_data is not None and clip_data.getItemCount() > 0:
                    uri = clip_data.getItemAt(0).getUri()
            if uri is None:
                self.set_status("没有拿到相册图片。")
                return
            self._on_file_selection([uri.toString()])
        except Exception as exc:
            self.set_status(f"读取相册图片失败：{exc}")

    def _select_from_popup(self, chooser: FileChooserIconView, popup: Popup):
        if chooser.selection:
            popup.dismiss()
            self._on_file_selection(chooser.selection)
        else:
            self.set_status("还没有选中照片。")

    def _on_file_selection(self, selection):
        if not selection:
            self.set_status("没有选择照片。")
            return

        try:
            self.input_path = self._selection_to_path(str(selection[0]))
        except Exception as exc:
            self.set_status(f"照片读取失败：{exc}")
            return

        self.placeholder.opacity = 1
        self.placeholder.text = "正在生成预览。"
        self.preview_image.source = ""
        self.preview_image.opacity = 0
        self.preview_image.reload()
        self.set_status("已选择照片，正在生成预览。")
        self.preview_current()

    def _selection_to_path(self, selected: str) -> Path:
        if selected.startswith("content://"):
            if platform != "android":
                raise ValueError("当前平台不能读取相册 URI。")
            return self._copy_android_uri_to_cache(selected)

        if selected.startswith("file://"):
            parsed = urlparse(selected)
            selected = unquote(parsed.path)
            if selected.startswith("/") and len(selected) > 2 and selected[2] == ":":
                selected = selected[1:]

        path = Path(selected)
        if not path.exists():
            raise FileNotFoundError(selected)
        self._validate_image_path(path)
        return path

    def _copy_android_uri_to_cache(self, uri_text: str) -> Path:
        from jnius import autoclass, jarray

        Uri = autoclass("android.net.Uri")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        FileOutputStream = autoclass("java.io.FileOutputStream")

        uri = Uri.parse(uri_text)
        resolver = PythonActivity.mActivity.getContentResolver()
        imports_dir = Path(self.user_data_dir) / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        decoded_path = self._decode_android_uri_to_jpeg(resolver, uri, imports_dir / f"album_{stamp}.jpg")
        if decoded_path is not None:
            self._validate_image_path(decoded_path)
            return decoded_path

        input_stream = resolver.openInputStream(uri)
        if input_stream is None:
            raise ValueError("无法打开相册图片流。")

        mime_type = (resolver.getType(uri) or "").lower()
        if mime_type in ("image/heic", "image/heif"):
            input_stream.close()
            raise ValueError("这张照片是 HEIC/HEIF，当前系统解码失败，请在相册中导出为 JPG 后再选。")

        ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
        }.get(mime_type, ".jpg")
        output_path = imports_dir / f"album_{stamp}{ext}"

        output_stream = FileOutputStream(str(output_path))
        buffer = jarray("b")([0] * 8192)
        try:
            while True:
                count = input_stream.read(buffer)
                if count < 0:
                    break
                if count:
                    output_stream.write(buffer, 0, count)
        finally:
            output_stream.close()
            input_stream.close()

        self._validate_image_path(output_path)
        return output_path

    def _decode_android_uri_to_jpeg(self, resolver, uri, output_path: Path) -> Path | None:
        from jnius import autoclass

        FileOutputStream = autoclass("java.io.FileOutputStream")
        bitmap = None
        input_stream = None
        output_stream = None

        try:
            try:
                BuildVersion = autoclass("android.os.Build$VERSION")
                if BuildVersion.SDK_INT >= 28:
                    ImageDecoder = autoclass("android.graphics.ImageDecoder")
                    source = ImageDecoder.createSource(resolver, uri)
                    bitmap = ImageDecoder.decodeBitmap(source)
            except Exception:
                bitmap = None

            if bitmap is None:
                BitmapFactory = autoclass("android.graphics.BitmapFactory")
                input_stream = resolver.openInputStream(uri)
                if input_stream is None:
                    return None
                bitmap = BitmapFactory.decodeStream(input_stream)

            if bitmap is None:
                return None

            BitmapCompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
            output_stream = FileOutputStream(str(output_path))
            ok = bitmap.compress(BitmapCompressFormat.JPEG, 95, output_stream)
            output_stream.flush()
            if not ok:
                return None
            return output_path
        except Exception:
            return None
        finally:
            if output_stream is not None:
                output_stream.close()
            if input_stream is not None:
                input_stream.close()
            if bitmap is not None:
                try:
                    bitmap.recycle()
                except Exception:
                    pass

    def _validate_image_path(self, path: Path):
        if not path.exists() or path.stat().st_size <= 0:
            raise ValueError("没有读取到有效照片数据。")

        try:
            from PIL import Image as PILImage

            with PILImage.open(path) as image:
                image.verify()
        except Exception as exc:
            raise ValueError("照片格式无法读取，请换一张 JPG/PNG，或在相册中重新导出后再选。") from exc

    def preview_current(self, *_args):
        if self.preview_event is not None:
            self.preview_event.cancel()
            self.preview_event = None
        if self.busy:
            self.pending_preview = True
            return
        if not self.input_path:
            self.set_status("请先打开相册选择一张照片。")
            return

        self._start_render(save=False)

    def save_current(self, *_args):
        if self.busy:
            return
        if not self.input_path:
            self.set_status("请先打开相册选择一张照片。")
            return

        self._start_render(save=True)

    def _start_render(self, save: bool):
        self.busy = True
        if not save:
            self.placeholder.text = "正在生成预览。"
            self._start_preview_loading()
        self.set_status("正在保存成片。" if save else "正在生成预览。")
        input_path = self.input_path
        film_option = self._current_film_option()
        style_key = self._current_style_key()
        text_align = self._current_text_align()
        side_border_ratio = self.side_border_ratio
        top_border_ratio = self.top_border_ratio
        thread = threading.Thread(
            target=self._render_worker,
            args=(
                save,
                input_path,
                film_option,
                style_key,
                text_align,
                side_border_ratio,
                top_border_ratio,
            ),
            daemon=True,
        )
        thread.start()

    def _render_worker(
        self,
        save: bool,
        input_path: Path,
        film_option: FilmOption,
        style_key: str,
        text_align: str,
        side_border_ratio: float,
        top_border_ratio: float,
    ):
        try:
            output = self._make_output_path(save)
            render_film_frame(
                input_path=input_path,
                output_path=output,
                film_name=film_option.name,
                film_type=film_option.film_type,
                film_cover_path=film_option.cover_path,
                style_key=style_key,
                text_align=text_align,
                side_border_ratio=side_border_ratio,
                top_border_ratio=top_border_ratio,
                max_long_edge=None if save else 1800,
            )
            if platform == "android" and save:
                self._scan_android_gallery(output)
            Clock.schedule_once(lambda *_args: self._render_done(output, save))
        except Exception as exc:
            message = str(exc)
            Clock.schedule_once(lambda *_args: self._render_failed(message))

    def _make_output_path(self, save: bool) -> Path:
        if save:
            directory = self._export_dir()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return directory / f"film_border_{stamp}.jpg"

        directory = Path(self.user_data_dir) / "preview"
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return directory / f"preview_{stamp}.jpg"

    def _export_dir(self) -> Path:
        if platform == "android":
            try:
                from android.storage import primary_external_storage_path

                directory = Path(primary_external_storage_path()) / "Pictures" / "FilmBorder"
            except Exception:
                directory = Path(self.user_data_dir) / "exports"
        else:
            directory = Path.cwd() / "exports"

        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _current_style_key(self) -> str:
        return STYLE_BY_LABEL.get(self.style_spinner.text, "classic_white")

    def _current_text_align(self) -> str:
        return TEXT_ALIGN_BY_LABEL.get(self.text_align_spinner.text, "center")

    def _render_done(self, output: Path, save: bool):
        self.busy = False
        if save:
            self.set_status(f"已保存：{output}")
            if self.pending_preview:
                self.pending_preview = False
                self._schedule_preview()
            return

        self.preview_path = output
        self._stop_preview_loading()
        Animation.cancel_all(self.placeholder)
        Animation(opacity=0, d=0.16, t="out_quad").start(self.placeholder)
        self.preview_image.source = ""
        self.preview_image.reload()
        self.preview_image.opacity = 0
        self.preview_image.source = image_source(output)
        self.preview_image.reload()
        Animation.cancel_all(self.preview_image)
        Animation(opacity=1, d=0.26, t="out_quad").start(self.preview_image)
        self.set_status("预览已更新。")
        if self.pending_preview:
            self.pending_preview = False
            self._schedule_preview()

    def _render_failed(self, message: str):
        self.busy = False
        self._stop_preview_loading()
        self.placeholder.text = "预览生成失败。"
        Animation.cancel_all(self.placeholder)
        self.placeholder.opacity = 0
        Animation(opacity=1, d=0.18, t="out_quad").start(self.placeholder)
        self.set_status(f"处理失败：{self._friendly_error(message)}")
        if self.pending_preview:
            self.pending_preview = False
            self._schedule_preview()

    def _start_preview_loading(self):
        self.placeholder.opacity = max(self.placeholder.opacity, 0.45)
        Animation.cancel_all(self.placeholder)
        pulse = Animation(opacity=0.45, d=0.55, t="in_out_sine") + Animation(
            opacity=1,
            d=0.55,
            t="in_out_sine",
        )
        pulse.repeat = True
        pulse.start(self.placeholder)

    def _stop_preview_loading(self):
        Animation.cancel_all(self.placeholder)

    def set_status(self, text: str):
        text = " ".join(str(text).split())
        if len(text) > 90:
            text = f"{text[:87]}..."
        self.status_label.text = text

    def _friendly_error(self, message: str) -> str:
        lower_message = message.lower()
        if "cannot identify image file" in lower_message:
            return "照片格式无法读取，请换一张 JPG/PNG，或在相册中重新导出后再选。"
        if "heic" in lower_message or "heif" in lower_message:
            return "HEIC/HEIF 解码失败，请在相册中导出为 JPG 后再选。"
        return message

    def _scan_android_gallery(self, path: Path):
        try:
            from jnius import autoclass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            MediaScannerConnection = autoclass("android.media.MediaScannerConnection")
            MediaScannerConnection.scanFile(PythonActivity.mActivity, [str(path)], None, None)
        except Exception:
            pass


if __name__ == "__main__":
    FilmBorderApp().run()
