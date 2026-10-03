"""Prepare EndfieldCapture entry-only source/owner observations offline."""
from __future__ import annotations

import argparse
from pathlib import Path
from scripts.game_data.wwise_source_native import load_validated_source_contract
from scripts.game_data.wwise_decoder_provider_native import load_validated_decoder_provider_contract
from scripts.repo_paths import REPO_ROOT
from scripts.webui.story_recovery import prepare_audio_source_observer as recipes
from scripts.webui.story_recovery import runtime_trace_core as core
from scripts.webui.audio.semantics import source_observer_profile as profiles

DEFAULT_OUTPUT = REPO_ROOT / "reports/audio/endfield_source_owner_manifest.json"
DEFAULT_REPORT = REPO_ROOT / "reports/audio/endfield_source_owner_preflight.json"
PROVIDER_OUTPUT = REPO_ROOT / "reports/audio/endfield_source_provider_manifest.json"
PROVIDER_REPORT = REPO_ROOT / "reports/audio/endfield_source_provider_preflight.json"
IO_OUTPUT = REPO_ROOT / "reports/audio/endfield_source_io_manifest.json"
IO_REPORT = REPO_ROOT / "reports/audio/endfield_source_io_preflight.json"
TRANSFER_OUTPUT = REPO_ROOT / "reports/audio/endfield_source_transfer_manifest.json"
TRANSFER_REPORT = REPO_ROOT / "reports/audio/endfield_source_transfer_preflight.json"


def prepare(game_root: Path, output: Path, report: Path, *, include_provider: bool = False, include_io: bool = False, include_transfer: bool = False) -> tuple[dict | None, dict]:
    include_io = include_io or include_transfer
    selected = game_root.resolve()
    output, report = recipes._check_publication_paths(selected, output, report)
    contract, audit = load_validated_source_contract(
        gameassembly=selected / "GameAssembly.dll",
        metadata=selected / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        ak_sound_engine=selected / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll")
    audit = {**audit, "observer": "EndfieldCapture", "selectedGameRoot": str(selected), "profileStatus": "withheld"}
    manifest = None
    if contract is not None:
        queue, queue_audit = recipes._load_selected_queue_contract(contract, selected)
        carrier, carrier_audit = recipes._load_selected_owner_carrier_contract(contract, selected)
        audit.update(queueNativeGate=queue_audit, ownerCarrierNativeGate=carrier_audit)
        if queue is not None and carrier is not None:
            profile = profiles.build_owner_carrier_profile(contract, queue, carrier_audit["ownerCarrierObserverSpec"])
            if include_provider or include_io:
                provider, provider_gate = load_validated_decoder_provider_contract(
                    gameassembly=selected / "GameAssembly.dll", metadata=selected / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
                    ak_sound_engine=selected / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll", include_storage=True,
                    include_package=include_io, include_retention=include_io, include_result=include_io, include_read=include_io)
                storage_gate = provider_gate.get("providerStorageGate", {})
                audit["providerNativeGate"] = provider_gate
                if provider is None or storage_gate.get("status") != "validated":
                    failed = provider_gate if provider is None else storage_gate
                    audit.update(status=failed.get("status", "missing"), detail=failed.get("detail", "provider storage gate missing"))
                    recipes._atomic_json(report, audit)
                    return None, audit
                profile = profiles.add_provider_entries(profile, contract, provider, storage_gate["contract"])
                if include_io:
                    children = [provider_gate.get(key,{"status":"missing","detail":key+" unavailable"}) for key in ("providerRetentionGate","externalPackageGate","packageResultGate","packageReadGate")]
                    failed = next((child for child in children if child.get("status") != "validated"), None)
                    if failed:
                        audit.update(status=failed["status"],detail=failed.get("detail","I/O companion gate failed"))
                        recipes._atomic_json(report,audit)
                        return None,audit
                    profile = profiles.add_io_entries(profile,storage_gate["contract"],children[0]["contract"],children[1]["contract"])
                    profile = profiles.add_package_completion_entry(profile,children[2]["contract"])
                    profile = profiles.add_package_read_entries(profile,children[3]['contract'])
                    if include_transfer:
                        transform_gate=children[3].get('packageTransformGate',{'status':'missing','detail':'transfer companion unavailable'})
                        if transform_gate.get('status')!='validated':
                            audit.update(status=transform_gate['status'],detail=transform_gate.get('detail','transfer companion gate failed'))
                            recipes._atomic_json(report,audit)
                            return None,audit
                        profile=profiles.add_transfer_receiver_entries(profile,children[3]['contract'],transform_gate['contract'])
            manifest = profiles.project(profile)
            core.verify_game_files(selected, manifest)
            recipes._atomic_json(output, manifest)
            audit.update(status="validated", profileStatus="ready", managedHooks=2, nativeEntryHooks=len(manifest["nativeHooks"]),
                         manifestPath=str(output), evidenceBoundary=manifest["captureBoundary"])
        else:
            failed = queue_audit if queue is None else carrier_audit
            audit.update(status=failed["status"], detail=failed.get("detail", "companion gate failed"))
    recipes._atomic_json(report, audit)
    return manifest, audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--include-provider", action="store_true", help="Combine decoder preparation, ordinary/alternate factories, open dispatch and descriptor entries with source/owner observations.")
    parser.add_argument("--include-io", action="store_true", help="Also observe retained provider/device state and external-package path/key entries in the same window; implies provider.")
    parser.add_argument("--include-transfer", action="store_true", help="Also retain proved transfer/receiver interface fields in one combined entry-only window; implies I/O and requires the validated transform companion.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    output = args.output or (TRANSFER_OUTPUT if args.include_transfer else IO_OUTPUT if args.include_io else PROVIDER_OUTPUT if args.include_provider else DEFAULT_OUTPUT)
    report = args.report or (TRANSFER_REPORT if args.include_transfer else IO_REPORT if args.include_io else PROVIDER_REPORT if args.include_provider else DEFAULT_REPORT)
    manifest, audit = prepare(args.game_root, output, report, include_provider=args.include_provider,include_io=args.include_io,include_transfer=args.include_transfer)
    print(f"EndfieldCapture source/owner: {audit['status']}; profile {audit['profileStatus']}")
    if manifest:
        print(f"2 managed + {len(manifest['nativeHooks'])} entry-only native observations -> {output}")
    return 0 if manifest else 2


if __name__ == "__main__":
    raise SystemExit(main())
