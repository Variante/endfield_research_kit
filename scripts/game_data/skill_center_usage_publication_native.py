"""Original usage-cell fetch-add/read and conditional exchange publication.

This joins an on-disk Center tag3 request to the existing plain definition
cache program. Atomic publication is not a CAS winner test or runtime evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_creation_instructions import decode_generic_creation_instructions
from scripts.game_data.il2cpp.generic_creation_control import generic_memory_effect
from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
from scripts.game_data.il2cpp.type_data_initialization_control import _complete
from scripts.game_data.il2cpp.enum_encoded_method_paths import program as encoded_program
from scripts.game_data.skill_pending_storage_native import _match
from scripts.game_data.skill_timing_runtime_native import _require
from scripts.game_data import skill_center_method_info_native as method_info
from scripts.game_data import skill_center_delegate_native as delegate

SCHEMA='endfield.skill-center-usage-publication-native-contract.v1'
AUDIT_SCHEMA='endfield.skill-center-usage-publication-native-audit.v1'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_usage_publication_native.json'
DEPS={'methodInfo':('skill_center_method_info_native.json',method_info.SCHEMA),
      'delegate':('skill_center_delegate_native.json',delegate.SCHEMA)}

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)
def _rules():
    return dict(originalProgramOnly=True,usageTag3PublicationCfgProved=True,
        completeUpdaterPartitionCfgAndFramesProved=True,atomicReadIsFetchAddZero=True,
        publicationIsExchangeNotCompareExchange=True,nonnullResolverReturnRequiredForExchange=True,
        returnsComputedPointerAfterExchange=True,tag3DispatchPreservesEncodedWord=True,
        usageInitializationToDefinitionCacheProved=True,constructorSelectedCellInitializationRequestProved=True,
        constructorReadyStoreAfterNormalCallsProved=True,independentConcurrentCellChangesPermitted=True,
        constructorReadyImpliesNonNullCellsProved=False,runtimeUsageInitializationObserved=False,
        actualToSkillMethodInfoContentsProved=False,liveCacheIdentityProved=False,
        runtimeOriginalImplementationObserved=False,wholeOtherUsageKindsProved=False)

def _rows():
    return [dict(id=k,evidence='conditional')for k in
        ['hotReadyWord','tag3NullResolution','tag3PublishComputed','constructorReadySkip','constructorInitializesCell']]

def _programs(c):
    h=bytes.fromhex;O=lambda k,w=1:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    op=c['operands'];spans={r['id']:r for r in c['spans']}
    targets={**op,'readyCompareRelativeEnd':op['readyFlagCell']-1,'readyStoreRelativeEnd':op['readyFlagCell']-1}
    p={
      'updaterEntry':[h('48895c24'),O('saveRbx'),h('574883ec'),O('updaterFrame'),
        h('33db488bf98bcbf0480fc10ff6c1'),O('unresolvedMask'),h('75'),R('unresolvedRva',1),
        h('488bc1488b5c24'),O('restoreRbx'),h('4883c4'),O('updaterFrame'),h('5fc3')],
      'updaterSwitch':[h('48897424'),O('saveRsi'),h('8bc1c1e8'),O('kindShift'),
        h('8bf1d1ee81e6'),O('indexMask',4),h('ffc883f8'),O('maxKindIndex'),h('77'),R('noResultRva',1),
        h('4c8d05'),R('imageBaseRva'),h('4898418b9480'),O('tableRva',4),h('4903d0ffe2')],
      'tag3Result':[h('e8'),R('encodedRva'),h('488bd84885db74'),R('noResultRva',1),
        h('488bc3488707488b7424'),O('saveRsi'),h('488bc3eb'),R('restoreRva',1)],
      'constructorPrefix':[h('48895c24'),O('ctorSaveRbx'),h('48896c24'),O('ctorSaveRbp'),
        h('48897424'),O('ctorSaveRsi'),h('574883ec'),O('ctorFrame'),h('803d'),R('readyCompareRelativeEnd'),
        h('00498bf8488bf2488bd90f85'),R('constructorResumeRva')],
      'constructorReady':[h('c605'),R('readyStoreRelativeEnd'),O('readyStoreValue')],
    }
    _require(len(spans)==len(c['spans'])and set(spans)==set(p)|{'constructorCells'},
        'centerUsage.program-coverage',sorted(set(p)|{'constructorCells'}),sorted(spans))
    _require(all(type(v)is int for v in op.values()),'centerUsage.operand-types','ordinary integer operands',op)
    for key,parts in p.items():
        _require(_match(bytes.fromhex(spans[key]['hex']),spans[key]['rva'],parts,{},op,targets),
            'centerUsage.semantic-program',key,spans[key]['hex'])
    end=lambda key:spans[key]['rva']+len(bytes.fromhex(spans[key]['hex']))
    _require(end('updaterEntry')==spans['updaterSwitch']['rva']==op['unresolvedRva']and
        end('updaterSwitch')==spans['tag3Result']['rva'] and
        end('constructorPrefix')==spans['constructorCells']['rva']and
        end('constructorCells')==spans['constructorReady']['rva']and end('constructorReady')==op['constructorResumeRva'],
        'centerUsage.contiguous-edges','selected updater and constructor local CFG',op)
    _require(op['unresolvedMask']==1 and op['readyStoreValue']==1 and op['maxKindIndex']==6 and
        op['imageBaseRva']==0 and op['restoreRva']==spans['updaterEntry']['rva']+30 and
        op['noResultRva']==spans['tag3Result']['rva']+19,
        'centerUsage.selected-layout','low-bit unresolved tag, seven table kinds, exact restore locations',op)
    return spans

def _constructor_requests(c,spans,selected_cell):
    span=spans['constructorCells'];raw=bytes.fromhex(span['hex']);requests=[]
    _require(raw and len(raw)%12==0,'centerUsage.constructor-request-partition','LEA RCX/call pairs',len(raw))
    for offset in range(0,len(raw),12):
        at=span['rva']+offset;code=raw[offset:offset+12]
        _require(code[:3]==bytes.fromhex('488d0d')and code[7]==0xe8,
            'centerUsage.constructor-request-grammar','LEA cell address into RCX then direct call',at)
        cell=at+7+struct.unpack_from('<i',code,3)[0];target=at+12+struct.unpack_from('<i',code,8)[0]
        _require(target==c['functions']['updater'],'centerUsage.constructor-request-target','same proved updater',target)
        requests.append(dict(cellRva=cell,callRva=at+7))
    selected=[r for r in requests if r['cellRva']==selected_cell]
    _require(len(selected)==1,'centerUsage.constructor-selected-cell','one original same-cell initialization request',selected)
    return dict(normalCallCount=len(requests),selected=selected[0])

def _regions(image,c,role):
    entry=c['functions'][role];expected=[[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role]
    actual=[r['runtimeTriple'][:2]for r in image.unwind_index.family(entry)['ranges']]
    _require(actual==expected,'centerUsage.complete-family',role,actual)
    return [(image.pe.image_base+a,image.pe.bytes_at_va(image.pe.image_base+a,b-a))for a,b in actual]

def _updater_graph(image,c,regions):
    base=image.pe.image_base;pieces=c['pieces'];owned=[(a,a+len(raw))for a,raw in regions]
    check_byte_partition(owned,[(base+p['startRva'],base+p['endRva'],p['kind'])for p in pieces],'centerUsage')
    rows=[];tables=[]
    for piece in pieces:
        a,b=piece['startRva'],piece['endRva'];raw=image.pe.bytes_at_va(base+a,b-a)
        if piece['kind']=='code':rows+=checked_rows(decode_generic_creation_instructions(image.mapper,raw,base+a),raw,'centerUsage')
        elif piece['kind']=='padding':_require(raw==bytes.fromhex('0f1f00'),'centerUsage.padding','unreferenced three-byte NOP',raw.hex())
        elif piece['kind']=='table':tables.append((a,raw))
        else:raise ValueError('centerUsage.unknown-piece-kind')
    _require(len(tables)==1 and tables[0][0]==c['operands']['tableRva'] and len(tables[0][1])==4*(c['operands']['maxKindIndex']+1),
        'centerUsage.table-geometry','one bounded seven-entry RVA table',tables)
    targets=[base+r for(r,)in struct.iter_unpack('<i',tables[0][1])]
    _require(targets[2]==base+next(s['rva']for s in c['spans']if s['id']=='tag3Result'),
        'centerUsage.tag3-table-target','actual tag3 index 3-1 selects encoded-method call',targets[2]-base)
    graph=_complete(rows,base+c['functions']['updater'],table_targets={base+c['operands']['tableJumpRva']:set(targets)},
        memory_effect_decoder=generic_memory_effect)
    starts={int(r['va'],16)for r in rows};ends={int(r['va'],16)+len(bytes.fromhex(r['bytes']))for r in rows}
    for span in c['spans']:
        if span['owner']=='updater':
            _require(base+span['rva']in starts and base+span['rva']+len(bytes.fromhex(span['hex']))in ends,
                'centerUsage.instruction-anchor','complete updater instructions',span['id'])
    return graph

def _validate(image,c,deps):
    spans=_programs(c);image.validate_method_row(c['constructor'],label='centerUsage.constructor')
    _require(c['constructor'][1:3]==['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine','.ctor']and
        c['constructor'][3]==c['functions']['constructor'],'centerUsage.constructor-owner','named original Center constructor',c['constructor'])
    image.check_windows(c['codeWindows'],label='centerUsage');families={role:_regions(image,c,role)for role in c['functions']}
    for span in spans.values():
        raw=bytes.fromhex(span['hex']);a=span['rva'];b=a+len(raw)
        _require(span['owner']in families and any(lo<=image.pe.image_base+a and image.pe.image_base+b<=lo+len(data)for lo,data in families[span['owner']])and
            image.pe.bytes_at_va(image.pe.image_base+a,len(raw))==raw,
            'centerUsage.actual-owned-span','actual bytes in selected related family',span['id'])
    graph=_updater_graph(image,c,families['updater']);prior=method_info._validate(image,deps['methodInfo'],deps['delegate'])
    dep=deps['methodInfo'];base=image.pe.image_base;op=c['operands']
    _require(c['functions']['updater']==spans['updaterEntry']['rva']and
        op['encodedRva']==dep['functions']['encoded'],'centerUsage.actual-resolver-call','existing encoded method resolver',op['encodedRva'])
    encoded_regions=[(base+w['startRva'],image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva']))for w in dep['codeWindows']if w['owner']=='encoded']
    encoded=encoded_program(encoded_regions,base+op['encodedRva'],tag=3)
    _require(encoded['tailTarget']==base+dep['functions']['definition']and op['kindShift']==encoded['kindShift']and
        op['indexMask']==encoded['definitionOrSpecIndexMask'],'centerUsage.definition-cache-join','same actual tag3 definition-cache request',encoded)
    constructor=_constructor_requests(c,spans,prior['usageCellRva'])
    _require(_same(c['rules'],_rules())and _same(c['rows'],_rows()),'centerUsage.rules-and-rows',_rules(),c['rules'])
    return dict(rules=_rules(),rows=_rows(),updaterInstructions=graph['instructions'],
        usageCellRva=prior['usageCellRva'],constructorRequest=constructor,
        semanticParameters=dict(unresolvedMask=op['unresolvedMask'],kindShift=op['kindShift'],tag3=3,
            atomicWordBits=64,encodedRequestBits=32,encodedMask=(1<<32)-1,kindMask=7,indexMask=op['indexMask'],
            publication='atomic-exchange',initialRead='atomic-fetch-add-zero',
            constructorReadyValue=op['readyStoreValue']),evidenceBoundary=c['evidenceBoundary'])

def load_skill_center_usage_publication(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerUsage');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata);deps={};snapshots={path:digest}
        for key,(name,schema)in DEPS.items():
            p=CONTRACTS_DIR/name;dep,d=read_reviewed_contract(p,schema=schema,status='reviewed',label='centerUsage.'+key)
            _require(_same(dep['nativeInputs'],pins),'centerUsage.dependency-build',pins,dep['nativeInputs'])
            deps[key]=dep;snapshots[p]=d
        result=_validate(image,c,deps)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and all(hashlib.sha256(p.read_bytes()).hexdigest().upper()==d for p,d in snapshots.items()),
            'centerUsage.input-bookend','unchanged selected native and contracts',after.detail)
        audit.update(status='validated-conditional-usage-publication',detail='',nativeInputs=pins,**result)
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error,StopIteration)as exc:
        audit.update(status='validation_failed',detail=str(exc)[:1200],rules={},rows=[],nativeInputs={},failures=[dict(check=str(exc).split(':',1)[0],detail=str(exc)[:1200])])
    return audit

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--gameassembly',type=Path,required=True);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('reports/skill_center_usage_publication_native.json'));args=parser.parse_args()
    output=args.output.resolve();reports=(Path(__file__).resolve().parents[2]/'reports').resolve()
    if not output.is_relative_to(reports):parser.error('--output must remain under repository reports/')
    audit=load_skill_center_usage_publication(gameassembly=args.gameassembly,metadata=args.metadata)
    if audit['status']!='validated-conditional-usage-publication':
        print(f"{audit['status']}: publication skipped; existing report untouched")
        if audit.get('detail'):print(audit['detail'])
        return 1
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{audit['status']}: rows={len(audit['rows'])} output={output}");return 0

if __name__=='__main__':raise SystemExit(main())
