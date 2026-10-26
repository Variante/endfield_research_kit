"""Current CameraControllerBase Param with a null-only nested constant."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.memorypack.reference_null_param import derive
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_camera_controller_param_native.json'
SCHEMA='endfield.levelscript-camera-controller-param-native.v1'


def validate(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];reader=snapshot_complete_reader_inputs()
        layout={'codecKind':'Param<CameraControllerBase>','memberCount':4,'constantMarker':255,'stringEncoding':'int32-pool-index'}
        if fact['schema']!=SCHEMA or fact['status']!='exact-current-build'or fact['valueType']!='Beyond.Gameplay.View.CameraControllerBase'or fact['layout']!=layout or set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError('cameraControllerParam.contract-shape')
        if(gameassembly is None)!=(metadata is None):raise ValueError('cameraControllerParam.both-native-paths-required')
        root=Path(game_root)if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
        if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        dependency=CONTRACTS_DIR/'levelscript_nominal_key_param_native.json';before=dependency.read_bytes();key=json.loads(before)
        proof=derive(open_native_image(gate.gameassembly,gate.metadata),pins,fact,key)
        if proof!=fact['proof']:raise ValueError('cameraControllerParam.reviewed-source-proof')
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes()or before!=dependency.read_bytes():raise ValueError('cameraControllerParam.contract-drift')
        fresh=snapshot_complete_reader_inputs()
        if reader!=fresh:raise ValueError('cameraControllerParam.reader-drift:'+str(reader_input_changes(reader,fresh))[:1000])
        return dict(status='validated',layout=layout,nativeInputs=pins,evidenceBoundary=fact['evidenceBoundary'])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label='cameraControllerParamNative',source_path=contract_path)
