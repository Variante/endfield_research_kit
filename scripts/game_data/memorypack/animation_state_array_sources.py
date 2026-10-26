"""Actual StatePerformConfig value-array source, separate from element wire.

The return overload creates a fresh null array local and calls its own byref
overload. Buffered null/empty/positive count paths, typed array allocation,
value32 indexed addresses and repeated slot-five output calls are exact. The
element's MC3 wrapper/adapter and enclosing field/frame require separate joins.
Ready coherent nominal contexts, normal typed helpers, matching compatible
formatter callbacks, disabled collector and disjoint buffered storage remain
conditions. No reference8 array, raw bulk value array or wire32 is inferred.
"""
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.View.Animation.StatePerformConfig'
SCHEMA='endfield.animation-state-perform-array-source.v1'
FIELDS=(('stateName','string',16),('stateHash','int',24),('performId','string',32),
    ('interruptType','Beyond.Gameplay.View.Animation.StatePerformInterruptConditionType',40))


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationStateArray.'+check+':'+str(detail)[:600])


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td=ctx.index.types[TYPE];md=image.metadata
    need('own-plain-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fs=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fs]
    need('exact-own-fields',actual==list(FIELDS))
    for f,(_,name,_)in zip(fs,FIELDS,strict=True):
        scalar.ordinary(image,ctx.type_pointer(f.type_index),14 if name=='string'else 8 if name=='int'else 17,'animationStateArray.layout')
    enum=ctx.index.types[FIELDS[-1][1]]
    ef=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('own-enum-Int32',ctx.is_enum(FIELDS[-1][1])and len(ef)==1
        and ctx.field(FIELDS[-1][1]+'::'+md.string(ef[0].name_index))[1:]==('int',16))
    need('size-row-bounded',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-boxed48-managed32',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(48,32))
    return dict(typeName=TYPE,typeDefinition=td.index,managedBytes=32,boxedBytes=48,fields=actual,
        referenceLaneOffsets=[0,16],paddingByteRanges=[[12,16],[28,32]],wireGrammarAdmitted=False)


def return_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9');g.branch('74',False,1)
    g.take('4c8b4338','488d542438','48c744243800000000','488bcf','4d8b00')
    call=g.at;target=g.relative('e8')
    g.take('488b442438','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,byrefCallInstructionVa=call,byrefTargetVa=target,
        initiallyNullOutputProved=True,arrayLocalEntryRspOffset=16,entryRspRestored=True,
        sameReader=True,unchangedArrayReferenceReturnedInRax=True,normalReturn=True)


def byref_program(regions,entry,*,count):
    need('literal-count-witness',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);symbols={};calls=[]
    def call(role):
        at=g.at;target=g.relative('e8');need('coherent-helper:'+role,role not in symbols or symbols[role]==target)
        symbols[role]=target;calls.append(dict(role=role,instructionVa=at,targetVa=target))
    g.take('48895c2410','55','57','4156','4883ec20','4983783800','498bd8','488bfa','488be9');g.branch('74',False,1)
    g.take('4533f6','4489742450','488d542450','488bcd');call('header')
    g.take('84c0');g.branch('0f84',count==-1)
    callbacks=[];backedge=None
    if count==-1:
        g.take('488bcf','4c8937');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742440','8b742450','85f6');g.branch('0f85',count>0)
        if count==0:
            g.take('488b4b38','488b4908');call('empty')
            g.take('488bcf','488907');call('barrier')
        else:
            g.take('4c3937');g.branch('74',True,1)
            g.take('488b4b38','ba02000000');call('context')
            g.take('488bd6','488bc8');call('allocate')
            g.take('488bcf','488907');call('barrier')
            provider_class=g.at;provider_cell=g.relative('488b0d')
            g.take('4439b1e0000000');g.branch('75',True,1)
            g.take('488b4b38','488b4918');call('provider')
            g.take('488bd8','85f6');g.branch('0f8e',False)
            loop=g.at
            for n in range(count):
                need('actual-identical-loop-entry',g.at==loop)
                g.take('488b0f','4885c9');g.branch('74',False,1)
                g.take('4885db');g.branch('74',False,1)
                g.take('4963d6');call('index')
                g.take('4c8bc8','4c8bc5','488bd3');callbacks.append(g.at);call('dispatch')
                g.take('41ffc6','443bf6');backedge=g.at;g.branch('7c',n+1<count,1)
            g.jump('e9')
        g.take('488b742440')
    g.take('488b5c2448','4883c420','415e','5f','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=True,elementCallbackSites=callbacks,
        symbols=symbols,helperCalls=calls,actualBackedgeVa=backedge,
        headerBytes=4,elementManagedBytes=32,elementWireBytes=None,elementGrammarAdmitted=False,
        initiallyNullArrayRequired=True,normalReturn=True,entryRspRestored=True,
        providerClassUsage=None if count<=0 else dict(instructionVa=provider_class,cellVa=provider_cell),
        callbackAbi=dict(formatter='rdx',reader='r8 same incoming RCX savedRBP',output='r9 actual indexed element address'),
        savedCount='esi',index='r14d',allIntegerNonvolatilesRestored=True)


def header_program(regions,entry,offsets):
    g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'04','488bfa','488bd9');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b08','890f','8b73'+rem,'83c6fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,
        '486343'+used,'488b4b'+total,'448b07','482bc8','4963c0','483bc8');g.branch('0f8c',False)
    g.take('488b5c2430','4183f8ff','488b742438','0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,signedCountBytes=4,headerBytes=4,onlyMinusOneIsNull=True,
        countStoredUnchanged=True,readerUpdates=[dict(field=k,delta=-4 if k=='bufferLength'else 4)for k in('currentPtr','bufferLength','advancedCount','consumed')],
        normalReturn=True,entryRspRestored=True)


def index_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('72',True,1)
    g.take('488d4201','48c1e005','4803c1','4883c428','c3')
    return dict(selectedBytes=g.seen,arrayDataOffset=32,elementManagedBytes=32,normalReturn=True,
        address='same incoming array RCX +32+32*zero-extended nonnegative EDX index',entryRspRestored=True)


def empty_program(regions,entry,context):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('74',False,1)
    g.take('488b4b38','33d2');g.call(context);g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4b38','33d2');g.call(context);g.take('488b80b8000000','488b00','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,ownedEmptyArrayMethodInfoRequired=True,normalReturn=True,entryRspRestored=True)


def provider_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9');g.branch('75',True,1)
    g.take('488b5f38');cell=g.relative('488b0d');g.take('488b1b');type_ready=g.relative('e8')
    g.take('33d2','488bcb');type_handle=g.relative('e8');provider_cell=g.relative('488b0d')
    g.take('488bd8');class_ready=g.relative('e8');g.take('488bcb');provider=g.relative('e8')
    g.take('488b4f38','ba01000000','488bd8');context=g.relative('e8')
    g.take('488bd0','488bcb');backend=g.relative('e8');g.take('4885c0');g.branch('0f85',True)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=cell,providerClassCell=provider_cell,
        helpers=dict(typeReady=type_ready,typeHandle=type_handle,classReady=class_ready,provider=provider,context=context,backend=backend),
        matchingNonnullBackendResultRequired=True,normalReturn=True,entryRspRestored=True,
        runtimeFormatterSelectionProved=False)


def dispatch_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bd9','498bf8','488bf2')
    prepare=g.relative('e8')
    g.take('4c8b0e','4c8bc3','488bd7','488bce','498b8190010000','4d8b8998010000',
        '488b5c2430','488b742438','4883c420','5f','48ffe0')
    return dict(selectedBytes=g.seen,prepareTargetVa=prepare,formatterSlot=5,
        callbackArguments=dict(rcx='same formatter',rdx='same Reader',r8='actual indexed State value32 output',r9='same selected slot MethodInfo'),
        normalTailCallback=True,entryRspRestored=True,canonicalCallbackEqualityRequiredForElementGrammar=True)


def formatter_declaration(image,ctx,method,reader_definition):
    """Authenticate an abstract slot declaration, without claiming a body."""
    from scripts.game_data.il2cpp.context import type_parameter_owner
    md=image.metadata;td=md.types[method.declaring_type];ps=md.parameters_for(method)
    need('abstract-slot-five-ABI',image.type_name(td.index)=='MemoryPack.MemoryPackFormatter`1'
        and md.string(method.name_index)=='Deserialize'and method.slot==5 and method.flags&0x440==0x440
        and not method.flags&16 and ctx.type_name(method.return_type)=='void'and len(ps)==2 and td.generic_container_index>=0)
    section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
    need('formatter-container-range',section.offset<=at<=section.offset+section.size-16)
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    identity=type_parameter_owner(md.buf,start,[t.generic_container_index for t in md.types],source='animationStateArray')
    need('formatter-reciprocal-class-VAR',(owner,count,is_method)==(td.index,1,0)
        and identity['typeIndex']==td.index and identity['ordinal']==0)
    reader=image.pe.bytes_at_va(ctx.type_pointer(ps[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(ps[1].type_index),16)
    need('same-Reader-and-owned-output-byrefs',reader[10:12]==bytes.fromhex('1120')
        and int.from_bytes(reader[:8],'little')==reader_definition
        and output[10:12]==bytes.fromhex('1320')and int.from_bytes(output[:8],'little')==start)
    return dict(methodDefinition=method.index,formatterSlot=5,abstractDeclaration=True,
        sameReaderByref=True,ownClassVAROutputByref=True,concreteCallbackBodyProved=False)


def bind_call(context,source_target,component,pins,*,base):
    """Exact finite outer call identity; element grammar remains separate."""
    usage=component.get('typedRequest',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
    nominal=component.get('proof',{}).get('layout',{})
    need('own-State32-array-source',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-state-perform-value-array'
        and component.get('nativeInputs')==pins and component.get('actualSourceProved')is True
        and component.get('elementType')==TYPE and component.get('closedArrayType')==TYPE+'[]'
        and component.get('elementValueType')is True and component.get('elementManagedBytes')==32
        and component.get('elementWireBytes')is None and component.get('initiallyNullArrayRequired')is True
        and all(component.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
        and component.get('countRange')==[-1,4096]and component.get('countLimit')==4096)
    need('same-complete-value-array-caller',(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),
        context.get('register'),context.get('typeKind'))==('MemoryPack.MemoryPackReader','ReadArray',TYPE,'rdx',17)
        and len(raw)==16 and raw[10:12]==bytes.fromhex('1180')
        and int.from_bytes(raw[:8],'little')==nominal.get('typeDefinition')==context.get('typeDefinition')
        and(usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))==
            (context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))
        and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadArray',[],[TYPE])
        and component.get('arrayReaderMethodDefinition')==usage['methodSpec'][0]
        and type(base)is int and type(source_target)is int and source_target>base
        and component.get('arrayReaderTargetRva')==source_target-base)
    return dict(typeName=TYPE+'[]',elementType=TYPE,sourceTargetRva=source_target-base,
        readerMethodDefinition=usage['methodSpec'][0],mode='typed-value-array',parentLocalStoreFrameRequired=True,
        elementGrammarAdmitted=False)


def derive(image,pins,*,typed_request,call_target,element_type=TYPE,count_limit=4096):
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
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need('finite-StatePerformConfig-selection',element_type==TYPE and type(call_target)is int and call_target>base
        and type(count_limit)is int and 3<=count_limit<=10000)
    validate_typed_usage_context(image,typed_request,label='animationStateArray')
    need('actual-nominal-ReadArray',(typed_request.get('tag'),typed_request.get('typeName'),typed_request.get('methodName'),
        typed_request.get('classArguments'),typed_request.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[TYPE]))
    need('literal-RDX-context',len(bytes.fromhex(typed_request['instructionHex']))==7
        and bytes.fromhex(typed_request['instructionHex'])[:3]==bytes.fromhex('488b15'))
    nominal=layout(image,ctx);argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-complete-value-carrier',raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    front=owned(image,call_target);front_program=return_program(front['regions'],call_target)
    byref=owned(image,front_program['byrefTargetVa']);programs=[byref_program(byref['regions'],byref['pointer'],count=n)for n in(-1,0,1,2,3)]
    symbols={}
    for p in programs:
        for k,v in p['symbols'].items():need('coherent-actual-helper:'+k,k not in symbols or symbols[k]==v);symbols[k]=v
    helpers={k:owned(image,symbols[k])for k in('header','empty','provider','index','dispatch')}
    offsets=scalar.reader_offsets(image,'animationStateArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    helper_programs=dict(header=header_program(helpers['header']['regions'],symbols['header'],offsets),
        index=index_program(helpers['index']['regions'],symbols['index']),
        empty=empty_program(helpers['empty']['regions'],symbols['empty'],symbols['context']),
        provider=provider_program(helpers['provider']['regions'],symbols['provider']))
    helper_programs['dispatch']=dispatch_program(helpers['dispatch']['regions'],symbols['dispatch'])
    barrier=_fast_barrier(image,symbols['barrier'])
    sy=ContextSymbols(image);first=sy.context(typed_request['methodSpec'][0],is_method=True);second=sy.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='animationStateArray')
    fm=md.methods[second['entries'][5]['methodSpec'][0]]
    declaration=formatter_declaration(image,ctx,fm,md.methods[first['definition']].declaring_type)
    context=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),argument.type_pointer_va,fm.index,fail=lambda k,e,a:need(k,e==a,dict(expected=e,actual=a)))
    classes=[]
    for at in (programs[-1]['providerClassUsage']['instructionVa'],):
        u=derive_typed_usage_context(image,at-base,label='animationStateArray.provider')
        need('actual-provider-class',u['tag']==1 and u['typeName']=='MemoryPack.MemoryPackFormatterProvider');classes.append(u)
    induction=prove_induction([p for p in programs if p['countWitness']>=0],initial='4533f6',increment='41ffc6',
        comparison='443bf6',counter='r14d',saved_count='esi',max_count=count_limit,
        backedge_sites=[programs[-1]['actualBackedgeVa']])
    _publication_gate(image,pins)
    sources=dict(front=front,byref=byref,**helpers)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-state-perform-value-array',nativeInputs=pins,
        elementType=TYPE,elementValueType=True,closedArrayType=TYPE+'[]',typedRequest=typed_request,
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
        countRange=[-1,count_limit],countLimit=count_limit,nullable=True,positiveCountsAdmitted=True,
        elementManagedBytes=32,elementWireBytes=None,initiallyNullArrayRequired=True,
        actualSourceProved=True,elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,returnProgram=front_program,programs=programs,induction=induction,
            helperPrograms=helper_programs,barrier=barrier,ownedContexts=[first,second],arrayContext=context,
            formatterDeclaration=declaration,providerClasses=classes,readerOffsets=offsets,
            sourceWindows={k:v['windows']for k,v in sources.items()},
            actualSourceRegions={k:[[a,r.hex()]for a,r in v['regions']]for k,v in sources.items()},
            symbolRvas={k:v-base for k,v in symbols.items()}),evidenceBoundary=__doc__)))
