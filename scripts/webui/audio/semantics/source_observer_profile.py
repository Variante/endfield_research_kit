"""Pure Audio observer recipes projected from authenticated native contracts.

The shared recipe owns field declarations for historical paired recordings and
EndfieldCapture entry snapshots. It performs no capture, publication or lookup.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any

GENERIC_SCHEMA = "audioRuntimeTrace.hooks.v2"
NATIVE_SCHEMA = "endfieldCapture.audioSourceOwnerBuild.v1"
LEGACY_PROVIDER_SCHEMA = "endfieldCapture.audioSourceProviderBuild.v1"
PROVIDER_SCHEMA = "endfieldCapture.audioSourceProviderBuild.v2"
IO_SCHEMA = "endfieldCapture.audioSourceIoBuild.v1"
IO_RESULT_SCHEMA = "endfieldCapture.audioSourceIoBuild.v2"
IO_READ_SCHEMA = "endfieldCapture.audioSourceIoBuild.v3"
IO_TRANSFER_SCHEMA = "endfieldCapture.audioSourceIoBuild.v4"
ABI = "win64.transparent_entry_snapshot.v1"


def matches_generic_profile_recipe(profile: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Compare capture operations, preserving descriptive boundary shape.

    The top-level evidenceBoundary is explanatory contract prose, not a hook
    declaration or an audit claim source. Its wording may evolve as the same
    native bytes gain stronger proof. Historical captures still require the
    exact key/type shape and every operational field of the selected recipe.
    Other boundary blocks remain exact: some contain consumer-role keys used
    by the strict auditor. The auditor publishes its maintained claims only.
    """
    if not isinstance(profile, dict) or not isinstance(expected, dict):
        return False
    recorded_boundary, current_boundary = profile.get("evidenceBoundary"), expected.get("evidenceBoundary")
    if (not isinstance(recorded_boundary, dict) or not isinstance(current_boundary, dict)
            or recorded_boundary.keys() != current_boundary.keys()
            or not all(isinstance(value, str) and value.strip()
                       for value in (*recorded_boundary.values(), *current_boundary.values()))):
        return False
    identity = {**profile, "evidenceBoundary": current_boundary}
    # JSON retains boolean/number distinctions which dict equality erases.
    return json.dumps(identity, sort_keys=True, separators=(",", ":")) == json.dumps(expected, sort_keys=True, separators=(",", ":"))


def build_profile(
    contract: dict[str, Any], *, include_source_consumer: bool = False,
    include_source_bridge: bool = False, queue_contract: dict[str, Any] | None = None,
    include_owner_carrier: bool = False, owner_carrier_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project verified recipes; the optional consumer keeps its RCX role anonymous."""
    if sum((include_source_consumer, include_source_bridge, include_owner_carrier)) > 1:
        raise ValueError("select one source consumer, source bridge or owner carrier recipe")
    if include_owner_carrier:
        if queue_contract is None or owner_carrier_spec is None:
            raise ValueError("owner carrier recipe requires validated queue and owner carrier companions")
        return build_owner_carrier_profile(contract, queue_contract, owner_carrier_spec)
    if include_source_bridge:
        if include_source_consumer:
            raise ValueError("select one source consumer or source bridge recipe")
        if queue_contract is None:
            raise ValueError("source bridge recipe requires a validated companion queue contract")
        return build_source_bridge_profile(contract, queue_contract)
    hooks = [{
        "name": row["name"], "sourceKind": row["sourceKind"], "mode": "request",
        "rva": row["rva"], "required": True, "args": copy.deepcopy(row["args"]),
        "returnKind": row["returnKind"],
    } for row in contract["managedMethods"]]
    native_hooks = []
    for row in contract["methods"]:
        memory = []
        for observation in row["observe"]:
            layout = contract["structures"][observation["structure"]]
            memory.extend({**field, "argIndex": observation["argIndex"]} for field in layout["fields"])
        native_hooks.append({
            "name": f"AkSoundEngine.{row['key']}", "sourceKind": row["key"],
            "rva": row["rva"], "required": True,
            "args": copy.deepcopy(row["args"]), "returnKind": "void", "memory": memory,
        })
    profile = {
        "schema": GENERIC_SCHEMA,
        "gameBuild": "endfield-source-" + contract["nativeInputs"]["gameAssemblySha256"][:12],
        "processName": "Endfield.exe", "moduleName": "GameAssembly.dll",
        "nativeModuleName": "AkSoundEngine.dll", "observerProfile": "boundedSourceStateV1",
        "files": copy.deepcopy(contract["captureFiles"]),
        "hooks": hooks, "nativeHooks": native_hooks,
        "evidenceBoundary": copy.deepcopy(contract["evidenceBoundary"]),
        "correlationBoundary": {
            "pairing": "Pair native entry/result by sessionId, threadId and nativeCaptureId; retain sourceThisPointer and mediaRefOutputPointer.",
            "sourceState": "Same-pointer SetSource then LockDataPtr is conditional on complete pairs, same thread and no intervening observed source reset. Pointer reuse and uncaptured lifecycle remain open.",
            "identities": "externalSourceKey, externalCookie, sourceArgumentU32, sourceLookupWord and sourceArgumentWord24 retain distinct roles; equality alone creates no ownership edge.",
            "managedContext": "managedCallStack and nativeParentCaptureId witness synchronous nesting only; nearby timestamps do not prove asynchronous ownership.",
            "bytes": "Only fixed source/info/output scalar fields are sampled. Media bytes, file contents and unbounded structures are not read.",
        },
    }

    if include_source_consumer:
        consumers = contract.get("consumers")
        if not consumers:
            raise ValueError("selected verified source contract has no source consumer entries")
        for row in consumers:
            owner = row["ownerArgument"]
            source = row["sourcePointerField"]
            output = row["outputReference"]
            memory = [{"name": source["name"], "kind": "pointer", "offset": source["offset"],
                       "argIndex": owner["index"]}]
            memory.extend({"name": field["name"], "kind": field["kind"],
                           "offset": output["offset"] + field["offset"], "argIndex": owner["index"]}
                          for field in contract["structures"][output["structure"]]["fields"])
            native_hooks.append({
                "name": f"AkSoundEngine.{row['key']}", "sourceKind": row["key"],
                "rva": row["entryRva"], "required": True,
                "args": {owner["name"]: {"index": owner["index"], "kind": owner["kind"]}},
                # The observer ignores the result; the consumer return ABI is
                # not declared by the native contract.
                "returnKind": "void", "memory": memory,
            })
        profile["observerProfile"] = "boundedSourceStateWithConsumerV1"
        profile["sourceConsumerEvidenceBoundary"] = {
            row["key"]: copy.deepcopy(row["evidenceBoundary"]) for row in consumers
        }
        profile["correlationBoundary"]["sourceConsumer"] = (
            "The consumer RCX argument is an anonymous address point. Fixed reads sample only its directly proved source member "
            "and embedded output-reference fields, without following the source pointer. Native parent IDs witness synchronous "
            "nesting only; no primary allocation address, SDK type, lifetime, managed ownership or successful media lookup is established."
        )
    return profile


def _source_fields(contract: dict[str, Any], arg_index: int, *, prefix: str = "") -> list[dict[str, Any]]:
    return [{"name": prefix + field["name"][0].upper() + field["name"][1:] if prefix else field["name"],
             "kind": field["kind"], "offset": field["offset"], "argIndex": arg_index}
            for field in contract["structures"]["source"]["fields"]]


def build_source_bridge_profile(contract: dict[str, Any], queue_contract: dict[str, Any]) -> dict[str, Any]:
    """Build bounded true-entry samples from the independently gated companion."""
    if queue_contract.get("nativeInputs") != contract.get("nativeInputs"):
        raise ValueError("source bridge companion native inputs differ from source contract")
    bridge = queue_contract.get("sourceBridgeObserver")
    if (not isinstance(bridge, dict) or isinstance(bridge.get("maxDescriptorRows"), bool)
            or bridge.get("maxDescriptorRows") != 1):
        raise ValueError("source bridge companion must declare its one-descriptor sample scope")
    roles, layouts = bridge["functionRoles"], bridge["bridgeLayouts"]
    blob, allocation, descriptor = (layouts[key] for key in ("playbackBlob", "externalAllocation", "descriptor"))
    groups = {row["key"]: row for row in queue_contract["nativeGroups"]}
    profile = build_profile(contract, include_source_consumer=True)
    existing_hooks = {row["sourceKind"]: row for row in profile["nativeHooks"]}
    lock_hooks = [row for row in profile["nativeHooks"] if row["sourceKind"] == "sourceLockDataPtr"]
    consumer_hooks = [existing_hooks[row["key"]] for row in contract["consumers"]]
    if len(lock_hooks) != 1 or len(contract.get("ownerTransports", [])) != 1:
        raise ValueError("source bridge recipe requires one LockDataPtr and owner transport")
    transport = contract["ownerTransports"][0]
    native_hooks = []
    for role_key in ("sourceSelector", "sourceClone", "sourceSetWideText", "ownerFactory", "ownerConstructor"):
        role = roles[role_key]
        source_role = role.get("sourceContractRole")
        if source_role is not None:
            expected_source_role = {"ownerFactory": "factory", "ownerConstructor": "constructor"}.get(role_key)
            if source_role != expected_source_role:
                raise ValueError(f"source bridge {role_key} has an invalid source contract endpoint")
            endpoint = transport[source_role]
        else:
            endpoint = groups[role["groupKey"]]
        hook = {"name": f"AkSoundEngine.{endpoint['key']}", "sourceKind": endpoint["key"],
                "rva": endpoint["entryRva"], "required": True,
                "args": copy.deepcopy(role["args"]), "returnKind": role["returnKind"], "memory": []}
        if role_key == "sourceSelector":
            source_index = role["args"]["originalSourcePointer"]["index"]
            blob_index = role["args"]["playbackBlobPointer"]["index"]
            hook["memory"] = _source_fields(contract, source_index, prefix="original")
            for name, kind, layout_key in (
                ("playbackConfigInterfacePointer", "pointer", "configInterfacePointer"),
                ("externalDescriptorAllocationPointer", "pointer", "externalAllocationPointer"),
                ("playbackContextPointer", "pointer", "contextPointer"),
                ("playbackExternalFlagsWord", "u32", "flagsWord"),
                ("playbackSerialWord", "u32", "serialWord"),
            ):
                hook["memory"].append({"name": name, "kind": kind, "argIndex": blob_index, "offset": blob[layout_key]})
            allocation_offsets = [blob["externalAllocationPointer"]]
            hook["memory"].extend([
                {"name": "playbackConfigAddressPointPointer", "kind": "pointer", "argIndex": blob_index,
                 "pointerOffsets": [blob["configInterfacePointer"]], "offset": 0,
                 "requireMemory": {"name": "playbackConfigInterfacePointer", "nonzero": True}},
                {"name": "externalDescriptorCount", "kind": "u32", "argIndex": blob_index,
                 "pointerOffsets": allocation_offsets, "offset": allocation["count"],
                 "requireMemory": {"name": "externalDescriptorAllocationPointer", "nonzero": True}},
            ])
            for key, kind in (("matchWord", "u32"), ("argumentWord", "u32"), ("wideTextPointer", "pointer"),
                              ("memoryPointer", "pointer"), ("byteCountWord", "u32"), ("selectionWord", "u32")):
                hook["memory"].append({"name": "descriptor0" + key[0].upper() + key[1:], "kind": kind,
                    "argIndex": blob_index, "pointerOffsets": allocation_offsets,
                    "offset": allocation["firstDescriptor"] + descriptor[key],
                    "requireMemory": {"name": "externalDescriptorCount", "equals": bridge["maxDescriptorRows"]}})
            hook["memory"].append({"name": "descriptor0WideText", "kind": "utf16Direct", "argIndex": blob_index,
                "pointerOffsets": [blob["externalAllocationPointer"], allocation["firstDescriptor"] + descriptor["wideTextPointer"]],
                "offset": 0, "requireMemory": {"name": "descriptor0WideTextPointer", "nonzero": True}})
        elif role_key == "sourceClone":
            hook["memory"] = _source_fields(contract, role["args"]["originalSourcePointer"]["index"], prefix="original")
        elif role_key == "sourceSetWideText":
            if hook["args"]["descriptorWideTextPointer"].get("allowNull") is not True:
                raise ValueError("source bridge wide-text argument must declare its nullable pointer role")
            hook["memory"] = _source_fields(contract, role["args"]["sourceThisPointer"]["index"])
            hook["memory"].append({"name": "descriptorWideText", "kind": "utf16Direct", "offset": 0,
                                   "argIndex": role["args"]["descriptorWideTextPointer"]["index"],
                                   "requireArgument": {"name": "descriptorWideTextPointer", "nonzero": True}})
        else:
            source_index = endpoint["sourceArgument"]["index"]
            hook["memory"] = _source_fields(contract, source_index)
            if role_key == "ownerConstructor":
                owner_index = endpoint["ownerArgument"]["index"]
                hook["memory"].extend([
                    {"name": "primaryEmbeddedAddressPointPointer", "kind": "pointer", "argIndex": owner_index,
                     "offset": transport["consumerOwnerOffset"], "samplePhase": "result"},
                    {"name": "primaryStoredSourcePointer", "kind": "pointer", "argIndex": owner_index,
                     "offset": transport["primarySourcePointerOffset"], "samplePhase": "result"},
                ])
        native_hooks.append(hook)
    profile["nativeHooks"] = [*native_hooks, *consumer_hooks, *lock_hooks]
    profile["observerProfile"] = "boundedSourceBridgeWithConsumerV1"
    profile["sourceBridgeEvidenceBoundary"] = copy.deepcopy(queue_contract["evidenceBoundary"])
    profile["sourceBridgeArgumentScopes"] = {
        key: {"argumentScope": role["argumentScope"],
              "additionalStackInputs": role.get("additionalStackInputs", False)}
        for key, role in roles.items() if "argumentScope" in role
    }
    profile["sourceBridgeSelectionScope"] = {
        "descriptorSampleLimit": bridge["maxDescriptorRows"],
        "descriptorClosure": "Only an allocation count of 1 can close the sampled descriptor choice; other counts remain unresolved.",
        "wideText": "Bounded terminated 16-bit text from declared descriptor/setter roles; no media bytes are sampled.",
        "queueJoin": "Playback serial and retained pointer observations are conditional. Allocation creation, generation and complete lifetime are not observed by this recipe.",
    }
    profile["correlationBoundary"]["sourceBridge"] = (
        "True selector/clone/wide-setter/factory/constructor entries sample declared pointers and fixed fields. "
        "Strict same-thread native parent nesting can connect the selected source to its constructed owner and consumer. "
        "The queued managed request join remains conditional on serial and allocation lineage; equality alone establishes no ownership."
    )
    profile["correlationBoundary"]["bytes"] = (
        "Fixed source/owner/blob fields and one declared descriptor row are sampled through bounded pointer chains. "
        "Terminated descriptor/setter text is bounded by the generic agent. Media bytes and file contents are not read."
    )
    return profile


def build_owner_carrier_profile(
    contract: dict[str, Any], queue_contract: dict[str, Any], spec: dict[str, Any],
) -> dict[str, Any]:
    """Add entry-only decoder-owner samples to the exact source bridge recipe."""
    if (spec.get("schema") != "endfield.wwise-owner-carrier-observer.v1"
            or spec.get("moduleName") != Path(contract["captureFiles"]["akSoundEngine"]["relativePath"]).name
            or spec.get("memorySamplePhase") != "entry"):
        raise ValueError("owner carrier companion must declare the selected module and entry-only scope")
    transports = contract.get("ownerTransports", [])
    if (len(transports) != 1 or type(spec.get("sourcePointerOffset")) is not int
            or spec["sourcePointerOffset"] != transports[0]["primarySourcePointerOffset"]
            or json.dumps(spec.get("sourceFields"), sort_keys=True) != json.dumps(contract["structures"]["source"]["fields"], sort_keys=True)):
        raise ValueError("owner carrier source projection differs from the selected source contract")
    role = spec["roles"]["carrierCommand4"]
    args = role["args"]
    if (set(args) != {"carrierPointer", "primaryOwnerPointer"} or role.get("returnKind") != "void"
            or any(not isinstance(value, dict) or type(value.get("index")) is not int
                   or not 0 <= value["index"] <= 3 or value.get("kind") != "pointer" for value in args.values())
            or len({value["index"] for value in args.values()}) != 2):
        raise ValueError("owner carrier true-entry arguments and ignored return policy are required")

    def field(layout: str, name: str, kind: str = "pointer") -> int:
        value = spec["layouts"][layout][name]
        if (not isinstance(value, dict) or value.get("kind") != kind or type(value.get("offset")) is not int
                or not 0 <= value["offset"] <= 4096):
            raise ValueError(f"owner carrier {layout}.{name} must be a bounded declared {kind} field")
        return value["offset"]

    carrier_index, owner_index = args["carrierPointer"]["index"], args["primaryOwnerPointer"]["index"]
    memory = []
    for name in ("currentDecoderPointer", "pendingDecoderPointer"):
        memory.append({"name": name, "kind": "pointer", "argIndex": carrier_index,
                       "offset": field("carrier", name), "samplePhase": "entry",
                       "requireArgument": {"name": "carrierPointer", "nonzero": True}})
        memory.append({"name": name.removesuffix("Pointer") + "PrimaryOwnerPointer", "kind": "pointer",
                       "argIndex": carrier_index, "pointerOffsets": [field("carrier", name)],
                       "offset": field("decoder", "primaryOwnerPointer"), "samplePhase": "entry",
                       "requireMemory": {"name": name, "nonzero": True}})
    memory.extend([
        {"name": "primaryOwnerAddressPointPointer", "kind": "pointer", "argIndex": owner_index,
         "offset": field("primaryOwner", "addressPoint"), "samplePhase": "entry",
         "requireArgument": {"name": "primaryOwnerPointer", "nonzero": True}},
        {"name": "primaryStoredSourcePointer", "kind": "pointer", "argIndex": owner_index,
         "offset": spec["sourcePointerOffset"], "samplePhase": "entry",
         "requireArgument": {"name": "primaryOwnerPointer", "nonzero": True}},
    ])
    for source_field in spec["sourceFields"]:
        memory.append({"name": "owner" + source_field["name"][0].upper() + source_field["name"][1:],
                       "kind": source_field["kind"], "argIndex": owner_index,
                       "pointerOffsets": [spec["sourcePointerOffset"]], "offset": source_field["offset"],
                       "samplePhase": "entry", "requireMemory": {"name": "primaryStoredSourcePointer", "nonzero": True}})
    profile = build_source_bridge_profile(contract, queue_contract)
    profile["nativeHooks"].append({"name": f"AkSoundEngine.{role['sourceKind']}", "sourceKind": role["sourceKind"],
                                   "rva": role["entryRva"], "required": True, "args": copy.deepcopy(args),
                                   "returnKind": "void", "memory": memory})
    profile["observerProfile"] = "boundedSourceBridgeWithOwnerCarrierV1"
    profile["ownerCarrierEvidenceBoundary"] = copy.deepcopy(spec["evidenceBoundary"])
    profile["ownerCarrierSampleScope"] = {
        "memorySamplePhase": "entry",
        "decoderSelection": "Current/pending decoder pointers and their stored owner pointers are sampled before command-4 control; result fields are null.",
        "sourceState": "The argument owner address point, stored source pointer and fixed source fields are sampled at this entry only.",
        "lifetime": "No decoder/source generation, queue retention, earlier-selector continuity or managed request ownership follows from a later pointer match.",
    }
    profile["correlationBoundary"]["ownerCarrier"] = (
        "The selected command-4 handler compares current or pending decoder owner to the primary owner argument. "
        "Entry-only snapshots can witness that comparison scope after independent address-point/caller validation. "
        "The handler can release a decoder; no decoder/owner/source field is dereferenced on return."
    )
    return profile


def read_program(hook: dict) -> tuple[str, list[dict]]:
    """Compile proved entry reads; result-only fields are deliberately absent."""
    fields = [copy.deepcopy(row) for row in hook["memory"] if row.get("samplePhase") != "result"]
    if not 1 <= len(fields) <= 24 or sum(row["kind"] == "utf16Direct" for row in fields) > 1:
        raise ValueError("entry read budget exceeded")
    rows, names = [], {}
    for index, field in enumerate(fields):
        chain = field.get("pointerOffsets", [])
        if len(chain) > 2:
            raise ValueError("entry pointer-chain budget exceeded")
        chain = chain + [4097] * (2 - len(chain))
        mode, reference, value = 0, 0, 0
        if "requireMemory" in field:
            gate = field["requireMemory"]
            reference = names[gate["name"]]
            mode, value = (1, 0) if gate.get("nonzero") is True else (2, gate["equals"])
        elif "requireArgument" in field:
            gate = field["requireArgument"]
            if gate.get("nonzero") is not True:
                raise ValueError("unsupported entry argument guard")
            mode, reference = 3, hook["args"][gate["name"]]["index"]
        words = [field["argIndex"], {"pointer": 1, "u64": 1, "u32": 2, "utf16Direct": 3}[field["kind"]],
                 field["offset"], *chain, mode, reference, value]
        if any(type(word) is not int or word < 0 for word in words) or words[0] > 3 or words[2] > 4096:
            raise ValueError("unbounded entry declaration")
        rows.append(",".join(map(str, words)) + ";")
        names[field["name"]] = index
    program = "".join(rows)
    if len(program) >= 1024:
        raise ValueError("entry program budget exceeded")
    return program, fields


def add_provider_entries(profile: dict, source: dict, provider: dict, storage: dict, *, expanded: bool = True) -> dict:
    """Project RCX decoder and RCX/RDX provider/descriptor reads proved by bodies.

    These are transparent entries, so additional stack inputs and returns need
    no guessed prototype. Layouts and addresses come only from gated contracts.
    """
    if provider["nativeInputs"] != source["nativeInputs"] or storage["nativeInputs"] != source["nativeInputs"]:
        raise ValueError("provider entry contracts differ from selected source inputs")
    result = copy.deepcopy(profile)
    groups = {row["key"]: row for row in provider["nativeGroups"]}
    storage_groups = {row["key"]: row for row in storage["nativeGroups"]}
    layout = provider["layouts"]
    owner_offset = layout["decoder"]["primaryOwnerPointer"]
    source_offset = layout["primaryOwner"]["sourcePointer"]
    memory = [
        {"name": "decoderPrimaryOwnerPointer", "kind": "pointer", "argIndex": 0, "offset": owner_offset},
        {"name": "decoderProviderOutputPointer", "kind": "pointer", "argIndex": 0, "offset": layout["decoder"]["providerOutputPointer"]},
        {"name": "ownerStoredSourcePointer", "kind": "pointer", "argIndex": 0, "pointerOffsets": [owner_offset],
         "offset": source_offset, "requireMemory": {"name": "decoderPrimaryOwnerPointer", "nonzero": True}},
    ]
    for row in source["structures"]["source"]["fields"]:
        memory.append({"name": "owner" + row["name"][0].upper() + row["name"][1:], "kind": row["kind"],
                       "argIndex": 0, "pointerOffsets": [owner_offset, source_offset], "offset": row["offset"],
                       "requireMemory": {"name": "ownerStoredSourcePointer", "nonzero": True}})
    for name, kind, field in (("ownerAlternatePointer", "pointer", "alternatePointer"), ("ownerAlternateWord", "u32", "alternateWord")):
        memory.append({"name": name, "kind": kind, "argIndex": 0, "pointerOffsets": [owner_offset],
                       "offset": layout["primaryOwner"][field], "requireMemory": {"name": "decoderPrimaryOwnerPointer", "nonzero": True}})
    result["nativeHooks"].append({"name": "AkSoundEngine.anonymousDecoderProviderPreparation", "sourceKind": "anonymousDecoderProviderPreparation",
        "rva": groups["anonymousDecoderProviderPreparation"]["entryRva"], "required": True, "returnKind": "void",
        "args": {"decoderPointer": {"index": 0, "kind": "pointer"}, "requestPointer": {"index": 1, "kind": "pointer"}}, "memory": memory})
    descriptor = storage["layouts"]["descriptor"]
    memory = [{"name": "providerAddressPointPointer", "kind": "pointer", "argIndex": 0, "offset": storage["layouts"]["provider"]["primaryTable"]}]
    for name, kind, field in (("inputTextPointer", "pointer", "textPointer"), ("inputNumericWord", "u32", "numericWord"),
                              ("inputAuxiliaryPointer", "pointer", "auxiliaryPointer"), ("inputModeWord", "u32", "modeWord")):
        memory.append({"name": name, "kind": kind, "argIndex": 1, "offset": descriptor[field]})
    memory.append({"name": "inputWideText", "kind": "utf16Direct", "argIndex": 1, "offset": 0,
                   "pointerOffsets": [descriptor["textPointer"]], "requireMemory": {"name": "inputTextPointer", "nonzero": True}})
    result["nativeHooks"].append({"name": "AkSoundEngine.anonymousProviderDescriptorStorage", "sourceKind": "anonymousProviderDescriptorStorage",
        "rva": storage_groups["providerDescriptorStorage"]["entryRva"], "required": True, "returnKind": "void",
        "args": {"providerPointer": {"index": 0, "kind": "pointer"}, "inputDescriptorPointer": {"index": 1, "kind": "pointer"}}, "memory": memory})
    if expanded:
        # Capture the whole reviewed dispatch/storage lane together. In particular,
        # the alternate factory does not dereference its incoming media pointer.
        descriptor_fields = copy.deepcopy(memory[1:])
        result["nativeHooks"].append({
            "name": "AkSoundEngine.anonymousOrdinaryProviderFactory", "sourceKind": "anonymousOrdinaryProviderFactory",
            "rva": storage_groups["ordinaryProviderFactory"]["entryRva"], "required": True, "returnKind": "void",
            "args": {"factoryPointer": {"index": 0, "kind": "pointer"},
                     "inputDescriptorPointer": {"index": 1, "kind": "pointer"},
                     "optionsPointer": {"index": 2, "kind": "pointer"},
                     "requestPointer": {"index": 3, "kind": "pointer"}}, "memory": descriptor_fields})
        # The selected initializer's storeFactoryTable witness stores at the
        # allocation base. Zero is the ordinary address-point base displacement,
        # not a build-specific layout inferred from another object family.
        result["nativeHooks"].append({
            "name": "AkSoundEngine.anonymousAlternateProviderFactory", "sourceKind": "anonymousAlternateProviderFactory",
            "rva": storage_groups["alternateProviderFactory"]["entryRva"], "required": True, "returnKind": "void",
            "args": {"factoryPointer": {"index": 0, "kind": "pointer"},
                     "inputDataPointer": {"index": 1, "kind": "pointer"},
                     "inputDataWord": {"index": 2, "kind": "u64"},
                     "optionsPointer": {"index": 3, "kind": "pointer"}},
            "memory": [{"name": "factoryAddressPointPointer", "kind": "pointer", "argIndex": 0, "offset": 0,
                        "requireArgument": {"name": "factoryPointer", "nonzero": True}}]})
        leaves = {row["key"]: row for row in storage["leafWindows"]}
        open_fields = copy.deepcopy(memory)
        open_fields.insert(1, {"name": "providerStoredDescriptorPointer", "kind": "pointer", "argIndex": 0,
                               "offset": storage["layouts"]["provider"]["descriptorAllocation"]})
        result["nativeHooks"].append({
            "name": "AkSoundEngine.anonymousOrdinaryProviderOpen", "sourceKind": "anonymousOrdinaryProviderOpen",
            "rva": leaves["ordinaryProviderOpen"]["entryRva"], "required": True, "returnKind": "void",
            "args": {"providerPointer": {"index": 0, "kind": "pointer"},
                     "inputDescriptorPointer": {"index": 1, "kind": "pointer"}}, "memory": open_fields})
        result["providerBatchScope"] = (
            "One window retains every reviewed source/owner/carrier entry plus decoder preparation, "
            "ordinary and alternate factories, ordinary open-dispatch and descriptor storage. "
            "Multiple distinct voice plays may share the window; no per-voice restart is required."
        )
    result["providerEntryScope"] = (
        "Local decoder/owner/source fields and provider input descriptor/text at entry only. "
        "No returned provider, stored copy, successful file opening, pointer lifetime or cross-call request ownership is established."
    )
    return result


def add_io_entries(profile: dict, storage: dict, retention: dict, package: dict) -> dict:
    """Add separately gated retained-provider and external-package entry reads."""
    if "providerBatchScope" not in profile or any(c["nativeInputs"] != storage["nativeInputs"] for c in (retention,package)):
        raise ValueError("I/O entries require the combined provider recipe and matching selected companions")
    profile = copy.deepcopy(profile)
    groups = {g["key"]:g for g in retention["nativeGroups"]}
    provider, descriptor = retention["layouts"]["provider"], storage["layouts"]["descriptor"]
    fields = [{"name":"providerAddressPointPointer","kind":"pointer","argIndex":0,"offset":provider["addressPoint"]},
              {"name":"retainedDescriptorPointer","kind":"pointer","argIndex":0,"offset":provider["descriptor"]},
              {"name":"selectedDevicePointer","kind":"pointer","argIndex":0,"offset":provider["device"]}]
    guard = {"name":"retainedDescriptorPointer","nonzero":True}
    for name,kind,key in (("retainedTextPointer","pointer","textPointer"),("retainedNumericWord","u32","numericWord"),("retainedFlagsPointer","pointer","auxiliaryPointer")):
        fields.append({"name":name,"kind":kind,"argIndex":0,"pointerOffsets":[provider["descriptor"]],"offset":descriptor[key],"requireMemory":guard})
    fields.append({"name":"retainedWideText","kind":"utf16Direct","argIndex":0,"pointerOffsets":[provider["descriptor"],descriptor["textPointer"]],"offset":0,"requireMemory":{"name":"retainedTextPointer","nonzero":True}})
    for group,name in (("providerRetainedPreparation","anonymousProviderRetainedPreparation"),("providerStartPrimary","anonymousProviderStartPrimary")):
        memory = copy.deepcopy(fields)
        if group == "providerStartPrimary":
            io = retention["layouts"]["device"]["ioContext"]
            memory.extend([
                {"name":"selectedIoContextPointer","kind":"pointer","argIndex":0,"pointerOffsets":[provider["device"]],"offset":io,"requireMemory":{"name":"selectedDevicePointer","nonzero":True}},
                {"name":"selectedIoAddressPointPointer","kind":"pointer","argIndex":0,"pointerOffsets":[provider["device"],io],"offset":0,"requireMemory":{"name":"selectedIoContextPointer","nonzero":True}}])
        profile["nativeHooks"].append({"name":"AkSoundEngine."+name,"sourceKind":name,"rva":groups[group]["entryRva"],"required":True,"returnKind":"void","args":{"providerPointer":{"index":0,"kind":"pointer"}},"memory":memory})
    groups = {g["key"]:g for g in package["nativeGroups"]}
    profile["nativeHooks"].append({"name":"AkSoundEngine.anonymousExternalPackagePathHash","sourceKind":"anonymousExternalPackagePathHash","rva":groups["externalPathHash"]["entryRva"],"required":True,"returnKind":"void",
        "args":{"packageContextPointer":{"index":0,"kind":"pointer"},"pathPointer":{"index":1,"kind":"pointer"}},
        "memory":[{"name":"externalPackageWideText","kind":"utf16Direct","argIndex":1,"offset":0,"requireArgument":{"name":"pathPointer","nonzero":True}}]})
    table = package["lookupLayout"]["tablePointer"]
    profile["nativeHooks"].append({"name":"AkSoundEngine.anonymousExternalPackageKeyLookup","sourceKind":"anonymousExternalPackageKeyLookup","rva":groups["externalKeyLookup"]["entryRva"],"required":True,"returnKind":"void",
        "args":{"packageContextPointer":{"index":0,"kind":"pointer"},"externalPackageKey":{"index":1,"kind":"u64"},"flagsPointer":{"index":2,"kind":"pointer"}},
        "memory":[{"name":"externalPackageFlagsKind","kind":"u32","argIndex":2,"offset":0},
                  {"name":"externalPackageTablePointer","kind":"pointer","argIndex":0,"offset":table},
                  {"name":"externalPackageTableCount","kind":"u32","argIndex":0,"pointerOffsets":[table],"offset":0,"requireMemory":{"name":"externalPackageTablePointer","nonzero":True}}]})
    profile["observerProfile"] = "endfieldSourceIoEntryV1"
    return profile


def add_package_completion_entry(profile: dict, contract: dict) -> dict:
    """Read completed descriptors before the handler can release its request."""
    if profile.get("observerProfile") != "endfieldSourceIoEntryV1":
        raise ValueError("package completion requires the complete source-I/O recipe")
    result = copy.deepcopy(profile)
    p,q,r = (contract[key] for key in ("providerLayout","requestLayout","resultLayout"))
    memory = [{"name":"providerAddressPointPointer","kind":"pointer","argIndex":0,"offset":p['addressPoint']},
              {"name":"providerRetainedRequestPointer","kind":"pointer","argIndex":0,"offset":p['retainedRequest']},
              {"name":"providerResultPointer","kind":"pointer","argIndex":0,"offset":p['result']}]
    for name,kind,key in (("requestTextPointer","pointer","text"),("requestNumericWord","u32","numeric"),
                          ("requestFlagsPointer","pointer","flags"),("requestModeWord","u32","mode"),
                          ("requestProviderPointer","pointer","provider"),("requestResultPointer","pointer","result")):
        memory.append({"name":name,"kind":kind,"argIndex":1,"offset":q[key]})
    memory.append({"name":"requestWideText","kind":"utf16Direct","argIndex":1,"pointerOffsets":[q['text']],"offset":0,
                   "requireMemory":{"name":"requestTextPointer","nonzero":True}})
    memory.append({"name":"requestFlagsKind","kind":"u32","argIndex":1,"pointerOffsets":[q['flags']],"offset":0,
                   "requireMemory":{"name":"requestFlagsPointer","nonzero":True}})
    for name,kind,key in (("resultByteLength","u64","byteLength"),("resultBlockOffset","u64","blockOffset"),
                          ("resultByteOffset","u32","byteOffset"),("resultKeyLow","u32","keyLow"),
                          ("resultPackagePointer","pointer","package"),("resultBlockBytes","u32","blockBytes")):
        memory.append({"name":name,"kind":kind,"argIndex":1,"pointerOffsets":[q['result']],"offset":r[key],
                       "requireMemory":{"name":"requestResultPointer","nonzero":True}})
    memory.append({"name":"resultPackageBackingObjectPointer","kind":"pointer","argIndex":1,"pointerOffsets":[q['result'],r['package']],
                   "offset":contract['packageLayout']['backingObject'],"requireMemory":{"name":"resultPackagePointer","nonzero":True}})
    entry = next(g['entryRva'] for g in contract['nativeGroups'] if g['key']=='providerPackageCompletion')
    result['nativeHooks'].append({"name":"AkSoundEngine.anonymousProviderPackageCompletion","sourceKind":"anonymousProviderPackageCompletion",
        "rva":entry,"required":True,"returnKind":"void","args":{"providerPointer":{"index":0,"kind":"pointer"},
            "requestPointer":{"index":1,"kind":"pointer"},"completionStatus":{"index":2,"kind":"u32"}},"memory":memory})
    result['observerProfile'] = 'endfieldSourceIoEntryV2'
    return result


def add_package_read_entries(profile: dict, contract: dict) -> dict:
    """Keep older entries and add bounded read/completion/transform inputs."""
    if profile.get('observerProfile') != 'endfieldSourceIoEntryV2':
        raise ValueError('package reads require the complete completion recipe')
    result=copy.deepcopy(profile)
    b,t,o,c,d=(contract[name] for name in ('batchLayout','transferLayout','overlappedLayout','cookieLayout','descriptorLayout'))
    entries={g['key']:g['entryRva'] for g in contract['nativeGroups']}
    def field(name,kind,arg,offset,chain=(),guard=None,argument=None):
        value={'name':name,'kind':kind,'argIndex':arg,'offset':offset}
        if chain: value['pointerOffsets']=list(chain)
        if guard: value['requireMemory']={'name':guard,'nonzero':True}
        if argument: value['requireArgument']={'name':argument,'nonzero':True}
        return value
    descriptor_fields=(('descriptorByteLength','u64','byteLength'),('descriptorBlockOffset','u64','blockOffset'),
        ('descriptorByteOffset','u32','byteOffset'),('descriptorKeyLow','u32','keyLow'),
        ('descriptorPackagePointer','pointer','package'),('descriptorBlockBytes','u32','blockBytes'))
    transfer_fields=(('transferFilePosition','u64','filePosition'),('transferRequestedBytes','u32','requestedBytes'),
        ('transferTransformBytes','u32','transformBytes'),('transferBufferPointer','pointer','buffer'),
        ('transferCallbackPointer','pointer','callback'),('transferCookiePointer','pointer','cookie'))
    batch=[field('ioAddressPointPointer','pointer',0,0),
           field('firstDescriptorPointer','pointer',2,b['descriptor'],argument='batchCount'),
           field('firstTransferPointer','pointer',2,b['transfer'],argument='batchCount')]
    batch.extend(field(name,kind,2,d[key],(b['descriptor'],),'firstDescriptorPointer') for name,kind,key in descriptor_fields)
    batch.append(field('descriptorFileHandle','pointer',2,contract['descriptorHandleOffset'],(b['descriptor'],),'firstDescriptorPointer'))
    batch.extend(field(name,kind,2,t[key],(b['transfer'],),'firstTransferPointer') for name,kind,key in transfer_fields)
    completion=[field('overlappedPositionLow','u32',2,o['positionLow']),field('overlappedPositionHigh','u32',2,o['positionHigh']),
                field('transferPointer','pointer',2,o['transfer'])]
    completion.extend(field(name,kind,2,t[key],(o['transfer'],),'transferPointer') for name,kind,key in transfer_fields)
    completion.append(field('cookieDescriptorPointer','pointer',2,c['descriptor'],(o['transfer'],t['cookie']),'transferCookiePointer'))
    transform=[field(name,kind,0,d[key]) for name,kind,key in descriptor_fields]
    transform.append(field('descriptorFileHandle','pointer',0,contract['descriptorHandleOffset']))
    transform.append(field('descriptorEncryptionFlagWord','u32',0,contract['transformLeaf']['encryptionFlagOffset']))
    transform.extend(field(name,kind,1,t[key]) for name,kind,key in transfer_fields)
    transform.extend((field('cookieDescriptorPointer','pointer',1,c['descriptor'],(t['cookie'],),'transferCookiePointer'),
        field('cookiePrimaryIoPointer','pointer',1,c['primaryIo'],(t['cookie'],),'transferCookiePointer'),
        field('cookiePrimaryIoAddressPointPointer','pointer',1,0,(t['cookie'],c['primaryIo']),'cookiePrimaryIoPointer'),
        field('bufferFirstWord','u32',1,0,(t['buffer'],),'transferBufferPointer')))
    for kind,entry,args,memory in (
        ('anonymousDefaultIoReadBatch',entries['defaultIoReadBatch'],{'ioContextPointer':{'index':0,'kind':'pointer'},'batchCount':{'index':1,'kind':'u32'},'batchPointer':{'index':2,'kind':'pointer'}},batch),
        ('anonymousDefaultIoReadCompletion',entries['defaultIoReadCompletion'],{'platformError':{'index':0,'kind':'u32'},'transferredBytes':{'index':1,'kind':'u32'},'overlappedPointer':{'index':2,'kind':'pointer'}},completion),
        ('anonymousPackageReadTransform',contract['transformLeaf']['entryRva'],{'descriptorPointer':{'index':0,'kind':'pointer'},'transferPointer':{'index':1,'kind':'pointer'}},transform)):
        result['nativeHooks'].append({'name':'AkSoundEngine.'+kind,'sourceKind':kind,'rva':entry,'required':True,'returnKind':'void','args':args,'memory':memory})
    result['observerProfile']='endfieldSourceIoEntryV3'
    return result


def add_transfer_receiver_entries(profile: dict, read: dict, transform: dict) -> dict:
    """Add self-contained transfer/receiver inputs from the validated companion."""
    if profile.get('observerProfile')!='endfieldSourceIoEntryV3':
        raise ValueError('transfer receiver entries require the complete read recipe')
    result=copy.deepcopy(profile)
    block,node,carrier=(transform[key] for key in ('transferBlockLayout','completionNodeLayout','bufferCarrierLayout'))
    t,c,d=(read[key] for key in ('transferLayout','cookieLayout','descriptorLayout'))
    user=block['userData']-block['transferOffset']
    groups={g['key']:g['entryRva'] for g in transform['nativeGroups']}
    def field(name,kind,arg,offset,chain=(),guard=None):
        value={'name':name,'kind':kind,'argIndex':arg,'offset':offset}
        if chain:value['pointerOffsets']=list(chain)
        if guard:value['requireMemory']={'name':guard,'nonzero':True}
        return value
    local=[field('transferUserDataPointer','pointer',1,user),
        field('transferBlockOwnerPointer','pointer',1,block['owner'],(user,),'transferUserDataPointer'),
        field('transferBlockOwnerAddressPointPointer','pointer',1,0,(user,block['owner']),'transferBlockOwnerPointer'),
        field('transferCompletionHeadPointer','pointer',1,block['completionList'],(user,),'transferUserDataPointer'),
        field('firstCompletionReceiverPointer','pointer',1,node['receiver'],(user,block['completionList']),'transferCompletionHeadPointer'),
        field('firstCompletionBufferCarrierPointer','pointer',1,node['bufferCarrier'],(user,block['completionList']),'transferCompletionHeadPointer')]
    leaf=next(h for h in result['nativeHooks'] if h['sourceKind']=='anonymousPackageReadTransform')
    leaf['memory'].extend(local)
    dispatch=[]
    for name,kind,key in (('transferFilePosition','u64','filePosition'),('transferRequestedBytes','u32','requestedBytes'),
        ('transferTransformBytes','u32','transformBytes'),('transferBufferPointer','pointer','buffer'),
        ('transferCallbackPointer','pointer','callback'),('transferCookiePointer','pointer','cookie')):
        dispatch.append(field(name,kind,0,t[key]))
    dispatch.extend({**copy.deepcopy(value),'argIndex':0} for value in local)
    dispatch.extend([field('cookieDescriptorPointer','pointer',0,c['descriptor'],(t['cookie'],),'transferCookiePointer'),
        field('cookiePrimaryIoPointer','pointer',0,c['primaryIo'],(t['cookie'],),'transferCookiePointer'),
        field('cookiePrimaryIoAddressPointPointer','pointer',0,0,(t['cookie'],c['primaryIo']),'cookiePrimaryIoPointer')])
    for name,kind,key in (('descriptorByteLength','u64','byteLength'),('descriptorBlockOffset','u64','blockOffset'),
        ('descriptorByteOffset','u32','byteOffset'),('descriptorKeyLow','u32','keyLow'),
        ('descriptorPackagePointer','pointer','package'),('descriptorBlockBytes','u32','blockBytes')):
        dispatch.append(field(name,kind,0,d[key],(t['cookie'],c['descriptor']),'cookieDescriptorPointer'))
    dispatch.extend([field('descriptorFileHandle','pointer',0,read['descriptorHandleOffset'],(t['cookie'],c['descriptor']),'cookieDescriptorPointer'),
        field('descriptorEncryptionFlagWord','u32',0,read['transformLeaf']['encryptionFlagOffset'],(t['cookie'],c['descriptor']),'cookieDescriptorPointer'),
        field('bufferFirstWord','u32',0,0,(t['buffer'],),'transferBufferPointer')])
    result['nativeHooks'].append({'name':'AkSoundEngine.anonymousTransferCompletionDispatcher','sourceKind':'anonymousTransferCompletionDispatcher',
        'rva':groups['transferCompletionDispatcher'],'required':True,'returnKind':'void',
        'args':{'transferPointer':{'index':0,'kind':'pointer'},'completionStatus':{'index':1,'kind':'u32'}},'memory':dispatch})
    for name,owner in (('anonymousPrimaryReceiverTransferCompletion','primaryProviderTransferCompletion'),
                       ('anonymousQueuedReceiverTransferCompletion','queuedReceiverTransferCompletion')):
        memory=[field('receiverAddressPointPointer','pointer',0,0),field('nodeNextPointer','pointer',1,node['next']),
            field('nodeReceiverPointer','pointer',1,node['receiver']),field('nodeStateWord','u32',1,node['state']),
            field('nodeBufferCarrierPointer','pointer',1,node['bufferCarrier']),
            field('nodeReceiverAddressPointPointer','pointer',1,0,(node['receiver'],),'nodeReceiverPointer'),
            field('carrierTransferBlockPointer','pointer',1,carrier['transferBlock'],(node['bufferCarrier'],),'nodeBufferCarrierPointer'),
            field('carrierTransferBlockOwnerPointer','pointer',1,block['owner'],(node['bufferCarrier'],carrier['transferBlock']),'carrierTransferBlockPointer')]
        for field_name,kind,key in (('carrierTransferFilePosition','u64','filePosition'),('carrierTransferRequestedBytes','u32','requestedBytes'),
            ('carrierTransferTransformBytes','u32','transformBytes'),('carrierTransferBufferPointer','pointer','buffer'),
            ('carrierTransferCallbackPointer','pointer','callback')):
            memory.append(field(field_name,kind,1,block['transferOffset']+t[key],(node['bufferCarrier'],carrier['transferBlock']),'carrierTransferBlockPointer'))
        result['nativeHooks'].append({'name':'AkSoundEngine.'+name,'sourceKind':name,'rva':groups[owner],'required':True,'returnKind':'void',
            'args':{'receiverPointer':{'index':0,'kind':'pointer'},'completionNodePointer':{'index':1,'kind':'pointer'},
                    'completionStatus':{'index':2,'kind':'u32'},'dispatchFlagRegister':{'index':3,'kind':'u32'}},'memory':memory})
    result['observerProfile']='endfieldSourceIoEntryV4'
    result['transferReceiverScope']={
        'entryOnly':'Same-entry fixed fields retain transfer user-data, block owner/address point, first completion receiver and node carrier. Dispatcher buffer word is a raw pre-dispatch DWORD; a post-transform interpretation requires the independently authenticated default-I/O and caller-path condition. It is not PCM.',
        'receiverFamilies':'Direct receiver entry arguments and address points can select the two reviewed interface families. Only the low byte of dispatchFlagRegister is a proved handler input.',
        'recycling':'Dispatcher recycles the transfer block before receiver dispatch. Carrier block fields at receiver entry are raw local observations and cannot be promoted to the original transfer identity or an allocation generation.',
        'bounded':'At most one list head is followed; no unbounded traversal, native result hook, named codec identity or decoder/provider dereference is added.'}
    return result


def project(profile: dict) -> dict:
    manifest = copy.deepcopy(profile)
    provider = "providerEntryScope" in manifest
    expanded = "providerBatchScope" in manifest
    manifest.update(schema=(PROVIDER_SCHEMA if expanded else LEGACY_PROVIDER_SCHEMA) if provider else NATIVE_SCHEMA,
                    observerProfile=("endfieldSourceProviderEntryV2" if expanded else "endfieldSourceProviderEntryV1") if provider else "endfieldSourceOwnerEntryV1")
    if profile.get("observerProfile") == "endfieldSourceIoEntryV1":
        manifest.update(schema=IO_SCHEMA, observerProfile="endfieldSourceIoEntryV1")
    elif profile.get("observerProfile") == "endfieldSourceIoEntryV2":
        manifest.update(schema=IO_RESULT_SCHEMA, observerProfile="endfieldSourceIoEntryV2")
    elif profile.get('observerProfile') == 'endfieldSourceIoEntryV3':
        manifest.update(schema=IO_READ_SCHEMA,observerProfile='endfieldSourceIoEntryV3')
    elif profile.get('observerProfile') == 'endfieldSourceIoEntryV4':
        manifest.update(schema=IO_TRANSFER_SCHEMA,observerProfile='endfieldSourceIoEntryV4')
    abis = {"AudioAdapter._PostEventWithExternalSource": "win64.il2cpp_post_event_external_source.v2",
            "AudioAdapter._PostEvent": "win64.il2cpp_post_event.v2"}
    if manifest['schema']==IO_TRANSFER_SCHEMA:
        abis['AudioAdapter._PostEventWithExternalSource']='win64.il2cpp_post_event_external_source.v3'
        manifest['managedResultScalarFacts']={'externalCookie':'pointerFact0','rawBeyondCodecArgument':'pointerFact1',
            'boundary':'Only the selected external-post result ABI retains these original scalar arguments; no Wwise codec identity or asynchronous ownership follows.'}
    if {hook["name"] for hook in manifest["hooks"]} != set(abis):
        raise ValueError("expected both exact managed post ABIs")
    for hook in manifest["hooks"]:
        hook.update(module="GameAssembly.dll", abiId=abis[hook["name"]])
    for hook in manifest["nativeHooks"]:
        program, fields = read_program(hook)
        hook.update(module="AkSoundEngine.dll", abiId=ABI, readProgram=program, memory=fields,
                    observationPhase="entryOnly")
    manifest["captureBoundary"] = (
        "Entry-only fixed-field observations with preserved original registers, stack arguments and return address. "
        "No native result, synchronous parent nesting, atomic snapshot, pointer generation or lifetime is observed. "
        "One descriptor is read only when the allocation count is exactly one; text is bounded to 160 UTF-16 units "
        "and must terminate. Owner/carrier reads never dereference text or media bytes."
    )
    if manifest["schema"] in (IO_SCHEMA, IO_RESULT_SCHEMA, IO_READ_SCHEMA, IO_TRANSFER_SCHEMA):
        manifest["captureBoundary"] += " Retained provider descriptors, device I/O fields and external-package path/key inputs are separate local reads; no returned lookup row or file/decode result is observed."
        if manifest["schema"] in (IO_RESULT_SCHEMA,IO_READ_SCHEMA,IO_TRANSFER_SCHEMA):
            manifest["captureBoundary"] += " The package completion entry additionally samples its existing request/result descriptor before release; status and local pointers do not establish media reads, decoding or audibility."
        if manifest['schema'] in (IO_READ_SCHEMA,IO_TRANSFER_SCHEMA):
            manifest['captureBoundary'] += ' Read entries additionally sample the first batch record, platform completion arguments and local descriptor/transfer fields before buffer transformation. One guarded buffer DWORD is sampled; no full payload, PCM, pointer lifetime or audibility is established.'
        if manifest['schema']==IO_TRANSFER_SCHEMA:
            manifest['captureBoundary'] += ' Transfer and receiver entries additionally retain bounded local user-data, owner/address-point, node receiver/address-point and carrier fields. Dispatcher recycles its block before receiver dispatch, so later carrier block fields do not establish the original transfer or an allocation generation.'
    return manifest

