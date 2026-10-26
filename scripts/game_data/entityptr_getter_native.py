"""Current compiled constant getter source; live selection remains conditional."""
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.compiled_pointer_getter_native import validate
SCHEMA='endfield.entity-ptr-getter-native.v3'
NATIVE_MAPPING_ID='entityptr-getter-semantics.v3'
DEFAULT_CONTRACT=CONTRACTS_DIR/'entityptr_getter.json'

def load_entityptr_getter_contract(contract_path=DEFAULT_CONTRACT,*,gameassembly=None,metadata=None,game_root=None,**proof_paths):
 if game_root is not None and gameassembly is None and metadata is None:
  root=Path(game_root);gameassembly=root.parent/'GameAssembly.dll';metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
 rows,audit=validate(contract_path,schema=SCHEMA,gameassembly=gameassembly,metadata=metadata,**proof_paths)
 audit['nativeMappingId']=NATIVE_MAPPING_ID
 return rows,audit

if __name__=='__main__':
 import argparse,json
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT);parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);args=parser.parse_args()
 rows,audit=load_entityptr_getter_contract(args.contract,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(audit,indent=2));raise SystemExit(audit['status']!='validated')
