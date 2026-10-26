"""Actual Int32 and Boolean bulk sources, with independent closed contexts.

These are two finite programs, not a width-selected array formatter. The
Int32 caller inlines its Dangerous context; the Boolean caller explicitly
tails the matching Dangerous method. Actual helper bodies and MethodInfo
flows are proved without equating code clones to registered entry pointers.
Only buffered counts -1..64 are covered. No enclosing field is admitted.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import npc_array_sources as arrays

LABEL = 'moduleUnmanagedArray'
LIMIT = 64
_EXTRA_MEMBERS={
    ('Beyond.Gameplay.View.Animation.CharacterSpecialDashEntry',1,'performSpDashIndexes','int[]'),
    ('Beyond.Gameplay.View.Animation.SpecialIdleEntry',2,'performSpIdleIndexes','int[]'),
}


def owns_member(owner,index,name,declared):
    return(owner=='Beyond.Gameplay.RunePuzzleData'and declared in('int[]','bool[]'))or(owner,index,name,declared)in _EXTRA_MEMBERS


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL+'.'+check+':'+str(detail)[:800])


def boolean_forwarder(regions, entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','48837a3800','488bda','488bf9')
    g.branch('75',True,1)
    g.take('488b5338','488bcf','488b12','488b5c2430','4883c420','5f')
    target=g.relative('e9')
    return dict(selectedBytes=g.seen,dangerousTargetVa=target,contextSlot=0,
        sameReaderRcx=True,exactNestedMethodInfoRdx=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],normalReturnByTailRequired=True)


def boolean_program(regions,entry,offsets,s,*,count):
    need('bounded-Boolean-count',type(count)is int and -1<=count<=LIMIT)
    g=BytesPath(regions,entry)
    cur,rem=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength'))
    g.take('48895c2408','48896c2418','4889742420','57','4883ec20',
           '48837a3800','488bf2','488be9')
    g.branch('75',True,1)
    g.take('488d542438','c744243800000000','488bcd')
    g.call(s['header'])
    g.take('84c0')
    g.branch('74',count==-1,1)
    if count==-1:
        g.take('33c0')
    else:
        g.take('8b7c2438','85ff')
        g.branch('74',count==0,1)
        if count==0:
            g.take('488b4e38','488b09')
            g.call(s['empty'])
            g.jump('eb',1)
        else:
            g.take('3b7d'+rem)
            g.branch('7e',True,1)
            g.take('4c8b4638','33d2','8bcf','4d8b4008')
            g.call(s['allocate'])
            g.take('488b5638','488bc8','488bd8','488b5210')
            g.call(s['dataReference'])
            g.take('488b55'+cur,'4c8bc7','488bc8')
            g.call(s['copy'])
            g.take('8bd7','488bcd')
            g.call(s['advance'])
            g.take('488bc3')
            g.jump('eb',1)
    g.take('488b5c2430','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,elementWireBytes=1,
        byteCount='same nonnegative signed count in EDI/RDI',payloadBytes=max(0,count),
        allocationCountPassedUnchanged=count>0,rawStoredBooleanBitsPreserved=True,
        booleanNormalizationClaimed=False,resultRegister='rax',sameReaderCounters=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi'],normalReturn=True)


def boolean_allocate(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','4983783800','498bd8','8bf9')
    g.branch('75',True,1)
    g.take('488b4b38','488b09')
    g.call(s['classData'])
    g.take('488bd7','488bc8','488b5c2430','4883c420','5f')
    need('actual-normal-typed-allocation-tail',g.relative('e9')==s['arrayAllocate'])
    return dict(selectedBytes=g.seen,arrayContextSlot=0,countPassedUnchanged=True,
        normalReturnByTailRequired=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'])


def boolean_data_reference(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec30','48837a3800','488bda','488bf9')
    g.branch('75',True,1)
    g.take('4c8b4338','488d4c2420','488bd7','4d8b00')
    g.call(s['asSpan'])
    g.take('488b5338','488d4c2420','0f28442420','660f7f442420','488b5208')
    g.call(s['getReference'])
    g.take('488b5c2440','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,source='whole same typed hidden Span16 local',
        localDisplacement=32,contextSlots=[0,1],entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],normalReturn=True)


def boolean_as_span(regions,entry,s):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','4983783800',
           '498bd8','488bf2','488bf9')
    g.branch('75',True,1)
    g.take('0f57c0','488bd6','0f1107','4c8b4338','488bcf','4d8b4008')
    g.call(s['spanConstructor'])
    g.take('488b5c2430','488bc7','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,sameHiddenOutputRcxReturned=True,sameArrayPassedRdx=True,
        constructorContextSlot=1,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],normalReturn=True)


def boolean_get_reference(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4883ec38','48837a3800','0f2801','660f7f442420')
    g.branch('75',True,1)
    g.take('488b442420','4883c438','c3')
    return dict(selectedBytes=g.seen,result='same incoming Span first QWORD',
        entryRspRestored=True,allNonvolatilesUnchanged=True,normalReturn=True)


def boolean_span_constructor(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20')
    ready=g.relative('803d')
    g.take('00','488bda','488bf9')
    g.branch('75',True,1)
    g.take('4885db')
    g.branch('74',False,1)
    g.take('488d4320','488907','8b4318','894708')
    g.jump('eb',1)
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedMetadataFlag=ready,
        arrayDataOffset=32,arrayLengthOffset=24,spanPointerOffset=0,spanLengthOffset=8,
        exactSameNonNullArrayRequired=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rdi'],normalReturn=True)


def empty_program(regions,entry,s,*,element_type):
    """Same slot-zero byte algorithm; the actual typed context stays separate."""
    need('two-exact-empty-context-elements',element_type in('int','bool'))
    proof=arrays.int_empty(regions,entry,s)
    if element_type=='bool':
        proof['condition']='Ready exact typed Empty<bool> context and initialized EmptyArray<bool> class; matching static array exists. Empty object identity and runtime initialization remain conditional.'
    return proof


def int32_program(regions,entry,offsets,s,*,count):
    """Reuse the exact Int32 instruction lemma; positive paths do not unroll."""
    need('bounded-Int32-count',type(count)is int and -1<=count<=LIMIT)
    witness=min(count,1)
    parsed=arrays.int_array(regions,entry,offsets,s,count=witness)
    need('same-positive-dynamic-four-byte-program',parsed['elementBytes']==4 and parsed['normalReturn']is True)
    return dict(program=parsed,countWitness=witness,countLimit=LIMIT,
        headerBytes=4,elementWireBytes=4,byteCount='ESI = 4 * nonnegative EDI count',
        boundedMultiplicationNoOverflow=True,maximumCopyBytes=LIMIT*4,
        countSpecificLoopUnrolled=False,positiveBranchIndependentOfCount=True,
        rawBitsPreserved=True,normalReturn=True)


def bind_member(source,context,event,setter,pins,*,owner):
    """Finite declared field/actual E8 join; the caller owns frame/store VM."""
    need('explicit-Rune-or-Extra-primitive-array-member',owns_member(owner,event.get('memberIndex'),event.get('fieldName'),event.get('declaredType'))
         and event.get('kind')=='reference:'+event['declaredType'])
    element=event['declaredType'][:-2];kind=8 if element=='int'else 2
    need('fresh-own-complete-array-source',source.get('schema')=='endfield.module-unmanaged-array-source.v1'
         and source.get('status')=='validated-conditional-source'and source.get('nativeInputs')==pins
         and source.get('typeName')==event['declaredType']and source.get('elementType')==element
         and source.get('targetRva')==event.get('sourceTargetRva')
         and source.get('resultRegister')=='rax'and source.get('completeBufferedSourceProved')is True
         and source.get('entryRspRestored')is True and source.get('allNonvolatilesRestored')is True
         and source.get('parentFieldAdmitted')is False and source.get('wholeOwnerAdmitted')is False
         and source.get('elementCallbackUsed')is False and source.get('booleanNormalizationClaimed')is False
         and type(source.get('countLimit'))is int and 0<=source['countLimit']<=LIMIT)
    need('actual-independent-primitive-array-context',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
         and context.get('methodName')=='ReadUnmanagedArray'and context.get('register')=='rdx'
         and context.get('fullTypeName')==element and context.get('typeKind')==kind
         and bytes.fromhex(context.get('argumentRawHex',''))[10:12]==bytes((kind,128))
         and isinstance(context.get('methodSpec'),list)and len(context['methodSpec'])==3
         and context['methodSpec'][0]==source.get('readerMethodDefinition'))
    proof=source.get('proof',{});request=proof.get('context',{}).get('typedRequest',{})
    need('same-fresh-actual-MethodSpec-and-call',request.get('methodSpec')==context['methodSpec']
         and request.get('instructionRva')==context.get('instructionRva')
         and bytes.fromhex(request.get('instructionHex',''))==bytes.fromhex(context.get('instructionHex',''))
         and proof.get('actualCall',{}).get('sourceInstruction')==event.get('instruction'))
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('own-exact-SZARRAY-setter-element-pointer',len(raw)==16 and raw[10:12]==bytes((29,0))
         and setter.get('storedBytes')==8 and setter.get('member',{}).get('declaredType')==event['declaredType']
         and setter['member'].get('name')==event.get('fieldName')
         and int.from_bytes(raw[:8],'little')==proof.get('context',{}).get('concreteElementPointer'))
    return dict(typeName=event['declaredType'],elementType=element,readMethod='ReadUnmanagedArray',
        readerMethodDefinition=source['readerMethodDefinition'],sourceTargetRva=source['targetRva'],
        countLimit=source['countLimit'],sourceOnly=True,positiveGrammarAdmitted=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def _span_context(image,context):
    """Own AsSpan<T>, GetReference<T> and the closed Span<T> constructor."""
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    md=image.metadata;ctx=NativeReferenceContext(image);symbols=ContextSymbols(image)
    data=context['contexts'][4]
    rows=[symbols.context(r['methodSpec'][0],is_method=True)for r in data['entries']]
    validate_generic_contexts(image,rows,label=LABEL+'.span')
    section=md.sections['genericContainers'];containers=[m.generic_container_index for m in md.methods]
    def owner(row,name):
        method=md.methods[row['definition']];at=section.offset+method.generic_container_index*16
        need('bounded-owned-span-MVAR',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
        own,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
        param=method_parameter_owner(md.buf,start,containers,source=LABEL)
        need('reciprocal-span-MVAR',(own,count,is_method,param['methodIndex'],param['ordinal'])==(method.index,1,1,method.index,0))
        need('static-onearg-span-helper',bool(method.flags&16)and method.parameter_count==1 and md.string(method.name_index)==name)
        return method,start
    def variable(pointer,var,kind=30):
        raw=image.pe.bytes_at_va(pointer,16)
        need('exact-owned-span-type-parameter',raw[10:12]==bytes((kind,0))and int.from_bytes(raw[:8],'little')==var)
    aspan,av=owner(rows[0],'AsSpan');getref,gv=owner(rows[1],'GetReference')
    need('actual-span-helper-owner-types',(image.type_name(aspan.declaring_type),image.type_name(getref.declaring_type))==
        ('System.MemoryExtensions','System.Runtime.InteropServices.MemoryMarshal'))
    argument,=md.parameters_for(aspan);raw=image.pe.bytes_at_va(ctx.type_pointer(argument.type_index),16)
    need('AsSpan-owned-array-parameter',raw[10:12]==bytes((29,0)))
    variable(int.from_bytes(raw[:8],'little'),av)
    def span_type(index,var,byref=False):
        raw=image.pe.bytes_at_va(ctx.type_pointer(index),16)
        need('owned-constructed-Span',raw[10:12]==bytes((21,160 if byref else 128)))
        definition,inst=struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
        dr=image.pe.bytes_at_va(definition,16)
        td=ctx.index.types['System.Span`1']
        need('exact-Span-value-definition',dr[10:12]==bytes((17,128))and int.from_bytes(dr[:8],'little')==td.index)
        args=image.instantiations.resolve_pointer(inst).arguments
        need('sole-Span-owned-type-argument',len(args)==1)
        variable(args[0].type_pointer_va,var)
    span_type(aspan.return_type,av)
    p,=md.parameters_for(getref);span_type(p.type_index,gv)
    returned=image.pe.bytes_at_va(ctx.type_pointer(getref.return_type),16)
    need('GetReference-own-MVAR-byref-return',returned[10:12]==bytes((30,32))and int.from_bytes(returned[:8],'little')==gv)
    entries=rows[0]['entries']
    need('AsSpan-exact-constructor-context',len(entries)==2 and entries[1]['relativeSlot']==1
         and entries[1]['kind']==3 and entries[1]['typeName']=='System.Span`1'and entries[1]['methodName']=='.ctor')
    spec=entries[1]['methodSpec'];args=image.instantiations.resolve(spec[1]).arguments
    need('closed-Span-constructor-sole-class-argument',len(args)==1 and spec[2]==-1)
    variable(args[0].type_pointer_va,av)
    td=ctx.index.types['System.Span`1'];ctor=md.methods[spec[0]]
    at=section.offset+td.generic_container_index*16
    own,count,ismethod,sv=struct.unpack_from('<iiii',md.buf,at)
    need('owned-Span-constructor-ABI',(own,count,ismethod)==(td.index,1,0)
         and ctor.declaring_type==td.index and not ctor.flags&16 and ctor.parameter_count==1
         and ctx.type_name(ctor.return_type)=='void')
    p,=md.parameters_for(ctor);raw=image.pe.bytes_at_va(ctx.type_pointer(p.type_index),16)
    need('Span-constructor-array-parameter',raw[10:12]==bytes((29,0)))
    variable(int.from_bytes(raw[:8],'little'),sv,19)
    return dict(contexts=rows,spanConstructorDefinition=ctor.index,
        ownArrayParameterAndSpanResultProved=True,runtimeContextSelectionObserved=False)


def derive(image,pins,*,typed_request,call_target,source_instruction,element_type,count_limit=LIMIT):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_unmanaged_array_context import derive_int32,derive_boolean
    from scripts.game_data.memorypack.unmanaged_enum_member_sources import bind_actual_call
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memory_copy_bounded_native import validate_components as copy_source
    _publication_gate(image,pins)
    need('two-explicit-primitive-domains',element_type in('int','bool')and type(count_limit)is int and 0<=count_limit<=LIMIT)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    context=(derive_int32 if element_type=='int'else derive_boolean)(image,typed_request)
    call=bind_actual_call(typed_request,source_instruction,source_target=call_target,base=base)
    image.check_instruction_windows([source_instruction],label=LABEL+'.parentE8')
    entry=GenericEntries(image).resolve(typed_request['methodSpec'][0],[],[element_type])
    need('same-exact-actual-MethodSpec',entry['methodSpecIndex']==typed_request['methodSpecIndex'])
    caller=owned(image,call_target)
    def target(body,offset):
        rows=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        need('one-owned-actual-E8',len(rows)==1 and len(bytes.fromhex(rows[0]['bytes']))==5 and bytes.fromhex(rows[0]['bytes'])[0]==232,(body['pointer']-base,offset))
        return control_transfer(rows[0])['target']
    forwarder=None
    if element_type=='bool':
        forwarder=boolean_forwarder(caller['regions'],call_target)
        danger=GenericEntries(image).resolve(context['contexts'][1]['definition'],[],['bool'])
        need('actual-closed-Boolean-Dangerous-tail',danger['pointer']==forwarder['dangerousTargetVa'])
        body=owned(image,forwarder['dangerousTargetVa'])
        s={k:target(body,o)for k,o in dict(header=57,allocate=104,dataReference=123,copy=138,advance=148,empty=165).items()}
        programs=[boolean_program(body['regions'],body['pointer'],scalar.reader_offsets(image,LABEL),s,count=n)for n in(-1,0,1)]
    else:
        body=caller
        s={k:target(body,o)for k,o in dict(empty=136,allocate=200,dataReference=219,copy=234,advance=244).items()}
        offsets=scalar.reader_offsets(image,LABEL)
        offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
        programs=[int32_program(body['regions'],body['pointer'],offsets,s,count=n)for n in(-1,0,1)]
    def component(name):
        proof=owned(image,s[name]);components[name]=proof
        return proof
    components={};helpers={}
    empty=component('empty');s['indexed']=target(empty,22)
    helpers['empty']=empty_program(empty['regions'],empty['pointer'],s,element_type=element_type)
    alloc=component('allocate')
    if element_type=='int':
        # The complete parser owns the tail; select its actual E9 bytes independently.
        tail=[r for r in alloc['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
        need('one-owned-allocation-tail',len(tail)==1)
        s['arrayAllocate']=control_transfer(tail[0])['target']
        helpers['allocate']=arrays.int_allocate(alloc['regions'],alloc['pointer'],s)
    else:
        s['classData']=target(alloc,37)
        tail=[r for r in alloc['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe9']
        need('one-owned-Boolean-allocation-tail',len(tail)==1)
        s['arrayAllocate']=control_transfer(tail[0])['target']
        helpers['allocate']=boolean_allocate(alloc['regions'],alloc['pointer'],s)
    data=component('dataReference');s['asSpan']=target(data,38 if element_type=='int'else 46)
    if element_type=='int':helpers['dataReference']=arrays.int_data_reference(data['regions'],data['pointer'],s)
    else:
        s['getReference']=target(data,75)
        helpers['dataReference']=boolean_data_reference(data['regions'],data['pointer'],s)
        ref=component('getReference');helpers['getReference']=boolean_get_reference(ref['regions'],ref['pointer'])
    span=component('asSpan');s['spanConstructor']=target(span,51 if element_type=='int'else 59)
    helpers['asSpan']=(arrays.array_as_span if element_type=='int'else boolean_as_span)(span['regions'],span['pointer'],s)
    constructor=component('spanConstructor')
    helpers['spanConstructor']=(arrays.array_span_constructor if element_type=='int'else boolean_span_constructor)(constructor['regions'],constructor['pointer'])
    span_context=_span_context(image,context)
    offsets=scalar.reader_offsets(image,LABEL)
    scalar.advance_source(image,vector_recorder(image)(s['advance']-base,fragments=True),offsets,LABEL+'.advance')
    header=None
    if element_type=='bool':
        from scripts.game_data.memorypack.npc_collection_sources import _collection_header
        header=_collection_header(image,s['header'],{**offsets,'totalLength':ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16})
    declaration=json.loads((CONTRACTS_DIR/'memory_copy_bounded_native.json').read_bytes())
    need('same-selected-copy-inputs',declaration['nativeInputs']==pins)
    need('exact-actual-copy-target',base+declaration['entryRva']==s['copy'])
    copy=copy_source(image,declaration)
    need('complete-count-copy-bound',copy['maxBytes']>=count_limit*(4 if element_type=='int'else 1))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.module-unmanaged-array-source.v1',status='validated-conditional-source',nativeInputs=pins,
        typeName=element_type+'[]',elementType=element_type,readerMethodDefinition=typed_request['methodSpec'][0],
        targetRva=call_target-base,resultRegister='rax',countLimit=count_limit,collectionCounts=[-1,0],
        headerBytes=4,elementWireBytes=4 if element_type=='int'else 1,positiveCountsAdmitted=count_limit>0,
        rawBitsPreserved=True,elementCallbackUsed=False,booleanNormalizationClaimed=False,
        completeBufferedSourceProved=True,entryRspRestored=True,allNonvolatilesRestored=True,
        canonicalEntryPointerMatched=entry['pointer']==call_target,canonicalPointerEquivalenceInferred=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(context=context,actualCall=call,registration=entry,forwarder=forwarder,
            callerSourceWindows=caller['windows'],callerSourceRegions=[[a,h.hex()]for a,h in caller['regions']],
            sourceWindows=body['windows'],sourceRegions=[[a,h.hex()]for a,h in body['regions']],programs=programs,
            helpers=helpers,helperBodies={k:dict(windows=v['windows'],regions=[[a,h.hex()]for a,h in v['regions']])for k,v in components.items()},
            spanContext=span_context,collectionHeader=header,copy=copy,symbolRvas={k:v-base for k,v in s.items()}),
        conditions=['Exact coherent current closed MethodInfo records and RGCTX slots are stable.',
            'Buffered signed count is -1 or 0..countLimit, Reader/payload/frame/arrays are disjoint and nonwrapping.',
            'Typed empty-array/class/allocation helpers return normally with the independently proved context; allocation contents and execution are unobserved.',
            'Actual parent must separately prove Reader/MethodInfo argument origins, field stores, every frame and its own count gate.'])))
