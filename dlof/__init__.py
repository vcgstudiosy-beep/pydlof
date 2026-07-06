"""
dlof — مكتبة بايثون كاملة لصيغة DLoF (Document Loop Format).

مثال سريع:

    import dlof

    doc = dlof.load("ch01.dlof")
    print(doc.metadata.title)
    print(doc.main_content.text)          # bookChapter.text مثلاً

    for node in dlof.walk_next("ch01.dlof"):
        print(node.filename, node.document.metadata.title)

    dlof.validate.assert_valid("ch01.dlof")
"""

from . import characters, html_export, loop, packages, settings, validator
from .exceptions import (
    DlofError,
    DlofLinkError,
    DlofPackageError,
    DlofParseError,
    DlofValidationError,
)
from .loop import (
    LoopNode,
    find_loop_root,
    load_folder,
    ordered_chain,
    resolve_ref,
    validate_loop_integrity,
    walk_next,
    walk_previous,
)
from .models import (
    Attachment,
    AttachmentKind,
    BookChapter,
    ContentHash,
    Domain,
    DocumentLoop,
    DlofTemplatePackage,
    EpisodeItem,
    GenericItem,
    HtmlOptions,
    InfoExplain,
    LastPublish,
    LinkRef,
    LoopLinks,
    MediaFile,
    Metadata,
    OgContentType,
    PublishEndpoint,
    PublishMode,
    PublishProtocol,
    PublishStatus,
    QAItem,
    RemoteSync,
    Seo,
    Signature,
    SyncPolicy,
    SyncProtocol,
    Template,
    TemplateLayout,
    TermDefinition,
    TwitterCard,
    WebPublish,
    guess_media_kind,
)
from .parser import parse_file, parse_file as load, parse_string
from .writer import to_element, to_string, write_file as save

__version__ = "1.0.0"

__all__ = [
    # وحدات فرعية
    "characters",
    "html_export",
    "loop",
    "packages",
    "settings",
    "validator",
    # استثناءات
    "DlofError",
    "DlofLinkError",
    "DlofPackageError",
    "DlofParseError",
    "DlofValidationError",
    # تجوّل الحلقة
    "LoopNode",
    "find_loop_root",
    "load_folder",
    "ordered_chain",
    "resolve_ref",
    "validate_loop_integrity",
    "walk_next",
    "walk_previous",
    # نماذج
    "Attachment",
    "AttachmentKind",
    "BookChapter",
    "ContentHash",
    "Domain",
    "DocumentLoop",
    "DlofTemplatePackage",
    "EpisodeItem",
    "GenericItem",
    "HtmlOptions",
    "InfoExplain",
    "LastPublish",
    "LinkRef",
    "LoopLinks",
    "MediaFile",
    "Metadata",
    "OgContentType",
    "PublishEndpoint",
    "PublishMode",
    "PublishProtocol",
    "PublishStatus",
    "QAItem",
    "RemoteSync",
    "Seo",
    "Signature",
    "SyncPolicy",
    "SyncProtocol",
    "Template",
    "TemplateLayout",
    "TermDefinition",
    "TwitterCard",
    "WebPublish",
    "guess_media_kind",
    # تحليل/كتابة سريعة
    "parse_file",
    "parse_string",
    "load",
    "to_element",
    "to_string",
    "save",
]
