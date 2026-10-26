"""Fresh selected-input gate for finite ActionMap condition parent sources.

The pooled-reader contract supplies only reviewed native identities. Its wire
or source grammar is never used to prove these parent fields. Every caller
program is freshly derived, with full reader/native/contract bookends.
"""
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, reader_input_changes
from scripts.game_data.memorypack import pooled_source_helper
from scripts.game_data.memorypack import levelscript_action_condition_parent_sources as source

LABEL = 'levelscriptActionConditionParentsNative'


def validate(*, wrapper_name, game_root=None, gameassembly=None, metadata=None):
    path = pooled_source_helper.CONTRACT_PATH
    try:
        source.need('finite-wrapper-selector', type(wrapper_name) is str and wrapper_name in source.WRAPPERS)
        if (gameassembly is None) != (metadata is None):
            raise ValueError(LABEL+'.both-native-paths-required')
        if gameassembly is None:
            if game_root is None:
                raise ValueError(LABEL+'.explicit-selected-inputs-required')
            root = Path(game_root)
            gameassembly = root.parent/'GameAssembly.dll'
            metadata = root/'il2cpp_data/Metadata/global-metadata.dat'
        before = snapshot_complete_reader_inputs(); raw = path.read_bytes()
        pins = pooled_source_helper._contract()['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gameassembly, metadata=metadata)
        if gate.status != 'validated':
            return dict(status=gate.status, detail=gate.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        image = open_native_image(gate.gameassembly, gate.metadata)
        result = source.derive(image, pins, wrapper_name=wrapper_name)
        if (result.get('schema') != source.SCHEMA or result.get('status') != 'validated'
                or result.get('nativeInputs') != pins or not result.get('bindings')
                or set(result.get('parentSources', {})) != {wrapper_name}
                or any(row.get('wrapperName') != wrapper_name for row in result['bindings'].values())
                or any(result.get(key) is not False for key in ('conditionGrammarAdmitted', 'unionSelectionAdmitted',
                    'wholeOwnerAdmitted', 'runtimeConditionEvaluationAdmitted'))):
            raise ValueError(LABEL+'.complete-parent-source-required')
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != 'validated':
            return dict(status=after.status, detail='Native inputs changed: '+after.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        current = snapshot_complete_reader_inputs()
        if before != current or raw != path.read_bytes():
            raise ValueError(LABEL+'.source-or-contract-drift:'+str(reader_input_changes(before, current))[:1200])
        compact = {key: value for key, value in result.items() if key != 'parentSources'}
        return dict(compact, nativeSources={'GameAssembly.dll': str(Path(gate.gameassembly).resolve()),
                                            'global-metadata.dat': str(Path(gate.metadata).resolve())})
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        return native_validation_failure(error, label=LABEL, source_path=path)
