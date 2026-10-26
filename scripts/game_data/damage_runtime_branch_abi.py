"""Selected-build ABI witness for the named damage capture root."""
from __future__ import annotations

import hashlib

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.damage_process_formula_native import validate_windows
from scripts.game_data.il2cpp.native_image import read_reviewed_contract

CONTRACT = CONTRACTS_DIR / 'damage_runtime_branch_abi_native.json'
SCHEMA = 'endfield.damage-runtime-branch-abi-native-contract.v1'


def validate_damage_branch_abi(selected, hook, parameter):
    """Use reviewed native consumers, never an arbitrary byte-pattern match."""
    from scripts.game_data.mission_trace_capture_prepare import PreparationError

    if (hook['type'], hook['method'], parameter['name'], parameter['type']) != (
            'Beyond.Gameplay.Core.DamageAction', '_ProcessDamage', 'transferredSource',
            'Beyond.ObjectPtr`1<Beyond.Gameplay.Core.AbilitySystem>'):
        raise PreparationError('damage_branch.abi: no reviewed native argument witness')
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA,
                                         label='damage_branch_abi', status='reviewed')
    image = selected.image
    for key, raw in (('gameAssemblySha256', image.pe.buf), ('metadataSha256', image.metadata.buf)):
        if hashlib.sha256(raw).hexdigest().lower() != contract['nativeInputs'][key].lower():
            raise PreparationError('damage_branch.abi: selected native input mismatch: ' + key)
    failures = validate_windows(image, contract)
    if failures:
        raise PreparationError('damage_branch.abi: reviewed native window mismatch: ' + str(failures[0]))
    witness = contract.get('captureAbi')
    if not isinstance(witness, dict) or witness.get('parameter') != parameter['name']:
        raise PreparationError('damage_branch.abi: reviewed native consumer declaration missing')
    _, _, entry = selected.resolve(hook)
    if entry - image.pe.image_base != int(witness['entryRva'], 16):
        raise PreparationError('damage_branch.abi: selected named entry differs')
    required = set(witness['requiredWindows'])
    if not required or not required <= {row['name'] for row in contract['windows']}:
        raise PreparationError('damage_branch.abi: required native windows missing')
    return dict(contractSchema=SCHEMA, **witness)
