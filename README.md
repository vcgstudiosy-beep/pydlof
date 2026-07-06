# dlof — مكتبة بايثون لصيغة DLoF

مكتبة بايثون كاملة لصيغة **DLoF (Document Loop Format)**: صيغة XML مفتوحة
لتخزين وربط المستندات في "حلقات" ذاتية الترابط (كل ملف يحمل بداخله إشارة
إلى الملف **التالي** و**السابق**، دون فهرس مركزي).

مبنية بالكامل ومطابقة لمخطط `dlof.xsd` الرسمي (v1.0 + remoteSync + webPublish)
ولمخطط `dlof-template.xsd`، وتم اختبارها والتحقق من صحتها مقابل كل أمثلة
مستودع DLoF الرسمي.

## المزايا

- **قراءة/كتابة** كاملة لملفات `.dlof` (كل أنواع المحتوى: `genericItem`,
  `qaItem`, `bookChapter`, `termDefinition`, `infoExplain`, `episodeItem`)
  مع المرفقات (`attachments`)، القالب (`template`)، مجلد الوسائط
  (`mediaFolder`)، المزامنة الحيّة (`remoteSync`)، والنشر على الويب
  (`webPublish` بكل حقول SEO/OpenGraph).
- **التحقق من الصحة (validation)** مقابل مخطط XSD الرسمي عبر `lxml`.
- **التجوّل في الحلقة** (loop traversal): تتبّع `next`/`previous` عبر ملفات
  متعددة، بناء تسلسل كامل بدءاً من أي نقطة، اكتشاف الحلقات المغلقة، وفحص
  سلامة الروابط (اكتشاف الروابط المعلّقة).
- **حزم DLoF**: قراءة وكتابة `.dlofpkg` (ملف مفرد + مرفقات)، `.dlofSeries`
  (سلسلة كاملة)، و`.dlofTemplate` (حزمة قالب تصميم، مع توليد `Template.kt`
  مرجعي تلقائياً).
- **امتداد الشخصيات (Yime)**: تحليل/بناء `characters.dlof` وقوائم الشخصيات
  والعلاقات بينها.
- **إعدادات السلسلة**: تحليل وكتابة `set.txt` (مفتاح=قيمة) بواجهة مكتوبة
  النوع (`SeriesSettings`).
- **تصدير HTML**: توليد صفحة ويب مستقلة من أي مستند `.dlof`، تستخدم القالب
  المرفق (أو المُسترد من مكتبة قوالب) وبيانات SEO/OpenGraph إن وُجدت.
- **واجهة سطر أوامر**: `dlof validate|info|chain|tohtml|check-loop`.

## التثبيت

```bash
pip install -e .
```

يتطلب Python 3.9+ و `lxml`.

## البدء السريع

```python
import dlof

# قراءة ملف .dlof
doc = dlof.load("ch01.dlof")
print(doc.metadata.title)
print(doc.main_content.text)          # bookChapter.text مثلاً

# التحقق من الصحة مقابل XSD الرسمي
errors = dlof.validator.validate_file("ch01.dlof")
assert not errors

# التجوّل عبر الحلقة كاملة بدءاً من أي نقطة فيها
for node in dlof.ordered_chain("ch02.dlof"):
    print(node.filename, "->", node.document.metadata.title)

# بناء مستند جديد وحفظه
new_doc = dlof.DocumentLoop(
    id="qa-001",
    metadata=dlof.Metadata(title="سؤال: ما عاصمة مصر؟", domain=dlof.Domain.EDUCATION),
    loop_links=dlof.LoopLinks(loop_root=True),
    content=[dlof.QAItem(question="ما عاصمة مصر؟", answer="القاهرة")],
)
dlof.save(new_doc, "qa-001.dlof")

# تصدير HTML
dlof.html_export.write_html(doc, "ch01.html")
```

راجع [`examples/build_qa_loop.py`](examples/build_qa_loop.py) لمثال كامل
لبناء حلقة تعليمية من عدة ملفات مترابطة من الصفر.

## واجهة سطر الأوامر

```bash
python -m dlof validate path/to/file.dlof
python -m dlof info path/to/file.dlof
python -m dlof chain path/to/file.dlof        # يعرض الحلقة كاملة
python -m dlof tohtml path/to/file.dlof -o out.html
python -m dlof check-loop path/to/folder      # يفحص كل الروابط ضمن مجلد
```

## بنية المكتبة

| الوحدة | الوصف |
|---|---|
| `dlof.models` | Dataclasses تمثّل كل بنية DLoF (DocumentLoop, Metadata, LoopLinks, أنواع المحتوى، Attachment، Template، WebPublish...) |
| `dlof.parser` | تحليل XML → نماذج (`parse_file`, `parse_string`) |
| `dlof.writer` | نماذج → XML (`to_string`, `write_file`) |
| `dlof.validator` | التحقق من الصحة مقابل XSD الرسمي |
| `dlof.loop` | التجوّل في الحلقة (`walk_next`, `walk_previous`, `ordered_chain`, `validate_loop_integrity`) |
| `dlof.packages` | `.dlofpkg` / `.dlofSeries` / `.dlofTemplate` + حلّ `template ref` |
| `dlof.settings` | تحليل/كتابة `set.txt` |
| `dlof.characters` | امتداد الشخصيات (Yime) |
| `dlof.html_export` | تصدير HTML |
| `dlof.cli` | واجهة سطر الأوامر |

## الاختبارات

```bash
DLOF_EXAMPLES_DIR=/path/to/dlof-repo/spec/examples \
    python -m unittest discover -s tests -v
```

تتحقق الاختبارات من كل أمثلة المستودع الرسمي (`spec/examples/`) — تحليل،
تحقق من الصحة، إعادة الكتابة (round-trip)، التجوّل في الحلقات، الشخصيات،
الحزم، والقوالب.

## الترخيص

MIT.
