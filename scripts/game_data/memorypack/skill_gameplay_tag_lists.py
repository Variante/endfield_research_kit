"""Exact closed generated GameplayTag list, never Query's raw4 array grammar.

This actual ListFormatter<Tag> selects the canonical generated value4 adapter,
so each positive element is MC1/tagId Int32 or FF/default4. Query's distinct
ReadUnmanagedArray<Tag> has raw4 payload and is not reused here. Complete signed
count/capacity/empty/provider/callback/Add source and unchanged R12D loop own the
list. The shared pure loop certificate transfers no BuffId type or width.
Ready coherent closed contexts/callbacks, normal zeroed typed allocations,
reused-empty spare capacity, disjoint buffered storage and normal helpers are
conditions. Nonempty Clear, growth, runtime selection and parent/root/EOF stay
independent and unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import need,VALUE

LIST='System.Collections.Generic.List`1<'+VALUE+'>'


def list4_program(regions,entry,o,s,*,count=1,new=True):
    need('literal-list-path',True,type(count)is int and count in(-1,0,1,2,3)and type(new)is bool)
    cur,rem,adv,used,total=(bytes((o[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g=BytesPath(regions,entry)
    g.take('48895c2420','55','56','57','4155','4156','4883ec20','4533ed','498be9','837a'+rem+'04',
        '4d8bf0','488bfa','44896c2458');g.branch('0f8c',False)
    g.take('488b47'+cur,'8b30','8b5f'+rem,'83c3fc');g.branch('0f88',False)
    g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','895f'+rem,
        '486347'+used,'488b4f'+total,'482bc8','4863c6','483bc8');g.branch('0f8c',False)
    g.take('83feff');g.branch('0f84',count==-1)
    loop=None;parts=[];callbacks=[];provider=None
    if count==-1:g.take('498bce','4d892e');g.call(s['barrier'])
    else:
        g.take('4c89642450','4c897c2460','4d392e');g.branch('0f85',not new)
        if new:
            g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
            g.take('488b4d20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False)
            g.take('85f6');g.branch('0f88',False)
            g.take('488b4520','488b88c0000000','4c8b7908','498b4720','488b88c0000000');g.branch('0f85',count>0)
            if count:
                g.take('ba01000000');g.call(s['context']);g.take('488bd6','488bc8');g.call(s['arrayAllocate']);g.jump('e9')
            else:
                g.take('33d2');g.call(s['context']);g.take('4439a8e0000000');g.branch('0f84',False)
                g.take('498b4f20','33d2','488b89c0000000');g.call(s['context'])
                g.take('488b88b8000000','488b01')
            g.take('488d4b10','48894310');g.call(s['barrier']);g.take('498bce','49891e');g.call(s['barrier'])
        else:
            g.take('488b4520','498b1e','488b88c0000000','488b4110','4c396820');g.branch('75',True,1)
            g.take('ff431c','44896b18');g.jump('e9')
        provider=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf8','458be5','85f6');g.branch('7f',count>0,1)
        if count:
            loop=g.at
            for i in range(count):
                need('same-actual-loop-entry',loop,g.at);before=len(g.seen)
                g.take('44896c2458','4d85ff');g.branch('74',False,1)
                g.take('4c8d4c2458','4c8bc7','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
                g.take('4d8b2e','8b5c2458','4d85ed');g.branch('74',False,1)
                g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4520','8bd3','498bcd','4c8b80c0000000','4d8b4030');g.call(s['add'])
                g.take('41ffc4','41bd00000000','443be6');g.branch('0f8d',i+1==count)
                if i+1<count:g.jump('eb',1)
                parts.append(g.seen[before:])
        g.take('4c8b642450','4c8b7c2460')
    g.take('488b5c2468','4883c420','415e','415d','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,loopEntry=loop,loopBodies=parts,
        callbackSites=callbacks,providerClassCell=provider,headerBytes=4,managedElementBytes=4,
        elementWireBytes=None,childOutput='zero4 frame+88; complete EAX/tag bits passed unchanged to Add EDX',
        addContextSlot=6,normalReturn=True,entryRspRestored=True)


def add4_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','ff411c','8bda','488b5110','498bf0',
        '48634118','488bf9','4885d2');g.branch('74',False,1)
    g.take('3b4218');g.branch('73',False,1)
    g.take('8d4801','894f18','3b4218');g.branch('73',False,1)
    g.take('895c8220','488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,managedInputBytes=4,arrayStride=4,arrayDataOffset=32,
        completeIncomingEDXBitsStored=True,sizeIncrementedOnce=True,versionIncrementedOnce=True,
        growthAdmitted=False,elementWireBytes=None)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,bind_list_add_abi
    from scripts.game_data.memorypack.skill_gameplay_tag_value_sources import derive as child_source
    from scripts.game_data.memorypack.skill_gameplay_tag_value_transfer import derive as transfer_source
    from scripts.game_data.memorypack.skill_root_buff_id_lists import induction
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);need('bounded-positive-list-count',True,type(count_limit)is int and 3<=count_limit<=10000)
    base=image.pe.image_base;ge=GenericEntries(image)
    context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=VALUE)
    def call(at):
        rows=[r for r in body['rows']if int(r['va'],16)==at];need('one-owned-list-call',1,len(rows))
        raw=bytes.fromhex(rows[0]['bytes']);need('exact-list-E8',(5,232),(len(raw),raw[0]));return control_transfer(rows[0])['target']
    s={k:call(body['pointer']+o)for k,o in dict(context=141,allocate=149,barrier=298,provider=338,arrayAllocate=424,dispatch=455,add=518).items()}
    offsets=scalar.reader_offsets(image,'gameplayTagList');offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[list4_program(body['regions'],body['pointer'],offsets,s,count=n,new=new)for n in range(-1,4)for new in(True,False)]
    certificate=induction(paths,count_limit=count_limit)
    add=owned(image,s['add']);add_proof=add4_program(add['regions'],s['add'])
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    add_registration=ge.resolve(slots[6]['methodSpec'][0],[VALUE],[]);add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    child=child_source(image,pins);transfer=transfer_source(image,pins,child)
    need('same-closed-list-registration',context['registration'],transfer['registrations']['list'])
    for role in('provider','dispatch'):need('same-actual-value-transfer:'+role,s[role]-base,transfer['symbolRvas'][role])
    need('same-own-typed-value-barrier',child['symbolRvas']['barrier'],s['barrier']-base)
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    element=dict(typeName=VALUE,memberCount=1,nullable=True,nullMarker=255,managedBytes=4,wireBytes=None,
        positiveWireBytes=5,nullWireBytes=1,nullReturnsDefaultValue=True,
        orderedReads=[dict(fieldName='tagId',kind='int32')],callbackSelectionConditional=True,
        rawUnmanagedTagGrammarUsed=False,wholeOwnerAdmitted=False)
    collection=dict(elementType=VALUE,closedListType=LIST,elementValueType=True,managedElementBytes=4,
        elementWireBytes=None,collectionCounts=[-1,0],positiveCountsAdmitted=True,countLimit=count_limit,
        nullable=True,elementCapability='skill-root-gameplay-tag',elementGrammarAdmitted=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-gameplay-tag-list-components.v1',nativeInputs=pins,
        status='validated-conditional-components',capabilities={'skill-root-gameplay-tag':element,
            'skill-root-gameplay-tag-value-list':collection},proof=dict(context=context,programs=paths,
            induction=certificate,addRegistration=add_registration,addABI=add_abi,addProgram=add_proof,addWindows=add['windows'],
            canonicalAddBodySemanticsUsed=False,actualAddSourceIndependentlyProved=True,
            reusedClear=dict(inlineVersionIncrement=True,inlineSizeZero=True,elementArrayTouched=False,initialCountZeroRequired=True),
            child=child,transfer=transfer,barrier=barrier,barrierProof=barrier_proof),
        evidenceBoundary=dict(exact='Own selected List<GameplayTag> signed null/empty/positive source, typed inlined capacity, generated MC1/value4 canonical callback, raw DWORD Add store and bounded unchanged-count induction.',
            conditional=__doc__,structuralOnly='Stored generated tag records.',unresolved=['actual enclosing field/owner source join','growth/nonempty reused list','runtime meaning/selection','whole owner/physical EOF']))))
