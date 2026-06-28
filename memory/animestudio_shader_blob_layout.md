# AnimeStudio shader blob layout investigation

Date: 2026-06-28

Scope: Endfield shader subprogram blobs that previously exported only
unsupported-bytecode metadata from `ShaderConverter.cs`.

## Result

The failing shader blobs are not an extra encrypted layer and are not compressed
twice. They are a newer Endfield/Unity serialized shader subprogram layout. The
outer `subShaderBlob` chunks use the normal Unity LZ4 path (`m_CompressionType =
3`) and decompress into clear structured records.

The old failure signatures (`Unit`, `Shad`, `_RTR`, `_Glo`) came from applying
the older Unity `ShaderSubProgram` parser to records that begin with marker
`0x0C11FFE2`. After that marker, the next fields are not the old layout's
keyword strings. The parser therefore read constant-buffer/resource data as
string lengths and emitted misleading `ReadAlignedString` failures.

## Decoded outer layout

The decompressed platform blob starts with a segment entry table:

```text
0x00  uint32 entry_count
0x04  repeat entry_count:
        uint32 record_offset
        uint32 record_length
        uint32 segment
```

Each record at `record_offset` starts with:

```text
0x00  uint32 marker/version = 0x0C11FFE2
0x04  uint32 raw_program_type
0x08  16 bytes reserved/zero in inspected samples
```

Records with raw program types such as `1`, `2`, `3`, `4`, and `7` are
parameter/resource records. They contain names such as `UnityPerDraw`,
`_Globals`, `_RTRCBuffer`, and `ShaderVariablesGlobal`, but not native bytecode.
For bytecode export it is correct to skip those records after validating their
record length.

Native records inspected so far use:

```text
0x18  int32 keyword_count
      aligned keyword strings
      int32 native_payload_length
      byte[native_payload_length] native_payload
```

Known native `raw_program_type` values:

```text
25  Vulkan/SPIR-V path, payload contains SMOL-V-like snippets
33  D3D11 path, payload contains DXBC snippets
```

## Native payload layout

The D3D11 and Vulkan payloads both start with a small snippet table. The first
int32 is preserved as an opaque requirements/flags value. Starting at offset
`0x04`, the table stores `(code_offset:int32, code_size:int32)` pairs until the
reader reaches the earliest code offset.

D3D11 snippets begin with the standard `DXBC` container magic. Example payloads:

| Signature | Shader | Payload length | DXBC snippets |
| --- | --- | ---: | --- |
| `Unit` | `Mobile/Particles/Additive` | `0x538` | `0xB0+0x178`, `0x228+0x310` |
| `_RTR` | `Hidden/RayTracingReflection` | `0x354` | `0xB0+0xA0`, `0x150+0x204` |
| `Shad` | `HGRP/Foliage/FoliageOccluder` | `0x4B4` | `0xB0+0xB4`, `0x164+0x350` |

Vulkan snippets begin with bytes `4C 4F 4D 53` (`LOMS`), which is little-endian
`0x534D4F4C`, matching the existing `SmolvDecoder.SmolHeaderMagic` convention.
So the Vulkan payload is a known container family, not opaque encryption.

## Tested samples

| Signature | Sample | Source |
| --- | --- | --- |
| `Unit` | `Mobile/Particles/Additive`, PathID `2855819893914472268` | `Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk` |
| `_RTR` | `Hidden/RayTracingReflection` | `Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk` |
| `Shad` | `HGRP/Foliage/FoliageOccluder`, PathID `-7228570525590668` | `Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk` |
| `_Glo` | `HGRP/UI/Grid` | `Endfield_Data\Persistent\VFS\0CE8FA57\FCF21734CEDE10386D06530C787F510D.chk` |

Targeted CLI probes against these four signatures all completed with exit code
0 after the parser change. The old unsupported-layout warnings and
`ReadAlignedString` failures were no longer produced for those samples.

## Implemented parser improvement

`ShaderConverter.cs` now:

- recognizes Endfield subprogram record marker `0x0C11FFE2`;
- reads native program records by bounded record length instead of the older
  Unity subprogram layout;
- distinguishes parameter/resource records from native bytecode records;
- exports `SerializedPlayerSubProgram` entries, which are where these Endfield
  shaders reference the player blobs;
- maps Endfield raw program type `33` to the D3D11 export path;
- extracts DXBC containers from Endfield D3D11 snippet payloads by offset and
  size;
- extracts SMOL-V-like snippets from Endfield Vulkan payloads and feeds them to
  the existing SPIR-V converter as isolated snippet programs.

This is a real layout parse for the inspected outer blob structure. It replaces
the temporary metadata-only fallback for these records.

## Remaining incomplete understanding

Two gaps remain, but they are downstream of the original blob layout problem:

1. D3D11 DXBC containers are found and preserved with offset, size, and hash, but
   HLSL text decompilation is not available in the current run because
   `AnimeStudio.HLSLDecompiler` fails its type initializer when the native
   decompiler DLL is absent. A Vortice `D3DDisassemble` fallback was tested and
   hard-crashed the process with `0xC0000005`, so it should not be used as an
   automatic fallback without a separate isolation process.

2. Vulkan snippets are identified as SMOL-V-like containers, but the existing
   `SmolvDecoder` cannot decode the Endfield samples. Observed failures include
   `Unable to decode SMOL-V shader` and `The given key '4294967279' was not
   present in the dictionary.` The next parser step is likely in
   `SmolvDecoder` or Unity-version-specific SMOL-V handling, not in the outer
   shader blob reader.

## Build and verification notes

`scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded after the
parser change. The build produced 14 pre-existing warnings in unrelated
AnimeStudio files and 0 errors.

During investigation, a temp output build of `AnimeStudio.CLI.csproj` also
succeeded with `dotnet build -c Release -f net9.0-windows --no-restore -o
tmp\animestudio_cli_shader_test_bin`.

Targeted conversions with the rebuilt normal CLI verified:

```text
Mobile/Particles/Additive: 2 DXBC snippets, 2 SMOL-V snippets, 0 bytecode-unavailable fallbacks
Hidden/RayTracingReflection: 2 DXBC snippets, 2 SMOL-V snippets, 0 bytecode-unavailable fallbacks
HGRP/Foliage/FoliageOccluder: 2 DXBC snippets, 2 SMOL-V snippets, 0 bytecode-unavailable fallbacks
HGRP/UI/Grid: 144 DXBC snippets, 144 SMOL-V snippets, 0 bytecode-unavailable fallbacks
```

