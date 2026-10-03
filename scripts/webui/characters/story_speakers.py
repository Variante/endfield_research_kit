"""Discover speakers directly from exported story Tables, without Story builds.

Authored actor/sender ids are direct speaker evidence, not proof of a person's
identity. A visible name without an id is an unresolved label candidate (which
may be a group, role or narrator). A question-mark placeholder with a single
braced name uses that name; preserve its original label in evidence. Explicit
ampersand labels marked 异口同声 contribute separate participant evidence.
Never infer aliases from icons or extract people from prose.
Evidence is grouped with bounded localized line samples for review.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Iterator

from scripts.webui.characters.appearances import add_to_record, speaker_appearance

if TYPE_CHECKING:
    from scripts.webui.characters.build_character_data import CharacterCatalog


TABLES = ("DialogTextTable", "RadioTable", "EnvTalkTable", "MailSenderTable")
SAMPLE_LIMIT = 8


def visible_name(value: str) -> bool:
    text = unicodedata.normalize("NFKC", value).strip()
    return any(character != "?" and not character.isspace() for character in text)


def normalized_speaker_name(value: str) -> str:
    """Use the single named annotation in ???{Name}, retaining other labels."""
    text = value.strip()
    match = re.fullmatch(r"\?[?\s]*\{([^{}]+)\}", unicodedata.normalize("NFKC", text))
    if not match:
        return text
    name = match.group(1).strip()
    if not visible_name(name) or any(character in name for character in "?&、,;/+|{}"):
        return text
    # Scoped annotations are source labels, not a bare canonical name.
    if re.match(r"[a-z]\d", name, re.IGNORECASE):
        return text
    return name


def label_identity(value: str) -> str:
    label = unicodedata.normalize("NFKC", value).strip()
    return "story_label_" + hashlib.sha256(label.encode("utf-8")).hexdigest()[:24]


def joint_speaker_names(value: str, *, require_unison: bool = True) -> list[str]:
    """Split explicit A&B{异口同声}; other compound/scoped labels stay intact."""
    match = re.fullmatch(r"([^{}]+)\{([^{}]+)\}", unicodedata.normalize("NFKC", value).strip())
    if not match or (require_unison and match.group(2).strip() != "异口同声"):
        return []
    names = [name.strip() for name in match.group(1).split("&")]
    if len(names) < 2 or len(set(names)) != len(names):
        return []
    if any(not visible_name(name) or any(character in name for character in "?、,;/+|{}") for name in names):
        return []
    return names


def speaker_rows(tables: dict[str, dict[str, Any]]) -> Iterator[tuple[str, str, Any, Any, Any]]:
    """Yield only explicit speaker fields from the known table layouts."""
    for key, row in sorted(tables.get("DialogTextTable", {}).items()):
        if isinstance(row, dict):
            yield "DialogTextTable", key, row.get("actorNameId"), row.get("actorName"), row.get("dialogText")
    for key, row in sorted(tables.get("RadioTable", {}).items()):
        if not isinstance(row, dict):
            continue
        for index, line in enumerate(row.get("radioSingleDataList") or []):
            if not isinstance(line, dict):
                continue
            line_key = f"{key}.radioSingleDataList[{index}]"
            yield "RadioTable", line_key, line.get("actorNameId"), line.get("actorName"), line.get("radioText")
            if line.get("infoActorName"):
                yield "RadioTable", line_key + ".infoActorName", line.get("actorNameId"), line.get("infoActorName"), None
    for key, row in sorted(tables.get("EnvTalkTable", {}).items()):
        if not isinstance(row, dict):
            continue
        for index, line in enumerate(row.get("envTalkDataList") or []):
            if isinstance(line, dict):
                yield "EnvTalkTable", f"{key}.envTalkDataList[{index}]", line.get("actorId"), None, line.get("text")
    for key, row in sorted(tables.get("MailSenderTable", {}).items()):
        if isinstance(row, dict):
            yield "MailSenderTable", key, row.get("id") or key, row.get("senderName"), None


def add_story_speakers(
    catalog: CharacterCatalog,
    tables: dict[str, dict[str, Any]],
    localize: Callable[[Any], str],
    fallback_localize: Callable[[Any], str],
    language: str,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    seen_names: set[tuple[str, str, str]] = set()
    source_counts: dict[str, int] = defaultdict(int)
    # Only standalone authored speaker names can resolve a split participant.
    # This join remains unresolved evidence; it is not an authored id on the
    # joint line and does not merge ordinary name-only candidates.
    authored_names: dict[str, set[str]] = defaultdict(set)
    for _source, _key, actor_id, name_node, _text in speaker_rows(tables):
        if actor_id:
            name = normalized_speaker_name(fallback_localize(name_node))
            if visible_name(name) and not joint_speaker_names(name):
                identity = catalog.record(actor_id, "actor")["id"]
                authored_names[unicodedata.normalize("NFKC", name)].add(identity)
    for source, key, actor_id, name_node, text_node in speaker_rows(tables):
        actor_id = str(actor_id or "").strip()
        original_name = localize(name_node)
        name = normalized_speaker_name(original_name)
        if not visible_name(name):
            name = ""
        if not actor_id and not name:
            continue
        fallback_name = fallback_localize(name_node)
        appearance = speaker_appearance(source, key, tables, localize)
        joint_names = joint_speaker_names(fallback_name or original_name) if not actor_id else []
        if joint_names:
            localized_names = joint_speaker_names(original_name, require_unison=False)
            if len(localized_names) != len(joint_names):
                localized_names = joint_names
            source_counts[source] += 1
            for participant, localized_name in zip(joint_names, localized_names):
                targets = authored_names.get(participant, set())
                target_id = next(iter(targets)) if len(targets) == 1 else ""
                row = catalog.record(target_id, "actor") if target_id else catalog.record(label_identity(participant), "story_candidate")
                add_to_record(row, appearance, boundary="unresolved", attribution="jointSpeakerLabel", label=original_name)
                signature = (row["id"], source, localized_name)
                if signature not in seen_names:
                    catalog.add_name(row, localized_name, source, key, language=language)
                    seen_names.add(signature)
                group = groups.setdefault((row["id"], source, "story_joint_speaker"), {
                    "source": source, "type": "story_joint_speaker", "key": key,
                    "evidenceBoundary": "unresolved", "occurrenceCount": 0, "samples": [],
                    "nameNormalizations": [],
                    "participantName": participant, "matchedSpeakerId": target_id,
                    "note": "Explicit joint speaker label split into participants. Any identity association uses a unique standalone authored speaker name, not an actor id on this line.",
                })
                group["occurrenceCount"] += 1
                normalization = {"originalName": original_name, "name": localized_name, "rule": "joint_speaker_unison_label"}
                if normalization not in group["nameNormalizations"]:
                    group["nameNormalizations"].append(normalization)
                if len(group["samples"]) < SAMPLE_LIMIT:
                    group["samples"].append({
                        "key": key, "name": original_name,
                        "nameTextId": name_node.get("id") if isinstance(name_node, dict) else None,
                        "textId": text_node.get("id") if isinstance(text_node, dict) else None,
                        "text": localize(text_node)[:400],
                        "participantName": localized_name,
                    })
            continue
        if actor_id:
            row = catalog.record(actor_id, "actor")
            catalog.add_alias(row, actor_id)
            evidence_type = "story_speaker"
        else:
            # Translation ids are line-specific in these tables. Group labels
            # using the fallback language so CN/EN builds share candidate ids.
            label = fallback_name if visible_name(fallback_name) else original_name
            identity = label_identity(normalized_speaker_name(label))
            row = catalog.record(identity, "story_candidate")
            if normalized_speaker_name(label) != label.strip():
                catalog.add_alias(row, label_identity(label))
            evidence_type = "story_speaker_label"
        add_to_record(row, appearance, boundary="direct" if actor_id else "unresolved",
                      attribution="authoredSpeaker" if actor_id else "speakerLabel", label=original_name)
        signature = (row["id"], source, name)
        if name and signature not in seen_names:
            catalog.add_name(row, name, source, key, language=language)
            seen_names.add(signature)
        group = groups.setdefault((row["id"], source, evidence_type), {
            "source": source, "type": evidence_type, "key": key,
            "speakerId": actor_id,
            "evidenceBoundary": "direct" if actor_id else "unresolved",
            "occurrenceCount": 0, "samples": [], "nameNormalizations": [],
            "note": (
                "Authored speaker id; character identity and model ownership are not inferred."
                if actor_id else
                "Visible speaker label without an actor id. May name a person, group, role or narrator; identity unresolved."
            ),
        })
        group["occurrenceCount"] += 1
        source_counts[source] += 1
        if name and name != original_name.strip():
            normalization = {"originalName": original_name, "name": name, "rule": "question_mark_single_name_annotation"}
            if normalization not in group["nameNormalizations"]:
                group["nameNormalizations"].append(normalization)
        if len(group["samples"]) < SAMPLE_LIMIT:
            group["samples"].append({
                "key": key,
                "name": original_name,
                "nameTextId": name_node.get("id") if isinstance(name_node, dict) else None,
                "textId": text_node.get("id") if isinstance(text_node, dict) else None,
                "text": localize(text_node)[:400],
            })
    for (identity, _source, _type), evidence in groups.items():
        catalog.add_evidence(catalog.records[identity], evidence.pop("source"), evidence.pop("type"), evidence.pop("key"), **evidence)
    return [
        {"source": source, "table": source + ".json", "rule": "explicit speaker ids and unresolved visible speaker labels", "observations": count}
        for source, count in sorted(source_counts.items())
    ]


def add_proxy_speakers(
    catalog: CharacterCatalog,
    env_talk_table: dict[str, Any],
    proxy_rows: dict[str, Any],
    proxy_info: dict[str, Any],
    templates: dict[str, Any],
    named_text: Callable[[str], str],
    language: str,
) -> None:
    """Name ambient speakers through explicit proxy/name-key references only.

    Retain scoped proxy identities separately. No suffix stripping, shared
    prefab match or icon match proves a canonical character relationship.
    """
    template_names: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for key, template in sorted(templates.items()):
        if not isinstance(template, dict):
            continue
        identity = str(template.get("npcNameId") or key)
        for field in ("name", "title"):
            name_key = str(template.get(field) or "")
            name = named_text(name_key)
            if visible_name(name):
                template_names[identity].add((name_key, name))
    known_names: dict[str, set[str]] = defaultdict(set)
    for row in catalog.records.values():
        for alias in [row["id"], *row["aliases"]]:
            known_names[str(alias)].update(item["text"] for item in row["names"] if visible_name(item["text"]))
    relevant = {
        actor_id for source, _key, actor_id, _name, _text in speaker_rows({"EnvTalkTable": env_talk_table})
        if source == "EnvTalkTable" and actor_id
    }
    relevant.update(
        str(value.get("proxyId") or key)
        for key, value in proxy_rows.items()
        if isinstance(value, dict) and value.get("envTalkIds")
    )
    rows_by_id = {str(value.get("proxyId") or key): (key, value) for key, value in proxy_rows.items() if isinstance(value, dict)}
    for proxy_id in sorted(relevant):
        key, proxy = rows_by_id.get(proxy_id, (proxy_id, {}))
        override_key = str((proxy.get("overrideNpcNameId") or {}).get("key") or "")
        if proxy.get("ifOverrideNpcName") and override_key:
            name = named_text(override_key)
            if visible_name(name):
                row = catalog.record(proxy_id, "actor")
                catalog.add_alias(row, proxy_id)
                catalog.add_name(row, name, "NpcProxyTable", str(key), language=language)
                catalog.add_evidence(row, "NpcProxyTable", "story_speaker", str(key),
                                     evidenceBoundary="direct", speakerId=proxy_id, nameKey=override_key,
                                     envTalkIds=proxy.get("envTalkIds"), note="Explicit ambient speaker name override.")
            continue
        info = proxy_info.get(proxy_id)
        if not isinstance(info, dict):
            continue
        identity = str(info.get("npcNameId") or "")
        names = known_names.get(identity, set()) | {name for _key, name in template_names.get(identity, set())}
        if not names:
            continue
        row = catalog.record(proxy_id, "actor")
        catalog.add_alias(row, proxy_id)
        for name in sorted(names):
            catalog.add_name(row, name, "NpcProxyExDataTable", proxy_id, language=language)
        catalog.add_evidence(row, "NpcProxyExDataTable", "story_speaker", proxy_id,
                             evidenceBoundary="direct", speakerId=proxy_id, npcNameId=identity,
                             nameKeys=sorted(key for key, _name in template_names.get(identity, set())),
                             envTalkIds=proxy.get("envTalkIds"),
                             note="Explicit proxyInfoData.npcNameId reference; scoped identity is retained separately.")
