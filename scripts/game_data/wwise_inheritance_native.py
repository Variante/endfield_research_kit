"""Authenticate native hierarchy loading and inherited parameter defaults.

Consumes one already opened image from the explicit codec gate. No bank is
loaded and no native engine state or audio endpoint is changed by this module.
"""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_codec_factory_native as codec
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_declarations, validate_native_group_windows,
)
from scripts.game_data.wwise_voice_pipeline_native import _instruction

CONTRACT_PATH = CONTRACTS_DIR / 'wwise_inheritance_native.json'
SCHEMA = 'endfield.wwise-inheritance-native.v1'
OWNERS = ('wwise_authored_parameters_native', 'wwise_source_queue_native')


def load_inheritance_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status='reviewedCurrentBuild', label='wwise-inheritance')
    return value


def collect_groups(contract, owners):
    groups = list(contract['nativeGroups'])
    for row in codec._rows(contract.get('nativeGroupDependencies'), 'inheritance dependencies', 32):
        owner_key, key = row.get('ownerContract'), row.get('key')
        owner = owners.get(owner_key) if owner_key in OWNERS else None
        if owner is None or contract.get('nativeInputs') != owner.get('nativeInputs'):
            codec._fail('inheritanceOwnerInputs', str(owner_key), 'same selected native triplet', 'missing or different owner')
        group = next((g for g in owner.get('nativeGroups', []) if g.get('key') == row.get('ownerGroup')), None)
        if group is None or key != row.get('ownerGroup'):
            codec._fail('inheritanceOwnerGroup', str(key), row.get('ownerGroup'), 'missing or aliased group')
        groups.append(group)
    validate_native_group_declarations(groups)
    return groups


def validate_inheritance_bytes(contract, image, bodies, records, owners):
    fail = codec._fail
    if contract.get('schema') != SCHEMA or contract.get('status') != 'reviewedCurrentBuild':
        fail('inheritanceSchema', 'contract', SCHEMA, contract.get('schema'))
    groups = collect_groups(contract, owners)
    validate_native_group_windows(groups, image, bodies, records)
    groups = {g['key']: g for g in groups}
    for row in codec._rows(contract.get('directEdges'), 'inheritance edges', 96):
        raw = _instruction(image, groups, row.get('group'), row.get('rva'), 5)
        target = groups.get(row.get('targetGroup'))
        opcode = {'call':b'\xe8', 'tailJump':b'\xe9'}.get(row.get('kind'))
        actual = _rva(row.get('rva'), 'edge') + 5 + struct.unpack_from('<i', raw, 1)[0]
        if opcode is None or raw[:1] != opcode or target is None or actual != _rva(target['entryRva'], 'target'):
            fail('inheritanceEdge', str(row.get('rva')), row.get('targetGroup'), hex(actual))
    seen = set()
    for row in codec._rows(contract.get('instructionBindings'), 'inheritance operands', 64):
        pair = (row.get('group'), row.get('rva'))
        raw = _hex(row.get('instructionHex'), str(pair), 15)
        actual = _instruction(image, groups, pair[0], pair[1], len(raw))
        if pair in seen or actual != raw:
            fail('inheritanceInstruction', str(pair), raw.hex(), actual.hex())
        seen.add(pair)
    globals_ = contract.get('globals', {})
    if not isinstance(globals_, dict) or not 1 <= len(globals_) <= 16:
        fail('inheritanceGlobals', 'globals', 'bounded named globals', globals_)
    seen = set()
    for row in codec._rows(contract.get('globalBindings'), 'inheritance global operands', 32):
        name = row.get('global')
        if name not in globals_:
            fail('inheritanceGlobalDeclaration', str(name), 'declared global', row)
        raw = _instruction(image, groups, row.get('group'), row.get('rva'), 7)
        prefix = _hex(row.get('prefixHex'), str(name), 3)
        actual = _rva(row.get('rva'), str(name)) + 7 + struct.unpack_from('<i', raw, 3)[0]
        if len(prefix) != 3 or raw[:3] != prefix or actual != _rva(globals_[name], str(name)):
            fail('inheritanceGlobalOperand', str(name), globals_[name], hex(actual))
        seen.add(name)
    if seen != set(globals_):
        fail('inheritanceGlobalCoverage', 'globals', sorted(globals_), sorted(seen))
    windows = {}
    for row in codec._rows(contract.get('dataWindows'), 'inheritance data', 16):
        key, length = row.get('key'), row.get('bytes')
        if not isinstance(key, str) or not key or key in windows or type(length) is not int or not 1 <= length <= 4096:
            fail('inheritanceDataExtent', str(key), 'unique bounded data', length)
        _digest(row.get('sha256'), key)
        raw = image.bytes_at_va(image.image_base + _rva(row.get('rva'), key), length)
        if hashlib.sha256(raw).hexdigest() != row['sha256'] or raw != _hex(row.get('hex'), key, 4096):
            fail('inheritanceDataBytes', key, row['sha256'], hashlib.sha256(raw).hexdigest())
        windows[key] = raw
    for row in codec._rows(contract.get('virtualBindings'), 'inheritance slots', 32):
        key, slot = row.get('dataWindow'), row.get('slot')
        target = groups.get(row.get('targetGroup'))
        if key not in windows or type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > len(windows[key]) or target is None:
            fail('inheritanceVirtualDeclaration', str(key), 'bounded checked slot and target', row)
        actual_target = struct.unpack_from('<Q', windows[key], slot)[0] - image.image_base
        if actual_target != _rva(target['entryRva'], key):
            fail('inheritanceVirtualTarget', str(slot), target['entryRva'], hex(actual_target))
        raw = _hex(row.get('instructionHex'), str(slot), 15)
        expected = (b'\xff\x50' + slot.to_bytes(1, 'little') if slot < 128 else
                    b'\xff\x90' + slot.to_bytes(4, 'little'))
        if raw != expected or _instruction(image, groups, row.get('group'), row.get('rva'), len(raw)) != raw:
            fail('inheritanceVirtualCall', str(slot), expected.hex(), raw.hex())


def validate_optional_inheritance(image, bodies, records, authored, queue):
    try:
        contract = load_inheritance_contract()
        validate_inheritance_bytes(contract, image, bodies, records, dict(zip(OWNERS, (authored, queue))))
        return dict(status='validated', detail='conditional hierarchy/default-parameter consumers validated',
                    selectedContractSchema=contract['schema'], ownedNativeGroups=len(contract['nativeGroups']),
                    nativeGroups=len(contract['nativeGroups'])+len(contract['nativeGroupDependencies']),
                    nativeGroupDependencies=contract['nativeGroupDependencies'], evidenceBoundary=contract['evidenceBoundary'])
    except codec.SourceContractError as error:
        return dict(status='mismatched', detail=str(error)[:320], diagnostic=error.diagnostic)
    except FileNotFoundError as error:
        return dict(status='missing', detail=str(error)[:320])
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return dict(status='mismatched', detail=str(error)[:320],
                    diagnostic=dict(failedCheck='inheritance', actual=str(error)[:160]))
