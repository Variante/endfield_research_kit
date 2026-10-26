"""Registered MethodSpec descriptor flow and selected inherited-ctor row join."""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex,read_exception_directory
from scripts.game_data.il2cpp.register_rotates import decode_rotate_instructions
from scripts.game_data.il2cpp.owned_partition import checked_rows
from scripts.game_data.il2cpp.method_spec_descriptor_control import validate_method_spec_descriptor_control
from . import buff_camera_context_slot_publication as parent_owner

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_method_spec_descriptor_native.json'
SCHEMA='endfield.buff-camera-method-spec-descriptor-native-contract.v1'
LABEL='buffCameraMethodSpecDescriptor'
def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'runtimeSlot7Observed':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False}


def _validate_image(image,c):
    def fail(check,expected,actual):
        raise ValueError(json.dumps({'validator':LABEL,'source':CONTRACT_PATH.as_posix(),'check':check,'expected':str(expected)[:1000],'actual':str(actual)[:1000]}))
    parent,_=read_reviewed_contract(CONTRACTS_DIR/c['parentContract'],schema=parent_owner.SCHEMA,status='exact-current-build',label=LABEL)
    if parent['nativeInputs']!=c['nativeInputs']:fail('dependency-build',c['nativeInputs'],parent['nativeInputs'])
    joined=parent_owner._validate_image(image,parent);base=image.pe.image_base
    first=joined['methodSlotArgumentFlow']['callSitesAndTargets'][0]
    if first[1]-base!=c['function']['entryRva']:fail('actual-method-slot-descriptor-call',c['function']['entryRva'],first)
    directory,size,raw=read_exception_directory(image.pe)
    unwind=UnwindChainIndex(raw,lambda at,n:image.pe.bytes_at_va(base+at,n),table_rva=directory,image_size=size)
    f=c['function'];family=json.loads(json.dumps(unwind.family(f['entryRva'])))
    if family!=f['unwindFamily']:fail('complete-exception-family',f['unwindFamily'],family)
    if [(w['startRva'],w['endRva']) for w in f['codeWindows']]!=[tuple(r['runtimeTriple'][:2]) for r in family['ranges']]:
        fail('complete-byte-range-membership',family['ranges'],f['codeWindows'])
    image.check_windows(f['codeWindows'],label=LABEL);rows=[]
    for w in f['codeWindows']:
        data=image.pe.bytes_at_va(base+w['startRva'],w['endRva']-w['startRva'])
        rows.extend(checked_rows(decode_rotate_instructions(image.mapper,data,base+w['startRva']),data,LABEL))
    control=validate_method_spec_descriptor_control(rows,image_base=base,entry_rva=f['entryRva'],globals=c['globals'],calls=c['calls'])
    if control['completeControl']['instructionsChecked']!=37:fail('complete-control-size',37,control['completeControl']['instructionsChecked'])
    # Authenticate the selected on-disk registration layout; runtime publication remains conditional.
    metadata=int(image.registration['methodSpecs'],16);insts=int(image.registration['genericInsts'],16)
    reg=image.metadata_registration
    if image.pe.u64_at_va(reg+control['metadataMethodSpecTablePointerOffset'])!=metadata or image.pe.u64_at_va(reg+control['metadataGenericInstTablePointerOffset'])!=insts:
        fail('current-static-registration-field-layout','methodSpecs and genericInsts pointers',image.registration)
    index=c['selectedMethodSpecIndex']
    if type(index) is not int or not 0<=index<min(image.registration['methodSpecsCount'],1<<31):fail('selected-index-domain','nonnegative in-range signed index',index)
    values=list(struct.unpack('<iii',image.pe.bytes_at_va(metadata+index*control['methodSpecRecordBytes'],12)))
    base_c,_=read_reviewed_contract(CONTRACTS_DIR/parent['baseConstructorContract'],schema='endfield.buff-camera-base-constructor-native-contract.v1',status='exact-current-build',label=LABEL)
    slot=next(r for r in base_c['classContext']['entries'] if r['relativeSlot']==joined['inheritedConstructorSlot'])
    if slot['index']!=index or slot['methodSpec']!=values:fail('same-inherited-constructor-method-spec',slot,values)
    arguments=[]
    for role,i in zip(('class','method'),values[1:]):
        if i==-1:arguments.append({'role':role,'index':-1,'selectedStaticPointer':0})
        elif 0<=i<image.registration['genericInstsCount']:
            instance=image.instantiations.resolve(i)
            arguments.append({'role':role,'index':i,'selectedStaticPointer':image.pe.u64_at_va(insts+i*8),'instantiation':instance.as_dict()})
        else:fail('selected-instantiation-index','in-range or -1',i)
    return {'descriptorControl':control,'selectedInheritedConstructorMethodSpec':values,'selectedInstantiationPointers':arguments,
        'priorSlotPublication':joined,'runtimeRegistrationAndDescriptorCacheObserved':False,'actualDescriptorOrColdTargetSelected':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL);pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    summary=_validate_image(open_native_image(gate.gameassembly,gate.metadata),c)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'runtimeSlot7Observed':False,
        'actualDescriptorOrColdTargetSelected':False,'positiveListGrammarProved':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,'evidenceBoundary':c['evidenceBoundary']}
