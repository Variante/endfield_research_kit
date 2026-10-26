"""Whole selected MC2 fallback caller with separate dictionary/tag obligations."""
import json
from scripts.game_data.memorypack import animation_fallback_set_programs as paths
from scripts.game_data.memorypack.animation_fallback_dictionary_sources import TYPE as DICTIONARY,VALUE

TYPE='Beyond.Gameplay.View.Animation.AnimationMontageSetSo'
TAGS='System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>'
SCHEMA='endfield.animation-fallback-set-source.v1'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackSetSource.'+key)


def normalized(value):return json.loads(json.dumps(value))


def window_identity(values):
    return[(w['startRva'],w['endRva'],w['sha256'])for w in values]


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle,generated_member_sources as members
    from scripts.game_data.memorypack import animation_fallback_null_sources as null_owner,animation_fallback_dictionary_sources as dictionaries
    from scripts.game_data.memorypack import animation_fallback_factory_sources as factory
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.levelscript_family_regenerate import Build
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    ordinary=null_owner.derive(image,pins,typed_request=typed_request,source_target=source_target)
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper,=[w for w in wrappers.values()if w.wrapped_type==TYPE]
    need('only-own-two-reference-fields',[(m.name,m.declared_type)for m in wrapper.members]==[('_montages',DICTIONARY),('_npcMontages',TAGS)])
    methods=pointer.methods(image,wrapper);method=methods['Deserialize'];body=pointer.owned(image,image.method_pointer_va(method));rows=body['rows']
    primitive_param.reader_abi(image,ctx,method,wrapper)
    def actual_after(index):
        row=next(r for r in rows[index+1:]if bytes.fromhex(r['bytes'])[:1]==b'\xe8')
        return row,control_transfer(row)['target']
    dict_row,=[r for r in rows if bytes.fromhex(r['bytes'])[:3]==bytes.fromhex('4c8b05')]
    dict_usage=derive_typed_usage_context(image,int(dict_row['va'],16)-base,label='fallbackSet.dictionary')
    _,dict_target=actual_after(rows.index(dict_row))
    dictionary=dictionaries.derive(image,pins,typed_request=dict_usage,source_target=dict_target)
    tag_rows=[]
    for i,row in enumerate(rows):
        if bytes.fromhex(row['bytes'])[:3]!=bytes.fromhex('488b15'):continue
        usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='fallbackSet.tagList')
        if usage.get('methodName')=='ReadPackable'and usage.get('methodArguments')==[TAGS]:tag_rows.append((i,usage))
    need('one-actual-GameplayTag-list-request',len(tag_rows)==1);tag_index,tag_usage=tag_rows[0];tag_call,tag_target=actual_after(tag_index)
    validate_typed_usage_context(image,tag_usage,label='fallbackSet.tagList')
    bind_typed_read(image,tag_usage,method_name='ReadPackable',argument=TAGS,kind=21,reference=True)
    Build(image,pins).prove_named_target(tag_target,'MemoryPack.MemoryPackReader','ReadPackable',result_abi='reference')
    barrier=base+dictionary['proof']['symbolRvas']['barrier'];getter_cache={}
    life=lifecycle._derive(image,pins,wrapper,wrappers,barrier-base,getter_cache,
        typed_factory_prover=lambda *args:factory.prove(*args,pins=pins))
    setters=[members._derive_setter(image,m,wrappers,barrier-base,getter_cache,pins=pins)for m in wrapper.members]
    setter_sources=[]
    for setter in setters:
        selected=pointer.owned(image,base+setter['method'][3])
        setter_sources.append(dict(windows=selected['windows'],regions=[[a-base,h.hex().upper()]for a,h in selected['regions']],
            program=paths.setter_program(selected['regions'],selected['pointer'],field=setter['fieldOffset'],barrier=barrier)))
    formatter=pointer.owned(image,base+life['concreteFormatter']['method'][3])
    need('whole-direct-named-setters-and-holder',all(s.get('profile')=='direct-base-holder-setter'and s.get('storedBytes')==8
        and s.get('incomingValueStoredUnchanged')is True for s in setters)
        and normalized(life.get('baseHolder'))==[wrapper.name,TYPE,16])
    header_calls=[control_transfer(rows[i-1])['target']for i,r in enumerate(rows)if r['text']=='test al, al'
        and i>0 and bytes.fromhex(rows[i-1]['bytes'])[:1]==b'\xe8']
    need('one-actual-object-header-helper',len(header_calls)==1);header,=header_calls
    allocate_calls=[];ready_calls=[]
    for i,row in enumerate(rows):
        if bytes.fromhex(row['bytes'])[:1]!=b'\xe8':continue
        if i+1<len(rows)and rows[i+1]['text']=='mov rdi, rax':allocate_calls.append(control_transfer(row)['target'])
        if i>0 and bytes.fromhex(rows[i-1]['bytes'])==bytes.fromhex('48c744244800000000'):ready_calls.append(control_transfer(row)['target'])
    # The entry zero precedes the header; the second zero precedes class-ready.
    ready_calls=[t for t in ready_calls if t!=header]
    need('one-wrapper-allocation-and-one-ready-helper',len(allocate_calls)==len(ready_calls)==1)
    symbols=dict(header=header,barrier=barrier,allocate=allocate_calls[0],constructor=image.method_pointer_va(methods['.ctor']),
        classReady=ready_calls[0],dictionary=dict_target,dictionarySetter=base+setters[0]['method'][3],tags=tag_target,tagSetter=base+setters[1]['method'][3])
    programs=[paths.program(body['regions'],body['pointer'],symbols,new=new,null=null)for new,null in((False,False),(True,False),(False,True),(True,True))]
    offsets=scalar.reader_offsets(image,'fallbackSet');header_source=primitive_param.object_header_source(image,vector_recorder(image)(header-base,fragments=True),offsets)
    ready=pointer.owned(image,symbols['classReady']);ready_program=paths.class_ready_program(ready['regions'],ready['pointer'])
    allocations=[];classes=[]
    for p in programs:
        if p['allocationClassInstructionVa']is not None:
            usage=derive_typed_usage_context(image,p['allocationClassInstructionVa']-base,label='fallbackSet.wrapperAllocation')
            need('same-allocated-concrete-wrapper',(usage.get('tag'),usage.get('typeName'))==(1,wrapper.name));allocations.append(usage)
        if p['dictionaryClassInstructionVa']is not None:
            usage=derive_typed_usage_context(image,p['dictionaryClassInstructionVa']-base,label='fallbackSet.dictionaryClass')
            need('actual-ready-reference-dictionary-class',(usage.get('tag'),usage.get('typeName'))==(1,DICTIONARY));classes.append(usage)
    result=normalized(dict(schema=SCHEMA,status='validated-conditional-fallback-set-source',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
        memberCount=2,wholeSelectedCallerProved=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(method=[method.index,wrapper.name,'Deserialize',body['pointer']-base],windows=body['windows'],
            regions=[[a-base,h.hex().upper()]for a,h in body['regions']],members=[m.row()for m in wrapper.members],programs=programs,
            symbolRvas={k:v-base for k,v in symbols.items()},ordinary=ordinary,lifecycle=life,setters=setters,setterSources=setter_sources,
            formatterSource=dict(windows=formatter['windows'],regions=[[a-base,h.hex().upper()]for a,h in formatter['regions']],rows=formatter['rows']),
            header=header_source,readerOffsets=offsets,allocations=allocations,classes=classes,
            dictionary=dictionary,tagRequest=tag_usage,tagSourceInstruction=[int(tag_call['va'],16)-base,tag_call['bytes'].replace(' ','').upper()],
            tagSourceTargetRva=tag_target-base,ready=dict(windows=ready['windows'],regions=[[a-base,h.hex().upper()]for a,h in ready['regions']],program=ready_program)),
        evidenceBoundary=dict(exact='Own MC2 new/existing/FF reader, fresh dictionary zero-out and whole named reference transfers, ordinary Original/canonical callback and typed opaque ScriptableObject factory.',
            conditional='Selected initialized coherent contexts/classes and canonical callbacks, normal successful opaque Unity creation and helper/insertion ABI, disabled collector and stable disjoint input/Reader/output/frame. Runtime Unity initialization and final dictionary behavior remain unproved.')))
    _publication_gate(image,pins);return result


def selected_regions(program,windows,base,label):
    """Authenticate sparse complete selected programs against their own windows."""
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    data={}
    for at,h in program['selectedBytes']:
        for i,b in enumerate(bytes.fromhex(h)):
            need('coherent-selected-byte:'+label,at+i not in data or data[at+i]==b);data[at+i]=b
    values=[]
    for w in windows:
        a=base+w['startRva'];b=base+w['endRva']
        need('complete-selected-window:'+label,all(at in data for at in range(a,b)))
        values.append([w['startRva'],bytes(data[at]for at in range(a,b)).hex()])
    return regions(windows,values,base,label)


def verify_factory(selected,pins,base,barrier):
    """Own nominal factory facts, replaying only neutral transport algorithms."""
    from scripts.game_data.memorypack import skill_camera_custom_factory_sources as factory_paths
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    p=selected['initialization']['independentFactory'];program=selected['program'];usage=p['typedFactoryRequest']
    need('own-independent-opaque-typed-factory',p.get('schema')=='endfield.animation-fallback-ScriptableObject-factory.v1'
        and p.get('nativeInputs')==pins and(p.get('typeName'),p.get('wrapperName'))==(TYPE,selected['method'][1])
        and p.get('completeSelectedFactoryAdmitted')is True and p.get('childGrammarAdmitted')is False
        and p.get('opaqueUnityInitializationRequired')is True
        and all(p.get(k)is False for k in('originalManagedConstructorInvoked','originalManagedConstructorEffectsProved',
            'runtimeEngineCallbackOrObjectInitializationObserved'))
        and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            (6,'UnityEngine.ScriptableObject','CreateInstance',[],[TYPE]))
    raw=bytes.fromhex(p['originalRawTypeHex']);method=usage['methodSpec'][0]
    need('own-exact-CLASS-T-and-formal-MVAR',len(raw)==16 and raw[10:12]==bytes((18,0))
        and int.from_bytes(raw[:8],'little')==p['originalTypeDefinition']
        and p['formalResult']['parameterOwner'].get('methodIndex')==method
        and p['formalResult']['parameterOwner'].get('ordinal')==0
        and bytes.fromhex(p['formalResult']['rawHex'])[10:12]==bytes((30,0)))
    context=p['context'];entries=context.get('entries',[])
    need('both-independent-context-slots-own-T',context.get('definition')==method and context.get('isMethod')is True
        and[e.get('relativeSlot')for e in entries]==[0,1]and[e.get('kind')for e in entries]==[1,2]
        and all(e.get('type',{}).get('parameterOwner',{}).get('methodIndex')==method
            and e['type']['parameterOwner'].get('ordinal')==0 for e in entries))
    symbols={k:base+v for k,v in p['symbolRvas'].items()}
    native=regions(p['factoryWindows'],p['factoryRegions'],base,'fallback-own-factory')
    target=program['factoryTargetVa']
    need('full-own-generic-factory-program',normalized(factory_paths.factory_program(native,target,symbols))==p['factoryProgram'])
    native=regions(p['engineWindows'],p['engineRegions'],base,'fallback-own-engine')
    need('full-own-warm-and-cold-engine-programs',normalized([factory_paths.engine_program(native,symbols['engineCreate'],cold=c)
        for c in(False,True)])==p['enginePrograms']
        and p['engineIcallLiteral']['rva']==p['enginePrograms'][1]['literalPointer']-base
        and bytes.fromhex(p['engineIcallLiteral']['rawHex'])==
            b'UnityEngine.ScriptableObject::CreateScriptableObjectInstanceFromType(System.Type,System.Boolean)\0')
    native=regions(p['castWindows'],p['castRegions'],base,'fallback-own-cast');g=BytesPath(native,symbols['checkedCast'])
    g.take('48895c2410','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1)
    g.take('4889742430','488b31','488bcf','488bd6');compatible=g.relative('e8')
    need('full-own-compatible-cast-program',normalized(factory_paths.checked_cast_success_program(native,symbols['checkedCast'],compatible=compatible))==p['castProgram'])
    index=p['initializedClassIndexer'];native=selected_regions(index['program'],index['codeWindows'],base,'fallback-indexer')
    need('actual-own-context-indexer',index['entryRva']==p['symbolRvas']['contextEntry']
        and normalized(paths.initialized_indexer_program(native,base+index['entryRva']))==index['program'])
    native=regions(p['wrapperWindows'],p['wrapperRegions'],base,'fallback-own-wrapper-factory')
    checked=factory_paths.wrapper_program(native,base+selected['method'][3],factory=target,barrier=barrier)
    checked.update(typedFactoryMode='scriptable-object-generic',factoryUsageInstruction=[usage['instructionRva'],usage['instructionHex']],
        factoryTargetVa=target,originalReferenceStoredUnchanged=True,inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)])
    need('same-own-wrapper-RAX-full-reference-store',normalized(checked)==program
        and usage==selected['originalTypedFactory']and selected['initialization']['originalManagedConstructorInvoked']is False
        and program['typedFactoryUsage']['instruction']==base+usage['instructionRva'])


def verify_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack import animation_fallback_null_sources as ordinary,animation_fallback_dictionary_sources as dictionary
    from scripts.game_data.memorypack import reference_adapter_sources as adapters
    from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    need('own-whole-selected-MC2-source',actual.get('schema')==SCHEMA and actual.get('nativeInputs')==pins
        and actual.get('status')=='validated-conditional-fallback-set-source'and actual.get('typeName')==TYPE
        and actual.get('memberCount')==2 and actual.get('wholeSelectedCallerProved')is True
        and actual.get('childGrammarAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
    p=actual['proof'];ordinary.validate_component(p['ordinary'],pins);base=p['ordinary']['proof']['imageBase']
    need('same-own-MC2-wrapper',actual['wrapperName']==p['ordinary']['wrapperName']
        and p['method'][1:3]==[actual['wrapperName'],'Deserialize']
        and[(m.get('name'),m.get('declaredType'))for m in p['members']]==[('_montages',DICTIONARY),('_npcMontages',TAGS)])
    s={k:base+v for k,v in p['symbolRvas'].items()};native=regions(p['windows'],p['regions'],base,'fallback-whole-MC2')
    checked=[paths.program(native,base+p['method'][3],s,new=n,null=z)for n,z in((False,False),(True,False),(False,True),(True,True))]
    need('all-four-MC2-paths-and-frames',normalized(checked)==p['programs'])
    dictionary.verify_source(p['dictionary'],pins)
    need('same-owned-dictionary-call-and-context',p['dictionary']['sourceTargetRva']==p['symbolRvas']['dictionary']
        and all(x['dictionaryContextInstructionVa']==base+p['dictionary']['proof']['context']['typedRequest']['instructionRva']
            for x in checked if not x['null']))
    tag=p['tagRequest'];need('actual-own-returned-tag-list',
        (tag.get('tag'),tag.get('typeName'),tag.get('methodName'),tag.get('classArguments'),tag.get('methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadPackable',[],[TAGS])
        and len(bytes.fromhex(tag.get('instructionHex','')))==7 and bytes.fromhex(tag['instructionHex'])[:3]==bytes.fromhex('488b15')
        and p['tagSourceTargetRva']==p['symbolRvas']['tags']
        and all(x['tagContextInstructionVa']==base+tag['instructionRva']and x['tagCallInstructionVa']==base+p['tagSourceInstruction'][0]
            for x in checked if not x['null']))
    ready=p['ready'];native=regions(ready['windows'],ready['regions'],base,'fallback-class-ready')
    need('same-actual-ready-class-program',normalized(paths.class_ready_program(native,s['classReady']))==ready['program'])
    life=p['lifecycle'];need('own-direct-holder-and-concrete-callback',life.get('baseHolder')==[actual['wrapperName'],TYPE,16]
        and life.get('typedCache')is None and life.get('directHolderMode')is True
        and life.get('typedOriginalFactoryMode')=='scriptable-object-generic'
        and life['readerMethod']==p['method']and len(life.get('factories',[]))==2
        and[f['method'][2]for f in life['factories']]==['.ctor','CreateInstance'])
    for factory in life['factories']:verify_factory(factory,pins,base,s['barrier'])
    for i,(field,typename,offset)in enumerate((('_montages',DICTIONARY,24),('_npcMontages',TAGS,32))):
        setter=p['setters'][i];owned=p['setterSources'][i];native=regions(owned['windows'],owned['regions'],base,'fallback-setter-'+field)
        need('own-exact-full-reference-setter:'+field,setter.get('profile')=='direct-base-holder-setter'
            and setter.get('method',[None])[0]==p['members'][i]['methodIndex']
            and setter.get('member')==p['members'][i]and setter.get('fieldOffset')==offset
            and setter.get('targetField')==TYPE+'::'+field and setter.get('storedBytes')==8
            and setter.get('incomingValueStoredUnchanged')is True and window_identity(setter['codeWindows'])==window_identity(owned['windows'])
            and normalized(paths.setter_program(native,base+setter['method'][3],field=offset,barrier=s['barrier']))==owned['program'])
    fmt=life['concreteFormatter'];owned=p['formatterSource'];native=regions(owned['windows'],owned['regions'],base,'fallback-concrete-slot5')
    data={a+i:b for a,h in native for i,b in enumerate(h)};rows=owned['rows']
    need('all-exact-formatter-instruction-bytes',window_identity(fmt['codeWindows'])==window_identity(owned['windows'])
        and all(bytes(data.get(int(r['va'],16)+i,0)for i in range(len(bytes.fromhex(r['bytes']))))==bytes.fromhex(r['bytes'])for r in rows))
    calls=[control_transfer(r)['target']for r in rows if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
    need('own-whole-concrete-slot5-forwarder',len(calls)==2 and normalized(prove_zero_wrapper_forwarder(rows,
        dict(metadataInit=calls[0],classInit=calls[1]),base+p['method'][3]))==fmt['program'])
    a=p['ordinary']['proof']['adapter'];symbols={k:base+v for k,v in a['canonicalRoutes']['symbolRvas'].items()}
    for role,parse in(('main',adapters.main),('dispatch',adapters.dispatch)):
        native=ordinary._regions(p['ordinary']['proof']['nullSources'][role],base)
        for options in({},dict(create=False),dict(wrapper_null=True),dict(create=False,wrapper_null=True),dict(null=True)):
            parse(native,symbols[role],symbols,**options)
    return base
