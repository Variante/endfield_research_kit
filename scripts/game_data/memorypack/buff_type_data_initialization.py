"""Selected native registration publication and type-data initialization proofs."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
from scripts.game_data.il2cpp.type_data_initialization_instructions import decode_type_data_initialization_instructions
from scripts.game_data.il2cpp.type_data_initialization_control import validate_type_data_initialization
from .core import CONTRACTS_DIR

LABEL='buffTypeDataInitialization'
SCHEMA='endfield.buff-type-data-initialization-native-contract.v1'
SCOPE='complete-registration-and-type-initialization-control-with-conditional-record-pointer-writeback'
CONTRACT_PATH=CONTRACTS_DIR/'buff_type_data_initialization_native.json'
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'scope':SCOPE,'wholeRootAdmitted':False,
        'runtimeExecutionKnown':False,'concreteDamageTypeClassOrSharingProved':False}
def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    programs={}
    for role,f in c['functions'].items():
        if f['ownershipKind']=='exceptionFamily':
            actual=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if actual!=f['unwindFamily']:raise ValueError(LABEL+'.exception-family:'+role)
            owned=[tuple(p['runtimeTriple'][:2]) for p in actual['ranges']]
        elif f['ownershipKind']=='closedEntryProgram':
            if f['entryRva'] in unwind.entries or f['unwindFamily'] is not None or len(f['codeWindows'])!=1:raise ValueError(LABEL+'.ordinary-entry-ownership')
            owned=[(f['codeWindows'][0]['startRva'],f['codeWindows'][0]['endRva'])]
        else:raise ValueError(LABEL+'.ownership-kind')
        pieces=[];rows=[]
        for kind in ('codeWindows','paddingWindows','tableWindows'):
            image.check_windows(f[kind],label=LABEL+'.'+role+'.'+kind)
            for w in f[kind]:
                start,end=w['startRva'],w['endRva'];b=image.pe.bytes_at_va(base+start,end-start);pieces.append((start,end,kind))
                if kind=='codeWindows':rows.extend(checked_rows(decode_type_data_initialization_instructions(image.mapper,b,base+start),b,LABEL+'.'+role))
                elif kind=='paddingWindows' and b!=bytes.fromhex(w['rawHex']):raise ValueError(LABEL+'.padding-bytes')
        check_byte_partition(owned,pieces,LABEL+'.'+role);programs[role]=rows
    p=c['staticRegistrations']
    if (base+p['metadataRva'],base+p['codeRva'])!=(image.metadata_registration,image.code_registration):raise ValueError(LABEL+'.static-registration-identity')
    old,_=read_reviewed_contract(CONTRACTS_DIR/'buff_class_name_lookup_native.json',schema='endfield.buff-class-name-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    init,_=read_reviewed_contract(CONTRACTS_DIR/'buff_formatter_metadata_initialization_native.json',schema='endfield.buff-formatter-metadata-initialization-native-contract.v1',status='exact-current-build',label=LABEL)
    enum,_=read_reviewed_contract(CONTRACTS_DIR/'buff_enum_underlying_native.json',schema='endfield.buff-enum-underlying-native-contract.v1',status='exact-current-build',label=LABEL)
    if any(old['nativeInputs']!=other['nativeInputs'] for other in (init,enum,c)):raise ValueError(LABEL+'.same-selected-native-inputs')
    if c['globals']['metadataRegistration']!=old['globals']['metadataRegistration'] or c['globals']['metadataHeader']!=old['globals']['metadataHeader'] or c['globals']['metadataBase']!=old['globals']['metadataBase']:raise ValueError(LABEL+'.same-consumer-global-cells')
    if c['recordGeometry']!={'recordBytes':old['layout']['typeRecordBytes'],'headerOffsetField':old['layout']['typeDefinitionsHeader']}:raise ValueError(LABEL+'.same-record-geometry')
    if c['functions']['metadataInitializer']['entryRva']!=init['function']['entryRva'] or c['functions']['typeLoop']['entryRva']!=init['postInitializeEntryRva']:raise ValueError(LABEL+'.same-initializer-entries')
    t=c['dispatch'];tables={'selector':image.pe.bytes_at_va(base+t['selectorRva'],t['maxKindIndex']+1),
        'targets':image.pe.bytes_at_va(base+t['targetsRva'],t['targetCount']*4)}
    selected=c['selectedDamageType'];d=enum['selectedDamageTypeMetadata']
    if (selected['typePointerVa'],selected['byvalTypeIndex'],selected['storedSignedIndex'],selected['kindByte'])!=(d['typePointerVa'],d['byvalTypeIndex'],d['typeDefinition'],17):raise ValueError(LABEL+'.same-static-damage-record')
    raw_type=image.pe.bytes_at_va(selected['typePointerVa'],16)
    if raw_type.hex().upper()!=d['rawTypeHex']:raise ValueError(LABEL+'.static-damage-record-bytes')
    layout=c['layout'];registration=base+p['metadataRva']
    count=int.from_bytes(image.pe.bytes_at_va(registration+layout['typesCount'],4),'little',signed=True)
    types=image.pe.u64_at_va(registration+layout['typesPointer'])
    if count!=image.registration['typesCount'] or types!=int(image.registration['types'],16):raise ValueError(LABEL+'.static-types-table-fields')
    type_table=image.pe.bytes_at_va(types,count*8);ptr=selected['typePointerVa']
    entries=[int.from_bytes(type_table[i:i+8],'little') for i in range(0,len(type_table),8)]
    index=selected['byvalTypeIndex']
    if not 0<=index<count or entries[index]!=ptr:raise ValueError(LABEL+'.selected-type-slot')
    overlaps=[i for i,pointer in enumerate(entries) if ptr-7<=pointer<=ptr+15]
    if overlaps!=[index]:raise ValueError(LABEL+'.selected-type-record-write-alias')
    records=len(image.metadata.types)
    for role,section_name in (('recordFixup','typeDefinitions'),('alternateFixup','genericParameters')):
        f=c['fixups'][role];section=image.metadata.sections[section_name]
        if int.from_bytes(image.metadata.buf[f['headerOffsetField']:f['headerOffsetField']+4],'little',signed=True)!=section.offset or section.size%f['recordBytes']:raise ValueError(LABEL+'.metadata-record-section:'+role)
        if role=='recordFixup' and section.size!=records*f['recordBytes']:raise ValueError(LABEL+'.type-record-count')
    result=validate_type_data_initialization(programs,tables,image_base=base,contract=c,records=records)
    offset=image.metadata.sections['typeDefinitions'].offset+selected['storedSignedIndex']*c['recordGeometry']['recordBytes']
    if offset!=selected['conditionalRecordOffsetFromLoadedMetadataBase']:raise ValueError(LABEL+'.selected-fixup-offset')
    return {**result,'selectedDamageTypeStaticTypeSlot':index,'staticTypePointerTableCount':count,
        'staticTypePointerTableSha256':hashlib.sha256(type_table).hexdigest().upper(),
        'selectedRecordDataAndKindWritesDoNotOverlapOtherTypeWritebackSlots':True,
        'conditionalDamageTypeRecordOffsetFromLoadedMetadataBase':offset,
        'selectedMetadataInitializerSourceIdentityProved':False,'registeredTypeRecordPointerLiveObserved':False}
def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:raise ValueError(LABEL+'.scope')
    pins=c['nativeInputs'];before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def valid_unity():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not valid_unity():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not valid_unity():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'scope':SCOPE,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'concreteDamageTypeClassOrSharingProved':False}
