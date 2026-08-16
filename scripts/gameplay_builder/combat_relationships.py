"""Build a compact, evidence-labelled combat relationship payload for WebUI.

The normal input is the curated Gameplay index.  When the local source graph is
available, direct decoded references to buffs, effects, audio, and assets are
added.  Missing graph data is a supported degraded mode.

Run from the repository root:
    python scripts/build_combat_relationships.py
    python scripts/build_combat_relationships.py --languages CN EN JP
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXPORT_ROOT = Path(os.environ.get("ENDFIELD_EXPORT_ROOT") or ROOT / "export_full")
DEFAULT_DATA_ROOT = ROOT / "webui" / "data" / "lang"
DEFAULT_GRAPH = ROOT / "reports" / "source_graph" / "endfield_source_graph.sqlite"
DEFAULT_ANIMESTUDIO_ROOT = EXPORT_ROOT / "recovered" / "AnimeStudio-cli"
SCHEMA_VERSION = 7

GRAPH_EDGE_TYPES = {
    "skill_data_has_param_string",
    "skill_data_references_buff",
    "skill_data_references_effect",
    "skill_data_references_audio",
    "buff_data_references_buff",
    "buff_data_references_effect",
    "buff_data_references_audio",
}
IGNORED_CONFIG_GRAPH_EDGE_TYPES = {
    "skill_data_defines_skill",
    "skill_data_has_tag_string",
    "skill_data_references_icon",
    "buff_data_defines_buff",
    "buff_data_has_param_string",
    "buff_data_has_tag_string",
    "buff_data_references_icon",
}
KNOWN_CONFIG_GRAPH_EDGE_TYPES = GRAPH_EDGE_TYPES | IGNORED_CONFIG_GRAPH_EDGE_TYPES
HEURISTIC_CONFIG_GRAPH_EDGE_TYPES = frozenset(GRAPH_EDGE_TYPES)
INFERRED_GRAPH_EDGE_TYPES = {
    "asset_used_by_gameplay",
    "effect_name_matches_export_base_asset",
} | HEURISTIC_CONFIG_GRAPH_EDGE_TYPES
PROJECTILE_TOKEN_RE = re.compile(r"(?:projectile|bullet|missile)", re.IGNORECASE)
SELECTOR_COUNT_RE = re.compile(r"(?:^|,)(find|select|query):(\d+)")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--languages", nargs="+", default=["CN"])
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--animestudio-root", type=Path, default=DEFAULT_ANIMESTUDIO_ROOT)
    parser.add_argument("--max-assets-per-entity", type=int, default=8)
    parser.add_argument("--max-assets-per-effect", type=int, default=2)
    return parser.parse_args(argv)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def compact_source(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: value[key] for key in sorted(value) if value[key] not in (None, "", [], {})}
    return value


def graph_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def raw_stats(entry: dict[str, Any]) -> dict[str, Any]:
    stats = entry.get("stats") or {}
    points = stats.get("rows") or stats.get("checkpoints") or []
    selected: list[Any] = []
    if points:
        selected.append(points[0])
        if len(points) > 1:
            selected.append(points[-1])
    return {
        key: value
        for key, value in {
            "source": stats.get("source"),
            "templateId": stats.get("templateId"),
            "maxLevel": stats.get("maxLevel"),
            "pointCount": stats.get("pointCount") or stats.get("rowCount"),
            "interpolated": stats.get("interpolated"),
            "authoredBoundaryPoints": selected,
        }.items()
        if value not in (None, "", [], {})
    }


def node_sort_key(node: dict[str, Any]) -> tuple[str, str]:
    return str(node.get("kind", "")), str(node.get("id", ""))


def edge_sort_key(edge: dict[str, Any]) -> tuple[str, str, str, str, str]:
    evidence = edge.get("evidence") or {}
    return (
        str(edge.get("source", "")),
        str(edge.get("type", "")),
        str(edge.get("target", "")),
        str(evidence.get("source", "")),
        str(evidence.get("path", "")),
    )


class PayloadBuilder:
    def __init__(
        self,
        language: str,
        gameplay: dict[str, Any],
        graph_path: Path,
        graph_stale_reason: str,
        animestudio_root: Path,
        max_assets_per_entity: int,
        max_assets_per_effect: int,
    ) -> None:
        self.language = language
        self.gameplay = gameplay
        self.graph_path = graph_path
        self.graph_stale_reason = graph_stale_reason
        self.animestudio_root = animestudio_root
        self.max_assets_per_entity = max(0, max_assets_per_entity)
        self.max_assets_per_effect = max(0, max_assets_per_effect)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        self.roots: list[str] = []
        self.graph: sqlite3.Connection | None = None
        self.skill_ids: set[str] = set()
        self.buff_ids: set[str] = set()
        self.effect_ids: set[str] = set()
        self.ability_entity_available = False
        self.ability_entity_files = 0
        self.ability_entity_records = 0
        self.ability_entity_components = 0
        self.ability_entity_root_matches = 0
        self.ability_entity_openings = 0
        self.ability_entity_opening_mirrors = 0
        self.ability_entity_surrounding_configs = 0
        self.ability_entity_surrounding_mirrors = 0
        self.ability_entity_next_boundary_mirrors = 0
        self.target_settings_available = False
        self.target_settings_files = 0
        self.target_settings_records = 0
        self.target_settings_attached = 0
        self.target_selector_links = 0
        self.graph_edge_contract_observed: dict[str, int] = {}
        self.graph_edge_contract_accepted: dict[str, int] = {}
        self.graph_edge_contract_unexpected: dict[str, int] = {}

    def inspect_graph_edge_contract(self) -> None:
        """Reset the edge contract before inspecting reachable graph rows.

        Rows are recorded while traversing current Gameplay skill roots and
        their accepted BuffData descendants.  Unrelated graph domains and
        unreachable skills/buffs are outside this consumer contract.
        """
        self.graph_edge_contract_observed = {}
        self.graph_edge_contract_accepted = {}
        self.graph_edge_contract_unexpected = {}

    def inspect_graph_edge_row(self, row: tuple[Any, ...]) -> None:
        kind = str(row[2])
        if not kind.startswith(("skill_data_", "buff_data_")):
            return
        self.graph_edge_contract_observed[kind] = self.graph_edge_contract_observed.get(kind, 0) + 1
        if kind not in KNOWN_CONFIG_GRAPH_EDGE_TYPES:
            self.graph_edge_contract_unexpected[kind] = self.graph_edge_contract_unexpected.get(kind, 0) + 1

    def add_node(self, node_id: str, kind: str, label: str = "", **values: Any) -> None:
        node = self.nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label or node_id.split(":", 1)[-1]})
        if label and (not node.get("label") or node.get("label") == node_id.split(":", 1)[-1]):
            node["label"] = label
        for key, value in values.items():
            if value not in (None, "", [], {}):
                node[key] = value

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        *,
        confidence: str,
        evidence_source: str,
        evidence_path: str = "",
        raw: Any = None,
        note: str = "",
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            return
        key = (source, target, edge_type, evidence_source, evidence_path)
        edge: dict[str, Any] = {
            "source": source,
            "target": target,
            "type": edge_type,
            "confidence": confidence,
            "evidence": {"source": evidence_source},
        }
        if evidence_path:
            edge["evidence"]["path"] = evidence_path
        if raw not in (None, "", [], {}):
            edge["evidence"]["raw"] = raw
        if note:
            edge["note"] = note
        self.edges[key] = edge

    def add_authored_gameplay(self) -> None:
        for entry in sorted(self.gameplay.get("entries") or [], key=lambda item: (str(item.get("kind", "")), str(item.get("id", "")))):
            kind = str(entry.get("kind") or "")
            if kind not in {"character", "enemy"}:
                continue
            key = str(entry.get("id") or "").strip()
            if not key:
                continue
            node_id = f"{kind}:{key}"
            raw: dict[str, Any]
            if kind == "character":
                raw = {
                    "rarity": entry.get("rarity"),
                    "profession": entry.get("profession"),
                    "professionLabel": entry.get("professionLabel"),
                    "element": entry.get("element"),
                    "elementLabel": entry.get("elementLabel"),
                    "weaponType": entry.get("weaponType"),
                    "weaponTypeLabel": entry.get("weaponTypeLabel"),
                    "stats": raw_stats(entry),
                }
            else:
                raw = {
                    "displayType": entry.get("displayType"),
                    "displayTypeLabel": entry.get("displayTypeLabel"),
                    "damageScalars": entry.get("damageScalars") or [],
                    "resilience": entry.get("resilience") or [],
                    "attrModifiers": entry.get("attrModifiers") or [],
                    "stats": raw_stats(entry),
                }
            raw = {name: value for name, value in raw.items() if value not in (None, "", [], {})}
            self.add_node(
                node_id,
                kind,
                str(entry.get("title") or key),
                key=key,
                subtitle=entry.get("subtitle"),
                source=compact_source(entry.get("source")),
                raw=raw,
            )
            self.roots.append(node_id)
            if kind == "character":
                self.add_character_skills(node_id, entry)
            else:
                self.add_enemy_relations(node_id, entry)

    def add_character_skills(self, character_id: str, entry: dict[str, Any]) -> None:
        for group_index, group in enumerate(entry.get("skillGroups") or []):
            group_key = str(group.get("id") or f"{entry.get('id')}:group:{group_index}")
            group_id = f"skill_group:{group_key}"
            self.add_node(
                group_id,
                "skill_group",
                str(group.get("name") or group_key),
                key=group_key,
                subtitle=group.get("typeLabel"),
                raw={
                    key: value
                    for key, value in {
                        "type": group.get("type"),
                        "descriptionTemplate": group.get("descriptionTemplate"),
                        "blackboard": group.get("blackboard") or [],
                        "iconId": group.get("iconId"),
                    }.items()
                    if value not in (None, "", [], {})
                },
            )
            self.add_edge(
                character_id,
                group_id,
                "has_skill_group",
                confidence="direct",
                evidence_source="webui/gameplay",
                evidence_path=f"skillGroups[{group_index}]",
                raw={"id": group_key, "type": group.get("type")},
            )
            for skill_index, skill_key_value in enumerate(group.get("actionSkillIds") or []):
                skill_key = str(skill_key_value).strip()
                if not skill_key:
                    continue
                skill_id = f"gameplay_skill:{skill_key}"
                self.skill_ids.add(skill_key)
                self.add_node(skill_id, "ability", skill_key, key=skill_key)
                self.add_edge(
                    group_id,
                    skill_id,
                    "references_action_skill",
                    confidence="direct",
                    evidence_source="webui/gameplay",
                    evidence_path=f"actionSkillIds[{skill_index}]",
                    raw=skill_key,
                )

    def add_enemy_relations(self, enemy_id: str, entry: dict[str, Any]) -> None:
        display_source = entry.get("displaySource") or {}
        display_table = str(display_source.get("table") or "EnemyTemplateDisplayInfoTable.json")
        display_key = str(display_source.get("id") or entry.get("id") or "")
        for index, ability in enumerate(entry.get("abilities") or []):
            key = str(ability.get("id") or "").strip()
            if not key:
                continue
            # EnemyTemplateDisplayInfoTable.abilityDescIds is a localized
            # presentation reference.  It is not a SkillData/action id, so
            # do not put it in the executable-skill namespace or feed it to
            # source-graph SkillData enrichment.
            description_id = f"ability_description:{key}"
            self.add_node(
                description_id,
                "ability_description",
                str(ability.get("name") or key),
                key=key,
                semanticStatus="exact display-table ability-description reference; executable SkillData not proven",
                source={"table": display_table, "id": display_key, "field": "abilityDescIds"},
                raw={
                    "description": ability.get("description"),
                    "descriptionId": key,
                    "legacySkillNodeId": f"gameplay_skill:{key}",
                },
            )
            self.add_edge(
                enemy_id,
                description_id,
                "has_ability_description",
                confidence="direct",
                evidence_source=display_table,
                evidence_path=f"{display_key}.abilityDescIds[{index}]",
                raw=key,
                note="The display table directly lists this localized ability-description ID; this does not prove an executable SkillData/action relationship.",
            )

        variants = [variant for variant in entry.get("variants") or [] if isinstance(variant, dict)]
        for variant_index, variant in enumerate(variants):
            key = str(variant.get("id") or "").strip()
            if not key:
                continue
            source = variant.get("source") or {}
            source_table = str(source.get("table") or "EnemyTable.json")
            source_key = str(source.get("id") or key)
            variant_id = f"enemy_variant:{key}"
            raw = {
                name: value
                for name, value in {
                    "templateId": variant.get("templateId"),
                    "attrTemplateId": variant.get("attrTemplateId"),
                    "modelId": variant.get("modelId"),
                    "aiTemplateId": variant.get("aiTemplateId"),
                    "displayType": variant.get("displayType"),
                    "isDangerous": variant.get("isDangerous"),
                    "bornBuffs": variant.get("bornBuffs") or [],
                    "attrModifiers": variant.get("attrModifiers") or [],
                }.items()
                if value not in (None, "", [], {})
            }
            self.add_node(
                variant_id,
                "enemy_variant",
                str(variant.get("name") or key),
                key=key,
                semanticStatus="exact authored EnemyTable row",
                source={"table": source_table, "id": source_key},
                raw=raw,
            )
            self.add_edge(
                enemy_id,
                variant_id,
                "has_authored_variant",
                confidence="direct",
                evidence_source=source_table,
                evidence_path=source_key,
                raw={"variantIndex": variant_index, "id": key},
                note="Template grouping and the complete variant row are preserved from EnemyTable.",
            )

            attr_template_key = str(variant.get("attrTemplateId") or "").strip()
            if attr_template_key:
                attr_template_id = f"enemy_attr_template:{attr_template_key}"
                attr_payload = (entry.get("attributeTemplates") or {}).get(attr_template_key) or {}
                self.add_node(
                    attr_template_id,
                    "attribute_template",
                    attr_template_key,
                    key=attr_template_key,
                    semanticStatus="exact authored attribute-template reference",
                    source=compact_source(attr_payload.get("source")) or {
                        "table": "EnemyAttributeTemplateTable.json",
                        "id": attr_template_key,
                    },
                    raw={
                        "statPointCount": (attr_payload.get("stats") or {}).get("pointCount"),
                        "interpolated": (attr_payload.get("stats") or {}).get("interpolated"),
                        "damageScalars": attr_payload.get("damageScalars") or [],
                        "resilience": attr_payload.get("resilience") or [],
                    },
                )
                self.add_edge(
                    variant_id,
                    attr_template_id,
                    "uses_attribute_template",
                    confidence="direct",
                    evidence_source=source_table,
                    evidence_path=f"{source_key}.attrTemplateId",
                    raw=attr_template_key,
                )

            for field, kind, edge_type in (
                ("modelId", "model", "uses_model_id"),
                ("aiTemplateId", "ai_template", "uses_ai_template"),
            ):
                value = str(variant.get(field) or "").strip()
                if not value:
                    continue
                target_id = f"{kind}_ref:{value}"
                self.add_node(target_id, kind, value, key=value, semanticStatus=f"exact {field} reference")
                self.add_edge(
                    variant_id,
                    target_id,
                    edge_type,
                    confidence="direct",
                    evidence_source=source_table,
                    evidence_path=f"{source_key}.{field}",
                    raw=value,
                )

            for buff_index, buff_value in enumerate(variant.get("bornBuffs") or []):
                buff_key = str(buff_value).strip()
                if not buff_key:
                    continue
                buff_id = f"buff:{buff_key}"
                self.buff_ids.add(buff_key)
                self.add_node(buff_id, "buff", buff_key, key=buff_key)
                self.add_edge(
                    variant_id,
                    buff_id,
                    "starts_with_buff",
                    confidence="direct",
                    evidence_source=source_table,
                    evidence_path=f"{source_key}.bornBuffs[{buff_index}]",
                    raw=buff_key,
                )

        # Compatibility fallback for older Gameplay payloads that did not
        # retain variant rows.
        if not variants:
            for index, buff_value in enumerate(entry.get("bornBuffs") or []):
                key = str(buff_value).strip()
                if not key:
                    continue
                buff_id = f"buff:{key}"
                self.buff_ids.add(key)
                self.add_node(buff_id, "buff", key, key=key)
                self.add_edge(
                    enemy_id,
                    buff_id,
                    "starts_with_buff",
                    confidence="direct",
                    evidence_source="EnemyTable.json",
                    evidence_path=f"{entry.get('id')}.bornBuffs[{index}]",
                    raw=key,
                )

    def ability_entity_paths(self) -> list[Path]:
        paths: list[Path] = []
        for source in ("Persistent", "StreamingAssets"):
            directory = self.animestudio_root / source / "json_by_type" / "MonoBehaviour"
            if directory.is_dir():
                paths.extend(directory.glob("data_abilityentity*.json"))
        return sorted(paths, key=lambda path: path.as_posix().lower())

    def ability_entity_root_candidates(self, ability_key: str) -> list[str]:
        wrapped = f"_{ability_key.lower()}_"
        candidates = []
        for root_id in self.roots:
            root_key = root_id.split(":", 1)[-1].lower()
            if root_key and f"_{root_key}_" in wrapped:
                candidates.append(root_id)
        return sorted(candidates)

    def add_ability_entity_evidence(self) -> None:
        """Add the byte-proven AbilityEntity inherited prefix and RID links.

        The guarded opening and surrounding config are included; later fields
        remain excluded. Entity ownership is displayed only as an
        identifier-token inference, never as a runtime link.
        """
        seen_abilities: set[str] = set()
        seen_components: set[str] = set()
        paths = self.ability_entity_paths()
        self.ability_entity_files = len(paths)
        self.ability_entity_available = bool(paths)
        for path in paths:
            try:
                document = load_json(path)
            except (OSError, ValueError):
                continue
            relative_path = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
            references = ((document.get("references") or {}).get("RefIds") or []) if isinstance(document, dict) else []
            for reference in references:
                data = reference.get("data") if isinstance(reference, dict) else None
                if not isinstance(data, dict) or data.get("layout") != "Beyond.Gameplay.AbilityEntityTemplateData":
                    continue
                ability_key = str(data.get("id") or "").strip()
                if not ability_key or ability_key in seen_abilities:
                    continue
                seen_abilities.add(ability_key)
                self.ability_entity_records += 1
                base_template = data.get("baseTemplate") or {}
                entity_template = data.get("entityTemplate") or {}
                component_list = entity_template.get("componentList") or []
                ability_id = f"ability_entity:{ability_key}"
                exact_prefix = {
                    key: value
                    for key, value in {
                        "factionIndex": base_template.get("factionIndex"),
                        "gameplayTags": entity_template.get("gameplayTags") or [],
                        "delayToRecycleTime": entity_template.get("delayToRecycleTime"),
                        "delayRecyclePerformTime": entity_template.get("delayRecyclePerformTime"),
                        "sendDieEvent": entity_template.get("sendDieEvent"),
                        "enableBornFadeIn": entity_template.get("enableBornFadeIn"),
                        "fadeInTime": entity_template.get("fadeInTime"),
                    }.items()
                    if value not in (None, "", [], {})
                }
                ability_raw: dict[str, Any] = {"exactInheritedPrefix": exact_prefix}
                semantic_status = "exact inherited prefix; ability-specific tail unresolved"
                opening = data.get("abilityEntityOpening") or {}
                if isinstance(opening, dict) and opening.get("structuredDecodeStatus") == "decoded-prefix":
                    mirrored_fields = {
                        key: opening.get(key)
                        for key in ("maxStackingCnt", "maxStackingCntBB", "lifeType", "duration", "durationBB")
                        if opening.get(key) not in (None, "", [], {})
                    }
                    metadata_ordered_fields = {
                        key: opening.get(key)
                        for key in ("maxDurationForServer", "canMove", "moveHeight", "moveRadius", "moveType", "useFrameTick")
                        if opening.get(key) not in (None, "", [], {})
                    }
                    ability_raw["mirroredRootOpening"] = mirrored_fields
                    ability_raw["guardedMetadataOrderedOpening"] = metadata_ordered_fields
                    ability_raw["nextUnresolvedField"] = opening.get("nextFieldBoundary") or "surroundingConfig"
                    self.ability_entity_openings += 1
                    mirror = opening.get("rootComponentMirror") or {}
                    if isinstance(mirror, dict) and mirror.get("status") == "matched":
                        self.ability_entity_opening_mirrors += 1
                    semantic_status = "exact inherited prefix and mirrored opening; metadata-ordered scalars qualified; body unresolved from surroundingConfig"
                    surrounding = data.get("surroundingConfig") or {}
                    if isinstance(surrounding, dict) and surrounding.get("structuredDecodeStatus") == "decoded":
                        surrounding_raw = {
                            key: surrounding.get(key)
                            for key in (
                                "surroundingBase",
                                "mountPoint",
                                "rotationType",
                                "centerOffset",
                                "normalVector",
                                "radius",
                                "radiusBB",
                                "angleSpeed",
                                "angleSpeedBB",
                                "rotationClockwise",
                                "initAngleType",
                                "initAngle",
                                "initAngleBB",
                            )
                            if surrounding.get(key) not in (None, "", [], {})
                        }
                        surrounding_raw["offset"] = surrounding.get("offset")
                        surrounding_raw["consumedByteCount"] = surrounding.get("consumedByteCount")
                        surrounding_raw["nextFieldBoundary"] = surrounding.get("nextFieldBoundary")
                        surrounding_raw["surroundingMovementMirror"] = surrounding.get("surroundingMovementMirror")
                        surrounding_raw["nextBoundaryMirror"] = surrounding.get("nextBoundaryMirror")
                        ability_raw["guardedSurroundingConfig"] = {
                            key: value
                            for key, value in surrounding_raw.items()
                            if value not in (None, "", [], {})
                        }
                        ability_raw["nextUnresolvedField"] = surrounding.get("nextFieldBoundary") or "followMountPointConfig"
                        self.ability_entity_surrounding_configs += 1
                        surrounding_mirror = surrounding.get("surroundingMovementMirror") or {}
                        if isinstance(surrounding_mirror, dict) and surrounding_mirror.get("status") == "matched":
                            self.ability_entity_surrounding_mirrors += 1
                        boundary_mirror = surrounding.get("nextBoundaryMirror") or {}
                        if isinstance(boundary_mirror, dict) and boundary_mirror.get("status") == "matched":
                            self.ability_entity_next_boundary_mirrors += 1
                        semantic_status = "exact inherited prefix, mirrored opening, and byte-guarded surrounding config; metadata-order names and enum/hash meanings qualified; body unresolved from followMountPointConfig"
                self.add_node(
                    ability_id,
                    "ability_entity",
                    str(base_template.get("name") or ability_key),
                    key=ability_key,
                    semanticStatus=semantic_status,
                    source={"file": relative_path, "layout": data.get("layout")},
                    raw=ability_raw,
                )
                for index, component in enumerate(component_list):
                    if not isinstance(component, dict) or component.get("rid") is None:
                        continue
                    rid = str(component["rid"])
                    type_data = component.get("type") or {}
                    component_id = f"ability_component:{rid}"
                    component_label = str(type_data.get("class") or f"RID {rid}")
                    self.add_node(
                        component_id,
                        "ability_component",
                        component_label,
                        key=rid,
                        semanticStatus="exact managed-reference link",
                        raw={
                            key: value
                            for key, value in {
                                "class": type_data.get("class"),
                                "namespace": type_data.get("ns"),
                                "assembly": type_data.get("asm"),
                            }.items()
                            if value not in (None, "")
                        },
                    )
                    self.add_edge(
                        ability_id,
                        component_id,
                        "has_managed_component",
                        confidence="direct",
                        evidence_source="AnimeStudio AbilityEntityTemplateData prefix",
                        evidence_path=f"{relative_path}#entityTemplate.componentList[{index}]",
                        raw={"rid": component.get("rid"), "type": type_data},
                        note="RID and managed type are decoded from the byte-proven inherited prefix.",
                    )
                    seen_components.add(component_id)

                candidates = self.ability_entity_root_candidates(ability_key)
                if len(candidates) == 1:
                    root_id = candidates[0]
                    self.add_edge(
                        root_id,
                        ability_id,
                        "identifier_matches_ability_entity",
                        confidence="inferred",
                        evidence_source="AnimeStudio identifier match",
                        evidence_path="AbilityEntityTemplateData.id",
                        raw={"entityId": root_id.split(":", 1)[-1], "abilityEntityId": ability_key},
                        note="The complete character/enemy identifier is a delimited token in the ability-entity ID; runtime ownership is not proven.",
                    )
                    self.ability_entity_root_matches += 1
        self.ability_entity_components = len(seen_components)

    @staticmethod
    def managed_reference_rids(value: Any) -> set[int]:
        result: set[int] = set()
        if isinstance(value, dict):
            if isinstance(value.get("type"), dict) and isinstance(value.get("rid"), int) and value["rid"] > 0:
                result.add(value["rid"])
            for child in value.values():
                result.update(PayloadBuilder.managed_reference_rids(child))
        elif isinstance(value, list):
            for child in value:
                result.update(PayloadBuilder.managed_reference_rids(child))
        return result

    @staticmethod
    def find_layout(value: Any, layout: str, path: str = "data") -> list[tuple[str, dict[str, Any]]]:
        result: list[tuple[str, dict[str, Any]]] = []
        if isinstance(value, dict):
            if value.get("layout") == layout:
                result.append((path, value))
            for key, child in value.items():
                result.extend(PayloadBuilder.find_layout(child, layout, f"{path}.{key}"))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                result.extend(PayloadBuilder.find_layout(child, layout, f"{path}[{index}]"))
        return result

    @staticmethod
    def compact_target_settings(target: dict[str, Any]) -> dict[str, Any]:
        selector = target.get("selectorData") or {}
        direction = target.get("advancedDirection") or {}
        return {
            "target": {
                key: target.get(key)
                for key in (
                    "targetSource", "targetGroupKey", "selectorOwner", "ownerContextKey",
                    "centerType", "centerContextKey", "centerToGround",
                    "enableAdvancedDirection", "selectorDirection", "target", "targetContextKey",
                )
                if target.get(key) not in (None, "", [], {})
            },
            "selector": {
                key: selector.get(key)
                for key in ("finderDataRid", "validatorData", "postProcessorData")
                if selector.get(key) not in (None, "", [], {})
            },
            "direction": {
                key: direction.get(key)
                for key in (
                    "directionType", "source", "target", "sourceMountPoint", "targetMountPoint",
                    "customSourceAndTarget", "clampToXZ", "invertDirection",
                )
                if direction.get(key) not in (None, "", [], {})
            },
        }

    def add_selector_link(
        self,
        target_id: str,
        link: Any,
        relation: str,
        evidence_path: str,
    ) -> None:
        if not isinstance(link, dict) or not isinstance(link.get("rid"), int) or link["rid"] <= 0:
            return
        type_data = link.get("type") or {}
        rid = str(link["rid"])
        component_id = f"selector_component:{rid}"
        self.add_node(
            component_id,
            "selector_component",
            str(type_data.get("class") or f"RID {rid}"),
            key=rid,
            semanticStatus="exact managed-reference link; runtime behavior not inferred",
            raw={
                key: value
                for key, value in {
                    "class": type_data.get("class"),
                    "namespace": type_data.get("ns"),
                    "assembly": type_data.get("asm"),
                }.items()
                if value not in (None, "")
            },
        )
        self.add_edge(
            target_id,
            component_id,
            relation,
            confidence="direct",
            evidence_source="AnimeStudio TargetSettings managed-reference link",
            evidence_path=evidence_path,
            raw={"rid": link["rid"], "type": type_data},
        )
        self.target_selector_links += 1

    def add_character_target_settings(self) -> None:
        paths: list[Path] = []
        for source in ("Persistent", "StreamingAssets"):
            directory = self.animestudio_root / source / "json_by_type" / "MonoBehaviour"
            if directory.is_dir():
                paths.extend(directory.glob("data_chr_*.json"))
        paths = sorted(paths, key=lambda path: path.as_posix().lower())
        self.target_settings_files = len(paths)
        self.target_settings_available = bool(paths)
        for path in paths:
            try:
                document = load_json(path)
            except (OSError, ValueError):
                continue
            references = ((document.get("references") or {}).get("RefIds") or []) if isinstance(document, dict) else []
            refs_by_rid = {
                reference["rid"]: reference
                for reference in references
                if isinstance(reference, dict) and isinstance(reference.get("rid"), int)
            }
            template = next(
                (
                    reference.get("data")
                    for reference in references
                    if isinstance(reference, dict)
                    and isinstance(reference.get("data"), dict)
                    and reference["data"].get("layout") == "Beyond.Gameplay.CharacterTemplateData"
                ),
                None,
            )
            if not isinstance(template, dict):
                continue
            character_key = str(template.get("id") or "").strip()
            root_id = f"character:{character_key}"
            reachable: set[int] = set()
            pending = deque(sorted(self.managed_reference_rids((template.get("entityTemplate") or {}).get("componentList") or [])))
            while pending:
                rid = pending.popleft()
                if rid in reachable or rid not in refs_by_rid:
                    continue
                reachable.add(rid)
                data = refs_by_rid[rid].get("data")
                for linked_rid in sorted(self.managed_reference_rids(data)):
                    if linked_rid not in reachable:
                        pending.append(linked_rid)

            relative_path = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()
            for rid, reference in sorted(refs_by_rid.items()):
                owner_data = reference.get("data")
                owner_type = reference.get("type") or {}
                targets = self.find_layout(owner_data, "Beyond.Gameplay.Core.TargetSettings")
                self.target_settings_records += len(targets)
                if root_id not in self.nodes or rid not in reachable:
                    continue
                for index, (target_path, target) in enumerate(targets):
                    if target.get("structuredDecodeStatus") != "decoded" or target.get("consumedByteCount") != target.get("length"):
                        continue
                    target_id = f"target_settings:{character_key}:{rid}:{index}"
                    owner_class = str(owner_type.get("class") or f"RID {rid}")
                    self.add_node(
                        target_id,
                        "target_settings",
                        f"{owner_class} · {target_path.rsplit('.', 1)[-1]}",
                        key=f"{character_key}:{rid}:{index}",
                        semanticStatus="exact byte structure; enum/hash names and runtime evaluator behavior remain qualified",
                        source={"file": relative_path, "ownerRid": rid, "ownerClass": owner_class, "path": target_path},
                        raw=self.compact_target_settings(target),
                    )
                    self.add_edge(
                        root_id,
                        target_id,
                        "has_target_settings",
                        confidence="direct",
                        evidence_source="AnimeStudio CharacterTemplateData RID reachability",
                        evidence_path=f"{relative_path}#rid={rid}/{target_path}",
                        raw={"ownerClass": owner_class, "consumedBytes": target.get("consumedByteCount")},
                        note="The owner RID is reachable from the exact CharacterTemplateData component list; evaluator order is not inferred.",
                    )
                    self.target_settings_attached += 1
                    selector = target.get("selectorData") or {}
                    self.add_selector_link(target_id, selector.get("finderDataRid"), "uses_target_finder", f"{target_path}.selectorData.finderDataRid")
                    for link_index, link in enumerate(selector.get("validatorData") or []):
                        self.add_selector_link(target_id, link, "uses_target_validator", f"{target_path}.selectorData.validatorData[{link_index}]")
                    for link_index, link in enumerate(selector.get("postProcessorData") or []):
                        self.add_selector_link(target_id, link, "uses_target_post_processor", f"{target_path}.selectorData.postProcessorData[{link_index}]")

    def open_graph(self) -> bool:
        if self.graph_stale_reason:
            return False
        if not self.graph_path.is_file():
            return False
        try:
            self.graph = sqlite3.connect(f"file:{self.graph_path.as_posix()}?mode=ro", uri=True)
            self.graph.execute("SELECT 1 FROM nodes LIMIT 1").fetchone()
            return True
        except sqlite3.Error:
            if self.graph is not None:
                self.graph.close()
            self.graph = None
            return False

    def graph_node(self, node_id: str) -> dict[str, Any] | None:
        if self.graph is None:
            return None
        row = self.graph.execute(
            "SELECT id, kind, name, source, path, data FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            return None
        raw = graph_json(row[5])
        values: dict[str, Any] = {
            "graphKind": row[1],
            "source": row[3],
            "path": row[4],
        }
        if isinstance(raw, dict):
            kept = {
                key: raw[key]
                for key in ("configPath", "dataPath", "domain", "fields", "path", "pid", "size", "type")
                if key in raw
            }
            if kept:
                values["raw"] = kept
        return {"id": row[0], "kind": row[1], "label": row[2] or row[0].split(":", 1)[-1], **values, "_graphData": raw}

    def merge_graph_node(self, node_id: str) -> dict[str, Any] | None:
        node = self.graph_node(node_id)
        if node is None:
            return None
        data = node.pop("_graphData", None)
        display_kind = str(node.pop("kind"))
        if display_kind == "gameplay_skill":
            display_kind = "ability"
        elif display_kind == "gameplay_effect" and PROJECTILE_TOKEN_RE.search(str(node.get("label") or "")):
            node["classification"] = {
                "confidence": "inferred",
                "basis": "identifier contains projectile, bullet, or missile",
                "graphKind": display_kind,
            }
        self.add_node(node_id, display_kind, str(node.pop("label")), **node)
        return data if isinstance(data, dict) else None

    def add_selector_summary(self, skill_id: str, graph_data: dict[str, Any] | None) -> None:
        if not graph_data:
            return
        sample = str(graph_data.get("sample") or "")
        counts = {name: int(value) for name, value in SELECTOR_COUNT_RE.findall(sample)}
        counts = {name: value for name, value in counts.items() if value > 0}
        if not counts:
            return
        selector_id = f"selector_summary:{skill_id.split(':', 1)[-1]}"
        self.add_node(
            selector_id,
            "selector",
            "Selector fields",
            semanticStatus="field-presence-only",
            raw=counts,
        )
        self.add_edge(
            skill_id,
            selector_id,
            "has_selector_fields",
            confidence="direct",
            evidence_source="webui/game_data",
            evidence_path=str(graph_data.get("dataPath") or graph_data.get("path") or "SkillData summary"),
            raw=counts,
            note="Decoded field counts only; target-selection behavior is not inferred.",
        )

    def add_graph_edge(self, row: tuple[Any, ...]) -> None:
        source, target, edge_type, evidence_source, evidence_path, raw_json = row
        edge_type = str(edge_type)
        if edge_type in GRAPH_EDGE_TYPES:
            self.graph_edge_contract_accepted[edge_type] = (
                self.graph_edge_contract_accepted.get(edge_type, 0) + 1
            )
        self.merge_graph_node(str(target))
        if str(target).startswith("buff:"):
            self.buff_ids.add(str(target).split(":", 1)[1])
        elif str(target).startswith("gameplay_effect:"):
            self.effect_ids.add(str(target).split(":", 1)[1])
        confidence = "inferred" if edge_type in INFERRED_GRAPH_EDGE_TYPES else "direct"
        self.add_edge(
            str(source),
            str(target),
            str(edge_type),
            confidence=confidence,
            evidence_source=str(evidence_source or "source_graph"),
            evidence_path=str(evidence_path or ""),
            raw=graph_json(raw_json),
        )

    def add_inferred_projectile_effects(self) -> None:
        """Attach projectile-looking effects when a stable entity token matches.

        The effect node and its name are direct graph facts.  Ownership is only
        an identifier-token inference, so these edges are never promoted to
        direct confidence.
        """
        if self.graph is None:
            return
        candidates = list(self.graph.execute(
            "SELECT id, name FROM nodes WHERE kind = 'gameplay_effect' "
            "AND (lower(name) LIKE '%projectile%' OR lower(name) LIKE '%bullet%' OR lower(name) LIKE '%missile%') "
            "ORDER BY name, id"
        ))
        for root_id in sorted(self.roots):
            entity_key = root_id.split(":", 1)[-1]
            tokens = [token.lower() for token in entity_key.split("_")[2:] if len(token) >= 4]
            if not tokens:
                continue
            for effect_id, effect_name in candidates:
                lowered = str(effect_name or "").lower()
                matched = next((token for token in tokens if token in lowered), "")
                if not matched:
                    continue
                self.merge_graph_node(str(effect_id))
                self.effect_ids.add(str(effect_id).split(":", 1)[-1])
                self.add_edge(
                    root_id,
                    str(effect_id),
                    "identifier_matches_projectile_effect",
                    confidence="inferred",
                    evidence_source="source_graph identifier match",
                    evidence_path="gameplay_effect.name",
                    raw={"entityToken": matched, "effectName": effect_name},
                    note="Shared identifier token suggests ownership; runtime linkage is not proven.",
                )

    def enrich_graph(self) -> bool:
        if not self.open_graph():
            return False
        self.inspect_graph_edge_contract()

        for skill_key in sorted(self.skill_ids):
            skill_id = f"gameplay_skill:{skill_key}"
            graph_data = self.merge_graph_node(skill_id)
            self.add_selector_summary(skill_id, graph_data)
            rows = self.graph.execute(
                "SELECT src, dst, kind, source, evidence, data FROM edges WHERE src = ? ORDER BY kind, dst, source, evidence",
                (skill_id,),
            )
            for row in rows:
                self.inspect_graph_edge_row(row)
                if row[2] == "skill_data_has_param_string" and not str(row[1]).startswith("skill_parameter:projectile_"):
                    continue
                if row[2] in GRAPH_EDGE_TYPES:
                    self.add_graph_edge(row)

        pending = deque(sorted(self.buff_ids))
        seen_buffs: set[str] = set()
        while pending:
            buff_key = pending.popleft()
            if buff_key in seen_buffs:
                continue
            seen_buffs.add(buff_key)
            buff_id = f"buff:{buff_key}"
            self.merge_graph_node(buff_id)
            rows = list(self.graph.execute(
                "SELECT src, dst, kind, source, evidence, data FROM edges WHERE src = ? ORDER BY kind, dst, source, evidence",
                (buff_id,),
            ))
            before = set(self.buff_ids)
            for row in rows:
                self.inspect_graph_edge_row(row)
                if row[2] in GRAPH_EDGE_TYPES:
                    self.add_graph_edge(row)
            for discovered in sorted(self.buff_ids - before):
                if discovered not in seen_buffs:
                    pending.append(discovered)

        self.add_inferred_projectile_effects()

        for effect_key in sorted(self.effect_ids):
            effect_id = f"gameplay_effect:{effect_key}"
            self.merge_graph_node(effect_id)
            rows = list(self.graph.execute(
                "SELECT src, dst, kind, source, evidence, data FROM edges WHERE src = ? AND kind = 'effect_name_matches_export_base_asset' ORDER BY dst LIMIT ?",
                (effect_id, self.max_assets_per_effect),
            ))
            for row in rows:
                self.add_graph_edge(row)

        for root_id in sorted(self.roots):
            rows = list(self.graph.execute(
                "SELECT dst, src, kind, source, evidence, data FROM edges WHERE dst = ? AND kind = 'asset_used_by_gameplay' ORDER BY "
                "CASE WHEN lower(src) LIKE '%icon_%' THEN 0 WHEN lower(src) LIKE '%.fbx' THEN 1 ELSE 2 END, src LIMIT ?",
                (root_id, self.max_assets_per_entity),
            ))
            for source, target, edge_type, evidence_source, evidence_path, raw_json in rows:
                self.merge_graph_node(str(target))
                self.add_edge(
                    root_id,
                    str(target),
                    "has_representative_asset",
                    confidence="inferred",
                    evidence_source=str(evidence_source or "source_graph"),
                    evidence_path=str(evidence_path or ""),
                    raw=graph_json(raw_json),
                    note=f"Source graph edge {edge_type} was reversed for entity-centric display.",
                )
        return True

    def build_root_index(self, edges: list[dict[str, Any]]) -> dict[str, list[int]]:
        outgoing: dict[str, list[int]] = defaultdict(list)
        for index, edge in enumerate(edges):
            outgoing[str(edge["source"])].append(index)
        result: dict[str, list[int]] = {}
        for root in sorted(self.roots):
            queue: deque[tuple[str, int]] = deque([(root, 0)])
            seen_nodes = {root}
            selected: set[int] = set()
            while queue:
                current, depth = queue.popleft()
                if depth >= 4:
                    continue
                for edge_index in outgoing.get(current, []):
                    selected.add(edge_index)
                    target = str(edges[edge_index]["target"])
                    if target not in seen_nodes:
                        seen_nodes.add(target)
                        queue.append((target, depth + 1))
            result[root] = sorted(selected)
        return result

    def payload(self) -> dict[str, Any]:
        self.add_authored_gameplay()
        self.add_ability_entity_evidence()
        self.add_character_target_settings()
        graph_available = self.enrich_graph()
        if self.graph is not None:
            self.graph.close()
            self.graph = None
        nodes = sorted(self.nodes.values(), key=node_sort_key)
        edges = sorted(self.edges.values(), key=edge_sort_key)
        kind_counts: dict[str, int] = defaultdict(int)
        confidence_counts: dict[str, int] = defaultdict(int)
        for node in nodes:
            kind_counts[str(node["kind"])] += 1
        for edge in edges:
            confidence_counts[str(edge["confidence"])] += 1
        return {
            "schemaVersion": SCHEMA_VERSION,
            "language": self.language,
            "scope": {
                "roots": ["character", "enemy"],
                "runtimeFormulaClaimed": False,
                "note": "Authored values and reference evidence only; relationships do not reconstruct final runtime combat formulas or target evaluator order.",
            },
            "graph": {
                "available": graph_available,
                "source": "reports/source_graph/endfield_source_graph.sqlite" if graph_available else None,
                "degradedMode": not graph_available,
                "stale": bool(self.graph_stale_reason),
                "staleReason": self.graph_stale_reason or None,
            },
            "abilityEntityEvidence": {
                "available": self.ability_entity_available,
                "source": "export_full/recovered/AnimeStudio-cli/*/json_by_type/MonoBehaviour/data_abilityentity*.json" if self.ability_entity_available else None,
                "files": self.ability_entity_files,
                "records": self.ability_entity_records,
                "components": self.ability_entity_components,
                "guardedOpenings": self.ability_entity_openings,
                "matchedRootComponentMirrors": self.ability_entity_opening_mirrors,
                "guardedSurroundingConfigs": self.ability_entity_surrounding_configs,
                "matchedSurroundingMovementMirrors": self.ability_entity_surrounding_mirrors,
                "matchedNextBoundaryMirrors": self.ability_entity_next_boundary_mirrors,
                "inferredRootMatches": self.ability_entity_root_matches,
                "surroundingConfigIncluded": self.ability_entity_surrounding_configs > 0,
                "remainingTailIncluded": False,
                "excludedFromField": "followMountPointConfig",
                "note": "The byte-proven inherited prefix and managed-component RID list are shown. The mirrored opening through useFrameTick and exact 92-byte surroundingConfig are included when guarded; metadata-order names plus enum/hash meanings remain qualified. Bytes from followMountPointConfig onward remain excluded.",
            },
            "targetSettingsEvidence": {
                "available": self.target_settings_available,
                "source": "export_full/recovered/AnimeStudio-cli/*/json_by_type/MonoBehaviour/data_chr_*.json" if self.target_settings_available else None,
                "files": self.target_settings_files,
                "records": self.target_settings_records,
                "attachedToGameplayRoots": self.target_settings_attached,
                "unattachedRecords": self.target_settings_records - self.target_settings_attached,
                "managedSelectorLinks": self.target_selector_links,
                "note": "Only exact-consumed TargetSettings reachable from curated character roots are displayed. Enum/hash names and runtime evaluator order remain unclaimed; avatar-template records without Gameplay roots are counted but not assigned.",
            },
            "graphEdgeContract": {
                "scope": "reachable_skill_buff_config_edges",
                "status": (
                    "unavailable"
                    if not graph_available
                    else "partial"
                    if self.graph_edge_contract_unexpected
                    or any(
                        self.graph_edge_contract_accepted.get(kind, 0) == 0
                        for kind in sorted(GRAPH_EDGE_TYPES)
                    )
                    else "validated"
                ),
                "expectedKinds": {
                    kind: {
                        "observed": self.graph_edge_contract_observed.get(kind, 0),
                        "accepted": self.graph_edge_contract_accepted.get(kind, 0),
                        "status": (
                            "accepted"
                            if self.graph_edge_contract_accepted.get(kind, 0)
                            else "observed-only"
                            if self.graph_edge_contract_observed.get(kind, 0)
                            else "missing"
                        ),
                    }
                    for kind in sorted(GRAPH_EDGE_TYPES)
                },
                "unexpectedKindCount": len(self.graph_edge_contract_unexpected),
                "unexpectedEdgeCount": sum(self.graph_edge_contract_unexpected.values()),
                "unexpectedKinds": dict(sorted(self.graph_edge_contract_unexpected.items())),
                "note": (
                    "Expected SkillData/BuffData string-scan edge kinds are accepted only as inferred candidates. "
                    "Known definition/tag/icon/unused-param kinds and unrelated graph domains are outside this "
                    "consumer contract; unknown SkillData/BuffData kinds are reported and never promoted."
                ),
            },
            "counts": {
                "roots": len(self.roots),
                "nodes": len(nodes),
                "edges": len(edges),
                "nodeKinds": dict(sorted(kind_counts.items())),
                "confidence": dict(sorted(confidence_counts.items())),
            },
            "roots": sorted(self.roots),
            "nodes": nodes,
            "edges": edges,
            "rootEdges": self.build_root_index(edges),
        }


def build_language(args: argparse.Namespace, language: str) -> tuple[Path, dict[str, Any]]:
    language = language.upper()
    input_path = args.data_root / language / "gameplay" / "index.json"
    if not input_path.is_file():
        raise FileNotFoundError(f"Gameplay input not found: {input_path}")
    gameplay = load_json(input_path)
    freshness_inputs = [input_path, args.data_root.parent / "manifest.json", ROOT / "webui" / "data" / "assets" / "index.json"]
    for source in ("Persistent", "StreamingAssets"):
        directory = args.animestudio_root / source / "json_by_type" / "MonoBehaviour"
        if directory.is_dir():
            freshness_inputs.extend(directory.glob("data_abilityentity*.json"))
            freshness_inputs.extend(directory.glob("data_chr_*.json"))
    existing_inputs = [path for path in freshness_inputs if path.is_file()]
    graph_stale_reason = ""
    if args.graph.is_file() and existing_inputs:
        newest_input = max(existing_inputs, key=lambda path: path.stat().st_mtime_ns)
        if newest_input.stat().st_mtime_ns > args.graph.stat().st_mtime_ns:
            display_path = newest_input.relative_to(ROOT).as_posix() if newest_input.is_relative_to(ROOT) else newest_input.as_posix()
            graph_stale_reason = f"source graph predates {display_path}; rebuild tools/endfield_source_graph.py before using graph edges"
    builder = PayloadBuilder(
        language,
        gameplay,
        args.graph,
        graph_stale_reason,
        args.animestudio_root,
        args.max_assets_per_entity,
        args.max_assets_per_effect,
    )
    payload = builder.payload()
    output_path = args.data_root / language / "gameplay" / "combat_relationships.json"
    write_json(output_path, payload)
    return output_path, payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for language in args.languages:
        output_path, payload = build_language(args, language)
        graph_mode = "source graph" if payload["graph"]["available"] else ("degraded (stale source graph)" if payload["graph"].get("stale") else "degraded (no source graph)")
        print(
            f"{language.upper()}: {payload['counts']['roots']} roots, "
            f"{payload['counts']['nodes']} nodes, {payload['counts']['edges']} edges, "
            f"{graph_mode} -> {output_path.relative_to(ROOT)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
