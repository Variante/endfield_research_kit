"""Authenticate current compact WorldChallenge wire composition on every operation."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.memorypack import subgame_compact_sources as sources,subgame_compact_joins as joins,subgame_world_models,subgame_enclosing_models,pooled_source_helper

CONTRACT_PATH=CONTRACTS_DIR/'gameplay_subgame_compact_native.json'
LABEL='gameplaySubGameCompactNative'

def derive(image,fact):
 pins=fact['nativeInputs'];world=sources.derive_world(image,pins);enclosing=sources.derive_enclosing(image,pins,world);joined=joins.validate_joins(image,pins,fact['profile'],world,enclosing)
 return dict(world=world,enclosing=enclosing,joins=joined)

def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 before=snapshot_complete_reader_inputs()
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if set(fact)!={'schema','status','nativeInputs','profile','proof','evidenceBoundary'}or(fact['schema'],fact['status'])!=('endfield.gameplay-subgame-compact-native.v1','conditional-current-build-wire')or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract-shape')
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  root=Path(game_root)if game_root is not None else None;gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  paths=[Path(__file__)]+[Path(m.__file__)for m in(sources,joins,subgame_world_models,subgame_enclosing_models)]+[CONTRACTS_DIR/n for n in('memorypack_reader_clones_native.json','memorypack_pooled_string_reader_native.json','levelscript_nominal_key_param_native.json','levelscript_pooled_string_list_native.json')];saved=[p.read_bytes()for p in paths];actual=derive(open_native_image(gate.gameassembly,gate.metadata),fact);validate_claims(fact['proof'],actual,label=LABEL+'.proof');validate_claims(actual,fact['proof'],label=LABEL+'.declaration')
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes()or saved!=[p.read_bytes()for p in paths]or before!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.inputs-changed-during-validation')
  selected=actual['enclosing']['selected']['union']['dispatch'];wrapper=next(c['registrations'][0]['wrapperType']for c in fact['profile']['compositions']if c['registrations'][0]['originalType']=='Beyond.Gameplay.Core.WorldChallengeSubGameData');route,=[r for r in selected['entries']if r['wrapperName']==wrapper]
  return dict(status='validated',nativeInputs=pins,unionTag=route['tag'],fields=[{k:f[k]for k in('name','kind','type')}for f in actual['world']['fields']],evidenceBoundary=fact['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
