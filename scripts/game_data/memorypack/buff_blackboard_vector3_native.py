"""Current BlackboardVector3 wire program: three BlackboardDouble children."""
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import blackboard_profile_source as source

SCHEMA='endfield.buff-blackboard-vector3-native-contract.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_blackboard_vector3_native.json'
LABEL='blackboardVector3Source'


def derive(image,inputs,reviewed=None):
    if reviewed is None:
        import json
        reviewed=json.loads(CONTRACT_PATH.read_bytes())
    source.need('blackboardVector3.schema',reviewed.get('schema')==SCHEMA)
    return source.derive(image,inputs,reviewed,kind='vec')


def validate_on_image(image,inputs):
    import sys
    return source.validate_on_image(sys.modules[__name__],image,inputs)


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    import sys
    return source.validate_current(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata)
