#!/usr/bin/env python3
"""Refresh deferred-render reports that project the installed IFix state.

The deferred reports are larger source-backed contracts, but their IFix
summary is derived data.  Keep that projection synchronized with the current
installed report without changing unrelated native/render evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
)
IFIX_STATE = SOURCE_ROOT / "installed_ifix_patch_state.json"
DEPENDENTS = (
    SOURCE_ROOT / "deferred_lighting_recovery.json",
    SOURCE_ROOT / "deferred_resolver_binding_contract.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_path(path: str | Path) -> str:
    return Path(path).resolve().relative_to(LAB_ROOT.parent.resolve()).as_posix()


def derive_summary(state_path: Path = IFIX_STATE) -> dict[str, Any]:
    if not state_path.is_file():
        raise FileNotFoundError(f"missing installed IFix report: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    persistent = state["vfs_state"]["persistent_overlay"]
    patch = persistent["file"]
    index = persistent["index"]
    targets = state["targets"]
    expected_count = state["patch_format"]["target_count"]
    if expected_count != len(targets):
        raise ValueError(
            "installed IFix report target count mismatch: "
            f"expected={expected_count} actual={len(targets)} source={state_path}"
        )
    report_sha256 = sha256(state_path)
    return {
        "index_repo_path": index["repo_path"],
        "index_sha256": index["sha256"],
        "block_version": persistent["block_version"],
        "file_count": persistent["file_count"],
        "chunk_count": persistent["chunk_count"],
        "byte_count": persistent["byte_count"],
        "target_count": expected_count,
        "state_repo_path": repo_path(state_path),
        "state_size": state_path.stat().st_size,
        "state_sha256": report_sha256,
        "patch_sha256": patch["sha256"],
    }


def _update_index_record(record: dict[str, Any], summary: dict[str, Any]) -> None:
    record.update(
        {
            "repo_path": summary["index_repo_path"],
            "sha256": summary["index_sha256"],
            "block": "IFixPatchOut",
            "file_count": summary["file_count"],
            "chunk_count": summary["chunk_count"],
            "byte_count": summary["byte_count"],
            "block_version": summary["block_version"],
            "target_count": summary["target_count"],
            "character_recovery_locally_replaced": False,
        }
    )
    state_report = record.setdefault("state_report", {})
    state_report.update(
        {
            "repo_path": summary["state_repo_path"],
            "size": summary["state_size"],
            "sha256": summary["state_sha256"],
        }
    )


def _update_overlay(record: dict[str, Any], summary: dict[str, Any]) -> None:
    record.update(
        {
            "name": "IFixPatchOut",
            "block_version": summary["block_version"],
            "file_count": summary["file_count"],
            "chunk_count": summary["chunk_count"],
            "byte_count": summary["byte_count"],
            "target_count": summary["target_count"],
        }
    )


def _refresh_text(value: str, target_count: int) -> str:
    value = value.replace(
        "active 30-target Gameplay.Beyond patch",
        f"active {target_count}-target Gameplay.Beyond patch",
    )
    value = value.replace(
        "active Persistent overlay has 30 exact Gameplay.Beyond targets",
        f"active Persistent overlay has {target_count} exact Gameplay.Beyond targets",
    )
    value = re.sub(
        r"(?<!\d)30 exact Gameplay\.Beyond targets",
        f"{target_count} exact Gameplay.Beyond targets",
        value,
    )
    return value


def refresh_payload(payload: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    """Update only known IFix projection fields in a report payload."""

    target_count = int(summary["target_count"])

    def walk(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in list(value.items()):
                child_path = path + (str(key),)
                if key == "installed_ifix_patch_index" and isinstance(child, dict):
                    _update_index_record(child, summary)
                elif key == "persistent_ifix_patch_overlay" and isinstance(child, dict):
                    _update_overlay(child, summary)
                elif key == "installed_ifix_target_count":
                    value[key] = target_count
                elif key == "persistent_target_count" and any(
                    "ifix" in part.lower() for part in child_path
                ):
                    value[key] = target_count
                elif key == "installed_ifix_state_sha256":
                    value[key] = summary["state_sha256"]
                elif isinstance(child, str) and (
                    "ifix" in " ".join(child_path).lower()
                    or "gameplay.beyond" in child.lower()
                ):
                    value[key] = _refresh_text(child, target_count)
                walk(value[key], child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (str(index),))

    walk(payload)
    return payload


_JSON_DECODER = json.JSONDecoder()


def _skip_json_space(text: str, offset: int) -> int:
    while offset < len(text) and text[offset] in " \t\r\n":
        offset += 1
    return offset


def _text_replacement(path: tuple[str, ...], value: Any, summary: dict[str, Any]) -> Any:
    """Return a replacement for one JSON scalar, or ``value`` unchanged."""

    target_count = int(summary["target_count"])
    if path[-1:] == ("installed_ifix_target_count",):
        return target_count
    if path[-1:] == ("persistent_target_count",) and any(
        "ifix" in part.lower() for part in path
    ):
        return target_count
    if path[-1:] == ("installed_ifix_state_sha256",):
        return summary["state_sha256"]

    if len(path) >= 1 and path[-1] in {
        "repo_path",
        "sha256",
        "block",
        "file_count",
        "chunk_count",
        "byte_count",
        "block_version",
        "target_count",
        "character_recovery_locally_replaced",
    }:
        if "installed_ifix_patch_index" in path:
            index = path.index("installed_ifix_patch_index")
            suffix = path[index + 1 :]
            index_values = {
                ("repo_path",): summary["index_repo_path"],
                ("sha256",): summary["index_sha256"],
                ("block",): "IFixPatchOut",
                ("file_count",): summary["file_count"],
                ("chunk_count",): summary["chunk_count"],
                ("byte_count",): summary["byte_count"],
                ("block_version",): summary["block_version"],
                ("target_count",): target_count,
                ("character_recovery_locally_replaced",): False,
                ("state_report", "repo_path"): summary["state_repo_path"],
                ("state_report", "size"): summary["state_size"],
                ("state_report", "sha256"): summary["state_sha256"],
            }
            if suffix in index_values:
                return index_values[suffix]

    if "persistent_ifix_patch_overlay" in path:
        key = path[-1]
        overlay_values = {
            "name": "IFixPatchOut",
            "block_version": summary["block_version"],
            "file_count": summary["file_count"],
            "chunk_count": summary["chunk_count"],
            "byte_count": summary["byte_count"],
            "target_count": target_count,
        }
        if key in overlay_values:
            return overlay_values[key]

    if isinstance(value, str) and (
        "ifix" in " ".join(path).lower() or "gameplay.beyond" in value.lower()
    ):
        return _refresh_text(value, target_count)
    return value


def _collect_text_edits(
    text: str, summary: dict[str, Any], *, offset: int = 0, path: tuple[str, ...] = ()
) -> list[tuple[int, int, str]]:
    """Locate scalar JSON values without reserializing the surrounding report."""

    offset = _skip_json_space(text, offset)
    if offset >= len(text):
        raise ValueError("unexpected end of JSON while refreshing IFix projection")
    if text[offset] == "{":
        edits: list[tuple[int, int, str]] = []
        offset = _skip_json_space(text, offset + 1)
        if offset < len(text) and text[offset] == "}":
            return edits
        while True:
            offset = _skip_json_space(text, offset)
            key, key_end = _JSON_DECODER.raw_decode(text, offset)
            if not isinstance(key, str):
                raise ValueError("non-string JSON object key")
            value_start = _skip_json_space(text, _skip_json_space(text, key_end) + 1)
            value_end = _json_value_end(text, value_start)
            value, _ = _JSON_DECODER.raw_decode(text, value_start)
            child_path = path + (key,)
            replacement = _text_replacement(child_path, value, summary)
            if replacement != value and not isinstance(replacement, (dict, list)):
                edits.append(
                    (
                        value_start,
                        value_end,
                        json.dumps(replacement, ensure_ascii=False),
                    )
                )
            if isinstance(value, (dict, list)):
                edits.extend(
                    _collect_text_edits(text, summary, offset=value_start, path=child_path)
                )
            offset = _skip_json_space(text, value_end)
            if offset >= len(text):
                raise ValueError("unterminated JSON object")
            if text[offset] == "}":
                return edits
            if text[offset] != ",":
                raise ValueError("invalid JSON object separator")
            offset += 1
    if text[offset] == "[":
        edits = []
        offset = _skip_json_space(text, offset + 1)
        index = 0
        if offset < len(text) and text[offset] == "]":
            return edits
        while True:
            value_start = offset
            value_end = _json_value_end(text, value_start)
            value, _ = _JSON_DECODER.raw_decode(text, value_start)
            child_path = path + (str(index),)
            replacement = _text_replacement(child_path, value, summary)
            if replacement != value and not isinstance(replacement, (dict, list)):
                edits.append(
                    (
                        value_start,
                        value_end,
                        json.dumps(replacement, ensure_ascii=False),
                    )
                )
            if isinstance(value, (dict, list)):
                edits.extend(
                    _collect_text_edits(text, summary, offset=value_start, path=child_path)
                )
            offset = _skip_json_space(text, value_end)
            if offset >= len(text):
                raise ValueError("unterminated JSON array")
            if text[offset] == "]":
                return edits
            if text[offset] != ",":
                raise ValueError("invalid JSON array separator")
            offset = _skip_json_space(text, offset + 1)
            index += 1
    return []


def _json_value_end(text: str, offset: int) -> int:
    value, end = _JSON_DECODER.raw_decode(text, offset)
    del value
    return end


def render(path: Path, summary: dict[str, Any]) -> str:
    text = path.read_text(encoding="utf-8")
    edits = _collect_text_edits(text, summary)
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text


def run(*, check: bool = False, state_path: Path = IFIX_STATE) -> dict[str, Any]:
    summary = derive_summary(state_path)
    changed: list[str] = []
    for path in DEPENDENTS:
        if not path.is_file():
            raise FileNotFoundError(f"missing deferred report: {path}")
        expected = render(path, summary)
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            changed.append(repo_path(path))
            if not check:
                path.write_text(expected, encoding="utf-8")
    if check and changed:
        raise ValueError(
            "deferred IFix projections are stale: " + ", ".join(changed)
        )
    return {
        "target_count": summary["target_count"],
        "block_version": summary["block_version"],
        "byte_count": summary["byte_count"],
        "state_sha256": summary["state_sha256"],
        "changed": changed,
        "check": check,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--state", type=Path, default=IFIX_STATE)
    args = parser.parse_args()
    print(json.dumps(run(check=args.check, state_path=args.state), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
