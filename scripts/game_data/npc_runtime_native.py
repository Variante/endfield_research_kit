"""Current pooled NPC source gate, independent of authored owner EOF admission."""
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs,reader_input_changes
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input
from scripts.game_data.memorypack.npc_runtime_sources import validate_components
CONTRACT_PATH=CONTRACTS_DIR/'npc_runtime_native.json'
DEPENDENCIES=dict(key='levelscript_nominal_key_param_native.json',copy='memory_copy_bounded_native.json',string='levelscript_pooled_string_list_native.json',clones='memorypack_reader_clones_native.json',pool='memorypack_pooled_string_reader_native.json',intList='levelscript_int_list_native.json')


def validate(*,game_root=None,contract_path=CONTRACT_PATH,gameassembly=None,metadata=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=json.loads(raw);pins=fact['nativeInputs'];reader=snapshot_complete_reader_inputs()
        if set(pins)!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}:raise ValueError('npcRuntime.native-input-set')
        if(gameassembly is None)!=(metadata is None):raise ValueError('npcRuntime.both-native-paths-required')
        root=Path(game_root)if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll'if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat'if root else None)
        if gate.status!='validated':return dict(status=gate.status,failedGate='installed_native_inputs',detail=gate.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        paths={k:CONTRACTS_DIR/v for k,v in DEPENDENCIES.items()};before={k:p.read_bytes()for k,p in paths.items()};dependencies={k:json.loads(v)for k,v in before.items()}
        if any(v['nativeInputs']!=pins for v in dependencies.values()):raise ValueError('npcRuntime.dependency-native-inputs')
        plan,proof=validate_components(open_native_image(gate.gameassembly,gate.metadata),pins,fact,dependencies)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
        failed=check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes()or before!={k:p.read_bytes()for k,p in paths.items()}:raise ValueError('npcRuntime.contract-drift')
        fresh=snapshot_complete_reader_inputs()
        if reader!=fresh:raise ValueError('npcRuntime.reader-source-drift:'+str(reader_input_changes(reader,fresh))[:1000])
        return dict(status='validated',layout=plan,proof=proof,nativeInputs=pins,nativeSources={'GameAssembly.dll':str(Path(gate.gameassembly).resolve()),'global-metadata.dat':str(Path(gate.metadata).resolve())},evidenceBoundary=fact['evidenceBoundary'])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:return native_validation_failure(error,label='npcRuntimeNative',source_path=contract_path)
