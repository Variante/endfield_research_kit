"""Extract and validate Endminf's exact actor overview AnimationClip.

This is deliberately narrower than the external UI-effect extraction.  The
input identity is taken from the playback-closure report and is joined to the
AssetMap and CABMap by source, source offset, signed PathID, and Unity type.
Name is checked as an additional identity field; it is never used as a
fallback selector.  A successful run leaves a terminal stage stamp only after
the AnimeStudio object-index sidecar, source freshness, and clip JSON have all
passed their contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
TOOLS_ROOT = PROJECT_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from character_import.audit_generic_actor_animations import parse_cab_map
from endfield_asset_map_filter import iter_asset_entries


TARGET_NAME = "A_actor_endminf_ui_overview_02"
TARGET_TYPE = "AnimationClip"
DEFAULT_CLOSURE = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
    / "ExternalUiEffects"
    / "endminf_animator_playback_closure.json"
)
DEFAULT_ASSET_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json"
)
DEFAULT_CAB_MAP = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Maps"
    / "endfield_streamingassets_assets.bin"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "Temp" / "Codex" / "endminf_actor_overview_02_exact_stage"
DEFAULT_ACTOR_HIERARCHY_ROOT = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Playable"
    / "Endminf"
)
DEFAULT_ACTOR_TOS = DEFAULT_ACTOR_HIERARCHY_ROOT / "endminf_ui_recovery_manifest.json"
ANIMESTUDIO_CLI = (
    REPO_ROOT
    / "tools"
    / "AnimeStudio"
    / "AnimeStudio.CLI"
    / "bin"
    / "Release"
    / "net9.0-windows"
    / "AnimeStudio.CLI.exe"
)
U64_MASK = (1 << 64) - 1
STAGE_SCHEMA = "endfield.endminf.actor-animation-clip-extraction.v2"
OBJECT_INDEX_REQUIRED_COUNTS = (
    "objects",
    "schemas",
    "monoScripts",
    "scalars",
    "pptrs",
    "objectsWithTruncatedScalars",
    "errors",
    "suppressedErrors",
)
EXPECTED_INFINITY_REPLACEMENTS = 121


class ExtractionError(RuntimeError):
    """Raised when exact source or output evidence cannot be established."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"JSON is missing or malformed: {path}: {exc}") from exc


def _normal_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").rstrip("/").casefold()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ExtractionError(f"cannot hash file: {path}: {exc}") from exc
    return digest.hexdigest()


def _snapshot(path: Path, *, with_hash: bool = False) -> dict[str, Any]:
    try:
        stat = path.stat()
    except OSError as exc:
        raise ExtractionError(f"installed source or tool is missing: {path}") from exc
    if not path.is_file():
        raise ExtractionError(f"expected a file, got: {path}")
    result: dict[str, Any] = {
        "path": str(path.resolve()).replace("\\", "/"),
        "bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }
    if with_hash:
        result["sha256"] = _sha256(path)
    return result


def _unsigned_hex(path_id: int) -> str:
    return f"{int(path_id) & U64_MASK:016X}"


def _find_dicts(value: Any, predicate: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if predicate(value):
            yield value
        for child in value.values():
            yield from _find_dicts(child, predicate)
    elif isinstance(value, list):
        for child in value:
            yield from _find_dicts(child, predicate)


def _target_from_closure(closure_path: Path) -> dict[str, Any]:
    closure = _json(closure_path)
    if not isinstance(closure, dict):
        raise ExtractionError("playback closure is not an object")
    missing = [
        row
        for row in closure.get("missingArtifacts") or []
        if isinstance(row, dict)
        and row.get("kind") == TARGET_TYPE
        and row.get("name") == TARGET_NAME
    ]
    if len(missing) != 1:
        raise ExtractionError(
            f"playback closure must contain exactly one missing {TARGET_NAME} artifact; found {len(missing)}"
        )
    missing_row = missing[0]
    try:
        path_id = int(missing_row["pathId"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ExtractionError("closure target PathID is malformed") from exc
    cab = str(missing_row.get("cab") or "")
    if not cab or not isinstance(missing_row.get("mismatchedCandidates"), list):
        raise ExtractionError("closure target lacks exact CAB/mismatch evidence")
    if missing_row["mismatchedCandidates"]:
        raise ExtractionError("closure target has mismatched artifact candidates")

    candidates = list(
        _find_dicts(
            closure,
            lambda row: (
                row.get("Name") == TARGET_NAME
                and row.get("Type") == TARGET_TYPE
                and int(row.get("PathID") or 0) == path_id
                and "Source" in row
                and "Offset" in row
            ),
        )
    )
    identities = {
        (
            str(row.get("Name") or ""),
            _normal_path(row.get("Source")),
            int(row.get("PathID")),
            str(row.get("Type") or ""),
            int(row.get("Offset")),
            str(row.get("Container") or ""),
        )
        for row in candidates
    }
    if len(identities) != 1:
        raise ExtractionError(
            f"closure target has {len(identities)} conflicting AssetMap identities"
        )
    name, source, identity_path_id, entry_type, offset, container = next(iter(identities))
    if identity_path_id != path_id or entry_type != TARGET_TYPE or name != TARGET_NAME:
        raise ExtractionError("closure target identity drifted")

    # Capture the closure's expected physical source snapshot when available.
    source_records = [
        row
        for row in _find_dicts(
            closure,
            lambda row: (
                str(row.get("cab") or "").casefold() == cab.casefold()
                and _normal_path(row.get("source")) == source
                and int(row.get("sourceOffset") or -1) == offset
            ),
        )
        if isinstance(row.get("sourceSnapshot"), dict)
    ]
    snapshots = {
        (
            int(row["sourceSnapshot"].get("bytes")),
            int(row["sourceSnapshot"].get("mtime_ns")),
        )
        for row in source_records
        if row["sourceSnapshot"].get("bytes") is not None
        and row["sourceSnapshot"].get("mtime_ns") is not None
    }
    if len(snapshots) > 1:
        raise ExtractionError("closure has conflicting physical source snapshots")
    return {
        "name": name,
        "source": source,
        "sourceRaw": next(row.get("Source") for row in candidates),
        "pathId": path_id,
        "type": entry_type,
        "offset": offset,
        "container": container,
        "cab": cab,
        "expectedSourceSnapshot": (
            {"bytes": next(iter(snapshots))[0], "mtime_ns": next(iter(snapshots))[1]}
            if snapshots
            else None
        ),
        "closure": _relative(closure_path),
    }


def _asset_map_row(asset_map_path: Path, target: dict[str, Any]) -> dict[str, Any]:
    if not asset_map_path.is_file():
        raise ExtractionError(f"AssetMap is missing: {asset_map_path}")
    matches: list[dict[str, Any]] = []
    for row in iter_asset_entries(asset_map_path):
        if (
            str(row.get("Name") or "") == target["name"]
            and str(row.get("Type") or "") == target["type"]
            and int(row.get("PathID") or 0) == target["pathId"]
            and int(row.get("Offset") or -1) == target["offset"]
            and _normal_path(row.get("Source")) == target["source"]
        ):
            matches.append(row)
    if len(matches) != 1:
        raise ExtractionError(
            f"AssetMap exact identity must resolve once, found {len(matches)}: {target['name']}"
        )
    row = dict(matches[0])
    if str(row.get("Container") or "") != target["container"]:
        raise ExtractionError("AssetMap exact target container differs from closure")
    return row


def _cab_row(cab_map_path: Path, target: dict[str, Any]) -> dict[str, Any]:
    if not cab_map_path.is_file():
        raise ExtractionError(f"CABMap is missing: {cab_map_path}")
    try:
        records = list(parse_cab_map(cab_map_path, "StreamingAssets"))
    except (OSError, EOFError, ValueError) as exc:
        raise ExtractionError(f"cannot parse CABMap {cab_map_path}: {exc}") from exc
    rows = [
        record
        for record in records
        if str(record.cab).casefold() == target["cab"].casefold()
        and int(record.offset) == target["offset"]
        and _normal_path(record.source) == target["source"]
    ]
    if len(rows) != 1:
        raise ExtractionError(
            f"CABMap exact CAB/source/offset must resolve once, found {len(rows)}: {target['cab']}"
        )
    row = rows[0]
    return {
        "cab": str(row.cab),
        "assetRoot": str(row.asset_root),
        "source": str(row.source),
        "sourceOffset": int(row.offset),
        "relativePath": str(row.relative_path),
        "baseFolder": str(row.base_folder),
        "dependencies": [str(value) for value in row.dependencies],
    }


def _finite_number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _clip_metrics(value: dict[str, Any]) -> dict[str, Any]:
    name = str(value.get("m_Name") or value.get("Name") or "")
    if name != TARGET_NAME:
        raise ExtractionError(f"AnimationClip JSON name mismatch: {name!r}")
    sample_rate = _finite_number(value.get("m_SampleRate"))
    muscle = value.get("m_MuscleClip")
    stop_time = _finite_number(muscle.get("m_StopTime")) if isinstance(muscle, dict) else None
    if sample_rate is None or sample_rate <= 0:
        raise ExtractionError("AnimationClip has no positive finite m_SampleRate")
    if stop_time is None or stop_time <= 0:
        raise ExtractionError("AnimationClip has no positive finite m_MuscleClip.m_StopTime")
    binding_constant = value.get("m_ClipBindingConstant")
    if not isinstance(binding_constant, dict):
        raise ExtractionError("AnimationClip lacks m_ClipBindingConstant")
    generic = binding_constant.get("genericBindings")
    pptr_mapping = binding_constant.get("pptrCurveMapping")
    if not isinstance(generic, list) or not isinstance(pptr_mapping, list):
        raise ExtractionError("AnimationClip binding arrays are malformed")
    curve_keys = (
        "m_RotationCurves",
        "m_CompressedRotationCurves",
        "m_EulerCurves",
        "m_PositionCurves",
        "m_ScaleCurves",
        "m_FloatCurves",
        "m_PPtrCurves",
    )
    curves: dict[str, int] = {}
    for key in curve_keys:
        rows = value.get(key)
        if not isinstance(rows, list):
            raise ExtractionError(f"AnimationClip curve array is malformed: {key}")
        curves[key] = len(rows)
    acl = value.get("m_AclCompressedBuffer")
    acl_count = acl.get("FloatCurveCount") if isinstance(acl, dict) else None
    if acl_count is not None and (not isinstance(acl_count, int) or acl_count < 0):
        raise ExtractionError("AnimationClip ACL FloatCurveCount is malformed")
    return {
        "name": name,
        "sampleRate": sample_rate,
        "lengthSeconds": stop_time,
        "loopTime": value.get("m_MuscleClip", {}).get("m_LoopTime"),
        "bindingCounts": {
            "genericBindings": len(generic),
            "pptrCurveMapping": len(pptr_mapping),
            "totalBindingEntries": len(generic) + len(pptr_mapping),
            **curves,
            "aclFloatCurveCount": acl_count,
        },
    }


def _converted_clip_metrics(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ExtractionError(f"converted AnimationClip is unreadable: {path}: {exc}") from exc
    if not text.startswith("%YAML 1.1") or "AnimationClip:" not in text:
        raise ExtractionError("converted AnimationClip is not Unity YAML")

    def scalar(pattern: str, label: str) -> str:
        matches = re.findall(pattern, text, flags=re.MULTILINE)
        if not matches:
            raise ExtractionError(f"converted AnimationClip lacks {label}")
        return matches[-1]

    name = scalar(r"^\s+m_Name:\s*(\S+)\s*$", "m_Name")
    sample_rate = _finite_number(scalar(r"^\s+m_SampleRate:\s*([^\s]+)\s*$", "m_SampleRate"))
    stop_time = _finite_number(scalar(r"^\s+m_StopTime:\s*([^\s]+)\s*$", "m_StopTime"))
    if name != TARGET_NAME or sample_rate is None or sample_rate <= 0 or stop_time is None or stop_time <= 0:
        raise ExtractionError("converted AnimationClip identity or timing is invalid")
    start = text.find("  m_ClipBindingConstant:\n")
    end = text.find("  m_AnimationClipSettings:\n", start + 1)
    if start < 0 or end < 0:
        raise ExtractionError("converted AnimationClip lacks binding/settings sections")
    binding_section = text[start:end]
    generic_count = len(re.findall(r"^    - path:", binding_section, flags=re.MULTILINE))
    pptr_match = re.search(r"^    pptrCurveMapping:\s*(\[\])?\s*$", binding_section, flags=re.MULTILINE)
    if not pptr_match:
        raise ExtractionError("converted AnimationClip lacks pptrCurveMapping")
    return {
        "name": name,
        "sampleRate": sample_rate,
        "lengthSeconds": stop_time,
        "loopTime": scalar(r"^\s+m_LoopTime:\s*([^\s]+)\s*$", "m_LoopTime") in {"1", "true", "True"},
        "bindingCounts": {
            "genericBindings": generic_count,
            "pptrCurveMapping": 0 if pptr_match.group(1) == "[]" else None,
            "totalBindingEntries": generic_count,
        },
    }


def _assert_converted_matches_json(converted: dict[str, Any], serialized: dict[str, Any]) -> None:
    if converted["name"] != serialized["name"]:
        raise ExtractionError("JSON/Convert AnimationClip names differ")
    if abs(converted["sampleRate"] - serialized["sampleRate"]) > 1e-6:
        raise ExtractionError("JSON/Convert AnimationClip sample rates differ")
    if abs(converted["lengthSeconds"] - serialized["lengthSeconds"]) > 1e-5:
        raise ExtractionError("JSON/Convert AnimationClip lengths differ")
    if converted["loopTime"] != serialized["loopTime"]:
        raise ExtractionError("JSON/Convert AnimationClip loop flags differ")
    if converted["bindingCounts"] != {
        key: serialized["bindingCounts"][key]
        for key in ("genericBindings", "pptrCurveMapping", "totalBindingEntries")
    }:
        raise ExtractionError("JSON/Convert AnimationClip binding counts differ")


def _object_index_summary(path: Path, identity: dict[str, Any]) -> dict[str, Any]:
    """Read the CLI JSONL sidecar and require its terminal audit record.

    AnimeStudio's object-index sidecar is intentionally emitted for the JSON
    carrier load (AnimationClip plus the minimum MonoBehaviour schema carrier).
    The clip itself remains selected by the exact filter_data row; the sidecar
    is only accepted when its terminal summary is complete and error-free.
    """
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeError) as exc:
        raise ExtractionError(f"object_index_jsonl is unreadable: {path}: {exc}") from exc
    if not lines:
        raise ExtractionError("object_index_jsonl is empty")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"object_index_jsonl line {line_number} is malformed") from exc
        if not isinstance(value, dict):
            raise ExtractionError(f"object_index_jsonl line {line_number} is not an object")
        records.append(value)
    if any(record.get("recordType") == "summary" for record in records[:-1]):
        raise ExtractionError("object_index_jsonl has a non-terminal summary record")
    summary = records[-1]
    if summary.get("recordType") != "summary" or summary.get("schemaVersion") != 1:
        raise ExtractionError("object_index_jsonl lacks schemaVersion=1 terminal summary")
    if summary.get("complete") is not True:
        raise ExtractionError("object_index_jsonl terminal summary is not complete")
    if summary.get("source") != identity["source"]:
        raise ExtractionError("object_index_jsonl source differs from exact target")
    if summary.get("cab") != identity["cab"]:
        raise ExtractionError("object_index_jsonl CAB differs from exact target")
    if summary.get("pathId") != identity["pathId"]:
        raise ExtractionError("object_index_jsonl PathID differs from exact target")
    if summary.get("type") != identity["type"] or summary.get("name") != identity["name"]:
        raise ExtractionError("object_index_jsonl type/name differs from exact target")
    counts = summary.get("counts")
    if not isinstance(counts, dict):
        raise ExtractionError("object_index_jsonl terminal summary lacks counts")
    for key in OBJECT_INDEX_REQUIRED_COUNTS:
        value = counts.get(key)
        if type(value) is not int or value < 0:
            raise ExtractionError(f"object_index_jsonl count is malformed: {key}")
        if value != 0:
            raise ExtractionError(f"object_index_jsonl exact carrier count is nonzero: {key}={value}")
    errors = summary.get("errors")
    if not isinstance(errors, list) or errors:
        raise ExtractionError("object_index_jsonl terminal summary contains errors")
    return {
        "recordType": "summary",
        "schemaVersion": 1,
        "complete": True,
        "counts": {key: counts[key] for key in OBJECT_INDEX_REQUIRED_COUNTS},
        "errors": [],
        "source": identity["source"],
        "cab": identity["cab"],
        "pathId": identity["pathId"],
        "type": identity["type"],
        "name": identity["name"],
    }


def _annotate_object_index(path: Path, identity: dict[str, Any]) -> dict[str, Any]:
    """Attach exact source identity to the CLI's terminal JSONL summary."""
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, UnicodeError) as exc:
        raise ExtractionError(f"object_index_jsonl is unreadable after JSON export: {path}: {exc}") from exc
    if not lines:
        raise ExtractionError("AnimeStudio JSON export produced an empty object_index_jsonl")
    try:
        summary = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise ExtractionError("AnimeStudio JSON object_index_jsonl terminal record is malformed") from exc
    if not isinstance(summary, dict) or summary.get("recordType") != "summary":
        raise ExtractionError("AnimeStudio JSON object_index_jsonl has no terminal summary")
    summary.update(
        {
            "source": identity["source"],
            "cab": identity["cab"],
            "pathId": identity["pathId"],
            "type": identity["type"],
            "name": identity["name"],
        }
    )
    lines[-1] = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return _object_index_summary(path, identity)


def _normalize_anim(raw_path: Path, normalized_path: Path) -> dict[str, Any]:
    """Create a separate Unity-readable ASCII copy without touching raw output."""
    try:
        raw_bytes = raw_path.read_bytes()
        raw_text = raw_bytes.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise ExtractionError(f"exact raw .anim is unreadable as UTF-8: {raw_path}: {exc}") from exc
    replacement_count = raw_text.count("\u221e")
    if replacement_count != EXPECTED_INFINITY_REPLACEMENTS:
        raise ExtractionError(
            f"exact raw .anim Infinity replacement count is {replacement_count}, "
            f"expected {EXPECTED_INFINITY_REPLACEMENTS}"
        )
    normalized_text = raw_text.replace("\u221e", "Infinity")
    remaining = normalized_text.count("\u221e")
    if remaining:
        raise ExtractionError("Unity-normalized .anim still contains U+221E")
    normalized_bytes = normalized_text.encode("utf-8")
    if any(byte >= 128 for byte in normalized_bytes):
        raise ExtractionError("Unity-normalized .anim contains non-ASCII bytes")
    normalized_path.write_bytes(normalized_bytes)
    raw_snapshot = _snapshot(raw_path, with_hash=True)
    normalized_snapshot = _snapshot(normalized_path, with_hash=True)
    return {
        "replacementCount": replacement_count,
        "remainingInfinityCodepoints": remaining,
        "asciiOnly": True,
        "token": "Infinity",
        "rawSha256": raw_snapshot["sha256"],
        "rawBytes": raw_snapshot["bytes"],
        "normalizedSha256": normalized_snapshot["sha256"],
        "normalizedBytes": normalized_snapshot["bytes"],
    }


def _validate_normalized_anim(
    raw_path: Path,
    normalized_path: Path,
    expected_metrics: dict[str, Any],
) -> dict[str, Any]:
    raw_snapshot = _snapshot(raw_path, with_hash=True)
    normalized_snapshot = _snapshot(normalized_path, with_hash=True)
    if expected_metrics.get("replacementCount") != EXPECTED_INFINITY_REPLACEMENTS:
        raise ExtractionError("stage normalized .anim replacement count is not 121")
    if expected_metrics.get("remainingInfinityCodepoints") != 0:
        raise ExtractionError("stage normalized .anim records residual U+221E")
    if expected_metrics.get("asciiOnly") is not True:
        raise ExtractionError("stage normalized .anim is not recorded as ASCII-only")
    if expected_metrics.get("rawSha256") != raw_snapshot.get("sha256"):
        raise ExtractionError("stage raw .anim hash changed after normalization")
    if expected_metrics.get("rawBytes") != raw_snapshot.get("bytes"):
        raise ExtractionError("stage raw .anim byte count changed after normalization")
    if expected_metrics.get("normalizedSha256") != normalized_snapshot.get("sha256"):
        raise ExtractionError("stage normalized .anim hash drifted")
    if expected_metrics.get("normalizedBytes") != normalized_snapshot.get("bytes"):
        raise ExtractionError("stage normalized .anim byte count drifted")
    try:
        text = normalized_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ExtractionError(f"stage normalized .anim is unreadable: {normalized_path}: {exc}") from exc
    if text.count("\u221e") != 0:
        raise ExtractionError("stage normalized .anim still contains U+221E")
    if not text or any(byte >= 128 for byte in text.encode("utf-8")):
        raise ExtractionError("stage normalized .anim contains non-ASCII text")
    if text.count("Infinity") < EXPECTED_INFINITY_REPLACEMENTS:
        raise ExtractionError("stage normalized .anim lost expected Infinity tokens")
    return expected_metrics


def _exact_hash_mapping_attempt(root: Path, path_hashes: Iterable[int]) -> dict[str, Any]:
    """Search authored Endminf hierarchy/TOS text for exact decimal hashes.

    A hit is evidence to inspect, not a mapping: resolving still requires one
    authored transform path.  This deliberately does not inspect unrelated
    FX stages or assign a name from hash/order.
    """
    hashes = sorted({int(value) for value in path_hashes})
    matches: dict[str, list[str]] = {str(value): [] for value in hashes}
    if not root.exists():
        return {
            "path": _relative(root),
            "exists": False,
            "matches": matches,
            "result": "source_missing",
        }
    suffixes = {".json", ".yaml", ".yml", ".prefab", ".asset", ".controller", ".txt"}
    patterns = {value: re.compile(rf"(?<![0-9]){value}(?![0-9])") for value in hashes}
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or candidate.suffix.casefold() not in suffixes:
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for value, pattern in patterns.items():
            if pattern.search(text):
                matches[str(value)].append(_relative(candidate))
    result = (
        "hash_hits_but_no_unique_authored_transform_path"
        if any(matches.values())
        else "no_exact_path_hash_to_unique_transform_mapping"
    )
    return {"path": _relative(root), "exists": True, "matches": matches, "result": result}


def _binding_gap_report(clip_value: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """Report only exact path-hash evidence; never infer actor bone names."""
    generic = ((clip_value.get("m_ClipBindingConstant") or {}).get("genericBindings"))
    if not isinstance(generic, list):
        raise ExtractionError("cannot build binding gap report from malformed genericBindings")
    grouped: dict[int, list[dict[str, Any]]] = {}
    for index, binding in enumerate(generic):
        if not isinstance(binding, dict):
            raise ExtractionError(f"generic binding {index} is malformed")
        try:
            path_hash = int(binding["path"])
            attribute = int(binding["attribute"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ExtractionError(f"generic binding {index} lacks exact path/attribute") from exc
        if binding.get("typeID") != "Transform":
            raise ExtractionError(f"generic binding {index} is not a Transform binding")
        grouped.setdefault(path_hash, []).append(
            {"index": index, "attribute": attribute, "typeID": "Transform"}
        )
    if len(generic) != 9 or len(grouped) != 3:
        raise ExtractionError(
            f"binding gap contract requires 9 bindings and 3 unique path hashes; "
            f"found {len(generic)} and {len(grouped)}"
        )
    rows = [
        {
            "pathHash": path_hash,
            "bindingCount": len(entries),
            "attributes": sorted(entry["attribute"] for entry in entries),
            "bindings": entries,
            "status": "unresolved_no_unique_actor_hierarchy_or_tos_mapping",
        }
        for path_hash, entries in sorted(grouped.items())
    ]
    path_hashes = [row["pathHash"] for row in rows]
    hierarchy_attempt = _exact_hash_mapping_attempt(DEFAULT_ACTOR_HIERARCHY_ROOT, path_hashes)
    tos_attempt = _exact_hash_mapping_attempt(DEFAULT_ACTOR_TOS, path_hashes)
    return {
        "schema": "endfield.endminf.actor-animation-binding-gaps.v1",
        "status": "ok_with_unresolved_bindings",
        "identity": identity,
        "bindingCount": len(generic),
        "uniquePathHashCount": len(rows),
        "rows": rows,
        "mappingAttempts": [
            {"kind": "existing_endminf_actor_hierarchy", **hierarchy_attempt},
            {"kind": "endminf_actor_tos_manifest", **tos_attempt},
        ],
        "resolutionRule": "only an exact unique path-hash plus authored actor hierarchy/TOS path may resolve; no name/order guess",
        "unresolvedReason": "the three hashes have no unique mapping in the existing Endminf actor hierarchy/TOS evidence",
    }


def _validate_binding_gap_report(
    path: Path, clip_value: dict[str, Any], identity: dict[str, Any]
) -> dict[str, Any]:
    report = _json(path)
    if not isinstance(report, dict) or report.get("identity") != identity:
        raise ExtractionError("binding gap report identity is missing or drifted")
    expected = _binding_gap_report(clip_value, identity)
    if report != expected:
        raise ExtractionError("binding gap report drifted from exact serialized bindings")
    for row in report["rows"]:
        if row.get("status") != "unresolved_no_unique_actor_hierarchy_or_tos_mapping":
            raise ExtractionError("binding gap report contains a guessed or resolved mapping")
    return report


def _safe_reset(output: Path, *, force: bool) -> None:
    allowed = (PROJECT_ROOT / "Temp" / "Codex").resolve()
    resolved = output.resolve()
    try:
        relative = resolved.relative_to(allowed)
    except ValueError as exc:
        raise ExtractionError(f"output is outside scoped Temp/Codex root: {output}") from exc
    if not relative.parts:
        raise ExtractionError("refusing to clear Temp/Codex itself")
    if not output.exists():
        return
    stamp = output / ".character_import_stage.json"
    if not force:
        raise ExtractionError(f"output already exists; pass --force to replace only {output}")
    if output.is_dir():
        shutil.rmtree(output)
    else:
        output.unlink()


def _load_existing_if_exact(output: Path, expected_identity: dict[str, Any]) -> dict[str, Any] | None:
    stamp_path = output / ".character_import_stage.json"
    if not stamp_path.is_file():
        return None
    stamp = _json(stamp_path)
    identity = stamp.get("identity") if isinstance(stamp, dict) else None
    if identity == expected_identity and stamp.get("status") == "ok":
        return stamp
    raise ExtractionError("existing stage stamp does not match the requested exact identity; use --force")


def _validate_file_snapshot(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    current = _snapshot(path, with_hash="sha256" in expected)
    for key in ("path", "bytes", "mtime_ns", "sha256"):
        if key in expected and current.get(key) != expected.get(key):
            raise ExtractionError(f"stage file provenance is stale for {path}: {key}")
    return current


def _validate_filter_file(path: Path, target: dict[str, Any], expected_row: dict[str, Any]) -> None:
    value = _json(path)
    if not isinstance(value, list) or len(value) != 1 or value[0] != expected_row:
        raise ExtractionError("stage filter_data is not the one exact AssetMap row")
    row = value[0]
    expected = {
        "Name": target["name"],
        "Type": target["type"],
        "PathID": target["pathId"],
        "Offset": target["offset"],
    }
    for key in ("Name", "Type", "PathID", "Offset", "Source"):
        if key == "Source":
            matches = _normal_path(row.get(key)) == target["source"]
        elif key in {"PathID", "Offset"}:
            matches = int(row.get(key) or 0) == expected[key]
        else:
            matches = row.get(key) == expected[key]
        if not matches:
            raise ExtractionError(f"stage filter_data identity drifted at {key}")


def _validate_existing_stage(
    *,
    output: Path,
    identity: dict[str, Any],
    target: dict[str, Any],
    row: dict[str, Any],
    cab: dict[str, Any],
    asset_map_path: Path,
    cab_map_path: Path,
) -> dict[str, Any]:
    stamp_path = output / ".character_import_stage.json"
    stamp = _json(stamp_path)
    if not isinstance(stamp, dict) or stamp.get("schema") != STAGE_SCHEMA or stamp.get("status") != "ok":
        raise ExtractionError("stage stamp is not a terminal successful exact extraction")
    if stamp.get("identity") != identity:
        raise ExtractionError("stage stamp identity differs from the requested exact target")
    current_source = _snapshot(Path(identity["source"]))
    source_freshness = stamp.get("sourceFreshness") or {}
    expected_source = source_freshness.get("expected")
    if source_freshness.get("status") != "validated" or expected_source is None:
        raise ExtractionError("stage source freshness is not validated")
    if current_source.get("bytes") != expected_source.get("bytes") or current_source.get("mtime_ns") != expected_source.get("mtime_ns"):
        raise ExtractionError("stage source provenance is stale")
    filter_record = stamp.get("filterData") or {}
    filter_path = Path(filter_record.get("path") or "")
    _validate_file_snapshot(filter_path, filter_record)
    _validate_filter_file(filter_path, target, row)
    object_index_record = stamp.get("objectIndex") or {}
    object_index_path_record = object_index_record.get("path") or {}
    object_index_path = Path(object_index_path_record.get("path") or "")
    _validate_file_snapshot(object_index_path, object_index_path_record)
    object_index = _object_index_summary(object_index_path, identity)
    if object_index != object_index_record.get("summary"):
        raise ExtractionError("stage object_index_jsonl summary drifted")
    artifact_group = stamp.get("artifact") or {}
    json_artifact = (artifact_group.get("json") or {}).get("path") or {}
    convert_artifact = (artifact_group.get("convert") or {}).get("path") or {}
    normalized_artifact = (artifact_group.get("normalized") or {}).get("path") or {}
    binding_gap_record = stamp.get("bindingGaps") or {}
    binding_gap_path_record = binding_gap_record.get("path") or {}
    binding_gap_path = Path(binding_gap_path_record.get("path") or "")
    _validate_file_snapshot(binding_gap_path, binding_gap_path_record)
    artifact_path = Path(json_artifact.get("path") or "")
    converted_path = Path(convert_artifact.get("path") or "")
    normalized_path = Path(normalized_artifact.get("path") or "")
    _validate_file_snapshot(artifact_path, json_artifact)
    _validate_file_snapshot(converted_path, convert_artifact)
    _validate_file_snapshot(normalized_path, normalized_artifact)
    clip_value = _json(artifact_path)
    if not isinstance(clip_value, dict):
        raise ExtractionError("stage AnimationClip artifact is not an object")
    metrics = _clip_metrics(clip_value)
    converted_metrics = _converted_clip_metrics(converted_path)
    _assert_converted_matches_json(converted_metrics, metrics)
    if metrics != (artifact_group.get("json") or {}).get("metrics"):
        raise ExtractionError("stage JSON AnimationClip metrics drifted")
    if converted_metrics != (artifact_group.get("convert") or {}).get("metrics"):
        raise ExtractionError("stage converted AnimationClip metrics drifted")
    normalized_metrics = (artifact_group.get("normalized") or {}).get("metrics") or {}
    _validate_normalized_anim(converted_path, normalized_path, normalized_metrics)
    binding_gap = _validate_binding_gap_report(binding_gap_path, clip_value, identity)
    if binding_gap != binding_gap_record.get("value"):
        raise ExtractionError("stage binding gap report stamp/file values differ")
    terminal_summary = stamp.get("terminalSummary") or {}
    if terminal_summary.get("complete") is not True or terminal_summary.get("errors") != []:
        raise ExtractionError("stage terminal summary is not complete and error-free")
    if terminal_summary.get("counts") != object_index.get("counts"):
        raise ExtractionError("stage terminal summary counts differ from object_index_jsonl")
    for key in ("source", "cab", "pathId", "type", "name"):
        if terminal_summary.get(key) != object_index.get(key) or terminal_summary.get(key) != identity.get(key):
            raise ExtractionError(f"stage terminal summary identity drifted at {key}")
    provenance_record = (stamp.get("objectProvenance") or {}).get("path") or {}
    provenance_path = Path(provenance_record.get("path") or "")
    _validate_file_snapshot(provenance_path, provenance_record)
    provenance = _json(provenance_path)
    if not isinstance(provenance, dict) or provenance.get("status") != "ok" or provenance.get("identity") != identity:
        raise ExtractionError("stage object provenance is missing or drifted")
    if provenance != (stamp.get("objectProvenance") or {}).get("value"):
        raise ExtractionError("stage object provenance stamp/file values differ")
    cli_record = stamp.get("cli") or {}
    _validate_file_snapshot(Path(cli_record.get("path") or ""), cli_record)
    log_record = stamp.get("log") or {}
    log_path = Path(log_record.get("path") or "")
    _validate_file_snapshot(log_path, log_record)
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\bExport .* error\b|\[Error\]", log_text):
        raise ExtractionError("stage AnimeStudio log contains an export error")
    # Re-join the current maps, so an old stamp cannot mask a changed map.
    if _asset_map_row(asset_map_path, target) != row or _cab_row(cab_map_path, target) != cab:
        raise ExtractionError("stage source-map provenance differs from current maps")
    print(
        f"checked {output}: name={metrics['name']} length={metrics['lengthSeconds']}s "
        f"sampleRate={metrics['sampleRate']} bindings={metrics['bindingCounts']['totalBindingEntries']} "
        "objectProvenance=validated"
    )
    return stamp


def _run_cli(
    *,
    source: Path,
    output: Path,
    filter_path: Path,
    cli_log: Path,
    export_type: str,
    identity: dict[str, Any],
    object_index_path: Path | None = None,
) -> None:
    command = [
        str(ANIMESTUDIO_CLI),
        str(source),
        str(output),
        "--game",
        "ArknightsEndfield",
        "--types",
        *( ["AnimationClip:Both", "MonoBehaviour:Parse"] if object_index_path is not None else ["AnimationClip:Both"] ),
        "--export_type",
        export_type,
        "--group_assets",
        "ByType",
        "--logger_flags",
        "Warning",
        "Error",
        "--filter_data",
        str(filter_path),
    ]
    if object_index_path is not None:
        command.extend(["--object_index_jsonl", str(object_index_path)])
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    with cli_log.open("a", encoding="utf-8") as handle:
        handle.write(
            "COMMAND: " + subprocess.list2cmdline(command) + "\n\n"
            + "STDOUT:\n" + completed.stdout
            + "\nSTDERR:\n" + completed.stderr + "\n"
        )
    if completed.returncode != 0:
        raise ExtractionError(f"AnimeStudio targeted extraction failed with exit code {completed.returncode}")
    log_text = completed.stdout + "\n" + completed.stderr
    errors = [line for line in log_text.splitlines() if re.search(r"\bExport .* error\b|\[Error\]", line)]
    if errors:
        raise ExtractionError(f"AnimeStudio targeted extraction reported {len(errors)} error log lines")


def extract(
    *,
    closure_path: Path,
    asset_map_path: Path,
    cab_map_path: Path,
    output: Path,
    force: bool,
    dry_run: bool,
    check: bool,
) -> dict[str, Any]:
    if not ANIMESTUDIO_CLI.is_file():
        raise ExtractionError(f"AnimeStudio CLI is missing: {ANIMESTUDIO_CLI}")
    target = _target_from_closure(closure_path)
    row = _asset_map_row(asset_map_path, target)
    cab = _cab_row(cab_map_path, target)
    current_source = Path(str(row["Source"]))
    source_snapshot = _snapshot(current_source)
    expected_source = target.get("expectedSourceSnapshot")
    if expected_source is not None and source_snapshot != {
        "path": source_snapshot["path"],
        "bytes": int(expected_source["bytes"]),
        "mtime_ns": int(expected_source["mtime_ns"]),
    }:
        raise ExtractionError(
            "installed source freshness differs from the playback-closure snapshot: "
            f"{current_source}"
        )
    if str(cab["cab"]).casefold() != target["cab"].casefold():
        raise ExtractionError("CABMap resolved a different CAB than the playback closure")
    identity = {
        "name": target["name"],
        "type": target["type"],
        "pathId": target["pathId"],
        "pathIdHex": _unsigned_hex(target["pathId"]),
        "source": source_snapshot["path"],
        "sourceOffset": target["offset"],
        "cab": cab["cab"],
        "container": target["container"],
    }
    output = output.resolve()
    if check:
        if not output.is_dir():
            raise ExtractionError(f"stage does not exist for --check: {output}")
        return _validate_existing_stage(
            output=output,
            identity=identity,
            target=target,
            row=row,
            cab=cab,
            asset_map_path=asset_map_path,
            cab_map_path=cab_map_path,
        )
    if output.exists() and not force:
        # Reuse is never stamp-only: stale files, sidecar counts, normalized
        # bytes, binding gaps, and current source maps all go through the same
        # complete validator used by --check.
        return _validate_existing_stage(
            output=output,
            identity=identity,
            target=target,
            row=row,
            cab=cab,
            asset_map_path=asset_map_path,
            cab_map_path=cab_map_path,
        )
    _safe_reset(output, force=force)
    output.mkdir(parents=True, exist_ok=True)
    filters = output / "filters"
    filters.mkdir()
    object_index_dir = output / "object_index"
    object_index_dir.mkdir()
    filter_path = filters / f"endminf_actor_overview_02_001_{Path(current_source).stem}.json"
    filter_path.write_text(json.dumps([row], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    object_index_path = object_index_dir / (
        f"endminf_actor_overview_02_001_{Path(current_source).stem}.jsonl"
    )
    cli_log = output / "animestudio.log"
    cli_snapshot = _snapshot(ANIMESTUDIO_CLI, with_hash=True)
    if not dry_run:
        _run_cli(
            source=current_source,
            output=output,
            filter_path=filter_path,
            cli_log=cli_log,
            export_type="JSON",
            identity=identity,
            object_index_path=object_index_path,
        )
        object_index = _annotate_object_index(object_index_path, identity)
        _run_cli(
            source=current_source,
            output=output,
            filter_path=filter_path,
            cli_log=cli_log,
            export_type="Convert",
            identity=identity,
        )
    expected_file = output / "AnimationClip" / f"{TARGET_NAME}_p{_unsigned_hex(target['pathId'])}.json"
    expected_converted_file = output / "AnimationClip" / f"{TARGET_NAME}_p{_unsigned_hex(target['pathId'])}.anim"
    normalized_file = output / "AnimationClip" / (
        f"{TARGET_NAME}_p{_unsigned_hex(target['pathId'])}_unity_normalized.anim"
    )
    binding_gap_file = output / "binding_gaps.json"
    if dry_run:
        report = {
            "schema": STAGE_SCHEMA,
            "status": "planned",
            "identity": identity,
            "sourceFreshness": {"status": "validated", "current": source_snapshot, "expected": expected_source},
            "cabMap": cab,
            "filterData": _relative(filter_path),
            "objectIndex": _relative(object_index_path),
            "cli": cli_snapshot,
            "output": _relative(output),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report

    if not expected_file.is_file():
        raise ExtractionError(f"targeted extraction did not produce exact AnimationClip JSON: {expected_file}")
    if not expected_converted_file.is_file():
        raise ExtractionError(f"targeted conversion did not produce exact AnimationClip YAML: {expected_converted_file}")
    if not object_index_path.is_file():
        raise ExtractionError(f"targeted JSON export did not produce object_index_jsonl: {object_index_path}")
    object_index = _object_index_summary(object_index_path, identity)
    clip_value = _json(expected_file)
    if not isinstance(clip_value, dict):
        raise ExtractionError("AnimationClip JSON is not an object")
    metrics = _clip_metrics(clip_value)
    converted_metrics = _converted_clip_metrics(expected_converted_file)
    _assert_converted_matches_json(converted_metrics, metrics)
    normalized_metrics = _normalize_anim(expected_converted_file, normalized_file)
    binding_gap = _binding_gap_report(clip_value, identity)
    binding_gap_file.write_text(
        json.dumps(binding_gap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _validate_binding_gap_report(binding_gap_file, clip_value, identity)
    artifact_snapshot = _snapshot(expected_file, with_hash=True)
    converted_snapshot = _snapshot(expected_converted_file, with_hash=True)
    normalized_snapshot = _snapshot(normalized_file, with_hash=True)
    filter_snapshot = _snapshot(filter_path, with_hash=True)
    object_index_snapshot = _snapshot(object_index_path, with_hash=True)
    binding_gap_snapshot = _snapshot(binding_gap_file, with_hash=True)
    terminal_summary = {
        "complete": True,
        "errors": [],
        "counts": object_index["counts"],
        "source": identity["source"],
        "cab": identity["cab"],
        "pathId": identity["pathId"],
        "type": identity["type"],
        "name": identity["name"],
    }
    object_provenance = {
        "schema": "endfield.exact-object-provenance.v1",
        "status": "ok",
        "identity": identity,
        "assetMap": {"path": _relative(asset_map_path), "row": row},
        "cabMap": {"path": _relative(cab_map_path), "row": cab},
        "sourceSnapshot": source_snapshot,
        "filterData": filter_snapshot,
        "artifacts": {
            "json": artifact_snapshot,
            "convert": converted_snapshot,
            "normalized": normalized_snapshot,
            "objectIndex": object_index_snapshot,
            "bindingGaps": binding_gap_snapshot,
        },
        "metrics": {
            "json": metrics,
            "convert": converted_metrics,
            "normalized": normalized_metrics,
            "bindingGaps": binding_gap,
        },
        "objectIndex": {"summary": object_index, "types": ["AnimationClip:Both", "MonoBehaviour:Parse"]},
        "terminalSummary": terminal_summary,
        "selection": "source+offset+signed PathID+type+name exact join; no name-only fallback",
    }
    object_provenance_path = output / "object_provenance.json"
    object_provenance_path.write_text(
        json.dumps(object_provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    stamp = {
        "schema": STAGE_SCHEMA,
        "status": "ok",
        "identity": identity,
        "sourceFreshness": {
            "status": "validated",
            "current": source_snapshot,
            "expected": expected_source,
        },
        "assetMap": {"path": _relative(asset_map_path), "row": row},
        "cabMap": {"path": _relative(cab_map_path), "row": cab},
        "cli": cli_snapshot,
        "filterData": filter_snapshot,
        "objectIndex": {
            "path": object_index_snapshot,
            "summary": object_index,
            "types": ["AnimationClip:Both", "MonoBehaviour:Parse"],
        },
        "terminalSummary": terminal_summary,
        "objectProvenance": {
            "path": _snapshot(object_provenance_path, with_hash=True),
            "value": object_provenance,
        },
        "artifact": {
            "json": {"path": artifact_snapshot, "metrics": metrics},
            "convert": {"path": converted_snapshot, "metrics": converted_metrics},
            "normalized": {"path": normalized_snapshot, "metrics": normalized_metrics},
        },
        "bindingGaps": {"path": binding_gap_snapshot, "value": binding_gap},
        "log": _snapshot(cli_log, with_hash=True),
        "evidenceBoundary": (
            "one exact AnimationClip selected by closure AssetMap identity and CABMap source/offset; "
            "serialized clip timing/binding evidence only, no actor mount or runtime playback claim"
        ),
    }
    (output / ".character_import_stage.json").write_text(
        json.dumps(stamp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "endminf_actor_overview_02_stage.json").write_text(
        json.dumps(stamp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {output}: name={metrics['name']} length={metrics['lengthSeconds']}s "
        f"sampleRate={metrics['sampleRate']} bindings={metrics['bindingCounts']['totalBindingEntries']} "
        f"objectProvenance=validated"
    )
    return stamp


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--closure", type=Path, default=DEFAULT_CLOSURE)
    parser.add_argument("--asset-map", type=Path, default=DEFAULT_ASSET_MAP)
    parser.add_argument("--cab-map", type=Path, default=DEFAULT_CAB_MAP)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true", help="validate an existing exact stage without running AnimeStudio")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        extract(
            closure_path=args.closure,
            asset_map_path=args.asset_map,
            cab_map_path=args.cab_map,
            output=args.output,
            force=args.force,
            dry_run=args.dry_run,
            check=args.check,
        )
        return 0
    except (ExtractionError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
