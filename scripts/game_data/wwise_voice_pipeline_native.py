"""Authenticate owner/admission, PCM routing, mixing and sink submission stages.

The codec gate supplies its already opened selected native image. This validator
does not construct an owner, decode samples, initialize a device or publish data.

Evidence and admission boundary:

The original source-attachment routine now stores the same wrapper in an active
playback context and that context on its primary owner. Original resident
readiness and virtual preparation set the wrapper's prepared flag. The whole
active-context sample consumer uses the native initialized frame quantum and
returns exactly the direct prepared-wrapper float bytes through the final
frame. This closes a conditional downstream PCM transfer: voice admission is
disabled for the offline cohort, prior transition state is empty, and no
pending source or optional sample processor is present. Original failure,
transition, cleanup and processing branches retain separate boundaries. The
context sample buffer alone still does not establish mixer routing or device
output.

The stronger owner/frame/output lane is reviewed in
`wwise_voice_pipeline_native.json` and authenticated by the codec gate's
optional voice-pipeline check on the same opened image. It reuses the existing
source owner and codec groups. The earlier helper called an embedded
parameter-refresh interface "owner readiness"; that method refreshes playback
parameters and its caller ignores the return value. Resident-reference
readiness, codec preparation, policy admission and frame readiness are separate
checks. Original parameter refresh now executes with authored parameter
collection excluded by a supplied stored flag. This removes the owner callback
from the admitted cohort without proving the game's authored owner setup.

The complete cohort also executes the original primary and embedded owner
constructors. They retain the same physical bank source and supplied node,
initialize gain/rate/control defaults, and acquire the supplied object's and
node's references. The primary constructor remains owned by the source
transport contract; the voice-pipeline validator checks its direct call into
the embedded constructor without copying that catalog. Opaque
object/play-parameter storage and the constructor input that excludes authored
collection remain supplied. Constructor execution removes hand-written owner
defaults from the output witness; it does not identify a live posted object's
generation or prove authored parameter/effect values.

Original attachment with admission enabled reads inherited or cached policy,
evaluates effective gain when required, and applies a strict frame-counter
comparison against the native look-ahead limit. The boundary immediately below
the limit admits; equality keeps a prepared wrapper attached but returns not
ready. Under supplied silent parameter state, one policy rejects and cleans up
the wrapper, while another returns success with an attached **unprepared**
wrapper. Attachment success therefore does not imply media preparation or PCM.
Policy-node inputs and the initial frame counter are explicit conditions;
authored policy, stealing/virtualization and route ownership remain separate.

Original context construction/start initializes an optional frame processor,
retains the codec's packed format, and allocates native filter history. The
original worker consumes the context descriptor, then frame publication stores
that exact descriptor in routing records. A codec block is not yet a device
frame: raw blocks can have variable capacities, and the channel configuration
and requested output capacity must be populated. Whole native frame preparation
first executed with an empty route list: it publishes those descriptor fields
from the retained format and native quantum and returns an admitted result. The
stronger route cohort below also executes nonempty preparation. Worker
scheduling and the authored bus selection remain supplied. Clearing beyond the
descriptor can erase retained context fields; requesting a larger capacity than
the native output allocation is not an admitted ABI. Neither invalid helper
state establishes a game defect.

At matching source/engine rates and zero pitch, the original initialized frame
converter assembles those blocks into the native output quantum. Frame
preparation corrects a nonnegative initial frame counter by the native frame
amount before the first sample. The complete prepared cohort emits exactly the
prior native decoded PCM, with final zero padding. A separate cohort that omits
frame preparation emits a quantum of leading silence from the converter's
initial-offset calculation; it is not an unavoidable playback delay. The
original frame release must run after consumption: omitting it replays the
cached output instead of advancing the decoder. The current cohort executes
that release, native planar tail padding and initialized filter-bypass/history
methods. This proves frame assembly and buffer lifetime within the isolated
loop, not the game's concurrent lifetime or varying pitch/rate/effect paths.

In the earlier output cohort, the same processed allocation reaches original
master-bus/output-consumer methods through a supplied single-input bus
topology. Original sink input and channel dispatch interleave the planar float
channels, and original frame-end submission obtains a render buffer, copies the
prepared float span and releases it. Complete emitted frames, the decoded
suffix and final zero padding are checked independently. A separate native
bus-row traversal/constant-gain kernel sums two actual decoded frames with
supplied routing records and gains. The render interface is identified by the
binary service IID and the local Windows SDK's `IAudioRenderClient`
declaration, not by function proximity. Its `GetBuffer`/`ReleaseBuffer`
interfaces, audio-client padding and context status are supplied finite
surfaces; no endpoint is initialized or heard.

The sink's no-input branch releases a buffer with the SDK silence flag. Generic
error or null render buffer sets the sink's invalid flag without releasing or
admitting PCM. `AUDCLNT_E_BUFFER_TOO_LARGE` instead consults a context
interface before deciding that flag; it is not the device-invalidated HRESULT.
These branches and the real submission copy are native computations under
supplied COM results. Authored bus topology, untested route admission branches,
endpoint/format negotiation, original real COM execution and hardware
audibility remain open. The normal submission method does not compare the
release HRESULT locally, and its non-resampling frame-end caller clears
input-present without inspecting that result. A supplied release failure still
completes the byte copy and leaves the sink-invalid flag clear. Positive
copy/submission receipts therefore require the supplied successful release
result; buffer contents or input-flag clearing alone do not prove that the OS
accepted a frame. This is a conditional error handling observation, not an
observed endpoint failure or a game defect. The current generated voice-output
receipt composes this stream-to-render-buffer cohort with the earlier
separately authenticated Event/Action/Sound identity; it does not claim a
continuously observed live Event generation.
"""
from __future__ import annotations

import hashlib
import struct
import uuid

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_declarations,
    validate_native_group_windows,
)
from scripts.game_data import wwise_codec_factory_native as codec

CONTRACT_PATH = CONTRACTS_DIR / "wwise_voice_pipeline_native.json"
SCHEMA = "endfield.wwise-voice-pipeline-native.v2"
DEPENDENCIES = ("contextSourceAttachment", "mediaSourcePreparation", "contextSourceSampleBuffer", "codecSampleBufferAllocate")


def load_voice_pipeline_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-voice-pipeline")
    return value


def collect_groups(contract, parent):
    expected = [{"key": key, "ownerContract": "wwise_codec_factory_native", "ownerGroup": key} for key in DEPENDENCIES]
    if contract.get("nativeGroupDependencies") != expected:
        codec._fail("voicePipelineDependencies", "groups", expected, contract.get("nativeGroupDependencies"))
    if contract.get("nativeInputs") != parent.get("nativeInputs"):
        codec._fail("voicePipelineInputs", "codec owner", "same selected native triplet", "different declarations")
    groups = list(contract["nativeGroups"])
    for row in expected:
        group = next((g for g in parent.get("nativeGroups", []) if g.get("key") == row["ownerGroup"]), None)
        if group is None:
            codec._fail("voicePipelineOwnerMissing", row["key"], row["ownerGroup"], "missing owner group")
        groups.append({**group, "key": row["key"]})
    validate_native_group_declarations(groups)
    return groups


def _instruction(image, groups, group, rva, length):
    start = _rva(rva, str(group))
    owner = groups.get(group) if isinstance(group, str) else None
    if owner is None or not any(int(w["rva"], 16) <= start and start + length <= int(w["rva"], 16) + w["bodyLength"] for w in owner["windows"]):
        codec._fail("voicePipelineInstructionExtent", str(group), "within authenticated group", rva)
    return image.bytes_at_va(image.image_base + start, length)


def validate_voice_pipeline_bytes(contract, image, bodies, records, parent, source):
    fail = codec._fail
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("voicePipelineSchema", "contract", SCHEMA, contract.get("schema"))
    if contract.get("nativeInputs") != source.get("nativeInputs"):
        fail("voicePipelineSourceInputs", "source owner", "same selected triplet", "different declarations")
    all_groups = collect_groups(contract, parent)
    validate_native_group_windows(all_groups, image, bodies, records)
    groups = {g["key"]: g for g in all_groups}
    for row in codec._rows(contract.get("directEdges"), "voice direct edges", 64):
        witness = codec._witness(groups, row.get("group"), row.get("witnessRole"))
        raw = bytes.fromhex(witness["instructionHex"])
        target = groups.get(row.get("targetGroup"))
        opcode = {"call": b"\xe8", "tailJump": b"\xe9"}.get(row.get("kind"))
        actual = int(witness["rva"], 16) + 5 + struct.unpack_from("<i", raw, 1)[0] if len(raw) == 5 else None
        if target is None or opcode is None or raw[:1] != opcode or actual != int(target["entryRva"], 16):
            fail("voicePipelineEdge", witness["role"], row.get("targetGroup"), actual)
    windows = {}
    for row in codec._rows(contract.get("dataWindows"), "voice data", 16):
        key, length = row.get("key"), row.get("bytes")
        if not isinstance(key, str) or not key or key in windows or type(length) is not int or not 1 <= length <= 4096:
            fail("voicePipelineDataExtent", str(key), "unique key and bounded length", length)
        _digest(row.get("sha256"), key)
        raw = image.bytes_at_va(image.image_base + _rva(row.get("rva"), key), length)
        if hashlib.sha256(raw).hexdigest() != row["sha256"] or raw != _hex(row.get("hex"), key, 4096):
            fail("voicePipelineDataBytes", key, row["sha256"], hashlib.sha256(raw).hexdigest())
        windows[key] = (row, raw)
    for row in codec._rows(contract.get("addressPointBindings"), "voice address points", 16):
        name, slot = row.get("dataWindow"), row.get("slot")
        target = groups.get(row.get("targetGroup"))
        if name not in windows or target is None or type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > len(windows[name][1]):
            fail("voicePipelineAddressPoint", str(name), "bounded slot and named group", row)
        actual = struct.unpack_from("<Q", windows[name][1], slot)[0]
        expected = image.image_base + int(target["entryRva"], 16)
        if actual != expected:
            fail("voicePipelineAddressPoint", name, hex(expected), hex(actual))
    owner_key = contract.get("sourceOwnerTransportDependency")
    owner = next((r for r in source.get("ownerTransports", []) if r.get("key") == owner_key), None)
    if owner is None:
        fail("voicePipelineSourceOwner", str(owner_key), "existing checked owner transport", "missing")
    binding = contract.get("sourceConstructorCallBinding", {})
    target = groups.get(binding.get("targetGroup"))
    raw = _instruction(image, {"sourcePrimaryConstructor": owner["constructor"]}, "sourcePrimaryConstructor", binding.get("rva"), 5)
    actual = int(binding["rva"], 16) + 5 + struct.unpack_from("<i", raw, 1)[0]
    if target is None or raw[:1] != b"\xe8" or actual != int(target["entryRva"], 16):
        fail("voicePipelineSourceConstructorCall", "existing source constructor", binding.get("targetGroup"), hex(actual))
    for row in codec._rows(contract.get("ownerAddressPointBindings"), "voice owner slots", 8):
        slot, target = row.get("slot"), groups.get(row.get("targetGroup"))
        if row.get("ownerTransport") != owner_key or type(slot) is not int or not 0 <= slot <= 256 or slot % 8 or target is None:
            fail("voicePipelineOwnerSlot", str(owner_key), "bounded named owner slot", row)
        _digest(row.get("sha256"), "owner slot")
        at = _rva(owner["addressPointWindow"]["rva"], "existing owner address point") + slot
        raw = image.bytes_at_va(image.image_base + at, 8)
        if hashlib.sha256(raw).hexdigest() != row["sha256"] or struct.unpack("<Q", raw)[0] != image.image_base + int(target["entryRva"], 16):
            fail("voicePipelineOwnerSlot", row["targetGroup"], "selected owner method", raw.hex())
    layout = contract.get("layout")
    if not isinstance(layout, dict):
        fail("voicePipelineLayout", "layout", "named bounded fields", layout)
    seen = set()
    for row in codec._rows(contract.get("fieldBindings"), "voice fields", 64):
        name, width = row.get("field"), row.get("displacementBytes")
        offset = layout.get(name) if isinstance(name, str) else None
        if type(width) is not int or width not in (1, 4) or type(offset) is not int or not 0 <= offset < 1 << (width * 8):
            fail("voicePipelineFieldDeclaration", str(name), "bounded displacement", row)
        if name in seen:
            fail("voicePipelineFieldDuplicate", name, "one field binding", name)
        seen.add(name)
        raw = _hex(row.get("prefixHex"), name, 10) + offset.to_bytes(width, "little")
        suffix = row.get("suffixHex")
        if suffix != "":
            raw += _hex(suffix, name, 10)
        actual = _instruction(image, groups, row.get("group"), row.get("rva"), len(raw))
        if actual != raw:
            fail("voicePipelineField", name, raw.hex(), actual.hex())
    if seen != set(layout):
        fail("voicePipelineFieldCoverage", "layout", sorted(layout), sorted(seen))
    identity = contract.get("renderClientIdentity", {})
    name = identity.get("dataWindow")
    if name not in windows or identity.get("interface") != "IAudioRenderClient" or len(windows[name][1]) != 16:
        fail("voicePipelineRenderIdentity", "render client", "named16-byte IID", identity)
    if uuid.UUID(bytes_le=windows[name][1]) != uuid.UUID(identity["uuid"]):
        fail("voicePipelineRenderIid", "render client", identity["uuid"], windows[name][1].hex())
    for field, slot_field in (("getBufferCallRva", "getBufferSlot"), ("releaseBufferCallRva", "releaseBufferSlot")):
        slot = identity.get(slot_field)
        if type(slot) is not int or not 0 <= slot <= 127 or slot % 8:
            fail("voicePipelineRenderSlot", slot_field, "bounded interface slot", slot)
        actual = _instruction(image, groups, identity.get("getBufferGroup"), identity.get(field), 3)
        if actual != b"\xff\x50" + bytes((slot,)):
            fail("voicePipelineRenderCall", field, slot, actual.hex())
    load = identity["getServiceIidLoadRva"]
    raw = _instruction(image, groups, identity["getServiceGroup"], load, 7)
    target = int(load, 16) + 7 + struct.unpack_from("<i", raw, 3)[0]
    if raw[:3] != b"\x48\x8d\x15" or target != int(windows[name][0]["rva"], 16):
        fail("voicePipelineRenderServiceIid", "GetService", windows[name][0]["rva"], hex(target))
    raw = _instruction(image, groups, identity["getServiceGroup"], identity["getServiceOutputRva"], 4)
    if raw != b"\x4c\x8d\x47" + bytes((layout["renderClient"],)):
        fail("voicePipelineRenderServiceOutput", "GetService", layout["renderClient"], raw.hex())
    raw = _instruction(image, groups, identity["getServiceGroup"], identity["getServiceCallRva"], 3)
    if raw != b"\xff\x50\x70":
        fail("voicePipelineRenderServiceCall", "GetService", "retained audio-client service slot", raw.hex())
