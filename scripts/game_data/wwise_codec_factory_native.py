"""Authenticate selected source-kind/plugin factory and codec construction bytes.

This is an installed-format native validator, not a live decoder or WebUI builder.
It accepts only an explicit selected binary triplet and preserves registration,
provider/header, initialization and output conditions separately.

Evidence and admission boundary:

The independently owned codec factory contract
(`wwise_codec_factory_native.json`) and validator
(`wwise_codec_factory_native.py`) now authenticate the owner-held source read,
source-kind extraction, full plugin-ID dispatch, static codec registration,
wrapper construction and codec activation. The registry scans complete plugin
keys in stored order. An earlier matching registration wins without replacing
its factory pointers; source kind selects one of the retained factory slots. A
separate built-in branch and a fallback header branch remain explicit,
including the latter's ability to change the source argument or kind before
dispatch.

The selected authored Vorbis and Opus raw arguments register the same
media-source wrapper factory shape with distinct codec instance factories. Both
constructors retain the same primary owner and install the same wrapper address
point. The wrapper stores its codec factory separately; preparation later calls
it, stores the constructed codec instance and invokes that instance's
initialization slot. These codec instances have distinct address points. This
closes a conditional implementation route and distinguishes it from the
separately instrumented streamed-file preparation family. It does not identify
a saved live voice's allocation or prove singleton/registry stability. Raw
arguments remain separate from managed enum labels.

Original selected initialization bytes consume authenticated format prefixes
from the same external and numeric WEM witnesses. Their rate, channel and
sample-count metadata agree with the existing offline PCM receipts. Wrong
format tags and sizes take distinct original failure paths without writing that
metadata. Format output remains separate from sample output.

The media wrapper's preparation caller reaches the original RIFF-prefix reader.
It returns format, encoded-data, loop, auxiliary and seek views and can succeed
at a data header before its payload is available. It does not enforce the RIFF
declared whole-file length. First format wins, odd-chunk padding is conditional
on a readable zero byte, and a legacy channel branch can rewrite the supplied
format bytes. Readable chunk substructures and provider lifetime remain
separate conditions; this is not a safe arbitrary RIFF decoder. The selected
physical WEMs also pass this original reader.

A selected Opus WEM now follows that native RIFF reader, the complete original
codec initializer, packet collection, original Opus sample computation and
planar sample writes. The whole media wrapper returns the same sample buffers
and advances its cursor through pre-skip and final trim to the stored frame
count. The independently decoded reference agrees in frame geometry, and every
sample is within one signed-16-bit quantization step. This is an offline native
PCM witness, with explicit resident input, owner/descriptor state, allocations,
byte copies and emulated CPU/thread storage. Independent execution in an
isolated helper, using the selected DLL's normal Windows loader/CRT
initialization, returns exactly the same float samples and wrapper buffers.
Only helper-process allocation/free entry points are replaced and an available
setup-cache lock is initialized. Platform models calculate no sample values.
WAV packaging performs a separately declared float-to-integer conversion; it is
not device output or byte-identical decoder equality.

The same contract joins media preparation's embedded-owner adjustment and
resident pointer/count reads to the existing source LockDataPtr consumer and
media-reference layout. This is an authenticated storage join, rather than an
offset inferred from proximity. For selected direct numeric Events, original
source read/set and exact-key registry lookup now feed whole native
preparation, RIFF parsing, codec construction/setup and sample-wrapper output
on the host CPU. The registry rows hold independently authenticated physical
package entries. Original readable-row admission now constructs those entries
and their buffer records through native exact-key hash insertion, retaining the
supplied media pointer/count without copying or decoding its bytes. Available
table capacity, typed input lifetime, owner readiness and provider interfaces
remain conditions: the readiness replacement invokes the original lookup with
the checked consumer arguments, without executing complete owner preparation.
Starting with an empty reference, a wrong-key registry collision leaves no
resident pointer and preparation stops before creating a codec. This does not
generalize to early-return paths retaining an existing reference.

The same admission code rejects null/empty payloads and unwinds a successful
prefix after a later invalid row or allocation failure in bounded native
cohorts. Duplicate IDs prepend buffer records to the shared entry. Among the
eligible positive-length rows tested, source lookup chooses the greatest byte
count; equal-size ties select the first list occurrence, which is the latest
admitted row in that cohort. Preserve row identity and actual selected bytes:
this is neither package/language precedence nor a unique filename from an ID.

The selected memory-labelled sources take the resident-memory provider branch.
It passes the acquired pointer/count to the provider; it does not request a
numeric filename at that slot. Their WEMs nevertheless come from a separate
sound package. Successful preparation advances the input view past RIFF and
Vorbis setup before sample processing. The whole wrapper returns finite samples
through the stored end frame and produces playable offline WAVs. Physical
bank/source identity joins these witnesses to the earlier Event and Action
execution cohorts; separate cohorts do not establish one live pointer
generation or actual package callback/API selection.

The node preparation slot now closes a stronger conditional population path. It
addresses the same embedded source as the checked bank loader and node-play
wrapper, then forwards that source to original resident preparation. The
manager either prepares immediately or collects complete source records for a
later drain. Deferred records are ordered and reused by their file-ID word;
equal-key records are overwritten, so this collection is not a distinct list of
every source registration. The native source record carries the registry ID,
numeric file ID, requested byte count, language flag and plugin codec into the
file-open request. Keep registry identity and file identity distinct even when
a selected physical source repeats the same value in both words.

Original numeric stream open/setup/read/close, resident allocation and buffer
publication now execute before native source lookup, whole preparation and
context PCM. The supplied stream-manager interface observes that original
request and selects an independently authenticated physical package occurrence;
it copies the clear WEM into the original allocation. The later memory-provider
branch consumes those allocated/read bytes. Immediate and deferred preparation
return exactly the earlier native floats for the checked source, and selected
numeric Events preserve their complete PCM through the context consumer. Open
failure, a partial read followed by EOF, and read error leave no resident bytes
for the source lookup. The original reader attempts the remaining bytes before
rejecting incomplete input. Existing prepared buffers, alternate buffer kinds,
source counter lifetime, wider rollback and allocation reuse remain distinct
branches. Readable node storage, manager capacity/collection state, package
selection, provider interfaces and pointer generations remain conditions. This
narrows the missing join to the game's actual package/provider choice and live
ownership; it does not establish a continuously observed Event generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data import wwise_source_native as source_native
from scripts.game_data.wwise_source_provider_dispatch_native import load_dispatch_contract
from scripts.game_data.wwise_source_native import SourceContractError, _collect_source_image
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_declarations,
    validate_native_group_windows, validate_opened_managed_inputs,
)

CONTRACT_PATH = CONTRACTS_DIR / "wwise_codec_factory_native.json"
SCHEMA = "endfield.wwise-codec-factory-native.v4"


def _fail(check: str, subject: str, expected: Any, actual: Any) -> None:
    raise SourceContractError(check, subject, expected, actual)


def _rows(value: Any, subject: str, maximum: int) -> list[dict]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum or any(not isinstance(row, dict) for row in value):
        _fail("codecDeclarationRows", subject, f"1..{maximum} objects", type(value).__name__)
    return value


def load_codec_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-codec-factory")
    return contract


def _witness(groups: dict, group: Any, role: Any) -> dict:
    owner = groups.get(group) if isinstance(group, str) else None
    found = next((row for row in owner["instructionWitnesses"] if row["role"] == role), None) if owner else None
    if found is None:
        _fail("codecNamedWitness", str(group), "named authenticated group instruction", role)
    return found


def _codec_groups(contract: dict, dependency_contract: dict | None = None) -> list[dict]:
    """Reuse the source-provider owner's declaration without a second catalog."""
    groups = list(contract["nativeGroups"])
    dependencies = contract.get("nativeGroupDependencies", [])
    if dependencies == []:
        return groups
    for row in _rows(dependencies, "nativeGroupDependencies", 1):
        if (set(row) != {"key", "ownerContract", "ownerGroup"}
                or row["ownerContract"] != "wwise_source_provider_dispatch_native"
                or row["ownerGroup"] != "anonymousSourceProviderPreparation"
                or not isinstance(row["key"], str) or not row["key"]):
            _fail("codecGroupDependency", "nativeGroupDependencies", "named source-provider owner/group", row)
        owner = dependency_contract if dependency_contract is not None else load_dispatch_contract()
        if owner.get("nativeInputs") != contract["nativeInputs"]:
            _fail("codecGroupDependencyInputs", row["key"], "same selected native triplet", "different declarations")
        group = next((value for value in owner.get("nativeGroups", []) if value.get("key") == row["ownerGroup"]), None)
        if group is None:
            _fail("codecGroupDependencyMissing", row["key"], row["ownerGroup"], "missing owner group")
        groups.append({**group, "key": row["key"]})
    validate_native_group_declarations(groups)
    return groups


def validate_codec_declarations(contract: dict, *, dependency_contract: dict | None = None) -> None:
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        _fail("codecSchema", "contract", SCHEMA, contract.get("schema"))
    inputs = contract.get("nativeInputs", {})
    for name in ("gameAssemblySha256", "globalMetadataSha256", "akSoundEngineSha256"):
        _digest(inputs.get(name), name)
    size = inputs.get("akSoundEngineFileSize")
    if type(size) is not int or not 0 < size <= 256 * 1024 * 1024:
        _fail("codecInputSize", "nativeInputs", "bounded positive size", size)
    validate_native_group_declarations(contract.get("nativeGroups"))
    groups = {row["key"]: row for row in _codec_groups(contract, dependency_contract)}
    windows = {}
    for window in _rows(contract.get("dataWindows"), "dataWindows", 32):
        key = window.get("key")
        if not isinstance(key, str) or not key or key in windows:
            _fail("codecDataKey", "dataWindows", "unique nonempty key", key)
        windows[key] = window
        _rva(window.get("rva"), key); _digest(window.get("sha256"), key)
        if type(window.get("bytes")) is not int or not 1 <= window["bytes"] <= 4096:
            _fail("codecDataExtent", key, "1..4096 bytes", window.get("bytes"))
    for edge in _rows(contract.get("directEdges"), "directEdges", 64):
        witness = _witness(groups, edge.get("group"), edge.get("witnessRole"))
        encoded = bytes.fromhex(witness["instructionHex"])
        name, kind = edge.get("targetGroup"), edge.get("kind")
        target = groups.get(name) if isinstance(name, str) else None
        opcode = {"call": b"\xe8", "tailJump": b"\xe9"}.get(kind) if isinstance(kind, str) else None
        actual = int(witness["rva"], 16) + 5 + struct.unpack_from("<i", encoded, 1)[0] if len(encoded) == 5 else None
        if target is None or opcode is None or encoded[:1] != opcode or actual != int(target["entryRva"], 16):
            _fail("codecDirectEdge", witness["role"], name, actual)
    seen = set()
    for row in _rows(contract.get("initializedCodecs"), "initializedCodecs", 32):
        codec, company, kind = row.get("codecId"), row.get("companyId"), row.get("kind")
        if (type(codec) is not int or not 0 <= codec <= 0xffff or type(company) is not int or not 0 <= company <= 0xfff
                or type(kind) is not int or not 0 <= kind <= 255 or (codec, company) in seen):
            _fail("codecRegistrationWords", "initializedCodecs", "distinct bounded codec/company and kind", row)
        seen.add((codec, company)); _rva(row.get("recordRva"), "codecRecord")
        for field in ("initializerGroup", "factoryGroup", "instanceFactoryGroup", "sampleGroup"):
            if not isinstance(row.get(field), str) or row[field] not in groups:
                _fail("codecRegistrationGroup", field, "named authenticated group", row.get(field))
        for field, length in (("headerWindow", 16), ("factoryWindow", 32)):
            key = row.get(field)
            if not isinstance(key, str) or key not in windows or windows[key]["bytes"] != length:
                _fail("codecRegistrationData", field, f"named {length}-byte window", key)
        if int(windows[row["headerWindow"]]["rva"], 16) != int(row["recordRva"], 16) + 8:
            _fail("codecRegistrationHeader", str(codec), "record header after next pointer", row)
    for binding in _rows(contract.get("addressPointBindings"), "addressPointBindings", 16):
        key, target, slot = binding.get("dataWindow"), binding.get("targetGroup"), binding.get("slot")
        if (not isinstance(key, str) or key not in windows or not isinstance(target, str) or target not in groups
                or type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > windows[key]["bytes"]):
            _fail("codecAddressPointBinding", "addressPointBindings", "bounded slot and named group/window", binding)
    dependency = contract.get("sourceOwnerDependency")
    if not isinstance(dependency, dict) or not isinstance(dependency.get("ownerTransportKey"), str):
        _fail("codecSourceDependency", "contract", "named existing source owner transport", dependency)
    binding = dependency.get("sourcePointerWitness")
    if not isinstance(binding, dict):
        _fail("codecSourcePointerBinding", "contract", "named source load witness", binding)
    _witness(groups, binding.get("group"), binding.get("role")); _hex(binding.get("prefixHex"), "sourcePointer", 10)
    resident_fields = set()
    for binding in _rows(dependency.get("residentOwnerReadBindings"), "residentOwnerReadBindings", 3):
        name = binding.get("field")
        if (name not in ("embeddedOwner", "residentData", "residentByteCount") or name in resident_fields
                or type(binding.get("operandBytes")) is not int or binding["operandBytes"] not in (1, 4)):
            _fail("codecResidentBinding", "source dependency", "distinct named owner read with disp8/disp32", binding)
        resident_fields.add(name)
        _witness(groups, binding.get("group"), binding.get("role")); _hex(binding.get("prefixHex"), name, 10)
    if resident_fields != {"embeddedOwner", "residentData", "residentByteCount"}:
        _fail("codecResidentBindingCoverage", "source dependency", "three owner reads", sorted(resident_fields))
    sample_fields = set()
    for field in _rows(contract.get("sampleBufferFields"), "sampleBufferFields", 24):
        subject = field.get("name")
        if (not isinstance(subject, str) or not subject or not isinstance(field.get("structure"), str) or not field["structure"]
                or type(field.get("offset")) is not int or not 0 <= field["offset"] <= 127
                or type(field.get("bytes")) is not int or field["bytes"] not in (2, 4, 8)):
            _fail("codecSampleField", "sampleBufferFields", "named disp8 field with scalar width", field)
        witness = _witness(groups, field.get("group"), field.get("role"))
        prefix = _hex(field.get("operandPrefixHex"), subject, 10)
        identity = (field["structure"], subject)
        if identity in sample_fields:
            _fail("codecSampleFieldDuplicate", subject, "unique structure/field", identity)
        sample_fields.add(identity)
        operand_width = 2 if prefix[0] == 0x66 else 8 if 0x48 <= prefix[0] <= 0x4f else 4
        if field["bytes"] != operand_width:
            _fail("codecSampleFieldWidth", subject, operand_width, field["bytes"])
        suffix = _hex(field["operandSuffixHex"], subject, 8) if "operandSuffixHex" in field else b""
        expected = prefix + bytes((field["offset"],)) + suffix
        if bytes.fromhex(witness["instructionHex"]) != expected:
            _fail("codecSampleFieldOperand", subject, expected.hex(), witness["instructionHex"])
    dispatch = contract.get("sampleDispatch")
    if not isinstance(dispatch, dict) or type(dispatch.get("slot")) is not int or not 0 <= dispatch["slot"] <= 127 or dispatch["slot"] % 8:
        _fail("codecSampleDispatch", "sampleDispatch", "bounded virtual slot", dispatch)
    witness = _witness(groups, dispatch.get("group"), dispatch.get("role"))
    expected = _hex(dispatch.get("instructionPrefixHex"), "sampleDispatch", 8) + bytes((dispatch["slot"],))
    if bytes.fromhex(witness["instructionHex"]) != expected:
        _fail("codecSampleDispatchOperand", "sampleDispatch", expected.hex(), witness["instructionHex"])
    for row in contract["initializedCodecs"]:
        key = row.get("sampleAddressPoint")
        if (not isinstance(key, str) or key not in windows or not any(
                binding["dataWindow"] == key and binding["slot"] == dispatch["slot"] and binding["targetGroup"] == row["sampleGroup"]
                for binding in contract["addressPointBindings"])):
            _fail("codecSampleDispatchBinding", str(row["codecId"]), "checked codec sample slot/address point", key)


def validate_codec_bytes(contract: dict, image: Any, bodies: dict, records: dict, source: dict,
                         *, dependency_contract: dict | None = None) -> None:
    dependency_groups = _codec_groups(contract, dependency_contract)
    validate_codec_declarations(contract, dependency_contract=dependency_contract)
    if contract["nativeInputs"] != source["nativeInputs"]:
        _fail("codecSourceInputs", "source dependency", "same selected native triplet", "different declarations")
    dependency = contract["sourceOwnerDependency"]
    owner = next((row for row in source["ownerTransports"] if row["key"] == dependency["ownerTransportKey"]), None)
    if owner is None:
        _fail("codecSourceOwner", "source dependency", "existing owner transport", dependency["ownerTransportKey"])
    groups = {row["key"]: row for row in contract["nativeGroups"]}
    binding = dependency["sourcePointerWitness"]
    witness = _witness(groups, binding["group"], binding["role"])
    expected = bytes.fromhex(binding["prefixHex"]) + struct.pack("<I", owner["primarySourcePointerOffset"])
    if bytes.fromhex(witness["instructionHex"]) != expected:
        _fail("codecSourcePointerOffset", witness["role"], expected.hex(), witness["instructionHex"])
    consumer = next((row for row in source.get("consumers", []) if row["key"] == owner.get("consumerKey")), None)
    if consumer is None:
        _fail("codecResidentConsumer", "source dependency", "owner's checked LockDataPtr consumer", owner.get("consumerKey"))
    output = consumer["outputReference"]
    fields = {field["name"]: field["offset"] for field in source["structures"][output["structure"]]["fields"]}
    offsets = {"embeddedOwner": owner["consumerOwnerOffset"],
               "residentData": owner["consumerOwnerOffset"] + output["offset"] + fields["mediaRefDataPointer"],
               "residentByteCount": owner["consumerOwnerOffset"] + output["offset"] + fields["mediaRefByteCount"]}
    for binding in dependency["residentOwnerReadBindings"]:
        witness = _witness(groups, binding["group"], binding["role"])
        offset, width = offsets[binding["field"]], binding["operandBytes"]
        if type(offset) is not int or not 0 <= offset < 1 << (8 * width):
            _fail("codecResidentOffsetWidth", binding["field"], "offset fitting checked displacement", offset)
        expected = bytes.fromhex(binding["prefixHex"]) + offset.to_bytes(width, "little")
        if bytes.fromhex(witness["instructionHex"]) != expected:
            _fail("codecResidentOwnerOffset", binding["field"], expected.hex(), witness["instructionHex"])
    validate_native_group_windows(dependency_groups, image, bodies, records)
    raw_windows = {}
    for window in contract["dataWindows"]:
        raw = image.bytes_at_va(image.image_base + int(window["rva"], 16), window["bytes"])
        actual = hashlib.sha256(raw).hexdigest()
        if len(raw) != window["bytes"] or actual != window["sha256"].casefold():
            _fail("codecDataSha256", window["key"], window["sha256"], actual)
        raw_windows[window["key"]] = raw
    for row in contract["initializedCodecs"]:
        raw = raw_windows[row["headerWindow"]]
        actual = (raw[0], struct.unpack_from("<I", raw, 4)[0], struct.unpack_from("<I", raw, 8)[0])
        expected = (row["kind"], row["companyId"], row["codecId"])
        if actual != expected:
            _fail("codecStaticRecordWords", str(row["codecId"]), expected, actual)
        factories = struct.unpack_from("<QQ", raw_windows[row["factoryWindow"]])
        target = image.image_base + int(groups[row["factoryGroup"]]["entryRva"], 16)
        if factories != (target, target):
            _fail("codecStaticFactoryPair", str(row["codecId"]), hex(target), [hex(at) for at in factories])
        witness = _witness(groups, row["factoryGroup"], "loadCodecInstanceFactory")
        encoded = bytes.fromhex(witness["instructionHex"])
        actual = int(witness["rva"], 16) + 7 + struct.unpack_from("<i", encoded, 3)[0] if len(encoded) == 7 and encoded[:3] == b"\x4c\x8d\x05" else None
        expected = int(groups[row["instanceFactoryGroup"]]["entryRva"], 16)
        if actual != expected:
            _fail("codecInstanceFactoryAddress", str(row["codecId"]), hex(expected), actual)
    for binding in contract["addressPointBindings"]:
        actual = struct.unpack_from("<Q", raw_windows[binding["dataWindow"]], binding["slot"])[0]
        expected = image.image_base + int(groups[binding["targetGroup"]]["entryRva"], 16)
        if actual != expected:
            _fail("codecAddressPointTarget", binding["dataWindow"], hex(expected), hex(actual))


def load_validated_codec_contract(*, gameassembly: Path, metadata: Path, ak_sound_engine: Path,
                                  contract_path: Path = CONTRACT_PATH,
                                  include_voice_pipeline: bool = False,
                                  include_voice_routing: bool = False,
                                  include_sink_negotiation: bool = False,
                                  include_authored_parameters: bool = False,
                                  include_inheritance: bool = False) -> tuple[dict | None, dict]:
    audit = {"status": "missing", "contractPath": str(contract_path), "detail": ""}
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        audit.update(detail="three explicit selected native paths are required", diagnostic={"failedCheck": "selectedInputs", "actual": "missing path"})
        return None, audit
    try:
        contract = load_codec_contract(contract_path)
        dependency_contract = load_dispatch_contract() if contract.get("nativeGroupDependencies") else None
        validate_codec_declarations(contract, dependency_contract=dependency_contract)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["globalMetadataSha256"], gameassembly=gameassembly, metadata=metadata, require_metadata=True)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != "validated":
            return None, audit
        if not ak_sound_engine.is_file():
            audit.update(status="missing", detail=f"selected AkSoundEngine.dll not found: {ak_sound_engine}")
            return None, audit
        size, digest = ak_sound_engine.stat().st_size, sha256_file(ak_sound_engine)
        if size != inputs["akSoundEngineFileSize"] or digest.casefold() != inputs["akSoundEngineSha256"].casefold():
            _fail("codecAkSoundEngineInput", str(ak_sound_engine), f"{inputs['akSoundEngineFileSize']}/{inputs['akSoundEngineSha256']}", f"{size}/{digest}")
        managed = NativeImage(gameassembly, metadata, label="wwise-codec-factory")
        validate_opened_managed_inputs(contract, managed)
        image, bodies, records = _collect_source_image(ak_sound_engine, managed.mapper)
        if hashlib.sha256(image.buf).hexdigest() != inputs["akSoundEngineSha256"].casefold():
            _fail("codecOpenedInput", str(ak_sound_engine), inputs["akSoundEngineSha256"], hashlib.sha256(image.buf).hexdigest())
        source = source_native.load_source_contract()
        source_native.validate_source_contract(source)
        source_native.validate_source_bodies(source, bodies)
        source_native.validate_source_consumers(source, image, records)
        source_native.validate_source_transports(source, image, bodies)
        validate_codec_bytes(contract, image, bodies, records, source, dependency_contract=dependency_contract)
        audit.update(status="validated", nativeGroups=len(contract["nativeGroups"])+len(contract.get("nativeGroupDependencies", [])),
                     ownedNativeGroups=len(contract["nativeGroups"]), nativeGroupDependencies=contract.get("nativeGroupDependencies", []),
                     initializedCodecs=[row["codecId"] for row in contract["initializedCodecs"]],
                     detail="selected source/plugin registry, codec construction, initialization and native sample-buffer interfaces validated; live output unresolved",
                     evidenceBoundary=contract["evidenceBoundary"])
        if include_voice_pipeline or include_voice_routing or include_sink_negotiation or include_authored_parameters or include_inheritance:
            child_options = {}
            if include_voice_routing:
                child_options["include_routing"] = True
            if include_sink_negotiation:
                child_options["include_sink_negotiation"] = True
            if include_authored_parameters:
                child_options["include_authored_parameters"] = True
            if include_inheritance:
                child_options["include_inheritance"] = True
            audit["voicePipelineGate"] = validate_optional_voice_pipeline(image, bodies, records, contract, source, **child_options)
            if audit["voicePipelineGate"]["status"] != "validated":
                audit.update(status=audit["voicePipelineGate"]["status"], detail=audit["voicePipelineGate"]["detail"])
                return None, audit
        return contract, audit
    except SourceContractError as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic=error.diagnostic)
    except FileNotFoundError as error:
        audit.update(status="missing", detail=str(error)[:320])
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic={"failedCheck": "codecFactoryContract", "actual": str(error)[:160]})
    return None, audit


def validate_optional_voice_pipeline(image, bodies, records, parent, source, *, include_routing=False, include_sink_negotiation=False, include_authored_parameters=False, include_inheritance=False):
    from scripts.game_data import wwise_voice_pipeline_native as voice
    try:
        contract = voice.load_voice_pipeline_contract()
        voice.validate_voice_pipeline_bytes(contract, image, bodies, records, parent, source)
        audit = {"status": "validated", "detail": "conditional owner/admission, PCM routing, bus sum and render-buffer submission stages validated",
                "selectedContractSchema": contract["schema"], "ownedNativeGroups": len(contract["nativeGroups"]),
                "nativeGroups": len(contract["nativeGroups"]) + len(contract["nativeGroupDependencies"]),
                "nativeGroupDependencies": contract["nativeGroupDependencies"], "evidenceBoundary": contract["evidenceBoundary"]}
        if include_routing or include_authored_parameters or include_inheritance:
            from scripts.game_data.wwise_voice_routing_native import validate_optional_voice_routing
            if include_authored_parameters or include_inheritance:
                from scripts.game_data.wwise_voice_routing_native import load_voice_routing_contract, validate_voice_routing_bytes
                routing_contract = load_voice_routing_contract()
                validate_voice_routing_bytes(routing_contract, image, bodies, records, contract)
                # Reuse the checked declarations for the authored-parameter child.
                audit["voiceRoutingGate"] = {"status": "validated", "detail": "conditional native route creation, bus admission/mix and frame reset validated",
                    "selectedContractSchema": routing_contract["schema"], "ownedNativeGroups": len(routing_contract["nativeGroups"]),
                    "nativeGroups": len(routing_contract["nativeGroups"]) + len(routing_contract["nativeGroupDependencies"]),
                    "nativeGroupDependencies": routing_contract["nativeGroupDependencies"], "evidenceBoundary": routing_contract["evidenceBoundary"]}
            else:
                audit["voiceRoutingGate"] = validate_optional_voice_routing(image, bodies, records, contract)
            if audit["voiceRoutingGate"]["status"] != "validated":
                child = audit["voiceRoutingGate"]
                return {"status": child["status"], "detail": child["detail"], "voiceRoutingGate": child}
        if include_authored_parameters or include_inheritance:
            from scripts.game_data.wwise_authored_parameters_native import validate_optional_authored_parameters
            from scripts.game_data.wwise_source_queue_native import load_queue_contract
            audit["authoredParametersGate"] = validate_optional_authored_parameters(image, bodies, records, contract, load_queue_contract(), routing_contract)
            if audit["authoredParametersGate"]["status"] != "validated":
                child = audit["authoredParametersGate"]
                return {"status": child["status"], "detail": child["detail"], "authoredParametersGate": child}
        if include_inheritance:
            from scripts.game_data.wwise_authored_parameters_native import load_authored_parameters_contract
            from scripts.game_data.wwise_inheritance_native import validate_optional_inheritance
            audit["inheritanceGate"] = validate_optional_inheritance(image, bodies, records, load_authored_parameters_contract(), load_queue_contract())
            if audit["inheritanceGate"]["status"] != "validated":
                child = audit["inheritanceGate"]
                return {"status": child["status"], "detail": child["detail"], "inheritanceGate": child}
        if include_sink_negotiation:
            from scripts.game_data.wwise_sink_negotiation_native import validate_optional_sink_negotiation
            audit["sinkNegotiationGate"] = validate_optional_sink_negotiation(image, bodies, records, contract)
            if audit["sinkNegotiationGate"]["status"] != "validated":
                child = audit["sinkNegotiationGate"]
                return {"status": child["status"], "detail": child["detail"], "sinkNegotiationGate": child}
        return audit
    except SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": {"failedCheck": "voicePipeline", "actual": str(error)[:160]}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--ak-sound-engine", required=True, type=Path)
    parser.add_argument("--include-voice-pipeline", action="store_true", help="also authenticate owner/admission, PCM routing, bus mixing and render-buffer submission on the same selected image")
    parser.add_argument("--include-voice-routing", action="store_true", help="also authenticate the voice pipeline and native route creation, bus admission/mix and frame reset on the same selected image")
    parser.add_argument("--include-sink-negotiation", action="store_true", help="also authenticate the voice pipeline and native sink format/service negotiation on the same selected image; never activates an audio endpoint")
    parser.add_argument("--include-authored-parameters", action="store_true", help="also authenticate the voice pipeline, routing and authored Sound parameter/filter/gain consumers on the same selected image; never changes engine state")
    parser.add_argument("--include-inheritance", action="store_true", help="also authenticate hierarchy/STMG/default-parameter consumers and their voice/authored/routing dependencies on the same image; never changes engine state")
    args = parser.parse_args()
    _, audit = load_validated_codec_contract(gameassembly=args.gameassembly, metadata=args.metadata, ak_sound_engine=args.ak_sound_engine,
                                           include_voice_pipeline=args.include_voice_pipeline, include_voice_routing=args.include_voice_routing,
                                           include_sink_negotiation=args.include_sink_negotiation,
                                           include_authored_parameters=args.include_authored_parameters,
                                           include_inheritance=args.include_inheritance)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
