"""Audit EndfieldCapture entry-only source/owner evidence against selected inputs.

No native result or cross-call ownership is reconstructed. Only the reviewed
carrier entry may admit a local decoder/owner snapshot after caller and address
point checks. Missing files, counts or gates withhold every claim.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from scripts.game_data.wwise_source_native import load_validated_source_contract
from scripts.game_data.il2cpp.native_image import pe_mapped_image_size
from scripts.game_data import wwise_source_queue_native as queue_native
from scripts.game_data import wwise_owner_carrier_native as carrier_native
from scripts.game_data import wwise_decoder_provider_native as provider_native
from scripts.common import sha256_file
from scripts.repo_paths import REPO_ROOT
from scripts.webui.audio.semantics import source_observer_profile as profiles
from scripts.webui.audio.semantics import source_io_observations
from scripts.webui.audio.semantics import managed_post_observations
from scripts.webui.audio.semantics.context_utils import json_dump
from scripts.webui.audio.semantics import runtime_capture_import as legacy

SCHEMA = "endfield.audio-source-owner-entry-audit.v4"
ENTRY_SCHEMA = "endfieldCapture.audioSourceOwnerEntry.v1"
BOUNDARY = "Entry-only non-atomic snapshots. No return, synchronous nesting, earlier-source continuity, generation/lifetime, managed ownership, provider/file identity, decode success or audibility is established."


def _json(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _integer(value, maximum=2**64-1) -> bool:
    return type(value) is int and 0 <= value <= maximum


def validate_manifest_declarations(recorded: dict, expected: dict) -> dict:
    """Keep operational recipes exact while retaining historical proof prose.

    Native gates re-prove selected binaries now. The recorded explanation of
    their exact tier can predate stronger offline checks; it is not an ABI or
    read-program declaration. Only this one bounded text value may differ.
    Its boundary keys and every other declaration must still match exactly.
    """
    previous = recorded.get('evidenceBoundary', {})
    current = expected.get('evidenceBoundary', {})
    old_text = previous.get('exact') if isinstance(previous, dict) else None
    new_text = current.get('exact') if isinstance(current, dict) else None
    changed = old_text != new_text
    comparable = expected
    if changed:
        if (not isinstance(previous, dict) or not isinstance(current, dict)
                or set(previous) != set(current)
                or not isinstance(old_text, str) or not isinstance(new_text, str)
                or not 0 < len(old_text) <= 4096 or not 0 < len(new_text) <= 4096):
            raise ValueError('staged source-owner exact-evidence provenance has different keys or invalid text')
        comparable = copy.deepcopy(expected)
        comparable['evidenceBoundary']['exact'] = old_text
    if json.dumps(recorded, sort_keys=True) != json.dumps(comparable, sort_keys=True):
        raise ValueError('staged source-owner declarations differ from current authenticated recipe')
    return {'exactBoundaryTextChanged': changed,
            'recordedExactEvidence': old_text, 'currentExactEvidence': new_text,
            'evidenceBoundary': 'Capture-time documentation is retained separately from current selected-native proof. Every ABI, read program, file identity and other manifest declaration remains exact.'}


def audit_entries(rows: list[dict], hooks: list[dict], spans: dict[int, tuple[int, int]], spec: dict,
                  mapped_image_bytes: int | None = None, *, provider_spec: dict | None = None) -> dict:
    by_name = {hook["name"]: hook for hook in hooks}
    counts, states, candidates = Counter(), Counter(), Counter()
    texts, storage = {}, {}
    samples, ids, sequences, extents = [], set(), set(), set()
    provider_entries = {}
    role = spec["roles"]["carrierCommand4"]
    carrier_name = "AkSoundEngine." + role["sourceKind"]
    allowed_callers = {int(rva, 16) for rva in spec["callers"]["carrierCommand4"]}
    for number, row in enumerate(rows, 1):
        hook = by_name.get(row.get("hook"))
        if row.get("schema") != ENTRY_SCHEMA or hook is None:
            raise ValueError(f"source_owner.jsonl:{number}: unknown schema/hook")
        for key in ("sequence", "captureId", "timestampNs", "threadId", "windowId", "returnAddress", "moduleBase", "moduleBytes", "hookIndex"):
            if not _integer(row.get(key)):
                raise ValueError(f"source_owner.jsonl:{number}: invalid {key}")
        if row["captureId"] in ids or row["sequence"] in sequences or not row["captureId"] or not row["sequence"]:
            raise ValueError(f"source_owner.jsonl:{number}: duplicate/zero identity")
        ids.add(row["captureId"]); sequences.add(row["sequence"])
        span = spans.get(row["windowId"])
        if span is None or not span[0] <= row["timestampNs"] <= span[1]:
            raise ValueError(f"source_owner.jsonl:{number}: entry outside its closed window")
        if row["hookIndex"] != hooks.index(hook) + 2:
            raise ValueError(f"source_owner.jsonl:{number}: hook index differs from activation")
        args, values, status, text = (row.get(key) for key in ("args", "values", "states", "textUnits"))
        if (not isinstance(args, list) or len(args) != 4 or any(not _integer(v) for v in args)
                or not isinstance(values, list) or len(values) != len(hook["memory"])
                or any(not _integer(v) for v in values)
                or not isinstance(status, list) or len(status) != len(values)
                or any(not _integer(v, 2) for v in status)
                or not isinstance(text, list) or len(text) > 160 or any(not _integer(v, 65535) or v == 0 for v in text)):
            raise ValueError(f"source_owner.jsonl:{number}: snapshot field shape differs from declaration")
        facts = {}
        text_fields = 0
        for index, field in enumerate(hook["memory"]):
            value, state = values[index], status[index]
            if state == 0 and value != 0:
                raise ValueError(f"source_owner.jsonl:{number}: guarded-out field carries a value")
            states[{0: "guardedOut", 1: "read", 2: "inaccessibleOrUnterminated"}[state]] += 1
            if field["kind"] == "u32" and value > 0xffffffff:
                raise ValueError(f"source_owner.jsonl:{number}: u32 field exceeds its width")
            if field["kind"] == "utf16Direct":
                text_fields += 1
                if (state and value != len(text)) or (state == 1 and len(text) == 160) or (state == 0 and text):
                    raise ValueError(f"source_owner.jsonl:{number}: invalid terminated text receipt")
            facts[field["name"]] = value if state == 1 else None
            # Recheck every dependent guard instead of trusting a captured state.
            gate = field.get("requireMemory")
            allowed = True
            if gate:
                guard = facts.get(gate["name"])
                allowed = guard is not None and (guard != 0 if gate.get("nonzero") else guard == gate["equals"])
            gate = field.get("requireArgument")
            if gate:
                allowed = allowed and args[hook["args"][gate["name"]]["index"]] != 0
            if (not allowed and state != 0) or (allowed and state == 0):
                raise ValueError(f"source_owner.jsonl:{number}: field guard disagrees with receipt")
        if not text_fields and text:
            raise ValueError(f"source_owner.jsonl:{number}: undeclared text")
        for index, field in enumerate(hook["memory"]):
            if field["kind"] == "utf16Direct" and status[index] == 1:
                decoded = b"".join(unit.to_bytes(2, "little") for unit in text).decode("utf-16-le")
                texts.setdefault(hook["sourceKind"], Counter())[decoded] += 1
        flags = next((facts[field["name"]] for field in hook["memory"]
                      if field["name"].endswith("SourceFlagsWord") or field["name"] == "sourceFlagsWord"), None)
        if flags is not None:
            summary = storage.setdefault(hook["sourceKind"], Counter())
            summary["bit8Set" if flags & 256 else "bit8Clear"] += 1
            if flags & 256:
                data = next((facts[field["name"]] for field in hook["memory"]
                             if field["name"].endswith("SourceDataPointer") or field["name"] == "sourceDataPointer"), None)
                word8 = next((facts[field["name"]] for field in hook["memory"]
                              if field["name"].endswith("SourceStoredWord8") or field["name"] == "sourceStoredWord8"), None)
                if data is not None: summary["bit8SetNonzeroDataPointer" if data else "bit8SetZeroDataPointer"] += 1
                if word8 is not None: summary["bit8SetZeroWord8" if word8 == 0 else "bit8SetNonzeroWord8"] += 1
        counts[hook["sourceKind"]] += 1
        base, size = row["moduleBase"], row["moduleBytes"]
        if (not base or base % 4096 or not 0 < size < 2**32 or base + size >= 0x800000000000
                or mapped_image_bytes is not None and size != mapped_image_bytes):
            raise ValueError(f"source_owner.jsonl:{number}: invalid mapped module extent")
        extents.add((base, size))
        if len(extents) > 1:
            raise ValueError(f"source_owner.jsonl:{number}: mapped module extent changed inside session")
        if provider_spec and hook["sourceKind"] in provider_spec["callers"]:
            kind = hook["sourceKind"]
            entry = provider_entries.setdefault(kind, {"entryCount": 0, "callerRoles": Counter()})
            entry["entryCount"] += 1
            entry["callerRoles"][provider_spec["callers"][kind].get(row["returnAddress"] - base, "unreviewedCaller")] += 1
            if "inputTextPointer" in facts:
                pointer = facts["inputTextPointer"]
                text_state = "unreadablePointer" if pointer is None else "nullPointer" if pointer == 0 else "nonzeroPointer"
                entry.setdefault("inputText", Counter())[text_state] += 1
                if pointer:
                    entry["inputText"]["terminatedText" if facts.get("inputWideText") is not None else "unreadableOrUnterminatedText"] += 1
            for field, point in (("providerAddressPointPointer", "providerAddressPointRva"),
                                 ("factoryAddressPointPointer", "factoryAddressPointRva")):
                if field in facts:
                    value = facts[field]
                    state = "unreadable" if value is None else "matched" if value == base + int(provider_spec[point], 16) else "different"
                    entry.setdefault("addressPoint", Counter())[state] += 1
            if "providerStoredDescriptorPointer" in facts:
                value = facts["providerStoredDescriptorPointer"]
                entry.setdefault("storedDescriptorPointer", Counter())["unreadable" if value is None else "nonzero" if value else "zero"] += 1
            if kind == "anonymousAlternateProviderFactory":
                entry.setdefault("inputData", Counter())["nonzeroPointer" if args[hook["args"]["inputDataPointer"]["index"]] else "zeroPointer"] += 1
                entry["inputData"]["nonzeroWord" if args[hook["args"]["inputDataWord"]["index"]] else "zeroWord"] += 1
        if row["hook"] == carrier_name:
            candidates["entries"] += 1
            owner = args[role["args"]["primaryOwnerPointer"]["index"]]
            if row["returnAddress"] - base not in allowed_callers:
                candidates["unreviewedCaller"] += 1; continue
            if facts.get("primaryOwnerAddressPointPointer") != base + int(spec["primaryAddressPointRva"], 16):
                candidates["unvalidatedAddressPoint"] += 1; continue
            matches = [kind for kind in ("currentDecoder", "pendingDecoder")
                       if owner and facts.get(kind + "Pointer") and facts.get(kind + "PrimaryOwnerPointer") == owner]
            if matches:
                candidates["matchingOwnerEntries"] += 1
                if len(samples) < 12:
                    samples.append({"captureId": row["captureId"], "matchingDecoderRoles": matches,
                                    "storedSourcePointer": hex(facts["primaryStoredSourcePointer"]) if facts.get("primaryStoredSourcePointer") is not None else None})
            else:
                candidates["noReadableMatchingOwner"] += 1
    result = {"entryCount": len(rows), "hookCounts": {hook["sourceKind"]: counts[hook["sourceKind"]] for hook in hooks}, "fieldReadStates": dict(states),
            "sourceStorageByHook": {kind: dict(value) for kind, value in storage.items()},
            "nativeTextsByHook": [{"sourceKind": kind, "distinctTextCount": len(value),
                                   "observationCount": sum(value.values()), "textsTruncated": len(value) > 32,
                                   "texts": [{"text": path, "entryCount": count} for path, count in sorted(value.items())[:32]]}
                                  for kind, value in sorted(texts.items())],
            "ownerCarrierSnapshots": dict(candidates), "ownerCarrierSamples": samples, "evidenceBoundary": BOUNDARY}
    if provider_spec:
        result["providerEntryObservations"] = {
            "schema": "endfield.audio-provider-entry-observations.v1", "status": "validated",
            "hooks": {kind: {key: dict(value) if isinstance(value, Counter) else value for key, value in entry.items()}
                      for kind, entry in provider_entries.items()},
            "evidenceBoundary": "Caller roles use authenticated instruction return sites. Address points and descriptors are local entry reads. No entry-to-entry chain, provider result, stored-copy completion, operating-system file open, lifetime or audibility is established."}
    return result


def audit_session(session: Path, expected: dict, spec: dict, mapped_image_bytes: int | None = None, *, provider_gate: dict | None = None, io_gates: dict | None = None) -> dict:
    for relative in ("events.jsonl", "audio/source_owner.jsonl"):
        if (session / relative).stat().st_size > 128 * 1024 * 1024:
            raise ValueError(f"{relative}: audit input exceeds 128 MiB budget")
    if (session / "runtime.error").exists() or (session / ".initializing").exists():
        raise ValueError("runtime.error or unfinished session initialization")
    descriptor = _json(session / "session.json")
    if descriptor.get("schema") != "endfieldCapture.session.v1" or descriptor.get("providers") != 2:
        raise ValueError("expected an Audio-only native session")
    writer = _json(session / "collected/summary.json")
    if (writer.get("schema") != "endfieldCapture.summary.v1" or writer.get("complete") is not True
            or writer.get("writerError") is not False or writer.get("dropped") != 0 or writer.get("invalidRecords") != 0):
        raise ValueError("event writer is not complete")
    events = legacy._read_jsonl(session / "events.jsonl")
    if (not events or len(events) != writer.get("records") or events[0].get("type") != 1
            or events[-1].get("type") != 2):
        raise ValueError("event writer count or session start/stop differs from receipt")
    callbacks = {}
    for number, event in enumerate(events, 1):
        if (event.get("writerSequence") != number or event.get("producerSequence") != number
                or event.get("sessionId") != descriptor.get("numericSessionId")):
            raise ValueError(f"events.jsonl:{number}: sequence or session mismatch")
        if event.get("provider") == 2 and event.get("type") == 10:
            decoded = legacy.decode_payload(bytes.fromhex(event["payloadHex"]))
            if decoded["hookName"] not in (legacy.POST_HOOK, legacy.POST_EXTERNAL_HOOK) or decoded["kind"] not in (0, 1):
                raise ValueError(f"events.jsonl:{number}: unexpected managed callback")
            pair = callbacks.setdefault(decoded["captureId"], {})
            if decoded["kind"] in pair:
                raise ValueError(f"events.jsonl:{number}: duplicate managed phase")
            pair[decoded["kind"]] = decoded
            decoded["timestampNs"] = event.get("timestampNs")
            decoded["threadId"] = event.get("threadId")
    for pair in callbacks.values():
        if set(pair) != {0, 1} or pair[0]["hookName"] != pair[1]["hookName"] or not pair[1]["flags"] & 4:
            raise ValueError("managed post callbacks are not exactly paired inside captured windows")
    recorded = _json(session / "private/source-owner-build-manifest.json")
    recipe_provenance = validate_manifest_declarations(recorded, expected)
    activation = _json(session / "private/audio-activation.json")
    wanted = [{key: hook.get(key, "") for key in ("name", "module", "rva", "abiId", "readProgram")}
              for hook in [*expected["hooks"], *expected["nativeHooks"]]]
    actual = [{key: hook.get(key, "") for key in ("name", "module", "rva", "abiId", "readProgram")}
              for hook in activation.get("hooks", [])]
    activation_schema = {profiles.IO_TRANSFER_SCHEMA: 'audioRuntimeTrace.activation.v8', profiles.IO_READ_SCHEMA: 'audioRuntimeTrace.activation.v7', profiles.IO_RESULT_SCHEMA: "audioRuntimeTrace.activation.v6", profiles.IO_SCHEMA: "audioRuntimeTrace.activation.v5",
                         profiles.PROVIDER_SCHEMA: "audioRuntimeTrace.activation.v4",
                         profiles.LEGACY_PROVIDER_SCHEMA: "audioRuntimeTrace.activation.v3",
                         profiles.NATIVE_SCHEMA: "audioRuntimeTrace.activation.v2"}[expected["schema"]]
    if (activation.get("schema") != activation_schema or actual != wanted
            or activation.get("files") != expected["files"] or activation.get("processName") != "Endfield.exe"):
        raise ValueError("staged activation differs from authenticated recipe")
    runtime = session / "private/EndfieldCapture.dll"
    if (runtime.stat().st_size != descriptor.get("runtimeBytes") or
            hashlib.sha256(runtime.read_bytes()).hexdigest() != descriptor.get("runtimeSha256")):
        raise ValueError("staged runtime differs from recorded runtime identity")
    gate = legacy.check_session(session)
    summary = _json(session / "audio/summary.json")
    if any(summary.get(key) is not True for key in ("sourceOwnerSelected", "sourceOwnerWriteComplete", "hooksQuiescent")):
        raise ValueError("source-owner selection/write/quiescence receipt is missing")
    for key in ("attempted", "enqueued", "dropped", "unresolvedResults", "windowsStarted", "windowsCompleted", "sourceOwnerRows"):
        if not _integer(summary.get(key)):
            raise ValueError(f"audio summary counter missing or invalid: {key}")
    if summary["attempted"] != summary["enqueued"]:
        raise ValueError("audio callback queue counts differ")
    spans, open_window = {}, None
    for row in legacy._read_jsonl(session / "audio/windows.jsonl"):
        if row.get("schema") != legacy.WINDOW_SCHEMA:
            raise ValueError("unknown audio window schema")
        if not _integer(row.get("requestId")) or not _integer(row.get("timestampNs")):
            raise ValueError("window identity or timestamp missing")
        if row.get("action") == "start" and open_window is None and row["requestId"] not in spans:
            open_window = row
        elif row.get("action") == "stop" and open_window and row["requestId"] == open_window["requestId"]:
            start, end = row["startNs"], row["endNs"]
            if (start != open_window["startNs"] or not _integer(start) or not _integer(end) or end < start
                    or open_window["timestampNs"] != start or row["timestampNs"] != end
                    or any(start <= previous[1] for previous in spans.values())):
                raise ValueError("audio window boundaries differ")
            spans[row["requestId"]] = (start, end); open_window = None
        else:
            raise ValueError("audio windows are not exactly paired")
    if open_window or len(spans) != gate["windowsCompleted"]:
        raise ValueError("audio window journal differs from summary")
    managed_counts = Counter()
    for pair in callbacks.values():
        entry, result = pair[0], pair[1]
        start, end = entry["timestampNs"], result["timestampNs"]
        if (not _integer(start) or not _integer(end) or start > end
                or entry["threadId"] != result["threadId"] or entry["hookIndex"] != result["hookIndex"]
                or not any(left <= start <= end <= right for left, right in spans.values())):
            raise ValueError("managed post pair differs in thread/hook or crosses a closed window")
        managed_counts[entry["hookName"]] += 1
    rows = legacy._read_jsonl(session / "audio/source_owner.jsonl")
    if len(rows) != summary.get("sourceOwnerRows"):
        raise ValueError("source-owner row count differs from summary")
    provider_spec = provider_gate.get("observerSpec") if provider_gate and provider_gate.get("status") == "validated" else None
    result = audit_entries(rows, expected["nativeHooks"], spans, spec, mapped_image_bytes, provider_spec=provider_spec)
    if provider_gate and provider_spec is None:
        result["providerEntryObservations"] = {"schema": "endfield.audio-provider-entry-observations.v1",
            "status": provider_gate.get("status", "missing"), "detail": provider_gate.get("detail", "dispatch gate unavailable")}
    if io_gates is not None:
        result["ioEntryObservations"] = source_io_observations.summarize(rows, expected["nativeHooks"], io_gates)
        if expected['schema'] == profiles.IO_TRANSFER_SCHEMA:
            from scripts.webui.audio.semantics.transfer_receiver_observations import summarize as summarize_transfers
            result['ioEntryObservations']['packageReadObservations']['transferReceiverObservations'] = summarize_transfers(
                rows, {hook['name']:hook for hook in expected['nativeHooks']}, io_gates['packageReadGate'])
    return {"schema": SCHEMA, "status": "validated", "claimsAvailable": True,
            "session": session.name, "gate": gate, "managedPostCounts": dict(managed_counts),
            "recipeProvenance": recipe_provenance,
            "managedPostObservations": managed_post_observations.summarize(callbacks, expected["hooks"]), **result}


def audit(session: Path, game_root: Path | None = None, *, gameassembly: Path | None = None,
          metadata: Path | None = None, package_index: Path | None = None,
          decode_witness: Path | None = None) -> dict:
    if game_root is not None:
        game_root = game_root.resolve()
        gameassembly = game_root / "GameAssembly.dll"
        metadata = game_root / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    if gameassembly is None or metadata is None:
        return {"schema": SCHEMA, "status": "missing", "claimsAvailable": False,
                "detail": "explicit selected GameAssembly and metadata paths are required"}
    game_root = gameassembly.resolve().parent
    paths = {"gameassembly": gameassembly, "metadata": metadata,
             "ak_sound_engine": game_root / "Endfield_Data/Plugins/x86_64/AkSoundEngine.dll"}
    source, gate = load_validated_source_contract(**paths)
    if source is None:
        return {"schema": SCHEMA, "status": gate["status"], "claimsAvailable": False, "nativeGate": gate}
    queue, queue_gate = queue_native.load_validated_queue_contract(**paths)
    carrier, carrier_gate = carrier_native.load_validated_owner_carrier_contract(**paths)
    if queue is None or carrier is None:
        failed = queue_gate if queue is None else carrier_gate
        return {"schema": SCHEMA, "status": failed["status"], "claimsAvailable": False, "nativeGate": failed}
    try:
        if any(row["nativeInputs"] != source["nativeInputs"] for row in (queue, carrier)):
            raise ValueError("companion inputs differ from authenticated source")
        spec = carrier_gate["ownerCarrierObserverSpec"]
        profile = profiles.build_owner_carrier_profile(source, queue, spec)
        recorded = _json(session / "private/source-owner-build-manifest.json")
        dispatch_gate, io_gates = None, None
        if recorded.get("schema") in (profiles.IO_TRANSFER_SCHEMA, profiles.IO_READ_SCHEMA, profiles.IO_RESULT_SCHEMA, profiles.IO_SCHEMA, profiles.PROVIDER_SCHEMA, profiles.LEGACY_PROVIDER_SCHEMA):
            include_io = recorded["schema"] in (profiles.IO_TRANSFER_SCHEMA, profiles.IO_READ_SCHEMA, profiles.IO_RESULT_SCHEMA, profiles.IO_SCHEMA)
            include_result = recorded["schema"] in (profiles.IO_TRANSFER_SCHEMA, profiles.IO_READ_SCHEMA,profiles.IO_RESULT_SCHEMA)
            include_read = recorded['schema'] in (profiles.IO_TRANSFER_SCHEMA, profiles.IO_READ_SCHEMA)
            include_transfer = recorded['schema'] == profiles.IO_TRANSFER_SCHEMA
            provider, provider_gate = provider_native.load_validated_decoder_provider_contract(**paths, include_storage=True, include_dispatch=True,
                include_package=include_io,include_retention=include_io,include_result=include_result,include_read=include_read)
            dispatch_gate = provider_gate.get("sourceDispatchGate", {"status": "missing", "detail": "source dispatch gate unavailable"})
            storage_gate = provider_gate.get("providerStorageGate", {})
            if provider is None or storage_gate.get("status") != "validated":
                failed = provider_gate if provider is None else storage_gate
                return {"schema": SCHEMA, "status": failed.get("status", "missing"), "claimsAvailable": False, "nativeGate": failed}
            profile = profiles.add_provider_entries(profile, source, provider, storage_gate["contract"],
                                                    expanded=recorded["schema"] != profiles.LEGACY_PROVIDER_SCHEMA)
            if include_io:
                children = [provider_gate.get(key,{"status":"missing","detail":key+" unavailable"}) for key in ("providerRetentionGate","externalPackageGate")]
                failed = next((child for child in children if child.get("status") != "validated"), None)
                if failed:
                    return {"schema":SCHEMA,"status":failed["status"],"claimsAvailable":False,"nativeGate":failed}
                profile = profiles.add_io_entries(profile,storage_gate["contract"],children[0]["contract"],children[1]["contract"])
                if include_result:
                    result_gate = provider_gate.get("packageResultGate", {"status":"missing","detail":"package result gate unavailable"})
                    if result_gate.get("status") != "validated":
                        return {"schema":SCHEMA,"status":result_gate["status"],"claimsAvailable":False,"nativeGate":result_gate}
                    profile = profiles.add_package_completion_entry(profile,result_gate["contract"])
                if include_read:
                    read_gate=provider_gate.get('packageReadGate',{'status':'missing','detail':'package read gate unavailable'})
                    if read_gate.get('status')!='validated':
                        return {'schema':SCHEMA,'status':read_gate['status'],'claimsAvailable':False,'nativeGate':read_gate}
                    profile=profiles.add_package_read_entries(profile,read_gate['contract'])
                    if include_transfer:
                        transform_gate = read_gate.get('packageTransformGate', {'status':'missing','detail':'transfer companion unavailable'})
                        if transform_gate.get('status') != 'validated':
                            return {'schema':SCHEMA,'status':transform_gate['status'],'claimsAvailable':False,'nativeGate':transform_gate}
                        profile = profiles.add_transfer_receiver_entries(profile, read_gate['contract'], transform_gate['contract'])
                io_gates = provider_gate
        expected = profiles.project(profile)
        # The selected native gates checked the three binaries; the descriptor
        # also pins the launched executable, independently of saved reports.
        target = expected["files"]["executable"]
        target_path = (game_root / target["relativePath"]).resolve()
        if target_path.stat().st_size != target["bytes"] or sha256_file(target_path) != target["sha256"]:
            raise ValueError("selected executable differs from authenticated source recipe")
        report = audit_session(session, expected, spec, pe_mapped_image_size(paths["ak_sound_engine"]), provider_gate=dispatch_gate, io_gates=io_gates)
        if package_index is not None and io_gates is not None and recorded['schema'] in (profiles.IO_TRANSFER_SCHEMA, profiles.IO_READ_SCHEMA):
            from scripts.webui.audio.semantics.package_read_witness import match_indexed_words, SCHEMA as witness_schema
            try:
                witness=match_indexed_words(legacy._read_jsonl(session/'audio/source_owner.jsonl'),
                    {h['name']:h for h in expected['nativeHooks']},io_gates['packageReadGate'],package_index)
            except (OSError,ValueError,KeyError,TypeError) as error:
                witness={'schema':witness_schema,'status':'incomplete','detail':str(error)[:240]}
            report['ioEntryObservations']['packageReadObservations']['encodedWordWitness']=witness
            if decode_witness is not None:
                from scripts.webui.audio.semantics.package_decode_witness import project_decode_receipt
                report['ioEntryObservations']['packageReadObservations']['offlineDecodeObservations'] = (
                    project_decode_receipt(witness, decode_witness))
        return report
    except (OSError, ValueError, KeyError, TypeError, legacy.SessionError) as error:
        return {"schema": SCHEMA, "status": "incomplete", "claimsAvailable": False, "detail": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "reports/audio/endfield_source_owner_audit.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if not any(output.is_relative_to((REPO_ROOT / name).resolve()) for name in ("reports", "scratch", "tmp")):
        parser.error("audit output must remain under reports, scratch or tmp")
    if output.is_relative_to(args.session.resolve()):
        parser.error("audit output must remain outside the captured session")
    report = audit(args.session, args.game_root.resolve())
    json_dump(output, report)
    print(json.dumps({key: report[key] for key in ("status", "claimsAvailable", "detail", "entryCount") if key in report}))
    return 0 if report.get("claimsAvailable") else 2


if __name__ == "__main__":
    raise SystemExit(main())
