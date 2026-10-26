"""Bounded Quest state message field writes; no live state or dictionary mutation."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_state_message_writes_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_quest_state_message_writes_native_claims.json'
SCHEMA='endfield.dynamic-quest-state-message-writes-native-claims.v1'


from scripts.game_data.il2cpp.context import unresolved_usage_index

def check_block(rows,role,program,constructor,owned_rows):
    _grammar(rows,program);by={r['offset']:r for r in rows};owned={_va(r):r for r in owned_rows}
    start,end={'constructed':(602,661),'localRecord':(698,738)}[role];cursor=start;origin=_va(rows[0])-start
    for row in rows:
        raw=_raw(row);require(row['offset']==cursor and _va(row)==origin+cursor and raw and not row['text'].startswith(('db','unknown','ff/')),'quest-message-block-complete',row);cursor+=len(raw)
        require(_va(row) in owned and _raw(owned[_va(row)])==raw,'quest-message-owned-block-row',row)
        if row['text'].startswith('call '):require(len(raw)==5 and raw[0]==0xe8,'quest-message-direct-call-boundary',row)
    require(cursor==end,'quest-message-block-end',cursor)
    if role=='constructed':
        fixed={614:'488BD8',617:'4885C0',626:'33D2',628:'488BCB',636:'4C8B7718',640:'4C897310',644:'488D4B10',653:'448B4F20',657:'44894B18'}
        require(_raw(by[602])[:3]==bytes.fromhex('488B0D') and len(_raw(by[602]))==7,'quest-message-type-context-load',by[602])
        require(_raw(by[620])[:2]==bytes.fromhex('0F84') and branch_target(by[620]) in owned,'quest-message-nonnull-constructor-edge',by[620])
        require(branch_target(by[631])==constructor,'quest-message-actual-constructor',by[631])
        _register_preserved([r for r in rows if r['offset']<657],{'rdi'},{_va(by[a]) for a in (609,631,648)})
        _register_preserved([r for r in rows if 614<r['offset']<657],{'rbx'},{_va(by[a]) for a in (631,648)})
        _register_preserved([r for r in rows if 636<r['offset']<640],{'r14'},set())
        require(by[636].get('write',{}).get('register')=='r14' and by[653].get('write',{}).get('register')=='r9d','quest-message-loaded-lanes',None)
        transfers={'messageKeyOffset':_raw(by[636])[-1],'recordKeyOffset':_raw(by[640])[-1],
                   'messageStateOffset':_raw(by[653])[-1],'recordStateOffset':_raw(by[657])[-1]}
    else:
        fixed={698:'488B5C2458',703:'4885DB',712:'448B6318',716:'4489642438',721:'448B7720',725:'4885DB',734:'44897318'}
        for at in (706,728):require(_raw(by[at])[:2]==bytes.fromhex('0F84') and branch_target(by[at]) in owned,'quest-message-local-nonnull-owned-edge',at)
        _register_preserved([r for r in rows if 698<r['offset']<734],{'rbx','rdi'},set())
        require(not any(r['text'].startswith('call ') for r in rows),'quest-message-local-no-call',None)
        _register_preserved([r for r in rows if 721<r['offset']<734],{'r14'},set())
        transfers={'messageStateOffset':_raw(by[721])[-1],'recordStateOffset':_raw(by[734])[-1],
                   'previousStateOffset':_raw(by[712])[-1],'previousStateCallerFrameOffset':_raw(by[716])[-1]}
    for at,raw in fixed.items():require(_raw(by[at])==bytes.fromhex(raw),'quest-message-source-store-frame',at)
    return {'block':role,'transfers':transfers,'sourceStateBits':32,'stateNormalizationOrRangeCheckProved':False,
            'allocationSucceededProved':False,'dictionaryLookupOrMutationProved':False,'entryOrNormalReturnProved':False,'runtimeObserved':False}


def bind_fields(proofs,fields):
    for proof in proofs:
        for key,value in proof['transfers'].items():
            if key.endswith('CallerFrameOffset'):continue
            role='recordState' if key=='previousStateOffset' else key.removesuffix('Offset')
            require(role in fields and value==fields[role]['offset'],'quest-message-field-displacement',(key,value,fields.get(role)))
    return proofs


def type_context(image,row,record):
    raw=_raw(row);require(raw[:3]==bytes.fromhex('488B0D') and len(raw)==7,'quest-message-type-context-load',row)
    cell=_va(row)+7+struct.unpack_from('<i',raw,3)[0];usage=image.pe.bytes_at_va(cell,8)
    type_index=unresolved_usage_index(usage,image.registration['typesCount'],tag=1,source=str(image.gameassembly),offset=cell)
    require(_class(image,type_index)==record,'quest-message-type-context-same-constructor-owner',type_index)
    return {'cellRva':cell-image.pe.image_base,'rawUsageHex':usage.hex().upper(),'registeredTypeIndex':type_index,'definition':record,'rawTypeHex':_type_record(image,type_index).hex().upper(),'liveResolutionProved':False}


def validate(image,contract,cache):
    md=image.metadata;specs=dict(contract['methods']);specs['questState']=cache['methods']['questState'];methods={};message=None;quest_enum=None
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'quest-message-qualified-owner-'+role,len(owners));candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role in ('handler','questState'):
            require(len(candidates)==1,'quest-message-qualified-method-'+role,len(candidates));method=candidates[0];params=md.parameters_for(method)
            require(not method.flags&0x10 and len(params)==1,'quest-message-instance-arity-'+role,method.flags)
            if role=='handler':
                _abi(image,method.return_type,'Void','quest-message-handler-return');message=_class(image,params[0].type_index)
                require(md.type_full_name(md.types[message])==spec['parameters'][0],'quest-message-concrete-message',message)
            else:_abi(image,params[0].type_index,'String','quest-message-state-getter-parameter');quest_enum=_enum(image,method.return_type,spec['returnType'])
        else:method=select_ordinary_overload(image,candidates,spec)
        pointer=image.method_pointer_va(method);require(pointer is not None,'quest-message-actual-pointer',role);methods[role]=(method,pointer)
    require(methods['handler'][0].declaring_type==methods['questState'][0].declaring_type,'quest-message-same-system-owner',None)
    record=methods['constructor'][0].declaring_type;fields={}
    for role,spec in contract['fields'].items():
        owner=message if role.startswith('message') else record;field=_field(image,owner,spec['name'],spec['offset'])
        if spec['type']=='enum':require(_enum(image,field.type_index,specs['questState']['returnType'])==quest_enum,'quest-message-record-actual-getter-enum',None)
        else:_abi(image,field.type_index,spec['type'],'quest-message-field-'+role)
        fields[role]={'index':field.index,'ownerDefinition':owner,'name':spec['name'],'offset':spec['offset'],'rawTypeHex':_type_record(image,field.type_index).hex().upper()}
    pe=image.pe;pointer=methods['handler'][1];end=image.mapper.pdata_function_extents(pe).get(pointer)
    require(end is not None and end-pointer==1992,'quest-message-owned-handler-extent',end);raw=pe.bytes_at_va(pointer,end-pointer)
    rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper))
    blocks={role:[r for r in rows if start<=r['offset']<end] for role,start,end in [('constructed',602,661),('localRecord',698,738)]}
    proofs=[check_block(blocks[role],role,contract['programs'][role],methods['constructor'][1],rows) for role in blocks];bind_fields(proofs,fields)
    context=type_context(image,blocks['constructed'][0],record)
    return {'writes':proofs,'fields':fields,'recordEnumDefinition':quest_enum,'typeContext':context,
            'handler':{'index':methods['handler'][0].index,'rva':pointer-pe.image_base,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'completeOwnedPartitionProved':True,'completeManagedProgramProved':False},
            'constructor':{'index':methods['constructor'][0].index,'rva':methods['constructor'][1]-pe.image_base,'ownerDefinition':record},'blocksReachedFromEntryProved':False}

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_state_message_writes')
    cache,=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='quest_message_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,cache)
    return {'format':'endfield.dynamic-quest-state-message-writes-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_state_message_writes_native_latest.json')
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
        print('quest-state-message-writes:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest message writes passed: typed field bit transfers; live state and mutation unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
