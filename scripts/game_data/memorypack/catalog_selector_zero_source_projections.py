"""Dedicated zero-selector reader attribution for current catalog review.

The concrete union caller owns this reader path independently of an Original
generic formatter. A generic reference-reader refusal cannot erase this exact
path, or grant that other path. Consumer and catalog roles remain separate.
"""
import hashlib
import json

NAMES={
    'Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_CharacterTeamFinder_DataForMemoryPack':
        ('SelectorFinder',2,'Beyond.Gameplay.Core.Selector+CharacterTeamFinder+Data'),
    'Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_MainCharacterValidator_DataForMemoryPack':
        ('SelectorValidator',10,'Beyond.Gameplay.Core.Selector+MainCharacterValidator+Data'),
}


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogSelectorZeroSource.'+check+':'+str(detail)[:800])


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def project(component,pins,reader_method,*,image_base):
    """Validate the complete dedicated source; pure projection is not admission."""
    name=component.get('wrapperName')
    if name not in NAMES:return NotImplemented
    family,tag,original=NAMES[name]
    need('exact-owned-nominal',bool(pins)and component.get('family')==family and component.get('tag')==tag
        and component.get('wrappedType')==original and component.get('memberCount')==0
        and component.get('wrapperNullAdmitted')is True
        and component.get('originalRegistrationRequiredByThisCaller')is False)
    need('actual-static-reader',isinstance(reader_method,list)and len(reader_method)==4
        and reader_method[1:3]==[name,'Deserialize']and type(reader_method[0])is int
        and type(reader_method[3])is int and reader_method[0]>=0 and reader_method[3]>0
        and type(image_base)is int and image_base>0)
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    windows=_source_windows(component.get('readerWindows'))
    need('reader-entry-owned',any(w['startRva']==reader_method[3]for w in windows))
    formatter=component.get('concreteFormatter',{});method=formatter.get('method',[])
    forward=formatter.get('program',{})
    need('own-concrete-formatter-forwarder',len(method)==4 and method[1].startswith(name+'+')
        and method[2]=='Deserialize'and forward.get('completeOriginalForwarderChecked')is True
        and forward.get('conditionalReaderAndOutputForwardingProved')is True
        and forward.get('actualReaderTailcall',{}).get('target')==image_base+reader_method[3])
    _source_windows(formatter.get('windows'))
    programs=component.get('programs',[])
    need('complete-three-source-paths',len(programs)==3
        and {(p.get('allocated'),p.get('wrapperNull'))for p in programs}=={(False,False),(False,True),(True,False)}
        and all(type(p.get('allocated'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('selectedBytes')and p.get('normalReturn')is True and p.get('entryRspRestored')is True
            and p.get('positiveMemberCount')==(None if p['wrapperNull']else 0)for p in programs))
    holder=component.get('holder',{})
    need('own-ancestral-holder',holder.get('concreteOriginalType')==original and holder.get('offset')==16
        and holder.get('originalAncestry',[None])[0]==original)
    for key in('coherentCachedGetter','coherentPrehook'):
        owned=component.get(key,{})
        need('independent-'+key,bool(owned.get('program',{}).get('selectedBytes')))
        _source_windows(owned.get('windows'))
    factories=component.get('factories',[])
    need('both-owned-factories',len(factories)==2
        and {f.get('method',[None,None,None])[2]for f in factories}=={'.ctor','CreateInstance'})
    for factory in factories:
        need('whole-factory-tail',factory['method'][1]==name and factory.get('program',{}).get('selectedBytes')
            and factory['program'].get('normalReturnViaBarrier')is True
            and bool(factory.get('holderSetter',{}).get('program',{}).get('selectedBytes'))
            and bool(factory.get('strictCast',{}).get('program',{}).get('selectedBytes')))
        for source in(factory,):_source_windows(source.get('sourceWindows'))
        _source_windows(factory.get('holderSetter',{}).get('windows'))
        _source_windows(factory.get('strictCast',{}).get('windows'))
    return dict(schema='endfield.catalog-selector-zero-source-projection.v1',nativeInputs=dict(pins),
        wrapperName=name,wrappedType=original,maintainedOwner='scripts.game_data.memorypack.skill_selector_current_sources',
        sourceKind='dedicated-reference-domain-source',sourceDomain='zero-selector',sourceMethods=[reader_method,method]+[f['method']for f in factories],
        codeWindows=windows,sourceProofSha256=fingerprint(component),originalIsValueType=False,
        genericReferenceReaderApplicable=True,genericReferenceReaderUsed=False,genericNotApplicableClaimed=False,
        completeSelectedSourceAdmitted=False,nativeAttributionProved=False,retainedSelectedSourceComplete=True,
        childGrammarFromSourceAdmitted=False,currentConsumerAdmitted=False,catalogAdmitted=False,
        historicalAttributionHoldCleared=False,
        conditions=['Exact current concrete formatter-to-static-reader path, zero object header, new/existing/FF paths.',
            'Own coherent getter/prehook, both typed factory paths and independent holder and compatible cast.',
            'Initialized compatible metadata and normal successful allocation/helpers with disabled collector.',
            'Union/base-adapter transfer, generic Original formatter and catalog semantic roles are separate.'])


def derive_current(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import skill_selector_current_sources as owner,pointer_param
    _publication_gate(image,pins)
    source=owner.derive_zero_components(image,pins,wrapper_names=list(NAMES))
    need('complete-explicit-current-scope',source.get('status')=='validated-zero-components'
        and source.get('nativeInputs')==pins and source.get('unionTransfersAdmitted')is False
        and source.get('wholeSkillDataAdmitted')is False
        and {row.get('wrapperName')for row in source.get('components',[])}==set(NAMES)
        and len(source['components'])==len(NAMES))
    ctx=NativeReferenceContext(image);wrappers={w.name:w for w in image.memorypack_wrappers.values()};rows=[]
    for component in source['components']:
        name=component['wrapperName'];original=NAMES[name][2]
        need('actual-reference-original',ctx.is_value_type(original)is False,original)
        method=pointer_param.methods(image,wrappers[name])['Deserialize']
        entry=[method.index,name,'Deserialize',image.method_pointer_va(method)-image.pe.image_base]
        row=project(component,pins,entry,image_base=image.pe.image_base)
        rows.append(dict(row,completeSelectedSourceAdmitted=True,nativeAttributionProved=True,
            retainedSourceProofEqualityClaimed=False))
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-selector-zero-source-attribution.v1',nativeInputs=dict(pins),sources=rows,
        sourceCount=len(rows),fullCurrentOwnerSources=source,sourceProgramSemanticsReproved=True,
        currentConsumersAdmitted=False,catalogsActivated=0,historicalAttributionHoldsCleared=0)
