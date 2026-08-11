#!/usr/bin/env python3
"""Stable semantic hashes for actor-scoped operator-light evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("actors"), dict):
        raise ValueError(f"operator-light source has no actors object: {path}")
    return payload


def scoped_payload(payload: dict[str, Any], actor_names: Iterable[str]) -> dict[str, Any]:
    actors = payload.get("actors")
    if not isinstance(actors, dict):
        raise ValueError("operator-light payload has no actors object")
    names = tuple(actor_names)
    missing = [name for name in names if name not in actors]
    if missing:
        raise ValueError(
            "operator-light payload is missing scoped actors: "
            + ", ".join(missing)
        )
    return {"actors": {name: actors[name] for name in names}}


def scoped_sha256(path: Path, actor_names: Iterable[str]) -> str:
    """Hash canonical JSON for exactly the actor rows consumed by an audit."""

    payload = scoped_payload(load_payload(path), actor_names)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
