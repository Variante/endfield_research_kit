"""Fresh current mask-component gate; no whole AnimationConfig admission."""
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,native_validation_failure
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.memorypack.animation_mask_sources import validate_components

CONTRACT_PATH=CONTRACTS_DIR/'animation_masks_native.json'
SCHEMA='endfield.animation-masks-native.v1'


def validate(*,game_root=None):
 try:
  fact,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='conditional-current-build',label='animationMasks');pins=fact['nativeInputs'];root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=root.parent/'GameAssembly.dll'if root else None,metadata=root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  failed=check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  proof=validate_components(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='selected native inputs changed during mask validation')
  return check_unity_input(gate.gameassembly,pins)or dict(status='validated',nativeInputs=pins,supportedCounts=fact['supportedCounts'],proof=proof,evidenceBoundary=fact['evidenceBoundary'])
 except(ValueError,KeyError,IndexError,TypeError,OSError)as error:return native_validation_failure(error,label='animationMasks',source_path=CONTRACT_PATH)
