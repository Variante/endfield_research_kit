"""Exact current LevelData reference-list parents with null/empty counts only.

No nominal element grammar follows from the closed typed request. Each parent
is independently bound to the current reference collection source and its
owned generic VAR/factory/provider/count/output programs.
"""
REFERENCE_FIELDS=(
 'airWalls','aiTransData','cameraPoses','charPatrol','doodadGroup','dynamicOccludeAreas',
 'enemies','enemyGroup','enemyPatrol','environmentVolumes','factoryMines','factoryRegions',
 'guideHints','interactiveLockData','interactives','levelUIs','mapVolumeDatas','missionAreas',
 'npcAttractPointData','npcClusters','npcGroup','npcPatrol','npcs','patrols','predefinedParams',
 'riftVolumes','sludgeDatas','spawners','splines','waterVolumes','worldWayPointData',
)


def select_fields(leveldata):
    """Closed field selection; this function grants no native/source capability."""
    selected=[]
    for field,read in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True):
        if field['name']not in REFERENCE_FIELDS:continue
        if (read['fieldName']!=field['name']or read.get('typedUsage')is None
                or not field['typeName'].startswith('System.Collections.Generic.List`1<')
                or not field['typeName'].endswith('>')):
            raise ValueError('leveldataEmptyLists.closed-field-source:'+field['name'])
        selected.append((field,read))
    if tuple(f['name']for f,_ in selected)!=REFERENCE_FIELDS:
        raise ValueError('leveldataEmptyLists.complete-current-parent-set')
    return selected


def derive(image,pins,leveldata):
    import json
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    if pins!=leveldata['nativeInputs']:raise ValueError('leveldataEmptyLists.selected-inputs')
    base=image.pe.image_base;parents=[];capabilities={}
    for field,read in select_fields(leveldata):
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataEmptyLists.parent')
        element=field['typeName'][len('System.Collections.Generic.List`1<'):-1]
        component=derive_reference_list_component(image,pins,typed_request=usage,
            call_target=read['sourceTarget'],element_type=element,count_limit=0)
        parents.append(dict(field=field,source=read,typedRequest=usage,component=component))
        capabilities[field['name']]=dict(closedListType=field['typeName'],headerBytes=4,
            allowedCounts=[-1,0],countLimit=0,positiveElementsAdmitted=False,
            elementGrammarAdmitted=False,parentFieldAdmitted=True,wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(nativeInputs=pins,parents=parents,capabilities=capabilities,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
