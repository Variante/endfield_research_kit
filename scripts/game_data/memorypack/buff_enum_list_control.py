"""Authenticate independent Int32Enum buffered list and scalar composition."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.generic_entries import GenericEntries
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from .core import CONTRACTS_DIR
from .enum_list_sources import validate_enum_list_sources

LABEL='buffEnumListControl'
SCHEMA='endfield.buff-enum-list-control-native-contract.v1'
SCOPE='independent-int32enum-selected-buffered-header-list-bridge-and-spare-capacity-output'
CONTRACT_PATH=CONTRACTS_DIR/'buff_enum_list_control_native.json'

def _fail(check,expected,actual):
    raise ValueError(json.dumps({'validator':LABEL,'check':check,'source':CONTRACT_PATH.as_posix(),
        'expected':str(expected)[:1024],'actual':str(actual)[:1024]}))
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'scope':SCOPE,
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'concreteDamageTypeSharingSelected':False}

def _validate(image,c):
    base=image.pe.image_base;selected=NativeReferenceContext(image);generic=GenericEntries(image)
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    if set(c['functions'])!={'list','scalar','header','bridge','add'} or set(c['formatters'])!={'list','scalar'}:
        _fail('reviewed-function-membership','five physical entries and two independent compiled entries',c.keys())
    if set(c['selectedCalls'])!={'provider','barrier','classPrepare'}:
        _fail('reviewed-call-membership','provider, barrier and classPrepare',c['selectedCalls'])
    for role,f in c['functions'].items():
        family=json.loads(json.dumps(unwind.family(f['entryRva'])))
        if family!=f['unwindFamily'] or [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[
                tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
            _fail('complete-unwind-membership',role,f)
        image.check_windows(f['codeWindows'],label=LABEL+'.'+role)
    registrations={}
    for role,definition in (('list','MemoryPack.Formatters.ListFormatter`1'),('scalar','MemoryPack.Formatters.UnmanagedFormatter`1')):
        row=c['formatters'][role]
        image.validate_method_row(row['method'][:3],label=LABEL)
        if row['method'][1:3]!=[definition,'Deserialize'] or row['classArguments']!=['System.Int32Enum'] or row['methodArguments']!=[]:
            _fail('independent-placeholder-selection',definition,row)
        actual=generic.resolve(row['method'][0],row['classArguments'],[])
        if json.loads(json.dumps(actual))!=row['registration'] or actual['pointer']-base!=row['method'][3] or row['method'][3]!=c['functions'][role]['entryRva']:
            _fail('independent-compiled-entry',row,actual)
        instance=image.instantiations.resolve(actual['classInstantiation']['index'])
        if len(instance.arguments)!=1:_fail('one-compiled-argument',1,instance)
        arg=instance.arguments[0];argraw=image.pe.bytes_at_va(arg.type_pointer_va,16)
        if runtime_type_name(image.pe,image.metadata,arg.type_pointer_va)!='System.Int32Enum' or argraw[10]!=17 or argraw[11]&0x20:
            _fail('actual-placeholder-type','non-byref Int32Enum',argraw.hex())
        registrations[role]=actual
    if not selected.is_enum('System.Int32Enum') or selected.field('System.Int32Enum::value__')[1:]!=('int',16):
        _fail('placeholder-underlying-field','enum with boxed offset16 int value__',selected.field('System.Int32Enum::value__'))
    offsets=c['readerFieldsUnboxedOffsets']
    if offsets!={name:selected.field('MemoryPack.MemoryPackReader::'+name)[2]-16 for name in offsets}:
        _fail('current-named-reader-fields',offsets,'selected metadata differs')
    roles={'singleElement':'list','twoElements':'list','emptyExisting':'list','nullList':'list',
        'bufferedHeader':'header','enumBridge':'bridge','spareCapacityAdd':'add','bufferedScalar':'scalar'}
    if set(c['programs'])!=set(roles):_fail('program-membership',sorted(roles),sorted(c['programs']))
    for name,role in roles.items():
        proof=c['programs'][name];f=c['functions'][role]
        if proof['codeWindows']!=f['codeWindows'] or proof['program'][0][0]!=f['entryRva']:
            _fail('selected-program-entry-and-ownership',role,name)
    entries={role:f['entryRva'] for role,f in c['functions'].items()}
    entries.update(c['selectedCalls'])
    summary=validate_enum_list_sources(image,c['programs'],offsets,entries,fail=_fail)
    return {'compiledRegistrations':registrations,'placeholderUnderlyingField':'int',
        'selectedControl':summary,'otherOwnedPathsSemanticsProved':False}

def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if c.get('scope')!=SCOPE:_fail('scope',SCOPE,c.get('scope'))
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
        'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'concreteDamageTypeSharingSelected':False}
