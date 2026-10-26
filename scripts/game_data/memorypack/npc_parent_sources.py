"""Fresh initialized mixed NPC121 source and owned field/constructor joins."""
import struct
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_registered_formatter_composition
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
from scripts.game_data.il2cpp.string_source_programs import prove_collection_header
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
from scripts.game_data.memorypack import npc_parent_programs as source,scalar_param_native as scalar,primitive_param,pooled_nominal_key_sources as keys,reference_adapter_sources as reference
from scripts.game_data.memorypack.vector_layout import vector_recorder


def validate_components(image,pins,fact,key_fact,copy_fact,env_fact):
    if fact.get('schema')!='endfield.npc-runtime-source-component.v1'or fact['nativeInputs']!=pins or key_fact['nativeInputs']!=pins or copy_fact['nativeInputs']!=pins:raise ValueError('npcParent.schema/selected-inputs')
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);build=Build(image,pins);wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==fact['originalType']];s={k:base+v for k,v in fact['symbols'].items()};td=ctx.index.types[wrapper.name];methods={md.string(m.name_index):m for m in md.methods_for(td)}
    reviewed=[dict(m.row(),fieldOwner=build.wrappers[m.declaring_wrapper].wrapped_type,ownedField=list(ctx.field(build.wrappers[m.declaring_wrapper].wrapped_type+'::'+m.name)))for m in wrapper.members]
    if(wrapper.name,reviewed)!=(fact['wrapperType'],fact['members'])or len(wrapper.members)!=121:raise ValueError('npcParent.current-reviewed-field-order')
    if ctx.parent(wrapper.name)!='Beyond.MemoryPack.Beyond_Gameplay_LevelNpcDataForMemoryPack'or ctx.field(wrapper.name+'::__realInstance')!=(wrapper.name,wrapper.wrapped_type,32):raise ValueError('npcParent.root-own-holder')
    def owned(pointer,*,decode=True):
        regions=[];rows=[];windows=[]
        for p in image.unwind_index.family(pointer-base)['ranges']:
            a,z=p['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,z-a);regions.append((base+a,raw));windows.append(dict(startRva=a,endRva=z));rows+=decode_type_data_initialization_instructions(image.mapper,raw,base+a)if decode else[]
        return regions,rows,windows
    pointer=image.method_pointer_va(methods['Deserialize']);regions,rows,windows=owned(pointer);rows.sort(key=lambda r:int(r['va'],16));start=next(i for i,r in enumerate(rows)if r['text']=='cmp r14b, 0x79')+2;end=next(i for i,r in enumerate(rows)if r['text']=='mov [rax+0x208], rdi')+1;fields=[]
    for i,m in enumerate(wrapper.members):
        owner=build.wrappers[m.declaring_wrapper].wrapped_type;field=ctx.field(owner+'::'+m.name);setter=image.body_index.body(m.declaring_wrapper,'set___'+m.name+'__')
        fields.append(dict(name=m.name,kind=m.kind,mode='outref-dictionary'if i==110 else'int32-array'if i==42 else'vector12'if i in(10,11,12)else'inline4'if m.declared_type in('Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId')else'hidden16'if m.declared_type=='Beyond.LangKey'else'ordinary',offset=field[2],transfer='direct'if i in(0,1,2,3,5,6,7,8,9,13)else'getter-store'if i>=93 and i!=95 else'setter',hiddenLocal=-48 if i in(80,81)else-32,reference=m.kind in('string','array','list')or m.kind=='object'and m.declared_type not in('Beyond.LangKey','Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId','UnityEngine.Vector3'),setter=setter.pointer))
    array=dict(header=s['intArrayHeader'],indexedClass=s['indexedClass'],arrayAllocate=s['arrayAllocate'],copyForwarder=s['copyForwarder'],advance=s['advance'],setter=fields[42]['setter']);transfer=source.mixed_transfers(rows[start:end],fields,s,array_source=lambda count:source.selected_array(regions,s['intArrayEntry'],array,count=count));prefixes=[source.root_prefix(regions,pointer,dict(barrier=s['barrier'],allocate=s['allocate'],constructor=image.method_pointer_va(methods['.ctor'])),allocated=a,null=n)for a in(False,True)for n in(False,True)]
    normal_return=source.normal_return(regions,transfer['fieldTransfers'][-1]['endVA'])
    if{p['nextInstructionVA']for p in prefixes if not p['null']}!={int(rows[start]['va'],16)}:raise ValueError('npcParent.prefix-count-field-join')
    for profile in prefixes:
        cell=profile['allocationTypeCellVA']
        if cell:
            at=next(a for a,b in profile['selectedBytes']if b=='488b0d'and a+7+int.from_bytes(image.pe.bytes_at_va(a+3,4),'little',signed=True)==cell);u=derive_typed_usage_context(image,at-base,label='npcParent.wrapper-allocation')
            if(u['tag'],u['typeName'])!=(1,wrapper.name):raise ValueError('npcParent.wrapper-allocation-class')
    contexts=[];primitive_targets=set();key_sources=set();read_targets=set()
    offsets=scalar.reader_offsets(image,'npcParent');rec=vector_recorder(image)
    for m,r in zip(wrapper.members,transfer['fieldTransfers'],strict=True):
        if r.get('contextLoad'):
            usage=derive_typed_usage_context(image,int(r['contextLoad']['va'],16)-base,label='npcParent.field')
            if r['mode']=='outref-dictionary':
                if(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])!=('Beyond.SerializeFieldDictionary`2','DeserializeV2',['string','Beyond.Gameplay.Core.NpcAiInstanceData'],[]):raise ValueError('npcParent.typed-AI-dictionary')
                ai_type=ctx.index.types['Beyond.SerializeFieldDictionary`2'];method,=[x for x in md.methods_for(ai_type)if md.string(x.name_index)=='DeserializeV2'];selected=GenericEntries(image).resolve(method.index,['object','Beyond.Gameplay.Core.NpcAiInstanceData'],[])
                if selected['pointer']!=r['target']:raise ValueError('npcParent.actual-AI-canonical-physical-target')
            elif(usage['typeName'],usage['classArguments'],usage['methodArguments'])!=('MemoryPack.MemoryPackReader',[],[m.declared_type if m.kind!='array'else m.declared_type[:-2]]):raise ValueError('npcParent.typed-current-reader:'+m.name)
            expected_name='ReadUnmanaged'if m.kind=='enum'else'ReadArray'if m.kind=='array'else'ReadPackable'if m.kind=='list'else'ReadValue'
            if r['mode']!='outref-dictionary'and usage['methodName']!=expected_name:raise ValueError('npcParent.typed-reader-method:'+m.name)
            contexts.append(dict(field=m.name,usage=usage))
        if r['mode']=='hidden16':key_sources.add(r['target'])
        elif r['mode']not in('ordinary',):continue
        elif m.kind=='string':build.prove_pooled_string_target(r['target'])
        elif m.kind in('bool','enum','scalar32','scalar64','float32'):
            key=(m.kind,r['target']);primitive_targets.add(key)
            if m.kind=='enum':
                enum=ctx.index.types[m.declared_type];underlying=[ctx.type_name(f.type_index)for f in md.fields_for(enum)if md.string(f.name_index)=='value__']
                if underlying!=['int']:raise ValueError('npcParent.enum-int32:'+m.declared_type)
        else:read_targets.add((m.kind,r['target']))
    for kind,target in primitive_targets:
        if kind=='bool':scalar.boolean_source(image,rec(target-base),offsets,'npcParent.boolean')
        elif kind=='float32':primitive_param.single_source(image,rec(target-base,fragments=True),offsets)
        else:scalar.integer_source(image,rec(target-base,fragments=True),offsets,'npcParent.integer',width=8 if kind=='scalar64'else 4)
    for kind,target in read_targets:build.prove_reader_clone_target(target,'MemoryPack.MemoryPackReader.'+('ReadArray'if kind=='array'else'ReadPackable'if kind=='list'else'ReadValue'),result_abi='reference')
    if env_fact['nativeInputs']!=pins:raise ValueError('npcParent.array-selected-inputs')
    string_row=next(r for r in transfer['fieldTransfers']if r['field']=='envTalkIds');usage=next(r['usage']for r in contexts if r['field']=='envTalkIds');cs=ContextSymbols(image);first=cs.context(usage['methodSpec'][0],is_method=True);second=cs.context(first['entries'][0]['methodSpec'][0],is_method=True);array_method=md.methods[second['entries'][5]['methodSpec'][0]];declaring=ctx.index.types['Beyond.Gameplay.LevelNpcData'];field=next(f for f in md.fields_for(declaring)if md.string(f.name_index)=='envTalkIds');raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    if raw[10:12]!=bytes((29,0)):raise ValueError('npcParent.original-string-array')
    validate_read_array_context(image,[first,second],usage,GenericEntries(image),int.from_bytes(raw[:8],'little'),array_method.index,fail=lambda *args:(_ for _ in()).throw(ValueError('npcParent.string-array:'+str(args)[:1000])))
    if string_row['target']!=base+env_fact['fields'][0]['targetRva']:raise ValueError('npcParent.exact-shared-string-array-source')
    unmanaged=derive_typed_usage_context(image,s['intArrayEntry']-base,label='npcParent.int-array');expected=env_fact['intArray']['usage']
    if(unmanaged['typeName'],unmanaged['methodName'],unmanaged['methodArguments'],unmanaged['methodSpec'])!=(expected['typeName'],expected['methodName'],expected['methodArguments'],expected['methodSpec']):raise ValueError('npcParent.same-closed-int-array-context')
    validate_generic_contexts(image,env_fact['intArray']['contexts'],label='npcParent.int-array')
    symbols=env_fact['intArray']['symbols']
    if any(s[own]!=base+symbols[child]for own,child in(('indexedClass','indexed'),('arrayAllocate','arrayAllocate'),('advance','advance'))):raise ValueError('npcParent.same-int-array-helpers')
    if base+copy_fact['entryRva']!=base+symbols['copy']:raise ValueError('npcParent.same-bounded-copy-source')
    keys.validate_components(image,key_fact)
    if key_sources!={base+key_fact['symbols']['value16']}:raise ValueError('npcParent.actual-LangKey16-source')
    for original in('Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId'):
        tt=ctx.index.types[original];f=[f for f in md.fields_for(tt)if not ctx.field_attributes(f.type_index)&16];size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+tt.index*8)
        if not ctx.is_value_type(original)or len(f)!=1 or ctx.field(original+'::'+md.string(f[0].name_index))!=(original,'int',16)or(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))!=(20,4):raise ValueError('npcParent.nominal-int32-ABI:'+original)
    if[ctx.field('UnityEngine.Vector3::'+a)for a in'xyz']!=[('UnityEngine.Vector3','float',o)for o in(16,20,24)]:raise ValueError('npcParent.inline-Vector3-fields')
    scalar.advance_source(image,rec(s['advance']-base,fragments=True),offsets,'npcParent.advance');forward=image.pe.bytes_at_va(s['copyForwarder'],5)
    if forward[0]!=233 or s['copyForwarder']+5+int.from_bytes(forward[1:],'little',signed=True)!=base+copy_fact['entryRva']:raise ValueError('npcParent.actual-copy-forwarder')
    setters=[]
    for member in wrapper.members[14:93]:
        _,declaring,_,target,offset,method=_setter_metadata(image,build.wrappers,member);p=image.method_pointer_va(method);r,rs,_=owned(p);mode='value4'if member.declared_type=='Beyond.Gameplay.Core.GameplayTag'else'value16'if member.declared_type=='Beyond.LangKey'else'bool'if member.kind=='bool'else'int32'if member.kind in('scalar32','enum')else'uint64'if member.kind=='scalar64'else'float'if member.kind=='float32'else'reference';paths=[source.selected_setter(r,p,offset,mode,s,refresh=k)for k in('coherent','empty','different')]
        cells={v for p in paths for v in p['castClassCellVAs']};usages=[]
        for row in rs:
            raw=bytes.fromhex(row['bytes'])
            if raw[:3]==bytes.fromhex('488b15')and int(row['va'],16)+7+int.from_bytes(raw[3:],'little',signed=True)in cells:
                usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='npcParent.inherited-cast')
                if(usage['tag'],usage['typeName'])!=(1,'Beyond.Gameplay.LevelNpcData'):raise ValueError('npcParent.inherited-cache-type')
                usages.append(usage)
        if len(usages)!=2 or len(cells)!=1:raise ValueError('npcParent.same-two-inherited-cast-usages')
        setters.append(paths)
    getter=image.method_pointer_va(methods['GetValue']);gr,_,_=owned(getter);scalar.owned_method_abi(image,ctx,methods['GetValue'].index,td.index,(wrapper.wrapped_type,18,True),[],'npcParent.getter');getters=[source.getter(gr,getter,dict(cast=s['compatibleCast'],barrier=s['barrier']),refresh=k)for k in('coherent','empty','different')];cr,_,_=owned(s['compatibleCast']);casts=[source.compatible_cast(cr,s['compatibleCast'],s['assignable'],null=n)for n in(False,True)];br,_,_=owned(image.method_pointer_va(methods['set___forceEnableMorph__']),decode=False);bools=[source.bool_setter(br,image.method_pointer_va(methods['set___forceEnableMorph__']),s,refresh=k)for k in('coherent','empty','different')]
    for profile in getters+bools:
        for a,b in profile['selectedBytes']:
            if b=='488b15':
                u=derive_typed_usage_context(image,a-base,label='npcParent.root-cache-cast')
                if(u['tag'],u['typeName'])!=(1,wrapper.wrapped_type):raise ValueError('npcParent.root-cache-class')
    for role,owner in(('baseConstructor','Beyond.MemoryPack.Beyond_Gameplay_LevelNpcDataForMemoryPack'),('originalBaseConstructor','Beyond.Gameplay.LevelNpcData')):
        selected=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)=='.ctor'and image.method_pointer_va(m)==s[role]]
        if len(selected)!=1 or selected[0].flags&16 or selected[0].parameter_count or ctx.type_name(selected[0].return_type)!='void':raise ValueError('npcParent.constructor-base-ABI')
    if ctx.field(wrapper.wrapped_type+'::forceEnableMorph')!=(wrapper.wrapped_type,'bool',544):raise ValueError('npcParent.root-bool-field')
    entity='Beyond.MemoryPack.Beyond_Gameplay_LevelEntityDataForMemoryPack';em,=[m for m in md.methods_for(ctx.index.types[entity])if md.string(m.name_index)=='set___entityDataIdKey__'];er,_,_=owned(image.method_pointer_va(em));source.entity_string_setter(er,image.method_pointer_va(em),field=ctx.field('Beyond.Gameplay.LevelEntityData::entityDataIdKey')[2]);ctor=image.method_pointer_va(methods['.ctor']);cr,_,_=owned(ctor);constructor=source.constructor(cr,ctor,s)
    for role,cell in constructor['classCells'].items():
        at=next(a for a,b in constructor['selectedBytes']if b in('488b0d','488b35')and a+7+int.from_bytes(image.pe.bytes_at_va(a+3,4),'little',signed=True)==cell);u=derive_typed_usage_context(image,at-base,label='npcParent.constructor');expected=dict(baseWrapper='Beyond.MemoryPack.Beyond_Gameplay_LevelNpcDataForMemoryPack',rootOriginal=wrapper.wrapped_type,envTalkOriginal='Beyond.Gameplay.Core.NpcRuntimeEnvTalkData',staticString='string')[role]
        if(u['tag'],u['typeName'])!=(1,expected):raise ValueError('npcParent.constructor-type:'+role)
    validate_eager_wrap_registration(image,fact['eager'],label='npcParent');validate_registered_formatter_composition(image,fact['composition'],label='npcParent');core=dict(key_fact['referenceRoutes'],wrappers=[]);reference.validate_reference_routes(image,core,[]);symbols={k:base+v for k,v in core['symbolRvas'].items()};composition=fact['composition'];interface,=composition['interfaces'];section=md.sections['interfaceOffsets'];at=section.offset+td.interface_offsets_start*8;pairs=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]));ordinal=pairs.index((interface['interfaceTypeIndex'],interface['interfaceOffset']));vr,_,_=owned(symbols['conversion']);reference.conversion(vr,symbols['conversion'],base+core['conversionPrepareRva'],getter,ordinal=ordinal);forward=md.methods[interface['formatterDeserializeMethodIndex']];fp=image.method_pointer_va(forward);_,_,fw=owned(fp);fr=[r for w in fw for r in image.body_index._decode(base+w['startRva'],w['endRva']-w['startRva'])];prove_zero_wrapper_forwarder(fr,dict(metadataInit=s['metadataInit'],classInit=s['classInit']),pointer);dr,_,_=owned(symbols['dispatch']);deserialize_slot(dr,symbols['dispatch'],prepare=symbols['prepare'],callback=fp)
    hr,hrows,hw=owned(s['intArrayHeader']);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16;primary=[r for r in hrows if base+hw[0]['startRva']<=int(r['va'],16)<base+hw[0]['endRva']];prove_collection_header(primary,[r for r in hrows if r not in primary],offsets,dict(getNextSpan=s['refill'],advanceFallback=s['advanceFallback'],insufficient=s['insufficient']))
    return dict(memberCount=121,fieldTransfers=transfer['fieldTransfers'],contexts=contexts,initializedPrefixPaths=len(prefixes),inheritedSetterPaths=sum(map(len,setters)),rootGetterPaths=len(getters),rootBoolPaths=len(bools),wholeOwnerAdmitted=False,liveProviderSelectionProved=False)
