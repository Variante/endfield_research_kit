"""Concrete BlackboardString source, lifecycle and ordinary reference ABI.

The exact string/string generic base is distinct from numeric blackboards.
Its MC3 program consumes pooled key4, normalized bool1 and pooled value4;
managed string references never supply an eight-byte wire width. Selected
initialized contexts, typed zeroed fresh allocation, compatible nullable casts,
owned cache24 refresh against holder16, disabled collector, matched canonical
callbacks, exported StringPool and stable disjoint buffered storage remain
conditions. Stored configuration proves no evaluated blackboard value or live
provider/default/inflation selection. Cold/refill/error and enclosing owner/EOF
claims remain unresolved. Each native selection is derived afresh.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack import scalar_param_native as scalar
import hashlib
import json

LABEL='skillBlackboardStringSources'
TYPE='Beyond.Blackboard+BlackboardString'
WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardStringForMemoryPack'
BASE='Beyond.Blackboard+BlackboardParamBase`2<string,string>'
BASE_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_string_string_ForMemoryPack'
CAPABILITY='skill-blackboard-string'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def constructor_program(regions,entry,s):
    """Own called Original constructor; both wrapper holders receive its ref."""
    g=BytesPath(regions,entry);usages=[]
    def usage(op):
        at=g.at;cell=g.relative(op);usages.append(dict(instruction=at,cell=cell));return cell
    g.take('48895c2408','57','4883ec20');ready=flag(g);g.take('488bd9');g.branch('0f84',False)
    usage('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
    usage('488b0d');allocate=g.relative('e8');g.take('488bf8','4885c0');g.branch('0f84',False)
    g.take('33d2','488bc8');original=g.relative('e8')
    g.take('488d4b18','48897b18');g.call(s['barrier']);g.take('488d4b10','48897b10');g.call(s['barrier'])
    g.take('488b7b10');selected=usage('488b15');g.take('488bcf');g.call(s['strictCast'])
    g.take('48894318','488bcf');need('same-constructor-concrete-class',selected,usage('488b15'));g.call(s['strictCast'])
    g.take('488d4b18','488b5c2430','4883c420','5f')
    need('same-constructor-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,classUsages=usages,
        allocate=allocate,originalConstructor=original,originalHolderOffset=16,typedCacheOffset=24,
        ownCacheAndBaseHolderReceiveSameOriginal=True,normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def original_constructor_program(regions,entry,s,*,value_offset):
    """Copy a selected static string reference, without asserting its contents."""
    need('owned-string-value-slot',24,value_offset)
    g=BytesPath(regions,entry);g.take('4053','4883ec20','488bd9')
    at=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('33c0','48894318');selected=g.at;string_cell=g.relative('488b05')
    g.take('488b88b8000000','488b01','488d4b18','48894318','4883c420','5b')
    need('original-constructor-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,baseClassUsage=dict(instruction=at,cell=cell),
        staticStringClassUsage=dict(instruction=selected,cell=string_cell),staticFieldSlot=0,
        valueOffset=value_offset,staticReferenceCopiedUnchanged=True,staticReferenceContentsProved=False,
        normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def reader_program(regions,entry,offsets,slots,s,*,new=False,null=False,prepare_empty=False,original_null=False):
    """Complete normal MC3/FF paths, including exact final reference barrier."""
    need('literal-reader-choices',True,all(type(v)is bool for v in(new,null,prepare_empty,original_null)))
    need('valid-reader-choices',True,not(new and(prepare_empty or original_null))and not(original_null and not(prepare_empty and null)))
    need('owned-buffered-slots',dict(blackboardKey=32,useBlackboardKey=16,value=24),slots)
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
    if null:g.take('48c70600000000','488bce');g.jump('eb',1)
    else:
        g.take('48833e00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor']);g.take('488bce','48892e');g.call(s['barrier'])
            g.take('90');g.jump('e9');allocation=dict(instruction=at,cell=cell)
        g.take('4080ff03');g.branch('0f85',False)
        for index,(name,kind)in enumerate((('blackboardKey','poolKey'),('useBlackboardKey','boolean'),('value','poolValue'))):
            g.take('488bcb','488b3e')if index==2 else g.take('488b3e','488bcb')
            call=g.at;target=g.relative('e8');calls[kind]=dict(instruction=call,target=target)
            g.take('4885ff');g.branch('74',False,1);g.take('488b4f10','4885c9');g.branch('74',False,1)
            g.take({'poolKey':'48894120','boolean':'884110','poolValue':'48894118'}[kind])
            if kind!='boolean':
                g.take('4883c1'+('20'if index==0 else'18'))
                if index==0:g.call(s['barrier'])
        need('same-pooled-string-source',calls['poolKey']['target'],calls['poolValue']['target'])
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    need('reader-final-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        prepareCacheEmpty=prepare_empty,prepareOriginalNull=original_null,inlineClassUsages=classes,
        wrapperAllocationUsage=allocation,primitiveCalls=calls,memberCount=None if null else 3,
        originalHolderOffset=16,typedCacheOffset=24,wireBytes=1 if null else 10,
        normalReturnViaBarrier=True,entryRspRestored=True,childGrammarsAdmitted=False)


def derive(image,pins):
    """Re-prove the exact named string/string source, callbacks and lifecycle."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import type_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_fast_barrier
    from scripts.game_data.memorypack.skill_root_buff_input_sources import (
        derived_cached_getter_program,prepare_program,nullable_class_cast_program,compatible_class_program)
    from scripts.game_data.memorypack.skill_blackboard_double_sources import strict_cast_program,factory_program
    from scripts.game_data.memorypack.skill_blackboard_int_sources import instance_setter_program
    from scripts.game_data.memorypack.generated_member_sources import base_setter_program
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack import pooled_source_helper
    selected_inputs(pins);_publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need('nominal-string-lineage',(BASE_WRAPPER,BASE,False),(ctx.parent(WRAPPER),ctx.parent(TYPE),ctx.is_value_type(TYPE)))
    for owner,field,typename,slot,kind in((BASE_WRAPPER,'___instance',BASE,16,21),(WRAPPER,'__realInstance',TYPE,24,18)):
        need('owned-holder:'+field,(owner,typename,slot),ctx.field(owner+'::'+field))
        fd,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==field]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),kind,LABEL+'.'+field,reference=True)
    parent_pointer=ctx.type_pointer(ctx.index.types[TYPE].parent_index)
    scalar.ordinary(image,parent_pointer,21,LABEL+'.closedBase',reference=True)
    parent=ContextSymbols(image).type(parent_pointer);need('closed-string-base-name',BASE,parent['name'])
    need('closed-string-base-arguments',['string','string'],[arg['name']for arg in parent['classArguments']])
    for argument in parent['classArguments']:
        raw=bytes.fromhex(argument['rawHex']);need('closed-built-in-string-reference',True,len(raw)==16 and raw[10:12]==b'\x0e\x00')
    base_td=ctx.index.types[BASE.split('<')[0]];base_fields={md.string(f.name_index):f for f in md.fields_for(base_td)}
    need('exact-base-instance-fields',{'blackboardKey','useBlackboardKey','value'},set(base_fields))
    for name,kind in(('blackboardKey',14),('useBlackboardKey',2)):
        scalar.ordinary(image,ctx.type_pointer(base_fields[name].type_index),kind,LABEL+'.base.'+name,reference=kind==14)
    raw=image.pe.bytes_at_va(ctx.type_pointer(base_fields['value'].type_index),16)
    need('base-value-owned-VAR',b'\x13\x00',raw[10:12])
    parameter=type_parameter_owner(md.buf,int.from_bytes(raw[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
    need('base-value-owned-first-parameter',(base_td.index,0),(parameter['typeIndex'],parameter['ordinal']))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==WRAPPER];mm=methods(image,wrapper)
    bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in
        ('.ctor','CreateInstance','get___instance','set___instance','OnDeserialized','Deserialize')}
    for name in('GetValue','get___instance','CreateInstance','OnDeserialized','.ctor'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,True)if name in('GetValue','get___instance')else('void',1,False),[],LABEL+'.'+name)
    scalar.owned_method_abi(image,ctx,mm['set___instance'].index,wrapper.type_definition,
        ('void',1,False),[(TYPE,18,True)],LABEL+'.instanceSetter')
    getter_pointer=image.method_pointer_va(mm['GetValue']);thunk=image.pe.bytes_at_va(getter_pointer,7)
    need('exact-GetValue-instance-getter-thunk',b'\x33\xd2\xe9',thunk[:3])
    need('same-owned-instance-getter',bodies['get___instance']['pointer'],getter_pointer+7+int.from_bytes(thunk[3:],'little',signed=True))
    getter_entry=dict(selectedBytes=[[getter_pointer,thunk.hex().upper()]],sameWholeReceiverRcx=True,
        unusedMethodInfoEdxZero=True,stackAndNonvolatilesUnchanged=True,fullGetterSemanticsDelegated=True)
    def after(body,raw):
        return {control_transfer(row)['target']for i,row in enumerate(body['rows'])if i
            and bytes.fromhex(row['bytes'])[:1]==b'\xe8'and bytes.fromhex(body['rows'][i-1]['bytes']).hex()==raw}
    cast,=after(bodies['get___instance'],'488bcf');barrier,=after(bodies['get___instance'],'488d4b18')
    strict,={control_transfer(row)['target']for i,row in enumerate(bodies['CreateInstance']['rows'][:-1])
        if bytes.fromhex(row['bytes'])[:1]==b'\xe8'and bodies['CreateInstance']['rows'][i+1]['text']=='mov [rdi+0x18], rax'}
    bodies['cast']=owned(image,cast);bodies['strictCast']=owned(image,strict)
    predicate,={control_transfer(row)['target']for row in bodies['cast']['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8'}
    bodies['assignable']=owned(image,predicate);prepare,=after(bodies['assignable'],'488bcf')
    class_predicate=compatible_class_program(bodies['assignable']['regions'],predicate,prepare)
    casts=[nullable_class_cast_program(bodies['cast']['regions'],cast,predicate,null=n)for n in(False,True)]
    strict_casts=[strict_cast_program(bodies['strictCast']['regions'],strict,predicate,null=n)for n in(False,True)]
    symbols=dict(cast=cast,strictCast=strict,barrier=barrier,assignable=predicate,constructor=bodies['.ctor']['pointer'])
    constructor=constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],symbols)
    symbols.update(allocate=constructor['allocate'],originalConstructor=constructor['originalConstructor'],instanceSetter=bodies['set___instance']['pointer'])
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'],symbols)
    om,=[method for method in md.methods_for(ctx.index.types[TYPE])if md.string(method.name_index)=='.ctor'and method.parameter_count==0]
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[],LABEL+'.originalConstructor')
    need('actual-named-original-constructor',image.method_pointer_va(om),symbols['originalConstructor'])
    bodies['originalConstructor']=owned(image,symbols['originalConstructor'])
    slots=dict(blackboardKey=32,useBlackboardKey=16,value=24);setters=[]
    expected=[('blackboardKey','string',14,'reference-return'),('useBlackboardKey','bool',2,'normalized-byte-return'),('value','string',14,'reference-return')]
    setter_names=[s[1]for s in image.setter_methods(ctx.index.types[BASE_WRAPPER],parameter='typeName',label=LABEL)]
    need('selected-named-base-setter-order',['set___'+n+'__'for n,_,_,_ in expected],setter_names)
    for name,typename,kind,mode in expected:
        method,=[m for m in md.methods_for(ctx.index.types[BASE_WRAPPER])if md.string(m.name_index)=='set___'+name+'__']
        scalar.owned_method_abi(image,ctx,method.index,method.declaring_type,('void',1,False),[(typename,kind,kind==14)],LABEL+'.'+name)
        body=owned(image,image.method_pointer_va(method));bodies['setter:'+name]=body
        program=base_setter_program(body['rows'],holder=16,field=slots[name],mode=mode,barrier=barrier)
        setters.append(dict(method=[method.index,BASE_WRAPPER,md.string(method.name_index),body['pointer']-base],
            declaredBaseField=name,closedFieldType=typename,sourceOwnedFieldOffset=slots[name],program=program))
    original=original_constructor_program(bodies['originalConstructor']['regions'],bodies['originalConstructor']['pointer'],symbols,value_offset=slots['value'])
    string_td=ctx.index.types['System.String'];string_slots=runtime_type_field_offsets(md,image.pe,image.registration,string_td.index)
    static_fields=[f for f in md.fields_for(string_td)if ctx.field_attributes(f.type_index)&16
        and string_slots[md.string(f.name_index)]==original['staticFieldSlot']and ctx.type_name(f.type_index)=='string']
    need('one-owned-static-string-slot',1,len(static_fields));static_field=static_fields[0]
    scalar.ordinary(image,ctx.type_pointer(static_field.type_index),14,LABEL+'.staticString',reference=True)
    original['selectedStaticStringField']=[string_td.index,'System.String',md.string(static_field.name_index),original['staticFieldSlot']]
    setter=instance_setter_program(bodies['set___instance']['regions'],bodies['set___instance']['pointer'],symbols)
    barrier_windows,barrier_proof,_=_fast_barrier(image,barrier)
    getters=[derived_cached_getter_program(bodies['get___instance']['regions'],bodies['get___instance']['pointer'],symbols,cache=state,cache_offset=24)
        for state in('coherent','empty','stale')]
    prepares=[prepare_program(bodies['OnDeserialized']['regions'],bodies['OnDeserialized']['pointer'],symbols,**path)
        for path in({},{'cache_empty':True},{'cache_empty':True,'original_null':True})]
    offsets=scalar.reader_offsets(image,LABEL)
    programs=[reader_program(bodies['Deserialize']['regions'],bodies['Deserialize']['pointer'],offsets,slots,symbols,**path)
        for path in({},{'new':True},{'null':True},{'new':True,'null':True},{'prepare_empty':True},
            {'prepare_empty':True,'null':True},{'prepare_empty':True,'original_null':True,'null':True})]
    primitives=programs[0]['primitiveCalls'];record=vector_recorder(image)
    boolean=record(primitives['boolean']['target']-base);scalar.boolean_source(image,boolean,offsets,LABEL+'.bool')
    pool=pooled_source_helper.validate_on_image(image,primitives['poolKey']['target'],pins)
    typed=[]
    def typed_class(usage,name):
        actual=derive_typed_usage_context(image,usage['instruction']-base,label=LABEL+'.class')
        need('exact-owned-class',(1,name),(actual['tag'],actual['typeName']));typed.append(actual)
    for usage,name in zip(constructor['classUsages'],(BASE_WRAPPER,TYPE,TYPE,TYPE),strict=True):typed_class(usage,name)
    typed_class(factory['allocationUsage'],TYPE);typed_class(original['baseClassUsage'],BASE)
    typed_class(original['staticStringClassUsage'],'string')
    for program in factory['concreteClassUsages']:typed_class(program,TYPE)
    for program in getters+prepares+programs:
        for usage in program.get('concreteClassUsages',program.get('inlineClassUsages',[])):typed_class(usage,TYPE)
        if program.get('wrapperAllocationUsage'):typed_class(program['wrapperAllocationUsage'],WRAPPER)
        if 'ff'in program and not program['ff']:need('same-independent-primitive-calls',primitives,program['primitiveCalls'])
    pair=derive_pair(image,TYPE,WRAPPER);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-owned-reference-getter',getter_pointer-base,adapter['getterMethod'][3])
    need('same-own-static-reader',[mm['Deserialize'].index,WRAPPER,'Deserialize',bodies['Deserialize']['pointer']-base],adapter['pairForwarder']['readerMethod'])
    reader=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=WRAPPER,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
            ('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),('value','pooled-string','byte-payload'))],
        **{key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        callbackSelectionConditional=True,positiveWireBytes=10,nullWireBytes=1,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-string-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-string',capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
        proof=dict(closedBase=parent,baseValueParameter=parameter,pair=pair,readerPrograms=programs,
            constructor=constructor,originalConstructor=original,factory=factory,instanceSetter=setter,
            getters=getters,getterEntry=getter_entry,prepares=prepares,baseSetters=setters,classPredicate=class_predicate,casts=casts,strictCasts=strict_casts,
            sourceWindows={name:body['windows']for name,body in bodies.items()},typedClassUsages=typed,
            getterEntryWindow=dict(startRva=getter_pointer-base,endRva=getter_pointer-base+7,sha256=hashlib.sha256(thunk).hexdigest().upper(),boundary='exact seven-byte GetValue thunk; full named getter owned separately'),
            barrierWindows=barrier_windows,barrierProof=barrier_proof,selectedDisabledBarrierPreservesR9R10=True,
            primitiveSources=dict(boolean=boolean,pool=pool),adapter=adapter,referenceReaders=reader),
        evidenceBoundary=dict(exact='Nominal string/string closed base, named base setter field source, pooled key4/bool1/pooled value4, complete initialized MC3/new/FF/return paths, holder/cache refresh, constructors/factory/setter/casts and independently selected canonical reference ABI.',
            conditional=__doc__,structuralOnly='Stored key/flag/string configuration.',unresolved=['runtime evaluation/provider/callback choice','cold/refill/error paths','enclosing owners/physical EOF']))))
