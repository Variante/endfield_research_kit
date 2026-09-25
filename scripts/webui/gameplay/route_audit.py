"""Summarize exact character DamageUnit branch rows from built Gameplay data."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.repo_paths import REPO_ROOT


DEFAULT_INDEX = REPO_ROOT / "webui/data/lang/CN/gameplay/index.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/game_data/character_damage_routes.json"
SCHEMA = "endfield.character-damage-route-audit.v3"


def summarize(index: dict[str, Any], *, input_sha256: str) -> dict[str, Any]:
    if ((index.get("skillDamageEvidence") or {}).get("status") != "validated"
            or (index.get("skillDamageRouteEvidence") or {}).get("status") != "validated"
            or (index.get("skillDamagePoiseRouteEvidence") or {}).get("status") != "validated"
            or (index.get("skillDamageDefiniteValueEvidence") or {}).get("status") != "validated"):
        raise ValueError("selected damage plan or native route is not validated")
    catalog = index.get("skillDamageUnits")
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError("missing SkillData damage catalog")
    counts: Counter[tuple[bool, bool, str | None]] = Counter()
    attribute_counts: Counter[tuple[bool, bool, str | None, str]] = Counter()
    examples: dict[tuple[bool, bool, str | None], list[str]] = {}
    poise_counts: Counter[tuple[str | None, bool | None, str]] = Counter()
    poise_examples: dict[tuple[str | None, bool | None, str], list[str]] = {}
    total = 0
    for skill_id, record in sorted(catalog.items()):
        if not isinstance(record, dict) or record.get("status") != "exact":
            raise ValueError(f"non-exact SkillData row: {skill_id}")
        units = record.get("units")
        if not isinstance(units, list):
            raise ValueError(f"missing units: {skill_id}")
        for unit in units:
            if not isinstance(unit, dict):
                raise ValueError(f"invalid DamageUnit: {skill_id}")
            simple = unit.get("simpleCalculation")
            snapshot = unit.get("takeAtkSnapshot")
            if type(simple) is not bool or type(snapshot) is not bool:
                raise ValueError(f"missing route flags: {skill_id}")
            calculation = unit.get("atkCalculation")
            if calculation is not None and (
                not isinstance(calculation, dict)
                or not isinstance(calculation.get("type"), str)
            ):
                raise ValueError(f"invalid attack calculation: {skill_id}")
            attribute = unit.get("damageAttributeType")
            if not isinstance(attribute, dict) or not isinstance(attribute.get("name"), str):
                raise ValueError(f"missing damage attribute: {skill_id}")
            poise = unit.get("poiseCalculation")
            if poise is not None and (
                not isinstance(poise, dict)
                or not isinstance(poise.get("type"), str)
                or not isinstance(poise.get("scalars"), dict)
            ):
                raise ValueError(f"invalid Poise calculation: {skill_id}")
            poise_scale = (poise.get("scalars") or {}).get("applyScale") if poise else None
            if poise is not None and poise["type"] == "Beyond.Gameplay.Core.DefiniteValueCalculation" and type(poise_scale) is not bool:
                raise ValueError(f"missing DefiniteValue applyScale: {skill_id}")
            key = (simple, snapshot, calculation["type"] if calculation else None)
            counts[key] += 1
            attribute_counts[(*key, attribute["name"])] += 1
            poise_key = (poise["type"] if poise else None, poise_scale, attribute["name"])
            poise_counts[poise_key] += 1
            total += 1
            rows = examples.setdefault(key, [])
            if len(rows) < 3:
                rows.append(f"{skill_id}:{unit.get('sourcePath') or ''}")
            poise_rows = poise_examples.setdefault(poise_key, [])
            if len(poise_rows) < 3:
                poise_rows.append(f"{skill_id}:{unit.get('sourcePath') or ''}")
    partition = [{
        "simpleCalculation": key[0], "takeAtkSnapshot": key[1],
        "atkCalculationType": key[2], "count": count,
        "damageAttributeCounts": {
            attribute: attribute_count
            for (simple, snapshot, kind, attribute), attribute_count in attribute_counts.items()
            if (simple, snapshot, kind) == key
        },
        "examples": examples[key],
    } for key, count in counts.most_common()]
    poise_partition = [{
        "poiseCalculationType": key[0], "applyScale": key[1],
        "damageAttributeType": key[2], "count": count,
        "examples": poise_examples[key],
    } for key, count in poise_counts.most_common()]
    return {
        "schema": SCHEMA, "status": "validated", "language": index.get("language"),
        "inputSha256": input_sha256, "skillDataFiles": len(catalog),
        "damageUnits": total, "partition": partition,
        "poiseCalculationPartition": poise_partition,
        "conditionalFormulaRows": {
            "simpleHp": sum(count for (simple, snapshot, _, attribute), count in attribute_counts.items()
                            if simple and not snapshot and attribute == "Hp"),
            "atkScaleEvaluatorHp": sum(
                count for (simple, snapshot, kind, attribute), count in attribute_counts.items()
                if not simple and not snapshot and attribute == "Hp"
                and kind == "Beyond.Gameplay.Core.AtkScaleCalculation"
            ),
            "breakingAttackEvaluatorHp": sum(
                count for (simple, snapshot, kind, attribute), count in attribute_counts.items()
                if not simple and not snapshot and attribute == "Hp"
                and kind == "Beyond.Gameplay.Core.BreakingAttackCalculation"
            ),
            "definiteValuePoiseInput": sum(
                count for (kind, apply_scale, _attribute), count in poise_counts.items()
                if kind == "Beyond.Gameplay.Core.DefiniteValueCalculation"
                and type(apply_scale) is bool
            ),
        },
        "boundary": "Exact authored SkillData rows plus selected native normal-entity and Poise input routes. Attack formula badges are restricted to Hp rows. A Poise badge names the conditional intermediate calculation input to PoisePackData, not applied or displayed Poise. No action execution, live patch state, blackboard result, mitigation or final damage is established.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    raw = args.index.read_bytes()
    report = summarize(json.loads(raw), input_sha256=hashlib.sha256(raw).hexdigest())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "damageUnits": report["damageUnits"],
                      "partitionRows": len(report["partition"]), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
