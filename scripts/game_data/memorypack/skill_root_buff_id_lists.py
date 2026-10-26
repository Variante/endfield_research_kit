"""Own BuffId wire value and bounded value8 list/callback/Add sources.

The signed count owns null/empty and positive paths independently. Fresh lists
receive the unchanged capacity; reused lists must initially be empty and have
spare capacity. The actual callback returns managed8, Add forwards the same
QWORD to its independently proved checked array store and barrier tail. None of
these managed widths supplies BuffId's MC1/pool4 wire grammar. Complete source
iterations establish one R12D increment and signed ESI comparison; children
preserve those nonvolatiles under the selected ABI. Ready coherent typed
contexts, compatible zeroed typed allocations, disjoint buffered storage and
normal helper/barrier effects are explicit conditions. Nonempty Clear, growth,
runtime selection and enclosing root/EOF remain unresolved. The standalone
derive_value path composes the same own MC1 source and default transfer while
granting no positive collection or parent admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_buff_id_sources import need,VALUE

LIST='System.Collections.Generic.List`1<'+VALUE+'>'


def value_capability():
    """Exact MC1 value scope only; its managed8 is not a serialized width."""
    return dict(typeName=VALUE,memberCount=1,nullable=True,nullMarker=255,managedBytes=8,wireBytes=None,
        positiveWireBytes=5,nullWireBytes=1,nullReturnsDefaultValue=True,
        orderedReads=[dict(fieldName='buffId',kind='pooled-string')],callbackSelectionConditional=True,wholeOwnerAdmitted=False)


def derive_value(image,pins):
    """Fresh own MC1 source/default adapter without requiring any list parent."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_buff_id_sources import derive as child_source
    from scripts.game_data.memorypack.skill_root_buff_id_transfer import derive as transfer_source
    _publication_gate(image,pins);child=child_source(image,pins);transfer=transfer_source(image,pins,child)
    need('value-only-exact-current-child',(pins,VALUE,'proved-wrapper-source-requires-value8-adapter'),
        tuple(child.get(k)for k in('nativeInputs','typeName','status')))
    need('value-only-complete-MC1-FF-paths',[1,1,None],[p.get('memberCount')for p in child['programs']])
    need('value-only-normal-source-returns',True,all(p.get('normalReturnViaBarrier')is True and p.get('entryRspRestored')is True
        for p in child['programs']))
    need('value-only-own-managed8-layout',True,type(child.get('layout',{}).get('managedBytes'))is int and child['layout']['managedBytes']==8)
    need('value-only-exact-current-transfer',(pins,VALUE,'proved-selected-value8-transfer',8,None),
        tuple(transfer.get(k)for k in('nativeInputs','typeName','status','managedBytes','wireBytes')))
    need('value-only-same-child-barrier',child['symbolRvas']['barrier'],transfer['symbolRvas']['barrier'])
    _publication_gate(image,pins)
    return dict(schema='endfield.skill-root-buff-id-value.v1',status='validated-conditional-buff-id-value',nativeInputs=pins,
        capabilities={'skill-root-buff-id':value_capability()},requiredExternalCapabilities=['byte-payload'],
        proof=dict(child=child,transfer=transfer),positiveCollectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own nominal BuffId MC1/pool4/new/FF source, managed8 constructor/GetValue and selected canonical/default value transfer.',
            conditional='Initialized coherent nominal contexts, matching callbacks, stable disjoint buffered storage and normal noninterfering helpers/disabled collector.',
            structuralOnly='Stored buff identifier.',unresolved=['actual parent ReadValue context/E8/field transfer','positive collection parent/count/callback/Add','runtime selection','whole owner/EOF']))


def list8_program(regions,entry,offsets,s,*,count=1,new=True):
    need('literal-list-witness',True,type(count)is int and count in(-1,0,1,2,3)and type(new)is bool)
    g=BytesPath(regions,entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2420','55','56','57','4155','4156','4883ec20','4533ed','498be9','837a'+rem+'04',
        '4d8bf0','488bfa','4c896c2458');g.branch('0f8c',False)
    g.take('488b47'+cur,'486330','8b5f'+rem,'83c3fc');g.branch('0f88',False)
    g.take('488347'+cur+'04','8347'+adv+'04','8347'+used+'04','895f'+rem,
        '486347'+used,'488b4f'+total,'482bc8','483bce');g.branch('0f8c',False)
    g.take('83feff');g.branch('0f84',count==-1)
    loop=None;parts=[];callbacks=[];provider=None
    if count==-1:g.take('498bce','4d892e');g.call(s['barrier'])
    else:
        g.take('4c89642450','4c897c2460','4d392e');g.branch('0f85',not new)
        if new:
            g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
            g.take('488b4d20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False)
            g.take('488b4520','8bd6','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
            g.take('498bce','49891e');g.call(s['barrier'])
        else:
            g.take('488b4520','498b1e','488b88c0000000','488b4110','4c396820');g.branch('75',True,1)
            g.take('488b4520','488bcb','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
        provider=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf8','458be5','85f6');g.branch('7f',count>0,1)
        if count:
            loop=g.at
            for i in range(count):
                need('same-list-loop-entry',loop,g.at);before=len(g.seen)
                g.take('4c896c2458','4d85ff');g.branch('0f84',False)
                g.take('4c8d4c2458','4c8bc7','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
                g.take('4d8b2e','488b5c2458','4d85ed');g.branch('74',False,1)
                g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4520','488bd3','498bcd','4c8b80c0000000','4d8b4030');g.call(s['add'])
                g.take('41ffc4','41bd00000000','443be6');g.branch('0f8d',i+1==count)
                if i+1<count:g.jump('eb',1)
                parts.append(g.seen[before:])
        g.take('4c8b642450','4c8b7c2460')
    g.take('488b5c2468','4883c420','415e','415d','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=new,headerBytes=4,managedElementBytes=8,
        elementWireBytes=None,loopEntry=loop,loopBodies=parts,callbackSites=callbacks,
        providerClassCell=provider,index='r12d initialized from zero r13d, incremented once',
        savedCount='signed32 count sign-extended to rsi, unchanged',
        callbackOutput='zero8 frame+88',addArguments=dict(rcx='same list',rdx='same complete QWORD',r8='owned closed Add MethodInfo'),
        addContextSlot=6,normalReturn=True,entryRspRestored=True)


def capacity_program(regions,entry,s,*,positive):
    need('literal-capacity-mode',True,type(positive)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('75',positive,1)
    if positive:
        g.take('ba01000000');g.call(s['context']);g.take('488bd3','488bc8');g.call(s['arrayAllocate']);g.jump('eb',1)
    else:
        g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('74',False,1)
        g.take('488b4f20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488b88b8000000','488b01')
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f')
    need('capacity-tail-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,positive=positive,arrayClassContextSlot=1,
        zeroArrayClassContextSlot=0,capacityPassedUnchanged=True,listArrayOffset=16,
        countZeroRequiresZeroedTypedListAllocation=True,normalReturnViaBarrier=True,entryRspRestored=True)


def add8_program(regions,entry,array_set):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','ff411c','488bf9','4c8b4910',
        '498bf0','48634918','488bda','4d85c9');g.branch('74',False,1)
    g.take('413b4918');g.branch('0f83',False)
    g.take('8d4101','488bd1','498bc9','894718','4c8bc3');g.call(array_set)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,normalReturn=True,versionOffset=28,countOffset=24,
        versionIncrementedOnce=True,countIncrementedOnce=True,unchangedQwordFromRdxToR8=True,
        checkedIndexFromOldCount=True,spareCapacityRequired=True,growthAdmitted=False,elementWireBytes=None)


def array_set8_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883ec28','3b5118');g.branch('73',False,1)
    g.take('4c8944d120','488d0cd1','4883c120','4883c428')
    need('array-store-tail-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,normalReturnViaBarrier=True,arrayStride=8,arrayDataOffset=32,
        exactUnchangedQwordStore=True,checkedNonnegativeIndexRequired=True,entryRspRestored=True,elementWireBytes=None)


def induction(programs,*,count_limit):
    need('bounded-list-count-limit',True,type(count_limit)is int and 3<=count_limit<=10000)
    modes=[]
    for new in(True,False):
        rows={n:next(p for p in programs if p['newList']is new and p['countWitness']==n)for n in range(4)}
        need('complete-zero-no-elements',(True,[]),(rows[0]['normalReturn'],rows[0]['callbackSites']))
        final=rows[1]['loopBodies'][0];continued=rows[2]['loopBodies'][0]
        need('same-final-body',final,rows[2]['loopBodies'][-1])
        need('same-three-iteration-bodies',[continued,continued,final],rows[3]['loopBodies'])
        need('identical-body-before-selected-exit',final,continued[:-2])
        need('actual-continue-jump','eb',continued[-2][1])
        need('one-counter-increment',1,sum(h=='41ffc4'for a,h in final))
        need('one-unchanged-count-comparison',1,sum(h=='443be6'for a,h in final))
        modes.append(dict(newList=new,loopEntry=rows[1]['loopEntry'],continuedBody=continued,finalBody=final))
    return dict(countRange=[0,count_limit],counter='r12d',savedCount='rsi signed32',profiles=modes,
        noSignedCounterOverflow=True,
        invariant='At entry r12d=i, 0<=i<count. One exact child/Add preserves nonvolatiles and increments once; signed comparison exits iff i+1>=count, otherwise the exact EB returns to the identical body. R13 resets to zero before each comparison.',
        childABIAndTypedSpareCapacityRequired=True)


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context,clear_zero_program,bind_list_add_abi
    from scripts.game_data.memorypack.skill_root_buff_id_sources import derive as child_source
    from scripts.game_data.memorypack.skill_root_buff_id_transfer import derive as transfer_source
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.levelscript_two_routes_native import _window
    _publication_gate(image,pins);need('finite-positive-list-bound',True,type(count_limit)is int and 3<=count_limit<=10000)
    base=image.pe.image_base;ge=GenericEntries(image)
    context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=VALUE)
    def call(source,at):
        rows=[r for r in source['rows']if int(r['va'],16)==at]
        need('one-source-call',1,len(rows));raw=bytes.fromhex(rows[0]['bytes'])
        need('exact-owned-E8',(5,232),(len(raw),raw[0]));return control_transfer(rows[0])['target']
    s={k:call(body,body['pointer']+off)for k,off in dict(context=139,allocate=147,constructor=209,
        barrier=220,provider=260,dispatch=329,add=394).items()}
    # Actual reused-empty Clear lies in its owned cold fragment.
    branch=BytesPath(body['regions'],body['pointer']+120).relative('0f85')
    s['clear']=call(body,branch+59)
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    clear=ge.resolve(slots[2]['methodSpec'][0],[VALUE],[]);need('actual-closed-Clear',clear['pointer'],s['clear'])
    prefix=image.pe.bytes_at_va(s['clear'],19);need('actual-empty-Clear-JLE',b'\x7e',prefix[17:18])
    end=s['clear']+19+int.from_bytes(prefix[18:19],'little',signed=True)
    clear_program=clear_zero_program([(s['clear'],prefix),(end,image.pe.bytes_at_va(end,1))],s['clear'])
    clear_windows=[_window(image,s['clear'],s['clear']+19,'actual BuffId Clear selected prefix; no full extent'),
        _window(image,end,end+1,'actual BuffId Clear selected empty return')]
    ctor=owned(image,s['constructor']);s['arrayAllocate']=call(ctor,s['constructor']+132)
    need('same-capacity-context-helper',s['context'],call(ctor,s['constructor']+46))
    capacities=[capacity_program(ctor['regions'],s['constructor'],s,positive=p)for p in(False,True)]
    add=owned(image,s['add']);array_set=call(add,s['add']+65);setter=owned(image,array_set)
    add_program=add8_program(add['regions'],s['add'],array_set);set_program=array_set8_program(setter['regions'],array_set,s['barrier'])
    add_registration=ge.resolve(slots[6]['methodSpec'][0],[VALUE],[]);add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    offsets=scalar.reader_offsets(image,'buffIdList');offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    paths=[list8_program(body['regions'],body['pointer'],offsets,s,count=n,new=new)for n in range(-1,4)for new in(True,False)]
    certificate=induction(paths,count_limit=count_limit)
    child=child_source(image,pins);transfer=transfer_source(image,pins,child)
    need('same-selected-list-registration',context['registration'],transfer['registrations']['list'])
    for role in('provider','dispatch','barrier'):need('same-child-transfer:'+role,s[role]-base,transfer['symbolRvas'][role])
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier']);_publication_gate(image,pins)
    cap=value_capability()
    collection=dict(elementType=VALUE,closedListType=LIST,elementValueType=True,managedElementBytes=8,elementWireBytes=None,
        collectionCounts=[-1,0],positiveCountsAdmitted=True,countLimit=count_limit,nullable=True,
        elementCapability='skill-root-buff-id',elementGrammarAdmitted=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-buff-id-list.v1',nativeInputs=pins,status='validated-conditional-components',
        capabilities={'skill-root-buff-id':cap,'skill-root-buff-id-list':collection},proof=dict(context=context,programs=paths,
            induction=certificate,capacityPrograms=capacities,capacityWindows=ctor['windows'],
            clearRegistration=clear,clearProgram=clear_program,clearWindows=clear_windows,
            addRegistration=add_registration,addABI=add_abi,addProgram=add_program,addWindows=add['windows'],
            actualAddSourceIndependentlyProved=True,canonicalAddBodySemanticsUsed=False,
            arraySetProgram=set_program,arraySetWindows=setter['windows'],child=child,transfer=transfer,barrier=barrier,barrierProof=barrier_proof),
        evidenceBoundary=dict(exact='Current typed BuffId value-list count/null/empty/positive source, typed capacity, complete unchanged managed8 callback/Add/checked array store and bounded loop induction, independent MC1/pool4 child.',
            conditional=__doc__,structuralOnly='Stored buff identifier sequence.',
            unresolved=['enclosing field/owner framing','growth/nonempty existing Clear','runtime selection','physical EOF']))))
