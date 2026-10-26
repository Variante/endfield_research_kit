"""Two finite Extra value-array ABIs, independent from their element grammar.

Renderer entries occupy eight managed bytes even though their native-size row
is unavailable. PlayEffect entries occupy32 managed bytes, with native marshal
size40. Actual indexed addresses, boxed layouts and complete selected loops
prove these two sizes separately. No reference8 element or raw wire width is
inferred. Ready coherent contexts, compatible callbacks, normal typed helpers,
disabled collector and disjoint stable buffered storage remain conditions.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import animation_state_array_sources as shared

PREFIX='Beyond.Gameplay.View.Animation.AnimationConfigExtraData+'
RENDERER=PREFIX+'AnimationEventRendererVisibilityEntry'
PLAY=PREFIX+'AnimationEventPlayEffectEntry'
SCHEMA='endfield.animation-extra-value-array-source.v1'
FIELDS={RENDERER:[['rendererNamePrefixes','string[]',16]],PLAY:[
    ['eventName','string',16],['effectName','string',24],['targetBonePath','string',32],
    ['followPosition','bool',40],['followRotation','bool',41],['stopWithState','bool',42]]}


def need(check,condition):
    if not condition:raise ValueError('animationExtraValueArray.'+check)


def layout(image,ctx,element_type):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('finite-element',element_type in FIELDS);td=ctx.index.types[element_type];md=image.metadata
    need('own-plain-value',ctx.is_value_type(element_type)and not ctx.is_enum(element_type)
        and ctx.parent(element_type)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(element_type+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('exact-own-field-map',actual==FIELDS[element_type])
    for f,(_,name,_)in zip(fields,actual,strict=True):
        scalar.ordinary(image,ctx.type_pointer(f.type_index),{'string[]':29,'string':14,'bool':2}[name],
            'animationExtraValueArray.field',reference=name!='bool')
    need('bounded-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    boxed,native=image.pe.u32_at_va(at),image.pe.u32_at_va(at+4)
    managed=8 if element_type==RENDERER else 32
    need('separate-boxed-managed-and-marshaled-sizes',(boxed,native)==((24,0xffffffff)if element_type==RENDERER else(48,40)))
    return dict(typeName=element_type,typeDefinition=td.index,boxedBytes=boxed,managedBytes=managed,
        marshaledNativeBytes=native,marshaledSizeUsedForManagedWidth=False,fields=actual,
        referenceLaneOffsets=[0]if element_type==RENDERER else[0,8,16],
        paddingByteRanges=[]if element_type==RENDERER else[[27,32]],wireGrammarAdmitted=False)


def return_program(regions,entry,*,play=False):
    if not play:return shared.return_program(regions,entry)
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('75',True,1)
    g.take('4c8b4338','488d542438','48c744243800000000','488bcf','4d8b00')
    at=g.at;target=g.relative('e8');g.take('488b442438','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,byrefCallInstructionVa=at,byrefTargetVa=target,initiallyNullOutputProved=True,
        arrayLocalEntryRspOffset=16,entryRspRestored=True,sameReader=True,unchangedArrayReferenceReturnedInRax=True,normalReturn=True)


def byref_program(regions,entry,*,count,play=False):
    need('literal-small-count',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);symbols={};calls=[];callbacks=[];backedge=None;provider_class=None;provider_cell=None
    def call(role):
        at=g.at;t=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==t)
        symbols[role]=t;calls.append(dict(role=role,instructionVa=at,targetVa=t))
    if play:
        g.take('48895c2408','48896c2410','56','57','4156','4883ec20','4983783800','498bf8','488bda','4c8bf1');g.branch('75',True,1)
        g.take('c744245000000000','488d542450','498bce');call('header');g.take('84c0');g.branch('0f84',count==-1)
        if count==-1:g.take('48c70300000000')
        else:
            g.take('8b742450','85f6');g.branch('0f84',count==0)
            if count==0:
                g.take('488b4f38','488b4908');call('empty');g.take('488903');g.jump('eb',1)
            else:
                g.take('48833b00');g.branch('74',True,1)
                g.take('488b4f38','488b4910');call('context');g.take('488bd6','488bc8');call('allocate')
                g.take('488bcb','488903');call('barrier')
                provider_class=g.at;provider_cell=g.relative('488b0d');call('classReady')
                g.take('488b4f38','488b4918');call('provider');g.take('33ff','488be8','85f6');g.branch('7e',False,1)
                loop=g.at
                for n in range(count):
                    need('same-loop-entry',g.at==loop)
                    g.take('488b0b','4885c9');g.branch('74',False,1)
                    g.take('4885ed');g.branch('74',False,1)
                    g.take('4863d7');call('index');g.take('4c8bc8','4d8bc6','488bd5');callbacks.append(g.at);call('dispatch')
                    g.take('ffc7','3bfe');backedge=g.at;g.branch('7c',n+1<count,1)
                g.jump('eb',1)
        if count<=0:g.take('488bcb');call('barrier')
        g.take('488b5c2440','488b6c2448','4883c420','415e','5f','5e','c3')
    else:
        g.take('48895c2410','55','57','4156','4883ec20','4983783800','498bd8','488bfa','488be9');g.branch('74',False,1)
        g.take('4533f6','4489742450','488d542450','488bcd');call('header');g.take('84c0');g.branch('0f84',count==-1)
        if count==-1:
            g.take('488bcf','4c8937');call('barrier');g.take('90');g.jump('e9')
        else:
            g.take('4889742440','8b742450','85f6');g.branch('0f85',count>0)
            if count==0:
                g.take('488b4b38','488b4908');call('empty');g.take('488bcf','488907');call('barrier')
            else:
                g.take('4c3937');g.branch('74',True,1)
                g.take('488b4b38','ba02000000');call('context');g.take('488bd6','488bc8');call('allocate')
                g.take('488bcf','488907');call('barrier')
                provider_class=g.at;provider_cell=g.relative('488b0d');g.take('4439b1e0000000');g.branch('75',True,1)
                g.take('488b4b38','488b4918');call('provider');g.take('488bd8','85f6');g.branch('0f8e',False)
                loop=g.at
                for n in range(count):
                    need('same-loop-entry',g.at==loop)
                    g.take('488b0f','4885c9');g.branch('74',False,1)
                    g.take('4885db');g.branch('74',False,1)
                    g.take('443b7118');g.branch('73',False,1)
                    g.take('4963c6','4883c120','4c8bc5','488bd3','4c8d0cc1');callbacks.append(g.at);call('dispatch')
                    g.take('41ffc6','443bf6');backedge=g.at;g.branch('7c',n+1<count,1)
                g.jump('e9')
            g.take('488b742440')
        g.take('488b5c2448','4883c420','415e','5f','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newArray=True,elementCallbackSites=callbacks,
        symbols=symbols,helperCalls=calls,actualBackedgeVa=backedge,headerBytes=4,
        elementManagedBytes=32 if play else 8,elementWireBytes=None,elementGrammarAdmitted=False,
        initiallyNullArrayRequired=True,normalReturn=True,entryRspRestored=True,
        providerClassUsage=None if count<=0 else dict(instructionVa=provider_class,cellVa=provider_cell),
        callbackAbi=dict(formatter='rdx',reader='r8 same Reader',output='r9 actual indexed value output'),
        savedCount='esi',index='edi'if play else'r14d',allIntegerNonvolatilesRestored=True)


def provider_program(regions,entry,*,play=False):
    if not play:return shared.provider_program(regions,entry)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
    g.take('488b5f38');type_cell=g.relative('488b0d');g.take('488b1b');ready=g.relative('e8')
    g.take('33d2','488bcb');handle=g.relative('e8');provider_cell=g.relative('488b0d')
    g.take('488bd8');need('same-ready-class-helper',g.relative('e8')==ready)
    g.take('488bcb');backend=g.relative('e8');g.take('488b4f38','488bd8','488b4908');context=g.relative('e8')
    g.take('488bd0','488bcb');cast=g.relative('e8');g.take('4885c0');g.branch('0f85',True)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider_cell,
        helpers=dict(typeReady=ready,typeHandle=handle,classReady=ready,provider=backend,context=context,backend=cast),
        matchingNonnullBackendResultRequired=True,normalReturn=True,entryRspRestored=True,runtimeFormatterSelectionProved=False)


def empty_program(regions,entry,context,*,play=False):
    if not play:return shared.empty_program(regions,entry,context)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('75',True,1)
    g.take('488b4b38','488b09');g.call(context);g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b4b38','488b09');g.call(context);g.take('488b80b8000000','488b00','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,ownedEmptyArrayMethodInfoRequired=True,normalReturn=True,entryRspRestored=True)


def dispatch_program(regions,entry):
    result=shared.dispatch_program(regions,entry)
    result['callbackArguments']['r8']='actual indexed nominal value output'
    return result


def derive(image,pins,*,typed_request,call_target,element_type,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;play=element_type==PLAY
    need('finite-nominal-array',element_type in FIELDS and type(call_target)is int and call_target>base
        and type(count_limit)is int and 3<=count_limit<=10000)
    validate_typed_usage_context(image,typed_request,label='animationExtraValueArray')
    need('actual-nominal-ReadArray',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[element_type]))
    usage=bytes.fromhex(typed_request.get('instructionHex',''))
    need('actual-RDX-context-load',len(usage)==7 and usage[:3]==bytes.fromhex('488b15'))
    nominal=layout(image,ctx,element_type);argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-value-carrier',raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    front=owned(image,call_target);front_program=return_program(front['regions'],call_target,play=play)
    byref=owned(image,front_program['byrefTargetVa']);programs=[byref_program(byref['regions'],byref['pointer'],count=n,play=play)for n in(-1,0,1,2,3)]
    symbols={}
    for path in programs:
        for role,target in path['symbols'].items():need('same-actual-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    helpers={role:owned(image,symbols[role])for role in('header','empty','provider','dispatch')}
    if play:helpers['index']=owned(image,symbols['index'])
    offsets=scalar.reader_offsets(image,'animationExtraValueArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    helper_programs=dict(header=shared.header_program(helpers['header']['regions'],symbols['header'],offsets),
        empty=empty_program(helpers['empty']['regions'],symbols['empty'],symbols['context'],play=play),
        provider=provider_program(helpers['provider']['regions'],symbols['provider'],play=play),
        dispatch=dispatch_program(helpers['dispatch']['regions'],symbols['dispatch']))
    if play:helper_programs['index']=shared.index_program(helpers['index']['regions'],symbols['index'])
    barrier=_fast_barrier(image,symbols['barrier'])
    sy=ContextSymbols(image);first=sy.context(typed_request['methodSpec'][0],is_method=True);second=sy.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='animationExtraValueArray')
    fm=md.methods[second['entries'][5]['methodSpec'][0]]
    declaration=shared.formatter_declaration(image,ctx,fm,md.methods[first['definition']].declaring_type)
    context=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),argument.type_pointer_va,fm.index,
        fail=lambda k,e,a:need(k+':expected='+str(e)[:250]+':actual='+str(a)[:250],e==a))
    classes=[]
    for at in(programs[-1]['providerClassUsage']['instructionVa'],):
        request=derive_typed_usage_context(image,at-base,label='animationExtraValueArray.provider')
        need('actual-provider-class',request.get('tag')==1 and request.get('typeName')=='MemoryPack.MemoryPackFormatterProvider');classes.append(request)
    initial,increment,comparison,counter=('33ff','ffc7','3bfe','edi')if play else('4533f6','41ffc6','443bf6','r14d')
    induction=prove_induction([p for p in programs if p['countWitness']>=0],initial=initial,increment=increment,
        comparison=comparison,counter=counter,saved_count='esi',max_count=count_limit,mode_key='newArray',
        backedge_sites=[programs[-1]['actualBackedgeVa']])
    _publication_gate(image,pins);sources=dict(front=front,byref=byref,**helpers)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-extra-value-array',nativeInputs=pins,
        elementType=element_type,elementValueType=True,closedArrayType=element_type+'[]',typedRequest=typed_request,
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
        countRange=[-1,count_limit],countLimit=count_limit,nullable=True,positiveCountsAdmitted=True,
        elementManagedBytes=nominal['managedBytes'],elementWireBytes=None,initiallyNullArrayRequired=True,
        actualSourceProved=True,elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,returnProgram=front_program,programs=programs,induction=induction,
            helperPrograms=helper_programs,barrier=barrier,ownedContexts=[first,second],arrayContext=context,
            formatterDeclaration=declaration,providerClasses=classes,readerOffsets=offsets,
            sourceWindows={k:v['windows']for k,v in sources.items()},
            actualSourceRegions={k:[[a,r.hex()]for a,r in v['regions']]for k,v in sources.items()},
            symbolRvas={k:v-base for k,v in symbols.items()}),evidenceBoundary=__doc__)))


def bind_call(context,source_target,component,pins,*,base):
    typ=component.get('elementType');usage=component.get('typedRequest',{});nominal=component.get('proof',{}).get('layout',{})
    need('own-value-array-source',typ in FIELDS and component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-extra-value-array'and component.get('nativeInputs')==pins
        and component.get('elementValueType')is True and component.get('closedArrayType')==typ+'[]'
        and component.get('elementManagedBytes')==nominal.get('managedBytes')==(8 if typ==RENDERER else 32)
        and component.get('elementWireBytes')is None and component.get('initiallyNullArrayRequired')is True
        and component.get('actualSourceProved')is True and component.get('countRange')==[-1,4096]and component.get('countLimit')==4096
        and all(component.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('exact-own-typed-caller',tuple(context.get(k)for k in('methodOwner','methodName','fullTypeName','register','typeKind'))
        ==('MemoryPack.MemoryPackReader','ReadArray',typ,'rdx',17)
        and len(raw)==16 and raw[10:12]==b'\x11\x80'and int.from_bytes(raw[:8],'little')==nominal.get('typeDefinition')==context.get('typeDefinition')
        and tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))
        and component.get('arrayReaderMethodDefinition')==usage.get('methodSpec',[None])[0]
        and type(base)is int and type(source_target)is int and source_target>base and component.get('arrayReaderTargetRva')==source_target-base)
    return dict(typeName=typ+'[]',elementType=typ,sourceTargetRva=source_target-base,
        readerMethodDefinition=usage['methodSpec'][0],mode='typed-value-array',parentLocalStoreFrameRequired=True,elementGrammarAdmitted=False)
