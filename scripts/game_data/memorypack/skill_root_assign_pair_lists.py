"""Closed AssignPair value40 list count, callback, Add and return composition.

Signed counts -1/0 and bounded positive counts are separate exact paths. New
lists require normal typed zeroed allocations with capacity equal to the saved
count. Reused lists start empty with enough capacity; only their actual selected
zero-size Clear path is admitted. The unchanged count/index and one/two witness
paths establish the identical loop/backedge, zero40 output, exact canonical
callback, copy16+16+8 and owned Add stride40. Managed40 is not the serialized
width: the independently proved child is MC6/FF. Ready coherent selected closed
contexts, normal typed allocations, disjoint buffered input/output/frame and
compatible noninterfering helpers/barriers remain conditional. Runtime provider
selection, growth/nonempty Clear, malformed/refill paths and whole owner/EOF are
unresolved. An enclosing caller must supply its independently proved typed
request and actual source call target.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_assign_pair_sources import need,VALUE

LIST='System.Collections.Generic.List`1<'+VALUE+'>'


def add40_program(regions,entry,barrier):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec50','ff411c','498bf0','4c8b4910',
        '488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1)
    g.take('413b4118');g.branch('0f83',False)
    g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
    g.take('0f1007','488d1480','488bc8','0f104f10','48ffc0','410f1144d120',
        'f20f104720','488d0481','410f114cd130','498d0cc1','f2410f1144d140')
    g.call(barrier)
    g.take('488b5c2460','488b742468','4883c450','5f','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,inputValueAddress='incoming rdx preserved rdi',
        copiedBytes=40,chunkBytes=[16,16,8],arrayDataOffset=32,arrayStride=40,
        originalIndex='signed list count saved rax before increment',versionIncremented=True,
        countIncrementedExactlyOnce=True,spareCapacityRequired=True,growthAdmitted=False,
        elementWireBytes=None)


def list40_program(regions,entry,offsets,s,*,count=1,new=True):
    if type(count)is not int or count not in(-1,0,1,2)or type(new)is not bool:raise ValueError('assignList.path')
    g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('4053','55','56','57','4156','4881eca0000000','33c0','0f57c0','837a'+rem+'04',
        '498be9','4d8bf0','4889442460','488bda','0f11442440','0f11442450');g.branch('0f8c',False)
    g.take('488b43'+cur,'8b38','8b73'+rem,'83c6fc');g.branch('0f88',False)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4863c7','483bc8');g.branch('0f8c',False)
    g.take('83ffff');g.branch('0f84',count==-1)
    loop=None;callbacks=[];adds=[];body_parts=[];provider=None;allocation=None
    if count==-1:
        g.take('33f6','498bce','498936');g.call(s['barrier'])
    else:
        g.take('4c89a424d0000000','4c89bc24e0000000','49833e00');g.branch('0f85',not new)
        if new:
            g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('488b4d20','488b91c0000000','488b4a08','4883792000');g.branch('0f84',False)
            g.take('85ff');g.branch('0f88',False)
            g.take('488b4520','488b88c0000000','4c8b7908','498b4720','488b88c0000000');g.branch('0f85',count>0)
            if count:
                g.take('ba01000000');g.call(s['context'])
                g.take('488bd7','488bc8');allocation=g.at;g.call(s['arrayAllocate']);g.jump('e9')
            else:
                g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('0f84',False)
                g.take('498b4f20','33d2','488b89c0000000');g.call(s['context'])
                g.take('488b88b8000000','488b01')
            g.take('488d4e10','48894610');g.call(s['barrier'])
            g.take('498bce','498936');g.call(s['barrier'])
        else:
            g.take('488b4520','498b36','488b88c0000000','488b4110','4883782000');g.branch('75',True,1)
            g.take('488b4520','488bce','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
        provider=g.relative('488b0d');g.take('83b9e000000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('33f6','4c8bf8','85ff');g.branch('7f',count>0,1)
        if count:
            loop=g.at
            for i in range(count):
                if g.at!=loop:raise ValueError('assignList.actual-back-edge')
                before=len(g.seen)
                g.take('33c0','0f57c0','4889442460','0f11442440','0f11442450','4d85ff');g.branch('0f84',False)
                g.take('4c8d4c2440','4c8bc3','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
                g.take('0f10442440','4d8b26','f20f10542460','f20f119424d8000000','0f104c2450',
                    '0f11442420','0f114c2430','4d85e4');g.branch('0f84',False)
                g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4520','488d542470','498bcc','0f29442470','0f298c2480000000',
                    'f20f11942490000000','4c8b80c0000000','4d8b4030');adds.append(g.at);g.call(s['add'])
                g.take('ffc6','3bf7');g.branch('0f8d',i+1==count)
                body_parts.append(g.seen[before:])
                if i+1<count:g.jump('e9')
        g.take('4c8ba424d0000000','4c8bbc24e0000000')
    g.take('4881c4a0000000','415e','5f','5e','5d','5b','c3')
    if count==2 and body_parts[0]!=body_parts[1]:raise ValueError('assignList.identical-loop')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,headerBytes=4,managedElementBytes=40,
        elementWireBytes=None,loopEntry=loop,loopBodies=body_parts,callbackSites=callbacks,
        providerClassCell=provider,arrayAllocationSite=allocation,
        count='incoming signed header saved edi unchanged',index='esi initialized0; INC/compare to edi',
        valueCopyChunks=[16,16,8],childOutput='zero40 frame+64',addInput='same40 bits copied to frame+112',
        addCallSites=adds,addContextSlot=6,addArguments=dict(rcx='same list',rdx='same complete40 local',r8='owned List<AssignPair>.Add MethodInfo'),
        normalReturn=True,entryRspRestored=True)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    """Own a closed collection only; no BuffInput/union/root framing is implied."""
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,clear_zero_program,bind_list_add_abi
    from scripts.game_data.memorypack.skill_root_assign_pair_sources import derive as child_source
    from scripts.game_data.memorypack.skill_root_assign_pair_transfer import derive as transfer_source
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.levelscript_two_routes_native import _window
    need('bounded-positive-count-limit',True,type(count_limit)is int and 1<=count_limit<=4096)
    base=image.pe.image_base;ge=GenericEntries(image)
    context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=VALUE)
    by={int(r['va'],16)-body['pointer']:r for r in body['rows']}
    def call(offset):
        row=by[offset];raw=bytes.fromhex(row['bytes']);need('exact-list-E8',(5,232),(len(raw),raw[0]))
        return control_transfer(row)['target']
    s={name:call(offset)for name,offset in dict(context=158,allocate=166,barrier=305,provider=356,dispatch=440,add=563,arrayAllocate=599).items()}
    existing=control_transfer(by[139])['target']
    clear_at=existing-body['pointer']+60
    s['clear']=call(clear_at)
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    clear=ge.resolve(slots[2]['methodSpec'][0],[VALUE],[])
    need('exact-closed-Clear-target',clear['pointer'],s['clear'])
    # This concrete Clear has no unwind owner. Keep only its actual selected
    # raw prefix and zero-size return, never guessed padding/full extent.
    prefix=image.pe.bytes_at_va(s['clear'],19);need('selected-clear-JLE',b'\x7e',prefix[17:18])
    returned=s['clear']+19+int.from_bytes(prefix[18:19],'little',signed=True)
    clear_regions=[(s['clear'],prefix),(returned,image.pe.bytes_at_va(returned,1))]
    clear_program=clear_zero_program(clear_regions,s['clear'])
    clear_windows=[_window(image,s['clear'],s['clear']+19,'actual selected closed AssignPair Clear prefix; no full-extent claim'),
        _window(image,returned,returned+1,'actual selected zero-size AssignPair Clear return')]
    add=ge.resolve(slots[6]['methodSpec'][0],[VALUE],[])
    add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    add_source=owned(image,s['add']);add_program=add40_program(add_source['regions'],s['add'],s['barrier'])
    offsets=scalar.reader_offsets(image,'assignPairList')
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[list40_program(body['regions'],body['pointer'],offsets,s,count=count,new=new)
        for count in(-1,0,1,2)for new in(True,False)]
    child=child_source(image,pins);transfer=transfer_source(image,pins,child)
    need('same-selected-list-registration',context['registration'],transfer['registrations']['list'])
    for role in('provider','dispatch','barrier'):need('same-value-transfer:'+role,s[role]-base,transfer['symbolRvas'][role])
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    child_cap=dict(typeName=VALUE,memberCount=6,nullable=True,nullMarker=255,managedBytes=40,wireBytes=None,
        positiveWireBytes=22,nullWireBytes=1,nullReturnsDefaultValue=True,
        orderedReads=[dict(fieldName=f,kind=k)for f,k in(
            ('directValueType','enum32'),('inputValueKey','pooled-string'),('numericValue','single-bits'),
            ('stringValue','pooled-string'),('targetKey','pooled-string'),('useDirectValue','bool'))],
        callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    collection_cap=dict(elementType=VALUE,closedListType=LIST,elementValueType=True,managedElementBytes=40,
        elementWireBytes=None,collectionCounts=[-1,0],positiveCountsAdmitted=True,countLimit=count_limit,
        nullable=True,elementCapability='skill-root-assign-pair',elementGrammarAdmitted=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-assign-pair-list.v1',status='validated-conditional-components',
        nativeInputs=pins,capabilities={'skill-root-assign-pair':child_cap,'skill-root-assign-pair-list':collection_cap},
        proof=dict(context=context,programs=programs,clearRegistration=clear,clearProgram=clear_program,
            clearWindows=clear_windows,addRegistration=add,addProgram=add_program,addWindows=add_source['windows'],
            addBinding=dict(actualOptimizedTargetRva=s['add']-base,canonicalRegistrationRva=add['pointer']-base,
                pointerEqualityProved=s['add']==add['pointer'],canonicalBodySemanticsUsed=False,
                actualSourceIndependentlyProved=True,ownedMethodInfoSlot=6,abi=add_abi),
            child=child,transfer=transfer,barrier=barrier,barrierProof=barrier_proof),
        evidenceBoundary=dict(exact='Own selected closed AssignPair value-list signed count/null/empty/positive programs, typed capacity context, callback40, copy40, owned closed Add stride40 and complete loop/return; independent child MC6/FF and hidden40 conversion.',
            conditional=__doc__,structuralOnly='Stored blackboard assignment configuration.',
            unresolved=['enclosing BuffInput/union/root source framing','growth and nonempty existing Clear','runtime selection','physical EOF']))))
