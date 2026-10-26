"""Conditional Quest state value sources; opaque dictionary API and live state."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
if __name__=='__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.dynamic_quest_state_value_source_native')
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
CONTRACT=CONTRACTS_DIR/'dynamic_quest_state_value_source_native_claims.json'
SCHEMA='endfield.dynamic-quest-state-value-source-native-claims.v1'


from scripts.game_data.dynamic_mission_state_symbols_native import declared_members
from scripts.game_data.il2cpp.protocol import field_defaults

def check_sources(parts,programs,patch,parent_id):
    require(len(parts)==len(programs)==8,'quest-state-owned-roster',len(parts));allrows=[]
    for rows,program,size in zip(parts,programs,(38,241,11,18,19,47,158,44)):
        _grammar(rows,program);cursor=0;start=_va(rows[0])
        for row in rows:
            require(row['offset']==cursor and _va(row)==start+cursor and _raw(row) and not row['text'].startswith(('db','unknown','ff/')),'quest-state-complete-partition',row);cursor+=len(_raw(row));allrows.append(row)
        require(cursor==size,'quest-state-owned-size',cursor)
    byva={_va(r):r for r in allrows};require(len(byva)==len(allrows),'quest-state-disjoint-ranges',len(allrows))
    p={r['offset']:r for r in parts[0]};m={r['offset']:r for r in parts[1]}
    require(_va(p[32])+len(_raw(p[32]))==_va(m[0]),'quest-state-explicit-fallthrough',None)
    fixedp={0:'48895C2410',5:'57',6:'4883EC30',10:'488BFA',13:'488BD9',16:'33D2',28:'33D2',30:'84C0'}
    fixedm={0:'4889742440',5:'33F6',12:'4889742458',22:'84C0',30:'488B8BE0000000',37:'4885C9',53:'4C8D442458',58:'488BD7',66:'84C0',70:'488B442458',75:'4885C0',84:'4533C0',87:'488BD7',90:'488BCB',98:'488BF8',101:'4885C0',110:'397010',126:'4889742458',150:'488B10',153:'4885D2',175:'488B8BD8000000',182:'4885C9',198:'4C8D442458',203:'488BD7',211:'84C0',215:'488B4C2458',220:'4885C9',225:'B803000000',230:'394118',233:'0F45C6',236:'488B742440'}
    for mapping,fixed in [(p,fixedp),(m,fixedm)]:
        for at,raw in fixed.items():require(_raw(mapping[at])==bytes.fromhex(raw),'quest-state-frame-fields-constant',at)
    require(branch_target(p[23])==branch_target(m[17])==patch and branch_target(m[93])==parent_id,'quest-state-actual-patch-and-parent-calls',None)
    directions={24:'0F85',40:'0F84',68:'74',78:'0F85',104:'0F84',113:'0F86',137:'0F84',156:'0F84',169:'0F8F',185:'0F84',213:'74',223:'74'}
    for at,op in directions.items():require(_raw(m[at]).startswith(bytes.fromhex(op)) and branch_target(m[at]) in byva,'quest-state-owned-direction',at)
    require(_raw(p[32])[:2]==b'\x0f\x85' and branch_target(p[32])==_va(parts[7][0]),'quest-state-root-patch-edge',p[32])
    expected={24:_va(parts[6][0]),40:_va(parts[5][0])+35,68:_va(m[84]),78:_va(parts[4][0]),104:_va(parts[3][0]),113:_va(parts[3][0]),137:_va(parts[5][0]),156:_va(parts[5][0])+41,169:_va(parts[6][0])+49,185:_va(parts[5][0])+41,213:_va(parts[3][0]),223:_va(parts[3][0])}
    for at,target in expected.items():require(branch_target(m[at])==target,'quest-state-actual-owned-destination',at)
    for rows,raws in [(parts[2],['488B5C2448','4883C430','5F','C3']),(parts[3],['488B742440','33C0','488B5C2448','4883C430','5F','C3']),(parts[4],['8B4018','488B742440','488B5C2448','4883C430','5F','C3'])]:
        require([_raw(r) for r in rows]==[bytes.fromhex(x) for x in raws],'quest-state-field-zero-return-frame',rows)
    choices={_va(p[32]):False,**{_va(m[a]):False for a in (24,40,137,156,169,185)}};paths=[]
    def walk(va,path):
        require(va in byva and va not in path and len(path)<160 and len(paths)<32,'quest-state-owned-selected-CFG',va);path=path+[va];row=byva[va]
        if row['text']=='ret':paths.append(path);return
        require(row['text']!='int3','quest-state-selected-exception',row)
        if row['text'].startswith('jmp '):walk(branch_target(row),path)
        elif row['text'].startswith(('je ','jne ','jcc ')):
            if choices.get(va) is not False:walk(branch_target(row),path)
            if choices.get(va) is not True:walk(va+len(_raw(row)),path)
        else:walk(va+len(_raw(row)),path)
    walk(_va(p[0]),[]);require(len(paths)==11,'quest-state-eleven-normal-paths',len(paths))
    for path in paths:
        first=path.index(_va(p[13]))+1
        restore=next(i for i,va in enumerate(path) if byva[va]['text']=='mov rbx, [rsp+0x48]')
        watched=[byva[va] for va in path[first:restore]];calls={_va(r) for r in watched if r['text'].startswith('call ')};_register_preserved(watched,{'rbx'},calls)
        original_end=path.index(_va(m[93])) if _va(m[93]) in path else restore
        interval=[byva[va] for va in path[first:original_end]];_register_preserved(interval,{'rdi'},{_va(r) for r in interval if r['text'].startswith('call ')})
        esi_start=path.index(_va(m[5]))+1;esi_end=next(i for i,va in enumerate(path) if byva[va]['text']=='mov rsi, [rsp+0x40]')
        interval=[byva[va] for va in path[esi_start:esi_end]];_register_preserved(interval,{'rsi'},{_va(r) for r in interval if r['text'].startswith('call ')})
    return {'normalPaths':11,'directRecordStateOffset':_raw(parts[4][0])[-1],'parentRecordStateOffset':_raw(m[230])[-1],'returnedStringLengthOffset':_raw(m[110])[-1],'directStorageOffset':int.from_bytes(_raw(m[30])[3:],'little',signed=True),'fallbackStorageOffset':int.from_bytes(_raw(m[175])[3:],'little',signed=True),'fallbackParentCompareBits':int.from_bytes(_raw(m[225])[1:],'little',signed=True),'fallbackOutputBits':int.from_bytes(_raw(m[225])[1:],'little',signed=True),'fallbackOtherBits':0,'dictionaryAPIOrMutationProved':False,'runtimeObserved':False}

def _source_methods(image,specs):
    md=image.metadata;methods={};definitions={}
    for role,spec in specs.items():
        owners=[td for td in md.types if md.type_full_name(td)==spec['type'] and md.string(md.images[image.owners[td.index]].name_index)==spec['image']]
        require(len(owners)==1,'completion-qualified-owner-'+role,len(owners));candidates=[m for m in md.methods_for(owners[0]) if md.string(m.name_index)==spec['method']]
        if role in ('lookup','missionState','questState'):
            matched=[]
            for m in candidates:
                params=md.parameters_for(m)
                if bool(m.flags&0x10)!=(spec['callAbi']=='static') or len(params)!=len(spec['parameters']):continue
                try:
                    for param,token in zip(params,spec['parameters']):_abi(image,param.type_index,token,'completion-parameter-'+role)
                    definition=_class(image,m.return_type) if role=='lookup' else _enum(image,m.return_type,spec['returnType'])
                    require(md.type_full_name(md.types[definition])==spec['returnType'],'completion-return-concrete-'+role,definition)
                except (ValueError,KeyError,IndexError,RuntimeError,struct.error):continue
                matched.append((m,definition))
            require(len(matched)==1,'completion-unique-full-ABI-'+role,[m.index for m,_ in matched]);m,definitions[role]=matched[0]
        else:m=select_ordinary_overload(image,candidates,spec)
        pointer=image.method_pointer_va(m);require(pointer is not None,'completion-actual-pointer-'+role,pointer);methods[role]=(m,pointer)
    require(len({methods[r][0].declaring_type for r in ('lookup','missionState','questState','parentId')})==1,'completion-same-concrete-system',None)
    return methods,definitions


def storage_reference(image,field,record):
    selected=NativeReferenceContext(image);extent=closed_generic_reference_extent(selected,field.type_index)
    owners=[td for td in image.metadata.types if image.metadata.type_full_name(td)=='System.Collections.Generic.Dictionary`2']
    require(len(owners)==1 and owners[0].index==extent['definitionTypeIndex'],'quest-state-declared-storage-definition',extent)
    raw=bytes.fromhex(extent['declaredTypeRecordHex']);generic=int.from_bytes(raw[:8],'little');pe=image.pe
    count,argv=struct.unpack('<QQ',pe.bytes_at_va(pe.u64_at_va(generic+8),16));require(count==2,'quest-state-storage-argument-count',count)
    arguments=[pe.bytes_at_va(pe.u64_at_va(argv+i*8),16) for i in range(2)]
    require(arguments[0][10]==0x0e and arguments[0][11]==0 and arguments[1][10]==0x12 and arguments[1][11]==0 and int.from_bytes(arguments[1][:8],'little')==record,
            'quest-state-storage-ordinary-String-record-arguments',[r.hex() for r in arguments])
    return {**extent,'argumentRawHex':[r.hex().upper() for r in arguments],'actualDictionaryAPIProved':False}


def bind_offsets(proof,fields):
    for key,field in [('directRecordStateOffset','directState'),('parentRecordStateOffset','missionState'),('returnedStringLengthOffset','stringLength'),('directStorageOffset','directStorage'),('fallbackStorageOffset','fallbackStorage')]:
        require(proof[key]==fields[field]['offset'],'quest-state-source-field-displacement',(key,proof[key],fields[field]['offset']))
    return proof


def mapping_aliases(declarations,proof):
    aliases={}
    for label,role,bits in [('compared','missionState',proof['fallbackParentCompareBits']),('equalOutput','questState',proof['fallbackOutputBits']),('otherOutput','questState',proof['fallbackOtherBits'])]:
        matching=[m for m in declarations[role]['members'] if m['id']==bits];require(bool(matching),'quest-state-compared-or-output-declaration',(label,bits));aliases[label]=matching
    return aliases


def validate(image,contract,cache,stored,provider,symbols,message):
    md=image.metadata;pe=image.pe;specs=dict(contract['methods']);specs.update({'patch':provider['methods']['patch'],'lookup':stored['methods']['lookup'],
        'missionState':cache['methods']['missionState'],'questState':cache['methods']['questState'],'constructor':message['methods'][contract['recordDefinitionRole']]})
    methods,definitions=_source_methods(image,specs);direct=methods['constructor'][0].declaring_type;owner=methods['questState'][0].declaring_type;fields={}
    direct_spec=message['fields'][contract['recordFieldRole']];mission_spec=stored['returnedField']
    for role,definition,spec,enum_role in [('directState',direct,direct_spec,'questState'),('missionState',definitions['lookup'],mission_spec,'missionState')]:
        f=_field(image,definition,spec['name'],spec['offset']);require(_enum(image,f.type_index,specs[enum_role]['returnType'])==definitions[enum_role],'quest-state-field-same-return-enum-definition',role)
        fields[role]={'index':f.index,'ownerDefinition':definition,'name':spec['name'],'offset':spec['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    string_spec=provider['stringLength'];owners=[td for td in md.types if md.type_full_name(td)==string_spec['owner']]
    require(len(owners)==1,'quest-state-unique-string-length-owner',len(owners));f=_field(image,owners[0].index,string_spec['name'],string_spec['offset']);_abi(image,f.type_index,'Int32','quest-state-string-length-field')
    fields['stringLength']={'index':f.index,'ownerDefinition':owners[0].index,'name':string_spec['name'],'offset':string_spec['offset'],'rawTypeHex':_type_record(image,f.type_index).hex().upper()}
    for role,record in [('direct',direct),('fallback',definitions['lookup'])]:
        spec=contract['storageFields'][role];f=_field(image,owner,spec['name'],spec['offset']);fields[role+'Storage']={'index':f.index,'ownerDefinition':owner,'name':spec['name'],'offset':spec['offset'],'reference':storage_reference(image,f,record)}
    require(symbols['methodRoles']==['missionState','questState'],'quest-state-declaration-roles',symbols['methodRoles']);defaults=field_defaults(md)
    declarations={r:declared_members(image,definitions[r],specs[r]['returnType'],defaults) for r in symbols['methodRoles']}
    pointer=methods['questState'][1];table_rva,size,table=read_exception_directory(pe);family=UnwindChainIndex(table,lambda rva,n:pe.bytes_at_va(pe.image_base+rva,n),table_rva=table_rva,image_size=size).family(pointer-pe.image_base)
    require(len(family['ranges'])==8,'quest-state-eight-declared-owned-ranges',len(family['ranges']));parts=[];windows=[]
    for part in family['ranges']:
        begin,end,_=part['runtimeTriple'];require(0<end-begin<=512,'quest-state-bounded-owned-range',part)
        raw=pe.bytes_at_va(pe.image_base+begin,end-begin);parts.append(_instruction_partition(raw,pe.image_base+begin,_composed_decoder(image.mapper)))
        windows.append({'runtimeTriple':part['runtimeTriple'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest().upper(),'parentChain':part['parentChain']})
    require(_va(parts[0][0])==pointer,'quest-state-actual-primary-start',pointer)
    proof=check_sources(parts,contract['programs'],methods['patch'][1],methods['parentId'][1]);bind_offsets(proof,fields)
    aliases=mapping_aliases(declarations,proof)
    proof.update({'fields':fields,'enumDeclarations':declarations,'mappingAliases':aliases,'windows':windows,
                  'methods':{r:{'index':m.index,'rva':p-pe.image_base,'ownerDefinition':m.declaring_type,'rawReturnTypeHex':_type_record(image,m.return_type).hex().upper()} for r,(m,p) in methods.items()},
                  'directSlotCompatibleTypeDefinition':direct,'fallbackSlotCompatibleTypeDefinition':definitions['lookup'],'returnedStringHierarchyOrSameRecordProved':False,'completeManagedProgramProved':False})
    return proof

@authenticate_native_proof(lambda:CONTRACT)
def validate_native_claims(gameassembly,metadata,inputs):
    contract,_=read_reviewed_contract(CONTRACT,schema=SCHEMA,status='reviewed',label='quest_state_value_source')
    cache,stored,provider,symbols,message=[read_reviewed_contract(CONTRACTS_DIR/d['path'],schema=d['schema'],status=d['status'],label='completion_dependency')[0] for d in contract['dependencies']]
    by={Path(row['path']).name:row for row in inputs}
    gate=check_installed_native_inputs(by['GameAssembly.dll']['sha256'],by['global-metadata.dat']['sha256'],gameassembly=gameassembly,metadata=metadata)
    require(gate.status==NATIVE_EVIDENCE_VALIDATED,'native-inputs',f'{gate.status}:{gate.detail}')
    proof=validate(open_native_image(gameassembly,metadata),contract,cache,stored,provider,symbols,message)
    return {'format':'endfield.dynamic-quest-state-value-source-native-audit.v1','status':'validated','proof':proof,
            'nativeInputs':{name:row['sha256'] for name,row in by.items()},'evidenceBoundary':contract['evidenceBoundary']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/animestudio/dynamic_quest_state_value_source_native_latest.json')
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
        print('quest-state-value-source:'+str(exc)[:1400],file=sys.stderr);return 1
    print('Quest state value sources passed: conditional field/constant returns; dictionary API/live state unresolved')
    return 0
if __name__=='__main__':raise SystemExit(main())
