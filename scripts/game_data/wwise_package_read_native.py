"""Selected default package read, platform completion and pre-transform entry."""
import hashlib
import struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation
from scripts.game_data import wwise_external_package_native as package_native

SCHEMA = 'endfield.wwise-package-read-native.v1'
CONTRACT_PATH = CONTRACTS_DIR/'wwise_package_read_native.json'


def load_read_contract(path: Path = CONTRACT_PATH) -> dict:
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status='reviewedCurrentBuild', label='wwise-package-read')
    return value


def validate_read_bytes(contract, image, bodies, records, parent, package, result):
    fail = preparation._fail
    if contract.get('schema') != SCHEMA or contract.get('status') != 'reviewedCurrentBuild':
        fail('packageReadSchema', 'contract', SCHEMA, contract.get('schema'))
    if any(c['nativeInputs'] != parent['nativeInputs'] for c in (contract, package, result)):
        fail('packageReadInputs', 'dependencies', parent['nativeInputs'], contract['nativeInputs'])
    groups = contract['nativeGroups']
    if len(groups) != 2 or {g['key'] for g in groups} != {'defaultIoReadBatch','defaultIoReadCompletion'}:
        fail('packageReadGroups', 'groups', 'two complete read groups', [g['key'] for g in groups])
    validate_native_group_windows(groups, image, bodies, records)
    witnesses = {g['key']: carrier._witnesses(g) for g in groups}
    b,t,o,c = (contract[name] for name in ('batchLayout','transferLayout','overlappedLayout','cookieLayout'))
    for layout, names in ((b,{'stride','descriptor','transfer'}), (t,{'filePosition','requestedBytes','transformBytes','buffer','callback','cookie'}),
                          (o,{'positionLow','positionHigh','transfer'}), (c,{'primaryIo','descriptor'})):
        if set(layout) != names or any(type(v) is not int or not 0 <= v < 128 for v in layout.values()):
            fail('packageReadLayout', 'typed fields', sorted(names), layout)
    if b['descriptor'] or t['filePosition'] or c['primaryIo']:
        fail('packageReadImplicitOffsets', 'implicit loads', 'zero', (b,t,c))
    if contract['descriptorLayout'] != result['resultLayout']:
        fail('packageReadDescriptorLayout', 'result dependency', result['resultLayout'], contract['descriptorLayout'])
    handle_offset=contract['descriptorHandleOffset']
    if type(handle_offset) is not int or not 0<=handle_offset<128:
        fail('packageReadHandleLayout','file handle','bounded field offset',handle_offset)
    byte = lambda value: value.to_bytes(1,'little').hex()
    expected = {
      'defaultIoReadBatch': {'retainBatch':'498be8','retainIo':'488bf9','adjustPrimaryIo':'4c8d79f8','retainCount':'448bf2',
        'batchHead':'0f104500','batchTransfer':'f20f1045'+byte(b['transfer']), 'cookieIo':'4c8938',
        'cookieDescriptor':'4c8950'+byte(c['descriptor']), 'storeCookie':'488946'+byte(t['cookie']),
        'storeTransfer':'488973'+byte(o['transfer']), 'loadPositionLow':'8b06','loadPositionHigh':'488b06','shiftPositionHigh':'48c1e820',
        'storePositionLow':'8943'+byte(o['positionLow']), 'storePositionHigh':'8943'+byte(o['positionHigh']),
        'loadRequestedBytes':'448b46'+byte(t['requestedBytes']), 'loadBuffer':'488b56'+byte(t['buffer']),
        'loadFileHandle':'498b4a'+byte(handle_offset),'passCallback':'4c896c2420','nextBatch':'4883c5'+byte(b['stride'])},
      'defaultIoReadCompletion': {'loadTransfer':'498b58'+byte(o['transfer']), 'retainError':'448bd1',
        'loadCookie':'488b4b'+byte(t['cookie']), 'loadCookieIo':'488b11','testError':'4585d2',
        'loadDescriptor':'488b49'+byte(c['descriptor']), 'passTransfer':'488bd3','successStatus':'bf01000000',
        'passStatus':'8bd7','passCompletionTransfer':'488bcb','loadTransferCallback':'488b43'+byte(t['callback']),
        'tailTransferCallback':'48ffe0'}}
    for owner, values in expected.items():
        for role, raw in values.items():
            actual = witnesses[owner][role]['instructionHex']
            if actual != raw:
                fail('packageReadInstruction', owner+'.'+role, raw, actual)
    def target(row, opcode):
        raw=bytes.fromhex(row['instructionHex'])
        if not raw.startswith(opcode):
            fail('packageReadTargetOpcode', row['role'], opcode.hex(), raw.hex())
        return int(row['rva'],16)+len(raw)+int.from_bytes(raw[-(1 if len(raw)==2 else 4):],'little',signed=True)
    slot=contract['readSlot']
    entry=next(g['entryRva'] for g in groups if g['key']=='defaultIoReadBatch')
    if slot['addressPointRva']!=package['ioDispatch']['ioAddressPointRva'] or slot['targetOwner']!='defaultIoReadBatch' or type(slot['offset']) is not int or not 0<=slot['offset']<128 or slot['offset']%8:
        fail('packageReadSlot', 'default I/O slot', 'validated package address point / read slot', slot)
    slot_bytes=image.bytes_at_va(image.image_base+int(slot['addressPointRva'],16)+slot['offset'],8)
    if len(slot_bytes)!=8:
        fail('packageReadSlotTarget','read slot','complete QWORD target',slot_bytes.hex())
    actual=struct.unpack('<Q',slot_bytes)[0]
    if actual!=image.image_base+int(entry,16):
        fail('packageReadSlotTarget', 'read slot', entry, hex(actual-image.image_base))
    batch, completion=witnesses['defaultIoReadBatch'],witnesses['defaultIoReadCompletion']
    callback=next(g['entryRva'] for g in groups if g['key']=='defaultIoReadCompletion')
    if target(batch['completionCallback'],bytes.fromhex('4c8d2d'))!=int(callback,16):
        fail('packageReadCallbackTarget', 'read callback', callback, batch['completionCallback'])
    iat=contract['readImport']
    if iat['name']!='ReadFileEx' or target(batch['callReadFileEx'],b'\xff\x15')!=int(iat['iatRva'],16) or package_native._import_at(image,int(iat['iatRva'],16))!=iat['name']:
        fail('packageReadImport', 'read operation', 'ReadFileEx import', iat)
    leaf=contract['transformLeaf']; raw=bytes.fromhex(leaf['bodyHex']); start=int(leaf['entryRva'],16)
    if len(raw)!=leaf['bodyLength'] or hashlib.sha256(raw).hexdigest()!=leaf['bodySha256'] or image.bytes_at_va(image.image_base+start,len(raw))!=raw:
        fail('packageReadTransformBytes', 'bounded complete leaf', leaf['bodySha256'], hashlib.sha256(raw).hexdigest())
    if any(at < start+len(raw) and record[1] > start for at,record in records.items()):
        fail('packageReadTransformLeaf', 'unwindless leaf', 'no overlapping unwind window', leaf['entryRva'])
    lw={w['role']:w for w in leaf['instructionWitnesses']}
    for row in lw.values():
        at=int(row['rva'],16); code=bytes.fromhex(row['instructionHex'])
        if not start<=at or at+len(code)>start+len(raw) or image.bytes_at_va(image.image_base+at,len(code))!=code:
            fail('packageReadTransformWitness', row['role'], 'within authenticated complete leaf', row)
    wanted={'testFlag':'8079'+byte(leaf['encryptionFlagOffset'])+'00','retainTransfer':'488bc2',
      'loadPositionLow':'448b0a','loadTransformBytes':'448b42'+byte(t['transformBytes']),
      'subtractDescriptorOffset':'442b49'+byte(result['resultLayout']['byteOffset']),
      'loadKeyLow':'8b51'+byte(result['resultLayout']['keyLow']), 'loadBuffer':'488b48'+byte(t['buffer']), 'return':'c3'}
    for role,code in wanted.items():
        row=lw[role]; at=int(row['rva'],16)
        if row['instructionHex']!=code or not start<=at<start+len(raw) or image.bytes_at_va(image.image_base+at,len(bytes.fromhex(code))).hex()!=code:
            fail('packageReadTransformInstruction', role, code, row)
    if target(lw['skipTransform'],b'\x74')!=int(lw['return']['rva'],16) or target(lw['tailTransform'],b'\xe9')!=int(leaf['targetRva'],16):
        fail('packageReadTransformBranch', 'leaf', 'reviewed return/tail targets', leaf)
    if target(completion['callTransform'],b'\xe8')!=start or target(completion['rejectError'],b'\x75')!=int(completion['passStatus']['rva'],16):
        fail('packageReadSuccessBranch', 'completion', 'zero-error transform before status callback', completion)


def observer_spec(contract, package):
    group=next(g for g in contract['nativeGroups'] if g['key']=='defaultIoReadCompletion')
    row=carrier._witnesses(group)['callTransform']
    return {'transformCallerReturnRva':hex(int(row['rva'],16)+len(bytes.fromhex(row['instructionHex']))),
            'ioAddressPointRva':contract['readSlot']['addressPointRva'],
            'primaryIoAddressPointRva':package['ioDispatch']['primaryAddressPointRva']}
