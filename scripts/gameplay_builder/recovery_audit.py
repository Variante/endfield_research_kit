"""Audit generated Gameplay action recovery coverage.

The Gameplay index is a generated artifact, so this module deliberately does
not inspect serialized buffers or infer new semantics.  It records the
decoder's published evidence and compares two reports to make regressions and
schema changes visible after a rebuild.

Example::

    python -m scripts.gameplay_builder.recovery_audit
    python -m scripts.gameplay_builder.recovery_audit --previous old.json

The default outputs are ignored generated reports under ``reports/gameplay``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "webui" / "data" / "lang" / "CN" / "gameplay" / "index.json"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "gameplay"
REPORT_SCHEMA_VERSION = "gameplay-recovery-audit.v2"
BRANCH_FIELDS = ("conditionAction", "failActions", "succeedActions")
HEX_TOKEN_RE = re.compile(r"^0x[0-9a-fA-F]+$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
FULL_ERROR_SAMPLE_LIMIT = 64
FULL_BUFF_FILENAME_RE = re.compile(r"^buff_[A-Za-z0-9_]+\.json$")


def _json_path(parts: tuple[object, ...]) -> str:
    """Render a deterministic, human-readable JSON path."""

    result = ""
    for part in parts:
        if isinstance(part, int):
            result += f"[{part}]"
        else:
            result += "." + str(part) if result else str(part)
    return result


def _value(value: Any, default: str = "<missing>") -> str:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _action_fields(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    decoded = item.get("decoded")
    if not isinstance(decoded, dict):
        decoded = {}
    action_type = _value(item.get("name") or decoded.get("type") or item.get("type"))
    status = _value(item.get("decodeStatus") or decoded.get("decodeStatus"))
    semantic_status = _value(
        item.get("semanticStatus") or decoded.get("semanticStatus")
    )
    member_count = _value(item.get("memberCount") or decoded.get("memberCount"))
    tag = _value(item.get("tag"))
    return action_type, status, semantic_status, member_count, tag


def _iter_root_sequences(
    payload: dict[str, Any], structure: list[dict[str, Any]] | None = None,
) -> Iterator[tuple[str, tuple[object, ...], dict[str, Any]]]:
    """Yield only authored SequenceActionData roots from the Buff index."""

    if structure is None:
        structure = []

    def malformed(kind: str, owner: str, path: tuple[object, ...], expected: Any, actual: Any) -> None:
        structure.append({
            "kind": kind,
            "severity": "error",
            "owner": owner,
            "path": _json_path(path),
            "expected": expected,
            "actual": actual,
        })

    buffs = payload.get("buffs")
    if not isinstance(buffs, dict):
        malformed("invalid-buffs", "<root>", ("buffs",), "object", type(buffs).__name__)
        return
    for owner in sorted(buffs):
        buff = buffs[owner]
        if not isinstance(buff, dict):
            malformed("invalid-buff", owner, ("buffs", owner), "object", type(buff).__name__)
            continue
        buff_path = ("buffs", owner)
        if "abilityEventActions" not in buff:
            malformed(
                "invalid-buff-events", owner, buff_path + ("abilityEventActions",),
                "list", "<missing>",
            )
            continue
        events = buff.get("abilityEventActions")
        if not isinstance(events, list):
            malformed(
                "invalid-buff-events", owner, buff_path + ("abilityEventActions",),
                "list", type(events).__name__,
            )
            continue
        for event_index, event in enumerate(events):
            event_path = buff_path + ("abilityEventActions", event_index)
            if not isinstance(event, dict):
                malformed("invalid-event", owner, event_path, "object", type(event).__name__)
                continue
            if "actions" not in event:
                malformed("invalid-event-actions", owner, event_path + ("actions",), "list", "<missing>")
                continue
            if not isinstance(event.get("actions"), list):
                malformed(
                    "invalid-event-actions", owner, event_path + ("actions",),
                    "list", type(event.get("actions")).__name__,
                )
                continue
            for sequence_index, sequence in enumerate(event["actions"]):
                sequence_path = event_path + ("actions", sequence_index)
                if not isinstance(sequence, dict):
                    malformed("invalid-root-sequence", owner, sequence_path, "object", type(sequence).__name__)
                    continue
                if "actionDataCount" not in sequence or "actionDataItems" not in sequence:
                    malformed(
                        "invalid-root-sequence", owner, sequence_path,
                        "object with actionDataCount and actionDataItems",
                        "missing required field",
                    )
                yield owner, sequence_path, sequence


def _row(
    item: dict[str, Any], owner: str, path: tuple[object, ...]
) -> dict[str, Any]:
    action_type, status, semantic_status, member_count, tag = _action_fields(item)
    decoded = item.get("decoded")
    source = decoded.get("source") if isinstance(decoded, dict) else None
    source_path = source.get("path") if isinstance(source, dict) else None
    item_path = _json_path(path)
    offset = _value(item.get("offset"))
    byte_count = _value(item.get("bytes"))
    tag_value = _value(item.get("tag"))
    return {
        "id": f"{owner}:{offset}:{byte_count}:{tag_value}",
        "owner": owner,
        "path": item_path,
        "offset": offset,
        "bytes": byte_count,
        "actionType": action_type,
        "status": status,
        "decodeStatus": status,
        "semanticStatus": semantic_status,
        "memberCount": member_count,
        "tag": tag,
        "sourcePath": _value(source_path, "<missing>"),
        "boundaryProof": _value(item.get("boundaryProof"), "<missing>"),
    }


def _branch_valid(branch: Any) -> bool:
    return (
        isinstance(branch, dict)
        and isinstance(branch.get("actionDataItems"), list)
        and isinstance(branch.get("actionDataCount"), int)
        and not isinstance(branch.get("actionDataCount"), bool)
    )


def _summary_field_errors(
    item: dict[str, Any], owner: str, path: tuple[object, ...],
) -> list[dict[str, Any]]:
    checks = (
        ("offset", lambda value: isinstance(value, str) and HEX_TOKEN_RE.fullmatch(value) is not None, "hex string (0x...)"),
        ("bytes", lambda value: isinstance(value, int) and not isinstance(value, bool) and value >= 0, "non-negative integer"),
        ("tag", lambda value: isinstance(value, str) and HEX_TOKEN_RE.fullmatch(value) is not None, "hex string (0x...)"),
        ("memberCount", lambda value: isinstance(value, int) and not isinstance(value, bool) and value >= 0, "non-negative integer"),
    )
    errors = []
    for field, valid, expected in checks:
        value = item.get(field)
        if valid(value):
            continue
        errors.append({
            "kind": "invalid-action-summary-field",
            "severity": "error",
            "owner": owner,
            "path": _json_path(path),
            "field": field,
            "expected": expected,
            "actual": "<missing>" if field not in item else value,
        })
    return errors


def _walk_sequence(
    sequence: dict[str, Any], owner: str, sequence_path: tuple[object, ...],
    structure: list[dict[str, Any]], sequence_nodes: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Walk a sequence and only its three explicitly typed nested branches."""

    items = sequence.get("actionDataItems")
    expected = sequence.get("actionDataCount")
    actual = len(items) if isinstance(items, list) else 0
    expected_valid = isinstance(expected, int) and not isinstance(expected, bool) and expected >= 0
    sequence_text = _json_path(sequence_path)
    sequence_nodes.append({
        "owner": owner,
        "path": sequence_text,
        "kind": "root" if len(sequence_path) >= 2 and sequence_path[-2] == "actions" else "nested",
        "authored": expected if expected_valid else 0,
        "materialized": actual,
        "unmaterialized": max((expected - actual), 0) if expected_valid else 0,
    })
    if not expected_valid or not isinstance(items, list):
        structure.append({
            "kind": "invalid-sequence-shape",
            "severity": "error",
            "owner": owner,
            "path": sequence_text,
            "expected": "integer actionDataCount and list actionDataItems",
            "actual": {
                "actionDataCount": expected if expected is not None else "<missing>",
                "actionDataItems": type(items).__name__,
            },
        })
    if not expected_valid or expected != actual:
        structure.append({
            "kind": "sequence-count-mismatch",
            "severity": "error",
            "owner": owner,
            "path": sequence_text,
            "expected": expected if expected is not None else "<missing>",
            "actual": actual,
        })
    if not isinstance(items, list):
        return
    for index, item in enumerate(items):
        item_path = sequence_path + ("actionDataItems", index)
        if not isinstance(item, dict):
            structure.append({
                "kind": "invalid-action-item",
                "severity": "error",
                "owner": owner,
                "path": _json_path(item_path),
                "expected": "object",
                "actual": type(item).__name__,
            })
            continue
        structure.extend(_summary_field_errors(item, owner, item_path))
        row = _row(item, owner, item_path)
        decoded = item.get("decoded")
        if row["status"] == "exact" and item.get("boundaryProof") != "typed-consumption":
            structure.append({
                "kind": "exact-boundary-proof-invalid",
                "severity": "error",
                "owner": owner,
                "path": _json_path(item_path),
                "field": "boundaryProof",
                "expected": "typed-consumption",
                "actual": item.get("boundaryProof", "<missing>"),
            })
        if not isinstance(decoded, dict):
            structure.append({
                "kind": "invalid-decoded-action",
                "severity": "error",
                "owner": owner,
                "path": _json_path(item_path),
                "expected": "object",
                "actual": type(decoded).__name__,
            })
        else:
            checks = (
                ("status", item.get("decodeStatus"), decoded.get("decodeStatus")),
                ("type", item.get("name"), decoded.get("type")),
                ("bytes", item.get("bytes"), decoded.get("byteLength")),
                ("semanticStatus", item.get("semanticStatus"), decoded.get("semanticStatus")),
                ("memberCount", item.get("memberCount"), decoded.get("memberCount")),
            )
            for field, summary, decoded_value in checks:
                both_sides_required = field in {"semanticStatus", "memberCount"}
                comparable = (
                    summary is not None and decoded_value is not None
                    if both_sides_required
                    else (summary is not None or decoded_value is not None)
                )
                if comparable and summary != decoded_value:
                    structure.append({
                        "kind": "summary-decoded-mismatch",
                        "severity": "error",
                        "owner": owner,
                        "path": _json_path(item_path),
                        "field": field,
                        "expected": summary,
                        "actual": decoded_value,
                    })
            for branch_name in BRANCH_FIELDS:
                if branch_name not in decoded:
                    continue
                branch = decoded[branch_name]
                branch_path = item_path + ("decoded", branch_name)
                if not _branch_valid(branch):
                    structure.append({
                        "kind": "invalid-nested-branch",
                        "severity": "error",
                        "owner": owner,
                        "path": _json_path(branch_path),
                        "field": branch_name,
                        "expected": "object with integer actionDataCount and list actionDataItems",
                        "actual": type(branch).__name__,
                    })
                    continue
                yield from _walk_sequence(branch, owner, branch_path, structure, sequence_nodes)
        yield row


def _collect_occurrences(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    structure: list[dict[str, Any]] = []
    sequence_nodes: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for owner, path, sequence in _iter_root_sequences(payload, structure):
        rows.extend(_walk_sequence(sequence, owner, path, structure, sequence_nodes))
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_id.setdefault(str(row["id"]), []).append(row)
    for occurrence_id in sorted(by_id):
        duplicate_rows = by_id[occurrence_id]
        if len(duplicate_rows) < 2:
            continue
        for row in duplicate_rows:
            structure.append({
                "kind": "duplicate-occurrence-id",
                "severity": "error",
                "owner": row["owner"],
                "path": row["path"],
                "expected": "unique canonical occurrence id",
                "actual": occurrence_id,
            })
    rows.sort(key=lambda row: str(row["id"]))
    structure.sort(key=lambda item: (
        str(item.get("kind")), str(item.get("owner")), str(item.get("path")),
        str(item.get("field", "")), str(item.get("expected", "")),
    ))
    sequence_nodes.sort(key=lambda item: (str(item["owner"]), str(item["path"])))
    return rows, sequence_nodes, structure


def iter_action_occurrences(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield root and explicitly typed nested action occurrences."""

    rows, _sequence_nodes, _structure = _collect_occurrences(payload)
    yield from rows


def _histogram(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = Counter(_value(row.get(key)) for row in rows)
    return {name: counts[name] for name in sorted(counts)}


def _pair_histogram(rows: list[dict[str, Any]], first: str, second: str) -> dict[str, int]:
    counts = Counter(
        f"{_value(row.get(first))}|{_value(row.get(second))}" for row in rows
    )
    return {name: counts[name] for name in sorted(counts)}


def _validate_previous(
    previous: Any, language: str, scope: str,
) -> tuple[list[dict[str, Any]] | None, dict[str, Any]]:
    if not isinstance(previous, dict):
        return None, {"status": "error", "reason": "previous report is not an object"}
    if previous.get("schemaVersion") != REPORT_SCHEMA_VERSION:
        return None, {
            "status": "error", "reason": "previous report schemaVersion mismatch",
            "expected": REPORT_SCHEMA_VERSION, "actual": previous.get("schemaVersion", "<missing>"),
        }
    if previous.get("language") != language:
        return None, {
            "status": "error", "reason": "previous report language mismatch",
            "expected": language, "actual": previous.get("language", "<missing>"),
        }
    if previous.get("scope") != scope:
        return None, {
            "status": "error", "reason": "previous report scope mismatch",
            "expected": scope, "actual": previous.get("scope", "<missing>"),
        }
    previous_content_hash = previous.get("contentSha256")
    if not isinstance(previous_content_hash, str) or SHA256_RE.fullmatch(previous_content_hash) is None:
        return None, {
            "status": "error", "reason": "previous report contentSha256 is invalid",
            "expected": "64 hexadecimal characters",
            "actual": previous_content_hash if previous_content_hash is not None else "<missing>",
        }
    if scope == "full":
        previous_full = previous.get("fullCorpus")
        if not isinstance(previous_full, dict):
            return None, {
                "status": "error", "reason": "previous full report fullCorpus is missing",
            }
        for field in ("selectedManifestSha256", "allSourceManifestSha256"):
            value = previous_full.get(field)
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                return None, {
                    "status": "error", "reason": f"previous full report {field} is invalid",
                    "expected": "64 hexadecimal characters",
                    "actual": value if value is not None else "<missing>",
                }
    rows = previous.get("occurrences")
    if not isinstance(rows, list):
        return None, {"status": "error", "reason": "previous report occurrences is not a list"}
    seen: set[str] = set()
    required = (
        "owner", "offset", "bytes", "tag", "actionType", "status",
        "semanticStatus", "memberCount", "boundaryProof",
    )
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return None, {"status": "error", "reason": "previous occurrence is not an object", "index": index}
        missing = [key for key in required if key not in row or row.get(key) in (None, "")]
        occurrence_id = row.get("id")
        if missing or not isinstance(occurrence_id, str) or not occurrence_id:
            return None, {
                "status": "error", "reason": "previous occurrence is malformed",
                "index": index, "missing": missing,
            }
        if row.get("status") == "exact" and row.get("boundaryProof") != "typed-consumption":
            return None, {
                "status": "error", "reason": "previous exact occurrence boundaryProof is invalid",
                "index": index, "expected": "typed-consumption",
                "actual": row.get("boundaryProof", "<missing>"),
            }
        expected_id = f"{row['owner']}:{row['offset']}:{row['bytes']}:{row['tag']}"
        if occurrence_id != expected_id:
            return None, {
                "status": "error", "reason": "previous occurrence canonical id mismatch",
                "index": index, "expected": expected_id, "actual": occurrence_id,
            }
        if occurrence_id in seen:
            return None, {
                "status": "error", "reason": "previous report has duplicate occurrence id",
                "actual": occurrence_id,
            }
        seen.add(occurrence_id)
    return rows, {"status": "valid", "occurrences": len(rows)}


def _diagnostics(
    current: list[dict[str, Any]], previous: dict[str, Any] | None, language: str,
    content_sha256_value: str | None, scope: str, full_corpus: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    current_hash = content_sha256_value or "<not-available>"
    previous_hash = (
        previous.get("contentSha256", "<missing>")
        if isinstance(previous, dict) else "<unavailable>"
    )
    same_input = current_hash != "<not-available>" and previous_hash == current_hash
    comparison_meta = {
        "currentContentSha256": current_hash,
        "previousContentSha256": previous_hash,
        "sameInput": same_input,
    }
    if previous is None:
        return [], {"status": "not-requested", "reviewRequired": False, **comparison_meta}
    previous_rows, validation = _validate_previous(previous, language, scope)
    if previous_rows is None:
        return [], {**validation, "reviewRequired": True, **comparison_meta}
    previous_by_id = {str(row["id"]): row for row in previous_rows}
    current_by_id = {str(row["id"]): row for row in current}
    diagnostics: list[dict[str, Any]] = []
    if scope == "full":
        current_full = full_corpus or {}
        previous_full = previous.get("fullCorpus") or {}
        for field in ("selectedManifestSha256", "allSourceManifestSha256"):
            current_manifest = current_full.get(field, "<missing>")
            previous_manifest = previous_full.get(field, "<missing>")
            if current_manifest != previous_manifest:
                diagnostics.append({
                    "kind": "full-manifest-changed", "severity": "warning",
                    "field": field, "expected": previous_manifest, "actual": current_manifest,
                })
    for occurrence_id in sorted(set(current_by_id) & set(previous_by_id)):
        old = previous_by_id[occurrence_id]
        new = current_by_id[occurrence_id]
        old_status = _value(old.get("status") or old.get("decodeStatus"))
        new_status = _value(new.get("status") or new.get("decodeStatus"))
        if old_status != new_status:
            if old_status == "exact" and new_status != "exact":
                kind, severity = "status-regression", "error"
            elif old_status != "exact" and new_status == "exact":
                kind, severity = "status-promotion", "info"
            else:
                kind, severity = "status-changed", "warning"
            diagnostics.append({
                "kind": kind, "severity": severity, "id": occurrence_id,
                "actionType": _value(new.get("actionType")),
                "previousStatus": old_status, "currentStatus": new_status,
            })
        old_semantic = _value(old.get("semanticStatus"))
        new_semantic = _value(new.get("semanticStatus"))
        if old_semantic != new_semantic:
            diagnostics.append({
                "kind": "semantic-status-changed", "severity": "warning", "id": occurrence_id,
                "actionType": _value(new.get("actionType")),
                "previousSemanticStatus": old_semantic, "currentSemanticStatus": new_semantic,
            })
        for field in ("actionType", "memberCount", "tag", "bytes"):
            old_shape = _value(old.get(field))
            new_shape = _value(new.get(field))
            if old_shape != new_shape:
                diagnostics.append({
                    "kind": "action-shape-changed", "severity": "warning", "id": occurrence_id,
                    "field": field, "expected": old_shape, "actual": new_shape,
                })

    current_ids = set(current_by_id)
    previous_ids = set(previous_by_id)
    current_exact = sum(1 for row in current if _value(row.get("status")) == "exact")
    previous_exact = sum(1 for row in previous_rows if _value(row.get("status")) == "exact")
    current_non_exact = len(current) - current_exact
    previous_non_exact = len(previous_rows) - previous_exact
    if current_exact < previous_exact:
        diagnostics.append({
            "kind": "exact-count-regression", "severity": "error",
            "expected": previous_exact, "actual": current_exact,
        })
    if current_non_exact > previous_non_exact:
        diagnostics.append({
            "kind": "non-exact-count-regression", "severity": "error",
            "expected": previous_non_exact, "actual": current_non_exact,
        })
    for occurrence_id in sorted(current_ids - previous_ids):
        diagnostics.append({"kind": "occurrence-added", "severity": "warning", "id": occurrence_id})
    for occurrence_id in sorted(previous_ids - current_ids):
        diagnostics.append({"kind": "occurrence-removed", "severity": "warning", "id": occurrence_id})

    current_families = _histogram(current, "actionType")
    previous_families = _histogram(previous_rows, "actionType")
    for family in sorted(set(current_families) | set(previous_families)):
        old_count, new_count = previous_families.get(family, 0), current_families.get(family, 0)
        if new_count < old_count:
            diagnostics.append({
                "kind": "family-count-regression", "severity": "error" if same_input else "warning", "family": family,
                "expected": old_count, "actual": new_count,
            })

    current_statuses = _histogram(current, "status")
    previous_statuses = _histogram(previous_rows, "status")
    for status in sorted(set(current_statuses) | set(previous_statuses)):
        old_count, new_count = previous_statuses.get(status, 0), current_statuses.get(status, 0)
        if new_count < old_count:
            diagnostics.append({
                "kind": "status-count-regression", "severity": "error" if status == "exact" else "info", "status": status,
                "expected": old_count, "actual": new_count,
            })

    current_tag_counts = _histogram(current, "tag")
    previous_tag_counts = _histogram(previous_rows, "tag")
    for tag in sorted(set(current_tag_counts) - set(previous_tag_counts)):
        diagnostics.append({"kind": "new-tag", "severity": "warning", "tag": tag, "count": current_tag_counts[tag]})

    current_member_pairs = _pair_histogram(current, "actionType", "memberCount")
    previous_member_pairs = _pair_histogram(previous_rows, "actionType", "memberCount")
    for pair in sorted(set(current_member_pairs) - set(previous_member_pairs)):
        action_type, member_count = pair.split("|", 1)
        diagnostics.append({
            "kind": "new-member-count", "severity": "warning", "actionType": action_type,
            "memberCount": member_count, "count": current_member_pairs[pair],
        })
    diagnostics.sort(key=lambda item: (
        str(item.get("kind")), str(item.get("id", "")), str(item.get("family", "")),
        str(item.get("status", "")), str(item.get("field", "")),
    ))
    review_required = any(
        item.get("severity") in {"warning", "error"} for item in diagnostics
    )
    return diagnostics, {
        "status": "compared", "previousOccurrences": len(previous_rows),
        "matchedOccurrences": len(current_ids & previous_ids),
        "newOccurrences": len(current_ids - previous_ids),
        "removedOccurrences": len(previous_ids - current_ids),
        "reviewRequired": review_required,
        **comparison_meta,
    }


def build_full_corpus_payload(export_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode every exported BuffData file with Persistent overlay precedence.

    This is intentionally an audit-only view.  It never writes or mutates the
    generated WebUI index and preserves bounded file/decode error samples.
    """

    if __package__ and __package__.startswith("scripts."):
        from scripts.game_data.memorypack.buff import buff_gameplay_semantics
    else:
        from game_data.memorypack.buff import buff_gameplay_semantics

    export_root = export_root.resolve()

    source_roots = {
        "StreamingAssets": export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "BuffData",
        "Persistent": export_root / "structured" / "Persistent" / "Data" / "Json" / "BuffData",
    }
    discovered: dict[str, dict[str, Path]] = {source: {} for source in source_roots}
    file_meta: dict[str, dict[str, dict[str, Any]]] = {source: {} for source in source_roots}
    manifest_hashes: dict[str, str] = {}
    root_status: dict[str, dict[str, Any]] = {}
    missing_roots: list[str] = []
    invalid_files: list[dict[str, Any]] = []
    error_samples: list[dict[str, Any]] = []
    error_count = 0
    invalid_file_count = 0
    source_file_counts: dict[str, int] = {}
    valid_file_counts: dict[str, int] = {}

    def relative(path: Path) -> str:
        return path.relative_to(export_root).as_posix() if path.is_relative_to(export_root) else path.as_posix()

    def evidence(path: Path) -> tuple[int | str, str, str | None]:
        try:
            data = path.read_bytes()
            return len(data), hashlib.sha256(data).hexdigest(), None
        except OSError as exc:
            return "<unavailable>", "<unavailable>", f"{type(exc).__name__}: {exc}"

    def add_error(kind: str, source: str, path: Path, detail: str) -> None:
        nonlocal error_count, invalid_file_count
        error_count += 1
        size, digest, _ = evidence(path)
        sample = {
            "kind": kind,
            "source": source,
            "file": relative(path),
            "relativePath": relative(path),
            "expected": "canonical BuffData file decodable by buff_gameplay_semantics",
            "actual": str(detail)[:500],
            "size": size,
            "sha256": digest,
            "detail": str(detail)[:500],
        }
        invalid_kind = kind in {"read-error", "unsupported-file", "parse-error", "decode-error"}
        if invalid_kind:
            invalid_file_count += 1
        if len(error_samples) < FULL_ERROR_SAMPLE_LIMIT:
            error_samples.append(sample)
        if invalid_kind:
            invalid_files.append(sample)

    for source, root in source_roots.items():
        root_path = root.relative_to(export_root).as_posix()
        if not root.is_dir():
            missing_roots.append(source)
            root_status[source] = {"status": "missing", "path": root_path, "fileCount": 0}
            source_file_counts[source] = 0
            valid_file_counts[source] = 0
            manifest_hashes[source] = hashlib.sha256(b"").hexdigest()
            continue
        try:
            paths = sorted((path for path in root.iterdir() if path.is_file()), key=lambda path: path.name)
        except OSError as exc:
            root_status[source] = {"status": "error", "path": root_path, "fileCount": 0}
            source_file_counts[source] = 0
            valid_file_counts[source] = 0
            add_error("read-error", source, root, f"{type(exc).__name__}: {exc}")
            manifest_hashes[source] = hashlib.sha256(b"").hexdigest()
            continue
        source_file_counts[source] = len(paths)
        valid_count = 0
        manifest_rows: list[str] = []
        for path in paths:
            size, digest, read_detail = evidence(path)
            manifest_rows.append(f"{path.name}\t{digest}")
            if read_detail is not None:
                add_error("read-error", source, path, read_detail)
            if FULL_BUFF_FILENAME_RE.fullmatch(path.name) is None:
                invalid_file_count += 1
                error_count += 1
                invalid_row = {
                    "kind": "invalid-filename",
                    "source": source,
                    "relativePath": relative(path),
                    "expected": FULL_BUFF_FILENAME_RE.pattern,
                    "actual": path.name,
                    "size": size,
                    "sha256": digest,
                }
                invalid_files.append(invalid_row)
                if len(error_samples) < FULL_ERROR_SAMPLE_LIMIT:
                    error_samples.append(invalid_row)
                continue
            name = path.stem
            valid_count += 1
            discovered[source][name] = path
            file_meta[source][name] = {
                "source": source,
                "id": name,
                "path": relative(path),
                "size": size,
                "sha256": digest,
            }
        valid_file_counts[source] = valid_count
        root_status[source] = {
            "status": "present",
            "path": root_path,
            "fileCount": len(paths),
            "validFileCount": valid_count,
        }
        manifest_hashes[source] = hashlib.sha256("\n".join(manifest_rows).encode("utf-8")).hexdigest()

    streaming_names = set(discovered["StreamingAssets"])
    persistent_names = set(discovered["Persistent"])
    selected_names = sorted(streaming_names | persistent_names)
    persistent_only = sorted(persistent_names - streaming_names)
    streaming_only = sorted(streaming_names - persistent_names)
    selected_records: dict[str, Any] = {}
    selected_sources: dict[str, str] = {}
    selected_statuses: dict[str, str] = {}

    for name in selected_names:
        source = "Persistent" if name in persistent_names else "StreamingAssets"
        path = discovered[source][name]
        selected_sources[name] = source
        try:
            record = buff_gameplay_semantics(path)
            if not isinstance(record, dict):
                add_error("decode-error", source, path, "decoder returned non-object")
                record = {"id": name, "status": "decode-error", "evidenceStatus": "unresolved"}
            status = str(record.get("status") or "")
            if status.startswith("unsupported") or status in {"parse-error", "read-error"}:
                add_error("unsupported-file" if status.startswith("unsupported") else status, source, path, status)
        except OSError as exc:
            add_error("read-error", source, path, f"{type(exc).__name__}: {exc}")
            record = {"id": name, "status": "read-error", "evidenceStatus": "unresolved", "error": str(exc)}
        except Exception as exc:  # bounded per-file audit failure; continue corpus scan
            add_error("decode-error", source, path, f"{type(exc).__name__}: {exc}")
            record = {"id": name, "status": "decode-error", "evidenceStatus": "unresolved", "error": str(exc)}
        record.setdefault("abilityEventActions", [])
        record["source"] = {"kind": source, "path": relative(path)}
        selected_records[name] = record
        selected_statuses[name] = str(record.get("status") or "<missing>")

    source_manifest: list[dict[str, Any]] = []
    shadowed: list[dict[str, Any]] = []
    for source in ("StreamingAssets", "Persistent"):
        for name in sorted(file_meta[source]):
            meta = dict(file_meta[source][name])
            meta["sha"] = meta["sha256"]
            selected_source = selected_sources.get(name)
            is_selected = selected_source == source
            meta["status"] = selected_statuses.get(name, "shadowed") if is_selected else "shadowed"
            meta["selection"] = "selected" if is_selected else "shadowed"
            if not is_selected:
                counterpart = file_meta[selected_source][name]  # type: ignore[index]
                same_bytes = meta["sha256"] == counterpart["sha256"]
                meta["selectedSource"] = selected_source
                meta["selectedPath"] = counterpart["path"]
                meta["selectedSha256"] = counterpart["sha256"]
                meta["selectedCounterpart"] = {
                    "source": selected_source,
                    "id": name,
                    "path": counterpart["path"],
                    "size": counterpart["size"],
                    "sha256": counterpart["sha256"],
                }
                meta["sameBytesAsSelected"] = same_bytes
                shadowed.append({
                    "id": name,
                    "source": source,
                    "path": meta["path"],
                    "selectedSource": selected_source,
                    "selectedPath": counterpart["path"],
                    "sameBytesAsSelected": same_bytes,
                })
            source_manifest.append(meta)
    source_manifest.sort(key=lambda row: (str(row["source"]), str(row["id"])))
    selected_manifest = [row for row in source_manifest if row["selection"] == "selected"]

    def manifest_digest(records: list[dict[str, Any]]) -> str:
        canonical = {"scope": "full", "rootStatus": root_status, "records": records}
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    full_meta = {
        "status": "error" if missing_roots or error_count else "ok",
        "rootStatus": root_status,
        "sourceFileCounts": source_file_counts | {"selected": len(selected_names)},
        "validSourceFileCounts": valid_file_counts,
        "selected": selected_names,
        "selectedSources": selected_sources,
        "shadowed": shadowed,
        "persistentOnly": persistent_only,
        "streamingOnly": streaming_only,
        "missingRoots": missing_roots,
        "invalidFiles": invalid_files,
        "invalidFileCount": invalid_file_count,
        "errorSamples": error_samples,
        "errorCount": error_count,
        "manifestHashes": manifest_hashes,
        "sourceManifest": source_manifest,
        "selectedManifestSha256": manifest_digest(selected_manifest),
        "allSourceManifestSha256": manifest_digest(source_manifest),
    }
    payload = {
        "language": "FULL",
        "buffs": selected_records,
        "fullCorpus": full_meta,
    }
    return payload, full_meta


def build_report(
    payload: dict[str, Any], previous: dict[str, Any] | None = None, *,
    input_sha256: str | None = None, scope: str = "active",
    full_corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows, sequence_nodes, structure_diagnostics = _collect_occurrences(payload)
    language = _value(payload.get("language"), "<missing>")
    content_hash = content_sha256(payload)
    diagnostics, comparison = _diagnostics(
        rows, previous, language, content_hash, scope, full_corpus,
    )
    authored = sum(int(node["authored"]) for node in sequence_nodes)
    materialized = sum(int(node["materialized"]) for node in sequence_nodes)
    unmaterialized = sum(int(node["unmaterialized"]) for node in sequence_nodes)
    counts = {
        "sequences": len(sequence_nodes),
        "authored": authored,
        "materialized": materialized,
        "unmaterialized": unmaterialized,
        "actionOccurrences": len(rows),
        "exactActions": sum(1 for row in rows if row["status"] == "exact"),
        "nonExactActions": sum(1 for row in rows if row["status"] != "exact"),
        "owners": len({row["owner"] for row in rows}),
        "actionTypes": len(_histogram(rows, "actionType")),
        "decodeStatuses": len(_histogram(rows, "decodeStatus")),
        "semanticStatuses": len(_histogram(rows, "semanticStatus")),
        "memberCounts": len(_histogram(rows, "memberCount")),
        "tags": len(_histogram(rows, "tag")),
    }
    report = {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "scope": scope,
        "language": language,
        "inputGenerated": payload.get("generated"),
        "inputSha256": input_sha256 or "<not-available>",
        "contentSha256": content_hash,
        "counts": counts,
        "sequenceCoverage": {
            "sequences": len(sequence_nodes),
            "authored": authored,
            "materialized": materialized,
            "unmaterialized": unmaterialized,
        },
        "histograms": {
            "actionType": _histogram(rows, "actionType"),
            "status": _histogram(rows, "status"),
            "decodeStatus": _histogram(rows, "decodeStatus"),
            "semanticStatus": _histogram(rows, "semanticStatus"),
            "memberCount": _histogram(rows, "memberCount"),
            "tag": _histogram(rows, "tag"),
            "actionTypeMemberCount": _pair_histogram(rows, "actionType", "memberCount"),
        },
        "comparison": comparison,
        "structureDiagnostics": structure_diagnostics,
        "changeDiagnostics": diagnostics,
        "occurrences": rows,
        "sequences": sequence_nodes,
    }
    if full_corpus is not None:
        report["fullCorpus"] = full_corpus
    return report


def render_markdown(report: dict[str, Any]) -> str:
    def escape(value: Any) -> str:
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`").replace("\r", "").replace("\n", "<br>")

    def code(value: Any) -> str:
        return f"`{escape(value)}`"

    counts = report.get("counts") or {}
    lines = [
        "# Gameplay recovery coverage audit",
        "",
        f"- Scope: {code(report.get('scope', 'active'))}",
        f"- Language: {code(report.get('language', '<missing>'))}",
        f"- Input generated: {code(report.get('inputGenerated', '<missing>'))}",
        f"- Input SHA-256: {code(report.get('inputSha256', '<missing>'))}",
        f"- Content SHA-256: {code(report.get('contentSha256', '<missing>'))}",
        f"- Sequence coverage: **{counts.get('sequences', 0)}** sequences; "
        f"authored **{counts.get('authored', 0)}**, materialized **{counts.get('materialized', 0)}**, "
        f"unmaterialized **{counts.get('unmaterialized', 0)}**",
        f"- Action occurrences: **{counts.get('actionOccurrences', 0)}**",
        f"- Owners: **{counts.get('owners', 0)}**",
        "",
    ]
    full_corpus = report.get("fullCorpus") or {}
    if full_corpus:
        lines.extend([
            f"- Full corpus status: {code(full_corpus.get('status', '<missing>'))}",
            f"- Selected BuffData files: **{len(full_corpus.get('selected') or [])}**",
            f"- Shadowed by Persistent: **{len(full_corpus.get('shadowed') or [])}**",
            f"- Invalid files: **{full_corpus.get('invalidFileCount', 0)}**",
            f"- Missing roots: {code(', '.join(full_corpus.get('missingRoots') or []) or '<none>')}",
            "",
        ])
    histograms = report.get("histograms") or {}
    for title, key in (
        ("Action type", "actionType"),
        ("Status", "status"),
        ("Semantic status", "semanticStatus"),
        ("Member count", "memberCount"),
        ("Tag", "tag"),
    ):
        lines.extend([f"## {title}", "", "| Value | Count |", "| --- | ---: |"])
        for value, count in (histograms.get(key) or {}).items():
            lines.append(f"| {code(value)} | {count} |")
        lines.append("")
    comparison = report.get("comparison") or {}
    structure = report.get("structureDiagnostics") or []
    lines.extend(["## Structure diagnostics", ""])
    if not structure:
        lines.append("No structural diagnostics.")
    else:
        lines.extend(["| Kind | Severity | Details |", "| --- | --- | --- |"])
        for item in structure:
            details = ", ".join(
                f"{key}={code(item[key])}"
                for key in ("owner", "path", "field", "expected", "actual")
                if key in item
            )
            lines.append(f"| {code(item.get('kind'))} | {escape(item.get('severity'))} | {details} |")
    lines.extend(["", "## Baseline change diagnostics", ""])
    if comparison:
        lines.append(
            "Input comparison: "
            f"current={code(comparison.get('currentContentSha256', '<missing>'))}, "
            f"previous={code(comparison.get('previousContentSha256', '<missing>'))}, "
            f"sameInput={code(comparison.get('sameInput', False))}."
        )
        lines.append("")
    if comparison.get("status") in {"unavailable", "error"}:
        lines.append(f"Previous report comparison failed: {escape(comparison.get('reason', 'unknown reason'))}.")
    elif comparison.get("status") == "not-requested":
        lines.append("No previous report supplied.")
    elif not report.get("changeDiagnostics"):
        lines.append("No changes detected for matched occurrences, tags, or member counts.")
    else:
        lines.extend(["| Kind | Severity | Details |", "| --- | --- | --- |"])
        for item in report["changeDiagnostics"]:
            details = ", ".join(
                f"{key}={code(item[key])}"
                for key in ("id", "actionType", "family", "tag", "memberCount", "status", "field", "expected", "actual", "count")
                if key in item
            )
            lines.append(f"| {code(item.get('kind'))} | {escape(item.get('severity'))} | {details} |")
    lines.append("")
    return "\n".join(lines)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_sha256(payload: dict[str, Any]) -> str:
    """Hash deterministic Gameplay content while excluding build timestamp metadata."""

    normalized = dict(payload)
    normalized.pop("generated", None)
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_report(report: dict[str, Any], output: Path, markdown_output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_output.write_text(render_markdown(report), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Generated Gameplay index JSON.")
    parser.add_argument(
        "--full-corpus", action="store_true",
        help="Audit every exported BuffData file with Persistent overlay precedence.",
    )
    parser.add_argument(
        "--export-root", type=Path, default=ROOT / "export_full",
        help="Export root used by --full-corpus (default: export_full).",
    )
    parser.add_argument("--previous", type=Path, help="Earlier audit JSON for regression/schema comparison.")
    parser.add_argument("--output", type=Path, help="Audit JSON output path.")
    parser.add_argument("--markdown-output", type=Path, help="Audit Markdown output path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    full_meta: dict[str, Any] | None = None
    if args.full_corpus:
        payload, full_meta = build_full_corpus_payload(args.export_root.resolve())
        language = "full"
        manifest_bytes = json.dumps(
            full_meta.get("manifestHashes") or {}, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        input_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    else:
        payload = _read_json(args.input)
        language = _value(payload.get("language"), "unknown").lower()
        input_sha256 = sha256_file(args.input)
    output = args.output or DEFAULT_REPORT_ROOT / (
        "gameplay_recovery_audit_full.json" if args.full_corpus
        else f"gameplay_recovery_audit_{language}.json"
    )
    markdown_output = args.markdown_output or output.with_suffix(".md")
    previous = _read_json(args.previous) if args.previous else None
    report = build_report(
        payload, previous, input_sha256=input_sha256,
        scope="full" if args.full_corpus else "active",
        full_corpus=full_meta,
    )
    write_report(report, output, markdown_output)
    print(
        f"Gameplay recovery audit: {report['counts']['actionOccurrences']} actions, "
        f"{len(report['structureDiagnostics'])} structural and "
        f"{len(report['changeDiagnostics'])} baseline diagnostics -> {output}"
    )
    structure_error = any(
        item.get("severity") == "error" for item in report["structureDiagnostics"]
    )
    comparison_error = report["comparison"].get("status") in {"unavailable", "error"}
    review_required = bool(report["comparison"].get("reviewRequired"))
    change_error = any(
        item.get("severity") == "error" for item in report["changeDiagnostics"]
    )
    full_error = bool(full_meta and full_meta.get("status") == "error")
    return 1 if structure_error or comparison_error or review_required or change_error or full_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
