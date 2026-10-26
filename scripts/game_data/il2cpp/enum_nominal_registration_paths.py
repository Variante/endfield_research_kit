"""Exact nominal enum eager-registration transfers, without callback admission.

An installed nominal UnmanagedFormatter<T> allocation, its own closed constructor
MethodInfo and Register<T> MethodInfo are three separate typed requests. The
selected source must pass the same newly allocated reference through the actual
constructor and registration call. A tail registration additionally restores its
actual caller frame before transferring control. Whole owned caller/callee
partitions and normal control flow are retained independently of the selected
successful macro. Execution of that caller, metadata initialization and normal
allocation/constructor/helper effects remain explicit conditions.

The ordinary formatter constructor obtains its base constructor from its own
class RGCTX. Register obtains T from its own method RGCTX, converts that carrier
to System.Type and supplies that Type and the unchanged formatter reference to
the actual dictionary insertion source. Neither a MethodSpec nor this argument
transfer establishes successful publication, startup order, later cache lookup,
the receiver's actual slot5, or nominal callback wire semantics. In particular,
the IsEnum reflection fallback's DangerousUnmanagedFormatter is a different
nominal class and must not replace this ordinary eager-registration proof.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-nominal-registration-paths.v1'
LABEL='enumNominalRegistrationPaths'
FORMATTER='MemoryPack.Formatters.UnmanagedFormatter`1'
PROVIDER='MemoryPack.MemoryPackFormatterProvider'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def source_rows(rows):
    """Attach independently decoded complete immediate-store effects only."""
    from scripts.game_data.il2cpp.integer_effects import decode_immediate_memory_store
    from scripts.game_data.il2cpp.initializer_instructions import decode_initializer_byte_store
    result=[]
    for row in rows:
        raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
        parsed=decode_immediate_memory_store(raw,0,at)or decode_initializer_byte_store(raw,0,at)
        if parsed:
            own,end=parsed;spelling=own['text'].replace('mov qword [','mov [').replace('mov dword [','mov [').replace('mov byte [','mov [')
            spellings={own['text'],spelling};address=own['immediateMemoryStoreOperation']['destinationAddress']
            if address['ripRelative']:
                displacement=address['displacement'];suffix=('+'+hex(displacement))if displacement>=0 else('-'+hex(-displacement))
                spellings.update(v.replace('[rip =>','[rip'+suffix+' =>')for v in tuple(spellings))
            need('whole-immediate-store-bytes-and-text',end==len(raw)and row['text']in spellings)
            row=dict(row,text=own['text'],immediateMemoryStoreOperation=own['immediateMemoryStoreOperation'])
        result.append(row)
    return result


def macro_program(regions,entry):
    g=BytesPath(regions,entry);allocation_site=g.at;allocation_type=g.relative('488b0d');allocate=g.relative('e8')
    g.take('488bd8','4885c0');branch=g.read(1)
    if branch==b'\x74':failure=g.relative('',1)
    elif branch==b'\x0f':failure=g.relative('84')
    else:raise ValueError(LABEL+'.allocation-null-branch')
    need('actual-owned-allocation-failure',failure in g.bytes)
    ctor_site=g.at;ctor=g.relative('488b15');g.take('488bc8');ctor_target=g.relative('e8')
    register_site=g.at;register=g.relative('488b15');g.take('488bcb')
    tail=g.bytes.get(g.at)==0x48
    if tail:g.take('4883c420','5b');target=g.relative('e9')
    else:target=g.relative('e8')
    return dict(selectedBytes=g.seen,entry=entry,end=g.at,allocationUsageInstruction=allocation_site,
        allocationTypeCell=allocation_type,actualAllocator=allocate,actualNullFailure=failure,
        constructorUsageInstruction=ctor_site,constructorMethodInfoCell=ctor,actualConstructor=ctor_target,
        registerUsageInstruction=register_site,registerMethodInfoCell=register,actualRegister=target,
        sameAllocatedReferencePreservedInRbx=True,constructorRcX='unchanged actual allocation RAX',
        registerRcX='unchanged actual allocation preserved in RBX',nonnullAllocationRequired=True,
        constructorNormalReturnRequired=True,tailRegister=tail,
        callerEntryRspRestoredBeforeTail=tail,callerSavedRbxRestoredBeforeTail=tail,
        callerExecutionOrRegistrationPublicationProved=False)


def constructor_program(regions,entry,*,cold):
    need('literal-constructor-path',type(cold)is bool);g=BytesPath(regions,entry)
    g.take('4883ec28','488b4220','488b88c0000000','488b01','4883782000');g.branch('0f84',cold)
    if cold:
        g.take('488b4220','488b88c0000000','488b01','ff10','90');g.jump('e9')
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,entry=entry,cold=cold,methodInfoClassOffset=32,classRgctxOffset=192,
        baseConstructorContextSlot=0,actualBaseConstructorIndirectCall=cold,receiverUnchanged=True,
        noInstanceStoresOnSelectedPath=True,baseConstructorNormalEffectsRequired=cold,
        entryRspRestored=True,normalReturn=True)


def register_program(regions,entry,*,cold_context=False):
    need('literal-register-context-path',type(cold_context)is bool);g=BytesPath(regions,entry)
    g.take('4053','57','4156','4883ec40','48837a3800','488bda','4c8bf1');g.branch('0f84',cold_context)
    metadata_cells=[];metadata=None;initializer=None
    if cold_context:
        for _ in range(3):
            metadata_cells.append(g.relative('488d0d'));target=g.relative('e8')
            need('same-register-metadata-initializer',metadata in(None,target));metadata=target
        g.take('48837b3800');g.branch('0f85',False);g.take('488bcb');initializer=g.relative('e8');g.jump('e9')
    provider=g.relative('488b3d');g.take('83bfe000000000');g.branch('0f84',False)
    system_type=g.relative('488b0d');g.take('488bbfb8000000','488b5b38','83b9e000000000','488b7f18','488b1b')
    g.branch('0f84',False);g.take('33d2','488bcb');handle=g.relative('e8');g.take('488bd8','4885ff');g.branch('0f84',False)
    g.take('48896c2468');dictionary_method=g.relative('488b2d');g.take('48c744246000000000','4885c0');g.branch('0f84',False)
    g.take('4889742470','488b7718','4885f6');g.branch('0f84',False)
    g.take('488b4d20','ba0c000000','488b89c0000000');context_slot=g.relative('e8')
    g.take('488bd0','b901000000','4c8bcb','4c8bc6');hashing=g.relative('e8')
    g.take('488b4d20','8bf0','488b91c0000000','488b4a78','4883792000');g.branch('0f84',False)
    g.take('488b4d20','4d8bce','448bc6','488b91c0000000','488bcf','488b4278','488bd3',
        '4889442438','488d442460','4889442430','c644242801','c644242001')
    insertion=g.relative('e8');g.take('488b742470','488b6c2468','4883c440','415e','5f','5b','c3')
    return dict(selectedBytes=g.seen,entry=entry,coldContext=cold_context,metadataUsageCells=metadata_cells,
        actualMetadataInitializer=metadata,actualMethodContextInitializer=initializer,
        providerClassCell=provider,systemTypeClassCell=system_type,actualTypeFromHandle=handle,
        closedDictionaryMethodInfoCell=dictionary_method,actualClassContextSlotResolver=context_slot,
        actualHashHelper=hashing,actualInsertion=insertion,
        methodInfoContextOffset=56,nominalCarrierMethodContextSlot=0,
        registryStaticFieldsOffset=184,registryDictionaryFieldOffset=24,dictionaryTablesFieldOffset=24,
        dictionaryHashContextSlot=12,dictionaryInsertionContextSlot=15,
        insertionArguments=dict(rcx='actual provider staticFields.registry dictionary',
            rdx='actual System.Type converted from unchanged Register<T> method context slot0',
            r8d='actual hash helper result',r9='unchanged incoming formatter reference',
            stack32=True,stack40=True,stack48='address of owned zero-initialized output reference',
            stack56='actual closed dictionary context slot15 MethodInfo'),
        initializedProviderSystemTypeAndDictionaryContextsRequired=True,nonnullDictionaryTypeAndTablesRequired=True,
        sameIncomingFormatterReferencePassedUnchanged=True,normalInsertionReturnRequired=True,
        entryRspRestored=True,normalReturn=True,nonvolatilesRestored=['rbx','rdi','r14','rbp','rsi'],
        insertionOrSubsequentLookupSemanticsProved=False)


def _read(image,pointer):
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    body=owned(image,pointer);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));return body,source_rows(rows)


def _full(image,pointer,*,tail_targets=()):
    from scripts.game_data.il2cpp.consumer_entry_program import ordinary_consumer_entry
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.owned_partition import check_byte_partition
    body,rows=_read(image,pointer)
    if not tail_targets:
        from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
        graph,padding=complete_program(body['regions'],rows,pointer)
        return body,rows,dict(windows=body['windows'],control=graph,padding=padding)
    ranges=[(at,at+len(raw))for at,raw in body['regions']]
    pieces=[(int(r['va'],16),int(r['va'],16)+len(bytes.fromhex(r['bytes'])),'instruction')for r in rows]
    check_byte_partition(ranges,pieces,LABEL);tails={}
    for row in rows:
        if bytes.fromhex(row['bytes'])[:1]!=b'\xe9':continue
        flow=control_transfer(row)
        # Other terminal registrar transfers are retained as their exact own
        # external E9/frame obligations, without naming/admitting their helper.
        if flow['kind']=='jump'and not any(a<=flow['target']<b for a,b in ranges):
            tails[int(row['va'],16)]=dict(target=flow['target'])
    need('bounded-actual-caller-tail-exits',len(tails)<=16)
    graph=ordinary_consumer_entry(rows,entry=pointer,owned_ranges=ranges,tail_exits=tails)
    return body,rows,dict(windows=body['windows'],entryProgram=graph)


def _select_nominal_transfers(image,pins,*,enum_types):
    """Own exact typed caller transfers; callee bodies are separate obligations."""
    import struct
    from bisect import bisect_right
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.native_cell_references import selected_qword_reference_candidates
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    _publication_gate(image,pins);names=tuple(enum_types)
    need('bounded-explicit-unique-nominals',0<len(names)<=32 and len(set(names))==len(names)
        and all(type(n)is str and n for n in names))
    ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image);pe=image.pe;base=pe.image_base
    td=ctx.index.types[FORMATTER];provider=ctx.index.types[PROVIDER]
    ctor_methods=[m for m in md.methods_for(td)if md.string(m.name_index)=='.ctor']
    register_methods=[m for m in md.methods_for(provider)if md.string(m.name_index)=='Register'and m.generic_container_index>=0]
    need('one-actual-constructor-and-register-definition',len(ctor_methods)==len(register_methods)==1)
    ctor,=ctor_methods;register,=register_methods;specs={}
    need('constructor-instance-noarg-void-and-register-static-onearg-void',
        not ctor.flags&16 and not md.parameters_for(ctor)and ctx.type_name(ctor.return_type)=='void'
        and register.flags&16 and len(md.parameters_for(register))==1 and ctx.type_name(register.return_type)=='void')
    for i,(method,ci,mi)in enumerate(ge.specs):
        if method not in(ctor.index,register.index):continue
        cn,_=ge.arguments(ci);mn,_=ge.arguments(mi)
        if method==ctor.index and cn in[[n]for n in names]and not mn:specs[i]=(cn[0],'constructor')
        if method==register.index and mn in[[n]for n in names]and not cn:specs[i]=(mn[0],'register')
    need('exact-two-own-methodspecs-per-nominal',len(specs)==2*len(names)
        and all(sorted(role for n,role in specs.values()if n==name)==['constructor','register']for name in names))
    words={(6<<29)|(i<<1)|1:i for i in specs};cells={}
    for section in pe.sections:
        if section['characteristics']&0x20000000:continue
        raw=pe.buf[section['rawPointer']:section['rawPointer']+section['rawSize']]
        for off in range((-section['virtualAddress'])%8,len(raw)-7,8):
            value=struct.unpack_from('<Q',raw,off)[0]
            if value in words:cells[section['virtualAddress']+off]=words[value]
    candidates=selected_qword_reference_candidates(pe,set(cells));starts=sorted(image.unwind_index.entries)
    choices={n:[]for n in names};cache={}
    for candidate in candidates:
        spec=cells[candidate['cellRva']];name,role=specs[spec]
        if candidate['kind']!='load'or role!='constructor':continue
        at=candidate['siteRva'];i=bisect_right(starts,at)-1
        need('usage-owned-unwind-range',i>=0 and starts[i]<=at<image.unwind_index.entries[starts[i]][1])
        primary=image.unwind_index.resolve(starts[i])
        # Large unrelated registrars are not needed when an independently owned
        # bounded caller exists. This is source selection, never wire admission.
        family=image.unwind_index.family(primary)
        if sum(p['runtimeTriple'][1]-p['runtimeTriple'][0]for p in family['ranges'])>4096:continue
        if primary not in cache:cache[primary]=_read(image,base+primary)
        body,rows=cache[primary];by={int(r['va'],16):i for i,r in enumerate(rows)}
        need('actual-constructor-instruction-boundary',base+at in by);index=by[base+at]
        need('actual-allocation-prefix-precedes-constructor',index>=5)
        start=int(rows[index-5]['va'],16);program=macro_program(body['regions'],start)
        need('same-exact-candidate-constructor-site',program['constructorUsageInstruction']==base+at)
        choices[name].append((len(rows),primary,program))
    selected={};ctor_targets=set();register_targets=set()
    for name in sorted(names):
        need('bounded-owned-macro-for-'+name,bool(choices[name]));_,primary,program=min(choices[name],key=lambda v:(v[0],v[1]))
        _,_,full=_full(image,base+primary,tail_targets=(program['actualRegister'],))
        usages={role:derive_typed_usage_context(image,program[key]-base,label=LABEL)for role,key in
            [('allocation','allocationUsageInstruction'),('constructor','constructorUsageInstruction'),('register','registerUsageInstruction')]}
        allocation,construct,reg=[usages[r]for r in('allocation','constructor','register')]
        need('actual-closed-allocation-'+name,allocation['tag']==1 and allocation['typeName']==FORMATTER+'<'+name+'>'
            and bytes.fromhex(allocation['typeRawHex'])[10:12]==b'\x15\x00')
        need('actual-own-closed-constructor-'+name,construct['tag']==6 and construct['methodSpec'][0]==ctor.index
            and construct['typeName']==FORMATTER and construct['methodName']=='.ctor'
            and construct['classArguments']==[name]and construct['methodArguments']==[])
        need('actual-own-closed-register-'+name,reg['tag']==6 and reg['methodSpec'][0]==register.index
            and reg['typeName']==PROVIDER and reg['methodName']=='Register'
            and reg['classArguments']==[]and reg['methodArguments']==[name])
        enum=ctx.index.types[name];raw=pe.bytes_at_va(ctx.type_pointer(enum.byval_type_index),16)
        need('actual-nominal-enum-definition-'+name,ctx.is_enum(name)and raw[10:12]==b'\x11\x80'
            and int.from_bytes(raw[:8],'little')==enum.index)
        selected[name]=dict(typeDefinition=enum.index,nominalRawHex=raw.hex().upper(),callerRva=primary,
            completeCaller=full,typedUsages=usages,selectedMacro=program)
        ctor_targets.add(program['actualConstructor']);register_targets.add(program['actualRegister'])
    need('same-actual-constructor-and-register-bodies',len(ctor_targets)==len(register_targets)==1)
    return selected,ctor.index,register.index,next(iter(ctor_targets)),next(iter(register_targets))


def derive(image,pins,*,enum_types):
    """Fresh exact nominal source discovery; grants no provider/callback grammar."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    selected,ctor_index,register_index,ctor_target,register_target=_select_nominal_transfers(image,pins,enum_types=enum_types)
    ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types[FORMATTER]
    ctor=md.methods[ctor_index];register=md.methods[register_index]
    cb,cr,cf=_full(image,ctor_target);rb,rr,rf=_full(image,register_target)
    constructors=[constructor_program(cb['regions'],cb['pointer'],cold=c)for c in(False,True)]
    registrations=[register_program(rb['regions'],rb['pointer'],cold_context=c)for c in(False,True)]
    symbols=ContextSymbols(image);context=symbols.context(register.index,is_method=True)
    need('one-register-own-MVAR-context',context['count']==1 and context['entries'][0]['kind']==1)
    variable=context['entries'][0]['type'];owner=variable.get('parameterOwner',{})
    need('register-MVAR-is-own-ordinal-zero',bytes.fromhex(variable['rawHex'])[10:12]==b'\x1e\x00'
        and owner.get('methodIndex')==register.index and owner.get('ordinal')==0)
    parameter,=md.parameters_for(register);formal=symbols.type(ctx.type_pointer(parameter.type_index))
    need('register-formal-formatter-of-own-MVAR',formal.get('definition',{}).get('name')=='MemoryPack.MemoryPackFormatter`1'
        and formal.get('classArguments')==[variable]and bytes.fromhex(formal['rawHex'])[10:12]==b'\x15\x00')
    class_context=symbols.context(td.index,is_method=False)
    need('own-formatter-class-base-ctor-and-base-class-context',class_context['count']==2
        and[e['kind']for e in class_context['entries']]==[3,2])
    base_ctor,base_class=class_context['entries'];args=base_ctor.get('classArguments',[])
    need('own-formatter-base-ctor-VAR0',base_ctor['typeName']=='MemoryPack.MemoryPackFormatter`1'
        and base_ctor['methodName']=='.ctor'and base_ctor['methodArguments']==[]and len(args)==1
        and bytes.fromhex(args[0]['rawHex'])[10:12]==b'\x13\x00'
        and args[0].get('parameterOwner',{}).get('typeIndex')==td.index
        and args[0]['parameterOwner']['ordinal']==0)
    need('same-owned-base-class-context-VAR',base_class['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1'
        and base_class['type']['classArguments']==args)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(nominals=selected,constructorMethod=[ctor.index,FORMATTER,'.ctor'],
            registerMethod=[register.index,PROVIDER,'Register'],constructorFamily=cf,constructorPrograms=constructors,
            registerFamily=rf,registerPrograms=registrations,registerMethodContext=context,
            registerFormalParameter=formal,constructorClassContext=class_context),
        nominalAllocationConstructorAndRegisterTransfersProved=True,
        dictionaryPublicationOrCallbackSelectionProved=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Fresh nominal MethodSpecs/allocation type, full bounded selected caller families and actual constructor/Register families with exact successful transfers.',
            conditional=__doc__,structuralOnly='Typed eager-registration source distinct from reflection fallback.',
            unresolved=['actual registry insertion and initialized lookup/cache state','actual nominal receiver slot5 and MethodInfo',
                'caller execution/startup order','enum/list/parent/EOF'])),default=_json_set))
