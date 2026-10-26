"""Selected-build guarded source-return proof; legacy camera adoption is separate.

The normal camera-group 'and' path preserves the preceding source helper's
full reference return into the setter argument when its receiver is nonzero.
The error-path call before INT3 is not the value origin: a zero receiver has
no ordinary setter continuation. The legacy camera catalog cannot prove this
normal source return. Closed list contexts and element/cursor composition
remain independent obligations.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from .contracts import CONTRACTS_DIR
from .il2cpp.native_image import open_native_image,read_reviewed_contract
from .il2cpp.reference_setter_guard_bridge import validate_reference_setter_guard_bridge

CONTRACT_PATH=CONTRACTS_DIR/'buff_camera_condition_group_source_return_native.json'
SCHEMA='endfield.buff-camera-condition-group-source-return-native-contract.v1'
LABEL='cameraConditionGroupSourceReturn'


def _skip(status,detail,pins):
    return {'status':status,'detail':detail,'nativeInputs':pins,'normalSourceReturnProved':False,
        'legacyCameraContractCorrectionApplied':False,'positiveListGrammarProved':False,'runtimeExecutionKnown':False}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path):
    c,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL);pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not unity_matches():return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll missing or mismatched',pins)
    image=open_native_image(gate.gameassembly,gate.metadata);base=image.pe.image_base
    image.validate_method_row(c['readerMethod'],label=LABEL);image.check_windows([c['readerWindow']],label=LABEL)
    start,end=c['readerWindow']['startRva'],c['readerWindow']['endRva']
    for key in ('sourceCall','setterCall'):
        call=c[key]
        if not (start<=call['rva'] and call['rva']+5<=end):raise ValueError(LABEL+'.call-window')
        raw=image.pe.bytes_at_va(base+call['rva'],5)
        if raw!=bytes.fromhex(call['instructionHex']) or raw[0]!=0xe8 or call['rva']+5+int.from_bytes(raw[1:],'little',signed=True)!=call['targetRva']:raise ValueError(LABEL+'.actual-'+key)
    b=c['bridge']
    if b['startRva']!=c['sourceCall']['rva']+5 or b['endRva']!=c['setterCall']['rva'] or not start<=b['startRva']<b['endRva']<=end:raise ValueError(LABEL+'.complete-bridge-range')
    raw=image.pe.bytes_at_va(base+b['startRva'],b['endRva']-b['startRva'])
    if raw!=bytes.fromhex(b['rawHex']) or hashlib.sha256(raw).hexdigest().upper()!=b['sha256']:raise ValueError(LABEL+'.bridge-bytes')
    summary=validate_reference_setter_guard_bridge(raw,start_va=base+b['startRva'],setter_site_va=base+b['endRva'],error_target_va=base+b['errorTargetRva'])
    old=c['supersededIncorrectSourceCall']
    if old['rva']!=b['startRva']+5 or old['targetRva']!=b['errorTargetRva'] or old==c['sourceCall']:raise ValueError(LABEL+'.superseded-error-call')
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not unity_matches():return _skip(after.status if after.status!='validated' else 'mismatched','Selected native inputs changed',pins)
    return {'status':'validated','nativeInputs':pins,'summary':summary,'normalSourceReturnProved':True,
        'legacyCameraContractCorrectionApplied':False,'positiveListGrammarProved':False,'runtimeExecutionKnown':False,
        'evidenceBoundary':c['evidenceBoundary']}
