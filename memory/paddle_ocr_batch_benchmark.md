# PaddleOCR Batch Benchmark

Date: 2026-06-26

Scope: PP-OCRv5 `server` model on cached P10 gameplay OCR crops from
`tmp/gameplay_video_ocr/frames/1769193684_T17_BV1JdzMBsEUc_P10_5ae99ba540ec`.
The benchmark used the same `run_paddleocr_batch` path as
`scripts/story_recovery/build_gameplay_video_ocr_audit.py`, excluding frame
extraction and model initialization.

Environment:

- PaddleOCR 3.5.0
- GPU: NVIDIA GeForce RTX 5080
- Model: `PP-OCRv5_server_det` + `PP-OCRv5_server_rec`
- Input: cached subtitle crop JPEGs, sampled evenly from 3,855 P10 frames

Result:

- The old default batch size 8 measured about 8.3 fps.
- Batch sizes 24-56 formed the high-throughput band.
- Batch 40 had the fastest individual runs and was the best stable default.
- Batch 56 was effectively tied in aggregate, but 64+ regressed.

Aggregated fps from the benchmark sweeps:

| Batch | Runs | Mean fps | Best fps | Worst fps |
|---:|---:|---:|---:|---:|
| 1 | 1 | 7.167 | 7.167 | 7.167 |
| 2 | 1 | 8.153 | 8.153 | 8.153 |
| 4 | 1 | 8.409 | 8.409 | 8.409 |
| 8 | 1 | 8.316 | 8.316 | 8.316 |
| 12 | 1 | 7.832 | 7.832 | 7.832 |
| 16 | 2 | 7.597 | 8.185 | 7.010 |
| 20 | 1 | 7.797 | 7.797 | 7.797 |
| 24 | 3 | 10.151 | 11.318 | 9.499 |
| 28 | 4 | 10.683 | 12.214 | 8.852 |
| 32 | 3 | 10.225 | 11.187 | 8.822 |
| 40 | 4 | 11.651 | 12.445 | 10.194 |
| 48 | 3 | 10.191 | 10.663 | 9.376 |
| 56 | 3 | 11.686 | 12.371 | 10.946 |
| 64 | 2 | 8.972 | 9.520 | 8.424 |
| 96 | 1 | 8.081 | 8.081 | 8.081 |
| 128 | 1 | 8.266 | 8.266 | 8.266 |

Maintained default:

- `scripts/story_recovery/build_gameplay_video_ocr_audit.py`
  `--paddleocr-frame-batch-size` default: `40`
- `scripts/story_recovery/build_gameplay_video_story_order.py` exposes the same
  flag for `--run-ocr` and also defaults to `40`.

Scratch benchmark files:

- `scratch/paddle_ocr_batch_benchmark.py`
- `scratch/paddle_ocr_batch_benchmark_server_320.json`
- `scratch/paddle_ocr_batch_benchmark_server_focused_480.json`
- `scratch/paddle_ocr_batch_benchmark_server_reverse_480.json`
- `scratch/paddle_ocr_batch_benchmark_server_top_repeat_480.json`
