"""Read an explicit exported AIConfig -> brain -> blackboard mode/RID chain.

Stored selection is conditional on the supplied configuration. This reader
does not select a live entity's AIConfig, instantiate a graph or schedule it.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path

from scripts.repo_paths import REPO_ROOT
from scripts.game_data.unity_store import UnityObjectStore
from scripts.game_data.extraction.verify_export_freshness import build_report, Requirements, DEFAULT_SUMMARY

SCHEMA='endfield.skill-ai-mode-sources.v1'


def need(check,condition):
    if not condition:raise ValueError('skillAIModeSources.'+check)


def _freshness(root,game_root):
    need('installed-root-present',Path(game_root).is_dir())
    report=build_report(game_root=Path(game_root).resolve(),output_root=root,summary_path=DEFAULT_SUMMARY,
        sources=None,requirements=Requirements(unity=('MonoBehaviour','MonoScript'),asset_map=True))
    need('export-freshness',report.get('fresh')is True)
    return report


def _snapshot(root):
    store=root/'game/Unity.sqlite'
    paths=[store,Path(str(store)+'-wal'),Path(str(store)+'-journal'),root/'layout.json',root/'meta/extraction/provenance.json']
    paths+=sorted(path for layer in ('Persistent','StreamingAssets')for path in (root/'meta'/layer/'asset_map').glob('*.json'))
    result=[]
    for path in paths:
        if not path.is_file():continue
        stat=path.stat();item=dict(path=path.as_posix(),size=stat.st_size,mtimeNs=stat.st_mtime_ns,ctimeNs=stat.st_ctime_ns)
        if path!=store and path.suffix=='.json':
            digest=hashlib.sha256()
            with path.open('rb')as stream:
                for block in iter(lambda:stream.read(1<<20),b''):digest.update(block)
            item['sha256']=digest.hexdigest()
        result.append(item)
    need('store-and-map-inputs',store.is_file()and any('/asset_map/'in row['path']for row in result))
    return result


def _candidate_map_rows(path,wanted):
    """Parse only wanted PathID rows while scanning the complete flat map.

    The maintained exporter writes one property per line. Every candidate is
    JSON-decoded and compared by physical source, offset, PathID and type.
    Scanning to EOF prevents a later duplicate from being silently ignored.
    """
    lines=[];selected=False;inside=False;closed=False
    with path.open('rb')as stream:
        for line in stream:
            raw=line.strip()
            if not inside:
                inside=raw.startswith(b'"AssetEntries"');continue
            if raw==b'{':lines=[raw];selected=False;continue
            if raw in (b'}',b'},'):
                if selected:
                    row=json.loads(b'\n'.join(lines+[b'}']))
                    need('asset-map-row-shape',all(key in row for key in ('Source','Offset','PathID','Type')))
                    yield row
                lines=[];continue
            if raw.startswith(b']'):closed=True;break
            lines.append(raw)
            if raw.startswith(b'"PathID"'):
                value=json.loads(raw.partition(b':')[2].rstrip(b','))
                selected=type(value)is int and value in wanted
    need('asset-map-complete',inside and closed)


def _tag(value):
    result=value['tag']['tagId']
    need('signed-tag',type(result)is int and -(1<<31)<=result<1<<31)
    return result


def _dictionary(value,key):
    keys=value['_keyData'];values=value['_valueData']
    need('parallel-dictionary',type(keys)is list and type(values)is list and len(keys)==len(values))
    converted=[key(item)for item in keys]
    need('distinct-dictionary-keys',len(converted)==len(set(converted)))
    return dict(zip(converted,values))


def read_mode_sources(export_root,*,game_root,config_object,blackboard_object,mode,character_object=None,character_id=None):
    root=Path(export_root).resolve();need('mode-int32',type(mode)is int and -(1<<31)<=mode<1<<31)
    fresh=_freshness(root,game_root);before=_snapshot(root);store=UnityObjectStore.for_export(root)
    documents={};loaded={}
    def load(row):
        key=(row.type,row.name)
        raw=store.read_bytes(*key);need('stored-sha256',hashlib.sha256(raw).hexdigest()==row.sha256)
        value=json.loads(raw);h=value['$animestudio']
        need('stored-header',(h['type'],h['pathId'],h['sourceFile'])==(row.type,row.path_id,row.source_file))
        if key in loaded:need('repeat-object-stable',loaded[key][1]==raw)
        loaded[key]=(row,raw);documents[key]=value
        return value
    def named(name):
        rows=store.rows_by_object_name('MonoBehaviour',name);need('unique-explicit-object',len(rows)==1)
        return load(rows[0])
    def resolve(source,pointer,path,expected_type='MonoBehaviour'):
        fid,pid=pointer['m_FileID'],pointer['m_PathID']
        need('nonnull-pptr',type(fid)is int and type(pid)is int and pid!=0)
        cab=source['$animestudio']['sourceFile']
        if fid:
            refs=[row for row in source['$animestudio'].get('pptrReferences',[])if row.get('path')==path
                and row.get('fileId')==fid and row.get('pathId')==pid]
            need('external-pptr-header',len(refs)==1 and type(refs[0].get('expectedTargetSourceFile'))is str)
            cab=refs[0]['expectedTargetSourceFile']
        rows=[row for row in store.rows_by_path_id(pid,cab)if row.type==expected_type]
        need('unique-physical-pptr',len(rows)==1)
        return load(rows[0])
    def typed(value,name):
        script=resolve(value,value['m_Script'],'$.m_Script','MonoScript')
        need('monoscript-type',script['m_Namespace']+'.'+script['m_ClassName']==name)
    config=named(config_object);typed(config,'Beyond.Gameplay.AI.Config.CharacterAIConfigData')
    character=None;character_binding=None
    need('character-selection-pair',(character_object is None)==(character_id is None))
    if character_object is not None:
        character=named(character_object);refs=character['references']['RefIds'];by_rid={row['rid']:row for row in refs}
        need('character-unique-rids',len(by_rid)==len(refs))
        def exact_character_ref(pointer,namespace,class_name):
            rid=pointer['rid'];need('character-owned-rid',type(rid)is int and rid in by_rid)
            row=by_rid[rid];data=row['data']
            need('character-exact-rid-type',row['type']['ns']==namespace and row['type']['class']==class_name
                and data.get('$decoded')is True and data.get('exactTypeTreeDecoded')is True
                and data['offset']==row['dataOffset']and data['length']==row['dataLength'])
            return row
        template=exact_character_ref(character['data'],'Beyond.Gameplay','CharacterTemplateData')
        need('character-id',template['data']['id']==character_id and type(character_id)is str)
        components=template['data']['componentList'];ids=[item['rid']for item in components]
        need('character-distinct-components',len(ids)==len(set(ids)))
        candidates=[(index,row)for index,row in enumerate(refs)if row['rid']in ids
            and row['type'].get('ns')=='Beyond.Gameplay.AI'and row['type'].get('class')=='CharacterAIComponentData']
        need('one-owned-ai-component',len(candidates)==1)
        index,component=candidates[0];exact_character_ref({'rid':component['rid']},'Beyond.Gameplay.AI','CharacterAIComponentData')
        selected_config=resolve(character,component['data']['aiCfg'],f'$.references.RefIds[{index}].data.aiCfg')
        need('character-config-identity',selected_config['$animestudio']==config['$animestudio'])
        character_binding=dict(characterId=character_id,rootRid=template['rid'],aiComponentRid=component['rid'],componentIndex=ids.index(component['rid']))
    brain=resolve(config,config['brainConfig'],'$.brainConfig');typed(brain,'Beyond.Gameplay.AI.Config.CharacterAIBrainConfigData')
    bb=named(blackboard_object);typed(bb,'Beyond.Gameplay.AI.Config.CharacterAIBlackboard')
    need('root-blackboard-only',bb['parent']=={'m_FileID':0,'m_PathID':0})
    modes=_dictionary(brain['mode'],lambda value:value if type(value)is int else need('mode-key-int',False))
    need('selected-mode-present',mode in modes);mode_tag=_tag(modes[mode])
    mode_map=_dictionary(bb['mode'],_tag);need('mode-tag-present',mode_tag in mode_map)
    mode_index=[_tag(value)for value in bb['mode']['_keyData']].index(mode_tag)
    selected=resolve(bb,mode_map[mode_tag],f'$.mode._valueData[{mode_index}]')
    typed(selected,'Beyond.Gameplay.AI.Config.CharacterAIModeData')
    graphs=_dictionary(bb['graph'],_tag);graph_tag=_tag(selected['graph']);need('graph-tag-present',graph_tag in graphs)
    refs=bb['references']['RefIds'];by_rid={row['rid']:row for row in refs}
    need('unique-managed-rids',len(by_rid)==len(refs))
    def managed(pointer):
        rid=pointer['rid'];need('managed-reference-present',type(rid)is int and rid in by_rid)
        row=by_rid[rid];data=row['data']
        need('exact-managed-payload',data.get('$decoded')is True and data.get('exactTypeTreeDecoded')is True
            and '$undecoded'not in data and row['dataLength']==data['length']and row['dataOffset']==data['offset'])
        return copy.deepcopy(row)
    graph=managed(graphs[graph_tag]['graph']);behaviors=[];behavior_map=_dictionary(bb['behavior'],_tag)
    for key,value in _dictionary(selected['behavior'],_tag).items():
        payload=_tag(value);need('behavior-tag-present',payload in behavior_map)
        rows=behavior_map[payload]['dataList'];need('behavior-reference-list',type(rows)is list)
        behaviors.append(dict(behaviorTag=key,payloadTag=payload,data=[managed(row)for row in rows]))
    selected_docs=([character]if character is not None else[])+[config,brain,bb,selected]
    physical={}
    for value in selected_docs:
        h=value['$animestudio'];key=(h['sourceOriginalPath'].replace('\\','/').casefold(),h['sourceOffset'],h['pathId'])
        need('unique-physical-selected-documents',key not in physical);physical[key]=[]
    for item in before:
        if '/asset_map/'not in item['path']:continue
        for row in _candidate_map_rows(Path(item['path']),{key[2]for key in physical}):
            key=(str(row['Source']).replace('\\','/').casefold(),row['Offset'],row['PathID'])
            if row['Type']=='MonoBehaviour'and key in physical:
                need('nonempty-asset-path',type(row.get('Container'))is str and bool(row['Container']))
                physical[key].append(dict(assetMap=item['path'],entry=row))
    need('unique-asset-map-physical-bindings',all(len(rows)==1 for rows in physical.values()))
    identities=[]
    for value in selected_docs:
        h=value['$animestudio'];key=(h['sourceOriginalPath'].replace('\\','/').casefold(),h['sourceOffset'],h['pathId'])
        identities.append(dict(name=value['m_Name'],sourceFile=h['sourceFile'],pathId=h['pathId'],rawDataSha256=h['rawDataSha256'],assetMapBinding=physical[key][0]))
    for key,(row,raw)in loaded.items():
        need('object-bookend',raw==store.read_bytes(*key)and row in store.rows_by_path_id(row.path_id,row.source_file))
    need('input-bookend',before==_snapshot(root));_freshness(root,game_root)
    return dict(schema=SCHEMA,status='stored-configuration-chain',mode=mode,modeTag=mode_tag,
        aiBBPath=config['aiBBPath'],graphTag=graph_tag,graph=graph,behaviors=behaviors,
        registerSystem=selected['registerSystem'],objects=identities,inputSnapshot=before,exportFreshness=fresh,
        characterTemplateBinding=character_binding,characterConfigStoredBindingProved=character_binding is not None,
        activeEntityConfigSelected=False,configuredBlackboardAssetPathProved=False,runtimeSelectionProved=False,
        evidenceBoundary='Exact physical exported object/PPtr/tag/RID chain under the explicit configuration and root blackboard. aiBBPath loading, active entity configuration, runtime graph construction and scheduling require separate native joins.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-root',type=Path,required=True);parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--config-object',required=True);parser.add_argument('--blackboard-object',required=True)
    parser.add_argument('--character-object');parser.add_argument('--character-id')
    parser.add_argument('--mode',type=int,required=True)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_ai_mode_sources.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    try:result=read_mode_sources(args.export_root,game_root=args.game_root,config_object=args.config_object,blackboard_object=args.blackboard_object,mode=args.mode,character_object=args.character_object,character_id=args.character_id)
    except (ValueError,KeyError,TypeError,OSError)as error:print(json.dumps(dict(status='refused',detail=str(error))));return 2
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],mode=result['mode'],graphType=result['graph']['type'],behaviorCount=len(result['behaviors']))));return 0


if __name__=='__main__':raise SystemExit(main())
