"""Current named BlackboardInt and three-scalar BlackboardVector3 programs."""
from __future__ import annotations

import json

from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.buff_frontiers_regenerate import _method_row
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.native_image import read_reviewed_contract,open_native_image,native_validation_failure
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,buff_profile_source as source
from scripts.game_data.memorypack import buff_blackboard_double_native,pooled_source_helper,primitive_param,scalar_param_native
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.skill_custom_root_motion_regenerate import prove_primitive
from scripts.game_data.skill_timeline_routes_regenerate import reference_primitives
from scripts.game_data.contracts import CONTRACTS_DIR

INT_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardIntForMemoryPack'
INT_BASE='Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_int_int_ForMemoryPack'
INT_INSTANCE='Beyond.Blackboard+BlackboardParamBase`2<int,int>'
VECTOR_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardVector3ForMemoryPack'
DOUBLE='Beyond.Blackboard+BlackboardDouble'
need=source.need


def integer_header(rows,header,offsets,barrier,base):
    b,r,c,s=(offsets[n] for n in ('currentPtr','bufferLength','advancedCount','consumed'))
    null=ec.one(rows,lambda row:row['text']=='cmp dil, -0x1','blackboardInt.null')
    load=ec.one(rows,lambda row:ec.va(row)<ec.va(null) and row['text']==f'mov rax, [rbx+{b:#x}]','blackboardInt.header-source')
    g=_Path(rows);g.at=ec.va(load)
    g.take(f'mov rax, [rbx+{b:#x}]','movzx edi, byte [rax]',f'mov ebp, [rbx+{r:#x}]','sub ebp, 0x1');g.branch(8,False)
    g.take(f'inc qword [rbx+{b:#x}]',f'inc dword [rbx+{c:#x}]',f'inc dword [rbx+{s:#x}]',
        f'mov [rbx+{r:#x}], ebp','cmp dil, -0x1')
    edge=g.rows[g.at];g.branch(4,False);g.take('cmp qword [rsi], 0x0');g.branch(4,False)
    source.need('blackboardInt.header-rejoin',g.at==ec.va(header))
    n=_Path(rows);n.at=control_transfer(edge)['target']
    n.take('mov rcx, rsi','mov qword [rsi], 0x0');n.call(barrier);n.jump()
    n.take('mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]','mov rsi, [rsp+0x40]',
        'add rsp, 0x20','pop rdi','ret')
    source.need('blackboardInt.frame',[row['text'] for row in rows[:5]]==[
        'mov [rsp+0x8], rbx','mov [rsp+0x10], rbp','mov [rsp+0x18], rsi','push rdi','sub rsp, 0x20'])
    by={ec.va(row):row for row in rows}
    return dict(sourceProgram=[ec.site(by[a],base) for a in g.seen],nullProgram=[ec.site(by[a],base) for a in n.seen],wireBytes=1)


def setter_program(rows,entry,instance,kind):
    holder,arg,width={'string':('rcx','rdx',8),'bool':('rax','dl',1),'int':('rax','edx',4)}[kind]
    stores=[]
    for row in rows:
        memory=row.get('memoryOperation',{});address=memory.get('address',{})
        if memory.get('direction')=='store' and memory.get('register')==arg and address.get('base')==holder:
            source.need('blackboardInt.setter-width',memory.get('memoryBytes')==width and address.get('index') is None)
            stores.append(row)
    store=ec.one(stores,lambda row:True,'blackboardInt.setter-store')
    slot=store['memoryOperation']['address']['displacement']
    source.need('blackboardInt.setter-slot',16<=slot<128)
    g=_Path(rows);g.at=entry
    g.take('sub rsp, 0x28',f'mov {holder}, [rcx+{instance:#x}]',f'test {holder}, {holder}');g.branch(4,False)
    g.take(f'mov [{holder}+{slot:#x}], {arg}')
    barrier=None
    if kind=='string':
        g.take(f'add rcx, {slot:#x}','add rsp, 0x28');tail=g.row();flow=control_transfer(tail)
        source.need('blackboardInt.setter-reference-tail',flow['kind']=='jump');barrier=flow['target']
    else:g.take('add rsp, 0x28','ret')
    return slot,g.seen,barrier


def integer_program(rows,header,instance,slots,targets,barrier):
    g=_Path(rows);g.at=ec.va(header)
    g.take('cmp dil, 0x3');g.branch(5,False)
    for index,(name,kind,register) in enumerate((('blackboardKey','string','rax'),('useBlackboardKey','bool','al'),('value','int32','eax'))):
        if index<2:g.take('mov rdi, [rsi]','mov rcx, rbx')
        else:g.take('mov rcx, rbx','mov rdi, [rsi]')
        g.call(targets[kind]);g.take('test rdi, rdi');g.branch(4,False)
        g.take(f'mov rcx, [rdi+{instance:#x}]','test rcx, rcx');g.branch(4,False)
        g.take(f'mov [rcx+{slots[name]:#x}], {register}')
        if index==0:g.take(f'add rcx, {slots[name]:#x}');g.call(barrier)
    g.take('mov rbx, [rsp+0x30]','mov rbp, [rsp+0x38]','mov rsi, [rsp+0x40]',
        'add rsp, 0x20','pop rdi','ret')
    return g.seen


def vector_program(rows,header,instance,slots,contexts,target):
    g=_Path(rows);g.at=ec.va(header)
    g.take('cmp bpl, 0x3');g.branch(5,False)
    stores=[]
    for index,(field,context) in enumerate(zip(('x','y','z'),contexts)):
        source.need('blackboardVector3.context-order',g.at==context['instructionRva']+target['base'])
        load=g.row();source.need('blackboardVector3.exact-context',ec.raw(load).hex().upper()==context['instructionHex'])
        wrapper='rsi' if index<2 else 'rdi'
        g.take('mov rcx, rbx',f'mov {wrapper}, [rdi]');g.call(target['reader'])
        g.take(f'test {wrapper}, {wrapper}');g.branch(4,False)
        g.take(f'mov r8, [{wrapper}+{instance:#x}]','test r8, r8');g.branch(4,False)
        guard=g.row();raw=ec.raw(guard)
        source.need('blackboardVector3.barrier-guard',len(raw)==7 and raw[:2]==b'\x83\x3d' and raw[-1]==0)
        if g.rows[g.at]['text'].startswith('lea rbp, [rip'):
            address=g.row();source.need('blackboardVector3.bitmap-address',len(ec.raw(address))==7 and ec.raw(address)[:3]==b'\x48\x8d\x2d')
        stores.append(g.at);g.take(f'mov [r8+{slots[field]:#x}], rax');g.branch(4,True)
    g.take('mov rbx, [rsp+0x38]','mov rbp, [rsp+0x40]','mov rsi, [rsp+0x48]',
        'add rsp, 0x20','pop rdi','ret')
    return g.seen,stores


def derive(image,inputs,reviewed,*,kind):
    from scripts.game_data.memorypack.blackboard_reference_parent import derive as parent_reference
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    name='Beyond.Blackboard+Blackboard'+('Int' if kind=='int' else 'Vector3')
    wrapper_name=INT_WRAPPER if kind=='int' else VECTOR_WRAPPER
    source.need('blackboard.profile-declarations',reviewed['typeName']==name and reviewed['wrapperName']==wrapper_name)
    wrapper=ec.one(list(image.memorypack_wrappers.values()),lambda w:w.name==wrapper_name,'blackboard.wrapper')
    source.need('blackboard.wrapped-type',wrapper.wrapped_type==name and not wrapper.wrapped_is_value_type)
    members=[dict(name=m.name,declaredType=m.declared_type) for m in wrapper.members]
    expected=([dict(name='blackboardKey',declaredType='string'),dict(name='useBlackboardKey',declaredType='bool'),dict(name='value',declaredType='int')]
        if kind=='int' else [dict(name=n,declaredType=DOUBLE) for n in ('x','y','z')])
    source.need('blackboard.member-order-types',members==expected,members)
    clones=ec.clone_facts(image,inputs);clone=clones['ReadValue']
    outer=parent_reference(image,type_name=name,wrapper_name=wrapper_name,
        parent_wrapper=reviewed['parentRole']['ownerType'],parent_field=reviewed['parentRole']['field'],clone_fact=clone)
    method=_method_row(image,[0,wrapper_name,'Deserialize',1]);family,windows,rows=ec.family(image,method[3])
    primitive_param.reader_abi(image,ctx,image.metadata.methods[method[0]],wrapper)
    source.need('blackboard.decode',not any(r['text'].startswith('db ') for r in rows))
    offsets=ec.source_offsets(image);header=ec.one(rows,lambda row:row['text']==('cmp dil, 0x3' if kind=='int' else 'cmp bpl, 0x3'),'blackboard.member3')
    path,choices=ec.fast_path(rows,header,'rbx',offsets);contexts=ec.contexts(image,rows)
    facts={};slots={};reference_barrier=None
    if kind=='int':
        source.need('blackboardInt.base-wrapper',ctx.parent(wrapper_name)==INT_BASE and ctx.parent(name)==INT_INSTANCE)
        real=ctx.field(wrapper_name+'::__realInstance');holder=ctx.field(INT_BASE+'::___instance')
        source.need('blackboardInt.instance-types',real[1]==name and holder[1]==INT_INSTANCE)
        instance=holder[2];td=image.named_types[INT_BASE]
        setters=image.setter_methods(td,parameter='typeName',label='blackboardIntSource')
        source.need('blackboardInt.setter-declarations',[(s[1],s[2]) for s in setters]==[
            ('set___blackboardKey__','System.String'),('set___useBlackboardKey__','System.Boolean'),('set___value__','System.Int32')])
        setter_proofs=[]
        for member,setter in zip(expected,setters):
            abi={'string':('string',14,True),'bool':('bool',2,False),'int':('int',8,False)}[member['declaredType']]
            scalar_param_native.owned_method_abi(image,ctx,setter[0],td.index,('void',1,False),[abi],'blackboardIntSource.setter')
            pointer=image.method_pointer_va(image.metadata.methods[setter[0]]);sf,sw,sr=ec.family(image,pointer-base)
            slot,program,barrier=setter_program(sr,pointer,instance,member['declaredType']);slots[member['name']]=slot
            if barrier is not None:reference_barrier=barrier
            by={ec.va(r):r for r in sr};windows+=sw
            setter_proofs.append(dict(method=setter,family=sf,instanceOffset=instance,fieldOffset=slot,selectedProgram=[ec.site(by[a],base) for a in program]))
        source.need('blackboardInt.distinct-slots',len(set(slots.values()))==3)
        primitives=reference_primitives();reference=json.loads((CONTRACTS_DIR/'skill_custom_root_motion_native.json').read_bytes())
        source.need('blackboardInt.primitive-inputs',reference['nativeInputs']==inputs)
        targets=dict(clones,string=base+primitives['bytes'],bool=base+primitives['bool'],int32=base+primitives['int32'])
        prove_primitive(image,targets['bool'],'bool-byte');prove_primitive(image,targets['int32'],'int32')
        pooled_source_helper.validate_on_image(image,targets['string'],inputs)
        header_proof=integer_header(rows,header,offsets,reference_barrier,base)
        addresses=integer_program(rows,header,instance,slots,targets,reference_barrier)
        kinds=['byte-payload','byte','scalar32']
        facts=dict(baseWrapper=INT_BASE,instanceOffset=instance,setters=setter_proofs,fieldOffsets=slots)
        child_contracts=[]
    else:
        holder=ctx.field(wrapper_name+'::__instance');source.need('blackboardVector3.instance-type',holder[1]==name)
        instance=holder[2]
        for field in ('x','y','z'):
            actual=ctx.field(name+'::'+field);source.need('blackboardVector3.field-type',actual[1]==DOUBLE);slots[field]=actual[2]
        source.need('blackboardVector3.context-types',len(contexts)==3 and all(c['methodOwner']=='MemoryPack.MemoryPackReader' and
            c['methodName']=='ReadValue' and c['methodSpec'][0]==clone['equivalentMethod'][0] and c['typeKind']==0x12 and
            c['fullTypeName']==DOUBLE and c['typeDefinition']==ctx.index.types[DOUBLE].index and c['register']=='rdx' for c in contexts))
        scalar=buff_blackboard_double_native.derive(image,inputs)
        source.need('blackboardVector3.scalar-current',scalar==json.loads(buff_blackboard_double_native.CONTRACT_PATH.read_bytes()))
        header_proof=ec.wrapper_header(image,rows,header,'rbx',offsets)
        addresses,stores=vector_program(rows,header,instance,slots,contexts,dict(base=base,reader=base+clone['targetRva']))
        kinds=['scalar-payload']*3;by={ec.va(r):r for r in rows}
        facts=dict(instanceOffset=instance,fieldOffsets=slots,directStores=[ec.site(by[a],base) for a in stores])
        child_contracts=[buff_blackboard_double_native.CONTRACT_PATH.name]
        targets=dict(clones,bool=None,int32=None,string=None)
    source.need('blackboard.complete-selected-path',addresses==[ec.va(row) for row in path])
    if kind=='int':targets.update(ReadValue=clone)
    claim=dict(ownerType=wrapper_name,members=expected,anonymousReadOrder=kinds)
    events=ec.profile_events(image,claim,path,contexts,'rbx',offsets,targets,{DOUBLE:'scalar-payload'})
    wire_kinds={'byte-payload':'int32-pool-index','byte':'bool-byte','scalar32':'raw-int32','scalar-payload':'blackboard-double'}
    layout=dict(nullHeader=255,memberCount=len(members),members=[dict(name=m['name'],kind=wire_kinds[e['kind']]) for m,e in zip(members,events)])
    source.need('blackboard.wire-layout',reviewed['wireLayout']==layout,layout)
    by={ec.va(r):r for r in rows};unique={}
    for window in windows+outer['codeWindows']+outer.get('setterWindows',[]):unique.setdefault((window['startRva'],window['endRva']),window)
    out=dict(reviewed)
    out.update(status='exact-current-build',nativeInputs=dict(inputs),typeDefinition=outer['typeDefinition'],contextTypeKind=0x12,
        referenceReaderMethodDefinition=clone['equivalentMethod'][0],referenceReaderTargetRva=clone['targetRva'],
        readerMethod=method,codeWindows=list(unique.values()),proof=dict(family=family,readerOffsets=offsets,header=header_proof,
        outerReference=outer,events=events,typedStores=facts,selectedProgram=[ec.site(by[a],base) for a in addresses],
        selectedConditions=[dict(instruction=ec.site(d['instruction'],base),condition=d['condition'],taken=d['taken']) for d in choices],
        childContracts=child_contracts))
    return json.loads(json.dumps(out))


def validate_on_image(owner,image,inputs):
    reviewed,_=read_reviewed_contract(owner.CONTRACT_PATH,schema=owner.SCHEMA,status='exact-current-build',label=owner.LABEL)
    source.need('blackboard.native-inputs',reviewed['nativeInputs']==inputs)
    actual=owner.derive(image,inputs,reviewed)
    source.need('blackboard.current-proof',actual==reviewed,ec.first_difference(reviewed,actual))
    return {k:actual[k] for k in ('nativeInputs','typeName','typeDefinition','contextTypeKind',
        'referenceReaderMethodDefinition','referenceReaderTargetRva','wireLayout','evidenceBoundary')} | {'status':'validated'}


def validate_current(owner,*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(owner.LABEL+'.native:both-selected-paths-required')
    try:
        reviewed,_=read_reviewed_contract(owner.CONTRACT_PATH,schema=owner.SCHEMA,status='exact-current-build',label=owner.LABEL)
        inputs=reviewed['nativeInputs']
        gate=check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        image=open_native_image(gate.gameassembly,gate.metadata);_publication_gate(image,inputs)
        result=owner.validate_on_image(image,inputs);_publication_gate(image,inputs)
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError) as error:
        return native_validation_failure(error,label=owner.LABEL,source_path=owner.CONTRACT_PATH)
