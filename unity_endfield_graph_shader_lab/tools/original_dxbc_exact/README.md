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
