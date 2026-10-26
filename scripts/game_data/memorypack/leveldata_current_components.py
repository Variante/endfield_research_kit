"""Fresh current LevelData children; positive unknown owners remain closed.

The field/read/store owner and each child source run on the same selected
image. The returned manifest is an internal input to the current source
operation, never a runtime-observation or an unconditional formatter choice.
"""
ROOT='Beyond.Gameplay.LevelData'
BRIEF='Beyond.Gameplay.LevelScriptBriefData'


def derive(image,pins,owners,children):
    import json
    from scripts.game_data.memorypack import (
        leveldata_owner_sources,leveldata_empty_collection_sources,
        leveldata_empty_record_sources,leveldata_null_object_sources,
        leveldata_empty_dictionary_sources,leveldata_airwall_record_sources,
        leveldata_airwall_geometry_sources,leveldata_vector2_list_sources,
        leveldata_levelscript_parent_sources,levelscript_spawner_sources,leveldata_mission_sources,
        levelscript_ulong_dictionary_sources,leveldata_patrol_component_sources,leveldata_npc_component_sources,
        leveldata_npc_child_sources,leveldata_simple_record_sources,leveldata_extended_record_sources,
        leveldata_npc_battle_components,leveldata_npc_battle_layout,leveldata_npc_extra_sources,
        leveldata_function_area_sources,leveldata_condition_components,leveldata_spline_sources,leveldata_lock_sources,
        leveldata_function_specific_components,leveldata_water_sources,leveldata_map_region_sources,leveldata_attract_point_sources,leveldata_npc_group_sources,leveldata_waypoint_sources,
        leveldata_specific_components,leveldata_integer_host_sources,leveldata_authored_patrol_sources,leveldata_occlusion_sources,
        leveldata_factory_mine_sources,leveldata_enemy_sources,leveldata_core_patrol_sources,leveldata_factory_config_sources,
        leveldata_factory_region_sources,leveldata_auxiliary_container_sources,leveldata_enemy_group_sources,
        leveldata_levelwide_components,leveldata_condition_global_var_sources,leveldata_mission_area_sources)
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need=lambda k,e,a:scalar.need('currentLevelDataComponents',k,e,a)
    need('current-root-owners',pins,owners['nativeInputs'])
    need('current-pooled-children',pins,children['nativeInputs'])
    owner=leveldata_owner_sources.derive(image,pins)
    proofs=dict(owner=owner)
    proofs['emptyLists']=leveldata_empty_collection_sources.derive(image,pins,owner)
    proofs['emptyRecords']=leveldata_empty_record_sources.derive(image,pins,owner)
    proofs['nullObjects']=leveldata_null_object_sources.derive(image,pins,owner)
    proofs['emptyDictionary']=leveldata_empty_dictionary_sources.derive(image,pins,owner)
    proofs['airWalls']=leveldata_airwall_record_sources.derive(image,pins,owner)
    proofs['geometry']=leveldata_airwall_geometry_sources.derive(image,pins,proofs['airWalls'])
    proofs['vector2List']=leveldata_vector2_list_sources.derive(image,pins,proofs['geometry'])
    proofs['scriptParents']=leveldata_levelscript_parent_sources.derive(image,pins,owners,owner)
    proofs['spawners']=levelscript_spawner_sources.derive(image,pins,owner)
    proofs['ulongDictionaries']=levelscript_ulong_dictionary_sources.derive(image,pins,owners,owner)
    proofs['missions']=leveldata_mission_sources.derive(image,pins,proofs['airWalls'],children)
    proofs['npcPatrol']=leveldata_patrol_component_sources.derive(image,pins,owner)
    proofs['corePatrol']=leveldata_core_patrol_sources.derive(image,pins,owner)
    proofs['factoryRegions']=leveldata_factory_region_sources.derive(image,pins,owner)
    proofs['auxiliaryContainers']=leveldata_auxiliary_container_sources.derive(image,pins,owner)
    proofs['enemyGroups']=leveldata_enemy_group_sources.derive(image,pins,owner)
    proofs['missionAreas']=leveldata_mission_area_sources.derive(image,pins,owner)
    proofs['npcs']=leveldata_npc_component_sources.derive(image,pins,owner)
    proofs['npcChildren']=leveldata_npc_child_sources.derive(image,pins,proofs['npcs'])
    proofs['npcBattle']=leveldata_npc_battle_components.derive(image,pins,proofs['npcs'])
    proofs['npcExtra']=leveldata_npc_extra_sources.derive(image,pins,proofs['npcs'])
    proofs['simpleRecords']=leveldata_simple_record_sources.derive(image,pins,owner)
    proofs['extendedRecords']=leveldata_extended_record_sources.derive(image,pins,owner,positive_polyline=True)
    proofs['functionAreaBase']=leveldata_function_area_sources.derive(image,pins,proofs['emptyRecords'],positive_factory_hide=True)
    proofs['functionAreaRanges']=leveldata_function_area_sources.derive_ranges(image,pins,proofs['emptyRecords'],proofs['geometry'])
    proofs['splines']=leveldata_spline_sources.derive(image,pins,owner)
    proofs['locks']=leveldata_lock_sources.derive(image,pins,owner)
    proofs['water']=leveldata_water_sources.derive(image,pins,owner)
    proofs['mapVolumes']=leveldata_map_region_sources.derive(image,pins,owner)
    proofs['attractPoints']=leveldata_attract_point_sources.derive(image,pins,owner)
    proofs['npcGroups']=leveldata_npc_group_sources.derive(image,pins,owner)
    proofs['wayPoints']=leveldata_waypoint_sources.derive(image,pins,owner)
    proofs['specificData']=leveldata_specific_components.derive(image,pins,owner)
    proofs['integerHosts']=leveldata_integer_host_sources.derive(image,pins,owner)
    proofs['authoredPatrol']=leveldata_authored_patrol_sources.derive(image,pins,owner)
    proofs['occlusion']=leveldata_occlusion_sources.derive(image,pins,owner)
    proofs['factoryMines']=leveldata_factory_mine_sources.derive(image,pins,owner)
    proofs['enemies']=leveldata_enemy_sources.derive(image,pins,owner)
    proofs['factoryConfig']=leveldata_factory_config_sources.derive(image,pins,owner)
    proofs['conditions']=leveldata_condition_components.derive(image,pins)
    proofs['levelWideConditions']=leveldata_condition_global_var_sources.derive_opt_in(image,pins)
    need('same-independent-LevelWide-default-condition-graph',proofs['conditions']['capability'],
        proofs['levelWideConditions']['capability']['baseCapability'])
    proofs['levelWide']=leveldata_levelwide_components.derive(image,pins,owner,
        condition=dict(nativeInputs=pins,capabilities={leveldata_condition_components.CAP:
            proofs['levelWideConditions']['capability']}))
    proofs['functionSpecific']=leveldata_function_specific_components.derive(image,pins,profile='all18')
    condition=proofs['conditions']['capability'];condition_bindings={}
    need('same-independently-derived-condition-graph',condition,
        proofs['functionSpecific']['children']['complex']['conditions']['capability'])
    need('same-independently-derived-occlusion-condition-graph',condition,
        proofs['occlusion']['condition']['capability'])
    # Every consumer retains its actual nominal request and E8 target. The
    # independently complete graph never supplies a parent join by name.
    field,read=next((f,r)for f,r in zip(owner['fields'],owner['program']['orderedReads'],strict=True)if f['name']=='buildableCondition')
    usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-image.pe.image_base,label='currentConditions.hostParent')
    binding=leveldata_condition_components.bind_reference(pins,dict(fieldName=field['name'],typeName=field['typeName'],
        sourceTargetRva=read['sourceTarget']-image.pe.image_base,typedRequest=usage),
        dict(nativeInputs=pins,capabilities={leveldata_condition_components.CAP:condition}),leveldata_condition_components.CAP)
    condition_bindings[ROOT+'::buildableCondition']=dict(binding,ownerType=ROOT)
    interactive_parent=proofs['conditions']['interactiveParent'];usage=interactive_parent['typedRequest']
    binding=leveldata_condition_components.bind_reference(pins,dict(fieldName='progressLockCondition',typeName=condition['typeName'],
        sourceTargetRva=interactive_parent['readValueTargetRva'],typedRequest=usage),
        dict(nativeInputs=pins,capabilities={leveldata_condition_components.CAP:condition}),leveldata_condition_components.CAP)
    condition_bindings['Beyond.Gameplay.LevelInteractiveData::progressLockCondition']=dict(binding,ownerType='Beyond.Gameplay.LevelInteractiveData')
    condition['parentBindings']=condition_bindings
    proofs['conditionHostParent']=dict(field=field,source=read,typedRequest=derive_typed_usage_context(image,
        read['typedUsage']['instruction']-image.pe.image_base,label='currentConditions.hostParentBookend'))
    collections={};records={}
    def collection(original,field,limit,*,whole=False):
        name=original+'::'+field['name']
        if name in collections:raise ValueError('currentLevelDataComponents.duplicate-collection:'+name)
        collections[name]=dict(typeName=field['typeName'],headerBytes=4,countLimit=limit,
            allowedCounts=[-1,0]if limit==0 else None,wholeGrammarAdmitted=whole,
            wholeOwnerAdmitted=False)
    for parent in proofs['emptyLists']['parents']:collection(ROOT,parent['field'],0)
    for original,record in proofs['emptyRecords']['records'].items():
        records[original]=dict(memberCount=len(record['fields']),nullAdmitted=True,
            positiveAdmitted=True,childPositiveElementsAdmitted=False)
        for child in record['childLists']:collection(original,child['field'],0)
    for parent in proofs['nullObjects']['parents']:
        name=parent['field']['typeName'];records[name]=dict(nullAdmitted=True,positiveAdmitted=False)
    for section in('airWalls','geometry'):
        for original,record in proofs[section]['records'].items():
            records[original]=dict(memberCount=len(record['fields']),nullAdmitted=True,positiveAdmitted=True)
    # The shared reference-list program proves all positive signed counts;
    # this consumer sets explicit finite resource limits independently.
    for parent in proofs['airWalls']['parents']:
        name=parent['owner']+'::'+parent['field']['name']
        collections.pop(name,None);collection(parent['owner'],parent['field'],4096,whole=True)
    vector=proofs['vector2List']['parent']
    collection('Beyond.Gameplay.PolyLineWall',dict(name=vector['fieldName'],typeName=vector['typeName']),65536,whole=True)
    for name,record in proofs['geometry']['records'].items():
        need('geometry-normal-program:'+name,True,any(not p['null']for p in record['programs']))
    total='Beyond.Gameplay.MissionTotalCheckData'
    for original in proofs['missions']['records']:
        records[original]=dict(memberCount=4,nullAdmitted=True,positiveAdmitted=True)
    for parent in proofs['missions']['listParents']:
        collection(total,dict(name=parent['fieldName'],typeName=parent['typeName']),4096,whole=True)

    host_fields={f['name']:f for f in owner['fields']}
    wide=proofs['levelWide'];binding=wide['parent']['binding']
    need('LevelWide-actual-host-dictionary',wide['parent']['typedRequest'],wide['outer']['actualParent']['typedRequest'])
    records[leveldata_levelwide_components.TYPE]=wide['capability']
    collections[ROOT+'::levelWideConfigs']=dict(typeName=binding['typeName'],headerBytes=4,
        countLimit=wide['capability']['countLimit'],allowedCounts=None,profileAdmitted=True,
        wholeGrammarAdmitted=False,initiallyNullDictionariesRequired=True,
        actualCallbackEqualsCanonicalRequired=True,runtimeFormatterSelectionObserved=False,childBinding=binding)
    for field in('levelScriptBriefDataDict','levelScriptDataPathDict'):
        collection(ROOT,host_fields[field],16384,whole=True)
    records[BRIEF]=dict(memberCount=9,nullAdmitted=True,positiveAdmitted=True)
    brief=owners['owners'][BRIEF]
    for field in brief['fields']:
        name=field['typeName']
        if name not in children['capabilities']:continue
        cap=children['capabilities'][name]
        need('Brief-whole-child:'+field['name'],True,cap.get('wholeGrammarAdmitted'))
        need('Brief-child-bounds:'+field['name'],(16384,4),(cap.get('countLimit'),cap.get('headerBytes')))
        collection(BRIEF,field,16384,whole=True)
    need('four-exact-Brief-child-parents',
        ['interactiveActiveRiskEntityIdList','properties','propertyIdToKeyMap','refWorldEntityIdList'],
        [f['name']for f in brief['fields']if BRIEF+'::'+f['name']in collections])
    collection(ROOT,host_fields['autoSpawnedInteractives'],16384,whole=True)
    for field in('interactives','spawners'):
        collections.pop(ROOT+'::'+field);collection(ROOT,host_fields[field],16384,whole=True)
    patrol=proofs['npcPatrol']['capability']
    need('Patrol-own-positive-count-profile',(4096,4096,32),
        (patrol['countLimit'],patrol['blackboardCountLimit'],patrol['blackboardElementValueBytes']))
    collections.pop(ROOT+'::npcPatrol');collection(ROOT,host_fields['npcPatrol'],4096,whole=True)
    collections.pop(ROOT+'::npcs');collections[ROOT+'::npcs']=proofs['npcs']['capability']
    for field,original in leveldata_simple_record_sources.FIELDS.items():
        collections.pop(ROOT+'::'+field);collection(ROOT,host_fields[field],4096)
        collections[ROOT+'::'+field].update(profileAdmitted=True,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
        records[original]=proofs['simpleRecords']['capabilities'][original]
    for field,original in leveldata_extended_record_sources.FIELDS.items():
        collections.pop(ROOT+'::'+field);collection(ROOT,host_fields[field],4096)
        collections[ROOT+'::'+field].update(profileAdmitted=True,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
        records[original]=proofs['extendedRecords']['capabilities'][original]
    records[leveldata_extended_record_sources.POLY]=proofs['extendedRecords']['positivePolyline']['capability']
    area=proofs['functionAreaBase'];original=leveldata_function_area_sources.PARENT
    need('FunctionArea-exact-positive-child',(True,False,4096),
        (area['capability']['profileAdmitted'],area['capability']['wholeGrammarAdmitted'],area['capability']['countLimit']))
    records[original].pop('childPositiveElementsAdmitted')
    records[original].update(positiveChildFields=['baseData','functionAreaConditions','ranges','specificDatas'],otherPositiveChildElementsAdmitted=False)
    records[leveldata_function_area_sources.TYPE]=area['capability']
    need('FunctionArea-positive-factory-hide',True,area['capability']['positiveFactoryHideDescAdmitted'])
    records[leveldata_function_area_sources.HIDE]=area['capability']['factoryHideCapability']
    core=proofs['corePatrol'];parent=core['parent'];binding=parent['binding'];request=parent['typedRequest']
    need('CorePatrol-actual-host-list',request,parent['collection']['witnessComponent']['typedRequest'])
    records[leveldata_core_patrol_sources.ROOT]=core['capability']
    collections[ROOT+'::patrols']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=leveldata_core_patrol_sources.LIMIT,
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,childBinding=binding)
    factory=proofs['factoryConfig'];factory_cap=factory['capability']
    records[leveldata_factory_config_sources.BLACKBOX]=factory_cap
    parent=factory['parents']['predefinedParams'];binding=parent['binding'];request=parent['typedRequest']
    need('FactoryConfig-actual-predefined-host-list',request,parent['collection']['witnessComponent']['typedRequest'])
    collections[ROOT+'::predefinedParams']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=leveldata_factory_config_sources.LIMIT,
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,childBinding=binding)
    regions=proofs['factoryRegions'];binding=regions['parent']['binding'];request=regions['parent']['typedRequest']
    need('FactoryRegion-actual-host-list',request,regions['parent']['collection']['witnessComponent']['typedRequest'])
    records[leveldata_factory_region_sources.REGION]=regions['capability']
    collections[ROOT+'::factoryRegions']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=leveldata_factory_region_sources.LIMIT,
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,childBinding=binding)
    records.update(proofs['auxiliaryContainers']['capabilities'])
    groups=proofs['enemyGroups'];binding=groups['parent']['binding'];request=groups['parent']['typedRequest']
    need('EnemyGroup-actual-host-list',request,groups['parent']['collection']['witnessComponent']['typedRequest'])
    records[leveldata_enemy_group_sources.GROUP]=groups['capability']
    collections[ROOT+'::enemyGroup']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=leveldata_enemy_group_sources.LIMIT,
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,childBinding=binding)
    mission=proofs['missionAreas'];binding=mission['parent']['binding'];request=mission['parent']['typedRequest']
    need('MissionArea-actual-host-list',request,mission['parent']['collection']['witnessComponent']['typedRequest'])
    records[leveldata_mission_area_sources.TYPE]=mission['capability']
    collections[ROOT+'::missionAreas']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=leveldata_mission_area_sources.LIMIT,
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,initiallyNullListRequired=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,childBinding=binding)
    field,=[f for f in area['parent']['ownedParent']['fields']if f['name']=='baseData']
    collections.pop(original+'::baseData');collection(original,field,4096)
    request=area['parent']['typedRequest'];component=area['parent']['collection']['witnessComponent']
    need('FunctionArea-actual-parent-source',request,component['typedRequest'])
    collections[original+'::baseData'].update(profileAdmitted=True,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        childBinding=dict(fieldName='baseData',typeName=field['typeName'],capability=leveldata_function_area_sources.CAP,
            readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=component['callTargetRva']))
    collections[original+'::ranges']=proofs['functionAreaRanges']['capability']
    records[leveldata_condition_components.TYPE]=condition
    records[leveldata_specific_components.TYPE]=proofs['specificData']['capability']
    for section,parents in(('integerHosts',proofs['integerHosts']['parents']),
            ('authoredPatrol',proofs['authoredPatrol']['parents']),
            ('occlusion',{leveldata_occlusion_sources.FIELD:proofs['occlusion']['parent']}),
            ('factoryMines',{leveldata_factory_mine_sources.FIELD:proofs['factoryMines']['parent']}),
            ('enemies',{leveldata_enemy_sources.FIELD:proofs['enemies']['parent']})):
        records.update({leveldata_enemy_sources.TYPE:proofs[section]['capability']}if section=='enemies'else proofs[section]['capabilities'])
        for field,parent in parents.items():
            binding=parent['binding'];request=parent['typedRequest'];witness=parent['collection']['witnessComponent']
            need('actual-finite-host-list:'+field,request,witness['typedRequest'])
            collections[ROOT+'::'+field]=dict(typeName=parent['declaration']['typeName'],headerBytes=4,countLimit=4096,
                allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,
                actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
                childBinding=dict(fieldName=field,typeName=binding['typeName'],capability=binding['capability'],
                    readerMethodDefinition=binding['readerMethodDefinition'],sourceTargetRva=binding['sourceTargetRva']))
    records[leveldata_condition_components.AREA_RECORD]=proofs['conditions']['functionArea']['recordCapability']
    collections[original+'::functionAreaConditions']=proofs['conditions']['functionArea']['capability']
    specific=proofs['functionSpecific']['capability'];specific['owningConditionGraphJoined']=True
    records[leveldata_function_specific_components.TYPE]=specific
    binding=specific['listParent']
    collections[original+'::specificDatas']=dict(typeName=binding['typeName'],headerBytes=4,countLimit=binding['countLimit'],
        allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,
        actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
        childBinding=dict(fieldName='specificDatas',typeName=binding['typeName'],capability=leveldata_function_specific_components.LIST_CAP,
            readerMethodDefinition=binding['readerMethodDefinition'],sourceTargetRva=binding['sourceTargetRva']))
    for section,original,field_name,capability in(('splines',leveldata_spline_sources.TYPE,'splines',leveldata_spline_sources.CAP),
            ('locks',leveldata_lock_sources.TYPE,'interactiveLockData',leveldata_lock_sources.CAP),
            ('water',leveldata_water_sources.TYPE,'waterVolumes',leveldata_water_sources.CAP),
            ('water',leveldata_water_sources.TYPE,'riftVolumes',leveldata_water_sources.CAP),
            ('mapVolumes',leveldata_map_region_sources.REGION,'mapVolumeDatas',leveldata_map_region_sources.CAP),
            ('attractPoints',leveldata_attract_point_sources.TYPE,'npcAttractPointData',leveldata_attract_point_sources.CAP),
            ('npcGroups',leveldata_npc_group_sources.GROUP,'npcGroup',leveldata_npc_group_sources.CAP),
            ('wayPoints',leveldata_waypoint_sources.TYPE,'worldWayPointData',leveldata_waypoint_sources.CAP)):
        proof=proofs[section]
        parent=proof['additionalParents'][field_name]if section=='water'and field_name=='riftVolumes'else proof['parent']
        request=parent['typedRequest'];witness=parent['collection']['witnessComponent']
        need('actual-positive-host-list:'+field_name,request,witness['typedRequest'])
        caps=proof['capabilities']if section in('locks','mapVolumes','npcGroups')else{original:proof['capability']}
        records.update(caps)
        declaration=parent['declaration']if section in('water','mapVolumes','attractPoints','npcGroups','wayPoints')else parent['field']
        collections[ROOT+'::'+field_name]=dict(typeName=declaration['typeName'],headerBytes=4,countLimit=4096,
            allowedCounts=None,profileAdmitted=True,wholeGrammarAdmitted=False,
            actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
            childBinding=dict(fieldName=field_name,typeName=declaration['typeName'],capability=capability,
                readerMethodDefinition=request['methodSpec'][0],sourceTargetRva=witness['callTargetRva']))
    from scripts.game_data.memorypack.leveldata_lang_key_components import TYPE as LANG_KEY,CAP as LANG_CAP
    records[LANG_KEY]=proofs['locks']['langKey']['capabilities'][LANG_CAP]
    interactive=children['capabilities']['System.Collections.Generic.Dictionary`2<uint,Beyond.Gameplay.LevelInteractiveData>']
    need('Interactive-exact-grammar','MC25-or-FF;condition-FF-only',interactive.get('recordGrammar'))
    records['Beyond.Gameplay.LevelInteractiveData']=dict(recordGrammar='MC25-or-FF;bounded-condition-runtime',
        conditionCapability=leveldata_condition_components.CAP)
    spawner=proofs['spawners']['capability']
    need('spawner-whole-record',(True,6),(spawner['wholeGrammarAdmitted'],spawner['recordMemberCount']))
    records['Beyond.Gameplay.LevelSpawnerInstData']=dict(memberCount=6,nullAdmitted=True,positiveAdmitted=True)
    battle=leveldata_npc_battle_layout.make_profile(proofs['npcBattle'])
    npc_layout=leveldata_npc_battle_layout.extend_layout(proofs['npcChildren']['layout'],battle)
    npc_layout=leveldata_npc_extra_sources.extend_layout(npc_layout,proofs['npcExtra']['profile'])
    caps=dict(orderedFields=[f['name']for f in owner['fields']],collections=collections,records=records,
        patrolLayout=proofs['npcPatrol']['layout'],
        npcLayout=npc_layout,npcChildProfile=proofs['npcChildren']['capability'],npcBattleProfile=battle,
        npcExtraProfile=proofs['npcExtra']['profile'])
    return json.loads(json.dumps(dict(nativeInputs=pins,proofs=proofs,capabilities=caps,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
