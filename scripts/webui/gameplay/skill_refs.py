"""Publish authored SkillData relationships from the last current Data publication.

Run through ``build_gameplay --stage skill-refs``. This consumes Data; it never
builds it, decodes native formats, or claims that an authored action executed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.common import (
    EXPORT_LAYOUT, GLOBAL_METADATA_REL, check_installed_native_inputs,
    resolve_installed_game_data_root,
)
from scripts.game_data.unity_store import UnityObjectStore, UnityStoreError
from scripts.repo_paths import REPO_ROOT
from scripts.webui.data_inspector.contract import json_safe
from scripts.webui.data_inspector.publication import load_dataset

SCHEMA = "endfield.webui.skill-references.v1"
BOUNDARY = (
    "Stored named action references and frame windows from fully consumed SkillData. "
    "They do not establish runtime execution, final damage or branch order. Nested "
    "paths retain their authored context; frames are not converted to seconds. "
    "Buff source presence does not validate its interior; anonymous values remain structural-only."
)
# Named union fields, not suffix/name heuristics. Blackboard keys are deliberately
# absent: projectileIDKey, buffIdKey and skillBBKey do not identify static targets.
REFERENCE_FIELDS = {
    "CreateBuffAction+Data": {"buffId": "buff"},
    "AuraAction+Data": {"buffId": "buff"},
    "AbilityActions.FinishBuffAction+Data": {"buffId": "buff"},
    "Conditions.CheckBuffStackNum+Data": {"buffId": "buff"},
    "Conditions.CheckBuffIdInContext+Data": {"buffId": "buff"},
    "InheritBuffAction+Data": {"targetBuffId": "buff"},
    "CreateBuffAttachingSkill+Data": {"buffId": "buff"},
    "CheckGlobalCDTimerAction+Data": {"buffId": "buff"},
    "AddGlobalCDTimer+Data": {"buffId": "buff"},
    "Selector+SmartTargetFinder+Data": {"buffId": "buff"},
    "GetTargetBuffBBAction+Data": {"buffId": "buff"},
    "SaveBuffStackNum+Data": {"buffId": "buff"},
    "SpawnAbilityEntity+Data": {"abilityEntitySkillId": "skill"},
    "LaunchProjectile+Data": {
        "projectileId": "projectile", "projectileSkillId": "skill",
        "skillIdOnBlock": "skill", "skillIdOnFinish": "skill", "skillIdOnReach": "skill",
    },
    "ComboCacheAction+Data": {"skillId": "skill"},
    "ChangeSkillAction+Data": {"revertedSkillId": "skill", "targetSkillId": "skill"},
    "SetSkillCdAtOnce+Data": {"skillId": "skill"},
    "AllowNextSkillAction+Data": {"allowedSkillIdList": "skill"},
}
REFERENCE_FIELDS = {"Beyond.Gameplay.Core." + key: value for key, value in REFERENCE_FIELDS.items()}
PROJECTILE_SKILL_FIELDS = (
    "activeSkillIds", "passiveSkillIds", "normalAttackIds", "normalAttackList",
    "enabledBreakingNormalAttacks", "enabledPassiveSkills",
    "normalSkillId", "ultimateSkillId", "plungingAttackStartId", "plungingAttackEndId",
    "dodgeSkillId", "comboSkillId",
)


def native_diagnostic(recorded: dict[str, Any], export_root: Path,
                      game_root: Path | None) -> str:
    """Authenticate the publication's native pair against the selected installation."""
    selected = recorded.get("selectedNative") or {}
    if not isinstance(selected, dict):
        return "SkillData selectedNative: object expected."
    if selected.get("nativeStatus") != "validated" or selected.get("planStatus") != "validated":
        return "SkillData publication has no validated selected-native wrapper plan."
    if any(re.fullmatch(r"[0-9a-fA-F]{64}", str(selected.get(key) or "")) is None
           for key in ("gameAssemblySha256", "metadataSha256")):
        return "SkillData publication native input hashes are missing or invalid."
    if game_root is None:
        if export_root.resolve() != EXPORT_LAYOUT.root.resolve():
            return "Alternate export requires --game-root to authenticate SkillData."
        game_root = resolve_installed_game_data_root()
    gate = check_installed_native_inputs(
        selected["gameAssemblySha256"], selected["metadataSha256"],
        gameassembly=game_root.parent / "GameAssembly.dll", metadata=game_root / GLOBAL_METADATA_REL,
    )
    return "" if gate.validated else f"Selected SkillData native inputs {gate.status}: {gate.detail}"


def project_skill(record: dict[str, Any]) -> dict[str, Any]:
    """Project only named unions from a whole-file exact, identifier-matched record."""
    facts = record.get("facts") or {}
    payload = record.get("payload") or {}
    if not isinstance(facts, dict) or not isinstance(payload, dict):
        raise ValueError("SkillData facts/payload: objects expected")
    if (record.get("status") != "structural_only" or facts.get("wholeFileCursorExact") is not True
            or facts.get("identifierMatchesFilename") is not True):
        raise ValueError("SkillData record lacks whole-file cursor/identifier proof")
    skill_id = payload.get("skillId")
    if not isinstance(skill_id, str) or not skill_id or skill_id != Path(record["source"]["path"]).stem:
        raise ValueError("SkillData skillId does not match its source filename")
    nodes: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    visited = 0

    def walk(value: Any, path: str, window: dict[str, Any] | None = None,
             parent: str = "", depth: int = 0) -> None:
        nonlocal visited
        visited += 1
        if depth > 64 or visited > 250_000:
            raise ValueError("SkillData projection traversal limit exceeded")
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", window, parent, depth + 1)
            return
        if not isinstance(value, dict):
            return
        if "_startFrame" in value and "_endFrame" in value:
            window = {"startFrame": value["_startFrame"], "endFrame": value["_endFrame"], "path": path}
        type_name = value.get("$type")
        fields = value.get("$value")
        if isinstance(type_name, str) and isinstance(fields, dict):
            ref_fields = REFERENCE_FIELDS.get(type_name, {})
            own_refs = []
            for field, kind in ref_fields.items():
                candidates = fields.get(field)
                candidates = candidates if isinstance(candidates, list) else [candidates]
                for target in candidates:
                    if isinstance(target, str) and target:
                        ref = {"kind": kind, "target": target, "field": field, "path": path, "type": type_name}
                        references.append(ref)
                        own_refs.append(ref)
            # CreateBuffAction stores its static targets in named `buffs`
            # items too. A runtime-key selection must not link the fallback ID.
            if type_name == "Beyond.Gameplay.Core.CreateBuffAction+Data":
                for index, buff in enumerate(fields.get("buffs") or []):
                    if not isinstance(buff, dict) or buff.get("readIdFromBlackboard") is not False:
                        continue
                    target = buff.get("buffId")
                    if isinstance(target, str) and target:
                        ref = {"kind": "buff", "target": target, "field": f"buffs[{index}].buffId",
                               "path": path, "type": type_name}
                        references.append(ref)
                        own_refs.append(ref)
            is_action = "serverActionIndex" in fields
            if is_action or own_refs:
                params = {key: item for key, item in fields.items()
                          if isinstance(item, (str, int, float, bool)) and key not in ref_fields}
                # Preserve explicitly named value operands for presentation.
                # This is a stored value, not an evaluated blackboard lookup.
                operands = {key: {name: item[name] for name in
                            ("blackboardKey", "useBlackboardKey", "value", "useCustomValue") if name in item}
                            for key, item in fields.items() if isinstance(item, dict)
                            and isinstance(item.get("useBlackboardKey"), bool)
                            and isinstance(item.get("value"), (str, int, float, bool))}
                nodes.append({"path": path, "type": type_name, "tag": value.get("$tag"),
                              "kind": "action" if is_action else "reference-context",
                              "parent": parent, "window": window, "parameters": params,
                              "operands": operands, "references": own_refs})
                parent = path
        for key, child in value.items():
            walk(child, f"{path}.{key}" if path else key, window, parent, depth + 1)

    walk(payload, "")
    return {"id": skill_id, "recordId": record["id"], "source": record["source"],
            "status": "structural_only", "nodes": nodes, "references": references,
            "actionCount": sum(node["kind"] == "action" for node in nodes)}


def projectile_targets(path: Path, export_root: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Use only last-published projectiles whose exported source bytes still match."""
    targets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    audit: dict[str, Any] = {"datasetId": "gameplay-projectiles", "status": "unavailable"}
    try:
        publication = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(publication, dict) or publication.get("schemaVersion") != 5:
            raise ValueError("Projectile publication schema is unsupported")
        entries = publication.get("entries")
        if not isinstance(entries, list) or any(not isinstance(row, dict) for row in entries):
            raise ValueError("Projectile entries: object list expected")
        with UnityObjectStore(export_root / "game/Unity.sqlite") as store:
            for row in entries:
                source = row.get("source") or {}
                name = Path(source.get("jsonPath") or "").name
                if source.get("root") != "MonoBehaviour" or not name:
                    raise ValueError(f"Projectile source identity missing: {row.get('id')}")
                document = store.read_json("MonoBehaviour", name)
                metadata = document.get("$animestudio") or {}
                digest = source.get("rawDataSha256")
                if (re.fullmatch(r"[0-9a-fA-F]{64}", str(digest or "")) is None
                        or digest != metadata.get("rawDataSha256")
                        or str(source.get("pathId")) != str(metadata.get("pathId"))
                        or not row.get("confidence", {}).get("byteComplete")):
                    raise ValueError(f"Projectile publication is stale: {row.get('id')}")
                template = row.get("template") or {}
                targets[row["id"]].append({"id": row["id"], "source": {"store": "unity", "group": "MonoBehaviour", "name": name},
                    "lifetime": row.get("lifetime"), "collision": row.get("collision"),
                    "skills": {key: template[key] for key in PROJECTILE_SKILL_FIELDS if key in template}})
        audit.update(status="current", recordCount=sum(map(len, targets.values())),
                     publicationSha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnityStoreError) as exc:
        targets.clear()
        audit["diagnostic"] = str(exc)[:600]
    return dict(targets), audit


def resolve_reference(reference: dict[str, Any], skills: dict[str, list[dict[str, Any]]],
                      buffs: dict[str, list[str]], projectiles: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    kind, target = reference["kind"], reference["target"]
    candidates = {"skill": skills, "buff": buffs, "projectile": projectiles}[kind].get(target, [])
    result = {**reference, "resolution": "missing" if not candidates else "ambiguous" if len(candidates) != 1 else "exact_id"}
    if len(candidates) == 1:
        if kind == "buff":
            result.update(resolution="source_only", sourcePath=candidates[0])
        elif kind == "skill":
            result["recordId"] = candidates[0]["recordId"]
    return result


def build(data_root: Path, export_root: Path, game_root: Path | None = None) -> dict[str, Any]:
    records, audit = load_dataset(data_root / "data_inspector", export_root, "skill-data", "game/Json/SkillData",
        signature_check=lambda recorded: native_diagnostic(recorded, export_root, game_root))
    projected = []
    rejected = []
    for record in records:
        try:
            projected.append(project_skill(record))
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append({"recordId": record.get("id"), "diagnostic": str(exc)[:300]})
    skills: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in projected:
        skills[row["id"]].append(row)
    buffs: dict[str, list[str]] = defaultdict(list)
    for path in sorted((export_root / "game/Json/BuffData").rglob("*.json")):
        buffs[path.stem].append(path.relative_to(export_root).as_posix())
    projectiles, projectile_audit = projectile_targets(data_root / "gameplay/projectiles.json", export_root)
    output = data_root / "gameplay/skill_refs"
    output.mkdir(parents=True, exist_ok=True)
    catalog = []
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()
    for row in projected:
        for node in row["nodes"]:
            node["references"] = [resolve_reference(ref, skills, buffs, projectiles) for ref in node["references"]]
        row["references"] = [ref for node in row["nodes"] for ref in node["references"]]
        for ref in row["references"]:
            counts[ref["kind"]] += 1
            counts["resolution:" + ref["resolution"]] += 1
            if ref["kind"] == "skill" and ref["resolution"] == "exact_id":
                incoming[ref["target"]].append({"id": row["id"], "field": ref["field"], "path": ref["path"]})
    for row in projected:
        row["incoming"] = incoming.get(row["id"], [])
        filename = hashlib.sha256(row["recordId"].encode("utf-8")).hexdigest()[:24] + ".json"
        row["schema"] = SCHEMA
        (output / filename).write_text(json.dumps(json_safe(row), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        catalog.append({"id": row["id"], "recordId": row["recordId"], "path": filename,
                        "actions": row["actionCount"], "references": len(row["references"]),
                        "targets": sorted({ref["target"] for ref in row["references"]}),
                        "kinds": sorted({ref["kind"] for ref in row["references"]})})
    index = {"schema": SCHEMA, "boundary": BOUNDARY, "status": audit["status"],
             "sources": [audit, projectile_audit], "records": catalog, "rejected": rejected,
             "counts": dict(counts), "projectiles": projectiles}
    (output / "index.json").write_text(json.dumps(json_safe(index), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "webui/data")
    parser.add_argument("--export-root", type=Path, default=EXPORT_LAYOUT.root)
    parser.add_argument("--game-root", type=Path, help="Explicit selected Endfield_Data directory; required for alternate exports.")
    args = parser.parse_args(argv)
    result = build(args.data_root, args.export_root, args.game_root)
    print(f"Skill references: {len(result['records']):,} records; status {result['status']}; {len(result['rejected'])} rejected")
    for audit in result["sources"]:
        if audit["status"] != "current":
            print(f"  {audit['datasetId']}: {audit.get('diagnostic', audit['status'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
