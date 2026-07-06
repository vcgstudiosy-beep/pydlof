"""
أدوات التجوّل في "الحلقة" (loop) — تتبّع previous/next عبر ملفات .dlof
متعددة داخل مجلد واحد، دون أي فهرس مركزي، تماشياً مع فلسفة الصيغة.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

from . import models as m
from . import parser
from .exceptions import DlofLinkError
from .models import LOOP_FILE_EXTENSIONS


def resolve_ref(base_dir: str, ref: str) -> Optional[str]:
    """
    يحاول إيجاد المسار الفعلي لملف مُشار إليه بواسطة `ref` ضمن loopLinks،
    بالبحث في نفس المجلد وبتجربة الامتدادات المرادفة (.dlof/.ep/.episode).
    يعيد None إن تعذّر العثور على الملف (رابط معلّق — حالة طبيعية في DLoF).
    """
    candidate = os.path.join(base_dir, ref)
    if os.path.isfile(candidate):
        return candidate

    root, ext = os.path.splitext(ref)
    if ext.lower() in LOOP_FILE_EXTENSIONS:
        for alt_ext in LOOP_FILE_EXTENSIONS:
            alt_path = os.path.join(base_dir, root + alt_ext)
            if os.path.isfile(alt_path):
                return alt_path
    return None


def load_folder(folder: str) -> Dict[str, m.DocumentLoop]:
    """
    يحمّل كل ملفات .dlof/.ep/.episode ضمن مجلد (غير متكرر داخل مجلدات فرعية)
    ويعيدها كقاموس {اسم_الملف: DocumentLoop}.
    """
    docs: Dict[str, m.DocumentLoop] = {}
    for name in sorted(os.listdir(folder)):
        _, ext = os.path.splitext(name)
        if ext.lower() not in LOOP_FILE_EXTENSIONS:
            continue
        full_path = os.path.join(folder, name)
        if not os.path.isfile(full_path):
            continue
        try:
            docs[name] = parser.parse_file(full_path)
        except Exception:
            # ملف غير صالح ضمن المجلد — يُتجاهل عند بناء الحلقة الكاملة
            continue
    return docs


def find_loop_root(folder: str) -> Optional[str]:
    """يعيد اسم الملف الذي يحمل loopRoot=true ضمن المجلد، إن وُجد."""
    for name, doc in load_folder(folder).items():
        if doc.loop_links.loop_root:
            return name
    return None


@dataclass
class LoopNode:
    filename: str
    document: m.DocumentLoop


def walk_next(start_path: str, max_steps: int = 10_000) -> Iterator[LoopNode]:
    """
    يتجوّل بدءاً من ملف معيّن في اتجاه next حتى الوصول لنهاية الحلقة
    (لا next) أو حتى يعود للملف الذي بدأ منه (حلقة مغلقة).
    """
    base_dir = os.path.dirname(os.path.abspath(start_path))
    visited = set()
    current_path = os.path.abspath(start_path)

    steps = 0
    while current_path and steps < max_steps:
        steps += 1
        if current_path in visited:
            return  # عاد إلى نقطة زُرناها من قبل: حلقة مغلقة، توقف
        visited.add(current_path)

        doc = parser.parse_file(current_path)
        yield LoopNode(filename=os.path.basename(current_path), document=doc)

        if doc.loop_links.next is None:
            return
        next_path = resolve_ref(base_dir, doc.loop_links.next.ref)
        if next_path is None:
            raise DlofLinkError(
                f"الرابط 'next' في {current_path} يشير إلى "
                f"'{doc.loop_links.next.ref}' الذي لا يمكن العثور عليه"
            )
        current_path = next_path


def walk_previous(start_path: str, max_steps: int = 10_000) -> Iterator[LoopNode]:
    """نفس walk_next لكن باتجاه previous."""
    base_dir = os.path.dirname(os.path.abspath(start_path))
    visited = set()
    current_path = os.path.abspath(start_path)

    steps = 0
    while current_path and steps < max_steps:
        steps += 1
        if current_path in visited:
            return
        visited.add(current_path)

        doc = parser.parse_file(current_path)
        yield LoopNode(filename=os.path.basename(current_path), document=doc)

        if doc.loop_links.previous is None:
            return
        prev_path = resolve_ref(base_dir, doc.loop_links.previous.ref)
        if prev_path is None:
            raise DlofLinkError(
                f"الرابط 'previous' في {current_path} يشير إلى "
                f"'{doc.loop_links.previous.ref}' الذي لا يمكن العثور عليه"
            )
        current_path = prev_path


def ordered_chain(start_path: str) -> List[LoopNode]:
    """
    يبني قائمة كاملة مرتبة للحلقة بدءاً من أي نقطة فيها: يعود للخلف أولاً
    حتى يجد البداية (أو حلقة مغلقة)، ثم يمشي للأمام حتى النهاية.
    """
    # walk_previous يبدأ بعقدة start_path نفسها، فنأخذها ونعكس الترتيب
    backward = list(walk_previous(start_path))
    backward.reverse()  # الآن: [البداية ... start_path]

    # walk_next يبدأ أيضاً بعقدة start_path نفسها — نتجاهل أول عنصر لتفادي التكرار
    forward_from_start = list(walk_next(start_path))[1:]

    chain = backward + forward_from_start

    # في حال الحلقة المغلقة، قد يظهر نفس الملف مرتين (البداية في النهاية)؛
    # نزيل أي تكرار لاحق مع الحفاظ على أول ظهور.
    seen = set()
    unique_chain = []
    for node in chain:
        if node.filename in seen:
            continue
        seen.add(node.filename)
        unique_chain.append(node)
    return unique_chain


def validate_loop_integrity(folder: str) -> List[str]:
    """
    يفحص كل ملفات المجلد ويتأكد أن كل رابط previous/next يُحلّ فعلياً
    إلى ملف موجود. يعيد قائمة رسائل الأخطاء (فارغة إن كانت كل الروابط سليمة).
    """
    errors = []
    docs = load_folder(folder)
    for name, doc in docs.items():
        for direction, link in (("previous", doc.loop_links.previous), ("next", doc.loop_links.next)):
            if link is None:
                continue
            if resolve_ref(folder, link.ref) is None:
                errors.append(f"{name}: رابط {direction} معلّق -> '{link.ref}' غير موجود")
    return errors
