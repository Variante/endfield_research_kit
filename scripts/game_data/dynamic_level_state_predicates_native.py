"""Selected GameLevel State getters and conditional writer declaration comparisons."""
from __future__ import annotations
import argparse,hashlib,json,struct,sys
from pathlib import Path
if __name__=='__main__' and not __package__:
 raise SystemExit('Run with python -m scripts.game_data.dynamic_level_state_predicates_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs,NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets,field_defaults
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.dynamic_mission_string_providers_native import require,_raw,_va,branch_target,_register_preserved,_grammar,_abi,_type_record,select_ordinary_overload
from scripts.game_data.dynamic_erosion_consumers_native import _preserved_interval
from scripts.game_data.dynamic_mission_state_cache_native import _class,_enum
from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.dynamic_quest_action_requests_native import _parts
from scripts.game_data.memorypack.corpus_gate import _fingerprint,_parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_level_state_predicates_native_claims.json'
SCHEMA='endfield.dynamic-level-state-predicates-native-claims.v1'

from scripts.game_data.dynamic_level_predicate_value_sources_native import _methods,_field

def _partition(parts,programs,sizes):
 require(len(parts)==len(programs)==len(sizes),'getter-owned-roster',None);allrows=[]
 for rows,program,size in zip(parts,programs,sizes):
  _grammar(rows,program);cursor=0;begin=_va(rows[0])
  for r in rows:
   require(r['offset']==cursor and _va(r)==begin+cursor and not r['text'].startswith(('db','unknown','ff/')),'getter-continuous-boundary',r);cursor+=len(_raw(r));allrows.append(r)
  require(cursor==size,'getter-owned-size',cursor)
 require(len({_va(r) for r in allrows})==len(allrows),'getter-disjoint-parts',None)
 return {r['offset']:r for r in parts[0]},allrows

def check_loaded(parts,programs,spec,patch,field):
 p,allrows=_partition(parts,programs,(42,43));threshold=spec['thresholdBits'];argument=spec['patchArgumentBits']
 fixed={0:'4053',2:'4883EC20',6:'488BD9',9:'33D2',11:'B9'+argument.to_bytes(4,'little').hex(),21:'84C0',29:'837B'+bytes((field,threshold)).hex(),33:'0F9DC0',36:'4883C420',40:'5B',41:'C3'}
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'loaded-raw-prefix-return',at)
 require(len(_raw(p[16]))==5 and _raw(p[16])[0]==0xe8 and branch_target(p[16])==patch,'loaded-actual-patch',None)
 require(_raw(p[23])[:2]==bytes.fromhex('0F85') and branch_target(p[23])==_va(parts[1][0]),'loaded-patch-edge-owned-start',None)
 _preserved_interval(parts[0],0,6,'rcx',set(),'loaded-incoming')
 _register_preserved([r for r in parts[0] if 6<r['offset']<40],{'rbx'},{_va(p[16])})
 return {'selectedNormalPaths':1,'actualStateLaneOffset':field,'signedThresholdBits':threshold,'normalizedBooleanLowByte':True,'fullRaxNormalized':False,'selection':'Actual qualified patch call AL=0'}

def check_ready(parts,programs,spec,field):
 p,allrows=_partition(parts,programs,(101,100));byva={_va(r):r for r in allrows}
 fixed={0:'4053',2:'4883EC20',6:'488BD9',16:'83B9E000000000',25:'488B81B8000000',32:'488B00',35:'4885C0',40:'817818'+spec['guardComparisonBits'].to_bytes(4,'little').hex(),53:'837B'+bytes((field,spec['thresholdBits'])).hex(),57:'0F9DC0',60:'4883C420',64:'5B',65:'C3'}
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'ready-raw-guard-compare-frame',at)
 for at in (9,71):require(len(_raw(p[at]))==7 and _raw(p[at])[:3]==bytes.fromhex('488B0D'),'ready-context-load',at)
 require(_va(p[9])+7+struct.unpack_from('<i',_raw(p[9]),3)[0]==_va(p[71])+7+struct.unpack_from('<i',_raw(p[71]),3)[0],'ready-same-context-slot-not-runtime-record',None)
 require(len(_raw(p[66]))==5 and _raw(p[66])[0]==0xe8,'ready-opaque-normal-call',None)
 for at,op,dest in ((23,0x74,_va(p[66])),(38,0x74,_va(p[95])),(78,0xeb,_va(p[25]))):require(_raw(p[at])[0]==op and branch_target(p[at])==dest,'ready-owned-edge',at)
 require(_raw(p[47])[:2]==bytes.fromhex('0F8F') and branch_target(p[47])==_va(parts[1][0]),'ready-selected-guard-edge',None)
 choices={_va(p[a]):False for a in (38,47)};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<50,'ready-selected-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  require(r['text']!='int3','ready-exception-excluded',None)
  if r['text'].startswith('jmp '):walk(branch_target(r),path)
  elif r['text'].startswith(('je ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(_va(p[0]),[]);require(len(paths)==2,'ready-two-init-paths',len(paths))
 _preserved_interval(parts[0],0,6,'rcx',set(),'ready-incoming')
 for path in paths:
  interval=[byva[v] for v in path[path.index(_va(p[6]))+1:path.index(_va(p[64]))]];_register_preserved(interval,{'rbx'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedNormalPaths':2,'actualStateLaneOffset':field,'signedThresholdBits':spec['thresholdBits'],'normalizedBooleanLowByte':True,'fullRaxNormalized':False,'selection':'Anonymous context/header/cache guards select stored lane; normal opaque callees preserve frame and receiver storage'}

def declaration_comparisons(writers,predicates):
 rows=[]
 for name,spec in writers['selectedWrites'].items():
  bits=spec['storedInt32Bits'];require(type(bits) is int and 0<=bits<2**32,'writer-declaration-bits',bits);value=int.from_bytes(bits.to_bytes(4,'little'),'little',signed=True)
  rows.append({'writer':name,'storedInt32Value':value,'getterLowByteIfSelected':{k:int(value>=p['thresholdBits']) for k,p in predicates.items()}})
 return {'status':'conditional declaration association; writer bodies not reauthenticated by this receipt','conditions':['Writer independently authenticated for same native and proof sources','Same concrete receiver and unchanged State storage between store and getter comparison','Getter selected normal-return path and normal callee/frame noninterference'],'rows':rows,'runtimeLifecycleProved':False}

def validate(image,contract,level,provider,writers):
 specs=dict(contract['methods']);specs['patch']=provider['methods']['patch'];methods=_methods(image,specs)
 owner=methods['isLoaded'][0].declaring_type;require(methods['isReady'][0].declaring_type==owner,'predicate-same-concrete-owner',None)
 require(image.metadata.type_full_name(image.metadata.types[owner])==level['fields']['state']['owner'],'predicate-state-owner',None)
 field=_field(image,owner,level['fields']['state']);declarations=declared_members(image,field['targetDefinition'],level['fields']['state']['type'],field_defaults(image.metadata));proof={};windows={}
 writer_methods=_methods(image,writers['methods']);require(all(m.declaring_type==owner for m,p in writer_methods.values()),'writer-declaration-same-concrete-owner',None)
 for role in contract['methods']:
  parts,windows[role]=_parts(image,methods[role][1],contract['ownedByteCounts'][role]);s=contract['predicates'][role]
  require(type(s['thresholdBits']) is int and 0<=s['thresholdBits']<128 and 0<=field['offset']<128,'predicate-small-signed-literal',None)
  require(any(r['id']==s['thresholdBits'] for r in declarations['members']),'predicate-declared-threshold',s['thresholdBits'])
  proof[role]=check_loaded(parts,contract['programs'][role],s,methods['patch'][1],field['offset']) if role=='isLoaded' else check_ready(parts,contract['programs'][role],s,field['offset'])
 return {'getters':proof,'field':field,'stateDeclarations':declarations,'windows':windows,'methods':{r:{'index':m.index,'rva':p-image.pe.image_base,'ownerDefinition':m.declaring_type} for r,(m,p) in methods.items()},'writerDeclarationComparisons':declaration_comparisons(writers,contract['predicates']),'runtimeLifecycleOrReadyProved':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='level_state_writes')
    level,provider,writers=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='level_state_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,level,provider,writers)
    return {'format':'endfield.dynamic-level-state-predicates-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_level_state_predicates_native_latest.json')
    args=parser.parse_args(argv)
    try:
        json_sources=json_proof_snapshots(CONTRACT)
        sources=_parser_source_snapshots(Path(__file__))+json_sources+[_fingerprint(p) for p in (NATIVE_MAPPER_PATH,METADATA_HELPER_PATH)]
        inputs=[_fingerprint(p) for p in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs];groups._guard_publication(args.output_json,protected)
        result=validate_native_claims(args.gameassembly,args.metadata,inputs)
        result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        require_json_proof_unchanged(CONTRACT,json_sources)
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print('level-state-predicates:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Level State selected normal getters passed; live/lifecycle and writer reauthentication unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
