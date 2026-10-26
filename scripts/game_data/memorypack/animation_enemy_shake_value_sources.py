"""EnemyHurtShakeIntensityConfig's own MC2 and canonical value8 callback.

The two raw Single fields are copied through the actual SSE GetValue program.
The canonical callback owns FF/default8, wrapper-null/default8 and its selected
interface return. No ReadValue raw8 fast path is used to infer MC2 framing.
"""
import hashlib
import json
import struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot

TYPE='Beyond.Gameplay.View.Animation.EnemyAnimExtraData+EnemyHurtShakeIntensityConfig'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_View_Animation_EnemyAnimExtraData_EnemyHurtShakeIntensityConfigForMemoryPack'
SCHEMA='endfield.animation-enemy-shake-value-source.v1'
FIELDS=[['animationSpeed','float',16],['animationWeight','float',20]]


def need(check,condition):
    if not condition:raise ValueError('animationEnemyShakeValue.'+check)


def normalized(v):return json.loads(json.dumps(v))


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('f30f104114','f30f104910','0f14c8','66480f7ec8','c3')
    return dict(selectedBytes=g.seen,managedBytes=8,sourceSlices=[[0,4],[4,4]],resultRegister='rax',
        fullInputBitsReturnedUnchanged=True,floatBitsNormalized=False,normalReturn=True,entryRspRestored=True,calleeCalls=0)


def getter_entry(image,owner,getter):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('own-named-getter',image.type_name(owner.index)==WRAPPER and getter.declaring_type==owner.index)
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    scalar.owned_method_abi(image,NativeReferenceContext(image),getter.index,owner.index,(TYPE,17,False),[],'enemyShake.GetValue')
    at=image.method_pointer_va(getter);return getter_program([(at,image.pe.bytes_at_va(at,19))],at)


def wrapper_program(regions,entry,*,new=False,null=False):
    need('literal-selected-path',type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);symbols={};calls=[];allocation=None
    def call(role):
        at=g.at;t=g.relative('e8');need('same-helper:'+role,role not in symbols or symbols[role]==t)
        symbols[role]=t;calls.append(dict(role=role,instructionVa=at,targetVa=t))
    g.take('48895c2418','57','4883ec20');flag=g.relative('803d');g.take('00','488bda','488bf9');g.branch('74',False,1)
    g.take('488d542430','c644243000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    if null:
        g.take('488bcb','48c70300000000');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742438','48833b00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','48894810','488bcb','488903');call('barrier');g.take('90');g.jump('e9')
            allocation=dict(instructionVa=at,cellVa=cell,zeroedManagedBytes=8)
        g.take('0fb6742430','4080fe02');g.branch('0f85',False)
        g.take('488b33','488bcf');call('single');g.take('4885f6');g.branch('74',False,1)
        g.take('f30f114610','488bcf','488b1b');call('single');g.take('4885db');g.branch('74',False,1)
        g.take('488b742438','f30f114314')
    g.take('488b5c2440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,newWrapper=new,wrapperNull=null,metadataReadyFlagVa=flag,
        symbols=symbols,sourceCalls=calls,allocation=allocation,memberCount=None if null else 2,
        wireBytes=1 if null else 9,managedBytes=8,entryRspRestored=True,normalReturn=True,
        wireOrder=[]if null else['animationSpeed','animationWeight'],defaultValueReturnAdmitted=False)


def nonnull_program(regions,entry,s,*,wrapper_null=False):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','4c89442418','57','4883ec20');g.relative('803d');g.take('00',
        '498bf9','488bf2','488bd9');g.branch('0f84',False)
    g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    g.take('488b4f20');g.call(s['resolve']);g.take('488b88c0000000','488b4920');g.call(s['wrapperProvider'])
    g.take('4885c0');g.branch('74',False,1)
    g.take('b905000000','4c8d4c2440','4c8bc3','488bd0');g.call(s['wrapperInvoke'])
    g.take('488b5c2440','4885db');g.branch('74',wrapper_null,1)
    if wrapper_null:g.take('33c0');g.jump('eb',1)
    else:
        g.take('488b4f20');g.call(s['resolve']);g.take('ba08000000','488b88c0000000');g.call(s['indexed'])
        g.take('488bd0','4c8bc3');g.call(s['conversion'])
    g.take('488b5c2430','488906','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wrapperNull=wrapper_null,managedBytes=8,defaultZeroBytes=8 if wrapper_null else 0,
        sameFullQwordStored=True,referenceLaneOffsets=[],barrierCalls=[],normalReturn=True,entryRspRestored=True)


def primitive_program(regions,entry,offsets,*,single):
    g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    if single:
        g.take('48895c2408','57','4883ec30','8379'+rem+'04','488bd9','0f29742420');g.branch('0f8c',False)
        g.take('488b43'+cur,'f30f1030','8b7b'+rem,'83c7fc');g.branch('0f88',False)
        g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,'488b5c2440',
            '0f28c6','0f28742420','4883c430','5f','c3')
    else:
        g.take('48895c2408','4889742410','57','4883ec20','8379'+rem+'01','488bfa','488bd9');g.branch('0f8c',False)
        g.take('488b43'+cur,'0fb608','880f','8b73'+rem,'83ee01');g.branch('0f88',False)
        g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'8973'+rem,'803fff','488b5c2430','488b742438',
            '0f95c0','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=4 if single else 1,rawSingleBits=single,
        onlyFFReturnsFalse=not single,entryRspRestored=True,normalReturn=True)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td=ctx.index.types[TYPE];md=image.metadata
    need('own-nongeneric-plain-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('own-two-Single-fields',actual==FIELDS)
    for f in fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,'enemyShake.Single')
    need('bounded-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
    need('own-boxed24-native8',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,8))
    return dict(typeName=TYPE,typeDefinition=td.index,boxedBytes=24,managedBytes=8,fields=actual,
        referenceLaneOffsets=[],paddingByteRanges=[])


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources as bp
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,event_args_paths
    from scripts.game_data.memorypack import pooled_global_buff_id_sources as paths
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);ge=GenericEntries(image)
    nominal=layout(image,ctx);wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    need('own-wrapper-MC2',wrapper.wrapped_type==TYPE and ctx.field(WRAPPER+'::__instance')==(WRAPPER,TYPE,16)
        and[(m.name,m.declared_type)for m in wrapper.members]==[(a,b)for a,b,c in FIELDS])
    mm=pointer.methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    pair=derive_pair(image,TYPE,WRAPPER,getter_entry_prover=getter_entry)
    forward=pointer.registered_pair(image,pair,wrapper,label='enemyShake.pair')
    getter=getter_entry(image,image.metadata.types[wrapper.type_definition],mm['GetValue'])
    zero=[]
    for name in('.ctor','CreateInstance'):
        method=mm[name];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],'enemyShake.zero')
        zero.append(dict(method=[method.index,WRAPPER,name,image.method_pointer_va(method)-base],
            program=pointer.leaf(image,image.method_pointer_va(method),['33C0','48894110','C3'])))
    body=pointer.owned(image,image.method_pointer_va(mm['Deserialize']))
    wrapper_paths=[wrapper_program(body['regions'],body['pointer'],**p)for p in({},{'new':True},{'null':True})]
    symbols={}
    for path in wrapper_paths:
        for role,target in path['symbols'].items():need('same-wrapper-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    usage=derive_typed_usage_context(image,wrapper_paths[1]['allocation']['instructionVa']-base,label='enemyShake.allocate')
    need('own-wrapper-allocation',usage.get('tag')==1 and usage.get('typeName')==WRAPPER
        and base+usage['usageCellRva']==wrapper_paths[1]['allocation']['cellVa'])
    sources={'wrapper':body};registrations={}
    for role,name in(('adapter','Deserialize'),('nonnull','DeserializeNotNull'),('readNull','ReadIsNull')):
        method=bp._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2',name)
        registrations[role]=ge.resolve(method.index,[TYPE,'object'],[]);symbols[role]=registrations[role]['pointer']
        sources[role]=pointer.owned(image,symbols[role])
    for role,at in dict(readNull=55,typeHandle=109,isAbstract=129,activate=153,nonnull=182).items():
        target=bp._call(sources['adapter'],at);need('same-canonical-helper:'+role,role not in symbols or symbols[role]==target);symbols[role]=target
    for role,at in dict(resolve=66,wrapperProvider=82,wrapperInvoke=108,indexed=144,conversion=155).items():symbols[role]=bp._call(sources['nonnull'],at)
    need('same-owned-context-resolver',symbols['resolve']==bp._call(sources['nonnull'],127))
    for role in('conversion','wrapperInvoke'):sources[role]=pointer.owned(image,symbols[role])
    symbols['prepare']=bp._call(sources['conversion'],27);need('same-wrapper-preparation',symbols['prepare']==bp._call(sources['wrapperInvoke'],35))
    symbols['peek']=bp._call(sources['readNull'],14)
    p=BytesPath(sources['readNull']['regions'],symbols['readNull']+21);null_at=p.relative('0f85')
    need('same-null-header',bp._call(sources['readNull'],null_at-symbols['readNull']+8)==symbols['header'])
    sources['peek']=pointer.owned(image,symbols['peek'])
    face,=pair['composition']['interfaces'];td=image.metadata.types[wrapper.type_definition]
    section=image.metadata.sections['interfaceOffsets'];start=section.offset+td.interface_offsets_start*8
    ordinal=list(struct.iter_unpack('<ii',image.metadata.buf[start:start+td.interface_offsets_count*8])).index((face['interfaceTypeIndex'],face['interfaceOffset']))
    paths_out=dict(adapter=[paths.adapter_program(sources['adapter']['regions'],symbols['adapter'],symbols,**p)for p in({},{'create':False},{'null':True})],
        nonnull=[nonnull_program(sources['nonnull']['regions'],symbols['nonnull'],symbols,wrapper_null=n)for n in(False,True)],
        readNull=[paths.read_null_program(sources['readNull']['regions'],symbols['readNull'],symbols,null=n)for n in(False,True)],
        conversion=paths.conversion_program(sources['conversion']['regions'],symbols['conversion'],symbols,ordinal=ordinal),
        wrapperInvocation=deserialize_slot(sources['wrapperInvoke']['regions'],symbols['wrapperInvoke'],prepare=symbols['prepare'],
            callback=image.method_pointer_va(image.metadata.methods[face['formatterDeserializeMethodIndex']])))
    offsets=scalar.reader_offsets(image,'enemyShake');record=vector_recorder(image)
    primitive_param.object_header_source(image,record(symbols['header']-base),offsets)
    primitive_param.single_source(image,record(symbols['single']-base),offsets)
    primitive_paths={}
    for role in('single','header'):
        sources[role]=pointer.owned(image,symbols[role])
        primitive_paths[role]=primitive_program(sources[role]['regions'],symbols[role],offsets,single=role=='single')
    peek=event_args_paths.peek(sources['peek']['regions'],symbols['peek'],offsets)
    barrier=_fast_barrier(image,symbols['barrier']);context,context_proof=bp._adapter_context(image,ge)
    _publication_gate(image,pins)
    return normalized(dict(schema=SCHEMA,status='validated-conditional-enemy-shake-canonical-value8',nativeInputs=pins,
        typeName=TYPE,wrapperName=WRAPPER,managedBytes=8,referenceLaneOffsets=[],paddingByteRanges=[],
        ordinaryOriginalCallbackAdmitted=True,ordinaryOriginalReadValueAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=nominal,pair=pair,forwarding=forward,getter=getter,zeroLeaves=zero,wrapperPaths=wrapper_paths,
            paths=paths_out,registrations=registrations,interfaceOrdinal=ordinal,allocationUsage=usage,
            adapterContext=context,adapterContextProof=context_proof,primitivePaths=primitive_paths,readerOffsets=offsets,peek=peek,barrier=barrier,
            symbolRvas={k:v-base for k,v in symbols.items()},sourceWindows={k:v['windows']for k,v in sources.items()},
            sourceRegions={k:[[a-base,r.hex()]for a,r in v['regions']]for k,v in sources.items()})))
