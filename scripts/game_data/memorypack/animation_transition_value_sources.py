"""Own FMorphEmotionTransitionInfo MC2 wrapper and managed8 storage source.

Float duration and the independently typed Int32 enum form the MC2 wire order.
The complete QWORD getter, zero8 constructor and FF wrapper-null branch supply
managed ABI facts, not raw8 wire or an Original default. Canonical transfer,
the actual enclosing SkMorph field and runtime animation remain separate.
"""
import json
import hashlib
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.FMorphEmotionTransitionInfo'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_FMorphEmotionTransitionInfoForMemoryPack'
ENUM='Beyond.Gameplay.Core.EMorphEmotionTransitionType'
SCHEMA='endfield.animation-transition-value-source.v1'
CAPABILITY='animation-morph-transition-info'
RAW_SCHEMA='endfield.animation-transition-raw8-source.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('animationTransitionValue.'+check+':'+str(detail)[:600])


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('own-ordinary-value8',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fs=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fs]
    need('exact-owned-fields',actual==[('fixedTransitionDuration','float',16),('fixedTransitionType',ENUM,20)])
    for f,kind in zip(fs,(12,17),strict=True):scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,'animationTransitionValue.field')
    enum=ctx.index.types[ENUM];ef=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('owned-Int32-enum',ctx.is_enum(ENUM)and len(ef)==1 and ctx.field(ENUM+'::'+md.string(ef[0].name_index))[1:]==('int',16))
    scalar.ordinary(image,ctx.type_pointer(ef[0].type_index),8,'animationTransitionValue.enum')
    need('bounded-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    sp=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
    need('own-boxed24-native8',(image.pe.u32_at_va(sp),image.pe.u32_at_va(sp+4))==(24,8))
    return dict(typeName=TYPE,typeDefinition=td.index,boxedBytes=24,managedBytes=8,fields=actual,
        referenceLaneOffsets=[],paddingByteRanges=[],wireGrammarAdmitted=False)


def wrapper_program(regions,entry,*,new=False,null=False):
    need('literal-path-booleans',type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);s={};calls=[]
    def call(role):
        at=g.at;t=g.relative('e8');need('same-helper:'+role,role not in s or s[role]==t);s[role]=t;calls.append(dict(role=role,instructionVa=at,targetVa=t))
    g.take('48895c2410','4889742418','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('75',True,1)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None;enum_usage=None
    if null:g.take('488bcb','48c70300000000');call('barrier')
    else:
        g.take('48833b00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate')
            g.take('4885c0');g.branch('74',False,1)
            g.take('33c9','48894810','488bcb','488903');call('barrier')
            allocation=dict(instructionVa=at,cellVa=cell,zeroedManagedBytes=8)
        g.take('807c243002');g.branch('75',False,1)
        g.take('488b33','488bcf');call('single');g.take('4885f6');g.branch('74',False,1)
        g.take('f30f114610','488bcf');enum_usage=g.at;enum_cell=g.relative('488b15')
        g.take('488b1b');call('enum');g.take('4885db');g.branch('74',False,1)
        g.take('894314');g.jump('eb',1)
    g.take('488b5c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=flag,newWrapper=new,wrapperNull=null,
        allocation=allocation,enumUsageInstructionVa=enum_usage,enumUsageCellVa=None if null else enum_cell,
        symbols=s,sourceCalls=calls,memberCount=None if null else 2,wireBytes=1 if null else 9,
        wireOrder=[]if null else['fixedTransitionDuration','fixedTransitionType'],managedBytes=8,
        normalReturn=True,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
        originalDefaultValueAdmitted=False)


def derive_wrapper(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('exact-own-wrapper-and-members',wrapper.wrapped_type==TYPE and
        [(m.name,m.declared_type)for m in wrapper.members]==[('fixedTransitionDuration','float'),('fixedTransitionType',ENUM)])
    nominal=layout(image,ctx);mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'animationTransitionValue.GetValue')
    factories=[]
    for name in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],'animationTransitionValue.'+name)
        factories.append(dict(method=[mm[name].index,WRAPPER,name,image.method_pointer_va(mm[name])-base],
            program=leaf(image,image.method_pointer_va(mm[name]),['33C0','48894110','C3'])))
    named=[]
    for name,typ,kind,expected in(('fixedTransitionDuration','float',12,['F30F114910','C3']),('fixedTransitionType',ENUM,17,['895114','C3'])):
        m=mm['set___'+name+'__'];scalar.owned_method_abi(image,ctx,m.index,wrapper.type_definition,('void',1,False),[(typ,kind,False)],'animationTransitionValue.setter')
        named.append(dict(method=[m.index,WRAPPER,'set___'+name+'__',image.method_pointer_va(m)-base],program=leaf(image,image.method_pointer_va(m),expected)))
    pair=derive_pair(image,TYPE,WRAPPER);forward=registered_pair(image,pair,wrapper,label='animationTransitionValue.registration')
    body=owned(image,image.method_pointer_va(mm['Deserialize']));programs=[wrapper_program(body['regions'],body['pointer'],**p)for p in({},{'new':True},{'null':True})]
    symbols={}
    for p in programs:
        for k,v in p['symbols'].items():need('same-owned-source-target:'+k,k not in symbols or symbols[k]==v);symbols[k]=v
    usage=derive_typed_usage_context(image,programs[1]['allocation']['instructionVa']-base,label='animationTransitionValue.allocate')
    need('own-typed-wrapper-allocation',usage.get('tag')==1 and usage.get('typeName')==WRAPPER
        and base+usage['usageCellRva']==programs[1]['allocation']['cellVa'])
    enum_usage=derive_typed_usage_context(image,programs[0]['enumUsageInstructionVa']-base,label='animationTransitionValue.enum')
    need('actual-owned-enum-request',(enum_usage.get('tag'),enum_usage.get('typeName'),enum_usage.get('methodName'),
        enum_usage.get('classArguments'),enum_usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[ENUM]))
    record=vector_recorder(image);offsets=scalar.reader_offsets(image,'animationTransitionValue')
    header=primitive_param.object_header_source(image,record(symbols['header']-base,fragments=True),offsets)
    single=primitive_param.single_source(image,record(symbols['single']-base,fragments=True),offsets)
    integer=scalar.integer_source(image,record(symbols['enum']-base,fragments=True),offsets,'fixedTransitionType',width=4)
    barrier=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-transition-wrapper-requires-canonical-value8-transfer',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,layout=nominal,managedBytes=8,
        programs=programs,sourceWindows=body['windows'],sourceRegions=[[a,r.hex()]for a,r in body['regions']],
        getter=getter,factories=factories,namedSetters=named,registeredPair=pair,forwarding=forward,
        sources=dict(header=header,single=single,enum=integer,barrier=barrier),enumUsage=enum_usage,
        allocationUsage=usage,symbolRvas={k:v-base for k,v in symbols.items()},
        originalDefaultValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=__doc__)))


def raw_program(regions,entry,offsets):
    g=BytesPath(regions,entry)
    rem,cur=(bytes((offsets[k],)).hex()for k in('bufferLength','currentPtr'))
    g.take('48895c2408','57','4883ec20','8379'+rem+'08','488bf9');g.branch('0f8c',False)
    g.take('488b5f'+cur,'ba08000000','488bcf','488b1b');call=g.at;target=g.relative('e8')
    g.take('488bc3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,managedOutputBytes=8,resultRegister='rax',readerRegister='rcx',
        capturedSourceSlices=[[0,8]],sameFullQwordReturnedInRax=True,entryRspRestored=True,
        allIntegerNonvolatilesRestored=True,normalReturn=True,advanceCallInstructionVa=call,advanceTargetVa=target,
        actualReaderArgument='rdi',actualSignedCountArgument=8,independentAdvanceSourceRequired=True,
        wrapperFramingUsed=False,firstFFIsRawData=True,readerOffsets=dict(offsets))


def derive_raw(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    validate_typed_usage_context(image,typed_request,label='animationTransitionRaw8')
    need('actual-own-RDX-ReadUnmanaged',typed_request.get('tag')==6 and tuple(typed_request.get(k)for k in
        ('typeName','methodName','classArguments','methodArguments'))==('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and len(bytes.fromhex(typed_request.get('instructionHex','')))==7
        and bytes.fromhex(typed_request['instructionHex'])[:3]==bytes.fromhex('488b15'))
    nominal=layout(image,ctx);argument,=image.instantiations.resolve(typed_request['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-ordinary-nominal-value-record',raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    method=md.methods[typed_request['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
    need('own-noarg-instance-Reader-ReadUnmanaged',image.type_name(method.declaring_type)=='MemoryPack.MemoryPackReader'
        and md.string(method.name_index)=='ReadUnmanaged'and not method.flags&16 and method.parameter_count==0
        and not list(md.parameters_for(method))and method.generic_container_index>=0
        and section.offset<=at<=section.offset+section.size-16)
    container=struct.unpack_from('<iiii',md.buf,at);parameter=method_parameter_owner(md.buf,container[3],
        [m.generic_container_index for m in md.methods],source='animationTransitionRaw8')
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('same-reciprocal-return-MVAR',container[:3]==(method.index,1,1)and parameter['methodIndex']==method.index
        and parameter['ordinal']==0 and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
    need('explicit-actual-source-entry',type(source_target)is int and source_target>base)
    body=owned(image,source_target);offsets=scalar.reader_offsets(image,'animationTransitionRaw8')
    program=raw_program(body['regions'],source_target,offsets)
    advance=derive_advance(image,pins,target=program['advanceTargetVa'],offsets=offsets)
    _publication_gate(image,pins)
    result=json.loads(json.dumps(dict(schema=RAW_SCHEMA,status='validated-conditional-transition-info-raw8',nativeInputs=pins,
        typeName=TYPE,typeDefinition=nominal['typeDefinition'],readMethod='ReadUnmanaged',readerMethodDefinition=method.index,
        sourceTargetRva=source_target-base,wireBytes=8,managedBytes=8,resultAbi='register-value',resultRegister='rax',
        contextRegister='rdx',referenceLaneOffsets=[],paddingByteRanges=[],actualSourceProved=True,
        wrapperFramingUsed=False,firstFFIsRawData=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,typedRequest=typed_request,closedCarrierHex=raw.hex(),ownedMethodParameter=parameter,
            program=program,readerOffsets=offsets,family=body.get('family',{}),sourceWindows=body['windows'],
            sourceRegions=[[a,r.hex()]for a,r in body['regions']],advanceSource=advance))))
    verify_raw(result,pins);return result


def verify_raw(source,pins):
    from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
    need('own-complete-raw8-source',source.get('schema')==RAW_SCHEMA
        and source.get('status')=='validated-conditional-transition-info-raw8'and source.get('nativeInputs')==pins
        and source.get('typeName')==TYPE and source.get('readMethod')=='ReadUnmanaged'
        and source.get('wireBytes')==source.get('managedBytes')==8 and source.get('resultAbi')=='register-value'
        and source.get('resultRegister')=='rax'and source.get('contextRegister')=='rdx'
        and source.get('referenceLaneOffsets')==source.get('paddingByteRanges')==[]
        and source.get('actualSourceProved')is True and source.get('wrapperFramingUsed')is False
        and source.get('firstFFIsRawData')is True and source.get('parentFieldAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    p=source['proof'];nominal=p.get('layout',{});usage=p.get('typedRequest',{});raw=bytes.fromhex(p.get('closedCarrierHex',''))
    need('exact-own-layout-and-closed-request',nominal.get('typeName')==TYPE and nominal.get('typeDefinition')==source.get('typeDefinition')
        and nominal.get('boxedBytes')==24 and nominal.get('managedBytes')==8
        and nominal.get('fields')==[['fixedTransitionDuration','float',16],['fixedTransitionType',ENUM,20]]
        and nominal.get('referenceLaneOffsets')==nominal.get('paddingByteRanges')==[]
        and len(raw)==16 and raw[10:12]==bytes.fromhex('1180')and int.from_bytes(raw[:8],'little')==source['typeDefinition']
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and usage.get('methodSpec',[None])[0]==source.get('readerMethodDefinition'))
    usage_raw=bytes.fromhex(usage.get('instructionHex',''))
    need('actual-owned-RDX-context-load',len(usage_raw)==7 and usage_raw[:3]==bytes.fromhex('488b15'))
    program=p.get('program',{});selected=program.get('selectedBytes',[])
    need('actual-owned-entry-and-full-regions',bool(selected)and bool(p.get('sourceWindows'))
        and len(p['sourceWindows'])==len(p.get('sourceRegions',[])))
    base=selected[0][0]-source['sourceTargetRva'];regions=[]
    for at,h in p['sourceRegions']:
        raw=bytes.fromhex(h);matches=[w for w in p['sourceWindows']if base+w.get('startRva',-base)==at
            and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('all-owned-region-hashes',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
        regions.append((at,raw))
    need('same-complete-raw8-byte-program',json.loads(json.dumps(raw_program(regions,base+source['sourceTargetRva'],p['readerOffsets'])))==program)
    verify_advance(p['advanceSource'],program,pins,base)
    return base


def require_capability(cap):
    need('finite-raw8-capability',cap.get('typeName')==TYPE and cap.get('capability')==CAPABILITY
        and cap.get('wholeGrammarAdmitted')is True and cap.get('nullable')is False
        and cap.get('wireBytes')==cap.get('managedBytes')==8 and cap.get('firstFFIsRawData')is True
        and cap.get('wrapperFramingUsed')is False and cap.get('referenceLaneOffsets')==cap.get('paddingByteRanges')==[]
        and type(cap.get('readerMethodDefinition'))is int and type(cap.get('sourceTargetRva'))is int
        and cap['readerMethodDefinition']>=0 and cap['sourceTargetRva']>0)
    return cap


def compose(source,pins):
    verify_raw(source,pins)
    cap=dict(capability=CAPABILITY,typeName=TYPE,typeDefinition=source['typeDefinition'],wholeGrammarAdmitted=True,
        nullable=False,wireBytes=8,managedBytes=8,firstFFIsRawData=True,wrapperFramingUsed=False,
        referenceLaneOffsets=[],paddingByteRanges=[],readerMethodDefinition=source['readerMethodDefinition'],
        sourceTargetRva=source['sourceTargetRva'],actualContainingRouteAdmitted=False,runtimeAnimationProved=False)
    require_capability(cap)
    return dict(schema='endfield.animation-transition-raw8-components.v1',nativeInputs=pins,capability=CAPABILITY,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=[],proof=dict(source=source),parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def read(reader,*,depth=0,budget=None):
    need('bounded-raw8-depth',type(depth)is int and 0<=depth<=64)
    require_capability(reader.operation.child(CAPABILITY));at=reader.pos;raw=reader.take(8,'FMorphEmotionTransitionInfo.raw8')
    return dict(typeName=TYPE,start=at,end=reader.pos,rawHex=raw.hex(),fixedTransitionDurationBits=raw[:4].hex(),
        fixedTransitionTypeBits=raw[4:].hex(),wrapperFramingUsed=False,runtimeAnimationProved=False)
