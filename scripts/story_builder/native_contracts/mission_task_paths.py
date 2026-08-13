"""Load the canonical current-build LevelScript task-path contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "missionTaskPaths.nativeContract.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("mission_task_paths.json")
REQUIRED_HOOKS = frozenset({
    "conditionResultChanged",
    "sendProgress",
    "stateUpdate",
    "progressUpdate",
    "conditionCompletionChanged",
    "startFinish",
    "scriptSetDone",
})
HOOK_FIELDS = (
    "symbol",
    "token",
    "methodIndex",
    "rva",
    "message",
    "messageId",
    "captureScope",
    "fieldOffsets",
)


class MissionTaskPathContractError(RuntimeError):
    """Raised when the reviewed task-path contract is missing or malformed."""


def load_mission_task_paths(
    path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Return a validated, normalized contract with source identity."""

    path = path.resolve()
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MissionTaskPathContractError(
            f"cannot load mission task-path contract {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise MissionTaskPathContractError(
            f"mission task-path contract schema must be {SCHEMA!r}: {path}"
        )
    game_build = payload.get("gameBuild")
    if not isinstance(game_build, str) or not game_build.strip():
        raise MissionTaskPathContractError(
            f"mission task-path contract has no gameBuild: {path}"
        )
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict) or set(hooks) != REQUIRED_HOOKS:
        raise MissionTaskPathContractError(
            "mission task-path contract hooks differ: "
            f"expected={sorted(REQUIRED_HOOKS)!r} "
            f"actual={sorted(hooks) if isinstance(hooks, dict) else type(hooks).__name__!r}"
        )
    normalized: dict[str, dict[str, Any]] = {}
    for name in sorted(REQUIRED_HOOKS):
        row = hooks[name]
        if not isinstance(row, dict):
            raise MissionTaskPathContractError(
                f"mission task-path hook {name!r} must be an object: {path}"
            )
        for field in ("symbol", "token", "methodIndex", "rva"):
            if field not in row:
                raise MissionTaskPathContractError(
                    f"mission task-path hook {name!r} has no {field}: {path}"
                )
        normalized[name] = {
            field: row[field]
            for field in HOOK_FIELDS
            if field in row
        }
    return {
        "schema": SCHEMA,
        "gameBuild": game_build,
        "hooks": normalized,
        "source": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
