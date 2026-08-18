"""Compare a recovered lab render against the original game capture.

The lab renders characters at the supplied reference capture resolution, so a
recovered PNG and the original capture are directly comparable inside the
UI-free character band. This tool measures that band per region of interest and
writes a deterministic JSON report plus a diff visualization.

Policy: the measurements are a regression and priority signal for recovery
work. A smaller delta never on its own proves that a recovered value is the
original value; only serialized data, native behavior, or a validated capture
can do that.

Usage:
    python tools/compare_recovered_vs_original.py --character wulfa
    python tools/compare_recovered_vs_original.py --character wulfa \
        --recovered scratch/character_recovery/composed_frame/wulfa.png \
        --label composed --report-root scratch/character_recovery/visual_delta
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from skimage import color as skcolor

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(PROJECT_ROOT, "config", "visual_comparison_rois.json")
DEFAULT_REPORT_ROOT = os.path.join(
    PROJECT_ROOT, "scratch", "character_recovery", "visual_delta"
)


class ComparisonError(RuntimeError):
    """Fail-closed comparison error."""


def _sha256(path: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    total = 0
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    return total, digest.hexdigest()


def _load_rgb(path: str) -> np.ndarray:
    if not os.path.isfile(path):
        raise ComparisonError(f"image not found: {path}")
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _srgb_to_linear(srgb: np.ndarray) -> np.ndarray:
    scaled = srgb.astype(np.float64) / 255.0
    low = scaled / 12.92
    high = ((scaled + 0.055) / 1.055) ** 2.4
    return np.where(scaled <= 0.04045, low, high)


def _luminance(linear: np.ndarray) -> np.ndarray:
    return (
        0.2126 * linear[..., 0] + 0.7152 * linear[..., 1] + 0.0722 * linear[..., 2]
    )


def _estimate_alignment(
    reference: np.ndarray, recovered: np.ndarray, band: list[int]
) -> tuple[np.ndarray, dict]:
    """Estimate the residual reference->recovered similarity transform.

    The lab camera is reconstructed from source data, so any residual
    translation/rotation/scale is itself a camera-fidelity signal. It is
    reported rather than silently absorbed, and the inverse is applied only so
    that per-pixel colour metrics measure shading rather than geometry.
    """
    x0, y0, x1, y1 = band
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY)[y0:y1, x0:x1]
    rec_gray = cv2.cvtColor(recovered, cv2.COLOR_RGB2GRAY)[y0:y1, x0:x1]
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 500, 1e-7)
    correlation, warp = cv2.findTransformECC(
        ref_gray.astype(np.float32) / 255.0,
        rec_gray.astype(np.float32) / 255.0,
        warp,
        cv2.MOTION_EUCLIDEAN,
        criteria,
        None,
        5,
    )
    # ECC solved in band-local coordinates, so its rotation pivots on the band
    # origin. Re-express the same transform about the full-image origin before
    # it is applied to the whole picture.
    origin = np.array([x0, y0], dtype=np.float64)
    linear = warp[:, :2].astype(np.float64)
    band_translation = [round(float(warp[0, 2]), 3), round(float(warp[1, 2]), 3)]
    warp = warp.copy()
    warp[:, 2] = (warp[:, 2].astype(np.float64) + origin - linear @ origin).astype(
        np.float32
    )

    rotation = float(np.degrees(np.arctan2(-warp[0, 1], warp[0, 0])))
    summary = {
        "mode": "ecc_euclidean",
        "band": list(band),
        "correlation": round(float(correlation), 6),
        "bandTranslationPixels": band_translation,
        "translationPixels": [round(float(warp[0, 2]), 3), round(float(warp[1, 2]), 3)],
        "rotationDegrees": round(rotation, 4),
        "note": (
            "residual reference->recovered transform; a non-zero value is an "
            "unclosed camera/pose difference, not a shading result"
        ),
    }
    return warp, summary


def _apply_alignment(recovered: np.ndarray, warp: np.ndarray) -> np.ndarray:
    height, width = recovered.shape[:2]
    return cv2.warpAffine(
        recovered,
        warp,
        (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _region_metrics(
    reference: np.ndarray,
    recovered: np.ndarray,
    recovered_raw: np.ndarray,
    box: list[int],
) -> dict:
    x0, y0, x1, y1 = box
    ref = reference[y0:y1, x0:x1]
    rec = recovered[y0:y1, x0:x1]
    raw = recovered_raw[y0:y1, x0:x1]
    if ref.size == 0:
        raise ComparisonError(f"empty region box {box}")

    ref_lab = skcolor.rgb2lab(ref.astype(np.float64) / 255.0)
    rec_lab = skcolor.rgb2lab(rec.astype(np.float64) / 255.0)
    raw_lab = skcolor.rgb2lab(raw.astype(np.float64) / 255.0)
    delta_e = skcolor.deltaE_ciede2000(ref_lab, rec_lab)
    delta_e_raw = skcolor.deltaE_ciede2000(ref_lab, raw_lab)

    ref_lin = _srgb_to_linear(ref)
    rec_lin = _srgb_to_linear(rec)
    ref_lum = _luminance(ref_lin)
    rec_lum = _luminance(rec_lin)

    def _stats(values: np.ndarray) -> dict:
        return {
            "mean": round(float(values.mean()), 6),
            "p10": round(float(np.percentile(values, 10)), 6),
            "p50": round(float(np.percentile(values, 50)), 6),
            "p90": round(float(np.percentile(values, 90)), 6),
            "std": round(float(values.std()), 6),
        }

    return {
        "box": list(box),
        "pixels": int(ref.shape[0] * ref.shape[1]),
        "deltaE00": {
            "mean": round(float(delta_e.mean()), 4),
            "p50": round(float(np.percentile(delta_e, 50)), 4),
            "p95": round(float(np.percentile(delta_e, 95)), 4),
            "max": round(float(delta_e.max()), 4),
        },
        "deltaE00Unaligned": {
            "mean": round(float(delta_e_raw.mean()), 4),
            "p95": round(float(np.percentile(delta_e_raw, 95)), 4),
        },
        "luminanceLinear": {
            "reference": _stats(ref_lum),
            "recovered": _stats(rec_lum),
            "meanDelta": round(float(rec_lum.mean() - ref_lum.mean()), 6),
            "contrastDelta": round(float(rec_lum.std() - ref_lum.std()), 6),
        },
        "lab": {
            "referenceMean": [round(float(ref_lab[..., i].mean()), 4) for i in range(3)],
            "recoveredMean": [round(float(rec_lab[..., i].mean()), 4) for i in range(3)],
            "chromaDelta": round(
                float(
                    np.hypot(rec_lab[..., 1].mean(), rec_lab[..., 2].mean())
                    - np.hypot(ref_lab[..., 1].mean(), ref_lab[..., 2].mean())
                ),
                4,
            ),
        },
        "srgbMean": {
            "reference": [round(float(ref[..., i].mean()), 3) for i in range(3)],
            "recovered": [round(float(rec[..., i].mean()), 3) for i in range(3)],
        },
    }


def _write_diff_image(
    reference: np.ndarray,
    recovered: np.ndarray,
    regions: list[dict],
    path: str,
    scale: int = 4,
) -> None:
    x0 = min(region["box"][0] for region in regions)
    y0 = min(region["box"][1] for region in regions)
    x1 = max(region["box"][2] for region in regions)
    y1 = max(region["box"][3] for region in regions)

    ref = reference[y0:y1, x0:x1]
    rec = recovered[y0:y1, x0:x1]
    diff = np.abs(rec.astype(np.int16) - ref.astype(np.int16)).sum(axis=2)
    diff = np.clip(diff * 2, 0, 255).astype(np.uint8)
    heat = np.stack([diff, np.zeros_like(diff), 255 - diff], axis=2)

    height = (y1 - y0) // scale
    width = (x1 - x0) // scale
    panels = [
        Image.fromarray(ref).resize((width, height), Image.LANCZOS),
        Image.fromarray(rec).resize((width, height), Image.LANCZOS),
        Image.fromarray(heat).resize((width, height), Image.LANCZOS),
    ]
    canvas = Image.new("RGB", (width * 3, height))
    for index, panel in enumerate(panels):
        canvas.paste(panel, (width * index, 0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    canvas.save(path)


def _write_roi_overlay(reference: np.ndarray, regions: list[dict], path: str) -> None:
    overlay = reference.copy()
    for region in regions:
        x0, y0, x1, y1 = region["box"]
        for thickness in range(4):
            overlay[y0 + thickness, x0:x1] = (255, 0, 0)
            overlay[y1 - 1 - thickness, x0:x1] = (255, 0, 0)
            overlay[y0:y1, x0 + thickness] = (255, 0, 0)
            overlay[y0:y1, x1 - 1 - thickness] = (255, 0, 0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image = Image.fromarray(overlay)
    image.resize((image.width // 3, image.height // 3), Image.LANCZOS).save(path)


def compare(
    character: str,
    config_path: str,
    recovered_path: str | None,
    label: str,
    report_root: str,
    write_overlay: bool,
    align: bool = True,
) -> dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    characters = config["characters"]
    if character not in characters:
        raise ComparisonError(
            f"unknown character '{character}'; known: {sorted(characters)}"
        )
    entry = characters[character]

    reference_path = os.path.join(PROJECT_ROOT, entry["reference"]["relativePath"])
    reference_bytes, reference_hash = _sha256(reference_path)
    if reference_bytes != entry["reference"]["bytes"]:
        raise ComparisonError(
            f"reference byte count changed: {reference_bytes} != "
            f"{entry['reference']['bytes']}"
        )
    if reference_hash != entry["reference"]["sha256"]:
        raise ComparisonError(
            f"reference sha256 changed: {reference_hash} != "
            f"{entry['reference']['sha256']}"
        )

    if recovered_path is None:
        recovered_path = os.path.join(PROJECT_ROOT, entry["recoveredRelativePath"])
    recovered_path = os.path.abspath(recovered_path)
    recovered_bytes, recovered_hash = _sha256(recovered_path)

    reference = _load_rgb(reference_path)
    recovered = _load_rgb(recovered_path)
    expected = tuple(config["policy"]["resolution"])
    if (reference.shape[1], reference.shape[0]) != expected:
        raise ComparisonError(
            f"reference resolution {reference.shape[1]}x{reference.shape[0]} "
            f"is not the pinned {expected[0]}x{expected[1]}"
        )
    if recovered.shape != reference.shape:
        raise ComparisonError(
            f"recovered resolution {recovered.shape[1]}x{recovered.shape[0]} "
            f"does not match the reference"
        )

    band = config["policy"]["alignmentBand"]
    if align:
        warp, alignment = _estimate_alignment(reference, recovered, band)
        aligned = _apply_alignment(recovered, warp)
    else:
        alignment = {"mode": "none", "note": "alignment disabled by caller"}
        aligned = recovered

    regions = entry["regions"]
    measured = {}
    for region in regions:
        measured[region["name"]] = _region_metrics(
            reference, aligned, recovered, region["box"]
        )
        measured[region["name"]]["note"] = region["note"]

    weights = np.array(
        [measured[region["name"]]["pixels"] for region in regions], dtype=np.float64
    )
    delta_means = np.array(
        [measured[region["name"]]["deltaE00"]["mean"] for region in regions]
    )
    overall = float((delta_means * weights).sum() / weights.sum())

    report = {
        "schemaVersion": 1,
        "boundary": "diagnostic_only",
        "generatedUtc": _dt.datetime.now(_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "character": character,
        "label": label,
        "reference": {
            "path": os.path.relpath(reference_path, PROJECT_ROOT).replace("\\", "/"),
            "bytes": reference_bytes,
            "sha256": reference_hash,
        },
        "recovered": {
            "path": os.path.relpath(recovered_path, PROJECT_ROOT).replace("\\", "/"),
            "bytes": recovered_bytes,
            "sha256": recovered_hash,
        },
        "alignment": alignment,
        "overallDeltaE00Mean": round(overall, 4),
        "regions": measured,
    }

    os.makedirs(report_root, exist_ok=True)
    report_path = os.path.join(report_root, f"{character}_{label}.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    diff_path = os.path.join(report_root, f"{character}_{label}_diff.png")
    _write_diff_image(reference, aligned, regions, diff_path)
    if write_overlay:
        _write_roi_overlay(
            reference, regions, os.path.join(report_root, f"{character}_rois.png")
        )

    report["reportPath"] = report_path
    report["diffPath"] = diff_path
    return report


def _print_against_baseline(report: dict, baseline_path: str) -> None:
    with open(baseline_path, "r", encoding="utf-8") as handle:
        baseline = json.load(handle)
    if baseline["character"] != report["character"]:
        raise ComparisonError(
            f"baseline character '{baseline['character']}' does not match "
            f"'{report['character']}'"
        )
    print(f"  vs baseline [{baseline['label']}]:")
    overall = report["overallDeltaE00Mean"] - baseline["overallDeltaE00Mean"]
    print(
        f"    overall dE {baseline['overallDeltaE00Mean']:.4f} -> "
        f"{report['overallDeltaE00Mean']:.4f} ({overall:+.4f})"
    )
    for name, region in report["regions"].items():
        if name not in baseline["regions"]:
            print(f"    {name:<20} (absent from baseline)")
            continue
        before = baseline["regions"][name]["deltaE00"]["mean"]
        after = region["deltaE00"]["mean"]
        change = after - before
        marker = "improved" if change < 0 else ("regressed" if change > 0 else "same")
        print(
            f"    {name:<20} dE {before:>7.3f} -> {after:>7.3f} "
            f"({change:+7.3f}) {marker}"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument(
        "--recovered", default=None, help="recovered PNG; defaults to the config path"
    )
    parser.add_argument("--label", default="current")
    parser.add_argument("--report-root", default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--roi-overlay", action="store_true")
    parser.add_argument(
        "--baseline",
        default=None,
        help="an earlier report JSON to report per-region improvement against",
    )
    parser.add_argument(
        "--no-align",
        action="store_true",
        help="skip residual camera alignment; per-pixel metrics then mix "
        "geometry and shading error",
    )
    args = parser.parse_args(argv)

    try:
        report = compare(
            args.character,
            args.config,
            args.recovered,
            args.label,
            args.report_root,
            args.roi_overlay,
            align=not args.no_align,
        )
    except ComparisonError as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 2

    print(f"{report['character']} [{report['label']}]")
    alignment = report["alignment"]
    if alignment["mode"] != "none":
        print(
            f"  residual camera: band translation={alignment['bandTranslationPixels']} px "
            f"rotation={alignment['rotationDegrees']} deg "
            f"cc={alignment['correlation']}"
        )
    print(f"  overall deltaE00 mean: {report['overallDeltaE00Mean']}")
    for name, region in report["regions"].items():
        luminance = region["luminanceLinear"]
        print(
            f"  {name:<20} dE={region['deltaE00']['mean']:>7.3f} "
            f"p95={region['deltaE00']['p95']:>7.3f} "
            f"dLum={luminance['meanDelta']:>+9.5f} "
            f"dContrast={luminance['contrastDelta']:>+9.5f}"
        )
    if args.baseline:
        try:
            _print_against_baseline(report, args.baseline)
        except ComparisonError as error:
            print(f"baseline comparison failed: {error}", file=sys.stderr)
            return 2
    print(f"  report: {report['reportPath']}")
    print(f"  diff:   {report['diffPath']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
