"""Conditional typed Quest action requests; execution and queue behavior unresolved."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_action_requests_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, _register_preserved)
from scripts.game_data.dynamic_mission_state_cache_native import _enum
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_quest_action_requests_native_claims.json'
SCHEMA='endfield.dynamic-quest-action-requests-native-claims.v1'


from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.il2cpp.protocol import field_defaults

def _partition(parts,programs,sizes):
    require(len(parts)==len(programs)==len(sizes),'quest-action-owned-roster',len(parts));allrows=[]
    for rows,program,size in zip(parts,programs,sizes):
        _grammar(rows,program);cursor=0;start=_va(rows[0])
        for row in rows:
            require(row['offset']==cursor and _va(row)==start+cursor and not row['text'].startswith(('db','unknown','ff/')),'quest-action-complete-partition',row)
            cursor+=len(_raw(row));allrows.append(row)
        require(cursor==size,'quest-action-owned-size',cursor)
    by={_va(r):r for r in allrows};require(len(by)==len(allrows),'quest-action-disjoint-owned-ranges',None);return by

def check_suffix(parts,programs,remove,safe):
 _partition(parts,programs,(56,355,211));p={r['offset']:r for r in parts[0]};m={r['offset']:r for r in parts[1]}
 for at,b in {0:'48896C2418',5:'56',6:'4883EC30',17:'488BEA',20:'488BF1'}.items():require(_raw(p[at])==bytes.fromhex(b),'source-entry-bindings-frame',at)
 require(_raw(m[0])==bytes.fromhex('48895C2440') and _raw(m[12])==bytes.fromhex('48897C2448'),'source-callee-saves-frame',None)
 require(_raw(m[159])[:1]==b'\x74' and branch_target(m[159])==_va(m[252]),'source-owned-suffix-entry',None)
 rows=[r for r in parts[1] if 252<=r['offset']<=312]
 require([r['offset'] for r in rows]==[252,255,261,264,267,272,275,281,284,287,292,297,302,307,311,312],'whole-selected-suffix-boundaries',None)
 fixed={252:'4533C9',255:'41B801000000',261:'488BD5',264:'488BCE',272:'4533C9',275:'41B802000000',281:'488BD5',284:'488BCE',292:'488B7C2448',297:'488B5C2440',302:'488B6C2450',307:'4883C430',311:'5E',312:'C3'}
 by={r['offset']:r for r in rows}
 for at,b in fixed.items():require(_raw(by[at])==bytes.fromhex(b),'argument-constant-source-or-frame',at)
 for at,pointer in [(267,remove),(287,safe)]:require(branch_target(by[at])==pointer,'actual-qualified-request-pointer',at)
 require(all(_va(r)==_va(rows[0])+r['offset']-252 for r in rows),'continuous-owned-suffix',None)
 _register_preserved(rows[:10],{'rbp','rsi'},{_va(by[267]),_va(by[287])})
 return {'typedRequestBits':[1,2],'entryPathProved':False,'selectedSuffixNormalReturnProved':True,'incomingOriginalReceiverAndStringRequired':True,'runtimeActionExecutionProved':False}

def check_safe(parts,programs,patch,available,run):
 byva=_partition(parts,programs,(134,136));p={r['offset']:r for r in parts[0]}
 fixed={0:'48895C2408',5:'4889742410',10:'57',11:'4883EC50',22:'418BF8',25:'488BF2',28:'488BD9',64:'33D2',76:'33D2',78:'84C0',86:'33C9',93:'84C0',101:'4533C9',104:'448BC7',107:'488BD6',110:'488BCB',118:'488B5C2460',123:'488B742468',128:'4883C450',132:'5F',133:'C3'}
 for at,b in fixed.items():require(_raw(p[at])==bytes.fromhex(b),'saved-input-null-and-frame',at)
 require(branch_target(p[71])==patch,'actual-patch-call',None)
 for at,pointer in [(88,available),(113,run)]:require(branch_target(p[at])==pointer,'actual-qualified-typed-request',at)
 require(_raw(p[31])[:1]==bytes.fromhex('75') and branch_target(p[31])==_va(p[64]),'actual-init-edge',None)
 require(_raw(p[80])[:2]==bytes.fromhex('0F85') and branch_target(p[80])==_va(parts[1][0])+83,'actual-patch-edge',None)
 require(_raw(p[95])[:2]==bytes.fromhex('0F84') and branch_target(p[95])==_va(parts[1][0]),'actual-Bool-zero-edge',None)
 choices={_va(p[80]):False,_va(p[95]):False};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<80,'selected-normal-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  if r['text'].startswith(('jne ','jcc ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(_va(p[0]),[]);require(len(paths)==2,'two-init-direct-normal-paths',len(paths))
 for path in paths:
  start=path.index(_va(p[28]))+1;end=path.index(_va(p[118]));interval=[byva[v] for v in path[start:end]];_register_preserved(interval,{'rbx','rsi','rdi'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'selectedNormalPaths':2,'actualStaticBoolRequestArgument':'null String','actualBoolLowByteSelection':'nonzero','actualRunQuestActionInputBits':'original QuestAction low32 unmodified','runtimeLevelAvailabilityOrActionExecutionProved':False,'queueOrTupleABIProved':False}

def source_methods(image,specs):
    md=image.metadata;methods={};definitions={}
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'quest-action-qualified-owner',role);matches=[]
        for m in md.methods_for(owners[0]):
            if md.string(m.name_index)!=spec['method'] or bool(m.flags&16)!=(spec['callAbi']=='static'):continue
            params=md.parameters_for(m)
            if len(params)!=len(spec['parameters']):continue
            try:
                _abi(image,m.return_type,spec['returnType'],'return')
                definition=None
                for p,token in zip(params,spec['parameters']):
                    if token=='Beyond.Gameplay.QuestAction':definition=_enum(image,p.type_index,token)
                    else:_abi(image,p.type_index,token,'parameter')
            except (ValueError,KeyError,IndexError,RuntimeError):continue
            matches.append((m,definition))
        require(len(matches)==1,'quest-action-unique-full-ordinary-ABI',(role,[m.index for m,_ in matches]));m,definition=matches[0];pointer=image.method_pointer_va(m)
        require(pointer is not None,'quest-action-actual-pointer',role);methods[role]=(m,pointer)
        if definition is not None:definitions[role]=definition
    require(len({methods[r][0].declaring_type for r in ('source','safe','remove','run')})==1,'quest-action-same-concrete-system',None)
    require(len(definitions)==3 and len(set(definitions.values()))==1,'quest-action-same-concrete-enum',definitions)
    return methods,next(iter(definitions.values()))

def _parts(image,pointer,sizes):
    pe=image.pe;table_rva,size,table=read_exception_directory(pe);family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(pointer-pe.image_base)
    require(len(family['ranges'])==len(sizes),'quest-action-declared-family',len(family['ranges']));parts=[];windows=[]
    for part,expected in zip(family['ranges'],sizes):
        begin,end,_=part['runtimeTriple'];require(end-begin==expected,'quest-action-owned-extent',(end-begin,expected))
        raw=pe.bytes_at_va(pe.image_base+begin,end-begin);parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
        windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    require(_va(parts[0][0])==pointer,'quest-action-actual-primary-start',pointer);return parts,windows


def matching_aliases(declaration,bits):
    rows=[r for r in declaration['members'] if r['id']==bits];require(bool(rows),'quest-action-argument-declaration',bits);return rows


def validate(image,contract,provider):
    specs=dict(contract['methods']);specs['patch']=provider['methods']['patch'];methods,definition=source_methods(image,specs)
    source,source_windows=_parts(image,methods['source'][1],(56,355,211));safe,safe_windows=_parts(image,methods['safe'][1],(134,136))
    suffix=check_suffix(source,contract['programs'],methods['remove'][1],methods['safe'][1]);direct=check_safe(safe,contract['safePrograms'],methods['patch'][1],methods['available'][1],methods['run'][1])
    declaration=declared_members(image,definition,'Beyond.Gameplay.QuestAction',field_defaults(image.metadata))
    return {'suffix':suffix,'safeDirect':direct,'actionDeclarations':declaration,'suffixArgumentAliases':[matching_aliases(declaration,b) for b in suffix['typedRequestBits']],
       'windows':{'source':source_windows,'safe':safe_windows},'methods':{r:{'index':m.index,'rva':p-image.pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},
       'fullSucceedQuestEntryProved':False,'queueOrTupleABIProved':False,'runtimeActionExecutionProved':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_action_requests')
    provider,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='quest_action_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-quest-action-requests-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_action_requests_native_latest.json')
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
        print('quest-action-requests:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest action requests passed: conditional typed suffix/direct calls; entry, queue and execution unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
