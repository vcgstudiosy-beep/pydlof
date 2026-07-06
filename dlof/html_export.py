"""
توليد صفحة HTML مستقلة من DocumentLoop واحد — يستخدم <template> للتصميم
و<webPublish>/<seo> (إن وُجدا) لبيانات SEO/OpenGraph، مطابقاً لفلسفة
"كل ملف .dlof يحمل تعليمات نشره ووصفه بداخله".
"""

from __future__ import annotations

import html
from typing import Optional

from . import models as m

_LAYOUT_CSS = {
    m.TemplateLayout.STANDARD: "max-width: 760px; margin: 2rem auto; padding: 0 1rem;",
    m.TemplateLayout.CARD: (
        "max-width: 640px; margin: 3rem auto; padding: 2rem; border-radius: 16px; "
        "box-shadow: 0 4px 24px rgba(0,0,0,.12);"
    ),
    m.TemplateLayout.MAGAZINE: "max-width: 920px; margin: 2rem auto; padding: 0 2rem; column-gap: 2rem;",
    m.TemplateLayout.MINIMAL: "max-width: 620px; margin: 4rem auto; padding: 0 1rem;",
}


def _esc(text: Optional[str]) -> str:
    return html.escape(text) if text else ""


def _content_to_html(item: m.ContentItem) -> str:
    if isinstance(item, m.QAItem):
        parts = [f"<h2>{_esc(item.question)}</h2>", f"<p>{_esc(item.answer)}</p>"]
        if item.explanation:
            parts.append(f"<blockquote>{_esc(item.explanation)}</blockquote>")
        if item.difficulty:
            parts.append(f"<p><em>الصعوبة: {_esc(item.difficulty)}</em></p>")
        return "\n".join(parts)

    if isinstance(item, m.BookChapter):
        parts = []
        if item.chapter_number is not None:
            parts.append(f"<p class='chapter-number'>الفصل {item.chapter_number}</p>")
        parts.append(f"<h2>{_esc(item.chapter_title)}</h2>")
        parts.append(f"<div class='chapter-text'>{_esc(item.text)}</div>")
        if item.summary:
            parts.append(f"<p><em>{_esc(item.summary)}</em></p>")
        return "\n".join(parts)

    if isinstance(item, m.TermDefinition):
        parts = [f"<h2>{_esc(item.term)}</h2>", f"<p>{_esc(item.definition)}</p>"]
        if item.example:
            parts.append(f"<p><strong>مثال:</strong> {_esc(item.example)}</p>")
        return "\n".join(parts)

    if isinstance(item, m.InfoExplain):
        parts = [f"<h2>{_esc(item.topic)}</h2>", f"<p>{_esc(item.explanation)}</p>"]
        if item.source:
            parts.append(f"<p><small>المصدر: {_esc(item.source)}</small></p>")
        return "\n".join(parts)

    if isinstance(item, m.EpisodeItem):
        parts = [f"<h2>{_esc(item.episode_title)}</h2>"]
        meta_bits = []
        if item.season_number is not None:
            meta_bits.append(f"الموسم {item.season_number}")
        if item.episode_number is not None:
            meta_bits.append(f"الحلقة {item.episode_number}")
        if meta_bits:
            parts.append(f"<p class='episode-meta'>{' · '.join(meta_bits)}</p>")
        if item.synopsis:
            parts.append(f"<p>{_esc(item.synopsis)}</p>")
        if item.body:
            parts.append(f"<div class='episode-body'>{_esc(item.body)}</div>")
        return "\n".join(parts)

    if isinstance(item, m.GenericItem):
        return f"<h2>{_esc(item.element or item.type)}</h2><div>{_esc(item.body)}</div>"

    return ""


def render_html(doc: m.DocumentLoop, standalone: bool = True, template_library: Optional[dict] = None) -> str:
    """
    يبني صفحة HTML كاملة (أو جزء <body> فقط إن standalone=False) لمستند dlof.

    template_library: قاموس اختياري {id: DlofTemplatePackage} (راجع
    dlof.packages.load_template_library) لحلّ template.ref إلى تصميم فعلي.
    """
    template = doc.template or m.Template()
    if template_library:
        from . import packages as _packages

        template = _packages.resolve_template(template, template_library)
    layout_css = _LAYOUT_CSS.get(template.layout, _LAYOUT_CSS[m.TemplateLayout.STANDARD])

    html_options = doc.web_publish.html_options if (doc.web_publish and doc.web_publish.html_options) else m.HtmlOptions()
    seo = doc.web_publish.seo if (doc.web_publish and doc.web_publish.seo) else None

    lang = html_options.lang or doc.metadata.language or "ar"
    direction = html_options.dir or "rtl"

    body_parts = []

    if html_options.include_meta_panel:
        meta_bits = [
            f"<span class='domain'>"
            f"{_esc(doc.metadata.domain.value if isinstance(doc.metadata.domain, m.Domain) else str(doc.metadata.domain))}"
            f"</span>"
        ]
        if doc.metadata.author:
            meta_bits.append(f"<span class='author'>{_esc(doc.metadata.author)}</span>")
        if doc.metadata.tags:
            meta_bits.append(
                "<span class='tags'>" + " ".join(f"#{_esc(t)}" for t in doc.metadata.tags) + "</span>"
            )
        body_parts.append(f"<header class='dlof-meta'>{' &middot; '.join(meta_bits)}</header>")

    content_html = "\n".join(_content_to_html(item) for item in doc.content)
    body_parts.append(f"<article class='dlof-content'>{content_html}</article>")

    if html_options.include_loop_nav:
        prev_html = ""
        next_html = ""
        if doc.loop_links.previous:
            title = _esc(doc.loop_links.previous.title or doc.loop_links.previous.ref)
            prev_html = f"<a class='loop-prev' href='{_esc(doc.loop_links.previous.ref)}'>&larr; {title}</a>"
        if doc.loop_links.next:
            title = _esc(doc.loop_links.next.title or doc.loop_links.next.ref)
            next_html = f"<a class='loop-next' href='{_esc(doc.loop_links.next.ref)}'>{title} &rarr;</a>"
        if prev_html or next_html:
            body_parts.append(f"<nav class='dlof-loop-nav'>{prev_html}{next_html}</nav>")

    body_html = "\n".join(body_parts)

    if not standalone:
        return body_html

    head_parts = [
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>{_esc(doc.metadata.title)}</title>",
    ]
    if seo and seo.meta_description:
        head_parts.append(f"<meta name='description' content='{_esc(seo.meta_description)}'>")
    if seo and seo.canonical_url:
        head_parts.append(f"<link rel='canonical' href='{_esc(seo.canonical_url)}'>")
    if seo and seo.keywords:
        head_parts.append(f"<meta name='keywords' content='{_esc(', '.join(seo.keywords))}'>")
    if seo and seo.og_image:
        head_parts.append(f"<meta property='og:image' content='{_esc(seo.og_image)}'>")
    head_parts.append(f"<meta property='og:title' content='{_esc(doc.metadata.title)}'>")
    if seo and seo.og_type:
        head_parts.append(f"<meta property='og:type' content='{_esc(seo.og_type.value)}'>")
    if seo and seo.twitter_card:
        head_parts.append(f"<meta name='twitter:card' content='{_esc(seo.twitter_card.value)}'>")
    if seo and seo.structured_data:
        head_parts.append(f"<script type='application/ld+json'>{seo.structured_data}</script>")
    if html_options.analytics_id:
        head_parts.append(f"<!-- analytics: {_esc(html_options.analytics_id)} -->")

    css = f"""
    body {{ font-family: {template.font_family or 'system-ui, sans-serif'};
            background: {template.background_color or '#ffffff'};
            color: {template.text_color or '#1c1b1f'}; line-height: 1.7; }}
    .dlof-page {{ {layout_css} }}
    .dlof-meta {{ color: {template.secondary_color or '#666'}; font-size: .9rem; margin-bottom: 1rem; }}
    h2 {{ color: {template.primary_color or '#333'}; }}
    .dlof-loop-nav {{ display: flex; justify-content: space-between; margin-top: 2rem;
                       border-top: 1px solid #eee; padding-top: 1rem; }}
    .dlof-loop-nav a {{ color: {template.primary_color or '#333'}; text-decoration: none; }}
    """
    if html_options.inject_css:
        css += "\n" + html_options.inject_css

    head_joined = "\n".join(head_parts)
    return (
        f"<!DOCTYPE html>\n"
        f"<html lang='{_esc(lang)}' dir='{_esc(direction)}'>\n"
        f"<head>\n{head_joined}\n<style>{css}</style>\n</head>\n"
        f"<body>\n<div class='dlof-page'>\n{body_html}\n</div>\n</body>\n</html>\n"
    )


def write_html(doc: m.DocumentLoop, path: str, template_library: Optional[dict] = None) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_html(doc, template_library=template_library))
    return path
