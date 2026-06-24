# AnimeStudio Decode Gaps

Date: 2026-06-24

## Scope

This notes the Endfield assets AnimeStudio did not fully decode or convert in
the latest checked runs. Evidence comes from:

- `reports/20260623_182105/export_full_summary.md` for the story JSON export.
- `reports/20260623_204545/export_full_summary.md` for the asset conversion
  export.
- matching per-type AnimeStudio stdout logs under those report directories.

The wrapper-level result was still healthy: AnimeStudio subprocess failures were
`0`, `export_full/unresolved/failed_to_decode.txt` had `0` entries, and
`export_full/unresolved/manifest_reference_missing.txt` had `0` entries. The
items below are partial decode or conversion gaps, not full export failure.

## MonoBehaviour JSON

Story `json_by_type` exported all selected stages with return code `0`, but some
MonoBehaviours were emitted as metadata-only JSON because their script payload
could not be decoded into fields:

| Source | Metadata-only MonoBehaviours |
| --- | ---: |
| `StreamingAssets` | 2,433 |
| `Persistent` | 238 |

Observed causes:

- `EndOfStreamException` from impossible `ReadAlignedString` sizes, where the
  string length requested far more bytes than remained in the object.
- `InvalidDataException` from negative string lengths.

Samples from the summary:

- `StreamingAssets`: `MonoBehaviour#22257`, `data_eny_0077_agshield`,
  `data_facemorph_avatar_antal`.
- `Persistent`: `CharacterDisplayConfig`, `data_eny_0115_nefarcore`,
  `data_eny_0086_rpsword`.

Impact: these objects are preserved with `$animestudio` metadata, name, PathID,
raw-data hash/length, script linkage when available, and decode error. Their
actual script fields are not available unless a better TypeTree/DummyDll path is
provided or the layout parser is improved.

## Shader Conversion

The asset `convert_by_type` run skipped many shader text conversions:

| Source | Shader `Export ... error` count |
| --- | ---: |
| `StreamingAssets` | 241 |
| `Persistent` | 209 |

The dominant failure mode is inside `ShaderConverter`: `ReadAlignedString` or
`ReadBytes` sees impossible serialized shader-program sizes, for example:

- `Shader:HGRP/CutsceneEffect` with `ReadAlignedString requests 1684105299 bytes ... but only 11080 bytes remain`.
- `Shader:Hidden/RayTracingReflection` with `ReadAlignedString requests 1381257823 bytes ... but only 1352 bytes remain`.
- One Persistent shader hit `ReadBytes has negative byte count -1996292093`.

Impact: these individual `.shader` text outputs are skipped. The failure is
bounded by the guarded readers, so the worker continues instead of allocating
huge buffers or aborting the whole stage.

## AnimationClip Conversion

The asset `convert_by_type` run logged 108 StreamingAssets AnimationClip
conversion errors:

| Category | Count |
| --- | ---: |
| Root object cast from generic `AnimeStudio.Object` to `Animator` | 66 |
| Unknown Light curve attributes in `CustomCurveResolver` | 41 |
| Raw numeric resolver error (`39`) | 1 |

Samples:

- `AnimationClip:A_ui_cutscene_e0m0_1_tittletext_01` failed with
  `Unable to cast object of type 'AnimeStudio.Object' to type 'AnimeStudio.Animator'`.
- `AnimationClip:Recorded (23)` and `Recorded (16)` failed with
  `Unknown attribute 44543834 for Light`.
- `AnimationClip:P_agtrinit_skill232_summon_02_ready` failed with resolver
  message `39`.

Impact: these `.anim` conversion outputs are skipped. The root-cast class of
failure was fixed after this run in the AnimeStudio code, but the report remains
evidence until the AnimationClip stage is refreshed. Unknown Light curve
attribute handling still needs a resolver mapping or fallback behavior.

## Lower-Priority Warnings

Asset map builds still report unknown class IDs such as
`Unknown ClassIDType 1186182244 for object with PathID -653593890721436740`.
These did not cause stage failures and should be treated as unsupported Unity
class metadata unless a downstream workflow needs those objects.

## Follow-Up Candidates

- Refresh `convert_by_type:AnimationClip` after the root-cast fix to verify the
  66 cast errors disappear from the current report set.
- Add fallback handling or mappings for AnimationClip Light attributes
  `44543834` and `1127824095`.
- Investigate whether Endfield shader blobs require a different serialized
  shader layout or a graceful raw-shader fallback when text conversion cannot
  parse a subprogram.
- For MonoBehaviour payload recovery, try a usable Endfield DummyDll set or
  script-derived TypeTrees; otherwise keep metadata-only JSON as the bounded
  and expected fallback.
