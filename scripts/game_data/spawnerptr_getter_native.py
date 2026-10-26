"""Current compiled constant getter source; live selection remains conditional."""
from pathlib import Path
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.compiled_pointer_getter_native import validate
SCHEMA='endfield.spawner-ptr-getter-native.v3'
NATIVE_MAPPING_ID='spawnerptr-getter.v3'
DEFAULT_CONTRACT=CONTRACTS_DIR/'spawnerptr_getter.json'

def load_spawnerptr_getter_contract(contract_path=DEFAULT_CONTRACT,*,gameassembly=None,metadata=None,game_root=None,**proof_paths):
 if game_root is not None and gameassembly is None and metadata is None:
  root=Path(game_root);gameassembly=root.parent/'GameAssembly.dll';metadata=root/'il2cpp_data/Metadata/global-metadata.dat'
 rows,audit=validate(contract_path,schema=SCHEMA,gameassembly=gameassembly,metadata=metadata,**proof_paths)
 audit['nativeMappingId']=NATIVE_MAPPING_ID
 return next(iter(rows.values()),{}),audit

def project_spawnerptr_getter(record,getter):
 node=record.get('typedNode')or{}
 if record.get('family')!='GetterBase'or(node.get('unionTag'),node.get('memberCount'))!=(getter.get('unionTag'),getter.get('serializedMemberCount')):return{}
 param=(node.get('fields')or{}).get(getter.get('wireField'))
 if not isinstance(param,dict):return{}
 value=param.get('value');identity=value.get('id')if isinstance(value,dict)else None
 return dict(spawnerId=identity,idRef=param.get('idRef'),paramSource=param.get('paramSource'),path=param.get('path'),bindingKind='constant'if param.get('paramSource')==0 and type(identity)is int and identity>0 else'runtime_unresolved',nativeMappingId=NATIVE_MAPPING_ID,payloadShape='current-typed-spawnerptr-getter',evidenceBoundary=getter.get('evidenceBoundary'))

if __name__=='__main__':
 import argparse,json
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,default=DEFAULT_CONTRACT);parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True);args=parser.parse_args()
 rows,audit=load_spawnerptr_getter_contract(args.contract,gameassembly=args.gameassembly,metadata=args.metadata);print(json.dumps(audit,indent=2));raise SystemExit(audit['status']!='validated')
