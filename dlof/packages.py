"""
التعامل مع صيغ حزم DLoF الثلاث (راجع spec/PACKAGE_FORMATS.md):

- `.dlofpkg`      — ملف dlof واحد + meta.json + مرفقات (توزيع مستقل)
- `.dlofSeries`   — سلسلة كاملة (مجلد مضغوط بهيكله الداخلي)
- `.dlofTemplate` — حزمة قالب تصميم (template.xml + Template.kt)
"""

from __future__ import annotations

import json
import os
import zipfile
from typing import Dict, Optional, Tuple

from lxml import etree

from . import models as m
from . import parser as dlof_parser
from . import writer as dlof_writer
from .exceptions import DlofPackageError

DLOFPKG_VERSION = "1.0"
TEMPLATE_NS = "https://dlof.org/schema/template/1.0"


# ══════════════════════════════════════════════════════════════
# .dlofpkg — حزمة ملف dlof فردي
# ══════════════════════════════════════════════════════════════

def create_dlofpkg(doc: m.DocumentLoop, output_path: str,
                    extra_meta: Optional[Dict] = None) -> str:
    """
    يبني حزمة .dlofpkg تحتوي package.dlof + meta.json + مرفقات مستخرجة
    من doc.attachments (بدلاً من تضمينها base64 مضاعفاً داخل الـ zip).
    """
    meta = {
        "id": doc.id,
        "title": doc.metadata.title,
        "domain": doc.metadata.domain.value if isinstance(doc.metadata.domain, m.Domain) else str(doc.metadata.domain),
        "version": doc.version,
        "author": doc.metadata.author or "",
        "language": doc.metadata.language,
        "createdAt": doc.metadata.created_at.isoformat() if doc.metadata.created_at else "",
        "dlofpkg_version": DLOFPKG_VERSION,
    }
    if extra_meta:
        meta.update(extra_meta)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("package.dlof", dlof_writer.to_string(doc))
        zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        for att in doc.attachments:
            if att.data is not None:
                zf.writestr(f"attachments/{att.file_name}", att.data)
    return output_path


def read_dlofpkg(path: str) -> Tuple[m.DocumentLoop, Dict]:
    """يقرأ حزمة .dlofpkg ويعيد (DocumentLoop, meta.json كقاموس)."""
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if "package.dlof" not in names:
            raise DlofPackageError(f"{path} لا يحتوي package.dlof — حزمة .dlofpkg غير صالحة")
        xml_text = zf.read("package.dlof").decode("utf-8")
        doc = dlof_parser.parse_string(xml_text)

        meta = {}
        if "meta.json" in names:
            meta = json.loads(zf.read("meta.json").decode("utf-8"))
        return doc, meta


def extract_dlofpkg(path: str, dest_dir: str) -> str:
    """يستخرج حزمة .dlofpkg بالكامل (الملف + المرفقات) إلى مجلد."""
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(dest_dir)
    return dest_dir


# ══════════════════════════════════════════════════════════════
# .dlofSeries — حزمة السلسلة الكاملة
# ══════════════════════════════════════════════════════════════

def create_dlof_series(series_folder: str, output_path: str) -> str:
    """
    يضغط مجلد سلسلة كاملاً (بما فيه series-index.dlof، الحلقات، fonts/،
    media/، set.txt، characters.dlof) إلى ملف .dlofSeries.
    """
    series_folder = os.path.abspath(series_folder)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(series_folder):
            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, os.path.dirname(series_folder))
                zf.write(full_path, rel_path)
    return output_path


def extract_dlof_series(path: str, dest_dir: str) -> str:
    """
    يستخرج حزمة .dlofSeries إلى dest_dir ويعيد مسار مجلد السلسلة الفعلي
    (المجلد الجذري الوحيد داخل الأرشيف).
    """
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(dest_dir)
        top_levels = {os.path.normpath(n).split(os.sep)[0] for n in zf.namelist()}

    if len(top_levels) == 1:
        return os.path.join(dest_dir, next(iter(top_levels)))
    return dest_dir


# ══════════════════════════════════════════════════════════════
# .dlofTemplate — حزمة قالب تصميم
# ══════════════════════════════════════════════════════════════

def _template_xml_to_string(pkg: m.DlofTemplatePackage) -> str:
    nsmap = {None: TEMPLATE_NS}
    root = etree.Element(f"{{{TEMPLATE_NS}}}dlofTemplate", nsmap=nsmap)
    root.set("id", pkg.id)
    root.set("name", pkg.name)
    if pkg.author:
        root.set("author", pkg.author)
    root.set("version", pkg.version)

    design_el = etree.SubElement(root, f"{{{TEMPLATE_NS}}}design")
    d = pkg.design
    if d.primary_color:
        design_el.set("primaryColor", d.primary_color)
    if d.secondary_color:
        design_el.set("secondaryColor", d.secondary_color)
    if d.background_color:
        design_el.set("backgroundColor", d.background_color)
    if d.text_color:
        design_el.set("textColor", d.text_color)
    if d.font_family:
        design_el.set("fontFamily", d.font_family)
    design_el.set("layout", d.layout.value if isinstance(d.layout, m.TemplateLayout) else str(d.layout))
    if d.header_attachment_ref:
        design_el.set("headerAttachmentRef", d.header_attachment_ref)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")


def _parse_template_xml(xml_text: str) -> m.DlofTemplatePackage:
    root = etree.fromstring(xml_text.encode("utf-8"))
    design_el = root.find(f"{{{TEMPLATE_NS}}}design")
    layout_text = design_el.get("layout", "standard") if design_el is not None else "standard"
    try:
        layout = m.TemplateLayout(layout_text)
    except ValueError:
        layout = m.TemplateLayout.STANDARD

    design = m.Template(
        ref=root.get("id"),
        primary_color=design_el.get("primaryColor") if design_el is not None else None,
        secondary_color=design_el.get("secondaryColor") if design_el is not None else None,
        background_color=design_el.get("backgroundColor") if design_el is not None else None,
        text_color=design_el.get("textColor") if design_el is not None else None,
        font_family=design_el.get("fontFamily") if design_el is not None else None,
        layout=layout,
        header_attachment_ref=design_el.get("headerAttachmentRef") if design_el is not None else None,
    )
    return m.DlofTemplatePackage(
        id=root.get("id", ""),
        name=root.get("name", ""),
        design=design,
        author=root.get("author"),
        version=root.get("version", "1.0"),
    )


def _template_kt_source(pkg: m.DlofTemplatePackage) -> str:
    """يولّد Template.kt مرجعياً مطابقاً لصيغة المثال في التوثيق."""
    d = pkg.design
    layout_name = (d.layout.value if isinstance(d.layout, m.TemplateLayout) else str(d.layout)).upper()

    def kt_str(value: Optional[str]) -> str:
        return f'"{value}"' if value else "null"

    return (
        f"val {pkg.id.replace('-', '_')}Template = Template(\n"
        f"    ref = \"{pkg.id}\",\n"
        f"    primaryColor = {kt_str(d.primary_color)},\n"
        f"    secondaryColor = {kt_str(d.secondary_color)},\n"
        f"    backgroundColor = {kt_str(d.background_color)},\n"
        f"    textColor = {kt_str(d.text_color)},\n"
        f"    fontFamily = {kt_str(d.font_family)},\n"
        f"    layout = TemplateLayout.{layout_name},\n"
        f"    headerAttachmentRef = {kt_str(d.header_attachment_ref)}\n"
        f")\n"
    )


def create_dlof_template(pkg: m.DlofTemplatePackage, output_path: str) -> str:
    """يبني حزمة .dlofTemplate (template.xml + Template.kt)."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("template.xml", _template_xml_to_string(pkg))
        zf.writestr("Template.kt", _template_kt_source(pkg))
    return output_path


def read_dlof_template(path: str) -> m.DlofTemplatePackage:
    """يقرأ حزمة .dlofTemplate ويعيد DlofTemplatePackage (من template.xml)."""
    with zipfile.ZipFile(path, "r") as zf:
        if "template.xml" not in zf.namelist():
            raise DlofPackageError(f"{path} لا يحتوي template.xml — حزمة .dlofTemplate غير صالحة")
        xml_text = zf.read("template.xml").decode("utf-8")
    return _parse_template_xml(xml_text)


def load_template_library(folder: str) -> Dict[str, m.DlofTemplatePackage]:
    """
    يحمّل كل ملفات .dlofTemplate ضمن مجلد إلى قاموس {id: DlofTemplatePackage}،
    ليُستخدم لاحقاً في resolve_template.
    """
    library: Dict[str, m.DlofTemplatePackage] = {}
    for name in os.listdir(folder):
        if name.endswith(".dlofTemplate"):
            pkg = read_dlof_template(os.path.join(folder, name))
            library[pkg.id] = pkg
    return library


def resolve_template(template: m.Template, library: Dict[str, m.DlofTemplatePackage]) -> m.Template:
    """
    يحلّ template.ref مقابل مكتبة قوالب محلية (راجع dlof-template.xsd):
    الحقول المحلية المحددة صراحة في template تطغى على تصميم القالب المرجعي.
    إن لم يوجد ref أو لم يوجد القالب في المكتبة، يُعاد template كما هو.
    """
    if not template.ref or template.ref not in library:
        return template

    base_design = library[template.ref].design
    return m.Template(
        ref=template.ref,
        primary_color=template.primary_color or base_design.primary_color,
        secondary_color=template.secondary_color or base_design.secondary_color,
        background_color=template.background_color or base_design.background_color,
        text_color=template.text_color or base_design.text_color,
        font_family=template.font_family or base_design.font_family,
        layout=template.layout if template.layout != m.TemplateLayout.STANDARD else base_design.layout,
        header_attachment_ref=template.header_attachment_ref or base_design.header_attachment_ref,
    )
