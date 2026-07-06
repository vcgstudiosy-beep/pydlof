"""
تحليل وكتابة ملف `set.txt` — إعدادات السلسلة (fonts, theme, display,
episodes, comic, reading, audio, subtitles, characters, export, meta).

الصيغة: `key=value` سطر لكل إعداد، والتعليقات تبدأ بـ `#`.
المفاتيح منظمة بنقاط (namespaces) مثل `theme.primaryColor`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Optional


def parse_set_txt(text: str) -> Dict[str, str]:
    """يحلّل محتوى set.txt إلى قاموس مسطّح {key: value}."""
    settings: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        # يسمح بتعليق نهاية السطر بعد فراغ متبوع بـ # (مثل: fonts.title=Cairo.ttf   # ملاحظة)
        # لكن لا يقطع قيماً تبدأ بـ # مباشرة (مثل ألوان hex: #6200EE)
        match = re.search(r"\s#", rest)
        value = (rest[: match.start()] if match else rest).strip()
        settings[key.strip()] = value
    return settings


def load_set_txt(path: str) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        return parse_set_txt(f.read())


def write_set_txt(settings: Dict[str, str], path: Optional[str] = None) -> str:
    """يكتب قاموس الإعدادات إلى نص set.txt (سطر key=value لكل مفتاح)."""
    lines = [f"{k}={v}" for k, v in settings.items()]
    text = "\n".join(lines) + "\n"
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return text


def _get(d: Dict[str, str], key: str, default: str = "") -> str:
    return d.get(key, default)


def _get_bool(d: Dict[str, str], key: str, default: bool = False) -> bool:
    val = d.get(key)
    if val is None or val == "":
        return default
    return val.strip().lower() == "true"


def _get_int(d: Dict[str, str], key: str, default: int = 0) -> int:
    val = d.get(key)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


@dataclass
class SeriesSettings:
    """واجهة مريحة ومكتوبة النوع فوق قاموس مفاتيح set.txt المسطّح."""

    raw: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_text(cls, text: str) -> "SeriesSettings":
        return cls(raw=parse_set_txt(text))

    @classmethod
    def from_file(cls, path: str) -> "SeriesSettings":
        return cls(raw=load_set_txt(path))

    def to_text(self) -> str:
        return write_set_txt(self.raw)

    def save(self, path: str) -> str:
        return write_set_txt(self.raw, path)

    def get(self, key: str, default: str = "") -> str:
        return self.raw.get(key, default)

    def set(self, key: str, value) -> None:
        self.raw[key] = str(value)

    # ── اختصارات لأشهر الحقول ──
    @property
    def series_id(self) -> str:
        return _get(self.raw, "series.id")

    @property
    def series_title(self) -> str:
        return _get(self.raw, "series.title")

    @property
    def series_domain(self) -> str:
        return _get(self.raw, "series.domain", "series")

    @property
    def language(self) -> str:
        return _get(self.raw, "series.language", "ar")

    @property
    def rtl(self) -> bool:
        return _get_bool(self.raw, "series.rtl", True)

    @property
    def primary_color(self) -> str:
        return _get(self.raw, "theme.primaryColor", "#6200EE")

    @property
    def secondary_color(self) -> str:
        return _get(self.raw, "theme.secondaryColor", "#03DAC6")

    @property
    def background_color(self) -> str:
        return _get(self.raw, "theme.backgroundColor", "#FFFFFF")

    @property
    def text_color(self) -> str:
        return _get(self.raw, "theme.textColor", "#1C1B1F")

    @property
    def dark_mode(self) -> bool:
        return _get_bool(self.raw, "theme.darkMode", False)

    @property
    def display_layout(self) -> str:
        return _get(self.raw, "display.layout", "standard")

    @property
    def total_episodes(self) -> int:
        return _get_int(self.raw, "episodes.totalEpisodes", 0)

    @property
    def total_seasons(self) -> int:
        return _get_int(self.raw, "episodes.totalSeasons", 1)

    @property
    def characters_file(self) -> Optional[str]:
        val = self.get("characters.file")
        return val or None
