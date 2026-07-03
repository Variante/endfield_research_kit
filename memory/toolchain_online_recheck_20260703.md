# Toolchain Online Recheck - 2026-07-03

## Context

The current recovery push rechecked local tools against current public Unity and
IL2CPP recovery tool families before starting the P3 MonoBehaviour refresh.

## Online Tool Families Checked

- AssetRipper / AssetStudio / UnityPy remain the main public Unity asset
  extraction families to compare against AnimeStudio.
- Il2CppDumper, Cpp2IL, and Il2CppInspector remain the relevant public IL2CPP
  metadata/code-recovery families.
- Ruri.ShaderDecompiler, HLSLcc, SPIRV-Cross, and SMOL-V are still the relevant
  shader bytecode/translation path for the shader sidecar work.
- FlatBuffers `flatc` reflection support remains the right direction for the
  world-streaming `.bytes` follow-up after the current root-table clustering.

Useful references:

- https://github.com/AssetRipper/AssetRipper
- https://github.com/K0lb3/UnityPy
- https://github.com/Perfare/AssetStudio
- https://github.com/Perfare/Il2CppDumper
- https://github.com/SamboyCoding/Cpp2IL
- https://github.com/djkaty/Il2CppInspector
- https://github.com/ShiyumeMeguri/Ruri.ShaderDecompiler
- https://github.com/KhronosGroup/SPIRV-Cross
- https://github.com/Unity-Technologies/HLSLcc
- https://github.com/aras-p/smol-v
- https://flatbuffers.dev/flatc/

## Local Inventory

Relevant local tools already present:

- `tools/AnimeStudio/`
- `tools/fluffy-dumper-src/`
- `tools/endfield-il2cpp/`
- `tools/Cpp2IL-2022.0.7/`
- `tools/Cpp2IL-src-2022.0.7/`
- `tools/Il2CppDumper-v6.7.46/`
- `tools/DummyDll/`
- `tools/Ruri.ShaderDecompiler/`
- `tools/EndfieldStudio-main/`

No new external tool needs to be promoted into the maintained repo surface yet.
The next high-value work is to use the current local AnimeStudio/IL2CPP stack:
refresh the MonoBehaviour corpus, bucket fresh managed-reference failures, then
target parser gaps with current evidence instead of the stale June inventory.
