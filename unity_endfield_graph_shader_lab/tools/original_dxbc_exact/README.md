# Original deferred-resolver DXBC diagnostic

This project-local tool is an isolated, default-off Direct3D 11 diagnostic. It
does not participate in the character room, compatibility pipeline, or normal
player builds.

Run:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
run_original_dxbc_exact_diagnostic.bat
```

The wrapper:

1. Hash-checks and embeds the exact selected resolver VS/PS.
2. Builds the native plugin and validates both blobs on WARP D3D11.
3. Starts Unity 2022.3.62f3 with `-force-d3d11`.
4. Records the editor fail-closed result.
5. Builds and runs a D3D11-only isolated standalone scene.
6. Verifies the live reports and writes the durable audit to
   `scratch/reverse_engineering/gacha_unity_original_bytecode_execution/`.

Activation requires all of the following:

- the explicit `-endfield-original-dxbc-diagnostic` batch token;
- native contract version 2 and a successful shader-extension configure event;
- an explicit native arm call;
- the unique local keyword `ENDFIELD_ORIGINAL_DXBC_EXACT`;
- exact D3D11 vertex/pixel objects created from the embedded DXBC and bound
  for the native draw event (the compiler callback may remain unused in the
  player process);
- zero unarmed, blocked, or failed callbacks when compiler callbacks occur;
- a changed one-pixel GPU readback; and
- no production-room submission.

The diagnostic binds the frame-proven Endminf retail D3D11 objects in native render event 0
and issues the three-vertex draw after Unity has populated the synthetic b/t/s
fixture; event 1 records the binding state. Before the draw, the native event
recreates all 25 source SRVs from Unity's D3D11 texture resources. The retail
pixel variant is the live `Default Lit - Full Lighting` program observed in all
49 retained frames of capture `20260826T091023Z` (SHA-256 prefix
`b21a1e35eda1c5bc`). It uses nine constant-buffer slots and resources
`t0..t25`, without the simple-subsurface keyword. Unity clears those
SRV slots by event 1, so the report records that post-draw cleanup separately.
The neutral fixture is still not a render-fidelity fixture. The compiler
callback remains an optional build-time variant probe, while the runtime proof
does not depend on a player-side compiler callback or a shell material
overwriting the exact stages.

Do not enable the keyword or arm the plugin outside this disposable diagnostic.

## Endminf combined Uber transport

The build also hash-checks and embeds the exact active Endminf CharInfo
ordinary `BLOOM + VIGNETTE` pixel shader and the captured
`BLOOM + RADIAL_BLUR + VIGNETTE` peak variant with their shared fullscreen
vertex shader. WARP validation must create all three shader objects
successfully. The native transport
uses an immutable 64-packet render-thread ring, stage-local VS/PS constants,
strict source/bloom/LUT/output descriptors, and complete touched-state restore.
Canonical Endminf video export enables
`ENDFIELD_RECOVERED_ENDMINF_UBER_EXACT=1` for the source-certified peak tick;
an explicit environment value still overrides that default for controlled A/B
runs. Runtime submission fails closed before drawing when the generated live
payload is unavailable. It selects the peak pixel shader only in the
source-certified 4.35-second window and uses the ordinary shader elsewhere.
Capture `20260827T183054Z`, frame 1818, supplies the active shader identities
and stage-qualified VS b0 plus PS b0/b1 payloads. Its generic-fullscreen record
predates active-variant priority tagging, so this is live constant/resource
evidence but does not claim draw-bound fixed pipeline state.
`build_endminf_uber_capture_payload.py` converts only that validated report
into immutable native constant bytes; the older unbound 3DMigoto arena is not
accepted as runtime state.
Capture `20260829T024828Z` contributes the ordinary pixel shader and 35
complete ordinary PS-constant witnesses. Every lane read by that shader is
bit-stable and matches the corresponding peak-template lane, so the ordinary
variant safely binds the same larger buffers. That cadence-invalid,
pre-hardening session does not certify current VS b0 or t1 texture bytes;
those remain explicit recapture gaps rather than parity claims.

Validate the next hardened Full session as one ordinary/peak/ordinary contract:

```powershell
python unity_endfield_graph_shader_lab\tools\verify_endminf_uber_capture.py `
  D:\fluffy-dump\scratch\reverse_engineering\endfield_capture\SESSION `
  --sequence-contract `
  --output D:\fluffy-dump\tmp\character_recovery\SESSION_uber_sequence.json
```

The sequence mode requires a complete cadence-valid graphics summary, every
published frame's exact VS/PS constants and t0/t1/t2 bytes, one peak shader
bracketed by ordinary shaders, stable shader-read ordinary lanes, and exact
archived VS/Normal-PS/Peak-PS hashes.

The native build also executes both retail Uber variants on WARP against a
small deterministic synthetic RGBA16F source/R11 bloom fixture plus the exact
captured CharInfo LUT, and pins the two output hashes. This proves shader
execution, constant-buffer ABI, fixed state, and
variant distinction; it is deliberately not presented as a retail-image
fidelity fixture.

`ValidateEndminfUberShaders.exe` also has a fail-closed full-resolution replay
mode for diagnostic captures:

```text
ValidateEndminfUberShaders.exe LUT SOURCE_RGBA16F WIDTH HEIGHT OUTPUT_RGBA8 peak PS_B0 PS_B1
```

`PS_B0` and `PS_B1` are mandatory frame-local shader-declared ranges; replay
never silently combines a retained source with the embedded packet from a
different frame. Until the exact half-resolution R11 bloom payload is present,
the replay binds a zero t1 and prints `bloom=zero`. The raw output is the
pre-copy Uber render target and therefore retains the retail fullscreen
orientation; vertically resolve it, or replay the following retail copy pass,
before comparing it with the final backbuffer. This mode isolates missing
bloom/downstream composition and is not a parity claim.

## M27 Unity-owned draw substitution

The same plugin now contains a separate, default-off M27 compiler-callback
route for a Unity-owned particle draw. It embeds the exact retail HGBuffer
subprogram-113 pair and checks them at build time:

- VS `0678_endfield_dxbc_0.dxbc`: 8,148 bytes,
  SHA-256 `c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c`;
- PS `0679_endfield_dxbc_1.dxbc`: 8,200 bytes,
  SHA-256 `92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e`.

`M27SubstitutionRegistry.h` dispatches by both compiler stage and the SHA-256
of Unity's input shell bytecode. The callback never uses a keyword, callback
order, byte count, or first-seen variant as shader identity. A reserved-variant
inventory delta isolated one VS 10/9 shell and one PS 10/5 shell:

- VS `b6ffa6a650c43fa86cfed1a146ecdfb046d6c92c7e866ff6f51ac79a6c7d4833`;
- PS `9a6803527679aa4d4822ca38a4257c2dafcbce2748a67c7e3387f63e3ee54707`.

Both entries are pinned. Unknown callback hashes leave Unity's shader object
unchanged. The editor validator clears Unity's cached GPU data for only the
dedicated shell, activates its reserved material variant, and requires exactly
the two pinned substitutions with zero mismatch or conflict counters.

Build and validate without replacing the Unity project plugin asset:

```powershell
.\build_plugin.ps1 -ToolOnly
```

The build runs `VerifyM27SubstitutionRegistry.exe`, which verifies both retail
blob hashes, asks WARP D3D11 to create both shader objects, proves exact
stage+SHA dispatch, rejects unknown and cross-stage hashes, and requires the
registry to be ready.

## M14 VFXBaseV2 draw substitution

The registry also retains the exact M14 segmented-trail pair captured at game
frame 13175 in session `20260826T000901Z`:

- VS4914: 6,148 bytes, SHA-256
  `62a5ce6c09171de949ade143b0520cef5b6f899137c1d0190d4014b053eee698`;
- PS4915: 5,072 bytes, SHA-256
  `5558deddb1ee6188dfb530e5be89d86d67352362384fababc585e778b78b99e7`.

Its dedicated Unity shell preserves the retail 8/7 vertex and 7/2 pixel
signatures, two SceneColor/SceneMV targets, premultiplied-alpha blend state,
and the captured constant/resource slot envelope. Reserved-variant inventory
is pinned to VS
`0dc6bf259f8510c1e280160543cab0b591485a34bf226c048bf3f245fdad6714`
and PS
`465a86bc25083537c7cfa6d8f481253d907a29e4097fc5ce378d080083e25b57`.
Unknown hashes remain fail-closed. `RunM14Observation` validates live Unity
substitution and writes its callback inventory under project-local scratch.

## Endminf M31 fixed state

The split M31 native draw has its own fixed-function contract; it must not
reuse M14 state. `M31FixedStateContract.h` owns the exact point-clamp and
linear-wrap samplers, independent SceneColor/SceneMV blends, reversed-Z
read-only depth/stencil state, and raster state recovered from the serialized
`HGRP/Effect/VFXBaseV2` pass, `M_fx_endminm_gfx_31`, and retained runtime
evidence. `VerifyM31FixedState.exe`, run by `build_plugin.ps1`, creates all of
those objects on WARP and proves the D32/S8 read-only DSV can remain bound while
its depth plane is simultaneously sampled. The next complete hardened retail
capture remains the authority for admitting the exact live DSV flags and MRT1
descriptor.
