# AnimeStudio SMOL-V decoder recovery

Date: 2026-06-28

## Result

Endfield Vulkan shader payloads are regular SMOL-V containers, not another
encrypted or compressed layer. The remaining failure was in the local C# SMOL-V
decoder, which was older than the payloads used by Endfield.

The local decoder treated the full second header word as the SPIR-V version.
Upstream SMOL-V stores its own encoding version in the high byte of that same
word and masks the low 24 bits back to the SPIR-V version. Endfield samples use
SMOL-V encoding version 1, which adds opcodes `331` through `366` and changes
the ID-delta decode path to the modern zigzag semantics. The older C# decoder
therefore produced bad IDs such as `4294967280` and sometimes ran past the true
snippet boundary before returning `Unable to decode SMOL-V shader`.

## Implemented parser improvement

`tools/AnimeStudio/AnimeStudio.Utility/Smolv/` now:

- masks the SMOL-V encoding byte out of the SPIR-V version word;
- accepts SMOL-V encoding versions `0` and `1`;
- uses version-specific known-opcode table bounds;
- adds version-1 opcodes `ExecutionModeId`, `DecorateId`, and
  `GroupNonUniform*`;
- ports upstream `MemberDecorate` compact-run decoding;
- uses the modern zigzag ID-delta semantics used by version `0`/`1` samples;
- bounds varint and raw word reads by the snippet size passed by the shader
  table, not by the end of the enclosing stream.

The upstream comparison source was the public `aras-p/smol-v` decoder:

```text
https://github.com/aras-p/smol-v/blob/master/source/smolv.cpp
```

## Verification

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with 14 existing warnings and 0 errors.

Targeted repro:

```text
D:\fluffy-dump\tmp\verify_shader_water_smolv\Shader\HGRP_WaterForwardRendering_p25A759680DDC6F56.shader
```

The previous `HGRP/WaterForwardRendering` targeted output had 28 SMOL-V
snippets and 28 `disassembly error` comments. After the decoder change:

| Metric | Count |
| --- | ---: |
| SMOL-V snippets | 28 |
| DXBC snippets | 28 |
| `disassembly error` | 0 |
| `Unable to decode SMOL-V shader` | 0 |
| bad dictionary key errors | 0 |
| `OpEntryPoint` lines | 28 |

Full shader-shard audit:

```text
D:\fluffy-dump\tmp\animestudio_shader_smolv_full_audit_20260628_020333\summary.json
```

| Metric | Count |
| --- | ---: |
| Existing shader shards replayed | 9 |
| Shader outputs | 443 |
| SMOL-V snippets | 59,686 |
| DXBC snippets | 56,878 |
| SMOL-V disassembly errors | 0 |
| `Unable to decode` errors | 0 |
| bad dictionary key errors | 0 |
| `OpEntryPoint` lines | 59,686 |
| nonzero AnimeStudio exits | 0 |

## Remaining shader gaps

Vulkan shader payloads are now decoded from SMOL-V into SPIR-V disassembly for
the existing shard set. The remaining shader limitation is D3D11 HLSL
decompilation: DXBC containers are found and preserved by offset, size, and
hash, but the native `AnimeStudio.HLSLDecompiler` dependency is not available in
the current run. A previous in-process Vortice fallback crashed with
`0xC0000005`, so any future HLSL fallback should run out of process.