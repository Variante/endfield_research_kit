"""Positive masks composed from the fresh legacy child and new list source.

The legacy native gate owns MC2/default16, the canonical adapter, StringPathHash,
pooled string and typed list/context/Add/constructor programs. The independent
positive source extends only the repeated list control and fresh count capacity.
"""
import json
from scripts.game_data.memorypack import animation_mask_positive_sources as source
from scripts.game_data.memorypack.animation_mask_positive_codec import CAPABILITY,TYPE,require_capability

SCHEMA='endfield.animation-mask-positive-components.v1'


def need(key,condition):
    if not condition:raise ValueError('animationMaskPositiveComponents.'+key)


def compose(component,pins):
    from scripts.game_data.contracts import CONTRACTS_DIR
    source.verify_source(component,pins)
    declaration=json.loads((CONTRACTS_DIR/'animation_masks_native.json').read_bytes())
    legacy=component['proof']['legacySourceValidation']
    need('same-complete-independent-legacy-child-domain',declaration.get('nativeInputs')==pins
        and declaration.get('supportedCounts')==legacy.get('supportedCounts')==[-1,0,1]
        and declaration.get('fieldOrder')==['layerName','maskPath']and declaration.get('elementWireBytes')==13
        and TYPE=='System.Collections.Generic.List`1<'+declaration['profile']['types']['entry']+'>'
        and component['proof']['source']['windows']==declaration['profile']['sources']['list']['windows']
        and component['proof']['source']['entryRva']==declaration['profile']['sources']['list']['entryRva']
        and legacy.get('entryRuntimeBytes')==16 and legacy.get('entryWireBytes')==13
        and type(legacy.get('selectedPrograms'))is int and legacy['selectedPrograms']>0
        and type(legacy.get('interfaceOrdinal'))is int)
    need('new-zero-output-full-count-capacity',component.get('countLimit')==4096
        and component.get('initiallyNullOutputProved')is True
        and component.get('newConstructorCapacityEqualsCountProved')is True
        and component['proof']['induction'].get('maxCount')==4096)
    cap=dict(typeName=TYPE,wholeGrammarAdmitted=True,positiveCountsAdmitted=True,countLimit=4096,
        collectionCounts=[-1,0],memberCount=2,fieldOrder=['layerName','maskPath'],elementGrammarAdmitted=True,
        managedElementBytes=16,positiveElementWireBytes=13,nullElementWireBytes=1,nullElementReturnsDefault16=True,
        pooledLayerNameRequired=True,actualCallbackSelectionConditional=True,initiallyNullOutputProved=True,
        newConstructorCapacityEqualsCountProved=True,positiveLoopInductionProved=True,growthAdmitted=False,
        readerMethodDefinition=component['proof']['typedRequest']['methodSpec'][0],
        sourceTargetRva=component['proof']['sourceTargetRva'],legacyNullEmptyOneDomainPreserved=True)
    require_capability(cap)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-positive-mask-components',nativeInputs=pins,
        capability=CAPABILITY,capabilities={CAPABILITY:cap},requiredExternalCapabilities=['byte-payload'],
        proof=dict(source=component),parentFieldAdmitted=False,wholeOwnerAdmitted=False)))


def validate_component(component,pins):
    need('same-replayed-positive-mask-component',component.get('schema')==SCHEMA
        and component==compose(component['proof']['source'],pins))
    return dict(capability=CAPABILITY,capabilities=component['capabilities'],requiredExternalCapabilities=['byte-payload'])


def bind_root(root,pins,component):
    from scripts.game_data.memorypack.animation_config_root_sources import verify
    verify(root,pins);validate_component(component,pins)
    request=root['requests'][3];proof=component['proof']['source']['proof'];cap=component['capabilities'][CAPABILITY]
    need('own-actual-mask-member-and-ReadPackable',request['memberIndex']==3 and request['fieldName']=='boneWeightMasks'
        and request['typeName']==TYPE and request['typedRequest']==proof['typedRequest']
        and request['sourceTargetRva']==cap['sourceTargetRva'])
    return dict(memberIndex=3,fieldName='boneWeightMasks',capability=CAPABILITY,
        positiveCountsAdmitted=True,countLimit=4096,wholeReturnedReferenceAndBothParentFramesProved=True)


def derive(image,pins,*,root):
    request=root['requests'][3]
    actual=source.derive(image,pins,typed_request=request['typedRequest'],call_target=image.pe.image_base+request['sourceTargetRva'])
    result=compose(actual,pins);bind_root(root,pins,result);return result
