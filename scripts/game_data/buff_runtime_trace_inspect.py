"""Join retained Buff entry observations without promoting pointers to ownership."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

from scripts.game_data import mission_trace_inspect as trace

CONSUMERS = frozenset({
    "buff.CheckHp.ExecuteInternal", "buff.CheckPoiseValue.ExecuteInternal",
    "buff.ReadSkillSettingData.ExecuteInternal", "buff.SendBattleSignalToLevel.ExecuteInternal",
    "buff.GetTargetBuffBBAdvanced.ExecuteInternal", "buff.StoreAttributeValue.ExecuteInternal",
    "buff.Probablity.ExecuteInternal",
    "buff.CheckEntityNum.ExecuteInternal", "buff.AddGlobalCDTimer.ExecuteInternal",
    "buff.NotifyCharPassiveUIAction.ExecuteInternal",
})
INITIALIZERS = frozenset({
    "buff.AbilityActionData.NewAction", "buff.SequenceAction.Init", "buff.Skill.Init",
    "buff.Ability.Init", "buff.SkillHighlightEnvironment.Constructor",
})
DISPATCH_HOOK = "buff.AbilityActionData.DispatchAssignData"
IDENTITIES = ("entryStoredBuffId", "entryDataId", "entryInstanceUid", "entryClientInstId")
BOUNDARY = (
    "Retained entry observations only. A Buff Reset brackets an observed reference window, "
    "not an independently proved lifetime. Supplied, stored and instance identities stay distinct. "
    "Same-reference associations and later matching assignment arguments do not prove writes, "
    "returns, action-data selection, resolved targets, IFix or final gameplay effects."
)


def fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            length += len(chunk)
    return {"path": str(path.resolve()), "bytes": length, "sha256": digest.hexdigest()}


def checked_pin(pin: dict[str, Any]) -> dict[str, Any]:
    actual = fingerprint(Path(pin["path"]))
    trace.require(actual["bytes"] == pin.get("bytes", pin.get("length")) and
                  actual["sha256"].lower() == pin["sha256"].lower(),
                  f"Buff schema join: input byte identity differs: {pin['path']}")
    return actual


def join_canonical_sources(result: dict[str, Any], profile: dict[str, Any],
                           summary_path: Path, ledger_path: Path, *, max_ledger_bytes: int = 4 * 1024**3) -> dict[str, Any]:
    """Use a passing canonical receipt; never run another family/native gate here."""
    summary_pin = fingerprint(summary_path)
    summary = trace.read_object(summary_path, 32 * 1024**2)
    trace.require(summary.get("status") == "complete", "Buff schema join: canonical report incomplete")
    provenance = summary["provenance"]
    ledger_pin = checked_pin({"path": str(ledger_path), **provenance["outputFiles"]})
    family = provenance["familyReports"]["BuffData"]
    family_pin = checked_pin(family)
    native_sources = {Path(item["path"]).name.lower(): item for item in family["selectedRootSources"]
                      if Path(item["path"]).name.lower() in ("gameassembly.dll", "global-metadata.dat", "unityplayer.dll")}
    trace.require(set(native_sources) == {"gameassembly.dll", "global-metadata.dat", "unityplayer.dll"},
                  "Buff schema join: missing selected native input pins")
    for key, name in (("gameAssembly", "gameassembly.dll"), ("metadata", "global-metadata.dat")):
        captured = profile["files"][key]
        trace.require(captured["sha256"].lower() == native_sources[name]["sha256"].lower() and
                      captured["bytes"] == native_sources[name]["length"],
                      f"Buff schema join: retained {key} differs from canonical build")
    declared = provenance["buffSelectedRootReplayInputs"]
    trace.require(isinstance(declared, list) and 0 < len(declared) <= 4096, "Buff schema join: reader input budget")
    pins = [checked_pin(item) for item in declared]
    pinned_paths = {item["path"]: item for item in pins}
    for item in native_sources.values():
        actual_path = str(Path(item["path"]).resolve())
        trace.require(actual_path in pinned_paths and pinned_paths[actual_path]["sha256"].lower() == item["sha256"].lower(),
                      "Buff schema join: selected native input not covered by replay receipt")
    selected, seen = {}, set()
    buff_rows, total_bytes = 0, 0
    with gzip.open(ledger_path, "rb") as source:
        while line := source.readline(16 * 1024**2 + 1):
            total_bytes += len(line)
            trace.require(total_bytes <= max_ledger_bytes and len(line) <= 16 * 1024**2 and line.endswith(b"\n"),
                          "Buff schema join: expanded ledger/line budget exceeded")
            if b'BuffData' not in line:
                continue
            row = trace.parse_json(line, "canonical Buff row")
            if row.get("family") != "BuffData":
                continue
            buff_rows += 1
            relative = row["exportRelativePath"]
            trace.require(relative not in seen and relative.startswith("BuffData/"), "Buff schema join: duplicate/invalid source path")
            seen.add(relative)
            name = Path(relative).stem
            if name not in result["definitionCounts"]:
                continue
            candidate = result["sourceCandidates"].get(name)
            trace.require(candidate is not None and candidate["path"] == "game/Json/" + relative and
                          candidate["bytes"] == row["length"] and
                          candidate["sha256"].lower() == row["logicalSha256"].lower(),
                          f"Buff schema join: archived/canonical source differs: {name}")
            detail = row.get("detail") or {}
            exact = row["status"] == "schema_decoded" and detail.get("wholeSchemaExact") is True
            selected[name] = {"path": candidate["path"], "sha256": candidate["sha256"], "bytes": candidate["bytes"],
                              "status": row["status"], "wholeStoredSchemaExact": exact,
                              "residualDiagnostic": str(detail.get("rootSharedEventRefusal") or row.get("diagnostic") or "")[:2048],
                              "runtimeDataSelectionExact": False}
    trace.require(buff_rows == summary["summary"]["families"]["BuffData"]["files"] and
                  set(selected) == set(result["definitionCounts"]), "Buff schema join: source coverage count differs")
    all_pins = [summary_pin, ledger_pin, family_pin, *pins]
    trace.require(all_pins == [fingerprint(Path(item["path"])) for item in all_pins], "Buff schema join: receipt/inputs changed during join")
    return {"status": "joined", "inputSetSha256": summary["inputSetSha256"], "inputs": all_pins,
            "definitions": selected,
            "summary": {"observedDefinitions": len(selected),
                        "wholeStoredSchemaExact": sum(item["wholeStoredSchemaExact"] for item in selected.values()),
                        "remainingStoredSchema": sum(not item["wholeStoredSchemaExact"] for item in selected.values())},
            "boundary": "Canonical whole-file structure and archived bytes joined; neither runtime file loading nor a particular action-data node is proved."}


def fields(row: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for item in row["fields"]:
        trace.require(item.get("state") in (1, 4),
                      f"Buff join: sequence {row['sequence']} field {item.get('label')} is not exact/null")
        trace.require(item["label"] not in result, "Buff join: duplicate field label")
        result[item["label"]] = item.get("value")
    return result


def associate_skill_initializers(consumers: list[dict[str, Any]],
                                 entries: list[dict[str, Any]], *, buff_references: set[int]) -> None:
    """Retain prior initializer arguments, never cast an IActionEnvironment."""
    kinds = (
        ("buff.SkillHighlightEnvironment.Constructor", "skillEnvironmentConstructorAssociation",
         "environmentConstructorEntry", "skillEnvironmentGap", "skill-environment-constructor", "constructor"),
        ("buff.Ability.Init", "abilityInitializationAssociation",
         "abilityInitializationEntry", "abilityInitializationGap", "Ability-initialization", "Ability-initialization"),
    )
    initializers: dict[str, dict[int, list[dict[str, Any]]]] = {
        kind[0]: defaultdict(list) for kind in kinds}
    skill_entries: dict[int, list[dict[str, Any]]] = defaultdict(list)
    threads: dict[int, set[int]] = defaultdict(set)
    for entry in entries:
        environment = entry["fields"].get("suppliedEnvironmentIdentity")
        if isinstance(environment, int) and environment > 0:
            threads[environment].add(entry["threadId"])
        if entry["hook"] in initializers:
            initializers[entry["hook"]][entry["receiver"]].append(entry)
            threads[entry["receiver"]].add(entry["threadId"])
        elif entry["hook"] == "buff.Skill.Init":
            skill_entries[entry["receiver"]].append(entry)
    for consumer in consumers:
        threads[consumer["entryFields"]["entryEnvironment"]].add(consumer["threadId"])
    for consumer in consumers:
        environment = consumer["entryFields"]["entryEnvironment"]
        for hook, association_key, entry_key, gap_key, missing_name, repeated_name in kinds:
            observed = initializers[hook].get(environment, [])
            prior = [entry for entry in observed if entry["sequence"] < consumer["sequence"]]
            entry = prior[-1] if prior else None
            gap = "no-prior-observed-" + missing_name
            if entry:
                value = entry["fields"]
                owner = value["suppliedSkillIdentity"]
                name = value["suppliedSkillStoredId"]
                identity = (name, value["suppliedSkillDataId"], value["suppliedSkillInstId"])
                if len(observed) != 1:
                    gap = "environment-reference-has-repeated-" + repeated_name + "-entries"
                elif any(rows.get(environment) for other, rows in initializers.items() if other != hook):
                    gap = "environment-reference-has-conflicting-initializer-types"
                elif len(threads[environment]) != 1:
                    gap = "skill-environment-reference-observed-on-multiple-threads"
                elif environment in buff_references:
                    gap = "environment-reference-also-has-Buff-reset-evidence"
                elif not isinstance(owner, int) or owner <= 0 or not isinstance(name, str) or not name or name != identity[1]:
                    gap = "supplied-skill-reference-or-stored-identifiers-unconfirmed"
                elif any((item["fields"]["entrySkillStoredId"], item["fields"]["entrySkillDataId"],
                          item["fields"]["entrySkillInstId"]) != identity
                         for item in skill_entries.get(owner, [])):
                    gap = "supplied-skill-reference-has-conflicting-observed-identities"
                else:
                    gap = None
            consumer[association_key] = gap is None
            consumer[entry_key] = entry
            consumer[gap_key] = gap
            # Matching entry arguments prove neither initializer completion,
            # object lifetime, skill ownership nor a serialized action node.


def associate_new_actions(consumers: list[dict[str, Any]], entries: list[dict[str, Any]], *,
                          action_resets: dict[int, list[int]], action_threads: dict[int, set[int]],
                          environment_threads: dict[int, set[int]]) -> None:
    """Match observed references; a factory return and assignment are unobserved.

    Inspect the entire recording for conflicting evidence, including entries
    later than the consumer. Sharing immutable data across environments is
    allowed; repeating the same data/environment factory entry is ambiguous.
    """
    factories: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    threads: dict[int, set[int]] = defaultdict(set)
    for environment, observed in environment_threads.items():
        threads[environment].update(observed)
    for entry in entries:
        environment = entry["fields"].get("suppliedEnvironmentIdentity")
        if entry["hook"] in {"buff.SkillHighlightEnvironment.Constructor", "buff.Ability.Init"}:
            threads[entry["receiver"]].add(entry["threadId"])
        if isinstance(environment, int) and not isinstance(environment, bool) and environment > 0:
            threads[environment].add(entry["threadId"])
        if entry["hook"] == "buff.AbilityActionData.NewAction":
            factories[(entry["receiver"], environment)].append(entry)
    observations: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for consumer in consumers:
        resets = action_resets.get(consumer["receiver"], [])
        prior_resets = [sequence for sequence in resets if sequence < consumer["sequence"]]
        reset_sequence = prior_resets[-1] if prior_resets else 0
        consumer["actionResetSequence"] = reset_sequence or None
        observations[(consumer["receiver"], reset_sequence)].append(consumer)
    for consumer in consumers:
        values = consumer["entryFields"]
        data = values.get("entryStoredDataIdentity")
        environment = values["entryEnvironment"]
        observed = factories.get((data, environment), [])
        prior = [entry for entry in observed if entry["sequence"] < consumer["sequence"]]
        entry = prior[-1] if prior else None
        reset_sequence = consumer["actionResetSequence"] or 0
        window = observations[(consumer["receiver"], reset_sequence)]
        if "entryStoredDataIdentity" not in values:
            gap = "consumer-stored-data-reference-not-recorded"
        elif not isinstance(data, int) or isinstance(data, bool) or data <= 0:
            gap = "consumer-stored-data-reference-is-null-or-invalid"
        elif not isinstance(environment, int) or isinstance(environment, bool) or environment <= 0:
            gap = "consumer-environment-reference-is-null-or-invalid"
        elif entry is None:
            gap = "no-prior-NewAction-with-matching-data-and-environment"
        elif len(observed) != 1:
            gap = "data-environment-reference-has-repeated-NewAction-entries"
        elif entry["fields"].get("entryDataIdentity") != entry["receiver"]:
            gap = "NewAction-data-reference-differs-from-receiver"
        elif len(action_threads[consumer["receiver"]]) != 1:
            gap = "action-reference-observed-on-multiple-threads"
        elif len(threads[environment]) != 1 or entry["threadId"] != consumer["threadId"]:
            gap = "NewAction-environment-observed-on-multiple-threads"
        elif entry["sequence"] <= reset_sequence:
            gap = "NewAction-precedes-latest-action-reset"
        elif consumer["buffResetSequence"] and entry["sequence"] <= consumer["buffResetSequence"]:
            gap = "NewAction-precedes-latest-Buff-reset"
        elif any(item["entryFields"].get("entryStoredDataIdentity") != data or
                 item["entryFields"]["entryEnvironment"] != environment for item in window):
            gap = "action-stored-data-or-environment-changed-within-reset-window"
        else:
            gap = None
        consumer.update(newActionAssociation=gap is None, newActionEntry=entry, newActionGap=gap)


def analyze_events(events: Iterable[dict[str, Any]], *, enums: dict[str, Any] | None = None,
                   max_rows: int = 1_000_000) -> dict[str, Any]:
    """Keep reference, reset-window and explicit assignment evidence in separate columns."""
    epochs: list[dict[str, Any]] = []
    latest: dict[int, dict[str, Any]] = {}
    prior_buff: dict[int, dict[str, Any]] = {}
    assignments: dict[int, dict[str, Any]] = {}
    dispatches: dict[int, dict[str, Any]] = {}
    dispatch_entries: list[dict[str, Any]] = []
    buff_threads: dict[int, set[int]] = defaultdict(set)
    action_threads: dict[int, set[int]] = defaultdict(set)
    action_resets: dict[int, list[int]] = defaultdict(list)
    consumers: list[dict[str, Any]] = []
    initialization_entries: list[dict[str, Any]] = []
    calls: Counter[str] = Counter()
    definitions: Counter[str] = Counter()
    previous_sequence, previous_qpc, rows = 0, -1, 0
    enum_members = {item["value"]: item["name"] for item in
                    (enums or {}).get("Beyond.Gameplay.Core.Buff+Event", {}).get("members", [])}
    for row in events:
        rows += 1
        trace.require(rows <= max_rows, "Buff join: row budget exceeded")
        sequence, qpc, thread = row["sequence"], row["qpc"], row["threadId"]
        trace.require(sequence == previous_sequence + 1 and qpc >= previous_qpc,
                      f"Buff join: sequence/clock ordering at {sequence}")
        previous_sequence, previous_qpc = sequence, qpc
        hook, pointer = row["hook"], row["rawArgs"][0]
        if hook == DISPATCH_HOOK:
            # RCX is opaque helper context, not an instance receiver.
            pointer = row["rawArgs"][1]
        trace.require(isinstance(pointer, int) and pointer > 0, f"Buff join: null receiver at {sequence}")
        value = fields(row)
        calls[hook] += 1
        if hook == DISPATCH_HOOK:
            trace.require([value.get(label) for label in ("suppliedActionIdentity", "suppliedDataIdentity", "suppliedEnvironmentIdentity")]
                          == row["rawArgs"][1:4], f"Buff dispatch: field/register identity differs at {sequence}")
            entry = {"sequence": sequence, "qpc": qpc, "threadId": thread, "hook": hook,
                     "receiver": pointer, "suppliedDataReference": value["suppliedDataIdentity"],
                     "suppliedEnvironmentReference": value["suppliedEnvironmentIdentity"]}
            dispatch_entries.append(entry)
            dispatches[pointer] = entry
            action_threads[pointer].add(thread)
            buff_threads[entry["suppliedEnvironmentReference"]].add(thread)
        if hook in INITIALIZERS:
            initialization_entries.append({"sequence": sequence, "qpc": qpc, "threadId": thread,
                                           "hook": hook, "receiver": pointer, "fields": value})
        if hook.startswith("buff.Buff."):
            buff_threads[pointer].add(thread)
            if hook == "buff.Buff.Reset":
                supplied = value["suppliedBuffId"]
                trace.require(isinstance(supplied, str) and 0 < len(supplied) <= 160,
                              f"Buff join: missing supplied definition at {sequence}")
                definitions[supplied] += 1
                prior = prior_buff.get(pointer)
                changed = ({key: {"before": prior["fields"][key], "resetEntry": value[key]}
                            for key in IDENTITIES if prior["fields"][key] != value[key]} if prior else {})
                epoch = {"resetSequence": sequence, "receiver": pointer, "threadId": thread,
                         "suppliedBuffId": supplied,
                         "suppliedOwnerReference": value["suppliedBuffOwnerIdentity"],
                         "suppliedSourceReference": value["suppliedBuffSourceIdentity"],
                         "resetEntryIdentities": {key: value[key] for key in IDENTITIES},
                         "previousResetSequence": latest.get(pointer, {}).get("resetSequence"),
                         "previousObservationSequence": prior["sequence"] if prior else None,
                         "identityFieldsChangedBeforeResetEntry": changed,
                         "confirmedIdentity": None, "identityConflictSequences": [],
                         "hooks": {}, "eventArguments": {}}
                epochs.append(epoch)
                latest[pointer] = epoch
            else:
                epoch = latest.get(pointer)
                if epoch and epoch["threadId"] == thread:
                    epoch["hooks"][hook] = epoch["hooks"].get(hook, 0) + 1
                    identity = {key: value[key] for key in IDENTITIES}
                    prior_identity = epoch["confirmedIdentity"]
                    if prior_identity is not None and prior_identity["fields"] != identity:
                        epoch["identityConflictSequences"].append(sequence)
                    elif value["entryStoredBuffId"] == value["entryDataId"] == epoch["suppliedBuffId"]:
                        if prior_identity is None:
                            epoch["confirmedIdentity"] = {"sequence": sequence, "fields": identity}
                    if "suppliedBuffEvent" in value:
                        event = value["suppliedBuffEvent"]
                        label = str(event)
                        entry = epoch["eventArguments"].setdefault(label, {
                            "rawValue": event, "retainedName": enum_members.get(event), "rows": 0})
                        entry["rows"] += 1
            prior_buff[pointer] = {"sequence": sequence, "fields": {key: value[key] for key in IDENTITIES}}
        elif hook.startswith("buff.AbilityAction."):
            action_threads[pointer].add(thread)
            if hook == "buff.AbilityAction.Reset":
                action_resets[pointer].append(sequence)
                assignments.pop(pointer, None)
                dispatches.pop(pointer, None)
            elif hook in ("buff.AbilityAction.AssignData", "buff.AbilityAction.GenericAssignData", "buff.AbilityAction.ReAssign"):
                assignments[pointer] = {"sequence": sequence, "hook": hook, "threadId": thread,
                                        "suppliedEnvironmentReference": value["suppliedEnvironmentIdentity"],
                                        "entryEnvironmentReference": value["entryEnvironment"],
                                        "suppliedServerActionIndex": value.get("suppliedServerActionIndex"),
                                        "suppliedDataReference": value.get("suppliedDataIdentity")}
        elif hook in CONSUMERS:
            action_threads[pointer].add(thread)
            environment = value["entryEnvironment"]
            buff_threads[environment].add(thread)
            epoch = latest.get(environment)
            identity = epoch["confirmedIdentity"] if epoch else None
            assignment = assignments.get(pointer)
            association = bool(epoch and identity and epoch["threadId"] == thread)
            gap = ("no-observed-Buff-reset-for-environment-reference" if not epoch else
                   "no-prior-matching-stored-Buff-identity" if not identity else
                   "Buff-reset-thread-differs-from-consumer-thread" if epoch["threadId"] != thread else None)
            explicit = bool(association and assignment and assignment["threadId"] == thread and
                            assignment["suppliedEnvironmentReference"] == environment and
                            assignment["sequence"] > epoch["resetSequence"])
            dispatch = dispatches.get(pointer)
            dispatch_gap = ("no-dispatch-after-latest-action-reset" if not dispatch else
                            "dispatch-thread-differs-from-consumer" if dispatch["threadId"] != thread else
                            "dispatch-environment-differs-from-consumer" if dispatch["suppliedEnvironmentReference"] != environment else
                            "dispatch-data-reference-is-null" if not dispatch["suppliedDataReference"] else
                            "dispatch-precedes-latest-Buff-reset" if epoch and dispatch["sequence"] <= epoch["resetSequence"] else None)
            consumers.append({"sequence": sequence, "qpc": qpc, "threadId": thread, "hook": hook,
                              "receiver": pointer, "entryFields": value,
                              "buffResetSequence": epoch["resetSequence"] if epoch else None,
                              "buffId": epoch["suppliedBuffId"] if association else None,
                              "identityConfirmation": identity if association else None,
                              "environmentAssociation": association,
                              "explicitAssignmentAssociation": explicit,
                              "assignmentEntry": assignment,
                              "dispatchEntry": dispatch, "dispatchAssociation": dispatch_gap is None,
                              "dispatchGap": dispatch_gap,
                              "gap": gap})
    by_reset = {epoch["resetSequence"]: epoch for epoch in epochs}
    for consumer in consumers:
        epoch = by_reset.get(consumer["buffResetSequence"])
        if len(buff_threads[consumer["entryFields"]["entryEnvironment"]]) > 1:
            consumer.update(environmentAssociation=False, explicitAssignmentAssociation=False,
                            gap="Buff-reference-observed-on-multiple-threads")
        elif epoch and epoch["identityConflictSequences"]:
            consumer.update(environmentAssociation=False, explicitAssignmentAssociation=False,
                            gap="stored-instance-identity-changed-within-reset-window")
        if len(action_threads[consumer["receiver"]]) > 1:
            consumer["explicitAssignmentAssociation"] = False
            consumer["assignmentGap"] = "action-reference-observed-on-multiple-threads"
            consumer.update(dispatchAssociation=False, dispatchGap="action-reference-observed-on-multiple-threads")
        if len(action_threads[consumer["receiver"]]) <= 1 and len(buff_threads[consumer["entryFields"]["entryEnvironment"]]) > 1:
            consumer.update(dispatchAssociation=False, dispatchGap="dispatch-environment-observed-on-multiple-threads")
        if epoch and epoch["identityConflictSequences"]:
            consumer.update(dispatchAssociation=False, dispatchGap="stored-instance-identity-changed-within-reset-window")
        if not consumer["environmentAssociation"]:
            # A later conflicting observation revokes the window as a whole.
            # Keep the reset/entry evidence, but publish no surviving ID claim.
            consumer.update(buffId=None, identityConfirmation=None)
        if consumer["environmentAssociation"] and not consumer["explicitAssignmentAssociation"]:
            consumer.setdefault("assignmentGap", "no-matching-assignment-after-latest-Buff-reset-and-action-reset")
    associate_skill_initializers(consumers, initialization_entries, buff_references=set(latest))
    associate_new_actions(consumers, initialization_entries, action_resets=action_resets,
                          action_threads=action_threads, environment_threads=buff_threads)
    counts = {hook: {"entries": 0, "environmentAssociations": 0, "explicitAssignmentAssociations": 0,
                     "skillEnvironmentConstructorAssociations": 0, "abilityInitializationAssociations": 0,
                     "dispatchAssociations": 0, "newActionAssociations": 0}
              for hook in sorted(CONSUMERS)}
    for consumer in consumers:
        item = counts[consumer["hook"]]
        item["entries"] += 1
        item["environmentAssociations"] += int(consumer["environmentAssociation"])
        item["explicitAssignmentAssociations"] += int(consumer["explicitAssignmentAssociation"])
        item["skillEnvironmentConstructorAssociations"] += int(consumer["skillEnvironmentConstructorAssociation"])
        item["abilityInitializationAssociations"] += int(consumer["abilityInitializationAssociation"])
        item["dispatchAssociations"] += int(consumer["dispatchAssociation"])
        item["newActionAssociations"] += int(consumer["newActionAssociation"])
    assignment_methods = Counter(consumer["assignmentEntry"]["hook"] for consumer in consumers
                                 if consumer["explicitAssignmentAssociation"])
    return {"boundary": BOUNDARY, "rows": rows, "hookCalls": dict(sorted(calls.items())),
            "definitionCounts": dict(sorted(definitions.items())), "epochs": epochs, "consumers": consumers,
            "initializationEntries": initialization_entries,
            "dispatchEntries": dispatch_entries,
            "dispatchBoundary": "Simultaneous helper-entry action/data/environment references with later same-action/environment consumer entry. No invocation nesting, branch, return, cast, generic field assignment, lifetime, ownership or serialized-node selection is proved.",
            "initializationBoundary": "NewAction entry retains data and environment arguments, not the returned action. Constructor and Ability.Init reference associations separately retain earlier supplied skill evidence only; no environment downcast, completion, lifetime, action-node selection or skill ownership is established.",
            "newActionBoundary": "Earlier unique NewAction data/environment entry and later consumer stored data/environment references agree within an observed action reset window. This does not identify NewAction's returned action, prove assignment completion or object lifetime, or select a serialized node or file.",
            "summary": {"rows": rows, "resetWindows": len(epochs), "uniqueBuffDefinitions": len(definitions),
                        "uniqueBuffReceivers": len(latest),
                        "reusedReceiverResets": sum(item["previousResetSequence"] is not None for item in epochs),
                        "resetEntriesWithPreEntryIdentityChanges": sum(bool(item["identityFieldsChangedBeforeResetEntry"]) for item in epochs),
                        "consumers": counts,
                        "initializationCalls": {name: calls[name] for name in sorted(INITIALIZERS)},
                        "explicitAssignmentsByHook": dict(sorted(assignment_methods.items())),
                        "explicitAssignmentsWithSuppliedData": sum(
                            consumer["explicitAssignmentAssociation"] and
                            consumer["assignmentEntry"].get("suppliedDataReference") is not None
                            for consumer in consumers)},
            "runtimeOwnershipExact": False, "runtimeMeaningExact": False}


def bound_events(inspection_dir: Path, report: dict[str, Any], artifacts: dict[str, Any],
                 profile: dict[str, Any], hooks: list[dict[str, Any]], *, limits: trace.Limits) -> Iterator[dict[str, Any]]:
    """Re-use the passing inspection; bind its interpreted values to every retained row."""
    decoded_path = trace.safe_path(inspection_dir, report["decodedOutput"])
    journal = artifacts["mission-trace/events.jsonl"]
    digest = hashlib.sha256()
    decoded_bytes, rows = 0, 0
    with decoded_path.open("rb") as decoded, journal["path"].open("rb") as raw:
        while line := raw.readline(limits.input_line_bytes + 1):
            trace.require(len(line) <= limits.input_line_bytes and line.endswith(b"\n"), "Buff join: raw line budget")
            interpreted = decoded.readline(limits.output_line_bytes + 1)
            trace.require(interpreted and len(interpreted) <= limits.output_line_bytes and interpreted.endswith(b"\n"),
                          "Buff join: decoded row missing/oversized")
            digest.update(line)
            decoded_bytes += len(interpreted)
            trace.require(decoded_bytes <= limits.output_bytes, "Buff join: decoded byte budget")
            source, value = trace.parse_json(line, "retained row"), trace.parse_json(interpreted, "decoded row")
            index = trace.integer(source["hookIndex"], "hook index", len(hooks) - 1)
            hook = hooks[index]
            expected = [trace.decode_field(spec, observed, profile.get("enumDefinitions", {}))
                        for spec, observed in zip(hook["fields"], source["fields"])]
            trace.require(len(source["fields"]) == len(hook["fields"]) and value["fields"] == expected,
                          f"Buff join: decoded field/raw binding at sequence {source['sequence']}")
            for key in ("sequence", "qpc", "tickNs", "threadId", "hookIndex", "hook", "returnAddress", "argsReadMask", "callerGameAssemblyRva"):
                trace.require(value[key] == source[key], f"Buff join: decoded {key}/raw binding at {source['sequence']}")
            trace.require(value["hook"] == hook["name"] and value["rawArgs"] == source["args"], "Buff join: hook/argument binding")
            rows += 1
            trace.require(rows <= limits.rows, "Buff join: row budget exceeded")
            yield value
        trace.require(not decoded.read(1), "Buff join: extra decoded row")
    trace.require(digest.hexdigest().lower() == journal["sha256"].lower(), "Buff join: raw journal changed")
    trace.require(rows == report["decodedRows"] and decoded_bytes == report["decodedBytes"], "Buff join: inspection output count mismatch")


def inspect_runtime(inspection_dir: Path, output_dir: Path, *, limits: trace.Limits = trace.Limits(),
                    corpus_summary: Path | None = None, corpus_ledger: Path | None = None) -> dict[str, Any]:
    inspection_dir, output_dir = inspection_dir.resolve(), output_dir.resolve()
    inspection_path = inspection_dir / "inspection.json"
    report = trace.read_object(inspection_path, limits.json_bytes)
    session = Path(report["session"]).resolve()
    trace.require(any(output_dir.is_relative_to((trace.REPO_ROOT / folder).resolve()) for folder in ("reports", "scratch", "tmp")),
                  "Buff join: output must be under ignored reports/, scratch/, or tmp/")
    trace.require(not output_dir.is_relative_to(session) and not session.is_relative_to(output_dir) and
                  not output_dir.is_relative_to(inspection_dir) and not inspection_dir.is_relative_to(output_dir),
                  "Buff join: output must be outside original session and passing inspection")
    trace.require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())),
                  "Buff join: output directory must be new/empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {"schema": "endfield.buff-runtime-inspection.v5", "status": "failed",
                              "boundary": BOUNDARY, "session": str(session), "captureAdmitted": False,
                              "externalOriginAuthenticated": False, "nativeValidationReproved": False}
    try:
        facts = report["receiptFacts"]
        trace.require(report["status"] == "inspected" and all(facts.get(key) is True for key in
                      ("captureCompleteClaim", "healthyClaim", "allJournalRowsAccounted", "strictTransitionReceiptsConsistent")),
                      "Buff join: requires complete healthy lossless consistent capture")
        artifacts, inventory = trace.verify_inventory(session, limits)
        trace.require(inventory["inventorySha256"] == report["inventory"]["inventorySha256"], "Buff join: retained inventory changed")
        profile, _, hooks = trace.bindings(artifacts, limits)
        trace.require(any(hook["name"] == "buff.Buff.Reset" for hook in hooks), "Buff join: not a Buff lifecycle profile")
        trace.require(artifacts["private/mission-trace-build-manifest.json"]["sha256"] == report["profileSha256"] and
                      artifacts["mission-trace/summary.json"]["sha256"] == report["providerSummarySha256"],
                      "Buff join: inspection/profile/summary binding changed")
        pins = [fingerprint(inspection_path), fingerprint(inspection_dir / report["decodedOutput"]), fingerprint(Path(__file__))]
        result.update(analyze_events(bound_events(inspection_dir, report, artifacts, profile, hooks, limits=limits),
                                     enums=profile.get("enumDefinitions"), max_rows=limits.rows))
        names = sorted(hook["name"] for hook in hooks)
        result["hookCoverage"] = {"selected": len(names), "observed": len(result["hookCalls"]),
                                  "unobserved": [name for name in names if not result["hookCalls"].get(name)],
                                  "boundary": "Zero retained entries do not prove absence of behavior or alternate routes."}
        source_inventory = trace.bound_object(artifacts, "static-sources/inventory.json", limits)
        source_candidates: dict[str, dict[str, Any]] = {"buffData": {}, "skillData": {}}
        for row in source_inventory["files"]:
            if row.get("role") in source_candidates and row.get("copied") is True:
                candidates = source_candidates[row["role"]]
                name = row["sourceRelativePath"]
                family = "BuffData" if row["role"] == "buffData" else "SkillData"
                trace.require(name.startswith("game/Json/" + family + "/"), "Buff join: source role/path differs")
                artifact_name = "static-sources/" + row["archivedRelativePath"]
                bound = artifacts.get(artifact_name)
                trace.require(bound is not None and row["sha256"].lower() == bound["sha256"].lower() and row["bytes"] == bound["bytes"],
                              f"Buff join: source artifact binding {name}")
                stem = Path(name).stem
                trace.require(stem not in candidates, f"Buff join: duplicate source stem {stem}")
                candidates[stem] = {"path": name, "bytes": row["bytes"], "sha256": row["sha256"],
                                    "boundary": "ID-to-filename byte candidate; no runtime file loading or schema admission."}
        result["sourceCandidates"] = {name: source_candidates["buffData"].get(name) for name in result["definitionCounts"]}
        skill_names = {value for entry in result["initializationEntries"]
                       for key, value in entry["fields"].items()
                       if key in {"entrySkillStoredId", "entrySkillDataId", "suppliedSkillStoredId", "suppliedSkillDataId"}
                       and isinstance(value, str) and value}
        result["skillSourceCandidates"] = {name: source_candidates["skillData"].get(name) for name in sorted(skill_names)}
        trace.require((corpus_summary is None) == (corpus_ledger is None), "Buff schema join: supply both summary and ledger")
        if corpus_summary is not None and corpus_ledger is not None:
            try:
                result["storedSchema"] = join_canonical_sources(result, profile, corpus_summary, corpus_ledger)
            except (trace.InspectionError, OSError, KeyError, TypeError, ValueError) as exc:
                result["storedSchema"] = {"status": "unavailable", "failure": str(exc)[:2048], "definitions": {}}
        trace.require(pins == [fingerprint(Path(item["path"])) for item in pins], "Buff join: inspection/reader inputs changed")
        result.update(status="inspected", captureAdmitted=True, inputs=pins,
                      inventory=inventory, sourceArchiveNativeValidated=source_inventory.get("nativeValidated") is True)
    except (trace.InspectionError, OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        result.update(status="failed", captureAdmitted=False, failure=str(exc)[:2048])
        for key in ("epochs", "consumers", "sourceCandidates", "skillSourceCandidates", "initializationEntries",
                    "initializationBoundary", "newActionBoundary", "dispatchEntries", "dispatchBoundary", "summary", "definitionCounts", "hookCalls", "hookCoverage"):
            result.pop(key, None)
        (output_dir / "buff-runtime.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
        raise trace.InspectionError(result["failure"]) from exc
    (output_dir / "buff-runtime.json").write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspection-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--corpus-summary", type=Path)
    parser.add_argument("--corpus-ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect_runtime(args.inspection_dir, args.output_dir,
                                 corpus_summary=args.corpus_summary, corpus_ledger=args.corpus_ledger)
    except trace.InspectionError as exc:
        print(f"[buff_runtime_trace_inspect] failed: {exc}")
        return 2
    print("[buff_runtime_trace_inspect] " + json.dumps(result["summary"], ensure_ascii=True))
    if "storedSchema" in result:
        print("[buff_runtime_trace_inspect] stored schema: " + json.dumps(
            {key: result["storedSchema"][key] for key in ("status", "summary", "failure") if key in result["storedSchema"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
