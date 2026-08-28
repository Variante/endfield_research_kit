#!/usr/bin/env python3
"""Trace metadata-only fullscreen resource flow into Endminf's normal Uber.

The patched EndfieldCapture records PS SRV and RTV object/view identities for
each retained DrawInstanced(3,1). This analyzer finds the nearest earlier
resolver that wrote every resource read by the normal HGRP Uber pair. It never
infers an edge from matching dimensions or formats and fails closed when the
new resource-chain contract is absent or truncated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


NORMAL_UBER_VS = 0xA8C084C37EBA0ECC
NORMAL_UBER_PS = 0xDE96A55F118305EA


class AnalysisError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisError(f"{path} must contain one JSON object")
    return value


def shader_pair(resolver: dict) -> tuple[int, int]:
    shaders = resolver.get("shaders")
    if not isinstance(shaders, list):
        return 0, 0
    vertex = [int(row.get("identityHash", 0)) for row in shaders if row.get("stage") == 0]
    pixel = [int(row.get("identityHash", 0)) for row in shaders if row.get("stage") == 4]
    return (vertex[0] if len(vertex) == 1 else 0, pixel[0] if len(pixel) == 1 else 0)


def bounded_bindings(resolver: dict, key: str, frame: int, ordinal: int) -> list[dict]:
    chain = resolver.get("resourceChain")
    if not isinstance(chain, dict):
        raise AnalysisError(
            f"frame {frame} resolver {ordinal} lacks resourceChain metadata; "
            "capture with fullscreenResourceChainMetadata=true"
        )
    rows = chain.get(key)
    if not isinstance(rows, list):
        raise AnalysisError(f"frame {frame} resolver {ordinal} resourceChain.{key} is missing")
    result = []
    seen_slots = set()
    for row in rows:
        if not isinstance(row, dict):
            raise AnalysisError(f"frame {frame} resolver {ordinal} {key} row is invalid")
        slot = int(row.get("slot", -1))
        object_id = int(row.get("objectId", 0))
        view_id = int(row.get("viewId", 0))
        if slot < 0 or object_id <= 0 or view_id <= 0 or slot in seen_slots:
            raise AnalysisError(f"frame {frame} resolver {ordinal} has invalid/duplicate {key} binding")
        seen_slots.add(slot)
        result.append({"slot": slot, "objectId": object_id, "viewId": view_id})
    return result


def analyze_frame(path: Path) -> list[dict]:
    metadata = load_json(path)
    frame = int(metadata.get("frame", -1))
    if frame < 0:
        raise AnalysisError(f"{path} has no valid frame number")
    if metadata.get("captureIncomplete") or metadata.get("captureFailed"):
        raise AnalysisError(f"frame {frame} is incomplete or failed")
    if metadata.get("fullscreenResolverRecordsTruncated"):
        raise AnalysisError(f"frame {frame} fullscreen resolver census is truncated")
    resolvers = metadata.get("fullscreenResolvers")
    if not isinstance(resolvers, list):
        raise AnalysisError(f"frame {frame} has no fullscreen resolver census")

    normalized = []
    for resolver in resolvers:
        if not isinstance(resolver, dict):
            raise AnalysisError(f"frame {frame} has an invalid resolver row")
        ordinal = int(resolver.get("fullscreenOrdinal", -1))
        if ordinal < 0:
            raise AnalysisError(f"frame {frame} resolver has no valid ordinal")
        normalized.append({
            "ordinal": ordinal,
            "shaderPair": shader_pair(resolver),
            "inputs": bounded_bindings(resolver, "psInputs", frame, ordinal),
            "outputs": bounded_bindings(resolver, "renderTargets", frame, ordinal),
        })
    normalized.sort(key=lambda row: row["ordinal"])
    if any(normalized[index]["ordinal"] >= normalized[index + 1]["ordinal"]
           for index in range(len(normalized) - 1)):
        raise AnalysisError(f"frame {frame} resolver ordinals are not unique/increasing")

    results = []
    for uber in normalized:
        if uber["shaderPair"] != (NORMAL_UBER_VS, NORMAL_UBER_PS):
            continue
        edges = []
        for input_binding in uber["inputs"]:
            producers = [
                (candidate, output)
                for candidate in normalized if candidate["ordinal"] < uber["ordinal"]
                for output in candidate["outputs"]
                if output["objectId"] == input_binding["objectId"]
            ]
            producer, output = producers[-1] if producers else (None, None)
            edges.append({
                "inputSlot": input_binding["slot"],
                "resourceObjectId": input_binding["objectId"],
                "inputViewId": input_binding["viewId"],
                "producerOrdinal": producer["ordinal"] if producer else None,
                "producerShaderPair": list(producer["shaderPair"]) if producer else None,
                "producerTargetSlot": output["slot"] if output else None,
                "producerViewId": output["viewId"] if output else None,
                "exactObjectIdentityMatch": producer is not None,
            })
        results.append({
            "frame": frame,
            "uberOrdinal": uber["ordinal"],
            "uberShaderPair": list(uber["shaderPair"]),
            "edges": edges,
            "matchedInputCount": sum(row["exactObjectIdentityMatch"] for row in edges),
        })
    return results


def analyze(session_root: Path) -> dict:
    frames_root = session_root / "graphics" / "frames"
    if not frames_root.is_dir():
        raise AnalysisError(f"no graphics frame directory at {frames_root}")
    paths = sorted(
        (path / "metadata.json" for path in frames_root.iterdir()
         if path.is_dir() and path.name.isdigit() and (path / "metadata.json").is_file()),
        key=lambda path: int(path.parent.name),
    )
    if not paths:
        raise AnalysisError("session has no captured graphics metadata")
    samples = [sample for path in paths for sample in analyze_frame(path)]
    if not samples:
        raise AnalysisError("session has no exact normal-Uber resolver")
    matched = sum(sample["matchedInputCount"] for sample in samples)
    if matched == 0:
        raise AnalysisError("normal Uber was found, but no PS input matches an earlier resolver RTV")
    return {
        "schema": "endfield.endminf-fullscreen-resource-chain.v1",
        "status": "exact_object_identity_edges_recovered",
        "session": str(session_root.resolve()),
        "sampleCount": len(samples),
        "matchedEdgeCount": matched,
        "samples": samples,
        "limitations": [
            "Object identity proves resource flow within one captured frame; it does not prove which shader operation created the visible strip pixels.",
            "Only retained DrawInstanced(3,1) resolvers participate in the producer search.",
            "Texture payloads are intentionally not duplicated by this metadata-only census.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = analyze(args.session.resolve())
    except AnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
