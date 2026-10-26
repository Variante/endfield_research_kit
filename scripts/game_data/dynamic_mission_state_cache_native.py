"""Selected state callbacks to typed cache setter requests; no live state."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_state_cache_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, dictionary_context)
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition, _preserved_interval
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_mission_state_cache_native_claims.json'
SCHEMA='endfield.dynamic-mission-state-cache-native-claims.v1'


def _class(image,type_index):
    raw=_type_record(image,type_index)
    require(raw[10]==0x12 and raw[11]==0,'ordinary-concrete-class',raw.hex())
    definition=struct.unpack_from('<Q',raw)[0]
    require(0<=definition<len(image.metadata.types),'class-definition',definition)
    return definition


def _enum(image,type_index,name):
    raw=_type_record(image,type_index)
    require(raw[10]==0x11 and raw[11]&0x7f==0,'ordinary-enum-value',raw.hex())
    definition=struct.unpack_from('<Q',raw)[0];md=image.metadata
    require(0<=definition<len(md.types) and md.type_full_name(md.types[definition])==name,'enum-concrete-definition',definition)
    td=md.types[definition]
    require(td.parent_index>=0 and md.type_full_name(md.types[_class(image,td.parent_index)])=='System.Enum','enum-parent',definition)
    fields=[f for f in md.fields_for(td) if not int.from_bytes(_type_record(image,f.type_index)[8:10],'little')&0x10]
    require(len(fields)==1 and md.string(fields[0].name_index)=='value__','enum-only-instance-underlying-field',
            [md.string(f.name_index) for f in fields])
    _abi(image,fields[0].type_index,'Int32','enum-underlying-Int32')
    return definition


def _event_ref(image,index,name):
    raw=_type_record(image,index)
    require(raw[10]==0x15 and raw[11]==0x20,'explicit-event-value-reference',raw.hex())
    generic=struct.unpack_from('<Q',raw)[0];pe=image.pe;md=image.metadata
    pointer,inst=struct.unpack('<QQ',pe.bytes_at_va(generic,16));definition_raw=pe.bytes_at_va(pointer,16)
    require(definition_raw[10]==0x11 and definition_raw[11]&0x7f==0,'event-value-definition',definition_raw.hex())
    definition=struct.unpack_from('<Q',definition_raw)[0]
    require(0<=definition<len(md.types) and md.type_full_name(md.types[definition])==name,'event-concrete-owner',definition)
    argc,argv=struct.unpack('<QQ',pe.bytes_at_va(inst,16))
    require(argc==int(name.rsplit('`',1)[1]) and 1<=argc<=8,'event-declared-arity',argc)
    first=pe.bytes_at_va(pe.u64_at_va(argv),16)
    require(first[10]==0x0e and first[11]==0,'event-first-declared-String',first.hex())
    return {'definition':definition,'rawTypeHex':raw.hex().upper(),'firstArgumentRawHex':first.hex().upper(),
            'instanceFieldLayoutProved':False}


def _select(image,contract,provider):
    specs=dict(contract['methods']);specs.update({role:provider['methods'][role] for role in contract['providerRoles']})
    methods={};abis={};md=image.metadata
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        require(len(candidates)==1,'qualified-method-'+role,len(candidates));m=candidates[0];params=md.parameters_for(m)
        require(len(params)==len(spec['parameters']) and bool(m.flags&0x10)==(spec['callAbi']=='static'),'call-role-'+role,(m.flags,len(params)))
        ret=spec['returnType']
        if ret in ('Void','Boolean','Int32','UInt64','String'):_abi(image,m.return_type,ret,role+'-return')
        elif '+' in ret:abis[role]=_enum(image,m.return_type,ret)
        else:
            definition=_class(image,m.return_type)
            require(md.type_full_name(md.types[definition])==ret,'concrete-return-'+role,definition)
            abis[role]=definition
        for param,token in zip(params,spec['parameters']):
            if token.startswith('ref Beyond.EventData'):
                abis[role]=_event_ref(image,param.type_index,token[4:])
            else:_abi(image,param.type_index,token,role+'-parameter')
        pointer=image.method_pointer_va(m);require(pointer is not None,'actual-pointer-'+role,pointer)
        methods[role]=(m,pointer)
    require(methods['mission'][0].declaring_type==methods['quest'][0].declaring_type==methods['enqueue'][0].declaring_type,'same-callback-system-owner',methods)
    return methods,abis


def _field(image,owner,name,offset):
    md=image.metadata;td=md.types[owner]
    fields=[f for f in md.fields_for(td) if md.string(f.name_index)==name]
    require(len(fields)==1,'concrete-field-'+name,len(fields));field=fields[0]
    require(not int.from_bytes(_type_record(image,field.type_index)[8:10],'little')&0x10 and
            runtime_type_field_offsets(md,image.pe,image.registration,owner)[name]==offset,'field-instance-offset-'+name,(owner,offset))
    return field


def _ancestor(image,definition,name):
    md=image.metadata;pe=image.pe;seen=set()
    while definition not in seen and len(seen)<16:
        seen.add(definition);td=md.types[definition]
        if md.type_full_name(td)==name:return definition
        require(td.parent_index>=0,'ancestor-parent',name)
        raw=_type_record(image,td.parent_index)
        if raw[10]==0x15 and raw[11]==0:
            carrier=struct.unpack_from('<Q',raw)[0];raw=pe.bytes_at_va(pe.u64_at_va(carrier),16)
        require(raw[10]==0x12 and raw[11]==0,'ancestor-ordinary-definition',raw.hex())
        definition=struct.unpack_from('<Q',raw)[0]
        require(0<=definition<len(md.types),'ancestor-bounded-definition',definition)
    raise ValueError('mission_state_cache:ancestor-cycle-or-bound:'+name)


def _edge(row,opcode,va):
    require(_raw(row).startswith(bytes.fromhex(opcode)) and branch_target(row)==va,'selected-owned-edge',(row,va))


def _call(row,pointer,label):
    require(len(_raw(row))==5 and _raw(row)[0]==0xe8 and branch_target(row)==pointer,label,row)


def check_callback(primary,cold,role,methods,program):
    _grammar(primary,program['primary']);_grammar(cold,program['cold'])
    by={row['offset']:row for row in primary};cb={row['offset']:row for row in cold}
    mission=role=='mission'
    patch,test,patch_branch,manager_getter,lookup,lookup_test,success,epilogue,exception=(71,76,78,98,122,127,129,135,146) if mission else (40,45,47,67,91,96,98,104,148)
    _call(by[patch],methods['patch'][1],'actual-false-patch-call')
    require(_raw(by[test])==bytes.fromhex('84C0'),'patch-AL-test',by[test])
    _edge(by[patch_branch],'0F85',_va(cb[117]))
    _call(by[manager_getter],methods['managerGetter'][1],'typed-manager-getter')
    _call(by[lookup],methods['lookup'][1],'typed-lookup-request')
    require(_raw(by[lookup_test])==bytes.fromhex('84C0'),'lookup-AL-test',by[lookup_test])
    _edge(by[success],'0F85',_va(cb[0]))
    for at in ((94,106) if mission else (63,75)):_edge(by[at],'74',_va(by[exception]))
    require(len(_raw(by[exception]))==5 and _raw(by[exception])[0]==0xe8 and by[exception+5]['text']=='int3','owned-exception-call-start',by[exception])
    for at in (31,47,71):_edge(cb[at],'0F84',_va(by[exception]))
    _edge(cb[14],'75',_va(cb[21]));_edge(cb[112],'E9',_va(by[epilogue]))
    _call(cb[23],methods['player'][1],'typed-player-request')
    _call(cb[59],methods[role+'State'][1],'typed-state-getter')
    _call(cb[106],methods['enqueue'][1],'typed-enqueue-request')
    if mission:
        _edge(by[23],'75',_va(by[56]));cmp_at,store_at=10,49
        init_rows=[by[25],by[37]];init_calls=[by[32],by[44]]
    else:
        _edge(by[23],'74',_va(by[115]));_edge(by[146],'EB',_va(by[25]));cmp_at,store_at=10,139
        init_rows=[by[115],by[127]];init_calls=[by[122],by[134]]
    def rip(row,at):return _va(row)+len(_raw(row))+struct.unpack_from('<i',_raw(row),at)[0]
    require(_raw(by[cmp_at])[:2]==bytes.fromhex('803D') and _raw(by[store_at])[:2]==bytes.fromhex('C605') and
            _raw(by[cmp_at])[-1:]==b'\0' and _raw(by[store_at])[-1:]==b'\1' and rip(by[cmp_at],2)==rip(by[store_at],2),'same-entry-init-flag',(by[cmp_at],by[store_at]))
    require(all(_raw(row)[:3]==bytes.fromhex('488D0D') for row in init_rows) and
            rip(init_rows[0],3)==rip(cb[77],3) and rip(init_rows[1],3)==rip(cb[0],3) and
            all(len(_raw(row))==5 and _raw(row)[0]==0xe8 for row in init_calls+[cb[16]]),'same-initialized-context',init_rows)
    # All admitted instruction slots are closed. The only post-lookup stores are inside opaque callees.
    out=58 if mission else 27;out_pointer=111 if mission else 80
    require(_raw(by[out])==bytes.fromhex('C744244800000000') and _raw(by[out_pointer])==bytes.fromhex('4C8D442448'),
            'lookup-output-local-Int32',(by[out],by[out_pointer]))
    require(_raw(cb[87])==_raw(cb[96])==bytes.fromhex('8B542448'),'same-key-local-loads',(cb[87],cb[96]))
    require(_raw(cb[64])==bytes.fromhex('488B4F38') and _raw(cb[84])==bytes.fromhex('448BC0'),'state-to-cache-value',(cb[64],cb[84]))
    _preserved_interval(cold,64,84,'rax',set(),'getter-result')
    _preserved_interval(cold,87,91,'r8',set(),'setter-value')
    _preserved_interval(cold,68,91,'rcx',set(),'setter-receiver')
    for reg in ('rbx','rdi'):_preserved_interval(cold,0,112,reg,{16,23,59,91,106},'callback-original-'+reg)
    _preserved_interval(primary,25,out_pointer,'rdi',{row['offset'] for row in init_calls}|{patch,manager_getter},'callback-this')
    if not mission:
        for reg in ('rbx','rdi'):
            _preserved_interval(primary,115,146,reg,{122,134},'callback-init-original-'+reg)
    string_load=88 if mission else 57
    _preserved_interval(primary,string_load+3,lookup,'rbx',{manager_getter},'callback-string-request')
    admitted=[row for row in primary if lookup+5<=row['offset']<epilogue]+[row for row in cold if row['offset']<112]
    for row in admitted:
        raw=_raw(row)
        # The closed admitted grammar has no direct stores, PUSH/POP or stack adjustments.
        require(not row['text'].startswith(('mov [','movups [','movaps [','push ','pop ','add rsp','sub rsp')),
                'post-lookup-no-direct-store-or-frame-change',row)
        require((row.get('write') or {}).get('register') not in {'rsp','esp','sp','spl','rbp','ebp','bp','bpl'},
                'post-lookup-frame-alias-preserved',row)
    require([by[epilogue+i]['text'] for i in (0,5,9,10)]==['mov rbx, [rsp+0x30]','add rsp, 0x20','pop rdi','ret'],'balanced-selected-frame',epilogue)
    return {'source':'selected '+role+' state getter normal Int32-underlying enum return',
            'valueRequest':'Dictionary<Int32,Int32>.set_Item(key local, returned state bits)',
            'keyRequest':'same successful TryGetStrKey Int32 output to setter and enqueue request',
            'eventInstanceFieldLayoutProved':False,'runtimeObserved':False,
            'conditions':['actual IFix false; lookup true; nonnull typed receivers and valid original anonymous pointer as String',
                'normal returning Win64 callees preserve original registers and do not overwrite the key local',
                'same concrete cache/key and retained storage required for composition with query']}


def validate(image,contract,provider):
    methods,abis=_select(image,contract,provider);md=image.metadata;pe=image.pe
    system=methods['mission'][0].declaring_type
    cache=_field(image,system,contract['cacheField'],56)
    base=_ancestor(image,system,contract['managerField']['owner'])
    manager=_field(image,base,contract['managerField']['name'],16)
    require(_class(image,manager.type_index)==methods['managerGetter'][0].declaring_type and
            abis['managerGetter']==methods['lookup'][0].declaring_type,'concrete-manager-receiver-chain',base)
    mission_field=_field(image,abis['player'],contract['missionField'],136)
    require(_class(image,mission_field.type_index)==methods['missionState'][0].declaring_type==methods['questState'][0].declaring_type,'concrete-mission-receiver-chain',abis['player'])
    table,size,raw=read_exception_directory(pe)
    unwind=UnwindChainIndex(raw,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table,image_size=size)
    proofs={}
    for role in ('mission','quest'):
        method,pointer=methods[role];family=unwind.family(pointer-pe.image_base)
        require(sum(part['codeBytes'] for part in family['ranges'])<=4096,'bounded-callback-family',role)
        partitions=[]
        for part in family['ranges']:
            begin,end,_=part['runtimeTriple'];body=pe.bytes_at_va(pe.image_base+begin,end-begin)
            partitions.append((part,_instruction_partition(body,pe.image_base+begin,_composed_decoder(image.mapper)),hashlib.sha256(body).hexdigest().upper()))
        primary=[p for p in partitions if p[0]['runtimeTriple'][0]==pointer-pe.image_base]
        require(len(primary)==1,'selected-primary',len(primary));primary=primary[0]
        success_at=129 if role=='mission' else 98
        success=[r for r in primary[1] if r['offset']==success_at];require(len(success)==1,'lookup-success-edge',len(success))
        cold=[p for p in partitions if pe.image_base+p[0]['runtimeTriple'][0]==branch_target(success[0])]
        require(len(cold)==1,'explicit-owned-cold-start',len(cold));cold=cold[0]
        proof=check_callback(primary[1],cold[1],role,methods,contract['programs'][role])
        cb={r['offset']:r for r in cold[1]}
        _,context=dictionary_context(image,cb[77],cb[91],cache,method_name='set_Item',argument_kinds=(8,8))
        proof['context']=context;proof['eventCarrier']=abis[role]
        proof['bodies']=[{'runtimeTriple':p[0]['runtimeTriple'],'sha256':p[2],'bytes':p[0]['codeBytes']} for p in (primary,cold)]
        proof['unwindOwnership']=family;proof['unwindInstructionSemanticsProved']=False
        proofs[role]=proof
    return {'callbacks':proofs,'cacheField':{'ownerDefinition':system,'name':contract['cacheField'],'offset':56},
            'methods':{role:{'index':m.index,'definition':m.declaring_type,'rva':p-pe.image_base} for role,(m,p) in methods.items()}}


@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_state_cache')
    dependency=contract['dependencies'][0]
    provider,_=read_reviewed_contract(CONTRACTS_DIR/dependency['path'],schema=dependency['schema'],status='reviewed',label='mission_state_cache_provider')
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-mission-state-cache-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_state_cache_native_latest.json')
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
        print('mission-state-cache:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission state callbacks passed: typed cache setter requests; event layout/live state unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
