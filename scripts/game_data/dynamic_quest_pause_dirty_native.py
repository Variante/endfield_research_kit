"""Selected MissionData dirty-byte writes; opaque collection calls."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_pause_dirty_native')
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
from scripts.game_data.il2cpp.integer_addressing import decode_multibyte_nop
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_quest_pause_dirty_native_claims.json'
SCHEMA='endfield.dynamic-quest-pause-dirty-native-claims.v3'


def _dirty_decoder(mapper):
    class ExistingNop:
        def decode_one_x64(self,raw,offset,start_va):
            result=decode_multibyte_nop(raw,offset,start_va)
            return result if result is not None else mapper.decode_one_x64(raw,offset,start_va)
    return _composed_decoder(ExistingNop())


def check_clear_return(parts,programs):
    require(len(parts)==5,'quest-dirty-clear-declared-ranges',len(parts));byva={};sizes=[]
    for rows in parts:
        cursor=0;start=_va(rows[0])
        for row in rows:
            raw=_raw(row);require(row['offset']==cursor and _va(row)==start+cursor and raw and not row['text'].startswith(('db','unknown','ff/')),'quest-dirty-clear-recognized-partition',row);cursor+=len(raw)
            require(_va(row) not in byva,'quest-dirty-clear-disjoint-owned-instructions',row);byva[_va(row)]=row
        sizes.append(cursor)
    require(sizes==[36,552,17,52,281],'quest-dirty-clear-owned-sizes',sizes)
    primary,main=parts[:2];p={r['offset']:r for r in primary};m={r['offset']:r for r in main}
    _grammar(primary,programs[0]);_grammar([r for r in main if r['offset']<251],programs[1])
    require(_va(primary[-1])+len(_raw(primary[-1]))==_va(main[0]),'quest-dirty-clear-owned-entry-fallthrough',None)
    fixed={40:'807B6000',94:'488B7808',98:'4885FF',107:'488B4B48',111:'4885C9',127:'488BD7',135:'488B4B50',139:'4885C9',155:'488BD7',163:'488B4B58',167:'4885C9',188:'33FF',190:'8BF7',192:'488B4348',196:'4885C0',205:'3B7018',220:'488B4350',224:'4885C0',233:'3B7818',242:'C6436000'}
    for at,raw in fixed.items():require(_raw(m[at])==bytes.fromhex(raw),'quest-dirty-clear-source-zero-lanes-store',at)
    selected={(0,23):False,(1,21):False,(1,34):False,(1,44):True,(1,81):False,(1,101):False,(1,114):False,(1,142):False,(1,170):False,(1,199):False,(1,208):False,(1,227):False,(1,236):False}
    opcodes={21:'0F84',34:'0F8F',44:'75',81:'0F84',101:'0F84',114:'0F84',142:'0F84',170:'0F84',199:'0F84',208:'7C',227:'0F84',236:'0F8C',246:'E9'}
    for at,opcode in opcodes.items():require(_raw(m[at]).startswith(bytes.fromhex(opcode)) and branch_target(m[at]) in byva,'quest-dirty-clear-owned-direction',at)
    require(branch_target(m[44])==_va(m[67]) and branch_target(m[246])==_va(m[46]),'quest-dirty-clear-store-to-balanced-return',None)
    choices={_va(parts[part][next(i for i,r in enumerate(parts[part]) if r['offset']==at)]):take for (part,at),take in selected.items()}
    path=[];va=_va(primary[0])
    while True:
        require(va in byva and va not in path and len(path)<120,'quest-dirty-clear-selected-owned-path',va);path.append(va);row=byva[va]
        if row['text']=='ret':break
        require(row['text']!='int3','quest-dirty-clear-selected-exception',row)
        if row['text'].startswith('jmp '):va=branch_target(row)
        elif row['text'].startswith(('je ','jne ','jcc ','jl ')):
            require(va in choices,'quest-dirty-clear-explicit-selection',row);va=branch_target(row) if choices[va] else va+len(_raw(row))
        else:va+=len(_raw(row))
    require(path[-1]==_va(m[66]) and _va(m[242]) in path,'quest-dirty-clear-actual-store-and-return',path)
    # Reuse the exact zero-byte return frame/source proof, changing only the selected field branch.
    check_clean_return([primary,[r for r in main if r['offset']<74]], [programs[0], [_token for _token in programs[1][:len([r for r in main if r['offset']<74])]]], {_va(r[0]) for r in parts})
    watched=[byva[va] for va in path[path.index(_va(p[6]))+1:path.index(_va(m[242]))]]
    allowed={_va(m[a]) for a in (130,158,183)};_register_preserved(watched,{'rbx'},allowed)
    require({_va(r) for r in watched if r['text'].startswith('call ')}==allowed,'quest-dirty-clear-three-opaque-calls',None)
    return {'selectedNormalReturnProved':True,'constantByte':0,'opaqueNormalCalls':3,'signedReferenceLanes':'both Int32 reads at reference+24 <= 0','ListCountMeaningProved':False,'listMutationProved':False,'completeRefreshProgramProved':False,'runtimeObserved':False,'declaredRangesPartitioned':5}


def check_dirty(rows,role,program,patch):
    _grammar(rows,program);by={r['offset']:r for r in rows};byva={_va(r):r for r in rows};start=_va(rows[0]);cursor=0
    for row in rows:
        raw=_raw(row);require(row['offset']==cursor and _va(row)==start+cursor and raw and not row['text'].startswith(('db','unknown','ff/')),'quest-dirty-complete-partition',row);cursor+=len(raw)
        if row['text'].startswith(('je ','jne ','jcc ','jmp ')):require(branch_target(row) in byva,'quest-dirty-owned-edge',row)
        if row['text'].startswith('call '):require(len(raw)==5 and raw[0]==0xe8,'quest-dirty-direct-call',row)
    require(cursor==({'add':181,'remove':145}[role]),'quest-dirty-owned-size',cursor)
    add=role=='add';goal=124 if add else 88;patch_at=63 if add else 51
    fixed=[(0,'48895C2408'),(5,'57'),(6,'4883EC20'),(17,'488BFA'),(20,'488BD9')]
    fixed+=([(56,'33D2'),(68,'84C0'),(72,'488B4B50'),(76,'4885C9'),(88,'488BD7'),(96,'84C0'),(100,'488B4B50'),(104,'4885C9'),(116,'488BD7'),(124,'C6436001')] if add else [(44,'33D2'),(56,'84C0'),(60,'488B4B50'),(64,'4885C9'),(76,'488BD7'),(84,'84C0'),(88,'C6436001')])
    for at,raw in fixed:require(_raw(by[at])==bytes.fromhex(raw),'quest-dirty-source-args-store',at)
    edges={23:('75',56),70:('75',130),79:('74',147),98:('75',170),107:('74',147)} if add else {23:('75',44),58:('75',94),67:('74',111),86:('74',134)}
    for at,(opcode,target) in edges.items():require(_raw(by[at]).startswith(bytes.fromhex(opcode)) and branch_target(by[at])==_va(by[target]),'quest-dirty-selected-direction',(at,target))
    require(branch_target(by[patch_at])==patch,'quest-dirty-actual-patch',patch_at)
    cmp=by[10];store=by[49 if add else 37]
    require(_raw(cmp)[:2]==b'\x80\x3d' and _raw(cmp)[-1:]==b'\0' and _raw(store)[:2]==b'\xc6\x05' and _raw(store)[-1:]==b'\1' and
            _va(cmp)+len(_raw(cmp))+struct.unpack_from('<i',_raw(cmp),2)[0]==_va(store)+len(_raw(store))+struct.unpack_from('<i',_raw(store),2)[0],'quest-dirty-same-init-cell',None)
    selected={at:False for at in edges if at!=23};paths=[]
    def visit(at,path):
        require(at in by and at not in path and len(path)<100,'quest-dirty-path',at);path=path+[at];row=by[at]
        if at==goal:paths.append(path);return
        require(row['text'] not in ('int3','ret'),'quest-dirty-pre-store-stop',row);nxt=at+len(_raw(row))
        if row['text'].startswith(('je ','jne ','jcc ')):
            if selected.get(at) is not False:visit(byva[branch_target(row)]['offset'],path)
            if selected.get(at) is not True:visit(nxt,path)
        elif row['text'].startswith('jmp '):visit(byva[branch_target(row)]['offset'],path)
        else:visit(nxt,path)
    visit(0,[]);require(len(paths)==2,'quest-dirty-two-init-paths',len(paths))
    for path in paths:
        watched=[by[a] for a in path if 20<a<goal];_register_preserved(watched,{'rbx','rdi'},{_va(r) for r in watched if r['text'].startswith('call ')})
    return {'selectedWritePaths':2,'constantByte':1,'opaqueResultCondition':'first AL zero; second normal return' if add else 'AL nonzero', 'collectionMutationProved':False,'runtimeObserved':False,'fullNormalReturnProved':False}


def check_clean_return(parts,programs,owned_starts):
    require(len(parts)==len(programs)==2,'quest-dirty-clean-two-intervals',len(parts))
    for rows,program,size in zip(parts,programs,(36,74)):
        _grammar(rows,program);cursor=0;start=_va(rows[0])
        for row in rows:
            raw=_raw(row);require(row['offset']==cursor and _va(row)==start+cursor and raw and not row['text'].startswith(('db','unknown','ff/')),'quest-dirty-clean-recognized-prefix',row);cursor+=len(raw)
        require(cursor==size,'quest-dirty-clean-prefix-size',cursor)
    primary,main=parts;p={r['offset']:r for r in primary};m={r['offset']:r for r in main}
    require(_va(primary[-1])+len(_raw(primary[-1]))==_va(main[0]),'quest-dirty-clean-owned-fallthrough',None)
    fixedp={0:'4053',2:'4883EC20',6:'488BD9',16:'83B9E000000000',29:'488B81B8000000'}
    fixedm={0:'48896C2430',5:'4889742438',10:'48897C2440',15:'488B00',18:'4885C0',40:'807B6000',46:'488B7C2440',51:'488B742438',56:'488B6C2430',61:'4883C420',65:'5B',66:'C3'}
    for mapping,fixed in ((p,fixedp),(m,fixedm)):
        for at,raw in fixed.items():require(_raw(mapping[at])==bytes.fromhex(raw),'quest-dirty-clean-frame-field-read',at)
    require(_raw(p[23])[:2]==b'\x0f\x84' and branch_target(p[23]) in owned_starts,'quest-dirty-clean-entry-initializer-edge',p[23])
    require(_raw(m[21])[:2]==b'\x0f\x84','quest-dirty-clean-nonnull-edge',m[21])
    require(_raw(m[34])[:2]==b'\x0f\x8f' and branch_target(m[34]) in owned_starts,'quest-dirty-clean-cache-signed-selection',m[34])
    require(_raw(m[44])[:1]==b'\x75' and branch_target(m[44])==_va(m[67]),'quest-dirty-clean-byte-zero-selection',m[44])
    require(_raw(m[27])[:3]==bytes.fromhex('817818') and len(_raw(m[27]))==7,'quest-dirty-clean-anonymous-cache-lane',m[27])
    path=[r for r in primary if r['offset']>6]+[r for r in main if r['offset']<=40]
    require(all(not r['text'].startswith('call ') for r in path),'quest-dirty-clean-no-calls',path)
    _register_preserved(path,{'rbx'},set())
    require(all(not r['text'].startswith('call ') for r in main if r['offset']<=66),'quest-dirty-clean-return-no-call',None)
    return {'selectedNormalReturnProved':True,'zeroByteFieldOffset':96,'normalPathCalls':0,'completeRefreshMethodProved':False,'nonzeroRefreshAlgorithmProved':False,'runtimeObserved':False}


def clean_return(image,contract,method):
    m,pointer=method;pe=image.pe;table_rva,size,table=read_exception_directory(pe)
    family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(pointer-pe.image_base)
    require(2<=len(family['ranges'])<=8,'quest-dirty-clean-declared-owned-family',len(family['ranges']))
    primary,main=family['ranges'][:2];require(primary['runtimeTriple'][0]==pointer-pe.image_base and primary['codeBytes']==36 and main['codeBytes']>=74,'quest-dirty-clean-owned-prefix',family['ranges'][:2])
    parts=[];windows=[]
    for part,length in ((primary,36),(main,74)):
        begin,end,_=part['runtimeTriple'];raw=pe.bytes_at_va(pe.image_base+begin,length)
        parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
        windows.append({'runtimeTriple':part['runtimeTriple'],'provedPrefixBytes':length,'provedPrefixSha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    proof=check_clean_return(parts,contract['earlyReturnPrograms'],{pe.image_base+p['runtimeTriple'][0] for p in family['ranges']})
    full_parts=[];full_windows=[]
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];require(0<end-begin<=4096,'quest-dirty-clear-bounded-owned-part',part)
        raw=pe.bytes_at_va(pe.image_base+begin,end-begin);full_parts.append(_instruction_partition(raw,pe.image_base+begin,_dirty_decoder(image.mapper)))
        full_windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    clear=check_clear_return(full_parts,contract['clearReturnPrograms']);clear['windows']=full_windows
    proof.update({'methodIndex':m.index,'windows':windows,'clearReturn':clear});return proof


def validate(image,contract,provider):
    md=image.metadata;methods={};specs=dict(contract['methods']);specs['patch']=provider['methods']['patch']
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'quest-dirty-qualified-owner',role)
        m=select_ordinary_overload(image,[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']],spec)
        pointer=image.method_pointer_va(m);require(pointer is not None,'quest-dirty-pointer',role);methods[role]=(m,pointer)
    owner=methods['add'][0].declaring_type;require(owner==methods['remove'][0].declaring_type==methods['cleanReturn'][0].declaring_type,'quest-dirty-same-owner',owner)
    spec=contract['field'];f=_field(image,owner,spec['name'],spec['offset']);_abi(image,f.type_index,spec['type'],'quest-dirty-field')
    proofs=[];extents=image.mapper.pdata_function_extents(image.pe)
    for role in ('add','remove'):
        m,pointer=methods[role];end=extents.get(pointer);require(end is not None and 0<end-pointer<=4096,'quest-dirty-owned-extent',role)
        raw=image.pe.bytes_at_va(pointer,end-pointer);rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper));proof=check_dirty(rows,role,contract['programs'][role],methods['patch'][1])
        proof.update({'role':role,'methodIndex':m.index,'primary':{'rva':pointer-image.pe.image_base,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()},'opaqueCallTargets':[_va(r)+len(_raw(r))+struct.unpack_from('<i',_raw(r),1)[0] for r in rows if r['text'].startswith('call ')]});proofs.append(proof)
    return {'writes':proofs,'cleanReturn':clean_return(image,contract,methods['cleanReturn']),'field':{'index':f.index,'ownerDefinition':owner,'name':spec['name'],'offset':spec['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_pause_dirty')
    provider,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='pause_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-quest-pause-dirty-native-audit.v3','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_pause_dirty_native_latest.json')
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
        print('quest-pause-dirty:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest dirty writes passed: conditional byte one; collection mutation unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
