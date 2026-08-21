#!/usr/bin/env python3
"""Verify the exact Endminf overview FX-model binding boundary.

``A_actor_endminf_ui_overview_02`` is stored under the
``sk_fx_endminf_01_ui.fbx`` container, but a container name is not a model
closure.  This verifier joins the clip to the playback closure, AssetMap and
CABMap by source, offset, PathID and Unity type, then proves whether the same
exact container/serialized-file identity also contains model objects.  It
also rechecks the three generic binding hashes against the authored actor
manifest and Avatar m_TOS using Unity's CRC32 path rule.

The current build is intentionally a successful negative proof within the
current AssetMap/container scope: the exact FX container has one AnimationClip
row and no GameObject/Animator/Avatar/Transform/Mesh closure.  Consequently no
FX-model remap is emitted and the clip is never assigned to the main actor
skeleton by name or hash order.  This does not negate an unassessed runtime
hierarchy.
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


def _source_fields(value: Any, *, label: str) -> tuple[int, int]:
    if not isinstance(value, dict):
        raise VerificationError(f"{label} source snapshot is missing")
    try:
        return int(value["bytes"]), int(value["mtime_ns"])
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError(f"{label} source snapshot lacks bytes/mtime_ns") from exc


def _validate_source_provenance(
    stamp: dict[str, Any],
    identity: dict[str, Any],
    expected_source: Any,
    current_source: dict[str, Any],
) -> dict[str, Any]:
    """Require closure, stage and current-file provenance to agree.

    The closure currently records bytes/mtime (not a digest), so the verifier
    computes the current digest and publishes it in the proof.  ``--check``
    then makes a later audit fail if the source content changes even when its
    size and mtime are restored.
    """

    expected_bytes, expected_mtime = _source_fields(
        expected_source, label="closure expectedSourceSnapshot"
    )
    current_bytes, current_mtime = _source_fields(
        current_source, label="current source"
    )
    if (current_bytes, current_mtime) != (expected_bytes, expected_mtime):
        raise VerificationError(
            "current source bytes/mtime differ from closure expectedSourceSnapshot"
        )
    if _normal_path(current_source.get("path")) != _normal_path(identity["source"]):
        raise VerificationError("current source path differs from exact identity")
    freshness = stamp.get("sourceFreshness")
    if not isinstance(freshness, dict) or freshness.get("status") != "validated":
        raise VerificationError("stage sourceFreshness is not validated")
    stage_current = freshness.get("current")
    stage_expected = freshness.get("expected")
    if _source_fields(stage_current, label="stage sourceFreshness.current") != (
        current_bytes,
        current_mtime,
    ):
        raise VerificationError("stage sourceFreshness.current differs from current source")
    if _source_fields(stage_expected, label="stage sourceFreshness.expected") != (
        expected_bytes,
        expected_mtime,
    ):
        raise VerificationError(
            "stage sourceFreshness.expected differs from closure expectedSourceSnapshot"
        )
    for label, snapshot in (
        ("stage sourceFreshness.current", stage_current),
        ("stage sourceFreshness.expected", stage_expected),
    ):
        if snapshot.get("path") is not None and _normal_path(snapshot.get("path")) != _normal_path(identity["source"]):
            raise VerificationError(f"{label} path differs from exact identity")
        if snapshot.get("sha256") is not None and snapshot.get("sha256") != current_source["sha256"]:
            raise VerificationError(f"{label} sha256 differs from current source")
    if expected_source.get("sha256") is not None and expected_source.get("sha256") != current_source["sha256"]:
        raise VerificationError("current source sha256 differs from closure expectedSourceSnapshot")
    if not isinstance(current_source.get("sha256"), str) or len(current_source["sha256"]) != 64:
        raise VerificationError("current source sha256 was not computed")
    return {
        "closureExpected": dict(expected_source),
        "stageCurrent": dict(stage_current),
        "stageExpected": dict(stage_expected),
        "current": dict(current_source),
        "bytesMtimeValidated": True,
        "sha256Validated": True,
    }


def _stage_clip(
    stage: Path,
    identity: dict[str, Any],
    expected_source: Any,
) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not stage.is_dir():
        raise VerificationError(f"exact actor clip stage is missing: {stage}")
    stamp_path = stage / ".character_import_stage.json"
    if not stamp_path.is_file():
        raise VerificationError(f"exact actor clip stage stamp is missing: {stamp_path}")
    stamp = _json(stamp_path)
    if not isinstance(stamp, dict) or stamp.get("status") != "ok":
        raise VerificationError(f"exact actor clip stage stamp is stale: {stamp_path}")
    stage_identity = stamp.get("identity")
    if not isinstance(stage_identity, dict) or stage_identity != identity:
        raise VerificationError(f"exact actor clip stage stamp identity is stale: {stamp_path}")
    current_source = _snapshot(Path(identity["source"]))
    source_provenance = _validate_source_provenance(
        stamp, identity, expected_source, current_source
    )
    expected = stage / "AnimationClip" / (
        f"{identity['name']}_p{int(identity['pathId']) & ((1 << 64) - 1):016X}.json"
    )
    if not expected.is_file():
        raise VerificationError(f"exact actor clip JSON is missing: {expected}")
    value = _json(expected)
    if not isinstance(value, dict):
        raise VerificationError(f"exact actor clip JSON is not an object: {expected}")
    for key in ("m_Name", "Name"):
        if value.get(key) != stage_identity["name"]:
            raise VerificationError(f"clip {key} is not the exact staged target: {expected}")
    metadata = value.get("$animestudio")
    if metadata is not None and not isinstance(metadata, dict):
        raise VerificationError(f"clip $animestudio provenance is malformed: {expected}")
    if metadata is not None:
        checks = {
            "pathId": stage_identity["pathId"],
            "type": stage_identity["type"],
            "sourceOffset": stage_identity["sourceOffset"],
        }
        for key, wanted in checks.items():
            if metadata.get(key) != wanted:
                raise VerificationError(f"clip metadata {key} drifted: {expected}")
    return expected, value, stamp, source_provenance


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
    for path_hash in EXPECTED_BINDING_HASHES:
        rows = grouped[path_hash]
        attributes = sorted(int(row["attribute"]) for row in rows)
        if len(rows) != 3 or attributes != [1, 2, 3]:
            raise VerificationError(
                f"path hash {path_hash} must have exactly three Transform bindings "
                f"with attributes [1, 2, 3]; got count={len(rows)} attributes={attributes}"
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
        "evidenceScope": "current AssetMap container rows and exact source+offset rows only",
        "runtimeHierarchy": "not_assessed",
        "runtimeHierarchyNotNegated": True,
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
            "current_assetmap_container_scope_has_animation_clip_only_no_model_closure"
            if not model_rows and not same_file_model_rows
            else "current_assetmap_container_scope_model_rows_present_requires_explicit_hierarchy_join"
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
            {
                "pathHash": value,
                "keyPresent": False,
                "path": None,
                "candidateCount": 0,
                "candidatePaths": [],
                "algorithmMatches": False,
            }
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
            row.update(
                {
                    "keyPresent": True,
                    "path": authored,
                    "candidateCount": 1,
                    "candidatePaths": [authored],
                    "algorithmMatches": True,
                }
            )
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


def _remap_gates(
    model: dict[str, Any],
    manifest: dict[str, Any],
    avatar: dict[str, Any],
    hashes: Iterable[int],
) -> dict[str, Any]:
    """Return independent, fail-closed gates for an FX-model remap."""

    wanted = [int(value) for value in hashes]
    manifest_rows = {int(row["pathHash"]): row for row in manifest.get("targetRows", [])}
    avatar_rows = {int(row["pathHash"]): row for row in avatar.get("targetRows", [])}
    manifest_unique = all(
        manifest_rows.get(path_hash, {}).get("candidateCount") == 1
        and len(manifest_rows.get(path_hash, {}).get("candidatePaths") or []) == 1
        for path_hash in wanted
    )
    avatar_unique = all(
        avatar_rows.get(path_hash, {}).get("keyPresent") is True
        and avatar_rows.get(path_hash, {}).get("algorithmMatches") is True
        and avatar_rows.get(path_hash, {}).get("candidateCount") == 1
        and len(avatar_rows.get(path_hash, {}).get("candidatePaths") or []) == 1
        for path_hash in wanted
    )
    def first_path(rows: dict[int, dict[str, Any]], path_hash: int) -> Any:
        paths = rows.get(path_hash, {}).get("candidatePaths") or []
        return paths[0] if paths else None

    consistent = all(
        first_path(manifest_rows, path_hash) == first_path(avatar_rows, path_hash)
        and first_path(manifest_rows, path_hash) is not None
        for path_hash in wanted
    )
    model_closure = bool(
        model.get("containerModelRows")
        and model.get("sourceOffsetModelRows")
    )
    gates = {
        "modelClosure": model_closure,
        "manifestUnique": manifest_unique,
        "avatarTosUnique": avatar_unique,
        "manifestAvatarPathsConsistent": consistent,
    }
    missing = [name for name, passed in gates.items() if not passed]
    return {
        **gates,
        "allGatesPassed": not missing,
        "missingGates": missing,
        "evidenceScope": "current AssetMap/container plus authored manifest/Avatar TOS only",
        "runtimeHierarchy": "not_assessed",
        "runtimeHierarchyNotNegated": True,
    }


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
    expected_source = target.get("expectedSourceSnapshot")
    if not isinstance(expected_source, dict):
        raise VerificationError(
            "closure expectedSourceSnapshot is required for the exact target"
        )
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
    clip_path, clip, stage_stamp_value, source_provenance = _stage_clip(
        stage, identity, expected_source
    )
    stage_stamp = stage / ".character_import_stage.json"
    grouped = clip_binding_hashes(clip)
    model = _container_evidence(asset_map, identity)
    manifest = _manifest_evidence(actor_manifest, grouped)
    avatar_report = _avatar_evidence(avatar, grouped)
    remap_gates = _remap_gates(model, manifest, avatar_report, grouped)
    remap_eligible = bool(remap_gates["allGatesPassed"])
    if not remap_eligible:
        status = (
            "ok_current_assetmap_scope_model_closure_unresolved"
            if not remap_gates["modelClosure"]
            else "ok_current_assetmap_scope_remap_mapping_unresolved"
        )
        reason = (
            "not eligible in current AssetMap/container scope: missing gates "
            + ", ".join(remap_gates["missingGates"])
            + "; runtime hierarchy was not assessed; no FX-model .anim remap emitted"
        )
    else:
        status = "ok_current_assetmap_scope_remap_eligible"
        reason = (
            "current AssetMap/container scope and authored manifest/Avatar TOS provide "
            "unique consistent model-remap gates; runtime hierarchy still requires an "
            "explicit join before emission"
        )
    return {
        "schema": SCHEMA,
        "status": status,
        "evidenceScope": {
            "kind": "current_assetmap_container_and_authored_tos_scope",
            "description": (
                "Conclusions are bounded to the current AssetMap/CABMap exact identity, "
                "serialized source offset, actor manifest and Avatar m_TOS artifacts."
            ),
            "runtimeHierarchy": "not_assessed",
            "runtimeHierarchyNotNegated": True,
        },
        "identity": identity,
        "identityEvidence": {
            "closure": _snapshot(closure),
            "assetMap": _snapshot(asset_map),
            "cabMap": _snapshot(cab_map),
            "stageStamp": _snapshot(stage_stamp),
            "stageClip": _snapshot(clip_path),
            "stageProvenanceIdentity": stage_stamp_value["identity"],
            "source": source_provenance["current"],
            "closureExpectedSource": source_provenance["closureExpected"],
            "stageSourceFreshness": {
                "current": source_provenance["stageCurrent"],
                "expected": source_provenance["stageExpected"],
                "currentFile": source_provenance["current"],
                "bytesMtimeValidated": source_provenance["bytesMtimeValidated"],
                "sha256Validated": source_provenance["sha256Validated"],
            },
        },
        "clip": {
            "bindingCount": sum(len(rows) for rows in grouped.values()),
            "uniquePathHashCount": len(grouped),
            "bindingCountByHash": {
                str(path_hash): len(rows) for path_hash, rows in grouped.items()
            },
            "pathHashes": sorted(grouped),
            "typeIDsByHash": {
                str(path_hash): sorted({str(row["typeID"]) for row in rows})
                for path_hash, rows in grouped.items()
            },
            "attributesByHash": {
                str(path_hash): sorted(int(row["attribute"]) for row in rows)
                for path_hash, rows in grouped.items()
            },
        },
        "fxModelClosure": model,
        "remapGates": remap_gates,
        "mainActorSkeleton": {
            "role": "main-actor-skeleton",
            "remapApplied": False,
            "evidenceScope": "current authored actor manifest and canonical Avatar m_TOS only",
            "runtimeHierarchy": "not_assessed",
            "runtimeHierarchyNotNegated": True,
            "manifest": manifest,
            "avatar": avatar_report,
        },
        "remap": {
            "eligible": remap_eligible,
            "output": None,
            "reason": reason,
            "runtimeHierarchy": "not_assessed",
            "runtimeHierarchyNotNegated": True,
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
