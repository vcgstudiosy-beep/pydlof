"""استثناءات مكتبة DLoF / DLoF library exceptions."""


class DlofError(Exception):
    """الخطأ الأساسي لكل أخطاء مكتبة DLoF."""


class DlofParseError(DlofError):
    """خطأ أثناء تحليل ملف .dlof أو حزمة DLoF."""


class DlofValidationError(DlofError):
    """خطأ أثناء التحقق من صحة الملف مقابل مخطط XSD."""


class DlofLinkError(DlofError):
    """خطأ متعلق بربط الحلقة (loopLinks) — ملف جار غير موجود أو حلقة مكسورة."""


class DlofPackageError(DlofError):
    """خطأ متعلق بحزم .dlofpkg / .dlofSeries / .dlofTemplate."""
