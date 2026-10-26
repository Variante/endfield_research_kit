"""Exact ordinary-reference source attribution for three dropdown owners.

These projections retain the dedicated owners' four complete caller frames,
distinct caches, construction, getter and canonical adapter identities. They
do not turn a reference original into a value type or grant catalog, consumer,
child grammar or runtime callback admission. Native attribution requires a
fresh complete derivation of the same nominal owner.
"""
import hashlib,json


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogDropdownSource.'+check+':'+str(detail)[:700])


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def _types():
    from scripts.game_data.memorypack.skill_dropdown_blackboard_sources import TYPES
    from scripts.game_data.memorypack.skill_blowoff_priority_sources import TYPE,CAPABILITY
    return dict(TYPES,**{TYPE:CAPABILITY})


def project_record(record,pins,*,type_name):
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    known=_types();need('finite-nominal',type_name in known,type_name)
    cap=record.get('capability',{});proof=record.get('proof',{});scope=proof.get('scope',{})
    wrapper=cap.get('wrapperName');pair=proof.get('pair',{});programs=proof.get('programs',[])
    need('exact-reference-owner',cap.get('typeName')==type_name and isinstance(wrapper,str)and bool(wrapper)
        and scope.get('nativeInputs')==pins and bool(pins)and scope.get('wrappedType')==type_name
        and scope.get('wrapperName')==wrapper and scope.get('sourceScopeAdmitted')is True
        and all(cap.get(k)is True for k in('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
            'ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    need('all-four-owned-caller-frames',len(programs)==4
        and {(p.get('existing'),p.get('wrapperNull'))for p in programs}=={(False,False),(True,False),(False,True),(True,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool and p.get('selectedProgram')
            and p.get('frame',{}).get('entryRspRestored')is True
            and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in programs))
    for role in('constructor','factory','prehook'):
        selected=proof.get(role,{})
        need('complete-own-lifecycle:'+role,bool(selected.get('selectedBytes'))and selected.get('entryRspRestored')is True
            and(selected.get('normalReturn')is True or selected.get('normalReturnViaBarrier')is True))
    need('distinct-own-cache-getter-programs',{p.get('cacheState')for p in proof.get('ownGetterPrograms',[])}=={'coherent','empty','stale'}
        and all(p.get('typedCacheOffset')==40 and p.get('originalHolderOffset')==16 and p.get('normalReturn')is True
            and p.get('entryRspRestored')is True and p.get('selectedBytes')for p in proof['ownGetterPrograms']))
    registration=pair.get('registration',{})
    need('same-original-wrapper-pair',(registration.get('originalType'),registration.get('wrapperType'))==(type_name,wrapper))
    method=scope.get('method',[]);methods=pair.get('composition',{}).get('methods',[])
    need('own-static-reader-getter-formatter',len(method)==4 and method[1:3]==[wrapper,'Deserialize']
        and type(method[0])is int and type(method[3])is int and method[3]>0
        and len(methods)==2 and any(m[1:3]==[wrapper,'GetValue']for m in methods)
        and any(m[1].startswith(wrapper+'+')and m[2]=='Deserialize'for m in methods))
    need('same-canonical-adapter-static-reader',proof.get('adapter',{}).get('pairForwarder',{}).get('readerMethod')==method)
    return dict(schema='endfield.catalog-dedicated-reference-source-projection.v1',nativeInputs=dict(pins),
        wrapperName=wrapper,wrappedType=type_name,sourceKind='dedicated-reference-domain-source',
        maintainedOwner='scripts.game_data.memorypack.skill_blowoff_priority_sources'if type_name.endswith('+BlackboardCharBlowOffPriorityValue')
            else'scripts.game_data.memorypack.skill_dropdown_blackboard_sources',
        sourceMethods=[method]+methods,codeWindows=_source_windows(scope.get('codeWindows')),
        originalIsValueType=False,genericReferenceReaderApplicable=True,genericReferenceReaderUsed=False,
        genericNotApplicableClaimed=False,retainedSelectedSourceComplete=True,allFourCallerPathsProved=True,
        completeSelectedSourceAdmitted=False,nativeAttributionProved=False,childGrammarFromSourceAdmitted=False,
        currentConsumerAdmitted=False,catalogAdmitted=False,historicalAttributionHoldCleared=False,
        retainedSourceProofSha256=fingerprint(record),conditions=[
            'Exact own reference nominal, source windows, four caller frames, construction, distinct caches and canonical adapter.',
            'Initialized coherent compatible metadata/cache/literal cells, matching callbacks, normal typed allocations and helpers.',
            'Disabled collector and sufficiently buffered stable disjoint source, destination and frame storage.',
            'Independent current consumer, child grammar and exact native catalog semantic-role projections remain required.'])


def derive_current(image,pins,*,type_names):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import skill_dropdown_blackboard_sources as dropdown,skill_blowoff_priority_sources as blowoff
    need('finite-distinct-types',isinstance(type_names,list)and 0<len(type_names)<=3
        and len(set(type_names))==len(type_names)and set(type_names)<=set(_types()))
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);rows=[];sources=[]
    for name in type_names:
        need('actual-original-reference',ctx.is_value_type(name)is False,name)
        if name==blowoff.TYPE:
            fresh=blowoff.derive(image,pins)
            need('actual-blowoff-schema',fresh.get('schema')=='endfield.skill-blowoff-priority-sources.v1'
                and fresh.get('status')=='validated-conditional-blowoff-priority'and fresh.get('nativeInputs')==pins)
            record=dict(capability=fresh['capabilities'][blowoff.CAPABILITY],proof=fresh['proof'])
        else:
            fresh=dropdown.derive(image,pins,type_names=[name])
            need('actual-dropdown-schema',fresh.get('schema')=='endfield.skill-dropdown-blackboard-sources.v1'
                and fresh.get('status')=='validated-conditional-dropdown-blackboards'and fresh.get('nativeInputs')==pins)
            record=fresh['records'][name]
        row=project_record(record,pins,type_name=name)
        rows.append(dict(row,nativeAttributionProved=True,completeSelectedSourceAdmitted=True,
            currentSourceProofSha256=fingerprint(fresh),retainedSourceProofEqualityClaimed=False));sources.append(fresh)
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=rows,
        sourceCount=len(rows),fullCurrentOwnerSources=sources,retainedProgramProofsReused=False,
        sourceProgramSemanticsReproved=True,currentConsumersAdmitted=False,catalogsActivated=0,historicalAttributionHoldsCleared=0)
