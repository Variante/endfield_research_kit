"""Authenticate the declared interface and its actual return adapter bytes."""
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import Body, BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.unwind_chains import UnwindChainIndex, read_exception_directory
from scripts.game_data.il2cpp.interface_return_program import check_interface_return_program, check_default_interface_return
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build
from scripts.game_data.memorypack import buff_skill_cast_action_source_consumer as action_source
from scripts.game_data.memorypack.buff_selector_validator_identity_consumer import _rows, _method

CONTRACT_PATH = CONTRACTS_DIR / 'buff_skill_cast_interface_return_claims.json'
LABEL = 'buffSkillCastInterfaceReturn'


def _validate_image(image, contract):
    parent, _ = read_reviewed_contract(CONTRACTS_DIR / contract['parentContract'],
        schema='endfield.buff-skill-cast-action-source-claims.v1', status='reviewed', label=LABEL + '.parent')
    parent_proof = action_source._validate_image(image, parent)
    index = BodyIndex(image); selected = NativeReferenceContext(image, index=index)
    helper_pointer = parent_proof['helperPointer']
    helper = Body('<action-source>', helper_pointer, index._extent(helper_pointer), '', [])
    helper.rows = index._decode(helper.pointer, helper.size)
    helper_rows, _ = _rows(index, helper)
    named_targets = {int(row['text'][5:], 16) for row in helper_rows if row['text'].startswith('call 0x')
        and set(index.names_of(int(row['text'][5:], 16))) & set(parent['namedCalls'].values())}
    traps = {int(helper_rows[i-1]['text'][5:], 16) for i, row in enumerate(helper_rows) if row['text'] == 'int3'}
    calls = [i for i, row in enumerate(helper_rows) if row['text'].startswith('call 0x')
             and int(row['text'][5:], 16) not in named_targets | traps]
    if len(calls) != 1: raise ValueError(LABEL + '.actual-adapter-call')
    call_index = calls[0]; adapter_pointer = int(helper_rows[call_index]['text'][5:], 16)
    loads = [row for row in helper_rows if bytes.fromhex(row['bytes'])[:3] == b'\x4c\x8b\x05']
    if len(loads) != 1: raise ValueError(LABEL + '.actual-interface-context-load')
    load = loads[0]; raw = bytes.fromhex(load['bytes']); at = int(load['va'], 16)
    if len(raw) != 7: raise ValueError(LABEL + '.complete-interface-load')
    cell = at+7+int.from_bytes(raw[3:], 'little', signed=True)
    usage = image.pe.bytes_at_va(cell, 8)
    type_index = unresolved_usage_index(usage, image.registration['typesCount'], tag=1, source=str(image.gameassembly), offset=cell)
    type_pointer = image.pe.u64_at_va(int(image.registration['types'], 16)+type_index*8)
    type_raw = image.pe.bytes_at_va(type_pointer, 16)
    if len(type_raw) != 16 or type_raw[10] != 18 or type_raw[11] & 0x20:
        raise ValueError(LABEL + '.interface-reference-type-record')
    td_index = int.from_bytes(type_raw[:8], 'little')
    if not 0 <= td_index < len(image.metadata.types): raise ValueError(LABEL + '.interface-definition-index')
    interface = image.metadata.types[td_index]
    if (image.type_name(td_index) != contract['interfaceType'] or not interface.flags & 0x20
            or runtime_type_name(image.pe, image.metadata, type_pointer) != contract['interfaceType']):
        raise ValueError(LABEL + '.named-interface-context')
    spec = contract['interfaceMethod']
    methods = [m for m in image.metadata.methods_for(interface)
               if image.metadata.string(m.name_index) == spec['name'] and m.slot == contract['interfaceSlotLiteral']]
    if len(methods) != 1: raise ValueError(LABEL + '.interface-slot-declaration')
    method = methods[0]
    parameters = [selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)]
    if bool(method.flags & 0x10) != spec['isStatic'] or selected.type_name(method.return_type) != spec['returnType'] or parameters != spec['parameterTypes']:
        raise ValueError(LABEL + '.interface-method-signature')
    slot_rows = [row for row in helper_rows[max(0, call_index-3):call_index] if row['text'].startswith('mov edx, 0x')]
    if len(slot_rows) != 1 or int(slot_rows[0]['text'].split('0x')[1], 16) != method.slot:
        raise ValueError(LABEL + '.actual-interface-slot-argument')
    adapter = Body('<actual-interface-return-adapter>', adapter_pointer, index._extent(adapter_pointer), '', [])
    adapter.rows = index._decode(adapter.pointer, adapter.size)
    adapter_rows, adapter_ranges = _rows(index, adapter)
    if len(adapter_ranges) != 1 or adapter_ranges[0][0] != adapter_pointer:
        raise ValueError(LABEL + '.adapter-single-complete-range')
    base = image.pe.image_base
    directory, size, exception_raw = read_exception_directory(image.pe)
    unwind = UnwindChainIndex(exception_raw, lambda at, n: image.pe.bytes_at_va(base+at, n), table_rva=directory, image_size=size)
    family = unwind.family(adapter_pointer-base)
    actual_ranges = sorted((base+r['runtimeTriple'][0], base+r['runtimeTriple'][1]) for r in family['ranges'])
    if actual_ranges != [tuple(r) for r in adapter_ranges]:
        raise ValueError(LABEL + '.complete-exception-family-membership')
    adapter_bytes = image.pe.bytes_at_va(adapter_pointer, adapter_ranges[0][1]-adapter_pointer)
    adapter_proof = check_interface_return_program(adapter_bytes, pointer=adapter_pointer, specification=contract['compiledAdapter'])
    value_bytes = parent_proof['freshFillConsumerProof']['memberFlow']['copiedValueBytes']
    if adapter_proof['copiedReturnBytes'] != value_bytes:
        raise ValueError(LABEL + '.declared-return-copy-size')
    default = index.body(contract['interfaceType'], spec['name'])
    selected_method = _method(image, index, default.pointer, default.symbol)
    if selected_method.index != method.index: raise ValueError(LABEL + '.selected-default-method-row')
    default_rows, default_ranges = _rows(index, default)
    if len(default_ranges) != 1 or default_ranges[0][0] != default.pointer:
        raise ValueError(LABEL + '.complete-default-range')
    default_bytes = image.pe.bytes_at_va(default.pointer, default_ranges[0][1]-default.pointer)
    default_proof = check_default_interface_return(default_bytes,
        expected_program=contract['defaultReturnProgramHex'], copied_value_bytes=value_bytes)
    return {'freshParentProof': parent_proof, 'interface': {'definition': td_index,
        'registeredTypeIndex': type_index, 'diskUsageCellVa': cell, 'diskUsageHex': usage.hex().upper(),
        'typePointerVa': type_pointer, 'typeRawHex': type_raw.hex().upper(), 'type': contract['interfaceType'],
        'methodIndex': method.index, 'method': spec['name'], 'slot': method.slot, 'returnType': spec['returnType']},
        'adapterPointer': adapter_pointer, 'adapterUnwindFamily': family, 'adapter': adapter_proof,
        'defaultMethodPointer': default.pointer, 'defaultMethod': default_proof,
        'selectedDefaultTargetObserved': False, 'liveInterfaceCellObserved': False, 'runtimeExecutionKnown': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-skill-cast-interface-return-claims.v1', status='reviewed', label=LABEL)
    pins = selected_build._contract()['nativeInputs']
    def empty(status, detail):
        return {'status': status, 'detail': detail, 'nativeInputs': pins, 'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    before = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if before.status != 'validated': return empty(before.status, before.detail)
    unity = before.gameassembly.parent / 'UnityPlayer.dll'
    def matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll missing or mismatched')
    proof = _validate_image(open_native_image(before.gameassembly, before.metadata), contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=before.gameassembly, metadata=before.metadata)
    if after.status != 'validated': return empty(after.status, after.detail)
    if not matches(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll changed during validation')
    return {'status': 'validated', 'nativeInputs': pins, 'proof': proof, 'evidenceBoundary': contract['evidenceBoundary'],
            'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
