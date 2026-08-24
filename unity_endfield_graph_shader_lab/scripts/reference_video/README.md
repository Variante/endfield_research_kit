# Character reference video pipeline

This pipeline turns retail Character Info recordings into named, timestamped
image sequences for pose, camera, effects, lighting, and animation comparison
in the Unity recovery lab. It does not infer animation names or transition
times: those remain explicit annotations in
`config/reference_video_sequences.json`.

Requirements: `python`, `ffmpeg`, and `ffprobe` on `PATH`. The Python wrapper is
stdlib-only. The maintained recordings default to NVIDIA `h264_cuvid` GPU
decoding. Use `--software-decode` on a machine without a compatible NVIDIA GPU,
or `--decoder NAME` to select another FFmpeg hardware decoder.

## Extract the maintained recordings

From `unity_endfield_graph_shader_lab`:

```bat
scripts\reference_video\extract_reference_sequences.bat --list
scripts\reference_video\extract_reference_sequences.bat --recording endminf_overview_2026-08-21
scripts\reference_video\extract_reference_sequences.bat --recording roster_overview_2026-08-15 --character wulfa
scripts\reference_video\extract_reference_sequences.bat --check
```

Use `--dry-run` to inspect every `ffmpeg` command. Add `--force` only to replace
an already extracted selected sequence. Use `--resume` after an interrupted
multi-character run; it validates and skips every completed sequence before
continuing. Full 4K/60 PNG extraction is large;
use `--fps 10` for browsing/contact-sheet work, but retain 60 fps when timing or
animation phase matters. `--scale 1920:-2` creates a smaller diagnostic set
without altering the maintained config.

Outputs are disposable and ignored under:

```text
scratch/character_recovery/reference_sequences/<recording>/<character>/<segment>/
  frame_000001.png
  frame_000002.png
  ...
  sequence.json
```

The per-sequence sidecar pins the source size/hash, source interval, optional
exact one-based source `startFrame`, output
rate, resolution, FFmpeg command, and frame count. Exact frame-index trimming
and the configured end boundary are applied to the decoded source before any
output-rate resampling. Frame `N` represents
`startSeconds + (N - 1) / fps`; use the source interval rather than filenames
when aligning a Unity capture. `--check` validates source pins, the complete
configured segment and output contract, the FFmpeg command, contiguous
filenames, and expected frame counts.

## Add a future recording

1. Record at a stable resolution and frame rate. Leave a few settled loop
   seconds after each character switch. Avoid cursor movement over the actor
   where possible, and do not trim/transcode the original capture afterward.
2. Put the original under `../videos/` and add a recording entry to
   `config/reference_video_sequences.json`.
3. For a focused capture, add explicit `segments` with `startSeconds` and
   `endSeconds`. When a decoded frame is the selected boundary, also record its
   one-based `startFrame`; the extractor then trims by frame index instead of
   timestamp seeking. Use a behavior such as `ui_overview_start_then_loop` until an
   independently established transition lets you split it into separate
   `ui_overview_start` and `ui_overview_loop` segments.
4. For a roster walk, add ordered `markers`. A marker starts at the first frame
   where that model is visibly swapped in and ends at the next marker (or the
   video end). Keep uncertain identities explicit; never alias `endmin` to
   `endminf` without gender/prefab evidence. The maintained 2026-08-15 capture
   is labeled `endminf` from the user's confirmation that the recorded
   Endministrator is female.
5. Run `--dry-run`, extract one character, inspect its first/last frames, then
   extract the full recording and run `--check`.

The 2026-08-15 marker list is seeded from the previous frame-accurate model-swap
audit. It intentionally excludes the initial navigation before Camille and
does not claim that the whole interval is a single retail animation clip.
