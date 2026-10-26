"""Closed numeric-list Param joins and selected UInt32/Single source programs.

Int32 keeps its independently reviewed list source. UInt32 authenticates its
own registered list/callback/context and count loop; a typed parent request
never substitutes for that child proof. Live provider selection stays conditional.
"""
from __future__ import annotations

import hashlib
import json

from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
from scripts.game_data.il2cpp.formatter_composition import _vtable, derive_typed_usage_context
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.nullable_cast_program import check_nullable_cast_program
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
from scripts.game_data.memorypack import (
    int_list_sources, npc_ai_sources, reference_param, scalar_param_native as scalar,
    utf8_source_helper,
)
from scripts.game_data.memorypack.list_formatter_base_context import validate_list_formatter_base_context
from scripts.game_data.memorypack.new_list_reference_sources import validate_capacity_constructor_context

LABEL = 'numericListParam'
ELEMENTS = {'int': ('Param<List<int>>', 8, '<i'), 'uint': ('Param<List<uint>>', 9, '<I'),
            'float': ('Param<List<float>>', 12, '<f')}
ENCODINGS = {'int': 'int32', 'uint': 'uint32', 'float': 'float32-bits'}
BOUNDARY = dict(
    direct='Exact closed MC4 reference-valued Param ownership, typed ReadPackable constant, two Int32 bindings, pooled path, allocation/null/registration/forwarding; independently authenticated exact closed numeric List source and four-byte element callback.',
    conditional='Coherent initialized selected closed parent/List/provider/formatter contexts and actual callback equal to the reviewed closed primitive formatter; stable disjoint sufficiently buffered source/reader/output/frame, ordinary compatible helpers and disabled collector. UInt32 and Single select fresh zeroed List with requested capacity=count, or a reused cleared List with capacity>=count; their loops and Add take only spare-capacity paths. Single preserves all four source bytes without numeric conversion. Live formatter/cache/override choice, cold failures/refill and allocation effects are not observed.',
    unresolved=['UInt32/Single growth or reused capacity below count', 'live provider/default/override/inflation selection',
                'cold malformed/refill/initialization paths', 'whole-owner execution'])


def need(check, expected, actual):
    scalar.need(LABEL, check, expected, actual)


def uint_list_program(regions, entry, symbols, *, count, new=True):
    """One exact unsigned-element loop, with explicit count and capacity conditions."""
    if type(count) is not int or not -1 <= count <= 3 or type(new) is not bool:
        raise ValueError(LABEL+'.uint-witness-domain')
    g = BytesPath(regions, entry)
    g.take('4053','56','57','4156','4883ec38'); flag=g.relative('803d');g.take('00','498bf1','498bd8','488bfa');g.branch('0f84',False)
    g.take('4533f6','488d542420','488bcf','4489742420','4489742468');g.call(symbols['header']);g.take('84c0');g.branch('75',count!=-1,1)
    provider_owner = None
    if count == -1:
        g.take('488bcb','4c8933');g.call(symbols['barrier'])
    else:
        g.take('4c896c2478','48896c2460','4c89642470','4c897c2430','448b6c2420','4c3933');g.branch('0f85',not new)
        if new:
            g.take('488b4e20','33d2','488b89c0000000');g.call(symbols['context']);g.take('488bc8');g.call(symbols['allocate']);g.take('488be8','4885c0');g.branch('75',True,1)
            g.take('488b4e20','488b91c0000000','488b4a08','4c397120');g.branch('0f84',False)
            g.take('488b4620','418bd5','488bcd','4c8b80c0000000','4d8b4008');g.call(symbols['constructor']);g.take('488bcb','48892b');g.call(symbols['barrier'])
        else:
            g.take('488b4620','488b2b','488b88c0000000','488b4110','4c397020');g.branch('75',True,1)
            g.take('ff451c','44897518');g.jump('e9')
        provider_owner=g.relative('488b0d');g.take('4439b1e0000000');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','488b4918');g.call(symbols['provider']);g.take('488be8','458bfe','4585ed');g.branch('7e',count==0,1)
        loop = g.at
        for index in range(max(count, 0)):
            need('uint-same-loop-entry',loop,g.at)
            g.take('4489742468','4885ed');g.branch('0f84',False)
            g.take('4c8d4c2468','4c8bc7','488bd5');g.call(symbols['dispatch'])
            g.take('4c8b33','448b642468','4d85f6');g.branch('0f84',False)
            g.take('488b4620','4c8b80c0000000','498b4030','4883782000');g.branch('0f84',False)
            g.take('488b4620','418bd4','498bce','4c8b80c0000000','4d8b4030');g.call(symbols['add'])
            g.take('41ffc7','41be00000000','453bfd');g.branch('7c',index+1<count,1)
        g.take('488b6c2460','4c8b642470','4c8b7c2430','4c8b6c2478');g.jump('e9')
    g.take('4883c438','415e','5f','5e','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,headerBytes=4,
                elementCallbacks=max(count,0),elementOutputFrameOffset=104,
                providerOwnerCell=provider_owner,initializedFlag=flag,normalFrameAndReturn=True,
                counter='R15D starts zero, increments once after Add; signed compare to saved R13D count; exact same back edge',
                condition='Nonnegative count and normal selected UInt32 child/Add; new zeroed List capacity=count or cleared reused List with capacity>=count. No growth path.')


def uint_formatter_program(regions, entry, offsets, advance):
    g=BytesPath(regions,entry);cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
    g.take('48895c2408','57','4883ec20','837a'+rem+'04','498bf8','488bda');g.branch('0f8c',False)
    g.take('488b42'+cur,'8b00','ba04000000','488bcb','8907','488b5c2430','4883c420','5f')
    need('uint-formatter-advance',advance,g.relative('e9'))
    return dict(selectedBytes=g.seen,wireBytes=4,preservedBits=32,reader='incoming RDX',output='incoming R8',normalReturnViaAdvance=True)


def uint_dispatch_program(regions, entry, offsets, *, prepare, callback, advance):
    g=BytesPath(regions,entry);cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
    g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2');g.call(prepare)
    g.take('488b06','4c8b9090010000','4c8b8898010000');need('uint-selected-callback',callback,g.relative('488d05'))
    g.take('4c3bd0');g.branch('0f85',False);g.take('837b'+rem+'04');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b00','ba04000000','488bcb','8907');g.call(advance)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,slot=5,callback=callback,wireBytes=4,preservedBits=32,
                reader='incoming R8',output='incoming R9',normalReturn=True,
                condition='Ready receiver callback equals independently registered/proved UInt32 formatter; ordinary preparation preserving aliases and sufficient disjoint buffer.')


def uint_capacity_program(regions, entry, symbols, *, positive):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
    if positive:
        g.take('ba01000000');g.call(symbols['context']);g.take('8bd3','488bc8');g.call(symbols['arrayAllocate'])
    else:
        g.take('33d2');g.call(symbols['context']);g.take('83b8e000000000');g.branch('75',True,1)
        g.take('488b4f20','33d2','488b89c0000000');g.call(symbols['context']);g.take('488b88b8000000','488b01');g.jump('eb',1)
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
    need('uint-capacity-barrier',symbols['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,positiveCapacity=positive,capacityBits=32,capacityPassedUnchanged=True,
                itemsSlot=16,countWrites=0,versionWrites=0,normalReturnViaBarrier=True,
                condition='Fresh zeroed exact List<uint> and normal typed initialized array allocation returning requested capacity, or typed static empty array for zero.')


def uint_actual_add_program(regions, entry):
    """Prove the actual anonymous called clone, without a pointer/name inference."""
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','ff411c','498bf0','4c8b4910','8bfa','48634118','488bd9','4d85c9');g.branch('74',False,1)
    g.take('413b4118');g.branch('73',False,1)
    g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
    g.take('4189548120','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,elementBits=32,arrayStride=4,countSlot=24,versionSlot=28,
                itemsSlot=16,arrayLengthSlot=24,arrayDataOffset=32,normalReturn=True,
                value='all incoming EDX bits preserved to typed array',
                condition='Nonnull typed List<uint>/array, nonnegative initial count strictly below capacity; no growth or helper call.')


def uint_backend_forward_program(regions,entry,target):
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d');g.take('00','488bd9');g.branch('74',False,1)
    owner=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('488bcb','4883c420','5b');need('uint-provider-backend-tail',target,g.relative('e9'))
    return dict(selectedBytes=g.seen,providerOwnerCell=owner,initializedFlag=flag,
                unchangedKey='Incoming RCX Type preserved in RBX and restored to RCX before frame-restored tail',
                normalTail=True,condition='Initialized metadata and ready formatter-provider class; shared independently proved Type-key backend.')


def _owned(image, pointer, *, leaf=False):
    base=image.pe.image_base
    if leaf:
        decoded=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(pointer,128),pointer)
        end=max(int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in decoded['rows'])
        ranges=[(pointer-base,end-base)]
    else:
        ranges=[part['runtimeTriple'][:2]for part in image.unwind_index.family(pointer-base)['ranges']]
    windows=[];regions=[];rows=[]
    for start,end in ranges:
        raw=image.pe.bytes_at_va(base+start,end-start);regions.append((base+start,raw))
        windows.append(dict(startRva=start,endRva=end,sha256=hashlib.sha256(raw).hexdigest().upper()))
        rows.extend(image.body_index._decode(base+start,end-start))
    return dict(pointer=pointer,windows=windows,regions=regions,rows=rows)


def _target(row):
    raw=bytes.fromhex(row['bytes'])
    if len(raw)!=5 or raw[0]!=0xe8:raise ValueError(LABEL+'.direct-call-required')
    return int(row['va'],16)+5+int.from_bytes(raw[1:],'little',signed=True)


def _call_after(body, previous):
    candidates={_target(row)for index,row in enumerate(body['rows'])
                if index and body['rows'][index-1]['text']==previous and len(bytes.fromhex(row['bytes']))==5 and bytes.fromhex(row['bytes'])[0]==0xe8}
    need('helper-unique.'+previous,1,len(candidates));return next(iter(candidates))


def _uint_child(image, pins, parent, int_fact):
    base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image);entries=GenericEntries(image)
    selected={role:entries.resolve(int_fact['bodies'][role]['methodDefinition'],['uint'],[])
              for role in('list','integer','capacity','Add','Clear')}
    for role,row in selected.items():
        raw=bytes.fromhex(row['classInstantiation']['arguments'][0]['raw_type_record_hex'])
        need('uint-closed-type.'+role,(9,128),(raw[10],raw[11]))
    bodies={role:_owned(image,row['pointer'],leaf=role=='Clear')for role,row in selected.items()}
    list_definition=md.methods[int_fact['bodies']['list']['methodDefinition']].declaring_type
    integer_definition=md.methods[int_fact['bodies']['integer']['methodDefinition']].declaring_type
    list_context=ContextSymbols(image).context(list_definition)
    fail=lambda check,expected,actual:need(check,expected,actual)
    base_context=validate_list_formatter_base_context(image,list_context,entries,fail=fail)
    class_context=ContextSymbols(image).context(md.methods[int_fact['bodies']['capacity']['methodDefinition']].declaring_type)
    capacity_context=validate_capacity_constructor_context(image,list_context,class_context,entries,fail=fail)
    slots={r['relativeSlot']:r for r in list_context['entries']}
    _vtable(image,list_definition,5,int_fact['bodies']['list']['methodDefinition'],LABEL)
    _vtable(image,integer_definition,5,int_fact['bodies']['integer']['methodDefinition'],LABEL)
    need('uint-reader-request',['System.Collections.Generic.List`1<uint>'],parent['typedRead']['methodArguments'])
    symbols={
        'header':_call_after(bodies['list'],'mov [rsp+0x68], r14d'),
        'barrier':_call_after(bodies['list'],'mov [rbx], r14'),
        'context':_call_after(bodies['list'],'mov rcx, [rcx+0xc0]'),
        'allocate':_call_after(bodies['list'],'mov rcx, rax'),
        'constructor':selected['capacity']['pointer'],
        'provider':_call_after(bodies['list'],'mov rcx, [rcx+0x18]'),
        'dispatch':_call_after(bodies['list'],'mov rdx, rbp'),
        'add':_call_after(bodies['list'],'mov r8, [r8+0x30]'),
        'arrayAllocate':base+int_fact['calls']['arrayAllocate'],
    }
    need('uint-context-helper',base+int_fact['calls']['resolveClass'],symbols['context'])
    need('uint-barrier-helper',base+int_fact['calls']['barrier'],symbols['barrier'])
    headers=utf8_source_helper._contract();need('header-inputs',pins,headers['nativeInputs'])
    need('uint-header-helper',base+headers['bodies']['header']['entryRva'],symbols['header'])
    header_proof=utf8_source_helper._validate_native(image,headers)
    offsets=scalar.reader_offsets(image,LABEL)
    need('uint-reader-offsets',int_fact['readerFields'],{**offsets,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16})
    programs=[uint_list_program(bodies['list']['regions'],bodies['list']['pointer'],symbols,count=-1)]
    programs.extend(uint_list_program(bodies['list']['regions'],bodies['list']['pointer'],symbols,count=count,new=new)
                    for new in(False,True)for count in range(4))
    # Same exact scalar element Add code, independently bound to List<uint>.
    growth=entries.resolve(int_fact['bodies']['growth']['methodDefinition'],['uint'],[])
    add_proof=int_list_sources.add(bodies['Add']['regions'],bodies['Add']['pointer'],growth=growth['pointer'])
    actual_add=_owned(image,symbols['add'])
    actual_add_proof=uint_actual_add_program(actual_add['regions'],actual_add['pointer'])
    need('uint-actual-canonical-add-effects',
         (add_proof['elementBits'],add_proof['arrayStride'],add_proof['countSlot'],add_proof['versionSlot']),
         (actual_add_proof['elementBits'],actual_add_proof['arrayStride'],actual_add_proof['countSlot'],actual_add_proof['versionSlot']))
    clear_proof=int_list_sources.clear(bodies['Clear']['regions'],bodies['Clear']['pointer'])
    capacity_proofs=[uint_capacity_program(bodies['capacity']['regions'],bodies['capacity']['pointer'],symbols,positive=p)for p in(False,True)]
    need('uint-add-raw-bits',(32,4),(add_proof['elementBits'],add_proof['arrayStride']))
    # Exact callback and cursor Advance; no signedness substitution.
    dispatch=_owned(image,symbols['dispatch']);advance=base+headers['bodies']['advance']['entryRva']
    callback=uint_formatter_program(bodies['integer']['regions'],bodies['integer']['pointer'],offsets,advance)
    dispatch_proof=uint_dispatch_program(dispatch['regions'],dispatch['pointer'],offsets,
        prepare=base+int_fact['calls']['prepare'],callback=selected['integer']['pointer'],advance=advance)
    # Typed GetFormatter<T> call/context and its normal matching-result path.
    provider_spec=slots[3]['methodSpec'];provider_entry=entries.resolve(provider_spec[0],[],['uint'])
    provider=_owned(image,symbols['provider'])
    provider_calls=[_target(row)for row in provider['rows']if len(bytes.fromhex(row['bytes']))==5 and bytes.fromhex(row['bytes'])[0]==0xe8][:4]
    need('provider-first-calls',4,len(provider_calls));ps=dict(zip(('typeFromHandle','backend','type','cast'),provider_calls))
    backend=_owned(image,ps['backend'])
    backend_forward=uint_backend_forward_program(backend['regions'],backend['pointer'],base+int_fact['calls']['backend'])
    need('provider-shared-context',symbols['context'],ps['type'])
    need('provider-type-handle',base+int_fact['calls']['typeFromHandle'],ps['typeFromHandle'])
    provider_proof=npc_ai_sources.value_provider(provider['regions'],provider['pointer'],ps)
    cast=_owned(image,ps['cast']);cast_proof=check_nullable_cast_program(cast['rows'],entry=cast['pointer'],
        owned_ranges=[(a,a+len(raw))for a,raw in cast['regions']])
    pc=ContextSymbols(image).context(provider_spec[0],is_method=True);pcs={r['relativeSlot']:r for r in pc['entries']}
    need('provider-context-slots',[0,1],sorted(pcs))
    provider_method=md.methods[provider_spec[0]]
    need('provider-static-zero-argument-abi',(True,0),(bool(provider_method.flags&16),provider_method.parameter_count))
    need('provider-declared-return-pointer',ctx.type_pointer(pcs[1]['index']),ctx.type_pointer(provider_method.return_type))
    for slot,arguments in((0,[pcs[0]['type']]),(1,pcs[1]['type']['classArguments'])):
        need('provider-owned-mvar.'+str(slot),[(pc['definition'],0)],[(v['parameterOwner']['methodIndex'],v['parameterOwner']['ordinal'])for v in arguments])
    need('provider-formatter-result','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
    usages=[]
    for body,cell,expected in((bodies['list'],programs[1]['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider'),
                             (provider,provider_proof['providerClassCell'],'System.Type'),
                             (provider,provider_proof['rootClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
                             (backend,backend_forward['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        candidates=[row for row in body['rows']if bytes.fromhex(row['bytes'])[:3]==b'\x48\x8b\x0d'
                    and int(row['va'],16)+7+int.from_bytes(bytes.fromhex(row['bytes'])[3:],'little',signed=True)==cell]
        need('uint-typed-class-cell.'+expected,1,len(candidates))
        usage=derive_typed_usage_context(image,int(candidates[0]['va'],16)-base,label=LABEL)
        need('uint-class-cell-type',(1,expected),(usage['tag'],usage['typeName']));usages.append(usage)
    for role,slot in(('capacity',1),('Clear',2),('Add',6)):
        need('uint-closed-method.'+role,slots[slot]['methodSpec'][0],int_fact['bodies'][role]['methodDefinition'])
        need('uint-no-method-arguments.'+role,-1,slots[slot]['methodSpec'][2])
    return dict(closedEntries=selected,listContext=list_context,typedBase=base_context,capacityContext=capacity_context,
                listClassContext=class_context,readerOffsets=offsets,
                windows={role:body['windows']for role,body in bodies.items()},
                helperWindows={role:body['windows']for role,body in(('dispatch',dispatch),('provider',provider),('cast',cast),('actualAdd',actual_add),('backendForward',backend))},
                symbolRvas={k:v-base for k,v in symbols.items()},headerProof=header_proof,
                listPrograms=programs,callback=callback,dispatch=dispatch_proof,constructor=capacity_proofs,
                add=add_proof,actualAdd=actual_add_proof,clear=clear_proof,providerEntry=provider_entry,providerContext=pc,classUsages=usages,
                provider=provider_proof,cast=cast_proof,backendForward=backend_forward,
                providerJoin=dict(actualBodyProvedIndependently=True,
                    registeredBodyEquivalenceClaimed=False,
                    methodInfo='Actual ListFormatter owned VAR slot3, declared static GetFormatter<VAR>; actual clone reads that MethodInfo own MVAR slot0 and expected formatter slot1.'),
                wireCountBytes=4,wireElementBytes=4,nullCount=-1,positiveCountAdmitted=True,
                positiveCondition='New capacity=count or reused cleared List with capacity>=count; selected UInt32 callback and ordinary helpers. Growth is not admitted or inferred.')


def derive(image, pins, component, int_fact):
    element=component['elementType']
    if element not in ELEMENTS:raise ValueError(LABEL+'.unsupported-element:'+str(element))
    codec=ELEMENTS[element][0];need('codec-kind',codec,component['codecKind'])
    value_type='System.Collections.Generic.List`1<'+element+'>'
    parent,ctx,owned,calls=reference_param.derive_reference_parameter(image,pins,component['profile'],value_type,reader_method='ReadPackable')
    need('parent-selected-value',[value_type],parent['typedRead']['methodArguments'])
    if element=='int':
        entries=GenericEntries(image)
        closed=entries.resolve(int_fact['bodies']['list']['methodDefinition'],['int'],[])
        need('int-selected-list-source',int_fact['bodies']['list']['entryRva'],closed['pointer']-image.pe.image_base)
        need('int-exact-registration',int_fact['bodies']['list']['registration'],json.loads(json.dumps(closed)))
        child=dict(sourceContract='levelscript_int_list_native.json',closedList=closed,
                   wireCountBytes=4,wireElementBytes=4,nullCount=-1,positiveCountAdmitted=True,
                   evidenceBoundary=int_fact['evidenceBoundary'])
    elif element=='uint':
        child=_uint_child(image,pins,parent,int_fact)
    else:
        from scripts.game_data.memorypack.float_list_sources import derive as derive_float
        child=derive_float(image,pins,parent,int_fact)
    return json.loads(json.dumps(dict(parent=parent,child=child,evidenceBoundary=BOUNDARY)))
