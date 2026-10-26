"""Current RollingStone module profile composed with its exact root parent."""
ROOT='Beyond.Gameplay.LevelScriptData'
LIST='System.Collections.Generic.Dictionary`2<ulong,Beyond.Gameplay.LevelScriptModuleData>'


def bind_parent(field,read,declared,model,base):
    if (field['name'],field['typeName'],read['fieldName'],declared['field'])!=('modules',LIST,'modules',[ROOT,LIST,field['offset']]):
        raise ValueError('currentLevelScriptModules.nominal-parent')
    args=model['args']
    if (model['model'],args[1]+3,args[1]+13,args[2],args[3])!=('enclosing_root_field',
            read['typedUsage']['instruction'],read['sourceCall'],read['sourceTarget'],field['offset']):
        raise ValueError('currentLevelScriptModules.actual-call-target-store')
    if base+declared['typedContext']['instructionRva']!=read['typedUsage']['instruction']:
        raise ValueError('currentLevelScriptModules.same-context-source')
    return dict(field=field,source=read,declaredParent=declared)


def derive(image,pins,owners):
    import json
    from scripts.game_data import levelscript_module_structures_native as native
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    if owners['nativeInputs']!=pins:raise ValueError('currentLevelScriptModules.same-owner-pins')
    path=native.CONTRACT_PATH;raw=path.read_bytes();fact=json.loads(raw)
    if (fact.get('schema'),fact.get('status'),fact.get('nativeInputs'),fact.get('codecKinds'))!=(
            native.SCHEMA,'conditional-current-build-wire',pins,['RollingStoneControllerData']):
        raise ValueError('currentLevelScriptModules.exact-current-declaration')
    # Every selected complete source program, parent, nested callback, value
    # ABI and actual dispatch join is checked on this image by its owner.
    result=native._validate_native(image,fact)
    owner=owners['owners'][ROOT]
    field,read=next((f,r)for f,r in zip(owner['fields'],owner['program']['orderedReads'],strict=True)if f['name']=='modules')
    declared=fact['components']['enclosing']['rootField']
    model,=[r for r in fact['modelCalls']if r['model']=='enclosing_root_field']
    parent=bind_parent(field,read,declared,model,image.pe.image_base)
    fresh=derive_typed_usage_context(image,declared['typedContext']['instructionRva'],label='currentLevelScriptModules.parent')
    if json.loads(json.dumps(fresh))!=declared['typedContext']:raise ValueError('currentLevelScriptModules.fresh-typed-parent')
    tag=result['rollingTag']
    if type(tag)is not int or not 0<=tag<=65535:raise ValueError('currentLevelScriptModules.typed-tag')
    if path.read_bytes()!=raw:raise ValueError('currentLevelScriptModules.declaration-drift')
    return json.loads(json.dumps(dict(nativeInputs=pins,parent=parent,sourceResult=result,
        capability=dict(typeName=LIST,headerBytes=4,countLimit=16384,profileAdmitted=True,
            moduleType='Beyond.Gameplay.RollingStoneControllerData',
            wholeGrammarAdmitted=False,allowedModuleTags=[tag],nullUnionMarker=255,
            canonicalTagEncoding=True,reservedMarkersRefused=[251,252,253,254],
            positiveRecordMemberCount=3,launcherMemberCount=7,finiteFloatProfile=True,
            actualCallbackEqualsCanonicalRequired=True,sourceWitnessClassArguments=['ulong','object'],
            concreteRuntimeSelectionObserved=False,wholeOwnerAdmitted=False),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
