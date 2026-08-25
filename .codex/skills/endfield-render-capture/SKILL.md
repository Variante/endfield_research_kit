---
name: endfield-render-capture
description: Prepare, capture, and review Endfield character-render evidence with the prelaunch EndfieldCapture workflow and the temporary staged 3DMigoto D3D11 fallback. Use for neutral draw/resource recovery, shader-hash inventories, frame-analysis review, and deciding which captured resources are useful. Do not use for visual mods or changing game behavior.
---

# Endfield render capture

Prefer the native `tools/EndfieldCapture/` project. Its prelaunch host,
build/module gates, synthetic injection lifecycle, audio hooks, forced-D3D11
hooks, bounded network metadata observation, host-side recording, bounded
writer, and collector are implemented. Retail capture remains
experimental until a session passes provider summaries and collection.
EndfieldCapture is prelaunch-only: start `arm` before Endfield. Never add
generic attach-by-PID or attach it to an already-running process. The normal
retail renderer is not necessarily D3D11, so `-force-d3d11` captures remain
renderer-path evidence.

## Safety and evidence boundary

- Never add or enable `ShaderOverride`, `TextureOverride`, `Resource`,
  `CustomShader`, or command-list sections.
- Keep the staged `Mods` and `ShaderFixes` directories empty except for
  `.gitkeep`.
- Do not use `clear_rt`; it changes the captured frame.
- Frame analysis is observational but adds GPU readbacks and can affect timing.
  Pair every capture with an uncaptured screenshot and the game-build
  fingerprint.
- Do not copy DLLs or configuration into the installed game directory. Use
  `scratch/character_recovery/3dmigoto-dev-v1.0.0/`.
- Stop after a small number of frames. The broad preset can produce tens of GB
  per frame; inspect one frame before capturing more.
- For EndfieldCapture, run `check` and `arm` before starting Endfield. `arm`
  must refuse an already-running target, wait only for the exact configured
  executable, validate process/module path, size, SHA-256, architecture, and
  creation identity, then make at most one ordinary attachment attempt.
- Do not add public PID attachment, process suspension, rapid anti-cheat timing,
  privilege escalation, retry, fallback injection, or process-wide hook
  removal.
- Keep graphics, audio, network, and recording results independent. Failure or
  queue loss in one provider must fail that evidence domain closed without
  reclassifying another.

## EndfieldCapture workflow

1. Read `tools/EndfieldCapture/README.md`. The guided wrapper's `check`
   validates the selected executable and, for audio, `GameAssembly.dll`,
   `global-metadata.dat`, and `AkSoundEngine.dll`. Stop on any mismatch or
   `runtime.error`.
2. For guided use from the `endfield_research_kit` root, double-click the
   wrapper or pass the intended provider profile:

   ```bat
   tools\EndfieldCapture\StartCapture.bat
   tools\EndfieldCapture\StartCapture.bat graphics
   tools\EndfieldCapture\StartCapture.bat audio
   tools\EndfieldCapture\StartCapture.bat network
   tools\EndfieldCapture\StartCapture.bat both
   tools\EndfieldCapture\StartCapture.bat all
   ```

   The wrapper enforces prelaunch ordering, builds Release x64, runs `check`,
   starts `arm` in a separate capture console, and then automatically launches
   `Endfield.exe -force-d3d11` only after the prelaunch marker and capture-host
   PID liveness check. It resolves the executable from `ENDFIELD_GAME_EXE` or
   the research kit's
   `endfield_paths.bat`.
   After retaining the exact process identity, the host makes one attachment
   attempt. The injected runtime waits boundedly for `GameAssembly.dll` and
   `AkSoundEngine.dll`, then validates their loaded paths, sizes, and hashes
   from inside the target before installing hooks. This does not retry the
   attachment attempt.
   With no profile argument the wrapper selects all three injected providers.
   After a valid arm, its topmost click-through desktop overlay binds
   `Numpad 1` to one graphics-frame request, `Numpad 2` to one bounded
   audio-evidence marker, `Numpad 3` to toggle one bounded host-side
   Endfield-window frame sequence
   plus process-tree WAV, `Numpad 4` to request one bounded network-metadata
   window, and `Numpad 0` to hide or reveal the panel. These keys signal
   versioned, provider-specific control events and must report
   provider-not-ready instead of claiming capture when the host event is
   absent. The overlay is guidance and control only; it is not injected game UI
   or a capture-success signal.
   The audio marker contract is two seconds of lookback plus five seconds after
   the request and records runtime relationships, not PCM. The network window
   is two seconds of queued lookback plus eight seconds of follow-up. It stores
   socket lifecycle, endpoint, size, and completion metadata only--never
   payload bytes, TLS plaintext, credentials, replay, or traffic changes.
3. For development or test work, build and test from the submodule:

   ```bat
   cmake -S tools\EndfieldCapture -B tools\EndfieldCapture\build-local -G "Visual Studio 17 2022" -A x64
   cmake --build tools\EndfieldCapture\build-local --config Release
   ctest --test-dir tools\EndfieldCapture\build-local -C Release --output-on-failure
   ```

4. The wrapper owns the direct `check`/`arm` arguments: authoritative manifest,
   game directory, private runtime staging, session root, nonce-bound events,
   and the explicit one-attempt `--inject` authorization. Do not use reduced
   direct commands copied from the former scaffold.
5. Runtime `ready` means hooks/providers initialized. For graphics,
   `runtime.status.json` must later show `graphicsAttached=true`, proving a real
   Present supplied the game device/context/swap chain. An earlier request
   stays pending until an actual Present boundary.
6. For an all-provider session, request one bounded graphics frame, one
   identified audio window, and one network window. Optionally record one
   short gameplay take, type `stop`, then run the collector command in the
   tool README. Review provider
   completeness, dropped-event counts, module facts, actual observed graphics
   API/device facts, and capture limits before opening large resources.
   `Numpad 1` requests the next Present boundary, `Numpad 2` marks a bounded
   audio evidence window, `Numpad 3` toggles the external recorder, `Numpad 4`
   marks a bounded network window, and `Numpad 0` toggles the panel. Keep
   `status` for provider/completeness facts and `stop` for orderly shutdown. A
   hotkey signal is only a request; require the provider event and session
   summary before treating it as evidence.

## EndfieldCapture session storage

- Use one UTC-sortable session root for graphics, audio, or combined capture:
  `scratch/reverse_engineering/endfield_capture/<session-id>/`.
- Prefer session IDs such as `20260824T153000Z_graphics_endminf`; keep them
  under 64 bytes and avoid spaces or path separators.
- The session root owns `session.json`, `events.jsonl`, provider summaries,
  bounded sidecars, `collected/summary.json`, and the collector's hashed
  `collected/inventory.json`.
- Put bounded frame sidecars/resources under
  `graphics/frames/<frame-id>/`; put audio-provider sidecars under `audio/`.
  Audio runtime capture records relationships and bounded facts, not PCM or
  copies of opened files.
- Put metadata-only socket observations under `network/`. Put optional
  host-recorded `video/frame-*.bmp`, `audio.wav`, and status/summary files under
  `recording/`. The compatibility recorder is not MP4 and must fail closed if
  frames or process-loopback audio are absent after a request.
- Never write raw captures inside `tools/EndfieldCapture/`, the installed game,
  `export_full/`, `webui/`, or `reports/`.
- Keep a successful or diagnostically valuable raw session in `scratch/`.
  Use `tmp/reverse_engineering/endfield_capture/<session-id>/` only for a
  disposable failed/synthetic run and remove it after validation.
- Publish only compact validated summaries: graphics under
  `reports/assets/character_recovery/` and audio under
  `reports/story/recovery/audio/`. Durable interpretations belong in the
  matching memory topic, not beside raw files.

## Temporary staged 3DMigoto workflow

1. Use the staged `StartCapture.bat` and launch Endfield with `-force-d3d11`.
2. Confirm `package/d3d11_log.txt` contains `Game path`, `D3D11CreateDevice`,
   and a swap-chain hook before treating the run as valid.
3. Reach a settled target pose, focus the game window, and press `F8` once.
4. Wait for the frame to finish, close the game, and locate the new
   `package/FrameAnalysis-YYYY-MM-DD-HHMMSS/` directory.
5. Review `log.txt` first. It records draw/event order and the active capture
   options. Use `ShaderUsage.txt`, `.dsc` files, and filename hashes to index
   candidate draws before opening large resource files.

## What counts as useful recovery evidence

- `log.txt`: draw order, event numbers, bound shader/resource slots, and
  pipeline state.
- Filenames: draw number plus IB/VS/PS hashes; use these as stable joins across
  repeated captures of the same pose.
- `.dsc`: original D3D buffer/texture descriptions, formats, dimensions,
  strides, and usage flags.
- Vertex/index buffer text: geometry and input-layout clues. Prefer a selected
  draw's files over whole-frame inventories.
- Constant-buffer text: per-draw transforms, camera data, material parameters,
  and instance records, but retain raw bytes/offsets and do not infer semantic
  names without corroboration.
- JPGs: visual/resource candidates only; they are not lossless authored asset
  replacements.

## Review rules

- Compare the four most recent frame directories by draw count, shader hashes,
  resource descriptions, and stable filenames. Repeated records strengthen
  identification; changing CB data may represent animation or camera state.
- Report capture size before processing. Do not recursively copy or hash all
  resources when a directory is tens of GB.
- Promote durable conclusions to the owning character-render memory topic and
  keep raw captures under `scratch/character_recovery/` or `tmp/`.
- Do not publish a recovered renderer or alter Unity materials from a capture
  alone. Require exact mesh/material/texture joins and preserve uncertainty.

The native project and its staged implementation plan are documented in
`tools/EndfieldCapture/README.md` and `tools/EndfieldCapture/PLAN.md`. The
temporary known-good 3DMigoto configuration is documented in
`tools/3Dmigoto-AE/README.md` and
`scratch/character_recovery/3dmigoto-dev-v1.0.0/README.md`.
