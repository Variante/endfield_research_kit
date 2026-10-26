"""Authenticate reviewed closed List Params; named EntityPtr, UInt64 and string kinds admit count0."""
import json
from contextlib import contextmanager
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,snapshot_string_pool_inputs,reader_input_changes
from scripts.game_data.memorypack import null_list_param as proof,pooled_source_helper,utf8_source_helper
SCHEMA='endfield.levelscript-null-list-param-native.v5'
LABEL='levelscriptNullListParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_null_list_param_native.json'
CODECS={'Param<List<Vector3>>':'System.Collections.Generic.List`1<UnityEngine.Vector3>','Param<List<EntityPtr>>':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>','Param<List<ulong>>':'System.Collections.Generic.List`1<ulong>','Param<List<string>>':'System.Collections.Generic.List`1<string>'}
COUNTS={kind:[-1,0] if kind!='Param<List<Vector3>>' else [-1] for kind in CODECS}

def _contract(path):
 fact=json.loads(Path(path).read_bytes());rows=fact['components']
 if (set(fact)!={'schema','status','nativeInputs','components','evidenceBoundary'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or not rows
     or any(set(r)!={'codecKind','valueType','collectionCounts','profile','proof'} or not r['codecKind'].startswith('Param<List<') or not r['codecKind'].endswith('>>') or not r['valueType'].startswith('System.Collections.Generic.List`1<') or not r['valueType'].endswith('>') or CODECS.get(r['codecKind'])!=r['valueType'] or r['collectionCounts']!=COUNTS.get(r['codecKind']) or any(type(n)is not int for n in r['collectionCounts']) for r in rows)
     or len({r['codecKind'] for r in rows})!=len(rows) or len({r['valueType'] for r in rows})!=len(rows)):raise ValueError(LABEL+'.contract:shape')
 return fact

def _validate_native(image,fact,rows):
 for row in rows:
  actual=proof.derive(image,fact['nativeInputs'],row['profile'],row['valueType'],collection_counts=row['collectionCounts'])
  validate_claims(fact['evidenceBoundary'],actual['evidenceBoundary'],label=LABEL+'.boundary');validate_claims(actual['evidenceBoundary'],fact['evidenceBoundary'],label=LABEL+'.boundaryDeclaration')
  validate_claims(row['proof'],actual,label=LABEL+'.proof:'+row['codecKind']);validate_claims(actual,row['proof'],label=LABEL+'.declaration:'+row['codecKind'])

def validate_null_list_param_native_contract(*,codec_kind=None,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  sources=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs'];rows=[r for r in fact['components'] if codec_kind is None or codec_kind==r['codecKind']]
  if not rows:raise ValueError(LABEL+'.contract:unproved-codec='+str(codec_kind))
  if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
  root=Path(game_root) if game_root is not None else None
  gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
  if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  strings=pooled_source_helper.CONTRACT_PATH.read_bytes();headers=utf8_source_helper.CONTRACT_PATH.read_bytes();_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact,rows)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
  failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
  if failed:return failed
  if raw!=path.read_bytes() or strings!=pooled_source_helper.CONTRACT_PATH.read_bytes() or headers!=utf8_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
  after_sources=snapshot_complete_reader_inputs()
  if sources!=after_sources:raise ValueError(LABEL+'.source:reader-input-drift:'+str(reader_input_changes(sources,after_sources)))
  return dict(status='validated',codecKinds=[r['codecKind'] for r in rows],memberCount=4,rawSize=8,pathEncoding='int32-pool-index',collectionCounts={r['codecKind']:r['collectionCounts'] for r in rows},nativeInputs=pins,nativeSources={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),'global-metadata.dat':str(Path(gate.metadata).resolve())},evidenceBoundary=fact['evidenceBoundary'])
 except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

class NullListOperationError(ValueError):
 def __init__(self,detail):
  self.diagnostic=dict(validator=LABEL,gate='current-operation',expected='fresh active selected-root/pool operation with unchanged exit proof',actual=detail[:1400])
  super().__init__(detail)


class _CurrentNullListParams:
 def __init__(self,proof,game_root,strings):
  self._proof=proof;self.game_root=Path(game_root).resolve();self.strings=strings;self.active=True
 def audit(self,kind,game_root,strings):
  if not self.active:raise NullListOperationError(LABEL+'.operation:closed')
  if game_root is None or Path(game_root).resolve()!=self.game_root or strings is not self.strings:raise NullListOperationError(LABEL+'.operation:wrong-root-or-pool')
  if kind is not None and kind not in self._proof['codecKinds']:raise NullListOperationError(LABEL+'.operation:unproved-codec='+str(kind))
  result=json.loads(json.dumps(self._proof))
  if kind is None:return result
  result['codecKinds']=[kind];result['collectionCounts']={kind:result['collectionCounts'][kind]};return result


def prepared_null_list_audit(operation,*,codec_kind,game_root,strings):
 if not isinstance(operation,_CurrentNullListParams):raise NullListOperationError(LABEL+'.operation:invalid-capability')
 return operation.audit(codec_kind,game_root,strings)


@contextmanager
def current_null_list_params(*,game_root,strings):
 """One explicit selected-root/pool operation; no proof survives its exit."""
 if game_root is None:raise NullListOperationError(LABEL+'.operation:explicit-game-root-required')
 root=Path(game_root).resolve();sources=snapshot_complete_reader_inputs()
 pool_root=Path(strings.root).parent if strings is not None else None
 pool=snapshot_string_pool_inputs(pool_root)if pool_root is not None else None
 proof=validate_null_list_param_native_contract(game_root=root)
 expected=dict(status='validated',codecKinds=list(CODECS),memberCount=4,rawSize=8,pathEncoding='int32-pool-index',collectionCounts=COUNTS)
 if any(proof.get(k)!=v for k,v in expected.items()):raise NullListOperationError(LABEL+'.operation:enter:'+str(proof)[:1400])
 selected=proof['nativeSources']
 if Path(selected['GameAssembly.dll']).resolve()!=root.parent/'GameAssembly.dll' or Path(selected['global-metadata.dat']).resolve()!=root/'il2cpp_data/Metadata/global-metadata.dat':raise NullListOperationError(LABEL+'.operation:selected-pair-differs')
 operation=_CurrentNullListParams(proof,root,strings)
 try:yield operation
 finally:
  operation.active=False
  after=validate_null_list_param_native_contract(gameassembly=Path(selected['GameAssembly.dll']),metadata=Path(selected['global-metadata.dat']))
  if proof!=after:raise NullListOperationError(LABEL+'.operation:exit-proof-drift:'+str(after)[:1400])
  current=snapshot_complete_reader_inputs()
  if sources!=current:raise NullListOperationError(LABEL+'.operation:reader-source-drift:'+str(reader_input_changes(sources,current)))
  if pool_root is not None and pool!=snapshot_string_pool_inputs(pool_root):raise NullListOperationError(LABEL+'.operation:string-pool-drift')


if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
 parser.add_argument('--codec-kind');args=parser.parse_args();result=validate_null_list_param_native_contract(codec_kind=args.codec_kind,contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
