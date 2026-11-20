"""Plain MethodInfo source fragments; runtime descriptor contents stay unknown."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.enum_plain_method_descriptor_paths import decode,record_program,publication_program,preserve_until,token_program
from scripts.game_data.il2cpp.enum_method_key_construction import definition_program
from scripts.game_data.il2cpp.enum_encoded_method_paths import program as encoded_program
from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.skill_pending_storage_native import _match
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data import skill_center_delegate_native as delegate

SCHEMA='endfield.skill-center-method-info-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-method-info-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_method_info_native.json'

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
def _rules():
    return dict(originalPathOnly=True,secondaryPointerFallbackCfgProved=True,
        plainDescriptorFieldCopiesProved=True,flags54UpdateCfgProved=True,
        genericContainerLeafPreservesR8=True,tag3UsageDefinitionRequestProved=True,
        completeMaterializerCfgAndNormalFramesProved=True,independentHeapReadsRequired=True,
        unmodifiedSavedMetadataStackLocalsRequired=True,
        runtimeMethodInfoIdentityProved=False,actualToSkillMethodInfoContentsProved=False,
        wholeMethodPopulationProved=False,descriptorLifetimeProved=False,
        usageInitializationToDefinitionCacheProved=False)

def _rows():
    return [dict(id=k,evidence='conditional')for k in
        ['pointerFallback','metadataFieldCopies','flags54Update','usageTag3DefinitionRequest']]

def _programs(c):
    h=bytes.fromhex;O=lambda k,w=1:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    op=c['operands'];s={r['id']:r for r in c['spans']};b=op['descriptorBias']
    offsets={key+'Relative':value-b for key,value in c['descriptorSlots'].items()}
    op={**op,**offsets,'clear2Signed':op['clear2Mask']-256,'clear8Signed':op['clear8Mask']-256}
    p={
      'pointerFallback':[h('48837b'),O('primaryCodeRelative'),h('0075'),R('pointerFallbackEnd',1),
        h('488b43'),O('baseCodeRelative'),h('488943'),O('primaryCodeRelative')],
      'recordFields':[h('0fb745'),O('recordFlagsOffset'),h('66898424'),O('flagsLocal',4),
        h('0fb745'),O('recordIflagsOffset'),h('66898424'),O('iflagsLocal',4),
        h('0fb745'),O('recordSlotOffset'),h('66898424'),O('slotLocal',4),h('440fb77d'),O('recordCountOffset')],
      'parameterCount':[h('44887b'),O('parameterCountRelative')],
      'flagsCopies':[h('0fb78424'),O('flagsLocal',4),h('668943'),O('flagsRelative'),
        h('0fb78424'),O('iflagsLocal',4),h('668943'),O('iflagsRelative'),
        h('0fb78424'),O('slotLocal',4),h('668943'),O('slotRelative')],
      'clearInflated':[h('440fb643'),O('flags54Relative'),h('4180e0'),O('clear2Signed'),
        h('448843'),O('flags54Relative')],
      'genericFlags':[h('44896b'),O('tokenRelative'),h('48896b'),O('recordRelative'),
        h('8b4d'),O('recordGenericOffset'),h('e8'),R('genericLeafRva'),h('488943'),O('genericContainerRelative'),
        h('4885c00f85'),R('genericPresentRva'),h('8063'),O('flags54Relative'),O('clear8Signed')],
      'genericPresent':[h('4180c8'),O('set1Mask'),h('448843'),O('flags54Relative'),h('e9'),R('clear8Rva')],
      'genericLeaf':[h('83f9ff75'),R('genericLeafNonNullRva',1),h('33c0c3488b05'),R('metadataHeaderCell'),
        h('486350'),O('genericSectionHeaderOffset'),h('480315'),R('metadataBaseCell'),
        h('4863c148c1e0'),O('genericRecordShift'),h('4803c2c3')],
      'setupCall':[h('488d5424'),O('wrapperLocal'),h('488bcbe8'),R('materializerRva')],
      'primaryCode':[h('418bc525ffffff000f84'),R('primaryNullRva'),
        h('8d50ff488b06488b48'),O('imageCodeModuleOffset'),h('488b41'),O('moduleCodeArrayOffset'),
        h('488b04d0488943'),O('baseCodeRelative')],
    }
    _require(len(s)==len(c['spans'])and set(s)==set(p),'centerMethodInfo.program-coverage',sorted(p),sorted(s))
    _require(all(type(v)is int for v in op.values()),'centerMethodInfo.operands','integer operands',op)
    for key,parts in p.items():
        _require(_match(bytes.fromhex(s[key]['hex']),s[key]['rva'],parts,{},op,op),
            'centerMethodInfo.semantic-program',key,s[key]['hex'])
    end=lambda key:s[key]['rva']+len(bytes.fromhex(s[key]['hex']))
    _require(end('pointerFallback')==op['pointerFallbackEnd']and end('clearInflated')==s['genericFlags']['rva'] and
        op['clear8Rva']==end('genericFlags')-4 and op['genericPresentRva']==s['genericPresent']['rva'] and
        op['genericLeafRva']==s['genericLeaf']['rva'] and op['genericLeafNonNullRva']==s['genericLeaf']['rva']+8,
        'centerMethodInfo.fragment-edges','closed fallback/flag/leaf local branches',op)
    _require((op['clear2Mask'],op['clear8Mask'],op['set1Mask'])==(253,247,1),
        'centerMethodInfo.flag-masks','clear 0x02, optional set 0x01, independent clear 0x08',op)
    return s

def _family(image,c,role):
    entry=c['functions'][role];windows=[w for w in c['codeWindows']if w['owner']==role]
    actual=[r['runtimeTriple'][:2]for r in image.unwind_index.family(entry)['ranges']]
    _require(actual==[[w['startRva'],w['endRva']]for w in windows],
        'centerMethodInfo.complete-family',role,actual)
    return [(image.pe.image_base+w['startRva'],image.pe.bytes_at_va(image.pe.image_base+w['startRva'],w['endRva']-w['startRva']))for w in windows]

def _metadata_layout(c,md):
    # This is the maintained metadata reader's record shape, including v31's
    # optional return-parameter token. It is not a build-address catalog.
    pos=12+(4 if md.version>=31 else 0)
    expected=dict(recordFlagsOffset=pos+12,recordIflagsOffset=pos+14,
        recordSlotOffset=pos+16,recordCountOffset=pos+18,recordGenericOffset=pos+4)
    actual={key:c['operands'][key]for key in expected}
    _require(_same(actual,expected)and md.method_record_size==pos+20,
        'centerMethodInfo.record-layout',expected,actual)
    section=md.sections['genericContainers'];op=c['operands']
    _require(struct.unpack_from('<I',md.buf,op['genericSectionHeaderOffset'])[0]==section.offset and
        1<<op['genericRecordShift']==struct.calcsize('<iiii') and section.size%struct.calcsize('<iiii')==0,
        'centerMethodInfo.generic-section','actual metadata genericContainers section and four-int32 stride',op)

def _span_anchors(spans,owner,rows,base):
    starts={int(row['va'],16)for row in rows};ends={int(row['va'],16)+len(bytes.fromhex(row['bytes']))for row in rows}
    for span in spans.values():
        if span['owner']!=owner:continue
        start=base+span['rva'];end=start+len(bytes.fromhex(span['hex']))
        _require(start in starts and end in ends,'centerMethodInfo.instruction-anchors',owner,span['id'])

def _delegate_join(image,c,dep):
    _require(_same(c['nativeInputs'],dep['nativeInputs']),'centerMethodInfo.delegate-build',c['nativeInputs'],dep['nativeInputs'])
    offsets={f['id']:f['offset']for f in dep['fields']}
    # The maintained initializer grammar includes both resolver returns and
    # every physical flag-reading path. Compare its actual selected bytes too.
    delegate._programs(dep,offsets);image.check_windows(dep['codeWindows'],label='centerMethodInfo.delegate')
    for span in dep['spans']:
        raw=bytes.fromhex(span['hex'])
        _require(image.pe.bytes_at_va(image.pe.image_base+span['rva'],len(raw))==raw,
            'centerMethodInfo.delegate-span','actual validated consumer bytes',span['id'])
    slots=c['descriptorSlots'];op=dep['operands']
    _require((slots['primaryCode'],slots['flags'],slots['parameterCount'],slots['flags54'],c['alternateCodeOffset'])==
        (op['primaryCodeOffset'],op['flag4cOffset'],op['byte53Offset'],op['flag54Offset'],op['alternateCodeOffset']) and
        (~c['operands']['clear2Mask'])&255==op['resolverFlagMask'],
        'centerMethodInfo.delegate-slot-join','same source-populated and resolver-read MethodInfo slots',slots)

def _validate(image,c,delegate_contract):
    image.validate_method_row(c['predicate'],label='centerMethodInfo.predicate')
    _require(c['predicate'][1:3]==['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','_ToSkill'],
        'centerMethodInfo.predicate-name','CenterStateMachine._ToSkill',c['predicate'])
    image.check_windows(c['codeWindows'],label='centerMethodInfo');spans=_programs(c);base=image.pe.image_base;op=c['operands']
    _metadata_layout(c,image.metadata);_delegate_join(image,c,delegate_contract)
    families={role:_family(image,c,role)for role in c['functions']}
    for key,span in spans.items():
        raw=bytes.fromhex(span['hex']);at=base+span['rva']
        owner='genericLeaf'if key=='genericLeaf'else'setupWrapper'if key=='setupCall'else'materializer'
        _require(image.pe.bytes_at_va(at,len(raw))==raw and span['owner']==owner and
            any(w['owner']==owner and w['startRva']<=span['rva'] and span['rva']+len(raw)<=w['endRva']for w in c['codeWindows']),
            'centerMethodInfo.actual-span','actual bytes within selected owner',key)
    rows=[]
    for at,raw in families['materializer']:rows+=checked_rows(decode(image.mapper,raw,at),raw,'centerMethodInfo.materializer')
    rows.sort(key=lambda row:int(row['va'],16))
    _span_anchors(spans,'materializer',rows,base)
    graph,padding=complete_program(families['materializer'],rows,base+op['materializerRva'],
        recursive_calls={base+op['selfCallRva']:base+op['materializerRva']})
    _require(not padding and graph['normalFramesProved'],'centerMethodInfo.materializer-cfg','all bytes and normal frames',padding)
    record=record_program(families['materializer'],base+op['recordSelectorRva'])
    publication=publication_program(families['materializer'],base+op['publicationRva'],loop_entry=base+op['recordSelectorRva'])
    token=token_program(families['materializer'],base+op['tokenStoreRva'])
    _require(c['descriptorSlots']['token']==token['tokenDescriptorOffset'] and
        c['descriptorSlots']['record']==token['metadataRecordDescriptorOffset'],
        'centerMethodInfo.descriptor-base','same separately parsed descriptor-relative record and token stores',token)
    wrapper_rows=[]
    for at,raw in families['setupWrapper']:wrapper_rows+=checked_rows(decode(image.mapper,raw,at),raw,'centerMethodInfo.setupWrapper')
    _span_anchors(spans,'setupWrapper',wrapper_rows,base)
    # Register provenance crosses the intervening parameter-list branches only
    # through actual nonvolatile carriers; opaque memory effects stay premises.
    preserve_until(graph,rows,base+op['materializerRva'],record['tokenLoad'],base+spans['flagsCopies']['rva'],('rbp','rbx'))
    preserve_until(graph,rows,base+op['materializerRva'],base+spans['recordFields']['rva'],base+spans['parameterCount']['rva'],('rbp','rbx'))
    preserve_until(graph,rows,base+op['materializerRva'],base+spans['recordFields']['rva']+len(bytes.fromhex(spans['recordFields']['hex'])),
        base+spans['parameterCount']['rva'],('r15','rbx'))
    definitions=[definition_program(families['definition'],base+c['functions']['definition'],cold=cold)for cold in (False,True)]
    encoded=encoded_program(families['encoded'],base+c['functions']['encoded'],tag=3)
    _require(encoded['tailTarget']==base+c['functions']['definition'] and definitions[1]['methodSetupTarget']==base+c['functions']['setupWrapper'] and
        record['metadataHeaderCell']==definitions[1]['metadataHeaderCell']==base+op['metadataHeaderCell'] and
        record['metadataBaseCell']==definitions[1]['metadataBaseCell']==base+op['metadataBaseCell'],
        'centerMethodInfo.resolver-links','same encoded definition/class setup/metadata source',definitions[1])
    usage_at=c['usageInstructionRva'];raw=image.pe.bytes_at_va(base+usage_at,7)
    _require(raw[:3]==bytes.fromhex('4c8b05'),'centerMethodInfo.usage-load','R8 RIP-relative MethodInfo request',raw.hex())
    cell=usage_at+7+struct.unpack_from('<i',raw,3)[0]
    usage=image.pe.bytes_at_va(base+cell,8)
    index=unresolved_usage_index(usage,len(image.metadata.methods),tag=3,source='centerMethodInfo.usage',offset=cell)
    _require(index==c['predicate'][0],'centerMethodInfo.usage-definition',c['predicate'][0],index)
    md=image.metadata;m=md.methods[index];td=md.types[m.declaring_type];section=md.sections['methods']
    record_raw=md.buf[section.offset+index*md.method_record_size:section.offset+(index+1)*md.method_record_size]
    _require(md.method_record_size==record['methodRecordBytes']==32 and struct.unpack_from('<I',md.buf,record['methodSectionHeaderOffset'])[0]==section.offset,
        'centerMethodInfo.metadata-section','same selected 32-byte method record section',md.method_record_size)
    actual=dict(methodIndex=index,declaringTypeDefinition=m.declaring_type,classMethodStart=td.method_start,
        ordinal=index-td.method_start,flags=struct.unpack_from('<H',record_raw,24)[0],
        parameterCount=struct.unpack_from('<H',record_raw,30)[0],genericContainerIndex=struct.unpack_from('<i',record_raw,16)[0],
        token=struct.unpack_from('<I',record_raw,20)[0],rawRecordHex=record_raw.hex())
    _require(td.method_start<=index<td.method_start+td.method_count and actual['flags']==m.flags and
        actual['parameterCount']==m.parameter_count and _same(actual,c['selectedMetadataRecord']),
        'centerMethodInfo.selected-record',c['selectedMetadataRecord'],actual)
    _require(publication['descriptorStride']==c['descriptorStride'] and c['descriptorSlots']['flags54']<c['descriptorStride']<=c['alternateCodeOffset'],
        'centerMethodInfo.descriptor-extent','alternate code slot not populated by this plain descriptor stride',publication)
    _require(_same(c['rules'],_rules()) and _same(c['rows'],_rows()),'centerMethodInfo.rules',_rules(),c['rules'])
    return dict(rows=_rows(),rules=_rules(),selectedMetadataRecord=actual,
        semanticParameters=dict(descriptorBias=op['descriptorBias'],descriptorStride=c['descriptorStride'],
            slots=c['descriptorSlots'],alternateCodeOffset=c['alternateCodeOffset'],clearMask=op['clear2Mask'],
            optionalOrMask=op['set1Mask'],finalIndependentAndMask=op['clear8Mask']),
        materializerInstructions=len(rows),usageCellRva=cell,evidenceBoundary=c['evidenceBoundary'])

def load_skill_center_method_info(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerMethodInfo');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata)
        dep_path=CONTRACTS_DIR/'skill_center_delegate_native.json'
        dep,dep_digest=read_reviewed_contract(dep_path,schema=delegate.SCHEMA,status='reviewed',label='centerMethodInfo.delegate')
        result=_validate(image,c,dep)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest and
            hashlib.sha256(dep_path.read_bytes()).hexdigest().upper()==dep_digest,
            'centerMethodInfo.input-bookend','unchanged selected native and contract',after.detail)
        audit.update(status='validated-conditional-method-info-fragments',detail='',nativeInputs=pins,**result)
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error,StopIteration)as exc:
        audit.update(status='validation_failed',detail=str(exc)[:1200],rules={},rows=[],nativeInputs={},failures=[dict(check=str(exc).split(':',1)[0],detail=str(exc)[:1200])])
    return audit

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('reports/skill_center_method_info_native.json'));args=parser.parse_args()
    output=args.output.resolve();reports=(Path(__file__).resolve().parents[2]/'reports').resolve()
    if not output.is_relative_to(reports):parser.error('--output must remain under repository reports/')
    audit=load_skill_center_method_info(gameassembly=args.gameassembly,metadata=args.metadata)
    if audit['status']!='validated-conditional-method-info-fragments':
        print(f"{audit['status']}: publication skipped; existing report untouched")
        if audit.get('detail'):print(audit['detail'])
        return 1
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{audit['status']}: rows={len(audit['rows'])} output={output}");return 0

if __name__=='__main__':raise SystemExit(main())
