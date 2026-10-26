"""Re-prove the reviewed current ModelView stored grammar per operation."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
from scripts.game_data.memorypack import modelview_composition as composition,pooled_source_helper

CONTRACT_PATH=CONTRACTS_DIR/'model_view_state_controller_native.json'


def validate(*,game_root=None,gameassembly=None,metadata=None,contract_path=CONTRACT_PATH):
    try:
        before=snapshot_complete_reader_inputs();path=Path(contract_path);raw=path.read_bytes();c=json.loads(raw);composition.need('schema','endfield.model-view-state-controller-native.v1',c['schema']);composition.need('status','conditional-current-build-wire',c['status']);pins=c['nativeInputs'];composition.need('native-input-set',{'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'},set(pins))
        if (gameassembly is None)!=(metadata is None):raise ValueError('modelView.both-native-paths-required')
        folder=Path(game_root)if game_root else None;gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly else folder.parent/'GameAssembly.dll'if folder else None,metadata=metadata if metadata else folder/'il2cpp_data/Metadata/global-metadata.dat'if folder else None)
        if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        result=composition.derive(open_native_image(gate.gameassembly,gate.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,failedGate='installed_native_inputs_exit',detail=after.detail)
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes()or before!=snapshot_complete_reader_inputs():raise ValueError('modelView.inputs-changed-during-validation')
        return dict(status='validated',layout=result['layout'],selectedSourcePrograms=result['selectedSourcePrograms'],nativeInputs=pins,nativeSources={'GameAssembly.dll':str(gate.gameassembly),'global-metadata.dat':str(gate.metadata)},evidenceBoundary=c['evidenceBoundary'])
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label='modelViewNative',source_path=contract_path)
