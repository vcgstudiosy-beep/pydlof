"""
مثال: بناء حلقة تعليمية (qaItem) جديدة كاملة من الصفر، وحفظها كملفات
.dlof مترابطة في مجلد واحد، ثم التحقق من صحتها وسلامة روابطها.

التشغيل:
    python examples/build_qa_loop.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import dlof


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "output", "qa-loop")
    os.makedirs(out_dir, exist_ok=True)

    questions = [
        ("qa-001", "ما عاصمة مصر؟", "القاهرة"),
        ("qa-002", "ما عاصمة السعودية؟", "الرياض"),
        ("qa-003", "ما عاصمة المغرب؟", "الرباط"),
    ]

    docs = []
    for doc_id, question, answer in questions:
        doc = dlof.DocumentLoop(
            id=doc_id,
            metadata=dlof.Metadata(
                title=question,
                domain=dlof.Domain.EDUCATION,
                author="مكتبة dlof",
                language="ar",
                tags=["جغرافيا", "عواصم"],
            ),
            content=[dlof.QAItem(question=question, answer=answer, difficulty="سهل")],
        )
        docs.append(doc)

    # يربط كل مستند بجاريه (previous/next) ويضبط loopRoot على الأول فقط
    for i, doc in enumerate(docs):
        filename = f"{doc.id}.dlof"
        if i == 0:
            doc.loop_links.loop_root = True
        if i > 0:
            prev_doc = docs[i - 1]
            doc.loop_links.previous = dlof.LinkRef(ref=f"{prev_doc.id}.dlof", title=prev_doc.metadata.title)
        if i < len(docs) - 1:
            next_doc = docs[i + 1]
            doc.loop_links.next = dlof.LinkRef(ref=f"{next_doc.id}.dlof", title=next_doc.metadata.title)

    for doc in docs:
        path = os.path.join(out_dir, f"{doc.id}.dlof")
        dlof.save(doc, path)
        print(f"تم الحفظ: {path}")

    print()
    print("=== التحقق من الصحة ===")
    for doc in docs:
        path = os.path.join(out_dir, f"{doc.id}.dlof")
        errors = dlof.validator.validate_file(path)
        print(f"{doc.id}: {'صالح ✔' if not errors else errors}")

    print()
    print("=== فحص سلامة روابط الحلقة ===")
    errors = dlof.validate_loop_integrity(out_dir)
    print("لا توجد أخطاء ✔" if not errors else errors)

    print()
    print("=== التجوّل عبر الحلقة كاملة ===")
    start = os.path.join(out_dir, "qa-002.dlof")  # نبدأ من المنتصف عمداً
    for node in dlof.ordered_chain(start):
        print(f" - {node.filename}: {node.document.main_content.question} -> {node.document.main_content.answer}")


if __name__ == "__main__":
    main()
