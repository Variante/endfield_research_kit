"""Authenticate enum-class field sources and selected class-from-type flow."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
from scripts.game_data.il2cpp.class_enum_fields_control import validate_class_enum_fields
from scripts.game_data.il2cpp.owned_partition import checked_rows,check_byte_partition
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from .core import CONTRACTS_DIR
LABEL='buffClassEnumFields'
SCHEMA='endfield.buff-class-enum-fields-native-contract.v1'
SCOPE='complete-class-constructor-type-helper-and-selected-enum-field-and-primitive-cell-flow'
CONTRACT_PATH=CONTRACTS_DIR/'buff_class_enum_fields_native.json'
def _skip(status,detail,pins):return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'concreteDamageTypeSharingSelected':False}
def _validate(image,c):
    base=image.pe.image_base;directory,size,raw=read_exception_directory(image.pe);unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    programs={}
    for role,f in c['functions'].items():
        if f['ownershipKind']=='exceptionFamily':
            actual=json.loads(json.dumps(unwind.family(f['entryRva'])))
            if actual!=f['unwindFamily']:raise ValueError(LABEL+'.exception-family:'+role)
            owned=[tuple(p['runtimeTriple'][:2]) for p in actual['ranges']]
        elif f['ownershipKind']=='closedEntryProgram':
            if role!='apiWrapper' or f['entryRva'] in unwind.entries or f['unwindFamily'] is not None or len(f['codeWindows'])!=1:raise ValueError(LABEL+'.ordinary-entry-boundary')
            owned=[(f['codeWindows'][0]['startRva'],f['codeWindows'][0]['endRva'])]
        else:raise ValueError(LABEL+'.ownership-kind')
        pieces=[];rows=[]
        for kind in ('codeWindows','paddingWindows','tableWindows'):
            image.check_windows(f[kind],label=LABEL+'.'+role+'.'+kind)
            for w in f[kind]:
                start,end=w['startRva'],w['endRva'];b=image.pe.bytes_at_va(base+start,end-start);pieces.append((start,end,kind))
                if kind=='codeWindows':rows.extend(checked_rows(decode_enum_underlying_instructions(image.mapper,b,base+start),b,LABEL+'.'+role))
                elif kind=='paddingWindows' and b!=bytes.fromhex(w['rawHex']):raise ValueError(LABEL+'.padding')
        check_byte_partition(owned,pieces,LABEL+'.'+role);programs[role]=rows
    exports=resolve_named_exports(image.pe,['il2cpp_class_from_type'])
    if exports!=c['namedClassFromTypeExport'] or exports['selectedExports'][0]['targetRva']!=c['functions']['apiWrapper']['entryRva']:raise ValueError(LABEL+'.named-api-binding')
    old,_=read_reviewed_contract(CONTRACTS_DIR/'buff_class_name_lookup_native.json',schema='endfield.buff-class-name-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    enum,_=read_reviewed_contract(CONTRACTS_DIR/'buff_enum_underlying_native.json',schema='endfield.buff-enum-underlying-native-contract.v1',status='exact-current-build',label=LABEL)
    init,_=read_reviewed_contract(CONTRACTS_DIR/'buff_type_data_initialization_native.json',schema='endfield.buff-type-data-initialization-native-contract.v1',status='exact-current-build',label=LABEL)
    if any(v['nativeInputs']!=c['nativeInputs'] for v in (old,enum,init)):raise ValueError(LABEL+'.same-selected-native-inputs')
    l=c['layout']
    if (l['recordBytes'],l['typeDefinitionsHeader'],l['registrationTypes'])!=(old['layout']['typeRecordBytes'],old['layout']['typeDefinitionsHeader'],old['layout']['registrationTypes']):raise ValueError(LABEL+'.same-record-layout')
    if (l['classFlags'],l['elementClass'])!=(enum['layout']['classFlags'],enum['layout']['elementClass']):raise ValueError(LABEL+'.same-named-consumer-fields')
    for name in ('metadataHeader','metadataBase','metadataRegistration'):
        if c['globals'][name]!=old['globals'][name]:raise ValueError(LABEL+'.same-consumer-global:'+name)
    if c['functions']['constructor']['entryRva']!=old['functions']['constructor']['entryRva'] or c['request']['lookupEntryRva']!=old['functions']['lookup']['entryRva'] or c['functions']['publication']!=init['functions']['publication']:raise ValueError(LABEL+'.same-parent-entries')
    for lit,value in ((c['request']['typeLiteral'],'Int32'),(c['request']['namespaceLiteral'],'System')):
        b=bytes.fromhex(lit['rawHex'])
        if b!=value.encode('ascii')+b'\0' or image.pe.bytes_at_va(base+lit['rva'],len(b))!=b:raise ValueError(LABEL+'.literal-bytes')
    td=NativeReferenceContext(image);definition=td.index.types['Beyond.GEnums.DamageType'];section=image.metadata.sections['typeDefinitions']
    if section.size!=len(image.metadata.types)*l['recordBytes']:raise ValueError(LABEL+'.record-section')
    record=image.metadata.buf[section.offset+definition.index*l['recordBytes']:section.offset+(definition.index+1)*l['recordBytes']]
    bitfield=int.from_bytes(record[l['recordBitfield']:l['recordBitfield']+4],'little');element_index=int.from_bytes(record[l['elementIndex']:l['elementIndex']+4],'little',signed=True)
    if (bitfield,element_index)!=(definition.bitfield,definition.element_type_index):raise ValueError(LABEL+'.metadata-field-boundaries')
    pointer=td.type_pointer(element_index);element_raw=image.pe.bytes_at_va(pointer,16)
    actual={'typeDefinition':definition.index,'recordHex':record.hex().upper(),'bitfieldDwordOffset':l['recordBitfield'],'bitfield':bitfield,
        'storedEnumBit':bool(bitfield&2),'elementTypeIndexFieldOffset':l['elementIndex'],'elementTypeIndex':element_index,
        'elementTypeName':td.type_name(element_index),'elementTypePointerVa':pointer,'elementRawTypeHex':element_raw.hex().upper(),'underlyingField':list(td.field('Beyond.GEnums.DamageType::value__'))}
    if actual!=c['selectedDamageType'] or not actual['storedEnumBit'] or actual['elementTypeName']!='int' or element_raw[l['typeKind']]!=8 or actual['underlyingField'][1:]!=['int',16]:raise ValueError(LABEL+'.selected-damage-inputs')
    tables={key:image.pe.bytes_at_va(base+w['startRva'],len(bytes.fromhex(w['rawHex']))) for key,w in c['helperDispatch']['tables'].items()}
    summary=validate_class_enum_fields(programs,tables,image_base=base,contract=c)
    # Freshly authenticate the tiny old enum-base program because a null element
    # can now be a selected helper output. Its add has no null-element guard.
    f=enum['functions']['enumBase'];image.check_windows(f['codeWindows'],label=LABEL+'.old-enum-base-after-null-element-finding')
    return {**summary,'selectedDamageTypeMetadata':actual,'selectedEnumFlagBitAtStoreConditionallyTrue':True,
        'selectedElementArgumentKind':8,'selectedElementArgumentIsNull':False,'enumBaseNullElementWouldReturnTypeOffset':enum['layout']['valueType'],
        'enumBaseNullElementWitnessIsRuntimeObservation':False,'wholeRootAdmitted':False}
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
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'concreteDamageTypeSharingSelected':False}
