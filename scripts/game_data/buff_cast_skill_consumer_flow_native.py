"""Authenticate CastSkill's selected ordinary call-completion return."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.call_completion_return import validate_void_call_boolean_return

CONTRACT_PATH = CONTRACTS_DIR / 'buff_cast_skill_consumer_flow_native.json'
SCHEMA = 'endfield.buff-cast-skill-consumer-flow-native-contract.v1'


def load_consumer_flow(*, gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(CONTRACT_PATH, schema=SCHEMA, status='exact-current-build', label='buffCastSkillConsumerFlow')
    if (len(contract.get('programs', [])) != 1
            or contract['programs'][0]['caller'][1:3] != ['Beyond.Gameplay.Core.CastSkill', 'ExecuteInternal']
            or contract['programs'][0]['callee'][1:3] != ['Beyond.Gameplay.Core.AbilitySystem', 'TryCastSkillDuringAction']):
        raise ValueError('buffCastSkillConsumerFlow.contract-shape')
    pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    result = {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins, 'rows': [],
              'evidenceBoundary': contract['evidenceBoundary'], 'runtimeMeaningExact': False}
    if gate.status != 'validated':
        return result
    unity = Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        return {**result, 'status': 'missing' if not unity.is_file() else 'mismatched', 'detail': 'UnityPlayer.dll missing or mismatched'}
    image = open_native_image(gate.gameassembly, gate.metadata)
    rows = [validate_void_call_boolean_return(image, s) for s in contract['programs']]
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated' or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != pins['UnityPlayer.dll']:
        return {**result, 'status': after.status if after.status != 'validated' else 'mismatched', 'detail': 'native input drift after selected program'}
    return {**result, 'status': 'validated', 'rows': rows}
