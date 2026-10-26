"""Fresh current Sequence array programs, separately below action admission.

This is the selected current source grammar, not an address translation of the
historical array contract. The native callback uses two class slot loads and a
register call. Every selected source byte is consumed by the finite programs.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def _flag(g,prefix='803d'):
    cell=g.relative(prefix);g.take('00');return cell+1


def source_program(regions,entry,offsets,fields,*,count=1,ff=False,count_limit=17):
    if (type(count)is not int or type(count_limit)is not int or not 0<=count_limit<=17
            or not -1<=count<=count_limit or type(ff)is not bool):
        raise ValueError('currentSequenceArray.witness-scope')
    g=BytesPath(regions,entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    action,guard,main=(bytes((fields[n],)).hex()for n in('actionData','guard','main'))
    collectors=[];calls={};callbacks=[]
    def call(name):
        at=g.at;target=g.relative('e8')
        if name in calls and calls[name]!=target:raise ValueError('currentSequenceArray.distinct-call:'+name)
        calls[name]=target;return at
    def byte(register,remaining):
        g.take('488b43'+cur,'0fb6'+register,'8b'+remaining+rem,'83'+('ee'if remaining=='73'else'ef')+'01')
        g.branch('79',True,1)
        g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'89'+remaining+rem)
    g.take('4053','56','57','4157','4883ec38');_flag(g)
    g.take('4c8bfa','488bd9');g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    byte('38','73');g.take('4080ffff');g.branch('0f84',ff)
    if ff:
        g.take('33f6','498bcf','498937','4883c438','415f','5f','5e','5b')
        barrier=g.relative('e9')
        return dict(selectedBytes=g.seen,wrapperNull=True,wireBytes=1,barrierTarget=barrier,
            normalReturnViaBarrier=True,wholeOwnerAdmitted=False)
    g.take('49833f00');g.branch('75',True,1)
    g.take('4080ff03');g.branch('0f85',False)
    g.take('48896c2468','4c896c2428','4c89742420')
    usage_at=g.at;usage_cell=g.relative('488b3d')
    g.take('4d8b2f','48837f3800');g.branch('75',True,1)
    g.take('488b4738','33f6','4889742460','488b38','48397738');g.branch('75',True,1)
    g.take('837b'+rem+'04');g.branch('7d',True,1)
    g.take('488b43'+cur,'8b28','448b73'+rem,'4183c6fc');g.branch('79',True,1)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','448973'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False)
    g.take('4c89642430');collector_base=g.relative('4c8d25')
    g.take('83fdff');g.branch('0f84',count==-1)
    if count==-1:
        collectors.append(g.relative('3935'));g.take('4889742460');g.branch('74',True,1)
    else:
        g.take('85ed');g.branch('0f84',count==0)
        if count==0:
            g.take('488b4738','488b7808','48397738');g.branch('75',True,1)
            g.take('488b4738','488b00','f6803801000001');g.branch('75',True,1)
            g.take('39b0e0000000');g.branch('75',True,1)
            g.take('488b4738','488b00','f6803801000001');g.branch('75',True,1)
            collectors.append(g.relative('3935'))
            g.take('488b80b8000000','488b08','48894c2460');g.branch('0f84',True)
        else:
            g.take('488b442460','4885c0');g.branch('74',True,1)
            g.take('488b4738','488b4010','f6803801000001');g.branch('75',True,1)
            g.take('488bd5','488bc8');call('arrayAllocate')
            collectors.append(g.relative('3935'));g.take('4889442460');g.branch('74',True,1)
            provider_class=g.relative('488b0d')
            g.take('39b1e0000000');g.branch('75',True,1)
            g.take('488b4f38','488b4918');call('provider')
            g.take('4c8bf0','85ed');g.branch('0f8e',False)
            g.take('660f1f840000000000');loop=g.at
            for i in range(count):
                if g.at!=loop:raise ValueError('currentSequenceArray.same-loop-entry')
                g.take('488b7c2460','4885ff');g.branch('0f84',False)
                g.take('4d85f6');g.branch('0f84',False)
                g.take('3b7718');g.branch('0f83',False)
                g.take('498b0e');call('prepare')
                g.take('4d8b0e','488bd3','8bc6','498bce','4883c004','4c8d04c7',
                    '498b8190010000','4d8b8998010000')
                callbacks.append(g.at);g.take('ffd0','ffc6','3bf5');g.branch('7c',i+1<count,1)
            g.jump('e9')
    g.take('4d85ed');g.branch('0f84',False)
    g.take('4d8b4510','4d85c0');g.branch('0f84',False)
    collectors.append(_flag(g,'833d'))
    g.take('488b442460','498940'+action);g.branch('74',True,1)
    g.take('837b'+rem+'01','498b3f');g.branch('7d',True,1)
    byte('28','73')
    g.take('4885ff');g.branch('0f84',False)
    g.take('488b4f10','4885c9');g.branch('0f84',False)
    g.take('4084ed','0f95c0','8841'+guard)
    g.take('837b'+rem+'01','498b3f');g.branch('7d',True,1)
    byte('28','73')
    g.take('4885ff');g.branch('74',False,1)
    g.take('488b4f10','4885c9');g.branch('74',False,1)
    g.take('4c8b642430','4084ed','4c8b6c2428','488b6c2468','0f95c0','4c8b742420',
        '8841'+main,'4883c438','415f','5f','5e','5b','c3')
    if len(set(collectors))!=1:raise ValueError('currentSequenceArray.same-disabled-collector')
    return dict(selectedBytes=g.seen,countWitness=count,wrapperNull=False,directWireBytes=7,
        readArrayUsageInstruction=usage_at,readArrayUsageCell=usage_cell,collectorBase=collector_base,
        collectorCell=collectors[0],calls=calls,elementCallbackSites=callbacks,
        callbackAbi=dict(receiver='r14',reader='rbx',output='array+32+index*8',
            callbackClassSlot=400,methodInfoClassSlot=408),
        arrayReferenceStride=8,savedCount='ebp',indexRegister='esi',
        boundedFreshArray=True,flagsNormalizedByNonzero=True,entryRspRestored=True,
        elementGrammarAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,list_component):
    """Join complete current source, concrete array field and owned MVAR ABI."""
    from scripts.game_data.memorypack.skill_shared_sequence_sources import (
        LABEL,_selected_wrapper,_wrapper_holder,_fast_barrier)
    from scripts.game_data.memorypack import scalar_param_native as scalar,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
    name='Beyond.MemoryPack.Beyond_Gameplay_Core_SequenceActionDataForMemoryPack'
    original='Beyond.Gameplay.Core.SequenceActionData'
    element='Beyond.Gameplay.Core.AbilityAction+AbilityActionData'
    wrapper=_selected_wrapper(image,name);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    scalar.need(LABEL,'sequenceOriginal',original,wrapper.wrapped_type)
    scalar.need(LABEL,'sequenceOrderedFields',[
        ('actionData',element+'[]'),('onlyExecuteWhenSourceIsGuard','bool'),('onlyExecuteWhenSourceIsMainChar','bool')],
        [(m.name,m.declared_type)for m in wrapper.members])
    fields={key:ctx.field(original+'::'+field)[2]for key,field in(
        ('actionData','actionData'),('guard','onlyExecuteWhenSourceIsGuard'),('main','onlyExecuteWhenSourceIsMainChar'))}
    scalar.need(LABEL,'sequenceDistinctBoundedFields',True,
        len(set(fields.values()))==3 and all(16<=n<128 for n in fields.values()))
    td=ctx.index.types[original]
    field,=[f for f in image.metadata.fields_for(td)if image.metadata.string(f.name_index)=='actionData']
    raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    scalar.need(LABEL,'sequenceOwnedSZArray',b'\x1d\x00',raw[10:12])
    element_pointer=int.from_bytes(raw[:8],'little');eraw=image.pe.bytes_at_va(element_pointer,16)
    scalar.need(LABEL,'sequenceConcreteReferenceElement',(b'\x12\x00',element,False),
        (eraw[10:12],image.type_name(int.from_bytes(eraw[:8],'little')),ctx.is_value_type(element)))
    method=methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(method)
    source=owned(image,entry);offsets=scalar.reader_offsets(image,LABEL)
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs={str(n):source_program(source['regions'],entry,offsets,fields,count=n)for n in range(-1,18)}
    ff=source_program(source['regions'],entry,offsets,fields,ff=True)
    barrier,barrier_proof,_=_fast_barrier(image,ff['barrierTarget'])
    for n,program in programs.items():
        scalar.need(LABEL,'sequenceSameCollector',barrier_proof['disabledFlagRva']+base,program['collectorCell'])
        scalar.need(LABEL,'sequenceExactCallbackCount',max(0,int(n)),len(program['elementCallbackSites']))
        for key,owner in(('provider','provider'),('prepare','prepare'),('arrayAllocate','arrayAllocate')):
            if key in program['calls']:
                scalar.need(LABEL,'sequenceActual'+key,base+list_component['symbols'][owner],program['calls'][key])
    selected=programs['1'];usage=derive_typed_usage_context(image,selected['readArrayUsageInstruction']-base,label=LABEL)
    scalar.need(LABEL,'sequenceClosedReadArray',('MemoryPack.MemoryPackReader','ReadArray',[],[element]),
        tuple(usage[k]for k in('typeName','methodName','classArguments','methodArguments')))
    symbols=ContextSymbols(image);first=symbols.context(usage['methodSpec'][0],is_method=True)
    nested=first['entries'][0]['methodSpec'][0];second=symbols.context(nested,is_method=True)
    clones=ec.clone_facts(image,pins)
    reader=symbols.context(clones['ReadValue']['equivalentMethod'][0],is_method=True)
    provider=symbols.context(list_component['providerContext']['definition'],is_method=True)
    contexts=[first,second,reader,provider]
    validate_generic_contexts(image,contexts,label=LABEL+'.sequence')
    entries=GenericEntries(image);fail=lambda k,e,a:scalar.need(LABEL,k,e,a)
    reference=validate_read_value_context(image,reader,provider,entries,fail=fail)
    context=validate_read_array_context(image,[first,second],usage,entries,element_pointer,
        reference['formatterDeserializeDefinition'],fail=fail)
    scalar.need(LABEL,'sequenceSameOwnedProviderDeclaration',reference['providerMethodDefinition'],
        second['entries'][3]['methodSpec'][0])
    # Persist finite branch/loop witnesses. Every count -1..17 was checked by
    # the same grammar above, including the actual loop-back edge each time.
    # The larger repeated traces add no new source instructions.
    selected_programs={key:programs[key]for key in('-1','0','1','2','17')}
    return dict(wrapperName=name,wrappedType=original,memberCount=3,
        readerMethod=[method.index,name,'Deserialize',entry-base],sourceWindows=source['windows'],
        holder=_wrapper_holder(ctx,image,wrapper),readerOffsets=offsets,fieldOffsets=fields,
        readArrayUsage=usage,genericContexts=contexts,ownedReferenceContext=reference,ownedArrayContext=context,
        programs=selected_programs,ffProgram=ff,barrierProgram=barrier,
        collectionCounts=list(range(-1,18)),countLimit=17,wrapperNullAdmitted=True,
        positiveArraySourceAdmitted=True,elementGrammarAdmitted=False,wholeSkillDataAdmitted=False,
        boundary='Exact selected buffered initialized current MC3/FF source, nullable bounded signed count, fresh typed reference array, slot5 normal callback ABI, repeated index/count loop, ordered normalized flags and complete selected return. Child cursor effects and live provider/allocator selection remain separately conditional.')
