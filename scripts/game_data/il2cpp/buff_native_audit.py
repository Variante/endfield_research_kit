"""Corpus-independent native proofs needed to admit selected Buff roots.

This is deliberately a separate receipt from context_audit's corpus witnesses.
It runs the same formatter/context/dispatcher validators on selected binaries;
it establishes no serialized source identity, source cursor, or whole-root EOF.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context_audit_common import (
    AUDIT_PINS, CONSUMER_WINDOWS, GA_SHA, MD_SHA, UNITY_SHA, NATIVE_CONTRACT_PATH, require, sha, sweep,
)
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order, buff_union_routes
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.corpus_gate import _package_import_closure
from scripts.repo_paths import REPO_ROOT


FORMAT = "endfield.buff-selected-native-audit.v1"
SELECTED = (("63", "buff_63_native.json"), ("61", "buff_61_native.json"),
            ("B2", "buff_b2_native.json"))


def audit(game_root: Path) -> dict:
    """Reprove all selected native reads without consulting a generated corpus."""
    game_root = Path(game_root).resolve()
    assembly = game_root.parent / "GameAssembly.dll"
    metadata = game_root / "il2cpp_data/Metadata/global-metadata.dat"
    unity = game_root.parent / "UnityPlayer.dll"
    gate = check_installed_native_inputs(GA_SHA, MD_SHA, gameassembly=assembly, metadata=metadata)
    require(gate.status, "validated", f"Buff selected native inputs: {gate.detail}")
    require(sha(unity), UNITY_SHA, unity)
    # Pin the implementation and reviewed declarations before any proof. The
    # generated hashes are drift detection, never a substitute for validators.
    paths = set(_package_import_closure(Path(__file__)))
    paths.update(CONTRACTS_DIR / name for _tag, name in SELECTED)
    paths.add(NATIVE_CONTRACT_PATH)
    paths.update(REPO_ROOT / "tools/endfield-il2cpp" / name for name in
                 ("map_body_targets_to_gameassembly.py", "catalog_option_flow_metadata.py"))
    paths.update((assembly, metadata, unity))
    before = {str(p.resolve()): sha(p) for p in sorted(paths)}
    image = open_native_image(assembly, metadata)
    pe, md, reg = image.pe, image.metadata, image.registration
    require(hashlib.sha256(pe.buf).hexdigest().upper(), GA_SHA, assembly)
    require(hashlib.sha256(md.buf).hexdigest().upper(), MD_SHA, metadata)
    registration = AUDIT_PINS["registration"]
    require(image.code_registration, registration["codeRegistrationVa"], assembly)
    require(image.metadata_registration, registration["metadataRegistrationVa"], assembly)
    for begin, end, expected in CONSUMER_WINDOWS:
        require(hashlib.sha256(pe.bytes_at_va(pe.image_base + begin, end - begin)).hexdigest().upper(),
                expected, assembly, begin)
    # Preserve the complete generic-instance gate that used to precede these
    # rows in context_audit; only unrelated corpus witnesses are separated.
    generic_summary, _rows, failures = sweep(image.instantiations)
    require(failures, [], assembly)
    routes = buff_union_routes(pe, md, reg, image.modules, image.owners, source=str(assembly))
    selected = {}
    for tag, name in SELECTED:
        selected[f"selectedBuff{tag}ReadOrder"] = buff_action_read_order(
            pe, md, reg, image.instantiations, image.modules, image.owners,
            source=str(assembly), contract_path=CONTRACTS_DIR / name, native_image=image)
    for path, expected in before.items():
        require(sha(path), expected, path)
    return {
        "format": FORMAT, "schemaVersion": 1, "status": "structural-only", "failures": [],
        "nativeInputs": {"gameassembly": str(assembly), "gameassemblySha256": GA_SHA,
                         "metadata": str(metadata), "metadataSha256": MD_SHA,
                         "unityplayer": str(unity), "unityplayerSha256": UNITY_SHA},
        "sourceHashes": before, "genericInstantiationSummary": generic_summary,
        "selectedBuffUnionRoutes": routes, **selected,
        "evidenceBoundary": "direct selected native read order and static context/dispatcher joins; "
                            "no corpus, source cursor, whole-root EOF or runtime claim",
    }
