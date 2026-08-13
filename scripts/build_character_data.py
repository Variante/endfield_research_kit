#!/usr/bin/env python3
"""Build the WebUI Characters (人物) name-and-evidence catalog."""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__:
    from .common import EXPORT_ROOT, LANG_DIR, OUT_DIR, rel_path, write_json
else:
    from common import EXPORT_ROOT, LANG_DIR, OUT_DIR, rel_path, write_json


TABLE_ROOT_RELS = (
    ("StreamingAssets", Path("structured") / "StreamingAssets" / "Table"),
    ("Persistent", Path("structured") / "Persistent" / "Table"),
)
ASSET_MARKERS = (
    # "lod" is a LOD-variant marker, not a name (e.g. M_actor_lod_aglina_* is
    # the LOD material set for "aglina") — skip over it to reach the real name.
    # A trailing "_gender" (e.g. SK_actor_no_gender_*) is part of the token
    # itself, not a name suffix to drop — it's a generic genderless skeleton,
    # not a specific character, so keep "no_gender" whole rather than
    # truncating it to the misleading "no".
    ("actor_asset", re.compile(r"_actor_(?:lod_)?([a-z0-9]+(?:_gender)?)", re.IGNORECASE)),
    ("major_npc_asset", re.compile(r"(?:_major_npc_|_npc_major_)(?:lod_)?([a-z0-9]+)", re.IGNORECASE)),
    # dlg_npc_XXXX_<name>... → capture <name> (e.g. dlg_npc_0004_pelica_* → pelica)
    ("dlg_npc_asset", re.compile(r"dlg_npc_\d{4}_([a-z][a-z0-9]+)", re.IGNORECASE)),
    # icon_npc_XXXX_<name>... or icon_npc_<name>... → capture <name>
    # (e.g. icon_npc_1001_andrew* → andrew, icon_npc_buyuan* → buyuan)
    ("icon_npc_asset", re.compile(r"icon_npc_(?:\d{4}_)?([a-z][a-z0-9]+)", re.IGNORECASE)),
    # sns_npc_<name>_NN... → capture <name> (e.g. sns_npc_madina_01* → madina)
    ("sns_npc_asset", re.compile(r"sns_npc_([a-z][a-z0-9]+)", re.IGNORECASE)),
    # _npc_animal_<type>... → capture animal_<type> (e.g. P_npc_animal_bat → animal_bat)
    ("npc_animal_asset", re.compile(r"_npc_(animal_[a-z][a-z0-9]+)", re.IGNORECASE)),
    # _lod_<name>... → capture <name> (e.g. P_npc_lod_aglina → aglina, not "lod")
    ("npc_asset", re.compile(r"_lod_([a-z][a-z0-9]+)", re.IGNORECASE)),
    # generic fallback: _npc_<token>
    ("npc_asset", re.compile(r"_npc_([a-z0-9]+)", re.IGNORECASE)),
)
PATH_ID_SUFFIX_RE = re.compile(r"_p[0-9a-f]{16}(?=\.[^.]+$)", re.IGNORECASE)
# Tokens that ASSET_MARKERS can capture but that never name a character —
# config/table files, level-editor markers, generic shared props, or a
# marker-word left over once its real qualifier is stripped (e.g.
# "map_racing_NPC_unactive_*" → "unactive", "bg_npc_list_topic_*" → "list").
# These are excluded outright rather than recorded as identities.
EXCLUDED_TOKENS = frozenset({
    "lodconfig",
    "levelmapmark",
    "muzzle",
    "prefabtable",
    "prop",
    "shared",
    "general",
    "general_item",
    "list",
    "unactive",
    # "ztc" is a numbered VFX material group (M_fxgp_actor_ztc_001/002/...),
    # not a character; "shadow" is a generic decoration/blackbox shadow
    # sprite (bg_blackbox_npc_shadow, icon_blackbox_npc_shadow, ...).
    "ztc",
    "shadow",
    # "terminal"/"sterminal" are generic interactable-terminal animator sets
    # (AC_npc_terminal_*, AC_npc_sterminal_*); "social"/"single"/"group" are
    # generic SNS/social UI category icons, not per-NPC art; "phantp" is a
    # VFX soul-effect material (M_actor_phantp_souleffect_*); "diffuse" is a
    # VFX diffuse-texture material channel (..._npc_diffuse_1101_*), not a
    # character.
    "terminal",
    "sterminal",
    "social",
    "single",
    "group",
    "phantp",
    "diffuse",
    # "robot"/"machine"/"signaltower" are generic props/effects (a robot-
    # welcome VFX material, a machine mesh, a signal-tower mesh), not named
    # characters.
    "robot",
    "machine",
    "signaltower",
})
# Whole filename families to skip outright, before ASSET_MARKERS even runs —
# used when the family produces a different bogus token per file (numbered
# background plates, positional UI icons) rather than one fixed token.
EXCLUDED_FILENAME_FRAGMENTS = frozenset({
    "icon_settlement_npc",  # positional settlement-panel icons: _bottom/_left/_right
    "bg_blackbox_npc",  # numbered blackbox background plates: _1/_2/...
})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", nargs="+", default=["CN"])
    parser.add_argument("--default-language", default="CN")
    parser.add_argument("--export-root", type=Path, default=EXPORT_ROOT)
    parser.add_argument("--out-dir", type=Path, default=LANG_DIR)
    parser.add_argument("--asset-index", type=Path, default=OUT_DIR / "assets" / "index.json")
    return parser.parse_args(argv)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def merge_payload(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        return {**base, **overlay}
    if isinstance(base, list) and isinstance(overlay, list):
        return [*base, *overlay]
    return overlay


def table_roots(export_root: Path) -> list[tuple[str, Path]]:
    return [(label, export_root / rel) for label, rel in TABLE_ROOT_RELS if (export_root / rel).is_dir()]


def load_merged_table(roots: Iterable[tuple[str, Path]], name: str) -> dict[str, Any]:
    result: Any = {}
    found = False
    for _label, root in roots:
        payload = read_json(root / name)
        if payload is None:
            continue
        result = payload if not found else merge_payload(result, payload)
        found = True
    return result if isinstance(result, dict) else {}


def normalize_identity(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    match = re.match(r"^chr_\d+_(.+)$", text)
    return match.group(1) if match else text


def localized_text(node: Any, i18n: dict[str, Any], fallback: dict[str, Any]) -> str:
    if isinstance(node, str):
        return node.strip()
    if not isinstance(node, dict):
        return ""
    text = str(node.get("text") or "").strip()
    if text:
        return text
    text_id = node.get("id")
    if text_id in (None, "", 0, "0"):
        return ""
    return str(i18n.get(str(text_id)) or fallback.get(str(text_id)) or "").strip()


def unique_strings(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        folded = text.casefold()
        if not text or folded in seen:
            continue
        seen.add(folded)
        result.append(text)
    return result


def iter_asset_entries(asset_index_path: Path, export_root: Path) -> tuple[Iterable[dict[str, Any]], str]:
    payload = read_json(asset_index_path, {})
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if isinstance(entries, list):
        return entries, rel_path(asset_index_path)

    recovered_root = export_root / "recovered" / "AnimeStudio-cli"

    def scan() -> Iterable[dict[str, Any]]:
        if not recovered_root.is_dir():
            return
        kind_by_suffix = {
            ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
            ".fbx": "model", ".obj": "model", ".glb": "model",
            ".mp4": "video", ".webm": "video",
            ".json": "json",
        }
        for path in recovered_root.rglob("*"):
            if not path.is_file() or "convert_by_type" not in path.parts:
                continue
            kind = kind_by_suffix.get(path.suffix.lower())
            if not kind:
                continue
            yield {
                "k": kind,
                "r": path.relative_to(recovered_root).as_posix(),
            }

    return scan(), rel_path(recovered_root)


class CharacterCatalog:
    def __init__(self, language: str) -> None:
        self.language = language
        self.records: dict[str, dict[str, Any]] = {}
        self.alias_to_id: dict[str, str] = {}
        self.asset_groups: dict[tuple[str, str, str], dict[str, Any]] = {}

    def record(self, identity: Any, kind: str = "actor") -> dict[str, Any]:
        normalized = normalize_identity(identity) or "unknown"
        canonical = self.alias_to_id.get(normalized, normalized)
        row = self.records.setdefault(canonical, {
            "id": canonical,
            "kind": kind,
            "names": [],
            "aliases": [],
            "evidence": [],
        })
        priority = {"character": 0, "npc": 1, "actor": 2, "asset_npc": 3}
        if priority.get(kind, 9) < priority.get(str(row.get("kind") or ""), 9):
            row["kind"] = kind
        self.alias_to_id[normalized] = canonical
        return row

    def add_alias(self, row: dict[str, Any], alias: Any) -> None:
        text = str(alias or "").strip()
        normalized = normalize_identity(text)
        if not text or not normalized:
            return
        if text not in row["aliases"]:
            row["aliases"].append(text)
        self.alias_to_id.setdefault(normalized, row["id"])

    def add_name(self, row: dict[str, Any], text: Any, source: str, key: str, *, language: str = "") -> None:
        value = str(text or "").strip()
        if not value:
            return
        signature = (value.casefold(), source, key)
        if any((str(item.get("text") or "").casefold(), item.get("source"), item.get("key")) == signature for item in row["names"]):
            return
        row["names"].append({
            "text": value,
            "source": source,
            "key": key,
            **({"language": language} if language else {}),
        })

    def add_evidence(self, row: dict[str, Any], source: str, evidence_type: str, key: str, **details: Any) -> None:
        item = {"source": source, "type": evidence_type, "key": key}
        item.update({name: value for name, value in details.items() if value not in (None, "", [], {})})
        if item not in row["evidence"]:
            row["evidence"].append(item)

    def resolve_asset_identity(self, token_id: str) -> tuple[dict[str, Any] | None, str]:
        canonical = self.alias_to_id.get(token_id)
        if canonical and canonical in self.records:
            return self.records[canonical], "exact_alias"
        if len(token_id) < 5:
            return None, ""

        candidates: list[tuple[int, int, str, dict[str, Any]]] = []
        source_priority = {
            "CharacterTable": 0,
            "NpcTable": 1,
            "TextTable": 2,
            "SNSChatTable": 3,
            "Story actor registry": 4,
        }
        for row in self.records.values():
            localized_names = [
                str(item.get("text") or "").strip()
                for item in row.get("names", [])
                if item.get("source") != "Exported asset identifier" and str(item.get("text") or "").strip()
            ]
            if not localized_names:
                continue
            aliases = unique_strings([row.get("id"), *row.get("aliases", [])])
            matched_aliases = [
                normalize_identity(alias)
                for alias in aliases
                if normalize_identity(alias).endswith(token_id)
            ]
            if not matched_aliases:
                continue
            rank = min(
                (source_priority.get(str(item.get("source") or ""), 9) for item in row.get("names", [])),
                default=9,
            )
            extra_length = min(len(alias) - len(token_id) for alias in matched_aliases)
            candidates.append((rank, extra_length, str(row.get("id") or ""), row))

        if not candidates:
            return None, ""
        best_rank = min(item[0] for item in candidates)
        ranked = [item for item in candidates if item[0] == best_rank]
        known_names = {
            str(item[3]["names"][0].get("text") or "").strip().casefold()
            for item in ranked
            if item[3].get("names")
        }
        if len(known_names) != 1:
            return None, ""
        ranked.sort(key=lambda item: (item[1], item[2]))
        return ranked[0][3], "existing_name_suffix"

    def add_asset(self, path: str, asset_kind: str = "", path_id: str = "") -> None:
        basename = PATH_ID_SUFFIX_RE.sub("", Path(path).name)
        lowered = basename.lower()
        if any(fragment in lowered for fragment in EXCLUDED_FILENAME_FRAGMENTS):
            return
        matched: tuple[str, str] | None = None
        for evidence_type, pattern in ASSET_MARKERS:
            match = pattern.search(lowered)
            if match:
                matched = evidence_type, match.group(1)
                break
        if not matched:
            return
        evidence_type, token = matched
        token_id = normalize_identity(token)
        if token_id in EXCLUDED_TOKENS:
            return
        kind = "actor" if evidence_type == "actor_asset" else "asset_npc"
        row, resolution = self.resolve_asset_identity(token_id)
        if row is None:
            row = self.record(token_id, kind)
        self.add_alias(row, token)
        group_key = (row["id"], evidence_type, asset_kind or "asset")
        group = self.asset_groups.setdefault(group_key, {
            "source": "Exported assets",
            "type": evidence_type,
            "key": token,
            "assetKind": asset_kind or "asset",
            "count": 0,
            "paths": [],
            "pathIds": [],
            **({"matchedIdentity": row["id"], "matchRule": resolution} if resolution else {}),
        })
        group["count"] += 1
        if len(group["paths"]) < 12 and path not in group["paths"]:
            group["paths"].append(path)
        if path_id and len(group["pathIds"]) < 12 and path_id not in group["pathIds"]:
            group["pathIds"].append(path_id)

    def finish_assets(self) -> None:
        for (record_id, _evidence_type, _asset_kind), evidence in self.asset_groups.items():
            row = self.records[record_id]
            if not row["names"]:
                self.add_name(row, evidence["key"], "Exported asset identifier", evidence["key"])
            row["evidence"].append(evidence)

    def payload(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        rows = []
        for row in self.records.values():
            row["aliases"] = unique_strings(row["aliases"])
            row["names"].sort(key=lambda item: (
                {
                    "CharacterTable": 0,
                    "NpcTable": 1,
                    "TextTable": 2,
                    "SNSChatTable": 3,
                    "Story actor registry": 4,
                }.get(item["source"], 9),
                0 if item.get("language") == self.language else (1 if not item.get("language") else 2),
                item["text"].casefold(),
            ))
            row["evidence"].sort(key=lambda item: (item["source"], item["type"], item["key"]))
            preferred = next((item["text"] for item in row["names"] if item["source"] != "Exported asset identifier"), "")
            row["primaryName"] = preferred or (row["names"][0]["text"] if row["names"] else row["id"])
            row["sourceTypes"] = sorted({item["source"] for item in row["evidence"]})
            rows.append(row)
        rows.sort(key=lambda item: (
            {"character": 0, "npc": 1, "actor": 2, "asset_npc": 3}.get(item["kind"], 9),
            item["primaryName"].casefold(),
            item["id"],
        ))
        counts = defaultdict(int)
        for row in rows:
            counts[row["kind"]] += 1
        return {
            "generated": int(time.time()),
            "language": self.language,
            "sources": sources,
            "counts": {"records": len(rows), **dict(sorted(counts.items()))},
            "records": rows,
        }


def build_language_payload(
    language: str,
    roots: list[tuple[str, Path]],
    fallback_language: str,
    actor_path: Path,
    asset_index_path: Path,
) -> dict[str, Any]:
    catalog = CharacterCatalog(language)
    fallback_i18n = load_merged_table(roots, f"I18nTextTable_{fallback_language}.json")
    i18n = fallback_i18n if language == fallback_language else load_merged_table(roots, f"I18nTextTable_{language}.json")
    text_table = load_merged_table(roots, "TextTable.json")
    character_table = load_merged_table(roots, "CharacterTable.json")
    npc_table = load_merged_table(roots, "NpcTable.json")
    sns_chat_table = load_merged_table(roots, "SNSChatTable.json")
    sources: list[dict[str, Any]] = []

    for key, node in text_table.items():
        if not str(key).lower().startswith("npcname_"):
            continue
        identity = str(key)[len("npcName_"):]
        row = catalog.record(identity, "npc")
        catalog.add_alias(row, identity)
        catalog.add_alias(row, key)
        catalog.add_name(row, localized_text(node, i18n, fallback_i18n), "TextTable", str(key), language=language)
        catalog.add_evidence(row, "TextTable", "npc_name_key", str(key), textId=node.get("id") if isinstance(node, dict) else None)
    sources.append({"source": "TextTable", "table": "TextTable.json", "rule": "npcName_*"})

    for key, value in character_table.items():
        if not isinstance(value, dict):
            continue
        row = catalog.record(key, "character")
        catalog.add_alias(row, key)
        catalog.add_alias(row, value.get("charId"))
        catalog.add_alias(row, normalize_identity(key))
        catalog.add_name(row, localized_text(value.get("name"), i18n, fallback_i18n), "CharacterTable", str(key), language=language)
        catalog.add_name(row, value.get("engName"), "CharacterTable", str(key), language="EN")
        catalog.add_evidence(row, "CharacterTable", "playable_character_row", str(key), nameTextId=(value.get("name") or {}).get("id"))
    sources.append({"source": "CharacterTable", "table": "CharacterTable.json", "rule": "all playable-character rows"})

    for key, value in npc_table.items():
        if not isinstance(value, dict):
            continue
        row = catalog.record(key, "npc")
        for alias in (key, value.get("npcId"), value.get("dataKey"), value.get("npcGroupId")):
            catalog.add_alias(row, alias)
        catalog.add_name(row, localized_text(value.get("name"), i18n, fallback_i18n), "NpcTable", str(key), language=language)
        catalog.add_name(row, localized_text(value.get("title"), i18n, fallback_i18n), "NpcTable", str(key), language=language)
        catalog.add_evidence(
            row,
            "NpcTable",
            "npc_row",
            str(key),
            dataKey=value.get("dataKey"),
            npcGroupId=value.get("npcGroupId"),
            nameTextId=(value.get("name") or {}).get("id"),
        )
    sources.append({"source": "NpcTable", "table": "NpcTable.json", "rule": "all named NPC rows"})

    for key, value in sns_chat_table.items():
        if not isinstance(value, dict):
            continue
        chat_id = str(value.get("chatId") or key)
        row = catalog.record(chat_id, "npc")
        for alias in (key, chat_id):
            catalog.add_alias(row, alias)
        catalog.add_name(
            row,
            localized_text(value.get("name"), i18n, fallback_i18n),
            "SNSChatTable",
            str(key),
            language=language,
        )
        catalog.add_evidence(
            row,
            "SNSChatTable",
            "sns_chat_row",
            str(key),
            nameTextId=(value.get("name") or {}).get("id"),
            dataKey=chat_id,
        )
    sources.append({"source": "SNSChatTable", "table": "SNSChatTable.json", "rule": "all named SNS chat rows"})

    actor_payload = read_json(actor_path, {})
    actor_names = actor_payload.get("actorNames") if isinstance(actor_payload, dict) else {}
    if isinstance(actor_names, dict):
        for actor_id, names in actor_names.items():
            row = catalog.record(actor_id, "actor")
            catalog.add_alias(row, actor_id)
            for name in names if isinstance(names, list) else [names]:
                catalog.add_name(row, name, "Story actor registry", str(actor_id), language=language)
            catalog.add_evidence(
                row,
                "Story actor registry",
                "assembled_actor_name",
                str(actor_id),
                note="Generated from dialog, environment talk, SNS/mail, NPC templates, and related Story sources.",
            )
        sources.append({"source": "Story actor registry", "path": rel_path(actor_path), "rule": "all actorNames entries"})

    entries, asset_source_path = iter_asset_entries(asset_index_path, roots[0][1].parents[2])
    asset_entry_count = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        asset_entry_count += 1
        catalog.add_asset(str(entry.get("r") or ""), str(entry.get("k") or ""), str(entry.get("pid") or ""))
    if asset_entry_count:
        catalog.finish_assets()
        sources.append({
            "source": "Exported assets",
            "path": asset_source_path,
            "rule": "_actor_, _major_npc_/_npc_major_, and _npc_ filename markers",
        })

    return catalog.payload(sources)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    roots = table_roots(args.export_root)
    if not roots:
        print(f"Missing table directories under {args.export_root / 'structured'}")
        return 2
    fallback = str(args.default_language).strip().upper() or "CN"
    outputs = []
    for raw_language in args.languages:
        language = str(raw_language).strip().upper()
        if not language:
            continue
        actor_path = args.out_dir / language / "actors.json"
        payload = build_language_payload(language, roots, fallback, actor_path, args.asset_index)
        output = args.out_dir / language / "characters" / "index.json"
        write_json(output, payload)
        outputs.append((language, output, payload["counts"]))
    for language, output, counts in outputs:
        print(f"{language}: wrote {rel_path(output)} ({counts['records']} character/NPC identities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
