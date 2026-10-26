"""Exact null-only Original reference lane for AnimationConfig fallback sets.

The selected canonical adapter consumes FF and clears the whole reference
output before any wrapper allocation or child callback. The fallback set's
positive dictionaries and generated MC2 grammar remain unadmitted here.
"""
import hashlib
import json

SCHEMA='endfield.animation-fallback-null-components.v1'
TYPE='Beyond.Gameplay.View.Animation.AnimationMontageSetSo'
CAPABILITY='animation-fallback-montages-null'


def need(check,condition):
    if not condition:raise ValueError('animationFallbackNull.'+check)


def normalized(value):return json.loads(json.dumps(value))


def require_capability(cap):
    need('exact-null-only-nominal-capability',cap.get('typeName')==TYPE
        and cap.get('nullOnlyGrammarAdmitted')is True and cap.get('positiveGrammarAdmitted')is False
        and cap.get('ordinaryOriginalReadValueAdmitted')is True
        and cap.get('nullMarker')==255 and type(cap.get('nullMarker'))is int
        and cap.get('nullWireBytes')==1 and type(cap.get('nullWireBytes'))is int
        and cap.get('outputReferenceBytes')==8 and cap.get('runtimeCallbackSelectionObserved')is False
        and cap.get('actualCallbackEqualsCanonicalRequired')is True
        and type(cap.get('referenceReaderMethodDefinition'))is int
        and type(cap.get('referenceReaderTargetRva'))is int and cap['referenceReaderTargetRva']>0
        and type(cap.get('canonicalAdapterTargetRva'))is int and cap['canonicalAdapterTargetRva']>0)


def _regions(source,base):
    windows=source.get('windows',[]);regions=source.get('sourceRegions',[])
    need('all-and-only-owned-source-regions',len(windows)==len(regions)>0)
    out=[]
    for w,(at,encoded)in zip(windows,regions,strict=True):
        raw=bytes.fromhex(encoded)
        need('full-native-source-window',at==w['startRva'] and w['endRva']-at==len(raw)
            and hashlib.sha256(raw).hexdigest().upper()==w['sha256'].upper())
        out.append((base+at,raw))
    return out


def validate_component(component,pins):
    from scripts.game_data.memorypack import reference_adapter_sources as parser
    need('selected-native-null-component',component.get('schema')==SCHEMA
        and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-animation-fallback-null'
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    cap=component.get('capabilities',{}).get(CAPABILITY,{})
    require_capability(cap)
    need('only-own-null-capability',set(component['capabilities'])=={CAPABILITY}
        and component.get('requiredExternalCapabilities')==[])
    proof=component['proof'];base=proof['imageBase'];usage=proof['typedRequest'];adapter=proof['adapter']
    need('actual-nominal-reference-reader',tuple(usage.get(k)for k in
        ('tag','typeName','methodName','classArguments','methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
        and usage['methodSpec'][0]==cap['referenceReaderMethodDefinition']
        and proof['sourceTargetRva']==cap['referenceReaderTargetRva']
        and all(cap[k]==proof['referenceReaders'][k]for k in
            ('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    pair=proof['pair']
    need('own-reference-pair-and-canonical-selection',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
        and adapter.get('nativeInputs')==pins and adapter.get('typeName')==TYPE
        and adapter.get('wrapperName')==component['wrapperName'] and normalized(adapter.get('pair'))==normalized(pair)
        and pair['registration']['originalType']==TYPE
        and pair['registration']['wrapperType']==component['wrapperName']
        and adapter['callbackBinding']['canonicalTargetRva']==cap['canonicalAdapterTargetRva']
        and adapter['callbackBinding']['actualCallbackEqualsCanonicalRequired']is True
        and adapter['callbackBinding']['runtimeSelectionObserved']is False)
    getter=proof['getter']
    need('own-closed-holder-reference-getter',getter['instructions']==[
        [getter['entryRva'],'488B4110'],[getter['entryRva']+4,'C3']]
        and getter['physicalExtentProved']is False
        and adapter['getterMethod'][3]==getter['entryRva'])
    symbols={k:base+v for k,v in adapter['canonicalRoutes']['symbolRvas'].items()}
    sources=proof['nullSources'];programs=proof['nullPrograms']
    for key,parse in(('main',parser.main),('dispatch',parser.dispatch)):
        source=sources[key];raw=_regions(source,base)
        replay=parse(raw,base+source['entryRva'],symbols,null=True)
        need('complete-owned-null-program-'+key,normalized(replay)==programs[key]
            and source['entryRva']==adapter['canonicalRoutes']['symbolRvas'][key]
            and replay['null']is True and replay['outputBytes']==8
            and replay['normalReturn']is True and replay['sameIncomingReaderAndOutput']is True)
    need('exact-canonical-null-target',sources['main']['entryRva']==cap['canonicalAdapterTargetRva'])
    return dict(capability=CAPABILITY,capabilities=normalized(component['capabilities']),requiredExternalCapabilities=[])


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources as parser
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    usage=derive_typed_usage_context(image,typed_request['instructionRva'],label='animationFallbackNull.actual')
    need('fresh-actual-request',normalized(usage)==normalized(typed_request))
    need('own-reference-original',ctx.is_value_type(TYPE)is False)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('literal-own-reference-holder',tuple(ctx.field(wrapper.name+'::__instance'))==(wrapper.name,TYPE,16))
    pair=normalized(derive_pair(image,TYPE,wrapper.name));adapter=derive_adapter(image,pins,pair,wrapper)
    abi=reference_reader_abi(image,pins)
    need('actual-same-owned-reference-frontend',source_target==base+abi['referenceReaderTargetRva']
        and usage['methodSpec'][0]==abi['referenceReaderMethodDefinition'])
    getter=pointer.leaf(image,base+adapter['getterMethod'][3],['488B4110','C3'])
    symbols={k:base+v for k,v in adapter['canonicalRoutes']['symbolRvas'].items()}
    sources={};programs={}
    for key,parse in(('main',parser.main),('dispatch',parser.dispatch)):
        body=pointer.owned(image,symbols[key])
        sources[key]=dict(entryRva=symbols[key]-base,windows=body['windows'],
            sourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']])
        programs[key]=parse(body['regions'],symbols[key],symbols,null=True)
    cap=dict(typeName=TYPE,nullOnlyGrammarAdmitted=True,positiveGrammarAdmitted=False,
        ordinaryOriginalReadValueAdmitted=True,nullMarker=255,nullWireBytes=1,outputReferenceBytes=8,
        referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],
        referenceReaderTargetRva=abi['referenceReaderTargetRva'],
        canonicalAdapterTargetRva=adapter['callbackBinding']['canonicalTargetRva'],
        actualCallbackEqualsCanonicalRequired=True,runtimeCallbackSelectionObserved=False)
    result=normalized(dict(schema=SCHEMA,status='validated-conditional-animation-fallback-null',nativeInputs=pins,
        typeName=TYPE,wrapperName=wrapper.name,capabilities={CAPABILITY:cap},requiredExternalCapabilities=[],
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(imageBase=base,typedRequest=usage,
            sourceTargetRva=source_target-base,pair=pair,adapter=adapter,getter=getter,referenceReaders=abi,
            nullSources=sources,nullPrograms=programs),evidenceBoundary=__doc__))
    validate_component(result,pins);_publication_gate(image,pins);return result


def bind_root(parent,pins,component):
    from scripts.game_data.memorypack.animation_config_root_sources import verify
    verify(parent,pins);validate_component(component,pins)
    request=parent['requests'][0];cap=component['capabilities'][CAPABILITY]
    need('only-actual-fallback-field',request['memberIndex']==0 and request['fieldName']=='_fallbackMontages'
        and request['typeName']==TYPE and request['typedRequest']==component['proof']['typedRequest']
        and request['sourceTargetRva']==cap['referenceReaderTargetRva'])
    return dict(memberIndex=0,fieldName=request['fieldName'],typeName=TYPE,capability=CAPABILITY,
        nullOnlyGrammarAdmitted=True,positiveGrammarAdmitted=False,wholeReferenceFieldAndFramesProved=True)


def read(reader):
    cap=reader.operation.child(CAPABILITY);require_capability(cap)
    need('positive-fallback-set-unproved',reader.peek()==255)
    reader.take(1,'fallback-montages.null')
    return dict(isNull=True,typeName=TYPE)
