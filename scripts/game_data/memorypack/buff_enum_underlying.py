"""Authenticate enum projection, named API entries and record-pointer boundary."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.enum_underlying_instructions import decode_enum_underlying_instructions
from scripts.game_data.il2cpp.enum_underlying_control import validate_enum_underlying
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from .core import CONTRACTS_DIR

LABEL='buffEnumUnderlying'
SCHEMA='endfield.buff-enum-underlying-native-contract.v1'
SCOPE='complete-enum-projection-and-named-api-entry-programs-with-record-pointer-boundary'
CONTRACT_PATH=CONTRACTS_DIR/'buff_enum_underlying_native.json'
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'scope':SCOPE,'nativeInputs':pins,
        'concreteDamageTypeUnderlyingResultProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}

def _validate(image,c):
    base=image.pe.image_base
    names={'enumBase':'il2cpp_class_enum_basetype','isEnum':'il2cpp_class_is_enum',
        'getType':'il2cpp_class_get_type','getElement':'il2cpp_class_get_element_class'}
    exports=resolve_named_exports(image.pe,list(names.values()))
    if exports!=c['namedExports']:raise ValueError(LABEL+'.named-export-table')
    entries={r['symbolName']:r for r in exports['selectedExports']}
    for role,name in names.items():
        if entries[name]['isForwarder'] or entries[name]['targetRva']!=c['functions'][role]['entryRva']:
            raise ValueError(LABEL+'.direct-named-export:'+name)
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    programs={}
    for role,f in c['functions'].items():
        if f['ownershipKind']=='exceptionFamily':
            if role!='projection' or json.loads(json.dumps(unwind.family(f['entryRva'])))!=f['unwindFamily']:
                raise ValueError(LABEL+'.complete-exception-family:'+role)
            if [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[tuple(r['runtimeTriple'][:2]) for r in f['unwindFamily']['ranges']]:
                raise ValueError(LABEL+'.complete-window-membership')
        elif f['ownershipKind']=='closedEntryProgram':
            if role=='projection' or f['unwindFamily'] is not None or f['entryRva'] in unwind.entries or len(f['codeWindows'])!=1:
                raise ValueError(LABEL+'.closed-entry-ownership:'+role)
        else:raise ValueError(LABEL+'.ownership-kind')
        image.check_windows(f['codeWindows'],label=LABEL+'.'+role);rows=[]
        if f['codeWindows'][0]['startRva']!=f['entryRva']:raise ValueError(LABEL+'.actual-entry')
        for w in f['codeWindows']:
            data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
            rows.extend(checked_rows(decode_enum_underlying_instructions(image.mapper,data,base+w['startRva']),data,LABEL+'.'+role))
        programs[role]=rows
    for r in c['projectionIncomingCalls']:
        raw=image.pe.bytes_at_va(base+r['siteRva'],5)
        if raw.hex().upper()!=r['instructionHex'] or raw[0]!=0xe8 or r['siteRva']+5+int.from_bytes(raw[1:],'little',signed=True)!=c['functions']['projection']['entryRva']:
            raise ValueError(LABEL+'.actual-incoming-call')
    if not c['projectionIncomingCalls']:raise ValueError(LABEL+'.missing-incoming-call')
    # Reuse reviewed record geometry's declarations; authenticate every actual new instruction independently.
    old,_=read_reviewed_contract(CONTRACTS_DIR/'buff_class_name_lookup_native.json',
        schema='endfield.buff-class-name-lookup-native-contract.v1',status='exact-current-build',label=LABEL)
    p=c['recordProjection']
    if (old['nativeInputs']!=c['nativeInputs'] or p!={'metadataHeaderRva':old['globals']['metadataHeader'],
        'metadataBaseRva':old['globals']['metadataBase'],'headerTypeDefinitionsOffset':old['layout']['typeDefinitionsHeader'],
        'recordBytes':old['layout']['typeRecordBytes'],'multiplier':old['projections']['matchedRecord']['multiplier'],
        'shift':old['projections']['matchedRecord']['shift']} or c['classResolverRva']!=old['functions']['classResolver']['entryRva']):
        raise ValueError(LABEL+'.same-record-geometry-declarations')
    section=image.metadata.sections['typeDefinitions'];records=len(image.metadata.types)
    if section.size!=records*p['recordBytes'] or int.from_bytes(image.metadata.buf[p['headerTypeDefinitionsOffset']:p['headerTypeDefinitionsOffset']+4],'little')!=section.offset:
        raise ValueError(LABEL+'.selected-type-definition-section')
    selected=NativeReferenceContext(image);name='Beyond.GEnums.DamageType';td=selected.index.types[name]
    pointer=selected.type_pointer(td.byval_type_index);type_raw=image.pe.bytes_at_va(pointer,16)
    damage={'typeDefinition':td.index,'byvalTypeIndex':td.byval_type_index,'typePointerVa':pointer,'rawTypeHex':type_raw.hex().upper(),
        'isEnum':selected.is_enum(name),'underlyingField':list(selected.field(name+'::value__')),'liveClassIdentityProved':False}
    if damage!=c['selectedDamageTypeMetadata'] or not damage['isEnum'] or damage['underlyingField'][1:]!=['int',16] or type_raw[10]!=17 or int.from_bytes(type_raw[:8],'little')!=td.index:
        raise ValueError(LABEL+'.damage-type-on-disk-metadata')
    summary=validate_enum_underlying(programs,image_base=base,contract=c,metadata_records=records)
    return {**summary,'selectedDamageTypeMetadata':damage,'namedExports':exports,
        'damageTypeStoredDataIsDefinitionIndex':True,'damageTypeStoredDataHasLiveRecordPointerJoin':False}

def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:raise ValueError(LABEL+'.scope')
    pins=c['nativeInputs']
    before=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if before.status!='validated':return _skip(before.status,before.detail,pins)
    unity=Path(before.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate(open_native_image(before.gameassembly,before.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=before.gameassembly,metadata=before.metadata)
    if after.status!='validated' or not unity_matches():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','scope':SCOPE,'nativeInputs':pins,'summary':summary,'evidenceBoundary':c['evidenceBoundary'],
        'concreteDamageTypeUnderlyingResultProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}
