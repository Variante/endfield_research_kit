"""Selected typed display-list return; opaque refresh implementation."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_display_list_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_quest_display_list_native_claims.json'
SCHEMA='endfield.dynamic-quest-display-list-native-claims.v1'


def check_return(parts,programs,patch,refresh):
    require(len(parts)==len(programs)==2,'quest-display-two-owned-parts',len(parts))
    for rows,program,size in zip(parts,programs,(49,41)):
        _grammar(rows,program);cursor=0;start=_va(rows[0])
        for row in rows:
            raw=_raw(row);require(row['offset']==cursor and _va(row)==start+cursor and raw and not row['text'].startswith(('db','unknown','ff/')),'quest-display-complete-partition',row);cursor+=len(raw)
            if row['text'].startswith('call '):require(len(raw)==5 and raw[0]==0xe8,'quest-display-direct-call',row)
        require(cursor==size,'quest-display-owned-size',cursor)
    primary,cold=parts;by={r['offset']:r for r in primary}
    fixed={0:'4053',2:'4883EC20',6:'488BD9',9:'33D2',21:'33D2',23:'84C0',31:'488BCB',39:'488B4358',43:'4883C420',47:'5B',48:'C3'}
    for at,raw in fixed.items():require(_raw(by[at])==bytes.fromhex(raw),'quest-display-frame-source-return',at)
    require(_raw(by[25])[:2]==b'\x0f\x85' and branch_target(by[25])==_va(cold[0]),'quest-display-false-patch-owned-edge',by[25])
    require(branch_target(by[16])==patch and branch_target(by[34])==refresh,'quest-display-qualified-calls',None)
    _register_preserved([r for r in primary if 6<r['offset']<39],{'rbx'},{_va(by[16]),_va(by[34])})
    return {'selectedNormalReturnProved':True,'returnedInstanceFieldOffset':88,'runtimeObserved':False,'refreshAlgorithmProved':False,'listMutationProved':False}


def list_type(image,type_index):
    selected=NativeReferenceContext(image);extent=closed_generic_reference_extent(selected,type_index)
    require(extent['type']=='System.Collections.Generic.List`1<string>' and extent['argumentTypes']==['string'],'quest-display-closed-List-String',extent)
    raw=_type_record(image,type_index);carrier=image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16);inst=image.pe.bytes_at_va(int.from_bytes(carrier[8:16],'little'),16)
    count,argv=struct.unpack('<QQ',inst);require(count==1,'quest-display-string-arity',count)
    pointer=image.pe.u64_at_va(argv);arg=image.pe.bytes_at_va(pointer,16)
    require(len(arg)==16 and arg[10]==0x0e and arg[11]==0,'quest-display-ordinary-String-argument',arg.hex())
    return extent,raw[:8]


def validate(image,contract,provider):
    md=image.metadata;methods={};specs=dict(contract['methods']);specs['patch']=provider['methods']['patch'];returned=None
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'quest-display-qualified-owner',role);candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role=='getter':
            require(len(candidates)==1,'quest-display-unique-getter',len(candidates));m=candidates[0];require(not m.flags&0x10 and not md.parameters_for(m),'quest-display-instance-getter',m.flags);returned=list_type(image,m.return_type)
        else:m=select_ordinary_overload(image,candidates,spec)
        pointer=image.method_pointer_va(m);require(pointer is not None,'quest-display-pointer',role);methods[role]=(m,pointer)
    owner=methods['getter'][0].declaring_type;require(owner==methods['refresh'][0].declaring_type,'quest-display-same-concrete-owner',owner)
    spec=contract['field'];f=_field(image,owner,spec['name'],spec['offset']);field_type=list_type(image,f.type_index)
    require(field_type[0]['definitionTypeIndex']==returned[0]['definitionTypeIndex'] and field_type[1]==returned[1],'quest-display-return-field-same-closed-identity',None)
    table_rva,size,table=read_exception_directory(image.pe);unwind=UnwindChainIndex(table,lambda rva,n:image.pe.bytes_at_va(image.pe.image_base+rva,n),table_rva=table_rva,image_size=size)
    pointer=methods['getter'][1];family=unwind.family(pointer-image.pe.image_base);require(len(family['ranges'])==2,'quest-display-owned-family',len(family['ranges']))
    parts=[];windows=[]
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];require(0<end-begin<=256,'quest-display-bounded-part',part)
        raw=image.pe.bytes_at_va(image.pe.image_base+begin,end-begin);parts.append(_instruction_partition(raw,image.pe.image_base+begin,_composed_decoder(image.mapper)))
        windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    require(family['ranges'][0]['runtimeTriple'][0]==pointer-image.pe.image_base,'quest-display-primary-first',None)
    proof=check_return(parts,contract['programs'],methods['patch'][1],methods['refresh'][1])
    proof.update({'windows':windows,'field':{'index':f.index,'name':spec['name'],'offset':spec['offset'],'ownerDefinition':owner},'returnedReference':returned[0],'fieldReference':field_type[0],
                  'methods':{r:{'index':m.index,'rva':p-image.pe.image_base,'ownerDefinition':m.declaring_type} for r,(m,p) in methods.items()}})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_display_list')
    provider,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='pause_write_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-quest-display-list-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_display_list_native_latest.json')
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
        print('quest-display-list:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest display-list return passed: typed field pointer; refresh algorithm unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
