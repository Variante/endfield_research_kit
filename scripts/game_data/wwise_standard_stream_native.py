"""Original numeric stream reads and resident-memory provider handoff gate.

The decoder-provider command supplies one explicit selected/opened native image.
This module authenticates contracts; it does not create streams or decode media.
"""
from __future__ import annotations

import hashlib
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows
from scripts.game_data import wwise_decoder_provider_native as preparation
from scripts.game_data.wwise_package_transform_native import load_transform_contract
from scripts.game_data.wwise_source_provider_dispatch_native import load_dispatch_contract
from scripts.game_data.wwise_provider_storage_native import load_storage_contract
from scripts.game_data.wwise_package_result_native import load_result_contract
from scripts.game_data.wwise_package_read_native import load_read_contract
from scripts.game_data.wwise_external_package_native import load_package_contract, _import_at
from scripts.game_data.wwise_codec_factory_native import load_codec_contract

CONTRACT_PATH = CONTRACTS_DIR / 'wwise_standard_stream_native.json'
SCHEMA = 'endfield.wwise-standard-stream-native.v2'
DEPENDENCIES = {
    'standardConstructor': ('wwise_package_transform_native','queuedReceiverConstructor'),
    'providerOpen': ('wwise_source_provider_dispatch_native','anonymousProviderStorageOpen'),
    'descriptorStorage': ('wwise_provider_storage_native','providerDescriptorStorage'),
    'completionDispatch': ('wwise_package_result_native','providerCompletionDispatch'),
    'readQueue': ('wwise_package_transform_native','anonymousReceiverReadQueue'),
    'queuedReadCompletion': ('wwise_package_transform_native','queuedReceiverTransferCompletion'),
    'transferDispatch': ('wwise_package_transform_native','transferCompletionDispatcher'),
    'mediaTransform': ('wwise_package_transform_native','alignedPackageTransform'),
    'ioReadBatch': ('wwise_package_read_native','defaultIoReadBatch'),
    'ioReadCompletion': ('wwise_package_read_native','defaultIoReadCompletion'),
    'ioOpenBatch': ('wwise_external_package_native','defaultIoBatchDispatch'),
    'packageLookup': ('wwise_external_package_native','packageDescriptorLookup'),
    'memoryFactory': ('wwise_provider_storage_native','alternateProviderFactory'),
    'mediaPreparation': ('wwise_codec_factory_native','mediaSourcePreparation'),
}
LOADERS = {'wwise_package_transform_native':load_transform_contract,
           'wwise_source_provider_dispatch_native':load_dispatch_contract,
           'wwise_provider_storage_native':load_storage_contract,
           'wwise_package_result_native':load_result_contract,
           'wwise_package_read_native':load_read_contract,
           'wwise_external_package_native':load_package_contract,
           'wwise_codec_factory_native':load_codec_contract}
LEAF_DEPENDENCIES = {
    'transferInitializer': ('wwise_package_transform_native','transferInitializerLeaf','field'),
    'ioTransformWrapper': ('wwise_package_read_native','transformLeaf','field'),
    'memoryConstructor': ('wwise_provider_storage_native','alternateProviderConstructor','leafWindows'),
}


def load_standard_stream_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-standard-stream')
    return value


def collect_groups(contract, dependencies=None, *, owner_cache=None):
    """Reuse existing group owners without copying their catalogs or images."""
    rows = contract.get('nativeGroupDependencies')
    if not isinstance(rows,list) or len(rows) != len(DEPENDENCIES) or {r['key'] for r in rows} != set(DEPENDENCIES):
        preparation._fail('standardStreamDependencies','groups','complete named existing owners',rows)
    owners = owner_cache if owner_cache is not None else {}
    groups = list(contract['nativeGroups'])
    for row in rows:
        if (row['ownerContract'],row['ownerGroup']) != DEPENDENCIES[row['key']]:
            preparation._fail('standardStreamDependencyOwner',row['key'],DEPENDENCIES[row['key']],row)
        name = row['ownerContract']
        if name not in owners:
            owners[name] = dependencies[name] if dependencies is not None else LOADERS[name]()
        owner = owners[name]
        if owner.get('nativeInputs') != contract['nativeInputs']:
            preparation._fail('standardStreamDependencyInputs',row['key'],'same selected triplet','different declarations')
        group = next((g for g in owner.get('nativeGroups',[]) if g.get('key') == row['ownerGroup']),None)
        if group is None:
            preparation._fail('standardStreamDependencyMissing',row['key'],row['ownerGroup'],'missing owner group')
        groups.append({**group,'key':row['key']})
    validate_native_group_declarations(groups)
    return groups


def collect_leaf_dependencies(contract, owners):
    rows = contract.get('nativeLeafDependencies')
    if not isinstance(rows,list) or len(rows) != len(LEAF_DEPENDENCIES) or {r['key'] for r in rows} != set(LEAF_DEPENDENCIES):
        preparation._fail('standardStreamLeafDependencies','leaves','complete existing leaf owners',rows)
    result = {}
    for row in rows:
        if (row['ownerContract'],row['ownerField'],row['ownerShape']) != LEAF_DEPENDENCIES[row['key']]:
            preparation._fail('standardStreamLeafOwner',row['key'],LEAF_DEPENDENCIES[row['key']],row)
        owner = owners[row['ownerContract']]
        leaf = (owner.get(row['ownerField']) if row['ownerShape'] == 'field' else
                next((v for v in owner.get('leafWindows',[]) if v.get('key') == row['ownerField']),None))
        if not isinstance(leaf,dict):
            preparation._fail('standardStreamLeafMissing',row['key'],row['ownerField'],'missing owner leaf')
        result[row['key']] = leaf
    return result


def _validate_leaf_bytes(leaves,image,records):
    groups = {}
    for name,leaf in leaves.items():
        start,length = int(leaf['entryRva'],16),leaf['bodyLength']
        if type(length) is not int or not 1 <= length <= 256 or any(r[0] < start+length and r[1] > start for r in records.values()):
            preparation._fail('standardStreamLeafExtent',name,'bounded existing unwindless leaf',length)
        raw = image.bytes_at_va(image.image_base+start,length)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != leaf['bodySha256'] or raw[-1:] != b'\xc3':
            preparation._fail('standardStreamLeafBytes',name,leaf['bodySha256'],hashlib.sha256(raw).hexdigest())
        if 'bodyHex' in leaf and raw != bytes.fromhex(leaf['bodyHex']):
            preparation._fail('standardStreamLeafBody',name,'existing owner bytes','different bytes')
        if 'boundaryHex' in leaf:
            boundary = bytes.fromhex(leaf['boundaryHex'])
            if image.bytes_at_va(image.image_base+start+length,len(boundary)) != boundary:
                preparation._fail('standardStreamLeafBoundary',name,boundary.hex(),'different bytes')
        for row in leaf['instructionWitnesses']:
            at = int(row['rva'],16)-start;code = bytes.fromhex(row['instructionHex'])
            if at < 0 or at+len(code) > length or raw[at:at+len(code)] != code:
                preparation._fail('standardStreamLeafInstruction',name+'.'+row['role'],code.hex(),'different bytes')
        groups[name] = {'key':name,'entryRva':leaf['entryRva'],'windows':[{'rva':leaf['entryRva'],'bodyLength':length}]}
    return groups


def _read_instruction(image,groups,row,length):
    owner = groups.get(row.get('group'))
    start = int(row['rva'],16)
    if owner is None or not any(int(w['rva'],16) <= start and start+length <= int(w['rva'],16)+w['bodyLength'] for w in owner['windows']):
        preparation._fail('standardStreamInstructionExtent',row.get('group'),'within authenticated owner window',row['rva'])
    return image.bytes_at_va(image.image_base+start,length)


def validate_standard_stream_bytes(contract,image,bodies,records,parent,*,dependencies=None):
    fail = preparation._fail
    if contract.get('schema') != SCHEMA or contract.get('status') != 'reviewedCurrentBuild':
        fail('standardStreamSchema','contract',SCHEMA,contract.get('schema'))
    if contract['nativeInputs'] != parent['nativeInputs']:
        fail('standardStreamInputs','parent','same selected triplet','different declarations')
    owners = {}
    all_groups = collect_groups(contract,dependencies,owner_cache=owners)
    validate_native_group_windows(all_groups,image,bodies,records)
    groups = {g['key']:g for g in all_groups}
    groups.update(_validate_leaf_bytes(collect_leaf_dependencies(contract,owners),image,records))
    imported = contract.get('readImportDependency')
    if imported != {'ownerContract':'wwise_package_read_native','ownerField':'readImport'}:
        fail('standardStreamReadImportOwner','readImportDependency','existing package read import',imported)
    imported = owners[imported['ownerContract']][imported['ownerField']]
    actual = _import_at(image,int(imported['iatRva'],16))
    if imported['name'] != 'ReadFileEx' or actual != imported['name']:
        fail('standardStreamReadImport','ReadFileEx','owning import symbol',actual)
    call = next(r for r in groups['ioReadBatch']['instructionWitnesses'] if r['role'] == 'callReadFileEx')
    raw = bytes.fromhex(call['instructionHex'])
    target = int(call['rva'],16)+6+struct.unpack_from('<i',raw,2)[0] if len(raw) == 6 and raw[:2] == b'\xff\x15' else None
    if target != int(imported['iatRva'],16):
        fail('standardStreamReadImportCall','ioReadBatch',imported['iatRva'],target)
    layout = contract['layout']
    if not isinstance(layout,dict) or not layout or any(type(v) is not int or not 0 <= v <= 4096 for v in layout.values()):
        fail('standardStreamLayout','layout','bounded scalar offsets',layout)
    covered = set()
    for row in preparation._rows(contract['fieldBindings'],'fieldBindings',64):
        field,width = row['field'],row['displacementBytes']
        value = layout[field]
        if type(width) is not int or width not in (1,4) or value >= 1 << (width*8-1):
            fail('standardStreamDisplacement',field,'bounded signed displacement',value)
        expected = bytes.fromhex(row['prefixHex'])+value.to_bytes(width,'little')+bytes.fromhex(row.get('suffixHex',''))
        actual = _read_instruction(image,groups,row,len(expected))
        if actual != expected:
            fail('standardStreamField',field,expected.hex(),actual.hex())
        covered.add(field)
    for row in preparation._rows(contract['instructionBindings'],'instructionBindings',64):
        expected = bytes.fromhex(row['instructionHex'])
        if not 1 <= len(expected) <= 15:
            fail('standardStreamInstruction','length','1..15 bytes',len(expected))
        actual = _read_instruction(image,groups,row,len(expected))
        if actual != expected:
            fail('standardStreamInstruction',row['group'],expected.hex(),actual.hex())
    for row in preparation._rows(contract['directEdges'],'directEdges',64):
        raw = _read_instruction(image,groups,row,5)
        target = groups.get(row['targetGroup'])
        opcode = {'call':0xe8,'tailJump':0xe9}.get(row['kind'])
        actual = int(row['rva'],16)+5+struct.unpack_from('<i',raw,1)[0] if raw[0] == opcode else None
        expected = int(target['entryRva'],16) if target else None
        if target is None or actual != expected:
            fail('standardStreamEdge',row['group']+'.'+row['targetGroup'],expected,actual)
    for row in preparation._rows(contract['addressPointBindings'],'addressPointBindings',32):
        slot = row['slot']
        if type(slot) is not int or not 0 <= slot <= 256 or slot % 8 or row['targetGroup'] not in groups:
            fail('standardStreamSlot',row['key'],'bounded QWORD slot/owned target',row)
        if 'slotField' in row:
            if layout[row['slotField']] != slot:
                fail('standardStreamSlotField',row['slotField'],layout[row['slotField']],slot)
            covered.add(row['slotField'])
        raw = image.bytes_at_va(image.image_base+int(row['addressPointRva'],16)+slot,8)
        expected = image.image_base+int(groups[row['targetGroup']]['entryRva'],16)
        if len(raw) != 8 or hashlib.sha256(raw).hexdigest() != row['sha256'] or struct.unpack('<Q',raw)[0] != expected:
            fail('standardStreamSlotBytes',row['key'],hex(expected),raw.hex())
    if covered != set(layout):
        fail('standardStreamFieldCoverage','layout',sorted(layout),sorted(covered))
