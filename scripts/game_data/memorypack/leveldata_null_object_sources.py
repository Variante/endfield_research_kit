"""Current LevelData object-parent FF joins, with no positive child grammar."""
FIELDS={
    'blackbox':'Beyond.Gameplay.LevelDataBlackbox',
    'buildableCondition':'Beyond.Gameplay.ConditionRuntimeBase',
    'specificData':'Beyond.Gameplay.LevelSpecificData',
}


def bind_parent(field,read,usage,child,base):
    name=FIELDS.get(field['name'])
    if name is None or field['typeName']!=name or read['fieldName']!=field['name']:
        raise ValueError('leveldataNullObject.closed-parent')
    if (usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),
            usage.get('methodArguments'))!=(6,'MemoryPack.MemoryPackReader','ReadValue',[],[name]):
        raise ValueError('leveldataNullObject.closed-ReadValue-request')
    if (child.get('nullAdmitted')is not True or child.get('positiveAdmitted')is not False
            or (child.get('status'),child.get('typeName'),child.get('contextTypeKind'),child.get('nullAdmitted'),
            child.get('nullMarker'),child.get('consumedBytes'),child.get('outputBytes'),child.get('positiveAdmitted'))!=(
            'validated',name,18,True,255,1,8,False)):
        raise ValueError('leveldataNullObject.exact-null-capability')
    if (read['sourceTarget']!=base+child['referenceReaderTargetRva']
            or usage['methodSpec'][0]!=child['referenceReaderMethodDefinition']):
        raise ValueError('leveldataNullObject.actual-source-target-or-definition')
    return dict(field=field,source=read,typedRequest=usage,
        capability=dict(typeName=name,nullMarker=255,consumedBytes=1,outputBytes=8,
            nullAdmitted=True,positiveAdmitted=False,reservedMarkersAdmitted=False,
            parentFieldAdmitted=True,wholeOwnerAdmitted=False))


def derive(image,pins,leveldata):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    if pins!=leveldata['nativeInputs']:raise ValueError('leveldataNullObject.selected-inputs')
    proofs={};parents=[];base=image.pe.image_base
    for field,read in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True):
        if field['name']not in FIELDS:continue
        child=derive_reference_null(image,pins,FIELDS[field['name']])
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataNullObject.parent')
        parent=bind_parent(field,read,usage,child,base)
        proofs[field['typeName']]=child;parents.append(parent)
    if {p['field']['name']for p in parents}!=set(FIELDS):
        raise ValueError('leveldataNullObject.complete-current-parent-set')
    return json.loads(json.dumps(dict(nativeInputs=pins,parents=parents,children=proofs,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
