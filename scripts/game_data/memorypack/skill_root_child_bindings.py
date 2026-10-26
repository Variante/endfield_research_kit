"""Exact current root-child source joins, independent of child names or widths.

A previously proved caller contributes its actual nominal MethodSpec and E8
target. A freshly proved child contributes the matching reader definition,
target, selected native inputs and explicit positive grammar admission. This
join never treats two body addresses as aliases or infers a child grammar from
an Original/wrapper registration. It records structural stored configuration;
runtime callback selection and enclosing root/EOF remain separate.
"""
from scripts.game_data.memorypack import scalar_param_native as scalar

LABEL='skillRootChildBindings'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def bind_read_value(pins,join,child,capability):
    """Join a source-owned field to exactly one ordinary reference child."""
    need('same-child-native-inputs',pins,child['nativeInputs'])
    cap=child['capabilities'][capability];usage=join['typedRequest']
    need('positive-child-grammar',True,cap.get('wholeGrammarAdmitted')is True)
    need('ordinary-reference-child',True,cap.get('ordinaryOriginalReadValueAdmitted',True)is True)
    need('actual-reference-type',join['typeName'],cap['typeName'])
    need('actual-reference-request',('MemoryPack.MemoryPackReader','ReadValue',[],[cap['typeName']]),
        tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
    need('literal-reference-reader-identity',True,
        type(cap.get('referenceReaderMethodDefinition'))is int and type(cap.get('referenceReaderTargetRva'))is int)
    need('actual-reference-method-definition',usage['methodSpec'][0],cap['referenceReaderMethodDefinition'])
    need('actual-reference-call-target',join['sourceTargetRva'],cap['referenceReaderTargetRva'])
    return dict(fieldName=join['fieldName'],typeName=cap['typeName'],capability=capability,
        readerMethodDefinition=cap['referenceReaderMethodDefinition'],sourceTargetRva=cap['referenceReaderTargetRva'])


def collection_identity(child,capability):
    """Finite source-owned list scope; a list is not an ordinary record cap."""
    from scripts.game_data.memorypack.skill_root_children_codec import LISTS,POOLED_STRINGS
    cap=child['capabilities'][capability]
    if capability=='skill-look-at-target-info-list':
        from scripts.game_data.memorypack.skill_look_at_target_codec import require_collection,require_record
        from scripts.game_data.memorypack.skill_look_at_target_sources import CAPABILITY
        require_collection(cap);require_record(child['capabilities'].get(CAPABILITY,{}))
    if capability.startswith('skill-enum-list:'):
        from scripts.game_data.memorypack.skill_enum_list_codec import require_capability,element_capability
        nominal=capability.removeprefix('skill-enum-list:')
        require_capability(cap,child['capabilities'].get(element_capability(nominal),{}),name=nominal)
    if capability==POOLED_STRINGS:expected=('string',False,'byte-payload',10000)
    else:
        need('allowlisted-collection-capability',True,capability in LISTS)
        expected=LISTS[capability]
    element,value,element_cap,limit=expected
    need('exact-owned-collection-element',(element,value,element_cap),tuple(cap.get(k)for k in
        ('elementType','elementValueType','elementCapability')))
    need('literal-collection-flags',True,all(type(cap.get(k))is bool for k in
        ('elementValueType','nullable','positiveCountsAdmitted','elementGrammarAdmitted')))
    need('complete-positive-collection',True,all(cap[k]is True for k in
        ('nullable','positiveCountsAdmitted','elementGrammarAdmitted')))
    need('exact-closed-collection-type','System.Collections.Generic.List`1<'+element+'>',cap.get('closedListType'))
    need('signed-null-empty-collection-counts',True,cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts']))
    need('independently-bounded-collection-count',True,type(cap.get('countLimit'))is int and 1<=cap['countLimit']<=limit)
    need('literal-collection-reader-identity',True,type(cap.get('packableReaderMethodDefinition'))is int
        and cap['packableReaderMethodDefinition']>=0 and type(cap.get('packableReaderTargetRva'))is int
        and cap['packableReaderTargetRva']>0)
    if capability==POOLED_STRINGS:
        need('exact-pooled-string-collection',True,cap.get('stringEncoding')=='int32-pool-index'
            and type(cap.get('elementWireBytes'))is int and cap['elementWireBytes']==4
            and type(cap.get('elementManagedReferenceBytes'))is int and cap['elementManagedReferenceBytes']==8)
    shape=None if element_cap=='byte-payload'else child['capabilities'][element_cap]
    keys=('closedListType','elementType','elementValueType','packableReaderMethodDefinition','packableReaderTargetRva',
        'collectionCounts','countLimit','positiveCountsAdmitted','nullable','elementCapability','elementGrammarAdmitted')
    return dict(**{key:cap[key]for key in keys},elementCapabilityShape=shape)


def bind_read_packable_list(pins,join,child,capability):
    """Own actual ReadPackable<List<T>> identity without a ReadValue alias."""
    need('same-list-child-native-inputs',pins,child['nativeInputs']);identity=collection_identity(child,capability)
    usage=join['typedRequest'];nominal=identity['closedListType']
    need('actual-list-nominal',nominal,join['typeName'])
    need('actual-list-request',(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]),
        tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments')))
    need('actual-list-definition',identity['packableReaderMethodDefinition'],usage['methodSpec'][0])
    need('literal-actual-list-target',True,type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']>0)
    need('actual-list-call-target',identity['packableReaderTargetRva'],join['sourceTargetRva'])
    return dict(fieldName=join['fieldName'],typeName=nominal,capability=capability,
        readerMethodDefinition=identity['packableReaderMethodDefinition'],sourceTargetRva=identity['packableReaderTargetRva'],
        collectionIdentity=identity)


def reference_reader_abi(image,pins):
    """Independently owned ordinary ReadValue/ReadPackable reference sources."""
    import copy
    import json
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.memorypack import modelview_packable_sources,buff_ec_profiles_native as ec
    core=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())
    reference=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
    need('generic-packable-build',pins,core['nativeInputs']);need('generic-reference-build',pins,reference['nativeInputs'])
    routes=copy.deepcopy(reference['declarations']['adapters']['referenceRoutes']);routes['wrappers']=[]
    readers=modelview_packable_sources.validate_components(image,pins,core['readPackable'],routes)
    clones=ec.clone_facts(image,pins);read=clones['ReadValue']
    need('reference-result-ABI','reference',read['resultAbi'])
    return dict(genericReaders=readers,referenceClones=clones,
        referenceReaderMethodDefinition=read['equivalentMethod'][0],referenceReaderTargetRva=read['targetRva'])


def reference_record_abi(image,pins,record):
    """Compose a freshly source-proved plain holder16 record with its adapter.

    The caller must derive ``record`` itself on this image. Its complete source
    programs and direct holder getter/constructor supply concrete semantics;
    this function rechecks the exact pair, getter target and generic bodies.
    This result alone admits none of the record's delegated child grammars.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    need('complete-plain-source-paths',[record['memberCount'],record['memberCount'],None],
        [p['memberCount']for p in record['programs']])
    need('plain-source-normal-returns',True,all(p['normalReturn']is True for p in record['programs']))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==record['wrapperName']]
    need('same-nominal-source-wrapper',record['typeName'],wrapper.wrapped_type)
    adapter=derive_adapter(image,pins,record['registeredPair'],wrapper)
    need('same-source-owned-GetValue',record['getter']['entryRva'],adapter['getterMethod'][3])
    getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
    need('same-complete-plain-getter',record['getter'],getter)
    reader=reference_reader_abi(image,pins)
    _publication_gate(image,pins)
    return dict(adapter=adapter,**reader,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        childGrammarsAdmitted=False)
