"""Independent callback obligations below Interactive's static dictionaries.

The selected source already proves every signed count, call, store and loop.
Pooled strings and the actually compared Int32 callback are separate sources.
Reference values require the exact independently proved Original conversion;
their positive wire grammar remains the recursive reader's obligation. Other
declared children receive only the independently proved null/empty count path.
"""
import json

from scripts.game_data.memorypack import interactive_dictionary_components as dictionaries
from scripts.game_data.memorypack import interactive_object_sources as objects

REFERENCES=frozenset({'Beyond.Gameplay.Core.InteractiveTemplateVariant','Beyond.Gameplay.ParamListForGraph'})


def need(check,condition):
    if not condition:raise ValueError('interactiveDictionaryChildren.'+check)


def compose(source,pins,*,callbacks,reference=None):
    base,key,value=dictionaries.replay_source(source,pins);positive=key in('int','string')and(
        value in('int','string')or value in REFERENCES)
    used={};programs=source['proof']['programs']
    for name in set((key,value))&{'int','string'}:
        callback=callbacks.get(name,{})
        need('own-current-primitive-callback:'+name,callback.get('nativeInputs')==pins
            and callback.get('typeName')==name and callback.get('status')=='validated-conditional-callback'
            and callback.get('wireBytes')==4 and callback.get('outputBytes')==(4 if name=='int'else 8)
            and callback.get('callbackSlot')==5 and callback.get('actualRuntimeSelectionObserved')is False
            and type(callback.get('callbackTargetRva'))is int and callback['callbackTargetRva']>0)
        if name=='string':
            need('own-pooled-string-source',callback.get('schema')=='endfield.animation-custom-pooled-string-callback.v1'
                and callback.get('encoding')=='int32-pool-index'and callback.get('nullIndex')==-2
                and callback.get('emptyIndex')==-1)
        else:
            need('own-int32-inlined-callback-match',callback.get('schema')=='endfield.animation-custom-Int32-callback.v1'
                and all(p.get('intCallbackTargets',[None])[0]==base+callback['callbackTargetRva']
                    for p in programs if p.get('countWitness',0)>0))
        used[name]=callback
    if value in REFERENCES:
        need('own-actual-reference-value-conversion',type(reference)is dict
            and reference.get('schema')==objects.SCHEMA and reference.get('nativeInputs')==pins
            and reference.get('typeName')==value
            and all(reference.get(k)is True for k in('ownConcreteGetterSemanticsProved',
                'ownConcreteFactorySemanticsProved','ownConcreteCallbackProved'))
            and reference.get('childGrammarAdmitted')is False and reference.get('wholeOwnerAdmitted')is False)
        need('complete-inline-reference-callback-ABI',all(p.get('keyOutputBytes')==p.get('valueOutputBytes')==8
            and p.get('callbackSlot')==5 and p.get('callbackMethodInfoOffset')==408
            for p in programs if p.get('countWitness',0)>0))
    return json.loads(json.dumps(dict(schema='endfield.interactive-dictionary-child-bindings.v1',nativeInputs=pins,
        typeName=source['typeName'],keyType=key,valueType=value,countLimit=4096 if positive else 0,
        keyCallback=used.get(key),valueCallback=used.get(value),valueReference=reference,
        positiveChildCallbacksJoined=positive,positiveReferenceValueGrammarRequired=value in REFERENCES,
        actualCallbacksEqualProvedNominalsRequired=True,runtimeSelectionObserved=False,
        childGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))


def derive(image,pins,source,*,reference=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import derive_integer,derive_string
    _publication_gate(image,pins)
    _,key,value=dictionaries.replay_source(source,pins)
    callbacks={name:(derive_integer if name=='int'else derive_string)(image,pins)
        for name in set((key,value))&{'int','string'}}
    result=compose(source,pins,callbacks=callbacks,reference=reference)
    _publication_gate(image,pins)
    return result
