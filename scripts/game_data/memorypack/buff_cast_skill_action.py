"""Named CastSkill storage with independent string, caster and target children.

The paired BlackboardString retains both raw payloads and its selection flag.
Two TargetSettings records have separate original spans. No skill invocation,
cost decision or interrupt behavior is established by these stored operands.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_blackboard_string_child_receipt as strings

LABEL = 'buffCastSkillAction'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_cast_skill_action_native.json'
CHILDREN = ('target', 'blackboardString')


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-cast-skill-action-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(c.get('records', {})) != {'castSkill'} or c.get('actionDispatch') != {'39': 'castSkill'}
            or c.get('childTypes') != {'target': 'Beyond.Gameplay.Core.TargetSettings', 'paired-payload': strings.STRING_TYPE}
            or [m['fieldName'] for m in c['records']['castSkill']['members']] != [
                'isEnable', 'priorityLevel', 'priorityOffset', 'serverActionIndex',
                'caster', 'inheritSourceSkillCastId', 'interruptCurSkillOnlyWhenTargetCastable',
                'skillId', 'skipApplyCost', 'target']):
        raise ValueError(f'{LABEL}.contract:shape')
    for m in c['records']['castSkill']['members']:
        if m['kind'] in c['childTypes'] and (m['declaredType'] != c['childTypes'][m['kind']]
                or m.get('sourceContextInstructionRva') is None):
            raise ValueError(f'{LABEL}.contract:typed-child={m["fieldName"]}')
    return c


def supported_tags() -> frozenset[int]:
    return frozenset(map(int, _contract()['actionDispatch']))


def _members(c: dict[str, Any]) -> dict[str, Any]:
    return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in r['members']]
            for k, r in c['records'].items()}


def _fail(check: str, expected: Any, actual: Any, **details: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, nativeInputs=_contract()['nativeInputs'], **details)
    raise error


def validate_current_native_contract(*, children: dict[str, Any],
        gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); pins = c['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins}
    for name in CHILDREN:
        if children.get(name, {}).get('status') != 'validated' or children[name].get('nativeInputs') != pins:
            _fail('shared-child', {'name': name, 'nativeInputs': pins}, children.get(name))
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', pins['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    source_path = CONTRACTS_DIR / c['records']['castSkill']['sourceContract']; source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=source_path)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=_fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata)
    record = c['records']['castSkill']; route = routes.get(next(iter(supported_tags())))
    if (audit.get('status') != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != record['wrapperTypeName']
            or list(route.member_order) != [m['fieldName'] for m in record['members']]
            or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
        _fail('dispatcher-members', record['wrapperTypeName'], None if route is None else route.row())
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', pins['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': c['actionDispatch'], 'evidenceBoundary': c['evidenceBoundary']}


def decode_action(data: bytes, *, source: str, digest: str, start: int, end: int, tag: int,
        native_validation: dict[str, Any], target_decoder: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    c = _contract(); context = native_validation.get('children', {}); native = context.get('castSkill', {})
    if (native_validation.get('status') != 'validated' or native.get('status') != 'validated'
            or native_validation.get('nativeInputs') != c['nativeInputs'] or native.get('nativeInputs') != c['nativeInputs']
            or native.get('recordMembers') != _members(c) or native.get('actionDispatch') != c['actionDispatch']
            or any(context.get(n, {}).get('status') != 'validated' or context[n].get('nativeInputs') != c['nativeInputs'] for n in CHILDREN)
            or str(tag) not in c['actionDispatch'] or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((tag,), 'cast-skill-action') != tag:
        raise ValueError(f'{LABEL}.decode:physical-tag')
    record = c['records']['castSkill']; fields = []
    if reader.peek() == 255:
        reader.take(1, 'null-action-wrapper'); status = 'exact-null-wrapper'
    else:
        reader.header(len(record['members'])); status = 'named-action-exact-span'
        for m in record['members']:
            at = reader.pos; kind = m['kind']; value = {}
            if kind in ('byte', 'scalar32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, m['fieldName']).hex().upper()
            elif kind == 'paired-payload':
                reader.paired_payload()
                child = strings.decode_blackboard_string_value(data, source=source, logical_sha256=digest,
                    start=at, end=reader.pos, native_validation=context['blackboardString'])
                if child.get('wholeStoredSpanExact') is not True:
                    raise ValueError(f'{LABEL}.decode:string-span at={at}')
                value['child'] = {**child, 'recursiveStoredSchemaExact': True}
            elif kind == 'target':
                reader.target_profile(); span = {'start': at, 'end': reader.pos, 'fieldName': m['fieldName']}
                value['child'] = ({**span, 'status': 'exact-null-wrapper', 'recursiveStoredSchemaExact': True}
                    if data[at:reader.pos] == b'\xff' else target_decoder(data, source, digest, span, context))
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact') is not True
                    or [value['child'].get('start'), value['child'].get('end')] != [at, reader.pos]):
                raise ValueError(f'{LABEL}.decode:child-span at={at}')
            fields.append({'fieldName': m['fieldName'], 'declaredType': m['declaredType'], 'kind': kind,
                'start': at, 'end': reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:action-end={reader.pos}; expected={end}')
    return {'schema': 'endfield.buff-cast-skill-action-receipt.v1', 'source': source, 'logicalSha256': digest.upper(),
        'tag': tag, 'start': start, 'end': end, 'typeName': record['runtimeTypeName'], 'status': status,
        'namedFields': fields, 'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
