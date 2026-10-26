"""Four common action operands returned into inherited wrapper setters.

The selected buffered paths keep a reader and a ref-wrapper in Win64
nonvolatile registers. Each setter loads the metadata-owned base Data
reference before storing its primitive operand. External refill and error
callees, object creation and live condition evaluation remain unproved.
"""
from __future__ import annotations

from typing import Any, Callable
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import setter_output_sources as setters


def validate_inherited_action_sources(image: Any, source: dict, record: dict, *, fail: Callable) -> dict:
    proof = record['inheritedActionSource']
    order = [('isEnable', 'byte'), ('priorityLevel', 'scalar32'),
             ('priorityOffset', 'scalar32'), ('serverActionIndex', 'scalar32')]
    if (proof.get('mode') != 'reader-rdi-ref-wrapper-rbx-four-common-primitives'
            or record.get('inheritedMemberCount') != 4
            or [(m['fieldName'], m['kind']) for m in record['members']] != order):
        fail('inherited-action-scope', 'four inherited common primitive members', proof)
    selected = NativeReferenceContext(image)
    wrapper = proof['baseWrapperName']; data = proof['baseDataName']
    if (selected.parent(record['wrapperTypeName']) != wrapper
            or selected.parent(record['runtimeTypeName']) != data
            or selected.is_value_type(wrapper) or selected.is_value_type(data)):
        fail('inherited-action-base-types', [wrapper, data],
             [selected.parent(record['wrapperTypeName']), selected.parent(record['runtimeTypeName'])])
    owner, declared, instance = selected.field(wrapper + '::' + proof['baseInstanceField'])
    if owner != wrapper or declared != data or not 0 <= instance < 128:
        fail('inherited-action-instance-field', [wrapper, data, 'disp8 reference'], [owner, declared, instance])
    normal = next(w for w in source['codeWindows'] if w['startRva'] == record['readerMethod'][3])
    setters._parent(image, normal, record, proof, fail)
    for index, member in enumerate(record['members']):
        mode = 'normalized-byte-return' if index == 0 else 'int32-return'
        primitive = 'normalized-byte-return' if index == 0 else 'scalar32-return'
        transfer = member['setterTransfer']
        if transfer.get('mode') != mode or member['primitiveSource'].get('mode') != primitive:
            fail('inherited-action-operand-mode', [mode, primitive], [transfer.get('mode'), member['primitiveSource'].get('mode')])
        context = next((c for c in source['nestedContexts']
                        if c['instructionRva'] == member.get('sourceContextInstructionRva')), None)
        setters.validate_primitive_source(image, source, member, fail=fail)
        setters._bridge(image, normal, member, final=index == 3, context=context, fail=fail)
        method = image.metadata.methods[member['setterMethodIndex']]
        parameters = list(image.metadata.parameters_for(method))
        if (method.flags & 0x10 or image.type_name(method.declaring_type) != wrapper
                or len(parameters) != 1 or selected.type_name(parameters[0].type_index) != member['declaredType']
                or selected.type_name(method.return_type) != 'void'):
            fail('inherited-action-setter-type', 'instance void base setter with exact operand type', member['fieldName'])
        field_owner, field_type, offset = selected.field(data + '::' + member['fieldName'])
        if field_owner != data or field_type != member['declaredType'] or not 0 <= offset < 128:
            fail('inherited-action-data-field', [data, member['declaredType'], 'disp8'], [field_owner, field_type, offset])
        if (index == 0 and field_type != 'bool'
                or index and field_type != 'int' and not selected.is_enum(field_type)):
            fail('inherited-action-field-representation', 'Boolean or int/enum DWORD', field_type)
        rows = transfer['setterProgram']
        if len(rows) != 9:
            fail('inherited-action-setter-count', 9, rows)
        call = transfer['errorCall']
        named.check_call(image, call, label='inheritedActionSource', fail=fail)
        expected = [b'\x48\x83\xec\x28', b'\x48\x8b\x41' + bytes((instance,)),
                    b'\x48\x85\xc0', b'\x74\x08',
                    (b'\x88\x50' if index == 0 else b'\x89\x50') + bytes((offset,)),
                    b'\x48\x83\xc4\x28', b'\xc3',
                    image.pe.bytes_at_va(image.pe.image_base + call['rva'], 5), b'\xcc']
        window = next(w for w in source['codeWindows'] if w['startRva'] == member['assignment']['targetRva'])
        setters._program(image, window, rows, expected, fail)
        if (rows[0][0] != member['assignment']['targetRva'] or rows[7][0] != call['rva']
                or rows[3][0] + 2 + 8 != rows[7][0]):
            fail('inherited-action-setter-extent', 'actual setter entry and complete null/error branch', rows)
    return {'fieldsForwardedToBaseData': 4, 'bufferedPayloadBytes': 13,
            'booleanNormalization': 'zero-to-false; nonzero-to-true; raw stored source bits retained',
            'evidenceBoundary': 'conditional',
            'condition': 'selected buffered paths and ordinary child returns preserving Win64 nonvolatile registers',
            'refillExecutionKnown': False, 'conditionEvaluationKnown': False, 'liveExecutionKnown': False}
