"""
كتابة نماذج بايثون (dlof.models.DocumentLoop) إلى ملفات/نصوص .dlof (XML)
مطابقة لمخطط spec/schema/dlof.xsd.
"""

from __future__ import annotations

import base64
from typing import Optional

from lxml import etree

from . import models as m
from ._xmlutil import NSMAP, q, sub, sub_if


def to_element(doc: m.DocumentLoop) -> etree._Element:
    root = etree.Element(q("documentLoop"), nsmap=NSMAP)
    root.set("version", doc.version)
    root.set("id", doc.id)

    root.append(_metadata_to_el(doc.metadata))
    root.append(_loop_links_to_el(doc.loop_links))
    root.append(_content_to_el(doc.content))

    if doc.attachments:
        root.append(_attachments_to_el(doc.attachments))
    if doc.template is not None:
        root.append(_template_to_el(doc.template))
    if doc.media_folder:
        root.append(_media_folder_to_el(doc.media_folder))
    if doc.web_publish is not None:
        root.append(_web_publish_to_el(doc.web_publish))

    return root


def to_string(doc: m.DocumentLoop, pretty: bool = True) -> str:
    root = to_element(doc)
    xml_bytes = etree.tostring(
        root, pretty_print=pretty, xml_declaration=True, encoding="UTF-8"
    )
    return xml_bytes.decode("utf-8")


def write_file(doc: m.DocumentLoop, path: str, pretty: bool = True) -> str:
    xml_text = to_string(doc, pretty=pretty)
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml_text)
    return path


# ── metadata ──────────────────────────────────────────────────

def _metadata_to_el(md: m.Metadata) -> etree._Element:
    el = etree.Element(q("metadata"))
    sub(el, "title", md.title)
    sub(el, "domain", md.domain.value if isinstance(md.domain, m.Domain) else str(md.domain))
    sub_if(el, "author", md.author)
    sub_if(el, "createdAt", md.created_at)
    sub_if(el, "updatedAt", md.updated_at)
    sub(el, "language", md.language or "ar")
    if md.tags:
        tags_el = sub(el, "tags")
        for tag in md.tags:
            sub(tags_el, "tag", tag)
    if md.signature is not None:
        sig_el = etree.SubElement(el, q("signature"))
        sig_el.set("algorithm", md.signature.algorithm)
        sig_el.set("value", md.signature.value)
        if md.signature.signed_by:
            sig_el.set("signedBy", md.signature.signed_by)
        if md.signature.signed_at:
            sig_el.set("signedAt", md.signature.signed_at.isoformat())
    return el


# ── loopLinks ─────────────────────────────────────────────────

def _loop_links_to_el(links: m.LoopLinks) -> etree._Element:
    el = etree.Element(q("loopLinks"))
    if links.previous is not None:
        prev_el = etree.SubElement(el, q("previous"))
        prev_el.set("ref", links.previous.ref)
        if links.previous.title:
            prev_el.set("title", links.previous.title)
    if links.next is not None:
        next_el = etree.SubElement(el, q("next"))
        next_el.set("ref", links.next.ref)
        if links.next.title:
            next_el.set("title", links.next.title)
    sub(el, "loopRoot", "true" if links.loop_root else "false")
    return el


# ── content ───────────────────────────────────────────────────

def _content_to_el(items) -> etree._Element:
    el = etree.Element(q("content"))
    for item in items:
        el.append(_content_item_to_el(item))
    return el


def _remote_sync_to_el(rs: Optional[m.RemoteSync]) -> Optional[etree._Element]:
    if rs is None:
        return None
    el = etree.Element(q("remoteSync"))
    el.set("policy", rs.policy.value if isinstance(rs.policy, m.SyncPolicy) else str(rs.policy))
    if rs.interval_minutes is not None:
        el.set("intervalMinutes", str(rs.interval_minutes))
    if rs.target_field:
        el.set("targetField", rs.target_field)
    sub(el, "url", rs.url)
    sub(el, "protocol", rs.protocol.value if isinstance(rs.protocol, m.SyncProtocol) else str(rs.protocol))
    sub_if(el, "field", rs.field_path)
    sub_if(el, "etag", rs.etag)
    if rs.content_hash is not None:
        hash_el = etree.SubElement(el, q("contentHash"))
        hash_el.set("algorithm", rs.content_hash.algorithm)
        hash_el.set("value", rs.content_hash.value)
    sub_if(el, "syncedAt", rs.synced_at)
    sub_if(el, "headers", rs.headers)
    sub_if(el, "transform", rs.transform)
    return el


def _content_item_to_el(item: m.ContentItem) -> etree._Element:
    if isinstance(item, m.GenericItem):
        el = etree.Element(q("genericItem"))
        if item.custom_type:
            el.set("customType", item.custom_type)
        sub(el, "type", item.type)
        sub(el, "element", item.element)
        sub(el, "body", item.body)
        for raw_xml in item.extra_xml:
            el.append(etree.fromstring(raw_xml.encode("utf-8") if isinstance(raw_xml, str) else raw_xml))
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    if isinstance(item, m.QAItem):
        el = etree.Element(q("qaItem"))
        sub(el, "question", item.question)
        sub(el, "answer", item.answer)
        sub_if(el, "explanation", item.explanation)
        sub_if(el, "difficulty", item.difficulty)
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    if isinstance(item, m.BookChapter):
        el = etree.Element(q("bookChapter"))
        sub_if(el, "chapterNumber", item.chapter_number)
        sub(el, "chapterTitle", item.chapter_title)
        sub(el, "text", item.text)
        sub_if(el, "summary", item.summary)
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    if isinstance(item, m.TermDefinition):
        el = etree.Element(q("termDefinition"))
        sub(el, "term", item.term)
        sub(el, "definition", item.definition)
        sub_if(el, "example", item.example)
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    if isinstance(item, m.InfoExplain):
        el = etree.Element(q("infoExplain"))
        sub(el, "topic", item.topic)
        sub(el, "explanation", item.explanation)
        sub_if(el, "source", item.source)
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    if isinstance(item, m.EpisodeItem):
        el = etree.Element(q("episodeItem"))
        sub_if(el, "episodeNumber", item.episode_number)
        sub_if(el, "seasonNumber", item.season_number)
        sub(el, "episodeTitle", item.episode_title)
        sub_if(el, "synopsis", item.synopsis)
        sub_if(el, "duration", item.duration)
        sub_if(el, "seriesTitle", item.series_title)
        sub_if(el, "mediaRef", item.media_ref)
        sub_if(el, "releaseDate", item.release_date)
        sub_if(el, "body", item.body)
        sub_if(el, "thumbnailBase64", item.thumbnail_base64)
        rs_el = _remote_sync_to_el(item.remote_sync)
        if rs_el is not None:
            el.append(rs_el)
        return el

    raise TypeError(f"نوع محتوى غير مدعوم: {type(item)}")


# ── attachments ───────────────────────────────────────────────

def _attachments_to_el(attachments) -> etree._Element:
    el = etree.Element(q("attachments"))
    for att in attachments:
        att_el = etree.SubElement(el, q("attachment"))
        att_el.set("id", att.id)
        att_el.set("fileName", att.file_name)
        att_el.set("mimeType", att.mime_type)
        att_el.set("kind", att.kind.value if isinstance(att.kind, m.AttachmentKind) else str(att.kind))
        if att.size_bytes is not None:
            att_el.set("sizeBytes", str(att.size_bytes))
        if att.data is not None:
            sub(att_el, "data", base64.b64encode(att.data).decode("ascii"))
        elif att.uri:
            sub(att_el, "uri", att.uri)
        sub_if(att_el, "caption", att.caption)
    return el


# ── template ──────────────────────────────────────────────────

def _template_to_el(t: m.Template) -> etree._Element:
    el = etree.Element(q("template"))
    if t.ref:
        el.set("ref", t.ref)
    if t.primary_color:
        el.set("primaryColor", t.primary_color)
    if t.secondary_color:
        el.set("secondaryColor", t.secondary_color)
    if t.background_color:
        el.set("backgroundColor", t.background_color)
    if t.text_color:
        el.set("textColor", t.text_color)
    if t.font_family:
        el.set("fontFamily", t.font_family)
    el.set("layout", t.layout.value if isinstance(t.layout, m.TemplateLayout) else str(t.layout))
    if t.header_attachment_ref:
        el.set("headerAttachmentRef", t.header_attachment_ref)
    return el


# ── mediaFolder ───────────────────────────────────────────────

def _media_folder_to_el(files) -> etree._Element:
    el = etree.Element(q("mediaFolder"))
    for mf in files:
        mf_el = etree.SubElement(el, q("mediaFile"))
        mf_el.set("path", mf.path)
        mf_el.set("kind", mf.kind.value if isinstance(mf.kind, m.AttachmentKind) else str(mf.kind))
        if mf.label:
            mf_el.set("label", mf.label)
    return el


# ── webPublish ────────────────────────────────────────────────

def _web_publish_to_el(wp: m.WebPublish) -> etree._Element:
    el = etree.Element(q("webPublish"))
    el.set("enabled", "true" if wp.enabled else "false")
    if wp.output_file_name:
        el.set("outputFileName", wp.output_file_name)
    el.set("publishMode", wp.publish_mode.value if isinstance(wp.publish_mode, m.PublishMode) else str(wp.publish_mode))
    if wp.scheduled_at:
        el.set("scheduledAt", wp.scheduled_at.isoformat())

    ep_el = etree.SubElement(el, q("endpoint"))
    sub(ep_el, "host", wp.endpoint.host)
    sub(ep_el, "protocol", wp.endpoint.protocol.value if isinstance(wp.endpoint.protocol, m.PublishProtocol) else str(wp.endpoint.protocol))
    sub_if(ep_el, "remotePath", wp.endpoint.remote_path)
    sub_if(ep_el, "branch", wp.endpoint.branch)
    sub_if(ep_el, "credentialRef", wp.endpoint.credential_ref)
    sub_if(ep_el, "customHeaders", wp.endpoint.custom_headers)

    if wp.seo is not None:
        seo_el = etree.SubElement(el, q("seo"))
        sub_if(seo_el, "metaDescription", wp.seo.meta_description)
        sub_if(seo_el, "canonicalUrl", wp.seo.canonical_url)
        sub_if(seo_el, "ogImage", wp.seo.og_image)
        if wp.seo.og_type:
            sub(seo_el, "ogType", wp.seo.og_type.value)
        if wp.seo.keywords:
            kw_el = etree.SubElement(seo_el, q("keywords"))
            for kw in wp.seo.keywords:
                sub(kw_el, "keyword", kw)
        sub_if(seo_el, "structuredData", wp.seo.structured_data)
        if wp.seo.twitter_card:
            sub(seo_el, "twitterCard", wp.seo.twitter_card.value)
        sub_if(seo_el, "twitterSite", wp.seo.twitter_site)

    if wp.html_options is not None:
        ho = wp.html_options
        ho_el = etree.SubElement(el, q("htmlOptions"))
        ho_el.set("includeLoopNav", "true" if ho.include_loop_nav else "false")
        ho_el.set("includeMetaPanel", "true" if ho.include_meta_panel else "false")
        if ho.lang:
            ho_el.set("lang", ho.lang)
        ho_el.set("dir", ho.dir)
        if ho.inject_css:
            ho_el.set("injectCss", ho.inject_css)
        if ho.analytics_id:
            ho_el.set("analyticsId", ho.analytics_id)

    if wp.last_publish is not None:
        lp = wp.last_publish
        lp_el = etree.SubElement(el, q("lastPublish"))
        if lp.published_at:
            lp_el.set("publishedAt", lp.published_at.isoformat())
        if lp.published_url:
            lp_el.set("publishedUrl", lp.published_url)
        if lp.status:
            lp_el.set("status", lp.status.value)
        if lp.http_status is not None:
            lp_el.set("httpStatus", str(lp.http_status))

    return el
