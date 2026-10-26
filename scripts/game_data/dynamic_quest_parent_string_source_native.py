"""Conditional Quest String return sources; opaque String algorithms and cache API."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_parent_string_source_native')
from scripts.game_data.dynamic_native_provenance import json_proof_snapshots,require_json_proof_unchanged,authenticate_native_proof
from scripts.common import check_installed_native_inputs, NATIVE_EVIDENCE_VALIDATED
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.il2cpp.unwind_chains import read_exception_directory, UnwindChainIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, closed_generic_reference_extent
from scripts.game_data.dynamic_mission_string_providers_native import (require, _raw, _va, _grammar, _abi, _type_record,
    branch_target, _register_preserved)
from scripts.game_data.dynamic_mission_state_cache_native import _field, _enum
from scripts.game_data.dynamic_mission_condition_consumers_native import _composed_decoder
from scripts.game_data.dynamic_erosion_consumers_native import _instruction_partition
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _parser_source_snapshots
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data import dynamic_group_components_native as groups
from scripts.repo_paths import REPO_ROOT
CONTRACT=CONTRACTS_DIR/'dynamic_quest_parent_string_source_native_claims.json'
SCHEMA='endfield.dynamic-quest-parent-string-source-native-claims.v1'


from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.il2cpp.protocol import field_defaults

def check_sources(parts,programs,patch,index_of,substring):
    require(len(parts)==2,'two-owned-ranges',None);
    for part,program in zip(parts,programs):_grammar(part,program)
    rows=parts[0];by={r['offset']:r for r in rows};byva={_va(r):r for part in parts for r in part};require(len(byva)==sum(map(len,parts)),'disjoint-owned-ranges',None)
    for part,size in zip(parts,(229,44)):
        offset=0;start=_va(part[0])
        for r in part:
            require(r['offset']==offset and _va(r)==start+offset and not r['text'].startswith(('db','unknown','ff/')),'complete-boundary',r);offset+=len(_raw(r))
        require(offset==size,'owned-size',offset)
    fixed={0:'48895C2408',5:'4889742410',10:'57',11:'4883EC30',23:'33D2',40:'84C0',52:'4885C9',90:'488B5C2440',95:'488B742448',100:'4883C430',104:'5F',105:'C3',175:'4885C9',207:'488B5C2440',212:'488B742448',217:'4883C430',221:'5F',222:'C3',15:'488BFA',18:'488BD9',21:'33F6',30:'4889742458',48:'488B4B70',68:'4C8D442458',73:'488BD7',81:'84C0',85:'488B442458',106:'4885FF',111:'448B4F10',115:'4533C0',125:'488BCF',128:'4889742428',133:'C744242004000000',146:'85C0',150:'4533C9',153:'448BC0',156:'33D2',158:'488BCF',166:'488B4B70',170:'4889442458',187:'4C8BC0',190:'488BD7'}
    for at,b in fixed.items():require(_raw(by[at])==bytes.fromhex(b),'arguments-source-or-local',at)
    require(branch_target(by[35])==patch,'actual-patch-call',None)
    for at,pointer in [(141,index_of),(161,substring)]:require(branch_target(by[at])==pointer,'actual-string-call',at)
    for at,op in {42:'0F85',55:'0F84',83:'74',109:'74',148:'78',178:'74',198:'EB'}.items():require(_raw(by[at]).startswith(bytes.fromhex(op)),'actual-branch-direction',at)
    expected={42:_va(parts[1][0]),55:_va(by[223]),83:_va(by[106]),109:_va(by[223]),148:_va(by[200]),178:_va(by[223]),198:_va(by[85])}
    for at,target in expected.items():require(branch_target(by[at])==target,'owned-edge',at)
    choices={_va(by[a]):False for a in (42,55,109,178)};paths=[]
    def walk(va,path):
        require(va in byva and va not in path and len(path)<100,'owned-CFG',va);path=path+[va];r=byva[va]
        if r['text']=='ret':paths.append(path);return
        if r['text'].startswith('jmp '):walk(branch_target(r),path)
        elif r['text'].startswith(('je ','js ','jcc ')):
            if choices.get(va) is not False:walk(branch_target(r),path)
            walk(va+len(_raw(r)),path)
        else:walk(va+len(_raw(r)),path)
    walk(_va(rows[0]),[]);require(len(paths)==3,'three-selected-normal-paths',len(paths))
    for path in paths:
        start=path.index(_va(by[21]))+1;restore=next(i for i,v in enumerate(path) if byva[v]['text']=='mov rbx, [rsp+0x40]');interval=[byva[v] for v in path[start:restore]];calls={_va(r) for r in interval if r['text'].startswith('call ')};_register_preserved(interval,{'rbx','rdi','rsi'},calls)
    return {'selectedNormalPaths':3,'cacheFieldOffset':_raw(by[48])[-1],'StringLengthOffset':_raw(by[111])[-1],'comparisonBits':int.from_bytes(_raw(by[133])[-4:],'little'),'producer':'actual IndexOf Int32 result -> actual Substring(0,result) String -> local slot and return','semanticStringAlgorithmProved':False,'delimiterContentsProved':False,'cacheAPIProved':False,'liveHierarchyProved':False}

def source_methods(image,specs):
    md=image.metadata;methods={};enum_definition=None
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'string-source-qualified-owner',role);matches=[]
        for m in md.methods_for(owners[0]):
            if md.string(m.name_index)!=spec['method'] or bool(m.flags&16)!=(spec['callAbi']=='static'):continue
            params=md.parameters_for(m)
            if len(params)!=len(spec['parameters']):continue
            try:
                _abi(image,m.return_type,spec['returnType'],'return')
                definition=None
                for p,token in zip(params,spec['parameters']):
                    if token=='System.StringComparison':definition=_enum(image,p.type_index,token)
                    else:_abi(image,p.type_index,token,'parameter')
            except (ValueError,KeyError,IndexError,RuntimeError):continue
            matches.append((m,definition))
        require(len(matches)==1,'string-source-unique-full-ordinary-ABI',(role,[m.index for m,_ in matches]));m,definition=matches[0];pointer=image.method_pointer_va(m)
        require(pointer is not None,'string-source-actual-pointer',role);methods[role]=(m,pointer)
        if definition is not None:enum_definition=definition
    require(methods['indexOf'][0].declaring_type==methods['substring'][0].declaring_type,'same-concrete-String-owner',None)
    return methods,enum_definition

def storage_reference(image,field):
    selected=NativeReferenceContext(image);extent=closed_generic_reference_extent(selected,field.type_index)
    owners=[td for td in image.metadata.types if image.metadata.type_full_name(td)=='System.Collections.Generic.Dictionary`2']
    require(len(owners)==1 and owners[0].index==extent['definitionTypeIndex'],'string-source-dictionary-definition',extent)
    raw=bytes.fromhex(extent['declaredTypeRecordHex']);generic=int.from_bytes(raw[:8],'little');pe=image.pe
    count,argv=struct.unpack('<QQ',pe.bytes_at_va(pe.u64_at_va(generic+8),16));require(count==2,'string-source-dictionary-argument-count',count)
    arguments=[pe.bytes_at_va(pe.u64_at_va(argv+i*8),16) for i in range(2)]
    require(all(r[10]==0x0e and r[11]==0 for r in arguments),'string-source-dictionary-ordinary-String-arguments',[r.hex() for r in arguments])
    return {**extent,'argumentRawHex':[r.hex().upper() for r in arguments],'actualDictionaryAPIProved':False}


def bind_fields(proof,fields):
    for key,role in [('cacheFieldOffset','cache'),('StringLengthOffset','length')]:require(proof[key]==fields[role]['offset'],'string-source-field-displacement',(key,proof[key],fields[role]['offset']))
    return proof


def validate(image,contract,quest,provider):
    specs=dict(contract['methods']);specs.update({'getter':quest['methods']['parentId'],'patch':provider['methods']['patch']})
    methods,definition=source_methods(image,specs);md=image.metadata;pe=image.pe
    require(definition is not None,'string-source-comparison-enum',None)
    cache_spec=contract['cacheField'];f=_field(image,methods['getter'][0].declaring_type,cache_spec['name'],cache_spec['offset'])
    fields={'cache':{'index':f.index,'ownerDefinition':methods['getter'][0].declaring_type,'name':cache_spec['name'],'offset':cache_spec['offset'],'reference':storage_reference(image,f)}}
    length=provider['stringLength'];f=_field(image,methods['indexOf'][0].declaring_type,length['name'],length['offset']);_abi(image,f.type_index,'Int32','string-length')
    require(md.type_full_name(md.types[methods['indexOf'][0].declaring_type])==length['owner'],'same-concrete-String-length-owner',None)
    fields['length']={'index':f.index,'ownerDefinition':methods['indexOf'][0].declaring_type,'name':length['name'],'offset':length['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    pointer=methods['getter'][1];table_rva,size,table=read_exception_directory(pe);family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(pointer-pe.image_base)
    require(len(family['ranges'])==2,'string-source-two-owned-ranges',len(family['ranges']));parts=[];windows=[]
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];require(0<end-begin<=512,'string-source-bounded-range',part)
        raw=pe.bytes_at_va(pe.image_base+begin,end-begin);parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
        windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    require(_va(parts[0][0])==pointer,'string-source-actual-primary-start',pointer)
    proof=check_sources(parts,contract['programs'],methods['patch'][1],methods['indexOf'][1],methods['substring'][1]);bind_fields(proof,fields)
    declaration=declared_members(image,definition,'System.StringComparison',field_defaults(md));matching=[r for r in declaration['members'] if r['id']==proof['comparisonBits']]
    require(bool(matching),'string-source-comparison-declaration',proof['comparisonBits'])
    proof.update({'fields':fields,'comparisonDeclaration':declaration,'comparisonAliases':matching,'windows':windows,
       'methods':{r:{'index':m.index,'rva':p-pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},
       'globalReturnLiteralIdentityProved':False,'providerOrHierarchyProved':False,'runtimeObserved':False,'completeManagedProgramProved':False})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_parent_string_source')
    quest,provider=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='quest_string_source_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,quest,provider)
    return {'format':'endfield.dynamic-quest-parent-string-source-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_parent_string_source_native_latest.json')
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
        print('quest-parent-string-source:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest String return sources passed: conditional actual calls/local returns; algorithms/cache API unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
