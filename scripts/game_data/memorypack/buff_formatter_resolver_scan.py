"""Authenticate complete anonymous resolver scan/code/table control.

Gates the reviewed contract against the selected build (``native_owner``) and
rechecks the parent join; the body conclusions and their evidence tiers are
stated in ``il2cpp/resolver_scan_control.py``. A missing or mismatched input yields no claims.
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
from scripts.game_data.il2cpp.resolver_scan_control import validate_resolver_scan_control
from scripts.game_data.memorypack import buff_formatter_dispatch_fallback as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint  # read by native_owner.validate_owner
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL='buffFormatterResolverScan'
SCOPE='anonymous-generic-record-parameter-scan-and-bounded-table-control-only'
PATH=CONTRACTS_DIR/'buff_formatter_resolver_scan_native.json'


def _fail(check, expected, actual):
    fail(LABEL, SCOPE, PATH, check, expected, actual)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-resolver-scan-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('schema'),c.get('scope'),c.get('parentContract'))!=(
        'endfield.buff-formatter-resolver-scan-native-contract.v1',SCOPE,'buff_formatter_dispatch_fallback_native.json'):
        _fail('contract-shape','reviewed schema, scope and parent',c.get('schema'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract()
    if parent['nativeInputs']!=c['nativeInputs']:_fail('parent-build',c['nativeInputs'],parent['nativeInputs'])
    if parent['calls']['resolverFirst']!=c['entryRva'] or parent['programs']['prepareTail']['entryRva']!=c['calls']['prepare']:
        _fail('actual-parent-callees','parent direct resolver and validated preparation tail',c['calls'])
    parent_owner._validate_selected(gameassembly,parent)
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly))
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_resolver_scan_control(index,c),'actualParentDispatchAndPreparationTransfersRechecked':True}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    return validate_owner(
        sys.modules[__name__], gameassembly=gameassembly, metadata=metadata,
        open_claims={'childEffectsOrInitializationMeaningProved': False,
                     'actualRuntimeTargetSelected': False,
                     'callbackCursorEqualityProved': False,
                     'positiveListAdmitted': False,
                     'wholeRootAdmitted': False},
        check='native-control',
        expected='complete owned code/data partition, scan and leaf control, actual parent calls',
        phase='resolver scan', pass_native_inputs=False)
