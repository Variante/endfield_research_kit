"""Named stored DamageAction composition under selected native evidence.

The reviewed 11-member action, 33-member DamageUnit, four-member HitEnvData,
one-member HitSoundData and calculation tags 0/2/3 each join ordered source
reads to runtime field stores or generated setter calls. Closed MethodSpec
arguments authenticate every nested field type, including List<DamageUnit>;
the generated member names alone never establish read order. Complete normal
and null reader windows are authenticated against the selected native inputs.

The direct tier names stored fields. Conditional composition names positive
DamageUnit lists, the selected calculation wrappers, shared BlackboardDouble
and EffectActionCfg/vector children, and independently proved TargetSettings
children at their original byte spans. Null lists, null elements and empty
lists remain distinct. Positive tags require a separate List<GameplayTag>
source/count proof and independently named wrapped elements. Positive processor
lists compose through their own typed collection and independent leaf receipts.
Positive cost collections, other
calculation tags, positive terrain-effect arrays and unsupported target
children refuse the complete action. The shared child API composes the same
calculation and effect values for independently typed parent fields. Strings,
flags, enums and floats remain
raw stored values; live formatter selection, evaluated blackboards, damage
execution and a whole BuffData root are outside this module's proof.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as records_native
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_effect_config_child_receipt as effect_config
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vectors
from scripts.game_data.memorypack import skill_damage_unit_gameplay_tag_list as tag_list
from scripts.game_data.memorypack import buff_damage_processor_collection as processor_list

LABEL = "buffDamageAction"
TAG = 154
CONTRACT_PATH = CONTRACTS_DIR / "buff_damage_action_native.json"


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(
        CONTRACT_PATH, schema="endfield.buff-damage-action-native-contract.v3",
        status="exact-current-build", label=LABEL,
    )
    required = {"action", "unit", "environment", "sound", "calculation0",
                "calculation2", "calculation3"}
    if (value.get("unionTag") != TAG or value.get("sourceContract") != "buff_9a_native.json"
            or set(value.get("records", {})) != required
            or set(value.get("calculationDispatch", {})) != {"0", "2", "3"}
            or any(not record.get("members") or len({m["fieldName"] for m in record["members"]})
                   != len(record["members"]) for record in value["records"].values())):
        raise ValueError(f"{LABEL}.contract:shape")
    binding = value.get('damageTagsList')
    if binding != {'ownerRecord':'unit','sourceMemberIndex':9,'fieldName':'damageTags',
            'declaredType':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>'}:
        raise ValueError(f'{LABEL}.contract:tag-list-binding')
    list_contract, _ = tag_list._contract_and_sources()
    owner = list_contract['owner']; member = value['records']['unit']['members'][binding['sourceMemberIndex']]
    expected = value['nativeInputs']; list_pins = list_contract['nativeInputs']
    if (member['fieldName'] != binding['fieldName'] or member['declaredType'] != binding['declaredType']
            or member['kind'] != 'empty-list'
            or member.get('sourceContextInstructionRva') != owner['listCallsiteRva']
            or value['records']['unit']['runtimeTypeName'] != owner['typeName']
            or owner['sourceMemberIndex'] != binding['sourceMemberIndex']
            or value['dependencies'].get('damageTagsList') != tag_list.CONTRACT_PATH.name
            or value['dependencies'].get('namedTagElements') != 'buff_aura_heal_actions_native.json'
            or list_pins != {'gameassemblySha256':expected['GameAssembly.dll'],
                'globalMetadataSha256':expected['global-metadata.dat'],'unityplayerSha256':expected['UnityPlayer.dll']}):
        raise ValueError(f'{LABEL}.contract:tag-list-owner-or-build')
    processor_binding=value.get('damageProcessorsList')
    collection=processor_list._contract()
    owner=collection['owner']
    if (processor_binding!={'ownerRecord':'unit','sourceMemberIndex':owner['sourceMemberIndex'],
            'fieldName':owner['fieldName'],'declaredType':owner['declaredType']}
        or value['dependencies'].get('damageProcessorsList')!=processor_list.CONTRACT_PATH.name
        or collection['nativeInputs']!=expected):
        raise ValueError(f'{LABEL}.contract:processor-list-owner-or-build')
    return value


def _fail(check: str, expected: Any, actual: Any, *, record: str = "", field: str = "") -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
                            expected=expected, actual=actual)
    error.diagnostic.update({"validator": LABEL, "unionTag": TAG, "record": record,
                             "field": field, "nativeInputs": _contract()["nativeInputs"]})
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def validate_current_native_contract(*, vector_native: dict[str, Any],
                                     target_native: dict[str, Any]) -> dict[str, Any]:
    """Authenticate ordered read/destination joins and every nested field type."""
    contract = _contract(); expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"])
    if gate.status != "validated":
        return {"status": gate.status, "detail": gate.detail, "nativeInputs": expected}
    for name, child in (("vectors", vector_native), ("target", target_native)):
        if (child.get("status") != "validated"
                or any(child.get("nativeInputs", {}).get(k) != expected[k]
                       for k in ("GameAssembly.dll", "global-metadata.dat"))):
            _fail("shared-child", expected, {"name": name, "status": child.get("status"),
                                           "nativeInputs": child.get("nativeInputs")})
    unityplayer = Path(gate.gameassembly).parent / "UnityPlayer.dll"
    if not unityplayer.is_file() or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        _fail("UnityPlayer.dll", expected["UnityPlayer.dll"], "missing-or-mismatched")
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    if source.get("schemaVersion") != 1:
        _fail("source-schema", 1, source.get("schemaVersion"))
    image = open_native_image(gate.gameassembly, gate.metadata)
    proved = records_native.validate_named_records(image, source, contract["records"], label=LABEL, fail=_fail)
    contexts = {c["instructionRva"]: c for c in source["nestedContexts"]}
    for dispatch in contract["calculationDispatch"].values():
        record = contract["records"][dispatch["record"]]
        records_native.check_typed_context(image, contexts[dispatch["sourceContextInstructionRva"]], record["wrapperTypeName"], label=LABEL, fail=_fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    route = routes.get(TAG); action = contract["records"]["action"]
    if (audit.get("status") != "validated" or route is None or route.status != "resolved"
            or route.wrapper_name != action["wrapperTypeName"]
            or list(route.member_order) != [m["fieldName"] for m in action["members"]]
            or list(route.member_declared_types) != [m["declaredType"] for m in action["members"]]):
        _fail("dispatcher-members", action["wrapperTypeName"], None if route is None else route.row())
    list_native = tag_list.validate_current_native_contract()
    if not _tag_list_native_matches(list_native, expected):
        _fail('damage-tags-list-native', 'validated selected list source/count proof', list_native,
            record='unit', field='damageTags')
    processor_native=processor_list.validate_current_native_contract()
    if processor_native.get('status')!='validated' or processor_native.get('nativeInputs')!=expected:
        _fail('damage-processors-list-native','validated owned collection and independent leaves',
            processor_native,record='unit',field='damageProcessors')
    after = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('native-inputs-after', expected, after.detail)
    return {"status": "validated", "nativeInputs": expected, "unionTag": TAG,
            "recordMembers": proved, "damageTagsListNative": list_native,
            "damageProcessorsListNative":processor_native,
            "evidenceBoundary": contract["evidenceBoundary"]}


def _tag_list_native_matches(packet: dict[str, Any], expected: dict[str, Any]) -> bool:
    return (packet.get('status') == 'validated'
        and packet.get('nativeInputs') == {'gameassemblySha256':expected['GameAssembly.dll'],
            'globalMetadataSha256':expected['global-metadata.dat'],'unityplayerSha256':expected['UnityPlayer.dll']}
        and packet.get('sourceWindowValidation') == list(tag_list.SOURCE_NAMES))


def _decode_value(data: bytes, *, source: str, digest: str, start: int, end: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]] | None,
                  child_kind: str | None = None) -> dict[str, Any]:
    """Compose a bounded action or one independently typed shared child."""
    contract = _contract(); context = native_validation.get("children", {}); native = context.get("damage", {})
    wanted = {key: [{"fieldName": m["fieldName"], "kind": m["kind"]} for m in record["members"]]
              for key, record in contract["records"].items()}
    if (native_validation.get("status") != "validated" or native.get("status") != "validated"
            or native.get("nativeInputs") != contract["nativeInputs"] or native.get("unionTag") != TAG
            or native.get("recordMembers") != wanted or not source or not isinstance(data, bytes)
            or not _tag_list_native_matches(native.get('damageTagsListNative', {}), contract['nativeInputs'])
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader = Reader(data, source, end); reader.pos = start
    args = {"source": source, "logical_sha256": digest}

    def scalar_value(a: int, b: int) -> dict[str, Any]:
        return scalar.decode_adding_cooldown(data, a, b, native_validation=context["effectVectors"]["scalarNative"])

    def effect_value(a: int, b: int) -> dict[str, Any]:
        packet = context["effectVectors"]
        receipt = effect_config.decode_effect_config_child_receipt(data, **args, start=a, end=b,
                                                                  native_validation=packet["effectConfigNative"])
        for member in receipt["namedFields"]:
            if member["kind"] == "scalar":
                member["child"] = scalar_value(member["start"], member["end"])
            elif member["kind"] == "vector":
                member["child"] = vectors.decode_blackboard_vector3_value(data, **args, start=member["start"],
                                                                         end=member["end"], native_validation=packet)
        return {**receipt, "recursiveStoredSchemaExact": True}

    def calculation() -> dict[str, Any]:
        a = reader.pos
        tag = reader.nested_union_tag(tuple(int(t) for t in contract["calculationDispatch"]), "damage-calculation")
        child = None if tag is None else record(contract["calculationDispatch"][str(tag)]["record"])
        return {"start": a, "end": reader.pos, "unionTag": tag, "child": child,
                "recursiveStoredSchemaExact": True}

    def record(key: str) -> dict[str, Any]:
        a = reader.pos; members = contract["records"][key]["members"]
        if reader.peek() == 0xFF:
            reader.take(1, "null-" + key)
            return {"start": a, "end": reader.pos, "status": "exact-null", "namedFields": [],
                    "recursiveStoredSchemaExact": True}
        reader.header(len(members)); fields = []
        for member in members:
            begin = reader.pos; kind = member["kind"]; value = {}
            if kind in ("byte", "scalar32", "scalar64"):
                value["rawHex"] = reader.take({"byte": 1, "scalar32": 4, "scalar64": 8}[kind], member["fieldName"]).hex().upper()
            elif kind == "byte-payload":
                reader.byte_payload(); value["rawHex"] = data[begin:reader.pos].hex().upper()
            elif kind == "empty-list":
                if key=='unit' and member['fieldName']==contract['damageProcessorsList']['fieldName']:
                    count=reader.count(1,reserve=42,nullable=True)
                    for _ in range(max(0,count)):
                        reader.damage_processor_profile()
                    if count>0:
                        value['child']=processor_list.decode_collection(data,source=source,digest=digest,
                            start=begin,end=reader.pos,native_validation=native.get('damageProcessorsListNative',{}))
                    else:
                        value['child']={'start':begin,'end':reader.pos,'count':count,'elements':[],
                            'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
                    value['count']=count
                    fields.append({**member,**value,'start':begin,'end':reader.pos})
                    continue
                if key == 'unit' and member['fieldName'] == contract['damageTagsList']['fieldName']:
                    reader.damage_tag_collection()
                    count = struct.unpack_from('<i', data, begin)[0]
                    if count > 0:
                        # Aura's native validator depends on Damage. Consume
                        # its independently proved named element packet only
                        # after the complete context is assembled, avoiding a
                        # native dependency cycle.
                        from scripts.game_data.memorypack import buff_aura_heal_actions as named_tags
                        value['child'] = named_tags.decode_tag_elements(data, source=source, digest=digest,
                            start=begin, end=reader.pos, native_validation=context.get('auraHeal', {}))
                    else:
                        value['child'] = {'start':begin, 'end':reader.pos, 'count':count, 'elements':[],
                            'recursiveStoredSchemaExact':True, 'runtimeMeaningExact':False}
                    value['count'] = count
                    fields.append({**member, **value, 'start':begin, 'end':reader.pos})
                    continue
                count = reader.count(1, nullable=True)
                if count > 0:
                    raise ValueError(f"{LABEL}.decode:positive-{member['fieldName']}-unproved at={begin}")
                value["count"] = count
            elif kind == "counted-member33":
                count = reader.count(1, reserve=4, nullable=True)
                elements = [record("unit") for _ in range(max(0, count))]
                value["child"] = {"start": begin, "end": reader.pos, "count": count, "elements": elements,
                                  "recursiveStoredSchemaExact": True}
            elif kind == "calculation":
                value["child"] = calculation()
            elif kind == "scalar-payload":
                reader.scalar_payload(); value["child"] = scalar_value(begin, reader.pos)
            elif kind in ("member4", "member1"):
                value["child"] = record({"member4": "environment", "member1": "sound"}[kind])
            elif kind == "member85":
                reader.effect_configuration_profile(); value["child"] = effect_value(begin, reader.pos)
            elif kind == "target":
                reader.target_profile()
                span = {"start": begin, "end": reader.pos, "fieldName": member["fieldName"]}
                if data[begin:reader.pos] == b"\xff":
                    value["child"] = {**span, "status": "exact-null", "recursiveStoredSchemaExact": True}
                else:
                    value["child"] = target_decoder(data, source, digest, span, context)
            else:
                raise ValueError(f"{LABEL}.decode:unsupported-kind={kind}")
            fields.append({"fieldName": member["fieldName"], "kind": kind,
                           "start": begin, "end": reader.pos, **value})
        return {"start": a, "end": reader.pos, "status": "named-stored-members-exact-span",
                "typeName": contract["records"][key]["runtimeTypeName"], "namedFields": fields,
                "recursiveStoredSchemaExact": True}

    if child_kind == "calculation":
        receipt = calculation()
    elif child_kind == "effectData":
        reader.effect_configuration_profile()
        receipt = effect_value(start, reader.pos)
    elif child_kind is None:
        if reader.nested_union_tag((TAG,), "damage-action") != TAG:
            raise ValueError(f"{LABEL}.decode:physical-tag")
        receipt = record("action")
    else:
        raise ValueError(f"{LABEL}.decode:unsupported-child-kind={child_kind}")
    if reader.pos != end:
        raise ValueError(f"{LABEL}.decode:action-end={reader.pos}; expected={end}")
    if child_kind is not None:
        return {"source": source, "logicalSha256": digest.upper(), "start": start, "end": end,
                "kind": child_kind, "child": receipt, "recursiveStoredSchemaExact": True,
                "runtimeMeaningExact": False}
    return {"schema": "endfield.buff-damage-action-receipt.v1", "source": source,
            "logicalSha256": digest.upper(), "tag": TAG, "start": start, "end": end,
            "parent": receipt, "recursiveStoredSchemaExact": True, "runtimeMeaningExact": False}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int,
                  native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    """Reparse an independently framed action and compose each reached child."""
    return _decode_value(data, source=source, digest=digest, start=start, end=end,
                         native_validation=native_validation, target_decoder=target_decoder)


def decode_child_value(data: bytes, *, source: str, digest: str, start: int, end: int,
                       child_kind: str, native_validation: dict[str, Any]) -> dict[str, Any]:
    """Compose a calculation or effect after the caller proves its field type."""
    return _decode_value(data, source=source, digest=digest, start=start, end=end,
                         native_validation=native_validation, target_decoder=None, child_kind=child_kind)
