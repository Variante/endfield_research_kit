"""Gate the current pooled LangKey Param without claiming source ownership."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.memorypack import pooled_source_helper,pooled_nominal_key_sources
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_nominal_key_param_native.json'
SCHEMA='endfield.levelscript-nominal-key-param-native.v1'
LABEL='levelscriptNominalKeyParamNative'

def _validate_native(image,fact):pooled_nominal_key_sources.validate_components(image,fact)

def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  expected=dict(parentMemberCount=4,keyMemberCount=1,keyName='key',stringEncoding='int32-pool-index',managedKeyBytes=16,serializedPositiveKeyBytes=5,nonserializedRawText=True,wholeOwnerAdmitted=False)
  if(fact['schema'],fact['status'],fact['codecKinds'],fact['layout'])!=(SCHEMA,'exact-current-build',['Param<LangKey>'],expected)or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError(LABEL+'.contract:schema-or-layout')
  if(gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  dependencies=[CONTRACTS_DIR/name for name in('memorypack_reader_clones_native.json','memorypack_pooled_string_reader_native.json')];dependency_bytes=[p.read_bytes()for p in dependencies]
  _validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes()or dependency_bytes!=[p.read_bytes()for p in dependencies]:raise ValueError(LABEL+'.contract:changed-during-validation')
  return dict(status='validated',layout=fact['layout'],nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=CONTRACT_PATH if name=='contract'else None)
 args=parser.parse_args();result=validate(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated'else 2)
