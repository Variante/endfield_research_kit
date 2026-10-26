"""Own ShaderPropertyEntry array loop with a separately proved value24 callback.

The actual 24-byte indexing, EBX induction, fresh null output and five count
paths are required. The source proof does not admit enclosing fields or wire.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import animation_state_array_sources as shared
from scripts.game_data.memorypack import shader_property_value_sources as shader

TYPE=shader.TYPE
SCHEMA='endfield.animation-shader-value-array-source.v1'


def need(check,condition):
    if not condition:raise ValueError('animationShaderArray.'+check)


def byref_program(regions,entry,*,count):
    need('literal-small-count',type(count)is int and -1<=count<=3)
    g=BytesPath(regions,entry);symbols={};calls=[];callbacks=[];backedge=None;provider_usage=None
    def call(role):
        at=g.at;t=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==t)
        symbols[role]=t;calls.append(dict(role=role,instructionVa=at,targetVa=t))
    g.take('48895c2410','56','57','4156','4883ec20','4983783800','498bf8','488bf2','4c8bf1');g.branch('0f84',False)
    g.take('33db','895c2450','488d542450','498bce');call('header');g.take('84c0');g.branch('0f84',count==-1)
    if count==-1:g.take('488bce','48891e');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('48896c2440','8b6c2450','85ed');g.branch('0f84',count==0)
        if count==0:
            g.take('488b4f38','488b4908');call('empty');g.take('488bce','488906');call('barrier');g.take('90');g.jump('e9')
        else:
            g.take('48391e');g.branch('0f85',False)
            g.take('488b4f38','ba02000000');call('context');g.take('488bd5','488bc8');call('allocate')
            g.take('488bce','488906');call('barrier')
            at=g.at;cell=g.relative('488b0d');provider_usage=dict(instructionVa=at,cellVa=cell)
            g.take('3999e0000000');g.branch('74',False,1)
            g.take('488b4f38','488b4918');call('provider');g.take('488bf8','85ed');g.branch('7e',False,1)
            loop=g.at
            for n in range(count):
                need('same-loop-start',g.at==loop);g.take('488b0e','4885c9');g.branch('74',False,1)
                g.take('4885ff');g.branch('74',False,1);g.take('4863d3');call('index')
                g.take('4c8bc8','4d8bc6','488bd7');callbacks.append(g.at);call('dispatch')
                g.take('ffc3','3bdd');backedge=g.at;g.branch('7c',n+1<count,1)
        g.take('488b6c2440')
    g.take('488b5c2448','4883c420','415e','5f','5e','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newArray=True,elementCallbackSites=callbacks,symbols=symbols,
        helperCalls=calls,actualBackedgeVa=backedge,headerBytes=4,elementManagedBytes=24,elementWireBytes=None,
        elementGrammarAdmitted=False,initiallyNullArrayRequired=True,normalReturn=True,entryRspRestored=True,
        allIntegerNonvolatilesRestored=True,providerClassUsage=provider_usage,savedCount='ebp',index='ebx',
        callbackAbi=dict(formatter='rdx',reader='r8 same Reader',output='r9 actual indexed Shader value24 output'))


def index_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
    g.take('488d4202','488d0442','488d04c1','4883c428','c3')
    return dict(selectedBytes=g.seen,elementManagedBytes=24,arrayDataOffset=32,
        addressExpression='array+32+24*nonnegativeIndex',boundedIndexRequired=True,normalReturn=True,entryRspRestored=True)


def empty_program(regions,entry,context):
    g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('75',True,1)
    g.take('488b4b38','33d2');g.call(context);g.take('83b8e000000000');g.branch('75',True,1)
    g.take('488b4b38','33d2');g.call(context);g.take('488b80b8000000','488b00','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,ownedEmptyArrayMethodInfoRequired=True,normalReturn=True,entryRspRestored=True)


def provider_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_cell=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');handle=g.relative('e8');provider_cell=g.relative('488b0d')
    g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');provider=g.relative('e8');g.take('488b4f38','ba01000000','488bd8');context=g.relative('e8')
    g.take('488bd0','488bcb');cast=g.relative('e8');g.take('4885c0');g.branch('0f84',False)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassCell=type_cell,providerClassCell=provider_cell,
        helpers=dict(typeHandle=handle,provider=provider,context=context,backend=cast),
        matchingNonnullBackendResultRequired=True,normalReturn=True,entryRspRestored=True,runtimeFormatterSelectionProved=False)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
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
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need('actual-nominal-ReadArray',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadArray',[],[TYPE])and type(count_limit)is int and 3<=count_limit<=10000)
    validate_typed_usage_context(image,typed_request,label='animationShaderArray')
    raw=bytes.fromhex(typed_request.get('instructionHex',''));need('literal-RDX-context-load',len(raw)==7 and raw[:3]==bytes.fromhex('488b15'))
    nominal=shader.layout(image,ctx);argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    carrier=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('exact-own-value24-carrier',carrier[10:12]==b'\x11\x80'and int.from_bytes(carrier[:8],'little')==nominal['typeDefinition'])
    front=owned(image,call_target);front_program=shared.return_program(front['regions'],call_target)
    byref=owned(image,front_program['byrefTargetVa']);programs=[byref_program(byref['regions'],byref['pointer'],count=n)for n in(-1,0,1,2,3)]
    symbols={}
    for p in programs:
        for k,v in p['symbols'].items():need('same-actual-helper:'+k,k not in symbols or symbols[k]==v);symbols[k]=v
    helpers={k:owned(image,symbols[k])for k in('header','empty','provider','index','dispatch')}
    offsets=scalar.reader_offsets(image,'animationShaderArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    helper_programs=dict(header=shared.header_program(helpers['header']['regions'],symbols['header'],offsets),
        empty=empty_program(helpers['empty']['regions'],symbols['empty'],symbols['context']),
        provider=provider_program(helpers['provider']['regions'],symbols['provider']),index=index_program(helpers['index']['regions'],symbols['index']))
    callback=shader.derive(image,pins,dispatch_target=symbols['dispatch'])
    helper_programs['dispatch']=callback['proof']['paths']['actualDispatch']
    sy=ContextSymbols(image);first=sy.context(typed_request['methodSpec'][0],is_method=True);second=sy.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='animationShaderArray')
    fm=image.metadata.methods[second['entries'][5]['methodSpec'][0]]
    declaration=shared.formatter_declaration(image,ctx,fm,image.metadata.methods[first['definition']].declaring_type)
    context=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),argument.type_pointer_va,fm.index,
        fail=lambda k,e,a:need(k+':expected='+str(e)[:200]+':actual='+str(a)[:200],e==a))
    induction=prove_induction(programs[1:],initial='33db',increment='ffc3',comparison='3bdd',counter='ebx',saved_count='ebp',max_count=count_limit,
        mode_key='newArray',backedge_sites=[programs[-1]['actualBackedgeVa']])
    request=derive_typed_usage_context(image,programs[-1]['providerClassUsage']['instructionVa']-base,label='animationShaderArray.provider')
    need('own-formatter-provider-class',request.get('tag')==1 and request.get('typeName')=='MemoryPack.MemoryPackFormatterProvider')
    sources=dict(front=front,byref=byref,**helpers);barrier=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-shader-value-array',nativeInputs=pins,
        elementType=TYPE,elementValueType=True,closedArrayType=TYPE+'[]',typedRequest=typed_request,
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
        countRange=[-1,count_limit],countLimit=count_limit,nullable=True,positiveCountsAdmitted=True,
        elementManagedBytes=24,elementWireBytes=None,initiallyNullArrayRequired=True,actualSourceProved=True,
        elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,returnProgram=front_program,programs=programs,induction=induction,helperPrograms=helper_programs,
            callbackSource=callback,barrier=barrier,ownedContexts=[first,second],arrayContext=context,formatterDeclaration=declaration,
            providerClasses=[request],readerOffsets=offsets,symbolRvas={k:v-base for k,v in symbols.items()},
            sourceWindows={k:v['windows']for k,v in sources.items()},actualSourceRegions={k:[[a,r.hex()]for a,r in v['regions']]for k,v in sources.items()}))))


def bind_call(context,source_target,component,pins,*,base):
    usage=component.get('typedRequest',{});nominal=component.get('proof',{}).get('layout',{});raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('own-shader24-array-source',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-shader-value-array'and component.get('elementType')==TYPE
        and component.get('elementValueType')is True and component.get('closedArrayType')==TYPE+'[]'
        and component.get('elementManagedBytes')==24 and component.get('elementWireBytes')is None
        and component.get('countRange')==[-1,4096]and component.get('countLimit')==4096
        and component.get('initiallyNullArrayRequired')is True and component.get('actualSourceProved')is True
        and all(component.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    need('exact-current-typed-call',tuple(context.get(k)for k in('methodOwner','methodName','fullTypeName','register','typeKind'))
        ==('MemoryPack.MemoryPackReader','ReadArray',TYPE,'rdx',17)and len(raw)==16 and raw[10:12]==b'\x11\x80'
        and int.from_bytes(raw[:8],'little')==nominal.get('typeDefinition')==context.get('typeDefinition')
        and tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec'))
        and component.get('arrayReaderMethodDefinition')==usage.get('methodSpec',[None])[0]
        and component.get('arrayReaderTargetRva')==source_target-base)
    return dict(typeName=TYPE+'[]',elementType=TYPE,sourceTargetRva=source_target-base,
        readerMethodDefinition=usage['methodSpec'][0],mode='typed-value-array',parentLocalStoreFrameRequired=True,elementGrammarAdmitted=False)
