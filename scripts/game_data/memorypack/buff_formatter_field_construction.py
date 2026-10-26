"""Gate actual generic field construction, named getters and shared clear."""
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
from scripts.game_data.il2cpp.field_construction_control import GETTERS,validate_field_construction_control
from scripts.game_data.il2cpp.byte_fill_control import validate_byte_fill_control
from scripts.game_data.memorypack import buff_formatter_class_fields as parent_owner
from scripts.game_data.memorypack import buff_formatter_clear_tail as clear_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterFieldConstruction'
SCOPE='named-field-layout-and-complete-generic-construction-only'
PATH=CONTRACTS_DIR/'buff_formatter_field_construction_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-field-construction-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'),c.get('clearContract'))!=(SCOPE,parent_owner.PATH.name,clear_owner.PATH.name):
        _fail('contract-shape','reviewed scope and two contracts',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources()+[_fingerprint(clear_owner.PATH)],NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract();clear=clear_owner._contract();f=c['function'];setup=parent['functions']['setup']
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));base=pe.image_base
    join={'entryRva':setup['entryRva'],'calls':[r for r in setup['calls'] if r['kind']=='call' and r['target']==base+f['entryRva']]}
    if parent['nativeInputs']!=c['nativeInputs'] or clear['nativeInputs']!=c['nativeInputs']:
        _fail('parent-build','same explicit selected native inputs',(parent['nativeInputs'],clear['nativeInputs']),native_inputs=c['nativeInputs'])
    if setup['genericFieldsTargetRva']!=f['entryRva'] or join!=c['setupCallerJoin'] or not join['calls']:
        _fail('actual-generic-construction-call',join,c['setupCallerJoin'],native_inputs=c['nativeInputs'])
    expected={name:parent['physicalFields'][name] for name in ('fields','fieldCount','genericLink')}
    if c['classFields']!=expected or parent['functions']['fieldIterator']['strideBytes']!=f['strideBytes']:
        _fail('named-field-base-count-stride',expected,c['classFields'],native_inputs=c['nativeInputs'])
    if (c['genericReceiver']['entryRva'],c['genericReceiver']['tailTargetRva'])!=(setup['genericReceiverTargetRva'],parent['callerBlittableInheritance']['genericDefinitionTargetRva']):
        _fail('actual-generic-receiver-wrapper','same actual setup/bit-transfer helper',c['genericReceiver'],native_inputs=c['nativeInputs'])
    if f['clearTargetRva']!=clear['entryRva']:
        _fail('actual-shared-clear-entry',clear['entryRva'],f['clearTargetRva'],native_inputs=c['nativeInputs'])
    exports=resolve_named_exports(pe,GETTERS)
    if exports!=c['exportDeclarations']:_fail('selected-field-getter-declarations',c['exportDeclarations'],exports,native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,parent)
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    summary=validate_field_construction_control(index,c,exports)
    fill=validate_byte_fill_control(index,clear)
    required=('normalReturnEqualsIncomingDestinationProved','allRequestedBytesEqualLowIncomingValueByteConditionallyProved')
    if not all(fill.get(name) is True for name in required):
        _fail('shared-clear-value-and-return',required,fill,native_inputs=c['nativeInputs'])
    return {**summary,'actualCompleteSetupParentRechecked':True,'checkedParentFieldInstructions':parent_summary['checkedInstructions'],
            'checkedSharedClearInstructions':fill['checkedInstructions'],
            'allGenericRequestedBytesZeroConditionallyProved':True,
            'genericPublishedFieldsEqualReservedOldCursorConditionallyProved':True,
            'sharedClearConditionsRequired':['writable valid memory','compatible CPU and REP DF=0','nonwrapping endpoints','payload/control/stack storage noninterference'],
            'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    return validate_owner(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata,
        open_claims={'liveClassOrFormatterIdentityProved':False,'receiverCountEqualsSavedSourceCountProved':False,
            'incomingSlotContentsUnchangedProved':False,'allocationSuccessCapacityAndRuntimeExecutionProved':False,
            'actualTypeSubstitutionProved':False,'allStoresGloballyVisibleAtReturnProved':False,
            'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-field-construction-control',expected='complete generic construction, named field layout, parent call and shared clear joins',phase='generic field construction')
