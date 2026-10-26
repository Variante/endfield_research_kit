"""Conditional concrete ObjectiveData byte normalization; indexed API unresolved."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_objective_boolean_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.il2cpp.context import method_spec_usage_index, type_parameter_owner, generic_method_candidates
from scripts.game_data.dynamic_quest_state_value_source_native import storage_reference
from scripts.game_data.dynamic_mission_string_providers_native import select_ordinary_overload
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, _register_preserved)
from scripts.game_data.dynamic_mission_state_cache_native import _field
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_quest_objective_boolean_native_claims.json'
SCHEMA='endfield.dynamic-quest-objective-boolean-native-claims.v1'


from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.il2cpp.protocol import field_defaults

def check_predicate(rows,program,patch):
 _grammar(rows,program)
 by={r['offset']:r for r in rows};byva={_va(r):r for r in rows};require(len(by)==len(rows)==len(byva),'distinct',None);cursor=0;start=_va(rows[0])
 for r in rows:
  require(r['offset']==cursor and _va(r)==start+cursor and not r['text'].startswith(('db','unknown','ff/')),'complete-recognized-partition',r);cursor+=len(_raw(r))
 require(cursor==255,'owned-extent',cursor)
 require(branch_target(by[89])==patch,'actual-qualified-patch-call',None)
 fixed={0:'48895C2408',5:'4889742410',10:'57',11:'4883EC40',22:'418BD8',25:'488BF2',28:'488BF9',76:'488364243000',82:'33D2',94:'84C0',98:'488B8FE0000000',105:'4885C9',117:'4C8D442430',122:'488BD6',130:'84C0',134:'488B4C2430',139:'4885C9',144:'488B4120',148:'4885C0',153:'3B5818',165:'8BD3',167:'488BC8',175:'4885C0',180:'80782800',184:'0F95C0',189:'32C0',239:'488B5C2450',244:'488B742458',249:'4883C440',253:'5F',254:'C3'}
 for at,b in fixed.items():require(_raw(by[at])==bytes.fromhex(b),'frame-args-typed-displacements-normalizedByte',at)
 expected={31:(0x75,76),96:(0x75,193),108:(0x74,210),132:(0x74,189),142:(0x74,210),151:(0x74,210),156:(0x7d,189),178:(0x74,210),187:(0xeb,239),191:(0xeb,239),208:(0x75,216)}
 for at,(op,dest) in expected.items():require(_raw(by[at])[0]==op and branch_target(by[at])==_va(by[dest]),'owned-instruction-edge',at)
 choices={_va(by[a]):False for a in (96,108,142,151,178)};paths=[]
 def walk(va,path):
  require(va in byva and va not in path and len(path)<100,'complete-selected-CFG',va);path=path+[va];r=byva[va]
  if r['text']=='ret':paths.append(path);return
  require(r['text']!='int3','exception-exclusion',r)
  if r['text'].startswith('jmp '):walk(branch_target(r),path)
  elif r['text'].startswith(('je ','jne ','jge ')):
   if choices.get(va) is not False:walk(branch_target(r),path)
   if choices.get(va) is not True:walk(va+len(_raw(r)),path)
  else:walk(va+len(_raw(r)),path)
 walk(start,[]);require(len(paths)==6,'six-normal-paths',len(paths))
 for path in paths:
  interval=[byva[v] for v in path[path.index(_va(by[28]))+1:path.index(_va(by[239]))]];_register_preserved(interval,{'rbx','rsi','rdi'},{_va(r) for r in interval if r['text'].startswith('call ')})
 return {'normalPaths':6,'normalizedBooleanLowByte':True,'allRaxBitsNormalized':False,'directCompatibleObjectiveDataByteFieldOffset':_raw(by[180])[-2],'questStorageOffset':int.from_bytes(_raw(by[98])[3:],'little'),'questObjectivesOffset':_raw(by[144])[-1],'anonymousSignedLaneOffset':_raw(by[153])[-1],'dictionaryOrIndexedAPIProved':False,'validIndexOrLiveCompletionProved':False}

def _methods(image,specs):
    md=image.metadata;methods={}
    for role,spec in specs.items():
        owners=[t for t in md.types if md.type_full_name(t)==spec['type'] and md.string(md.images[image.owners[t.index]].name_index)==spec['image']]
        require(len(owners)==1,'objective-qualified-owner',(role,len(owners)));candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        method=select_ordinary_overload(image,candidates,spec);pointer=image.method_pointer_va(method);require(pointer is not None,'objective-actual-pointer',role);methods[role]=(method,pointer)
    return methods


def list_reference(image,field):
    selected=NativeReferenceContext(image);extent=closed_generic_reference_extent(selected,field.type_index);md=image.metadata;pe=image.pe
    require(md.type_full_name(md.types[extent['definitionTypeIndex']])=='System.Collections.Generic.List`1','objective-list-concrete-definition',extent)
    generic=int.from_bytes(bytes.fromhex(extent['declaredTypeRecordHex'])[:8],'little');count,argv=struct.unpack('<QQ',pe.bytes_at_va(pe.u64_at_va(generic+8),16));require(count==1,'objective-list-one-argument',count)
    argument=pe.bytes_at_va(pe.u64_at_va(argv),16);require(argument[10]==0x12 and argument[11]==0,'objective-list-ordinary-Class-argument',argument.hex())
    definition=int.from_bytes(argument[:8],'little');require(0<=definition<len(md.types),'objective-argument-definition-range',definition)
    return extent,argument,definition


def indexed_context(image,row,call_row,extent,argument):
    pe=image.pe;md=image.metadata;reg=image.registration;raw=_raw(row)
    require(len(raw)==7 and raw[:3]==bytes.fromhex('4C8B05'),'objective-context-R8-load',row);cell=_va(row)+7+struct.unpack_from('<i',raw,3)[0]
    spec=method_spec_usage_index(pe.bytes_at_va(cell,8),reg['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    definition,ci,mi=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+spec*12,12));require(0<=definition<len(md.methods) and 0<=ci<reg['genericInstsCount'] and mi==-1,'objective-context-roster',(definition,ci,mi))
    method=md.methods[definition];params=md.parameters_for(method)
    require(method.declaring_type==extent['definitionTypeIndex'] and md.string(method.name_index)=='get_Item' and not method.flags&16 and len(params)==1,'objective-context-definition',definition)
    _abi(image,params[0].type_index,'Int32','objective-context-parameter');record=_type_record(image,method.return_type);require(record[10]==0x13 and record[11]==0,'objective-context-ordinary-return-VAR',record.hex())
    owner=type_parameter_owner(md.buf,int.from_bytes(record[:8],'little'),[t.generic_container_index for t in md.types],source=str(image.metadata_path));require(owner['typeIndex']==method.declaring_type and owner['ordinal']==0,'objective-context-return-owner',owner)
    args=image.instantiations.resolve(ci).arguments;require(len(args)==1 and bytes.fromhex(args[0].raw_type_record_hex)==argument,'objective-context-same-field-argument',[a.raw_type_record_hex for a in args])
    code=image.mapper.code_registration_summary(pe,image.code_registration);table=int(reg['genericMethodTable'],16);candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],reg['methodSpecsCount'],{spec},code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    require(len(_raw(call_row))==5 and _raw(call_row)[0]==0xe8,'objective-opaque-direct-call',call_row)
    return {'methodSpecIndex':spec,'definition':definition,'classInstantiation':ci,'argumentRawHex':argument.hex().upper(),'actualCallPointerRva':branch_target(call_row)-pe.image_base,
        'exactCandidateCount':len(candidates),'candidatePointerRvas':[pe.u64_at_va(int(code['genericMethodPointers'],16)+r['indices'][0]*8)-pe.image_base for r in candidates[:8]],
        'actualIndexedAPIProved':False,'contextDescribesRequestOnly':True,'validIndexOrItemOrdinalProved':False}


def bind_fields(proof,fields):
    for key,role in [('questStorageOffset','storage'),('questObjectivesOffset','objectives'),('directCompatibleObjectiveDataByteFieldOffset','completed')]:require(proof[key]==fields[role]['offset'],'objective-field-displacement',(key,proof[key],fields[role]['offset']))
    return proof


def validate(image,contract,value,message,provider):
    specs=dict(contract['methods']);specs.update({'constructor':message['methods']['constructor'],'patch':provider['methods']['patch']});methods=_methods(image,specs);md=image.metadata;pe=image.pe;fields={}
    data=methods['constructor'][0].declaring_type;system=methods['predicate'][0].declaring_type;spec=value['storageFields']['direct'];f=_field(image,system,spec['name'],spec['offset'])
    fields['storage']={'index':f.index,'ownerDefinition':system,'name':spec['name'],'offset':spec['offset'],'reference':storage_reference(image,f,data)}
    spec=contract['fields']['objectives'];f=_field(image,data,spec['name'],spec['offset']);extent,argument,objective=list_reference(image,f)
    fields['objectives']={'index':f.index,'ownerDefinition':data,'name':spec['name'],'offset':spec['offset'],'reference':extent,'argumentRawHex':argument.hex().upper()}
    require(md.type_full_name(md.types[objective])==contract['objectiveType'],'objective-concrete-argument-type',objective)
    spec=contract['fields']['completed'];f=_field(image,objective,spec['name'],spec['offset']);_abi(image,f.type_index,'Boolean','objective-completed-field')
    fields['completed']={'index':f.index,'ownerDefinition':objective,'name':spec['name'],'offset':spec['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    pointer=methods['predicate'][1];table_rva,size,table=read_exception_directory(pe);family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(pointer-pe.image_base)
    require(len(family['ranges'])==1,'objective-single-owned-primary',len(family['ranges']));part=family['ranges'][0];begin,end,_=part['runtimeTriple'];require(pe.image_base+begin==pointer and end-begin==255,'objective-actual-primary-extent',part)
    raw=pe.bytes_at_va(pointer,end-begin);rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper));proof=check_predicate(rows,contract['program'],methods['patch'][1]);bind_fields(proof,fields);by={r['offset']:r for r in rows}
    proof.update({'fields':fields,'indexedContext':indexed_context(image,by[158],by[170],extent,argument),'window':{'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']},
       'methods':{r:{'index':m.index,'rva':p-pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},
       'genericStoredLaneOwnershipProved':False,'providerOrRuntimeCompletionProved':False})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_objective_boolean')
    value,message,provider=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='quest_objective_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,value,message,provider)
    return {'format':'endfield.dynamic-quest-objective-boolean-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_objective_boolean_native_latest.json')
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
        print('quest-objective-boolean:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Objective Boolean passed: compatible concrete byte normalized to AL; indexed API/lane ownership/live unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
