"""
تحليل امتداد الشخصيات (Yime) — العنصر <characters> بمجال الأسماء
https://dlof.org/ext/yime/1.0، المضمَّن عادة داخل genericItem
لملف characters.dlof (customType="characters").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from lxml import etree

from . import models as m

YIME_NS = "https://dlof.org/ext/yime/1.0"


def _yq(tag: str) -> str:
    return f"{{{YIME_NS}}}{tag}"


@dataclass
class Relation:
    target_id: str
    type: str = ""
    label: Optional[str] = None


@dataclass
class Character:
    id: str
    name: str
    role: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    status: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    backstory: Optional[str] = None
    goals: Optional[str] = None
    conflicts: Optional[str] = None
    relationships: List[Relation] = field(default_factory=list)
    appears_in: List[str] = field(default_factory=list)
    avatar_attachment_ref: Optional[str] = None
    author_notes: Optional[str] = None


@dataclass
class CharacterRoster:
    characters: List[Character] = field(default_factory=list)

    def get(self, character_id: str) -> Optional[Character]:
        for c in self.characters:
            if c.id == character_id:
                return c
        return None

    def relations_of(self, character_id: str) -> List[Relation]:
        c = self.get(character_id)
        return c.relationships if c else []


def parse_roster_from_generic_item(item: m.GenericItem) -> Optional[CharacterRoster]:
    """يبحث عن عنصر <characters> ضمن extra_xml الخاص بـ genericItem ويحلّله."""
    for raw_xml in item.extra_xml:
        el = etree.fromstring(raw_xml.encode("utf-8") if isinstance(raw_xml, str) else raw_xml)
        if el.tag == _yq("characters"):
            return parse_roster_element(el)
    return None


def parse_roster_from_document(doc: m.DocumentLoop) -> Optional[CharacterRoster]:
    """يبحث في محتوى DocumentLoop كاملاً عن أول genericItem يحمل قائمة شخصيات."""
    for item in doc.content:
        if isinstance(item, m.GenericItem):
            roster = parse_roster_from_generic_item(item)
            if roster is not None:
                return roster
    return None


def parse_roster_element(characters_el: etree._Element) -> CharacterRoster:
    roster = CharacterRoster()
    for char_el in characters_el.findall(_yq("character")):
        age_text = char_el.get("age")
        relationships = []
        rel_parent = char_el.find(_yq("relationships"))
        if rel_parent is not None:
            for rel_el in rel_parent.findall(_yq("relation")):
                relationships.append(
                    Relation(
                        target_id=rel_el.get("targetId", ""),
                        type=rel_el.get("type", ""),
                        label=rel_el.get("label"),
                    )
                )

        appears_in_text = _text(char_el, "appearsIn")
        appears_in = appears_in_text.split() if appears_in_text else []

        roster.characters.append(
            Character(
                id=char_el.get("id", ""),
                name=char_el.get("name", ""),
                role=char_el.get("role"),
                age=int(age_text) if age_text else None,
                gender=char_el.get("gender"),
                status=char_el.get("status"),
                alias=_text(char_el, "alias"),
                description=_text(char_el, "description"),
                appearance=_text(char_el, "appearance"),
                personality=_text(char_el, "personality"),
                backstory=_text(char_el, "backstory"),
                goals=_text(char_el, "goals"),
                conflicts=_text(char_el, "conflicts"),
                relationships=relationships,
                appears_in=appears_in,
                avatar_attachment_ref=_text(char_el, "avatarAttachmentRef"),
                author_notes=_text(char_el, "authorNotes"),
            )
        )
    return roster


def _text(parent: etree._Element, tag: str) -> Optional[str]:
    el = parent.find(_yq(tag))
    if el is None or el.text is None:
        return None
    return el.text.strip()


def roster_to_element(roster: CharacterRoster) -> etree._Element:
    """يبني عنصر <characters> (مجال أسماء yime) من CharacterRoster، لتضمينه
    في extra_xml الخاص بـ genericItem."""
    nsmap = {None: YIME_NS}
    root = etree.Element(_yq("characters"), nsmap=nsmap)
    for c in roster.characters:
        char_el = etree.SubElement(root, _yq("character"))
        char_el.set("id", c.id)
        char_el.set("name", c.name)
        if c.role:
            char_el.set("role", c.role)
        if c.age is not None:
            char_el.set("age", str(c.age))
        if c.gender:
            char_el.set("gender", c.gender)
        if c.status:
            char_el.set("status", c.status)

        def _add(tag, value):
            if value:
                sub_el = etree.SubElement(char_el, _yq(tag))
                sub_el.text = value

        _add("alias", c.alias)
        _add("description", c.description)
        _add("appearance", c.appearance)
        _add("personality", c.personality)
        _add("backstory", c.backstory)
        _add("goals", c.goals)
        _add("conflicts", c.conflicts)

        if c.relationships:
            rel_parent = etree.SubElement(char_el, _yq("relationships"))
            for rel in c.relationships:
                rel_el = etree.SubElement(rel_parent, _yq("relation"))
                rel_el.set("targetId", rel.target_id)
                rel_el.set("type", rel.type)
                if rel.label:
                    rel_el.set("label", rel.label)

        if c.appears_in:
            _add("appearsIn", " ".join(c.appears_in))
        _add("avatarAttachmentRef", c.avatar_attachment_ref)
        _add("authorNotes", c.author_notes)
    return root


def roster_to_generic_item(roster: CharacterRoster, body: str = "") -> m.GenericItem:
    """يبني genericItem (customType='characters') يحمل عنصر <characters> كامتداد."""
    el = roster_to_element(roster)
    xml_text = etree.tostring(el, encoding="unicode")
    return m.GenericItem(
        type="characters",
        element="roster",
        body=body,
        custom_type="characters",
        extra_xml=[xml_text],
    )
