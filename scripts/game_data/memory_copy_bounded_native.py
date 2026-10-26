"""Fresh bounded copy component; every caller retains its own typed/source gate."""
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,native_validation_failure
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
from scripts.game_data.il2cpp.bounded_copy_sources import prove_bounded_copy
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA='endfield.memory-copy-bounded-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'memory_copy_bounded_native.json'


def validate(*,game_root=None,contract_path=CONTRACT_PATH):
 try:contract,_=read_reviewed_contract(contract_path,schema=SCHEMA,status='reviewed-current-component',label='boundedCopy')
 except (OSError,ValueError) as error:return native_validation_failure(error,label='boundedCopy',source_path=Path(contract_path))
 pins=contract['nativeInputs'];root=Path(game_root) if game_root is not None else None
 def gate():return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=root.parent/'GameAssembly.dll' if root else None,metadata=root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
 selected=gate()
 if selected.status!='validated':return dict(status=selected.status,detail=selected.detail,nativeInputs=pins)
 failed=check_unity_input(selected.gameassembly,pins)
 if failed:return dict(failed,nativeInputs=pins)
 try:
  proof=validate_components(open_native_image(selected.gameassembly,selected.metadata),contract)
 except (ValueError,KeyError,IndexError,TypeError) as error:return native_validation_failure(error,label='boundedCopy',source_path=Path(contract_path))
 final=gate()
 if final.status!='validated':return dict(status=final.status,detail=final.detail,nativeInputs=pins)
 failed=check_unity_input(final.gameassembly,pins)
 if failed:return dict(failed,nativeInputs=pins)
 return dict(status='validated',nativeInputs=pins,entryRva=contract['entryRva'],maxBytes=256,proof=proof,evidenceBoundary=contract['evidenceBoundary'])


def validate_components(image,contract):
 if contract.get('schema')!=SCHEMA or contract.get('status')!='reviewed-current-component':raise ValueError('boundedCopy.component-schema')
 if contract.get('maxBytes')!=256:raise ValueError('boundedCopy.supported-count-bound')
 base=image.pe.image_base
 actual=[p['runtimeTriple'][:2]for p in image.unwind_index.family(contract['entryRva'])['ranges']]
 if actual!=[[w['startRva'],w['endRva']]for w in contract['ownedWindows']]:raise ValueError('boundedCopy.owned-window-membership')
 regions=[];rows=[];tables={}
 for window in contract['ownedWindows']:
  a,z=window['startRva'],window['endRva'];raw=image.pe.bytes_at_va(base+a,z-a)
  if hashlib.sha256(raw).hexdigest().upper()!=window['sha256']:raise ValueError('boundedCopy.owned-window-bytes')
  decoded=decode_memory_move_instructions(image.mapper,raw,base+a)
  if b''.join(bytes.fromhex(r['bytes'])for r in decoded)!=raw:raise ValueError('boundedCopy.complete-byte-partition')
  regions.append((base+a,raw));rows+=decoded
 for table in contract['tables']:
  a,z=table['startRva'],table['endRva'];raw=image.pe.bytes_at_va(base+a,z-a)
  if a in tables or raw.hex()!=table['raw'] or hashlib.sha256(raw).hexdigest().upper()!=table['sha256']:raise ValueError('boundedCopy.current-dispatch-table')
  tables[a]=raw
 proof=prove_bounded_copy(regions,base+contract['entryRva'],rows=rows,tables=tables,image_base=base)
 return proof
