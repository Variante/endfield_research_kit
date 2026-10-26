"""Authenticate the selected stored MissionCondition comparison offline."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import re
import sys
from pathlib import Path

if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_condition_consumers_native')

from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.integer_registers import decode_integer_register_instructions
from scripts.game_data.il2cpp.integer_byte_operations import decode_byte_register_logic
from scripts.game_data.il2cpp.integer_widths import _byte
from scripts.game_data.il2cpp.context import method_spec_usage_index, generic_method_candidates, type_parameter_owner
from scripts.game_data.dynamic_erosion_consumers_native import (_check_method, _ordinary_primitive_abi, _raw_type_abi, _mov_register,
    _lea_stack, _method_call_abi, _instruction_partition, _direct_call_boundary, _preserved_interval)
from scripts.game_data.dynamic_scalar_components_native import _getter_offset, _relative_call_target, _validate_carriers
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data import dynamic_group_components_native as groups
from scripts.game_data.corpus_common import atomic_write_text
from scripts.repo_paths import REPO_ROOT

CONTRACT=CONTRACTS_DIR / 'dynamic_mission_condition_consumers_native.json'
SCHEMA='endfield.dynamic-mission-condition-consumers-native-contract.v3'


def _require(condition,check,expected,actual):
    if not condition:
        raise ValueError(f'mission_condition_consumers:{check}:expected={str(expected)[:320]} actual={str(actual)[:320]}')


def compare_condition_state(value:int,state:int,is_same:int)->bool:
    """Selected comparison only; caller supplies the unresolved native value."""
    for name,number in (('value',value),('state',state),('is_same',is_same)):
        _require(type(number) is int and -(1<<31)<=number<(1<<31),'comparison-input-'+name,'stored/native Int32',number)
    return value==state if is_same==1 else value!=state


def _vector_return_abi(image,method):
    bits=_raw_type_abi(image,method.return_type,'mission-vector-proxy-return')
    _require((bits>>16)&0xff==0x11 and (bits>>24)&0x7f==0,
             'ordinary-vector-value-return','value kind11; low seven flags zero',f'rawBits={bits:08X}')


def _query_context(image,raw,query,pins):
    pe=image.pe;reg=image.registration;at=pins['contextLoadOffset']
    _require(raw[at:at+3]==bytes.fromhex('4C8B0D') and raw[at:at+7].hex().upper()==pins['contextLoadRawHex'],
             'query-context-load',pins['contextLoadRawHex'],raw[at:at+7].hex())
    cell_rva=query['rva']+at+7+struct.unpack_from('<i',raw,at+3)[0]
    _require(cell_rva==pins['usageCellRva'],'query-context-cell',pins['usageCellRva'],cell_rva)
    cell=pe.image_base+cell_rva;usage=pe.bytes_at_va(cell,8)
    _require(usage.hex().upper()==pins['usageRawHex'],'query-usage-bytes',pins['usageRawHex'],usage.hex())
    spec=method_spec_usage_index(usage,reg['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    _require(spec==pins['methodSpecIndex'],'query-selected-spec',pins['methodSpecIndex'],spec)
    spec_va=int(reg['methodSpecs'],16)+spec*12;spec_raw=pe.bytes_at_va(spec_va,12)
    _require(spec_raw.hex().upper()==pins['methodSpecRawHex'],'query-spec-bytes',pins['methodSpecRawHex'],spec_raw.hex())
    definition,class_inst,method_inst=struct.unpack('<iii',spec_raw)
    _require(definition==pins['definition'] and 0<=definition<len(image.metadata.methods) and
             class_inst==pins['classInstantiationIndex'] and 0<=class_inst<reg['genericInstsCount'] and method_inst==-1,
             'query-spec-roster','selected concrete class-only MethodSpec',(definition,class_inst,method_inst))
    method=image.metadata.methods[definition]
    _require(image.metadata.type_full_name(image.metadata.types[method.declaring_type])==pins['type'] and
             image.metadata.string(method.name_index)==pins['method'] and not method.flags&0x10,
             'query-generic-method','selected instance Dictionary.TryGetValue',definition)
    _ordinary_primitive_abi(image,method.return_type,0x02,'query-dictionary-return')
    parameters=image.metadata.parameters_for(method)
    _require(len(parameters)==2,'query-generic-parameters',2,len(parameters))
    for ordinal,param in enumerate(parameters):
        bits=_raw_type_abi(image,param.type_index,'query-dictionary-parameter')
        _require((bits>>16)&0xff==0x13 and bits>>24==(0 if ordinal==0 else 0x20),
                 'query-generic-parameter-abi-'+str(ordinal),'VAR flags key00/value20',f'{bits:08X}')
        pointer=pe.u64_at_va(int(reg['types'],16)+param.type_index*8);record=pe.bytes_at_va(pointer,16)
        expected=pins['signature']['parameters'][ordinal]
        _require(record.hex().upper()==expected['rawTypeRecordHex'],'query-parameter-record',expected['rawTypeRecordHex'],record.hex())
        owner=type_parameter_owner(image.metadata.buf,struct.unpack_from('<Q',record)[0],
            [row.generic_container_index for row in image.metadata.types],source=str(image.metadata_path))
        _require(owner['typeIndex']==method.declaring_type and owner['ordinal']==ordinal,
                 'query-generic-owner','same concrete Dictionary owner and ordinal',(owner['typeIndex'],owner['ordinal']))
    inst=image.instantiations.resolve(class_inst)
    _require(len(inst.arguments)==2,'query-concrete-arguments',2,len(inst.arguments))
    for arg in inst.arguments:
        record=bytes.fromhex(arg.raw_type_record_hex)
        _require(record[10]==0x08 and record[11]&0x7f==0,'query-concrete-Int32','ordinary Int32',record.hex())
    code=image.mapper.code_registration_summary(pe,image.code_registration);table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),
        reg['genericMethodTableCount'],reg['methodSpecsCount'],{spec},code['genericMethodPointersCount'],
        code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    _require(len(candidates)==1,'query-pointer-candidates','one explicitly selected MethodSpec candidate',len(candidates))
    slot=candidates[0]['indices'][0]
    _require(slot==pins['methodPointerIndex'],'query-pointer-slot',pins['methodPointerIndex'],slot)
    pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+slot*8)
    target=_relative_call_target(raw,query['rva'],pins['callOffset'],'query-TryGetValue-call')
    _require(target==pins['callTargetRva'] and pointer==pe.image_base+target,
             'query-context-call','selected MethodSpec pointer equals direct call',(target,pointer))
    return {'methodSpecIndex':spec,'classArguments':['System.Int32','System.Int32'],'method':pins['type']+'.'+pins['method']}


def _composed_decoder(mapper):
    class ByteSubset:
        def decode_one_x64(self,raw,offset,start_va):
            at=offset;rex=0
            if 0<=at<len(raw) and 0x40<=raw[at]<=0x4f:rex=raw[at];at+=1
            if not rex&0x0a and raw[at:at+1]==b'\x22':
                _require(at+2<=len(raw),'byte-and-truncated','complete register ModRM',raw[offset:].hex())
                modrm=raw[at+1]
                if modrm>>6==3:
                    destination=_byte(((modrm>>3)&7)|((rex&4)<<1),rex)
                    source=_byte((modrm&7)|((rex&1)<<3),rex);stop=at+2
                    return {'offset':offset,'va':hex(start_va+offset),'bytes':raw[offset:stop].hex(' '),
                        'text':f'and {destination}, {source}',
                        'write':{'register':destination,'value':'modified low/high byte; other parent bits preserved'}},stop
            result=decode_byte_register_logic(raw,offset,start_va)
            if result is not None:
                row,stop=result
                row['write']={'register':row['byteLogicalOperation']['destinationRegister'],'value':'modified byte; other parent bits preserved'}
                return row,stop
            return mapper.decode_one_x64(raw,offset,start_va)
    def decode(raw,start_va,*,stop_offset):
        _require(stop_offset==len(raw),'decoder-bound','complete bounded primary body',stop_offset)
        return decode_integer_register_instructions(ByteSubset(),raw,start_va)
    return decode


def _cfg_preserved(rows,base,start,stops,register,allowed_calls,selected_fallthrough,visit_check=None):
    """Explore all admitted paths; explicit false-patch edges alone are pruned."""
    by_offset={row['offset']:row for row in rows};states={};reached=set()
    def visit(at):
        if at in stops:reached.add(at);return
        _require(states.get(at)!=1,'cfg-cycle-'+register,'acyclic getter-to-predicate region',at)
        if states.get(at)==2:return
        states[at]=1
        _require(at in by_offset,'cfg-escape-'+register,'owned instruction or admitted stop',at)
        row=by_offset[at];size=len(bytes.fromhex(row['bytes']));next_at=at+size
        if visit_check is not None:visit_check(row)
        _preserved_interval([row],at,next_at,register,allowed_calls,'cfg-'+register)
        text=row['text'];mnemonic=text.split()[0]
        _require(mnemonic not in ('ret','int3'),'cfg-terminal-'+register,'reach predicate before return/exception',row)
        if mnemonic.startswith('j'):
            match=re.fullmatch(r'j[a-z]+ 0x([0-9a-f]+)',text)
            _require(match is not None,'cfg-branch-'+register,'direct decoded branch',row)
            target=int(match.group(1),16)-base
            if at in selected_fallthrough:
                _require(mnemonic!='jmp','cfg-selection-'+register,'conditional non-replacement fallthrough',row)
                successors=[next_at]
            elif mnemonic=='jmp':successors=[target]
            else:successors=[next_at,target]
        else:successors=[next_at]
        for successor in successors:visit(successor)
        states[at]=2
    visit(start)
    _require(reached==set(stops),'cfg-predicate-roster-'+register,sorted(stops),sorted(reached))


def _provider_local_store_check(row):
    """Direct fixed-frame stores only; indirect/callee isolation is conditional."""
    write=row.get('write') or {}
    _require(write.get('register') not in {'rbp','ebp','bp','bpl','rsp','esp','sp','spl'},
             'provider-frame-base','stable RBP/RSP',row)
    mnemonic,_,operands=row['text'].partition(' ')
    destination=operands.split(',',1)[0]
    if not destination.startswith('[') or mnemonic in ('cmp','test'):
        return
    if not destination.startswith('[rbp'):
        _require(not destination.startswith('[rsp'),'provider-rsp-store','no unbound RSP-relative store',row)
        return
    match=re.fullmatch(r'\[rbp(?:([+-])0x([0-9a-f]+))?\]',destination)
    _require(match is not None,'provider-frame-address','simple fixed RBP-relative destination',row)
    offset=int(match.group(2),16)*(1 if match.group(1)=='+' else -1) if match.group(2) else 0
    widths={'movups':16,'movaps':16,'movsd':8,'movss':4}
    width=widths.get(mnemonic)
    if mnemonic=='mov':
        source=operands.split(',',1)[1].strip()
        if re.fullmatch(r'(?:e[a-z]{2}|r(?:[89]|1[0-5])d)',source):width=4
        elif re.fullmatch(r'(?:r[a-z]{2}|r(?:[89]|1[0-5]))',source):width=8
        elif re.fullmatch(r'(?:[abcd][lh]|[sd]il|bpl|spl|r(?:[89]|1[0-5])b)',source):width=1
    _require(width is not None,'provider-frame-store-width','proved fixed-width store',row)
    _require(offset+width<=127 or offset>=131,'provider-local-overlap','store disjoint from RBP+127..130',row)


def _check_query_flow(raw,rva,pins,decode):
    rows=_instruction_partition(raw,rva,decode)
    _require(pins['callOffset']==112 and pins['contextLoadOffset']==97,
             'query-context-call-slots','same adjacent selected dictionary request slots',
             (pins['callOffset'],pins['contextLoadOffset']))
    probes={22:'418BF80FB7F2488BD9',61:'488B4B284885C9746F',77:'448BC70FB7D6',
        88:'488B4B384885C97454',104:'4C8D4424308B5008',117:'84C074388B442430',
        125:'488B5C2450488B7424584883C4405FC3',177:'33C0EBC8',186:'CC'}
    for at,expected in probes.items():
        value=bytes.fromhex(expected)
        _require(raw[at:at+len(value)]==value,'query-flow-'+str(at),expected,raw[at:at+len(value)].hex())
    _require(len(raw)==187,'query-primary-extent',187,len(raw))
    for at in (48,83,112,148,160,181):_direct_call_boundary(rows,at,'query-call-'+str(at))
    for register in ('rbx','rdi'):
        _cfg_preserved(rows,rva,61,{121,177},register,{83,112},{68,95})
    for start,end,register,label in ((125,140,'rax','return-frame'),(88,109,'rax','opaque-key-carrier'),
        (65,83,'rcx','lookup-receiver'),(92,112,'rcx','dictionary-receiver'),(109,112,'r8','output-pointer')):
        _preserved_interval(rows,start,end,register,set(),'query-'+label)
    _require(pins['contextLoadRawHex']==raw[97:104].hex().upper(),'query-call-context',pins['contextLoadRawHex'],raw[97:104].hex())
    return {'dictionary':'System.Collections.Generic.Dictionary<System.Int32,System.Int32>',
        'key':'opaque lookup object Int32 at offset8','successReturn':'Int32 output at RSP+48',
        'missReturn':0,'nullReceiver':'exception helper then int3',
        'runtimeObserved':False,'keyOwnershipResolved':False}


def _check_comparison_flow(contract,raw,bodies,methods,vector,fields,carriers,decode):
    partitions={role:_instruction_partition(body,methods[role]['rva'],decode) for role,body in bodies.items()}
    probes={}
    for name,row in contract['probes'].items():
        at=row['offset'];value=bytes.fromhex(row['bytes'])
        _require(0<=at and value and at+len(value)<=len(raw) and raw[at:at+len(value)]==value,
            'witness-'+name,value.hex(),raw[at:at+len(value)].hex())
        probes[name]=value
    rva=methods['update']['rva'];calls=contract['calls'];owned=contract['ownedAccessorCalls']
    def target(body,base,at,label):return _relative_call_target(body,base,at,label)
    for label,at in calls.items():_direct_call_boundary(partitions['update'],at,label)
    for label,at in owned.items():
        role='vector' if label.startswith('vector') else 'state' if label.startswith('state') else 'same'
        _direct_call_boundary(partitions[role],at,'owned-'+label)
    _require(target(raw,rva,calls['query'],'query')==methods['query']['rva'],'named-value-provider',methods['query']['rva'],target(raw,rva,calls['query'],'query'))
    for role in ('updatePatch','statePatch','samePatch'):
        _require(target(raw,rva,calls[role],role)==methods['patchCheck']['rva'],'patch-method-'+role,methods['patchCheck']['rva'],target(raw,rva,calls[role],role))
    for role,main_call in (('table','vectorTable'),('vector','vectorVector')):
        _require(target(raw,rva,calls[role],role)==target(bodies['vector'],methods['vector']['rva'],owned[main_call],main_call),
            'same-generated-helper-'+role,'source-owned main accessor helper',target(raw,rva,calls[role],role))
    _require(target(raw,rva,calls['initialize'],'initialize')==carriers['initialize']['rva'] and
        target(bodies['vector'],methods['vector']['rva'],owned['vectorForward'],'vectorForward')==carriers['forward']['rva'],
        'same-carrier-helpers','authenticated source-owned initialize/forward helpers',calls['initialize'])
    for role in ('state','same'):
        _require(target(raw,rva,calls[role+'Read'],role)==target(bodies[role],methods[role]['rva'],owned[role+'Read'],role),
            'same-stored-reader-'+role,'source-owned named Int32 getter helper',target(raw,rva,calls[role+'Read'],role))
    _require(target(raw,rva,calls['sameAuxiliary'],'sameAuxiliary')==
             target(bodies['same'],methods['same']['rva'],owned['sameAuxiliary'],'sameAuxiliary'),
        'same-owned-auxiliary','source-owned getter auxiliary helper',target(raw,rva,calls['sameAuxiliary'],'sameAuxiliary'))
    _require(_mov_register(probes['saveComp'])==(64,3,2) and _mov_register(probes['saveThis'])==(64,14,1),
        'original-inputs','original UInt64 and system receiver preserved',(probes['saveComp'].hex(),probes['saveThis'].hex()))
    _require(probes['hotSlot']==bytes.fromhex('488BFB48C1EF20'),'hot-slot-selection','original UInt64 shifted right 32',probes['hotSlot'].hex())
    _require(probes['firstIndex']==bytes.fromhex('448B7B08') and probes['counter']==bytes.fromhex('4533ED') and probes['addCounter']==bytes.fromhex('4503FD'),
        'record-index','anonymous cache Int32 at8 plus zero-initialized loop counter',probes['firstIndex'].hex())
    _require(probes['queryArgs']==bytes.fromhex('0FB7D7458BC7498BCE') and contract['probes']['queryArgs']['offset']+len(probes['queryArgs'])==calls['query'],
        'provider-same-index','zero-extended UInt16 hotSlot and same R15D conditionIndex immediately supplied',probes['queryArgs'].hex())
    _require(probes['queryReturn']==bytes.fromhex('89457F') and _mov_register(probes['stateReturn'])==(32,15,0),
        'comparison-values','provider EAX saved locally; stored State EAX saved in R15D',probes['queryReturn'].hex())
    _require(probes['tableSlot'][:1]==b'\xba' and struct.unpack_from('<I',probes['tableSlot'],1)[0]==vector['vtableSlot'],
        'selected-main-slot',vector['vtableSlot'],probes['tableSlot'].hex())
    stride=probes['vectorStride']
    _require(stride[:3]==bytes.fromhex('41C1E7') and 1<<stride[3]==vector['elementWidth'] and probes['vectorPosition']==bytes.fromhex('418D1407'),
        'selected-main-stride','same conditionIndex scaled by owned record width',stride.hex())
    _require(_lea_stack(probes['carrierOut'])==(1,-73) and probes['carrierCopies']==bytes.fromhex('0F1045B70F105DC733D2B963F600000F115DD70F1145970F115DA7'),
        'same-source-carriers','one returned32-byte source carrier duplicated to two getter slots',probes['carrierCopies'].hex())
    for role,position,buffer,tail in (('state',-73,-65,-33),('same',-105,-97,-81)):
        args=probes[role+'Args']
        _require(args[:2]==bytes.fromhex('8B55') and struct.unpack_from('<b',args,2)[0]==position and
                 _lea_stack(args[3:7])==(1,-9) and args[7:9]==bytes.fromhex('83C2') and args[9]==fields[role]['offset'],
            'stored-field-address-'+role,fields[role]['offset'],args.hex())
        source=probes[role+'Buffer'];last=probes[role+'Tail']
        _require(source[:3]==bytes.fromhex('0F1045') and struct.unpack_from('<b',source,3)[0]==buffer and
                 last[:3]==bytes.fromhex('F20F10') and last[3] in (0x45,0x4d) and struct.unpack_from('<b',last,4)[0]==tail,
            'same-byte-buffer-'+role,'ByteBuffer bytes from matching duplicated carrier',(source.hex(),last.hex()))
    branch=probes['sameEqualsOne'];at=contract['probes']['sameEqualsOne']['offset']
    _require(branch[:4]==bytes.fromhex('83F80175') and at+5+struct.unpack_from('<b',branch,4)[0]==contract['probes']['unequalPredicate']['offset'],
        'literal-selector','only IsSame==1 takes equality; all other Int32 take inequality',branch.hex())
    _require(probes['equalPredicate']==bytes.fromhex('443B7D7F0F94C1') and probes['unequalPredicate']==bytes.fromhex('443B7D7F0F95C1'),
        'stored-state-predicate','CMP stored State to provider value; SETE or SETNE',(probes['equalPredicate'].hex(),probes['unequalPredicate'].hex()))
    for name,role in (('patchBranch','updatePatch'),('statePatchBranch','statePatch'),('samePatchBranch','samePatch')):
        branch=probes[name];at=contract['probes'][name]['offset']
        _require(branch[:4]==bytes.fromhex('84C00F85') and calls[role]+5==at and at+8+struct.unpack_from('<i',branch,4)[0]>=len(raw),
            'conditional-fast-route-'+role,'named check AL immediately selects external alternative',branch.hex())
    _require(probes['cacheChanged']==bytes.fromhex('0FB64306403AC6408873060F95C0') and
             contract['probes']['cacheChanged']['offset']+len(probes['cacheChanged'])==contract['probes']['returnFrame']['offset'],
        'return-is-change-flag','old anonymous cache byte6 compared with SIL, rewritten; SETNE AL',probes['cacheChanged'].hex())
    _require(probes['returnFrame']==bytes.fromhex('4C8D9C24D0000000498B5B30498B7338498B7B40498BE3415F415E415D415C5DC3'),
        'change-flag-return','selected epilogue does not overwrite AL',probes['returnFrame'].hex())
    state_start=contract['probes']['stateReturn']['offset']+len(probes['stateReturn'])
    state_ends={contract['probes'][name]['offset'] for name in ('equalPredicate','unequalPredicate')}
    _direct_call_boundary(partitions['update'],565,'state-auxiliary-local-preservation')
    _cfg_preserved(partitions['update'],rva,
        contract['probes']['queryReturn']['offset']+len(probes['queryReturn']),state_ends,'rbp',
        set(calls.values())|{565},
        {221,contract['probes']['statePatchBranch']['offset']+2,
         contract['probes']['samePatchBranch']['offset']+2},_provider_local_store_check)
    _cfg_preserved(partitions['update'],rva,state_start,state_ends,'r15d',
        {calls['samePatch'],calls['sameRead'],calls['sameAuxiliary']},
        {contract['probes']['samePatchBranch']['offset']+2})
    _preserved_interval(partitions['update'],calls['sameRead']+5,contract['probes']['sameEqualsOne']['offset'],
        'rax',set(),'IsSame-return-to-selector')
    frame_start=contract['probes']['returnFrame']['offset']
    _preserved_interval(partitions['update'],frame_start,frame_start+len(probes['returnFrame']),
        'rax',set(),'changed-flag-return')
    return {'record':'MissionCondition','storedStateField':'State','selectorField':'IsSame','selectorLiteral':1,
        'selectedRelation':'equal','fallbackRelation':'not_equal','provider':methods['query']['type']+'.'+methods['query']['method'],
        'providerParameterNames':methods['query']['parameterNames'],'updateReturnsChangedFlag':True,
        'runtimeObserved':False,'authoredGroupToLiveCacheResolved':False,'providerValueOriginResolved':False}


def validate(gameassembly,metadata):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='validated',label='mission_condition_consumers')
    inputs=contract['nativeInputs']
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    _require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs','validated',f'{gate.status}:{gate.detail}')
    unity=_fingerprint(Path(gameassembly).parent/'UnityPlayer.dll')
    _require(unity['sha256'].upper()==inputs['unityPlayerSha256'].upper(),'unity-input',inputs['unityPlayerSha256'],unity['sha256'])
    image=open_native_image(gameassembly,metadata);methods=dict(contract['methods']);catalogs={}
    for dependency in contract['dependencies']:
        filename=dependency['path']
        catalog,_=read_reviewed_contract(CONTRACTS_DIR/filename,schema=dependency['schema'],status='validated',label='mission_condition_dependency')
        _require(catalog['nativeInputs']==inputs,'dependency-build-'+filename,inputs,catalog['nativeInputs'])
        catalogs[filename]=catalog
        rows=catalog['methods'].values() if isinstance(catalog['methods'],dict) else catalog['methods']
        rows=list(rows)
        for role,selector in dependency['methodRoles'].items():
            selected=[row for row in rows if (row['type'],row['method'])==(selector['type'],selector['method'])]
            _require(len(selected)==1,'selected-method-'+role,'exactly one source-owned method',len(selected))
            methods[role]=selected[0]
    bodies={role:_check_method(image,row) for role,row in methods.items()}
    _method_call_abi(image,methods,contract['methodCallAbi'])
    _vector_return_abi(image,image.metadata.methods[methods['vector']['index']])
    extents=image.mapper.pdata_function_extents(image.pe)
    for role in ('update','query'):
        row=methods[role]
        _require(extents.get(image.pe.image_base+row['rva'])==image.pe.image_base+row['rva']+row['bodyExtent'],
            'primary-body-'+role,row['bodyExtent'],extents.get(image.pe.image_base+row['rva']))
    for role in ('state','same','vector','patchCheck'):
        row=methods[role];end=extents.get(image.pe.image_base+row['rva'])
        _require(end is not None and 0<end-(image.pe.image_base+row['rva'])<=len(bodies[role]),
            'owned-primary-body-'+role,'primary body inside source-owned pinned window',end)
        bodies[role]=bodies[role][:end-(image.pe.image_base+row['rva'])]
    query=image.metadata.methods[methods['query']['index']];params=image.metadata.parameters_for(query)
    _require(methods['query']['parameters']==['System.UInt16','System.Int32'] and methods['query']['parameterNames']==['hotSlot','conditionIndex'],
        'query-signature','named UInt16 hotSlot and Int32 conditionIndex',methods['query']['parameters'])
    _ordinary_primitive_abi(image,params[0].type_index,0x07,'condition-query-hotSlot')
    scalar=catalogs['dynamic_scalar_components_native.json'];main=catalogs['dynamic_main_vector_native.json']
    record=next(row for row in scalar['layout']['records'] if row['name']=='MissionCondition')
    fields={role:next(field for field in record['fields'] if field['getterMethodIndex']==methods[role]['index']) for role in ('state','same')}
    for role,field in fields.items():
        _require(field['type']=='System.Int32' and _getter_offset(bodies[role],role)==field['offset'],
            'source-owned-field-'+role,field['offset'],_getter_offset(bodies[role],role))
    vector=next(row for row in main['layout']['vectors'] if row['name']=='MissionCondition')
    _require(vector['elementWidth']==record['width'],'owned-record-width',record['width'],vector['elementWidth'])
    carriers=_validate_carriers(scalar['layout'],image)
    flow=_check_comparison_flow(contract,bodies['update'],bodies,methods,vector,fields,carriers,_composed_decoder(image.mapper))
    query_context=_query_context(image,bodies['query'],methods['query'],contract['queryContext'])
    query_flow=_check_query_flow(bodies['query'],methods['query']['rva'],contract['queryContext'],_composed_decoder(image.mapper))
    return {'format':'endfield.dynamic-mission-condition-consumers-native-audit.v2','status':'validated',
        'nativeInputs':inputs,'flow':flow,'providerQuery':query_flow,'queryContext':query_context,
        'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_condition_consumers_native_latest.json')
    args=parser.parse_args(argv)
    try:
        sources=_parser_source_snapshots(Path(__file__))
        contract=json.loads(CONTRACT.read_text())
        sources.extend(_fingerprint(path) for path in [CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
            *(CONTRACTS_DIR/dependency['path'] for dependency in contract['dependencies'])])
        inputs=[_fingerprint(path) for path in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs]
        groups._guard_publication(args.output_json,protected)
        result=validate(args.gameassembly,args.metadata);result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print(f'dynamic-mission-condition-consumers-native:{str(exc)[:1400]}',file=sys.stderr);return 1
    print('MissionCondition native comparison passed: IsSame==1 selects State equality; update returns change flag; runtime unresolved')
    return 0


if __name__=='__main__':raise SystemExit(main())
