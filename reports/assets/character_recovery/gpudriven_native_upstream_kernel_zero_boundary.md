# GPUDriven native upstream and kernel-zero boundary

This report records the installed UnityPlayer call boundary checked against
the current original-data recovery target. It is intentionally separate from
the generated ABI inventory in
`unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/packed_flags_producer_recovery.json`.

## Evidence

- UnityPlayer SHA-256 begins `b47728` and GameAssembly SHA-256 begins `0c557`.
- The UnityPlayer internal-call table maps
  `GPUDrivenRendererV2::PopulatePerFrameData` to `0x1801e98f0`, whose native
  body calls `0x1810ff600`.
- The only direct E8 callers of `0x1810ff600` found in UnityPlayer are the
  wrapper tail `0x1801e994f` and the native upstream at
  `0x18127c7e1`. The upstream function at `0x18127c730` selects the V1 or V2
  object branch (`rbx+0x30` / `rbx+0x38`), then calls the corresponding
  frame/bind/dispatch helpers.
- A second native upstream (`0x181280530..0x1812808c1`) performs the same
  V1/V2 split. Its V1 dispatch reaches `0x1810f1890`; its V2 dispatch reaches
  `0x1810fe040`. In both upstreams, the dispatch call has `xor r9d,r9d`, so
  the native route selects GPUDriven kernel 0, not kernel 7.
- The checked V2 Populate body allocates runtime resources, copies descriptor
  blocks, resolves the TLS graphics context, emits the runtime descriptor
  command payload, and calls context vtable slots `+0xea0` and `+0x850`.
  It does not load factory `manager+0x38 + index*0x8c` records, call the
  84-byte `_UploadBuffer` packer, or select `UploadPerDrawParams` kernel 7.

## Recovery consequence

This closes the native GPUDriven wrapper/upstream and kernel-index boundary,
but it is not a positive producer proof for the missing character channel.
The factory 0x8c record to persistent resource copy remains a CPU-side
maintenance path, and the channel-2 resource at renderer `+0x160` /
resource `+0xd0` still has no authorized resource-to-descriptor upload edge.
Keep the factory-to-GPU upload claim fail-closed until a compatible native
binding or a target capture proves that alias.

## Reproduction pointers

Use the installed UnityPlayer internal-call table and raw E8 census; do not
disassemble the GameAssembly managed wrappers as if they were UnityPlayer
native bodies. The generated producer audit contains the full bounded address
lists and hashes.
