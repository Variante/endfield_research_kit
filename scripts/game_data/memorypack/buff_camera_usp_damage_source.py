"""Current named camera/USP/damage fields and static formatter registrations.

This source-only validator does not admit an action, collection or Buff root.
The recursive decoder owns independent children and complete original spans.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.il2cpp.formatter_registration_flow import validate_formatter_registration_flow
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack.action_dispatcher import load_action_routes

LABEL = 'buffCameraUspDamageSource'
CONTRACT_PATH = CONTRACTS_DIR/'buff_camera_usp_damage_actions_native.json'
SCHEMA = 'endfield.buff-camera-usp-damage-actions-native-contract.v1'


def _contract():
    value,_ = read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (set(value['records']) != {'addDynamicCcs','refrainObtainUsp','checkSkillDamageType',
                                  'conditionGroup','condition','damageTypeSource'}
            or len(value['actionDispatch']) != 3
            or set(value['actionDispatch'].values()) != {'addDynamicCcs','refrainObtainUsp','checkSkillDamageType'}
            or any(not isinstance(tag,str) or not tag.isdecimal() or not 0 <= int(tag) <= 65535
                   for tag in value['actionDispatch'])
            or set(value['formatterRegistrations']) != {'cameraGroups','cameraConditions','damageTypeList','damageTypeValue'}):
        raise ValueError(f'{LABEL}:contract-shape')
    return value


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract = _contract();pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gameassembly,metadata=metadata)
    if gate.status != 'validated':
        return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins,'recordMembers':{},'formatterRegistrations':{}}
    unity = Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def unity_matches():return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status':'mismatched' if unity.is_file() else 'missing','detail':'UnityPlayer.dll missing or mismatched',
            'nativeInputs':pins,'recordMembers':{},'formatterRegistrations':{}}
    image = open_native_image(gate.gameassembly,gate.metadata);sources = {};proved = {};audits = {}
    def fail(check,expected,actual,**details):
        raise ValueError(f'{LABEL}:{check}:expected={str(expected)[:1000]}; actual={str(actual)[:1000]}; details={details}')
    for key,record in contract['records'].items():
        name = record['sourceContract']
        if not isinstance(name,str) or Path(name).name != name or not name.endswith('.json'):
            raise ValueError(f'{LABEL}:source-contract-basename')
        if name not in sources:
            path = CONTRACTS_DIR/name;sources[name] = json.loads(path.read_bytes())
            audits[name] = buff_action_read_order(image.pe,image.metadata,image.registration,image.instantiations,
                image.modules,image.owners,source=str(gate.gameassembly),contract_path=path)
        proved.update(named.validate_named_records(image,sources[name],{key:record},label=LABEL,fail=fail))
    registrations = {}
    for key,flow in contract['formatterRegistrations'].items():
        record = contract['records'][flow['sourceRecord']]
        fields = flow['sourceFields']
        if not fields or len(set(fields)) != len(fields):raise ValueError(f'{LABEL}:unique-source-fields={key}')
        source = sources[record['sourceContract']];contexts = []
        for field in fields:
            members = [m for m in record['members'] if m['fieldName'] == field]
            if len(members) != 1 or members[0]['declaredType'] != flow['keyType']:
                raise ValueError(f'{LABEL}:source-field-key={key}.{field}')
            matches = [c for c in source['nestedContexts'] if c['instructionRva'] == members[0]['sourceContextInstructionRva']]
            if len(matches) != 1:raise ValueError(f'{LABEL}:source-context={key}.{field}')
            named.check_typed_context(image,matches[0],flow['keyType'],label=LABEL,fail=fail)
            contexts.append(matches[0])
        image.validate_method_row(flow['ownerMethod'],label=LABEL)
        if not flow['ownerWindow']['startRva'] <= flow['window']['startRva'] < flow['window']['endRva'] <= flow['ownerWindow']['endRva']:
            raise ValueError(f'{LABEL}:registration-owner-window={key}')
        image.check_windows([flow['ownerWindow']],label=LABEL)
        summaries = [validate_formatter_registration_flow(image,flow,context,label=LABEL+'.'+key)
                     for context in contexts]
        if any(row != summaries[0] for row in summaries):
            raise ValueError(f'{LABEL}:all-source-fields-register-identical-key={key}')
        registrations[key] = {**summaries[0],'sourceFields':fields}
    routes,audit = load_action_routes(gameassembly=gate.gameassembly,metadata=gate.metadata)
    for tag,key in contract['actionDispatch'].items():
        record = contract['records'][key];route = routes.get(int(tag))
        if (audit['status'] != 'validated' or route is None or route.status != 'resolved'
                or route.wrapper_name != record['wrapperTypeName']
                or list(route.member_order) != [m['fieldName'] for m in record['members']]
                or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
            raise ValueError(f'{LABEL}:current-union-route={key}')
    after = check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status':after.status if after.status!='validated' else 'mismatched',
            'detail':'native inputs changed during source validation','nativeInputs':pins,
            'recordMembers':{},'formatterRegistrations':{}}
    return {'status':'validated','scope':'named-fields-and-static-formatter-argument-flow-only',
        'nativeInputs':pins,'recordMembers':proved,'actionDispatch':contract['actionDispatch'],
        'sourceAudits':audits,'formatterRegistrations':registrations,
        'recursiveStoredSchemaExact':False,'wholeRootAdmitted':False,'runtimeExecutionKnown':False,
        'evidenceBoundary':contract['evidenceBoundary']}
