"""Own MC5/default40 grammar joined to the separately proved SkMorph ABI."""
import json
from scripts.game_data.memorypack import sk_morph_value_sources as source,sk_morph_wrapper_sources as wrapper
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.sk-morph-value-components.v1'
CAPABILITY='animation-sk-morph-setting'
WIRE=CAPABILITY


def need(check,condition):
    if not condition:raise ValueError('skMorphValueComponents.'+check)


def normalized(value):return json.loads(json.dumps(value))


def replay_value(value,pins):
    from scripts.game_data.memorypack.skill_smart_target_value_transfer import adapter_program,read_program
    from scripts.game_data.memorypack.skill_root_assign_pair_transfer import conversion40_program
    need('own-complete-source',value.get('schema')=='endfield.sk-morph-value-source.v1'
        and value.get('status')=='validated-conditional-sk-morph-hidden40-source'and value.get('nativeInputs')==pins
        and value.get('typeName')==source.TYPE and value.get('wrapperName')==source.WRAPPER
        and value.get('managedBytes')==40 and value.get('resultAbi')=='hidden-local'and value.get('actualSourceProved')is True
        and value.get('referenceLaneOffsets')==[24]and value.get('paddingByteRanges')==source.PADDING
        and value.get('wireGrammarAdmitted')is False and value.get('parentFieldAdmitted')is False and value.get('wholeOwnerAdmitted')is False)
    p=value['proof'];source.validate_layout(p['layout']);base=p['readerProgram']['selectedBytes'][0][0]-value['sourceTargetRva']
    need('literal-current-source-base',type(base)is int and base>=2**32)
    raw={role:regions(p['sourceWindows'][role],rows,base,'skMorph-'+role)for role,rows in p['actualSourceRegions'].items()}
    s={k:base+v for k,v in p['symbolRvas'].items()}
    need('same-complete-reader',normalized(read_program(raw['read'],base+value['sourceTargetRva'],s))==p['readerProgram'])
    for role in('adapter','dispatch'):
        checks=[adapter_program(raw[role],s[role],s,dispatch=role=='dispatch',**options)for options in({},dict(create=False),dict(null=True))]
        need('same-whole-canonical-and-actual-'+role,normalized(checks)==p['paths'][role])
    need('same-whole-nonnull-and-interface',normalized([source.nonnull_program(raw['nonnull'],s['nonnull'],s,wrapper_null=n)for n in(False,True)])==p['paths']['nonnull']
        and normalized(conversion40_program(raw['conversion'],s['conversion'],s['prepare'],ordinal=p['interfaceOrdinal']))==p['paths']['conversion']
        and p.get('actualComparedCanonicalAdapterRva')==p['symbolRvas']['adapter']and p.get('closedWrapperPointerEqualityInferred')is False
        and p.get('runtimeSelectionObserved')is False)
    def leaf(program,fn):
        selected=program.get('selectedBytes',[]);need('complete-owned-leaf-program',bool(selected))
        own=[(a,bytes.fromhex(h))for a,h in selected]
        need('exact-selected-leaf',normalized(fn(own,selected[0][0]))==program)
    leaf(p['ownGetter'],source.getter_program)
    need('both-own-default40-factories',len(p.get('zeroLeaves',[]))==2 and[r['method'][2]for r in p['zeroLeaves']]==['.ctor','CreateInstance'])
    for row in p['zeroLeaves']:leaf(row['program'],source.zero_program)
    pair=p['pair'];faces=pair.get('composition',{}).get('interfaces',[])
    need('own-registered-original-wrapper-pair',pair.get('registration',{}).get('originalType')==source.TYPE and pair.get('registration',{}).get('wrapperType')==source.WRAPPER
        and len(faces)==1 and p['ownGetter'].get('completePayloadBitsCopied')is True
        and faces[0].get('getValueMethodIndex')is not None)
    return base


def compose(pins,value,wire):
    from scripts.game_data.memorypack import animation_transition_value_sources as transition
    base=replay_value(value,pins);p=value['proof'];w=wire.get('proof',{})
    need('own-separate-MC5-wire',wire.get('schema')=='endfield.sk-morph-wrapper-source.v1'
        and wire.get('status')=='validated-conditional-sk-morph-MC5-source'and wire.get('nativeInputs')==pins
        and wire.get('typeName')==source.TYPE and wire.get('wrapperName')==source.WRAPPER
        and wire.get('memberCount')==5 and wire.get('wireBytes')==26 and wire.get('nullWireBytes')==1
        and wire.get('originalDefaultValueAdmitted')is False and wire.get('parentFieldAdmitted')is False
        and wire.get('wholeOwnerAdmitted')is False and w.get('layout')==p['layout'])
    raw=regions(w['windows'],w['regions'],base,'skMorph-wrapper');at=base+w['method'][3]
    checks=[wrapper.program(raw,at,**options)for options in({},dict(new=True),dict(null=True))]
    need('all-three-complete-wrapper-paths',normalized(checks)==w['programs']
        and{key:target-base for key,target in checks[0]['symbols'].items()}==w['symbolRvas'])
    need('same-canonical-wrapper-formatter',w['method']==p['forwarding']['readerMethod'])
    children=w['children'];requests=w['requests'];need('all-four-actual-typed-wire-helpers',len(requests)==4)
    for event,name in zip(requests,('Beyond.Resource.StringPathHash','Beyond.Gameplay.Core.GameplayTag','Beyond.Montage.SkMorphMotionType',source.TRANSITION),strict=True):
        usage=event['typedRequest'];need('own-helper-request:'+name,tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
            ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name])
            and event['sourceTargetVa']-base==w['symbolRvas'][event['role']])
    hash_child=children['hash'];hash_raw=regions(hash_child['windows'],hash_child['regions'],base,'skMorph-hash')
    from scripts.game_data.memorypack.animation_mask_sources import hash_program
    need('own-raw8-hash-helper',normalized(hash_program(hash_raw,base+w['symbolRvas']['hash'],w['readerOffsets']))==hash_child['program'])
    need('own-Tag4-and-enum4-and-normalized-bool',children['tag'].get('typeName')=='Beyond.Gameplay.Core.GameplayTag'
        and children['tag'].get('wireBytes')==children['tag'].get('managedBytes')==4
        and children['tag'].get('targetRva')==w['symbolRvas']['tag']
        and children['enum'].get('wireBytes')==4 and children['enum'].get('targetRva')==w['symbolRvas']['enum']
        and children['boolean'].get('wireBytes')==1 and children['boolean'].get('targetRva')==w['symbolRvas']['boolean'])
    transition.verify_raw(children['transition'],pins)
    need('own-transition-actual-call',children['transition']['sourceTargetRva']==w['symbolRvas']['transition']
        and children['transition']['proof']['typedRequest']==requests[3]['typedRequest'])
    child=transition.compose(children['transition'],pins);definition=value['readerMethodDefinition']
    cap=dict(typeName=source.TYPE,wrapperName=source.WRAPPER,typeDefinition=p['layout']['typeDefinition'],managedBytes=40,memberCount=5,
        nullable=True,nullMarker=255,nullWireBytes=1,nullReturnsDefaultValue=True,positiveWireBytes=26,wireBytes=None,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ordinaryOriginalCallbackAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        referenceLaneOffsets=[24],paddingByteRanges=source.PADDING,runtimeOnlyFieldNames=['motionAsset'],
        orderedFieldNames=p['layout']['serializedFieldNames'],valueReaderMethodDefinition=definition,valueReaderTargetRva=value['sourceTargetRva'],
        valueDispatcherTargetRva=p['symbolRvas']['dispatch'],canonicalAdapterTargetRva=p['symbolRvas']['adapter'],
        formatterDeserializeMethodDefinition=p['pair']['composition']['interfaces'][0]['formatterDeserializeMethodIndex'],transitionCapability=transition.CAPABILITY,
        requiredChildCapabilities=child['capabilities'],runtimeAnimationProved=False,wholeOwnerAdmitted=False)
    return dict(capabilities={**child['capabilities'],CAPABILITY:cap},requiredExternalCapabilities=[])


def validate_component(component,pins):
    need('own-current-value-component',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-sk-morph-value-components'and component.get('nativeInputs')==pins
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];joined=compose(pins,p['value'],p['wire'])
    need('exact-independent-child-capabilities',joined['capabilities']==component.get('capabilities')
        and joined['requiredExternalCapabilities']==component.get('requiredExternalCapabilities'))
    return joined


def derive(image,pins,*,typed_request,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);value=source.derive(image,pins,typed_request=typed_request,source_target=source_target)
    wire=wrapper.derive(image,pins);joined=compose(pins,value,wire);_publication_gate(image,pins)
    return normalized(dict(schema=SCHEMA,status='validated-conditional-sk-morph-value-components',nativeInputs=pins,
        **joined,proof=dict(value=value,wire=wire),parentFieldAdmitted=False,wholeOwnerAdmitted=False))
