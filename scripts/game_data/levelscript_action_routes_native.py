"""Fresh actual-switch, complete-source and child gates for ActionMap routes.

Only literal family/tag selectors and explicit native inputs are accepted.
The declaration contract supplies build pins, never a retained source proof.
"""
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs, reader_input_changes
from scripts.game_data.memorypack import pooled_source_helper

LABEL = 'levelscriptActionRoutesNative'
PIN_PATH = CONTRACTS_DIR / 'memorypack_pooled_string_reader_native.json'


def validate(*, family, tag, game_root=None, gameassembly=None, metadata=None):
    try:
        if family not in ('ActionBase', 'GetterBase', 'ActionHeader') or type(tag) is not int or not 0 <= tag <= 65535:
            raise ValueError(LABEL+'.literal-family-and-tag-required')
        if (gameassembly is None) != (metadata is None):
            raise ValueError(LABEL+'.both-native-paths-required')
        if gameassembly is None:
            if game_root is None:
                raise ValueError(LABEL+'.explicit-selected-inputs-required')
            root = Path(game_root); gameassembly = root.parent / 'GameAssembly.dll'
            metadata = root / 'il2cpp_data/Metadata/global-metadata.dat'
        before = snapshot_complete_reader_inputs(); raw = PIN_PATH.read_bytes(); pins = json.loads(raw)['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gameassembly, metadata=metadata)
        if gate.status != 'validated':
            return dict(status=gate.status, detail=gate.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        from scripts.game_data.memorypack import levelscript_action_route_components as sources
        from scripts.game_data.codecs.levelscript import current_generated_action_route as codec
        image = open_native_image(gate.gameassembly, gate.metadata)
        result = sources.derive(image, pins, family=family, tag=tag)
        if (result.get('schema') != sources.SCHEMA or result.get('nativeInputs') != pins
                or (result.get('family'), result.get('tag')) != (family, tag)
                or result.get('wholeOwnerAdmitted') is not False):
            raise ValueError(LABEL+'.same-fresh-selected-route-required')
        if result.get('status') == 'validated':
            codec.validate(result.get('capability'))
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != 'validated':
            return dict(status=after.status, detail='Native inputs changed: '+after.detail)
        failed = pooled_source_helper.check_unity_input(gate.gameassembly, pins)
        if failed:
            return failed
        current = snapshot_complete_reader_inputs()
        if before != current or raw != PIN_PATH.read_bytes():
            raise ValueError(LABEL+'.source-or-contract-drift:'+str(reader_input_changes(before, current))[:1200])
        # Large source/child proofs belong to the fresh batch report. The
        # lexical cache only needs the validated finite cursor capability.
        compact = {key: result[key] for key in ('schema', 'status', 'family', 'tag',
            'wrapperName', 'capability', 'reason', 'pending', 'wholeOwnerAdmitted') if key in result}
        return dict(compact, nativeInputs=pins,
            nativeSources={'GameAssembly.dll': str(Path(gate.gameassembly).resolve()),
                'global-metadata.dat': str(Path(gate.metadata).resolve())})
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        return native_validation_failure(error, label=LABEL, source_path=PIN_PATH)
