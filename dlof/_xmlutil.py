"""أدوات داخلية مساعدة للتعامل مع XML (lxml)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from lxml import etree

NS = "https://dlof.org/schema/1.0"
NSMAP = {None: NS}


def q(tag: str) -> str:
    """يعيد اسم العنصر مؤهلاً بمجال الأسماء الرسمي لـ DLoF."""
    return f"{{{NS}}}{tag}"


def find_text(parent: etree._Element, tag: str) -> Optional[str]:
    el = parent.find(q(tag))
    if el is None:
        return None
    return el.text if el.text is not None else ""


def find_int(parent: etree._Element, tag: str) -> Optional[int]:
    text = find_text(parent, tag)
    return int(text) if text not in (None, "") else None


def find_bool(parent: etree._Element, tag: str, default: bool = False) -> bool:
    text = find_text(parent, tag)
    if text is None:
        return default
    return text.strip().lower() == "true"


def find_datetime(parent: etree._Element, tag: str) -> Optional[datetime]:
    text = find_text(parent, tag)
    if not text:
        return None
    return parse_datetime(text)


def find_date(parent: etree._Element, tag: str) -> Optional[date]:
    text = find_text(parent, tag)
    if not text:
        return None
    return date.fromisoformat(text.strip())


def parse_datetime(text: str) -> datetime:
    text = text.strip()
    # xs:dateTime قد ينتهي بـ Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def sub(parent: etree._Element, tag: str, text: Optional[str] = None) -> etree._Element:
    """يضيف عنصراً فرعياً بنص اختياري، ويعيده."""
    el = etree.SubElement(parent, q(tag))
    if text is not None:
        el.text = text
    return el


def sub_if(parent: etree._Element, tag: str, value) -> Optional[etree._Element]:
    """يضيف عنصراً فرعياً فقط إن كانت القيمة غير فارغة (not None)."""
    if value is None:
        return None
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (datetime, date)):
        text = value.isoformat()
    else:
        text = str(value)
    return sub(parent, tag, text)
