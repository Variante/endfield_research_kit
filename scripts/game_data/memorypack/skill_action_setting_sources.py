"""Finite BuffIconDuration/KeywordEnhance settings with their actual children.

The MC2 duration selector stores its enum32 and pooled marker ID. The MC3
keyword edit stores an independently proved pooled-string list, enum32 and
ordinary BlackboardDouble reference. Neither an enum name nor a reference
stride supplies wire framing. Each current concrete new/existing/FF caller,
plain holder16 factory/getter and ordinary canonical adapter is freshly joined
to its exact typed child sources. Initialized coherent selected contexts,
normal compatible callbacks/allocations/helpers, disabled collector and stable
disjoint buffered storage remain conditions. Runtime enhancement/marker effects,
live selection and enclosing action/root/physical EOF remain unproved.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need

RECORDS={
    'Beyond.Gameplay.Core.BuffIconDurationSourceSetting':dict(capability='skill-buff-icon-duration-setting',
        wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffIconDurationSourceSettingForMemoryPack',
        members=(('durationSourceType','Beyond.Gameplay.Core.BuffIconDurationSourceType','enum32',None),
            ('timedMarkerId','string','byte-payload','byte-payload'))),
    'Beyond.Gameplay.Core.KeywordEnhanceEdit':dict(capability='skill-keyword-enhance-edit',
        wrapperName='Beyond.MemoryPack.Beyond_Gameplay_Core_KeywordEnhanceEditForMemoryPack',
        members=(('buffIds','System.Collections.Generic.List`1<string>','root-pooled-string-list','skill-root-pooled-string-list'),
            ('operationType','Beyond.Gameplay.Core.ModifyDynamicBlackboard+Data+OperationType','enum32',None),
            ('value','Beyond.Blackboard+BlackboardDouble','blackboard-double','scalar-payload'))),
}
REFERENCE='Beyond.Blackboard+BlackboardDouble'


def ordered_reads(type_name):
    return[dict(memberIndex=i,fieldName=n,kind=k,childCapability=c)for i,(n,t,k,c)in enumerate(RECORDS[type_name]['members'])]


def require_source(source,pins,type_name):
    need('setting-finite-nominal',True,type_name in RECORDS);spec=RECORDS[type_name]
    need('setting-complete-actual-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrappedType')==type_name and source.get('wrapperName')==spec['wrapperName']
        and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
        and source.get('wholeOwnerAdmitted')is False)
    need('setting-exact-member-declarations',[(n,t)for n,t,k,c in spec['members']],
        [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
    life=source['lifecycle']
    need('setting-owned-direct-holder',True,life.get('directHolderMode')is True and life.get('typedCache')is None
        and life.get('baseHolder')==[spec['wrapperName'],type_name,16])
    programs=source['programs']
    need('setting-four-complete-source-paths',True,len(programs)==4 and all(type(p.get('existing'))is bool
        and type(p.get('wrapperNull'))is bool and p.get('frame',{}).get('entryRspRestored')is True
        and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in programs)
        and{(p['existing'],p['wrapperNull'])for p in programs}=={(False,False),(True,False),(False,True),(True,True)})


def bind_program(type_name,compiled):
    expected=ordered_reads(type_name)
    wire=[dict(read,kind='scalar32'if read['kind']=='enum32'else read['kind'])for read in expected]
    need('setting-literal-count',True,type(compiled.get('memberCount'))is int and compiled['memberCount']==len(expected))
    need('setting-exact-compiled-child-program',True,compiled.get('reads')==wire
        and all(type(r.get('memberIndex'))is int for r in compiled['reads']))
    need('setting-exact-required-child-scope',sorted({r['childCapability']for r in expected if r['childCapability']is not None}),
        compiled['requiredCapabilities'])
    return expected


def _derive_on_children(image,pins,reference_children,*,type_names=None):
    """Caller freshly owns supplied ordinary children on this same image."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_reader_sources import derive_many
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_pooled_string_list_sources import derive as list_source
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.pointer_param import leaf
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    _publication_gate(image,pins);names=sorted(RECORDS)if type_names is None else list(type_names)
    need('setting-finite-distinct-selection',True,0<len(names)<=2 and len(set(names))==len(names)and set(names)<=set(RECORDS))
    factory_options={}
    if 'Beyond.Gameplay.Core.BuffIconDurationSourceSetting'in names:
        from scripts.game_data.memorypack.skill_icon_setting_factory_sources import prove
        factory_options['direct_factory_prover']=prove
    generated=derive_many(image,pins,[RECORDS[t]['wrapperName']for t in names],**factory_options)
    records={};caps={};identities={};collections={};required=set()
    for result,type_name in zip(generated['owners'],names,strict=True):
        if result['status']!='complete-reader-source-proved':
            raise ValueError('skillActionSetting.complete-reader:'+type_name+': '+str(dict(
                status=result['status'],reason=result.get('reason')))[:2600])
        source=result['proof'];require_source(source,pins,type_name);requests={};selected_lists={}
        for read in source['orderedSourceReads']:
            if not read['kind'].startswith('reference:'):continue
            index=read['memberIndex'];usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='skillActionSetting')
            requests[index]=usage
            if read['declaredType']=='System.Collections.Generic.List`1<string>':
                selected_lists[index]=list_source(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'])
                caps.update(selected_lists[index]['capabilities'])
        compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=type_name,value4={},
            references={REFERENCE:('skill-blackboard-double','blackboard-double','scalar-payload')},reference_children=reference_children,
            collections={'System.Collections.Generic.List`1<string>':('skill-root-pooled-string-list','root-pooled-string-list','skill-root-pooled-string-list')},
            typed_requests=requests,collection_children=selected_lists)
        need('setting-no-unproved-child',[],pending);order=bind_program(type_name,compiled);required.update(compiled['requiredCapabilities'])
        for binding in compiled['childBindings']:
            if 'collectionIdentity'in binding:collections[binding['capability']]=binding['collectionIdentity']
        if any(r['kind']=='blackboard-double'for r in order):
            child=reference_children[REFERENCE]['capabilities']['skill-blackboard-double']
            identities['scalar-payload']={k:child[k]for k in('typeName','referenceReaderMethodDefinition','referenceReaderTargetRva')}
        wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==source['wrapperName']]
        pair=derive_pair(image,type_name,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
        need('setting-same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
        need('setting-same-owned-reader',source['method'],adapter['pairForwarder']['readerMethod'])
        getter=leaf(image,image.pe.image_base+adapter['getterMethod'][3],['488B4110','C3'])
        cap=dict(typeName=type_name,wrapperName=wrapper.name,memberCount=len(order),nullMarker=255,nullAdmitted=True,nullable=True,
            wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
            ownConcreteFactorySemanticsProved=True,orderedReads=order,completeSourceOwnedProgram=True,
            callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
        caps[RECORDS[type_name]['capability']]=cap
        records[type_name]=dict(source=source,compiled=compiled,typedRequests=requests,listChildren=selected_lists,pair=pair,adapter=adapter,getter=getter)
    reader=reference_reader_abi(image,pins)
    for type_name in names:caps[RECORDS[type_name]['capability']].update({k:reader[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-action-setting-sources.v1',status='validated-conditional-action-settings',nativeInputs=pins,
        capabilities=caps,requiredExternalCapabilities=sorted(required),requiredExternalCapabilityIdentities=identities,
        requiredExternalCollectionIdentities=collections,proof=dict(records=records,referenceReaders=reader,referenceChildren=reference_children),
        wholeSkillDataAdmitted=False,evidenceBoundary=dict(exact='Finite MC2/MC3 complete selected caller/new/existing/FF/frame, named ordinary holder/getter/factory and canonical adapters, exact primitive/pool and nominal typed collection/reference child joins.',
            conditional=__doc__,structuralOnly='Stored duration selectors and keyword enhancement edits.',
            unresolved=['actual enclosing action/list/union joins','runtime duration/enhancement semantics/provider selection','cold/refill/error paths','whole root/physical EOF']))))


def derive(image,pins,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);names=sorted(RECORDS)if type_names is None else list(type_names)
    need('setting-finite-distinct-selection',True,0<len(names)<=2 and len(set(names))==len(names)and set(names)<=set(RECORDS))
    references={}
    if 'Beyond.Gameplay.Core.KeywordEnhanceEdit'in names:
        from scripts.game_data.memorypack.skill_blackboard_double_sources import derive as child_source
        references[REFERENCE]=child_source(image,pins)
    return _derive_on_children(image,pins,references,type_names=names)
