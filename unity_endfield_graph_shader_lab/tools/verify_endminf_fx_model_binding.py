#!/usr/bin/env python3
"""Verify the exact Endminf overview FX-model binding boundary.

``A_actor_endminf_ui_overview_02`` is stored under the
``sk_fx_endminf_01_ui.fbx`` container, but a container name is not a model
closure.  This verifier joins the clip to the playback closure, AssetMap and
CABMap by source, offset, PathID and Unity type, then proves whether the same
exact container/serialized-file identity also contains model objects.  It
also rechecks the three generic binding hashes against the authored actor
manifest and Avatar m_TOS using Unity's CRC32 path rule.

The current build is intentionally a successful negative proof: the exact FX
container has one AnimationClip row and no GameObject/Animator/Avatar/
Transform/Mesh closure.  Consequently no FX-model remap is emitted and the
clip is never assigned to the main actor skeleton by name or hash order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
if str(LAB_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(LAB_ROOT / "tools"))

from endfield_asset_map_filter import iter_asset_entries
from extract_endminf_actor_animation_clip import (
    DEFAULT_ACTOR_AVATAR,
    DEFAULT_ACTOR_TOS,
    DEFAULT_ASSET_MAP,
    DEFAULT_CAB_MAP,
    DEFAULT_CLOSURE,
    ExtractionError,
    _asset_map_row,
    _cab_row,
    _json,
    _normal_path,
    _relative,
    _target_from_closure,
)


DEFAULT_STAGE = LAB_ROOT / "Temp" / "Codex" / "endminf_actor_overview_02_exact_stage"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "assets" / "character_recovery" / "endminf_fx_model_binding_proof.json"
EXPECTED_BINDING_HASHES = (1875086154, 2258644607, 4054261481)
MODEL_TYPES = (
    "GameObject",
    "Animator",
    "Avatar",
    "Transform",
    "Mesh",
    "SkinnedMeshRenderer",
)
PATH_HASH_ALGORITHM = {
    "name": "Unity Avatar m_TOS transform-path CRC32",
    "implementation": "CRC32-IEEE over the exact UTF-8 full hierarchy path, masked to unsigned 32-bit",
    "python": "zlib.crc32(path.encode('utf-8')) & 0xffffffff",
}
SCHEMA = "endfield.endminf.fx-model-binding-proof.v1"


class VerificationError(RuntimeError):
    """Raised when exact evidence is missing, stale or contradictory."""


def unity_crc32(path: str) -> int:
    """Return Unity's unsigned CRC32 for an authored transform path."""

    return zlib.crc32(path.encode("utf-8")) & 0xFFFFFFFF


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise VerificationError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _snapshot(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise VerificationError(f"evidence file is missing: {path}: {exc}") from exc
    if not path.is_file():
        raise VerificationError(f"expected an evidence file: {path}")
    return {
        "path": _relative(path),
        "bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": _sha256(path),
    }


def _stage_clip(stage: Path, identity: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    if not stage.is_dir():
        raise VerificationError(f"exact actor clip stage is missing: {stage}")
    stamp_path = stage / ".character_import_stage.json"
    if not stamp_path.is_file():
        raise VerificationError(f"exact actor clip stage stamp is missing: {stamp_path}")
    stamp = _json(stamp_path)
    if not isinstance(stamp, dict) or stamp.get("status") != "ok" or stamp.get("identity") != identity:
        raise VerificationError(f"exact actor clip stage stamp identity is stale: {stamp_path}")
    expected = stage / "AnimationClip" / (
        f"{identity['name']}_p{int(identity['pathId']) & ((1 << 64) - 1):016X}.json"
    )
    if not expected.is_file():
        raise VerificationError(f"exact actor clip JSON is missing: {expected}")
    value = _json(expected)
    if not isinstance(value, dict):
        raise VerificationError(f"exact actor clip JSON is not an object: {expected}")
    metadata = value.get("$animestudio") or {}
    if metadata:
        checks = {
            "pathId": identity["pathId"],
            "type": identity["type"],
            "sourceOffset": identity["sourceOffset"],
        }
        for key, wanted in checks.items():
            if metadata.get(key) != wanted:
                raise VerificationError(f"clip metadata {key} drifted: {expected}")
    return expected, value


def clip_binding_hashes(value: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    """Group the exact generic Transform bindings by serialized path hash."""

    bindings = ((value.get("m_ClipBindingConstant") or {}).get("genericBindings"))
    if not isinstance(bindings, list):
        raise VerificationError("AnimationClip genericBindings is missing or malformed")
    grouped: dict[int, list[dict[str, Any]]] = {}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            raise VerificationError(f"generic binding {index} is malformed")
        try:
            path_hash = int(binding["path"])
            attribute = int(binding["attribute"])
        except (KeyError, TypeError, ValueError) as exc:
            raise VerificationError(f"generic binding {index} lacks path/attribute") from exc
        if binding.get("typeID") != "Transform":
            raise VerificationError(f"generic binding {index} is not a Transform binding")
        grouped.setdefault(path_hash, []).append(
            {"index": index, "attribute": attribute, "typeID": "Transform"}
        )
    if tuple(sorted(grouped)) != EXPECTED_BINDING_HASHES or len(bindings) != 9:
        raise VerificationError(
            f"expected exactly the three Endminf FX hashes and nine bindings; "
            f"got hashes={sorted(grouped)} entries={len(bindings)}"
        )
    return grouped


def _same_identity(row: dict[str, Any], identity: dict[str, Any]) -> bool:
    return (
        str(row.get("Name") or "") == identity["name"]
        and str(row.get("Type") or "") == identity["type"]
        and int(row.get("PathID")) == int(identity["pathId"])
        and int(row.get("Offset")) == int(identity["sourceOffset"])
        and _normal_path(row.get("Source")) == _normal_path(identity["source"])
        and str(row.get("Container") or "") == identity["container"]
    )


def _container_evidence(asset_map: Path, identity: dict[str, Any]) -> dict[str, Any]:
    exact_rows: list[dict[str, Any]] = []
    source_offset_rows: list[dict[str, Any]] = []
    for row in iter_asset_entries(asset_map):
        if str(row.get("Container") or "") == identity["container"]:
            exact_rows.append(row)
        if (
            _normal_path(row.get("Source")) == _normal_path(identity["source"])
            and int(row.get("Offset") or -1) == int(identity["sourceOffset"])
        ):
            source_offset_rows.append(row)
    target_rows = [row for row in exact_rows if _same_identity(row, identity)]
    if len(target_rows) != 1:
        raise VerificationError(
            f"exact AssetMap identity is not unique: targetRows={len(target_rows)}"
        )
    model_rows = [row for row in exact_rows if str(row.get("Type") or "") in MODEL_TYPES]
    same_file_model_rows = [
        row for row in source_offset_rows if str(row.get("Type") or "") in MODEL_TYPES
    ]
    return {
        "container": identity["container"],
        "containerRowCount": len(exact_rows),
        "containerTypeCounts": dict(sorted(Counter(str(row.get("Type") or "") for row in exact_rows).items())),
        "sourceOffset": identity["sourceOffset"],
        "sourceOffsetRowCount": len(source_offset_rows),
        "sourceOffsetTypeCounts": dict(
            sorted(Counter(str(row.get("Type") or "") for row in source_offset_rows).items())
        ),
        "modelTypes": list(MODEL_TYPES),
        "containerModelRows": len(model_rows),
        "sourceOffsetModelRows": len(same_file_model_rows),
        "targetIdentityRows": [
            {
                "name": row.get("Name"),
                "type": row.get("Type"),
                "pathId": row.get("PathID"),
                "source": row.get("Source"),
                "offset": row.get("Offset"),
                "container": row.get("Container"),
            }
            for row in target_rows
        ],
        "result": (
            "container_has_animation_clip_only_no_model_closure"
            if not model_rows and not same_file_model_rows
            else "model_rows_present_requires_explicit_hierarchy_join"
        ),
    }


def _manifest_evidence(path: Path, hashes: Iterable[int]) -> dict[str, Any]:
    wanted = sorted(set(int(value) for value in hashes))
    rows = {str(value): [] for value in wanted}
    if not path.is_file():
        return {"path": _relative(path), "exists": False, "targetRows": [{"pathHash": value, "candidatePaths": []} for value in wanted]}
    document = _json(path)
    transforms = document.get("transforms") if isinstance(document, dict) else None
    if not isinstance(transforms, list):
        raise VerificationError(f"actor manifest transforms are missing: {path}")
    valid = 0
    invalid = 0
    for row in transforms:
        if not isinstance(row, dict):
            invalid += 1
            continue
        authored = str(row.get("path") or "")
        try:
            stored = int(row.get("path_crc"))
        except (TypeError, ValueError):
            invalid += 1
            continue
        if not authored or stored != unity_crc32(authored):
            invalid += 1
            continue
        valid += 1
        if str(stored) in rows:
            rows[str(stored)].append(authored)
    return {
        "path": _relative(path),
        "exists": True,
        "hashAlgorithm": PATH_HASH_ALGORITHM,
        "transformCount": len(transforms),
        "validPathCrcCount": valid,
        "invalidPathCrcCount": invalid,
        "sourceSha256": _sha256(path),
        "targetRows": [
            {"pathHash": value, "candidateCount": len(rows[str(value)]), "candidatePaths": rows[str(value)]}
            for value in wanted
        ],
        "result": "all_target_hashes_absent_from_actor_manifest"
        if not any(rows.values())
        else "target_hashes_present_in_actor_manifest",
    }


def _avatar_evidence(path: Path, hashes: Iterable[int]) -> dict[str, Any]:
    wanted = sorted(set(int(value) for value in hashes))
    base: dict[str, Any] = {
        "path": _relative(path),
        "exists": path.is_file(),
        "hashAlgorithm": PATH_HASH_ALGORITHM,
        "targetRows": [
            {"pathHash": value, "keyPresent": False, "path": None, "algorithmMatches": False}
            for value in wanted
        ],
    }
    if not path.is_file():
        base["result"] = "source_missing"
        return base
    document = _json(path)
    tos = document.get("m_TOS") if isinstance(document, dict) else None
    if not isinstance(tos, dict):
        raise VerificationError(f"Avatar m_TOS is missing or malformed: {path}")
    rows = {str(value): base["targetRows"][index] for index, value in enumerate(wanted)}
    valid = 0
    invalid = 0
    for raw_key, raw_path in tos.items():
        try:
            key = int(raw_key)
        except (TypeError, ValueError):
            invalid += 1
            continue
        authored = str(raw_path)
        if unity_crc32(authored) != key:
            invalid += 1
            continue
        valid += 1
        row = rows.get(str(key))
        if row is not None:
            row.update({"keyPresent": True, "path": authored, "algorithmMatches": True})
    base.update(
        {
            "avatarName": str(document.get("m_Name") or document.get("Name") or ""),
            "tosEntryCount": len(tos),
            "validKeyCount": valid,
            "invalidKeyCount": invalid,
            "skeletonNodeCount": len(((document.get("m_Avatar") or {}).get("m_AvatarSkeleton") or {}).get("m_Node") or []),
            "sourceSha256": _sha256(path),
            "result": "all_target_hashes_absent_from_exact_avatar_tos"
            if not any(row["keyPresent"] for row in base["targetRows"])
            else "target_hashes_present_in_exact_avatar_tos",
        }
    )
    return base


def build_report(
    *,
    closure: Path,
    asset_map: Path,
    cab_map: Path,
    stage: Path,
    actor_manifest: Path,
    avatar: Path,
) -> dict[str, Any]:
    target = _target_from_closure(closure)
    row = _asset_map_row(asset_map, target)
    cab = _cab_row(cab_map, target)
    identity = {
        "name": target["name"],
        "type": target["type"],
        "pathId": target["pathId"],
        "pathIdHex": f"{int(target['pathId']) & ((1 << 64) - 1):016X}",
        "source": str(row["Source"]).replace("\\", "/"),
        "sourceOffset": int(row["Offset"]),
        "cab": cab["cab"],
        "container": target["container"],
    }
    clip_path, clip = _stage_clip(stage, identity)
    stage_stamp = stage / ".character_import_stage.json"
    grouped = clip_binding_hashes(clip)
    model = _container_evidence(asset_map, identity)
    manifest = _manifest_evidence(actor_manifest, grouped)
    avatar_report = _avatar_evidence(avatar, grouped)
    remap_eligible = bool(
        model["containerModelRows"]
        and model["sourceOffsetModelRows"]
        and all(
            row["candidateCount"] == 1
            for row in manifest["targetRows"]
        )
    )
    return {
        "schema": SCHEMA,
        "status": "ok_model_closure_unresolved" if not remap_eligible else "ok_model_closure_requires_explicit_join",
        "identity": identity,
        "identityEvidence": {
            "closure": _snapshot(closure),
            "assetMap": _snapshot(asset_map),
            "cabMap": _snapshot(cab_map),
            "stageStamp": _snapshot(stage_stamp),
            "stageClip": _snapshot(clip_path),
            "source": _snapshot(Path(identity["source"])),
        },
        "clip": {
            "bindingCount": sum(len(rows) for rows in grouped.values()),
            "uniquePathHashCount": len(grouped),
            "pathHashes": sorted(grouped),
            "attributesByHash": {
                str(path_hash): sorted(int(row["attribute"]) for row in rows)
                for path_hash, rows in grouped.items()
            },
        },
        "fxModelClosure": model,
        "mainActorSkeleton": {
            "role": "main-actor-skeleton",
            "remapApplied": False,
            "manifest": manifest,
            "avatar": avatar_report,
        },
        "remap": {
            "eligible": remap_eligible,
            "output": None,
            "reason": (
                "exact sk_fx container/source-offset has no GameObject/Animator/Avatar/Transform/Mesh closure; "
                "do not synthesize FX-model .anim or assign these hashes to the main actor skeleton"
                if not remap_eligible
                else "model rows exist but no automatic remap is allowed until every hash has one authored path"
            ),
        },
        "resolutionRule": (
            "only exact source+offset+PathID+type identity plus one authored transform path whose CRC32(UTF-8) "
            "equals the clip hash may produce a remapped .anim; container/name/order are not fallbacks"
        ),
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--cab-map", type=Path, default=DEFAULT_CAB_MAP)
    parser.add_argument("--stage", type=Path, default=DEFAULT_STAGE)
    parser.add_argument("--actor-manifest", type=Path, default=DEFAULT_ACTOR_TOS)
    parser.add_argument("--avatar", type=Path, default=DEFAULT_ACTOR_AVATAR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="validate an existing proof report")
    args = parser.parse_args(argv)
    try:
        expected = build_report(
            closure=args.closure,
            asset_map=args.asset_map,
            cab_map=args.cab_map,
            stage=args.stage,
            actor_manifest=args.actor_manifest,
            avatar=args.avatar,
        )
        if args.check:
            actual = _json(args.output)
            if actual != expected:
                raise VerificationError(f"proof report drifted from current exact evidence: {args.output}")
            print(f"checked {args.output}: status={actual['status']} remapEligible={actual['remap']['eligible']}")
            return 0
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(expected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(
            f"wrote {args.output}: status={expected['status']} "
            f"modelRows={expected['fxModelClosure']['containerModelRows']} "
            f"hashes={expected['clip']['pathHashes']}"
        )
        return 0
    except (VerificationError, ExtractionError, OSError, ValueError) as exc:
        print(f"verify_endminf_fx_model_binding: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
