# Factory shared-data and GPU-scene native boundary

This note records the installed UnityPlayer internal-call registrations below
the managed per-draw bridge. It is a positive/negative split: factory calls
land in the `0x8c` CPU record, while GPU-driven calls bind render resources
through a separate native surface. No static edge between those surfaces was
found in this pass.

## Binary identity

- `D:\Program Files\Endfield Game\UnityPlayer.dll`
- SHA-256: `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`

UnityPlayer's internal-call table maps these names to native entry points:

| registered call | native entry | bounded behavior |
| --- | --- | --- |
| `HGFactoryRenderManager::SetEntitySharedData` | `0x1801eb970` | resolves manager state at `0x1810d8c30`, then jumps to `0x1810d9170` |
| `HGFactoryRenderManager::SetEntitySharedDataPartial` | `0x1801eb9a0` | resolves the same manager state, then calls `0x1810d91f0` with offset/size |
| `GPUDrivenRendererV1::BindBuffersForCulling` | `0x1801e93a0` | obtains render resources and calls `0x1810f2ab0` |
| `GPUDrivenRendererV1::BindBuffersForRendering` | `0x1801e9480` | obtains render resources and calls `0x1810ef150` |
| `HGShadingStateSystem::SetupGpuSceneUploadCs` | `0x1801ee4c0` | initializes/obtains a runtime GPU-scene upload context through dynamic slots |

The full factory setter at `0x1810d9170` copies the source payload into
`manager+0x38 + sharedDataIndex*0x8c`, including lanes `+0x00..+0x80` and the
trailing dword at `+0x88`. The partial setter at `0x1810d91f0` computes the
same record base and forwards `offset` and `size` to the generic size-copy
helper at `0x181c9f9a0`; this is the native endpoint reached by the managed
`SetEntitySharedDataPartial` wrappers.

The GPU-driven V1 culling/render wrapper bodies do not pass the factory
manager `+0x38` record or its `+0x70` dirty byte. Their native callees resolve
resource bindings and pass a runtime context into buffer-binding helpers;
whether a later runtime-indirect callee consumes that context is still open.
`SetupGpuSceneUploadCs` likewise resolves runtime slots and retains no static
reference to the factory record, `_UploadBuffer`, kernel 7, or channel-2
resource `+0xd0`.

Therefore the current static boundary is:

```text
ApplyPerDrawRender
  -> SetEntitySharedDataPartial
  -> manager + sharedDataIndex*0x8c CPU record

GPUDrivenRenderer / SetupGpuSceneUploadCs
  -> runtime resource/context slots
  -> buffer/compute binding helpers

[factory record -> persistent GPU upload/dispatch consumer: unresolved]
```

The `0x1810d25c0` job callback remains a callback-local scratch consumer of
dirty factory records, as documented in
`factory_record_to_100_staging_contract.md`; it is not promoted to the GPU
upload path by these internal-call registrations.
