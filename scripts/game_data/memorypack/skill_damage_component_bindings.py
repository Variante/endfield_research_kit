"""Pure exact DamageUnit child joins; freshness belongs to the native owner.

The owner must derive the parent reference source and all delegated components
on the same selected image before calling this binder. This function opens no
image and grants no native authentication. An absent Effect or other child is
an explicit refusal, including when an exported sample happens to store FF.
"""
import json

from scripts.game_data.memorypack.skill_damage_codec import CAPABILITY,ordered_reads,REFERENCES,LISTS
from scripts.game_data.memorypack.skill_damage_unit_sources import TYPE,DECLARATIONS
from scripts.game_data.memorypack.skill_root_child_bindings import bind_read_value

LABEL='skillDamageComponentBindings'
ELEMENTS={
    'costDataList':('Beyond.Gameplay.Core.CastData+CostData',False,'skill-root-cost-data'),
    'damageProcessors':('Beyond.Gameplay.Core.DamageProcessorBase',False,'damage-processor-union'),
    'damageTags':('Beyond.Gameplay.Core.GameplayTag',True,'skill-root-gameplay-tag'),
}


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


def bind_list(join,cap,element):
    typename,value_type,element_cap=ELEMENTS[join['fieldName']]
    nominal='System.Collections.Generic.List`1<'+typename+'>';usage=join['typedRequest']
    need('exact-owned-list-type',join['typeName']==nominal and cap.get('closedListType')==nominal
        and cap.get('elementType')==typename and cap.get('elementValueType')is value_type
        and cap.get('elementCapability')==element_cap)
    need('actual-list-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
        usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadPackable',[],[nominal]))
    need('actual-list-method-target',type(cap.get('packableReaderMethodDefinition'))is int
        and cap['packableReaderMethodDefinition']==usage['methodSpec'][0]
        and type(cap.get('packableReaderTargetRva'))is int and cap['packableReaderTargetRva']>0
        and cap['packableReaderTargetRva']==join['sourceTargetRva'])
    need('complete-induced-list',cap.get('collectionCounts')==[-1,0]
        and all(type(n)is int for n in cap['collectionCounts'])
        and type(cap.get('countLimit'))is int and cap['countLimit']==10000
        and all(cap.get(k)is True for k in('positiveCountsAdmitted','nullable','elementGrammarAdmitted')))
    need('actual-complete-list-element',element.get('typeName')==typename)
    if value_type:
        need('generated-Tag-distinct-from-raw-query',type(element.get('managedBytes'))is int and element['managedBytes']==4
            and type(element.get('memberCount'))is int and element['memberCount']==1
            and type(element.get('positiveWireBytes'))is int and element['positiveWireBytes']==5
            and type(element.get('nullWireBytes'))is int and element['nullWireBytes']==1
            and element.get('nullable')is True and element.get('nullReturnsDefaultValue')is True
            and element.get('rawUnmanagedTagGrammarUsed')is False
            and element.get('orderedReads')==[dict(fieldName='tagId',kind='int32')])
    else:
        need('complete-ordinary-list-element',cap.get('wholeGrammarAdmitted')is True
            and element.get('wholeGrammarAdmitted')is True and element.get('ordinaryOriginalReadValueAdmitted',True)is True)
        need('actual-list-element-reader',all(type(cap.get(k))is int and cap[k]==element.get(k)
            for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')))
    keys=('closedListType','elementType','elementValueType','elementCapability','collectionCounts',
        'countLimit','positiveCountsAdmitted','nullable','elementGrammarAdmitted',
        'packableReaderMethodDefinition','packableReaderTargetRva')
    return dict(fieldName=join['fieldName'],listIdentity={k:cap[k]for k in keys},elementCapabilityShape=element)


def compose(parent,pins,caps):
    need('current-parent-reference-scope',parent.get('schema')=='endfield.damage-unit-reference-source.v1'
        and parent.get('status')=='validated-DamageUnit-source-and-reference-adapter'
        and parent.get('nativeInputs')==pins and parent.get('typeName')==TYPE
        and type(parent.get('memberCount'))is int and parent['memberCount']==34
        and all(parent.get(k)is False for k in('childGrammarsAdmitted','actualParentJoinAdmitted',
            'wholeDamageUnitAdmitted','wholeSkillDataAdmitted')))
    caller=parent['proof']['caller']
    need('complete-source-owned-parent-program',caller.get('typeName')==TYPE
        and caller.get('wrapperName')==parent.get('wrapperName')and caller.get('memberCount')==34
        and [(r['fieldName'],r['typeName'],r['kind'])for r in caller['fields']]==list(DECLARATIONS)
        and [p.get('memberCount')for p in caller['programs']]==[34,34,None]
        and all(p.get('normalReturn')is True for p in caller['programs'])and caller.get('wholeRecordAdmitted')is False)
    expected={field for field,_,kind in DECLARATIONS if kind in('reference','list')}
    joins={r['fieldName']:r for r in caller['requiredChildJoins']}
    need('complete-parent-child-join-bijection',len(joins)==len(caller['requiredChildJoins'])and set(joins)==expected)
    bindings=[];required=set()
    for read in ordered_reads():
        field=read['fieldName'];capability=read['childCapability']
        if capability is None:continue
        need('missing-complete-child:'+capability,capability in caps);required.add(capability)
        if field not in joins:
            need('complete-pool-grammar',capability=='byte-payload'and caps[capability].get('wholeGrammarAdmitted')is True)
            continue
        join=joins[field];cap=caps[capability]
        need('unadmitted-parent-child-source',join.get('childGrammarAdmitted')is False)
        if field in REFERENCES:
            need('actual-ordinary-parent-kind',join.get('kind')=='reference')
            bindings.append(bind_read_value(pins,join,dict(nativeInputs=pins,capabilities=caps),capability))
        else:
            need('actual-list-parent-kind',join.get('kind')=='list')
            element=ELEMENTS[field][2];need('missing-complete-list-element:'+element,element in caps)
            bindings.append(bind_list(join,cap,caps[element]))
    for key in('referenceReaderMethodDefinition','referenceReaderTargetRva'):
        need('literal-parent-reference-reader:'+key,type(parent.get(key))is int and parent[key]>=0)
    cap=dict(typeName=TYPE,wrapperName=parent['wrapperName'],memberCount=34,orderedReads=ordered_reads(),
        nullMarker=255,nullAdmitted=True,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,completeSourceOwnedProgram=True,
        **{k:parent[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')})
    return json.loads(json.dumps(dict(capabilities={CAPABILITY:cap},requiredExternalCapabilities=sorted(required),
        actualChildBindings=bindings,nativeAdmissionGranted=False,actualEnclosingParentAdmitted=False,
        wholeSkillDataAdmitted=False)))
