"""Selected Wwise package numeric lookup and external-path hashing.

This gate reuses the decoder-provider validator's opened images. Computed keys
are conditional static identities; they never admit a captured lookup result.

Evidence and admission boundary:

The reviewed package contract (`wwise_external_package_native.json`) now owns
the numeric branch and package lifecycle alongside external hashing. Numeric
lookup retains the descriptor's DWORD file ID and compares ordered key/language
pairs in stored rows. It uses the package's selected language only when
requested, otherwise zero. Bank codec classes select a present nonempty bank
table; a key miss in that table does not fall through to the sound table. Other
classes, or an absent/empty bank table, use the sound table. Loaded packages
are searched in linked-list order, with the first successful row winning;
descriptor allocation failure terminates the search. The returned descriptor
retains the package and stores the row's byte count and block geometry.

Original package load now reads the admitted encrypted physical headers,
executes the existing aligned XOR helper and assigns the original table
pointers. Those tables agree byte-for-byte with the maintained reader. This
cohort covers the selected four-sector header shape, available allocations,
supplied standard-stream reads and existing notification-registration state; it
does not generalize malformed-header safety. Successful load prepends its
package. A separate exact package-ID routine moves the first matching package
to the head, so newest load alone does not determine all later precedence.
Removal unlinks the entry and releases the list reference; selected descriptors
retain their own reference. Package-ID collision, destruction after the final
release, language callback updates and concurrent list mutation remain
separate.

The stronger numeric-output cohort loads the physical headers through those
original routines before forwarding the original source request unchanged to
native package lookup. Its returned package pointer and geometry select the
encoded bytes on disk. Original aligned media XOR produces exactly the
independently authenticated clear WEM, which reaches original resident
publication, preparation and context PCM with identical complete floats to the
earlier cohort. Package-load call sequence, stream/device interfaces, available
allocation and pointer lifetime remain supplied. Thus offline row selection,
header admission and byte transformation are now original native computations;
the game's actual load/reorder sequence and standard-stream scheduling still
need closure. Event/queue execution remains a separately authenticated cohort.
"""
from __future__ import annotations

import struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows, validate_native_group_declarations
from scripts.game_data.wwise_package_transform_native import load_transform_contract
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation

CONTRACT_PATH = CONTRACTS_DIR / 'wwise_external_package_native.json'
SCHEMA = 'endfield.wwise-external-package-native.v3'


def load_package_contract(path: Path = CONTRACT_PATH) -> dict:
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status='reviewedCurrentBuild', label='wwise-external-package')
    return value


def _package_groups(contract: dict, dependency_contract: dict | None = None) -> list[dict]:
    """Use the existing transform owner on the caller's already opened image."""
    dependencies = contract.get('nativeGroupDependencies')
    expected = [{'key':'headerAlignedTransform','ownerContract':'wwise_package_transform_native','ownerGroup':'alignedPackageTransform'}]
    if dependencies != expected:
        preparation._fail('packageGroupDependency','nativeGroupDependencies',expected,dependencies)
    owner = dependency_contract if dependency_contract is not None else load_transform_contract()
    if owner.get('nativeInputs') != contract['nativeInputs']:
        preparation._fail('packageGroupDependencyInputs','aligned transform','same selected inputs','different declarations')
    group = next((g for g in owner.get('nativeGroups',[]) if g.get('key') == dependencies[0]['ownerGroup']),None)
    if group is None:
        preparation._fail('packageGroupDependencyMissing','aligned transform',dependencies[0]['ownerGroup'],'missing owner group')
    groups = list(contract['nativeGroups'])+[{**group,'key':dependencies[0]['key']}]
    validate_native_group_declarations(groups)
    return groups


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
    owned = contract['nativeGroups']
    names = {'externalPathHash','externalKeyLookup','packageDescriptorLookup','defaultIoInitialization',
             'defaultIoBatchDispatch','numericKeyLookup','numericBankKeySearch','packageAdmission',
             'packageReprioritization','packageRemoval','packageHeaderLoad','packageTableAssignment','packageLanguageSelection'}
    if len(owned) != len(names) or {g['key'] for g in owned} != names:
        fail('externalPackageGroups', 'groups', 'distinct reviewed package groups', [g['key'] for g in owned])
    groups = _package_groups(contract)
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
    _validate_numeric_lookup(contract, witnesses, targets, fail)
    _validate_package_lifecycle(contract, witnesses, targets, fail)
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


def _validate_numeric_lookup(contract: dict, witnesses: dict, targets: dict, fail) -> None:
    """Bind numeric table, package-list and result geometry to owned operands."""
    layout = contract.get('numericLookup')
    fields = {'bankTablePointer','soundTablePointer','countBytes','rowsOffset','rowBytes','keyBytes',
              'languageOffset','languageBytes','packageLanguageOffset','packageLanguageBytes',
              'languageFlagOffset','bankCodecBase','bankCodecLastDelta','loadedPackagesOffset',
              'nextPackageOffset','packageReferenceOffset','rowLengthOffset','rowBlockOffset',
              'rowBlockBytesOffset','descriptorLengthOffset','descriptorBlockOffset',
              'descriptorBlockBytesOffset','descriptorPackageOffset','descriptorByteOffset',
              'descriptorNumericKeyOffset','allocationFailureStatus'}
    if not isinstance(layout, dict) or set(layout) != fields or any(type(v) is not int or not 0 <= v <= 127 for v in layout.values()):
        fail('numericPackageLayout', 'numericLookup', 'complete bounded scalar declarations', layout)
    if (layout['countBytes'],layout['keyBytes'],layout['languageBytes'],layout['packageLanguageBytes'],
            layout['rowBytes'],layout['descriptorLengthOffset']) != (4,4,4,2,5*4,0):
        fail('numericPackageLayout', 'operand widths/stride', 'DWORD count/key/language, WORD package language, five DWORD row, result length at base', layout)
    byte = lambda key: layout[key].to_bytes(1,'little').hex()
    negative = lambda key: ((-layout[key])&255).to_bytes(1,'little').hex()
    expected = {
        'numericKeyLookup': {
            'loadCodec':'418b4004','bankCodecZero':'85c0',
            'bankCodecOffset':'83c0'+negative('bankCodecBase'),
            'bankCodecRange':'83f8'+byte('bankCodecLastDelta'),
            'bankTable':'4c8b41'+byte('bankTablePointer'),'bankCount':'41833800',
            'soundTable':'488b41'+byte('soundTablePointer'),'soundCount':'8b10',
            'languageFlag':'413859'+byte('languageFlagOffset'),
            'languageId':'0fb779'+byte('packageLanguageOffset'),
            'soundRows':'488d70'+byte('rowsOffset'),'soundRowStride':'488d1489',
            'compareNumericKey':'44391c96','compareLanguage':'41394a'+byte('languageOffset')},
        'numericBankKeySearch': {
            'bankRows':'498d78'+byte('rowsOffset'),'languageFlag':'4584c9',
            'languageId':'0fb759'+byte('packageLanguageOffset'),'bankCount':'458b00',
            'bankRowStride':'488d1489','compareNumericKey':'44391c97',
            'compareLanguage':'413949'+byte('languageOffset')},
        'packageDescriptorLookup': {
            'loadedPackages':'498b5c24'+byte('loadedPackagesOffset'),
            'numericId':'418b6e08','passNumericFlags':'4c8bc6','passNumericKey':'8bd5',
            'packageNext':'488b5b'+byte('nextPackageOffset'),
            'allocationFailureStatus':'83fe'+byte('allocationFailureStatus'),
            'allocationFailureStops':'741a',
            'rowLength':'8b46'+byte('rowLengthOffset'),'rowBlockOffset':'8b4e'+byte('rowBlockOffset'),
            'rowBlockBytes':'8b46'+byte('rowBlockBytesOffset'),
            'storeLength':'488901','storeBlockOffset':'488948'+byte('descriptorBlockOffset'),
            'storeBlockBytes':'8941'+byte('descriptorBlockBytesOffset'),
            'storePackage':'488958'+byte('descriptorPackageOffset'),
            'rowByteOffset':'0faf4e'+byte('rowBlockBytesOffset'),
            'storeByteOffset':'8948'+byte('descriptorByteOffset'),
            'storeNumericKey':'8968'+byte('descriptorNumericKeyOffset'),
            'incrementReference':'ff43'+byte('packageReferenceOffset')},
    }
    for owner, values in expected.items():
        for role, raw in values.items():
            actual = witnesses[owner][role]['instructionHex']
            if actual != raw:
                fail('numericPackageInstruction', owner+'.'+role, raw, actual)
    for owner, role, target, opcode in (
            ('numericKeyLookup','tailBankSearch','numericBankKeySearch',0xe9),
            ('packageDescriptorLookup','lookupNumericKey','numericKeyLookup',0xe8)):
        witness = witnesses[owner][role];raw = bytes.fromhex(witness['instructionHex'])
        actual = int(witness['rva'],16)+5+struct.unpack_from('<i',raw,1)[0] if len(raw) == 5 and raw[0] == opcode else None
        if actual != targets[target]:
            fail('numericPackageEdge', owner+'.'+role, hex(targets[target]), actual)


def _validate_package_lifecycle(contract: dict, witnesses: dict, targets: dict, fail) -> None:
    layout = contract.get('packageLifecycle')
    fields = {'packageIdOffset','nextPackageOffset','referenceOffset','languageTableOffset',
              'bankTableOffset','soundTableOffset','externalTableOffset','headerPrefixBytes',
              'languageSizeOffset','bankSizeOffset','soundSizeOffset','externalSizeOffset',
              'notificationRegistrationOffset','initialReference','loadedHeadOffset','loadedTailOffset',
              'loadedCountOffset','packageSourceOffset','languageOffset'}
    if not isinstance(layout,dict) or set(layout) != fields or any(type(v) is not int or not 0 <= v <= 255 for v in layout.values()):
        fail('packageLifecycleLayout','packageLifecycle','complete bounded scalar declarations',layout)
    for numeric, lifecycle in (('bankTablePointer','bankTableOffset'),('soundTablePointer','soundTableOffset'),
            ('packageLanguageOffset','languageOffset'),('nextPackageOffset','nextPackageOffset'),
            ('packageReferenceOffset','referenceOffset'),('loadedPackagesOffset','loadedHeadOffset')):
        if contract['numericLookup'][numeric] != layout[lifecycle]:
            fail('packageLifecycleJoin',numeric,contract['numericLookup'][numeric],layout[lifecycle])
    byte = lambda key: layout[key].to_bytes(1,'little').hex()
    word = lambda key: layout[key].to_bytes(4,'little').hex()
    expected = {
        'packageAdmission':{'nextWriteEmpty':'488970'+byte('nextPackageOffset'),
            'nextWritePopulated':'488948'+byte('nextPackageOffset'),'packageId':'8b40'+byte('packageIdOffset')},
        'packageReprioritization':{'comparePackageId':'3958'+byte('packageIdOffset'),
            'nextRead':'488b40'+byte('nextPackageOffset'),'nextWriteEmpty':'488948'+byte('nextPackageOffset'),
            'nextWritePopulated':'488948'+byte('nextPackageOffset')},
        'packageRemoval':{'comparePackageId':'3959'+byte('packageIdOffset'),
            'nextRead':'488b49'+byte('nextPackageOffset'),'releaseReference':'8341'+byte('referenceOffset')+'ff',
            'destroyIfZero':'ff5008'},
        'packageHeaderLoad':{'packageIdStore':'8947'+byte('packageIdOffset'),
            'initialReference':'c747'+byte('referenceOffset')+word('initialReference'),
            'retainStream':'488947'+byte('packageSourceOffset'),
            'callbackRegistrationFlag':'80bb'+word('notificationRegistrationOffset')+'00',
            'acceptPlainMagic':'3d414b504b','acceptEncryptedMagic':'3d3a297844'},
        'packageTableAssignment':{'bankBytes':'8b42'+byte('bankSizeOffset'),
            'soundBytes':'418b03','externalBytes':'448b4a'+byte('externalSizeOffset'),
            'addressLanguageSize':'488d7a'+byte('languageSizeOffset'),
            'addressSoundSize':'4c8d5a'+byte('soundSizeOffset'),
            'languageBytes':'8b0f','headerPrefix':'4883c1'+byte('headerPrefixBytes'),
            'languageTable':'498952'+byte('languageTableOffset'),'bankTable':'498952'+byte('bankTableOffset'),
            'soundTable':'498952'+byte('soundTableOffset'),'externalTable':'498942'+byte('externalTableOffset')},
        'packageLanguageSelection':{'resetLanguage':'668941'+byte('languageOffset'),
            'languageTable':'488b49'+byte('languageTableOffset'),'retainLanguage':'668943'+byte('languageOffset')},
    }
    for owner, values in expected.items():
        for role, raw in values.items():
            actual = witnesses[owner][role]['instructionHex']
            if actual != raw:
                fail('packageLifecycleInstruction',owner+'.'+role,raw,actual)
    context = int(contract['ioDispatch']['primaryContextRva'],16)
    for owner, role, field, prefix in (
            ('packageAdmission','headRead','loadedHeadOffset','488b0d'),
            ('packageAdmission','headWriteEmpty','loadedHeadOffset','488905'),
            ('packageAdmission','headWritePopulated','loadedHeadOffset','488905'),
            ('packageAdmission','tailWriteEmpty','loadedTailOffset','488905'),
            ('packageAdmission','countIncrement','loadedCountOffset','ff05'),
            ('packageReprioritization','headRead','loadedHeadOffset','4c8b0d'),
            ('packageReprioritization','headWritePopulated','loadedHeadOffset','488905'),
            ('packageReprioritization','countIncrement','loadedCountOffset','ff05'),
            ('packageRemoval','headRead','loadedHeadOffset','4c8b0d'),
            ('packageRemoval','headRemove','loadedHeadOffset','4c8905'),
            ('packageRemoval','tailRemove','loadedTailOffset','488915'),
            ('packageRemoval','countRemove','loadedCountOffset','ff0d')):
        row = witnesses[owner][role];raw = bytes.fromhex(row['instructionHex']);head = bytes.fromhex(prefix)
        actual = int(row['rva'],16)+len(raw)+struct.unpack_from('<i',raw,len(head))[0] if len(raw) == len(head)+4 and raw.startswith(head) else None
        if actual != context+layout[field]:
            fail('packageLifecycleGlobal',owner+'.'+role,hex(context+layout[field]),actual)
    edges = contract.get('lifecycleEdges')
    expected_edges = {('packageAdmission','loadHeader','packageHeaderLoad'),
                      ('packageHeaderLoad','headerTransform','headerAlignedTransform'),
                      ('packageHeaderLoad','tableAssignment','packageTableAssignment'),
                      ('packageHeaderLoad','languageSelection','packageLanguageSelection')}
    if not isinstance(edges,list) or len(edges) != len(expected_edges) or {(r['group'],r['role'],r['target']) for r in edges} != expected_edges:
        fail('packageLifecycleEdges','lifecycleEdges','complete named lifecycle calls',edges)
    for edge in edges:
        row = witnesses[edge['group']][edge['role']];raw = bytes.fromhex(row['instructionHex'])
        actual = int(row['rva'],16)+5+struct.unpack_from('<i',raw,1)[0] if len(raw) == 5 and raw[0] == 0xe8 else None
        if actual != targets[edge['target']]:
            fail('packageLifecycleCall',edge['role'],hex(targets[edge['target']]),actual)


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
