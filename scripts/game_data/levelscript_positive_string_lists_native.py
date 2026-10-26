"""Fresh bounded literal/Param STRING-list gate; no whole owner admission."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import levelscript_positive_string_sources as source,pooled_source_helper


def validate(*,codec_kind,game_root=None,gameassembly=None,metadata=None):
 path=CONTRACTS_DIR/'levelscript_pooled_string_list_native.json'
 try:
  if game_root is None and (gameassembly is None or metadata is None):raise ValueError('positiveStringList.explicit-native-selection-required')
  before=snapshot_complete_reader_inputs();raw=path.read_bytes();pins=json.loads(raw)['nativeInputs']
  if(gameassembly is None)!=(metadata is None):raise ValueError('positiveStringList.both-native-paths')
  root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
   gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,
   metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  source.derive(open_native_image(gate.gameassembly,gate.metadata),pins,codec_kind=codec_kind)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='native-exit: '+after.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  if path.read_bytes()!=raw:raise ValueError('positiveStringList.contract-drift')
  changed=snapshot_complete_reader_inputs()
  if before!=changed:raise ValueError('positiveStringList.source-drift:'+str(reader_input_changes(before,changed)))
  return dict(status='validated',codecKind=codec_kind,countLimit=source.LIMIT,wireCountBytes=4,elementWireBytes=4,
   stringEncoding='int32-pool-index',positiveCountsAdmitted=True,nativeInputs=pins)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:
  return native_validation_failure(error,label='positiveStringList',source_path=path)
