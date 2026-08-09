#!/usr/bin/env python3
"""Validate same-frame canonical VisibilitySH publication from a Unity log."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
EXPECTED_CAPSULE_SHA256 = (
    "687ab01a054e6ef9d07e982de605489de181da089e221e14b450b108161bd5c1"
)
EXPECTED_PNG_SHA256 = {
    "d3d11": "1753e0bd900dfc068e2604632122136a4abf047af0ef5ba9607f17abc8a27ec7",
    "d3d12": "59902c424de630a496364d57e404a5a72bcbcc42712bf7ef6935900d7500cac3",
}
EXPECTED_GPU_SHA256 = {
    "d3d11": "ceaa3f173c90ffbdffa6062f9b046863ebd16fb554101856b8e0126a9d0cdb52",
    "d3d12": "ceaa3f173c90ffbdffa6062f9b046863ebd16fb554101856b8e0126a9d0cdb52",
}

CAPSULE_RE = re.compile(
    r"Recovered VisibilitySH CPU capsule fixture: actor=(?P<actor>\w+), "
    r"count=(?P<count>\d+), stride=(?P<stride>\d+), "
    r"order=\[(?P<order>[^]]*)\], sha256=(?P<sha>[0-9a-f]{64})\."
)
ACTIVE_RE = re.compile(
    r"Recovered VisibilitySH producer active: (?P<actor>\w+), "
    r"(?P<survivors>\d+)/(?P<authored>\d+) retail-cull survivors, "
    r"order=\[(?P<order>[^]]*)\], (?P<width>\d+)x(?P<height>\d+) "
    r"RGBAHalf, retail defaults interval=0\.8/range=5/half-resolution, "
    r"canonicalPublication=(?P<publication>[\w-]+)\."
)
READBACK_RE = re.compile(
    r"Recovered VisibilitySH GPU readback: actor=(?P<actor>\w+), "
    r"size=(?P<width>\d+)x(?P<height>\d+), bytes=(?P<bytes>\d+), "
    r"nonzeroPixels=(?P<nonzero>\d+), sha256=(?P<sha>[0-9a-f]{64})\."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_log(
    text: str,
    api: str,
    source: Path,
    expected_publication: str = "ready",
) -> dict[str, object]:
    failures: list[str] = []

    def require(check: str, actual: object, expected: object) -> None:
        if actual != expected:
            failures.append(
                "VisibilitySH frame validator failed: "
                f"check={check}; source={source}; "
                f"expected={expected!r}; actual={actual!r}"
            )

    api_token = {
        "d3d11": "Forcing GfxDevice: Direct3D 11",
        "d3d12": "Forcing GfxDevice: Direct3D 12",
    }[api]
    require("graphics_api", api_token in text, True)
    prerequisites_ready = (
        (
            "Recovered canonical CharInfo binning + reflection oct/global + "
            "exact VisibilitySHConstData frame resources are active"
        )
        in text
    )
    require(
        "canonical_prerequisites",
        prerequisites_ready,
        expected_publication == "ready",
    )
    require(
        "producer_failure_absent",
        "Recovered retail VisibilitySH producer failed closed:" in text,
        False,
    )
    require("batch_exit", "Exiting batchmode successfully now!" in text, True)

    capsule_match = CAPSULE_RE.search(text)
    active_match = ACTIVE_RE.search(text)
    readback_match = READBACK_RE.search(text)
    require("capsule_record_present", capsule_match is not None, True)
    require("active_record_present", active_match is not None, True)
    require("gpu_readback_present", readback_match is not None, True)

    capsule: dict[str, object] = {}
    active: dict[str, object] = {}
    readback: dict[str, object] = {}
    if capsule_match:
        capsule = {
            "actor": capsule_match["actor"],
            "count": int(capsule_match["count"]),
            "stride": int(capsule_match["stride"]),
            "order": [int(value) for value in capsule_match["order"].split(",")],
            "sha256": capsule_match["sha"],
        }
        require(
            "capsule_fixture",
            capsule,
            {
                "actor": "Wulfa",
                "count": 10,
                "stride": 48,
                "order": list(range(10)),
                "sha256": EXPECTED_CAPSULE_SHA256,
            },
        )
    if active_match:
        active = {
            "actor": active_match["actor"],
            "survivors": int(active_match["survivors"]),
            "authored": int(active_match["authored"]),
            "order": [int(value) for value in active_match["order"].split(",")],
            "width": int(active_match["width"]),
            "height": int(active_match["height"]),
            "canonicalPublication": active_match["publication"],
        }
        require(
            "canonical_publication",
            active["canonicalPublication"],
            expected_publication,
        )
        require("active_actor", active["actor"], "Wulfa")
        require("active_counts", (active["survivors"], active["authored"]), (10, 10))
        require("active_order", active["order"], list(range(10)))
    if readback_match:
        readback = {
            "actor": readback_match["actor"],
            "width": int(readback_match["width"]),
            "height": int(readback_match["height"]),
            "byteCount": int(readback_match["bytes"]),
            "nonzeroPixels": int(readback_match["nonzero"]),
            "sha256": readback_match["sha"],
        }
        require("readback_actor", readback["actor"], "Wulfa")
        require(
            "readback_byte_count",
            readback["byteCount"],
            readback["width"] * readback["height"] * 8,
        )
        require("readback_nonzero", readback["nonzeroPixels"] > 0, True)
        if active:
            require(
                "readback_dimensions",
                (readback["width"], readback["height"]),
                (active["width"], active["height"]),
            )
        expected_gpu_hash = EXPECTED_GPU_SHA256.get(api)
        if expected_gpu_hash:
            require("readback_sha256", readback["sha256"], expected_gpu_hash)

    return {
        "schema": "endfield-recovered-visibility-sh-frame-validation-v1",
        "valid": not failures,
        "graphicsApi": api,
        "defaultOff": True,
        "canonicalProperty": "_VisibilitySHRT",
        "canonicalReadyProperty": "_EndfieldRecoveredVisibilitySHReady",
        "expectedCanonicalPublication": expected_publication,
        "pass0ConsumerEnabled": False,
        "capsuleFixture": capsule,
        "activeFrame": active,
        "gpuReadback": readback,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, choices=("d3d11", "d3d12"))
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--beauty",
        type=Path,
        help="API-specific beauty frame copied immediately after Unity exits.",
    )
    parser.add_argument(
        "--expect-fail-closed",
        action="store_true",
        help="Require diagnostic rendering while canonical publication stays closed.",
    )
    args = parser.parse_args()

    text = args.log.read_text(encoding="utf-8", errors="replace")
    expected_publication = (
        "fail-closed" if args.expect_fail_closed else "ready"
    )
    report = validate_log(
        text,
        args.api,
        args.log,
        expected_publication,
    )
    report["sources"] = {
        "log": {"path": str(args.log), "sha256": sha256(args.log)},
        "producer": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredVisibilitySHProducer.cs",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/EndfieldRecoveredVisibilitySHProducer.cs"
            ),
        },
        "pipeline": {
            "path": "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs",
            "sha256": sha256(
                LAB_ROOT
                / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/HGCompatRenderPipeline.cs"
            ),
        },
        "nativeAudit": {
            "path": "scratch/character_recovery/visibility_capsule_runtime/visibility_capsule_runtime.json",
            "sha256": sha256(
                LAB_ROOT
                / "scratch/character_recovery/visibility_capsule_runtime/visibility_capsule_runtime.json"
            ),
        },
    }
    png = args.beauty or REPO_ROOT / "scratch/runtime_reference_wulfa.png"
    expected_png_hash = EXPECTED_PNG_SHA256[args.api]
    report["beautyFrame"] = {
        "path": str(png),
        "sha256": sha256(png) if png.is_file() else "",
        "expectedSha256": expected_png_hash,
        "unchanged": png.is_file() and sha256(png) == expected_png_hash,
    }
    if not report["beautyFrame"]["unchanged"]:
        report["failures"].append(
            "VisibilitySH frame validator failed: "
            f"check=beauty_frame; source={png}; "
            f"expected={expected_png_hash!r}; "
            f"actual={report['beautyFrame']['sha256']!r}"
        )
        report["valid"] = False

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not report["valid"]:
        for failure in report["failures"]:
            print(failure)
        return 1
    print(
        "VisibilitySH canonical frame validation passed: "
        f"api={args.api}, capsules=10/10, "
        f"nonzeroPixels={report['gpuReadback']['nonzeroPixels']}, "
        f"canonicalPublication={expected_publication}, "
        "pass0ConsumerEnabled=false."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
