"""Own SkMorph layout and conditional hidden40/canonical wrapper transfers.

The stored Unity object and padding are copied unchanged and consume no
serialized members. Neutral fixed40 byte programs supply only ABI transfers;
the exact nominal pair, fields, callback, getter and source are proved here.
The MC5 child grammar and enclosing field/frame remain separate obligations.
"""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Core.SkMorphPlaySetting'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_SkMorphPlaySettingForMemoryPack'
TRANSITION='Beyond.Gameplay.Core.FMorphEmotionTransitionInfo'
FIELDS=[('useAssetDirectly','bool',16),('motionType','Beyond.Montage.SkMorphMotionType',20),
    ('motionTag','Beyond.Gameplay.Core.GameplayTag',24),('motionAssetPathHash','Beyond.Resource.StringPathHash',32),
    ('motionAsset','UnityEngine.Object',40),('transitionInfo',TRANSITION,48)]
SLICES=[[0,16],[16,16],[32,8]]
PADDING=[[1,3],[12,4]]


def need(check,condition,detail=None):
    if not condition:raise ValueError('skMorphValue.'+check+':'+str(detail)[:700])


def validate_layout(nominal):
    need('own-complete-layout',nominal.get('typeName')==TYPE and type(nominal.get('typeDefinition'))is int
        and nominal.get('boxedBytes')==56 and nominal.get('managedBytes')==40
        and nominal.get('fields')==[list(r)for r in FIELDS]and nominal.get('referenceLaneOffsets')==[24]
        and nominal.get('paddingByteRanges')==PADDING and nominal.get('paddingRangeEncoding')=='start,length'
        and nominal.get('serializedFieldNames')==['motionAssetPathHash','motionTag','motionType','transitionInfo','useAssetDirectly']
        and nominal.get('runtimeOnlyFieldNames')==['motionAsset']and nominal.get('wireGrammarAdmitted')is False)
    children=nominal.get('nestedLayouts',[])
    need('own-complete-nested-layouts',[(r.get('typeName'),r.get('managedBytes'))for r in children]==[
        ('Beyond.Gameplay.Core.GameplayTag',4),('Beyond.Resource.StringPathHash',8),(TRANSITION,8)]
        and all(type(r.get('typeDefinition'))is int and r.get('referenceLaneOffsets')==r.get('paddingByteRanges')==[]for r in children)
        and[r.get('fields')for r in children]==[[['tagId','int',16]],[['hash','long',16]],
            [['fixedTransitionDuration','float',16],['fixedTransitionType','Beyond.Gameplay.Core.EMorphEmotionTransitionType',20]]])
    need('own-complete-enum-layouts',[(r.get('typeName'),r.get('backingType'),r.get('backingBytes'))for r in nominal.get('enums',[])]
        ==[(FIELDS[1][1],'int',4),('Beyond.Gameplay.Core.EMorphEmotionTransitionType','int',4)]
        and all(type(r.get('typeDefinition'))is int for r in nominal['enums']))
    return nominal


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    def fields(name):
        definition=ctx.index.types[name]
        need('own-nongeneric-value:'+name,ctx.is_value_type(name)and not ctx.is_enum(name)and definition.generic_container_index<0)
        rows=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
        return rows,[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in rows]
    rows,actual=fields(TYPE);need('own-six-physical-fields',actual==FIELDS,actual)
    for field,kind in zip(rows,(2,17,17,17,18,17),strict=True):
        scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'skMorphValue.field',reference=kind==18)
    nested=[]
    for name,expected,kinds,size in(
        ('Beyond.Gameplay.Core.GameplayTag',[('tagId','int',16)],(8,),4),
        ('Beyond.Resource.StringPathHash',[('hash','long',16)],(10,),8),
        (TRANSITION,[('fixedTransitionDuration','float',16),
            ('fixedTransitionType','Beyond.Gameplay.Core.EMorphEmotionTransitionType',20)],(12,17),8)):
        child,declared=fields(name);need('own-nested-fields:'+name,declared==expected,declared)
        for field,kind in zip(child,kinds,strict=True):scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,'skMorphValue.nested')
        definition=ctx.index.types[name];at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+definition.index*8)
        need('own-nested-size:'+name,(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(16+size,size))
        nested.append(dict(typeName=name,typeDefinition=definition.index,fields=declared,managedBytes=size,referenceLaneOffsets=[],paddingByteRanges=[]))
    enums=[]
    for name in(FIELDS[1][1],'Beyond.Gameplay.Core.EMorphEmotionTransitionType'):
        definition=ctx.index.types[name];backing,=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
        need('own-int32-enum:'+name,ctx.is_enum(name)and definition.generic_container_index<0
            and md.string(backing.name_index)=='value__'and ctx.field(name+'::value__')==(name,'int',16))
        scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'skMorphValue.enum')
        enums.append(dict(typeName=name,typeDefinition=definition.index,backingType='int',backingBytes=4))
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-boxed56-managed40',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(56,40))
    return validate_layout(json.loads(json.dumps(dict(typeName=TYPE,typeDefinition=td.index,boxedBytes=56,managedBytes=40,fields=FIELDS,
        nestedLayouts=nested,enums=enums,referenceLaneOffsets=[24],paddingByteRanges=PADDING,paddingRangeEncoding='start,length',
        runtimeOnlyFieldNames=['motionAsset'],serializedFieldNames=['motionAssetPathHash','motionTag','motionType','transitionInfo','useAssetDirectly'],
        wireGrammarAdmitted=False))))


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f104a20','0f1101','f20f104230','0f114910','f20f114120','c3')
    return dict(selectedBytes=g.seen,managedBytes=40,sourceSlices=SLICES,sourceWrapperRegister='rdx',outputRegister='rcx',
        returnsSameOutputRax=True,completePayloadBitsCopied=True,normalFrameAndReturn=True,physicalExtentProved=False,wireGrammarAdmitted=False)


def zero_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f57c0','33c0','0f114110','0f114120','48894130','c3')
    return dict(selectedBytes=g.seen,managedBytes=40,zeroedSlices=SLICES,completePayloadZeroed=True,
        normalFrameAndReturn=True,physicalExtentProved=False,wireGrammarAdmitted=False)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
    """Own full40 transfer with the actual runtime-object lane24 barrier."""
    need('literal-wrapper-null-path',type(wrapper_null)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','4c89442418','57','4883ec50');ready=flag(g)
    g.take('498bf9','488bf2','488bd9');g.branch('0f84',False)
    provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('0f84',False)
    g.take('b905000000','4c8d4c2470','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2470','4885db');g.branch('0f84',wrapper_null)
    if wrapper_null:g.take('0f57c0','33c0','0f1106','0f114610','48894620');g.jump('e9')
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('4c8bc0','488d4c2420','4c8bcb');g.call(s['conversion'])
        g.take('488d4e18','0f1008','0f105010','f20f104020','0f110e','0f115610','f20f114620');g.call(s['barrier'])
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,providerClassCell=provider,wrapperNull=wrapper_null,
        managedBytes=40,defaultZeroBytes=40 if wrapper_null else 0,copiedSlices=[]if wrapper_null else SLICES,
        referenceBarrierOffset=24,referenceLaneOffsets=[24],wrapperProviderContextSlot=4,conversionInterfaceContextSlot=8,
        sameIncomingReaderAndHiddenOutput=True,entryRspRestored=True,normalReturn=True,wireGrammarAdmitted=False)


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp,primitive_param,event_args_paths
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_global_buff_id_sources as providers
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_smart_target_value_transfer import adapter_program,read_program
    from scripts.game_data.memorypack.skill_root_assign_pair_transfer import conversion40_program
    from scripts.game_data.memorypack.skill_nominal_value_read_sources import _provider,_selected_classes
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    need('own-actual-R8-ReadValue-request',tuple(typed_request.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])and bytes.fromhex(typed_request.get('instructionHex',''))[:3]==bytes.fromhex('4c8b05'))
    typed=bp._typed_context(image,typed_request,TYPE,ge);nominal=layout(image,ctx);wrapper=_selected_wrapper(image,WRAPPER)
    need('own-inline-holder',ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16))
    pair=derive_pair(image,TYPE,WRAPPER);forwarding=pointer.registered_pair(image,pair,wrapper,label='skMorphValue.pair')
    face,=pair['composition']['interfaces'];getter=md.methods[face['getValueMethodIndex']]
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'skMorphValue.GetValue')
    at=image.method_pointer_va(getter);getter_proof=getter_program([(at,image.pe.bytes_at_va(at,128))],at)
    mm=pointer.methods(image,wrapper);leaves=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],'skMorphValue.zero')
        at=image.method_pointer_va(method);q=zero_program([(at,image.pe.bytes_at_va(at,128))],at)
        leaves.append(dict(method=[method.index,WRAPPER,name,at-base],program=q))
    td=md.types[wrapper.type_definition];start=md.sections['interfaceOffsets'].offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    context,context_proof=bp._adapter_context(image,ge);sources={};registrations={};s={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);s[role]=registrations[role]['pointer'];sources[role]=pointer.owned(image,s[role])
    sources['read']=pointer.owned(image,source_target)
    s.update(provider=bp._call(sources['read'],69),dispatch=bp._call(sources['read'],88))
    for role,offset in dict(readNull=54,typeHandle=108,creationTest=128,activate=152,nonnull=181).items():
        target=bp._call(sources['adapter'],offset)
        if role in s:need('same-canonical-target:'+role,s[role]==target)
        s[role]=target
    method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','ReadIsNull')
    registrations['readNull']=ge.resolve(method.index,[TYPE,'object'],[])
    need('own-ReadIsNull-source',registrations['readNull']['pointer']==s['readNull'])
    sources['readNull']=pointer.owned(image,s['readNull']);s['peek']=bp._call(sources['readNull'],14)
    ff=BytesPath(sources['readNull']['regions'],s['readNull']+21).relative('0f85')
    s['header']=BytesPath(sources['readNull']['regions'],ff+8).relative('e8')
    s.update({role:bp._call(sources['nonnull'],offset)for role,offset in dict(resolve=66,wrapperProvider=82,wrapperInvoke=112,
        indexed=152,conversion=168,barrier=201).items()})
    need('same-own-context-resolver',s['resolve']==bp._call(sources['nonnull'],135))
    for role in('provider','dispatch','conversion','wrapperInvoke','peek','header'):sources[role]=pointer.owned(image,s[role])
    s['prepare']=bp._call(sources['dispatch'],32);need('same-interface-preparation',s['prepare']==bp._call(sources['conversion'],36))
    paths={role:[adapter_program(sources[role]['regions'],s[role],s,dispatch=role=='dispatch',**p)
        for p in({},{'create':False},{'null':True})]for role in('adapter','dispatch')}
    paths['nonnull']=[nonnull_program(sources['nonnull']['regions'],s['nonnull'],s,wrapper_null=n)for n in(False,True)]
    paths['readNull']=[providers.read_null_program(sources['readNull']['regions'],s['readNull'],s,null=n)for n in(False,True)]
    paths['conversion']=conversion40_program(sources['conversion']['regions'],s['conversion'],s['prepare'],ordinal=ordinal)
    reader=read_program(sources['read']['regions'],source_target,s);provider=_provider(image,sources['provider'],s)
    need('own-TypeFromHandle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    need('same-provider-helper-targets',s['typeHandle']==provider['symbols']['typeHandle']and s['indexed']==provider['symbols']['indexed'])
    if provider['profile']=='called-cast':
        from scripts.game_data.il2cpp.initializer_control import control_transfer
        sources['cast']=pointer.owned(image,provider['symbols']['cast'])
        targets={control_transfer(r)['target']for r in sources['cast']['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'}
        need('one-own-cast-predicate',len(targets)==1);predicate,=targets
        provider['castPrograms']=[providers.successful_cast(sources['cast']['regions'],sources['cast']['pointer'],predicate,null=n)for n in(False,True)]
    read_classes=_selected_classes(image,sources['read'],reader);provider_classes=_selected_classes(image,sources['provider'],provider['program'])
    need('own-provider-class-contexts',[(r['tag'],r['typeName'])for r in read_classes]==[(1,'MemoryPack.MemoryPackFormatterProvider')]
        and[(r['tag'],r['typeName'])for r in provider_classes]==[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    invoke=deserialize_slot(sources['wrapperInvoke']['regions'],s['wrapperInvoke'],prepare=s['prepare'],callback=image.method_pointer_va(md.methods[face['formatterDeserializeMethodIndex']]))
    offsets=scalar.reader_offsets(image,'skMorphValue');peek=event_args_paths.peek(sources['peek']['regions'],s['peek'],offsets)
    header=vector_recorder(image)(s['header']-base);primitive_param.object_header_source(image,header,offsets)
    barrier,barrier_program,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.sk-morph-value-source.v1',status='validated-conditional-sk-morph-hidden40-source',
        nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,managedBytes=40,resultAbi='hidden-local',actualSourceProved=True,
        sourceTargetRva=source_target-base,readerMethodDefinition=typed_request['methodSpec'][0],referenceLaneOffsets=[24],paddingByteRanges=PADDING,
        wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,layout=nominal,pair=pair,forwarding=forwarding,ownGetter=getter_proof,zeroLeaves=leaves,
            adapterContext=context,adapterContextProof=context_proof,registrations=registrations,interfaceOrdinal=ordinal,readerProgram=reader,paths=paths,
            providerProgram=provider,readClasses=read_classes,providerClasses=provider_classes,wrapperInvocation=invoke,peek=peek,header=header,
            barrier=barrier,barrierProgram=barrier_program,symbolRvas={k:v-base for k,v in s.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
            actualSourceRegions={k:[[at-base,raw.hex()]for at,raw in v['regions']]for k,v in sources.items()},
            actualComparedCanonicalAdapterRva=s['adapter']-base,closedWrapperPointerEqualityInferred=False,runtimeSelectionObserved=False),
        evidenceBoundary=dict(exact='Own current named40 layout and runtime object lane, eager pair, canonical FF/default40/non-null/interface/GetValue and actual typed Reader/provider/dispatch.',
            conditional=__doc__,unresolved=['MC5 wrapper wire and nested transition child','enclosing field/setter/frame','runtime provider selection','whole owner and EOF']))))
