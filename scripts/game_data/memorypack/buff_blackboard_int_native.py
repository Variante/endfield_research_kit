"""Current named BlackboardInt wire program and typed reference request."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import blackboard_profile_source as source

SCHEMA='endfield.buff-blackboard-int-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_blackboard_int_native.json'
LABEL='blackboardIntSource'


def derive(image,inputs,reviewed=None):
    if reviewed is None:
        import json
        reviewed=json.loads(CONTRACT_PATH.read_bytes())
    source.need('blackboardInt.schema',reviewed.get('schema')==SCHEMA)
    return source.derive(image,inputs,reviewed,kind='int')


def validate_on_image(image,inputs):
    import sys
    return source.validate_on_image(sys.modules[__name__],image,inputs)


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    import sys
    return source.validate_current(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata)
