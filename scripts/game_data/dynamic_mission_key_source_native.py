"""Conditional key value sources to an opaque slot lane; no live key identity."""
from __future__ import annotations
import argparse
import sys
import hashlib
import json
import struct
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_key_source_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.context import method_spec_usage_index, type_parameter_owner
from scripts.game_data.dynamic_erosion_consumers_native import _check_method, _ordinary_primitive_abi, _raw_type_abi, _instruction_partition, _preserved_interval, _direct_call_boundary
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_scalar_components_native import _relative_call_target
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data import dynamic_mission_string_providers_native as string_providers

CONTRACT=CONTRACTS_DIR/'dynamic_mission_key_source_native_claims.json'
SCHEMA='endfield.dynamic-mission-key-source-native-claims.v3'

def validate_claims(gameassembly,metadata):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_key_source')
    catalogs={dependency['path']:read_reviewed_contract(CONTRACTS_DIR/dependency['path'],schema=dependency['schema'],status=dependency.get('status','validated'),label='mission_key_dependency')[0]
              for dependency in contract['dependencies']}
    scalar=catalogs['dynamic_scalar_components_native.json'];mission=catalogs['dynamic_mission_condition_consumers_native.json']
    inputs=scalar['nativeInputs'];require(inputs==mission['nativeInputs'],'same-dependency-build',mission['nativeInputs'])
    gate=check_installed_native_inputs(inputs['gameAssemblySha256'],inputs['metadataSha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status=='validated','selected-native-inputs',f'{gate.status}:{gate.detail}')
    require(_fingerprint(Path(gameassembly).parent/'UnityPlayer.dll')['sha256'].upper()==inputs['unityPlayerSha256'].upper(),
            'selected-unity-input','UnityPlayer hash differs')
    image=open_native_image(gameassembly,metadata);md=image.metadata;pe=image.pe;reg=image.registration
    writers=[row for row in scalar['methods'] if (row['type'],row['method'])==(contract['writer']['type'],contract['writer']['method'])]
    require(len(writers)==1,'source-owned-writer',len(writers));writer=writers[0]
    query=mission['methods']['query']
    require((query['type'],query['method'])==(contract['query']['type'],contract['query']['method']),'query-identity',query)
    consumers=[row for row in scalar['layout']['stringIndexConsumers'] if row['record']=='MissionCondition' and row['field']=='Id' and row['consumerMethodIndex']==writer['index']]
    require(len(consumers)==1,'source-owned-Id-consumer',len(consumers));consumer=consumers[0]
    keys=[row for row in scalar['methods'] if row['index']==consumer['runtimeKeyMethodIndex']]
    require(len(keys)==1,'source-owned-key-method',len(keys));key=keys[0]
    _check_method(image,writer);_check_method(image,key);query_raw=_check_method(image,query)
    writer_meta=md.methods[writer['index']];query_meta=md.methods[query['index']]
    require(writer_meta.declaring_type==query_meta.declaring_type and not writer_meta.flags&0x10 and not query_meta.flags&0x10,
            'same-concrete-system-owner',(writer_meta.declaring_type,query_meta.declaring_type))
    require(key['returnType']=='System.Int32','key-result-Int32',key['returnType'])
    require(not md.methods[key['index']].flags&0x10,'key-instance-call-ABI',md.methods[key['index']].flags)
    query_params=md.parameters_for(query_meta)
    _ordinary_primitive_abi(image,query_params[0].type_index,0x07,'key-query-hotSlot')
    owner=md.types[writer_meta.declaring_type];field_name=contract['poolField']
    fields=[f for f in md.fields_for(owner) if md.string(f.name_index)==field_name]
    require(len(fields)==1,'concrete-pool-field',len(fields));field=fields[0]
    selected=NativeReferenceContext(image)
    pool=closed_generic_reference_extent(selected,field.type_index)
    require(not selected.field_attributes(field.type_index)&0x10,'instance-pool-field',field.type_index)
    pool_offset=runtime_type_field_offsets(md,pe,reg,owner.index)[field_name]
    query_rows=_instruction_partition(query_raw,query['rva'],_composed_decoder(image.mapper))
    check_query_hot_slot_width(query_rows)
    require(query_raw[61:65]==bytes.fromhex('488B4B'+struct.pack('<b',pool_offset).hex()),'query-same-pool-field',query_raw[61:65].hex())
    helper=_relative_call_target(query_raw,query['rva'],83,'query-slot-helper')
    require(query_raw[70:73]==bytes.fromhex('4C8B0D') and query_raw[109:112]==bytes.fromhex('8B5008'),
            'query-context-and-lane',query_raw[70:77].hex())
    context=query['rva']+77+struct.unpack_from('<i',query_raw,73)[0]
    spec=method_spec_usage_index(pe.bytes_at_va(pe.image_base+context,8),reg['methodSpecsCount'],source=str(gameassembly),offset=pe.image_base+context)
    definition,class_inst,method_inst=struct.unpack('<iii',pe.bytes_at_va(int(reg['methodSpecs'],16)+spec*12,12))
    require(0<=definition<len(md.methods) and 0<=class_inst<reg['genericInstsCount'] and method_inst==-1,'slot-context-spec',(definition,class_inst,method_inst))
    slot_method=md.methods[definition]
    require(slot_method.declaring_type==pool['definitionTypeIndex'] and md.string(slot_method.name_index)=='GetSlot' and not slot_method.flags&0x10,
            'slot-context-concrete-owner',definition)
    arguments=image.instantiations.resolve(class_inst).arguments
    require(len(arguments)==1,'slot-context-type-argument',len(arguments))
    argument_record=bytes.fromhex(arguments[0].raw_type_record_hex)
    require(argument_record[10]==0x11 and argument_record[11]&0x7f==0,'slot-value-ABI',argument_record.hex())
    slot_definition=struct.unpack_from('<Q',argument_record)[0]
    require(0<=slot_definition<len(md.types) and pool['argumentTypes']==[md.type_full_name(md.types[slot_definition])],
            'slot-context-declared-value',pool['argumentTypes'])
    generic=struct.unpack_from('<Q',bytes.fromhex(pool['declaredTypeRecordHex']))[0]
    field_inst_pointer=struct.unpack_from('<Q',pe.bytes_at_va(generic,16),8)[0]
    field_arguments=image.instantiations.resolve_pointer(field_inst_pointer).arguments
    require(len(field_arguments)==1,'pool-concrete-argument',len(field_arguments))
    field_argument=bytes.fromhex(field_arguments[0].raw_type_record_hex)
    check_pool_argument(field_argument,slot_definition)
    # The context names the request; its registered entry need not be this helper.
    slot_params=md.parameters_for(slot_method)
    require(len(slot_params)==2,'slot-context-parameters',len(slot_params))
    _ordinary_primitive_abi(image,slot_params[0].type_index,0x07,'slot-context-hotSlot')
    _ordinary_primitive_abi(image,slot_params[1].type_index,0x08,'slot-context-index')
    return_bits=_raw_type_abi(image,slot_method.return_type,'slot-context-return')
    require((return_bits>>16)&0xff==0x13 and return_bits>>24==0x20,'slot-context-reference-return',f'{return_bits:08X}')
    return_pointer=selected.type_pointer(slot_method.return_type)
    return_record=pe.bytes_at_va(return_pointer,16)
    return_owner=type_parameter_owner(md.buf,struct.unpack_from('<Q',return_record)[0],
        [row.generic_container_index for row in md.types],source=str(metadata))
    require(return_owner['typeIndex']==slot_method.declaring_type and return_owner['ordinal']==0,
            'slot-context-return-owner',return_owner)
    _preserved_interval(query_rows,88,109,'rax',set(),'slot-return-to-query-key')
    call=consumer['runtimeKeyCallOffset'];block_start=call-28;block_end=call+74
    table_rva,image_size,table=read_exception_directory(pe)
    chains=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=image_size)
    family=chains.family(writer['rva'])
    require(any(a<=writer['rva']+block_start and writer['rva']+block_end<=b
        for a,b,_ in (row['runtimeTriple'] for row in family['ranges'])),'owned-writer-block',(block_start,block_end))
    block=pe.bytes_at_va(pe.image_base+writer['rva']+block_start,block_end-block_start)
    proof=check_block(block,writer['rva']+block_start,key['rva'],helper,pool_offset,context,image.mapper)
    provider=string_providers.validate(image,catalogs[contract['providerValueSource']['dependency']])
    key_source=provider['getKeyValueSource']
    require(key_source['getKeyMethod']['index']==key['index'] and key_source['getKeyMethod']['rva']==key['rva'],
            'same-actual-provider-value-method',key_source['getKeyMethod'])
    require_false_get_key_argument(block)
    proof['getKeyValueSource']=key_source
    proof['originalGetKeyBooleanFalse']=True
    proof.update({'writerScope':'bounded post-request lane only','queryDictionaryKeyRead':True,
        'requestContextType':pool['type'],'slotValueType':md.type_full_name(md.types[slot_definition]),
        'methodSpecIndex':spec,'actualHelperRva':helper,'writerBlockRva':writer['rva']+block_start,
        'writerBlockBytes':len(block),'writerBlockSha256':hashlib.sha256(block).hexdigest().upper(),
        'stringIndexConsumer':'source-owned MissionCondition.Id to GetStrSpan/GetStrKey request; hit output, counter candidate or anonymous-zero-lane -1; no live allocation identity',
        'combinationRequiresSameReturnedSlot':True})
    return {'format':'endfield.dynamic-mission-key-source-native-audit.v2','status':'validated',
        'nativeInputs':inputs,'proof':proof,'writerUnwindMembership':family,'evidenceBoundary':contract['evidenceBoundary']}


def require(ok,check,actual):
    if not ok:raise ValueError('mission-key-lane.'+check+': '+str(actual)[:700])

def require_false_get_key_argument(block):
    require(block[17:20]==bytes.fromhex('4533C0'),'original-Boolean-false-argument',block[17:20].hex())

def check_query_hot_slot_width(rows):
    selected=[row for row in rows if row['offset']==25]
    require(len(selected)==1,'query-hot-slot-word-register-boundary',len(selected))
    row=selected[0]
    require(bytes.fromhex(row['bytes'])==bytes.fromhex('0FB7F2') and row['text']=='movzx esi, dx' and
            row.get('sourceWidth')==16 and row.get('operandWidth')==32 and row.get('sourceExtension')=='zero extension',
            'query-hot-slot-actual-DX-zero-extension',row)

def check_pool_argument(raw,definition):
    require(len(raw)==16 and struct.unpack_from('<Q',raw)[0]==definition and raw[10]==0x11 and raw[11]&0x7f==0,
            'pool-context-same-concrete-value',raw.hex())

def check_block(raw,rva,key_pointer,helper_pointer,pool_offset,context_rva,mapper):
    try:rows=_instruction_partition(raw,rva,_composed_decoder(mapper))
    except (IndexError,struct.error) as exc:
        raise ValueError('mission-key-lane.instruction-partition:'+str(exc)[:400]) from exc
    require(len(raw)==102,'block-extent',len(raw))
    probes={0:'0F28842440010000660F7F4424504533C94533C0488D542450488BCB',
        33:'448BF0898424C4000000',43:'498B5D'+struct.pack('<b',pool_offset).hex(),47:'4885DB',
        56:'448B4424404403C6',71:'0FB7942490000000488BCB',
        87:'488B8C244002000048890844897008'}
    for at,encoded in probes.items():
        data=bytes.fromhex(encoded)
        require(raw[at:at+len(data)]==data,'program-'+str(at),raw[at:at+len(data)].hex())
    calls={at:_direct_call_boundary(rows,at,'key-lane-'+str(at)) for at in (28,82)}
    def target(at):return rva+at+5+struct.unpack_from('<i',raw,at+1)[0]
    require(target(28)==key_pointer and target(82)==helper_pointer,'same-actual-calls',(target(28),target(82)))
    require(raw[50:52]==bytes.fromhex('0F84') and not rva<=rva+56+struct.unpack_from('<i',raw,52)[0]<rva+len(raw),
        'conditional-nonnull-pool',raw[50:56].hex())
    require(raw[64:67]==bytes.fromhex('4C8B0D') and rva+71+struct.unpack_from('<i',raw,67)[0]==context_rva,
        'same-actual-context',raw[64:71].hex())
    _preserved_interval(rows,36,98,'r14d',{82},'returned-Int32-to-slot8')
    _preserved_interval(rows,87,98,'rax',set(),'same-returned-slot-to-store')
    _preserved_interval(rows,47,79,'rbx',set(),'same-pool-receiver')
    return {'source':'selected GetStrKey Int32 return','destination':'anonymous returned slot Int32 lane+8',
        'helperNameProved':False,'boxedFieldLabelProved':False,'entryProgramProved':False,'runtimeObserved':False}


from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.memorypack.corpus_gate import _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_key_source_native_latest.json')
    args=parser.parse_args(argv)
    try:
        contract=json.loads(CONTRACT.read_text())
        sources=_parser_source_snapshots(Path(__file__))
        sources.extend(_fingerprint(path) for path in (CONTRACT,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH,
            *(CONTRACTS_DIR/dependency['path'] for dependency in contract['dependencies'])))
        inputs=[_fingerprint(path) for path in (args.gameassembly,args.metadata,args.gameassembly.parent/'UnityPlayer.dll')]
        protected=[Path(row['path']) for row in sources+inputs]
        groups._guard_publication(args.output_json,protected)
        result=validate_claims(args.gameassembly,args.metadata)
        result['proofSources']=sources;result['proofInputs']=inputs
        encoded=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        groups._require_unchanged(sources+inputs);groups._guard_publication(args.output_json,protected)
        atomic_write_text(args.output_json,encoded)
    except (OSError,ValueError,KeyError,IndexError,RuntimeError,struct.error) as exc:
        print(f'dynamic-mission-key-source-native:{str(exc)[:1400]}',file=sys.stderr);return 1
    print('Mission key lane proved: GetStrKey returned Int32 to slot+8 and query key; allocation/live ownership unresolved')
    return 0

if __name__=='__main__':raise SystemExit(main())
