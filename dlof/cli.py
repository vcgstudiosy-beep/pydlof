"""
واجهة سطر الأوامر لمكتبة dlof.

الاستخدام:
    python -m dlof validate file.dlof
    python -m dlof info file.dlof
    python -m dlof chain file.dlof
    python -m dlof tohtml file.dlof -o out.html
    python -m dlof check-loop /path/to/folder
"""

from __future__ import annotations

import argparse
import sys

from . import html_export, loop, validator
from .exceptions import DlofError
from .parser import parse_file


def cmd_validate(args) -> int:
    errors = validator.validate_file(args.file)
    if not errors:
        print(f"✔ صالح: {args.file}")
        return 0
    print(f"✘ غير صالح: {args.file}")
    for err in errors:
        print(f"  - {err}")
    return 1


def cmd_info(args) -> int:
    doc = parse_file(args.file)
    print(f"id: {doc.id}")
    print(f"العنوان: {doc.metadata.title}")
    print(f"المجال: {doc.metadata.domain.value}")
    print(f"المؤلف: {doc.metadata.author or '-'}")
    print(f"loopRoot: {doc.loop_links.loop_root}")
    print(f"previous: {doc.loop_links.previous.ref if doc.loop_links.previous else '-'}")
    print(f"next: {doc.loop_links.next.ref if doc.loop_links.next else '-'}")
    print(f"عدد عناصر المحتوى: {len(doc.content)}")
    print(f"عدد المرفقات: {len(doc.attachments)}")
    return 0


def cmd_chain(args) -> int:
    try:
        nodes = loop.ordered_chain(args.file)
    except DlofError as exc:
        print(f"خطأ: {exc}", file=sys.stderr)
        return 1
    for i, node in enumerate(nodes, start=1):
        marker = " (البداية)" if node.document.loop_links.loop_root else ""
        print(f"{i}. {node.filename} — {node.document.metadata.title}{marker}")
    return 0


def cmd_tohtml(args) -> int:
    doc = parse_file(args.file)
    out_path = args.output or (args.file.rsplit(".", 1)[0] + ".html")
    html_export.write_html(doc, out_path)
    print(f"تم إنشاء: {out_path}")
    return 0


def cmd_check_loop(args) -> int:
    errors = loop.validate_loop_integrity(args.folder)
    if not errors:
        print("✔ كل روابط الحلقة سليمة")
        return 0
    print("✘ روابط معلّقة:")
    for err in errors:
        print(f"  - {err}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dlof", description="أداة سطر أوامر لصيغة DLoF")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="التحقق من صحة ملف .dlof مقابل المخطط الرسمي")
    p_validate.add_argument("file")
    p_validate.set_defaults(func=cmd_validate)

    p_info = sub.add_parser("info", help="عرض معلومات موجزة عن ملف .dlof")
    p_info.add_argument("file")
    p_info.set_defaults(func=cmd_info)

    p_chain = sub.add_parser("chain", help="عرض الحلقة كاملة بدءاً من أي ملف فيها")
    p_chain.add_argument("file")
    p_chain.set_defaults(func=cmd_chain)

    p_tohtml = sub.add_parser("tohtml", help="تحويل ملف .dlof إلى صفحة HTML مستقلة")
    p_tohtml.add_argument("file")
    p_tohtml.add_argument("-o", "--output", default=None)
    p_tohtml.set_defaults(func=cmd_tohtml)

    p_check = sub.add_parser("check-loop", help="فحص سلامة كل الروابط ضمن مجلد حلقة")
    p_check.add_argument("folder")
    p_check.set_defaults(func=cmd_check_loop)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
