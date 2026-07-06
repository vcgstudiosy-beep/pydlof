"""
التحقق من صحة ملفات .dlof مقابل مخطط XSD الرسمي، باستخدام lxml.
"""

from __future__ import annotations

import os
from typing import List, Union

from lxml import etree

from .exceptions import DlofValidationError

_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schema")
_DLOF_XSD_PATH = os.path.join(_SCHEMA_DIR, "dlof.xsd")
_TEMPLATE_XSD_PATH = os.path.join(_SCHEMA_DIR, "dlof-template.xsd")

_dlof_schema_cache = None
_template_schema_cache = None


def _load_schema(path: str) -> etree.XMLSchema:
    with open(path, "rb") as f:
        schema_doc = etree.parse(f)
    return etree.XMLSchema(schema_doc)


def _get_dlof_schema() -> etree.XMLSchema:
    global _dlof_schema_cache
    if _dlof_schema_cache is None:
        _dlof_schema_cache = _load_schema(_DLOF_XSD_PATH)
    return _dlof_schema_cache


def _get_template_schema() -> etree.XMLSchema:
    global _template_schema_cache
    if _template_schema_cache is None:
        _template_schema_cache = _load_schema(_TEMPLATE_XSD_PATH)
    return _template_schema_cache


def validate_file(path: str, kind: str = "dlof") -> List[str]:
    """
    يتحقق من ملف XML مقابل مخطط DLoF.
    kind: "dlof" لملفات .dlof/.ep/.episode أو "template" لملفات template.xml.
    يعيد قائمة رسائل الأخطاء (فارغة إن كان الملف صحيحاً).
    """
    with open(path, "rb") as f:
        doc = etree.parse(f)
    return validate_element(doc, kind=kind)


def validate_string(xml_text: Union[str, bytes], kind: str = "dlof") -> List[str]:
    data = xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text
    doc = etree.fromstring(data)
    return validate_element(doc, kind=kind)


def validate_element(doc, kind: str = "dlof") -> List[str]:
    schema = _get_dlof_schema() if kind == "dlof" else _get_template_schema()
    is_valid = schema.validate(doc)
    if is_valid:
        return []
    return [str(err) for err in schema.error_log]


def assert_valid(path_or_text: str, kind: str = "dlof", is_path: bool = True) -> None:
    """يرفع DlofValidationError إن كان الملف/النص غير صالح."""
    errors = validate_file(path_or_text, kind=kind) if is_path else validate_string(path_or_text, kind=kind)
    if errors:
        raise DlofValidationError(
            f"فشل التحقق من صحة {'الملف' if is_path else 'النص'}:\n" + "\n".join(errors)
        )
