"""Re-pin the audio hook catalog to the installed build.

`audio_runtime_trace_hooks.json` is the `audioRuntimeTrace.hooks.v2` evidence
catalog that `StartCapture.bat` hands to the capture host as its build
manifest. **The host owns the conversion**: it looks up five required hooks by
name, takes only each one's `rva`, supplies the module and ABI identifier from
its own table, and writes the `audioRuntimeTrace.activation.v1` manifest the
audio provider consumes. Producing that activation file here would be writing
something nothing reads -- a mistake this module was built making.

What actually blocks a capture is that the catalog is pinned to the build it
was recorded on. This re-pins it, and verifies the two halves differently
because they are different claims.

*The managed hooks* live in `GameAssembly.dll`, rebuilt on every client update,
so their addresses are re-resolved by name through `il2cpp.method_resolver` --
which derives `Il2CppCodeRegistration` rather than pinning it, and so runs
unchanged on a future build. They do move: on this build
`AudioAdapter._PostEvent` went from `0x328a690` to `0x337f270`, so carrying the
recorded value forward would have attached a hook to unrelated code.

*The native hooks* live in `AkSoundEngine.dll`, which was rebuilt to a
different SHA-256 at an identical 3,586,536 bytes. Their recorded addresses are
nonetheless still right, and that is checked rather than assumed against the
binary's own `.pdata` exception directory, where a `BeginAddress` *is* a
function start by definition. 29 of the catalog's 32 native rows land exactly
on one at a density of one function per 212 bytes of `.text`; the three that do
not are sixteen-byte leaf getters, which MSVC omits from `.pdata` by design. A
future rebuild that *does* move code therefore fails closed instead of hooking
whatever now sits at the address.

**Only the five hooks the host requires are refreshed.** Every other row keeps
a superseded address and is recorded as such in `refreshedHooks`, because a row
that silently kept a stale address would be indistinguishable from a current
one.

Fails closed and names the hook that stopped it: a failed native gate, an
ambiguous type name, an unresolved or overloaded method, a match with no native
body, or a native RVA that is no longer a function start.
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
from scripts.game_data.wwise_sdk_symbols import SymbolError, name_addresses
from scripts.repo_paths import REPO_ROOT as REPO


CATALOG = REPO / "scripts/webui/story_recovery/audio_runtime_trace_hooks.json"
DEFAULT_OUTPUT = CATALOG
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


SDK_DESCRIPTION = "Wwise 2023.1.17 SDK x64_vc170 Profile AkSoundEngine.lib"


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


def name_native_rows(rows: list[dict[str, Any]], audio_dll: Path) -> dict[str, Any]:
    """Annotate each native row the Wwise SDK can name, and say what that proves.

    A catalog row's ``name`` is the role someone expected the function to play;
    the symbol is what the code actually is. Six rows turned out to disagree,
    which is why this runs on every re-pin instead of being recorded once by
    hand: an annotation derived from a previous build is exactly the stale
    evidence the rest of this tool refuses.

    Optional by design. The SDK is a local install, so its absence leaves rows
    unnamed and is reported, never fatal -- refusing here would make re-pinning
    impossible on a machine that merely lacks Wwise.
    """
    wanted = []
    for row in rows:
        try:
            wanted.append(int(str(row.get("rva")), 16))
        except (TypeError, ValueError):
            continue
    try:
        named = name_addresses(wanted, dll=audio_dll)
    except SymbolError as error:
        return {"status": "unavailable", "detail": str(error), "named": 0}
    hits = 0
    for row in rows:
        try:
            found = named.get(int(str(row.get("rva")), 16))
        except (TypeError, ValueError):
            continue
        if not found:
            # Leave a superseded annotation behind and it would look current.
            for key in ("resolvedSymbol", "resolvedFrom", "resolvedEvidence"):
                row.pop(key, None)
            continue
        hits += 1
        row["resolvedSymbol"] = found["symbol"]
        row["resolvedFrom"] = SDK_DESCRIPTION
        row["resolvedEvidence"] = found["evidence"]
    return {"status": "named", "named": hits, "rows": len(rows)}


def refresh_catalog(catalog: Path = CATALOG) -> tuple[dict[str, Any], dict[str, Any]]:
    """The catalog re-pinned to the installed build, and a per-hook receipt.

    The five hooks the host requires are refreshed; every other row keeps its
    recorded address and is marked stale, because this build's evidence for it
    has not been re-derived. Marking is the point: a row that silently kept a
    superseded address would be indistinguishable from a current one.
    """
    gate = check_installed_native_inputs()
    if gate.status != "validated":
        raise ManifestError(f"installed native inputs: {gate.status}: {gate.detail}")
    value = json.loads(catalog.read_bytes())
    if value.get("schema") != CATALOG_SCHEMA:
        raise ManifestError(f"catalog schema {value.get('schema')!r} is not {CATALOG_SCHEMA}")

    game_root = Path(gate.gameassembly).parent
    audio_dll = game_root / AUDIO_MODULE_RELATIVE
    if not audio_dll.is_file():
        raise ManifestError(f"no AkSoundEngine.dll at {audio_dll}")
    starts = pdata_function_starts(audio_dll)
    symbols = name_native_rows(value.get("nativeHooks", []), audio_dll)
    managed_names = [name for name, (module, _) in IMPLEMENTED_HOOKS.items()
                     if module == GAME_MODULE]
    managed = resolve_managed(managed_names, Path(gate.gameassembly), Path(gate.metadata))

    receipt: list[dict[str, Any]] = []
    seen: set[str] = set()
    for section in ("hooks", "nativeHooks"):
        for row in value.get(section, []):
            name = row.get("name")
            if name not in IMPLEMENTED_HOOKS:
                continue
            seen.add(name)
            was = row.get("rva")
            module, _abi = IMPLEMENTED_HOOKS[name]
            if module == GAME_MODULE:
                row["rva"] = f"0x{managed[name]:x}"
                how = "re-resolved by name against the selected build"
            else:
                rva = int(str(was), 16)
                if rva not in starts:
                    raise ManifestError(
                        f"{name}: recorded rva {was} is not a function start in the "
                        f"installed {AUDIO_MODULE}; it must be re-derived, not carried")
                how = "recorded rva, verified as a .pdata function start"
            row["resolution"] = how
            receipt.append({"name": name, "module": module, "was": was,
                            "now": row["rva"], "moved": was != row["rva"], "how": how})
    missing = sorted(set(IMPLEMENTED_HOOKS) - seen)
    if missing:
        raise ManifestError(f"the catalog has no row for {missing}")

    files = {}
    for key, relative in (("executable", "Endfield.exe"),
                          ("gameAssembly", GAME_MODULE),
                          ("metadata", "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"),
                          ("akSoundEngine", AUDIO_MODULE_RELATIVE)):
        path = game_root / relative
        if not path.is_file() and key == "executable":
            path = game_root.parent / relative
        if not path.is_file():
            raise ManifestError(f"no {relative} under {game_root}")
        files[key] = {"relativePath": relative, "bytes": path.stat().st_size,
                      "sha256": _sha256(path)}
    value["files"] = {**value.get("files", {}), **files}
    value["gameBuild"] = (
        f"endfield-gameassembly-{(gate.gameassembly_sha256 or '')[:8].lower()}")
    value["refreshedHooks"] = {
        "note": (
            "Only the five hooks the capture host requires are refreshed against the "
            "installed build. Every other row keeps a superseded address and is not "
            "evidence for this build until re-derived."
        ),
        "hooks": receipt,
    }
    value["symbolNaming"] = {
        "note": (
            "Symbols come from matching each recorded address against the Wwise SDK "
            "library. A symbol identifies the code and so the class and method; it "
            "does not establish when the function runs or what calls it. Where a row's "
            "name and its symbol disagree, the symbol is the fact."
        ),
        **symbols,
    }
    return value, {"gameBuild": value["gameBuild"], "hooks": receipt,
                   "symbols": symbols,
                   "files": {k: v["sha256"][:16] for k, v in files.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true",
                        help="report what would change without writing it")
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        catalog, receipt = refresh_catalog(args.catalog)
    except (ManifestError, OSError, ValueError, KeyError, struct.error) as error:
        print(json.dumps({"status": "refused", "detail": str(error)}), file=sys.stderr)
        return 2
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # newline="" keeps the line feeds below literal. Without it Windows
        # expands every one to CRLF, which rewrites all 1,900 lines and buries
        # the few that actually changed in a whole-file diff.
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(catalog, ensure_ascii=False, indent=1) + chr(10))
    print(json.dumps({
        "status": "validated",
        **receipt,
        "written": None if args.check else str(args.output),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
