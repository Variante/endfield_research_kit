"""Gate the closed managed8 CameraShakeConfigPtr Param and pooled key/path.

The proof owns both generated wrappers, original value ABI, selected typed
reader/provider/adapter/conversion paths, allocation, null routes and formatter
registration. Current operations bind an explicit installed root and the exact
StringPool object through exit bookends. Live formatter selection and camera
execution remain conditional; no historical owner receipt is admitted here.

Evidence and admission boundary:

Conditional current CameraShakeConfigPtr proves its managed eight-byte one-
key value, actual return/adapter/conversion, owned nested value/string store
and final receiver program. This supersedes the earlier owned-slot/final-
receiver refusal; marshal-size sentinels and matching widths alone remain
insufficient. Selected native/pool exit checks and outer owner/effect gates
are separate.
"""
import json,struct
from contextlib import contextmanager
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.memorypack import camera_shake_param as proof,pooled_source_helper

SCHEMA='endfield.levelscript-camera-shake-param-native.v1'
LABEL='levelscriptCameraShakeParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_camera_shake_param_native.json'
CAPABILITIES=dict(codecKind='Param<CameraShakeConfigPtr>',memberCount=4,constantMemberCount=1,managedValueBytes=8,keyEncoding='int32-pool-index',pathEncoding='int32-pool-index',wholeNullAdmitted=True,constantNullAdmitted=True,positiveConstantAdmitted=True)


def _contract(path):
 fact=json.loads(Path(path).read_bytes())
 if set(fact)!={'schema','status','nativeInputs','profile','proof','evidenceBoundary'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:
  raise ValueError(LABEL+'.contract:shape')
 return fact


def _validate_native(image,fact):
 actual=proof.derive(image,fact['nativeInputs'],fact['profile'])
 for key,observed in (('proof',actual),('evidenceBoundary',actual['evidenceBoundary'])):
  validate_claims(fact[key],observed,label=LABEL+'.'+key)
  validate_claims(observed,fact[key],label=LABEL+'.declaration:'+key)


def validate_camera_shake_param_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  sources=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both-paths-required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  pool=pooled_source_helper.CONTRACT_PATH.read_bytes();_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or pool!=pooled_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:changed-during-validation')
  current=snapshot_complete_reader_inputs()
  if sources!=current:raise ValueError(LABEL+'.source:reader-input-drift:'+str(reader_input_changes(sources,current)))
  return dict(status='validated',**CAPABILITIES,nativeInputs=pins,nativeSources={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),'global-metadata.dat':str(Path(gate.metadata).resolve())},evidenceBoundary=fact['evidenceBoundary'])
 except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError,struct.error) as error:
  return native_validation_failure(error,label=LABEL,source_path=contract_path)


class CameraShakeOperationError(ValueError):pass


class _CurrentCameraShakeParams:
 def __init__(self,audit,root,strings):self.proof=audit;self.root=root;self.strings=strings;self.active=True
 def audit(self,game_root,strings):
  if not self.active or game_root is None or Path(game_root).resolve()!=self.root or strings is not self.strings:
   raise CameraShakeOperationError(LABEL+'.operation:closed-or-wrong-root-or-pool')
  return json.loads(json.dumps(self.proof))


def prepared_camera_shake_audit(operation,*,game_root,strings):
 if not isinstance(operation,_CurrentCameraShakeParams):raise CameraShakeOperationError(LABEL+'.operation:invalid-capability')
 return operation.audit(game_root,strings)


@contextmanager
def current_camera_shake_params(*,game_root,strings):
 if game_root is None or strings is None or not hasattr(strings,'root'):raise CameraShakeOperationError(LABEL+'.operation:explicit-root-and-export-pool-required')
 root=Path(game_root).resolve();sources=snapshot_complete_reader_inputs();pool_root=Path(strings.root).parent
 pool=snapshot_string_pool_inputs(pool_root)
 audit=validate_camera_shake_param_native_contract(game_root=root)
 if audit.get('status')!='validated' or any(audit.get(key)!=value for key,value in CAPABILITIES.items()):
  raise CameraShakeOperationError(LABEL+'.operation:enter:'+str(audit)[:1400])
 selected=audit['nativeSources']
 if Path(selected['GameAssembly.dll']).resolve()!=root.parent/'GameAssembly.dll' or Path(selected['global-metadata.dat']).resolve()!=root/'il2cpp_data/Metadata/global-metadata.dat':raise CameraShakeOperationError(LABEL+'.operation:selected-pair-differs')
 operation=_CurrentCameraShakeParams(audit,root,strings)
 try:yield operation
 finally:
  operation.active=False
  after=validate_camera_shake_param_native_contract(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
  if audit!=after:raise CameraShakeOperationError(LABEL+'.operation:exit-proof-drift:'+str(after)[:1400])
  current=snapshot_complete_reader_inputs()
  if sources!=current:raise CameraShakeOperationError(LABEL+'.operation:reader-source-drift:'+str(reader_input_changes(sources,current)))
  if pool!=snapshot_string_pool_inputs(pool_root):raise CameraShakeOperationError(LABEL+'.operation:string-pool-drift')


if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
 args=parser.parse_args();result=validate_camera_shake_param_native_contract(contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
