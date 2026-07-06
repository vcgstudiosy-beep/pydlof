"""
النماذج (dataclasses) التي تمثّل بنية ملف .dlof بالكامل حسب
spec/schema/dlof.xsd و spec/schema/dlof-template.xsd.

كل صنف هنا يقابل complexType واحد في المخطط الرسمي، بأسماء بايثونية
(snake_case) بينما تُحفظ أسماء XML الأصلية (camelCase) عبر التحويل
في parser.py و writer.py.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Union


# ══════════════════════════════════════════════════════════════
# التعدادات (Enums) المطابقة لأنواع XSD البسيطة
# ══════════════════════════════════════════════════════════════

class Domain(str, Enum):
    EDUCATION = "education"
    BOOK = "book"
    INFO_APP = "infoApp"
    INFO_LOOP = "infoLoop"
    SERIES = "series"
    CUSTOM = "custom"
    COMIC = "comic"
    CHARACTERS = "characters"


class AttachmentKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    FILE = "file"


class TemplateLayout(str, Enum):
    STANDARD = "standard"
    CARD = "card"
    MAGAZINE = "magazine"
    MINIMAL = "minimal"


class SyncProtocol(str, Enum):
    HTTPS = "https"
    RSS = "rss"
    SPARQL = "sparql"
    GIT = "git"
    WEBHOOK = "webhook"


class SyncPolicy(str, Enum):
    MANUAL = "manual"
    NOTIFY = "notify"
    AUTO = "auto"
    READONLY = "readonly"


class PublishProtocol(str, Enum):
    SFTP = "sftp"
    FTP = "ftp"
    GITHUB = "github"
    NETLIFY = "netlify"
    CUSTOM = "custom"


class PublishMode(str, Enum):
    MANUAL = "manual"
    ON_SAVE = "onSave"
    SCHEDULED = "scheduled"


class PublishStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class OgContentType(str, Enum):
    ARTICLE = "article"
    BOOK = "book"
    WEBSITE = "website"
    PROFILE = "profile"


class TwitterCard(str, Enum):
    SUMMARY = "summary"
    SUMMARY_LARGE_IMAGE = "summary_large_image"


# امتدادات ملفات الحلقة المقبولة كمرادفات لـ .dlof
LOOP_FILE_EXTENSIONS = (".dlof", ".ep", ".episode")

# تصنيف الامتدادات لمجلد media/
MEDIA_EXTENSION_MAP = {
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".ico", ".heic"},
    "video": {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v", ".3gp"},
    "audio": {".mp3", ".wav", ".ogg", ".aac", ".flac", ".m4a", ".wma", ".opus"},
    "subtitle": {".srt", ".vtt", ".ass", ".ssa"},
}


def guess_media_kind(filename: str) -> str:
    """يخمّن نوع الوسيط (kind) من امتداد اسم الملف."""
    import os

    ext = os.path.splitext(filename)[1].lower()
    for kind, exts in MEDIA_EXTENSION_MAP.items():
        if ext in exts:
            return kind
    return "file"


# ══════════════════════════════════════════════════════════════
# عناصر مساعدة مشتركة
# ══════════════════════════════════════════════════════════════

@dataclass
class Signature:
    algorithm: str
    value: str
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None


@dataclass
class Metadata:
    title: str
    domain: Domain = Domain.CUSTOM
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    language: str = "ar"
    tags: List[str] = field(default_factory=list)
    signature: Optional[Signature] = None


@dataclass
class LinkRef:
    ref: str
    title: Optional[str] = None


@dataclass
class LoopLinks:
    previous: Optional[LinkRef] = None
    next: Optional[LinkRef] = None
    loop_root: bool = False


@dataclass
class ContentHash:
    value: str
    algorithm: str = "sha256"


@dataclass
class RemoteSync:
    url: str
    protocol: SyncProtocol = SyncProtocol.HTTPS
    field_path: Optional[str] = None  # <field> (JSONPath/XPath)
    etag: Optional[str] = None
    content_hash: Optional[ContentHash] = None
    synced_at: Optional[datetime] = None
    headers: Optional[str] = None  # JSON مضغوط كنص
    transform: Optional[str] = None
    policy: SyncPolicy = SyncPolicy.NOTIFY
    interval_minutes: Optional[int] = None
    target_field: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# أنواع المحتوى (ContentType choice)
# ══════════════════════════════════════════════════════════════

@dataclass
class GenericItem:
    type: str = ""
    element: str = ""
    body: str = ""
    custom_type: Optional[str] = None
    # عناصر امتداد إضافية (xs:any namespace="##other") محفوظة كنص XML خام
    # حتى تستطيع معالجات مخصصة (مثل yime للشخصيات) تحليلها بنفسها.
    extra_xml: List[str] = field(default_factory=list)
    remote_sync: Optional[RemoteSync] = None

    TAG = "genericItem"


@dataclass
class QAItem:
    question: str = ""
    answer: str = ""
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    remote_sync: Optional[RemoteSync] = None

    TAG = "qaItem"


@dataclass
class BookChapter:
    chapter_title: str = ""
    text: str = ""
    chapter_number: Optional[int] = None
    summary: Optional[str] = None
    remote_sync: Optional[RemoteSync] = None

    TAG = "bookChapter"


@dataclass
class TermDefinition:
    term: str = ""
    definition: str = ""
    example: Optional[str] = None
    remote_sync: Optional[RemoteSync] = None

    TAG = "termDefinition"


@dataclass
class InfoExplain:
    topic: str = ""
    explanation: str = ""
    source: Optional[str] = None
    remote_sync: Optional[RemoteSync] = None

    TAG = "infoExplain"


@dataclass
class EpisodeItem:
    episode_title: str = ""
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    synopsis: Optional[str] = None
    duration: Optional[int] = None  # بالثواني
    series_title: Optional[str] = None
    media_ref: Optional[str] = None
    release_date: Optional[date] = None
    body: Optional[str] = None
    thumbnail_base64: Optional[str] = None
    remote_sync: Optional[RemoteSync] = None

    TAG = "episodeItem"


ContentItem = Union[GenericItem, QAItem, BookChapter, TermDefinition, InfoExplain, EpisodeItem]


# ══════════════════════════════════════════════════════════════
# المرفقات ومجلد الوسائط
# ══════════════════════════════════════════════════════════════

@dataclass
class Attachment:
    id: str
    file_name: str
    mime_type: str
    kind: AttachmentKind = AttachmentKind.FILE
    size_bytes: Optional[int] = None
    data: Optional[bytes] = None  # المحتوى الخام (بعد فك base64)
    uri: Optional[str] = None
    caption: Optional[str] = None

    @classmethod
    def from_file(cls, path: str, attachment_id: str, kind: Optional[str] = None,
                  mime_type: Optional[str] = None, caption: Optional[str] = None) -> "Attachment":
        """يبني مرفقاً من ملف على القرص، مع تضمين محتواه (base64)."""
        import mimetypes
        import os

        with open(path, "rb") as f:
            raw = f.read()
        guessed_mime, _ = mimetypes.guess_type(path)
        return cls(
            id=attachment_id,
            file_name=os.path.basename(path),
            mime_type=mime_type or guessed_mime or "application/octet-stream",
            kind=AttachmentKind(kind or guess_media_kind(path)),
            size_bytes=len(raw),
            data=raw,
            caption=caption,
        )

    def save_to(self, path: str) -> str:
        """يكتب بيانات المرفق إلى ملف على القرص. يتطلب أن يحمل المرفق `data`."""
        if self.data is None:
            raise ValueError("لا توجد بيانات مضمّنة لهذا المرفق (ربما يستخدم uri بدلاً من data)")
        with open(path, "wb") as f:
            f.write(self.data)
        return path

    @property
    def data_base64(self) -> Optional[str]:
        if self.data is None:
            return None
        return base64.b64encode(self.data).decode("ascii")


@dataclass
class MediaFile:
    path: str
    kind: AttachmentKind = AttachmentKind.FILE
    label: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# القالب (Template)
# ══════════════════════════════════════════════════════════════

@dataclass
class Template:
    ref: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    font_family: Optional[str] = None
    layout: TemplateLayout = TemplateLayout.STANDARD
    header_attachment_ref: Optional[str] = None


@dataclass
class DlofTemplatePackage:
    """يمثّل حزمة .dlofTemplate كاملة (template.xml)."""
    id: str
    name: str
    design: Template
    author: Optional[str] = None
    version: str = "1.0"


# ══════════════════════════════════════════════════════════════
# النشر على الويب (WebPublish)
# ══════════════════════════════════════════════════════════════

@dataclass
class PublishEndpoint:
    host: str
    protocol: PublishProtocol = PublishProtocol.CUSTOM
    remote_path: Optional[str] = None
    branch: Optional[str] = None
    credential_ref: Optional[str] = None
    custom_headers: Optional[str] = None


@dataclass
class Seo:
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    og_image: Optional[str] = None
    og_type: Optional[OgContentType] = None
    keywords: List[str] = field(default_factory=list)
    structured_data: Optional[str] = None
    twitter_card: Optional[TwitterCard] = None
    twitter_site: Optional[str] = None


@dataclass
class HtmlOptions:
    include_loop_nav: bool = True
    include_meta_panel: bool = True
    lang: Optional[str] = None
    dir: str = "rtl"
    inject_css: Optional[str] = None
    analytics_id: Optional[str] = None


@dataclass
class LastPublish:
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    status: Optional[PublishStatus] = None
    http_status: Optional[int] = None


@dataclass
class WebPublish:
    endpoint: PublishEndpoint
    enabled: bool = True
    output_file_name: Optional[str] = None
    publish_mode: PublishMode = PublishMode.MANUAL
    scheduled_at: Optional[datetime] = None
    seo: Optional[Seo] = None
    html_options: Optional[HtmlOptions] = None
    last_publish: Optional[LastPublish] = None


# ══════════════════════════════════════════════════════════════
# المستند الجذري: documentLoop
# ══════════════════════════════════════════════════════════════

@dataclass
class DocumentLoop:
    id: str
    metadata: Metadata
    loop_links: LoopLinks = field(default_factory=LoopLinks)
    content: List[ContentItem] = field(default_factory=list)
    version: str = "1.0"
    attachments: List[Attachment] = field(default_factory=list)
    template: Optional[Template] = None
    media_folder: List[MediaFile] = field(default_factory=list)
    web_publish: Optional[WebPublish] = None

    # -- مسار الملف الأصلي إن حُمِّل من القرص (لا يُكتب في XML) --
    source_path: Optional[str] = field(default=None, repr=False, compare=False)

    @property
    def main_content(self) -> Optional[ContentItem]:
        """أول عنصر محتوى، وهو الحالة الشائعة (عنصر محتوى واحد لكل ملف)."""
        return self.content[0] if self.content else None

    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        for att in self.attachments:
            if att.id == attachment_id:
                return att
        return None

    def display_title(self) -> str:
        return self.metadata.title
