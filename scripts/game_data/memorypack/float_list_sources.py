"""Selected current Single-list programs; no integer-to-float grammar inference.

The callback, inlined read, local/XMM transfer and actual list stores are
independently proved for the exact closed Single context. New lists request
capacity=count; reused lists require enough spare capacity after Clear. Growth,
runtime callback selection and cold source/allocation paths remain separate.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.context import type_parameter_owner
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
from scripts.game_data.memorypack import int_list_sources
from scripts.game_data.memorypack import scalar_param_native as scalar
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context


def need(key,expected,actual):
    if expected!=actual:raise ValueError('floatList.'+key+':expected='+str(expected)[:300]+':actual='+str(actual)[:300])


def list_program(regions,entry,offsets,s,*,count,new=True):
    if type(count)is not int or not -1<=count<=3 or type(new)is not bool:raise ValueError('floatList.witness-domain')
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry)
    g.take('4053','55','57','4154','4157','4883ec30','837a'+rem+'04','4d8bf9','4d8be0','c744246800000000','488bda');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b28','8b7b'+rem,'83c7fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False)
    g.take('4889742460','33f6','83fdff');g.branch('0f84',count==-1)
    provider=None;loop=None;callback_matches=[]
    if count==-1:
        g.take('498bcc','49893424');g.call(s['barrier']);g.take('488b742460')
    else:
        g.take('4c896c2470','4c89742478','0f29742420','49393424');g.branch('0f85',not new)
        if new:
            g.take('498b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488bc8');g.call(s['allocate'])
            g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('498b4f20','488b91c0000000','488b4a08','48397120');g.branch('0f84',False)
            g.take('85ed');g.branch('0f88',False)
            g.take('498b4720','488b88c0000000','4c8b7108','498b4620','488b88c0000000');g.branch('0f84',count==0)
            if count:
                g.take('ba01000000');g.call(s['context']);g.take('488bd5','488bc8');g.call(s['arrayAllocate'])
            else:
                g.take('33d2');g.call(s['context']);g.take('39b0e0000000');g.branch('74',False,1)
                g.take('498b4e20','33d2','488b89c0000000');g.call(s['context'])
                g.take('488b88b8000000','488b01');g.jump('e9')
            g.take('488d4f10','48894710');g.call(s['barrier']);g.take('498bcc','49893c24');g.call(s['barrier'])
        else:
            g.take('498b4720','498b3c24','488b88c0000000','488b4110','48397020');g.branch('75',True,1)
            g.take('ff471c','897718');g.jump('e9')
        provider=g.relative('488b0d');g.take('39b1e0000000');g.branch('0f84',False)
        g.take('498b4720','488b88c0000000','488b4918');g.call(s['provider']);g.take('4c8bf0','85ed');g.branch('0f8e',count==0)
        if count:
            callback_matches.append(g.relative('488d3d'));need('selected-callback',s['callback'],callback_matches[-1])
            g.take('660f1f840000000000');loop=g.at
        for index in range(max(count,0)):
            need('same-loop-entry',loop,g.at)
            g.take('c744246800000000','4d85f6');g.branch('0f84',False)
            g.take('498b0e');g.call(s['prepare']);g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
            g.take('837b'+rem+'04');g.branch('0f8c',False)
            g.take('488b43'+cur,'f30f1000','f30f11442468','8b7b'+rem,'83c7fc');g.branch('0f88',False)
            g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','897b'+rem,
                '498b3c24','f30f10742468','4885ff');g.branch('0f84',False)
            g.take('498b4720','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
            g.take('498b4720','488b5710','488b88c0000000','4c8b6930','ff471c','4885d2');g.branch('0f84',False)
            g.take('48634f18','3b4a18');g.branch('0f83',False)
            g.take('8d4101','894718','3b4a18');g.branch('0f83',False)
            g.take('f30f11748a20','ffc6');callback_matches.append(g.relative('488d3d'))
            need('same-selected-callback',s['callback'],callback_matches[-1]);g.take('3bf5');g.branch('0f8c',index+1<count)
        g.take('4c8b742478','4c8b6c2470','0f28742420','488b742460')
    g.take('4883c430','415f','415c','5f','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,wireCountBytes=4,wireElementBytes=4,
        elementOutputStackOffset=104,selectedCallback=s['callback'],providerOwnerCell=provider,
        elementReads=max(count,0),elementStoreBits=32,arrayStride=4,
        counter='ESI starts zero before count branch, increments once after each successful store, signed compares saved EBP count and returns to the exact same loop entry; bounded nonnegative count prevents Int32 overflow.',
        valueTransfer='Raw four-byte source MOVSS -> local RSP+104 -> XMM6 -> typed array element; no arithmetic or conversion.',
        xmm6Restored=count!=-1,normalFrameAndReturn=True,
        condition='Initialized coherent exact closed Single List/constructor/provider/Add contexts; matching actual callback, sufficient disjoint buffered source/Reader/output/frame; new zeroed List requested capacity=count or cleared reused List capacity>=count, no growth. Normal helpers/barriers and ready class predicates.')


def callback_program(regions,entry,offsets):
    # This is an exact raw DWORD source program. Its interpretation as Single
    # comes only from the independently selected closed formatter and ABI.
    result=int_list_sources.integer(regions,entry,offsets)
    return dict(**result,elementType='float',numericConversion=False,
        boundary='Exact independently registered Single callback preserves all32 source bits, including signed zero and nonfinite payloads; no Int32 callback identity is inferred.')


def add_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec30','ff411c','498bf8','4c8b4910','488bd9','48635118',
        '0f29742420','0f28f1','4d85c9');g.branch('75',True,1)
    g.take('413b5118');g.branch('72',True,1)
    g.take('8d4201','894118','413b5118');g.branch('72',True,1)
    g.take('f3410f11749120','488b5c2440','0f28742420','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,elementType='float',elementBits=32,arrayStride=4,arrayDataOffset=32,
        itemsSlot=16,countSlot=24,versionSlot=28,value='Complete incoming XMM1 low32 copied through XMM6 to the selected float array slot.',
        restoredNonvolatiles=['rbx','rdi','xmm6'],normalReturn=True,
        condition='Exact closed List<float>, nonnull typed array, initial nonnegative count below capacity and normal compatible ABI. Growth is excluded.')


def capacity_program(regions,entry,s,*,positive):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
    if positive:
        g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
    else:
        g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('74',False,1)
        g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('eb',1)
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
    need('capacity-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,positiveCapacity=positive,capacityBits=32,requestedCapacityUnchanged=True,
        itemsSlot=16,countWrites=0,versionWrites=0,normalReturnViaBarrier=True,
        condition='Exact closed Float List constructor, nonnegative capacity, coherent initialized List/element array contexts, typed fresh zeroed allocation or ready static empty array and normal class/array/barrier helpers.')


def provider_program(regions,entry,s):
    """Actual Single GetFormatter clone: guarded unchanged backend reference."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_class=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['typeFromHandle']);provider_class=g.relative('488b0d')
    g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');g.call(s['backend']);g.take('488b4f38','ba01000000','488bd8');g.call(s['type'])
    g.take('4885db');g.branch('0f84',False)
    g.take('488b0b','488bd0');g.call(s['assignable']);g.take('84c0');g.branch('0f84',False)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,providerClassCell=type_class,rootClassCell=provider_class,
        typeofContextSlot=0,formatterContextSlot=1,nonnullBackendResult=True,backendReferenceReturnedUnchanged=True,
        normalReturn=True,condition='Ready coherent owned GetFormatter MVAR context and Type/provider classes; normal TypeFromHandle/backend/indexed context returns; the independently selected compatibility helper accepts actual backend class against the owned expected formatter class. No live/default provider choice is proved.')


def _method_abis(image,ctx,definitions,context):
    """Fresh open declarations plus reciprocal VAR ownership for closed sources."""
    result={};reader=ctx.index.types['MemoryPack.MemoryPackReader'].index
    containers=[t.generic_container_index for t in image.metadata.types]
    for role in('list','callback','capacity','Add','Clear'):
        method=image.metadata.methods[definitions[role]];parameters=list(image.metadata.parameters_for(method))
        arity=2 if role in('list','callback')else 0 if role=='Clear'else 1
        need(role+'.instance-void-arity',(False,'void',arity),
            (bool(method.flags&16),ctx.type_name(method.return_type),len(parameters)))
        scalar.ordinary(image,ctx.type_pointer(method.return_type),1,'floatList.'+role+'.return')
        if role in('list','callback'):
            _vtable(image,method.declaring_type,5,method.index,'floatList')
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
            need(role+'.reader-byref',(b'\x11\x20',reader),(raw[10:12],int.from_bytes(raw[:8],'little')))
        if role in('callback','Add'):
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[-1].type_index),16)
            need(role+'.owned-var-kind',b'\x13'+bytes((32 if role=='callback'else 0,)),raw[10:12])
            owner=type_parameter_owner(image.metadata.buf,int.from_bytes(raw[:8],'little'),containers,source='floatList')
            need(role+'.owned-var',(method.declaring_type,0),(owner['typeIndex'],owner['ordinal']))
        elif role=='list':
            selected=image.pe.bytes_at_va(ctx.type_pointer(context['entries'][0]['index']),16)
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
            need('list.exact-owned-output',(b'\x15\x20',selected[:8]),(raw[10:12],raw[:8]))
        elif role=='capacity':
            raw=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
            need('capacity.signed-int32',('int',b'\x08\x80'),(ctx.type_name(parameters[0].type_index),raw[10:12]))
        result[role]=dict(methodDefinition=method.index,declaringType=method.declaring_type,instance=True,parameters=arity)
    return result


def derive(image,pins,parent,int_fact):
    """Derive the exact current closed float child; caller gates shared dependencies."""
    from scripts.game_data.memorypack.numeric_list_sources import (
        _owned,_target,_call_after,uint_backend_forward_program)
    need('dependency-build',pins,int_fact['nativeInputs'])
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image)
    definitions={role:int_fact['bodies'][('integer'if role=='callback'else role)]['methodDefinition']
        for role in('list','callback','capacity','Add','Clear')}
    selected={role:entries.resolve(definition,['float'],[])for role,definition in definitions.items()}
    for role,row in selected.items():
        arg,=row['classInstantiation']['arguments'];raw=bytes.fromhex(arg['raw_type_record_hex'])
        need('closed-single.'+role,b'\x0c\x80',raw[10:12])
    bodies={role:_owned(image,row['pointer'],leaf=role=='Clear')for role,row in selected.items()}
    context=ContextSymbols(image).context(md.methods[definitions['list']].declaring_type)
    list_context=ContextSymbols(image).context(md.methods[definitions['capacity']].declaring_type)
    base_proof=validate_list_formatter_base_context(image,context,entries,fail=need)
    capacity_context=validate_capacity_constructor_context(image,context,list_context,entries,fail=need)
    abi=_method_abis(image,ctx,definitions,context)
    need('typed-parent-request',['System.Collections.Generic.List`1<float>'],parent['typedRead']['methodArguments'])
    rows=bodies['list']['rows']
    allocations=[_target(r)for i,r in enumerate(rows)if i>1 and rows[i-1]['text']=='mov rcx, rax'
        and rows[i-2]['text'].startswith('call 0x')and len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
    need('one-normal-list-allocation',1,len(set(allocations)))
    s=dict(context=_call_after(bodies['list'],'mov rcx, [rcx+0xc0]'),allocate=allocations[0],
        barrier=_call_after(bodies['list'],'mov [r12], rdi'),provider=_call_after(bodies['list'],'mov rcx, [rcx+0x18]'),
        prepare=_call_after(bodies['list'],'mov rcx, [r14]'),arrayAllocate=base+int_fact['calls']['arrayAllocate'],callback=selected['callback']['pointer'])
    for role,key in(('context','resolveClass'),('barrier','barrier'),('prepare','prepare')):
        need('exact-shared-helper.'+role,base+int_fact['calls'][key],s[role])
    offsets=scalar.reader_offsets(image,'floatList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    need('current-reader-offsets',int_fact['readerFields'],offsets)
    programs=[list_program(bodies['list']['regions'],bodies['list']['pointer'],offsets,s,count=-1)]
    programs.extend(list_program(bodies['list']['regions'],bodies['list']['pointer'],offsets,s,count=count,new=new)
        for new in(False,True)for count in range(4))
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    induction=prove_induction(programs,initial='33f6',increment='ffc6',comparison='3bf5',
        counter='esi',saved_count='EBP holds the signed collection header word, preserved nonvolatile through children.')
    callback=callback_program(bodies['callback']['regions'],bodies['callback']['pointer'],offsets)
    add=add_program(bodies['Add']['regions'],bodies['Add']['pointer'])
    clear=int_list_sources.clear(bodies['Clear']['regions'],bodies['Clear']['pointer'])
    constructors=[capacity_program(bodies['capacity']['regions'],bodies['capacity']['pointer'],s,positive=positive)for positive in(False,True)]
    slots={r['relativeSlot']:r for r in context['entries']}
    for role,slot in(('capacity',1),('Clear',2),('Add',6)):
        need('closed-method-definition.'+role,definitions[role],slots[slot]['methodSpec'][0])
    provider_entry=entries.resolve(slots[3]['methodSpec'][0],[],['float'])
    provider=_owned(image,s['provider'])
    provider_calls=[_target(r)for r in provider['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8][:4]
    need('provider-call-count',4,len(provider_calls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),provider_calls))
    provider_proof=provider_program(provider['regions'],provider['pointer'],ps)
    backend=_owned(image,ps['backend']);backend_proof=uint_backend_forward_program(backend['regions'],backend['pointer'],base+int_fact['calls']['backend'])
    need('provider-current-type-handle',base+int_fact['calls']['typeFromHandle'],ps['typeFromHandle'])
    need('provider-current-indexed-context',s['context'],ps['type'])
    need('provider-current-compatible-helper',base+int_fact['calls']['assignable'],ps['assignable'])
    pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True);pcs={r['relativeSlot']:r for r in pc['entries']}
    need('provider-owned-slots',[0,1],sorted(pcs))
    provider_method=md.methods[pc['definition']]
    need('provider-static-no-arguments',(True,0),(bool(provider_method.flags&16),provider_method.parameter_count))
    need('provider-return-context',ctx.type_pointer(provider_method.return_type),ctx.type_pointer(pcs[1]['index']))
    for ordinal,args in((0,[pcs[0]['type']]),(1,pcs[1]['type']['classArguments'])):
        need('provider-owned-mvar.'+str(ordinal),[(pc['definition'],0)],[(a['parameterOwner']['methodIndex'],a['parameterOwner']['ordinal'])for a in args])
    need('provider-result-formatter','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
    usages=[]
    for body,cell,name in((bodies['list'],programs[1]['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (provider,provider_proof['providerClassCell'],'System.Type'),(provider,provider_proof['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (backend,backend_proof['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        candidates=[r for r in body['rows']if bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d' and
            int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        need('typed-class-cell.'+name,1,len(candidates))
        usage=derive_typed_usage_context(image,int(candidates[0]['va'],16)-base,label='floatList')
        need('typed-class-owner',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
    return json.loads(json.dumps(dict(closedEntries=selected,methodAbis=abi,listContext=context,listClassContext=list_context,
        typedBase=base_proof,capacityContext=capacity_context,readerOffsets=offsets,
        windows={role:b['windows']for role,b in bodies.items()},symbolRvas={k:v-base for k,v in s.items()},listPrograms=programs,countInduction=induction,
        callback=callback,add=add,clear=clear,constructor=constructors,providerEntry=provider_entry,providerContext=pc,
        provider=provider_proof,compatibilityHelperRva=ps['assignable']-base,backendForward=backend_proof,classUsages=usages,
        helperWindows={role:b['windows']for role,b in(('provider',provider),('backendForward',backend))},
        wireCountBytes=4,wireElementBytes=4,nullCount=-1,positiveCountAdmitted=True,numericConversion=False,
        providerJoin=dict(actualBodyProvedIndependently=True,registeredBodyEquivalenceClaimed=False,
            methodInfo='Actual ListFormatter owned VAR slot3 and static GetFormatter<VAR>; selected clone uses its own MVAR slot0 and expected MemoryPackFormatter<MVAR> slot1.'),
        positiveCondition='Initialized coherent exact closed float contexts and actual callback equal to the independently registered Single formatter. Fresh zeroed list requested capacity=count or reused cleared list capacity>=count, stable buffered disjoint storage and normal helper effects. No growth/refill/live-provider selection.')))
