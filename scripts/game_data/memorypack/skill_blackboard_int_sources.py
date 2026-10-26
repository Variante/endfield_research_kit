"""Concrete BlackboardInt lifecycle, separate from its warm wire declaration.

The nominal int/int base, holder16, cache24 and exact buffered MC3/FF programs
are independently selected. Compatible initialized metadata and typed fresh
zeroed allocation, exact generated callbacks, disabled collector, coherent
existing cache or its owned refresh, sufficient buffered disjoint storage and
normal class helpers remain conditions. Stored configuration establishes no
blackboard evaluation or live formatter/provider selection.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillBlackboardIntSources'
TYPE='Beyond.Blackboard+BlackboardInt'
WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardIntForMemoryPack'
BASE='Beyond.Blackboard+BlackboardParamBase`2<int,int>'
BASE_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_int_int_ForMemoryPack'
CAPABILITY='skill-blackboard-int'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def constructor_program(regions,entry,s,*,value_offset):
    """Full typed allocation, inline zero value and concrete cache refresh."""
    need('owned-Int32-slot',True,type(value_offset)is int and 16<=value_offset<128)
    g=BytesPath(regions,entry);usages=[]
    def usage(op):
        at=g.at;cell=g.relative(op);usages.append(dict(instruction=at,cell=cell));return cell
    g.take('48895c2410','57','4883ec20');ready=flag(g);g.take('488bd9');g.branch('0f84',False)
    usage('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    usage('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
    usage('488b0d');g.take('4889742430','83b9e000000000');g.branch('0f84',False)
    g.take('4533c9','488d4b18','44894f'+bytes((value_offset,)).hex(),'48897b18');g.call(s['barrier'])
    g.take('488d4b10','48897b10');g.call(s['barrier']);g.take('488b7b10')
    selected=usage('488b35');g.take('4885ff');g.branch('0f84',False)
    g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('48897b18');need('same-concrete-cache-class',selected,usage('488b35'))
    g.take('488b0f','488bd6');g.call(s['assignable']);g.take('84c0');g.branch('74',False,1)
    g.take('488d4b18','488b742430','488b5c2438','4883c420','5f')
    need('same-constructor-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,classUsages=usages,allocate=allocate,
        originalHolderOffset=16,typedCacheOffset=24,zeroInt32Offset=value_offset,
        ownCacheAndBaseHolderReceiveSameOriginal=True,normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def factory_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('75',True,1)
    at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
    g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('4533c0','33d2','488bcb');constructor=g.relative('e8')
    g.take('4533c0','488bd3','488bcf');instance_setter=g.relative('e8')
    g.take('488b5f10');classes=[]
    for ordinal in range(2):
        if ordinal:g.take('488bcb')
        site=g.at;target=g.relative('488b15');classes.append(dict(instruction=site,cell=target))
        if not ordinal:g.take('488bcb')
        g.call(s['strictCast'])
        if not ordinal:g.take('48894718')
    need('same-factory-class',classes[0]['cell'],classes[1]['cell'])
    g.take('488d4f18','488b5c2430','4883c420','5f')
    need('factory-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,allocationUsage=dict(instruction=at,cell=cell),
        allocate=allocate,originalConstructor=constructor,originalConstructorInt32Argument=0,
        instanceSetter=instance_setter,concreteClassUsages=classes,originalHolderOffset=16,typedCacheOffset=24,
        normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def instance_setter_program(regions,entry,s):
    """Exact two reference stores, with owned disabled barrier preserving R9/10."""
    g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895118','4883c118','4c8bca')
    g.call(s['barrier']);g.take('498d4a10','4d894a10','4883c428')
    need('setter-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,originalHolderOffset=16,typedCacheOffset=24,
        unchangedIncomingOriginal=True,requiredPreservedAcrossDisabledBarrier=['r9','r10'],
        normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def original_constructor_program(regions,entry,*,value_offset):
    """Own .ctor(int), preserving the actual incoming value across readiness."""
    need('owned-original-Int32-slot',True,type(value_offset)is int and 16<=value_offset<128)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bd9','8bfa')
    at=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('897b'+bytes((value_offset,)).hex(),'488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,baseClassUsage=dict(instruction=at,cell=cell),
        valueOffset=value_offset,incomingInt32StoredUnchanged=True,normalReturn=True,entryRspRestored=True,wireBytes=0)


def reader_program(regions,entry,offsets,slots,s,*,new=False,null=False,prepare_empty=False,original_null=False):
    need('literal-reader-choices',True,all(type(v)is bool for v in(new,null,prepare_empty,original_null)))
    need('valid-reader-choices',True,not(new and(prepare_empty or original_null))and not(original_null and not(prepare_empty and null)))
    need('owned-buffered-slots',dict(blackboardKey=24,useBlackboardKey=16,value=20),slots)
    g=BytesPath(regions,entry);classes=[];calls={};allocation=None
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bf2','488bd9');g.branch('0f84',False);g.take('488b2e','4885ed');g.branch('74',new,1)
    if not new:
        flag(g);g.branch('0f84',False);g.take('48837d1800');g.branch('0f84',prepare_empty)
        if prepare_empty:
            g.take('48837d1000');g.branch('0f84',original_null)
            if not original_null:
                g.take('488b7d10')
                for ordinal in range(2):
                    if ordinal:g.take('488bcf')
                    at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
                    if not ordinal:g.take('488bcf')
                    g.call(s['cast'])
                    if not ordinal:g.take('48894518')
                need('same-preparation-class',classes[0]['cell'],classes[1]['cell'])
                g.take('488d4d18');g.call(s['barrier']);g.take('90');g.jump('e9')
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb638','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080ffff');g.branch('0f84',null)
    if null:
        g.take('488bce','48c70600000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('48833e00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bce','48892e');g.call(s['barrier'])
            g.take('90');g.jump('e9');allocation=dict(instruction=at,cell=cell)
        g.take('4080ff03');g.branch('0f85',False)
        for index,(name,kind)in enumerate((('blackboardKey','pool'),('useBlackboardKey','boolean'),('value','int32'))):
            g.take('488bcb','488b3e')if index==2 else g.take('488b3e','488bcb')
            call=g.at;target=g.relative('e8');calls[kind]=dict(instruction=call,target=target)
            g.take('4885ff');g.branch('74',False,1);g.take('488b4f10','4885c9');g.branch('74',False,1)
            g.take({'pool':'48894118','boolean':'884110','int32':'894114'}[kind])
            if not index:g.take('4883c118');g.call(s['barrier'])
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        prepareCacheEmpty=prepare_empty,prepareOriginalNull=original_null,inlineClassUsages=classes,
        wrapperAllocationUsage=allocation,primitiveCalls=calls,memberCount=None if null else 3,
        originalHolderOffset=16,typedCacheOffset=24,wireBytes=1 if null else 10,
        normalReturn=True,entryRspRestored=True,childGrammarsAdmitted=False)


def derive(image,pins):
    """Re-prove the warm field grammar and complete own reference lifecycle."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import buff_blackboard_int_native as warm,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_fast_barrier
    from scripts.game_data.memorypack.skill_root_buff_input_sources import (
        derived_cached_getter_program,prepare_program,nullable_class_cast_program,compatible_class_program)
    from scripts.game_data.memorypack.skill_blackboard_double_sources import strict_cast_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    selected_inputs(pins);_publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    reviewed=json.loads(warm.CONTRACT_PATH.read_bytes());need('warm-native-inputs',pins,reviewed['nativeInputs'])
    actual=warm.derive(image,pins,reviewed);need('fresh-complete-warm-declaration',reviewed,actual)
    need('exact-int-wire',dict(nullHeader=255,memberCount=3,members=[dict(name=n,kind=k)for n,k in(
        ('blackboardKey','int32-pool-index'),('useBlackboardKey','bool-byte'),('value','raw-int32'))]),actual['wireLayout'])
    need('nominal-int-lineage',(BASE_WRAPPER,BASE,False),(ctx.parent(WRAPPER),ctx.parent(TYPE),ctx.is_value_type(TYPE)))
    for owner,field,typename,slot,kind in((BASE_WRAPPER,'___instance',BASE,16,21),(WRAPPER,'__realInstance',TYPE,24,18)):
        need('owned-holder:'+field,(owner,typename,slot),ctx.field(owner+'::'+field))
        fd,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==field]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),kind,LABEL+'.'+field,reference=True)
    parent_pointer=ctx.type_pointer(ctx.index.types[TYPE].parent_index)
    scalar.ordinary(image,parent_pointer,21,LABEL+'.closedBase',reference=True)
    parent=ContextSymbols(image).type(parent_pointer);need('closed-int-base-name',BASE,parent['name'])
    need('closed-int-base-arguments',['int','int'],[arg['name']for arg in parent['classArguments']])
    for argument in parent['classArguments']:
        raw=bytes.fromhex(argument['rawHex']);need('closed-ordinary-int-value',True,len(raw)==16 and raw[10:12]==bytes((8,128)))
    base_td=ctx.index.types[BASE.split('<')[0]]
    field,=[f for f in md.fields_for(base_td)if md.string(f.name_index)=='value']
    raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);need('base-value-owned-VAR',b'\x13\x00',raw[10:12])
    parameter=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
    need('base-value-owned-first-parameter',(base_td.index,0),(parameter['typeIndex'],parameter['ordinal']))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER]
    mm=methods(image,wrapper);pair=derive_pair(image,TYPE,WRAPPER,owned_getter_family=True)
    bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in
        ('.ctor','CreateInstance','GetValue','get___instance','set___instance','OnDeserialized','Deserialize')}
    for name in('GetValue','get___instance','CreateInstance','OnDeserialized','.ctor'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,True)if name in('GetValue','get___instance')else('void',1,False),[],LABEL+'.'+name)
    scalar.owned_method_abi(image,ctx,mm['set___instance'].index,wrapper.type_definition,
        ('void',1,False),[(TYPE,18,True)],LABEL+'.instanceSetter')
    def after(body,raw):
        return {control_transfer(row)['target']for i,row in enumerate(body['rows'])if i
            and bytes.fromhex(row['bytes'])[:1]==b'\xe8'and bytes.fromhex(body['rows'][i-1]['bytes']).hex()==raw}
    cast,=after(bodies['GetValue'],'488bcf');barrier,=after(bodies['GetValue'],'488d4b18')
    factory_rows=bodies['CreateInstance']['rows']
    strict,={control_transfer(row)['target']for i,row in enumerate(factory_rows[:-1])
        if bytes.fromhex(row['bytes'])[:1]==b'\xe8'and factory_rows[i+1]['text']=='mov [rdi+0x18], rax'}
    bodies['cast']=owned(image,cast);bodies['strictCast']=owned(image,strict)
    predicate,={control_transfer(row)['target']for row in bodies['cast']['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8'}
    bodies['assignable']=owned(image,predicate);prepare,=after(bodies['assignable'],'488bcf')
    class_predicate=compatible_class_program(bodies['assignable']['regions'],predicate,prepare)
    casts=[nullable_class_cast_program(bodies['cast']['regions'],cast,predicate,null=n)for n in(False,True)]
    strict_casts=[strict_cast_program(bodies['strictCast']['regions'],strict,predicate,null=n)for n in(False,True)]
    symbols=dict(cast=cast,strictCast=strict,barrier=barrier,assignable=predicate,constructor=bodies['.ctor']['pointer'])
    slots=actual['proof']['typedStores']['fieldOffsets']
    constructor=constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],symbols,value_offset=slots['value'])
    symbols['allocate']=constructor['allocate']
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'],symbols)
    need('same-factory-allocator',symbols['allocate'],factory['allocate'])
    need('same-actual-instance-setter',bodies['set___instance']['pointer'],factory['instanceSetter'])
    om,=[method for method in md.methods_for(ctx.index.types[TYPE])if md.string(method.name_index)=='.ctor'
        and method.parameter_count==1 and ctx.type_name(next(iter(md.parameters_for(method))).type_index)=='int']
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[('int',8,False)],LABEL+'.originalConstructor')
    need('actual-named-int-constructor',image.method_pointer_va(om),factory['originalConstructor'])
    bodies['originalConstructor']=owned(image,factory['originalConstructor'])
    original=original_constructor_program(bodies['originalConstructor']['regions'],bodies['originalConstructor']['pointer'],value_offset=slots['value'])
    setter=instance_setter_program(bodies['set___instance']['regions'],bodies['set___instance']['pointer'],symbols)
    barrier_windows,barrier_proof,_=_fast_barrier(image,barrier)
    getters={name:[derived_cached_getter_program(bodies[name]['regions'],bodies[name]['pointer'],symbols,cache=state,cache_offset=24)
        for state in('coherent','empty','stale')]for name in('GetValue','get___instance')}
    prepares=[prepare_program(bodies['OnDeserialized']['regions'],bodies['OnDeserialized']['pointer'],symbols,**path)
        for path in({},{'cache_empty':True},{'cache_empty':True,'original_null':True})]
    offsets=scalar.reader_offsets(image,LABEL)
    programs=[reader_program(bodies['Deserialize']['regions'],bodies['Deserialize']['pointer'],offsets,slots,symbols,**path)
        for path in({},{'new':True},{'null':True},{'new':True,'null':True},{'prepare_empty':True},
            {'prepare_empty':True,'null':True},{'prepare_empty':True,'original_null':True,'null':True})]
    primitives=programs[0]['primitiveCalls'];record=vector_recorder(image)
    bool_proof=record(primitives['boolean']['target']-base);scalar.boolean_source(image,bool_proof,offsets,LABEL+'.bool')
    int_proof=record(primitives['int32']['target']-base);scalar.integer_source(image,int_proof,offsets,LABEL+'.int32')
    pool=pooled_source_helper.validate_on_image(image,primitives['pool']['target'],pins)
    typed=[]
    def typed_class(usage,name):
        actual=derive_typed_usage_context(image,usage['instruction']-base,label=LABEL+'.class')
        need('exact-owned-class',(1,name),(actual['tag'],actual['typeName']));typed.append(actual)
    for usage,name in zip(constructor['classUsages'],(BASE_WRAPPER,TYPE,BASE,TYPE,TYPE),strict=True):typed_class(usage,name)
    typed_class(factory['allocationUsage'],TYPE);typed_class(original['baseClassUsage'],BASE)
    for program in factory['concreteClassUsages']:typed_class(program,TYPE)
    for paths in getters.values():
        for program in paths:
            for usage in program['concreteClassUsages']:typed_class(usage,TYPE)
    for program in prepares:
        for usage in program['concreteClassUsages']:typed_class(usage,TYPE)
    for program in programs:
        for usage in program['inlineClassUsages']:typed_class(usage,TYPE)
        if program['wrapperAllocationUsage']:typed_class(program['wrapperAllocationUsage'],WRAPPER)
        if not program['ff']:need('same-independent-primitive-calls',primitives,program['primitiveCalls'])
    adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-owned-reference-getter',bodies['GetValue']['pointer']-base,adapter['getterMethod'][3])
    need('same-own-static-reader',[mm['Deserialize'].index,WRAPPER,'Deserialize',bodies['Deserialize']['pointer']-base],
        adapter['pairForwarder']['readerMethod'])
    reader=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
            ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','int32',None))],
        **{key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        callbackSelectionConditional=True,positiveWireBytes=10,nullWireBytes=1,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-int-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-int',capabilities={CAPABILITY:cap},
        proof=dict(warm=actual,closedBase=parent,baseValueParameter=parameter,pair=pair,readerPrograms=programs,
            constructor=constructor,originalConstructor=original,factory=factory,instanceSetter=setter,
            getters=getters,prepares=prepares,classPredicate=class_predicate,casts=casts,strictCasts=strict_casts,
            sourceWindows={name:body['windows']for name,body in bodies.items()},typedClassUsages=typed,
            barrierWindows=barrier_windows,barrierProof=barrier_proof,
            selectedDisabledBarrierPreservesR9R10=True,primitiveSources=dict(boolean=bool_proof,int32=int_proof,pool=pool),
            adapter=adapter,referenceReaders=reader),
        evidenceBoundary=dict(exact='Nominal int/int closed base, pooled key4/bool1/Int32 value4, complete own initialized MC3/new/FF/return paths, holder/cache refresh, constructors, factory/setter/casts and independently selected canonical reference ABI.',
            conditional=__doc__,structuralOnly='Stored key/flag/Int32 configuration.',unresolved=['runtime evaluation/provider/callback choice','cold/refill/error paths','enclosing owners/physical EOF']))))
