"""Selected typed completion predicates; Boolean low byte, no live completion."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_completion_predicates_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, dictionary_context, _register_preserved, select_ordinary_overload)
from scripts.game_data.dynamic_mission_state_cache_native import _field, _enum, _class
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_mission_completion_predicates_native_claims.json'
SCHEMA='endfield.dynamic-mission-completion-predicates-native-claims.v1'


from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.il2cpp.protocol import field_defaults

def check_predicate(parts,role,programs,patch,request):
    require(len(parts)==len(programs),'completion-part-roster',len(parts));byva={}
    for rows,program in zip(parts,programs):
        _grammar(rows,program);cursor=0;start=_va(rows[0])
        for row in rows:
            require(row['offset']==cursor and _va(row)==start+cursor and _raw(row) and not row['text'].startswith(('db','unknown','ff/')),'completion-owned-partition',row);cursor+=len(_raw(row));require(_va(row) not in byva,'completion-disjoint',row);byva[_va(row)]=row
    primary=parts[0];m={r['offset']:r for r in primary};mission=role=='mission';size=81 if mission else 105
    require(primary[-1]['offset']+len(_raw(primary[-1]))==size,'completion-primary-size',size)
    fixed={0:'48895C2408',5:'57',6:'4883EC20',10:'488BDA',13:'488BF9',16:'33D2',28:'84C0'}
    fixed.update({36:'4533C9',39:'4533C0',42:'488BD3',45:'488BCF',53:'4885C0',64:'B001',66:'488B5C2430',71:'4883C420',75:'5F',76:'C3',77:'32C0'} if mission else {32:'4533C0',35:'488BD3',38:'488BCF',49:'0F94C0',94:'488B5C2430',99:'4883C420',103:'5F',104:'C3'})
    for at,raw in fixed.items():require(_raw(m[at])==bytes.fromhex(raw),'completion-frame-args-value',at)
    compare=_raw(m[58 if mission else 46]);prefix=bytes.fromhex('837818' if mission else '83F8')
    require(compare[:-1]==prefix and len(compare)==len(prefix)+1,'completion-ordinary-Int32-comparison',compare.hex())
    bits=int.from_bytes(compare[-1:],'little',signed=True)
    require(branch_target(m[23])==patch and branch_target(m[48 if mission else 41])==request,'completion-actual-calls',None)
    edges={30:('0F85',_va(parts[1][0])),56:('74',_va(m[77])),62:('75',_va(m[77])),79:('EB',_va(m[66]))} if mission else {30:('75',_va(m[54])),52:('EB',_va(m[94]))}
    for at,(opcode,target) in edges.items():require(_raw(m[at]).startswith(bytes.fromhex(opcode)) and branch_target(m[at])==target and target in byva,'completion-owned-selected-edge',at)
    _register_preserved([r for r in primary if 13<r['offset']<(48 if mission else 41)],{'rbx','rdi'},{_va(m[23])})
    paths=[]
    def walk(va,path):
        require(va in byva and va not in path and len(path)<80,'completion-owned-CFG',va);path=path+[va];row=byva[va]
        if row['text']=='ret':paths.append(path);return
        require(row['text']!='int3','completion-false-patch-exception',row)
        if row['text'].startswith('jmp '):walk(branch_target(row),path)
        elif row['text'].startswith(('je ','jne ','jcc ')):
            if va!=_va(m[30]):walk(branch_target(row),path)
            walk(va+len(_raw(row)),path)
        else:walk(va+len(_raw(row)),path)
    walk(_va(primary[0]),[]);require(len(paths)==(3 if mission else 1),'completion-normal-paths',len(paths))
    return {'normalPaths':len(paths),'BooleanLowByteOnly':True,'normalizedLowByte':True,'trueComparisonBits':bits,'missionStoredFieldOffset':compare[2] if mission else None,'nullMissionDataReturnsFalse':mission,'runtimeObserved':False,'lookupSelectionProved':False}

def matching_members(declaration,bits):
    members=[m for m in declaration['members'] if m['id']==bits]
    require(bool(members),'completion-declared-comparison-value',bits)
    return members


def _select_methods(image,specs):
    md=image.metadata;methods={};definitions={}
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'completion-qualified-owner-'+role,len(owners));candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role in ('lookup','missionState','questState'):
            matched=[]
            for m in candidates:
                params=md.parameters_for(m)
                if bool(m.flags&0x10)!=(spec['callAbi']=='static') or len(params)!=len(spec['parameters']):continue
                try:
                    for param,token in zip(params,spec['parameters']):_abi(image,param.type_index,token,'completion-parameter-'+role)
                    definition=_class(image,m.return_type) if role=='lookup' else _enum(image,m.return_type,spec['returnType'])
                    require(md.type_full_name(md.types[definition])==spec['returnType'],'completion-return-concrete-'+role,definition)
                except (ValueError,KeyError,IndexError,RuntimeError,struct.error):continue
                matched.append((m,definition))
            require(len(matched)==1,'completion-unique-full-ABI-'+role,[m.index for m,_ in matched]);m,definitions[role]=matched[0]
        else:m=select_ordinary_overload(image,candidates,spec)
        pointer=image.method_pointer_va(m);require(pointer is not None,'completion-actual-pointer-'+role,pointer);methods[role]=(m,pointer)
    require(len({methods[r][0].declaring_type for r in ('mission','quest','lookup','missionState','questState')})==1,'completion-same-concrete-system',None)
    return methods,definitions


def validate(image,contract,provider,stored,cache,symbols):
    md=image.metadata;specs=dict(contract['methods']);specs.update({'patch':provider['methods']['patch'],'lookup':stored['methods']['lookup'],
                    'missionState':cache['methods']['missionState'],'questState':cache['methods']['questState']})
    methods,definitions=_select_methods(image,specs);spec=stored['returnedField']
    f=_field(image,definitions['lookup'],spec['name'],spec['offset'])
    field_definition=_enum(image,f.type_index,specs['missionState']['returnType'])
    require(field_definition==definitions['missionState'],'completion-field-getter-same-enum-definition',field_definition)
    require(symbols['methodRoles']==['missionState','questState'],'completion-declaration-role-roster',symbols['methodRoles'])
    defaults=field_defaults(md);declarations={r:declared_members(image,definitions[r],specs[r]['returnType'],defaults) for r in symbols['methodRoles']}
    pe=image.pe;table_rva,size,table=read_exception_directory(pe);unwind=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size)
    proofs=[]
    for role in ('mission','quest'):
        method,pointer=methods[role];family=unwind.family(pointer-pe.image_base)
        require(len(family['ranges'])==(2 if role=='mission' else 1),'completion-owned-range-roster',role);parts=[];windows=[]
        for part in family['ranges']:
            begin,end,_=part['runtimeTriple'];require(0<end-begin<=256,'completion-bounded-owned-range',part)
            raw=pe.bytes_at_va(pe.image_base+begin,end-begin);parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
            windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
        require(_va(parts[0][0])==pointer,'completion-actual-primary-first',pointer)
        proof=check_predicate(parts,role,contract['programs'][role],methods['patch'][1],methods['lookup' if role=='mission' else 'questState'][1])
        if role=='mission':require(proof['missionStoredFieldOffset']==spec['offset'],'completion-actual-field-displacement',(proof['missionStoredFieldOffset'],spec['offset']))
        declaration=declarations['missionState' if role=='mission' else 'questState']
        proof.update({'role':role,'methodIndex':method.index,'windows':windows,'comparisonEnum':declaration,'comparisonAliases':matching_members(declaration,proof['trueComparisonBits'])});proofs.append(proof)
    return {'predicates':proofs,'missionField':{'index':f.index,'ownerDefinition':definitions['lookup'],'name':spec['name'],'offset':spec['offset'],'enumDefinition':field_definition,'rawTypeHex':_type_record(image,f.type_index).hex().upper()},
            'methods':{r:{'index':m.index,'rva':p-pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},
            'sameQueryResultOrLiveStateProved':False,'authoredSourceAssociationProved':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_completion_predicates')
    provider,stored,cache,symbols=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='completion_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider,stored,cache,symbols)
    return {'format':'endfield.dynamic-mission-completion-predicates-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_completion_predicates_native_latest.json')
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
        print('mission-completion-predicates:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission completion predicates passed: typed Boolean low byte; live completion unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
