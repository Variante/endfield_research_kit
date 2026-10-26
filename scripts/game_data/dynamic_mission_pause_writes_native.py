"""Selected typed pause-field byte writes; no live paused state."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_pause_writes_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_mission_pause_writes_native_claims.json'
SCHEMA='endfield.dynamic-mission-pause-writes-native-claims.v1'


def check_write(rows,role,program,methods):
    _grammar(rows,program);by={r['offset']:r for r in rows};byva={_va(r):r for r in rows}
    size={'pause':371,'handle':464}[role];start=_va(rows[0]);end=start
    for row in rows:
        require(_va(row)==end and row['offset']==end-start,'pause-write-complete-partition',row);end+=len(_raw(row))
    require(end-start==size,'pause-write-owned-primary-size',end-start)
    for row in rows:
        if row['text'].startswith(('je ','jne ','jcc ','jmp ')):
            raw=_raw(row)
            require(raw[:1] in (b'\xeb',b'\xe9',b'\x74',b'\x75') or raw[:2] in (b'\x0f\x84',b'\x0f\x85'),
                    'pause-write-admitted-branch-opcode',row)
            require(branch_target(row) in byva,'pause-write-all-owned-instruction-starts',row)
        if row['text'].startswith('call '):require(len(_raw(row))==5 and _raw(row)[0]==0xe8,'pause-write-direct-call-boundary',row)
    if role=='pause':
        fixed=((0,'488BC4'),(3,'48895808'),(7,'48896810'),(11,'48897018'),(15,'48897820'),(19,'4156'),(21,'4883EC30'),
               (32,'418AF8'),(35,'488BDA'),(38,'488BE9'),(103,'33D2'),(112,'84C0'),(134,'4533C9'),
               (137,'41B001'),(140,'488BD3'),(143,'488BCD'),(146,'4C8BF0'),(163,'488BF0'),
               (171,'4D85F6'),(176,'4885C0'),(181,'4885F6'),(186,'C6464001'))
        calls={'patch':107,'lookup':149};selected={114:False,174:False,179:False,184:False};goal=186;save=163
        branch_expect={41:98,114:301,174:263,179:263,184:263}
        init_cmp,init_store=25,91
    else:
        fixed=((0,'48895C2408'),(5,'48896C2410'),(10,'4889742418'),(15,'57'),(16,'4883EC30'),
               (27,'488BDA'),(30,'488BF9'),(95,'33D2'),(104,'84C0'),(112,'4885DB'),
               (121,'488B5318'),(125,'4533C9'),(128,'41B001'),(131,'488BCF'),(139,'488B6B18'),
               (143,'488BF0'),(146,'4885C0'),(155,'4533C0'),(158,'488BD5'),(161,'488BCF'),
               (169,'83F802'),(197,'408AF0'),(301,'8A4320'),(304,'884640'))
        calls={'patch':99,'lookup':134,'state':164};selected={106:False,115:False,149:False,172:True};goal=304;save=143
        branch_expect={33:90,106:406,115:420,149:357,172:301}
        init_cmp,init_store=20,83
    for at,raw in fixed:require(_raw(by[at])==bytes.fromhex(raw),'pause-write-fixed-frame-source-store',at)
    directions={41:'75',114:'0F85',174:'74',179:'74',184:'74'} if role=='pause' else {33:'75',106:'0F85',115:'0F84',149:'0F84',172:'75'}
    for at,target in branch_expect.items():
        require(_raw(by[at]).startswith(bytes.fromhex(directions[at])) and branch_target(by[at])==_va(by[target]),
                'pause-write-selected-owned-edge',(at,target))
    def rip(at):row=by[at];return _va(row)+len(_raw(row))+struct.unpack_from('<i',_raw(row),2)[0]
    require(_raw(by[init_cmp])[:2]==b'\x80\x3d' and _raw(by[init_cmp])[-1:]==b'\0' and
            _raw(by[init_store])[:2]==b'\xc6\x05' and _raw(by[init_store])[-1:]==b'\1' and rip(init_cmp)==rip(init_store),
            'pause-write-same-entry-init-cell',(init_cmp,init_store))
    for name,at in calls.items():require(branch_target(by[at])==methods[name],'pause-write-actual-qualified-call',(name,at))
    paths=[]
    def visit(at,path):
        require(at in by and at not in path and len(path)<150,'pause-write-owned-selected-path',(at,path));path=path+[at];row=by[at]
        if at==goal:paths.append(path);return
        require(row['text'] not in ('int3','ret'),'pause-write-selected-route-before-store',row)
        following=at+len(_raw(row))
        if row['text'].startswith('jmp '):visit(byva[branch_target(row)]['offset'],path)
        elif row['text'].startswith(('je ','jne ','jcc ')):
            target=byva[branch_target(row)]['offset']
            if selected.get(at) is not False:visit(target,path)
            if selected.get(at) is not True:visit(following,path)
        else:visit(following,path)
    visit(0,[]);require(len(paths)==2,'pause-write-two-initialization-selected-paths',len(paths))
    for path in paths:
        watched=[by[at] for at in path if save<at<goal]
        _register_preserved(watched,{'rsi'},{_va(by[at]) for at in path if by[at]['text'].startswith('call ')})
        original=[by[at] for at in path if (35 if role=='pause' else 27)<at<(149 if role=='pause' else 301)]
        _register_preserved(original,{'rbx'},{_va(by[at]) for at in path if by[at]['text'].startswith('call ')})
    return {'selectedWritePaths':len(paths),'write':'constant byte1' if role=='pause' else 'message isPaused_ exact byte copied',
            'normalizedBooleanByteProved':False,'fullNormalReturnProved':False,'runtimeObserved':False,
            'predicateGetterAndWrittenDataSameObjectProved':False,'RSIpreservedOnStorePaths':True,
            'excludedHandleState2SILClobber':role=='handle'}


def validate(image,contract,stored,provider):
    md=image.metadata;pe=image.pe;specs=dict(contract['methods']);specs.update({'lookup':stored['methods']['lookup'],
                  'state':stored['methods']['getter'],'patch':provider['methods']['patch']});methods={};defs={}
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and
                md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'pause-write-qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        require(len(candidates)==1,'pause-write-qualified-method-'+role,len(candidates));m=candidates[0];params=md.parameters_for(m)
        require(bool(m.flags&0x10)==(spec['callAbi']=='static') and len(params)==len(spec['parameters']),
                'pause-write-call-role-'+role,(m.flags,len(params)))
        if role=='lookup':defs['data']=_class(image,m.return_type);require(md.type_full_name(md.types[defs['data']])==spec['returnType'],'pause-write-data-definition',defs)
        elif role=='state':defs['state']=_enum(image,m.return_type,spec['returnType'])
        else:_abi(image,m.return_type,spec['returnType'],'pause-write-return-'+role)
        for param,token in zip(params,spec['parameters']):
            if token.startswith('Proto.'):
                defs['message']=_class(image,param.type_index)
                require(md.type_full_name(md.types[defs['message']])==token,'pause-write-message-definition',defs['message'])
            else:_abi(image,param.type_index,token,'pause-write-parameter-'+role)
        pointer=image.method_pointer_va(m);require(pointer is not None,'pause-write-actual-pointer-'+role,pointer);methods[role]=(m,pointer)
    require(len({methods[r][0].declaring_type for r in ('pause','handle','lookup','state')})==1,'pause-write-same-system-owner',methods)
    fields={}
    for role,owner,token in (('dataPaused',defs['data'],'Boolean'),('messageKey',defs['message'],'String'),('messagePaused',defs['message'],'Boolean')):
        spec=contract['fields'][role];f=_field(image,owner,spec['name'],spec['offset']);_abi(image,f.type_index,token,'pause-write-field-'+role)
        fields[role]={'index':f.index,'ownerDefinition':owner,'name':spec['name'],'offset':spec['offset'],
                      'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    extents=image.mapper.pdata_function_extents(pe);proofs=[]
    for role in ('pause','handle'):
        m,pointer=methods[role];end=extents.get(pointer);require(end is not None and 0<end-pointer<=4096,'pause-write-bounded-owned-primary',role)
        raw=pe.bytes_at_va(pointer,end-pointer);rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper))
        proof=check_write(rows,role,contract['programs'][role],{name:pair[1] for name,pair in methods.items()})
        proof.update({'role':role,'methodIndex':m.index,'primary':{'rva':pointer-pe.image_base,'bytes':len(raw),
                      'sha256':hashlib.sha256(raw).hexdigest().upper()}});proofs.append(proof)
    return {'writes':proofs,'fields':fields,'methods':{role:{'index':m.index,'rva':va-pe.image_base,'ownerDefinition':m.declaring_type}
                 for role,(m,va) in methods.items()},'stateReturnEnumDefinition':defs['state']}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_pause_writes')
    stored,provider=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='pause_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,stored,provider)
    return {'format':'endfield.dynamic-mission-pause-writes-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_pause_writes_native_latest.json')
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
        print('mission-pause-writes:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission pause writes passed: selected typed byte stores; live state/network effects unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
