"""Offline DamageAction observations; explicit synchronous enclosure only."""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any, Callable, Iterable

from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.mission_trace_invocations import Invocations, PAIRED_ABI
from scripts.game_data.mission_trace_replay import fingerprint
from scripts.repo_paths import REPO_ROOT

ROOT_HOOK = "damage.Action.ExecuteInternal"
SCHEMA = "endfield.damage-runtime-inspection.v1"
BOUNDARY = ("Observed same-thread synchronous DamageAction enclosure only. No actor/skill ownership, "
            "RNG seed, server authority, omitted callbacks or complete combat claim.")


def project_damage_rows(rows: Iterable[dict[str, Any]], hooks: list[dict[str, Any]], *,
                        source_context: dict[str, Any], compact: bool = False,
                        attribute_sink: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Project already inspected decoded rows; callers must admit their source first.

    This pure helper validates pairs again, but does not authenticate a session.
    Each observation preserves the decoded row, including fields and raw bits.
    """
    report = dict(schema=SCHEMA, status="projected", combatComplete=False,
                  sourceContext=source_context, boundary=BOUNDARY,
                  actions=[], unownedObservations=[], diagnostics=[])
    report["projectionMode"] = ("compact-attributes-sidecar-v1" if attribute_sink is not None
                                else "compact-attributes-v1" if compact else "full")
    report["projectionCounts"] = {"decodedRows": 0, "inlineObservationRows": 0,
                                  "attributeEntryRowsOmitted": 0, "attributeReturnRowsCompacted": 0}
    report["attributeSnapshots"] = []
    snapshot_groups, active_attributes, dumps = {}, {}, {}
    pairs, stacks, owners = Invocations(), {}, {}
    for row in rows:
        report["projectionCounts"]["decodedRows"] += 1
        index = trace.integer(row.get("hookIndex"), "hookIndex", len(hooks)-1)
        hook = hooks[index]
        trace.require(row.get("hook") == hook["name"] and
                      PAIRED_ABI.fullmatch(hook.get("abiId", "")), "damage projection requires named paired hooks")
        raw = {**row, "args": row.get("rawArgs")}
        pairs.observe(raw, hook)
        thread, identity = row["threadId"], row["invocationId"]
        stack = stacks.setdefault(thread, [])
        if row["phase"] == "enter":
            owner = owners.get((thread, row["parentInvocationId"]))
            if row["hook"] == ROOT_HOOK:
                owner = dict(invocationId=identity, parentInvocationId=row["parentInvocationId"],
                             threadId=thread, enter=dict(row), exit=None,
                             attribution={"actor": "unknown", "skill": "unknown", "target": "unknown"},
                             observations=[], attributeReturnCount=0)
                report["actions"].append(owner)
            owners[thread, identity] = owner
            dumps[thread, identity] = (identity if row["hook"] == "damage.Pack.DumpAttributes"
                                       else dumps.get((thread, row["parentInvocationId"])))
            if compact and row["hook"] == "buff.Attributes.GetValue":
                active_attributes[thread, identity] = row
            stack.append(identity)
        else:
            owner = owners.get((thread, identity))
            trace.require(stack and stack.pop() == identity, "damage projection crossing return")
            if row["hook"] == ROOT_HOOK and owner is not None:
                owner["exit"] = dict(row)
        role = ("formula" if row["hook"].startswith("damage.Formula.") else
                "pack" if row["hook"].startswith("damage.Pack.") else
                "hpModifier" if "ApplyModifier" in row["hook"] else
                "attribute" if row["hook"] == "buff.Attributes.GetValue" else
                "constant" if row["hook"].startswith("damage.Const.") else "action")
        dump_identity = dumps.get((thread, identity))
        if row["phase"] != "enter":
            owners.pop((thread, identity), None)
            dumps.pop((thread, identity), None)
        if compact and role == "attribute":
            if row["phase"] == "enter":
                report["projectionCounts"]["attributeEntryRowsOmitted"] += 1
                continue
            trace.require(PAIRED_ABI.fullmatch(hook["abiId"])[1] == "double",
                          "compact attribute snapshot requires double return ABI")
            entered = active_attributes.pop((thread, identity))
            fields = {field["label"]: field for field in entered.get("fields", [])}
            fields.update({field["label"]: field for field in row.get("fields", [])})
            uid = fields.get("attributesInstanceUid")
            caller = row.get("callerGameAssemblyRva")
            key = (thread, dump_identity, json.dumps(uid, sort_keys=True), caller,
                   owner["invocationId"] if owner is not None else None)
            group = snapshot_groups.get(key)
            if group is None:
                group = dict(threadId=thread, dumpInvocationId=dump_identity,
                             actionInvocationId=key[-1], attributesInstanceUid=uid,
                             callerGameAssemblyRva=caller,
                             columns=["sequence", "invocationId", "parentInvocationId", "thisRaw",
                                      "attributeTypeRaw", "attributeTypeField", "returnValue", "decodedReturnValue"], values=[])
                if attribute_sink is None:
                    snapshot_groups[key] = group
                    report["attributeSnapshots"].append(group)
            bits = row.get("returnValue")
            value = struct.unpack("<d", bits.to_bytes(8, "little"))[0] if bits is not None else None
            args = row.get("rawArgs", [])
            group["values"].append([row["sequence"], identity, row["parentInvocationId"],
                                    args[0] if args else None, args[1] if len(args) > 1 else None,
                                    fields.get("attributeType"), bits,
                                    value if value is not None and math.isfinite(value) else None])
            if owner is not None:
                owner["attributeReturnCount"] += 1
            if attribute_sink is not None:
                attribute_sink(group)
            report["projectionCounts"]["attributeReturnRowsCompacted"] += 1
            continue
        report["projectionCounts"]["inlineObservationRows"] += 1
        observation = {"role": role, **row}
        if row["phase"] == "return":
            return_type = PAIRED_ABI.fullmatch(hook["abiId"])[1]
            bits = row.get("returnValue")
            if return_type in {"float", "double"}:
                value = struct.unpack("<f" if return_type == "float" else "<d",
                                      bits.to_bytes(4 if return_type == "float" else 8, "little"))[0]
                observation["decodedReturnValue"] = value if math.isfinite(value) else None
                observation["returnValueFinite"] = math.isfinite(value)
            elif return_type == "bool":
                observation["decodedReturnValue"] = bool(bits)
        if role == "hpModifier":
            observation["observedTargetIdentity"] = {
                field["label"]: dict(field) for field in row.get("fields", [])
                if field.get("label") in {"targetServerId", "targetBattleInstanceId", "targetEntityName",
                                           "attributesIdentity", "attributesInstanceUid"}}
        if owner is None:
            report["unownedObservations"].append(observation)
        else:
            owner["observations"].append(observation)
    report["invocations"] = pairs.finish(True)
    return report


def inspect_damage_session(session: Path, output_dir: Path, *, local_files: bool = False,
                           limits: trace.Limits = trace.Limits()) -> dict[str, Any]:
    """Decode a retained package with the maintained reader, then project pairs.

    Writes only below reports/. Admission failures produce an empty blocked report.
    Retained native/source declarations remain observations, never re-proved facts.
    """
    output_dir = output_dir.resolve()
    trace.require(output_dir.is_relative_to((REPO_ROOT / "reports").resolve()),
                  "damage inspection output must be under reports/")
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "damage.inspection.json"
    trace.require(not destination.exists(), "damage inspection output already exists")
    report = dict(schema=SCHEMA, status="blocked", combatComplete=False, boundary=BOUNDARY,
                  sourceContext={"sessionPath": str(session.resolve())}, actions=[], unownedObservations=[], diagnostics=[])
    try:
        inspected = trace.inspect_session(session, output_dir / "trace", local_files=local_files, limits=limits)
        report["sourceContext"] = {"sessionPath": str(session.resolve()), "inspection": inspected, "operatorDeclaredScenario": None,
                                   "nativeValidationReproved": False, "sourceValidationReproved": False}
        facts = inspected.get("receiptFacts", {})
        trace.require(inspected.get("status") == ("analyzed" if local_files else "inspected"),
                      "damage admission requires passing maintained inspection")
        trace.require(facts.get("collectionBoundFailureMarkers") == [],
                      "damage admission retains failure markers")
        trace.require(all(facts.get(key) is True for key in
                          ("captureCompleteClaim", "healthyClaim", "allJournalRowsAccounted",
                           "strictTransitionReceiptsConsistent", "nativeInputHashesBoundToProfile")),
                      "damage admission requires healthy complete accounted paired receipt and native profile binding")
        artifacts, inventory = (trace.snapshot_local_inventory if local_files else trace.verify_inventory)(session.resolve(), limits)
        trace.require(inventory.get("inventorySha256") == inspected["inventory"].get("inventorySha256"),
                      "damage admission inventory changed after inspection")
        profile, summary, hooks = trace.bindings(artifacts, limits)
        recipe = trace.read_object(CONTRACTS_DIR / "damage_runtime_kernel_capture.json", limits.json_bytes)
        expected = {h["name"] for h in recipe["hooks"]}
        trace.require(len(hooks) == len(expected) and {h["name"] for h in hooks} == expected,
                      "damage admission requires exactly the reviewed kernel hook selection")
        for hook in hooks:
            spec = next(item for item in recipe["hooks"] if item["name"] == hook["name"])
            abi = PAIRED_ABI.fullmatch(hook.get("abiId", ""))
            expected_return = spec["returnType"]
            if expected_return not in {"void", "bool", "float", "double", "int", "pointer"}:
                trace.require(hook.get("pairedAbiProof", {}).get("enumReturn", {}).get("type") == expected_return,
                              "damage admission missing selected enum return proof: " + hook["name"])
                expected_return = "int"
            trace.require(hook.get("returnType") == spec["returnType"] and bool(abi) and abi[1] == expected_return,
                          "damage admission return ABI differs: " + hook["name"])
            trace.require({field["label"] for field in hook.get("fields", [])} ==
                          {field["label"] for field in spec.get("fields", [])},
                          "damage admission field selection differs: " + hook["name"])
        decoded_path = output_dir / "trace" / inspected["decodedOutput"]
        decoded_pin = fingerprint(decoded_path, limits.output_bytes)
        def decoded_rows():
            with decoded_path.open("rb") as source:
                for count, line in enumerate(source):
                    trace.require(count < limits.rows and len(line) <= limits.output_line_bytes,
                                  "damage decoded row budget exceeded")
                    yield trace.parse_json(line, "damage decoded row")
        attribute_path = output_dir / "attribute-returns.jsonl"
        trace.require(not attribute_path.exists(), "damage attribute sidecar already exists")
        with attribute_path.open("w", encoding="ascii") as attribute_output:
            def write_attribute(snapshot):
                json.dump(snapshot, attribute_output, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
                attribute_output.write("\n")
            report = project_damage_rows(decoded_rows(), hooks, compact=True, attribute_sink=write_attribute, source_context={
            **report["sourceContext"], "decodedSource": {"path": str(decoded_path.resolve()), **decoded_pin}, "nativeInputs": profile.get("files"),
            "hooks": hooks, "inventory": inventory, "receipt": summary,
            "provenanceBoundary": "Retained session consistency only; package origin and live ABI/source selection not independently authenticated."})
        report["attributeSnapshotSource"] = {
            "path": str(attribute_path.resolve()), **fingerprint(attribute_path, limits.output_bytes),
            "rows": report["projectionCounts"]["attributeReturnRowsCompacted"],
            "format": "jsonl; each row carries explicit identities, columns and one values row",
            "boundary": "All attribute returns retained here; entry rows and full field/raw detail remain in decodedSource."}
        report["status"] = "observed"
        trace.require(bool(report["actions"]), "damage admission observed no DamageAction enclosure")
        trace.require(fingerprint(decoded_path, limits.output_bytes) == decoded_pin,
                      "damage decoded source changed during projection")
        for artifact in artifacts.values():
            trace.require(fingerprint(artifact["path"], limits.artifact_bytes)["sha256"] == artifact["sha256"],
                          "damage retained source changed during projection")
    except (trace.InspectionError, ValueError, OSError, KeyError, TypeError) as exc:
        report.update(status="blocked", actions=[], unownedObservations=[], attributeSnapshots=[])
        report["diagnostics"] = [{"validator": "damage_runtime_inspect", "failedCheck": "session_admission_or_pair_projection",
                                  "sourcePath": str(session.resolve()), "detail": str(exc)[:2048]}]
    with destination.open("w", encoding="ascii") as output:
        json.dump(report, output, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
        output.write("\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--local-files", action="store_true")
    args = parser.parse_args(argv)
    result = inspect_damage_session(args.session, args.output_dir, local_files=args.local_files)
    print(f"[damage_runtime_inspect] {result['status']}; actions={len(result['actions'])}; combatComplete=False")
    for diagnostic in result["diagnostics"]:
        print(diagnostic["detail"])
    return 0 if result["status"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
