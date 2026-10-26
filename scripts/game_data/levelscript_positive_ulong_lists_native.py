"""Fresh selected Param<List<ulong>> source; UInt64 never borrows STRING."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import levelscript_positive_ulong_list_sources as source,pooled_source_helper


def validate(*,game_root=None,gameassembly=None,metadata=None):
 path=CONTRACTS_DIR/'levelscript_null_list_param_native.json'
 try:
  if game_root is None and (gameassembly is None or metadata is None):raise ValueError('positiveUlongList.explicit-native-selection-required')
  if(gameassembly is None)!=(metadata is None):raise ValueError('positiveUlongList.both-native-paths')
  before=snapshot_complete_reader_inputs();raw=path.read_bytes();pins=json.loads(raw)['nativeInputs']
  root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
   gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll',
   metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat')
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  source.derive(open_native_image(gate.gameassembly,gate.metadata),pins)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='native-exit: '+after.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  if path.read_bytes()!=raw:raise ValueError('positiveUlongList.contract-drift')
  changed=snapshot_complete_reader_inputs()
  if before!=changed:raise ValueError('positiveUlongList.source-drift:'+str(reader_input_changes(before,changed)))
  return dict(status='validated',codecKind=source.KIND,memberCount=4,countLimit=source.LIMIT,wireCountBytes=4,
   elementWireBytes=8,elementEncoding='raw-uint64',initiallyNullListProved=True,
   pathEncoding='int32-pool-index',positiveCountsAdmitted=True,nativeInputs=pins)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:
  return native_validation_failure(error,label='positiveUlongList',source_path=path)
