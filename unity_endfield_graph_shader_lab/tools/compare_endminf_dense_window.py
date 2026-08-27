#!/usr/bin/env python3
"""Compare a targeted Endminf Unity window against adjacent retail phases."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance


def load_rgb(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        image = image.convert("RGB")
        if size is not None and image.size != size:
            image = image.resize(size, Image.Resampling.LANCZOS)
        return np.asarray(image, dtype=np.uint8)


def metrics(reference: np.ndarray, recovered: np.ndarray) -> dict[str, float]:
    delta = recovered.astype(np.float64) - reference.astype(np.float64)
    absolute = np.abs(delta)
    mse = float(np.mean(delta * delta))
    return {
        "mae": float(np.mean(absolute)),
        "rmse": math.sqrt(mse),
        "bias": float(np.mean(delta)),
        "psnr": float("inf") if mse == 0.0 else 20.0 * math.log10(255.0 / math.sqrt(mse)),
        "pixelAnyChannelAtLeast16": float(np.mean(np.any(absolute >= 16.0, axis=2))),
    }


def crop(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = box
    return image[y0:y1, x0:x1]


def make_sheet(
    rows: list[dict],
    output: Path,
    indices: list[int],
    panel_size: tuple[int, int] = (480, 270),
) -> None:
    width, height = panel_size
    canvas = Image.new("RGB", (width * 3, height * len(indices)), "black")
    by_index = {row["index"]: row for row in rows}
    for sheet_row, index in enumerate(indices):
        row = by_index[index]
        reference = Image.fromarray(row.pop("_reference"))
        recovered = Image.fromarray(row.pop("_recovered"))
        difference = Image.fromarray(row.pop("_difference"))
        panels = (reference, recovered, difference)
        for column, panel in enumerate(panels):
            panel = panel.resize(panel_size, Image.Resampling.LANCZOS)
            canvas.paste(panel, (column * width, sheet_row * height))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def parse_box(values: list[int]) -> tuple[int, int, int, int]:
    box = tuple(values)
    if len(box) != 4 or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError(f"invalid ROI: {values}")
    return box


def sheet_indices(frame_count: int) -> list[int]:
    if frame_count <= 0:
        raise ValueError("comparison contains no recovered frames")
    # Keep the established dense-window cadence, but never request indices
    # outside a shorter targeted probe.
    return sorted({
        index for index in (0, 2, 4, 6, 8, 10, 12, 14, frame_count - 1)
        if 0 <= index < frame_count
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unity-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--reference-sidecar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-offsets", type=int, nargs="+", default=[-1, 0, 1])
    # The retail recording contains foreground Character Info controls that
    # are intentionally absent from the reproduction. Keep both comparison
    # windows inside the shared grey gameplay/portrait field: below the roster,
    # right of the statistics panel, left of the yellow actor card, and above
    # the bottom controls.
    parser.add_argument("--roi", type=int, nargs=4, default=[420, 110, 1340, 900])
    parser.add_argument("--effect-roi", type=int, nargs=4, default=[780, 120, 1340, 840])
    args = parser.parse_args()

    unity_report = json.loads((args.unity_dir / "report.json").read_text(encoding="utf-8"))
    sidecar = json.loads(args.reference_sidecar.read_text(encoding="utf-8"))
    if unity_report.get("foregroundUiOverlayIncluded"):
        raise ValueError("Unity capture contains the forbidden foreground UI overlay")
    if not unity_report.get("charInfoBackgroundIncluded") or not unity_report.get(
        "backgroundPortraitIncluded"
    ):
        raise ValueError("Unity capture is missing the required background or portrait")

    width = int(unity_report["width"])
    height = int(unity_report["height"])
    roi = parse_box(args.roi)
    effect_roi = parse_box(args.effect_roi)
    comparison = sidecar["segment"]["comparison"]
    body_anchor = int(comparison["bodyClipStartSourceFrame"])
    first_source = int(sidecar["output"]["firstSourceFrame"])
    fps = float(sidecar["output"]["fps"])

    reference_frame_count = int(sidecar["output"]["frameCount"])
    unity_frames = []
    for frame_row in unity_report["frames"]:
        requested = float(frame_row["requestedSeconds"])
        extracted = [
            body_anchor + round(requested * fps) + offset - first_source + 1
            for offset in args.source_offsets
        ]
        if min(extracted) < 1 or max(extracted) > reference_frame_count:
            break
        unity_frames.append(frame_row)
    if not unity_frames:
        raise ValueError("Unity and retail sequences have no common bounded frame window")
    frame_count = len(unity_frames)
    selected_sheet_indices = set(sheet_indices(frame_count))
    rows_by_offset: dict[int, list[dict]] = {
        offset: [] for offset in args.source_offsets
    }
    previous_reference: dict[int, np.ndarray | None] = {
        offset: None for offset in args.source_offsets
    }
    previous_recovered = None
    for index, frame_row in enumerate(unity_frames):
        recovered = load_rgb(
            args.unity_dir / frame_row["file"], (width, height)
        )
        for offset in args.source_offsets:
            requested = float(frame_row["requestedSeconds"])
            source_frame = body_anchor + round(requested * fps) + offset
            extracted_frame = source_frame - first_source + 1
            reference_path = args.reference_dir / f"frame_{extracted_frame:06d}.png"
            reference = load_rgb(reference_path, (width, height))
            roi_metrics = metrics(crop(reference, roi), crop(recovered, roi))
            effect_metrics = metrics(
                crop(reference, effect_roi), crop(recovered, effect_roi)
            )
            temporal = None
            prior_reference = previous_reference[offset]
            if prior_reference is not None and previous_recovered is not None:
                reference_delta = (
                    crop(reference, effect_roi).astype(np.float64)
                    - crop(prior_reference, effect_roi).astype(np.float64)
                )
                recovered_delta = (
                    crop(recovered, effect_roi).astype(np.float64)
                    - crop(previous_recovered, effect_roi).astype(np.float64)
                )
                temporal = {
                    "deltaMae": float(np.mean(np.abs(recovered_delta - reference_delta))),
                    "referenceAbsEnergy": float(np.mean(np.abs(reference_delta))),
                    "recoveredAbsEnergy": float(np.mean(np.abs(recovered_delta))),
                }
            row = {
                    "index": index,
                    "requestedSeconds": requested,
                    "postSeconds": float(frame_row["endminfPostSeconds"]),
                    "postChromatic": float(frame_row["endminfPostChromaticIntensity"]),
                    "postRadial": float(frame_row["endminfPostRadialIntensity"]),
                    "sourceFrame": source_frame,
                    "extractedFrame": extracted_frame,
                    "roi": roi_metrics,
                    "effectRoi": effect_metrics,
                    "effectTemporal": temporal,
                }
            if index in selected_sheet_indices:
                absolute = np.abs(
                    recovered.astype(np.int16) - reference.astype(np.int16)
                ).astype(np.uint8)
                heat = ImageEnhance.Contrast(Image.fromarray(absolute)).enhance(3.0)
                row.update({
                    "_reference": reference.copy(),
                    "_recovered": recovered.copy(),
                    "_difference": np.asarray(heat, dtype=np.uint8),
                })
            rows_by_offset[offset].append(row)
            previous_reference[offset] = reference
        previous_recovered = recovered

    alignments = []
    sheet_payload: dict[int, list[dict]] = {}
    for offset in args.source_offsets:
        rows = rows_by_offset[offset]
        summary = {
            "sourceOffsetFrames": offset,
            "meanRoiMae": float(np.mean([row["roi"]["mae"] for row in rows])),
            "meanEffectRoiMae": float(
                np.mean([row["effectRoi"]["mae"] for row in rows])
            ),
            "meanEffectTemporalDeltaMae": float(
                np.mean(
                    [
                        row["effectTemporal"]["deltaMae"]
                        for row in rows
                        if row["effectTemporal"] is not None
                    ]
                )
            ),
        }
        alignments.append({"summary": summary, "rows": rows})
        sheet_payload[offset] = rows

    best = min(alignments, key=lambda value: value["summary"]["meanEffectRoiMae"])
    best_offset = int(best["summary"]["sourceOffsetFrames"])
    sheet_path = args.output.with_name(args.output.stem + "_sheet.png")
    indices = sorted(selected_sheet_indices)
    make_sheet(sheet_payload[best_offset], sheet_path, indices)

    for alignment in alignments:
        for row in alignment["rows"]:
            row.pop("_reference", None)
            row.pop("_recovered", None)
            row.pop("_difference", None)
    report = {
        "schema": "endfield.endminf-dense-window-comparison.v2",
        "unityReport": str(args.unity_dir / "report.json"),
        "referenceSidecar": str(args.reference_sidecar),
        "roi": list(roi),
        "effectRoi": list(effect_roi),
        "anchorUncertaintyFrames": int(comparison["anchorUncertaintyFrames"]),
        "bestOffsetByMeanEffectRoiMae": best_offset,
        "sheet": str(sheet_path),
        "alignments": alignments,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "bestOffset": best_offset,
        "summaries": [value["summary"] for value in alignments],
        "report": str(args.output),
        "sheet": str(sheet_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
