"""Prove sampled actor scene membership and audit saved contact evidence offline.

Recompute the source-bound Collider/PxShape comparison first. A missing actor
header stays unavailable, even when another epoch captured the same pointer.
Contact configuration, scene membership and an empty split-results report array
never establish physical contact participation or absence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from scripts.common import sha256_file
from scripts.game_data import collision_runtime_mesh as mesh
from scripts.game_data import collision_runtime_shape as shape
from scripts.game_data.collision_runtime_mesh_native import load_layout
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text

SCHEMA = "endfield.collision-runtime-actor-comparison.v1"
NATIVE_SCHEMA = "endfield.collision-runtime-actor-native-contract.v1"
CONTRACT = CONTRACTS_DIR / "collision_runtime_actor_native.json"


def decode_membership(view, actor, player_base, contract):
    """Interpret the specialized rigid-static consumer, without a BSS lookup."""
    layout, scene = contract["layout"]["actor"], contract["layout"]["scene"]
    result = dict(status="null_actor" if not actor else "actor_member_only", actorAddress=f"{actor:016x}")
    if not actor:
        return result
    mesh._require(view.scalar(actor, "Q", "actor.vtable") == player_base+layout["vtableRva"], "PxRigidStatic vtable")
    result.update(status="typed_actor", concreteType=contract["typeName"]["ascii"])
    control = view.scalar(actor+layout["scb"]+layout["control"], "I", "actor.registrationControl")
    state = control >> layout["stateShift"]
    mesh._require(str(state) in contract["representation"]["controlStates"], "registration state out of range")
    stored = view.scalar(actor+layout["scb"], "Q", "actor.storedScbScene")
    result.update(controlWord=control, controlState=contract["representation"]["controlStates"][str(state)],
                  storedScbSceneAddress=f"{stored:016x}", apiMembership=state in (1, 2), fullyRegistered=False)
    if state not in (1, 2):
        result["status"] = "not_api_member"
        return result
    mesh._require(stored != 0, "registered actor has null ScbScene")
    public = stored+scene["fromScb"]
    mesh._require(public > 0, "invalid public scene conversion")
    mesh._require(view.scalar(public, "Q", "actor.publicSceneVtable") == player_base+scene["vtableRva"], "PxScene vtable")
    result.update(status="in_scene" if state == 2 else "insert_pending", sceneAddress=f"{public:016x}", fullyRegistered=state == 2)
    return result


def decode_scene_evidence(view, collider, player_base, contract):
    """Observe the scene and report storage; deliberately make no pair claim."""
    layout = contract["layout"]
    wrapper = view.scalar(collider+layout["collider"]["sceneWrapper"], "Q", "collider.sceneWrapper")
    mesh._require(wrapper != 0, "null Collider physics scene wrapper")
    public = view.scalar(wrapper+layout["wrapper"]["scene"], "Q", "wrapper.publicScene")
    mesh._require(public != 0, "null wrapper public scene")
    mesh._require(view.scalar(public, "Q", "wrapper.publicSceneVtable") == player_base+layout["scene"]["vtableRva"], "wrapper PxScene vtable")
    result = dict(wrapperAddress=f"{wrapper:016x}", sceneAddress=f"{public:016x}",
                  contactParticipation="unresolved", contactAbsence="unresolved", observations=[])
    scb = public+layout["scene"]["scb"]
    contact = layout["contact"]
    for label in ("split_headers", "raw_report_pairs", "reverse_actor_array"):
        row = dict(field=label, status="unavailable")
        try:
            if label == "split_headers":
                address = scb+contact["queue"]
                pointer = view.scalar(address, "Q", "contact.splitHeaderEntries")
                count = view.scalar(address+contact["count"], "I", "contact.splitHeaderCount")
                capacity = view.scalar(address+contact["capacity"], "I", "contact.splitHeaderCapacity") & 0x7fffffff
            elif label == "raw_report_pairs":
                row["requiredPointerAddress"] = f"{scb+contact['reportCore']:016x}"
                address = view.scalar(scb+contact["reportCore"], "Q", "contact.reportCore")
                mesh._require(address != 0, "null contact report core")
                pointer = view.scalar(address+contact["actorPairs"], "Q", "contact.reportActorPairs")
                count = view.scalar(address+contact["actorPairCount"], "I", "contact.reportActorPairCount")
                capacity = None
            else:
                address = public
                row["requiredPointerAddress"] = f"{public+layout['scene']['actorEntries']:016x}"
                pointer = view.scalar(public+layout["scene"]["actorEntries"], "Q", "scene.reverseActorEntries")
                count = view.scalar(public+layout["scene"]["actorCount"], "I", "scene.reverseActorCount")
                capacity = None
            mesh._require(count <= 1_000_000 and (capacity is None or count <= capacity), "invalid scene array count/capacity")
            mesh._require(count == 0 or pointer != 0, "nonempty scene array has null entries")
            row.update(status="observed_empty" if count == 0 else "observed_nonempty", address=f"{address:016x}",
                       entriesAddress=f"{pointer:016x}", count=count, capacity=capacity)
            if count:
                row["detail"] = "Stored count only; record layout, freshness and actor/contact joins are not decoded."
        except (mesh.WindowGap, ValueError) as exc:
            row["detail"] = str(exc)
        result["observations"].append(row)
    result["boundary"] = contract["representation"]["contactBoundary"]
    return result


def completed_scene_join(entry, end, entries, returns, profile, player_base, wrapper):
    """Join raw v5 records, not a cached sample's parentCall interpretation."""
    if entry["kind"] != 13:
        return dict(status="not_physics_checkpoint")
    core, finish = entries[entry["parent"]], returns[entry["parent"]]
    mesh._require(core["kind"] == finish["kind"] == 11, "snapshot parent is not physics core")
    raw = bytes.fromhex(finish["after"])
    original_return, expected, count = struct.unpack_from("<QQQ", raw)
    mesh._require(count == 1 and expected == wrapper, "completed physics scene wrapper/count differs")
    completions = [r for r in entries.values() if r["parent"] == core["call"] and r["kind"] == 12]
    mesh._require(len(completions) == 1, "missing/ambiguous raw completion child")
    completion = completions[0]
    mesh._require(mesh._le_pointer(completion["args"][0]) == wrapper and
                  mesh._le_pointer(completion["args"][1]) == player_base+profile["physicsSnapshots"]["completionReturnRva"],
                  "completion native scene/caller differs")
    mesh._require(returns[completion["call"]]["qpc"] <= original_return <= entry["qpc"] <= end["qpc"] <= finish["qpc"],
                  "snapshot/completion timing differs")
    return dict(status="matched", parentCall=core["call"], completionCall=completion["call"],
                originalCoreReturnQpc=original_return, snapshotEntryQpc=entry["qpc"],
                wrapperAddress=f"{wrapper:016x}", boundary="conditional: same completed native scene; separately timed windows")


def compare(root, raw_mesh_path, cooked_path, *, game_root=None, reinspect=False):
    result = dict(schema=SCHEMA, status="failed", session=str(root.resolve()), samples=[], diagnostics=[])
    try:
        attachment = shape.compare(root, raw_mesh_path, cooked_path, game_root=game_root, reinspect=reinspect)
        failure_samples = [{k: row[k] for k in ("call", "status", "detail") if k in row}
                           for row in attachment.get("samples", []) if row.get("status") != "attachment_matched"][:3]
        mesh._require(attachment["status"] in ("validated", "partial"),
                      "shape comparison:"+str(attachment["status"])+":"+
                      json.dumps(dict(diagnostics=attachment["diagnostics"], samples=failure_samples))[:1400])
        admission, profile, receipt, _ = mesh.load_admission(root, game_root=game_root)
        mesh._require(admission["journalSha256"] == attachment["journalSha256"] and
                      admission["nativeMemory"]["sha256"] == attachment["archiveSha256"] and
                      sha256_file(root/"private/collision-build.json") == attachment["profileSha256"], "capture changed between comparisons")
        directory = game_root.parent if game_root and game_root.name == "Endfield_Data" else game_root
        paths = {name: directory/row["relativePath"] if directory else Path(row["path"]) for name, row in profile["files"].items()}
        contract, gate = load_layout(gameassembly=paths["gameAssembly"], metadata=paths["metadata"], unityplayer=paths["unityPlayer"],
                                     contract_path=CONTRACT, schema=NATIVE_SCHEMA, validator="collision_runtime_actor_native")
        result["nativeGate"] = gate
        mesh._require(contract is not None, "actor native layout:"+gate["status"]+":"+gate.get("detail", ""))
        mesh._require(contract["nativeInputs"] == attachment["nativeGate"]["nativeInputs"], "actor/shape native build differs")
        archive = (root/"native-memory.bin").read_bytes()
        mesh._require(mesh._sha(archive) == attachment["archiveSha256"], "archive changed before actor reads")
        journal = [json.loads(line) for line in (root/"events.jsonl").read_text("utf-8").splitlines() if line.strip()]
        entries = {r["call"]:r for r in journal if r["phase"] == 0}
        returns = {r["call"]:r for r in journal if r["phase"] == 1}
        base = mesh._le_pointer(receipt["playerBase"])
        for sample in attachment["samples"]:
            row = dict(call=sample["call"], completedStepOrdinal=sample["completedStepOrdinal"], shapeComparison=sample)
            if "colliderAddress" not in sample:
                row.update(status="unavailable", detail=sample.get("detail", "same-call Collider root unavailable"),
                           sceneEvidence=dict(status="unavailable", detail="same-call Collider root unavailable"),
                           contactParticipation="unresolved")
                result["samples"].append(row)
                continue
            view = mesh.WindowView(admission["nativeMemory"]["windows"], archive, call=sample["call"],
                                   root=sample["colliderAddress"], role="collider")
            row["reads"] = view.reads
            try:
                scene = decode_scene_evidence(view, int(sample["colliderAddress"], 16), base, contract)
                for observation in scene["observations"]:
                    if "requiredPointerAddress" in observation:
                        address = int(observation["requiredPointerAddress"], 16)
                        observation["completeArchiveWindowsAnyCall"] = sum(
                            int(w["address"], 16) <= address and int(w["address"], 16)+w["bytes"] >= address+8
                            for w in admission["nativeMemory"]["windows"])
                        # Availability census only: other roots/calls never supply decoded bytes.
                row["sceneEvidence"] = scene
                row["completedSceneJoin"] = completed_scene_join(entries[sample["call"]], returns[sample["call"]], entries, returns,
                                                                 profile, base, int(scene["wrapperAddress"], 16))
            except (ValueError, KeyError, TypeError, struct.error) as exc:
                row["sceneEvidence"] = dict(status="unavailable" if isinstance(exc, mesh.WindowGap) else "rejected", detail=str(exc))
            try:
                mesh._require(sample["status"] == "attachment_matched", "same-call Collider/PxShape/cache attachment unavailable")
                observed = [a for a in sample.get("auxiliary", []) if a["field"] == "actor" and a["status"] == "observed"]
                mesh._require(len(observed) == 1, "same-call shape actor association unavailable")
                row["actorAddress"] = observed[0]["address"]
                row.update(decode_membership(view, int(observed[0]["address"],16), base, contract))
                if row["status"] in ("in_scene", "insert_pending"):
                    scene = row["sceneEvidence"]
                    mesh._require("sceneAddress" in scene and row["sceneAddress"] == scene["sceneAddress"], "actor/Collider scene differs or unavailable")
                    mesh._require(row.get("completedSceneJoin", {}).get("status") in ("matched", "not_physics_checkpoint"), "completed scene join unavailable")
            except (ValueError, KeyError, TypeError, struct.error) as exc:
                row.update(status="unavailable" if isinstance(exc, mesh.WindowGap) or sample["status"] != "attachment_matched" else "rejected", detail=str(exc))
                row.pop("fullyRegistered", None)
                row.pop("apiMembership", None)
            row["contactParticipation"] = "unresolved"
            result["samples"].append(row)
        members = [r for r in result["samples"] if r["status"] == "in_scene"]
        rejected = any(r["status"] == "rejected" or r["sceneEvidence"].get("status") == "rejected" for r in result["samples"])
        mesh._require(result["samples"], "no admitted samples")
        result.update(status="rejected" if rejected else "validated" if len(members) == len(result["samples"]) else "partial",
                      source=attachment["source"], shapeNativeGate=attachment["nativeGate"],
                      journalSha256=attachment["journalSha256"], archiveSha256=attachment["archiveSha256"], profileSha256=attachment["profileSha256"],
                      sampleCoverage=dict(Counter(r["status"] for r in result["samples"])),
                      uniqueRegisteredActors=len({r["actorAddress"] for r in members}),
                      uniqueRegisteredScenes=len({r["sceneAddress"] for r in members}),
                      completedSceneMatches=sum(r.get("completedSceneJoin",{}).get("status") == "matched" for r in members),
                      contactParticipation="unresolved", evidenceBoundary=contract["evidenceBoundary"],
                      remainingGaps=["Missing same-call actor headers cannot be filled from another epoch.",
                                     "Normal contact callback records/raw report pairs and persistent touching interactions are not recovered.",
                                     "Empty lazy split-results headers do not establish absence of contacts.",
                                     "Registration is sampled; windows are separately timed and do not prove continuous lifetime."])
        mesh._require(sha256_file(root/"events.jsonl") == result["journalSha256"] and
                      sha256_file(root/"native-memory.bin") == result["archiveSha256"] and
                      sha256_file(root/"private/collision-build.json") == result["profileSha256"], "capture changed during actor comparison")
        mesh._require(sha256_file(raw_mesh_path) == result["source"]["rawMeshSha256"] and
                      sha256_file(cooked_path) == result["source"]["cookedSha256"], "source changed during actor comparison")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, struct.error) as exc:
        result.update(status="failed", samples=[], diagnostics=[dict(check="runtime_actor_comparison", detail=str(exc)[:1600])])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--raw-mesh", type=Path, required=True)
    parser.add_argument("--cooked", type=Path, required=True)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--reinspect", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    output = mesh._output_path(args.output or args.session/"collected/runtime-actor-comparison.json")
    report = compare(args.session, args.raw_mesh, args.cooked, game_root=args.game_root, reinspect=args.reinspect)
    atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:report.get(k) for k in ("status", "sampleCoverage", "uniqueRegisteredActors", "uniqueRegisteredScenes", "completedSceneMatches", "contactParticipation", "diagnostics")}, ensure_ascii=False))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
