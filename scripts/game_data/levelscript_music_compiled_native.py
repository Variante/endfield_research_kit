"""Current named music call shape; evaluated values and Event posting remain unproved."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,native_validation_failure
from scripts.game_data.il2cpp.body_claims import BodyIndex,evaluate
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_music_compiled_claims.json'
SCHEMA='endfield.levelscript-music-compiled-call-claims.v1'
LABEL='levelscriptMusicCompiledCalls'

def audit_music_compiled_calls(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
 try:
  path=Path(contract_path);raw=path.read_bytes();contract,digest=read_reviewed_contract(path,schema=SCHEMA,label=LABEL,status='reviewed');methods=contract['methods']
  if(contract.get('evidenceBoundary')!='direct'or contract.get('admission')!='named-call-shape-only'or not isinstance(methods,dict)or not methods or any(not isinstance(row,dict)or not isinstance(row.get('type'),str)or not isinstance(row.get('method'),str)or not isinstance(row.get('claims'),list)or not row['claims']for row in methods.values())):raise ValueError(LABEL+'.contract:nonempty-named-method-claims-required')
  if gameassembly is None or metadata is None:return dict(status='missing',eventRequestsProved=False,methods=[],failedGate='explicit-native-pair',detail='Both selected native paths are required')
  gate=check_installed_native_inputs(gameassembly=gameassembly,metadata=metadata)
  if gate.status!='validated':return dict(status=gate.status,eventRequestsProved=False,methods=[],failedGate='installed-native-inputs',detail=gate.detail)
  pins={'GameAssembly.dll':gate.gameassembly_sha256.upper(),'global-metadata.dat':gate.metadata_sha256.upper()};unity=Path(gate.gameassembly).parent/'UnityPlayer.dll';pins['UnityPlayer.dll']=sha256_file_upper(unity);before=snapshot_complete_reader_inputs();rows,failures=evaluate(BodyIndex(open_native_image(gate.gameassembly,gate.metadata)),methods)
  after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
  if after.status!='validated':return dict(status=after.status,eventRequestsProved=False,methods=[],failedGate='native-bookend',detail=after.detail)
  if pins['UnityPlayer.dll']!=sha256_file_upper(unity)or before!=snapshot_complete_reader_inputs()or path.read_bytes()!=raw:raise ValueError(LABEL+'.source-native-Unity-contract-bookend-drift')
  status='validated'if not failures and len(rows)==len(methods)else'pendingReview'
  return dict(status=status,eventRequestsProved=False,evidenceBoundary='direct',admission='named-call-shape-only',nativeInputs=pins,readerInputs=before,contractSha256=digest,methods=rows,failures=failures,unresolved=contract.get('unresolved',[]))
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return dict(eventRequestsProved=False,methods=[],**native_validation_failure(error,label=LABEL,source_path=contract_path))
