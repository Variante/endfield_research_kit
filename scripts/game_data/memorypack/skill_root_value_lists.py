"""Positive selected List<DataPair> framing, with its own managed32 child.

The closed value-element formatter consumes a signed four-byte count, passes
that same positive count to the exact List constructor's owned array context,
and repeats its identical callback/copy/store loop to the saved count. Both new
and initially empty existing lists are covered under normal typed zeroed
allocation, matching initialized contexts and enough capacity. The 32-byte
array stride and two-chunk callback output are managed ABI facts; each element
instead consumes the independently proved DataPair MC4 wire program or FF.
Growth, nonempty Clear, malformed/refill paths and live formatter selection are
unresolved. This component neither admits another value list by its width nor
grants an enclosing root, runtime execution or physical EOF.
"""
from __future__ import annotations

import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillRootValueLists'
CAPABILITY='skill-root-data-pair-list-positive'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def data_pair_positive_program(regions,entry,offsets,s,*,iterations=1,new=True):
    """One and two witnesses establish the identical finite count/loop body."""
    need('explicit-loop-witness',True,type(iterations)is int and iterations in(1,2))
    need('literal-new-path',True,type(new)is bool)
    g=BytesPath(regions,entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('4053','55','56','4154','4156','4883ec70','837a'+rem+'04','0f57c0','0f11442450',
        '4d8bf1','4d8be0','0f11442460','488bf2');g.branch('0f8c',False)
    g.take('488b46'+cur,'8b28','8b5e'+rem,'83c3fc');g.branch('0f88',False)
    g.take('488346'+cur+'04','8346'+adv+'04','8346'+used+'04','895e'+rem,
        '486346'+used,'488b4e'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False)
    g.take('4889bc24a0000000','83fdff');g.branch('0f84',False)
    g.take('4c89ac24a8000000','4c89bc24b0000000','49833c2400');g.branch('0f85',not new)
    if new:
        g.take('498b4e20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('0f84',False)
        g.take('498b4e20','488b91c0000000','488b4a08','4883792000');g.branch('0f84',False)
        g.take('85ed');g.branch('0f88',False)
        g.take('498b4620','488b88c0000000','488b7908','488b4720','488b88c0000000');g.branch('0f85',True)
        g.take('ba01000000');g.call(s['context'])
        g.take('488bd5','488bc8');allocation=g.at;g.call(s['arrayAllocate']);g.jump('e9')
        g.take('488d4b10','48894310');g.call(s['barrier'])
        g.take('498bcc','49891c24');g.call(s['barrier'])
    else:
        allocation=None
        g.take('498b4620','498b1c24','488b88c0000000','488b4110','4883782000');g.branch('75',True,1)
        g.take('498b4620','488bcb','488b90c0000000','488b5210');g.call(s['clear']);g.take('90');g.jump('e9')
    provider_site=g.at;provider_cell=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('0f84',False)
    g.take('498b4620','488b88c0000000','488b4918');g.call(s['provider'])
    g.take('33ff','4c8bf8','85ed');g.branch('7f',True,1)
    loop=g.at;prefix=list(g.seen);bodies=[];callbacks=[];backedge=None
    for i in range(iterations):
        need('same-owned-loop-entry',loop,g.at);before=len(g.seen)
        g.take('0f57c0','0f11442450','0f11442460','4d85ff');g.branch('0f84',False)
        g.take('4c8d4c2450','4c8bc6','498bd7');callbacks.append(g.at);g.call(s['dispatch'])
        g.take('0f10442450','498b1c24','0f104c2460','0f11442420','0f114c2430','4885db')
        g.branch('0f84',False)
        g.take('498b4620','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
        g.take('498b4620','488b5310','488b88c0000000','4c8b6930','ff431c','4885d2');g.branch('0f84',False)
        g.take('48634b18','3b4a18');g.branch('73',False,1)
        g.take('8d4101','894318','3b4a18');g.branch('0f83',False)
        g.take('488d4101','48ffc1','48c1e005','48c1e105','4803ca','0f110410','0f114c1010')
        g.call(s['barrier']);g.take('ffc7','3bfd');backedge=g.at;g.branch('0f8c',i+1<iterations)
        bodies.append(g.seen[before:])
    g.jump('e9')
    g.take('4c8bac24a8000000','4c8bbc24b0000000','488bbc24a0000000',
        '4883c470','415e','415c','5e','5d','5b','c3')
    if iterations==2:need('identical-complete-second-loop',bodies[0],bodies[1])
    return dict(selectedBytes=g.seen,prefix=prefix,loopBodies=bodies,loopEntry=loop,loopBackEdge=backedge,
        newList=new,countWitness=iterations,headerBytes=4,signedCountBits=32,
        savedCount='ebp',index='edi initialized zero; INC followed by signed compare to unchanged ebp',
        callbackSites=callbacks,callbackAbi=dict(rdx='same selected formatter',r8='same Reader',r9='local zero32 output'),
        callbackManagedBytes=32,elementWireBytes=None,arrayDataOffset=32,arrayStride=32,
        copiedChunkOffsets=[0,16],listOffsets=dict(items=16,count=24,version=28,arrayLength=24),
        listCountIncrementEachIteration=True,versionIncrementEachIteration=True,
        positiveAllocationSite=allocation,capacityPassedFromSavedCount=new,
        arrayTypeContextSlot=1,providerSite=provider_site,providerCell=provider_cell,
        normalReturn=True,entryRspRestored=True,positiveGrowthPathAdmitted=False,
        condition='Positive signed count within the declared cap, matching closed DataPair contexts, selected nominal value32 callback and normal helpers. New typed allocation is zeroed with capacity exactly the unchanged saved count; existing list has size0 and capacity at least that count. Sufficient buffered disjoint Reader/source/output/frame, valid arrays and disabled or compatible value barriers are required.')


def _derive_collection(image,pins,collection,*,count_limit=4096):
    """Compose a freshly source-proved selected list with its own child."""
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_root_prefix_sources import PAIR,PAIR_LIST
    from scripts.game_data.memorypack.skill_root_value_dispatch import derive_data_pair_child
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs
    from scripts.game_data.memorypack.pointer_param import owned
    selected_inputs(pins);need('positive-count-limit',True,type(count_limit)is int and 1<=count_limit<=4096)
    need('same-list-component-pins',pins,collection['nativeInputs'])
    ctx=NativeReferenceContext(image);base=image.pe.image_base
    need('exact-value-element',(PAIR,True),(collection['elementType'],collection['elementValueType']))
    entry=collection['registration'];image.check_windows(collection['sourceWindows'],label=LABEL+'.list')
    td=ctx.index.types['MemoryPack.Formatters.ListFormatter`1']
    method,=[m for m in image.metadata.methods_for(td)if image.metadata.string(m.name_index)=='Deserialize']
    fresh=GenericEntries(image).resolve(method.index,[PAIR],[])
    need('fresh-same-closed-list-entry',json.loads(json.dumps(fresh)),entry)
    source=owned(image,fresh['pointer']);rows={int(r['va'],16):r for r in source['rows']}
    def call(offset):
        row=rows[source['pointer']+offset];raw=bytes.fromhex(row['bytes'])
        need('positive-list-direct-call',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    s={k:base+v for k,v in collection['helperRvas'].items()}
    s.update(arrayAllocate=call(631),dispatch=call(449))
    offsets=scalar.reader_offsets(image,LABEL);offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[data_pair_positive_program(source['regions'],source['pointer'],offsets,s,iterations=n,new=new)
        for new in(True,False)for n in(1,2)]
    child_component=derive_data_pair_child(image,pins)
    child=child_component['proof']['child'];transfer=child_component['proof']['transfer']
    need('same-selected-list',entry,transfer['listRegistration'])
    for role in('dispatch','provider','barrier'):
        need('same-positive-list-child-helper:'+role,s[role]-base,transfer['symbolRvas'][role])
    child_cap=child_component['capabilities']['skill-root-data-pair']
    list_cap=dict(elementType=PAIR,closedListType=PAIR_LIST,elementValueType=True,
        collectionCounts=[-1,0],positiveCountsAdmitted=True,countLimit=count_limit,nullable=True,
        elementCapability='skill-root-data-pair',elementGrammarAdmitted=True,
        packableReaderMethodDefinition=collection['typedRequest']['methodSpec'][0],
        packableReaderTargetRva=collection['callTargetRva'],managedElementBytes=32,
        elementWireBytes=None,wholeSkillDataAdmitted=False)
    return json.loads(json.dumps(dict(schema='endfield.skill-root-data-pair-list-positive.v1',
        status='validated-conditional-components',nativeInputs=pins,
        capabilities={'skill-root-data-pair':child_cap,CAPABILITY:list_cap},
        proof=dict(nullEmptyCollection=collection,positivePrograms=programs,child=child,transfer=transfer),
        evidenceBoundary=dict(exact='Own closed value-element list, typed capacity array context, signed count/callback32/copy32/spare-capacity store loop and exact loop backedge/return; independent DataPair MC4/FF wrapper, canonical value adapter and unchanged hidden32 GetValue conversion.',
            conditional=__doc__,structuralOnly='Stored root blackboard configuration does not prove runtime skill execution.',
            unresolved=['nonempty existing list Clear','list growth/refill/malformed paths','live formatter/MethodInfo selection','enclosing root/physical EOF']))))


def derive(image,pins,*,prefix=None,count_limit=4096):
    """Legacy root entry: its caller still independently proves root field3."""
    from scripts.game_data.memorypack.skill_root_prefix_sources import derive as prefix_source
    prefix=prefix_source(image,pins)if prefix is None else prefix
    need('same-prefix-pins',pins,prefix['nativeInputs'])
    return _derive_collection(image,pins,prefix['proof']['dataPairList'],count_limit=count_limit)


def derive_data_pair_list_component(image,pins,*,typed_request,call_target,count_limit=4096):
    """Caller-agnostic exact DataPair list; parent ownership is never borrowed.

    The supplied actual typed request and E8 target freshly select the nominal
    value-element count/constructor/Clear source. Positive callback32/copy32,
    Add/count loop and MC4/FF/default-zero32 child are then independently proved.
    The enclosing owner must prove its own field, cursor and returned-reference
    transfer; no Skill root or Patrol caller is admitted by this entry point.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_root_prefix_sources import derive_data_pair_list
    _publication_gate(image,pins)
    need('positive-count-limit',True,type(count_limit)is int and 1<=count_limit<=4096)
    # The legacy prefix returns a JSON declaration. Preserve that exact shape
    # at this new direct boundary too, before strict full-entry comparison.
    collection=json.loads(json.dumps(derive_data_pair_list(image,pins,typed_request,call_target)))
    result=_derive_collection(image,pins,collection,count_limit=count_limit)
    result.update(schema='endfield.data-pair-list-component.v1',parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    result['evidenceBoundary']=dict(result['evidenceBoundary'],structuralOnly='Stored DataPair collection; no enclosing owner or runtime interpretation.',
        unresolved=['actual enclosing typed field/cursor/returned-reference join','nonempty existing list Clear','list growth/refill/malformed paths','live formatter/MethodInfo selection','whole owner/physical EOF'])
    _publication_gate(image,pins);return result
