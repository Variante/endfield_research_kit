"""Reconstruct an Audio observation profile for offline saved-evidence validation.

This emits an ``audioRuntimeTrace.hooks.v2`` document from the verified source
contract. The optional bridge recipe describes only declared bounded fields
and terminated text. Validation reads selected native files and saved evidence.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if __name__ == "__main__" and not __package__:
    raise SystemExit("run as: python -m scripts.webui.story_recovery.prepare_audio_source_observer")

from scripts.game_data.wwise_source_native import CONTRACT_PATH, load_validated_source_contract
from scripts.game_data import wwise_source_queue_native as queue_native
from scripts.game_data import wwise_owner_carrier_native as carrier_native
from scripts.repo_paths import REPO_ROOT
from scripts.webui.story_recovery import runtime_trace_audio_manifest as manifest_io
from scripts.webui.story_recovery import runtime_trace_core as core
from scripts.webui.audio.semantics import source_observer_profile as profiles


DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/source_observer_profile.json"
DEFAULT_REPORT = REPO_ROOT / "reports/audio/source_observer_preflight.json"


def _load_selected_queue_contract(
    contract: dict[str, Any], game_root: Path, *, gameassembly: Path | None = None,
    metadata: Path | None = None, ak_sound_engine: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    selected = Path(game_root).resolve()
    companion, audit = queue_native.load_validated_queue_contract(
        gameassembly=Path(gameassembly).resolve() if gameassembly is not None else selected / "GameAssembly.dll",
        metadata=Path(metadata).resolve() if metadata is not None else selected / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        ak_sound_engine=Path(ak_sound_engine).resolve() if ak_sound_engine is not None else selected / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll",
    )
    if companion is not None and companion.get("nativeInputs") != contract.get("nativeInputs"):
        return None, {**audit, "status": "mismatched", "detail": "companion native inputs differ from the selected source contract"}
    return companion, audit


def _load_selected_owner_carrier_contract(
    contract: dict[str, Any], game_root: Path, *, gameassembly: Path | None = None,
    metadata: Path | None = None, ak_sound_engine: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    selected = Path(game_root).resolve()
    companion, audit = carrier_native.load_validated_owner_carrier_contract(
        gameassembly=Path(gameassembly).resolve() if gameassembly is not None else selected / "GameAssembly.dll",
        metadata=Path(metadata).resolve() if metadata is not None else selected / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        ak_sound_engine=Path(ak_sound_engine).resolve() if ak_sound_engine is not None else selected / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll",
    )
    if companion is not None and audit.get("status") != "validated":
        return None, {**audit, "status": "mismatched", "detail": "owner carrier companion returned rows without a validated gate"}
    if companion is not None and (companion.get("nativeInputs") != contract.get("nativeInputs")
                                  or not isinstance(audit.get("ownerCarrierObserverSpec"), dict)):
        return None, {**audit, "status": "mismatched", "detail": "owner carrier companion inputs/spec differ from selected source evidence"}
    return companion, audit


def validate_profile_recipe(
    profile: dict[str, Any], contract: dict[str, Any], game_root: Path, *, gameassembly: Path | None = None,
    metadata: Path | None = None, ak_sound_engine: Path | None = None,
) -> dict[str, Any]:
    """Exact capture recipes replay without requiring new companion evidence."""
    def exact(expected: dict[str, Any]) -> bool:
        return profiles.matches_generic_profile_recipe(profile, expected)

    if exact(profiles.build_profile(contract)):
        return {"status": "validated", "recipe": profile["observerProfile"]}
    if contract.get("consumers") and exact(profiles.build_profile(contract, include_source_consumer=True)):
        return {"status": "validated", "recipe": profile["observerProfile"]}
    carrier_recipe = profile.get("observerProfile") == "boundedSourceBridgeWithOwnerCarrierV1"
    if profile.get("observerProfile") != "boundedSourceBridgeWithConsumerV1" and not carrier_recipe:
        raise core.CaptureConfigurationError("profile does not match an exact maintained source observer recipe")
    if game_root is None:
        raise core.CaptureConfigurationError("source bridge recipe requires an explicit selected game root")
    companion, audit = _load_selected_queue_contract(contract, game_root, gameassembly=gameassembly,
                                                     metadata=metadata, ak_sound_engine=ak_sound_engine)
    if companion is None:
        raise core.CaptureConfigurationError(f"source bridge companion gate {audit.get('status')}: {audit.get('detail')}")
    if carrier_recipe:
        carrier_companion, carrier_audit = _load_selected_owner_carrier_contract(contract, game_root, gameassembly=gameassembly,
                                                                                metadata=metadata, ak_sound_engine=ak_sound_engine)
        if carrier_companion is None:
            raise core.CaptureConfigurationError(f"owner carrier companion gate {carrier_audit.get('status')}: {carrier_audit.get('detail')}")
        if not exact(profiles.build_owner_carrier_profile(contract, companion, carrier_audit["ownerCarrierObserverSpec"])):
            raise core.CaptureConfigurationError("profile differs from the exact selected owner carrier recipe")
        return {"status": "validated", "recipe": profile["observerProfile"], "queueNativeGate": audit,
                "ownerCarrierNativeGate": carrier_audit}
    if not exact(profiles.build_source_bridge_profile(contract, companion)):
        raise core.CaptureConfigurationError("profile differs from the exact selected source bridge recipe")
    return {"status": "validated", "recipe": profile["observerProfile"], "queueNativeGate": audit}



def _check_generated_path(path: Path) -> Path:
    resolved = path.resolve()
    roots = (REPO_ROOT / "reports", REPO_ROOT / "scratch", REPO_ROOT / "tmp")
    if not any(resolved.is_relative_to(root.resolve()) for root in roots):
        raise core.CaptureConfigurationError(f"generated observer output must stay under reports/, scratch/ or tmp/: {resolved}")
    return resolved


def _same_file(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True
    return left.exists() and right.exists() and os.path.samefile(left, right)


def _check_publication_paths(game_root: Path, output: Path, report: Path) -> tuple[Path, Path]:
    output, report = _check_generated_path(output), _check_generated_path(report)
    if _same_file(output, report):
        raise core.CaptureConfigurationError("observer profile and preflight report must be different files")
    protected = [
        CONTRACT_PATH, queue_native.CONTRACT_PATH, carrier_native.CONTRACT_PATH, game_root / "Endfield.exe", game_root / "GameAssembly.dll",
        game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        game_root / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll",
    ]
    for path in (output, report):
        for source in protected:
            if _same_file(path, source):
                raise core.CaptureConfigurationError(f"observer output aliases selected evidence: {path} -> {source}")
    return output, report


def _atomic_json(path: Path, value: dict[str, Any], *, validate=None) -> None:
    """Validate a complete temporary document before replacing its publication."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if validate is not None:
            validate(temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def prepare(
    game_root: Path, output: Path, report: Path, *, include_source_consumer: bool = False,
    include_source_bridge: bool = False, include_owner_carrier: bool = False,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Gate selected native files and the exact saved-profile recipe offline."""
    game_root = game_root.resolve()
    output, report = _check_publication_paths(game_root, output, report)
    contract, audit = load_validated_source_contract(
        gameassembly=game_root / "GameAssembly.dll",
        metadata=game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        ak_sound_engine=game_root / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll",
    )
    audit = {**audit, "selectedGameRoot": str(game_root), "profilePath": str(output),
             "observer": "savedAudioTraceProfile"}
    if contract is None:
        audit["profileStatus"] = "withheld"
        _atomic_json(report, audit)
        return None, audit
    companion = None
    if include_source_bridge or include_owner_carrier:
        companion, queue_audit = _load_selected_queue_contract(contract, game_root)
        audit["queueNativeGate"] = queue_audit
        if companion is None:
            audit.update(status=queue_audit["status"], detail="source bridge companion: " + queue_audit.get("detail", ""),
                         profileStatus="withheld")
            _atomic_json(report, audit)
            return None, audit
    carrier_spec = None
    if include_owner_carrier:
        carrier_companion, carrier_audit = _load_selected_owner_carrier_contract(contract, game_root)
        audit["ownerCarrierNativeGate"] = carrier_audit
        if carrier_companion is None:
            audit.update(status=carrier_audit["status"], detail="owner carrier companion: " + carrier_audit.get("detail", ""),
                         profileStatus="withheld")
            _atomic_json(report, audit)
            return None, audit
        carrier_spec = carrier_audit["ownerCarrierObserverSpec"]
    profile = profiles.build_profile(contract, include_source_consumer=include_source_consumer,
                            include_source_bridge=include_source_bridge, queue_contract=companion,
                            include_owner_carrier=include_owner_carrier, owner_carrier_spec=carrier_spec)
    # Verify every file (including the process executable) before publishing the
    # generated manifest. The native reader independently checked body witnesses.
    verified = core.verify_game_files(game_root, profile)
    manifest_io.validate_hook_ranges(profile, verified["gameAssembly"], verified["akSoundEngine"])
    _atomic_json(output, profile, validate=manifest_io.load_manifest)
    audit.update(profileStatus="ready", managedHooks=len(profile["hooks"]), nativeHooks=len(profile["nativeHooks"]),
                 capturedStructures={key: value["captureBytes"] for key, value in contract["structures"].items()},
                 unresolved=contract["evidenceBoundary"]["unresolved"])
    _atomic_json(report, audit)
    return profile, audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True, help="Explicit install directory containing Endfield.exe and GameAssembly.dll.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    recipes = parser.add_mutually_exclusive_group()
    recipes.add_argument("--include-source-consumer", action="store_true",
                        help="Include the verified anonymous consumer entry and fixed owner-relative fields.")
    recipes.add_argument("--include-source-bridge", action="store_true",
                         help="Include the independently gated bounded selector/source/owner bridge recipe.")
    recipes.add_argument("--include-owner-carrier", action="store_true",
                         help="Include source bridge plus independently gated entry-only command-4 decoder/owner snapshots.")
    args = parser.parse_args(argv)
    try:
        profile, audit = prepare(args.game_root, args.output, args.report, include_source_consumer=args.include_source_consumer,
                                 include_source_bridge=args.include_source_bridge, include_owner_carrier=args.include_owner_carrier)
    except (core.CaptureConfigurationError, OSError, ValueError, KeyError) as exc:
        print(f"Audio source observer preflight failed: {exc}", file=sys.stderr)
        return 1
    print(f"Audio source observer: {audit['status']}; profile {audit['profileStatus']}: {audit['detail']}")
    if profile is None:
        if audit.get("diagnostic"):
            print(json.dumps(audit["diagnostic"], ensure_ascii=False), file=sys.stderr)
        return 1
    print(f"{len(profile['hooks'])} managed + {len(profile['nativeHooks'])} native hooks -> {args.output}")
    if args.include_owner_carrier:
        print("Entry-only decoder/owner/source snapshots; queue generation, earlier-source continuity, managed ownership and provider remain unresolved.")
    elif args.include_source_bridge:
        print("Bounded source/owner/descriptor fields and declared wide text; queue lifetime, file identity and codec selection remain unresolved.")
    else:
        print("Fixed source/info/output reads only; external-cookie ownership, file identity and codec selection remain unresolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
