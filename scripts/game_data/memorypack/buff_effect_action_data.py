"""Current named source/destination proof for concrete EffectActionData.

This record is also used as a concrete Stack child. Its source proof does not
establish collection framing or justify prepending an AbilityAction union tag.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError
from scripts.game_data.memorypack import named_native_records as named

LABEL = 'buffEffectActionData'
CONTRACT_PATH = CONTRACTS_DIR / 'buff_effect_action_data_native.json'


def _contract() -> dict[str, Any]:
    value, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-effect-action-data-native-contract.v1',
        status='exact-current-build', label=LABEL)
    if set(value.get('records', {})) != {'effectAction'}:
        raise ValueError(f'{LABEL}.contract:shape')
    record=value['records']['effectAction']
    if (len(record['members']) != 18 or record['inheritedMemberCount'] != 4
            or record['runtimeTypeName'] != 'Beyond.Gameplay.Core.EffectAction+EffectActionData'
            or record['members'][1]['fieldName'] != 'priorityLevel'
            or record['members'][1].get('inlineSource', {}).get('mode') != 'inline-cursor-scalar32'):
        raise ValueError(f'{LABEL}.contract:concrete-source-profile')
    return value


def _fail(check: str, expected: Any, actual: Any, *, record: str = 'effectAction', field: str = '') -> None:
    contract=_contract()
    error=CensusGateError(f'{LABEL}.{check}',
        source=(CONTRACTS_DIR / contract['records'][record]['sourceContract']).as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, record=record, field=field, nativeInputs=contract['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),)
    raise error


def validate_current_native_contract() -> dict[str, Any]:
    contract=_contract();expected=contract['nativeInputs']
    gate=check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'])
    if gate.status != 'validated':
        return {'status':gate.status,'detail':gate.detail,'nativeInputs':expected}
    unity=Path(gate.gameassembly).parent / 'UnityPlayer.dll'
    actual=hashlib.sha256(unity.read_bytes()).hexdigest().upper() if unity.is_file() else 'missing'
    if actual != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll',expected['UnityPlayer.dll'],actual)
    image=open_native_image(gate.gameassembly,gate.metadata)
    path=CONTRACTS_DIR / contract['records']['effectAction']['sourceContract']
    source=json.loads(path.read_bytes())
    buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,
        image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
    proved=named.validate_named_records(image,source,contract['records'],label=LABEL,fail=_fail)
    after=check_installed_native_inputs(expected['GameAssembly.dll'],expected['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated':
        return {'status':after.status,'detail':after.detail,'nativeInputs':expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after',expected['UnityPlayer.dll'],'mismatched')
    return {'status':'validated','nativeInputs':expected,'recordMembers':proved,
            'evidenceBoundary':contract['evidenceBoundary'],'positiveCollectionAdmitted':False}
