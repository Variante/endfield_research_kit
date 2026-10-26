"""Gate named class bits and the actual input-helper field-preparation join."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.pe_exports import resolve_named_exports
from scripts.game_data.il2cpp.pe_imports import resolve_named_import_slots
from scripts.game_data.il2cpp.class_field_control import EXPORTS,validate_class_field_control
from scripts.game_data.memorypack import buff_formatter_incoming_address as parent_owner
from scripts.game_data.memorypack import buff_formatter_class_ancestry as ancestry_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterClassFields'
SCOPE='named-class-bits-field-iterator-preparation-and-input-helper-bit-transfer-only'
PATH=CONTRACTS_DIR/'buff_formatter_class_fields_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-class-fields-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'))!=(SCOPE,'buff_formatter_incoming_address_native.json'):
        _fail('contract-shape','reviewed scope and parent',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources(),NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract();ancestry=ancestry_owner._contract();entry=c['functions']['setup']['entryRva']
    known=set(parent['function']['incomingAddressCallRvas'])
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));base=pe.image_base
    actual={'entryRva':parent['function']['entryRva'],
            'calls':[r for r in parent['function']['calls'] if r['kind']=='call' and r['target']==base+entry]}
    if parent['nativeInputs']!=c['nativeInputs'] or ancestry['nativeInputs']!=c['nativeInputs'] or c['incomingCallerJoin']!=actual or not actual['calls']:
        _fail('actual-incoming-field-setup-join',actual,c['incomingCallerJoin'],native_inputs=c['nativeInputs'])
    if not all(r['siteRva'] in known for r in actual['calls']):
        _fail('incoming-address-call-provenance','selected original-address register value',actual['calls'],native_inputs=c['nativeInputs'])
    if c['physicalFields']['parent']!=ancestry['physicalFields']['parent'] or c['protocol']!=ancestry['protocol']:
        _fail('named-parent-and-protocol-provenance',ancestry['protocol'],c['protocol'],native_inputs=c['nativeInputs'])
    p=c['callerBlittableInheritance']['window'];owned=parent['function']['ownedWindows']
    if not any(w['startRva']<=p['startRva']<p['endRva']<=w['endRva'] for w in owned):
        _fail('caller-projection-owned-boundary','inside actual input-helper owned bytes',p,native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,parent)
    exports=resolve_named_exports(pe,EXPORTS)
    if exports!=c['exportDeclarations']:_fail('selected-named-export-declarations',c['exportDeclarations'],exports,native_inputs=c['nativeInputs'])
    imports=resolve_named_import_slots(pe,[c['functions']['bridge']['releaseSlotRva']])
    if imports!=c['releaseImportDeclarations']:_fail('selected-release-import-declaration',c['releaseImportDeclarations'],imports,native_inputs=c['nativeInputs'])
    old={r['slotRva']:r for r in parent['importDeclarations']['selectedImports']}
    if any(old.get(r['slotRva'])!=r for r in imports['selectedImports']):
        _fail('parent-release-import-provenance','same on-disk declaration',imports,native_inputs=c['nativeInputs'])
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    summary=validate_class_field_control(index,c,exports)
    return {**summary,'actualIncomingHelperAndNamedAncestryParentRechecked':True,
            'checkedParentIncomingInstructions':parent_summary['checkedInstructions'],
            'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    return validate_owner(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata,
        open_claims={'liveClassOrFormatterIdentityProved':False,'incomingSlotContentsUnchangedProved':False,
                     'initializationCapacityOrSynchronizationOutcomeProved':False,'recursiveTerminationProved':False,
                     'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-class-fields-control',expected='actual input-helper/setup join, named export/bit/field consumers and complete preparation programs',phase='class field control')
