"""Authenticate separately proved current raw8 ID storage; live method selection stays conditional."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import primitive_param,pooled_source_helper
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_pod_id_param_native.json'
LABEL='levelscriptPodIdParamNative'
VALUE_TYPES={f'Param<{name}>':f'Beyond.Gameplay.Core.{name}' for name in ('LsmPtr','SpawnerPtr','FunctionAreaPtr')}

def validate(codec_kind,*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  sources=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if set(fact)!={'schema','status','nativeInputs','components'} or (fact['schema'],fact['status'])!=('endfield.levelscript-pod-id-param-native.v2','exact-current-build') or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract:shape')
  rows=fact['components']
  if not isinstance(rows,list) or len(rows)!=len(VALUE_TYPES) or any(not isinstance(row,dict) or set(row)!={'codecKind','valueType','proof'} for row in rows):raise ValueError(LABEL+'.components:shape')
  if {row['codecKind']:row['valueType'] for row in rows}!=VALUE_TYPES:raise ValueError(LABEL+'.components:types')
  if codec_kind not in VALUE_TYPES:raise ValueError(LABEL+'.codecKind:unsupported')
  component,=[row for row in rows if row['codecKind']==codec_kind]
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  dependency=pooled_source_helper.CONTRACT_PATH.read_bytes()
  actual=primitive_param.derive_parameter(open_native_image(gate.gameassembly,gate.metadata),pins,'ulong',value_type=component['valueType'],unmanaged_qword=True)
  validate_claims(component['proof'],actual,label=LABEL+'.proof');validate_claims(actual,component['proof'],label=LABEL+'.declaration')
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or dependency!=pooled_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  after_sources=snapshot_complete_reader_inputs()
  if sources!=after_sources:raise ValueError(LABEL+'.source:reader-input-drift:'+str(reader_input_changes(sources,after_sources)))
  return dict(status='validated',codecKind=codec_kind,memberCount=4,rawSize=8,pathEncoding='int32-pool-index',nativeInputs=pins,evidenceBoundary=actual['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--codec-kind',required=True,choices=VALUE_TYPES);parser.add_argument('--game-root',type=Path);parser.add_argument('--contract',type=Path,default=CONTRACT_PATH);parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path);args=parser.parse_args()
 result=validate(args.codec_kind,game_root=args.game_root,contract_path=args.contract,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(result['status']!='validated')
