"""Project authenticated stored Model source records onto collision variants.

PathHash/manifest, logical Bundle and actual prefab-root pointers all participate
in the raw join. Stored Model axes and prefab-local matrices remain separate;
this module never evaluates a runtime/world transform or creates map links.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path

from scripts.game_data import dynamic_model_native
from scripts.game_data.cooked_collision_corpus import _selected_ledger
from scripts.common import resolve_installed_game_data_root
from scripts.webui.assets.collision_runtime import object_key, variant_key

SCHEMA = "endfield.assets-collision-model-sources.v1"


def project_models(entries: list[dict], models: list[dict], *, data_names: dict[str, str] | None = None) -> dict:
    variants = {variant_key(e["cl"]): e for e in entries if "cl" in e}
    if len(variants) != sum("cl" in e for e in entries):
        raise ValueError("duplicate physical collision variant in Model projection")
    grouped, sources, edges = defaultdict(dict), set(), set()
    for model in models:
        if not model.get("colliderBindings"):
            continue
        if model["pathStatus"] != "unique_authored_path" or len(model["assets"]) != 1:
            raise ValueError("bound Model source has no unique authored path")
        source_key = (model["source"], model["gridOrdinal"], model["ordinal"], model["byteOffset"])
        for binding in model["colliderBindings"]:
            owner_key = object_key(binding["collider"])
            for buffer in binding["cookedBuffers"]:
                key = (*object_key(binding["mesh"]), buffer["kind"], binding["meshRawSha256"], buffer["sha256"])
                if key not in variants:
                    continue
                collision = variants[key]["cl"]
                owners = collision.get("authored", {}).get("owners", [])
                if not any(object_key(owner["identity"]) == owner_key
                           and model["assets"][0]["path"] in owner["prefabPaths"] for owner in owners):
                    raise ValueError("Model binding differs from admitted Assets collider/prefab owner")
                row = dict(source=model["source"], gridOrdinal=model["gridOrdinal"],
                           uniqueId=model["uniqueId"], ordinal=model["ordinal"], byteOffset=model["byteOffset"],
                           prefabPath=model["assets"][0]["path"], storedTransform=model["values"]["Trans"],
                           colliderIdentity={**binding["collider"], "pathId": str(binding["collider"]["pathId"]),
                                             "sourceOffset": str(binding["collider"]["sourceOffset"])},
                           storedPrefabLocalMatrix=binding["composedPrefabLocalMatrix"])
                if data_names and model["source"] in data_names:
                    row["dataName"] = data_names[model["source"]]
                row_key = (*source_key, owner_key)
                if row_key in grouped[key] and grouped[key][row_key] != row:
                    raise ValueError("conflicting stored Model/collider source records")
                grouped[key][row_key] = row
                sources.add(source_key); edges.add((source_key, owner_key))
    for entry in entries:
        if "cl" in entry:
            entry["cl"].pop("models", None)
    for key, rows in grouped.items():
        variants[key]["cl"]["models"] = dict(schema=SCHEMA, records=list(rows.values()))
    return dict(schema=SCHEMA, status="validated", counts=dict(linkedVariants=len(grouped),
                sourceModels=len(sources), modelColliderEdges=len(edges)),
                evidenceBoundary="Exact authored Model fields and unique native-gated manifest path, active logical Bundle and declared prefab-root joins. Stored Model axes and prefab-local collider matrices remain separate. Selected grid transforms, live parenting/animation, world placement and activation remain unproved.")


def apply_model_sources(entries: list[dict], *, receipt_path: Path, scenes: list[dict],
                        joined_scenes: list[dict], root: Path, game_root: Path | None = None,
                        export_root: Path | None = None) -> dict:
    if not scenes:
        raise ValueError("Model source projection needs admitted scene inputs")
    selected_game = (game_root or resolve_installed_game_data_root()).resolve()
    if selected_game.name.casefold() == "endfield_data":
        selected_game = selected_game.parent
    outer = Path(scenes[0]["provenance"]["outerSummaryPath"])
    ledger = root / scenes[0]["provenance"]["outerLedger"]
    current = dynamic_model_native.validate_receipt(receipt_path,
        gameassembly=selected_game / "GameAssembly.dll",
        metadata=selected_game / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat",
        outer_path=outer, ledger_path=ledger, root=root)
    logical, colliders = {}, {}
    for scene, joined in zip(scenes, joined_scenes, strict=True):
        if scene["inputSetSha256"] != current["inputSetSha256"]:
            raise ValueError("Model/scene current input sets differ")
        _, _, files, _ = _selected_ledger(outer, ledger,
            json.loads(Path(scene["selection"]["path"]).read_bytes()), current["inputSetSha256"])
        for key, row in files.items():
            if key in logical and logical[key] != row["fileName"]:
                raise ValueError("Model scene source has conflicting logical Bundle names")
            logical[key] = row["fileName"]
        for row in joined["colliders"]:
            colliders.setdefault(object_key(row["collider"]["identity"]), row)
    dynamic_model_native.join_model_colliders(current["models"], dict(colliders=list(colliders.values())), logical)
    dynamic_model_native.check_receipt_snapshot(current)
    data_names = {}
    if export_root is not None:
        prefix = "Data/DynamicStreaming/"
        for row in current["files"]:
            relative = row["virtualPath"][len(prefix):]
            if Path(row["path"]).resolve() == (export_root / "raw/DynamicStreaming" / relative).resolve():
                data_names[row["virtualPath"]] = relative
    result = project_models(entries, current["models"], data_names=data_names)
    result["sourceCounts"] = current["counts"]
    return result
