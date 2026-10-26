"""Authenticate only reviewed closed List<T> Params with null constants."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import null_list_param as proof,pooled_source_helper,utf8_source_helper
SCHEMA='endfield.levelscript-null-list-param-native.v2'
LABEL='levelscriptNullListParamNative'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_null_list_param_native.json'
CODECS={'Param<List<Vector3>>':'System.Collections.Generic.List`1<UnityEngine.Vector3>','Param<List<EntityPtr>>':'System.Collections.Generic.List`1<Beyond.Gameplay.Core.EntityPtr>'}

def _contract(path):
 fact=json.loads(Path(path).read_bytes());rows=fact['components']
 if (set(fact)!={'schema','status','nativeInputs','components','evidenceBoundary'} or (fact['schema'],fact['status'])!=(SCHEMA,'exact-current-build') or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'} or not rows
     or any(set(r)!={'codecKind','valueType','profile','proof'} or not r['codecKind'].startswith('Param<List<') or not r['codecKind'].endswith('>>') or not r['valueType'].startswith('System.Collections.Generic.List`1<') or not r['valueType'].endswith('>') or CODECS.get(r['codecKind'])!=r['valueType'] for r in rows)
     or len({r['codecKind'] for r in rows})!=len(rows) or len({r['valueType'] for r in rows})!=len(rows)):raise ValueError(LABEL+'.contract:shape')
 return fact

def _validate_native(image,fact,rows):
 for row in rows:
  actual=proof.derive(image,fact['nativeInputs'],row['profile'],row['valueType'])
  validate_claims(fact['evidenceBoundary'],actual['evidenceBoundary'],label=LABEL+'.boundary');validate_claims(actual['evidenceBoundary'],fact['evidenceBoundary'],label=LABEL+'.boundaryDeclaration')
  validate_claims(row['proof'],actual,label=LABEL+'.proof:'+row['codecKind']);validate_claims(actual,row['proof'],label=LABEL+'.declaration:'+row['codecKind'])

def validate_null_list_param_native_contract(*,codec_kind=None,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
 try:
  path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs'];rows=[r for r in fact['components'] if codec_kind is None or codec_kind==r['codecKind']]
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
  return dict(status='validated',codecKinds=[r['codecKind'] for r in rows],memberCount=4,rawSize=8,pathEncoding='int32-pool-index',collectionCount=-1,nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
 except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('contract','game-root','gameassembly','metadata'):parser.add_argument('--'+name,type=Path,default=DEFAULT_CONTRACT if name=='contract' else None)
 parser.add_argument('--codec-kind');args=parser.parse_args();result=validate_null_list_param_native_contract(codec_kind=args.codec_kind,contract_path=args.contract,game_root=args.game_root,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='validated' else 2)
