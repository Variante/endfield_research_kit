"""Join one ordinary Int32 dictionary to the independent Unity curve owner."""
import json

from scripts.game_data.memorypack import animation_int_curve_dictionary_sources as source
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.animation-int-curve-dictionary-components.v1'
CAPABILITY=source.CAPABILITY
VALUE_CAPABILITY='skill-animation-curve'


def need(check,condition):
    if not condition:raise ValueError('animationIntCurveDictionaryComponents.'+check)


def normalized(value):return json.loads(json.dumps(value))


def compose(pins,actual,curve):
    from scripts.game_data.memorypack.animation_custom_dictionary_components import replay_callback
    from scripts.game_data.memorypack.skill_animation_curve_codec import require_capability
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    need('own-complete-ordinary-source',actual.get('schema')==source.SCHEMA
        and actual.get('status')=='validated-conditional-int-reference-dictionary-source' and actual.get('nativeInputs')==pins
        and actual.get('typeName')==source.TYPE and actual.get('sourceWitnessClassArguments')==['int','object']
        and actual.get('callbackEqualsCanonicalRequired')is True and actual.get('keyGrammarAdmitted')is True
        and actual.get('valueGrammarAdmitted')is False and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False
        and all(type(actual.get(k))is int and actual[k]>0 for k in('packableReaderMethodDefinition','packableReaderTargetRva','sourceTargetRva','sourceMethodDefinition')))
    p=actual['proof'];key=p['integerCallback'];base=replay_callback(key,pins)
    need('independent-Int32-key-callback',key.get('typeName')=='int')
    raw=regions(p['actualWindows'],p['actualSourceRegions'],base,'ordinary-Dictionary')
    symbols=source.paths.symbols(raw)
    need('same-actual-source-helper-targets',{k:v-base for k,v in symbols.items()}==p['symbolRvas'])
    programs=[source.paths.program(raw,base+actual['sourceTargetRva'],p['readerOffsets'],symbols,count=n,
        key_callback=base+key['callbackTargetRva'],same_comparer=same)for same in(False,True)for n in(-1,0,1,2,3)]
    need('whole-Dictionary-source-byte-replay',normalized(programs)==p['programs'])
    counted=source.paths.induction(programs,count_limit=p['induction']['countLimit'])
    need('both-owned-constructor-count-inductions',normalized(counted)==p['induction'])
    need('independent-strong-UnityCurve',curve.get('schema')=='endfield.skill-animation-curve-sources.v1'
        and curve.get('status')=='validated-conditional-unity-animation-curve' and curve.get('nativeInputs')==pins)
    value=require_capability(curve.get('capabilities',{}).get(VALUE_CAPABILITY,{}));cp=curve['proof'];method=cp['existingOutput']['sourceMethod']
    nominal=cp['existingOutput']['formatterCurveType']
    need('independently-owned-UnityCurve-definition',nominal.get('typeName')==source.VALUE
        and type(nominal.get('typeDefinition'))is int and nominal['typeDefinition']>=0)
    carrier=source.require_carrier(p['closedCarrier'],nominal['typeDefinition'])
    need('same-closed-nominal-and-parent-source',carrier==p.get('nominalIdentity')
        and p['typedRequest'].get('methodArguments')==[source.TYPE]
        and p['typedRequest'].get('methodName')=='ReadPackable'
        and p['typedRequest']['methodSpec'][0]==actual['packableReaderMethodDefinition']
        and p['actualParent'].get('memberIndex')==10 and p['actualParent'].get('fieldName')==source.FIELD
        and p['actualParent'].get('sameReturnedReferencePassedToNamedSetter')is True
        and p['actualParent'].get('sourceTargetRva')==actual['packableReaderTargetRva'])
    need('own-reference-curve-callback',method[1:3]==['MemoryPack.AnimationCurveFormatter','Deserialize']
        and value.get('typeName')==source.VALUE and cp['dispatchWindows']==p['helpers']['valueDispatch']['windows']
        and any(w.get('startRva')==method[3] for w in cp['existingOutput'].get('codeWindows',[])))
    helper=p['helpers']['valueDispatch'];owned=regions(helper['windows'],helper['regions'],base,'UnityCurve-dispatch')
    old=cp['dispatchTransfer'];chunks=old['selectedBytes'];at=next(a for a,h in chunks if h=='e8')
    operand=bytes.fromhex(dict(chunks)[at+1]);need('actual-dispatch-preparation-E8',len(operand)==4)
    prepare=at+5+int.from_bytes(operand,'little',signed=True)
    checked=deserialize_slot(owned,base+helper['entryRva'],prepare=prepare,callback=base+method[3])
    need('actual-generic-dispatch-Unity-callback-replay',normalized(checked)==old)
    cap=dict(typeName=source.TYPE,keyType='int',valueType=source.VALUE,headerBytes=4,nullCount=-1,
        countRange=[-1,counted['countLimit']],countLimit=counted['countLimit'],nodeLimit=16384,
        managedKeyBytes=4,keyWireBytes=4,managedValueBytes=8,valueWireBytes=None,nullable=True,
        positiveCountsAdmitted=True,wholeGrammarAdmitted=True,actualReadPackableAdmitted=True,
        packableReaderMethodDefinition=actual['packableReaderMethodDefinition'],packableReaderTargetRva=actual['packableReaderTargetRva'],
        dictionaryCallbackMethodDefinition=actual['sourceMethodDefinition'],dictionaryCallbackTargetRva=actual['sourceTargetRva'],
        keyCallbackMethodDefinition=key['callbackMethodDefinition'],keyCallbackTargetRva=key['callbackTargetRva'],
        valueCapability=VALUE_CAPABILITY,valueCapabilityShape=value,valueCallbackMethodDefinition=method[0],valueCallbackTargetRva=method[3],
        initiallyNullOutputRequired=True,callbackSelectionConditional=True,normalInsertionRequired=True,insertBehaviorByte=2,
        closedPointerEquivalenceProved=actual['closedPointerEquivalenceProved'],actualRuntimeSelectionObserved=False,
        orderedEntriesPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        conditions=[actual['evidenceBoundary']['conditional'],curve['evidenceBoundary']['conditional'],
            'The actual closed typed Dictionary callback equals this int/object source with coherent MethodInfos; each insertion returns normally. Duplicate/equality semantics and final native map contents are not reconstructed.'])
    from scripts.game_data.memorypack.animation_int_curve_dictionary_codec import require_capability as require_dictionary
    require_dictionary(cap)
    return dict(capabilities={CAPABILITY:cap,VALUE_CAPABILITY:value},requiredExternalCapabilities=[])


def _derive_on_curve(image,pins,*,typed_request,call_target,curve,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins)
    actual=source.derive(image,pins,typed_request=typed_request,call_target=call_target,count_limit=count_limit)
    joined=compose(pins,actual,curve)
    _publication_gate(image,pins)
    return normalized(dict(schema=SCHEMA,status='validated-conditional-int-UnityCurve-dictionary',nativeInputs=dict(pins),
        **joined,proof=dict(source=actual,curve=curve),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own nominal parent/formatter/constructor/comparer/count/key source and independently complete UnityCurve matched slot5 source joined without a closed pointer alias.',
            conditional=source.__doc__,structuralOnly='Ordered serialized entries and raw bits; no final map or animation behavior.')))


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.memorypack.skill_animation_curve_sources import derive as curve
    return _derive_on_curve(image,pins,typed_request=typed_request,call_target=call_target,
        curve=curve(image,pins),count_limit=count_limit)
