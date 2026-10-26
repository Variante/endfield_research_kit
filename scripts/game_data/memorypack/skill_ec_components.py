"""Finite recursive EC programs from complete current ordinary source owners.

Target, Direction and Selector form a recursive stored grammar. Their source
programs and ordinary adapters are proved before these capabilities are made;
the enclosing operation must separately supply its finite Finder routes and
PostProcessor/Validator list domains. No runtime selection or whole SkillData
claim follows. This pure compiler is not a native authentication boundary.
"""
import json

from scripts.game_data.memorypack.skill_root_child_bindings import need
from scripts.game_data.memorypack.skill_ec_reference_sources import TYPES

NAMES=dict(zip(TYPES,('target-profile','direction-profile','selector-profile')))
ORDERS={
 TYPES[0]:(('advancedDirection','reference', 'direction-profile'),('centerContextKey','pool','byte-payload'),
    ('centerToGround','bool',None),('centerType','int',None),('enableAdvancedDirection','bool',None),
    ('ownerContextKey','pool','byte-payload'),('selectorData','reference','selector-profile'),
    ('selectorDirection','int',None),('selectorOwner','int',None),('target','int',None),
    ('targetContextKey','pool','byte-payload'),('targetGroupKey','pool','byte-payload'),('targetSource','int',None)),
 TYPES[1]:(('clampToXZ','bool',None),('customSourceAndTarget','bool',None),('directionType','int',None),
    ('invertDirection','bool',None),('source','reference','target-profile'),('sourceMountPoint','int',None),
    ('target','reference','target-profile'),('targetMountPoint','int',None)),
 TYPES[2]:(('finderData','reference','SelectorFinder'),('postProcessorData','list','target-postprocessor-list'),
    ('validatorData','list','target-validator-list')),
}
EXTERNAL={'SelectorFinder':'Beyond.Gameplay.Core.Selector+Finder+Data',
 'target-postprocessor-list':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Selector+PostProcessor+Data>',
 'target-validator-list':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.Selector+Validator+Data>'}


def compile_component(component,pins,clones,requests):
    need('complete-selected-ec-reference-scope',True,component.get('schema')=='endfield.skill-ec-reference-sources.v1'
        and component.get('status')=='validated-conditional-ec-reference-sources'and component.get('nativeInputs')==pins
        and set(component.get('records',{}))==set(TYPES)and component.get('wholeSkillDataAdmitted')is False)
    need('exact-ec-request-scope',set(TYPES),set(requests))
    identities={name:dict(typeName=name,referenceReaderMethodDefinition=clones['ReadValue']['equivalentMethod'][0],
        referenceReaderTargetRva=clones['ReadValue']['targetRva'])for name in TYPES}
    external={};caps={};bindings=[]
    for typename,record in component['records'].items():
        source=record['source'];scope=source['sourceScope'];reads=source['orderedSourceReads'];order=ORDERS[typename]
        need('whole-current-ec-source',True,source.get('schema')=='endfield.generated-concrete-reader-source.v1'
            and source.get('nativeInputs')==pins and source.get('wrappedType')==typename
            and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
            and source.get('wholeOwnerAdmitted')is False and record.get('ordinaryOriginalReadValueSourceProved')is True
            and record.get('referenceIdentity')==identities[typename]
            and scope.get('events')==reads and scope.get('sourceScopeAdmitted')is True
            and source['method']==source['lifecycle']['readerMethod']==scope['method'])
        paths=source['programs'];need('four-complete-ec-paths',True,len(paths)==4
            and {(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
            and all(type(p['existing'])is bool and type(p['wrapperNull'])is bool and p['frame'].get('entryRspRestored')is True
                and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
        rich=scope.get('richProgram',{})
        need('complete-ec-value-flow',True,rich.get('completeSelectedNormalProgram')is True
            and rich.get('selectedProgram')==scope['selectedProgram']and len(rich.get('sources',[]))==len(order)
            and len(rich.get('fieldStores',[]))==len(order)and len(reads)==scope['memberCount']==len(order))
        program=[];required=set()
        for index,(read,(field,kind,child))in enumerate(zip(reads,order,strict=True)):
            need('exact-ec-member-order',(index,field),(read['memberIndex'],read['fieldName']))
            flow=rich['sources'][index];store=rich['fieldStores'][index]
            need('same-ec-source-field-store',True,flow['memberIndex']==store['memberIndex']==index
                and store.get('normalIncomingValueStoredUnchanged')is True)
            if kind in('bool','int'):
                expected,width=('byte',1)if kind=='bool'else('scalar32',4)
                need('exact-ec-inline-primitive',True,read['kind']==expected and read.get('wireBytes')==width
                    and flow.get('mode')=='buffered-inline'and flow.get('wireBytes')==width
                    and flow.get('program')==read.get('program')and store['storedBytes']==width)
                wire='bool-byte'if kind=='bool'else'scalar32'
            elif kind=='pool':
                need('exact-ec-pooled-source',True,read['kind']=='byte-payload'and read.get('wireBytes')==4
                    and read.get('mode')==flow.get('mode')=='proved-pooled-string'and store['storedBytes']==8)
                wire='byte-payload'
            else:
                nominal=TYPES[tuple(NAMES.values()).index(child)]if child in NAMES.values()else EXTERNAL[child]
                need('exact-ec-reference-kind','reference:'+nominal,read['kind'])
                usage=requests[typename][index];context=read['context'];method='ReadPackable'if kind=='list'else'ReadValue'
                need('actual-ec-nominal-request',('MemoryPack.MemoryPackReader',method,[],[nominal]),
                    tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments')))
                need('same-ec-owned-request',True,usage['instructionRva']==context['instructionRva']and usage['methodSpec']==context['methodSpec'])
                clone=clones[method];need('same-ec-reference-method',clone['equivalentMethod'][0],usage['methodSpec'][0])
                mode=read.get('mode')
                if mode=='typed-provider-slot-five':
                    need('actual-inline-ec-provider',clones['providerTarget'],read['providerCallTargetRva'])
                    need('actual-inline-ec-dispatch',clones['dispatchTarget'],read['sourceTargetRva'])
                    need('same-typed-provider-value-flow',mode,flow.get('mode'))
                else:
                    need('exact-ec-direct-reference-mode','proved-reference-clone',mode)
                    need('actual-ec-reference-source',clone['targetRva'],read['sourceTargetRva'])
                need('complete-ec-reference-store',8,store['storedBytes'])
                wire='reference-list'if kind=='list'else'selector-union'if child=='SelectorFinder'else child
                bindings.append(dict(ownerType=typename,fieldName=field,capability=child,nominalType=nominal,
                    methodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTargetRva'],sourceMode=mode))
                if child in EXTERNAL:external[child]=dict(typeName=nominal,readerMethodDefinition=clone['equivalentMethod'][0],
                    readerTargetRva=clone['targetRva'],readerMethod=method)
            if child is not None:required.add(child)
            program.append(dict(memberIndex=index,fieldName=field,kind=wire,childCapability=child))
        caps[NAMES[typename]]=dict(identities[typename],wrapperName=source['wrapperName'],memberCount=len(order),
            nullAdmitted=True,nullMarker=255,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
            ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,orderedReads=program,
            requiredCapabilities=sorted(required),recursiveDepthLimit=64,wholeSkillDataAdmitted=False,
            finiteSelectorRoutesRequireExplicitPrograms=True)
    return dict(capabilities=caps,requiredExternalCapabilities=['SelectorFinder','byte-payload','target-postprocessor-list','target-validator-list'],
        requiredExternalSourceIdentities=external,childBindings=bindings)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_ec_reference_sources import derive as source
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    _publication_gate(image,pins);component=source(image,pins);clones=ec.clone_facts(image,pins)
    selected={key:dict(value)for key,value in clones.items()if key in('ReadValue','ReadPackable')}
    for key in('providerTarget','dispatchTarget'):selected[key]=clones[key]-image.pe.image_base
    requests={typename:{read['memberIndex']:derive_typed_usage_context(image,read['context']['instructionRva'],label='skillEcComponents')
        for read in record['source']['orderedSourceReads']if read['kind'].startswith('reference:')}
        for typename,record in component['records'].items()}
    compiled=compile_component(component,pins,selected,requests);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-ec-components.v1',nativeInputs=pins,
        status='validated-conditional-finite-ec-components',**compiled,
        proof=dict(source=component,clones=selected,typedRequests=requests),wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete current Target13/Direction8/Selector3 source, own ordinary adapters and exact recursive field/primitive/pool/reference/list joins.',
            conditional=__doc__,structuralOnly='Stored target and selector configuration.',
            unresolved=['external finite Finder/list route domains','runtime callback/provider selection','enclosing owner/EOF']))))
