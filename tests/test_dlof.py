"""
اختبارات وحدة لمكتبة dlof باستخدام unittest (مكتبة بايثون القياسية،
لا تتطلب تثبيت pytest).

للتشغيل:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import datetime
import os
import shutil
import tempfile
import unittest

import dlof


class TestModelsRoundTrip(unittest.TestCase):
    """يبني DocumentLoop برمجياً بكل أنواع المحتوى، يكتبه XML، يعيد قراءته،
    ويتحقق من تطابق الحقول ومن صحته مقابل XSD."""

    def _roundtrip(self, doc: dlof.DocumentLoop) -> dlof.DocumentLoop:
        xml_text = dlof.to_string(doc)
        errors = dlof.validator.validate_string(xml_text)
        self.assertEqual(errors, [], f"XML غير صالح:\n{xml_text}\nأخطاء: {errors}")
        return dlof.parse_string(xml_text)

    def test_qa_item_roundtrip(self):
        doc = dlof.DocumentLoop(
            id="test-qa-1",
            metadata=dlof.Metadata(title="سؤال تجريبي", domain=dlof.Domain.EDUCATION, tags=["رياضيات"]),
            loop_links=dlof.LoopLinks(loop_root=True, next=dlof.LinkRef(ref="qa2.dlof", title="السؤال الثاني")),
            content=[dlof.QAItem(question="كم 2+2؟", answer="4", difficulty="سهل")],
        )
        doc2 = self._roundtrip(doc)
        self.assertEqual(doc2.id, "test-qa-1")
        self.assertEqual(doc2.metadata.title, "سؤال تجريبي")
        self.assertEqual(doc2.metadata.domain, dlof.Domain.EDUCATION)
        self.assertTrue(doc2.loop_links.loop_root)
        self.assertEqual(doc2.loop_links.next.ref, "qa2.dlof")
        self.assertIsInstance(doc2.main_content, dlof.QAItem)
        self.assertEqual(doc2.main_content.answer, "4")

    def test_book_chapter_roundtrip(self):
        doc = dlof.DocumentLoop(
            id="test-book-1",
            metadata=dlof.Metadata(title="فصل تجريبي", domain=dlof.Domain.BOOK,
                                     created_at=datetime.datetime(2026, 1, 1, 10, 0, 0)),
            content=[dlof.BookChapter(chapter_number=1, chapter_title="البداية", text="نص الفصل")],
        )
        doc2 = self._roundtrip(doc)
        self.assertEqual(doc2.main_content.chapter_number, 1)
        self.assertEqual(doc2.main_content.text, "نص الفصل")
        self.assertEqual(doc2.metadata.created_at, datetime.datetime(2026, 1, 1, 10, 0, 0))

    def test_episode_item_roundtrip(self):
        doc = dlof.DocumentLoop(
            id="test-ep-1",
            metadata=dlof.Metadata(title="حلقة تجريبية", domain=dlof.Domain.SERIES),
            content=[dlof.EpisodeItem(
                episode_number=1, season_number=1, episode_title="البداية",
                duration=1200, release_date=datetime.date(2026, 1, 1),
            )],
        )
        doc2 = self._roundtrip(doc)
        item = doc2.main_content
        self.assertEqual(item.episode_number, 1)
        self.assertEqual(item.duration, 1200)
        self.assertEqual(item.release_date, datetime.date(2026, 1, 1))

    def test_attachment_roundtrip(self):
        doc = dlof.DocumentLoop(
            id="test-att-1",
            metadata=dlof.Metadata(title="مع مرفق", domain=dlof.Domain.CUSTOM),
            content=[dlof.GenericItem(type="note", element="ملاحظة", body="نص")],
            attachments=[dlof.Attachment(
                id="att1", file_name="a.txt", mime_type="text/plain",
                kind=dlof.AttachmentKind.FILE, data=b"hello world",
            )],
            template=dlof.Template(primary_color="#112233", layout=dlof.TemplateLayout.CARD),
        )
        doc2 = self._roundtrip(doc)
        att = doc2.get_attachment("att1")
        self.assertIsNotNone(att)
        self.assertEqual(att.data, b"hello world")
        self.assertEqual(doc2.template.primary_color, "#112233")
        self.assertEqual(doc2.template.layout, dlof.TemplateLayout.CARD)


class TestRealExamples(unittest.TestCase):
    """يختبر المكتبة مقابل أمثلة حقيقية من مستودع DLoF الرسمي."""

    EXAMPLES_DIR = os.environ.get(
        "DLOF_EXAMPLES_DIR",
        "/home/claude/dlof-go/dlof-go-main/spec/examples",
    )

    def setUp(self):
        if not os.path.isdir(self.EXAMPLES_DIR):
            self.skipTest("مجلد الأمثلة الرسمية غير متوفر في هذه البيئة")

    def test_all_examples_parse_and_validate(self):
        found_any = False
        for root, _dirs, files in os.walk(self.EXAMPLES_DIR):
            for name in files:
                if not name.endswith((".dlof", ".ep", ".episode")):
                    continue
                found_any = True
                path = os.path.join(root, name)
                with self.subTest(file=path):
                    doc = dlof.load(path)
                    self.assertTrue(doc.id)
                    errors = dlof.validator.validate_file(path)
                    self.assertEqual(errors, [], f"{path} غير صالح: {errors}")
        self.assertTrue(found_any, "لم يُعثر على أي ملف .dlof للاختبار")

    def test_book_loop_chain(self):
        start = os.path.join(self.EXAMPLES_DIR, "ch02.dlof")
        if not os.path.isfile(start):
            self.skipTest("ch02.dlof غير موجود")
        chain = dlof.loop.ordered_chain(start)
        names = [n.filename for n in chain]
        self.assertEqual(names, ["ch01.dlof", "ch02.dlof", "ch03.dlof"])
        self.assertTrue(chain[0].document.loop_links.loop_root)

    def test_series_walk_next(self):
        start = os.path.join(self.EXAMPLES_DIR, "MySeries", "series-index.dlof")
        if not os.path.isfile(start):
            self.skipTest("MySeries/series-index.dlof غير موجود")
        nodes = list(dlof.walk_next(start))
        names = [n.filename for n in nodes]
        self.assertEqual(names, ["series-index.dlof", "ep01.dlof", "ep02.dlof", "ep03.dlof"])

    def test_loop_integrity(self):
        folder = os.path.join(self.EXAMPLES_DIR, "MySeries")
        if not os.path.isdir(folder):
            self.skipTest("MySeries غير موجود")
        errors = dlof.validate_loop_integrity(folder)
        self.assertEqual(errors, [])

    def test_characters_roster(self):
        path = os.path.join(self.EXAMPLES_DIR, "MySeries", "characters.dlof")
        if not os.path.isfile(path):
            self.skipTest("characters.dlof غير موجود")
        doc = dlof.load(path)
        roster = dlof.characters.parse_roster_from_document(doc)
        self.assertIsNotNone(roster)
        ids = {c.id for c in roster.characters}
        self.assertEqual(ids, {"sara", "omar", "zarqa", "hasan"})
        sara = roster.get("sara")
        self.assertEqual(sara.role, "protagonist")
        self.assertTrue(any(r.target_id == "omar" for r in sara.relationships))

    def test_series_settings(self):
        path = os.path.join(self.EXAMPLES_DIR, "MySeries", "set.txt")
        if not os.path.isfile(path):
            self.skipTest("set.txt غير موجود")
        settings = dlof.settings.SeriesSettings.from_file(path)
        self.assertEqual(settings.primary_color, "#6200EE")
        self.assertTrue(settings.rtl)
        self.assertEqual(settings.characters_file, "characters.dlof")

    def test_dlofpkg_roundtrip(self):
        path = os.path.join(self.EXAMPLES_DIR, "ep01.dlofpkg")
        if not os.path.isfile(path):
            self.skipTest("ep01.dlofpkg غير موجود")
        doc, meta = dlof.packages.read_dlofpkg(path)
        self.assertEqual(meta.get("id"), "myseries-ep01")

        tmp_dir = tempfile.mkdtemp()
        try:
            out_path = os.path.join(tmp_dir, "roundtrip.dlofpkg")
            dlof.packages.create_dlofpkg(doc, out_path)
            doc2, meta2 = dlof.packages.read_dlofpkg(out_path)
            self.assertEqual(doc2.id, doc.id)
            self.assertEqual(meta2.get("title"), meta.get("title"))
        finally:
            shutil.rmtree(tmp_dir)

    def test_dlof_template_roundtrip(self):
        path = os.path.join(self.EXAMPLES_DIR, "templates", "sunset-card.dlofTemplate")
        if not os.path.isfile(path):
            self.skipTest("sunset-card.dlofTemplate غير موجود")
        pkg = dlof.packages.read_dlof_template(path)
        self.assertEqual(pkg.id, "sunset-card")
        self.assertEqual(pkg.design.primary_color, "#D32F2F")

        tmp_dir = tempfile.mkdtemp()
        try:
            out_path = os.path.join(tmp_dir, "test.dlofTemplate")
            dlof.packages.create_dlof_template(pkg, out_path)
            pkg2 = dlof.packages.read_dlof_template(out_path)
            self.assertEqual(pkg2.design.primary_color, pkg.design.primary_color)
        finally:
            shutil.rmtree(tmp_dir)

    def test_html_export_with_template_resolution(self):
        doc_path = os.path.join(self.EXAMPLES_DIR, "book-cover-with-template.dlof")
        templates_dir = os.path.join(self.EXAMPLES_DIR, "templates")
        if not (os.path.isfile(doc_path) and os.path.isdir(templates_dir)):
            self.skipTest("ملفات القالب التجريبية غير متوفرة")
        doc = dlof.load(doc_path)
        library = dlof.packages.load_template_library(templates_dir)
        html = dlof.html_export.render_html(doc, template_library=library)
        self.assertIn("D32F2F", html)


class TestSettingsParsing(unittest.TestCase):
    def test_hex_colors_not_truncated_by_comment_stripping(self):
        text = "theme.primaryColor=#6200EE\nfonts.title=   # فارغ افتراضياً\n"
        parsed = dlof.settings.parse_set_txt(text)
        self.assertEqual(parsed["theme.primaryColor"], "#6200EE")
        self.assertEqual(parsed["fonts.title"], "")


class TestLinkResolution(unittest.TestCase):
    def test_resolve_ref_extension_synonyms(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            open(os.path.join(tmp_dir, "ep02.ep"), "w").close()
            resolved = dlof.resolve_ref(tmp_dir, "ep02.dlof")
            self.assertEqual(resolved, os.path.join(tmp_dir, "ep02.ep"))
        finally:
            shutil.rmtree(tmp_dir)

    def test_resolve_ref_missing_returns_none(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            self.assertIsNone(dlof.resolve_ref(tmp_dir, "missing.dlof"))
        finally:
            shutil.rmtree(tmp_dir)


if __name__ == "__main__":
    unittest.main()
