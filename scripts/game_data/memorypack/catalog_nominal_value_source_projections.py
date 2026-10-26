"""Two exact value-source projections for held catalogs, without activation.

GlobalBuffId owns its reviewed managed8 key/adapter source. Pull owns its
separate padded managed16 wrapper and conditional ordinary reference child.
Neither is supplied to the general reference-reader derivation. Attribution
freshly replays the same owner and requires the full retained proof to match.
"""
from scripts.game_data.memorypack.catalog_dedicated_source_projections import _fingerprint,_difference
from scripts.game_data.memorypack.catalog_source_review import _source_windows

SCHEMA='endfield.catalog-dedicated-source-projection.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogNominalValueSource.'+check+':'+str(detail)[:900])


def _methods(rows):
    need('own-named-method-identities',isinstance(rows,list)and rows and all(
        isinstance(row,list)and len(row)==4 and type(row[0])is int and row[0]>=0
        and type(row[1])is str and row[1]and type(row[2])is str and row[2]
        and type(row[3])is int and row[3]>0 for row in rows))
    return rows


def _global(source,pins):
    from scripts.game_data.memorypack import skill_global_buff_id_sources as owner
    fact=source['proof']['reviewedNominalSource'];validation=source['proof']['validation']
    need('same-own-global-identity',source.get('status')=='validated-conditional-global-buff-id'
        and source.get('typeName')==owner.VALUE and source.get('wrapperName')==owner.WRAPPER
        and source.get('nativeInputs')==pins)
    cap=owner.compose(fact,validation,pins)
    need('complete-own-global-capability',source.get('capabilities')=={owner.CAPABILITY:cap}
        and validation.get('readerRegistrationPointerEqual')is False
        and validation.get('providerRegistrationPointerEqual')is False
        and source.get('requiredExternalCapabilities')==['byte-payload'])
    named=fact['methods'];roles=('keyRead','keyConstructor','keyCreateInstance','keyGetValue','keyFormatter')
    methods=_methods([named[role]for role in roles])
    need('exact-global-key-method-owners',all(row[1]==owner.WRAPPER for row in methods[:-1])
        and methods[-1][1].startswith(owner.WRAPPER+'+')
        and [row[2]for row in methods]==['Deserialize','.ctor','CreateInstance','GetValue','Deserialize'])
    registrations=[row for row in fact['registrations']if row.get('originalType')==owner.VALUE
        and row.get('wrapperType')==owner.WRAPPER]
    need('own-global-registration',len(registrations)==1)
    programs={row['role']:row for row in fact['programs']if row['role']in roles}
    need('owned-key-reader-constructor-getter-formatter',set(programs)=={'keyRead','keyConstructor','keyGetValue','keyFormatter'}
        and all(programs[role]['entryRva']==named[role][3]for role in programs)
        and named['keyCreateInstance'][3]==named['keyConstructor'][3])
    windows=_source_windows([window for row in programs.values()for window in row['windows']])
    return owner,8,methods,windows,dict(memberCount=1,positiveWireBytes=5,nullWireBytes=1,
        keyEncoding='int32-pool-index',readerRegistrationPointerEquivalenceProved=False,
        providerRegistrationPointerEquivalenceProved=False,ownOriginalDefaultValueProved=True)


def _pull(source,pins):
    from scripts.game_data.memorypack import skill_pull_attenuation_sources as owner
    need('same-own-pull-identity',source.get('status')=='proved-pull-wrapper-source-requires-value-adapter'
        and source.get('typeName')==owner.TYPE and source.get('wrapperName')==owner.WRAPPER
        and source.get('nativeInputs')==pins)
    layout=source['layout'];fields=layout['fields']
    need('exact-own-pull-layout',layout.get('typeName')==owner.TYPE and layout.get('managedBytes')==16
        and layout.get('holder')==[owner.WRAPPER,owner.TYPE,16]
        and layout.get('referenceLaneOffsets')==[0]and layout.get('paddingByteRanges')==[[12,16]]
        and set(fields)=={'superArmorValue','attenuationFactor'}
        and tuple(fields['superArmorValue'][key]for key in('typeName','unboxedOffset','wrapperOffset','bytes'))==(owner.REFERENCE,0,16,8)
        and tuple(fields['attenuationFactor'][key]for key in('typeName','unboxedOffset','wrapperOffset','bytes'))==('float',8,24,4))
    programs=source['programs']
    need('complete-selected-pull-wrapper-paths',len(programs)==3
        and all(type(p.get('newWrapper'))is bool and type(p.get('ff'))is bool for p in programs)
        and {(p['newWrapper'],p['ff'])for p in programs}=={(False,False),(True,False),(False,True)}
        and all(p.get('normalReturn')is True and p.get('entryRspRestored')is True
            and p.get('hiddenValueBytes')==16 and p.get('originalDefaultValueAdmitted')is False
            and p.get('wireHeaderBytes')==1 and p.get('selectedBytes')for p in programs)
        and next(p for p in programs if p['ff'])['wrapperReferenceCleared']is True
        and next(p for p in programs if p['newWrapper'])['allocation']['zeroedManagedBytes']==16)
    need('exact-own-pull-hidden-getter',[row[1].upper()for row in source['getter']['instructions']]==['0F104210','488BC1','0F1101','C3'])
    need('own-pull-defaults',set(source['defaults'])=={'.ctor','CreateInstance'}and all(
        [row[1].upper()for row in proof['instructions']]==['0F57C0','0F114110','C3']for proof in source['defaults'].values()))
    owner.require_reference(source['referenceChild'],pins)
    need('exact-pull-wire-order-and-separate-boundaries',source['wireOrder']==owner.ORDER
        and all(source.get(key)is False for key in('positiveCollectionAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    forwarding=source['registration'];pair=source['registeredPair'];registration=pair['registration']
    need('own-pull-registration-and-full-forwarder',registration['originalType']==owner.TYPE
        and registration['wrapperType']==owner.WRAPPER
        and forwarding['readerMethod'][1:3]==[owner.WRAPPER,'Deserialize']
        and forwarding['forwarding']['completeOriginalForwarderChecked']is True
        and forwarding['forwarding']['conditionalReaderAndOutputForwardingProved']is True
        and forwarding['forwarding']['runtimeFormatterProviderSelectionProved']is False)
    methods=_methods([forwarding['readerMethod']]+pair['composition']['methods'])
    return owner,16,methods,_source_windows(source['sourceWindows']),dict(memberCount=2,
        fieldWireBytes=[4,None],referenceLaneOffsets=[0],paddingByteRanges=[[12,16]],
        hiddenGetterCopiesAllManagedBytes=True,constructorAndCreateZeroAllManagedBytes=True,
        ownOriginalDefaultValueProved=False,actualOrdinaryReferenceChildRequired=owner.REFERENCE)


def project(source,pins):
    """Pure structural projection, never native authentication or catalog use."""
    schema=source.get('schema')
    if schema=='endfield.skill-global-buff-id-sources.v1':owner,width,methods,windows,profile=_global(source,pins)
    elif schema=='endfield.skill-pull-attenuation-source.v1':owner,width,methods,windows,profile=_pull(source,pins)
    else:return NotImplemented
    typ=getattr(owner,'TYPE',None)or owner.VALUE
    return dict(schema=SCHEMA,nativeInputs=dict(pins),wrapperName=owner.WRAPPER,wrappedType=typ,
        maintainedOwner=owner.__name__,sourceKind='dedicated-value-original-wrapper-source',sourceMethods=methods,codeWindows=windows,
        managedBytes=width,rawManagedWidthIsWireWidth=False,profile=profile,
        retainedSelectedSourceComplete=True,completeSelectedSourceAdmitted=False,nativeAttributionProved=False,
        genericReferenceReaderApplicable=False,childGrammarFromSourceAdmitted=False,
        currentConsumerAdmitted=False,catalogAdmitted=False,historicalAttributionHoldCleared=False,
        retainedSourceProofSha256=_fingerprint(source),completeFreshOwnerReplayRequired=True,
        conditions=['Complete same-owner fresh replay and full proof equality are required.',
            'Initialized coherent nominal contexts, matching actual selected callbacks, buffered disjoint storage and normal helpers/disabled collector.',
            'Source attribution supplies neither current consumer nor catalog semantic roles.'])


def derive(image,pins,*,retained_sources):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('two-finite-distinct-value-owners',isinstance(retained_sources,list)and 0<len(retained_sources)<=2
        and len({source.get('wrapperName')for source in retained_sources})==len(retained_sources))
    _publication_gate(image,pins);rows=[]
    for source in retained_sources:
        projection=project(source,pins);need('explicit-owned-value-profile',projection is not NotImplemented,source.get('schema'))
        if source['schema']=='endfield.skill-global-buff-id-sources.v1':
            from scripts.game_data.memorypack.skill_global_buff_id_sources import derive as replay
            fresh=replay(image,pins)
        else:
            from scripts.game_data.memorypack.skill_pull_attenuation_sources import _derive_wrapper
            fresh=_derive_wrapper(image,pins,source['referenceChild'])
        need('same-complete-current-owned-source',fresh==source,dict(wrapperName=source['wrapperName'],
            retainedSha256=_fingerprint(source),currentSha256=_fingerprint(fresh),firstDifference=_difference(source,fresh)))
        rows.append(dict(projection,completeSelectedSourceAdmitted=True,nativeAttributionProved=True))
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=rows,
        sourceCount=len(rows),sourceProgramSemanticsReproved=True,currentConsumersAdmitted=False,
        catalogsActivated=0,historicalAttributionHoldsCleared=0,evidenceBoundary=__doc__)
