"""Selected package-descriptor writes and primary-provider completion entry."""
import struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation

CONTRACT_PATH = CONTRACTS_DIR/'wwise_package_result_native.json'
SCHEMA = 'endfield.wwise-package-result-native.v1'


def load_result_contract(path: Path=CONTRACT_PATH) -> dict:
    value,_ = read_reviewed_contract(path,schema=SCHEMA,status='reviewedCurrentBuild',label='wwise-package-result')
    return value


def validate_result_bytes(contract,image,bodies,records,parent,storage,package):
    fail = preparation._fail
    if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewedCurrentBuild':
        fail('packageResultSchema','contract',SCHEMA,contract.get('schema'))
    if any(c['nativeInputs']!=parent['nativeInputs'] for c in (contract,storage,package)):
        fail('packageResultInputs','selected inputs',parent['nativeInputs'],contract['nativeInputs'])
    groups = contract['nativeGroups']
    if len(groups)!=2 or {g['key'] for g in groups}!={'providerCompletionDispatch','providerPackageCompletion'}:
        fail('packageResultGroups','groups','two complete consumer groups',[g['key'] for g in groups])
    validate_native_group_windows(groups,image,bodies,records)
    witnesses = {g['key']:carrier._witnesses(g) for g in groups}
    layouts = {key:contract[key] for key in ('providerLayout','requestLayout','resultLayout','externalRowLayout','packageLayout')}
    names = {'providerLayout':{'addressPoint','retainedRequest','result'},
             'requestLayout':{'text','numeric','flags','mode','callback','provider','result'},
             'resultLayout':{'byteLength','blockOffset','byteOffset','keyLow','package','blockBytes'},
             'externalRowLayout':{'blockBytes','byteLength','blockOffset'},'packageLayout':{'backingObject'}}
    for name,layout in layouts.items():
        if set(layout)!=names[name] or any(type(v) is not int or not 0<=v<128 for v in layout.values()):
            fail('packageResultLayout',name,sorted(names[name]),layout)
    p,q,r,x,b = (layouts[key] for key in names)
    if p['retainedRequest']!=storage['layouts']['provider']['descriptorAllocation'] or p['addressPoint']!=storage['layouts']['provider']['primaryTable']:
        fail('packageResultStorageLayout','provider',storage['layouts']['provider'],p)
    for key,stored in [('text','textPointer'),('numeric','numericWord'),('flags','auxiliaryPointer'),('mode','modeWord')]:
        if q[key]!=storage['layouts']['descriptor'][stored]:
            fail('packageResultRequestLayout',key,storage['layouts']['descriptor'][stored],q[key])
    byte = lambda v:v.to_bytes(1,'little').hex()
    batch = carrier._witnesses(next(g for g in package['nativeGroups'] if g['key']=='defaultIoBatchDispatch'))
    for role,wanted in (('callbackSlot','ff57'+byte(q['callback'])),('storeResult','488947'+byte(q['result']))):
        if batch[role]['instructionHex']!=wanted:
            fail('packageResultBatchLayout',role,wanted,batch[role]['instructionHex'])
    if any(v+4>package['lookupLayout']['rowBytes'] for v in x.values()):
        fail('packageResultRowBounds','external row',package['lookupLayout']['rowBytes'],x)
    expected = {
      'providerCompletionDispatch':{'retainProvider':'488bf1','retainStatus':'418bf8',
        'loadRetainedRequest':'488b56'+byte(p['retainedRequest']),'loadRequestResult':'488b42'+byte(q['result']),
        'storeProviderResult':'488946'+byte(p['result']),'passStatus':'448bc7','passRequest':'488b56'+byte(p['retainedRequest']),
        'passProvider':'488bce','callCompletionSlot':'ff50'+byte(contract['completionSlot']['offset'])},
      'providerPackageCompletion':{'retainProvider':'488bd9','compareStatus':'4183f801','loadFlags':'488b42'+byte(q['flags']),
        'loadProviderResult':'488b4b'+byte(p['result']),'readResultLength':'488b11'}}
    if r['byteLength']:
        fail('packageResultLengthOffset','implicit load',0,r['byteLength'])
    for owner,values in expected.items():
        for role,wanted in values.items():
            actual=witnesses[owner][role]['instructionHex']
            if wanted!=actual: fail('packageResultInstruction',owner+'.'+role,wanted,actual)
    def inherited(owner,rows,wanted):
        parsed={row['role']:row for row in rows}
        if set(parsed)!=set(wanted) or len(parsed)!=len(rows):
            fail('packageResultInheritedCoverage',owner['key'],sorted(wanted),sorted(parsed))
        for role,raw in wanted.items():
            row=parsed[role];at=int(row['rva'],16);code=bytes.fromhex(raw)
            if row['instructionHex']!=raw or not any(int(w['rva'],16)<=at and at+len(code)<=int(w['rva'],16)+w['bodyLength'] for w in owner['windows']) or image.bytes_at_va(image.image_base+at,len(code))!=code:
                fail('packageResultInheritedInstruction',role,raw,row['instructionHex'])
    owner = next(g for g in package['nativeGroups'] if g['key']=='packageDescriptorLookup')
    inherited(owner,contract['packageWriteWitnesses'],{
      'loadByteLength':'8b46'+byte(x['byteLength']),'storeByteLength':'488901',
      'loadBlockOffset':'8b4e'+byte(x['blockOffset']),'storeBlockOffset':'488948'+byte(r['blockOffset']),
      'loadBlockBytes':'8b46'+byte(x['blockBytes']),'storeBlockBytes':'8941'+byte(r['blockBytes']),
      'storePackage':'488958'+byte(r['package']),'multiplyByteOffset':'0faf4e'+byte(x['blockBytes']),
      'storeByteOffset':'8948'+byte(r['byteOffset']),'storeKeyLow':'448968'+byte(r['keyLow']),
      'loadBackingObject':'488b4b'+byte(b['backingObject'])})
    owner = next(g for g in storage['nativeGroups'] if g['key']=='providerDescriptorStorage')
    inherited(owner,contract['storageWriteWitnesses'],{'storeRequestProvider':'488958'+byte(q['provider'])})
    slot=contract['completionSlot']
    point=next(r['targetRva'] for r in storage['addressPointBindings'] if r['owner']=='ordinaryProviderConstructor' and r['witness']=='addressPrimaryTable')
    if slot['addressPointRva']!=point or slot['targetOwner']!='providerPackageCompletion' or type(slot['offset']) is not int or not 0<=slot['offset']<128 or slot['offset']%8:
        fail('packageResultCompletionSlot','slot','reviewed primary provider slot',slot)
    raw=image.bytes_at_va(image.image_base+int(point,16)+slot['offset'],8)
    target=image.image_base+int(next(g['entryRva'] for g in groups if g['key']==slot['targetOwner']),16)
    if len(raw)!=8 or struct.unpack('<Q',raw)[0]!=target:
        fail('packageResultCompletionTarget','slot',hex(target),raw.hex())


def observer_spec(contract):
    dispatch=next(g for g in contract['nativeGroups'] if g['key']=='providerCompletionDispatch')
    call=carrier._witnesses(dispatch)['callCompletionSlot']
    return {'primaryAddressPointRva':contract['completionSlot']['addressPointRva'],
            'callerReturnRva':hex(int(call['rva'],16)+len(bytes.fromhex(call['instructionHex'])))}
