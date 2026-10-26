"""Fresh managed16 LangKey list induction over the retained nominal source."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import lang_key_list_sources as source,pooled_source_helper

KIND='Param<List<LangKey>>'
LIMIT=4096


def validate(*,game_root=None,gameassembly=None,metadata=None):
 path=CONTRACTS_DIR/'levelscript_lang_key_list_param_native.json'
 try:
  if game_root is None and (gameassembly is None or metadata is None):raise ValueError('positiveLangKeyList.explicit-native-selection-required')
  before=snapshot_complete_reader_inputs();raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if(fact['schema'],fact['status'],fact['codecKind'],fact['collectionCounts'])!=('endfield.levelscript-lang-key-list-param-native.v1','exact-current-build',KIND,[-1,0,1]):raise ValueError('positiveLangKeyList.contract')
  if(gameassembly is None)!=(metadata is None):raise ValueError('positiveLangKeyList.both-native-paths')
  root=Path(game_root)if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
   gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,
   metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  image=open_native_image(gate.gameassembly,gate.metadata);actual=source.derive(image,pins,fact['profile'])
  for name in('proof','evidenceBoundary'):
   value=actual if name=='proof'else actual[name]
   validate_claims(fact[name],value,label='positiveLangKeyList.'+name)
   validate_claims(value,fact[name],label='positiveLangKeyList.declaration.'+name)
  source.derive_bounded(image,pins,fact['profile'],actual,count_limit=LIMIT)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='native-exit: '+after.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  if path.read_bytes()!=raw:raise ValueError('positiveLangKeyList.contract-drift')
  changed=snapshot_complete_reader_inputs()
  if before!=changed:raise ValueError('positiveLangKeyList.source-drift:'+str(reader_input_changes(before,changed)))
  return dict(status='validated',codecKind=KIND,memberCount=4,countLimit=LIMIT,
   wireCountBytes=4,elementRuntimeBytes=16,elementEncoding='MC1/int32-pool-index-or-default',
   pathEncoding='int32-pool-index',positiveCountsAdmitted=True,nativeInputs=pins)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:
  return native_validation_failure(error,label='positiveLangKeyList',source_path=path)
