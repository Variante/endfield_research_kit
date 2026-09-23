"""Shared gate, hashing and sweep helpers for the IL2CPP context audit.

Moved verbatim out of ``context_audit``; that module owns the audit
contract and the report it assembles.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.il2cpp.context import ContextError, GenericInstantiationTable, method_parameter_owner, type_image_owners, match_image_modules, method_spec_usage_index, generic_type_carrier, select_rgctx_range, unresolved_usage_index, rip_qword_load_target
from scripts.game_data.il2cpp.context import method_spec_record, usage_method_spec, relative_branch_target, method_token_pointer
from scripts.repo_paths import REPO_ROOT

ROOT = REPO_ROOT

# The selected build and its reviewed code windows are declarations, not
# algorithm, so they live in a reviewed contract beside the other native contracts.
NATIVE_CONTRACT_PATH = CONTRACTS_DIR / 'il2cpp_context_audit_native.json'
NATIVE_CONTRACT, _NATIVE_CONTRACT_DIGEST = read_reviewed_contract(
    NATIVE_CONTRACT_PATH,
    schema='endfield.il2cpp-context-audit-native-contract.v2',
    label='il2cpp-context-audit',
    status='exact-current-build',
)
GA_SHA = NATIVE_CONTRACT['nativeInputs']['GameAssembly.dll'].upper()
MD_SHA = NATIVE_CONTRACT['nativeInputs']['global-metadata.dat'].upper()
UNITY_SHA = NATIVE_CONTRACT['nativeInputs']['UnityPlayer.dll'].upper()
CORPUS_REPORT_RELATIVE = 'reports/animestudio/skilldata_cursor_basis_latest.json'
CONSUMER_WINDOWS = tuple(
    (int(begin, 16), int(end, 16), digest)
    for begin, end, digest in NATIVE_CONTRACT['consumerWindows']
)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def require(actual, expected, source, offset=0):
    if actual != expected:
        raise ContextError(str(source), offset, expected, actual)


def native_gate():
    gate = check_installed_native_inputs(GA_SHA, MD_SHA)
    require(gate.status, 'validated', 'selected native inputs: ' + gate.detail)
    return gate


def sweep(table):
    rows, failures = [], []
    for index in range(table.count):
        try:
            rows.append(table.resolve(index).as_dict())
        except ContextError as error:
            failures.append({'index': index, **error.diagnostics})
    return {'success': len(rows), 'failed': len(failures), 'unsupported': 0}, rows, failures


def validate_selected_method_spec(row, records, base, method_count, instantiation_count, *, source):
    """Verify emitted identity against raw records, independently of loop locals."""
    if not isinstance(row,dict) or len(records)%12:
        raise ContextError(source,base,'MethodSpec evidence object and exact record array',type(row).__name__)
    index=row.get('index')
    if type(index) is not int or not 0<=index<len(records)//12:
        raise ContextError(source,base,'bounded reported MethodSpec index',index)
    offset=base+index*12
    raw=records[index*12:(index+1)*12]
    definition,_,method_inst=method_spec_record(raw,method_count,instantiation_count,source=source,offset=offset)
    for key,expected in (('va',offset),('rawHex',raw.hex().upper()),('definition',definition)):
        if row.get(key)!=expected:
            raise ContextError(source,offset,f'reported {key} matches raw MethodSpec',
                               {'expected':expected,'actual':row.get(key)})
    inst=row.get('methodInstantiation')
    if not isinstance(inst,dict) or inst.get('index')!=method_inst:
        raise ContextError(source,offset+8,'reported method instantiation matches raw MethodSpec',
                           {'expected':method_inst,'actual':inst})
