"""Join the reviewed current pooled Patrol component to this whole host source."""
TYPE='Beyond.Gameplay.AI.Config.NpcPatrolData'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
PAIR='Beyond.Blackboard+DataPair'
COUNT_LIMIT=4096
REFERENCE_PARENTS={(TYPE,'points','Beyond.Gameplay.AI.Config.NpcPatrolPoint'),
    ('Beyond.Gameplay.AI.Config.NpcPatrolPoint','actions','Beyond.Gameplay.Core.PatrolSubAction'),
    ('Beyond.Gameplay.LevelData','npcPatrol',TYPE)}


def extend_layout(layout,bridges,induction,pair_component):
    """The host's new bounds do not change the separately reviewed base profile."""
    import copy
    if (layout.get('root'),layout.get('countLimit'))!=(TYPE,17):
        raise ValueError('currentLevelDataPatrol.closed-layout')
    if {(r['parent'],r['field'],r['element'])for r in bridges}!=REFERENCE_PARENTS or len(bridges)!=3:
        raise ValueError('currentLevelDataPatrol.exact-reference-parents')
    actual={(owner,row['name'],row['element'])for owner,rows in layout['records'].items()
        for row in rows if row['wire']=='list'}
    if actual!=REFERENCE_PARENTS-{('Beyond.Gameplay.LevelData','npcPatrol',TYPE)}:
        raise ValueError('currentLevelDataPatrol.reference-child-grammar')
    if (induction.get('countProfile'),induction.get('headerBytes'),induction.get('elementRuntimeBytes'),
            induction.get('elementGrammarAdmitted'))!=('all-positive-Int32',4,8,False):
        raise ValueError('currentLevelDataPatrol.reference-count-induction')
    child=pair_component['capabilities']['skill-root-data-pair']
    collection=pair_component['capabilities']['skill-root-data-pair-list-positive']
    if child.get('nullReturnsDefaultValue')is not True or (child.get('typeName'),child.get('managedBytes'),child.get('memberCount'),
            child.get('nullReturnsDefaultValue'),child.get('positiveWireBytes'),child.get('nullWireBytes'))!=(PAIR,32,4,True,18,1):
        raise ValueError('currentLevelDataPatrol.exact-DataPair-child')
    if collection.get('positiveCountsAdmitted')is not True or collection.get('elementGrammarAdmitted')is not True or (collection.get('closedListType'),collection.get('countLimit'),collection.get('positiveCountsAdmitted'),
            collection.get('elementGrammarAdmitted'),collection.get('managedElementBytes'))!=(
            'System.Collections.Generic.List`1<'+PAIR+'>',COUNT_LIMIT,True,True,32):
        raise ValueError('currentLevelDataPatrol.exact-DataPair-list')
    result=copy.deepcopy(layout);result['countLimit']=COUNT_LIMIT
    rows=[row for owner,fields in result['records'].items()for row in fields if row['wire']=='empty-list']
    if len(rows)!=1 or (rows[0]['name'],rows[0]['element'])!=('eventBBDataPairs',PAIR):
        raise ValueError('currentLevelDataPatrol.one-DataPair-child')
    rows[0]['wire']='data-pair-list'
    result['dataPairCapability']=copy.deepcopy(child)
    result['dataPairListCapability']=copy.deepcopy(collection)
    return result


def bind_parent(field,read,bridge,base):
    if (field['name'],field['typeName'],read['fieldName'])!=('npcPatrol',LIST,'npcPatrol'):
        raise ValueError('currentLevelDataPatrol.closed-parent')
    if (bridge['parent'],bridge['field'],bridge['declaredType'],bridge['element'])!=(
            'Beyond.Gameplay.LevelData','npcPatrol',LIST,TYPE):
        raise ValueError('currentLevelDataPatrol.nominal-source-bridge')
    source=bridge['source']
    if (base+source['callRva'],base+source['targetRva'],source['fieldOffset'])!=(
            read['sourceCall'],read['sourceTarget'],field['offset']):
        raise ValueError('currentLevelDataPatrol.actual-call-target-store')
    return dict(field=field,source=read,componentParent=bridge)


def derive(image,pins,leveldata):
    import json
    from scripts.game_data import leveldata_npc_patrol_native as native
    from scripts.game_data.memorypack import patrol_sources,scalar_param_native as scalar
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    from scripts.game_data.memorypack.skill_root_value_lists import derive_data_pair_list_component
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    if leveldata['nativeInputs']!=pins:raise ValueError('currentLevelDataPatrol.selected-inputs')
    raw=native.CONTRACT_PATH.read_bytes();fact=json.loads(raw)
    if (fact.get('schema'),fact.get('status'),fact.get('nativeInputs'),fact.get('referenceListCountLimit'),
            fact.get('blackboardCounts'),fact.get('unionTags'))!=(native.SCHEMA,'exact-current-build',pins,17,[-1,0],[0,1]):
        raise ValueError('currentLevelDataPatrol.contract-profile')
    proof=patrol_sources.validate_on_image(image,fact)
    bridges=[r for r in proof['lists']['bridges']if r['parent']=='Beyond.Gameplay.LevelData']
    if len(bridges)!=1:raise ValueError('currentLevelDataPatrol.one-owning-parent')
    parent,=[(f,r)for f,r in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True)if f['name']=='npcPatrol']
    bound=bind_parent(*parent,bridges[0],image.pe.image_base)
    base=image.pe.image_base;ctx=NativeReferenceContext(image)
    offsets=scalar.reader_offsets(image,'currentLevelDataPatrol')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    body=owned(image,proof['lists']['entry']['pointer'])
    induction=reference_list_induction(body['regions'],body['pointer'],offsets,
        {k:base+v for k,v in proof['lists']['symbols'].items()})
    action,=[r for r in proof['direct']if r['type']=='Beyond.Gameplay.Core.PatrolSubAction']
    pair,=[r for r in action['fields']if r['name']=='eventBBDataPairs']
    if (pair['type'],pair['mode'],pair['typed'])!=('System.Collections.Generic.List`1<'+PAIR+'>','reference',True):
        raise ValueError('currentLevelDataPatrol.nominal-DataPair-parent')
    pair_component=derive_data_pair_list_component(image,pins,typed_request=pair['typedContext'],
        call_target=pair['target'],count_limit=COUNT_LIMIT)
    # The direct record program freshly proves this actual typed call, returned
    # reference and field store. No SkillData root-field join is transferred.
    cap=pair_component['capabilities']['skill-root-data-pair-list-positive']
    if (cap['packableReaderTargetRva'],cap['packableReaderMethodDefinition'])!=(
            pair['target']-base,pair['typedContext']['methodSpec'][0]):
        raise ValueError('currentLevelDataPatrol.DataPair-parent-source')
    layout=extend_layout(native._layout(image,proof),proof['lists']['bridges'],induction,pair_component)
    if native.CONTRACT_PATH.read_bytes()!=raw:raise ValueError('currentLevelDataPatrol.declaration-drift')
    return json.loads(json.dumps(dict(nativeInputs=pins,parent=bound,component=proof,layout=layout,
        referenceListInduction=induction,dataPairList=dict(parent=pair,component=pair_component),
        capability=dict(typeName=LIST,headerBytes=4,countLimit=COUNT_LIMIT,allowedCounts=None,
            recordMemberCount=10,wholeGrammarAdmitted=True,blackboardCounts=None,
            blackboardCountLimit=COUNT_LIMIT,blackboardElementValueBytes=32,
            unionTags=[0,1],nullUnionMarker=255,wholeOwnerAdmitted=False),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
