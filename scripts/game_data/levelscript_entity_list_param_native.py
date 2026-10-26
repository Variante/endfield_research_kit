"""Authenticate the closed positive EntityPtr-list Param component."""
import json
from contextlib import contextmanager
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.memorypack import entity_list_sources as source,pooled_source_helper

SCHEMA='endfield.levelscript-entity-ptr-list-param-native.v1'
LABEL='levelscriptEntityListParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_entity_ptr_list_param_native.json'
CAPABILITIES=dict(codecKind='Param<List<EntityPtr>>',memberCount=4,rawSize=8,
 pathEncoding='int32-pool-index',collectionCountEncoding='int32',constantNullCount=-1,
 maxConstantCount=10000,wholeNullAdmitted=True,positiveConstantsAdmitted=True,
 elementType='Beyond.Gameplay.Core.EntityPtr',elementMemberCount=3,elementNullMarker=255,
 elementFields=['uint64','uint32','bool-byte'],managedElementBytes=40)


def _contract(path):
 fact=json.loads(Path(path).read_bytes())
 if (set(fact)!={'schema','status','nativeInputs','proof','evidenceBoundary'}
     or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build')
     or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):
  raise ValueError(LABEL+'.contract:shape')
 return fact


def derive_on_image(image,pins):
 """Return a candidate without opening an additional image or publishing."""
 proof=source.derive(image,pins)
 return dict(schema=SCHEMA,status='exact-current-build',nativeInputs=dict(pins),
             proof=proof,evidenceBoundary=proof['evidenceBoundary'])


def validate_on_image(image,fact):
 actual=derive_on_image(image,fact['nativeInputs'])
 validate_claims(fact,actual,label=LABEL+'.proof')
 validate_claims(actual,fact,label=LABEL+'.declaration')


def _gate(pins,*,game_root=None,gameassembly=None,metadata=None):
 if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
 root=Path(game_root)if game_root is not None else None
 return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
  gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,
  metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)


def validate_entity_list_param_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  snapshot=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
  gate=_gate(pins,game_root=game_root,gameassembly=gameassembly,metadata=metadata)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  if failed:=pooled_source_helper.check_unity_input(gate.gameassembly,pins):return failed
  image=open_native_image(gate.gameassembly,gate.metadata)
  if (Path(image.gameassembly).resolve(),Path(image.metadata_path).resolve())!=(Path(gate.gameassembly).resolve(),Path(gate.metadata).resolve()):
   raise ValueError(LABEL+'.native:selected-image-differs')
  validate_on_image(image,fact)
  after=_gate(pins,gameassembly=image.gameassembly,metadata=image.metadata_path)
  if after.status!='validated':return dict(status=after.status,detail='Native input bookend: '+after.detail)
  if failed:=pooled_source_helper.check_unity_input(image.gameassembly,pins):return failed
  if raw!=path.read_bytes():raise ValueError(LABEL+'.contract:declaration-changed')
  current=snapshot_complete_reader_inputs()
  if snapshot!=current:raise ValueError(LABEL+'.source:reader-input-drift:'+str(reader_input_changes(snapshot,current)))
  return dict(status='validated',**CAPABILITIES,nativeInputs=pins,nativeSources={
   'GameAssembly.dll':str(Path(image.gameassembly).resolve()),'global-metadata.dat':str(Path(image.metadata_path).resolve())},
   evidenceBoundary=fact['evidenceBoundary'])
 except(ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError)as error:
  return native_validation_failure(error,label=LABEL,source_path=contract_path)


class EntityListOperationError(ValueError):pass


class _CurrentEntityLists:
 def __init__(self,audit,root,strings):self.proof=audit;self.root=root;self.strings=strings;self.active=True
 def audit(self,root,strings):
  if not self.active or root is None or Path(root).resolve()!=self.root or strings is not self.strings:
   raise EntityListOperationError(LABEL+'.operation:closed-or-wrong-root-or-pool')
  return json.loads(json.dumps(self.proof))


def prepared_entity_list_audit(operation,*,game_root,strings):
 if not isinstance(operation,_CurrentEntityLists):raise EntityListOperationError(LABEL+'.operation:invalid-capability')
 return operation.audit(game_root,strings)


@contextmanager
def current_entity_list_params(*,game_root,strings):
 if game_root is None or strings is None or not hasattr(strings,'root'):
  raise EntityListOperationError(LABEL+'.operation:explicit-root-and-export-pool-required')
 root=Path(game_root).resolve();sources=snapshot_complete_reader_inputs();pool_root=Path(strings.root).parent
 pool=snapshot_string_pool_inputs(pool_root);audit=validate_entity_list_param_native_contract(game_root=root)
 if audit.get('status')!='validated'or any(audit.get(k)!=v for k,v in CAPABILITIES.items()):
  raise EntityListOperationError(LABEL+'.operation:enter:'+str(audit)[:1400])
 selected=audit['nativeSources']
 if Path(selected['GameAssembly.dll']).resolve()!=root.parent/'GameAssembly.dll'or Path(selected['global-metadata.dat']).resolve()!=root/'il2cpp_data/Metadata/global-metadata.dat':
  raise EntityListOperationError(LABEL+'.operation:selected-pair-differs')
 operation=_CurrentEntityLists(audit,root,strings)
 try:yield operation
 finally:
  operation.active=False
  after=validate_entity_list_param_native_contract(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
  if audit!=after:raise EntityListOperationError(LABEL+'.operation:exit-proof-drift:'+str(after)[:1400])
  current=snapshot_complete_reader_inputs()
  if sources!=current:raise EntityListOperationError(LABEL+'.operation:reader-source-drift:'+str(reader_input_changes(sources,current)))
  if pool!=snapshot_string_pool_inputs(pool_root):raise EntityListOperationError(LABEL+'.operation:string-pool-drift')


if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract'else None)
 a=parser.parse_args();result=validate_entity_list_param_native_contract(contract_path=a.contract,game_root=a.game_root,gameassembly=a.gameassembly,metadata=a.metadata)
 print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated'else 2)
