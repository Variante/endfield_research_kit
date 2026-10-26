"""Compose fresh current NPC components on one selected immutable native image."""
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
from scripts.game_data.memorypack import modelview_reference_sources,modelview_packable_sources
from scripts.game_data.il2cpp.formatter_registration import validate_eager_wrap_registration
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.memory_copy_bounded_native import validate_components as validate_copy
from scripts.game_data.memorypack import npc_parent_sources as parent,npc_entity_sources as entity,npc_tag_sources as tag,npc_envtalk_sources as env,npc_ai_components as ai,npc_collection_sources as collections,pooled_string_list_sources as strings,reference_adapter_sources as reference
from scripts.game_data.memorypack.npc_layout import layout


def validate_components(image,pins,fact,dependencies):
    if fact.get('schema')!='endfield.npc-runtime-native-contract.v1'or fact.get('status')!='exact-current-build'or fact['nativeInputs']!=pins:raise ValueError('npcRuntime.schema/selected-inputs')
    key,copy,string=(dependencies[k]for k in('key','copy','string'))
    if any(f['nativeInputs']!=pins for f in(key,copy,string)):raise ValueError('npcRuntime.dependency-selected-inputs')
    proof=dict(copy=validate_copy(image,copy),strings=strings.validate_string_components(image,string))
    proof['parent']=parent.validate_components(image,pins,fact['parent'],key,copy,fact['envTalk'])
    reader=fact['readValue'];base=image.pe.image_base
    if reader.get('schema')!='endfield.npc-reference-read-value-source.v1'or reader['nativeInputs']!=pins:raise ValueError('npcRuntime.read-value-source-schema')
    actual=sorted(tuple(r['runtimeTriple'][:2])for r in image.unwind_index.family(reader['entryRva'])['ranges'])
    if actual!=sorted((r['startRva'],r['endRva'])for r in reader['ownedWindows']):raise ValueError('npcRuntime.read-value-complete-owner')
    image.check_windows(reader['ownedWindows'],label='npcRuntime.read-value');regions=[(base+r['startRva'],image.pe.bytes_at_va(base+r['startRva'],r['endRva']-r['startRva']))for r in reader['ownedWindows']]
    validate_generic_contexts(image,reader['contexts'],label='npcRuntime.read-value');validate_read_value_context(image,reader['contexts'][1],reader['contexts'][2],GenericEntries(image),fail=lambda k,e,a:(_ for _ in()).throw(ValueError('npcRuntime.read-value:'+str((k,e,a))[:1200])))
    proof['readValue']=modelview_reference_sources.read_value(regions,base+reader['entryRva'],{k:base+v for k,v in key['referenceRoutes']['symbolRvas'].items()})
    proof['readPackable']=modelview_packable_sources.validate_components(image,pins,fact['readPackable'],key['referenceRoutes'])
    for member,transfer in zip(fact['parent']['members'],proof['parent']['fieldTransfers'],strict=True):
        if transfer['mode']=='ordinary'and member['kind']=='object'and member['declaredType']not in('Beyond.LangKey','Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId','UnityEngine.Vector3')and transfer['target']!=base+reader['entryRva']:raise ValueError('npcRuntime.actual-reference-read-value:'+member['name'])
        if member['kind']=='list'and transfer['target']!=base+fact['readPackable']['entryRva']:raise ValueError('npcRuntime.actual-reference-read-packable:'+member['name'])
    proof['tag']=tag.validate_components(image,pins,fact['tag'])
    proof['entity']=entity.validate_components(image,pins,fact['entity'],key)
    proof['envTalk']=env.validate(image,pins,fact['envTalk'],string,copy)
    proof['ai']=ai.validate_components(image,pins,fact['ai'],string)
    ctx=NativeReferenceContext(image);build=Build(image,pins);root,=[w for w in build.wrappers.values()if w.wrapped_type==fact['parent']['originalType']];types={m.name:m.declared_type for m in root.members}
    expected={types[n]for n in('battleData','hitData','npcAbility','npcInfoData','npcRuntimeData')}
    if {r['eager']['originalType']for r in fact['nullReferences']}!=expected or len(fact['nullReferences'])!=5:raise ValueError('npcRuntime.exact-null-child-set')
    for selected in fact['nullReferences']:
        original=selected['eager']['originalType']
        if ctx.is_value_type(original):raise ValueError('npcRuntime.null-child-reference-ABI')
        validate_eager_wrap_registration(image,selected['eager'],label='npcRuntime.null-child')
        validate_registered_formatter_composition(image,selected['composition'],label='npcRuntime.null-child')
    core=dict(key['referenceRoutes'],wrappers=[])
    proof['nullReferences']=reference.validate_reference_routes(image,core,[])
    proof['collections']=collections.validate_components(image,pins,fact['collections'],fact['parent'],string)
    kinds=proof['collections']['collectionKinds']
    if set(kinds)!={'list','uint-dictionary','pool-dictionary'}or len(kinds)!=3:raise ValueError('npcRuntime.exact-enclosing-container-kinds')
    tag_type='Beyond.Gameplay.Core.GameplayTag';ai_type='Beyond.Gameplay.Core.NpcAiInstanceData';env_type='Beyond.Gameplay.Core.NpcRuntimeEnvTalkData';entity_type='Beyond.Gameplay.AI.EntityAttractData';lang='Beyond.LangKey'
    records={name:[m.row()for m in next(w for w in build.wrappers.values()if w.wrapped_type==name).members]for name in(tag_type,ai_type,env_type,entity_type,lang)}
    if [[r['name'],r['declaredType']]for r in records[lang]]!=[['key','string']]:raise ValueError('npcRuntime.nominal-key-wire')
    profile=dict(tagType=tag_type,aiType=ai_type,aiDictionaryType=types['overrideAIBehaviorDataDictionary'],inlineInt32Types=[tag_type,'Beyond.Audio.AudioId'],nullableRecords=[entity_type,env_type],nullOnlyTypes=sorted(expected),groups={m.declaring_wrapper:'levelEntityData'if i<14 else'levelNpcData'if i<93 else'npcRuntimeProxyData'for i,m in enumerate(root.members)},collections={})
    for name in('envTalkIds','envTalkOdd','idleBreakTags','preloadMontages','exDatas','npcGamePlayDataKeyList'):
        wire=dict(wire='pool')if name=='envTalkIds'else dict(wire='i32')if name=='envTalkOdd'else dict(wire='record',type=tag_type)if name in('idleBreakTags','preloadMontages')else dict(wire='unproved')
        profile['collections'][types[name]]=dict(countLimit=5 if name in('envTalkIds','envTalkOdd')else 2 if name in('idleBreakTags','preloadMontages')else-1,element=wire)
    profile['collections']['System.Collections.Generic.List`1<ulong>']=dict(countLimit=53,element=dict(wire='u64'))
    declared=dict(fact['profile'],nullOnlyTypes=sorted(fact['profile']['nullOnlyTypes']))
    if profile!=declared:raise ValueError('npcRuntime.reviewed-bounded-profile')
    result=layout([m.row()for m in root.members],records,profile);result['containerKinds']=kinds
    return result,proof
