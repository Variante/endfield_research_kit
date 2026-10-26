"""Authenticate the current bounded generated Param<List<LangKey>> source.

Evidence and admission boundary:

Conditional bounded LangKey list proof admits null, empty and single-element
only, with prior-empty Clear, requested capacity, exact managed16 Add/store,
provider callback/conversion and nominal child. Each child serializes
header/key; nonserialized rawText is omitted. Counts above one, positive
old-size Clear/growth, live inflated/cache/default contexts, text resolution
and execution remain unproved.
"""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack import lang_key_list_sources as source,pooled_source_helper
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_lang_key_list_param_native.json'
LABEL='levelscriptLangKeyListParamNative'
KIND='Param<List<LangKey>>'


def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
 try:
  sources=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs']
  if set(fact)!={'schema','status','codecKind','nativeInputs','collectionCounts','profile','proof','evidenceBoundary'} or (fact['schema'],fact['status'],fact['codecKind'])!=('endfield.levelscript-lang-key-list-param-native.v1','exact-current-build',KIND) or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or fact['collectionCounts']!=[-1,0,1] or any(type(n)is not int for n in fact['collectionCounts']):raise ValueError(LABEL+'.contract:shape')
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root) if game_root is not None else None;gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  actual=source.derive(open_native_image(gate.gameassembly,gate.metadata),pins,fact['profile'])
  for name in ('proof','evidenceBoundary'):
   value=actual if name=='proof'else actual[name];validate_claims(fact[name],value,label=LABEL+'.'+name);validate_claims(value,fact[name],label=LABEL+'.declaration:'+name)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  after_sources=snapshot_complete_reader_inputs()
  if sources!=after_sources:raise ValueError(LABEL+'.source:reader-input-drift:'+str(reader_input_changes(sources,after_sources)))
  return dict(status='validated',codecKind=KIND,memberCount=4,collectionCounts=[-1,0,1],elementRuntimeBytes=16,elementEncoding='MC1/int32-pool-index-or-default',pathEncoding='int32-pool-index',nativeInputs=pins,evidenceBoundary=actual['evidenceBoundary'])
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in('game-root','contract','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=CONTRACT_PATH if name=='contract'else None)
 a=parser.parse_args();result=validate(game_root=a.game_root,contract_path=a.contract,gameassembly=a.gameassembly,metadata=a.metadata);print(json.dumps(result,indent=2));raise SystemExit(result['status']!='validated')
