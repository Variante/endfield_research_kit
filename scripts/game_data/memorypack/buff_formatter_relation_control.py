"""Authenticate complete anonymous relation control and enumerated memory updates.

Gates the reviewed contract against the selected build (``native_owner``) and
rechecks the parent join; the body conclusions and their evidence tiers are
stated in ``il2cpp/relation_control.py``. A missing or mismatched input yields no claims.
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.relation_control import validate_relation_control
from scripts.game_data.memorypack import buff_formatter_carrier_conversion as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint  # read by native_owner.validate_owner
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL='buffFormatterRelationControl'
SCOPE='anonymous-relation-owned-control-and-enumerated-memory-updates-only'
PATH=CONTRACTS_DIR/'buff_formatter_relation_control_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-relation-control-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('schema'),c.get('scope'),c.get('parentContract'))!=(
        'endfield.buff-formatter-relation-control-native-contract.v1',SCOPE,'buff_formatter_resolver_scan_native.json'):
        _fail('contract-shape','reviewed schema, scope and parent',c.get('schema'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract();resolver=parent_owner.parent_owner._contract()
    if resolver['nativeInputs']!=c['nativeInputs'] or parent['nativeInputs']!=c['nativeInputs']:
        _fail('parent-build',c['nativeInputs'],resolver['nativeInputs'],native_inputs=c['nativeInputs'])
    if resolver['calls']['relationPredicate']!=c['entryRva']:
        _fail('actual-parent-callee','actual resolver relation target',c['entryRva'],native_inputs=c['nativeInputs'])
    parent_owner._validate_selected(gameassembly,parent)
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly))
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None));summary=validate_relation_control(index,c)
    if not any(row['targetRva']==parent['entryRva'] for row in summary['directCallSites']):
        _fail('actual-carrier-callee','checked carrier conversion entry',parent['entryRva'],native_inputs=c['nativeInputs'])
    return {**summary,'actualResolverRelationAndRelationCarrierJoinsRechecked':True}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    return validate_owner(
        sys.modules[__name__], gameassembly=gameassembly, metadata=metadata,
        open_claims={'completeTypedRelationMeaningProved': False,
                     'actualRuntimeTargetSelected': False,
                     'callbackCursorEqualityProved': False,
                     'positiveListAdmitted': False,
                     'wholeRootAdmitted': False},
        check='native-control',
        expected='complete owned relation partition, all branch boundaries, guarded tables and enumerated updates',
        phase='relation control')
