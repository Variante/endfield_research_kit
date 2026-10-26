"""Fresh source gates for nominal ActionMap Param children.

The selected parent contracts pin the native inputs. Their historical payload
receipts are neither read nor promoted here. Every child source is re-proved;
no saved component or caller-supplied proof activates this validator.
"""
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, reader_input_changes
from scripts.game_data.memorypack import levelscript_action_param_sources as source, pooled_source_helper

LABEL = 'levelscriptActionParamsNative'
_INPUT_CONTRACTS = {
    'Param<List<BuffPtr>>': 'levelscript_finish_buffs_native.json',
    'Param<ModelVisibleType>': 'levelscript_entities_visibility_native.json',
    'Param<CommonMaskBlendData>': 'levelscript_mask_param_native.json',
    'Param<EntityPtr>[]': 'levelscript_list_make_entity_ptr_native.json',
    # GlobalBuff's parent is derived afresh; this dependency supplies only
    # the selected build pins, never a borrowed pointer or Param grammar.
    'Param<ObjectPtr<GlobalBuff>>': 'memorypack_pooled_string_reader_native.json',
    'Param<Vector3>[]': 'memorypack_pooled_string_reader_native.json',
    'Param<List<GameplayTag>>': 'memorypack_pooled_string_reader_native.json',
}


def validate(*, codec_kind, game_root=None, gameassembly=None, metadata=None):
    path = CONTRACTS_DIR / _INPUT_CONTRACTS.get(codec_kind, 'invalid-action-param')
    try:
        if codec_kind not in _INPUT_CONTRACTS:
            raise ValueError(LABEL + '.finite-codec-domain')
        if (gameassembly is None) != (metadata is None):
            raise ValueError(LABEL + '.both-native-paths-required')
        if gameassembly is None:
            if game_root is None:
                raise ValueError(LABEL + '.explicit-selected-inputs-required')
            root = Path(game_root)
            gameassembly = root.parent / 'GameAssembly.dll'
            metadata = root / 'il2cpp_data/Metadata/global-metadata.dat'
        before = snapshot_complete_reader_inputs()
        raw = path.read_bytes()
        pins = json.loads(raw)['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gameassembly, metadata=metadata)
        if gate.status != 'validated':
            return dict(status=gate.status, detail=gate.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        image = open_native_image(gate.gameassembly, gate.metadata)
        if codec_kind == 'Param<List<GameplayTag>>':
            from scripts.game_data.memorypack import levelscript_gameplay_tag_list_param_sources as tags
            component = tags.derive(image, pins)
            capability = component['capabilities'][tags.CAPABILITY]
        elif codec_kind == 'Param<Vector3>[]':
            from scripts.game_data.memorypack import levelscript_vector_param_array_sources as vectors
            component = vectors.derive_parent(image, pins)
            capability = component['capabilities'][vectors.CAPABILITY]
        elif codec_kind == 'Param<ObjectPtr<GlobalBuff>>':
            from scripts.game_data.memorypack import levelscript_global_buff_param_sources as globals_
            component = globals_.derive(image, pins)
            capability = component['capabilities'][globals_.CAPABILITY]
        elif codec_kind == 'Param<EntityPtr>[]':
            from scripts.game_data.memorypack import levelscript_entity_param_array_sources as arrays
            component = arrays.derive(image, pins)
            capability = component['capabilities'][arrays.CAPABILITY]
        elif codec_kind == 'Param<CommonMaskBlendData>':
            from scripts.game_data.memorypack import levelscript_mask_curve_sources as masks
            component = masks.derive(image, pins)
            capability = component['capabilities'][masks.CAPABILITY]
        else:
            component = source.derive(image, pins, codec_kind=codec_kind)
            capability = component['capability']
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != 'validated':
            return dict(status=after.status, detail='Native inputs changed: ' + after.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        current = snapshot_complete_reader_inputs()
        if before != current or raw != path.read_bytes():
            raise ValueError(LABEL + '.source-or-contract-drift:' + str(reader_input_changes(before, current))[:1200])
        return dict(status='validated', codecKind=codec_kind, capability=capability,
            nativeInputs=pins, nativeSources={
                'GameAssembly.dll': str(Path(gate.gameassembly).resolve()),
                'global-metadata.dat': str(Path(gate.metadata).resolve())},
            runtimeEvaluationAdmitted=False, wholeOwnerAdmitted=False)
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        return native_validation_failure(error, label=LABEL, source_path=path)
