"""Gate sibling field-setup CFGs, selected homes/counts and named bits."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.field_setup_control import validate_field_setup_control
from scripts.game_data.memorypack import buff_formatter_field_construction as parent_owner
from scripts.game_data.memorypack import buff_formatter_class_fields as setup_owner
from scripts.game_data.memorypack import buff_formatter_context_allocation as allocation_owner
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.native_owner import fail,proof_sources,validate_owner

LABEL='buffFormatterFieldSetup'
SCOPE='complete-owned-ordinary-and-auxiliary-control-selected-field-home-reference-and-ready-joins-only'
PATH=CONTRACTS_DIR/'buff_formatter_field_setup_native.json'


def _fail(check,expected,actual,*,native_inputs=None):
    fail(LABEL,SCOPE,PATH,check,expected,actual,native_inputs=native_inputs)


def _contract():
    c,_=read_reviewed_contract(PATH,schema='endfield.buff-formatter-field-setup-native-contract.v1',status='exact-current-build',label=LABEL)
    if (c.get('scope'),c.get('parentContract'),c.get('setupContract'))!=(SCOPE,parent_owner.PATH.name,setup_owner.PATH.name):
        _fail('contract-shape','reviewed scope and parents',c.get('scope'),native_inputs=c.get('nativeInputs'))
    return c


def _proof_sources():
    return proof_sources(__file__,PATH,parent_owner._proof_sources()+[_fingerprint(allocation_owner.PATH)],NATIVE_MAPPER_PATH)


def _validate_selected(gameassembly,c):
    parent=parent_owner._contract();setup=setup_owner._contract();allocation=allocation_owner._contract()
    mapper=load_native_mapper(NATIVE_MAPPER_PATH);pe=mapper.PeImage(Path(gameassembly));base=pe.image_base
    if any(p['nativeInputs']!=c['nativeInputs'] for p in (parent,setup,allocation)):
        _fail('parent-build','same selected native inputs','one parent build differs',native_inputs=c['nativeInputs'])
    selected={f['role']:f for f in c['functions']}
    if set(selected)!={'ordinaryFields','auxiliary'} or len(c['functions'])!=2:_fail('function-set','two actual sibling roles',list(selected),native_inputs=c['nativeInputs'])
    targets={base+selected['ordinaryFields']['entryRva'],base+selected['auxiliary']['entryRva']};sf=setup['functions']['setup']
    join={'entryRva':sf['entryRva'],'calls':[r for r in sf['calls'] if r['kind']=='call' and r['target'] in targets]}
    if (selected['ordinaryFields']['entryRva'],selected['auxiliary']['entryRva'])!=(sf['ordinaryFieldsTargetRva'],sf['auxiliaryTargetRva']) or join!=c['setupCallerJoin'] or len(join['calls'])!=2:
        _fail('actual-sibling-setup-calls',join,c['setupCallerJoin'],native_inputs=c['nativeInputs'])
    fields={name:setup['physicalFields'][name] for name in ('fields','fieldCount','parent','stateFlags','fieldState')}
    bits=(setup['bits']['hasReferences'],setup['bits']['fieldsReady'],setup['functions']['hasReferences']['entryRva'])
    if c['classFields']!=fields or (c['hasReferencesBit'],c['fieldsReadyBit'],c['hasReferencesTargetRva'])!=bits or c['strideBytes']!=parent['function']['strideBytes']:
        _fail('named-field-and-bit-provenance',(fields,bits,parent['function']['strideBytes']),(c['classFields'],c['hasReferencesBit'],c['strideBytes']),native_inputs=c['nativeInputs'])
    actual={'contract':allocation_owner.PATH.name,'entryRva':allocation['entryRva']}
    if c['allocatorEntryJoin']!=actual or selected['ordinaryFields']['allocationPrefix']['allocatorTargetRva']!=allocation['entryRva']:
        _fail('actual-reviewed-allocator-entry',actual,c['allocatorEntryJoin'],native_inputs=c['nativeInputs'])
    parent_summary=parent_owner._validate_selected(gameassembly,parent)
    index=BodyIndex(SimpleNamespace(mapper=mapper,pe=pe,metadata=None))
    return {**validate_field_setup_control(index,c),'actualNamedParentAndSetupProofsRechecked':True,
            'checkedParentGenericInstructions':parent_summary['checkedInstructions'],
            'allocatorEntryIdentityProvedWithoutTransferringPreviousByteCountDomain':True,'conditions':c['conditions']}


def validate_current_native_contract(*,gameassembly=None,metadata=None):
    return validate_owner(sys.modules[__name__],gameassembly=gameassembly,metadata=metadata,
        open_claims={'completeTypedOrdinaryAuxiliaryEffectsProved':False,'liveClassOrFormatterIdentityProved':False,
            'incomingSlotContentsUnchangedProved':False,'initializationCapacityOrSynchronizationOutcomeProved':False,
            'actualConversionRoundingOrExceptionsProved':False,'callbackCursorEqualityProved':False,
            'positiveListAdmitted':False,'wholeRootAdmitted':False},
        check='native-field-setup-control',expected='complete sibling owned CFG/stores/frames, actual parent calls and selected count/home/reference/ready projections',phase='ordinary and auxiliary setup')
