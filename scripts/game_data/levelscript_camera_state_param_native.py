"""Authenticate the generated camera-state Param with only a null nested reference."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import camera_state_param as proof,pooled_source_helper
SCHEMA='endfield.levelscript-camera-state-param-native.v1'
LABEL='levelscriptCameraStateParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_camera_state_param_native.json'

def _contract(path):
 fact=json.loads(Path(path).read_bytes())
 if (set(fact)!={'schema','status','nativeInputs','profile','proof','evidenceBoundary'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):raise ValueError(LABEL+'.contract:shape')
 return fact


def _validate_native(image,fact):
 actual=proof.derive(image,fact['nativeInputs'],fact['profile'])
 for key in ('proof','evidenceBoundary'):
  expected=fact[key];observed=actual if key=='proof' else actual['evidenceBoundary']
  validate_claims(expected,observed,label=LABEL+'.'+key);validate_claims(observed,expected,label=LABEL+'.declaration:'+key)
 return actual['nullState']['wireBytes']


def validate_camera_state_param_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  strings=pooled_source_helper.CONTRACT_PATH.read_bytes();constant_bytes=_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or strings!=pooled_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
  return dict(status='validated',codecKind='Param<CameraControlState>',memberCount=4,rawSize=8,pathEncoding='int32-pool-index',constantNullMarker=255,constantWireBytes=constant_bytes,positiveConstantAdmitted=False,nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
 args=parser.parse_args();result=validate_camera_state_param_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
