"""Turn the audio evidence catalog into an activation manifest for one build.

`audio_runtime_trace_hooks.json` is an evidence catalog: 64 rows describing
every audio carrier this lane has identified, pinned to the build they were
recorded on. `EndfieldCapture`'s audio provider needs something narrower and
stricter -- an `audioRuntimeTrace.activation.v1` manifest naming only hooks it
actually implements, each with the ABI identifier its adapter declares, and a
file gate matching the installed build. Its own integration note says to make
that conversion *only after independently verifying the selected build*, which
is what this module does rather than assumes.

**The two halves are verified differently, because they are different claims.**

*The managed hooks* live in `GameAssembly.dll`, which is rebuilt on every client
update, so their addresses are re-resolved by name against the selected build
through `il2cpp.method_resolver` -- which derives `Il2CppCodeRegistration`
rather than pinning it, and therefore runs unchanged on a future build. A
recorded RVA is never carried forward.

*The native hooks* live in `AkSoundEngine.dll`. Carrying an address forward
there would normally be exactly the mistake this repository warns about, so it
is not taken on trust: each recorded RVA must still be a function start in the
installed DLL, checked against that binary's own `.pdata` exception directory.
That is a yes/no fact about the shipped file rather than a guess from prologue
bytes. On the build this was written against, 29 of the catalog's 32 native
rows land on a `.pdata` function start at one function per 212 bytes of
`.text`, which is not something arbitrary addresses do; the three that do not
are sixteen-byte leaf getters, which MSVC omits from `.pdata` by design.

**Fails closed everywhere.** A missing installed input, an unresolvable managed
name, an ambiguous type name, or a native RVA that is not a function start all
refuse the whole manifest and say which hook stopped it. A partially correct
activation manifest is worse than none: it would attach some hooks and silently
omit others, and the session would look successful.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT as REPO


CATALOG = REPO / "scripts/webui/story_recovery/audio_runtime_trace_hooks.json"
DEFAULT_OUTPUT = REPO / "scripts/webui/story_recovery/audio_runtime_trace_activation.json"
ACTIVATION_SCHEMA = "audioRuntimeTrace.activation.v1"
CATALOG_SCHEMA = "audioRuntimeTrace.hooks.v2"
GAME_MODULE = "GameAssembly.dll"
AUDIO_MODULE = "AkSoundEngine.dll"
AUDIO_MODULE_RELATIVE = "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll"

#: The hooks the shipped provider implements, with the ABI identifier its
#: adapter declares for each. A manifest naming anything else is rejected by
#: the provider before MinHook initializes, so the catalog's other 59 rows are
#: evidence and must not be activated.
IMPLEMENTED_HOOKS: dict[str, tuple[str, str]] = {
    "AudioAdapter._PostEvent": (GAME_MODULE, "win64.il2cpp_post_event.v2"),
    "AudioAdapter._PostEventWithExternalSource": (
        GAME_MODULE, "win64.il2cpp_post_event_external_source.v2"),
    "AkSoundEngine.SourceMediaLookup": (
        AUDIO_MODULE, "win64.source_media_lookup.v2"),
    "AkSoundEngine.SourceProviderPreparation": (
        AUDIO_MODULE, "win64.source_provider_preparation.v2"),
    "AkSoundEngine.DefaultIoOpenDispatch": (
        AUDIO_MODULE, "win64.default_io_open_dispatch.v1"),
}
PROCESS_NAME = "Endfield.exe"


class ManifestError(ValueError):
    """A gate refused the conversion; the detail names the hook that stopped it."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdata_function_starts(dll: Path) -> set[int]:
    """Every function start RVA the PE's own exception directory lists.

    x64 ``.pdata`` is an array of ``RUNTIME_FUNCTION``; a ``BeginAddress`` is a
    function start by definition, so membership is a fact about the binary
    rather than a reading of its bytes.
    """
    blob = dll.read_bytes()
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[pe:pe + 4] != b"PE\0\0":
        raise ManifestError(f"{dll.name}: not a PE image")
    sections = struct.unpack_from("<H", blob, pe + 6)[0]
    optional_size = struct.unpack_from("<H", blob, pe + 20)[0]
    offset = pe + 24 + optional_size
    for _ in range(sections):
        name = blob[offset:offset + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, _virtual_address, raw_size, raw_address = struct.unpack_from(
            "<IIII", blob, offset + 8)
        if name == ".pdata":
            starts = set()
            for index in range(min(virtual_size, raw_size) // 12):
                begin = struct.unpack_from("<I", blob, raw_address + index * 12)[0]
                if begin:
                    starts.add(begin)
            return starts
        offset += 40
    raise ManifestError(f"{dll.name}: no .pdata exception directory")


def resolve_managed(names: list[str], gameassembly: Path, metadata: Path) -> dict[str, int]:
    """Re-resolve each managed hook's RVA by name against the selected build."""
    from scripts.game_data.il2cpp.method_resolver import MethodSpec, open_resolver

    resolver, _receipt = open_resolver(gameassembly=gameassembly, metadata=metadata)
    resolved: dict[str, int] = {}
    for name in names:
        type_token, _, method = name.rpartition(".")
        matches = [
            full for full in resolver._type_index
            if full.replace("+", ".").split(".")[-1] == type_token
        ]
        if len(matches) != 1:
            raise ManifestError(
                f"{name}: {len(matches)} type(s) named {type_token!r} on this build; "
                "an ambiguous name is left visible rather than chosen")
        row = resolver.resolve(MethodSpec(type_name=matches[0], method_name=method))
        # ``exact`` and ``renamed`` are the resolver's two success states; a
        # rename is still an identity, since only the managed name survives an
        # update. Everything else -- a missing type or method, an ambiguous
        # overload or lambda -- refuses rather than picking.
        if row.get("status") not in ("exact", "renamed"):
            raise ManifestError(f"{name}: resolver status {row.get('status', 'unresolved')!r}")
        found = row.get("matches") or []
        if len(found) != 1:
            raise ManifestError(
                f"{name}: {len(found)} matching method(s); an overload is left "
                "visible rather than chosen")
        rva = found[0].get("rva")
        if not rva:
            raise ManifestError(
                f"{name}: matched but has no native body "
                f"({found[0].get('bodyStatus', 'unknown')})")
        resolved[name] = int(str(rva), 16)
    return resolved


def build_manifest(catalog: Path = CATALOG) -> dict[str, Any]:
    """The activation manifest for the installed build, or a refusal."""
    gate = check_installed_native_inputs()
    if gate.status != "validated":
        raise ManifestError(f"installed native inputs: {gate.status}: {gate.detail}")
    value = json.loads(catalog.read_bytes())
    if value.get("schema") != CATALOG_SCHEMA:
        raise ManifestError(f"catalog schema {value.get('schema')!r} is not {CATALOG_SCHEMA}")

    recorded: dict[str, dict[str, Any]] = {}
    for section in ("hooks", "semanticHooks", "nativeHooks"):
        for row in value.get(section, []):
            if row.get("name") in IMPLEMENTED_HOOKS:
                recorded[row["name"]] = row
    missing = sorted(set(IMPLEMENTED_HOOKS) - set(recorded))
    if missing:
        raise ManifestError(f"the catalog has no row for {missing}")

    audio_dll = Path(gate.gameassembly).parent / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll"
    if not audio_dll.is_file():
        raise ManifestError(f"no AkSoundEngine.dll at {audio_dll}")
    starts = pdata_function_starts(audio_dll)

    managed_names = [name for name, (module, _) in IMPLEMENTED_HOOKS.items()
                     if module == GAME_MODULE]
    managed = resolve_managed(managed_names, Path(gate.gameassembly), Path(gate.metadata))

    hooks: list[dict[str, Any]] = []
    for name, (module, abi_id) in sorted(IMPLEMENTED_HOOKS.items()):
        if module == GAME_MODULE:
            rva = managed[name]
            evidence = "re-resolved by name against the selected build"
        else:
            rva = int(str(recorded[name]["rva"]), 16)
            if rva not in starts:
                raise ManifestError(
                    f"{name}: recorded rva 0x{rva:x} is not a function start in the "
                    f"installed {AUDIO_MODULE}; it must be re-derived, not carried")
            evidence = "recorded rva, verified as a .pdata function start"
        hooks.append({
            "name": name, "module": module, "abiId": abi_id,
            "rva": f"0x{rva:x}", "required": True, "evidence": evidence,
        })

    game_root = Path(gate.gameassembly).parent
    files = []
    for relative in (GAME_MODULE, AUDIO_MODULE_RELATIVE,
                     "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"):
        path = game_root / relative
        if not path.is_file():
            raise ManifestError(f"no {relative} under {game_root}")
        files.append({"relativePath": relative,
                      "bytes": path.stat().st_size,
                      "sha256": _sha256(path)})
    return {
        "schema": ACTIVATION_SCHEMA,
        "gameBuild": f"endfield-gameassembly-{(gate.gameassembly_sha256 or '')[:8].lower()}",
        "processName": PROCESS_NAME,
        "moduleName": GAME_MODULE,
        "nativeModuleName": AUDIO_MODULE,
        "files": files,
        "hooks": hooks,
        "evidenceBoundary": (
            "Activating a hook proves the method executed in the attached process. "
            "Managed addresses are re-resolved by name against this build; native "
            "addresses are the catalog's, kept only because each is still a function "
            "start in the installed AkSoundEngine.dll. Neither establishes what the "
            "call did, whether it was audible, or any join between hooks."
        ),
        "sourceCatalog": {"path": str(catalog.relative_to(REPO)).replace("\\", "/"),
                          "sha256": _sha256(catalog).upper()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true",
                        help="report what would be written without writing it")
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        manifest = build_manifest(args.catalog)
    except (ManifestError, OSError, ValueError, KeyError, struct.error) as error:
        print(json.dumps({"status": "refused", "detail": str(error)}), file=sys.stderr)
        return 2
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "validated",
        "gameBuild": manifest["gameBuild"],
        "hooks": len(manifest["hooks"]),
        "files": len(manifest["files"]),
        "written": None if args.check else str(args.output),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
