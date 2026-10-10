"""Authenticate selected PE imports and relation caller argument/counter control.

Gates the reviewed contract against the selected build (``native_owner``) and
rechecks the parent join; the body conclusions and their evidence tiers are
stated in ``il2cpp/relation_import_control.py``. A missing or mismatched input yields no claims.
"""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from scripts.game_data.il2cpp.relation_import_control import validate_relation_import_control
from scripts.game_data.memorypack import buff_formatter_relation_control as parent_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint  # read by native_owner.validate_owner
from scripts.game_data.memorypack.native_owner import fail, proof_sources, validate_owner

LABEL = 'buffFormatterRelationImportControl'
SCOPE = 'selected-import-declarations-and-relation-argument-counter-control-only'
PATH = CONTRACTS_DIR / 'buff_formatter_relation_import_control_native.json'


def _fail(check, expected, actual, *, native_inputs=None):
    fail(LABEL, SCOPE, PATH, check, expected, actual, native_inputs=native_inputs)


def _contract():
    c, _ = read_reviewed_contract(PATH,
        schema='endfield.buff-formatter-relation-import-control-native-contract.v1',
        status='exact-current-build', label=LABEL)
    if (c.get('scope'), c.get('parentContract')) != (SCOPE, 'buff_formatter_relation_control_native.json'):
        _fail('contract-shape', 'reviewed scope and parent', c.get('scope'), native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__, PATH, parent_owner._proof_sources(), NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly, c):
    parent = parent_owner._contract()
    if parent['nativeInputs'] != c['nativeInputs'] or parent['entryRva'] != c['entryRva']:
        _fail('parent-build-entry', (parent['nativeInputs'], parent['entryRva']),
              (c['nativeInputs'], c['entryRva']), native_inputs=c['nativeInputs'])
    parent_summary = parent_owner._validate_selected(gameassembly, parent)
    mapper = load_native_mapper(NATIVE_MAPPER_PATH)
    pe = mapper.PeImage(Path(gameassembly))
    declarations = resolve_named_import_slots(pe, [r['slotRva'] for r in c['imports']])
    if declarations != c['importDeclarations']:
        _fail('pe-import-declarations', c['importDeclarations'], declarations, native_inputs=c['nativeInputs'])
    index = BodyIndex(SimpleNamespace(mapper=mapper, pe=pe, metadata=None))
    summary = validate_relation_import_control(index, parent, c, parent_summary)
    return {**summary, 'exactSelectedImportDeclarations': declarations,
            'actualResolverRelationAndRelationCarrierJoinsRechecked': True,
            'conditions': c['conditions']}


def validate_current_native_contract(*, gameassembly=None, metadata=None):
    return validate_owner(
        sys.modules[__name__], gameassembly=gameassembly, metadata=metadata,
        open_claims={'completeTypedRelationMeaningProved': False,
                     'liveIatValueOrCalleeSelected': False,
                     'actualRuntimeTargetSelected': False,
                     'callbackCursorEqualityProved': False,
                     'positiveListAdmitted': False,
                     'wholeRootAdmitted': False},
        check='native-import-control',
        expected='exact selected import ownership and complete caller argument/counter grammar',
        phase='relation import/control')
