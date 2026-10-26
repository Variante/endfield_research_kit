"""Authenticate the selected current camera-target enum Param component.

Evidence and admission boundary:

Conditional target enum storage proves initialized raw Int32 source,
pointer/counter widths, atomic retry edges, typed allocation/getter/owned
stores and bitmap marking, not width from enum backing. The gate precedes
null and needs the matching pool. Cold initialization/refill, live provider
selection, independent EntityPtr arrays and current owner EOF remain
separate.
"""
from __future__ import annotations
if __name__=='__main__' and not __package__:raise SystemExit('Run python -m scripts.game_data.levelscript_camera_target_param_native')
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,native_validation_failure
from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.memorypack import inlined_integer_param as proof
SCHEMA='endfield.levelscript-camera-target-param-native.v1'
LABEL='levelscriptCameraTargetParamNative'
VALUE_TYPE='Beyond.Gameplay.View.ETrackCameraTargetType'
KIND='Param<ETrackCameraTargetType>'
DEFAULT_CONTRACT=CONTRACTS_DIR/'levelscript_camera_target_param_native.json'

def _contract(path):
    fact=json.loads(Path(path).read_bytes())
    if (set(fact)!={'schema','status','nativeInputs','codecKind','valueType','proof'} or (fact['schema'],fact['status'],fact['codecKind'],fact['valueType'])!=(SCHEMA,'exact-current-build',KIND,VALUE_TYPE)
            or set(fact['nativeInputs'])!={'GameAssembly.dll','global-metadata.dat','UnityPlayer.dll'}):raise ValueError(LABEL+'.contract:shape')
    return fact

def _validate_native(image,fact):
    actual=proof.derive(image,fact['nativeInputs'],VALUE_TYPE)
    validate_claims(fact['proof'],actual,label=LABEL+'.proof');validate_claims(actual,fact['proof'],label=LABEL+'.declaration')

def validate_camera_target_param_native_contract(*,contract_path=DEFAULT_CONTRACT,game_root=None,gameassembly=None,metadata=None):
    try:
        path=Path(contract_path);raw=path.read_bytes();fact=_contract(path);pins=fact['nativeInputs']
        if (gameassembly is None)!=(metadata is None):raise ValueError(LABEL+'.native:both paths required')
        root=Path(game_root) if game_root is not None else None
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly if gameassembly is not None else root.parent/'GameAssembly.dll' if root else None,metadata=metadata if metadata is not None else root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        strings=pooled_source_helper.CONTRACT_PATH.read_bytes();_validate_native(open_native_image(gate.gameassembly,gate.metadata),fact)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        if after.status!='validated':return dict(status=after.status,detail='Native inputs changed: '+after.detail)
        failed=pooled_source_helper.check_unity_input(gate.gameassembly,pins)
        if failed:return failed
        if raw!=path.read_bytes() or strings!=pooled_source_helper.CONTRACT_PATH.read_bytes():raise ValueError(LABEL+'.contract:declaration changed during validation')
        return dict(status='validated',codecKind=KIND,memberCount=4,rawSize=4,pathEncoding='int32-pool-index',nativeInputs=pins,evidenceBoundary=fact['proof']['evidenceBoundary'])
    except (ValueError,KeyError,IndexError,TypeError,OSError,RuntimeError) as error:return native_validation_failure(error,label=LABEL,source_path=contract_path)

if __name__=='__main__':
    from scripts.game_data.memorypack.primitive_param import run_cli
    raise SystemExit(run_cli(validate_camera_target_param_native_contract,DEFAULT_CONTRACT))
