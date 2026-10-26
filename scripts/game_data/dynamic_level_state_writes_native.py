"""Conditional direct GameLevel State stores; following calls and lifecycle unresolved."""
from __future__ import annotations
import argparse,hashlib,json,struct,sys
from pathlib import Path
if __name__=='__main__' and not __package__:
 raise SystemExit('Run with python -m scripts.game_data.dynamic_level_state_writes_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_level_state_writes_native_claims.json'
SCHEMA='endfield.dynamic-level-state-writes-native-claims.v1'

from scripts.game_data.dynamic_level_predicate_value_sources_native import _methods,_field

def check_prefix(parts,programs,spec,patch,started,field_offset):
 require(len(parts)==len(programs),'state-writer-owned-roster',len(parts));allrows=[]
 for rows,program in zip(parts,programs):
  _grammar(rows,program);cursor=0;begin=_va(rows[0])
  for row in rows:
   require(row['offset']==cursor and _va(row)==begin+cursor and not row['text'].startswith(('db','unknown','ff/')),'state-writer-complete-partition',row)
   cursor+=len(_raw(row));allrows.append(row)
 require(len({_va(r) for r in allrows})==len(allrows),'state-writer-disjoint-ranges',None)
 rows=parts[0];by={r['offset']:r for r in rows};w=spec['witnesses'];stop=w['store'];prefix=[r for r in rows if r['offset']<=stop]
 require(_raw(by[0])==bytes.fromhex('4053') and _raw(by[2])==bytes.fromhex('4883EC')+bytes((spec['stackBytes'],)) and spec['stackBytes']>=32 and spec['stackBytes']%16==0,'state-writer-frame',None)
 require(_raw(by[w['saveReceiver']])==bytes.fromhex('488BD9'),'state-writer-original-receiver',None)
 _preserved_interval(prefix,0,w['saveReceiver'],'rcx',set(),'state-writer-incoming')
 require(_raw(by[w['initEdge']])[:1]==b'\x75' and branch_target(by[w['initEdge']])==_va(by[w['postInit']]),'state-writer-init-edge',None)
 require(_raw(by[w['postInit']])==bytes.fromhex('33D2') and _raw(by[w['patchArgument']])==b'\xb9'+spec['patchArgumentBits'].to_bytes(4,'little'),'state-writer-patch-arguments',None)
 call=by[w['patchCall']];require(len(_raw(call))==5 and _raw(call)[0]==0xe8 and branch_target(call)==patch,'state-writer-actual-patch',None)
 require(_raw(by[w['patchTest']])==bytes.fromhex('84C0') and _raw(by[w['patchEdge']])[:2]==bytes.fromhex('0F85'),'state-writer-false-patch-selection',None)
 bits=spec['storedInt32Bits'];require(type(bits) is int and 0<=bits<2**32 and 0<=field_offset<128,'state-writer-store-range',(bits,field_offset))
 require(_raw(by[stop])==bytes.fromhex('C743')+bytes((field_offset,))+bits.to_bytes(4,'little'),'state-writer-actual-32bit-store',None)
 choices={_va(by[w['patchEdge']]):False}
 if 'stateGuard' in spec:
  guard=spec['stateGuard'];cmp=by[guard['compare']];edge=by[guard['edge']]
  require(_raw(cmp)==bytes.fromhex('837B')+bytes((field_offset,guard['observedInt32Bits'])) and _raw(edge)[:2]==bytes.fromhex('0F85'),'state-writer-observed-lane-guard',None)
  require(_va(cmp)+len(_raw(cmp))==_va(edge) and _va(edge)+len(_raw(edge))==_va(by[stop]),'state-writer-guard-immediate-store',None);choices[_va(edge)]=False
 if 'getterGuard' in spec:
  guard=spec['getterGuard'];call=by[guard['call']];receiver=by[guard['receiver']]
  require(_raw(by[guard['hiddenArgumentClear']])==bytes.fromhex('33D2') and _raw(receiver)==bytes.fromhex('488BCB') and _va(receiver)+len(_raw(receiver))==_va(call),'state-writer-same-getter-receiver',None)
  require(len(_raw(call))==5 and _raw(call)[0]==0xe8 and branch_target(call)==started and _raw(by[guard['test']])==bytes.fromhex('84C0') and _raw(by[guard['edge']])[:1]==b'\x75','state-writer-actual-getter-zero',None)
  _preserved_interval(prefix,guard['hiddenArgumentClear']+len(_raw(by[guard['hiddenArgumentClear']])),guard['call'],'rdx',set(),'state-writer-hidden');choices[_va(by[guard['edge']])]=False
 byva={_va(r):r for r in prefix};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<100,'state-writer-owned-prefix-CFG',va);path=path+[va];row=byva[va]
  if va==_va(by[stop]):paths.append(path);return
  if row['text'].startswith(('jne ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(row),path)
   walk(va+len(_raw(row)),path)
  else:
   require(not row['text'].startswith(('j','ret','int3')),'state-writer-unexpected-transfer',row)
   walk(va+len(_raw(row)),path)
 walk(_va(rows[0]),[]);require(len(paths)==2,'state-writer-two-init-paths-to-store',len(paths))
 for path in paths:
  interval=[byva[v] for v in path[path.index(_va(by[w['saveReceiver']]))+1:-1]];_register_preserved(interval,{'rbx'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedPathsToStore':2,'storedInt32Bits':bits,'storedInt32Value':int.from_bytes(bits.to_bytes(4,'little'),'little',signed=True),'stateOffset':field_offset,'prefixStartRva':rows[0]['offset'],'prefixInstructions':len(prefix),'followingRequestsOrNormalReturnProved':False,'atomicTransitionOrLifecycleOrderProved':False}


def validate(image,contract,level,provider):
 specs=dict(contract['methods']);specs['started']=level['methods']['started'];specs['patch']=provider['methods']['patch'];methods=_methods(image,specs)
 definitions={methods[role][0].declaring_type for role in (*contract['methods'],'started')};require(len(definitions)==1,'state-writer-same-concrete-receiver',definitions);definition=next(iter(definitions))
 require(image.metadata.type_full_name(image.metadata.types[definition])==level['fields']['state']['owner'],'state-writer-field-owner',definition)
 field=_field(image,definition,level['fields']['state']);declaration=declared_members(image,field['targetDefinition'],level['fields']['state']['type'],field_defaults(image.metadata))
 proof={};windows={}
 for role in contract['methods']:
  try:
   parts,windows[role]=_parts(image,methods[role][1],contract['ownedByteCounts'][role]);result=check_prefix(parts,contract['programs'][role],contract['selectedWrites'][role],methods['patch'][1],methods['started'][1],field['offset'])
   aliases=[r for r in declaration['members'] if r['id']==result['storedInt32Value']];require(bool(aliases),'state-writer-declared-value-alias',result['storedInt32Value']);result['declarationAliases']=aliases;result['prefixStartRva']=_va(parts[0][0])-image.pe.image_base;result['prefixEndRva']=_va(next(r for r in parts[0] if r['offset']==contract['selectedWrites'][role]['witnesses']['store']))+7-image.pe.image_base;proof[role]=result
  except (ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
   raise ValueError('levelStateWrites.'+role+':'+str(exc)[:1200]) from exc
 return {'writes':proof,'field':field,'stateDeclarations':declaration,'windows':windows,'methods':{r:{'index':m.index,'rva':p-image.pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},'followingRequestsOrNormalReturnProved':False,'runtimeLifecycleOrObjectIdentityProved':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='level_state_writes')
    level,provider=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='level_state_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,level,provider)
    return {'format':'endfield.dynamic-level-state-writes-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_level_state_writes_native_latest.json')
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
        print('level-state-writes:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Level State prefix stores passed; following requests/normal return/lifecycle unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
