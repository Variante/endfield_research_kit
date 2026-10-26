"""Current closed LevelScript collection source components.

Parent field identity and element grammars are independent. Positive loops are
admitted only from a complete exact iteration and its authenticated backedge.
Provider choice, allocation effects and runtime inflation remain conditions.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def ulong_list_program(regions,entry,o,s,*,count):
    if type(count)is not int or count not in(-1,0,1):
        raise ValueError('levelscriptUlongList.count-profile')
    if set(o)!={'currentPtr','bufferLength','advancedCount','consumed','totalLength'}:
        raise ValueError('levelscriptUlongList.reader-fields')
    cur,rem,adv,used,total=(bytes((o[k],)).hex()for k in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry)
    g.take('4c89442418','53','55','57','4154','4155','4156','4883ec28',
        '4533ed','4d8be1','837a'+rem+'04','4d8bf0','488bda','4c896c2468')
    g.branch('0f8c',False)
    g.take('488b43'+cur,'8b28','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8')
    g.branch('0f8c',False);g.take('83fdff');g.branch('0f84',count==-1)
    callback=provider=None
    if count==-1:
        g.take('498bce','4d892e');g.call(s['barrier'])
        g.take('4883c428','415e','415d','415c','5f','5d','5b','c3')
    else:
        g.take('4889742460','4c897c2420','4d392e');g.branch('0f85',False)
        g.take('498b4c2420','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0')
        g.branch('0f84',False)
        g.take('498b4c2420','488b91c0000000','488b4a08','4c396920')
        g.branch('0f84',False);g.take('85ed');g.branch('0f88',False)
        g.take('498b442420','488b88c0000000','488b7108','488b4620','488b88c0000000')
        g.branch('0f84',count==0)
        if count:
            g.take('ba01000000');g.call(s['context'])
            g.take('488bd5','488bc8');g.call(s['arrayAllocate'])
        else:
            g.take('33d2');g.call(s['context']);g.take('4439a8e0000000')
            g.branch('74',False,1)
            g.take('488b4e20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488b88b8000000','488b01');g.jump('e9')
        g.take('488d4f10','48894710');g.call(s['barrier'])
        g.take('498bce','49893e');g.call(s['barrier'])
        provider=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
        g.take('498b442420','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf8','418bf5','85ed');g.branch('0f8e',count==0)
        if count:
            callback=g.relative('488d3d')
            if callback!=s['callback']:raise ValueError('levelscriptUlongList.selected-callback')
            loop=g.at
            g.take('4c896c2468','4d85ff');g.branch('0f84',False)
            g.take('498b0f');g.call(s['prepare'])
            g.take('498b07','4c8b9090010000','4c8b8898010000','4c3bd7')
            g.branch('0f85',False)
            g.take('837b'+rem+'08');g.branch('0f8c',False)
            g.take('488b43'+cur,'488b00','4889442468','8b7b'+rem,'83c7f8')
            g.branch('0f88',False)
            g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
                '498b3e','4c8b742468','4885ff');g.branch('0f84',False)
            g.take('498b442420','488b88c0000000','488b4130','4883782000')
            g.branch('0f84',False)
            g.take('498b442420','488b5710','488b88c0000000','4c8b6930',
                'ff471c','4885d2');g.branch('0f84',False)
            g.take('48634f18','3b4a18');g.branch('0f83',False)
            g.take('8d4101','894718','3b4a18');g.branch('0f83',False)
            g.take('4c8974ca20','4c8b742470')
            if g.relative('488d3d')!=callback:
                raise ValueError('levelscriptUlongList.same-callback')
            g.take('ffc6','41bd00000000','3bf5')
            if g.relative('0f8c')!=loop:
                raise ValueError('levelscriptUlongList.exact-loop-backedge')
        g.take('488b742460','4c8b7c2420','4883c428','415e','415d','415c','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,countProfile='null'if count==-1 else
        'zero'if count==0 else'all-positive-Int32',headerBytes=4,elementBytes=8,
        elementBitsPreserved=64,newOutput=True,callback=callback,providerClassCell=provider,
        normalReturn=True,countInvariant='EBP is immutable signed count; ESI starts0, increments exactly once after one raw64 read/store, and exact signed JL returns to the same loop head. Ordinary Win64 helpers preserve both. Fresh capacity=count prevents growth for all positive signed counts.',
        condition='Initialized coherent List<UInt64> contexts; initially null output; normal zeroed typed list/count-sized array allocation, shared context/provider/preparation/barrier ABI and callback equality to the independently proved closed UnmanagedFormatter<UInt64>; stable disjoint sufficient buffered bytes/counters, no wrapping or live-provider/default-selection claim.')


def ulong_formatter_program(regions,entry,o):
    cur,rem,adv,used=(bytes((o[k],)).hex()for k in
        ('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','837a'+rem+'08','498bf8','488bda')
    g.branch('0f8c',False)
    g.take('488b42'+cur,'488b00','488907','8b7b'+rem,'83c7f8')
    g.branch('0f88',False)
    g.take('488343'+cur+'08','8343'+adv+'08','8343'+used+'08','897b'+rem,
        '488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,resultBytes=8,rawBits=64,
        reader='incoming RDX',output='incoming R8',normalReturn=True)


def int_dictionary_induction(regions,entry,s,o):
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_i32_program
    witness=dictionary_i32_program(regions,entry,s,o,count=2,new=True)
    seen=witness['selectedBytes'];addresses=[a for a,_ in seen]
    repeated=[]
    for i,(at,raw)in enumerate(seen):
        if at in addresses[:i]:repeated.append((i,at,raw))
    if not repeated:raise ValueError('levelscriptIntDictionary.missing-repeated-loop')
    loop=repeated[0][1]
    branches=[]
    for i,(at,raw)in enumerate(seen[:-1]):
        if raw=='0f8c' and seen[i+1][0]==at+2:
            disp=bytes.fromhex(seen[i+1][1])
            if len(disp)==4 and at+6+int.from_bytes(disp,'little',signed=True)==loop:
                branches.append(at)
    if len(branches)!=2 or len(set(branches))!=1:
        raise ValueError('levelscriptIntDictionary.exact-loop-backedge')
    return dict(witness=witness,countProfile='all-positive-Int32',loopHead=loop,
        backedge=branches[0],keyWireBytes=4,valueRuntimeBytes=8,
        countInvariant='Saved signed count RSP+48 is unchanged; original counter RSP+64 starts0, restored to R15 before exactly one INC then saved back; exact signed JL returns to this same authenticated iteration. Strict body has no other counter/bound write, and ordinary calls preserve the frame. Fresh typed dictionary/count capacity and normal insert effects remain conditions.',
        elementGrammarAdmitted=False,parentFieldAdmitted=False)


def _repeat_backedge(program,label):
    seen=program['selectedBytes'];addresses=[a for a,_ in seen]
    repeated=[(i,a)for i,(a,_)in enumerate(seen)if a in addresses[:i]]
    if not repeated:raise ValueError(label+'.missing-repeated-iteration')
    loop=repeated[0][1];branches=[]
    for i,(at,raw)in enumerate(seen[:-1]):
        if raw not in('0f8c','7c'):continue
        width=4 if raw=='0f8c'else 1;size=len(bytes.fromhex(raw))
        following=seen[i+1]
        if following[0]!=at+size:continue
        disp=bytes.fromhex(following[1])
        if len(disp)==width and at+size+width+int.from_bytes(disp,'little',signed=True)==loop:
            branches.append(at)
    if len(branches)!=2 or len(set(branches))!=1:raise ValueError(label+'.exact-backedge')
    return dict(loopHead=loop,backedge=branches[0],witness=program,
        countProfile='all-positive-Int32',freshOutput=True)


def reference_list_induction(regions,entry,o,s):
    from scripts.game_data.memorypack.pooled_string_list_sources import list_source
    proof=_repeat_backedge(list_source(regions,entry,o,s,count=2,new=True,grow=False),
        'currentReferenceList')
    return dict(proof,headerBytes=4,elementRuntimeBytes=8,elementGrammarAdmitted=False,
        countInvariant='ESI starts0 and increments once after one zeroed-reference callback and unchanged reference store into fresh list backing array. Saved signed count RSP+104 is immutable and exact signed JL repeats this same body. Source-owned constructor(count) and normal initial size0/capacity=count prevent growth. Stable nonwrapping storage/counters and matching typed callbacks remain conditions.')


def int_list_induction(regions,entry,o,s):
    from scripts.game_data.memorypack.int_list_sources import source
    proof=_repeat_backedge(source(regions,entry,o,s,count=2,new=True,grow=False),'currentIntList')
    return dict(proof,headerBytes=4,elementWireBytes=4,elementRawBits=32,
        countInvariant='ESI starts0 and increments once after exactly one Int32 dispatcher read and same raw32 store into fresh list array. Saved signed count RSP+48 is immutable, with exact signed JL to this same body. Source-owned constructor(count) and initial size0/capacity=count prevent growth; ordinary callbacks and stable nonwrapping disjoint storage remain conditions.')


def _derive_ulong_list_source(image,pins):
    """Fresh closed list/element source, with no enclosing caller admission."""
    import copy
    import json
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar,modelview_packable_sources
    from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
    from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context
    from scripts.game_data.memorypack.pointer_param import owned
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image)
    def need(k,e,a):scalar.need('levelscriptUlongList',k,e,a)
    def load(name):
        fact=json.loads((CONTRACTS_DIR/name).read_bytes());need('dependency-build:'+name,pins,fact['nativeInputs']);return fact
    def select(owner):
        td=ctx.index.types[owner]
        method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
        entry=entries.resolve(method.index,['ulong'],[])
        raw=bytes.fromhex(entry['classInstantiation']['arguments'][0]['raw_type_record_hex'])
        need('exact-UInt64-primitive',(11,128),(raw[10],raw[11]))
        need('Deserialize-ABI',(False,5,2,'void'),
            (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
        _vtable(image,td.index,5,method.index,'levelscriptUlongList')
        return td,method,entry,owned(image,entry['pointer'])
    td,method,entry,body=select('MemoryPack.Formatters.ListFormatter`1')
    element_td,element_method,element_entry,element=select('MemoryPack.Formatters.UnmanagedFormatter`1')
    context=ContextSymbols(image).context(td.index)
    list_context=ContextSymbols(image).context(ctx.index.types['System.Collections.Generic.List`1'].index)
    typed=validate_list_formatter_base_context(image,context,entries,fail=need)
    capacity=validate_capacity_constructor_context(image,context,list_context,entries,fail=need)
    def after(text):
        i=next(i for i,r in enumerate(body['rows'])if r['text']==text)
        return next(control_transfer(r)['target']for r in body['rows'][i+1:]
            if control_transfer(r)['kind']=='call')
    symbols=dict(context=after('mov rcx, [rcx+0xc0]'),allocate=after('mov rcx, rax'),
        barrier=after('mov [rdi+0x10], rax'),arrayAllocate=after('mov rdx, rbp'),
        provider=after('mov rcx, [rcx+0x18]'),prepare=after('mov rcx, [r15]'),
        callback=element_entry['pointer'])
    offsets=scalar.reader_offsets(image,'levelscriptUlongList')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[ulong_list_program(body['regions'],body['pointer'],offsets,symbols,count=n)for n in(-1,0,1)]
    formatter=ulong_formatter_program(element['regions'],element['pointer'],offsets)
    declared='System.Collections.Generic.List`1<ulong>'
    core=load('npc_runtime_native.json')['readPackable']
    generic=load('leveldata_npc_patrol_native.json')['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core,routes)
    return dict(typeName=declared,listEntry=entry,elementEntry=element_entry,listWindows=body['windows'],
        elementWindows=element['windows'],listContext=context,capacityContext=capacity,
        typedContext=typed,referenceSource=reference,programs=programs,formatter=formatter,
        symbolRvas={k:v-base for k,v in symbols.items()},readerFields=offsets,
        counts='all-signed-nonnegative-or-minus1',parserCountLimit=16384,
        headerBytes=4,elementWireBytes=8,elementRawKind=11,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False),core


def derive_ulong_list(image,pins,owner_proof):
    """Authenticate the original exact four root/Brief parents, unchanged."""
    import json
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    fact,core=_derive_ulong_list_source(image,pins);base=image.pe.image_base
    need=lambda k,e,a:scalar.need('levelscriptUlongList',k,e,a)
    parents=[];declared=fact['typeName']
    # Fresh actual source requests, not field names or a copied registration.
    for original,owner in owner_proof['owners'].items():
        usages={u['instructionRva']:u for u in owner['typedUsages']}
        for field,read in zip(owner['fields'],owner['program']['orderedReads'],strict=True):
            if field['typeName']!=declared:continue
            usage=usages[read['typedUsage']['instruction']-base]
            validate_typed_usage_context(image,usage,label='levelscriptUlongList.parent')
            need('parent-typed-request',('ReadPackable',[declared]),(usage['methodName'],usage['methodArguments']))
            need('actual-reference-source',base+core['entryRva'],read['sourceTarget'])
            arg,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
            closed=ContextSymbols(image).type(arg.type_pointer_va)
            child,=closed['classArguments'];raw=bytes.fromhex(child['rawHex'])
            need('closed-parent-UInt64-kind',(11,128),(raw[10],raw[11]))
            parents.append(dict(owner=original,field=field,read=read,typedRequest=usage,closedCarrier=closed))
    need('exact-four-current-parents',4,len(parents))
    return json.loads(json.dumps(dict(parents=parents,**fact)))


def derive_ulong_list_component(image,pins,*,typed_request,call_target,count_limit=4096):
    """Caller-agnostic fresh UInt64 list; no field or whole-owner admission.

    The original four-parent owner is never accepted as a witness here. This
    independently authenticates the actual typed caller and reference-result
    source, closed UInt64 list/formatter registrations, raw64 element callback,
    allocation/context and complete null/zero/positive list programs.
    """
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    need=lambda k,e,a:scalar.need('levelscriptUlongListComponent',k,e,a)
    need('literal-bounded-count',True,type(count_limit)is int and 0<=count_limit<=16384)
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-actual-call-target',True,type(call_target)is int and call_target>base)
    declared='System.Collections.Generic.List`1<ulong>'
    validate_typed_usage_context(image,typed_request,label='levelscriptUlongListComponent.parent')
    binding=bind_typed_read(image,typed_request,method_name='ReadPackable',argument=declared,kind=21,reference=True)
    closed=ContextSymbols(image).type(binding['argumentPointer'])
    raw=bytes.fromhex(closed['rawHex']);ctx=NativeReferenceContext(image)
    need('ordinary-reference-list-carrier',bytes.fromhex('1500'),raw[10:12])
    need('exact-owned-list-definition',ctx.index.types['System.Collections.Generic.List`1'].index,
        int.from_bytes(bytes.fromhex(closed['definition']['rawHex'])[:8],'little'))
    need('one-closed-element',1,len(closed['classArguments']))
    child,=closed['classArguments'];element=bytes.fromhex(child['rawHex'])
    need('exact-ordinary-UInt64-element',('ulong',bytes.fromhex('0b80')),(child['name'],element[10:12]))
    fact,core=_derive_ulong_list_source(image,pins)
    need('exact-actual-reference-source',base+core['entryRva'],call_target)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.levelscript-uint64-list-component.v1',
        status='validated-conditional-uint64-list-component',nativeInputs=pins,typeName=declared,
        elementType='ulong',typedRequest=typed_request,typedBinding=binding,closedCarrier=closed,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        countLimit=count_limit,countRange=[-1,count_limit],nullable=True,positiveCountsAdmitted=True,
        headerBytes=4,elementWireBytes=8,elementRawBits=64,rawBitsPreserved=True,
        initiallyNullOutputRequired=True,actualCallbackEqualsProvedChildRequired=True,
        runtimeProviderSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=fact,evidenceBoundary=__doc__+' Matching ready UInt64/list contexts and callback, initially null output, normal allocation/provider/helper effects and sufficient disjoint nonwrapping buffered bytes are required.')))
