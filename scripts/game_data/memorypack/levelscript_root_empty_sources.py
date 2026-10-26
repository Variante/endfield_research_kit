"""Independently typed current root null/empty containers, no positive children."""
ROOT='Beyond.Gameplay.LevelScriptData'


def derive(image,pins,owners,children,host):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack import scalar_param_native as scalar
    base=image.pe.image_base;ctx=NativeReferenceContext(image);cs=ContextSymbols(image)
    need=lambda k,e,a:scalar.need('currentLevelScriptEmptyRoot',k,e,a)
    need('selected-source-components',(pins,pins,pins),
        (owners['nativeInputs'],children['nativeInputs'],host['nativeInputs']))
    root=owners['owners'][ROOT];parents=[];caps={}
    for field,read in zip(root['fields'],root['program']['orderedReads'],strict=True):
        name=field['name']
        if name not in('enemies','interactiveLocks','modules','triggerVolumes'):continue
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='currentLevelScriptEmptyRoot.parent')
        bind_typed_read(image,usage,method_name='ReadPackable',argument=field['typeName'],kind=21,reference=True)
        if name in('enemies','interactiveLocks','triggerVolumes'):
            original={'enemies':'Beyond.Gameplay.LevelEnemyData','interactiveLocks':'Beyond.Gameplay.InteractiveLockData',
                'triggerVolumes':'Beyond.Gameplay.LevelScriptTriggerVolumeData'}[name]
            argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
            carrier=cs.type(argument.type_pointer_va)
            need('exact-root-UInt32-dictionary','System.Collections.Generic.Dictionary`2<uint,'+original+'>',carrier['name'])
            key,value=carrier['classArguments']
            need('nominal-UInt32-key',b'\x09\x80',bytes.fromhex(key['rawHex'])[10:12])
            raw=bytes.fromhex(value['rawHex'])
            need('nominal-root-child-reference',(b'\x12\x00',ctx.index.types[original].index),
                (raw[10:12],int.from_bytes(raw[:8],'little')))
            component=children['uintReferenceDictionary'];programs=component['programs']
            need('both-empty-count-programs',True,all(any(p['countProfile']==kind for p in programs)for kind in('null','zero')))
            # Fresh current pooled child parents share this actual reference
            # ReadPackable source, not a source alias inferred from names.
            actual=children['keyValueList']['component']['callTargetRva']
            need('actual-UInt32-parent-source',base+actual,read['sourceTarget'])
            component=dict(closedCarrier=carrier,component=component);witness=['uint','object']
        else:
            dictionary=host['proofs']['ulongDictionaries']
            component,=[p for p in dictionary['parents']if p['owner']==ROOT and p['field']['name']=='modules']
            need('actual-Module-parent',read,component['source']);witness=['ulong','object']
        parents.append(dict(field=field,source=read,typedRequest=usage,component=component))
        caps[name]=dict(typeName=field['typeName'],headerBytes=4,countLimit=0,allowedCounts=[-1,0],
            positiveChildrenAdmitted=False,sourceWitnessClassArguments=witness,
            actualCallbackEqualsCanonicalRequired=True,concreteRuntimeSelectionObserved=False,
            typedConstructorAndHelperCompatibilityRequired=True,wholeOwnerAdmitted=False)
    need('four-exact-empty-root-parents',{'enemies','interactiveLocks','modules','triggerVolumes'},set(caps))
    return json.loads(json.dumps(dict(nativeInputs=pins,parents=parents,capabilities=caps,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
