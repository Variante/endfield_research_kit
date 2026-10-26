"""Selected Room effect lifecycle, configuration and stored parameter extent."""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract,NATIVE_MAPPER_PATH
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.wwise_source_native import _collect_opened_source_image
from scripts.game_data.wwise_source_queue_native import validate_native_group_declarations,validate_native_group_windows


def load_contract():
    c,_=read_reviewed_contract(CONTRACTS_DIR/'wwise_room_configuration_native.json',schema='endfield.wwise-room-configuration-native.v3',status='reviewedCurrentBuild',label='wwise-room-configuration')
    return c


def validate(c,image,selected_inputs):
    if c.get('schema')!='endfield.wwise-room-configuration-native.v3' or c.get('status')!='reviewedCurrentBuild' or c['nativeInputs']!=selected_inputs:raise ValueError('room configuration schema/status/selected inputs differ')
    groups=list(c['nativeGroups']);owners={}
    for dependency in c['borrowedGroups']:
        owner,_=read_reviewed_contract(CONTRACTS_DIR/(dependency['ownerContract']+'.json'),schema=dependency['ownerSchema'],status='reviewedCurrentBuild',label='room-configuration-owner')
        if owner['nativeInputs']!=selected_inputs:raise ValueError('room configuration owner inputs differ')
        owners[dependency['ownerContract']]=owner;indexed={g['key']:g for g in owner['nativeGroups']};groups.extend(indexed[k] for k in dependency['keys'])
    parameters,_=read_reviewed_contract(CONTRACTS_DIR/(c['parameterOwnerContract']+'.json'),schema='endfield.wwise-effect-parameters-native.v4',status='reviewedCurrentBuild',label='room-configuration-parameters')
    if parameters['nativeInputs']!=selected_inputs:raise ValueError('room configuration parameter inputs differ')
    validate_native_group_declarations(groups);_,bodies,records=_collect_opened_source_image(image,'selected Room configuration');validate_native_group_windows(groups,image,bodies,records)
    indexed={g['key']:g for g in groups}
    def read(group,at,n):
        if not any(int(w['rva'],16)<=at and at+n<=int(w['rva'],16)+w['bodyLength'] for w in indexed[group]['windows']):raise ValueError('room configuration instruction outside complete body')
        return image.bytes_at_va(image.image_base+at,n)
    for binding in c['callBindings']:
        at=int(binding['rva'],16);raw=read(binding['group'],at,5)
        if raw[0]!=0xe8 or at+5+struct.unpack_from('<i',raw,1)[0]!=int(indexed[binding['targetGroup']]['entryRva'],16) or at+5!=int(binding['returnRva'],16):raise ValueError('room configuration native call differs')
    for binding in c['fieldBindings']:
        witness=next(w for w in indexed[binding['group']]['instructionWitnesses'] if w['role']==binding['role']);raw=bytes.fromhex(witness['instructionHex']);offset=binding['displacementOffset'];size=binding['displacementBytes']
        if read(binding['group'],int(witness['rva'],16),len(raw))!=raw or int.from_bytes(raw[offset:offset+size],'little')!=c['layout'][binding['layoutField']]:raise ValueError('room configuration instance field differs')
    selectors=c['toneStageSelectors']
    if {v['stagePurpose'] for v in selectors}!={'inputTone','earlyLeftTone','earlyRightTone','lateTone'} or len(selectors)!=4:raise ValueError('room configuration tone stage coverage differs')
    for selector in selectors:
        raw=bytes.fromhex(selector['instructionHex'])
        if len(raw)!=7 or raw[0]!=0x83 or raw[1] not in (0xba,0xb9) or int.from_bytes(raw[2:6],'little')!=c['layout']['toneMode'] or raw[-1]!=selector['mode'] or read(selector['group'],int(selector['rva'],16),len(raw))!=raw:raise ValueError('room configuration native tone stage selector differs')
    input_owner=owners['wwise_room_input_native'];delay_offsets={}
    for role,field in (('copy','initialCopyDelay'),('swap','initialSwapDelay')):
        witness=next(v for v in input_owner['fieldBindings'] if v['layoutField']==field);raw=bytes.fromhex(witness['instructionHex']);offset=witness['displacementOffset'];value=input_owner['layout'][field]
        if read(witness['group'],int(witness['rva'],16),len(raw))!=raw or int.from_bytes(raw[offset:offset+4],'little')!=value:raise ValueError('room configuration input delay field differs')
        delay_offsets[role]=value
    binding=next(b for b in owners['wwise_bus_processing_native']['effectClassBindings'] if b['classId']==c['factoryClassId'])
    factory=indexed[binding['factoryGroup']];site=next(w for w in factory['instructionWitnesses'] if w['role']==binding['vtableRole']);at=int(site['rva'],16);raw=read(factory['key'],at,7);vtable=int(binding['vtableRva'],16)
    if raw[:3].hex()!=binding['vtablePrefixHex'] or at+7+struct.unpack_from('<i',raw,3)[0]!=vtable:raise ValueError('room configuration factory address point differs')
    record=struct.pack('<4Q',int(binding['classId'],16)&15,int(binding['classId'],16)>>16,image.image_base+int(factory['entryRva'],16),image.image_base+int(binding['parameterFactoryRva'],16))
    if image.bytes_at_va(image.image_base+int(binding['registrationRva'],16),32)!=record:raise ValueError('room configuration registered factory differs')
    if sorted(b['slot'] for b in c['effectSlots'])!=[8,16,48]:raise ValueError('room configuration effect slots differ')
    for slot in c['effectSlots']:
        pointer=struct.unpack('<Q',image.bytes_at_va(image.image_base+vtable+slot['slot'],8))[0]
        if pointer!=image.image_base+int(indexed[slot['group']]['entryRva'],16):raise ValueError('room configuration lifecycle target differs')
    p=parameters['registrationWitnesses'][c['factoryClassId']];method=parameters['parameterSchemas'][c['factoryClassId']]['setParamsBlock'];start=int(method['rva'],16);size=method['bodyLength']
    if hashlib.sha256(image.bytes_at_va(image.image_base+start,size)).hexdigest()!=method['bodySha256'] or hashlib.sha256(image.bytes_at_va(image.image_base+int(p['parameterFactoryRva'],16),p['parameterFactoryBodyLength'])).hexdigest()!=p['parameterFactoryBodySha256']:raise ValueError('room configuration parameter factory/bulk body differs')
    at=int(p['vtableLeaRva'],16);raw=image.bytes_at_va(image.image_base+at,7);parameter_vtable=int(p['vtableRva'],16)
    if raw[:3].hex()!=p['vtableLeaPrefixHex'] or at+7+struct.unpack_from('<i',raw,3)[0]!=parameter_vtable or struct.unpack('<Q',image.bytes_at_va(image.image_base+parameter_vtable+p['setParamsBlockSlot'],8))[0]!=image.image_base+start:raise ValueError('room configuration parameter address point/slot differs')
    projection=c['parameterProjection'];extent=projection['byteExtent'];stored=set();transient=[]
    if type(extent) is not int or not 0<extent<=256 or extent%4 or projection['wordBytes']!=4 or projection['instanceOffset']!=c['layout']['parameterObject']:raise ValueError('room configuration parameter projection extent differs')
    for store in projection['bulkStores']:
        at=int(store['rva'],16);raw=bytes.fromhex(store['instructionHex']);offset=store['offset'];width=store['bytes']
        if not start<=at<=start+size-len(raw) or image.bytes_at_va(image.image_base+at,len(raw))!=raw or width not in (1,4) or not 8<=offset<offset+width<=extent:raise ValueError('room configuration stored parameter witness differs')
        opcode_at=3 if raw[:3]==bytes.fromhex('f30f11') else 1 if raw[0] in (0x88,0x89,0xc6) else None
        if opcode_at is None:raise ValueError('room configuration parameter store opcode differs')
        modrm=raw[opcode_at];mode=modrm>>6;cursor=opcode_at+1
        if modrm&7 not in (1,7) or mode not in (1,2):raise ValueError('room configuration parameter store base differs')
        actual_offset=int.from_bytes(raw[cursor:cursor+(1 if mode==1 else 4)],'little',signed=True);actual_width=1 if raw[0] in (0x88,0xc6) else 4
        if (actual_offset,actual_width)!=(offset,width):raise ValueError('room configuration parameter store offset/width differs')
        if raw[0]==0xc6 and raw[-1]==1:transient.append(offset)
        stored.update(range(offset,offset+width))
    known=set()
    for begin,end in projection['knownRanges']:
        if not 8<=begin<end<=extent or known.intersection(range(begin,end)):raise ValueError('room configuration known parameter ranges differ')
        known.update(range(begin,end))
    if projection['transientBytes']!=sorted(transient) or known!=stored-set(transient) or max(stored)+1!=extent:raise ValueError('room configuration parameter coverage differs')
    for leaf in c['leafWindows']:
        raw=bytes.fromhex(leaf['bytesHex'])
        if len(raw)!=leaf['byteLength'] or image.bytes_at_va(image.image_base+int(leaf['rva'],16),len(raw))!=raw:raise ValueError('room configuration clear-history leaf differs')
    return dict(groups=indexed,inputDelayOffsets=delay_offsets,parameterVtableRva=p['vtableRva'],effectVtableRva=binding['vtableRva'])


def load_validated(*,gameassembly,metadata,ak_sound_engine):
    audit=dict(status='missing',detail='three explicit native paths required')
    if any(p is None for p in (gameassembly,metadata,ak_sound_engine)):return None,audit
    try:
        c=load_contract();inputs=c['nativeInputs'];gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['globalMetadataSha256'],gameassembly=Path(gameassembly),metadata=Path(metadata),require_metadata=True)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return None,audit
        path=Path(ak_sound_engine)
        if not path.is_file():return None,dict(status='missing',detail='selected AkSoundEngine.dll missing')
        if path.stat().st_size!=inputs['akSoundEngineFileSize'] or sha256_file(path).casefold()!=inputs['akSoundEngineSha256'].casefold():return None,dict(status='mismatched',detail='selected AkSoundEngine.dll size/hash differs')
        image=load_native_mapper(NATIVE_MAPPER_PATH).PeImage(path)
        if hashlib.sha256(image.buf).hexdigest()!=inputs['akSoundEngineSha256'].casefold():raise ValueError('opened Room configuration image differs')
        result=validate(c,image,inputs);audit.update(status='validated',detail='selected complete Room lifecycle/configuration and parameter projection validated',ownedGroups=len(c['nativeGroups']),inputDelayOffsets=result['inputDelayOffsets'],nativeEntryRvas={k:g['entryRva'] for k,g in result['groups'].items()},parameterVtableRva=result['parameterVtableRva'],effectVtableRva=result['effectVtableRva'],evidenceBoundary=c['evidenceBoundary'])
        return c,audit
    except FileNotFoundError as error:audit.update(status='missing',detail=str(error)[:320])
    except (OSError,ValueError,KeyError,TypeError,IndexError,StopIteration) as error:audit.update(status='mismatched',detail=str(error)[:320])
    return None,audit
