"""Static allocation/constructor/Register argument flow for one formatter.

The domain caller owns native input gates, reviewed windows and source-field
types. A checked static argument flow does not observe initialization, cache
mutation, provider selection or the formatter's serialized grammar.
"""
from __future__ import annotations

import struct

from .formatter_composition import validate_typed_usage_context
from .reference_layouts import NativeReferenceContext
from .protocol import runtime_type_name


def validate_formatter_registration_flow(image, flow, source_context, *, label):
    allocation, constructor, registration = (flow[k] for k in ('allocation','constructor','registration'))
    definition = flow['formatterDefinition']
    if definition not in ('MemoryPack.Formatters.ListFormatter`1','MemoryPack.Formatters.UnmanagedFormatter`1'):
        raise ValueError(f'{label}:unsupported-formatter-definition')
    for usage in (allocation,constructor,registration):
        validate_typed_usage_context(image,usage,label=label)
    if (allocation['tag'] != 1 or constructor['tag'] != 6 or registration['tag'] != 6
            or constructor['typeName'] != definition or constructor['methodName'] != '.ctor'
            or constructor['methodArguments'] != [] or len(constructor['classArguments']) != 1
            or registration['typeName'] != 'MemoryPack.MemoryPackFormatterProvider'
            or registration['methodName'] != 'Register' or registration['classArguments'] != []
            or registration['methodSpec'][2] != source_context['methodSpec'][2]):
        raise ValueError(f'{label}:constructor-and-source-registration-key')
    selected = NativeReferenceContext(image)
    pointer = selected.type_pointer(allocation['typeIndex']);raw = image.pe.bytes_at_va(pointer,16)
    if raw[10:12] != b'\x15\x00':
        raise ValueError(f'{label}:allocated-generic-reference')
    definition_pointer,instance_pointer = struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16))
    instance = image.instantiations.resolve_pointer(instance_pointer)
    key = image.instantiations.resolve(source_context['methodSpec'][2])
    if (runtime_type_name(image.pe,image.metadata,definition_pointer) != definition
            or instance.index != constructor['methodSpec'][1] or len(instance.arguments) != 1
            or len(key.arguments) != 1):
        raise ValueError(f'{label}:same-allocated-and-constructed-formatter')
    element = instance.arguments[0].type_pointer_va;key_pointer = key.arguments[0].type_pointer_va
    key_name = runtime_type_name(image.pe,image.metadata,key_pointer)
    if registration['methodArguments'] != [key_name] or key_name != flow['keyType']:
        raise ValueError(f'{label}:same-source-and-registered-key')
    if definition == 'MemoryPack.Formatters.ListFormatter`1':
        raw_key = image.pe.bytes_at_va(key_pointer,16)
        if raw_key[10:12] != b'\x15\x00':raise ValueError(f'{label}:list-key-carrier')
        list_definition,list_instance = struct.unpack('<QQ',image.pe.bytes_at_va(int.from_bytes(raw_key[:8],'little'),16))
        arguments = image.instantiations.resolve_pointer(list_instance).arguments
        if runtime_type_name(image.pe,image.metadata,list_definition) != 'System.Collections.Generic.List`1' or len(arguments) != 1:
            raise ValueError(f'{label}:single-list-element')
        requested_element = arguments[0].type_pointer_va
    else:
        requested_element = key_pointer
    if requested_element != element:
        raise ValueError(f'{label}:same-element-type-pointer')
    window = flow['window'];image.check_windows([window],label=label)
    program = flow['program'];mode = flow['continuation']
    if mode not in ('call','tail') or len(program) != (11 if mode == 'call' else 13):
        raise ValueError(f'{label}:bounded-registration-program')
    image.check_instruction_windows(program,label=label)
    cursor = window['startRva']
    for at,hex_value in program:
        raw = bytes.fromhex(hex_value)
        if at != cursor or not raw:raise ValueError(f'{label}:complete-instruction-tiling')
        cursor += len(raw)
    if cursor != window['endRva']:raise ValueError(f'{label}:complete-window-end')
    for at,expected in {2:'488BD8',3:'4885C0',6:'488BC8',9:'488BCB'}.items():
        if program[at][1] != expected:raise ValueError(f'{label}:allocation-object-reference-flow={at}')
    branch_at,branch_hex = program[4];branch = bytes.fromhex(branch_hex)
    if len(branch) == 2 and branch[0] == 0x74:
        target = branch_at+2+int.from_bytes(branch[1:],'little',signed=True)
    elif len(branch) == 6 and branch[:2] == b'\x0f\x84':
        target = branch_at+6+int.from_bytes(branch[2:],'little',signed=True)
    else:raise ValueError(f'{label}:non-null-allocation-guard')
    if target != flow['nullAllocationTargetRva'] or window['startRva'] <= target < window['endRva']:
        raise ValueError(f'{label}:null-allocation-cold-edge')
    for index,usage in ((0,allocation),(5,constructor),(8,registration)):
        if program[index] != [usage['instructionRva'],usage['instructionHex']]:
            raise ValueError(f'{label}:actual-usage-position={index}')
    if mode == 'tail' and [program[10][1],program[11][1]] != ['4883C420','5B']:
        raise ValueError(f'{label}:owned-tail-frame-restore')
    for index,name,opcode in ((1,'allocation',0xe8),(7,'constructor',0xe8),
                              (10 if mode=='call' else 12,'registration',0xe8 if mode=='call' else 0xe9)):
        at,hex_value = program[index];raw = bytes.fromhex(hex_value)
        if len(raw) != 5 or raw[0] != opcode or at+5+struct.unpack_from('<i',raw,1)[0] != flow['actualCalls'][name]:
            raise ValueError(f'{label}:actual-physical-transfer={name}')
    return {'formatterDefinition':definition,'elementType':runtime_type_name(image.pe,image.metadata,element),
        'elementTypePointerVa':element,'sourceKeyType':key_name,'sourceKeyTypePointerVa':key_pointer,
        'completeSelectedInstructions':len(program),'continuation':mode,
        'objectReferenceRetainedFromAllocationThroughRegister':True,
        'condition':'Non-null typed allocation, normal constructor return and Win64 nonvolatile/stack preservation.',
        'constructorEffectsProved':False,'registrationEffectsProved':False,
        'liveProviderResultProved':False,'serializedElementGrammarProved':False}
