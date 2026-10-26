"""Fresh current authored NPC Patrol source gate; no Audio request claim."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import patrol_sources,pooled_source_helper

CONTRACT_PATH=CONTRACTS_DIR/'leveldata_npc_patrol_native.json'
SCHEMA='endfield.leveldata-npc-patrol-native.v1'


def _layout(image,proof):
 records={};types={r['original']:r['wrapper']for r in proof['children']['children']}
 def fields(name,rows):
  result=[]
  for row in rows:
   field,kind,mode=row['name'],row['type'],row.get('mode')
   if kind=='string':wire='pool'
   elif kind=='bool':wire='bool'
   elif mode=='single'or kind=='float':wire='f32'
   elif mode=='dword'or kind in('int','Beyond.Gameplay.Core.GameplayTag','Beyond.Audio.AudioId')or row.get('kind')=='enum':wire='i32'
   elif kind=='UnityEngine.Vector3':wire='vector3'
   elif kind=='Beyond.Gameplay.Core.PatrolSubActionData':wire='union'
   elif kind.startswith('System.Collections.Generic.List`1<'):
    element=kind.split('<',1)[1][:-1];wire='empty-list'if element=='Beyond.Blackboard+DataPair'else'list'
   else:raise ValueError('Patrol.layout:unsupported-type:'+name+'.'+field+':'+kind)
   result.append(dict(name=field,type=kind,wire=wire,**(dict(element=element)if wire in('list','empty-list')else{})))
  records[name]=result
 for record in proof['direct']:fields(record['type'],record['fields'])
 point=proof['point'];fields(point['type'],[dict(name=n,type=t,kind=k)for n,t,k in point['fields']])
 for original,wrapper in types.items():
  w=next(w for w in image.memorypack_wrappers.values()if w.name==wrapper);fields(original,[dict(name=m.name,type=m.declared_type,kind=m.kind)for m in w.members])
 union={str(r['tag']):next(name for name,wrapper in types.items()if wrapper==r['wrapperName'])for r in proof['children']['union']['entries']}
 return dict(root='Beyond.Gameplay.AI.Config.NpcPatrolData',records=records,union=union,countLimit=17,enums=[dict(parent=r['parent'],field=r['field'],values={str(v['id']):v['name']for v in r['members']})for r in proof['joins']['enums']])


def validate(*,game_root=None,gameassembly=None,metadata=None,contract_path=None):
 path=Path(contract_path or CONTRACT_PATH)
 try:
  sources=snapshot_complete_reader_inputs();raw=path.read_bytes();fact=json.loads(raw)
  if(fact.get('schema'),fact.get('status'),fact.get('referenceListCountLimit'),fact.get('blackboardCounts'),fact.get('unionTags'))!=(SCHEMA,'exact-current-build',17,[-1,0],[0,1]):raise ValueError('Patrol.contract:schema/profile differs')
  if(gameassembly is None)!=(metadata is None):raise ValueError('Patrol.explicit-native-pair:both paths required')
  pins=fact['nativeInputs'];root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(gameassembly)if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=Path(metadata)if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  ga,md=Path(gate.gameassembly).resolve(),Path(gate.metadata).resolve();failure=pooled_source_helper.check_unity_input(ga,pins)
  if failure:return failure
  image=open_native_image(ga,md);proof=patrol_sources.validate_on_image(image,fact);layout=_layout(image,proof)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=ga,metadata=md)
  if after.status!='validated':return dict(status=after.status,failedGate='installed_native_inputs_after',detail=after.detail)
  failure=pooled_source_helper.check_unity_input(ga,pins)
  if failure:return failure
  if raw!=path.read_bytes():raise ValueError('Patrol.contract-changed-during-validation')
  changed=snapshot_complete_reader_inputs()
  if sources!=changed:raise ValueError('Patrol.reader-source-drift:'+str(reader_input_changes(sources,changed)))
  return dict(status='validated',layout=layout,nativeInputs=pins,nativeSources={'GameAssembly.dll':str(ga),'global-metadata.dat':str(md)},evidenceBoundary=fact['evidenceBoundary'],eventRequestsProved=False)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,StopIteration)as error:return native_validation_failure(error,label='leveldataNpcPatrol',source_path=path)
