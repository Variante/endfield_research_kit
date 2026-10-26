"""Exact current BezierKnot list fast path, with no standalone value codec.

The closed list source owns its signed count, raw56 buffered read and inline
Add56. Its compared callback is proved independently, but no differently
registered UnmanagedFormatter is substituted for a closed Bezier formatter.
The actual compatible provider result must select this exact compared body;
the list then takes its fully proved inline path without invoking a callback.
Ready coherent contexts, absent replacement, fresh zeroed count-sized storage
or initially empty reused storage with capacity >= count, buffered disjoint
input/output, disabled collector and normal helpers remain conditions.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='UnityEngine.Splines.BezierKnot'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAP='story-bezier-knot-list'
LIMIT=4096


def need(check,expected,actual):scalar.need('storyBezierList',check,expected,actual)


def callback_program(regions,entry,offsets):
    """Own the actual compared raw source; this asserts no registration alias."""
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec30');replacement=g.relative('488b05')
    g.take('488bda','488bd1','498bf8','488b08','4885c9');g.branch('0f85',False)
    g.take('837b'+rem+'38');g.branch('0f8c',False)
    g.take('488b43'+cur,'0f1008','0f105010','0f105820','f20f104030',
        '0f110f','0f115710','0f115f20','f20f114730','8b7b'+rem,'83c7c8');g.branch('0f88',False)
    g.take('488343'+cur+'38','8343'+adv+'38','8343'+used+'38','897b'+rem,
        '488b5c2440','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,replacementRootCell=replacement,wireBytes=56,managedOutputBytes=56,
        copySegments=[[0,16],[16,16],[32,16],[48,8]],readerRegister='rbx',outputRegister='rdi',
        originalRbxRestored=True,entryFrameRestored=True,normalReturn=True,
        closedRegistrationEquivalenceProved=False,standaloneElementAdmission=False)


def list_program(regions,entry,offsets,s,*,count,new):
    need('literal-witness',True,type(count)is int and count in(0,1,2,3)and type(new)is bool)
    if count==0:
        from scripts.game_data.memorypack.finite_value_list_empty_sources import selected_program
        result=selected_program(regions,entry,offsets,s,count=0,new=new)
        result.update(countWitness=0,elementReads=0)
        return result
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry)
    g.take('4053','57','4154','4155','4157','4881ece0000000','0f57c0','33c0',
        '837a'+rem+'04','4d8bf9','4d8be8','4889442460','488bda',
        '0f11442430','0f11442440','0f11442450');g.branch('0f8c',False)
    g.take('488b43'+cur,'448b20','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4963c4','483bc8');g.branch('0f8c',False)
    g.take('4889b42420010000','33f6','4183fcff');g.branch('0f84',False)
    g.take('4889ac2410010000','4c89b42428010000','49397500');g.branch('0f85',not new)
    if new:
        g.take('498b4f20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('498b4f20','488b91c0000000','488b4a08','48397120');g.branch('0f84',False)
        g.take('4585e4');g.branch('0f88',False)
        g.take('498b4720','488b88c0000000','488b6908','488b4520','488b88c0000000');g.branch('0f84',False)
        g.take('ba01000000');g.call(s['context']);g.take('498bd4','488bc8');g.call(s['arrayAllocate'])
        g.take('488d4f10','48894710');g.call(s['barrier'])
        g.take('498bcd','49897d00');g.call(s['barrier'])
    else:
        g.take('498b4720','498b7d00','488b88c0000000','488b4110','48397020');g.branch('75',True,1)
        g.take('ff471c','897718');g.jump('e9')
    provider_site=g.at;provider_cell=g.relative('488b0d')
    g.take('39b1e0000000');g.branch('0f84',False)
    g.take('498b4720','488b88c0000000','488b4918');g.call(s['provider'])
    g.take('4c8bf0','4585e4');g.branch('0f8e',False)
    need('actual-compared-source',s['callback'],g.relative('488d3d'))
    g.take('0f1f4000','0f1f840000000000');loop=g.at;replacement=None
    for index in range(count):
        need('same-loop-entry',loop,g.at)
        g.take('0f57c0','33c0','4889442460','0f11442430','0f11442440','0f11442450','4d85f6');g.branch('0f84',False)
        g.take('498b0e');g.call(s['prepare'])
        g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
        selected=g.relative('488b05')
        if replacement is None:replacement=selected
        need('same-replacement-cell',replacement,selected)
        g.take('488b08','4885c9');g.branch('0f85',False)
        g.take('837b'+rem+'38');g.branch('0f8c',False)
        g.take('488b43'+cur,'0f1000','0f11442430','0f104810','0f114c2440',
            '0f104020','0f11442450','f20f104830','f20f114c2460','8b7b'+rem,'83c7c8');g.branch('0f88',False)
        g.take('488343'+cur+'38','8343'+adv+'38','8343'+used+'38','897b'+rem,
            '0f10442430','498b7d00','f20f105c2460','f20f119c2418010000',
            '0f104c2440','0f10542450','0f11442468','0f114c2478','0f11942488000000','4885ff');g.branch('0f84',False)
        g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
        g.take('498b4720','488b5710','488b88c0000000','488b6930','ff471c','4885d2');g.branch('0f84',False)
        g.take('48634f18','3b4a18');g.branch('0f83',False)
        g.take('8d4101','894718','3b4a18');g.branch('0f83',False)
        # The raw IMUL and four stores are proved even if the disassembler
        # cannot frame this valid instruction sequence into text rows.
        g.take('486bc938','0f11441120','0f114c1130','0f11541140','f20f115c1150','ffc6')
        need('reloaded-compared-source',s['callback'],g.relative('488d3d'))
        g.take('413bf4');g.branch('0f8c',index+1<count)
    g.take('488bac2410010000','4c8bb42428010000','488bb42420010000',
        '4881c4e0000000','415f','415d','415c','5f','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,elementReads=count,
        headerBytes=4,elementWireBytes=56,managedElementBytes=56,arrayStrideBytes=56,
        arrayPayloadSegments=[[0,16],[16,16],[32,16],[48,8]],inlineAdd=True,elementCallbacks=0,
        countRegister='r12d',counterRegister='esi',providerOwnerUsage=dict(instruction=provider_site,cell=provider_cell),
        replacementRootCell=replacement,normalReturn=True,entryFrameRestored=True,
        nonvolatilesRestored=['rbx','rdi','r12','r13','r15','rsi','rbp','r14'],
        originalListSizeRequired=None if new else 0,spareCapacityRequired=True,
        actualCallbackEqualsComparedSourceRequired=True)


def derive(image,pins,*,typed_request,call_target):
    """Prove a collection only; the actual enclosing field/store stays separate."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context
    from scripts.game_data.memorypack.finite_value_list_empty_sources import derive as empty_source
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack import float_list_sources,numeric_list_sources,lang_key_list_sources
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    empty=empty_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    layouts={}
    plans={TYPE:(72,56,[('Position','Unity.Mathematics.float3',16),('TangentIn','Unity.Mathematics.float3',28),
        ('TangentOut','Unity.Mathematics.float3',40),('Rotation','Unity.Mathematics.quaternion',52),('Width','float',68)]),
        'Unity.Mathematics.float3':(28,12,[(n,'float',16+4*i)for i,n in enumerate(('x','y','z'))]),
        'Unity.Mathematics.quaternion':(32,16,[('value','Unity.Mathematics.float4',16)]),
        'Unity.Mathematics.float4':(32,16,[(n,'float',16+4*i)for i,n in enumerate(('x','y','z','w'))])}
    for name,(boxed,managed,plan)in plans.items():
        td=ctx.index.types[name];fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
        need('nominal-value-record:'+name,(True,False,'System.ValueType',-1),
            (ctx.is_value_type(name),ctx.is_enum(name),ctx.parent(name),td.generic_container_index))
        need('nominal-complete-layout:'+name,plan,
            [(md.string(f.name_index),ctx.type_name(f.type_index),ctx.field(name+'::'+md.string(f.name_index))[2])for f in fields])
        need('size-table-index:'+name,True,0<=td.index<image.registration['typeDefinitionsSizesCount'])
        size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
        need('boxed-and-native-size:'+name,(boxed,managed),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
        for field in fields:
            typename=ctx.type_name(field.type_index);raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
            if typename=='float':scalar.ordinary(image,ctx.type_pointer(field.type_index),12,'storyBezierList.Single')
            else:need('owned-undecorated-value-field:'+typename,(ctx.index.types[typename].index,b'\x11\x80'),
                (int.from_bytes(raw[:8],'little'),raw[10:12]))
        layouts[name]=dict(boxedBytes=boxed,managedBytes=managed,fields=plan)
    rows=body['rows'];s={}
    for role,before,after in(('context','mov rcx, [rcx+0xc0]',None),('allocate','mov rcx, rax','mov rdi, rax'),
            ('arrayAllocate','mov rcx, rax','lea rcx, [rdi+0x10]'),('provider','mov rcx, [rcx+0x18]',None),
            ('prepare','mov rcx, [r14]',None),('barrier','mov [r13+0x0], rsi',None)):
        targets={control_transfer(r)['target']for i,r in enumerate(rows)if 0<i<len(rows)-1
            and bytes.fromhex(r['bytes'])[:1]==b'\xe8'and rows[i-1]['text']==before
            and(after is None or rows[i+1]['text']==after)}
        need('one-actual-helper:'+role,1,len(targets));s[role],=targets
    compared={int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)
        for r in rows if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8d\x3d'}
    need('one-exact-compared-callback',1,len(compared));s['callback'],=compared
    callback=owned(image,s['callback']);offsets=scalar.reader_offsets(image,'storyBezierList')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[list_program(body['regions'],body['pointer'],offsets,s,count=n,new=new)for new in(False,True)for n in range(4)]
    induction=prove_induction(programs,initial='33f6',increment='ffc6',comparison='413bf4',counter='esi',
        saved_count='R12 holds the unchanged signed Int32 count; ESI is zeroed once and incremented after each exact read/Add.',max_count=LIMIT)
    child=callback_program(callback['regions'],callback['pointer'],offsets)
    need('same-actual-replacement-cell',{child['replacementRootCell']},
        {p['replacementRootCell']for p in programs if p['countWitness']>0})
    # The provider/context path is independently proved. No runtime choice or
    # missing closed UnmanagedFormatter registration is silently supplied.
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[pc],label='storyBezierList.provider');pcs={r['relativeSlot']:r for r in pc['entries']}
    need('provider-two-owned-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
    need('provider-static-noargs',(True,0),(bool(pm.flags&16),pm.parameter_count))
    need('provider-return-owned-formatter',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
    need('provider-formatter-definition','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
    for t in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
        need('same-owned-provider-MVAR',(pm.index,0),(t['parameterOwner']['methodIndex'],t['parameterOwner']['ordinal']))
    provider=owned(image,s['provider']);calls=[control_transfer(r)['target']for r in provider['rows']if control_transfer(r)['kind']=='call'][:4]
    need('provider-four-calls',4,len(calls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),calls,strict=True))
    pp=float_list_sources.provider_program(provider['regions'],provider['pointer'],ps)
    int_fact=_load('levelscript_int_list_native.json',pins);backend=owned(image,ps['backend'])
    backend_target=base+int_fact['bodies']['providerBackend']['entryRva']
    bp=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
    factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=s['context']),need)
    need('same-indexed-context',s['context'],ps['type'])
    need('actual-array-allocator',base+int_fact['calls']['arrayAllocate'],s['arrayAllocate'])
    usages=[]
    for source,cell,name in((body,programs[1]['providerOwnerUsage']['cell'],'MemoryPack.MemoryPackFormatterProvider'),
            (provider,pp['providerClassCell'],'System.Type'),(provider,pp['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
            (backend,bp['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        selected=[r for r in source['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
            and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        need('one-actual-class-cell:'+name,1,len(selected));usage=derive_typed_usage_context(image,int(selected[0]['va'],16)-base,label='storyBezierList.providerCell')
        need('actual-named-class-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
    need('same-provider-root-cell',factory['providerClassCell'],programs[1]['providerOwnerUsage']['cell'])
    need('same-backend-provider-root',factory['providerClassCell'],bp['providerOwnerCell'])
    barrier_windows,barrier,_=_fast_barrier(image,s['barrier'])
    cap=dict(typeName=LIST,elementType=TYPE,nullable=True,headerBytes=4,countLimit=LIMIT,
        allowedCounts=None,positiveCountsAdmitted=True,elementWireBytes=56,managedElementBytes=56,
        rawSingleOffsets=list(range(0,56,4)),recordHeaderBytes=0,inlineElementSource=True,
        actualCallbackEqualsProvedChildRequired=True,closedElementRegistrationEquivalenceProved=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=call_target-base)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.story-bezier-list-source.v1',status='validated-conditional-component',nativeInputs=pins,
        capability=cap,proof=dict(empty=empty,context=context,layouts=layouts,listPrograms=programs,countInduction=induction,
            comparedCallback=child,providerContext=pc,provider=pp,providerUsages=usages,actualBackendForward=bp,
            providerFactory=factory,barrierWindows=barrier_windows,barrierProgram=barrier,
            sourceWindows=dict(list=body['windows'],comparedCallback=callback['windows'],provider=provider['windows'],backend=backend['windows']),
            symbolRvas={k:v-base for k,v in s.items()}),evidenceBoundary=dict(
            exact='Fresh nominal BezierKnot/float3/quaternion/float4 layout, exact closed list caller/context, complete new/reused-empty count/read56/inlineAdd56/return paths and finite loop induction.',
            conditional=__doc__,unresolved=['actual enclosing field/store','live provider/callback selection','closed standalone element formatter equivalence','replacement/cold/refill/growth paths','whole owner/physical EOF']))))
