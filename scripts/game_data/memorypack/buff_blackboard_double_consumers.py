"""Current concrete BlackboardDouble consumer cells and complete selected paths.

Actual source fields join independently proved closed scalar destinations.
Normal dispatch selections, ordinary calls and conversion completion remain
conditions; this owner does not prove found values or runtime execution.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import (
    METADATA_HELPER_PATH,NATIVE_MAPPER_PATH,open_native_image,read_reviewed_contract)
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError,_fingerprint,_package_import_closure
from scripts.game_data.memorypack import buff_blackboard_double_data as data
from scripts.game_data.memorypack import closed_scalar_consumers as consumers

LABEL='buffBlackboardDoubleConsumers'
CONTRACT_PATH=CONTRACTS_DIR/'memorypack_blackboard_double_consumers_native.json'


def _contract() -> dict[str,Any]:
    c,_=read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.memorypack-blackboard-double-consumers-native-contract.v1',status='exact-current-build',label=LABEL)
    if c.get('mode')!=consumers.MODE or set(c.get('records',{}))!={'keyGetter','castValue','tryValue'}:
        raise ValueError(f'{LABEL}.contract:scope')
    return c


def _fail(check: str,expected: Any,actual: Any) -> None:
    c=_contract();error=CensusGateError(f'{LABEL}.{check}',source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024],actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL,record=c['runtimeTypeName'],nativeInputs=c['nativeInputs'])
    error.args=(json.dumps(error.diagnostic,sort_keys=True),);raise error


def _skip(status: str,detail: str,pins: dict) -> dict:
    return {'status':status,'detail':detail,'nativeInputs':pins,'wholeActionAdmitted':False,'wholeRootAdmitted':False}


def validate_current_native_contract(*,gameassembly: Path,metadata: Path) -> dict[str,Any]:
    c=_contract();pins=c['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return _skip(gate.status,gate.detail,pins)
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    if not unity.is_file():return _skip('missing','UnityPlayer.dll missing beside selected GameAssembly.dll',pins)
    if _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:return _skip('mismatched','Selected UnityPlayer.dll hash differs',pins)
    paths=set(_package_import_closure(Path(__file__)))|{CONTRACT_PATH,data.CONTRACT_PATH,NATIVE_MAPPER_PATH,METADATA_HELPER_PATH}
    inputs={r['path']:r for r in (_fingerprint(p) for p in paths)}
    fields=data.validate_current_native_contract(gameassembly=gate.gameassembly,metadata=gate.metadata)
    if fields.get('status')!='validated' or fields.get('nativeInputs')!=pins:
        return _skip('mismatched' if fields.get('status')=='validated' else fields.get('status','unresolved'),
                     'Independent closed scalar cells unavailable for selected native inputs',pins)
    declaration=data._contract()
    if declaration['nativeInputs']!=pins or declaration['closedScalarFields']['runtimeTypeDefinition']!=c['runtimeTypeDefinition']:
        _fail('closed-data-identity','Same current concrete runtime declaration',declaration['closedScalarFields']['runtimeTypeDefinition'])
    for before in fields['provenance']['inputs']:
        if before['path'] in inputs and inputs[before['path']]!=before:_fail('dependency-drift',inputs[before['path']],before)
        inputs[before['path']]=before
    image=open_native_image(gate.gameassembly,gate.metadata)
    if image.type_name(c['runtimeTypeDefinition'])!=c['runtimeTypeName']:
        _fail('concrete-type-identity',c['runtimeTypeName'],image.type_name(c['runtimeTypeDefinition']))
    transfer=consumers.validate_consumers(image,c,fields['sourceTransfer'],fail=_fail)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated':return _skip(after.status,after.detail,pins)
    if not unity.is_file() or _fingerprint(unity)['sha256']!=pins['UnityPlayer.dll']:
        return _skip('mismatched' if unity.is_file() else 'missing','Selected UnityPlayer.dll changed during validation',pins)
    for before in inputs.values():
        actual=_fingerprint(Path(before['path']))
        if before!=actual:_fail('source-drift',before,actual)
    return {'status':'validated','nativeInputs':pins,'runtimeTypeName':c['runtimeTypeName'],
        'consumerTransfer':transfer,'dataNativeValidation':fields,'provenance':{'inputs':sorted(inputs.values(),key=lambda r:r['path'])},
        'wholeActionAdmitted':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,
        'lookupBodyOrFoundValueProved':False,'evidenceBoundary':c['evidenceBoundary']}
