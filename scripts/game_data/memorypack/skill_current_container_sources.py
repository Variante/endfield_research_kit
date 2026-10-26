"""Current named Timeline/ForceSync normal source and direct field transfers."""
import re

from scripts.game_data.il2cpp.initializer_control import control_transfer,_ALIASES
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,scalar_param_native as scalar,pooled_source_helper
from scripts.game_data.memorypack.skill_shared_sequence_sources import (
    LABEL,_selected_wrapper,_wrapper_holder,_fast_barrier)
from scripts.game_data.memorypack.pointer_param import methods

DECLARATIONS={
 'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_TimelineActionDataForMemoryPack':(
    ('_endFrame','int','int32'),('_sequenceActionData','Beyond.Gameplay.Core.SequenceActionData','SequenceActionData'),
    ('_startFrame','int','int32'),('forceSyncAnimData','Beyond.Gameplay.Core.TimelineAction+ForceSyncAnimData','ForceSyncAnimData')),
 'Beyond.MemoryPack.Beyond_Gameplay_Core_TimelineAction_ForceSyncAnimDataForMemoryPack':(
    ('forceSync','bool','bool-byte'),('montageName','string','byte-payload'),
    ('playbackSpeed','float','float32-bits'),('targetFrame','int','int32')),
}


def _reg(name):return _ALIASES.get(name,name)


def _inline(path,index,reader,offsets):
    load=path[index+1]
    if ec.raw(load).startswith(b'\xf3\x0f\x10'):
        raw=ec.raw(load)
        if len(raw)!=4 or raw[3]&0xc7!=0x00:raise ValueError(LABEL+'.container:inline-single-address')
        # 0F10 /r with mod00,r/m000 is the actual four-byte [RAX] Single
        # load. Supply only those byte-derived facts to the shared cursor proof.
        local=list(path);local[index+1]=dict(load,memoryOperation=dict(direction='load',memoryBytes=4,
            address=dict(base='rax',index=None,displacement=0)))
        width,program=ec.inline_read(local,index,reader,offsets)
        return width,[path[index+n]for n in range(len(program))]
    return ec.inline_read(path,index,reader,offsets)


def _field_flow(path,events,fields,*,reader='rbx',output='rdi'):
    """Track only byte-proved moves and selected source results to fields."""
    state={reader:('reader',None),output:('output',None)};stored={};flags=None
    origins={event['sourceVa']:event for event in events}
    def get(register):return state.get(_reg(register))
    for row in path:
        text=row['text'];head,_,rest=text.partition(' ');origin=origins.get(ec.va(row))
        flow=control_transfer(row)
        if flow['kind']in('call','indirectCall','registerCall'):
            for reg in('rax','rcx','rdx','r8','r9','r10','r11','xmm0','xmm1','xmm2','xmm3','xmm4','xmm5'):state.pop(reg,None)
            if origin:state['xmm0'if origin['kind']=='float32-bits'else'rax']=('member',origin['memberIndex'])
            flags=None;continue
        if head=='test':
            a,_,b=rest.partition(', ');flags=get(a)if a==b else None
            continue
        if head=='setne':
            state[_reg(rest)]=flags if flags and flags[0]=='member'else None
            continue
        if head in('cmp','push','nop','ret')or head.startswith('j'):continue
        move=re.fullmatch(r'(mov|movzx|movss|movaps) (\w+), (.+)',text)
        if move:
            op,destination,value=move.groups();target=_reg(destination);tracked=None
            if re.fullmatch(r'\w+',value):tracked=get(value)
            else:
                memory=re.fullmatch(r'(?:byte |dword |qword )?\[(\w+)(?:\+0x([0-9a-f]+))?\]',value)
                if memory:
                    register,offset=memory.groups();offset=int(offset or'0',16);base=get(register)
                    if base==('output',None)and offset==0:tracked=('wrapper',None)
                    elif base==('wrapper',None)and offset==16:tracked=('original',None)
            if origin:tracked=('member',origin['memberIndex'])
            if tracked is None:state.pop(target,None)
            else:state[target]=tracked
            continue
        store=re.fullmatch(r'(mov|movss) \[(\w+)\+0x([0-9a-f]+)\], (\w+)',text)
        if store:
            op,receiver,offset,value=store.groups();base=get(receiver);origin=get(value)
            if base==('original',None):
                offset=int(offset,16)
                if not origin or origin[0]!='member':raise ValueError(LABEL+'.container:unproved-field-value:'+text)
                index=origin[1];expected=fields[index]
                if offset!=expected['offset']or index in stored:raise ValueError(LABEL+'.container:field-offset-or-duplicate:'+text)
                raw=ec.raw(row)
                width=4 if op=='movss'else 1 if raw[0]==0x88 else 8 if raw[0]==0x49 or raw[:2]==b'\x48\x89'else 4
                if width!=expected['bytes']:raise ValueError(LABEL+'.container:field-store-width:'+text)
                stored[index]=row
            continue
        # Every unreviewed register write kills its symbolic origin. It can
        # never preserve a member value through arithmetic by accident.
        destination=rest.split(',')[0]
        if re.fullmatch(r'\w+',destination):state.pop(_reg(destination),None)
        flags=None
    if set(stored)!=set(range(len(fields))):raise ValueError(LABEL+'.container:missing-field-transfer:'+str(sorted(stored)))
    return stored


def derive(image,pins):
    from scripts.game_data import skill_timeline_routes_regenerate as uniform
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    ctx=NativeReferenceContext(image);base=image.pe.image_base;offsets=scalar.reader_offsets(image,LABEL)
    clones=ec.clone_facts(image,pins);record=vector_recorder(image);proofs={}
    primitive={}
    reference=__import__('json').loads((pooled_source_helper.CONTRACT_PATH.parent/'skill_custom_root_motion_native.json').read_bytes())
    scalar.need(LABEL,'containerPrimitiveBuild',pins,reference['nativeInputs'])
    kinds=uniform.reference_primitives(reference)
    for kind,primitive_kind in(('bool','bool-byte'),('int32','int32')):
        primitive[kind]=record(kinds[kind])
        (scalar.boolean_source if kind=='bool'else scalar.integer_source)(image,primitive[kind],offsets,LABEL+'.container.'+kind)
    pooled_source_helper.validate_on_image(image,base+kinds['bytes'],pins)
    for name,declared in DECLARATIONS.items():
        wrapper=_selected_wrapper(image,name)
        scalar.need(LABEL,'containerOrderedMembers',[(n,t)for n,t,_ in declared],[(m.name,m.declared_type)for m in wrapper.members])
        method=methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(method)-base
        family,windows,rows=ec.family(image,entry)
        header=ec.one(rows,lambda r:uniform._is_cmp_r8_imm8(r)and ec.raw(r)[-1]==4,'container.header')
        reader=uniform.reader_register([dict(r,va=ec.va(r))for r in rows])
        scalar.need(LABEL,'containerReaderAndOutputSave',True,reader=='rbx'and any(r['text']=='mov rdi, rdx'for r in rows))
        path,conditions=ec.fast_path(rows,header,reader,offsets)
        events=[];source_loads=set()
        for i,row in enumerate(path):
            flow=control_transfer(row)
            if row['text']==f'mov rax, [{reader}+{offsets["currentPtr"]:#x}]':
                width,program=_inline(path,i,reader,offsets);value=path[i+1]
                events.append(dict(sourceVa=ec.va(value),mode='inline-buffered',bytes=width,program=[ec.site(r,base)for r in program]))
                source_loads.add(ec.va(value))
            elif flow['kind']=='call':
                prior=ec.last_write(path,i,'rcx')
                if prior and prior['text']==f'mov rcx, {reader}':
                    events.append(dict(sourceVa=ec.va(row),mode='direct-source',targetRva=flow['target']-base))
            elif flow['kind']in('indirectCall','registerCall','indirectJump','registerJump'):
                raise ValueError(LABEL+'.container:unreviewed-indirect-transfer')
        scalar.need(LABEL,'containerSourceCount',4,len(events));fields=[]
        for index,((field,typename,kind),event)in enumerate(zip(declared,events,strict=True)):
            event.update(memberIndex=index,fieldName=field,kind=kind)
            width=1 if typename=='bool'else 4 if typename in('int','float')else 8
            slot=ctx.field(wrapper.wrapped_type+'::'+field)
            scalar.need(LABEL,'containerFieldType',typename,slot[1]);fields.append(dict(name=field,offset=slot[2],bytes=width))
            if event['mode']=='inline-buffered':scalar.need(LABEL,'containerInlineWireWidth',width,event['bytes'])
            else:
                expected=kinds['bool']if kind=='bool-byte'else kinds['int32']if kind=='int32'else kinds['bytes']if kind=='byte-payload'else clones['ReadValue']['targetRva']
                scalar.need(LABEL,'containerActualSourceTarget',expected,event['targetRva'])
                if typename not in('bool','int','float','string'):
                    i=next(i for i,r in enumerate(path)if ec.va(r)==event['sourceVa'])
                    load=ec.last_write(path,i,'rdx');usage=derive_typed_usage_context(image,ec.va(load)-base,label=LABEL)
                    scalar.need(LABEL,'containerTypedSource',('MemoryPack.MemoryPackReader','ReadValue',[],[typename]),tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
                    event['typedRead']=usage
        transfers=_field_flow(path,events,fields)
        header_proof=ec.wrapper_header(image,rows,header,reader,offsets)
        barrier,_,_=_fast_barrier(image,base+header_proof['referenceBarrierTargetRva'])
        proofs[name]=dict(wrapperName=name,wrappedType=wrapper.wrapped_type,memberCount=4,
            readerMethod=[method.index,name,'Deserialize',entry],sourceFamily=family,sourceWindows=windows,
            headerProof=header_proof,holder=_wrapper_holder(ctx,image,wrapper),barrierProgram=barrier,
            sourceEvents=events,fieldOffsets=fields,fieldStores={str(i):ec.site(r,base)for i,r in transfers.items()},
            normalProgram=[ec.site(r,base)for r in path],selectedConditions=conditions,wrapperNullAdmitted=True)
    return dict(profiles=proofs,primitives=primitive,skillDataPrefix=derive_skill_prefix(image,pins),wholeSkillDataAdmitted=False)


def skill_prefix_program(regions,entry,offsets,field_offset,base):
    """Initialized existing-wrapper root49 prefix through field0/barrier only."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2410','4889742418','48897c2420','55','4154','4155','4156','4157','488bec','4881ec80000000','33f6')
    if g.relative('4c8d2d')!=base:raise ValueError(LABEL+'.root49:imagebase-source')
    flag=g.relative('403835')
    g.take('4c8bf2','488bf9');g.branch('0f85',True)
    g.take('837f'+rem+'01');g.branch('7d',True,1)
    g.take('488b47'+cur,'440fb620','8b5f'+rem,'83eb01');g.branch('79',True,1)
    g.take('48ff47'+cur,'ff47'+adv,'ff47'+used,'895f'+rem,'4180fcff');g.branch('0f84',False)
    g.take('0f29742470','493936');g.branch('0f85',True)
    g.take('4180fc31');g.branch('0f85',False)
    usage_at=g.at;usage_cell=g.relative('488b15')
    g.take('488bcf','498b1e');call_at=g.at;target=g.relative('e8')
    g.take('4885db');g.branch('0f84',False)
    g.take('488b4b10','4885c9');g.branch('0f84',False)
    slot=field_offset.to_bytes(4,'little').hex()
    g.take('488981'+slot,'4881c1'+slot);barrier=g.relative('e8')
    return dict(selectedBytes=g.seen,initializedFlagCell=flag,memberCount=49,
        directWireBytes=1,memberIndex=0,fieldOffset=field_offset,typedReadInstruction=usage_at,
        typedReadCell=usage_cell,sourceCall=call_at,sourceTarget=target,barrierTarget=barrier,
        field0CursorComposition=True,completeReturnProved=False,wholeSkillDataAdmitted=False,
        condition='Own initialized metadata path, matching existing nonnull wrapper/original, buffered source, selected MC49 and normal delegated field0/barrier return. No wrapper-null/new-wrapper path or following field is admitted.')


def derive_skill_prefix(image,pins):
    from scripts.game_data.memorypack.pointer_param import owned
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_SkillDataForMemoryPack'
    wrapper=_selected_wrapper(image,name);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    scalar.need(LABEL,'root49CurrentMetadataCount',49,len(wrapper.members))
    scalar.need(LABEL,'root49FirstMember',('actionGroupData','Beyond.Gameplay.Core.ActionGroupData'),
        (wrapper.members[0].name,wrapper.members[0].declared_type))
    field=ctx.field(wrapper.wrapped_type+'::actionGroupData')
    scalar.need(LABEL,'root49OriginalFieldType','Beyond.Gameplay.Core.ActionGroupData',field[1])
    method=methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(method)
    source=owned(image,entry);offsets=scalar.reader_offsets(image,LABEL)
    program=skill_prefix_program(source['regions'],entry,offsets,field[2],base)
    usage=derive_typed_usage_context(image,program['typedReadInstruction']-base,label=LABEL)
    scalar.need(LABEL,'root49ClosedField0Source',('MemoryPack.MemoryPackReader','ReadValue',[],[field[1]]),
        tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
    clones=ec.clone_facts(image,pins)
    scalar.need(LABEL,'root49ActualReferenceTarget',base+clones['ReadValue']['targetRva'],program['sourceTarget'])
    barrier,_,_=_fast_barrier(image,program['barrierTarget'])
    return dict(wrapperName=name,wrappedType=wrapper.wrapped_type,memberCount=49,
        readerMethod=[method.index,name,'Deserialize',entry-base],sourceWindows=source['windows'],
        holder=_wrapper_holder(ctx,image,wrapper),field0=field,typedRead=usage,program=program,
        barrierProgram=barrier,wrapperNullAdmitted=False,wholeSkillDataAdmitted=False)
