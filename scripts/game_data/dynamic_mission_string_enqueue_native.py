"""Typed mission string lookup and local-copy owner requests; no live refresh."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_mission_string_enqueue_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_mission_string_enqueue_native_claims.json'
SCHEMA='endfield.dynamic-mission-string-enqueue-native-claims.v1'


def _native_set_value(image,index):
    raw=_type_record(image,index);md=image.metadata;pe=image.pe
    require(raw[10]==0x15 and raw[11]&0x7f==0,'ordinary-native-set-value',raw.hex())
    generic=struct.unpack_from('<Q',raw)[0]
    pointer,inst=struct.unpack('<QQ',pe.bytes_at_va(generic,16));definition_raw=pe.bytes_at_va(pointer,16)
    require(definition_raw[10]==0x11 and definition_raw[11]&0x7f==0,'native-set-value-definition',definition_raw.hex())
    definition=struct.unpack_from('<Q',definition_raw)[0]
    require(0<=definition<len(md.types),'native-set-definition-range',definition)
    td=md.types[definition]
    require(md.type_full_name(td)=='Unity.Collections.NativeParallelHashSet`1' and td.generic_container_index>=0,
            'native-set-concrete-owner',definition)
    section=md.sections['genericContainers'];at=section.offset+td.generic_container_index*16
    require(section.offset<=at and at+16<=section.offset+section.size,'native-set-container-range',at)
    owner,argc,is_method,_=struct.unpack_from('<iiii',md.buf,at)
    require((owner,argc,is_method)==(definition,1,0),'native-set-own-generic-container',(owner,argc,is_method))
    argc,argv=struct.unpack('<QQ',pe.bytes_at_va(inst,16));require(argc==1,'native-set-argument-count',argc)
    argument=pe.bytes_at_va(pe.u64_at_va(argv),16)
    require(argument[10]==0x0b and argument[11]&0x7f==0,'native-set-UInt64-argument',argument.hex())
    return {'definition':definition,'rawTypeHex':raw.hex().upper(),'definitionRawHex':definition_raw.hex().upper(),'argumentRawHex':argument.hex().upper(),
            'managedInstanceSizeProved':False,'instanceFieldLayoutProved':False,'completeParameterAbiProved':False}


def check_request(rows,program,patch_pointer,owner_pointer):
    _grammar(rows,program);by={r['offset']:r for r in rows}
    require(len(by)==len(rows),'enqueue-distinct-offsets',len(by))
    start=_va(rows[0]);end=start
    for row in rows:
        require(_va(row)==end and row['offset']==end-start,'enqueue-contiguous-partition',row)
        end+=len(_raw(row))
    require(end-start==214,'enqueue-complete-program-bytes',end-start)
    fixed=((0,'48895C2408'),(5,'57'),(6,'4883EC30'),(17,'8BFA'),(19,'488BD9'),
           (55,'0F57C0'),(58,'33D2'),(65,'0F11442420'),(75,'84C0'),(79,'488B4B30'),
           (83,'4885C9'),(95,'4C8D442420'),(100,'8BD7'),(107,'84C0'),(111,'0F28442420'),
           (116,'488D542420'),(121,'4533C0'),(124,'660F7F442420'),(130,'488BCB'),
           (138,'488B4348'),(142,'4885C0'),(147,'83782000'),(153,'488BCB'),
           (203,'488B5C2440'),(208,'4883C430'),(212,'5F'),(213,'C3'))
    for at,raw in fixed:require(_raw(by[at])==bytes.fromhex(raw),'enqueue-fixed-frame-copy-arguments',at)
    for at,opcode,target in ((22,'75',55),(77,'75',163),(86,'74',180),(109,'74',203),
                             (145,'74',180),(151,'7E',203),(161,'EB',203),(178,'75',186)):
        require(_raw(by[at]).startswith(bytes.fromhex(opcode)) and branch_target(by[at])==_va(by[target]),
                'enqueue-owned-instruction-edge',(at,target))
    def rip(row,offset):return _va(row)+len(_raw(row))+struct.unpack_from('<i',_raw(row),offset)[0]
    require(_raw(by[10])[:2]==bytes.fromhex('803D') and _raw(by[10])[-1:]==b'\0' and
            _raw(by[48])[:2]==bytes.fromhex('C605') and _raw(by[48])[-1:]==b'\1' and
            rip(by[10],2)==rip(by[48],2),'enqueue-same-entry-init-flag',(by[10],by[48]))
    require(_raw(by[24])[:3]==bytes.fromhex('488D0D') and _raw(by[88])[:3]==bytes.fromhex('4C8B0D') and
            rip(by[24],3)==rip(by[88],3),'enqueue-same-initialized-lookup-context',(by[24],by[88]))
    calls={31,43,70,102,133,156,170,180,198}
    require({r['offset'] for r in rows if r['text'].startswith('call ')}==calls,'enqueue-complete-call-boundaries',calls)
    for at in calls:require(len(_raw(by[at]))==5 and _raw(by[at])[0]==0xe8,'enqueue-direct-call',at)
    require(branch_target(by[70])==patch_pointer and branch_target(by[133])==owner_pointer,
            'enqueue-actual-qualified-request-calls',(by[70],by[133]))
    _register_preserved([r for r in rows if 19<r['offset']<100],{'rdi','rbx'},
                        {_va(by[31]),_va(by[43]),_va(by[70])})
    _register_preserved([r for r in rows if 102<r['offset']<203],{'rbx'},
                        {_va(by[a]) for a in (133,156,170,180,198)})
    byva={_va(r):r for r in rows};paths=[]
    selected={77:False,86:False,145:False};conditional={22,77,86,109,145,151,178}
    def visit(at,path):
        require(at in by and at not in path and len(path)<100,'enqueue-owned-normal-path',(at,path))
        path=path+[at];row=by[at]
        if at==213:paths.append(path);return
        require(at not in (163,165,170,175,178,180,185,186,189,192,195,198),'enqueue-selected-path-exclusion',at)
        following=at+len(_raw(row))
        if at==161:visit(byva[branch_target(row)]['offset'],path)
        elif at in conditional:
            if selected.get(at) is not False:visit(byva[branch_target(row)]['offset'],path)
            if selected.get(at) is not True:visit(following,path)
        else:visit(following,path)
    visit(0,[]);require(len(paths)==6,'enqueue-six-selected-normal-paths',len(paths))
    for path in paths:
        require((133 in path)==(111 in path)==(124 in path),'enqueue-copy-request-same-path',path)
    return {'selectedNormalPaths':len(paths),'lookupMiss':'no owner request; balanced return',
            'lookupHit':'same local address and 16B mechanical copy passed to actual typed owner request',
            'callerLocalRange':[32,48],'savedFrameRanges':[[48,56],[64,72]],'returnAddressRange':[56,64],'pendingRawInt32LaneOffset':32,
            'pendingLaneMeaningProved':False,'managedInstanceSizeProved':False,
            'completeParameterAbiProved':False,'runtimeObserved':False}


def validate(image,contract,provider):
    md=image.metadata;pe=image.pe;methods={}
    specs=dict(contract['methods']);specs['patch']=provider['methods']['patch']
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and
                md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'enqueue-qualified-owner-'+role,len(owners))
        candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role!='ownerRequest':m=select_ordinary_overload(image,candidates,spec)
        else:
            require(len(candidates)==1,'enqueue-owner-request-unique',len(candidates));m=candidates[0]
            require(not m.flags&0x10 and len(md.parameters_for(m))==1,'enqueue-owner-instance-arity',m.flags)
            _abi(image,m.return_type,'Void','enqueue-owner-return')
        pointer=image.method_pointer_va(m);require(pointer is not None,'enqueue-actual-method-pointer',role)
        methods[role]=(m,pointer)
    owner=methods['consumer'][0].declaring_type
    require(methods['ownerRequest'][0].declaring_type==owner,'enqueue-same-concrete-system-owner',owner)
    value=_native_set_value(image,md.parameters_for(methods['ownerRequest'][0])[0].type_index)
    field_spec=contract['fields']['lookup'];field=_field(image,owner,field_spec['name'],field_spec['offset'])
    pending_spec=contract['fields']['pending'];pending=_field(image,owner,pending_spec['name'],pending_spec['offset'])
    extent=closed_generic_reference_extent(NativeReferenceContext(image),pending.type_index)
    require(extent['type']=='System.Collections.Generic.HashSet`1<ulong>','enqueue-pending-concrete-reference',extent['type'])
    pointer=methods['consumer'][1];end=image.mapper.pdata_function_extents(pe).get(pointer)
    require(end is not None and 0<end-pointer<=4096,'enqueue-bounded-owned-primary',end)
    raw=pe.bytes_at_va(pointer,end-pointer);rows=_instruction_partition(raw,pointer,_composed_decoder(image.mapper))
    proof=check_request(rows,contract['program'],methods['patch'][1],methods['ownerRequest'][1]);by={r['offset']:r for r in rows}
    _,context=dictionary_context(image,by[88],by[102],field,method_name='TryGetValue',argument_kinds=(8,0x15))
    require(context['argumentRawHex'][1].upper()==value['rawTypeHex'],'enqueue-same-value-raw-type',(context,value))
    proof.update({'lookupContext':context,'valueType':value,'methods':{role:{'index':m.index,'rva':va-pe.image_base,
                  'ownerDefinition':m.declaring_type} for role,(m,va) in methods.items()},
                  'primary':{'rva':pointer-pe.image_base,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper()},
                  'fieldOffsets':{'lookup':field_spec['offset'],'pending':pending_spec['offset']},
                  'fields':{role:{'index':f.index,'ownerDefinition':owner,'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
                            for role,f in (('lookup',field),('pending',pending))}})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='mission_string_enqueue')
    dependency=contract['dependencies'][0]
    provider,_=read_reviewed_contract(CONTRACTS_DIR/dependency['path'],schema=dependency['schema'],status='reviewed',label='mission_string_enqueue_provider')
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,provider)
    return {'format':'endfield.dynamic-mission-string-enqueue-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_mission_string_enqueue_native_latest.json')
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
        print('mission-string-enqueue:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Mission string enqueue passed: typed requests/local copy; managed size and live refresh unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
