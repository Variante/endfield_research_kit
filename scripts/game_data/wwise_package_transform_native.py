"""Selected native aligned package XOR path and anonymous callback dispatch."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows
from scripts.game_data.wwise_owner_carrier_native import _witnesses
from scripts.game_data.wwise_decoder_provider_native import _fail
from scripts.game_data.wwise_package import KEY_SEED_XOR, KEY_MULTIPLIER

SCHEMA='endfield.wwise-package-transform-native.v4'
CONTRACT_PATH=CONTRACTS_DIR/'wwise_package_transform_native.json'


def load_transform_contract(path=CONTRACT_PATH):
    value,_=read_reviewed_contract(path,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-package-transform')
    return value


def validate_transform_bytes(contract,image,bodies,records,read,result):
    if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewedCurrentBuild':
        _fail('packageTransformSchema','contract',SCHEMA,contract.get('schema'))
    if contract['nativeInputs']!=read['nativeInputs'] or result['nativeInputs']!=read['nativeInputs']:
        _fail('packageTransformInputs','read dependency',read['nativeInputs'],contract['nativeInputs'])
    groups=contract['nativeGroups']
    names={'alignedPackageTransform','transferCompletionDispatcher','deviceTransferProducer','anonymousReceiverReadQueue','primaryProviderTransferCompletion','queuedReceiverConstructor','queuedReceiverTransferCompletion'}
    if len(groups)!=len(names) or {g['key'] for g in groups}!=names:
        _fail('packageTransformGroups','groups',sorted(names),[g['key'] for g in groups])
    transform=next(g for g in groups if g['key']=='alignedPackageTransform')
    if transform['entryRva']!=read['transformLeaf']['targetRva']:
        _fail('packageTransformTarget','read leaf',read['transformLeaf']['targetRva'],transform['entryRva'])
    validate_native_group_windows(groups,image,bodies,records)
    _validate_transfer_protocol(contract,image,records,read,result)
    algorithm={'name':'position-indexed-little-endian-xor','seedXor':KEY_SEED_XOR,'multiply':KEY_MULTIPLIER,'wordBytes':4,'provedOffsetAlignment':4}
    if contract['algorithm']!=algorithm:
        _fail('packageTransformAlgorithm','offline implementation',algorithm,contract['algorithm'])
    xor=KEY_SEED_XOR.to_bytes(4,'little').hex(); multiply=KEY_MULTIPLIER.to_bytes(4,'little').hex()
    w=_witnesses(transform)
    expected={'retainOffset':'418bd9','retainAlignment':'458bd9','wordOffset':'c1eb02','retainLength':'418bf8','seedWordOffset':'03da','retainBuffer':'4c8bd1','alignmentMask':'4183e303',
      'wordSetup':'8bf7','tailMask':'83e703','wordCount':'c1ee02','testWords':'85f6','retainSeed':'448bc3','retainWordCount':'448bde','retainCursor':'4d8bca',
      'deriveWord':'418bc0','advanceWordCursor':'4d8d4904','wordShift8':'c1e808','wordByte1':'0fb6d0','wordByte0':'410fb6c0',
      'wordXor':'35'+xor,'wordMultiply0':'69c0'+multiply,'wordXor1':'33d0','wordReload2':'418bc0','wordShift16':'c1e810','wordByte2':'0fb6c8',
      'wordMultiply1':'69c2'+multiply,'wordXor2':'33c8','wordReload3':'418bc0','wordShift24':'c1e818','advanceSeed':'41ffc0',
      'wordMultiply2':'69d1'+multiply,'wordXor3':'33d0','wordMultiply3':'69c2'+multiply,'xorWord':'413141fc','decrementWords':'4983eb01',
      'testTail':'85ff','tailSeed':'448d041e','tailReload1':'418bc0','tailShift8':'c1e808','tailByte1':'0fb6d0','tailByte0':'410fb6c0',
      'tailXor':'35'+xor,'tailMultiply0':'69c0'+multiply,'tailXor1':'33d0','tailReload2':'418bc0','tailShift16':'c1e810','tailByte2':'0fb6c8',
      'tailMultiply1':'69c2'+multiply,'tailShift24':'41c1e818','tailXor2':'33c8','tailMultiply2':'69c1'+multiply,
      'tailCursorDelta':'8d0cb500000000','tailCursor':'4c03d1','tailXor3':'4133c0','tailMultiply3':'69c0'+multiply,
      'storeTailKey':'89442438','testTailAgain':'85ff','tailKeyAddress':'488d542438','retainTailCount':'8bcf','tailKeyDelta':'492bd2',
      'loadTailKeyByte':'420fb60412','xorTailByte':'413002','advanceTailCursor':'4d8d5201','decrementTail':'4883e901','epilogue':'4883c410','return':'c3'}
    for role,code in expected.items():
        if w[role]['instructionHex']!=code:
            _fail('packageTransformInstruction',role,code,w[role]['instructionHex'])
    branches={'jumpAligned':('0f84','wordSetup'),'skipWords':('74','testTail'),'loopWords':('75','deriveWord'),
              'skipTail':('0f84','epilogue'),'skipTailAgain':('74','epilogue'),'loopTail':('75','loadTailKeyByte')}
    for role,(prefix,target) in branches.items():
        row=w[role];raw=bytes.fromhex(row['instructionHex']);op=bytes.fromhex(prefix)
        if not raw.startswith(op) or len(raw) not in (2,6):
            _fail('packageTransformBranchOpcode',role,prefix,raw.hex())
        actual=int(row['rva'],16)+len(raw)+int.from_bytes(raw[len(op):],'little',signed=True)
        if actual!=int(w[target]['rva'],16):
            _fail('packageTransformBranchTarget',role,w[target]['rva'],hex(actual))
    dispatch=_witnesses(next(g for g in groups if g['key']=='transferCompletionDispatcher'))
    slot=contract['receiverSlotOffset']
    if type(slot) is not int or not 0<=slot<128 or slot%8:
        _fail('packageTransformReceiverSlot','dispatcher','bounded aligned slot',slot)
    for role,code in {'retainContext':'488b7920','retainStatus':'8bf2','loadNext':'488b4318','passRequest':'488bd3',
                      'loadReceiver':'488b4a20','retainNext':'488bd8','passStatus':'448bc6','loadAddressPoint':'488b01','callReceiver':'ff50'+slot.to_bytes(1,'little').hex()}.items():
        if dispatch[role]['instructionHex']!=code:
            _fail('packageTransformDispatchInstruction',role,code,dispatch[role]['instructionHex'])


def _validate_transfer_protocol(contract,image,records,read,result):
    import hashlib
    import struct
    leaf=contract['transferInitializerLeaf'];start=int(leaf['entryRva'],16);raw=bytes.fromhex(leaf['bodyHex'])
    if len(raw)!=leaf['bodyLength'] or hashlib.sha256(raw).hexdigest()!=leaf['bodySha256'] or image.bytes_at_va(image.image_base+start,len(raw))!=raw:
        _fail('packageTransferInitializerBytes','complete leaf',leaf['bodySha256'],hashlib.sha256(raw).hexdigest())
    if any(at<start+len(raw) and record[1]>start for at,record in records.items()):
        _fail('packageTransferInitializerFraming','leaf','no overlapping unwind record',leaf['entryRva'])
    fields=contract['transferBlockLayout'];node=contract['completionNodeLayout']
    if set(fields)!={'transferOffset','userData','owner','completionList'} or set(node)!={'next','receiver','state','bufferCarrier'} or any(type(v) is not int or not 0<=v<128 for v in (*fields.values(),*node.values())):
        _fail('packageTransferLayout','fields','bounded block/node offsets',(fields,node))
    carrier=contract['bufferCarrierLayout']
    if set(carrier)!={'transferBlock'} or type(carrier['transferBlock']) is not int or not 0<=carrier['transferBlock']<128:
        _fail('packageTransferLayout','buffer carrier','bounded transfer-block pointer offset',carrier)
    byte=lambda v:v.to_bytes(1,'little').hex()
    base=fields['transferOffset'];transfer=read['transferLayout'];lw={r['role']:r for r in leaf['instructionWitnesses']}
    expected={'retainOwner':'4c8bda','storePosition':'488948'+byte(base+transfer['filePosition']),
        'loadRequested':'8b4c2428','storeRequested':'8948'+byte(base+transfer['requestedBytes']),
        'loadTransform':'8b4c2430','storeTransform':'8948'+byte(base+transfer['transformBytes']),
        'storeCallback':'488948'+byte(base+transfer['callback']),'storeBuffer':'4c8940'+byte(base+transfer['buffer']),
        'storeUserData':'488940'+byte(fields['userData']),'clearCookie':'48c740'+byte(base+transfer['cookie'])+'00000000',
        'storeOwner':'4c8958'+byte(fields['owner']),'return':'c3'}
    for witness in lw.values():
        at=int(witness['rva'],16);code=bytes.fromhex(witness['instructionHex'])
        if not start<=at or at+len(code)>start+len(raw) or image.bytes_at_va(image.image_base+at,len(code))!=code:
            _fail('packageTransferInitializerWitness',witness['role'],'inside exact complete leaf',witness)
    for role,code in expected.items():
        if lw[role]['instructionHex']!=code:_fail('packageTransferInitializerInstruction',role,code,lw[role]['instructionHex'])
    groups={g['key']:g for g in contract['nativeGroups']}
    target=lambda row:int(row['rva'],16)+len(bytes.fromhex(row['instructionHex']))+int.from_bytes(bytes.fromhex(row['instructionHex'])[-4:],'little',signed=True)
    if not lw['callbackAddress']['instructionHex'].startswith('488d0d') or target(lw['callbackAddress'])!=int(groups['transferCompletionDispatcher']['entryRva'],16):
        _fail('packageTransferInitializerCallback','callback LEA',groups['transferCompletionDispatcher']['entryRva'],lw['callbackAddress'])
    dispatcher=_witnesses(groups['transferCompletionDispatcher'])
    for role,code in {'retainContext':'488b79'+byte(fields['userData']-base),'loadNext':'488b43'+byte(node['next']),
                      'loadReceiver':'488b4a'+byte(node['receiver'])}.items():
        if dispatcher[role]['instructionHex']!=code:_fail('packageTransferDispatcherLayout',role,code,dispatcher[role]['instructionHex'])
    caller_expectations={
      'deviceTransferProducer':{'retainDevice':'4c8bf1','retainOwner':'488bf2','passOwner':'488bd6','passDevice':'498bce','passPosition':'4d8bcf','loadBuffer':'4d8b4008','passRequested':'89442420','passTransform':'89442428'},
      'anonymousReceiverReadQueue':{'retainReceiver':'488bf9','loadDevice':'488b4f60','passOwner':'488bd7','passPosition':'4d8bcf','passDevice':'498bce','passTransform':'89742428','passRequested':'89442420',
        'retainBlock':'488be8','loadListHead':'488b45'+byte(fields['completionList']),'storeListHead':'48895d'+byte(fields['completionList']),
        'storeNodeNext':'488943'+byte(node['next']),'storeReceiver':'48897b'+byte(node['receiver']),
        'loadBufferCarrier':'488b4c2438','reloadBufferCarrier':'488b4c2438','storeNodeBufferCarrier':'48894b'+byte(node['bufferCarrier']),
        'storeCarrierTransferBlock':'488941'+byte(contract['bufferCarrierLayout']['transferBlock'])},
      'primaryProviderTransferCompletion':{'retainReceiver':'488bf9','retainDispatchFlag':'450fb6e9','retainStatus':'458be0','retainRequest':'488bf2','testRequest':'4885f6',
        'requireSuccess':'4183fc01','loadRequestState':'8b4e'+byte(node['state']),'stateMask':'2407','blockedState':'3c02',
        'currentRequest':'48397500','storeRequestState':'894e'+byte(node['state']),'wakeTargetDevice':'488b4f60'}}
    caller_expectations['queuedReceiverTransferCompletion']=caller_expectations['primaryProviderTransferCompletion']
    for name,wanted in caller_expectations.items():
        witnesses=_witnesses(groups[name])
        for role,code in wanted.items():
            if witnesses[role]['instructionHex']!=code:_fail('packageTransferConsumerInstruction',name+'.'+role,code,witnesses[role]['instructionHex'])
        if name in {'deviceTransferProducer','anonymousReceiverReadQueue'}:
            call=witnesses['callInitializer']
            if not call['instructionHex'].startswith('e8') or target(call)!=start:
                _fail('packageTransferInitializerCaller',name,leaf['entryRva'],call)
    slot=contract['primaryReceiverSlot']
    if slot['addressPointRva']!=result['completionSlot']['addressPointRva'] or slot['offset']!=contract['receiverSlotOffset'] or slot['targetOwner']!='primaryProviderTransferCompletion':
        _fail('packageTransformReceiverSlot','primary provider','authenticated result address point and dispatcher slot',slot)
    data=image.bytes_at_va(image.image_base+int(slot['addressPointRva'],16)+slot['offset'],8)
    if len(data)!=8 or struct.unpack('<Q',data)[0]!=image.image_base+int(groups[slot['targetOwner']]['entryRva'],16):
        _fail('packageTransformReceiverSlotTarget','primary provider',groups[slot['targetOwner']]['entryRva'],data.hex())
    _validate_queued_receiver_interface(contract,image,groups)


def _validate_queued_receiver_interface(contract,image,groups):
    """Join queue and completion only through an authenticated installed interface."""
    import struct
    binding=contract['queuedReceiverInterface']
    expected={'constructorOwner':'queuedReceiverConstructor','addressWitness':'addressReceiverTable',
        'objectOffset':0,'queueTargetOwner':'anonymousReceiverReadQueue',
        'completionTargetOwner':'queuedReceiverTransferCompletion'}
    for key,value in expected.items():
        if binding.get(key)!=value:
            _fail('packageQueuedReceiverInterface',key,value,binding.get(key))
    point=binding.get('addressPointRva')
    try:
        point_rva=int(point,16)
    except (TypeError,ValueError):
        _fail('packageQueuedReceiverInterface','address point','hexadecimal RVA',point)
    constructor=_witnesses(groups[binding['constructorOwner']])
    for role,code in {'retainReceiver':'488bd9','storeReceiverTable':'488903','returnReceiver':'488bc3'}.items():
        if constructor[role]['instructionHex']!=code:
            _fail('packageQueuedReceiverConstructor',role,code,constructor[role]['instructionHex'])
    address=constructor[binding['addressWitness']];raw=bytes.fromhex(address['instructionHex'])
    target=int(address['rva'],16)+len(raw)+int.from_bytes(raw[-4:],'little',signed=True)
    if len(raw)!=7 or raw[:3]!=b'\x48\x8d\x05' or target!=point_rva:
        _fail('packageQueuedReceiverConstructor','address point LEA',point,hex(target))
    for slot_key,owner_key in (('queueSlot','queueTargetOwner'),('completionSlot','completionTargetOwner')):
        offset=binding.get(slot_key)
        if type(offset) is not int or not 0<=offset<128 or offset%8:
            _fail('packageQueuedReceiverInterface',slot_key,'bounded aligned slot',offset)
        if slot_key=='completionSlot' and offset!=contract['receiverSlotOffset']:
            _fail('packageQueuedReceiverInterface',slot_key,contract['receiverSlotOffset'],offset)
        data=image.bytes_at_va(image.image_base+point_rva+offset,8)
        target=groups[binding[owner_key]]['entryRva']
        if len(data)!=8 or struct.unpack('<Q',data)[0]!=image.image_base+int(target,16):
            _fail('packageQueuedReceiverSlotTarget',slot_key,target,data.hex())
