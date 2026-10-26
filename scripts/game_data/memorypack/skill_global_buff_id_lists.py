"""Exact GlobalBuffId value8 list with independently owned MC1 wire values.

The actual closed nominal ListFormatter and ReadPackable request select a
called signed4 collection-header source. Fresh typed capacity or reused empty
storage, zero8 callback output, the selected canonical GlobalBuffId dispatch,
unchanged QWORD Add/checked array store and one-counter loop have separate
programs. Managed8 is never consumed as wire width: the own child is MC1/pool4
or FF/default8. This is no BuffId list alias. Ready coherent nominal contexts,
the compared canonical callback, normal typed allocation/helpers, spare
capacity, disabled collector and disjoint stable buffered storage are
conditions. Nonempty reuse/growth/refill, live provider selection, enclosing
field/action/union/root and physical EOF remain unresolved.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.GlobalBuffId'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAPABILITY='skill-action-global-buff-id-list'
ELEMENT='skill-global-buff-id'


def list_program(regions,entry,s,*,count=1,new=True):
    need('GlobalId-list-literal-path',True,type(count)is int and count in(-1,0,1,2,3)and type(new)is bool)
    g=BytesPath(regions,entry);g.take('4056','57','4155','4156','4883ec38');ready=flag(g)
    g.take('498bf9','498bf0','4c8bf2');g.branch('0f84',False)
    g.take('4533ed','488d542468','498bce','44896c2468','4c896c2420');g.call(s['header'])
    g.take('84c0');g.branch('0f84',count==-1);loop=None;parts=[];callbacks=[];adds=[];provider_cell=None
    if count==-1:
        g.take('488bce','4c892e');g.call(s['barrier']);g.take('90');g.jump('e9')
    else:
        g.take('48896c2470','48895c2460','4c89642478','4c897c2430','8b6c2468','4c392e');g.branch('0f85',not new)
        if new:
            g.take('488b4f20','33d2','488b89c0000000');g.call(s['context'])
            g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
            g.take('488b4f20','488b91c0000000','488b4a08','4c396920');g.branch('0f84',False)
            g.take('488b4720','8bd5','488bcb','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
            g.take('488bce','48891e');g.call(s['barrier'])
        else:
            g.take('488b4720','488b1e','488b90c0000000','488b4210','4c396820');g.branch('75',True,1)
            g.take('488b4720','488bcb','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
        provider_cell=g.relative('488b0d');g.take('4439a9e0000000');g.branch('0f84',False)
        g.take('488b4720','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('4c8bf8','458be5','85ed');g.branch('7e',count==0,1)
        if count:
            loop=g.at
            for i in range(count):
                need('GlobalId-list-same-loop-entry',loop,g.at);before=len(g.seen)
                g.take('4c896c2420','4d85ff');g.branch('74',False,1)
                g.take('4c8d4c2420','4d8bc6','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
                g.take('4c8b2e','488b5c2420','4d85ed');g.branch('74',False,1)
                g.take('488b4720','488b90c0000000','488b4230','4883782000');g.branch('0f84',False)
                g.take('488b4720','488bd3','498bcd','4c8b80c0000000','4d8b4030');adds.append(g.at);g.call(s['add'])
                g.take('41ffc4','41bd00000000','443be5');g.branch('7c',i+1<count,1);parts.append(g.seen[before:])
        g.take('4c8b642478','488b5c2460','4c8b7c2430','488b6c2470')
    g.take('4883c438','415e','415d','5f','5e','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,countWitness=count,newList=new,headerBytes=4,
        managedElementBytes=8,elementWireBytes=None,loopEntry=loop,loopBodies=parts,callbackSites=callbacks,addCallSites=adds,
        providerClassCell=provider_cell,savedCount='unchanged signed32 EBP from header local+104',counter='R12D initialized0, incremented once',
        callbackOutput='zero8 frame+32',addArguments=dict(rcx='same list',rdx='same whole returned QWORD',r8='own List<GlobalBuffId>.Add MethodInfo'),
        normalReturn=True,entryRspRestored=True)


def capacity_program(regions,entry,s,*,positive):
    need('GlobalId-list-literal-capacity',True,type(positive)is bool)
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','8bda','498bf8','488bf1','85d2');g.branch('0f88',False)
    g.take('498b4820','488b89c0000000');g.branch('74',not positive,1)
    if positive:
        g.take('ba01000000');g.call(s['context']);g.take('8bd3','488bc8');g.call(s['arrayAllocate'])
    else:
        g.take('33d2');g.call(s['context']);g.take('83b8e000000000');g.branch('74',False,1)
        g.take('488b4f20','33d2','488b89c0000000');g.call(s['context']);g.take('488b88b8000000','488b01');g.jump('eb',1)
    g.take('488d4e10','48894610','488b5c2430','488b742438','4883c420','5f');need('GlobalId-list-capacity-tail',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,positive=positive,capacityPassedUnchanged=True,
        arrayClassContextSlot=1,zeroArrayClassContextSlot=0,listArrayOffset=16,
        normalReturnViaBarrier=True,entryRspRestored=True,zeroedFreshListRequired=True)


def induction(programs,count_limit):
    need('GlobalId-list-bounded-induction',True,type(count_limit)is int and 3<=count_limit<=10000);profiles=[]
    for new in(True,False):
        rows={n:next(p for p in programs if p['newList']is new and p['countWitness']==n)for n in range(4)}
        need('GlobalId-list-zero-no-elements',(True,[]),(rows[0]['normalReturn'],rows[0]['callbackSites']))
        body=rows[1]['loopBodies'][0]
        need('GlobalId-list-identical-positive-bodies',[[body]*n for n in(1,2,3)],[rows[n]['loopBodies']for n in(1,2,3)])
        need('GlobalId-list-one-increment-and-count-compare',(1,1,1),tuple(sum(h==raw for at,h in body)for raw in('41ffc4','443be5','7c')))
        profiles.append(dict(newList=new,loopEntry=rows[1]['loopEntry'],body=body))
    return dict(countRange=[0,count_limit],profiles=profiles,counter='R12D',savedCount='signed32 EBP',noSignedCounterOverflow=True,
        invariant='At loop entry R12D=i, 0<=i<count. One exact child/Add stores the complete QWORD and increments once; signed JL returns to the identical body iff i+1<count. R13 is reset0 after each iteration. Child/helpers preserve selected nonvolatiles; typed capacity/disjoint storage remain required.')


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_value_list_context import derive as context_source,clear_zero_program,bind_list_add_abi
    from scripts.game_data.memorypack.skill_root_buff_id_lists import add8_program,array_set8_program
    from scripts.game_data.memorypack.skill_global_buff_id_sources import derive as child_source
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.npc_collection_sources import _collection_header
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack import scalar_param_native as scalar
    _publication_gate(image,pins);need('GlobalId-list-resource-bound',True,type(count_limit)is int and 3<=count_limit<=10000)
    base=image.pe.image_base;context,body=context_source(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    def call(source,offset):
        rows=[r for r in source['rows']if int(r['va'],16)==source['pointer']+offset]
        need('GlobalId-list-owned-E8',True,len(rows)==1 and len(bytes.fromhex(rows[0]['bytes']))==5 and bytes.fromhex(rows[0]['bytes'])[0]==232)
        return control_transfer(rows[0])['target']
    s={role:call(body,off)for role,off in dict(header=54,context=113,allocate=121,constructor=183,barrier=194,provider=234,dispatch=270,add=335).items()}
    reused=BytesPath(body['regions'],body['pointer']+94).relative('0f85');s['clear']=call(dict(body,pointer=reused),59)
    prefix=image.pe.bytes_at_va(s['clear'],19);need('GlobalId-list-empty-Clear-branch',b'\x7e',prefix[17:18])
    clear_end=s['clear']+19+int.from_bytes(prefix[18:19],'little',signed=True)
    clear_regions=[(s['clear'],prefix),(clear_end,image.pe.bytes_at_va(clear_end,1))];clear=clear_zero_program(clear_regions,s['clear'])
    ctor=owned(image,s['constructor']);s['arrayAllocate']=call(ctor,59)
    need('GlobalId-list-same-capacity-context-helper',s['context'],call(ctor,49))
    capacities=[capacity_program(ctor['regions'],ctor['pointer'],s,positive=n)for n in(False,True)]
    add=owned(image,s['add']);array_set=call(add,65);array_body=owned(image,array_set)
    add_program=add8_program(add['regions'],add['pointer'],array_set);array_program=array_set8_program(array_body['regions'],array_set,s['barrier'])
    slots={r['relativeSlot']:r for r in context['context']['entries']};add_abi=bind_list_add_abi(image,slots[6]['methodSpec'][0])
    offsets=scalar.reader_offsets(image,'GlobalBuffIdList');offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    header=_collection_header(image,s['header'],offsets)
    programs=[list_program(body['regions'],body['pointer'],s,count=n,new=new)for n in range(-1,4)for new in(True,False)]
    loop=induction(programs,count_limit);child=child_source(image,pins);fact=child['proof']['reviewedNominalSource']
    for role in('provider','dispatch','barrier'):
        need('GlobalId-list-own-independently-proved-actual-helper:'+role,base+fact['symbols'][role],s[role])
    provider,=[c for c in fact['contexts']if c['methodName']=='GetFormatter']
    need('GlobalId-list-actual-provider-formal-method',provider['definition'],slots[3]['methodSpec'][0])
    barrier,barrier_program,_=_fast_barrier(image,s['barrier'])
    def window(at,raw,boundary):return dict(startRva=at-base,endRva=at-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),boundary=boundary)
    cap=dict(elementType=TYPE,elementValueType=True,managedElementBytes=8,elementWireBytes=None,closedListType=LIST,
        collectionCounts=[-1,0],countLimit=count_limit,positiveCountsAdmitted=True,nullable=True,elementCapability=ELEMENT,elementGrammarAdmitted=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,callbackSelectionConditional=True,wholeOwnerAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-global-buff-id-list.v1',status='validated-conditional-global-buff-id-list',nativeInputs=pins,
        capabilities={**child['capabilities'],CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],proof=dict(context=context,programs=programs,
            induction=loop,collectionHeader=header,collectionHeaderWindows=owned(image,s['header'])['windows'],
            capacities=capacities,capacityWindows=ctor['windows'],clear=clear,clearWindows=[window(a,b,'actual selected initially-empty Clear prefix/return; physical extent unproved')for a,b in clear_regions],
            add=add_program,addABI=add_abi,addWindows=add['windows'],arraySet=array_program,arraySetWindows=array_body['windows'],
            child=child,actualHelperBindings={k:v-base for k,v in s.items()},barrier=barrier,barrierProgram=barrier_program),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Actual nominal closed list/context, signed4 header, null/empty/positive source, typed capacity, whole managed8 canonical callback/Add/checked store, bounded loop and separate GlobalBuffId MC1 child.',
            conditional=__doc__,structuralOnly='Stored global buff identifier collection.',unresolved=['enclosing parent/union/root/EOF','runtime provider/callback choice','nonempty reused Clear/growth/refill']))))
