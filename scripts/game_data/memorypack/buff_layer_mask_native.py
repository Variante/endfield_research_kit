"""Current atomic LayerMask source and its actual four-byte Advance callee."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import unmanaged_word_source as source

SCHEMA='endfield.memorypack-layer-mask-source-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_layer_mask_source_native.json'
LABEL='layerMaskSource'


def derive(image,inputs,reviewed=None):
    if reviewed is None:
        import json
        reviewed=json.loads(CONTRACT_PATH.read_bytes())
    source.need('layerMask.schema',reviewed.get('schema')==SCHEMA and reviewed.get('typeName')=='UnityEngine.LayerMask')
    return source.derive(image,inputs,reviewed)


def validate_on_image(image,inputs):
    import sys
    return source.validate_on_image(sys.modules[__name__],image,inputs)


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    import sys
    return source.validate_current(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata)
