"""Source-bound named AnimationCurve storage, with independent native copies.

The selected formatter copies two wrap words and seven words per Keyframe.
Callback resolution names establish stored destinations, not evaluation or
execution of Unity callbacks. The explicit stored-profile adapter retains
source-named headerless Keyframe words; callers prove each parent typed join.
"""
from __future__ import annotations

import hashlib
import json
import struct
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.context import generic_type_carrier
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL = "memorypackAnimationCurve"
CONTRACT_PATH = CONTRACTS_DIR / "memorypack_animation_curve_native.json"


def formatter_curve_type(image: Any, *, source_method=None) -> dict[str, Any]:
    """Resolve the actual closed argument owned by this selected formatter.

    The caller authenticates the selected image and curve child contract.
    The generic base relationship proves a type join, not curve evaluation.
    """
    source_method = source_method if source_method is not None else _contract()['sourceMethod']
    method=image.metadata.methods[source_method[0]]
    formatter=image.metadata.types[method.declaring_type]
    if image.type_name(formatter.index)!=source_method[1]:
        _fail('formatter-owner',source_method[1],image.type_name(formatter.index))
    table=int(image.registration['types'],16);pointer=image.pe.u64_at_va(table+formatter.parent_index*8)
    raw=image.pe.bytes_at_va(pointer,16);carrier=image.pe.bytes_at_va(struct.unpack_from('<Q',raw)[0],32)
    base_raw=image.pe.bytes_at_va(struct.unpack_from('<Q',carrier)[0],16)
    owned=generic_type_carrier(raw,carrier,base_raw,type_pointer=pointer,type_count=len(image.metadata.types),source=str(image.gameassembly))
    if image.type_name(owned['baseDefinitionIndex'])!='MemoryPack.MemoryPackFormatter`1':
        _fail('formatter-base','MemoryPack.MemoryPackFormatter`1',owned)
    instance=image.instantiations.resolve_pointer(owned['classInstantiationPointerVa'])
    if len(instance.arguments)!=1:_fail('formatter-arity',1,len(instance.arguments))
    argument=bytes.fromhex(instance.arguments[0].raw_type_record_hex)
    if argument[10:12]!=b'\x12\0':_fail('formatter-reference-argument','named reference type',argument.hex())
    definition=struct.unpack_from('<Q',argument)[0];name=image.type_name(definition)
    if name!='UnityEngine.AnimationCurve':_fail('formatter-curve-type','UnityEngine.AnimationCurve',name)
    return {'typeDefinition':definition,'typeName':name,'formatterTypeDefinition':formatter.index,
            'baseCarrier':owned,'classInstantiation':instance.as_dict()}


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema="endfield.memorypack-animation-curve-native-contract.v2",
        status="exact-current-build", label=LABEL)
    fields = value.get("keyframeFields", [])
    if (value.get("storedMemberCount") != 3 or value.get("keyframeBytes") != 28
            or len(fields) != 7 or len({f["fieldName"] for f in fields}) != 7
            or [f["wireOffset"] for f in fields] != list(range(0, 28, 4))
            or any(f["bytes"] != 4 for f in fields)):
        raise ValueError(f"{LABEL}.contract:shape")
    return value


def _fail(check: str, expected: Any, actual: Any, *, field: str = "") -> None:
    error = CensusGateError(f"{LABEL}.{check}", source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, field=field)
    raise error


def _check_curve_copies(image: Any, contract: dict[str, Any]) -> None:
    from scripts.game_data.memorypack import animation_curve_source
    try:
        animation_curve_source.validate_on_image(image, contract['nativeInputs'], contract=contract)
    except ValueError as error:
        _fail('selected-source-proof', 'exact current named source derivation', str(error), field='sourcePrograms')


def validate_current_native_contract(*, gameassembly=None, metadata=None) -> dict[str, Any]:
    if (gameassembly is None) != (metadata is None):
        raise ValueError(f"{LABEL}.native:both-selected-paths-required")
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import animation_curve_source
    contract=_contract(); expected=contract['nativeInputs']
    gate=check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'],
        gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':
        return {'status':gate.status,'detail':gate.detail,'nativeInputs':expected}
    image=open_native_image(gate.gameassembly,gate.metadata)
    _publication_gate(image,expected)
    result=animation_curve_source.validate_on_image(image,expected,contract=contract)
    _publication_gate(image,expected)
    return result


def decode_curve(data: bytes, *, source: str, digest: str, start: int, end: int,
                 native_validation: dict[str, Any], require_end: bool = True) -> dict[str, Any]:
    contract=_contract()
    if (native_validation.get("status")!="validated" or native_validation.get("nativeInputs")!=contract["nativeInputs"]
            or any(native_validation.get(k)!=contract[k] for k in ("keyframeFields","storedMemberCount","keyframeBytes"))
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)
            or type(require_end) is not bool):
        raise ValueError(f"{LABEL}.decode:native-source-or-span")
    reader=Reader(data,source,end);reader.pos=start;fields=[];keys=[];count=None
    is_null=reader.peek()==255
    if is_null:
        reader.take(1,"null-curve")
    else:
        reader.header(contract["storedMemberCount"])
        for name in ("preWrapMode","postWrapMode"):
            at=reader.pos;raw=reader.take(4,name)
            fields.append({"fieldName":name,"start":at,"end":reader.pos,"rawHex":raw.hex().upper()})
        at=reader.pos;count=reader.count(contract["keyframeBytes"],nullable=True)
        for _ in range(max(0,count)):
            begin=reader.pos;members=[]
            for f in contract["keyframeFields"]:
                pos=reader.pos;raw=reader.take(f["bytes"],f["fieldName"])
                members.append({"fieldName":f["fieldName"],"declaredType":f["declaredType"],
                    "start":pos,"end":reader.pos,"rawHex":raw.hex().upper()})
            keys.append({"start":begin,"end":reader.pos,"namedFields":members})
        fields.append({"fieldName":"keys","start":at,"end":reader.pos,"count":count,"elements":keys})
    if require_end and reader.pos!=end:
        raise ValueError(f"{LABEL}.decode:curve-end={reader.pos}; expected={end}")
    return {"schema":"endfield.memorypack-animation-curve-receipt.v1","source":source,
        "logicalSha256":digest.upper(),"start":start,"end":reader.pos,"null":is_null,"keyCount":count,
        "namedFields":fields,"recursiveStoredSchemaExact":True,"runtimeMeaningExact":False}


def stored_curve_node(receipt: dict[str, Any]) -> dict[str, Any]:
    """Project an independently decoded curve into named bit-preserving values."""
    from scripts.game_data.memorypack import stored_plan_values as stored
    from scripts.game_data.memorypack.source_bound_stored_tree import bind_source_named_tree
    if receipt.get('recursiveStoredSchemaExact') is not True:
        raise ValueError(f'{LABEL}.stored:complete-source-receipt-required')
    if receipt['null']:
        if receipt['namedFields'] or receipt['keyCount'] is not None:
            raise ValueError(f'{LABEL}.stored:null-members')
        return stored.object_node([], null=True)
    fields = receipt['namedFields']; contract = _contract()
    if [f['fieldName'] for f in fields] != ['preWrapMode', 'postWrapMode', 'keys']:
        raise ValueError(f'{LABEL}.stored:source-member-order')
    def word(field):
        raw = bytes.fromhex(field['rawHex'])
        if len(raw) != 4 or field['end'] - field['start'] != len(raw):
            raise ValueError(f'{LABEL}.stored:named-word-span')
        return {'fieldName': field['fieldName'], 'start': field['start'], 'end': field['end'],
                'value': stored.fixed_node(raw)}
    keys = []
    for key in fields[2]['elements']:
        members = key['namedFields']
        if [(f['fieldName'], f['declaredType']) for f in members] != [
                (f['fieldName'], f['declaredType']) for f in contract['keyframeFields']]:
            raise ValueError(f'{LABEL}.stored:keyframe-source-member-order')
        keys.append({'kind': 'struct', 'start': key['start'], 'end': key['end'],
                     'memberOrder': [f['fieldName'] for f in members], 'members': [word(f) for f in members]})
    tree = stored.object_node([word(fields[0]), word(fields[1]),
        {'fieldName': fields[2]['fieldName'], 'start': fields[2]['start'], 'end': fields[2]['end'],
         'value': {'kind': 'list', 'count': receipt['keyCount'], 'elements': keys}}])
    # Every curve object and headerless keyframe has its own source fields.
    bind_source_named_tree(receipt, tree)
    return tree


def source_profile_reader(native_validation: dict[str, Any]):
    """Make an explicit curve-only profile callback; authenticate on each reach."""
    from scripts.game_data.memorypack import stored_plan_values as stored
    def profile(reader, member, depth):
        if (member.kind != 'profile' or member.profile != 'curve_profile'
                or type(depth) is not int or not 0 <= depth <= 256):
            raise ValueError(f'{LABEL}.profile:source-bound-curve-only')
        begin = reader.pos
        receipt = decode_curve(reader.data, source=reader.source,
            digest=hashlib.sha256(reader.data).hexdigest(), start=begin, end=reader.limit,
            native_validation=native_validation, require_end=False)
        tree = stored_curve_node(receipt)
        if stored.encode_stored_node(tree) != reader.data[begin:receipt['end']]:
            raise ValueError(f'{LABEL}.profile:named-field-value-reencode')
        reader.pos = receipt['end']
        return tree
    return profile
