"""Authenticate exact current raw24 AirWall parameter source and typed composition."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.memorypack import airwall_ptr_param,airwall_source,pooled_source_helper,unmanaged_qword_source
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_airwall_ptr_param_native.json'
LABEL='levelscriptAirWallPtrParamNative'

def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 before=snapshot_complete_reader_inputs()
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if set(fact)!={'schema','status','nativeInputs','codecKind','profile','proof'}or(fact['schema'],fact['status'],fact['codecKind'])!=('endfield.levelscript-airwall-ptr-param-native.v1','conditional-current-build-wire','Param<AirWallPtr>')or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract-shape')
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.both-native-paths-required')
  root=Path(game_root)if game_root is not None else None;gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  paths=[Path(m.__file__)for m in(airwall_ptr_param,airwall_source,unmanaged_qword_source)]+[pooled_source_helper.CONTRACT_PATH];saved=[p.read_bytes()for p in paths];actual=airwall_ptr_param.derive(open_native_image(gate.gameassembly,gate.metadata),pins,fact['profile']);validate_claims(fact['proof'],actual,label=LABEL+'.proof');validate_claims(actual,fact['proof'],label=LABEL+'.declaration')
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes()or saved!=[p.read_bytes()for p in paths]or before!=snapshot_complete_reader_inputs():raise ValueError(LABEL+'.inputs-changed-during-validation')
  return dict(status='validated',codecKind='Param<AirWallPtr>',memberCount=4,rawSize=24,pathEncoding='int32-pool-index',nativeInputs=pins,evidenceBoundary=actual['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)
