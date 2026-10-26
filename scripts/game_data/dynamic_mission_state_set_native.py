"""Authored IsQuest predicate to typed mission-set Add requests; no live mutation."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_state_set_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, dictionary_context, _register_preserved, select_ordinary_overload)
from scripts.game_data.dynamic_mission_state_cache_native import _field
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_mission_state_set_native_claims.json'
SCHEMA='endfield.dynamic-mission-state-set-native-claims.v1'


from scripts.game_data.il2cpp.context import method_spec_usage_index, type_parameter_owner, generic_method_candidates
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.dynamic_mission_key_source_native import check_block, require_false_get_key_argument
from scripts.game_data.dynamic_erosion_consumers_native import _preserved_interval, _check_method

def hashset_add_context(image,row,call_row,field):
    md=image.metadata;pe=image.pe;reg=image.registration
    extent=closed_generic_reference_extent(NativeReferenceContext(image),field.type_index)
    raw=_raw(row)
    require(raw[:3]==bytes.fromhex('4C8B05') and len(raw)==7,'state-set-context-register',raw.hex())
    cell=_va(row)+7+struct.unpack_from('<i',raw,3)[0]
    spec=method_spec_usage_index(pe.bytes_at_va(cell,8),reg['methodSpecsCount'],source=str(image.gameassembly),offset=cell)
    definition,ci,mi=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+spec*12,12))
    require(0<=definition<len(md.methods) and 0<=ci<reg['genericInstsCount'] and mi==-1,'state-set-method-spec',(definition,ci,mi))
    method=md.methods[definition];params=md.parameters_for(method)
    require(method.declaring_type==extent['definitionTypeIndex'] and
            md.type_full_name(md.types[method.declaring_type])=='System.Collections.Generic.HashSet`1' and
            md.string(method.name_index)=='Add' and not method.flags&0x10 and len(params)==1,'state-set-actual-method',definition)
    _abi(image,method.return_type,'Boolean','state-set-ordinary-return')
    record=_type_record(image,params[0].type_index)
    require(record[10]==0x13 and record[11]==0,'state-set-ordinary-VAR',record.hex())
    owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',record)[0],
            [td.generic_container_index for td in md.types],source=str(image.metadata_path))
    require(owner['typeIndex']==method.declaring_type and owner['ordinal']==0,'state-set-VAR-owner',owner)
    arguments=image.instantiations.resolve(ci).arguments;require(len(arguments)==1,'state-set-instantiation-arity',len(arguments))
    argument=bytes.fromhex(arguments[0].raw_type_record_hex)
    generic=struct.unpack_from('<Q',bytes.fromhex(extent['declaredTypeRecordHex']))[0]
    argc,argv=struct.unpack('<QQ',pe.bytes_at_va(pe.u64_at_va(generic+8),16))
    require(argc==1 and argument[10]==8 and argument[11]&0x7f==0 and
            argument==pe.bytes_at_va(pe.u64_at_va(argv),16),'state-set-same-ordinary-Int32',argument.hex())
    code=image.mapper.code_registration_summary(pe,image.code_registration);table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(pe.bytes_at_va(table,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],
            reg['methodSpecsCount'],{spec},code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    require(len(candidates)==1,'state-set-exact-pointer-candidate',len(candidates))
    pointer=pe.u64_at_va(int(code['genericMethodPointers'],16)+candidates[0]['indices'][0]*8)
    require(pointer==branch_target(call_row),'state-set-actual-call-pointer',(pointer,call_row))
    return {'methodSpecIndex':spec,'definition':definition,'classInstantiation':ci,'fieldType':extent['type'],
            'argumentRawHex':argument.hex().upper(),'actualPointerRva':pointer-pe.image_base}


def check_predicate(rows,program,getter_pointer):
    _grammar(rows,program);by={r['offset']:r for r in rows};start=_va(rows[0]);end=start
    for row in rows:
        require(_va(row)==end and row['offset']==end-start,'state-set-complete-bounded-partition',row)
        end+=len(_raw(row))
    require(end-start==210,'state-set-prefix-extent',end-start)
    for at,raw in ((0,'498B5D30'),(4,'4885DB'),(20,'4C8D842400010000'),(28,'418BD6'),(31,'488BCB'),
                   (81,'498B5D30'),(85,'4885DB'),(94,'0F28842400010000'),(102,'660F7F442450'),
                   (115,'4C8D442450'),(120,'418BD6'),(123,'488BCB'),(138,'488BD7'),
                   (141,'488D8C2400010000'),(154,'33D2'),(156,'488D4C2470'),(166,'83F801'),
                   (171,'0FB6F0'),(176,'4032F6'),(179,'498B5D40'),(183,'4885DB'),(199,'418BD6'),(202,'488BCB')):
        require(_raw(by[at])==bytes.fromhex(raw),'state-set-source-predicate-argument',at)
    for at,opcode,target in ((41,'75',131),(169,'75',176)):
        require(_raw(by[at]).startswith(bytes.fromhex(opcode)) and branch_target(by[at])==_va(by[target]),'state-set-owned-edge',(at,target))
    require(_raw(by[174])[:1]==b'\xeb' and branch_target(by[174])==end,'state-set-equal-one-skip-to-owned-exit',by[174])
    for at in (7,88,186):
        require(_raw(by[at])[:2]==bytes.fromhex('0F84') and not start<=branch_target(by[at])<end,
                'state-set-selected-nonnull-route',at)
    calls={34,76,126,149,161,205}
    require({r['offset'] for r in rows if r['text'].startswith('call ')}==calls,'state-set-all-direct-call-boundaries',calls)
    for at in calls:require(len(_raw(by[at]))==5 and _raw(by[at])[0]==0xe8,'state-set-direct-call',at)
    require(branch_target(by[161])==getter_pointer,'state-set-actual-authored-getter',by[161])
    _preserved_interval(rows,0,210,'r14',calls,'saved-returned-key-to-Add')
    _preserved_interval(rows,0,210,'r13',calls,'same-system-to-field')
    _preserved_interval(rows,183,205,'rbx',set(),'same-mission-set-receiver')
    return {'predicate':'authored IsQuest Int32 equals 1 skips Add; all other bits request Add',
            'addValue':'preserved actual GetStrKey returned Int32 bits','normalizedLow8SIL':{'equalOne':1,'otherwise':0},
            'wholeESIZeroOnOtherwiseProved':False,'setMutationProved':False,'entryProgramProved':False,'runtimeObserved':False}


def validate(image,contract,scalar,key,provider):
    md=image.metadata;pe=image.pe
    writers=[r for r in scalar['methods'] if r['type']==key['writer']['type'] and r['method']==key['writer']['method']]
    require(len(writers)==1,'state-set-source-writer-roster',len(writers));writer=writers[0];_check_method(image,writer)
    owner=md.methods[writer['index']].declaring_type
    require(not md.methods[writer['index']].flags&0x10,'state-set-writer-instance-role',writer['index'])
    records=[r for r in scalar['layout']['records'] if r['name']==contract['sourceRecord']]
    require(len(records)==1,'state-set-source-record-roster',len(records));record=records[0]
    fields=[f for f in record['fields'] if f['name']==contract['sourceField']]
    require(len(fields)==1 and fields[0]['type']=='System.Int32','state-set-source-field-type',fields)
    getter_index=fields[0]['getterMethodIndex'];getter_rows=[r for r in scalar['methods'] if r['index']==getter_index]
    require(len(getter_rows)==1,'state-set-source-getter-row',len(getter_rows));_check_method(image,getter_rows[0])
    getter=md.methods[getter_index];_abi(image,getter.return_type,'Int32','state-set-source-getter-return')
    require(not getter.flags&0x10 and not md.parameters_for(getter) and
            md.type_full_name(md.types[getter.declaring_type])==record['type'],'state-set-source-getter-role',getter_index)
    consumers=[r for r in scalar['layout']['stringIndexConsumers'] if r['record']==contract['sourceRecord'] and
               r['field']=='Id' and r['consumerMethodIndex']==writer['index']]
    require(len(consumers)==1,'state-set-source-key-consumer',len(consumers));consumer=consumers[0]
    runtime=provider['methods']['getKey'];key_owner=md.methods[consumer['runtimeKeyMethodIndex']].declaring_type
    td=md.types[key_owner]
    require(md.type_full_name(td)==runtime['type'] and md.string(md.images[image.owners[key_owner]].name_index)==runtime['image'],
            'state-set-qualified-key-owner',key_owner)
    selected=select_ordinary_overload(image,[m for m in md.methods_for(td) if md.string(m.name_index)==runtime['method']],runtime)
    require(selected.index==consumer['runtimeKeyMethodIndex'],'state-set-source-key-overload',selected.index)
    key_pointer=image.method_pointer_va(selected);getter_pointer=image.method_pointer_va(getter)
    require(key_pointer is not None and getter_pointer is not None,'state-set-source-method-pointers',(key_pointer,getter_pointer))
    pool=_field(image,owner,key['poolField'],40)
    field=_field(image,owner,contract['missionSet']['name'],contract['missionSet']['offset'])
    begin=consumer['runtimeKeyCallOffset']-28;end=begin+312
    table_rva,size,table=read_exception_directory(pe)
    family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(writer['rva'])
    require(any(a<=writer['rva']+begin and writer['rva']+end<=b for a,b,_ in (r['runtimeTriple'] for r in family['ranges'])),
            'state-set-source-owned-block',(begin,end))
    raw=pe.bytes_at_va(pe.image_base+writer['rva']+begin,end-begin);old=raw[:102];rva=writer['rva']+begin
    helper=rva+87+struct.unpack_from('<i',old,83)[0];context=rva+71+struct.unpack_from('<i',old,67)[0]
    check_block(old,rva,key_pointer-pe.image_base,helper,40,context,image.mapper);require_false_get_key_argument(old)
    prefix=raw[102:];rows=_instruction_partition(prefix,pe.image_base+rva+102,_composed_decoder(image.mapper))
    proof=check_predicate(rows,contract['program'],getter_pointer);by={r['offset']:r for r in rows}
    proof.update({'setContext':hashset_add_context(image,by[192],by[205],field),
            'sourceGetter':{'index':getter_index,'record':contract['sourceRecord'],'field':contract['sourceField']},
            'sourceKeyMethod':{'index':selected.index,'rva':key_pointer-pe.image_base},
            'missionSetField':{'index':field.index,'ownerDefinition':owner,'offset':contract['missionSet']['offset'],
                              'rawTypeHex':_type_record(image,field.type_index).hex().upper()},
            'writerBlock':{'rva':rva,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()},'writerOwnedFamily':family})
    return proof


@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_state_set')
    dependencies=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='state_set_dependency')[0]
                  for d in contract['dependencies']]
    scalar,key,provider=dependencies
    native=scalar['nativeInputs'];by={Path(r['path']).name:r for r in inputs}
    gate=check_installed_native_inputs(native['gameAssemblySha256'],native['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    require(by['UnityPlayer.dll']['sha256'].upper()==native['unityPlayerSha256'].upper(),'state-set-native-UnityPlayer',by['UnityPlayer.dll']['sha256'])
    proof=validate(open_native_image(gameassembly,metadata),contract,scalar,key,provider)
    return {'format':'endfield.dynamic-mission-state-set-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:r['sha256'] for name,r in by.items()},'evidenceBoundary':contract['evidenceBoundary']}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_state_set_native_latest.json')
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
        print('mission-state-set:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission state set passed: authored predicate/key Add requests; live mutation unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
