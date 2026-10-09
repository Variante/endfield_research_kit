"""Named ShapeFinder operands with separately admitted ColliderShapeData.

Flags, enum and float bits stay raw. No faction, angle, height or shape
selection and no resulting target entity is evaluated.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_collider_shape as collider
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL = 'buffSelectorShapeFinder'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_selector_shape_finder_native.json'


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-selector-shape-finder-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(c.get('records', {})) != {'shapeFinder'}
            or type(c.get('dispatcher', {}).get('unionTag')) is not int
            or c.get('sourceContract') != 'buff_7c_native.json'
            or len(c['records']['shapeFinder']['members']) != 11
            or c['records']['shapeFinder']['members'][-1]['fieldName'] != 'shapeData'
            or c.get('dependencies') != {'colliderShape': collider.CONTRACT_PATH.name}
            or c['records']['shapeFinder']['members'][-1]['declaredType'] != collider._contract()['records']['colliderShape']['runtimeTypeName']):
        raise ValueError(f'{LABEL}.contract:shape')
    return c


def _members(c: dict) -> dict:
    return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in r['members']]
            for k, r in c['records'].items()}


def _fail(check: str, expected: Any, actual: Any, **details: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, nativeInputs=_contract()['nativeInputs'], **details)
    raise error


def validate_current_native_contract(*, selector_native: dict[str, Any], collider_native: dict[str, Any],
        gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); expected = c['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': expected}
    for name, child in (('selector', selector_native), ('collider', collider_native)):
        if child.get('status') != 'validated' or child.get('nativeInputs') != expected:
            _fail('shared-child', expected, {'name': name, 'status': child.get('status'), 'nativeInputs': child.get('nativeInputs')})
    unity = gate.gameassembly.parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', expected['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    source_path = CONTRACTS_DIR / c['sourceContract']; source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations, image.modules,
        image.owners, source=str(gate.gameassembly), contract_path=source_path)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=_fail)
    dispatch = c['dispatcher']; route = image.validate_dispatcher(dispatch, label=LABEL)
    image.check_instruction_windows([dispatch['typeLoadInstruction']], label=LABEL)
    rva, raw_hex = dispatch['typeLoadInstruction']; raw = bytes.fromhex(raw_hex)
    if (raw[:3] != b'\x48\x8b\x15' or len(raw) != 7
            or image.pe.image_base + rva + 7 + struct.unpack_from('<i', raw, 3)[0] != route['usageCell']):
        _fail('route-type-load', route['usageCell'], dispatch['typeLoadInstruction'])
    registry = selector_native['_registry']; record = c['records']['shapeFinder']
    finder = [m for m in registry.plans[selector_native['selectorDefinition']] if m.name == 'finderData' and m.kind == 'union']
    definition = record['wrapperTypeDefinition']
    if (len(finder) != 1 or registry.union_tag_maps.get(finder[0].ref, {}).get(c['dispatcher']['unionTag']) != definition
            or registry.wrapped_names.get(definition) != record['runtimeTypeName']):
        _fail('selector-parent-route', record['runtimeTypeName'], definition)
    if (collider_native.get('recordMembers') != collider._members(collider._contract())
            or record['members'][-1]['declaredType'] != collider._contract()['records']['colliderShape']['runtimeTypeName']):
        _fail('typed-shape-child','independently admitted ColliderShapeData',record['members'][-1])
    after = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', expected['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': expected, 'unionTag': c['dispatcher']['unionTag'],
        'recordMembers': proved, 'evidenceBoundary': c['evidenceBoundary']}


def finder_tags() -> frozenset[int]:
    return frozenset((_contract()['dispatcher']['unionTag'],))


def decode_finder(data: bytes, *, source: str, digest: str, start: int, end: int,
        context: dict[str, Any]) -> dict[str, Any]:
    c=_contract();native=context.get('shapeFinder',{});tag=c['dispatcher']['unionTag']
    if (native.get('status')!='validated' or native.get('nativeInputs')!=c['nativeInputs']
            or native.get('unionTag')!=tag or native.get('recordMembers')!=_members(c)
            or not isinstance(data,bytes) or not source or not isinstance(digest,str)
            or hashlib.sha256(data).hexdigest().upper()!=digest.upper()
            or type(start) is not int or type(end) is not int or not 0<=start<end<=len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    for key in ('colliderShape',):
        if context.get(key,{}).get('status')!='validated' or context[key].get('nativeInputs')!=c['nativeInputs']:
            raise ValueError(f'{LABEL}.decode:shared-child-inputs')
    reader=Reader(data,source,end);reader.pos=start
    selected=reader.nested_union_tag((tag,),'shape-finder');fields=[]
    if selected is None:status='exact-null-union'
    elif reader.peek()==255:reader.take(1,'null-finder-wrapper');status='exact-null-wrapper'
    else:
        record=c['records']['shapeFinder'];reader.header(len(record['members']));status='named-finder-exact-span'
        for member in record['members']:
            begin=reader.pos;kind=member['kind'];value={}
            if kind in ('byte','scalar32'):
                value['rawHex']=reader.take(1 if kind=='byte' else 4,member['fieldName']).hex().upper()
            elif kind=='byte-payload':
                reader.byte_payload();value.update(rawHex=data[begin:reader.pos].hex().upper(),payloadEncoding='unresolved')
            elif kind=='collider-shape-profile':
                reader.collider_shape_profile()
                child=collider.decode_value(data,source=source,digest=digest,start=begin,end=reader.pos,native=context['colliderShape'])
                if child.get('recursiveStoredSchemaExact') is not True or [child.get('start'),child.get('end')]!=[begin,reader.pos]:
                    raise ValueError(f'{LABEL}.decode:shape-child-span')
                value['child']=child
            else:raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName':member['fieldName'],'declaredType':member['declaredType'],'kind':kind,
                'start':begin,'end':reader.pos,**value})
    if reader.pos!=end:raise ValueError(f'{LABEL}.decode:finder-end={reader.pos}; expected={end}')
    return {'source':source,'logicalSha256':digest.upper(),'start':start,'end':end,'tag':selected,
        'typeName':c['records']['shapeFinder']['runtimeTypeName'],'status':status,'namedFields':fields,
        'recursiveStoredSchemaExact':True,'runtimeMeaningExact':False}
