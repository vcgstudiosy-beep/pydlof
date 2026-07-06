"""
تحليل ملفات .dlof (XML) إلى نماذج بايثون (dlof.models.DocumentLoop).
"""

from __future__ import annotations

import base64
import os
from typing import Optional

from lxml import etree

from . import models as m
from ._xmlutil import (
    NS,
    find_bool,
    find_date,
    find_datetime,
    find_int,
    find_text,
    q,
)
from .exceptions import DlofParseError


def parse_file(path: str) -> m.DocumentLoop:
    """يقرأ ملف .dlof / .ep / .episode من القرص ويحلّله."""
    try:
        tree = etree.parse(path)
    except etree.XMLSyntaxError as exc:
        raise DlofParseError(f"فشل تحليل XML للملف {path}: {exc}") from exc
    doc = parse_element(tree.getroot())
    doc.source_path = os.path.abspath(path)
    return doc


def parse_string(xml_text: str) -> m.DocumentLoop:
    """يحلّل نص XML مباشرة إلى DocumentLoop."""
    try:
        root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    except etree.XMLSyntaxError as exc:
        raise DlofParseError(f"فشل تحليل نص XML: {exc}") from exc
    return parse_element(root)


def parse_element(root: etree._Element) -> m.DocumentLoop:
    if root.tag != q("documentLoop"):
        raise DlofParseError(
            f"العنصر الجذر يجب أن يكون <documentLoop>، وُجد بدلاً منه: {root.tag}"
        )

    doc_id = root.get("id")
    version = root.get("version", "1.0")
    if not doc_id:
        raise DlofParseError("العنصر الجذر <documentLoop> يفتقد الصفة الإلزامية 'id'")

    metadata_el = root.find(q("metadata"))
    if metadata_el is None:
        raise DlofParseError("عنصر <metadata> إلزامي وغير موجود")
    metadata = _parse_metadata(metadata_el)

    links_el = root.find(q("loopLinks"))
    loop_links = _parse_loop_links(links_el) if links_el is not None else m.LoopLinks()

    content_el = root.find(q("content"))
    content_items = _parse_content(content_el) if content_el is not None else []

    attachments_el = root.find(q("attachments"))
    attachments = _parse_attachments(attachments_el) if attachments_el is not None else []

    template_el = root.find(q("template"))
    template = _parse_template(template_el) if template_el is not None else None

    media_el = root.find(q("mediaFolder"))
    media_files = _parse_media_folder(media_el) if media_el is not None else []

    webpub_el = root.find(q("webPublish"))
    web_publish = _parse_web_publish(webpub_el) if webpub_el is not None else None

    return m.DocumentLoop(
        id=doc_id,
        version=version,
        metadata=metadata,
        loop_links=loop_links,
        content=content_items,
        attachments=attachments,
        template=template,
        media_folder=media_files,
        web_publish=web_publish,
    )


# ── metadata ──────────────────────────────────────────────────

def _parse_metadata(el: etree._Element) -> m.Metadata:
    domain_text = find_text(el, "domain") or "custom"
    try:
        domain = m.Domain(domain_text)
    except ValueError:
        domain = m.Domain.CUSTOM

    tags_el = el.find(q("tags"))
    tags = []
    if tags_el is not None:
        tags = [t.text or "" for t in tags_el.findall(q("tag"))]

    sig = None
    sig_el = el.find(q("signature"))
    if sig_el is not None:
        sig = m.Signature(
            algorithm=sig_el.get("algorithm", ""),
            value=sig_el.get("value", ""),
            signed_by=sig_el.get("signedBy"),
            signed_at=_parse_dt_attr(sig_el.get("signedAt")),
        )

    return m.Metadata(
        title=find_text(el, "title") or "",
        domain=domain,
        author=find_text(el, "author"),
        created_at=find_datetime(el, "createdAt"),
        updated_at=find_datetime(el, "updatedAt"),
        language=find_text(el, "language") or "ar",
        tags=tags,
        signature=sig,
    )


def _parse_dt_attr(value: Optional[str]):
    if not value:
        return None
    from ._xmlutil import parse_datetime

    return parse_datetime(value)


# ── loopLinks ─────────────────────────────────────────────────

def _parse_loop_links(el: etree._Element) -> m.LoopLinks:
    def _link(tag: str) -> Optional[m.LinkRef]:
        sub_el = el.find(q(tag))
        if sub_el is None:
            return None
        return m.LinkRef(ref=sub_el.get("ref", ""), title=sub_el.get("title"))

    return m.LoopLinks(
        previous=_link("previous"),
        next=_link("next"),
        loop_root=find_bool(el, "loopRoot", default=False),
    )


# ── content ───────────────────────────────────────────────────

_CONTENT_TAGS = {
    "genericItem": "_parse_generic_item",
    "qaItem": "_parse_qa_item",
    "bookChapter": "_parse_book_chapter",
    "termDefinition": "_parse_term_definition",
    "infoExplain": "_parse_info_explain",
    "episodeItem": "_parse_episode_item",
}


def _parse_content(el: etree._Element) -> list:
    items = []
    for child in el:
        if not isinstance(child.tag, str):
            continue  # يتجاهل التعليقات (Comment) وتعليمات المعالجة (PI)
        local = etree.QName(child).localname
        handler_name = _CONTENT_TAGS.get(local)
        if handler_name is None:
            continue
        handler = globals()[handler_name]
        items.append(handler(child))
    return items


def _parse_remote_sync(el: etree._Element) -> Optional[m.RemoteSync]:
    rs_el = el.find(q("remoteSync"))
    if rs_el is None:
        return None
    hash_el = rs_el.find(q("contentHash"))
    content_hash = None
    if hash_el is not None:
        content_hash = m.ContentHash(
            value=hash_el.get("value", ""),
            algorithm=hash_el.get("algorithm", "sha256"),
        )
    protocol_text = find_text(rs_el, "protocol") or "https"
    policy_text = rs_el.get("policy", "notify")
    interval = rs_el.get("intervalMinutes")
    return m.RemoteSync(
        url=find_text(rs_el, "url") or "",
        protocol=m.SyncProtocol(protocol_text),
        field_path=find_text(rs_el, "field"),
        etag=find_text(rs_el, "etag"),
        content_hash=content_hash,
        synced_at=find_datetime(rs_el, "syncedAt"),
        headers=find_text(rs_el, "headers"),
        transform=find_text(rs_el, "transform"),
        policy=m.SyncPolicy(policy_text),
        interval_minutes=int(interval) if interval is not None else None,
        target_field=rs_el.get("targetField"),
    )


def _parse_generic_item(el: etree._Element) -> m.GenericItem:
    known = {q("type"), q("element"), q("body"), q("remoteSync")}
    extra_xml = []
    for child in el:
        if not isinstance(child.tag, str):
            continue  # يتجاهل التعليقات (Comment) وتعليمات المعالجة (PI)
        if child.tag not in known:
            extra_xml.append(etree.tostring(child, encoding="unicode"))
    return m.GenericItem(
        type=find_text(el, "type") or "",
        element=find_text(el, "element") or "",
        body=find_text(el, "body") or "",
        custom_type=el.get("customType"),
        extra_xml=extra_xml,
        remote_sync=_parse_remote_sync(el),
    )


def _parse_qa_item(el: etree._Element) -> m.QAItem:
    return m.QAItem(
        question=find_text(el, "question") or "",
        answer=find_text(el, "answer") or "",
        explanation=find_text(el, "explanation"),
        difficulty=find_text(el, "difficulty"),
        remote_sync=_parse_remote_sync(el),
    )


def _parse_book_chapter(el: etree._Element) -> m.BookChapter:
    return m.BookChapter(
        chapter_title=find_text(el, "chapterTitle") or "",
        text=find_text(el, "text") or "",
        chapter_number=find_int(el, "chapterNumber"),
        summary=find_text(el, "summary"),
        remote_sync=_parse_remote_sync(el),
    )


def _parse_term_definition(el: etree._Element) -> m.TermDefinition:
    return m.TermDefinition(
        term=find_text(el, "term") or "",
        definition=find_text(el, "definition") or "",
        example=find_text(el, "example"),
        remote_sync=_parse_remote_sync(el),
    )


def _parse_info_explain(el: etree._Element) -> m.InfoExplain:
    return m.InfoExplain(
        topic=find_text(el, "topic") or "",
        explanation=find_text(el, "explanation") or "",
        source=find_text(el, "source"),
        remote_sync=_parse_remote_sync(el),
    )


def _parse_episode_item(el: etree._Element) -> m.EpisodeItem:
    return m.EpisodeItem(
        episode_title=find_text(el, "episodeTitle") or "",
        episode_number=find_int(el, "episodeNumber"),
        season_number=find_int(el, "seasonNumber"),
        synopsis=find_text(el, "synopsis"),
        duration=find_int(el, "duration"),
        series_title=find_text(el, "seriesTitle"),
        media_ref=find_text(el, "mediaRef"),
        release_date=find_date(el, "releaseDate"),
        body=find_text(el, "body"),
        thumbnail_base64=find_text(el, "thumbnailBase64"),
        remote_sync=_parse_remote_sync(el),
    )


# ── attachments ───────────────────────────────────────────────

def _parse_attachments(el: etree._Element) -> list:
    result = []
    for att_el in el.findall(q("attachment")):
        data_el = att_el.find(q("data"))
        data = None
        if data_el is not None and data_el.text:
            data = base64.b64decode(data_el.text.strip())
        size_text = att_el.get("sizeBytes")
        kind_text = att_el.get("kind", "file")
        result.append(
            m.Attachment(
                id=att_el.get("id", ""),
                file_name=att_el.get("fileName", ""),
                mime_type=att_el.get("mimeType", "application/octet-stream"),
                kind=m.AttachmentKind(kind_text),
                size_bytes=int(size_text) if size_text is not None else None,
                data=data,
                uri=find_text(att_el, "uri"),
                caption=find_text(att_el, "caption"),
            )
        )
    return result


# ── template ──────────────────────────────────────────────────

def _parse_template(el: etree._Element) -> m.Template:
    layout_text = el.get("layout", "standard")
    try:
        layout = m.TemplateLayout(layout_text)
    except ValueError:
        layout = m.TemplateLayout.STANDARD
    return m.Template(
        ref=el.get("ref"),
        primary_color=el.get("primaryColor"),
        secondary_color=el.get("secondaryColor"),
        background_color=el.get("backgroundColor"),
        text_color=el.get("textColor"),
        font_family=el.get("fontFamily"),
        layout=layout,
        header_attachment_ref=el.get("headerAttachmentRef"),
    )


# ── mediaFolder ───────────────────────────────────────────────

def _parse_media_folder(el: etree._Element) -> list:
    result = []
    for mf_el in el.findall(q("mediaFile")):
        result.append(
            m.MediaFile(
                path=mf_el.get("path", ""),
                kind=m.AttachmentKind(mf_el.get("kind", "file")),
                label=mf_el.get("label"),
            )
        )
    return result


# ── webPublish ────────────────────────────────────────────────

def _parse_web_publish(el: etree._Element) -> m.WebPublish:
    endpoint_el = el.find(q("endpoint"))
    endpoint = m.PublishEndpoint(host="", protocol=m.PublishProtocol.CUSTOM)
    if endpoint_el is not None:
        endpoint = m.PublishEndpoint(
            host=find_text(endpoint_el, "host") or "",
            protocol=m.PublishProtocol(find_text(endpoint_el, "protocol") or "custom"),
            remote_path=find_text(endpoint_el, "remotePath"),
            branch=find_text(endpoint_el, "branch"),
            credential_ref=find_text(endpoint_el, "credentialRef"),
            custom_headers=find_text(endpoint_el, "customHeaders"),
        )

    seo = None
    seo_el = el.find(q("seo"))
    if seo_el is not None:
        kw_el = seo_el.find(q("keywords"))
        keywords = [k.text or "" for k in kw_el.findall(q("keyword"))] if kw_el is not None else []
        og_type_text = find_text(seo_el, "ogType")
        tw_card_text = find_text(seo_el, "twitterCard")
        seo = m.Seo(
            meta_description=find_text(seo_el, "metaDescription"),
            canonical_url=find_text(seo_el, "canonicalUrl"),
            og_image=find_text(seo_el, "ogImage"),
            og_type=m.OgContentType(og_type_text) if og_type_text else None,
            keywords=keywords,
            structured_data=find_text(seo_el, "structuredData"),
            twitter_card=m.TwitterCard(tw_card_text) if tw_card_text else None,
            twitter_site=find_text(seo_el, "twitterSite"),
        )

    html_options = None
    ho_el = el.find(q("htmlOptions"))
    if ho_el is not None:
        html_options = m.HtmlOptions(
            include_loop_nav=(ho_el.get("includeLoopNav", "true") == "true"),
            include_meta_panel=(ho_el.get("includeMetaPanel", "true") == "true"),
            lang=ho_el.get("lang"),
            dir=ho_el.get("dir", "rtl"),
            inject_css=ho_el.get("injectCss"),
            analytics_id=ho_el.get("analyticsId"),
        )

    last_publish = None
    lp_el = el.find(q("lastPublish"))
    if lp_el is not None:
        status_text = lp_el.get("status")
        http_status = lp_el.get("httpStatus")
        last_publish = m.LastPublish(
            published_at=_parse_dt_attr(lp_el.get("publishedAt")),
            published_url=lp_el.get("publishedUrl"),
            status=m.PublishStatus(status_text) if status_text else None,
            http_status=int(http_status) if http_status is not None else None,
        )

    scheduled_text = el.get("scheduledAt")
    return m.WebPublish(
        endpoint=endpoint,
        enabled=(el.get("enabled", "true") == "true"),
        output_file_name=el.get("outputFileName"),
        publish_mode=m.PublishMode(el.get("publishMode", "manual")),
        scheduled_at=_parse_dt_attr(scheduled_text),
        seo=seo,
        html_options=html_options,
        last_publish=last_publish,
    )
