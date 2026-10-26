"""Own ExtraData static-out local/reset/field/frame joins for five domains."""
from scripts.game_data.memorypack import animation_extra_dictionary_components as component
from scripts.game_data.memorypack import animation_extra_dictionary_sources as source
from scripts.game_data.memorypack.animation_extra_parent_sources import PARENT_FIELDS,validate_setup


def need(check,condition):
    if not condition:raise ValueError('animationExtraDictionaryBinding.'+check)


def bind(owner,scope,read,pins,usage,child,capability,*,value_binder=None):
    name=read.get('declaredType');index=read.get('memberIndex');parent=owner.get('wrappedType')
    need('own-finite-field',name in source.TYPES and capability==component.CAPABILITIES[name]
        and parent in PARENT_FIELDS and PARENT_FIELDS[parent].get(index)==name)
    rebuilt=component.validate_component(child,pins,value_binder=value_binder);cap=rebuilt['capabilities'][capability]
    need('complete-own-current-parent',owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and owner.get('nativeInputs')==scope.get('nativeInputs')==pins and owner.get('sourceScope')==scope
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('childGrammarAdmitted')is False
        and owner.get('wholeOwnerAdmitted')is False and type(index)is int and 0<=index<len(owner['orderedSourceReads'])
        and owner['orderedSourceReads'][index]==read and scope.get('events')==owner['orderedSourceReads'])
    setter=owner['setters'][index];context=source.validate_event(read,setter)
    actual=scope.get('staticReferenceSources',{}).get(str(index),{});declared=child['proof']['source']
    component.replay_source(actual,pins)
    # Each actual containing call has its own independently replayed parent.
    # Reusing a nominal child never aliases the two call sites or their frames.
    keys=('schema','status','nativeInputs','typeName','keyType','valueType','profile','sourceTargetRva','readerMethodDefinition',
        'resultAbi','referenceBytes','keyOutputBytes','valueOutputBytes','valueStorageKind','objectMarkerBytes','countHeaderBytes')
    need('same-own-static-source-domain',all(actual.get(k)==declared.get(k)for k in keys)
        and actual['context']['arguments']==declared['context']['arguments']
        and actual['context']['methodSpec']==declared['context']['methodSpec']
        and all(actual['proof'].get(k)==declared['proof'].get(k)for k in('windows','regions','programs','countInduction',
            'readerOffsets','symbolRvas','genericClassSlots','helpers','objectHeader','barrier'))
        and actual.get('context')==context and context.get('typedRequest')==usage
        and actual['proof']['actualParent']['typeName']==parent and actual['proof']['actualParent']['memberIndex']==index
        and actual['sourceTargetRva']==read.get('sourceTargetRva')==cap['staticReaderTargetRva']
        and actual['readerMethodDefinition']==cap['staticReaderMethodDefinition']==usage.get('methodSpec',[None])[0])
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-parent-static-E8',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==cap['staticReaderTargetRva'])
    declared_parent=actual['proof']['actualParent'];lineage=declared_parent['originalFieldLineage']
    need('same-own-named-setter',scope['richSetters'][index]==setter and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('targetField')in{t+'::'+read['fieldName']for t in lineage}
        and setter.get('storedBytes')==8 and setter.get('member',{}).get('name')==read['fieldName']
        and setter['member'].get('declaredType')==name and setter['method'][2]=='set___'+read['fieldName']+'__'
        and setter['method'][0]==setter['member']['methodIndex'])
    rich=scope['richProgram'];selected=scope['selectedProgram'];flows=[r for r in rich['sources']if r['memberIndex']==index]
    stores=[r for r in rich['fieldStores']if r['memberIndex']==index]
    need('whole-static-local-to-named-field',rich.get('completeSelectedNormalProgram')is True and rich['selectedProgram']==selected
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='out-reference-local')]
        and len(stores)==1 and(stores[0]['sourceOffset'],stores[0]['storedBytes'])==(0,8)
        and stores[0]['instruction']in selected and read['instruction']in selected)
    locals_=[r for r in rich['hiddenSourceLocals']if r['memberIndex']==index]
    need('own-initially-null-reference-result-local',len(locals_)==1 and locals_[0].get('bytes')==8
        and locals_[0].get('sourceAbi')=='void-byref-reference8'and locals_[0].get('nominalTypeName')==name
        and locals_[0].get('nominalTypeDefinition')==context['typeDefinition']
        and locals_[0].get('initiallyZeroLocalRequired')is True and locals_[0].get('sourceInstruction')==read['instruction'])
    local=locals_[0];setup=rich.get('staticOutParentSetup',{});validate_setup(setup,scope['events'])
    zeros=[z for z in setup['initializedZeroLocals']if z.get('memberIndex')==index]
    need('one-own-null-reset',len(zeros)==1 and zeros[0]['displacement']==local['displacement']
        and zeros[0]in rich['initializedZeroLocals'])
    paths=owner['programs'];need('four-complete-selected-parent-frames',len(paths)==4
        and{(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(True,False),(False,True),(True,True)}
        and all(p['frame'].get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    for path in paths:
        if path['wrapperNull']:continue
        frame=path['frame'];lives=[r for r in frame.get('hiddenSourceLocalLifetimes',[])if r['memberIndex']==index]
        need('own-reset-before-source-and-protected-result-through-store',zeros[0]['instruction']in path['selectedProgram']
            and path['selectedProgram'].index(zeros[0]['instruction'])<path['selectedProgram'].index(read['instruction'])
            and len(lives)==1 and lives[0]['bytes']==8 and lives[0]['displacement']==local['displacement']
            and lives[0]['sourceInstruction']==read['instruction']and lives[0]['fieldStores']==stores
            and lives[0]['liveThroughInstruction']==stores[0]['instruction']
            and any(z.get('instruction')==zeros[0]['instruction']for z in frame.get('initializedZeroLocalProofs',[])))
    return dict(fieldName=read['fieldName'],typeName=name,capability=capability,readerMethodDefinition=cap['staticReaderMethodDefinition'],
        sourceTargetRva=cap['staticReaderTargetRva'],staticReferenceCapabilityShape=cap,ordinaryReferenceIdentityClaimed=False,
        staticReferenceTransfer=dict(sourceAbi='void-byref-reference8',wholeReferenceBytes=8,sourceLocal=local,fieldStores=stores,
            completeFieldTransferAndFrameProved=True))
