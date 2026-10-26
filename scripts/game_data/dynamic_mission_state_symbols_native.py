"""Typed Mission/Quest enum metadata declarations; no live state."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_state_symbols_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, dictionary_context, _register_preserved, select_ordinary_overload)
from scripts.game_data.dynamic_mission_state_cache_native import _enum
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_mission_state_symbols_native_claims.json'
SCHEMA='endfield.dynamic-mission-state-symbols-native-claims.v1'


from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members

def declared_members(image,definition,type_name,defaults):
    md=image.metadata;pe=image.pe
    owners=[td for td in md.types if md.type_full_name(td)==type_name]
    require(len(owners)==1 and owners[0].index==definition,'state-symbols-unique-concrete-enum-owner',len(owners))
    expected=[];provenance=[]
    for field in md.fields_for(owners[0]):
        if md.string(field.name_index)=='value__':continue
        raw=_type_record(image,field.type_index);attrs=int.from_bytes(raw[8:10],'little')
        require(attrs&0x50==0x50 and raw[10]==0x11 and raw[11]&0x7f==0 and struct.unpack_from('<Q',raw)[0]==definition,
                'state-symbols-own-static-default-field',(field.index,raw.hex()))
        entry=defaults.get(field.index);require(entry is not None,'state-symbols-default-required',field.index)
        _abi(image,entry[0],'Int32','state-symbols-default-ordinary-Int32')
        expected.append(field.index)
        provenance.append({'fieldIndex':field.index,'rawTypeHex':raw.hex().upper(),'defaultTypeIndex':entry[0],
                           'defaultDataIndex':entry[1],'defaultRawTypeHex':_type_record(image,entry[0]).hex().upper()})
    members=native_enum_members(md,defaults,pe,image.registration,type_name)
    require(len(members)==len(expected) and {m['fieldIndex'] for m in members}==set(expected),
            'state-symbols-exact-member-roster',members)
    return {'type':type_name,'definition':definition,'members':members,'memberSources':provenance,
            'runtimeObserved':False,'aliasesDiscarded':False}


def validate(image,contract,cache):
    md=image.metadata;defaults=field_defaults(md);proofs=[]
    for role in contract['methodRoles']:
        require(role in ('missionState','questState'),'state-symbols-supported-return-role',role)
        spec=cache['methods'][role]
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and
                md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'state-symbols-qualified-getter-owner',len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        require(len(candidates)==1,'state-symbols-qualified-getter-unique',len(candidates));method=candidates[0]
        params=md.parameters_for(method)
        require(not method.flags&0x10 and spec['callAbi']=='instance' and len(params)==len(spec['parameters']),
                'state-symbols-getter-instance-arity',method.flags)
        for param,token in zip(params,spec['parameters']):_abi(image,param.type_index,token,'state-symbols-getter-parameter')
        definition=_enum(image,method.return_type,spec['returnType'])
        pointer=image.method_pointer_va(method);require(pointer is not None,'state-symbols-getter-actual-pointer',method.index)
        proof=declared_members(image,definition,spec['returnType'],defaults)
        proof.update({'role':role,'getter':{'index':method.index,'rva':pointer-image.pe.image_base,
                      'ownerDefinition':method.declaring_type,'rawReturnTypeHex':_type_record(image,method.return_type).hex().upper()}})
        proofs.append(proof)
    require(len(proofs)==2 and len({p['role'] for p in proofs})==2,'state-symbols-role-roster',proofs)
    return {'enumDeclarations':proofs,'sourceAssociationProved':False,'queryDefaultIsObservedEnum':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_state_symbols')
    dependency=contract['dependencies'][0]
    provider,_=read_reviewed_contract(CONTRACTS_DIR/dependency['path'],schema=dependency['schema'],status='reviewed',label='mission_state_symbols_provider')
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-mission-state-symbols-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_state_symbols_native_latest.json')
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
        print('mission-state-symbols:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission state symbols passed: typed declarations; runtime/source classifications unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
