"""Authenticate complete anonymous carrier conversion dispatch/read/tail control.

Gates the reviewed contract against the selected build (``native_owner``) and
rechecks the parent join; the body conclusions and their evidence tiers are
stated in ``il2cpp/carrier_conversion_control.py``. A missing or mismatched input yields no claims.
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
from scripts.game_data.il2cpp.carrier_conversion_control import validate_carrier_conversion_control
from scripts.game_data.memorypack import buff_formatter_resolver_scan as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint  # read by native_owner.validate_owner
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL='buffFormatterCarrierConversion'
SCOPE='anonymous-carrier-tag-dispatch-global-read-and-recursive-tail-control-only'
PATH=CONTRACTS_DIR/'buff_formatter_carrier_conversion_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-carrier-conversion-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('schema'),c.get('scope'),c.get('parentContract'))!=(
        'endfield.buff-formatter-carrier-conversion-native-contract.v1',SCOPE,'buff_formatter_resolver_scan_native.json'):
        _fail('contract-shape','reviewed schema, scope and parent',c.get('schema'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _normalization_joins(parent,c):
    cases=[c['initialGlobal'],c['coldGlobal']]+[s for group in c['globalGroups'].values() for s in group]
    joins=[]
    for role in ('normalizationR8','normalizationR9','normalizationR10','normalizationRdx'):
        cell=parent['globalCells'][role];labels=[s['label'] for s in cases if s['globalCellRva']==cell]
        if not labels:_fail('normalization-global-join','actual checked return case for '+role,cell,native_inputs=c['nativeInputs'])
        joins.append({'callerRole':role,'globalCellRva':cell,'actualReturnCaseLabels':labels,
            'addressExpressionsEqual':True,'returnedValueEqualityRequiresStableCompatibleGlobal':True})
    return joins


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract()
    if parent['nativeInputs']!=c['nativeInputs']:_fail('parent-build',c['nativeInputs'],parent['nativeInputs'],native_inputs=c['nativeInputs'])
    if parent['calls']['typeCarrier']!=c['entryRva']:
        _fail('actual-parent-callees','parent actual carrier conversion entry',c['entryRva'],native_inputs=c['nativeInputs'])
    parent_owner._validate_selected(gameassembly,parent)
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly))
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    summary=validate_carrier_conversion_control(index,c)
    return {**summary,'actualParentCarrierCallsAndLowByteFlagRechecked':True,
        'conditionalNormalizationGlobalReturnJoins':_normalization_joins(parent,c)}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    return validate_owner(
        sys.modules[__name__], gameassembly=gameassembly, metadata=metadata,
        open_claims={'childEffectsOrInitializationMeaningProved': False,
                     'actualRuntimeTargetSelected': False,
                     'callbackCursorEqualityProved': False,
                     'positiveListAdmitted': False,
                     'wholeRootAdmitted': False},
        check='native-control',
        expected='complete owned carrier code/data partition, recursive/read/tail control, actual parent calls',
        phase='carrier conversion')
