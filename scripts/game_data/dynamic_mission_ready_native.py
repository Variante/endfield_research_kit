"""Names-based selected ready request; no stored/live readiness claim."""
from __future__ import annotations
import argparse
import sys
import hashlib
import json
import struct
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_ready_native')

from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.body_claims import BodyIndex, Body, check_claim
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.dynamic_erosion_consumers_native import (_ordinary_primitive_abi, _raw_type_abi,
    _instruction_partition, _preserved_interval, PRIMITIVE_TYPE_CODES)
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder

def branch_target(row):
    raw=bytes.fromhex(row['bytes']);va=int(row['va'],16)
    if len(raw)==2 and raw[0] in (0x74,0x75,0xeb):return va+2+struct.unpack('<b',raw[1:])[0]
    if len(raw)==6 and raw[:2] in (b'\x0f\x84',b'\x0f\x85'):return va+6+struct.unpack('<i',raw[2:])[0]
    if len(raw)==5 and raw[0] in (0xe8,0xe9):return va+5+struct.unpack('<i',raw[1:])[0]
    raise ValueError('mission-ready:unsupported direct branch '+str(row)[:400])

def reference_definition(image,type_index,expected):
    bits=_raw_type_abi(image,type_index,'mission-ready-reference')
    _require((bits>>16)&0xff==0x12 and bits>>24==0,'mission-ready-reference-ABI','ordinary class reference',f'{bits:08X}')
    pointer=image.pe.u64_at_va(int(image.registration['types'],16)+type_index*8)
    definition=struct.unpack_from('<Q',image.pe.bytes_at_va(pointer,16))[0]
    _require(0<=definition<len(image.metadata.types),'mission-ready-reference-owner','bounded concrete owner',definition)
    _require(image.metadata.type_full_name(image.metadata.types[definition])==expected,
             'mission-ready-reference-type',expected,image.metadata.type_full_name(image.metadata.types[definition]))
    return definition

def select_methods(image,index,contract):
    methods={};bodies={};extents=image.mapper.pdata_function_extents(image.pe)
    for role,spec in contract['methods'].items():
        owners=[owner for owner in image.metadata.types if image.metadata.type_full_name(owner)==spec['type'] and
            image.metadata.string(image.metadata.images[image.owners[owner.index]].name_index)==spec['image']]
        _require(len(owners)==1,'mission-ready-owner-'+role,'one assembly-qualified concrete owner',len(owners))
        owner=owners[0]
        candidates=[method for method in image.metadata.methods_for(owner)
            if image.metadata.string(method.name_index)==spec['method']]
        _require(len(candidates)==1,'mission-ready-method-'+role,'one concrete named method',len(candidates))
        method=candidates[0];params=image.metadata.parameters_for(method)
        _require([image.metadata.metadata_type_name(p.type_index) for p in params]==spec['parameters'] and
                 image.metadata.metadata_type_name(method.return_type)==spec['returnType'],
                 'mission-ready-signature-'+role,spec,(method.return_type,[p.type_index for p in params]))
        _require(('static' if method.flags&0x10 else 'instance')==spec['callAbi'],
                 'mission-ready-role-'+role,spec['callAbi'],method.flags)
        if spec['returnType'] in PRIMITIVE_TYPE_CODES:
            _ordinary_primitive_abi(image,method.return_type,PRIMITIVE_TYPE_CODES[spec['returnType']],role+'-return')
        for param,expected in zip(params,spec['parameters']):
            _ordinary_primitive_abi(image,param.type_index,PRIMITIVE_TYPE_CODES[expected],role+'-parameter')
        pointer=image.method_pointer_va(method)
        _require(pointer is not None,'mission-ready-pointer-'+role,'selected native pointer',pointer)
        methods[role]=(method,pointer)
        if role in ('ready','getter'):
            end=extents.get(pointer)
            _require(end is not None and 0<end-pointer<=4096,'mission-ready-primary-'+role,'bounded pdata extent',end)
            raw=image.pe.bytes_at_va(pointer,end-pointer)
            rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper))
            bodies[role]=Body(spec['type']+'.'+spec['method'],pointer,len(raw),hashlib.sha256(raw).hexdigest().upper(),rows)
    return methods,bodies

def check_ready_request(ready,getter,methods,field_offset):
    rows=ready.rows
    _require([row['bytes'] for row in rows[:3]]==['40 53','48 83 ec 20','48 8b d9'],
             'mission-ready-frame','ordinary preserved-RBX Win64 frame',[r['bytes'] for r in rows[:3]])
    def named_calls(pointer):return [at for at,row in enumerate(rows) if row['text'].startswith('call ') and branch_target(row)==pointer]
    patch=named_calls(methods['patch'][1]);player=named_calls(methods['player'][1])
    _require(len(patch)==len(player)==1,'mission-ready-calls','one patch check and one player request',(patch,player))
    patch_at=patch[0];p=player[0]
    _require(patch_at==5 and p==12,'mission-ready-prefix-call-slots','closed entry-to-request grammar',(patch_at,p))
    _require(rows[3]['bytes']=='33 d2' and len(bytes.fromhex(rows[4]['bytes']))==5 and
             bytes.fromhex(rows[4]['bytes'])[0]==0xb9 and
             len(bytes.fromhex(rows[8]['bytes']))==7 and bytes.fromhex(rows[8]['bytes'])[:3]==b'\x48\x8b\x0d' and
             rows[9]['bytes']=='83 b9 e0 00 00 00 00' and rows[10]['text'].startswith('je '),
             'mission-ready-prefix-program','continuous patch/initialization/player prefix',rows[3:13])
    _require(rows[patch_at+1]['bytes']=='84 c0' and bytes.fromhex(rows[patch_at+2]['bytes'])[:2]==b'\x0f\x85' and
             not ready.pointer<=branch_target(rows[patch_at+2])<ready.pointer+ready.size,
             'mission-ready-patch-route','false AL falls through; replacement outside primary',rows[patch_at:patch_at+3])
    _require(rows[p-1]['bytes']=='33 c9','mission-ready-static-player-request','zero metadata argument',rows[p-1])
    initialization_target=branch_target(rows[10])
    initialization=[row for row in rows if int(row['va'],16)==initialization_target]
    _require(len(initialization)==1 and initialization[0]['text'].startswith('call '),
             'mission-ready-initialization-boundary','owned direct call instruction',initialization_target)
    init_at=rows.index(initialization[0])
    _require(init_at+1<len(rows) and rows[init_at+1]['text'].startswith('jmp ') and
             branch_target(rows[init_at+1])==int(rows[p-1]['va'],16),
             'mission-ready-initialization-return','return to the same player request',rows[init_at:init_at+2])
    selected=rows[p+1:p+10]
    _require(len(selected)==9,'mission-ready-tail-span',9,len(selected))
    _require(selected[0]['bytes']=='48 85 c0' and selected[1]['text'].startswith('je ') and
             selected[2]['bytes']==('48 8b 88 '+struct.pack('<i',field_offset).hex(' ')) and
             selected[3]['bytes']=='48 85 c9' and selected[4]['text'].startswith('je '),
             'mission-ready-typed-nonnull','nonnull RAX player and same typed RCX mission receiver',selected[:5])
    exceptional=branch_target(selected[1])
    _require(exceptional==branch_target(selected[4]),'mission-ready-null-target','same non-value-returning path',exceptional)
    tail=selected[5:]
    _require([row['bytes'] for row in tail[:3]]==['33 d2','48 83 c4 20','5b'] and
             tail[3]['text'].startswith('jmp ') and branch_target(tail[3])==getter.pointer,
             'mission-ready-tail-frame','same receiver passed after frame restoration',tail)
    _preserved_interval(rows,selected[2]['offset']+len(bytes.fromhex(selected[2]['bytes'])),tail[3]['offset'],
                        'rcx',set(),'mission-ready-tail-receiver')
    failure=[row for row in rows if int(row['va'],16)>=exceptional]
    _require(len(failure)==2 and int(failure[0]['va'],16)==exceptional and
             failure[0]['text'].startswith('call ') and failure[1]['bytes']=='cc',
             'mission-ready-null-terminal','opaque helper followed by int3',failure)
    return {'receiver':'Beyond.Gameplay.GamePlayer.mission','getter':'Beyond.Gameplay.MissionSystem.get_missionSystemReady',
            'storedReadinessFieldRead':False,'runtimeObserved':False}

def check_getter_entry(getter,patch_pointer):
    getter_patch=[row for row in getter.rows if row['text'].startswith('call ') and branch_target(row)==patch_pointer]
    _require(len(getter_patch)==1,'mission-ready-getter-concrete-patch','same assembly-qualified IsPatched',getter_patch)
    getter_rows=getter.rows
    _require(len(getter_rows)==12 and [row['bytes'] for row in getter_rows[:4]]==
             ['40 53','48 83 ec 20','48 8b d9','33 d2'] and
             len(bytes.fromhex(getter_rows[4]['bytes']))==5 and bytes.fromhex(getter_rows[4]['bytes'])[0]==0xb9 and
             getter_rows[5] is getter_patch[0] and [row['bytes'] for row in getter_rows[9:]]==['48 83 c4 20','5b','c3'],
             'mission-ready-getter-entry-frame','closed entry-to-patch and balanced returning frame',getter_rows)


def validate(image,contract):
    index=BodyIndex(image);methods,bodies=select_methods(image,index,contract)
    player=reference_definition(image,methods['player'][0].return_type,contract['receiverField']['owner'])
    owner=image.metadata.types[player];fields=[field for field in image.metadata.fields_for(owner)
        if image.metadata.string(field.name_index)==contract['receiverField']['field']]
    _require(len(fields)==1,'mission-ready-field','one concrete mission field',len(fields))
    receiver_definition=reference_definition(image,fields[0].type_index,contract['receiverField']['type'])
    _require(receiver_definition==methods['getter'][0].declaring_type,
             'mission-ready-concrete-tail-owner','field definition equals actual getter declaring type',receiver_definition)
    offset=runtime_type_field_offsets(image.metadata,image.pe,image.registration,player)[contract['receiverField']['field']]
    for claim in contract['getterClaims']:
        result=check_claim(index,bodies['getter'],claim)
        _require(result is None,'mission-ready-getter-claim',claim,result)
    check_getter_entry(bodies['getter'],methods['patch'][1])
    proof=check_ready_request(bodies['ready'],bodies['getter'],methods,offset)
    proof['receiver']=contract['receiverField']['owner']+'.'+contract['receiverField']['field']
    proof['getter']=contract['methods']['getter']['type']+'.'+contract['methods']['getter']['method']
    constants=[claim['returnsAfterFalseCall']['value'] for claim in contract['getterClaims'] if 'returnsAfterFalseCall' in claim]
    _require(len(constants)==1,'mission-ready-return-claim','one proved Boolean constant',constants)
    proof['normalNonReplacementReturn']=bool(constants[0])
    proof['receiverFieldOffset']=offset
    proof['methods']={role:{'methodIndex':method.index,'image':contract['methods'][role]['image'],
        'bodyRva':pointer-image.pe.image_base,
        **({'primaryExtent':bodies[role].size,'bodySha256':hashlib.sha256(b''.join(bytes.fromhex(row['bytes']) for row in bodies[role].rows)).hexdigest().upper()}
           if role in bodies else {})} for role,(method,pointer) in methods.items()}
    return proof


from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT

CONTRACT=CONTRACTS_DIR/'dynamic_mission_ready_native_claims.json'
SCHEMA='endfield.dynamic-mission-ready-native-claims.v1'

def _require(condition,check,expected,actual):
    if not condition:
        raise ValueError(f'mission_ready:{check}:expected={str(expected)[:320]} actual={str(actual)[:320]}')

def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_ready')
    by_name={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by_name['GameAssembly.dll']['sha256'],by_name['global-metadata.dat']['sha256'],
        gameassembly=gameassembly,metadata=metadata)
    _require(gate.status==NATIVE_EVIDENCE_VALIDATED,'selected-inputs','validated',f'{gate.status}:{gate.detail}')
    image=open_native_image(gameassembly,metadata)
    proof=validate(image,contract)
    return {'format':'endfield.dynamic-mission-ready-native-audit.v1','status':'validated',
        'proof':proof,'evidenceBoundary':contract['evidenceBoundary'],
        'nativeInputs':{name:row['sha256'] for name,row in by_name.items()}}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_ready_native_latest.json')
    args=parser.parse_args(argv)
    try:
        sources=_parser_source_snapshots(Path(__file__))
        sources.extend(_fingerprint(path) for path in (CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH))
        inputs=[_fingerprint(path) for path in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs]
        groups._guard_publication(args.output_json,protected)
        result=validate_native_claims(args.gameassembly,args.metadata,inputs)
        result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print(f'dynamic-mission-ready-native:{str(exc)[:1400]}',file=sys.stderr);return 1
    print('Mission ready request proved: non-replacement/non-null path returns true; no stored/live readiness claim')
    return 0

if __name__=='__main__':raise SystemExit(main())
