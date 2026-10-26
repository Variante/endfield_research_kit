"""Authenticate the reviewed optimized BeyondReadString source on selected inputs."""
from __future__ import annotations
from pathlib import Path
from scripts.common import check_installed_native_inputs,sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract,native_validation_failure

CONTRACT_PATH=CONTRACTS_DIR/'memorypack_pooled_string_reader_native.json'
LABEL='memorypackPooledSourceHelper'


def _contract():
    value,_=read_reviewed_contract(CONTRACT_PATH,schema='endfield.memorypack-pooled-string-reader-native.v2',status='exact-current-build',label=LABEL)
    if (value.get('claim')!='MemoryPack.MemoryPackReader.ReadString'
            or value.get('equivalentMethod',[0])[1:3]!=['MemoryPack.MemoryPackReaderExtensions','BeyondReadString']
            or set(value.get('nativeInputs',{}))!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}
            or not value.get('codeWindows') or not value.get('instructions')
            or not isinstance(value.get('inlineSources'),list)
            or not isinstance(value.get('inlineSymbols'),dict)
            or set(value['inlineSymbols'])!={'pool','empty'}
            or any(type(v) is not int or not 0<v<1<<32 for v in value['inlineSymbols'].values())):
        raise ValueError(f'{LABEL}.contract:claim-or-program')
    return value


def validate_on_image(image,target,inputs):
    """Reuse the reviewed code/dataflow equivalence; it does not prove inline UTF8."""
    fact=_contract()
    if {k:v.upper() for k,v in fact['nativeInputs'].items()}!={k:v.upper() for k,v in inputs.items()}:
        raise ValueError('pooled-string:native-inputs:mismatched')
    if target!=image.pe.image_base+fact['targetRva']:raise ValueError(f'pooled-string:unproven-target={target:#x}')
    image.validate_method_row(fact['equivalentMethod'])
    image.check_windows(fact['codeWindows']);image.check_instruction_windows(fact['instructions'])
    return {'status':'validated','nativeInputs':fact['nativeInputs'],'sourceHelpers':[fact['targetRva']],
            'wireEncoding':'int32-pool-index','emptyIndex':-1,'nullIndex':-2,'evidenceBoundary':fact['evidenceBoundary']}


def check_unity_input(gameassembly,pins):
    unity=Path(gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return {'status':'missing','detail':'UnityPlayer.dll missing'}
    if sha256_file_upper(unity)!=pins['UnityPlayer.dll'].upper():
        return {'status':'mismatched','detail':'UnityPlayer.dll mismatched'}


def validate_current_native_contract(*,gameassembly:Path,metadata:Path,wrapper=None,field=None):
    try:
        fact=_contract();pins=fact['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return {'status':gate.status,'detail':gate.detail}
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        image=open_native_image(gate.gameassembly,gate.metadata)
        result=validate_on_image(image,image.pe.image_base+fact['targetRva'],pins)
        if wrapper is not None or field is not None:
            from scripts.game_data.memorypack.pooled_inline_sources import validate
            result=validate(image,fact,wrapper,field)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return {'status':after.status,'detail':'native inputs changed during validation'}
        failed=check_unity_input(gate.gameassembly,pins)
        return failed or result
    except (ValueError,KeyError,IndexError,TypeError,OSError) as error:
        return native_validation_failure(error,label=LABEL,source_path=CONTRACT_PATH)
