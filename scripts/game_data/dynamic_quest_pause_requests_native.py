"""Selected typed Quest pause requests; no live state or mutation."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_pause_requests_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_quest_pause_requests_native_claims.json'
SCHEMA='endfield.dynamic-quest-pause-requests-native-claims.v1'


def check_requests(rows,role,program,methods):
    _grammar(rows,program);by={r['offset']:r for r in rows};byva={_va(r):r for r in rows}
    start=_va(rows[0]);cursor=0
    for row in rows:
        raw=_raw(row);require(row['offset']==cursor and _va(row)==start+cursor and raw,'quest-pause-partition',row);cursor+=len(raw)
        require(not row['text'].startswith(('db','unknown','ff/')),'quest-pause-recognized',row)
        if row['text'].startswith(('je ','jne ','jcc ','jmp ')):
            require(raw[:1] in (b'\x74',b'\x75',b'\xeb',b'\xe9') or raw[:2] in (b'\x0f\x84',b'\x0f\x85'),'quest-pause-branch-opcode',row)
            require(branch_target(row) in byva,'quest-pause-owned-branch-start',row)
        if row['text'].startswith('call '):require(len(raw)==5 and raw[0]==0xe8,'quest-pause-direct-call-boundary',row)
    require(cursor=={'pause':99,'handle':333}[role],'quest-pause-owned-size',cursor)
    fixed={'pause':[(0,'48895C2408'),(5,'57'),(6,'4883EC20'),(10,'488BDA'),(13,'488BF9'),(16,'33D2'),(28,'84C0'),(32,'4533C0'),(35,'488BD3'),(38,'488BCF'),(88,'488B5C2430'),(93,'4883C420'),(97,'5F'),(98,'C3')],
           'handle':[(0,'48895C2408'),(5,'4889742410'),(10,'57'),(11,'4883EC20'),(22,'488BDA'),(25,'488BF9'),(49,'488364244800'),(60,'8BCE'),(62,'33D2'),(69,'84C0'),(77,'4885DB'),(86,'488BCF'),(89,'488B5318'),(93,'384320'),(98,'4533C9'),(101,'4533C0'),(111,'4533C0')]}[role]
    for at,raw in fixed:require(_raw(by[at])==bytes.fromhex(raw),'quest-pause-frame-typed-args',at)
    edges={30:('75',48),46:('EB',88)} if role=='pause' else {28:('75',49),71:('0F85',280),80:('0F84',294),96:('75',111),109:('EB',119)}
    for at,(opcode,target) in edges.items():require(_raw(by[at]).startswith(bytes.fromhex(opcode)) and branch_target(by[at])==_va(by[target]),'quest-pause-selected-edge',(at,target))
    calls={'patch':23,'stop':41} if role=='pause' else {'patch':64,'start':104,'pause':114}
    for name,at in calls.items():require(branch_target(by[at])==methods[name],'quest-pause-actual-qualified-call',(name,at))
    if role=='handle':
        cmp,store=by[15],by[42]
        require(_raw(cmp)[:2]==b'\x80\x3d' and _raw(cmp)[-1:]==b'\0' and _raw(store)[:2]==b'\xc6\x05' and _raw(store)[-1:]==b'\1' and
                _va(cmp)+len(_raw(cmp))+struct.unpack_from('<i',_raw(cmp),2)[0]==_va(store)+len(_raw(store))+struct.unpack_from('<i',_raw(store),2)[0],'quest-pause-init-cell',None)
        for row in rows:
            if 69<row['offset']<93:
                require((row.get('write') or {}).get('register') not in {'rax','eax','ax','al','ah'} and not row['text'].startswith('call '),'quest-pause-false-result-AL-preserved',row)
    paths=[]
    def visit(at,path):
        require(at in by and at not in path and len(path)<100,'quest-pause-selected-path',at);path=path+[at];row=by[at]
        if at==(98 if role=='pause' else 119):paths.append(path);return
        require(row['text'] not in ('ret','int3'),'quest-pause-premature-stop',row)
        nxt=at+len(_raw(row));selected={30:False} if role=='pause' else {71:False,80:False}
        if row['text'].startswith('jmp '):visit(byva[branch_target(row)]['offset'],path)
        elif row['text'].startswith(('je ','jne ','jcc ')):
            if selected.get(at) is not False:visit(byva[branch_target(row)]['offset'],path)
            if selected.get(at) is not True:visit(nxt,path)
        else:visit(nxt,path)
    visit(0,[]);require(len(paths)==(1 if role=='pause' else 4),'quest-pause-path-count',len(paths))
    for path in paths:
        stop=41 if role=='pause' else (104 if 104 in path else 114)
        watched=[by[a] for a in path if (13 if role=='pause' else 25)<a<stop]
        _register_preserved(watched,{'rbx','rdi'},{_va(r) for r in watched if r['text'].startswith('call ')})
    return {'selectedPaths':len(paths),'normalReturnProved':role=='pause','handlerPrefixOnly':role=='handle',
            'zeroMessageByteRequestsStartQuestFalse':role=='handle','nonzeroMessageByteRequestsPauseQuest':role=='handle',
            'messageBooleanNormalizationProved':False,'runtimeStateProved':False,'collectionMutationProved':False}


def validate(image,contract,provider):
    md=image.metadata;specs=dict(contract['methods']);specs['patch']=provider['methods']['patch'];methods={};message=None
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'quest-pause-qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role=='handle':
            require(len(candidates)==1,'quest-pause-message-method',len(candidates));m=candidates[0];params=md.parameters_for(m)
            require(not m.flags&0x10 and len(params)==1,'quest-pause-message-instance-ABI',m.flags);_abi(image,m.return_type,'Void','handler-return')
            message=_class(image,params[0].type_index);require(md.type_full_name(md.types[message])==spec['parameters'][0],'quest-pause-concrete-message',message)
        else:m=select_ordinary_overload(image,candidates,spec)
        pointer=image.method_pointer_va(m);require(pointer is not None,'quest-pause-selected-pointer',role);methods[role]=(m,pointer)
    require(len({methods[r][0].declaring_type for r in ('pause','handle','stop','start')})==1,'quest-pause-same-concrete-system',None)
    fields={}
    for role,token in (('messageKey','String'),('messagePaused','Boolean')):
        spec=contract['fields'][role];f=_field(image,message,spec['name'],spec['offset']);_abi(image,f.type_index,token,'quest-pause-message-field')
        fields[role]={'index':f.index,'ownerDefinition':message,'name':spec['name'],'offset':spec['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    extents=image.mapper.pdata_function_extents(image.pe);proofs=[]
    for role in ('pause','handle'):
        m,pointer=methods[role];end=extents.get(pointer);require(end is not None and 0<end-pointer<=4096,'quest-pause-owned-extent',role)
        raw=image.pe.bytes_at_va(pointer,end-pointer);rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper))
        proof=check_requests(rows,role,contract['programs'][role],{r:p for r,(_,p) in methods.items()})
        proof.update({'role':role,'methodIndex':m.index,'primary':{'rva':pointer-image.pe.image_base,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()}});proofs.append(proof)
    return {'requests':proofs,'fields':fields,'methods':{r:{'index':m.index,'rva':p-image.pe.image_base,'ownerDefinition':m.declaring_type} for r,(m,p) in methods.items()}}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_pause_requests')
    provider,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='pause_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-quest-pause-requests-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_pause_requests_native_latest.json')
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
        print('quest-pause-requests:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest pause requests passed: typed dispatch; live state and mutation unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
