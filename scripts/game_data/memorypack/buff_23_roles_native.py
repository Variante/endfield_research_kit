"""Reprove BroadcastAlertToCharacters member11 and SkillAlert member9 roles."""
from __future__ import annotations

import json
from scripts.common import check_installed_native_inputs
from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import native_validation_failure,open_native_image,read_reviewed_contract
from scripts.game_data.memorypack import buff_ec_profiles_native as ec,buff_scoped_roles

SCHEMA='endfield.buff-23-profile-roles-native.v1'
CONTRACT_PATH=CONTRACTS_DIR/'buff_23_roles_native.json'
PROJECTION_PATH=CONTRACTS_DIR/'buff_23_native.json'
LABEL='buff23ProfileRoles'


def need(check,condition,detail=None):
    if not condition:raise ValueError(f'{LABEL}.{check}:{str(detail)[:700]}')


def derive(image,inputs,reviewed,projection):
    need('schema',reviewed.get('schema')==SCHEMA and reviewed.get('projection')==PROJECTION_PATH.name)
    need('claim-set',[c['profile'] for c in reviewed['claims']]==['member11','skillAlert9'])
    return buff_scoped_roles.derive(image,inputs,reviewed,projection,
        role_contract=CONTRACT_PATH.name,dependencies=[ec.CONTRACT_PATH.name])


def validate_candidate_on_image(image,inputs,reviewed,projection):
    need('schema-and-status',reviewed.get('schema')==SCHEMA and reviewed.get('status')=='exact-current-build')
    need('native-inputs',reviewed['nativeInputs']==inputs)
    need('required-role-contract',projection.get('schemaVersion')==2 and projection.get('roleContract')==CONTRACT_PATH.name
        and bool(projection.get('codeWindows')) and all(w.get('requiredRoleContract')==CONTRACT_PATH.name for w in projection['codeWindows']))
    actual,projected=derive(image,inputs,reviewed,projection)
    need('reviewed-proof',actual==reviewed,ec.first_difference(reviewed,actual))
    need('projection-current',projected==projection,ec.first_difference(projection,projected))
    return dict(status='validated',nativeInputs=inputs,roleContract=CONTRACT_PATH.name,
        profiles={p['profile']:len(p['events']) for p in actual['proof']['profiles']},evidenceBoundary=actual['evidenceBoundary'])


def validate_on_image(image,inputs,*,projection=None):
    reviewed,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    return validate_candidate_on_image(image,inputs,reviewed,
        projection if projection is not None else json.loads(PROJECTION_PATH.read_bytes()))


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    if (gameassembly is None)!=(metadata is None):raise ValueError(f'{LABEL}.native:both-selected-paths-required')
    try:
        reviewed,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
        inputs=reviewed['nativeInputs'];gate=check_installed_native_inputs(inputs['GameAssembly.dll'],inputs['global-metadata.dat'],
            gameassembly=gameassembly,metadata=metadata)
        if gate.status!='validated':return dict(status=gate.status,detail=gate.detail)
        image=open_native_image(gate.gameassembly,gate.metadata)
        _publication_gate(image,inputs);result=validate_on_image(image,inputs);_publication_gate(image,inputs)
        return result
    except (ValueError,KeyError,IndexError,TypeError,OSError) as error:
        return native_validation_failure(error,label=LABEL,source_path=CONTRACT_PATH)
