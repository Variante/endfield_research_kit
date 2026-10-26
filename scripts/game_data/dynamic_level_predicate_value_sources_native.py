"""Conditional level predicate/getter values; runtime lifecycle remains unresolved."""
from __future__ import annotations
import argparse,hashlib,json,struct,sys
from pathlib import Path
if __name__=='__main__' and not __package__:
 raise SystemExit('Run with python -m scripts.game_data.dynamic_level_predicate_value_sources_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs,NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets,field_defaults
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.dynamic_mission_string_providers_native import require,_raw,_va,branch_target,_register_preserved,_grammar,_abi,_type_record,select_ordinary_overload
from scripts.game_data.dynamic_mission_state_cache_native import _class,_enum
from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.dynamic_quest_action_requests_native import _parts
from scripts.game_data.memorypack.corpus_gate import _fingerprint,_parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_level_predicate_value_sources_native_claims.json'
SCHEMA='endfield.dynamic-level-predicate-value-sources-native-claims.v1'

def check_caller(parts,programs,methods,base):
 for rows,program in zip(parts,programs):_grammar(rows,program)
 require(len(parts)==2,'whole-owned-roster',None);allrows=[]
 for rows,size in zip(parts,(119,103)):
  cursor=0;start=_va(rows[0])
  for r in rows:
   require(r['offset']==cursor and _va(r)==start+cursor and not r['text'].startswith(('db','unknown','ff/')),'complete-recognized-partition',r);cursor+=len(_raw(r));allrows.append(r)
  require(cursor==size,'whole-owned-size',cursor)
 p={r['offset']:r for r in parts[0]};q={r['offset']:r for r in parts[1]};byva={_va(r):r for r in allrows};require(len(byva)==len(allrows),'disjoint-owned-range',None)
 fixed={0:'4053',2:'4883EC20',6:'488BD9',9:'33D2',11:'B9CC230000',21:'84C0',36:'488B90B8000000',43:'4883BAF001000000',53:'488B92F0010000',60:'4883BAC000000000',70:'488B8AC0000000',77:'33D2',84:'84C0',88:'32C0',90:'4883C420',94:'5B',95:'C3',96:'4885DB',101:'837B1000',111:'B001',113:'4883C420',117:'5B',118:'C3'}
 require(_raw(p[29])[:3]==bytes.fromhex('488B05') and _raw(q[0])[:3]==bytes.fromhex('488B05'),'ordinary-root-slot-load',None)
 require(_va(p[29])+7+struct.unpack_from('<i',_raw(p[29]),3)[0]==_va(q[0])+7+struct.unpack_from('<i',_raw(q[0]),3)[0],'same-on-disk-type-slot-not-same-runtime-object',None)
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'root-lanes-typed-reference-length-and-Boolean-frame',at)
 for at,b in {7:'488B88B8000000',14:'488B89F0010000',21:'4885C9',26:'33D2',33:'4533C0',36:'488BD3',39:'488BC8',47:'84C0'}.items():require(_raw(q[at])==bytes.fromhex(b),'typed-second-request-args',at)
 require(branch_target(p[79])==methods['started'][1] and branch_target(q[28])==methods['id'][1],'actual-typed-getter-calls',None)
 require(branch_target(p[16])==methods['patch'][1] and branch_target(q[42])==methods['equals'][1],'actual-ordinary-patch-Equals-calls',None)
 for at,op,target in [(23,'0F85',_va(q[60])),(51,'74',_va(p[88])),(68,'74',_va(p[88])),(86,'75',_va(p[96])),(99,'74',_va(p[111])),(105,'0F87',_va(q[0]))]:require(_raw(p[at]).startswith(bytes.fromhex(op)) and branch_target(p[at])==target,'owned-primary-edge',at)
 for at,op,target in [(24,'74',_va(q[97])),(49,'0F84',_va(p[88])),(55,'E9',_va(p[111]))]:require(_raw(q[at]).startswith(bytes.fromhex(op)) and branch_target(q[at])==target,'owned-secondary-edge',at)
 choices={_va(p[23]):False,_va(q[24]):False};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<100,'selected-normal-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  require(r['text']!='int3','exception-excluded',r)
  if r['text'].startswith('jmp '):walk(branch_target(r),path)
  elif r['text'].startswith(('je ','jne ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   if choices.get(va) is not True:walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(_va(p[0]),[]);require(len(paths)==7,'seven-normal-policy-paths',len(paths))
 for path in paths:
  restore=_va(p[94]) if _va(p[94]) in path else _va(p[117]);interval=[byva[v] for v in path[path.index(_va(p[6]))+1:path.index(restore)]];_register_preserved(interval,{'rbx'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedNormalPaths':7,'normalizedBooleanLowByte':True,'allRaxNormalized':False,'actualStartedGetterNonzeroRequiredForTrue':True,'StringNullOrZeroLengthLaneReturnsTrueAfterGetter':True,'nonzeroLengthRequiresActualEqualsLowByteNonzeroForTrue':True,'sameRepeatedWorldInfoOrGameLevelProved':False,'ClassHeaderStaticPointerBridgeOrLiveAvailabilityProved':False}

def check_started(parts,programs):
 for rows,program in zip(parts,programs):_grammar(rows,program)
 require(len(parts)==2,'whole-owned-roster',None);allrows=[]
 for rows,size in zip(parts,(101,100)):
  cursor=0;start=_va(rows[0])
  for r in rows:
   require(r['offset']==cursor and _va(r)==start+cursor and not r['text'].startswith(('db','unknown','ff/')),'complete-recognized-boundary',r);cursor+=len(_raw(r));allrows.append(r)
  require(cursor==size,'owned-size',cursor)
 p={r['offset']:r for r in parts[0]};byva={_va(r):r for r in allrows};require(len(byva)==len(allrows),'disjoint',None)
 fixed={0:'4053',2:'4883EC20',6:'488BD9',16:'83B9E000000000',25:'488B81B8000000',32:'488B00',35:'4885C0',40:'817818CD230000',53:'837B1002',57:'0F9DC0',60:'4883C420',64:'5B',65:'C3'}
 require(_raw(p[9])[:3]==bytes.fromhex('488B0D') and _raw(p[71])[:3]==bytes.fromhex('488B0D'),'ordinary-context-slot-loads',None)
 require(_va(p[9])+7+struct.unpack_from('<i',_raw(p[9]),3)[0]==_va(p[71])+7+struct.unpack_from('<i',_raw(p[71]),3)[0],'same-context-slot-not-runtime-object',None)
 require(_raw(p[66])[:1]==b'\xe8','opaque-normal-helper-direct-call',None)
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'raw-guard-enum-signed-compare-and-frame',at)
 expected={23:(0x74,_va(p[66])),38:(0x74,_va(p[95])),78:(0xeb,_va(p[25]))}
 for at,(op,dest) in expected.items():require(_raw(p[at])[0]==op and branch_target(p[at])==dest,'owned-edge',at)
 require(_raw(p[47])[:2]==bytes.fromhex('0F8F') and branch_target(p[47])==_va(parts[1][0]),'actual-epoch-guard-edge',None)
 choices={_va(p[a]):False for a in (38,47)};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<50,'selected-normal-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  require(r['text']!='int3','exception-excluded',r)
  if r['text'].startswith('jmp '):walk(branch_target(r),path)
  elif r['text'].startswith(('je ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   if choices.get(va) is not True:walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(_va(p[0]),[]);require(len(paths)==2,'two-init-selected-paths',len(paths))
 for path in paths:
  interval=[byva[v] for v in path[path.index(_va(p[6]))+1:path.index(_va(p[64]))]];_register_preserved(interval,{'rbx'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedNormalPaths':2,'actualStateLaneOffset':16,'signedThresholdBits':2,'normalizedBooleanLowByte':True,'fullRaxNormalized':False,'inlineGuardMeaningProved':False,'liveStartedOrTransitionOrderProved':False}

def check_id(parts,programs):
 for rows,program in zip(parts,programs):_grammar(rows,program)
 require(len(parts)==2,'owned-roster',None);allrows=[]
 for rows,size in zip(parts,(116,100)):
  cursor=0;start=_va(rows[0])
  for r in rows:
   require(r['offset']==cursor and _va(r)==start+cursor and not r['text'].startswith(('db','unknown','ff/')),'recognized-boundary',r);cursor+=len(_raw(r));allrows.append(r)
  require(cursor==size,'whole-size',cursor)
 p={r['offset']:r for r in parts[0]};byva={_va(r):r for r in allrows};require(len(byva)==len(allrows),'disjoint',None)
 fixed={0:'4053',2:'4883EC20',6:'488BD9',16:'83B9E000000000',25:'488B81B8000000',32:'488B10',35:'4885D2',40:'817A18BA060000',53:'488B83C0000000',60:'4885C0',65:'488B4018',69:'4883C420',73:'5B',74:'C3',75:'4883C420',79:'5B',80:'C3'}
 require(_raw(p[9])[:3]==bytes.fromhex('488B0D') and _raw(p[86])[:3]==bytes.fromhex('488B0D'),'ordinary-context-slot-loads',None)
 require(_va(p[9])+7+struct.unpack_from('<i',_raw(p[9]),3)[0]==_va(p[86])+7+struct.unpack_from('<i',_raw(p[86]),3)[0],'same-context-slot-not-runtime-object',None)
 require(_raw(p[81])[:1]==b'\xe8','opaque-normal-helper-direct-call',None)
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'raw-guard-typed-pointer-and-frame',at)
 for at,op,target in [(23,0x74,_va(p[81])),(38,0x74,_va(p[110])),(63,0x74,_va(p[75])),(93,0xeb,_va(p[25]))]:require(_raw(p[at])[0]==op and branch_target(p[at])==target,'owned-edge',at)
 require(_raw(p[47])[:2]==bytes.fromhex('0F8F') and branch_target(p[47])==_va(parts[1][0]),'epoch-guard-edge',None)
 choices={_va(p[a]):False for a in (38,47)};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<60,'selected-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  require(r['text']!='int3','exception-exclusion',r)
  if r['text'].startswith('jmp '):walk(branch_target(r),path)
  elif r['text'].startswith(('je ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   if choices.get(va) is not True:walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(_va(p[0]),[]);require(len(paths)==4,'four-selected-normal-paths',len(paths))
 for path in paths:
  stop=_va(p[73]) if _va(p[73]) in path else _va(p[79]);interval=[byva[v] for v in path[path.index(_va(p[6]))+1:path.index(stop)]];_register_preserved(interval,{'rbx'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedNormalPaths':4,'nullCurLevelReturnsNull':True,'compatibleGameLevelReturnsIdPointer':True,'curLevelOffset':192,'idOffset':24,'ClassHeaderOrInlineGuardMeaningProved':False,'actualLiveLevelIdOrStabilityProved':False}

def _methods(image,specs):
 md=image.metadata;result={}
 for role,spec in specs.items():
  owners=[t for t in md.types if md.type_full_name(t)==spec['type'] and md.string(md.images[image.owners[t.index]].name_index)==spec['image']]
  require(len(owners)==1,'level-qualified-owner',(role,len(owners)))
  candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
  m=select_ordinary_overload(image,candidates,spec);p=image.method_pointer_va(m)
  require(p is not None,'level-actual-method-pointer',role);result[role]=(m,p)
 return result

def _field(image,definition,spec):
 md=image.metadata;owner=md.types[definition];fields=[f for f in md.fields_for(owner) if md.string(f.name_index)==spec['name']]
 require(len(fields)==1,'level-unique-concrete-field',spec['name']);f=fields[0];raw=_type_record(image,f.type_index)
 require(bool(struct.unpack_from('<H',raw,8)[0]&16)==(spec['role']=='static'),'level-field-role',spec['name'])
 offsets=runtime_type_field_offsets(md,image.pe,image.registration,definition)
 require(offsets.get(spec['name'])==spec['offset'],'level-field-offset',(spec['name'],offsets.get(spec['name'])))
 token=spec['type'];target=None
 if token in ('String','Int32'):_abi(image,f.type_index,token,'level-field-ordinary')
 elif token.endswith('+State'):target=_enum(image,f.type_index,token)
 else:
  target=_class(image,f.type_index);require(md.type_full_name(md.types[target])==token,'level-field-concrete-class',token)
 return {'index':f.index,'ownerDefinition':definition,'name':spec['name'],'offset':spec['offset'],'role':spec['role'],'rawTypeHex':raw.hex().upper(),'targetDefinition':target}

def validate(image,contract,provider):
 specs=dict(contract['methods']);specs['patch']=provider['methods']['patch'];methods=_methods(image,specs);md=image.metadata;pe=image.pe
 parts={};windows={};proof={}
 for role,sizes in [('caller',(119,103)),('started',(101,100)),('id',(116,100))]:parts[role],windows[role]=_parts(image,methods[role][1],sizes)
 proof['caller']=check_caller(parts['caller'],contract['programs']['caller'],methods,pe.image_base)
 proof['started']=check_started(parts['started'],contract['programs']['started'])
 proof['id']=check_id(parts['id'],contract['programs']['id'])
 row=next(r for r in parts['caller'][0] if r['offset']==29);raw=_raw(row);cell=_va(row)+7+struct.unpack_from('<i',raw,3)[0]
 root_index=unresolved_usage_index(pe.bytes_at_va(cell,8),image.registration['typesCount'],tag=1,source=str(image.gameassembly),offset=cell)
 root=_class(image,root_index);require(md.type_full_name(md.types[root])==contract['fields']['worldInfo']['owner'],'level-root-type-context',root)
 world=methods['id'][0].declaring_type;level=methods['started'][0].declaring_type
 fields={}
 for role,definition in [('worldInfo',root),('curLevel',world),('state',level),('id',level)]:
  spec=contract['fields'][role];require(md.type_full_name(md.types[definition])==spec['owner'],'level-field-qualified-owner',role);fields[role]=_field(image,definition,spec)
 for role,displacement in [('worldInfo',496),('curLevel',proof['id']['curLevelOffset']),('state',proof['started']['actualStateLaneOffset']),('id',proof['id']['idOffset'])]:require(fields[role]['offset']==displacement,'level-actual-raw-field-displacement',(role,fields[role]['offset'],displacement))
 require(fields['worldInfo']['targetDefinition']==world and fields['curLevel']['targetDefinition']==level,'level-same-concrete-getter-receivers',None)
 string_spec=dict(provider['stringLength']);string_spec.update(role='instance',type='Int32')
 string=methods['equals'][0].declaring_type;require(md.type_full_name(md.types[string])==string_spec['owner'],'level-String-concrete-owner',string)
 fields['stringLength']=_field(image,string,string_spec)
 require(fields['stringLength']['offset']==16,'level-caller-length-displacement',fields['stringLength'])
 declaration=declared_members(image,fields['state']['targetDefinition'],contract['fields']['state']['type'],field_defaults(md))
 require(any(r['id']==2 for r in declaration['members']),'level-threshold-declared-alias',declaration)
 proof.update(fields=fields,stateDeclarations=declaration,thresholdAliases=[r for r in declaration['members'] if r['id']==2],windows=windows,methods={r:{'index':m.index,'rva':p-pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},rootContext={'registeredTypeIndex':root_index,'definition':root},runtimeLifecycleOrRecordStabilityProved=False)
 return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='level_predicate_value_sources')
    provider,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='level_predicate_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-level-predicate-value-sources-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_level_predicate_value_sources_native_latest.json')
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
        print('level-predicate-value-sources:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Level predicate/getter selected normal paths passed; header/live/stability unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
