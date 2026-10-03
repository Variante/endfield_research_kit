"""Selected Wwise external-package path hashing and keyed table lookup.

This gate reuses the decoder-provider validator's opened images. Computed keys
are conditional static identities; they never admit a captured lookup result.
"""
from __future__ import annotations

import struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation

CONTRACT_PATH = CONTRACTS_DIR / 'wwise_external_package_native.json'
SCHEMA = 'endfield.wwise-external-package-native.v2'


def load_package_contract(path: Path = CONTRACT_PATH) -> dict:
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status='reviewedCurrentBuild', label='wwise-external-package')
    return value


def _import_at(image, wanted: int) -> str | None:
    """Resolve one PE32+ IAT slot through bounded import descriptors/thunks."""
    pe = struct.unpack_from('<I', image.buf, 0x3c)[0]
    directory, size = struct.unpack_from('<II', image.buf, pe + 24 + 120)
    if not directory or not 20 <= size <= 1 << 20:
        raise ValueError('externalPackageImport: invalid import directory')
    read = lambda at, count: image.bytes_at_va(image.image_base + at, count)
    for index in range(min(size // 20, 256)):
        original, _, _, _, first = struct.unpack('<IIIII', read(directory + index * 20, 20))
        if not original and not first:
            return None
        if first <= wanted < first + 4096 * 8 and (wanted - first) % 8 == 0:
            if not original:
                raise ValueError('externalPackageImport: original thunk table required')
            ordinal = (wanted - first) // 8
            for slot in range(ordinal + 1):
                entry = struct.unpack('<Q', read(original + slot * 8, 8))[0]
                if not entry:
                    break
                if slot == ordinal:
                    if entry & (1 << 63):
                        return None
                    raw = read(entry + 2, 260)
                    end = raw.find(b'\0')
                    if end < 0:
                        raise ValueError('externalPackageImport: unterminated symbol')
                    return raw[:end].decode('ascii')
    return None


def validate_package_bytes(contract: dict, image, bodies: dict, records: dict, parent: dict) -> None:
    fail = preparation._fail
    if contract.get('schema') != SCHEMA or contract.get('status') != 'reviewedCurrentBuild':
        fail('externalPackageSchema', 'contract', SCHEMA, contract.get('schema'))
    if contract['nativeInputs'] != parent['nativeInputs']:
        fail('externalPackageInputs', 'selected inputs', parent['nativeInputs'], contract['nativeInputs'])
    groups = contract['nativeGroups']
    if len(groups) != 5 or {g['key'] for g in groups} != {'externalPathHash','externalKeyLookup','packageDescriptorLookup','defaultIoInitialization','defaultIoBatchDispatch'}:
        fail('externalPackageGroups', 'groups', 'five distinct reviewed groups', [g['key'] for g in groups])
    validate_native_group_windows(groups, image, bodies, records)
    witnesses = {g['key']: carrier._witnesses(g) for g in groups}
    rules = contract['hashRules']
    if (rules.get('encoding'), rules.get('caseFold'), rules.get('algorithm'), rules.get('stripExtension'), rules.get('normalizeSeparators')) != ('utf8','ascii-A-Z-only','fnv1-64',False,False):
        fail('externalPackageHashRules', 'algorithm', 'complete UTF-8 path / ASCII folding / FNV-1', rules)
    layout = contract['lookupLayout']
    fields = {'tablePointer','countBytes','rowsOffset','rowBytes','keyOffset','keyBytes','languageOffset','languageBytes','requiredKind'}
    if set(layout) != fields or any(type(v) is not int or not 0 <= v <= 4096 for v in layout.values()):
        fail('externalPackageLookupLayout', 'typed fields', sorted(fields), layout)
    # MOV/CMP operands are DWORD counts/languages and a REX.W QWORD key;
    # LEA scales each row by three QWORDs, with an implicit zero key offset.
    if layout['countBytes'] != 4 or layout['languageBytes'] != 4 or layout['keyBytes'] != 8 or layout['rowBytes'] != 3*layout['keyBytes'] or layout['keyOffset']:
        fail('externalPackageLookupLayout', 'operand widths/stride', 'DWORD count/language, three QWORDs per row, key at row base', layout)
    expected = {
        'externalPathHash': {'retainText':'488bf2', 'utf8CodePage':'b9e9fd0000', 'asciiUpperBound':'3c19',
            'asciiLowerOffset':'80c120', 'seed':'48b8'+int(rules['seed'],0).to_bytes(8,'little').hex(),
            'multiplier':'49b8'+int(rules['multiplier'],0).to_bytes(8,'little').hex(),
            'multiply':'490fafc0','xorByte':'4833c1'},
        'externalKeyLookup': {'requireExternalKind':'418338'+layout['requiredKind'].to_bytes(1,'little').hex(),
            'retainKey':'4c8bda','loadTable':'488b41'+layout['tablePointer'].to_bytes(1,'little').hex(),
            'loadCount':'448b08','tableRows':'488d70'+layout['rowsOffset'].to_bytes(1,'little').hex(),
            'rowStride':'488d1449','compareKey':'4c391cd6',
            'compareLanguage':'41394a'+layout['languageOffset'].to_bytes(1,'little').hex()},
        'packageDescriptorLookup': {'retainDescriptor':'4c8bf2','requireMode':'837a1400','requireFlags':'48837a0c00',
            'loadText':'498b0e','loadFlags':'498b460c','selectKeyFamily':'833800',
            'passExternalFlags':'4c8bc6','passExternalKey':'498bd5'}}
    for owner, values in expected.items():
        for role, raw in values.items():
            actual = witnesses[owner][role]['instructionHex']
            if actual != raw:
                fail('externalPackageInstruction', owner+'.'+role, raw, actual)
    targets = {g['key']:int(g['entryRva'],16) for g in groups}
    for role, target in [('hashExternalPath','externalPathHash'),('lookupExternalKey','externalKeyLookup')]:
        row = witnesses['packageDescriptorLookup'][role]
        raw = bytes.fromhex(row['instructionHex'])
        if len(raw) != 5 or raw[0] != 0xe8 or int(row['rva'],16)+5+struct.unpack_from('<i',raw,1)[0] != targets[target]:
            fail('externalPackageCall', role, hex(targets[target]), raw.hex())
    imported = contract['conversionImport']
    for role in ('convertSize','convertText'):
        row = witnesses['externalPathHash'][role]
        raw = bytes.fromhex(row['instructionHex'])
        if len(raw) != 6 or raw[:2] != b'\xff\x15' or int(row['rva'],16)+6+struct.unpack_from('<i',raw,2)[0] != int(imported['iatRva'],16):
            fail('externalPackageConversionCall', role, imported['iatRva'], raw.hex())
    actual = _import_at(image, int(imported['iatRva'],16))
    if imported['name'] != 'WideCharToMultiByte' or actual != imported['name']:
        fail('externalPackageConversionImport', 'IAT symbol', 'WideCharToMultiByte', actual)
    io = contract['ioDispatch']
    offset = io['ioContextOffset']
    if type(offset) is not int or not 0 < offset < 128:
        fail('externalPackageIoOffset', 'secondary context', 'positive byte displacement', offset)
    initialization = witnesses['defaultIoInitialization']
    for role, prefix, target in (
        ('primaryTable','488d05',int(io['primaryAddressPointRva'],16)),
        ('ioTable','488d05',int(io['ioAddressPointRva'],16)),
        ('storePrimaryTable','488905',int(io['primaryContextRva'],16)),
        ('storeIoTable','488905',int(io['primaryContextRva'],16)+offset)):
        row = initialization[role]
        raw = bytes.fromhex(row['instructionHex'])
        if len(raw) != 7 or raw[:3].hex() != prefix or int(row['rva'],16)+7+struct.unpack_from('<i',raw,3)[0] != target:
            fail('externalPackageIoInitialization', role, hex(target), raw.hex())
    typed = {'retainRequests':'4d8bf0','retainIoContext':'4c8be9','loadRequest':'498b3e',
             'loadPrimaryTable':'498b45'+((-offset)&255).to_bytes(1,'little').hex(),
             'adjustPrimaryContext':'498d4d'+((-offset)&255).to_bytes(1,'little').hex(),
             'passDescriptor':'488bd7','storeResult':'48894728','callbackSlot':'ff5718'}
    dispatch = witnesses['defaultIoBatchDispatch']
    for role, wanted in typed.items():
        actual = dispatch[role]['instructionHex']
        if actual != wanted:
            fail('externalPackageIoInstruction', role, wanted, actual)
    slots = io['slots']
    if len(slots) != 2 or {(s['addressPoint'],s['targetOwner']) for s in slots} != {('primaryAddressPointRva','packageDescriptorLookup'),('ioAddressPointRva','defaultIoBatchDispatch')}:
        fail('externalPackageIoSlotCoverage','slots','primary lookup and secondary batch slots',slots)
    for slot in slots:
        at = slot['offset']
        if type(at) is not int or not 0 <= at < 128 or at % 8:
            fail('externalPackageIoSlotOffset',slot['targetOwner'],'bounded QWORD slot',at)
        address = image.image_base+int(io[slot['addressPoint']],16)+at
        raw = image.bytes_at_va(address,8)
        target = image.image_base+targets[slot['targetOwner']]
        if len(raw) != 8 or struct.unpack('<Q',raw)[0] != target:
            fail('externalPackageIoSlotTarget',slot['targetOwner'],hex(target),raw.hex())
        if slot['targetOwner'] == 'packageDescriptorLookup' and dispatch['lookupSlot']['instructionHex'] != 'ff50'+at.to_bytes(1,'little').hex():
            fail('externalPackageIoLookupSlot','dispatch',at,dispatch['lookupSlot']['instructionHex'])


def observer_spec(contract: dict) -> dict:
    """Pure projection; consumers must first admit the selected native gate."""
    groups = {g['key']:g for g in contract['nativeGroups']}
    witnesses = carrier._witnesses(groups['packageDescriptorLookup'])
    callers = {}
    for kind, role in (('anonymousExternalPackagePathHash','hashExternalPath'),
                       ('anonymousExternalPackageKeyLookup','lookupExternalKey')):
        row = witnesses[role]
        callers[kind] = {int(row['rva'],16)+len(bytes.fromhex(row['instructionHex'])):'packageDescriptorLookup'}
    return {'callers':callers, 'ioAddressPointRva':contract['ioDispatch']['ioAddressPointRva'],
            'requiredKind':contract['lookupLayout']['requiredKind']}


def external_path_key(path: str, contract: dict) -> int:
    """Compute the reviewed route's key; caller must admit the native contract."""
    if not isinstance(path,str) or not path or '\0' in path:
        raise ValueError('external package path must be nonempty terminated-text content')
    rules = contract['hashRules']
    if rules['algorithm'] != 'fnv1-64' or rules['encoding'] != 'utf8' or rules['caseFold'] != 'ascii-A-Z-only' or rules['stripExtension'] or rules['normalizeSeparators']:
        raise ValueError('unsupported external package hash rules')
    result, multiplier = int(rules['seed'],0), int(rules['multiplier'],0)
    for byte in path.encode('utf-8'):
        if 65 <= byte <= 90:
            byte += 32
        result = ((result * multiplier) & ((1 << 64)-1)) ^ byte
    return result
