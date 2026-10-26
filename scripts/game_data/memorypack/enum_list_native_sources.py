"""Finite nominal enum lists, conditionally selected through own formatter paths.

Each exact enum remains nominal in its ListFormatter allocation, constructor,
Register<List<Enum>> request, original class/MethodInfo and RGCTX variables.
The independently proved primitive method-selection path can select the exact
ListFormatter<Int32Enum> code registration while retaining those original
contexts. This is separate from the enum element's own ordinary formatter and
raw DWORD callback selection. Neither an Int32 underlying field nor a matching
pointer/name substitutes for these two source joins.

The selected full list source has signed four-byte count, -1 null, zero empty,
and one unchanged Reader/output-local/Add iteration. Fresh and cleared reused
paths, actual capacity constructor, raw DWORD Add, provider and dispatcher are
independently owned. Witnesses0..3 plus the same R14D loop support a finite
nonnegative count bound under nonwrapping normal child/ABI/capacity effects.
Fresh allocation starts zeroed; reused storage has enough capacity after Clear.
Collector-disabled barriers, initialized coherent original contexts/interner/
method tables, successful nominal registry hits/casts and no intervening
formatter replacement remain explicit conditions. Runtime selection/state,
growth/refill/error paths and enclosing parent/full-file EOF are unresolved.
"""
import copy
import json
import struct
from bisect import bisect_right

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.enum_nominal_callback_sources import (
    CONTRACT_PATH as CALLBACK_PROFILE, _derive_on_profile, _nodes, validate_profile,
)
from scripts.game_data.il2cpp.enum_nominal_registration_paths import macro_program,source_rows
from scripts.game_data.il2cpp.formatter_composition import (
    _vtable,derive_typed_usage_context,validate_generic_contexts,
)
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack import enum_list_source_programs as programs

SCHEMA='endfield.nominal-enum-list-sources.v1'
LABEL='nominalEnumLists'
FORMATTER='MemoryPack.Formatters.ListFormatter`1'
PROVIDER='MemoryPack.MemoryPackFormatterProvider'
LIST='System.Collections.Generic.List`1'
ENUM_TYPES=(
    'Beyond.GEnums.DamageType',
    'Beyond.GEnums.FCNodeType',
    'Beyond.Gameplay.Core.AbilityEntityFinishReason',
    'Beyond.Gameplay.Core.Buff+FinishReason',
    'Beyond.Gameplay.Core.Skill+InterruptReason',
    'Beyond.Gameplay.GainAtbMethod',
    'Beyond.Gameplay.GainAtbType',
    'Beyond.Gameplay.SkillType',
    'Beyond.Gameplay.View.CameraControlModuleType',
)


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def _fail(key,expected,actual):
    if expected!=actual:raise ValueError(LABEL+'.'+key+': expected='+str(expected)[:220]+': actual='+str(actual)[:220])


def decode(mapper,data,entry):
    from scripts.game_data.il2cpp.enum_registry_publication_paths import decode as inherited
    from scripts.game_data.il2cpp.integer_addressing import decode_register_arithmetic
    class Fallback:
        def decode_one_x64(self,raw,offset,at):
            result=decode_register_arithmetic(raw,offset,at)
            return result if result is not None else mapper.decode_one_x64(raw,offset,at)
    return inherited(Fallback(),data,entry)


def tail_control(rows,entry,tail_exits):
    """Actual E9 tails and complete indirect calls, with ordinary frame checks."""
    from scripts.game_data.il2cpp.type_data_initialization_control import _flow
    from scripts.game_data.il2cpp.field_setup_control import _frames
    by={int(r['va'],16):r for r in rows};edges={};calls=[];returns=[];tails=[]
    need('unique-tail-family-entry',len(by)==len(rows)and entry in by)
    need('bounded-exact-external-tail-set',type(tail_exits)is dict and 0<len(tail_exits)<=16)
    flows={}
    for at,row in sorted(by.items()):
        flow=_flow(row,{},{});kind=flow['kind'];end=at+len(bytes.fromhex(row['bytes']))
        if at in tail_exits:
            spec=tail_exits[at]
            need('exact-actual-external-E9',type(spec)is dict and set(spec)=={'target'}
                and bytes.fromhex(row['bytes'])[:1]==b'\xe9'and kind=='jump'
                and flow['target']==spec['target']and flow['target']not in by)
            flow=dict(flow,kind='tailExit');kind='tailExit';tails.append(dict(site=at,**flow))
        targets=set()
        if kind in('next','conditional','call','opaqueCall','indirectCall','registerCall'):targets.add(end)
        if kind in('conditional','jump'):targets.add(flow['target'])
        if kind in('call','opaqueCall','indirectCall','registerCall'):
            need('no-unproved-call-into-owned-interior',kind!='call'or flow['target']not in by)
            calls.append(dict(site=at,**flow))
        elif kind=='return':returns.append(at)
        else:need('finite-tail-family-control',kind in('next','conditional','jump','tailExit','trap'))
        need('tail-family-exact-local-edges',targets<=by.keys())
        edges[at]=targets;flows[at]=flow
    need('all-tail-witnesses-used',set(tail_exits)=={r['site']for r in tails})
    reached=set();pending=[entry]
    while pending:
        at=pending.pop()
        if at not in reached:reached.add(at);pending.extend(edges[at]-reached)
    selected=[r for r in rows if int(r['va'],16)in reached]
    def transfer(row):
        kind=flows[int(row['va'],16)]['kind']
        return dict(kind='return'if kind=='tailExit'else'call'if kind=='opaqueCall'else kind)
    frames=_frames(selected,{a:edges[a]for a in reached},0,dict(entryRva=entry),transfer_decoder=transfer)
    return dict(completeOwnedControlInstructionCount=len(rows),ordinaryEntryInstructionCount=len(reached),
        calls=calls,returns=returns,actualExternalTailExits=tails,edges=edges,ordinaryFrames=frames,
        unenteredOwnedRows=[r for r in rows if int(r['va'],16)not in reached],
        actualIndirectCalleeIdentityProved=False,actualExternalTailEffectsAdmitted=False,
        normalIndirectAndTailReturnRequired=True)


def full_source(image,pointer):
    """Complete actual owned family; external tail paths retain own obligations."""
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
    from scripts.game_data.il2cpp.enum_registry_publication_paths import ordinary_program
    body=owned(image,pointer);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows=source_rows(sorted(rows,key=lambda r:int(r['va'],16)))
    ranges=[(a,a+len(raw))for a,raw in body['regions']]
    check_byte_partition(ranges,[(int(r['va'],16),int(r['va'],16)+len(bytes.fromhex(r['bytes'])),'instruction')for r in rows],LABEL)
    tails={}
    for row in rows:
        if bytes.fromhex(row['bytes'])[:1]!=b'\xe9':continue
        flow=control_transfer(row)
        if flow['kind']=='jump'and not any(a<=flow['target']<b for a,b in ranges):
            need('exact-external-direct-tail',bytes.fromhex(row['bytes'])[:1]==b'\xe9')
            tails[int(row['va'],16)]=dict(target=flow['target'])
    graph=tail_control(rows,pointer,tails)if tails else ordinary_program(body['regions'],rows,pointer)
    body['rows']=rows
    return body,dict(windows=body['windows'],**graph)


def _call(rows,index):
    row=rows[index];raw=bytes.fromhex(row['bytes'])
    need('complete-actual-E8:'+str(index),len(raw)==5 and raw[0]==0xe8)
    return control_transfer(row)['target']


def _barrier_source(image,target):
    import hashlib
    base=image.pe.image_base;prefix=image.pe.bytes_at_va(target,12)
    need('bounded-actual-barrier-prefix',prefix[:2]==b'\x83\x3d'
        and prefix[6:10]==b'\x00\x4c\x8b\xc1'and prefix[10]==0x74)
    end=target+12+int.from_bytes(prefix[11:],'little',signed=True)
    need('bounded-separate-barrier-return',target+12<=end<=target+139)
    ret=image.pe.bytes_at_va(end,1);need('actual-barrier-return-byte',ret==b'\xc3')
    regions=[(target,prefix),(end,ret)];program=programs.disabled_barrier(regions,target)
    return dict(program=program,codeWindows=[dict(startRva=at-base,endRva=at-base+len(raw),
        sha256=hashlib.sha256(raw).hexdigest().upper(),boundary='actual selected no-unwind guard/copy/JE or RET slice; whole extent unproved')
        for at,raw in regions],fullPhysicalExtentProved=False)


def _registration(image,pins,callbacks,*,enum_types=ENUM_TYPES):
    from scripts.game_data.il2cpp.native_cell_references import selected_qword_reference_candidates
    ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image);pe=image.pe;base=pe.image_base
    ctor,=[m for m in md.methods_for(ctx.index.types[FORMATTER])if md.string(m.name_index)=='.ctor']
    register,=[m for m in md.methods_for(ctx.index.types[PROVIDER])if md.string(m.name_index)=='Register'and m.generic_container_index>=0]
    prior=callbacks['proof']['nominalRegistrySource']['proof'];scalar=prior['nominalRegistrationSource']['proof']
    need('same-fresh-Register-definition',register.index==scalar['registerMethod'][0])
    need('own-constructor-instance-noarg-void',not ctor.flags&16 and not md.parameters_for(ctor)and ctx.type_name(ctor.return_type)=='void')
    specs={}
    for i,(method,ci,mi)in enumerate(ge.specs):
        if method not in(ctor.index,register.index):continue
        cn,_=ge.arguments(ci);mn,_=ge.arguments(mi)
        if method==ctor.index and len(cn)==1 and cn[0]in enum_types and not mn:specs[i]=(cn[0],'constructor')
        if method==register.index and not cn and len(mn)==1:
            names=[n for n in enum_types if mn==[LIST+'<'+n+'>']]
            if names:specs[i]=(names[0],'register')
    need('one-own-constructor-register-per-nominal',len(specs)==2*len(enum_types)
        and all(sorted(r for n,r in specs.values()if n==name)==['constructor','register']for name in enum_types))
    words={(6<<29)|(i<<1)|1:i for i in specs};cells={}
    for section in pe.sections:
        if section['characteristics']&0x20000000:continue
        raw=pe.buf[section['rawPointer']:section['rawPointer']+section['rawSize']]
        for off in range((-section['virtualAddress'])%8,len(raw)-7,8):
            word=struct.unpack_from('<Q',raw,off)[0]
            if word in words:cells[section['virtualAddress']+off]=words[word]
    starts=sorted(image.unwind_index.entries);cache={};choices={n:[]for n in enum_types}
    for candidate in selected_qword_reference_candidates(pe,set(cells)):
        name,role=specs[cells[candidate['cellRva']]]
        if candidate['kind']!='load'or role!='constructor':continue
        at=candidate['siteRva'];i=bisect_right(starts,at)-1
        need('owned-registration-site',i>=0 and starts[i]<=at<image.unwind_index.entries[starts[i]][1])
        primary=image.unwind_index.resolve(starts[i]);family=image.unwind_index.family(primary)
        if sum(p['runtimeTriple'][1]-p['runtimeTriple'][0]for p in family['ranges'])>4096:continue
        if primary not in cache:cache[primary]=full_source(image,base+primary)
        body,full=cache[primary];by={int(r['va'],16):j for j,r in enumerate(body['rows'])}
        need('constructor-site-boundary',base+at in by and by[base+at]>=5)
        entry=int(body['rows'][by[base+at]-5]['va'],16);program=macro_program(body['regions'],entry)
        need('actual-own-constructor-site',program['constructorUsageInstruction']==base+at)
        choices[name].append((len(body['rows']),primary,program,full))
    selected={};ctor_targets=set();register_targets=set();symbols=ContextSymbols(image)
    for name in enum_types:
        need('selected-registration:'+name,bool(choices[name]))
        _,primary,program,full=min(choices[name],key=lambda row:(row[0],row[1]));closed=LIST+'<'+name+'>'
        usages={role:derive_typed_usage_context(image,program[key]-base,label=LABEL)for role,key in
            [('allocation','allocationUsageInstruction'),('constructor','constructorUsageInstruction'),('register','registerUsageInstruction')]}
        allocation,construct,reg=[usages[k]for k in('allocation','constructor','register')]
        need('own-closed-formatter-allocation:'+name,allocation['tag']==1 and allocation['typeName']==FORMATTER+'<'+name+'>'
            and bytes.fromhex(allocation['typeRawHex'])[10:12]==b'\x15\x00')
        need('own-closed-formatter-constructor:'+name,construct['tag']==6 and construct['methodSpec'][0]==ctor.index
            and construct['typeName']==FORMATTER and construct['methodName']=='.ctor'
            and construct['classArguments']==[name]and construct['methodArguments']==[])
        need('own-closed-list-registration:'+name,reg['tag']==6 and reg['methodSpec'][0]==register.index
            and reg['typeName']==PROVIDER and reg['methodName']=='Register'
            and reg['classArguments']==[]and reg['methodArguments']==[closed])
        ctor_arg,=image.instantiations.resolve(construct['methodSpec'][1]).arguments
        reg_arg,=image.instantiations.resolve(reg['methodSpec'][2]).arguments
        element=symbols.type(ctor_arg.type_pointer_va);container=symbols.type(reg_arg.type_pointer_va)
        td=ctx.index.types[name];raw=pe.bytes_at_va(ctx.type_pointer(td.byval_type_index),16)
        need('same-own-enum-carrier:'+name,ctx.is_enum(name)and ctx.field(name+'::value__')[1:]==('int',16)
            and raw[10:12]==b'\x11\x80'and element['name']==name and element['rawHex']==raw.hex().upper()
            and ctor_arg.type_pointer_va==ctx.type_pointer(td.byval_type_index))
        need('same-exact-list-element:'+name,container['name']==closed
            and container.get('definition',{}).get('name')==LIST and container['classArguments']==[element]
            and bytes.fromhex(container['rawHex'])[10:12]==b'\x15\x00')
        selected[name]=dict(typeDefinition=td.index,closedListType=closed,closedCarrier=container,
            typedUsages=usages,callerRva=primary,completeCaller=full,selectedMacro=program)
        ctor_targets.add(program['actualConstructor']);register_targets.add(program['actualRegister'])
    need('one-actual-list-ctor-and-register',len(ctor_targets)==len(register_targets)==1)
    constructor,ctor_full=full_source(image,next(iter(ctor_targets)))
    registration,register_full=full_source(image,next(iter(register_targets)))
    cp=[programs.constructor(constructor['regions'],constructor['pointer'],cold=c)for c in(False,True)]
    rp=[programs.register_list(registration['regions'],registration['pointer'],cold_context=c)for c in(False,True)]
    actual=rp[0];same=scalar['registerPrograms'][0]
    for key in('providerClassCell','systemTypeClassCell','actualTypeFromHandle','actualClassContextSlotResolver','actualHashHelper','actualInsertion'):
        need('same-independent-registry-helper:'+key,actual[key]==same[key])
    setter=derive_typed_usage_context(image,actual['dictionaryMethodUsageInstruction']-base,label=LABEL)
    need('same-exact-closed-registry-setter',setter['methodSpec']==prior['actualClosedRegistrySetter']['methodSpec']
        and actual['actualInsertion']==prior['selectedEmptyInsertion']['entry'])
    return dict(nominals=selected,constructorMethod=[ctor.index,FORMATTER,'.ctor'],registerMethod=[register.index,PROVIDER,'Register'],
        constructorFamily=ctor_full,constructorPrograms=cp,registerFamily=register_full,registerPrograms=rp,
        actualClosedRegistrySetter=setter,registryRoundtripConditionalSourceProved=True)


def _derive_with_callbacks(image,pins,callbacks,*,enum_types=ENUM_TYPES,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import counted_loop_sources,int_list_sources,scalar_param_native as scalar,modelview_packable_sources
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
    from scripts.game_data.memorypack.skill_gait_dictionary_callbacks import dispatch_program
    from scripts.game_data.il2cpp import enum_method_pointer_selection as method_owner,enum_method_table_seed_paths as seed_owner,enum_inflated_method_class_paths as original_owner
    _publication_gate(image,pins);base=image.pe.image_base
    need('finite-explicit-enum-scope',type(enum_types)is tuple and 0<len(enum_types)<=32
        and all(type(n)is str and n for n in enum_types)and list(enum_types)==sorted(set(enum_types)))
    need('finite-count-limit',type(count_limit)is int and 0<count_limit<=10000)
    need('fresh-callback-source-scope',callbacks['nativeInputs']==pins
        and callbacks['status']=='validated-conditional-callback-sources'and all(n in callbacks['capabilities']for n in enum_types))
    registration=_registration(image,pins,callbacks,enum_types=enum_types)
    ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image);symbols=ContextSymbols(image)
    td=ctx.index.types[FORMATTER]
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    need('actual-list-slot5-ABI',not method.flags&16 and method.slot==5 and method.parameter_count==2 and ctx.type_name(method.return_type)=='void')
    _vtable(image,td.index,5,method.index,LABEL)
    selected=ge.resolve(method.index,['System.Int32Enum'],[])
    selection=_nodes(callbacks,method_owner.SCHEMA);seed=_nodes(callbacks,seed_owner.SCHEMA);original=_nodes(callbacks,original_owner.SCHEMA)
    rows=[r for r in selection['proof']['selectedPlaceholderRegistrations']if r['formatterType']==FORMATTER and r['methodDefinition']==method.index]
    need('same-independent-normalized-list-registration',len(rows)==1 and json.loads(json.dumps(rows[0]['selectedRegistration']))==json.loads(json.dumps(selected)))
    static=[r for r in seed['proof']['selectedStaticMethodRows']if r['methodDefinition']==method.index]
    need('same-selected-list-static-key-triple',len(static)==1 and static[0]['methodSpecIndex']==selected['methodSpecIndex']
        and static[0]['actualClassInstantiationPointer']==selected['classInstantiation']['record_va']and static[0]['actualMethodInstantiationPointer']is None)
    need('same-original-list-definition',any(r['methodDefinition']==method.index and r['declaringType']==td.index and r['parameterCount']==2
        for r in original['proof']['intendedPlaceholderDefinitions']))
    context=symbols.context(td.index);list_context=symbols.context(ctx.index.types[LIST].index)
    validate_generic_contexts(image,[context,list_context],label=LABEL)
    typed=validate_list_formatter_base_context(image,context,ge,fail=_fail)
    capacity_context=validate_capacity_constructor_context(image,context,list_context,ge,fail=_fail)
    slots={r['relativeSlot']:r for r in context['entries']};params=list(md.parameters_for(method))
    add_method=md.methods[slots[6]['methodSpec'][0]];add_params=list(md.parameters_for(add_method))
    clear_method=md.methods[slots[2]['methodSpec'][0]]
    need('own-instance-List-Add-Clear-ABIs',add_method.declaring_type==clear_method.declaring_type==ctx.index.types[LIST].index
        and not(add_method.flags|clear_method.flags)&16 and len(add_params)==1 and not md.parameters_for(clear_method)
        and ctx.type_name(add_method.return_type)==ctx.type_name(clear_method.return_type)=='void')
    add_formal=symbols.type(ctx.type_pointer(add_params[0].type_index));add_owner=add_formal.get('parameterOwner',{})
    need('Add-byvalue-owned-List-VAR0',bytes.fromhex(add_formal['rawHex'])[10:12]==b'\x13\x00'
        and add_owner.get('typeIndex')==ctx.index.types[LIST].index and add_owner.get('ordinal')==0)
    reader=pe_raw(image,ctx.type_pointer(params[0].type_index));out=pe_raw(image,ctx.type_pointer(params[1].type_index))
    container=pe_raw(image,ctx.type_pointer(slots[0]['index']))
    need('same-byref-Reader-and-list-output',reader[10:12]==b'\x11\x20'and ctx.type_name(params[0].type_index)=='MemoryPack.MemoryPackReader'
        and out[10:12]==b'\x15\x20'and container[10:12]==b'\x15\x00'and out[:8]==container[:8])
    body,full=full_source(image,selected['pointer']);r=body['rows']
    targets={name:_call(r,i)for name,i in [('header',13),('resolveClass',26),('allocate',28),('capacity',42),('barrier',45),
        ('elementProvider',52),('elementDispatch',74),('add',89)]}
    children={};families={}
    for name,target in targets.items():
        if name not in('resolveClass','allocate','barrier'):
            children[name],families[name]=full_source(image,target)
    offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    lp=[programs.list_program(body['regions'],body['pointer'],targets,count=n,new=new)for new in(False,True)for n in range(-1,4)]
    barrier=_barrier_source(image,targets['barrier'])
    induction=counted_loop_sources.prove_induction([p for p in lp if p['countWitness']>=0],initial='458bf4',increment='41ffc6',
        comparison='443bf6',counter='r14d',saved_count='ESI')
    header=programs.buffered_header(children['header']['regions'],targets['header'],offsets)
    add=programs.spare_add(children['add']['regions'],targets['add'])
    capacity=children['capacity'];cr=capacity['rows']
    capacity_calls={name:_call(cr,i)for name,i in [('resolveClass',30),('arrayAllocate',33)]}
    tail=control_transfer(cr[28]);need('actual-capacity-barrier-tail',tail['kind']=='jump'and tail['target']==targets['barrier'])
    capacity_calls['barrier']=targets['barrier']
    cp=[int_list_sources.capacity(capacity['regions'],capacity['pointer'],capacity_calls,positive=p)for p in(False,True)]
    provider=children['elementProvider'];pp=[programs.element_provider(provider['regions'],provider['pointer'],cold_context=c)for c in(False,True)]
    canonical=callbacks['proof']['nominalRegistrySource']['proof']['selectedGenericProvider']
    need('same-provider-original-context-and-registry-source',pp[1]['actualMethodContextInitializer']==canonical['actualMethodContextInitializer']
        and pp[0]['actualBackend']==canonical['actualBackend']and pp[0]['actualTypeFromHandle']==canonical['actualTypeFromHandle']
        and pp[0]['providerClassCell']==canonical['actualProviderClassCell']and pp[0]['systemTypeClassCell']==canonical['actualTypeClassCell'])
    provider_context=symbols.context(slots[3]['methodSpec'][0],is_method=True)
    need('same-independent-provider-formal-context',provider_context==callbacks['proof']['normalizationClassMethodAndContextSource']['proof']['staticMethodContext'])
    dispatch=children['elementDispatch'];prepare=_call(dispatch['rows'],8)
    callback_targets={callbacks['capabilities'][n]['callbackTargetRva']for n in enum_types}
    need('one-independently-selected-element-code-registration',len(callback_targets)==1)
    dp=dispatch_program(dispatch['regions'],dispatch['pointer'],offsets,prepare=prepare,callback=base+next(iter(callback_targets)),kind='enum')
    need('actual-dispatcher-compares-selected-enum-callback',dp['selectedPath']=='matched-inline-raw4'and dp['rawBytes']==4)
    # A List itself is a reference result. Authenticate its actual generic
    # ReadPackable source without borrowing any element/parent grammar.
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    generic=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('same-reviewed-reference-source-native-inputs',core['nativeInputs']==pins and generic['nativeInputs']==pins)
    routes=copy.deepcopy(generic['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    packable,=[m for m in md.methods_for(ctx.index.types['MemoryPack.MemoryPackReader'])
        if md.string(m.name_index)=='ReadPackable'and m.generic_container_index>=0 and m.parameter_count==0]
    caps={}
    for name in enum_types:
        enum=callbacks['capabilities'][name];nominal=registration['nominals'][name]
        need('same-element-nominal-source-definition:'+name,enum['typeName']==name and enum['typeDefinition']==nominal['typeDefinition']
            and enum['wireBytes']==4 and enum['callbackSlot']==5 and enum['readerByref']is True and enum['outputByref']is True)
        caps['skill-enum-list:'+name]=dict(schema=SCHEMA,status='validated-conditional-enum-list',nativeInputs=pins,
            closedListType=nominal['closedListType'],elementType=name,elementTypeDefinition=enum['typeDefinition'],
            packableReaderMethodDefinition=packable.index,packableReaderTargetRva=core['readPackable']['entryRva'],
            countLimit=count_limit,headerBytes=4,signedCountBits=32,nullCount=-1,collectionCounts=[-1,0],nullable=True,
            elementValueType=True,elementCapability='skill-enum-callback:'+name,
            positiveCountsAdmitted=True,elementGrammarAdmitted=True,elementWireBytes=4,rawBitsPreserved=True,
            elementCallback=enum,formatterMethodDefinition=method.index,formatterCallbackTargetRva=selected['pointer']-base,
            actualRuntimeSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
            conditions=['Original nominal ListFormatter and enum formatter are selected through the independently proved source paths; runtime replacement is absent.',
                'Original class/MethodInfo/closed contexts and source-selected interner/method-key tables are coherent and initialized.',
                'Count is -1 or0..'+str(count_limit)+'; sufficient disjoint buffered Reader/output/element storage and nonwrapping counters.',
                'New list allocation is zeroed with typed count-sized array; reused list Clear completes with sufficient spare array capacity.',
                'Actual helpers, registry hash/equality/lock/cleanup/casts, constructor and callbacks return normally and preserve the proved nonvolatile ABI; selected barriers have collector disabled.'],
            evidenceBoundary=dict(exact='Own nominal registration/contexts, selected static ListFormatter code and complete actual count/loop/provider/dispatcher/Add source.',
                conditional=__doc__,structuralOnly='Raw signed DWORD enum bits with exact nominal identity; declared enum-value membership is not inferred.',
                unresolved=['runtime provider/MethodInfo state and replacements','growth/refill/failure paths','enclosing parent and EOF']))
        caps['skill-enum-callback:'+name]=enum
    _publication_gate(image,pins)
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-nominal-enum-lists',nativeInputs=pins,capabilities=caps,
        proof=dict(enumCallbackSources=callbacks,nominalListRegistrations=registration,selectedListRegistration=selected,
            selectedStaticListMethodRow=static[0],formatterContext=context,listContext=list_context,typedContext=typed,capacityContext=capacity_context,
            addFormalParameter=add_formal,
            completeListFamily=full,listPrograms=lp,countInduction=induction,actualSymbolRvas={k:v-base for k,v in targets.items()},
            completeChildFamilies=families,headerProgram=header,addProgram=add,capacityPrograms=cp,
            elementProviderPrograms=pp,providerContext=provider_context,elementDispatchProgram=dp,referenceReaderSource=reference,
            actualDisabledBarrier=barrier),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Fresh finite nominal enum-list source composition.',conditional=__doc__,
            structuralOnly='Stored raw nominal enum values.',unresolved=['runtime state/replacements','parent/EOF'])),default=_json_set))


def pe_raw(image,pointer):return image.pe.bytes_at_va(pointer,16)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    profile=json.loads(CALLBACK_PROFILE.read_bytes());validate_profile(profile,pins)
    callbacks=_derive_on_profile(image,pins,profile)
    return _derive_with_callbacks(image,pins,callbacks)


def _bind_request(image,pins,source,*,typed_request,call_target,enum_type,enum_types=ENUM_TYPES,count_limit=10000):
    """Fresh actual parent identity only; source capability remains conditional."""
    from scripts.game_data.il2cpp.enum_nominal_requests import bind
    need('finite-list-nominal',type(enum_types)is tuple and enum_type in enum_types)
    need('finite-count-limit',type(count_limit)is int and 0<count_limit<=10000)
    need('same-fresh-source-result',source.get('schema')==SCHEMA
        and source.get('status')=='validated-conditional-nominal-enum-lists'and source.get('nativeInputs')==pins)
    cap=source['capabilities']['skill-enum-list:'+enum_type]
    need('exact-source-capability',cap.get('schema')==SCHEMA and cap.get('nativeInputs')==pins
        and cap.get('elementType')==enum_type and cap.get('closedListType')==LIST+'<'+enum_type+'>'
        and cap.get('elementCapability')=='skill-enum-callback:'+enum_type
        and cap.get('elementValueType')is True and cap.get('positiveCountsAdmitted')is True
        and cap.get('elementGrammarAdmitted')is True and cap.get('parentFieldAdmitted')is False
        and cap.get('nullable')is True and cap.get('rawBitsPreserved')is True
        and all(type(cap.get(k))is int and cap[k]==v for k,v in
            [('countLimit',count_limit),('headerBytes',4),('signedCountBits',32),('nullCount',-1),('elementWireBytes',4)])
        and cap.get('collectionCounts')==[-1,0]
        and type(cap.get('packableReaderMethodDefinition'))is int and cap['packableReaderMethodDefinition']>=0
        and type(cap.get('packableReaderTargetRva'))is int and 0<cap['packableReaderTargetRva']<1<<32
        and cap.get('elementCallback')==source['capabilities'].get(cap['elementCapability']))
    request=bind(image,enum_type,typed_request)
    need('actual-list-parent-role',request['role']=='read-packable-enum-list')
    need('actual-selected-ReadPackable-definition-and-target',type(call_target)is int
        and typed_request['methodSpec'][0]==cap['packableReaderMethodDefinition']
        and call_target==image.pe.image_base+cap['packableReaderTargetRva'])
    return dict(closedListType=cap['closedListType'],elementType=enum_type,
        packableReaderMethodDefinition=cap['packableReaderMethodDefinition'],
        packableReaderTargetRva=cap['packableReaderTargetRva'],sourceRequest=typed_request,
        nominalRequest=request,collectionCapability=cap,parentFieldAdmitted=False)


def bind_request(image,pins,source,*,typed_request,call_target,enum_type):
    """Default Skill list scope; opt-in domains bind through their own owner."""
    return _bind_request(image,pins,source,typed_request=typed_request,call_target=call_target,enum_type=enum_type)
