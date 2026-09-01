#!/usr/bin/env python3
"""Load the exact local EndfieldCapture observer-build consumer contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CONTRACT_PATH = Path(__file__).with_suffix(".json")
EXPECTED_SCHEMA = "endfield.endfield-capture-observer-build-contract.v1"
SHA256_PATTERN = re.compile(r"[0-9A-F]{64}\Z")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class ObserverBuildContractError(RuntimeError):
    pass


def _positive_integer(value: Any, label: str) -> int:
    if (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
        raise ObserverBuildContractError(f"{label} must be a positive integer")
    return value


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ObserverBuildContractError(
            f"observer build contract is absent: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ObserverBuildContractError(
            f"observer build contract cannot be read: {path}: {exc}") from exc
    if not isinstance(contract, dict):
        raise ObserverBuildContractError(
            "observer build contract root must be an object")
    if contract.get("schema") != EXPECTED_SCHEMA:
        raise ObserverBuildContractError(
            "observer build contract schema is invalid")
    commit = contract.get("producerSourceCommit")
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        raise ObserverBuildContractError(
            "observer build contract producerSourceCommit is invalid")
    runtime = contract.get("runtime")
    if not isinstance(runtime, dict):
        raise ObserverBuildContractError(
            "observer build contract runtime is absent")
    if runtime.get("file") != "EndfieldCapture.dll":
        raise ObserverBuildContractError(
            "observer build contract runtime file is invalid")
    runtime["bytes"] = _positive_integer(
        runtime.get("bytes"), "observer runtime bytes")
    sha256 = runtime.get("sha256")
    if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
        raise ObserverBuildContractError(
            "observer build contract runtime SHA-256 is invalid")
    producers = contract.get("producerContracts")
    if not isinstance(producers, dict):
        raise ObserverBuildContractError(
            "observer build contract producerContracts is absent")
    animator = producers.get("animatorTimeline")
    m31 = producers.get("m31Chronology")
    if not isinstance(animator, dict) or not isinstance(m31, dict):
        raise ObserverBuildContractError(
            "observer build contract producer capacities are absent")
    animator["sampleCapacity"] = _positive_integer(
        animator.get("sampleCapacity"), "animator sample capacity")
    m31["candidateAttemptCapacity"] = _positive_integer(
        m31.get("candidateAttemptCapacity"),
        "M31 candidate-attempt capacity")
    m31["censusCapacity"] = _positive_integer(
        m31.get("censusCapacity"), "M31 census capacity")
    return contract


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_observer_binary(
    observer: Path,
    *,
    build_label: str,
    expected_sha256: str | None = None,
    expected_bytes: int | None = None,
) -> dict[str, Any]:
    if expected_sha256 is None:
        runtime = load_contract()["runtime"]
        expected_sha256 = runtime["sha256"]
        expected_bytes = runtime["bytes"]
    if not isinstance(expected_sha256, str):
        raise ObserverBuildContractError(
            "expected observer SHA-256 must be a string")
    normalized_sha256 = expected_sha256.upper()
    if not re.fullmatch(r"(?:[0-9A-F]{2})+", normalized_sha256):
        raise ObserverBuildContractError(
            "expected observer SHA-256 is invalid")
    if expected_bytes is not None:
        expected_bytes = _positive_integer(
            expected_bytes, "expected observer bytes")
    if not observer.is_file():
        raise ObserverBuildContractError(
            f"captured observer binary is absent: {observer}")
    observed_bytes = observer.stat().st_size
    observed_sha256 = sha256_file(observer)
    if observed_sha256 != normalized_sha256:
        raise ObserverBuildContractError(
            f"captured observer SHA-256 differs from the {build_label}: "
            f"expected {normalized_sha256}, observed {observed_sha256}")
    if expected_bytes is not None and observed_bytes != expected_bytes:
        raise ObserverBuildContractError(
            f"captured observer byte size differs from the {build_label}: "
            f"expected {expected_bytes}, observed {observed_bytes}")
    return {"sha256": observed_sha256, "bytes": observed_bytes}
