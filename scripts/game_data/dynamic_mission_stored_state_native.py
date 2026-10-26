"""Typed returned MissionData state-field reads; no live state."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_stored_state_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_mission_stored_state_native_claims.json'
SCHEMA='endfield.dynamic-mission-stored-state-native-claims.v1'


def check_getter(primary,cold,programs,patch_pointer,lookup_pointer):
    _grammar(primary,programs['primary']);_grammar(cold,programs['cold'])
    p={r['offset']:r for r in primary};c={r['offset']:r for r in cold}
    for rows,size in ((primary,83),(cold,46)):
        start=_va(rows[0]);end=start
        for row in rows:
            require(_va(row)==end and row['offset']==end-start,'stored-state-complete-partition',row)
            end+=len(_raw(row))
        require(end-start==size,'stored-state-complete-program-size',end-start)
    for at,raw in ((0,'48895C2408'),(5,'57'),(6,'4883EC20'),(10,'488BDA'),(13,'488BF9'),
                   (16,'33D2'),(28,'84C0'),(36,'4533C9'),(39,'4533C0'),(42,'488BD3'),
                   (45,'488BCF'),(53,'4885C0'),(58,'8B4018'),(61,'488B5C2430'),
                   (66,'4883C420'),(70,'5F'),(71,'C3'),(72,'488B5C2430'),(77,'4883C420'),(81,'5F'),(82,'C3')):
        require(_raw(p[at])==bytes.fromhex(raw),'stored-state-fixed-entry-arguments-return',at)
    for row,raw,target in ((p[30],'0F85',c[0]),(p[56],'74',p[72]),(c[15],'75',c[23]),(c[41],'E9',p[61])):
        require(_raw(row).startswith(bytes.fromhex(raw)) and branch_target(row)==_va(target),
                'stored-state-owned-branch-start',(row,target))
    require(_raw(c[17])[0]==0xe8 and len(_raw(c[17]))==5 and _raw(c[22])==b'\xcc',
            'stored-state-excluded-null-exception',c[17])
    for rows,expected in ((primary,{23,48}),(cold,{7,17,35})):
        require({r['offset'] for r in rows if r['text'].startswith('call ')}==expected,'stored-state-all-call-boundaries',expected)
        for row in rows:
            if row['offset'] in expected:require(len(_raw(row))==5 and _raw(row)[0]==0xe8,'stored-state-direct-call',row)
    require(branch_target(p[23])==patch_pointer and branch_target(p[48])==lookup_pointer,
            'stored-state-actual-qualified-calls',(p[23],p[48]))
    _register_preserved([r for r in primary if 13<r['offset']<48],{'rdi','rbx'},{_va(p[23])})
    # The exact closed epilogues write only RBX/SP/RDI: null RAX therefore retains EAX=0,
    # while the nonnull DWORD field load is the only EAX write until normal RET.
    for begin,end in ((61,71),(72,82)):
        for row in primary:
            if begin<=row['offset']<=end:
                require((row.get('write') or {}).get('register') not in {'rax','eax','ax','al','ah'},
                        'stored-state-return-value-preserved',row)
    return {'selectedNormalReturns':2,'nonnullReturn':'ordinary declared enum field DWORD read',
            'nullReturnBits':0,'lookupBooleanArgument':False,'runtimeObserved':False,
            'lookupImplementationProved':False,'callerSavedFrameRanges':[[32,40],[48,56]],'returnAddressRange':[40,48]}


def validate(image,contract,provider):
    md=image.metadata;pe=image.pe;methods={};definitions={}
    specs=dict(contract['methods']);specs['patch']=provider['methods']['patch']
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and
                md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'stored-state-qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role=='patch':m=select_ordinary_overload(image,candidates,spec)
        else:
            require(len(candidates)==1,'stored-state-method-unique-'+role,len(candidates));m=candidates[0]
            params=md.parameters_for(m)
            require(not m.flags&0x10 and len(params)==len(spec['parameters']),'stored-state-instance-arity-'+role,m.flags)
            for param,token in zip(params,spec['parameters']):_abi(image,param.type_index,token,'stored-state-parameter-'+role)
            definition=_enum(image,m.return_type,spec['returnType']) if role=='getter' else _class(image,m.return_type)
            require(md.type_full_name(md.types[definition])==spec['returnType'],'stored-state-return-definition-'+role,definition)
            definitions[role]=definition
        pointer=image.method_pointer_va(m);require(pointer is not None,'stored-state-actual-pointer-'+role,pointer)
        methods[role]=(m,pointer)
    require(methods['getter'][0].declaring_type==methods['lookup'][0].declaring_type,'stored-state-same-receiver-definition',methods)
    field_spec=contract['returnedField'];field=_field(image,definitions['lookup'],field_spec['name'],field_spec['offset'])
    enum=_enum(image,field.type_index,contract['methods']['getter']['returnType'])
    require(enum==definitions['getter'],'stored-state-field-return-same-enum-definition',(enum,definitions))
    table_rva,size,raw_table=read_exception_directory(pe)
    unwind=UnwindChainIndex(raw_table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size)
    pointer=methods['getter'][1];family=unwind.family(pointer-pe.image_base)
    require(len(family['ranges'])==2 and sum(p['codeBytes'] for p in family['ranges'])==129,
            'stored-state-bounded-owned-family',family['ranges'])
    parts=[];bodies=[]
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];raw=pe.bytes_at_va(pe.image_base+begin,end-begin)
        parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
        bodies.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()})
    require(_va(parts[0][0])==pointer,'stored-state-primary-family-start',parts)
    proof=check_getter(parts[0],parts[1],contract['programs'],methods['patch'][1],methods['lookup'][1])
    proof.update({'methods':{role:{'index':m.index,'rva':va-pe.image_base,'ownerDefinition':m.declaring_type}
                 for role,(m,va) in methods.items()},'returnedClassDefinition':definitions['lookup'],
                 'enumDefinition':enum,'returnedField':{'index':field.index,'name':field_spec['name'],'offset':field_spec['offset'],
                 'rawTypeHex':_type_record(image,field.type_index).hex().upper()},'ownedBodies':bodies})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_stored_state')
    dependency=contract['dependencies'][0]
    provider,_=read_reviewed_contract(CONTRACTS_DIR/dependency['path'],schema=dependency['schema'],status='reviewed',label='mission_stored_state_provider')
    for item in contract['dependencies'][1:]:
        read_reviewed_contract(CONTRACTS_DIR/item['path'],schema=item['schema'],status=item['status'],label='stored_state_dependency')
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-mission-stored-state-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_stored_state_native_latest.json')
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
        print('mission-stored-state:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission stored state passed: typed returned field/null default; live state unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
