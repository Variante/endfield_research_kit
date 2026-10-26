"""Selected positive Pull value16 list; no sixteen-byte wire inference.

The own closed ListFormatter source reads signed count4, passes the unchanged
count to its own capacity constructor, initializes each hidden callback result
to zero16, copies all16 through an aligned independent Add local and advances
one nonvolatile counter. New count-sized typed storage and initially empty
reused storage with sufficient capacity are admitted conditionally. Each
element consumes its independent MC2 Single/reference program or FF/default16.
The actual selected canonical callback, coherent contexts, normal compatible
helpers, disabled collector and disjoint sufficiently buffered storage remain
conditions. Growth/nonempty Clear, live provider choice and enclosing owner
or physical EOF are unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_pull_attenuation_sources import TYPE,WRAPPER,CAPABILITY,LIST,CHILD,ORDER


def list_program(regions,entry,s,*,count,new=True):
    need('pull-list-literal-path',True,type(count)is int and count in(-1,0,1,2,3)and type(new)is bool)
    g=BytesPath(regions,entry)
    g.take('488bc4','53','57','4156','4157','4883ec58','4c8bfa','0f57c0','4533f6',
        '488d5010','498bcf','44897010','498bd9','498bf8','0f1140a8')
    g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
    loop=None;bodies=[];callbacks=[];adds=[];exits=[];provider=None
    if count==-1:
        g.take('488bcf','4c8937');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('4889b42490000000','4889ac2480000000','4c89642450','0f29742440',
            '8bb42488000000','4c3937');g.branch('0f85',not new)
        if new:
            g.take('488b4b20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('488b4b20','488b91c0000000','488b4a08','4c397120');g.branch('0f84',False)
            g.take('488b4320','8bd6','488bcd','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
            g.take('488bcf','48892f');g.call(s['barrier'])
        else:
            g.take('488b4320','488b2f','488b90c0000000','488b4210','4c397020');g.branch('75',True,1)
            g.take('488b4320','488bcd','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
        at=g.at;cell=g.relative('488b0d');provider=dict(instruction=at,cell=cell)
        g.take('4439b1e0000000');g.branch('0f84',False)
        g.take('488b4320','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('488be8','85f6');g.branch('7f',count>0,1)
        if count:
            loop=g.at
            for i in range(count):
                need('pull-list-identical-owned-loop-entry',loop,g.at);before=len(g.seen)
                g.take('0f57c0','0f11442420','4885ed');g.branch('74',False,1)
                g.take('4c8d4c2420','4d8bc7','488bd5');callbacks.append(g.at);g.call(s['dispatch'])
                g.take('4c8b27','0f28742420','4d85e4');g.branch('74',False,1)
                g.take('488b4320','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4320','488d542430','498bcc','660f7f742430','4c8b80c0000000','4d8b4030')
                adds.append(g.at);g.call(s['add']);g.take('41ffc6','443bf6');bodies.append(g.seen[before:])
                exits.append(g.at);g.branch('0f8d',i+1==count)
                if i+1<count:g.jump('eb',1)
        g.take('4c8b642450','488bac2480000000','0f28742440','488bb42490000000')
    g.take('4883c458','415f','415e','5f','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,headerBytes=4,elementWireBytes=None,
        managedElementBytes=16,loopEntry=loop,loopBodies=bodies,loopExitInstructions=exits,
        elementCallbackSites=callbacks,addCallSites=adds,providerOwnerUsage=provider,
        countRegister='esi',counterRegister='r14d',headerLocalFromFrame=136,outputLocalFromFrame=32,addLocalFromFrame=48,
        sameWhole16CallbackOutputCopied=True,alignedDistinctAddLocal=True,allIntegerNonvolatilesRestored=True,
        restoredXmm6=count!=-1,normalReturn=True,entryRspRestored=True)


def add_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','ff411c',
        '498bf0','4c8b4910','488bfa','48634118','488bd9','4d85c9');g.branch('74',False,1)
    g.take('413b4118');g.branch('0f83',False)
    g.take('8d4801','894b18','413b4118');g.branch('73',False,1)
    g.take('0f1002','488d4802','4803c9','410f1104c9','488d4802','48c1e104','4903c9');g.call(barrier)
    g.take('488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,managedInputBytes=16,arrayStrideBytes=16,arrayDataOffset=32,
        referenceLaneOffset=0,listSizeOffset=24,listVersionOffset=28,oldIndexInBoundsCheckedTwice=True,
        unchangedWholeInput16Copied=True,newSizeEqualsOldPlusOne=True,versionIncrementedOnce=True,
        normalReturn=True,entryRspRestored=True,growthAdmitted=False)


def canonical_add_program(regions,entry,array_store):
    """Independent registered Add entry; never assign it the optimized body."""
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec30','ff411c',
        '488bd9','4c8b4910','498bf8','48634918','488bf2','4d85c9');g.branch('75',True,1)
    g.take('413b4918');g.branch('72',True,1)
    g.take('0f1002','8d4101','488bd1','4c8d442420','894318','498bc9','f30f7f442420');g.call(array_store)
    g.take('488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,managedInputBytes=16,unchangedWholeInput16Copied=True,
        arrayArgument='same list items',arrayIndex='unchanged prior signed list size',newSizeEqualsOldPlusOne=True,
        versionIncrementedOnce=True,normalReturn=True,entryRspRestored=True,growthAdmitted=False,
        actualOptimizedAddPointerEqualityClaimed=False)


def array_store_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
    g.take('410f2800','488d4202','4803c0','0f1104c1','488d4202','48c1e004','4803c8','4883c428')
    need('pull-canonical-array-same-lane0-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,managedInputBytes=16,arrayStrideBytes=16,arrayDataOffset=32,
        referenceLaneOffset=0,unchangedWholeInput16Copied=True,normalReturnViaBarrier=True,entryRspRestored=True)


def induction(programs,count_limit):
    need('pull-list-literal-count-bound',True,type(count_limit)is int and 3<=count_limit<=10000);profiles=[]
    for new in(True,False):
        rows={n:next(p for p in programs if p['newList']is new and p['countWitness']==n)for n in range(4)}
        need('pull-list-zero-no-element',[],rows[0]['elementCallbackSites'])
        need('pull-list-zero-complete-return',True,rows[0]['normalReturn']and rows[0]['entryRspRestored'])
        body=rows[1]['loopBodies'][0]
        need('pull-list-identical-one-two-three-cores',[[body]*n for n in(1,2,3)],[rows[n]['loopBodies']for n in(1,2,3)])
        need('pull-list-one-increment-and-signed-compare',(1,1),tuple(sum(h==raw for at,h in body)for raw in('41ffc6','443bf6')))
        need('pull-list-final-core-increment-compare',['41ffc6','443bf6'],[h for at,h in body[-2:]])
        for n in(1,2,3):
            p=rows[n];need('pull-list-one-owned-counter-init',1,sum(h=='4533f6'for at,h in p['selectedBytes']))
            need('pull-list-exit-and-callback-source-sites',([rows[1]['loopExitInstructions'][0]]*n,[rows[1]['elementCallbackSites'][0]]*n),
                (p['loopExitInstructions'],p['elementCallbackSites']))
        profiles.append(dict(newList=new,loopEntry=rows[1]['loopEntry'],loopBody=body,
            signedExitInstruction=rows[1]['loopExitInstructions'][0],counter='r14d',savedCount='unchanged signed32 esi'))
    return dict(schema='endfield.pull-value-list-induction.v1',countRange=[0,count_limit],profiles=profiles,
        noSignedCounterOverflow=True,exit='After one INC R14D, signed JGE(count ESI) exits; otherwise exact short JMP reaches same owned loop entry.',
        invariant='At entry R14D=i, 0<=i<count<=10000. Complete selected callback/Add core preserves ESI and all required nonvolatile registers, stores exactly one whole managed16 value, increments once, and returns to the identical body iff i+1<count.',
        condition='The strict byte program owns all selected instructions/edges/frame and the separate child/typed Add/capacity/disabled-barrier proofs hold. No growth, nonempty Clear or live callback choice is admitted.')


def value_capability():
    return dict(typeName=TYPE,wrapperName=WRAPPER,elementValueType=True,memberCount=2,managedBytes=16,
        referenceLaneOffsets=[0],paddingByteRanges=[[12,16]],nullable=True,nullAdmitted=True,nullMarker=255,
        wireBytes=None,positiveWireBytes=None,nullWireBytes=1,nullReturnsDefaultValue=True,orderedReads=ORDER,
        wholeGrammarAdmitted=True,canonicalValueCallbackProved=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,callbackSelectionConditional=True,
        wholeSkillDataAdmitted=False)


def _derive_on_child(image,pins,reference,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.skill_value_list_context import derive as context_source,clear_zero_program,bind_list_add_abi
    from scripts.game_data.memorypack.skill_pull_attenuation_sources import _derive_wrapper,require_reference
    from scripts.game_data.memorypack.skill_pull_attenuation_transfer import derive as transfer_source
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources,animation_mask_sources as capacity,scalar_param_native as scalar
    from scripts.game_data.memorypack.npc_collection_sources import _collection_header
    _publication_gate(image,pins);need('pull-list-bounded-count',True,type(count_limit)is int and 3<=count_limit<=10000)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);context,body=context_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    child=_derive_wrapper(image,pins,reference);transfer=transfer_source(image,pins,child)
    need('pull-list-same-fresh-closed-entry',context['registration'],transfer['registrations']['list'])
    s={role:buff_ptr_sources._call(body,off)for role,off in dict(header=43,context=111,allocate=119,constructor=181,barrier=192,provider=232,dispatch=312,add=385).items()}
    reused=BytesPath(body['regions'],body['pointer']+92).relative('0f85')
    reused_body=dict(body,pointer=reused);s['clear']=buff_ptr_sources._call(reused_body,59)
    programs=[list_program(body['regions'],body['pointer'],s,count=-1)]+[
        list_program(body['regions'],body['pointer'],s,count=n,new=new)for n in range(4)for new in(True,False)]
    certificate=induction(programs,count_limit)
    for role in('dispatch','provider','barrier'):
        need('pull-list-same-exact-transfer-helper:'+role,s[role]-base,transfer['symbolRvas'][role])
    constructor=pointer.owned(image,s['constructor']);s['arrayAllocate']=buff_ptr_sources._call(constructor,132)
    capacities=[capacity.capacity_program(constructor['regions'],constructor['pointer'],s,positive=n)for n in(False,True)]
    need('pull-list-same-capacity-indexed-helper',s['context'],buff_ptr_sources._call(constructor,46))
    clear_raw=image.pe.bytes_at_va(s['clear'],19);need('pull-list-exact-Clear-empty-branch',b'\x7e',clear_raw[17:18])
    clear_end=s['clear']+19+int.from_bytes(clear_raw[18:19],'little',signed=True)
    clear_regions=[(s['clear'],clear_raw),(clear_end,image.pe.bytes_at_va(clear_end,1))]
    clear=clear_zero_program(clear_regions,s['clear'])
    add=pointer.owned(image,s['add']);add_proof=add_program(add['regions'],add['pointer'],s['barrier'])
    slots={r['relativeSlot']:r for r in context['context']['entries']};add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    entries=GenericEntries(image);ctor_entry=entries.resolve(slots[1]['methodSpec'][0],[TYPE],[]);add_entry=entries.resolve(slots[6]['methodSpec'][0],[TYPE],[])
    need('pull-list-actual-own-closed-constructor',s['constructor'],ctor_entry['pointer'])
    # The actual optimized Add and registered closed Add have distinct entries.
    # Prove both complete selected sources, with the same freshly owned formal
    # VAR and unchanged whole value16/count/store semantics; never alias bodies.
    canonical_add=pointer.owned(image,add_entry['pointer']);array_target=buff_ptr_sources._call(canonical_add,156)
    canonical_array=pointer.owned(image,array_target)
    canonical_add_proof=canonical_add_program(canonical_add['regions'],canonical_add['pointer'],array_target)
    canonical_array_proof=array_store_program(canonical_array['regions'],array_target,s['barrier'])
    add_binding=dict(actualOptimizedEntryRva=s['add']-base,registeredEntryRva=add_entry['pointer']-base,
        pointerEqualityClaimed=False,bodiesIndependentlyProved=True,formalABI=add_abi,
        actualListMethodInfoContextSlot=6,methodInfoUsedBySelectedOptimizedFastPath=False,
        sameCompleteManaged16StoreAndSizeVersionUpdate=True)
    offsets=scalar.reader_offsets(image,'pullList');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    header=_collection_header(image,s['header'],offsets)
    usage=derive_typed_usage_context(image,next(p['providerOwnerUsage']['instruction']for p in programs if p['providerOwnerUsage'])-base,label='pullList.provider')
    need('pull-list-exact-provider-class',(1,'MemoryPack.MemoryPackFormatterProvider'),(usage['tag'],usage['typeName']))
    caps={CAPABILITY:value_capability(),LIST:dict(elementType=TYPE,elementValueType=True,closedListType=context['closedListType'],elementCapability=CAPABILITY,
        nullable=True,collectionCounts=[-1,0],countLimit=count_limit,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
        elementWireBytes=None,packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-pull-attenuation-list.v1',status='validated-conditional-pull-value-list',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=[CHILD],requiredExternalCapabilityIdentities={CHILD:{k:require_reference(reference,pins)[k]
            for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}},
        proof=dict(context=context,child=child,transfer=transfer,programs=programs,induction=certificate,capacities=capacities,
            constructorRegistration=ctor_entry,addRegistration=add_entry,addABI=add_abi,addProgram=add_proof,addBinding=add_binding,
            canonicalAddProgram=canonical_add_proof,canonicalArrayProgram=canonical_array_proof,
            canonicalAddWindows=canonical_add['windows'],canonicalArrayWindows=canonical_array['windows'],clearProgram=clear,
            clearObservedIntervals=[[at,raw.hex().upper()]for at,raw in clear_regions],clearFullPhysicalExtentProved=False,
            header=header,providerOwner=usage,sourceWindows=body['windows'],constructorWindows=constructor['windows'],addWindows=add['windows'],symbolRvas={k:v-base for k,v in s.items()}),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Actual nominal ReadPackable/list context, signed4 header/new/-1/empty reuse, typed capacity/empty storage, canonical managed16 callback, independent MC2/default child, whole16 Add/lane0 barrier and bounded count induction.',
            conditional=__doc__,structuralOnly='Stored pull attenuation configuration list.',
            unresolved=['actual enclosing action/field/union','live callback/provider selection','nonempty Clear/growth/refill','whole root/physical EOF']))))


def derive(image,pins,*,typed_request,call_target,count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import derive as child_source
    from scripts.game_data.memorypack.skill_pull_attenuation_sources import REFERENCE
    _publication_gate(image,pins)
    return _derive_on_child(image,pins,child_source(image,pins,type_names=[REFERENCE]),typed_request=typed_request,call_target=call_target,count_limit=count_limit)
