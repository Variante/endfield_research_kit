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
- native contract version 1 and a successful shader-extension configure event;
- an explicit native arm call;
- the unique local keyword `ENDFIELD_ORIGINAL_DXBC_EXACT`;
- exact D3D11 vertex/pixel objects created from the embedded DXBC and bound
  for the native draw event (the compiler callback may remain unused in the
  player process);
- zero unarmed, blocked, or failed callbacks when compiler callbacks occur;
- a changed one-pixel GPU readback; and
- no production-room submission.

The diagnostic binds the exact selected D3D11 objects in native render event 0
and issues the three-vertex draw after Unity has populated the synthetic b/t/s
fixture; event 1 records the binding state. Before the draw, the native event
recreates all 25 source SRVs from Unity's D3D11 texture resources; the
standalone report pins `shader_resource_mask=0x3fffffe`. Unity clears those
SRV slots by event 1, so the report records that post-draw cleanup separately.
The neutral fixture is still not a render-fidelity fixture. The compiler
callback remains an optional build-time variant probe, while the runtime proof
does not depend on a player-side compiler callback or a shell material
overwriting the exact stages.

Do not enable the keyword or arm the plugin outside this disposable diagnostic.
