"""Join the current host's exact NPC list to the independent NPC profile."""
ROOT='Beyond.Gameplay.LevelData'
NPC='Beyond.Gameplay.Core.NpcRuntimeProxyData'
LIST='System.Collections.Generic.List`1<'+NPC+'>'


def bind_parent(field,read,declared,base):
    if (field['name'],field['typeName'],read['fieldName'],declared['member']['name'],
            declared['member']['declaredType'],declared['field'][:2])!=('npcs',LIST,'npcs','npcs',LIST,[ROOT,LIST]):
        raise ValueError('currentLevelDataNpc.exact-nominal-parent')
    if (base+declared['callRva'],base+declared['targetRva'],declared['field'][2])!=(
            read['sourceCall'],read['sourceTarget'],field['offset']):
        raise ValueError('currentLevelDataNpc.actual-call-target-store')
    return dict(field=field,read=read,independentNpcParent=declared)


def derive(image,pins,leveldata):
    import json
    from scripts.game_data import npc_runtime_native as native
    from scripts.game_data.memorypack.npc_runtime_sources import validate_components
    if leveldata['nativeInputs']!=pins:raise ValueError('currentLevelDataNpc.same-host-inputs')
    paths=dict(owner=native.CONTRACT_PATH,**{k:native.CONTRACTS_DIR/v for k,v in native.DEPENDENCIES.items()})
    before={k:p.read_bytes()for k,p in paths.items()};facts={k:json.loads(v)for k,v in before.items()}
    if any(f.get('nativeInputs')!=pins for f in facts.values()):raise ValueError('currentLevelDataNpc.selected-inputs')
    fact=facts.pop('owner');layout,proof=validate_components(image,pins,fact,facts)
    declared,=[r for r in fact['collections']['parents']if r['original']==ROOT]
    bridge,=[f for f in declared['fields']if f['member']['name']=='npcs']
    field,read=next((f,r)for f,r in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True)if f['name']=='npcs')
    parent=bind_parent(field,read,bridge,image.pe.image_base)
    if layout['containerKinds']!=['list','uint-dictionary','pool-dictionary']:
        raise ValueError('currentLevelDataNpc.selected-container-kinds')
    if before!={k:p.read_bytes()for k,p in paths.items()}:raise ValueError('currentLevelDataNpc.declaration-drift')
    return json.loads(json.dumps(dict(nativeInputs=pins,parent=parent,proof=proof,layout=layout,
        capability=dict(typeName=LIST,headerBytes=4,countLimit=16384,allowedCounts=None,
            profileAdmitted=True,wholeGrammarAdmitted=False,requiresFreshNpcSemanticGate=True,
            elementType=NPC,memberCount=layout['memberCount'],wholeOwnerAdmitted=False),
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
