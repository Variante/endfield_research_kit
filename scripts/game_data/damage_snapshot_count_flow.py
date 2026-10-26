"""Prove a typed count request and the actual helper's null-input return path."""
from __future__ import annotations
import struct
from scripts.game_data.damage_snapshot_cache_flow import _address,_require
from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_pointer
from scripts.game_data.il2cpp.context import (relative_branch_target,rip_qword_load_target,method_spec_usage_index,
    method_spec_record,generic_type_carrier,method_parameter_owner)
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext


def _program(rows,expected,start,label):
    _require(len(rows)>=len(expected),label+'-length',len(expected),len(rows));address=start
    for r,raw in zip(rows,expected):
        _require(_address(r)==address,label+'-contiguity',hex(address),r['va'])
        actual=bytes.fromhex(r['bytes']);_require(actual==raw,label+'-instruction',raw.hex(),actual.hex());address+=len(raw)
    return address


def check_count_caller(rows,*,start,return_entry,operands):
    _require(len(rows)>=9,'snapshot-count-caller-length',9,len(rows))
    root=operands['opaqueActionRootDisp8'];child=operands['opaqueCollectionDisp8']
    _require(all(type(x) is int and 0<=x<=127 for x in (root,child)),'snapshot-count-caller-operands','positive disp8',[root,child])
    expected=[b'\x48\x8b\x4f'+bytes([root]),b'\x48\x85\xc9',None,None,b'\x48\x8b\x49'+bytes([child]),None,b'\x44\x8b\xf0',b'\x85\xc0',None]
    address=start;helper=None;excluded=None
    for n,(r,encoding) in enumerate(zip(rows,expected)):
        raw=bytes.fromhex(r['bytes']);_require(_address(r)==address,'snapshot-count-caller-contiguity',hex(address),r['va'])
        if n==2:
            _require(len(raw)==6 and raw[:2]==b'\x0f\x84','snapshot-count-root-guard','JE nonnull root exclusion',raw.hex());excluded=address+6+int.from_bytes(raw[2:],'little',signed=True)
        elif n==3:_require(len(raw)==7 and raw[:3]==b'\x48\x8b\x15','snapshot-count-context-register','RDX RIP qword',raw.hex())
        elif n==5:
            _require(len(raw)==5 and raw[:1]==b'\xe8','snapshot-count-physical-call','direct CALL',raw.hex());helper=relative_branch_target(raw,address,source='snapshotCount')
        elif n==8:
            _require(len(raw)==2 and raw[:1]==b'\x7e','snapshot-count-result-guard','signed JLE',raw.hex())
            target=address+2+int.from_bytes(raw[1:],'little',signed=True)
            _require(target==return_entry,'snapshot-count-zero-return-join',hex(return_entry),hex(target))
        else:_require(raw==encoding,'snapshot-count-caller-instruction',encoding.hex(),raw.hex())
        address+=len(raw)
    _require(excluded not in {_address(r) for r in rows[:9]},'snapshot-count-root-excluded','outside selected caller',hex(excluded))
    return {'callerEntry':hex(start),'physicalHelper':hex(helper),'contextLoad':rows[3],
            'resultRegisterTransfer':'EAX to R14D, then signed TEST EAX/JLE','zeroResultReturnJoin':hex(return_entry),
            'excludedRootNullTarget':hex(excluded),'callerInstructionCount':9,
            'anonymousRootChildOperands':{'actionRootDisp8':root,'rootCollectionDisp8':child}}


def check_count_null_helper(entry_rows,return_rows,*,pointer,entry_end,return_end,context_slot):
    _require(type(context_slot) is int and 0<=context_slot<=127,'snapshot-count-helper-slot','positive disp8',context_slot)
    expected=[b'\x48\x89\x5c\x24\x18',b'\x57',b'\x48\x83\xec\x30',b'\x48\x83\x7a'+bytes([context_slot])+b'\x00',
              b'\x48\x8b\xda',b'\x48\x8b\xf9',None,b'\x48\x85\xff',None]
    _require(len(entry_rows)>=9,'snapshot-count-helper-prefix',9,len(entry_rows))
    address=pointer;context_excluded=None;null_target=None
    for n,(r,encoding) in enumerate(zip(entry_rows,expected)):
        raw=bytes.fromhex(r['bytes']);_require(_address(r)==address and address+len(raw)<=entry_end,'snapshot-count-helper-entry-range','owned exact prefix',r['va'])
        if n in (6,8):
            _require(len(raw)==6 and raw[:2]==b'\x0f\x84','snapshot-count-helper-condition','JE context/null receiver',raw.hex())
            target=address+6+int.from_bytes(raw[2:],'little',signed=True)
            if n==6:context_excluded=target
            else:null_target=target
        else:_require(raw==encoding,'snapshot-count-helper-instruction',encoding.hex(),raw.hex())
        address+=len(raw)
    ret=[b'\x48\x8b\x5c\x24\x50',b'\x33\xc0',b'\x48\x83\xc4\x30',b'\x5f',b'\xc3']
    actual_end=_program(return_rows,ret,null_target,'snapshot-count-null-return')
    _require(actual_end==return_end,'snapshot-count-null-return-extent','complete exact RET fragment',hex(actual_end))
    _require(context_excluded not in {_address(r) for r in entry_rows[:9]+return_rows[:5]},'snapshot-count-context-excluded','outside selected null graph',hex(context_excluded))
    return {'helperEntryPrefixBytes':address-pointer,'helperEntryInstructionCount':9,'nullReturnEntry':hex(null_target),
            'nullReturnInstructionCount':5,'nullResultEax':0,'nullResultZeroExtendsRax':True,
            'excludedContextZeroTarget':hex(context_excluded),'wholeHelperSemanticsProved':False,
            'boundary':'The actual helper entry has exact pdata prefix ownership; a nonzero anonymous context-slot selection and null incoming RCX reach a separate exact owned restoring RET fragment. It restores RBX/RDI and frame, explicitly XORs EAX and returns zero. Context-zero and nonnull receiver paths are excluded; fragment ownership is not whole-function ownership.'}


def _count_request(index,load,spec):
    selected=NativeReferenceContext(index.image,index=index);reg=index.image.registration
    cell=rip_qword_load_target(bytes.fromhex(load['bytes']),_address(load),source='snapshotCountContext')
    si=method_spec_usage_index(index.pe.bytes_at_va(cell,8),reg['methodSpecsCount'],source='snapshotCountContext',offset=cell)
    addr=int(reg['methodSpecs'],16)+si*12
    di,ci,mi=method_spec_record(index.pe.bytes_at_va(addr,12),len(index.metadata.methods),reg['genericInstsCount'],source='snapshotCountContext',offset=addr)
    method=index.metadata.methods[di];owner=index.metadata.type_full_name(index.metadata.types[method.declaring_type])
    _require(owner==spec['countType'] and index.metadata.string(method.name_index)==spec['countMethod'] and method.flags&0x10 and ci==-1 and mi>=0,
             'snapshot-count-request-owner','selected static generic SafeCount method',[owner,ci,mi])
    require_ordinary_type(selected,method.return_type,'int','snapshot.count.return')
    parameters=index.metadata.parameters_for(method);_require(len(parameters)==1,'snapshot-count-request-arity',1,len(parameters))
    tp=selected.type_pointer(parameters[0].type_index);raw=index.pe.bytes_at_va(tp,16)
    _require(len(raw)==16 and raw[10:12]==b'\x15\x00','snapshot-count-formal-reference','ordinary generic reference',raw.hex())
    cp=int.from_bytes(raw[:8],'little');carrier_raw=index.pe.bytes_at_va(cp,32);bp=int.from_bytes(carrier_raw[:8],'little')
    carrier=generic_type_carrier(raw,carrier_raw,index.pe.bytes_at_va(bp,16),type_pointer=tp,type_count=len(index.metadata.types),source='snapshotCountFormal')
    base=index.metadata.types[carrier['baseDefinitionIndex']]
    _require(index.metadata.type_full_name(base)==spec['formalCollectionType'] and index.pe.bytes_at_va(bp,16)[11]==0,
             'snapshot-count-formal-owner','ordinary IList generic definition',index.metadata.type_full_name(base))
    formal=index.image.instantiations.resolve_pointer(carrier['classInstantiationPointerVa']).arguments
    _require(len(formal)==1,'snapshot-count-formal-arity',1,len(formal));fr=index.pe.bytes_at_va(formal[0].type_pointer_va,16)
    _require(len(fr)==16 and fr[10:12]==b'\x1e\x00','snapshot-count-formal-mvar','ordinary method MVAR',fr.hex())
    ownership=method_parameter_owner(index.metadata.buf,int.from_bytes(fr[:8],'little'),[m.generic_container_index for m in index.metadata.methods],source='snapshotCountMvar')
    _require(ownership['methodIndex']==di and ownership['ordinal']==0,'snapshot-count-mvar-owner',[di,0],[ownership['methodIndex'],ownership['ordinal']])
    arguments=index.image.instantiations.resolve(mi).arguments;_require(len(arguments)==1,'snapshot-count-method-arity',1,len(arguments))
    name=runtime_type_name(index.pe,index.metadata,arguments[0].type_pointer_va)
    require_ordinary_pointer(selected,arguments[0].type_pointer_va,name,spec['unitType'],'snapshot.count.methodArg0',reference_kind=0x12)
    entries=sorted({p for p,aliases in index.names_by_pointer.items() if any(a.get('methodSpecIndex')==si for a in aliases)})
    return {'countMethodSpecIndex':si,'requestedMethod':owner+'.'+spec['countMethod'],'requestedOrdinaryResult':'int',
            'requestedCollectionFormal':spec['formalCollectionType']+'<method MVAR0>','requestedMethodArgument':name,
            'registeredCountRequestEntries':[hex(p) for p in entries],'staticUsageCell':hex(cell)}


def check_snapshot_count(index,clear_proof,counter_proof,spec):
    _require(clear_proof.get('claim')=='snapshotIncomingThisCacheReset' and counter_proof.get('claim')=='snapshotResetZeroToCounterInitialization',
             'snapshot-count-dependencies','fresh reset/zero-initialization',[clear_proof.get('claim'),counter_proof.get('claim')])
    body=index.body(spec['type'],spec['method']);_require(body.symbol==clear_proof['symbol']==counter_proof['symbol'],'snapshot-count-same-body','same selected producer',body.symbol)
    start_matches=[n for n,r in enumerate(body.rows) if bytes.fromhex(r['bytes'])==b'\x48\x8b\x4f'+bytes([spec['anonymousOperands']['opaqueActionRootDisp8']]) and _address(r)>int(counter_proof['counterInitialization'],16)
                   and n+3<len(body.rows) and bytes.fromhex(body.rows[n+3]['bytes'])[:3]==b'\x48\x8b\x15']
    _require(len(start_matches)==1,'snapshot-count-caller-selection','one following exact root load',len(start_matches))
    fragment=body.rows[start_matches[0]:];proof=check_count_caller(fragment,start=_address(fragment[0]),return_entry=int(clear_proof['nullTargetReturn'],16),operands=spec['anonymousOperands'])
    request=_count_request(index,proof.pop('contextLoad'),spec);pointer=int(proof['physicalHelper'],16)
    _require(pointer in index.extents and 0<index.extents[pointer]-pointer<=256,'snapshot-count-entry-extent','exact bounded first pdata fragment',hex(pointer))
    end=index.extents[pointer];entry_rows=index._decode(pointer,end-pointer)
    _require(b''.join(bytes.fromhex(r['bytes']) for r in entry_rows)==index.pe.bytes_at_va(pointer,end-pointer),'snapshot-count-entry-byte-coverage','complete prefix fragment partition',end-pointer)
    _require(len(entry_rows)>=9,'snapshot-count-helper-available',9,len(entry_rows));branch=entry_rows[8];br=bytes.fromhex(branch['bytes'])
    null_pointer=_address(branch)+6+int.from_bytes(br[2:],'little',signed=True)
    _require(null_pointer in index.extents and 0<index.extents[null_pointer]-null_pointer<=128,'snapshot-count-null-extent','exact bounded RET fragment',hex(null_pointer))
    null_end=index.extents[null_pointer];returns=index._decode(null_pointer,null_end-null_pointer)
    _require(b''.join(bytes.fromhex(r['bytes']) for r in returns)==index.pe.bytes_at_va(null_pointer,null_end-null_pointer),'snapshot-count-null-byte-coverage','complete RET fragment partition',null_end-null_pointer)
    helper=check_count_null_helper(entry_rows,returns,pointer=pointer,entry_end=end,return_end=null_end,context_slot=spec['anonymousOperands']['helperContextSlotDisp8'])
    return {**proof,**request,**helper,'symbol':body.symbol,'claim':'snapshotCountRequestNullHelperToProducerReturn',
            'physicalHelperIsRegisteredCountRequestEntry':proof['physicalHelper'] in request['registeredCountRequestEntries'],
            'producerConsumerIndexJoinProved':False,
            'boundary':helper['boundary']+' The caller passes one opaque child pointer in RCX with a static typed SafeCount<DamageUnit> MethodSpec request in RDX. Normally returned EAX reaches R14D and signed TEST/JLE; the actual null-helper zero selects the same complete previously proved producer RET. Physical and registered entry identities are recorded independently. Valid initialized live context/storage, matching runtime generic ABI and normal calls/frame/noninterference remain conditions; nonnull count semantics, collection ownership/layout, actual index equality and final output remain unresolved.'}
