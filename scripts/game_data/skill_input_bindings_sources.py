"""Read stored combat bindings and authored Lua input bridges without running the game."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.unity_store import UnityObjectStore
from scripts.game_data.extraction.verify_export_freshness import build_report,Requirements,DEFAULT_SUMMARY
from scripts.game_data.skill_input_bindings_native import load_skill_input_bindings
from scripts.common import check_installed_native_inputs

SCHEMA='endfield.skill-input-bindings-source-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_input_bindings_sources.json'


def need(check,condition):
    if not condition:raise ValueError('skillInputBindingsSources.'+check)


def project_defaults(document,enums):
    """Project actual stored key/timing codes; never infer active runtime choices."""
    keys={r['id']:r['name']for r in enums['Beyond.Input.KeyboardKeyCode']}
    timings={r['id']:r['name']for r in enums['Beyond.Input.InputTimingType']};rows=[];seen=set()
    pairs=document['actionInfos']['_pairs'];need('action-pairs',isinstance(pairs,list))
    for index,pair in enumerate(pairs):
        action=pair['key'];need('unique-action',isinstance(action,str)and action not in seen);seen.add(action)
        value=pair['value'];devices={}
        for source in('primaryKeyboardInput','secondaryKeyboardInput'):
            raw=value[source];key=raw['key'];timing=raw['timingType']
            need('typed-key-timing',type(key)is int and type(timing)is int and key in keys and timing in timings)
            for flag in('useCtrl','useShift','useAlt','blockOtherTiming','enableContinuousTrigger'):
                need('binary-input-flag',type(raw[flag])is int and raw[flag]in(0,1))
            devices[source]={'raw':dict(raw),'keyName':keys[key],'timingName':timings[timing]}
        rows.append({'actionId':action,'jsonPath':f'$.actionInfos._pairs[{index}].value','needSecond':value['needSecond'],
            'bindings':devices,'evidence':'conditional-stored-default','activeBindingProved':False})
    return rows


def lua_source_claim(raw,spec):
    text=raw.decode('utf-8-sig');need('unique-lua-start',text.count(spec['start'])==1)
    start=text.index(spec['start']);end=text.find(spec['end'],start+len(spec['start']));need('lua-end',end>start)
    segment=text[start:end];positions=[segment.find(token)for token in spec['tokens']]
    need('lua-token-claims',all(p>=0 for p in positions))
    return {'id':spec['id'],'path':spec['path'],'sha256':hashlib.sha256(raw).hexdigest(),'startLine':text[:start].count('\n')+1,
        'tokens':list(spec['tokens']),'evidence':'direct-exported-source-text','runtimeBindingProved':False}


def _snapshot(root):
    paths=[root/'game/Unity.sqlite',root/'meta/extraction/provenance.json',root/'layout.json']
    paths+=[Path(str(paths[0])+suffix)for suffix in('-wal','-journal')]
    return [(str(p),p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ctime_ns)for p in paths if p.is_file()]


def read_input_binding_sources(export_root,*,game_root,gameassembly,metadata,contract_path=CONTRACT_PATH):
    root=Path(export_root).resolve();path=Path(contract_path);report={'schema':'endfield.skill-input-bindings-sources.v1',
        'status':'blocked','bindings':[],'uiReferences':[],'luaClaims':[],'rules':{},'failures':[]}
    try:
        contract,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillInputBindingsSources')
        native=load_skill_input_bindings(gameassembly=Path(gameassembly),metadata=Path(metadata));report['nativeAudit']=native
        need('native-enum-entry-gate',native['status']=='validated')
        fresh=build_report(game_root=Path(game_root).resolve(),output_root=root,summary_path=DEFAULT_SUMMARY,
            sources=None,requirements=Requirements(structured=('lua',),unity=('MonoBehaviour',),asset_map=False))
        report['freshness']=fresh;need('export-provenance',fresh.get('provenance')=='per-output provenance' and not fresh.get('missingOutputs'));before=_snapshot(root)
        store=UnityObjectStore.for_export(root);loaded={};sources=[]
        def load(row):
            key=(row.type,row.name);raw=store.read_bytes(*key);doc=json.loads(raw);header=doc['$animestudio']
            need('stored-sha256',hashlib.sha256(raw).hexdigest()==row.sha256)
            need('stored-identity',(header['type'],header['pathId'],header['sourceFile'])==(row.type,row.path_id,row.source_file))
            loaded[key]=(row,raw);sources.append({'type':row.type,'name':row.name,'sourceFile':row.source_file,'pathId':row.path_id,'sha256':row.sha256})
            return doc
        documents={}
        for name in contract['namedObjects']:
            rows=store.rows_by_object_name('MonoBehaviour',name);need('unique-explicit-object',len(rows)==1);documents[name]=load(rows[0])
        config=documents['InputSettingConfig'];bindings=[]
        for name,doc in documents.items():
            if 'actionInfos'not in doc:continue
            header=doc['$animestudio'];matches=[i for i,p in enumerate(config['inputSettingList'])if p['m_PathID']==header['pathId']]
            need('unique-config-pptr',len(matches)==1);index=matches[0];pointer=config['inputSettingList'][index]
            refs=[r for r in config['$animestudio']['pptrReferences']if r['path']==f'$.inputSettingList[{index}]']
            need('config-pptr-physical-source',len(refs)==1 and refs[0]['fileId']==pointer['m_FileID']
                and refs[0]['pathId']==header['pathId']and refs[0].get('expectedTargetSourceFile')==header['sourceFile'])
            for row in project_defaults(doc,native['enums']):bindings.append(dict(row,object=name,sourceFile=header['sourceFile'],pathId=header['pathId']))
        selector=contract['uiReference'];rows=store.rows_by_path_id(selector['pathId'],selector['sourceFile']);need('explicit-ui-reference',len(rows)==1)
        refs=load(rows[0]);keys=refs['refDict']['_keys'];values=refs['refDict']['_values'];need('ui-ref-bijection',len(keys)==len(values)and len(set(keys))==len(keys))
        refmap=dict(zip(keys,values));ui=[]
        for field in contract['uiRefFields']:
            pointer=refmap[field];need('local-ui-pptr',pointer['m_FileID']==0 and type(pointer['m_PathID'])is int and pointer['m_PathID']!=0)
            rows=store.rows_by_path_id(pointer['m_PathID'],selector['sourceFile']);need('unique-ui-target',len(rows)==1);target=load(rows[0])
            events={name:{'useBindingAction':value['useBindingAction'],'playerActionId':value['playerActionId']}
                for name,value in target.items()if name in('onPressStart','onPressEnd','onLongPress','onClick')and isinstance(value,dict)}
            ui.append({'referenceField':field,'jsonPath':'$.refDict','sourceFile':selector['sourceFile'],'pathId':pointer['m_PathID'],
                'events':events,'widgetId':target.get('id'),'evidence':'direct-stored-local-pptr','activePanelProved':False})
        lua=[];lua_loaded=[]
        for spec in contract['luaClaims']:
            file=root/'game/Lua/Data/LuaScripts'/spec['path'];need('lua-path-root',file.resolve().is_relative_to(root/'game/Lua'))
            raw=file.read_bytes();lua_loaded.append((file,raw));lua.append(lua_source_claim(raw,spec))
        # A source-side rebinding API is evidence of configurability, not a user profile.
        rebind=documents['InputRebindConfig']['actionScopeConfigs']
        pins=native['nativeInputs'];after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly),metadata=Path(metadata))
        need('native-after',after.status=='validated');need('source-snapshot-after',before==_snapshot(root))
        for key,(row,raw)in loaded.items():need('object-bytes-after',store.read_bytes(*key)==raw and row in store.rows_by_path_id(row.path_id,row.source_file))
        for file,raw in lua_loaded:need('lua-bytes-after',file.read_bytes()==raw)
        need('contract-bytes-after',hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest)
        report.update(status='validated-conditional-sources' if fresh.get('fresh')is True else 'validated-stored-export',currentInstalledDataProved=fresh.get('fresh')is True,bindings=bindings,uiReferences=ui,luaClaims=lua,
            sources=sources,rebindScopes=rebind,nativeInputs=pins,rules={'storedDefaultsProved':True,'sourceTextBridgesProved':True,
                'activeUserRebindingProved':False,'activePanelOrScopeProved':False,'physicalInputDeliveryProved':False,
                'defaultJumpShiftMouse1MappingProved':False,'longPressUltimateAcceptanceProved':False,
                'heldRepeatSchedulingProved':False,'playerCommandAcceptanceProved':False},
            gaps=['common_jump/common_sprint actions are stored on selected buttons; their Space/Shift/Mouse1 default mapping is not closed here',
                'long-press handler timing and ultimate acceptance require their own native consumer proof',
                'HGInputActions/legacy Rewired assets are not automatically the active gameplay binding system',
                'selected UI reference cohort is explicit; active panel and prefab resource selection are not proved'])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error)as error:
        report.update(status='blocked',bindings=[],uiReferences=[],luaClaims=[],rules={})
        report['failures'].append({'validator':'skill_input_bindings_sources','check':str(error)[:1000],'source':str(path)})
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in('export-root','game-root','gameassembly','metadata','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    need('output-root',any(a.output.resolve().is_relative_to(REPO_ROOT/r)for r in('reports','scratch','tmp')))
    r=read_input_binding_sources(a.export_root,game_root=a.game_root,gameassembly=a.gameassembly,metadata=a.metadata)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'bindingCount':len(r['bindings']),'failures':r['failures']}));return 0 if r['status']in('validated-conditional-sources','validated-stored-export')else 1


if __name__=='__main__':raise SystemExit(main())
