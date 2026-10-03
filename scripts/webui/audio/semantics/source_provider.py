"""Compact static provider-preparation evidence, independent of live captures."""
from pathlib import Path
from typing import Any

from scripts.game_data import wwise_decoder_provider_native as native

SCHEMA = "endfield.audio-static-provider-preparation.v1"


def build_static_provider_preparation(*, gameassembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {"schema": SCHEMA, "status": "missing", "evidenceKind": "static", "claims": []}
    if gameassembly is None or metadata is None:
        result["reason"] = "explicit_selected_native_paths_missing"
        return result
    gameassembly, metadata = Path(gameassembly), Path(metadata)
    # The plugin path is relative to the explicitly selected GameAssembly,
    # never an environment/default install or a path from a saved report.
    contract, audit = native.load_validated_decoder_provider_contract(
        gameassembly=gameassembly, metadata=metadata,
        ak_sound_engine=gameassembly.resolve().parent / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll",
        include_storage=True,
    )
    result.update(status=audit["status"], reason=audit.get("detail", ""))
    if contract is None or audit["status"] != "validated":
        if audit.get("diagnostic"):
            result["diagnostic"] = audit["diagnostic"]
        return result
    result.update(
        claims=[
            {"id": "decoderOwnerSource", "evidenceBoundary": "direct"},
            {"id": "conditionalPointerOrWord", "evidenceBoundary": "conditional"},
            {"id": "argumentHalfword", "evidenceBoundary": "direct"},
            {"id": "alternateOwnerInput", "evidenceBoundary": "conditional"},
        ],
        evidenceBoundary=contract["evidenceBoundary"],
    )
    storage = audit.get("providerStorageGate", {})
    result["providerStorageStatus"] = storage.get("status", "missing")
    if storage.get("status") == "validated":
        result["claims"].extend([
            {"id": "conditionalProviderInterface", "evidenceBoundary": "conditional"},
            {"id": "conditionalOwnedText", "evidenceBoundary": "conditional"},
        ])
        result["providerStorageBoundary"] = storage["evidenceBoundary"]
    else:
        result["providerStorageReason"] = storage.get("detail", "provider_storage_not_validated")
    return result
