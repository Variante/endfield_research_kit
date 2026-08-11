#!/usr/bin/env python3
"""Build the source-backed Gacha light survivor transport contract.

The contract carries only the authored candidate identity/order that is already
closed by the native cull and SetupState audits.  It deliberately does not
invent a target-frame LightCullResult pointer, count, or row payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
POPULATION = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_light_population_recovery.json"
)
DEFERRED = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_deferred_light_data_recovery.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "gacha_light_survivor_transport.json"
)

SCHEMA = "endfield.gacha-light-survivor-transport.v1"
EXPECTED_POPULATION_SCHEMA = "endfield.gacha-light-population-recovery.v4"
EXPECTED_DEFERRED_SCHEMA = "endfield.gacha-deferred-light-data-recovery.v22"


class ContractError(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(LAB_ROOT.parent.resolve()).as_posix()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def compact_candidate_rows(deferred: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (
        deferred["nativeProducer"]["pointRecordTransform"]
        ["authoredRoomCandidates"]["rows"]
    )
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[row["name"]] = {
            "lightPathId": row["lightPathId"],
            "worldPosition": row["worldPosition"],
            "worldForward": row["worldForward"],
            "record2XYCandidate": row["record2XYCandidate"],
        }
    return result


def build_contract(
    population_path: Path = POPULATION,
    deferred_path: Path = DEFERRED,
) -> dict[str, Any]:
    population = json.loads(population_path.read_text(encoding="utf-8"))
    deferred = json.loads(deferred_path.read_text(encoding="utf-8"))
    require(
        population.get("schema") == EXPECTED_POPULATION_SCHEMA,
        f"population schema drift: {population.get('schema')!r}",
    )
    require(
        deferred.get("schema") == EXPECTED_DEFERRED_SCHEMA,
        f"deferred schema drift: {deferred.get('schema')!r}",
    )

    selected = population["exactKnownAuthoredSelectedAspectSurvivors"]
    setup_order = list(selected["setupStateRelativeOrder"])
    require(len(setup_order) == selected["count"] == 17, "known authored count is not 17")
    require(len(set(setup_order)) == len(setup_order), "survivor order contains duplicates")
    character_rows = [row for row in selected["rows"] if row["source"] == "light_overview"]
    room_rows = [row for row in selected["rows"] if row["source"] == "SceneLight6Rarity"]
    require(len(character_rows) == 6, "known authored character count is not 6")
    require(len(room_rows) == 11, "known authored room count is not 11")
    require(
        setup_order == [row["name"] for row in selected["rows"]],
        "SetupState order differs from selected survivor rows",
    )

    room_candidates = compact_candidate_rows(deferred)
    deferred_room_rows = {
        row["name"]: row for row in deferred["selectedAuthoredRoomRows"]["rows"]
    }
    records: list[dict[str, Any]] = []
    for row in selected["rows"]:
        item: dict[str, Any] = {
            "name": row["name"],
            "source": row["source"],
            "priority": row["priority"],
            "cameraDistanceSquared": row["cameraDistanceSquared"],
            "targetFrameValue": "capture-only",
        }
        if row["source"] == "SceneLight6Rarity":
            candidate = room_candidates.get(row["name"])
            source_row = deferred_room_rows.get(row["name"])
            require(candidate is not None, f"missing transform candidate: {row['name']}")
            require(source_row is not None, f"missing deferred row: {row['name']}")
            item["lightPathId"] = source_row["lightPathId"]
            item["candidate"] = candidate
            item["staticRecordTerms"] = {
                "record0RgbBits": source_row["record0Color"]["record0RgbBits"],
                "record0WBits": source_row["record0Discriminator"]["record0WBits"],
                "record1WBits": source_row["record1InverseRange"]["record1WBits"],
                "record2ZBits": source_row["record2StaticTerms"]["record2ZBits"],
                "record2WBits": source_row["record2StaticTerms"].get("record2WBits"),
                "record2WStatus": (
                    "closed" if source_row["record2StaticTerms"]["record2WClosed"]
                    else "capture-only"
                ),
                "obbPackedTransformWords": source_row["obbPackedTransform"][
                    "nativeInverseCandidateWordHex"
                ],
            }
        records.append(item)

    return {
        "schema": SCHEMA,
        "status": "known_authored_selected_aspect_survivor_transport",
        "selection": {
            "displayAspect": "3840/2160",
            "displayAspectFloat": 16.0 / 9.0,
            "admission": "AtOrAboveSpot18Threshold",
            "knownAuthoredCount": len(setup_order),
            "knownAuthoredCharacterCount": len(character_rows),
            "knownAuthoredRoomCount": len(room_rows),
            "setupStateRelativeOrder": setup_order,
            "records": records,
        },
        "sourceEvidence": {
            "populationReport": repo_relative(population_path),
            "populationReportSha256": sha256(population_path),
            "deferredReport": repo_relative(deferred_path),
            "deferredReportSha256": sha256(deferred_path),
            "nativeOrder": "CullLights output distance order; SetupState priority descending then camera distance ascending",
            "knownAuthoredScope": "six light_overview rows plus eleven SceneLight6Rarity rows",
        },
        "boundary": {
            "targetFrameCaptureRequired": True,
            "targetFramePointerAndCount": "open",
            "runtimeCustomCarryIn": "open",
            "wholeListOrderAfterNativeCull": "open outside this selected authored scope",
            "pointShadowCacheIndices": "capture-only",
            "nonEmptyCookies": "not present in this authored selected scope",
            "productionPublication": "disabled; this contract does not publish a shader buffer",
            "decision": "transport authored identity/order only; fail closed until a retail LightCullResult capture supplies target-frame rows",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    contract = build_contract()
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        actual = args.output.read_text(encoding="utf-8")
        require(actual == rendered, f"generated contract drift: {args.output}")
    else:
        args.output.write_text(rendered, encoding="utf-8")
    print(
        f"gacha survivor transport: {contract['selection']['knownAuthoredCount']} "
        f"known authored rows; target-frame capture required; output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
