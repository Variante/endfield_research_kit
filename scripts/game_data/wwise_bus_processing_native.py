"""Authenticate post-mix bus processing on the explicitly selected opened image."""
from __future__ import annotations

import hashlib
import struct
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations, validate_native_group_windows
from scripts.game_data.wwise_biquad_arithmetic import validate_program


def load_contract():
    value, _ = read_reviewed_contract(CONTRACTS_DIR/'wwise_bus_processing_native.json',
        schema='endfield.wwise-bus-processing-observer.v5', status='reviewedCurrentBuild', label='wwise-bus-processing')
    return value


def validate_effect_classes(contract, indexed, image):
    parameters,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_effect_parameters_native.json',
        schema='endfield.wwise-effect-parameters-native.v5',status='reviewedCurrentBuild',label='wwise-effect-parameters')
    if parameters['nativeInputs']!=contract['nativeInputs']:raise ValueError('bus effect parameter identity inputs differ')
    for binding in contract['effectClassBindings']:
        class_id=int(binding['classId'],16);factory=indexed[binding['factoryGroup']]
        record=struct.pack('<QQQQ',class_id&15,class_id>>16,image.image_base+int(factory['entryRva'],16),image.image_base+int(binding['parameterFactoryRva'],16))
        if image.bytes_at_va(image.image_base+int(binding['registrationRva'],16),len(record))!=record:
            raise ValueError('bus effect registration differs: '+binding['classId'])
        w=next(w for w in factory['instructionWitnesses'] if w['role']==binding['vtableRole'])
        raw=bytes.fromhex(w['instructionHex']);vtable=int(binding['vtableRva'],16)
        if len(raw)!=7 or raw[:3].hex()!=binding['vtablePrefixHex'] or int(w['rva'],16)+7+struct.unpack_from('<i',raw,3)[0]!=vtable:
            raise ValueError('bus effect constructed vtable differs')
        target=image.image_base+int(indexed[binding['executeGroup']]['entryRva'],16)
        if image.bytes_at_va(image.image_base+vtable+binding['executeSlot'],8)!=struct.pack('<Q',target):
            raise ValueError('bus effect Execute slot differs')
        method=parameters['parameterSchemas'][binding['classId']]['setParamsBlock']
        body=image.bytes_at_va(image.image_base+int(method['rva'],16),method['bodyLength'])
        if hashlib.sha256(body).hexdigest()!=method['bodySha256']:
            raise ValueError('bus effect named parameter body differs')


def validate(contract, pipeline, image):
    """Caller first gates its explicit GameAssembly/metadata/AkSoundEngine paths."""
    if contract['nativeInputs'] != pipeline['nativeInputs']:
        raise ValueError('bus processing selected native inputs differ')
    groups = list(contract['nativeGroups'])
    groups += [g for g in pipeline['nativeGroups'] if g['key'] in contract['borrowedGroups']]
    if len(groups) != len(contract['nativeGroups'])+len(contract['borrowedGroups']):
        raise ValueError('bus processing borrowed native groups missing')
    validate_native_group_declarations(groups)
    _, bodies, records = _collect_opened_source_image(image, 'selected AkSoundEngine')
    validate_native_group_windows(groups, image, bodies, records)
    indexed = {g['key']:g for g in groups}
    for binding in contract['callBindings']:
        group = indexed[binding['group']]
        witness = next(w for w in group['instructionWitnesses'] if w['role']==binding['role'])
        raw = bytes.fromhex(witness['instructionHex']); at=int(witness['rva'],16)
        if len(raw)!=5 or raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[binding['targetGroup']]['entryRva'],16):
            raise ValueError('bus processing direct call differs: '+binding['role'])
    bindings=[(b,contract['layout']) for b in contract['fieldBindings']]
    effect=contract['collectionEffect']
    bindings += [(b,effect['layout']) for b in effect['fieldBindings']]
    bindings += [(b,contract['biquadProcessing']['eqLayout']) for b in contract['biquadProcessing']['fieldBindings']]
    for binding,layout in bindings:
        group=indexed[binding['group']]
        witness=next(w for w in group['instructionWitnesses'] if w['role']==binding['role'])
        encoded=bytes.fromhex(binding['prefixHex'])+layout[binding['field']].to_bytes(binding['width'],'little')+bytes.fromhex(binding.get('suffixHex',''))
        if encoded.hex()!=witness['instructionHex']:
            raise ValueError('bus processing field binding differs: '+binding['field'])
    for binding in contract['gainAbiBindings']:
        group=indexed['sourceFrameGain']; at=int(binding['rva'],16); raw=bytes.fromhex(binding['instructionHex'])
        if not any(int(w['rva'],16)<=at and at+len(raw)<=int(w['rva'],16)+w['bodyLength'] for w in group['windows']):
            raise ValueError('bus frame gain ABI witness outside body')
        if image.bytes_at_va(image.image_base+at,len(raw))!=raw:
            raise ValueError('bus frame gain floating ABI differs')
    validate_effect_classes(contract,indexed,image)
    validate_biquad_dispatch(contract,indexed,image)
    validate_biquad_programs(contract,indexed,image)
    return indexed


def validate_biquad_dispatch(contract,indexed,image):
    b=contract['biquadProcessing'];d=b['dispatch'];at=int(d['rva'],16)
    identity=b['serviceIdentity']
    point=int(identity['vtableRva'],16);object_rva=int(identity['objectRva'],16)
    if image.bytes_at_va(image.image_base+object_rva,8)!=struct.pack('<Q',image.image_base+point):
        raise ValueError('biquad static service address point differs')
    if identity['executeSlot']!=contract['layout']['effectExecuteSlot'] or image.bytes_at_va(image.image_base+point+identity['executeSlot'],8)!=struct.pack('<Q',image.image_base+int(indexed[b['serviceGroup']]['entryRva'],16)):
        raise ValueError('biquad static service execute slot differs')
    load_at=int(identity['globalLoadRva'],16);encoded=bytes.fromhex(identity['globalLoadInstructionHex'])
    owner=indexed['collectionEqProcessing']
    if len(encoded)!=7 or encoded[:3]!=bytes.fromhex('488b0d') or not any(int(w['rva'],16)<=load_at and load_at+7<=int(w['rva'],16)+w['bodyLength'] for w in owner['windows']):
        raise ValueError('biquad EQ service read exceeds its current owner')
    if image.bytes_at_va(image.image_base+load_at,7)!=encoded or load_at+7+struct.unpack_from('<i',encoded,3)[0]!=int(b['eqLayout']['processorServiceRva'],16):
        raise ValueError('biquad EQ service global read differs')
    raw=image.bytes_at_va(image.image_base+at,d['bodyLength'])
    if raw.hex()!=d['instructionHex'] or hashlib.sha256(raw).hexdigest()!=d['bodySha256']:
        raise ValueError('biquad dispatch bytes differ')
    # This leaf selects two authenticated bodies without creating a stack frame.
    if len(raw)!=27 or raw[:3]!=bytes.fromhex('448b15') or raw[7:16]!=bytes.fromhex('4585d2740a4183fa01') or raw[16:18]!=bytes.fromhex('0f84') or raw[22]!=0xe9:
        raise ValueError('biquad dispatch shape differs')
    if at+7+struct.unpack_from('<i',raw,3)[0]!=int(d['processorModeRva'],16):raise ValueError('biquad processor selector differs')
    if at+22+struct.unpack_from('<i',raw,18)[0]!=int(indexed[d['avxGroup']]['entryRva'],16) or at+27+struct.unpack_from('<i',raw,23)[0]!=int(indexed[d['fallbackGroup']]['entryRva'],16):
        raise ValueError('biquad dispatch targets differ')
    g=indexed[b['serviceGroup']];w=next(w for w in g['instructionWitnesses'] if w['role']=='dispatch');call=bytes.fromhex(w['instructionHex'])
    if len(call)!=5 or call[0]!=0xe8 or int(w['rva'],16)+5+struct.unpack_from('<i',call,1)[0]!=at:
        raise ValueError('biquad service dispatch call differs')
    for binding in b['uniformCalls']:
        group=indexed[binding['group']];w=next(w for w in group['instructionWitnesses'] if w['role']==binding['role']);raw=bytes.fromhex(w['instructionHex'])
        if len(raw)!=5 or raw[0] not in (0xe8,0xe9) or int(w['rva'],16)+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[binding['targetGroup']]['entryRva'],16):
            raise ValueError('biquad uniform transfer differs')


def validate_biquad_programs(contract,indexed,image):
    if set(contract['biquadProcessing']['prefixPrograms'])!={'sse','avx'}:raise ValueError('biquad arithmetic processor roster differs')
    for mode,program in contract['biquadProcessing']['prefixPrograms'].items():
        if mode not in ('sse','avx'):raise ValueError('biquad arithmetic processor differs')
        validate_program(program)
        group=indexed[program['ownerGroup']];entry=int(group['entryRva'],16)
        if entry!=int(program['entryRva'],16):raise ValueError('biquad program owner differs')
        caller=indexed[program['callerGroup']];w=next(w for w in caller['instructionWitnesses'] if w['role']==program['callerRole']);raw=bytes.fromhex(w['instructionHex'])
        if len(raw)!=5 or raw[0]!=0xe8 or int(w['rva'],16)+5+struct.unpack_from('<i',raw,1)[0]!=entry:raise ValueError('biquad two-buffer call differs')
        if mode=='avx':
            # The two-buffer path is jump-table case 1 (buffer count minus 1).
            table=contract['biquadProcessing']['twoBufferAvxDispatch']
            if table['selectedIndex']!=1 or not 2<=table['entryCount']<=8:raise ValueError('biquad two-buffer jump case differs')
            words=image.bytes_at_va(image.image_base+int(table['rva'],16),table['entryCount']*4)
            if struct.unpack_from('<I',words,table['selectedIndex']*4)[0]!=int(w['rva'],16)-table['callOffset']:raise ValueError('biquad two-buffer jump selection differs')
        at=entry
        for row in program['instructionPath']:
            raw=bytes.fromhex(row['instructionHex'])
            if int(row['rva'],16)!=at or not raw or image.bytes_at_va(image.image_base+at,len(raw))!=raw:raise ValueError('biquad expression instruction path differs')
            at+=len(raw)
        if int(program['instructionPath'][-1]['rva'],16)!=int(program['firstOutputStoreRva'],16):raise ValueError('biquad first-output boundary differs')
        if not any(int(win['rva'],16)<=entry and at<=int(win['rva'],16)+win['bodyLength'] for win in group['windows']):raise ValueError('biquad expression path exceeds owner')
        for row in program['constants']:
            if image.bytes_at_va(image.image_base+int(row['rva'],16),4)!=struct.pack('<I',row['word']):raise ValueError('biquad expression native constant differs')
