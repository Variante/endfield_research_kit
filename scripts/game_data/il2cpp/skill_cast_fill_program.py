"""Check a reviewed complete cast-info return program against original bytes.

The native owner supplies named calls, field offsets, value layout and decoder.
The reviewed grammar states the hidden-output ABI and each transfer explicitly;
normal return is conditional and never selects the anonymous caller's class.
"""
from .consumer_control import check_consumer_control
from .owned_partition import BranchGrammar

LABEL = 'skillCastFillProgram'
SEMANTICS = 'win64-hidden-output-rcx-this-rdx-three-member-cast-info-unpatched.v1'


def check_skill_cast_fill_program(rows, *, entry, owned_ranges, mapper, specification,
                                 source_fields, calls, inline_offsets, copied_value_bytes):
    if (specification['semantics'] != SEMANTICS or set(source_fields) != {'skillCastId', 'originSkill', 'cost'}
            or inline_offsets != {'skillCastId': 0, 'originSkill': 8, 'cost': 16}
            or copied_value_bytes != 24):
        raise ValueError(LABEL + '.typed-member-shape')
    if set(calls) != {'isPatched', 'getPatch', 'patchWrapper', 'trapHelper'}:
        raise ValueError(LABEL + '.call-membership')
    # Never accept text that disagrees with the independently decoded bytes.
    for row in rows:
        raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
        decoded, end = mapper.decode_one_x64(raw, 0, at)
        if end != len(raw) or decoded['text'] != row['text'] or decoded['text'].startswith('db'):
            raise ValueError(LABEL + '.original-byte-decoding:' + row['va'])
    control = check_consumer_control(rows, entry=entry, owned_ranges=owned_ranges)
    grammar = BranchGrammar(rows, label=LABEL)
    def expand(text):
        for role, offset in source_fields.items():
            text = text.replace('{' + role + '}', hex(offset))
        return text
    for step in specification['program']:
        if len(step) != 1:
            raise ValueError(LABEL + '.instruction-declaration')
        operation, value = next(iter(step.items()))
        if operation == 'take':
            grammar.take(expand(value))
        elif operation == 'pattern':
            grammar.pattern(value)
        elif operation == 'mark':
            grammar.mark(value)
        elif operation == 'branch':
            grammar.branch(*value)
        elif operation == 'call':
            grammar.call(calls[value])
        else:
            raise ValueError(LABEL + '.unknown-program-operation:' + operation)
    grammar.finish()
    return {'status': 'complete-reviewed-unpatched-member-return-program-proved',
        'instructionsChecked': control['instructionsChecked'], 'ownedRangesChecked': control['ownedRangesChecked'],
        'sourceReference': 'incoming RDX retained in RDI; valid Ability under hidden-return Win64 ABI',
        'outputReference': 'incoming RCX retained in RBX, returned in RAX',
        'selectedPath': 'first named IsPatched call returns AL zero and the compiled normal path returns',
        'members': [
            {'sourceRole': 'skillCastId', 'sourceOffset': source_fields['skillCastId'], 'bytes': 4, 'inlineOffset': 0},
            {'sourceRole': 'originSkill', 'sourceOffset': source_fields['originSkill'], 'bytes': 8, 'inlineOffset': 8},
            {'sourceRole': 'cost', 'sourceOffset': source_fields['cost'], 'bytes': 4, 'inlineOffset': 16}],
        'copiedValueBytes': copied_value_bytes, 'paddingBytesZeroed': [[4, 8], [20, 24]],
        'bitPreservingTransfers': True, 'numericConversionPerformed': False,
        'unpatchedReturnMemberFlowProved': True, 'patchedReturnMemberFlowProved': False,
        'callerEnvironmentSelected': False, 'runtimeExecutionKnown': False,
        'evidenceBoundary': 'conditional',
        'conditions': ['ordinary returning Win64 callees and selected two-pointer boxed layout',
                       'valid readable Ability and writable output/frame storage',
                       'source, output, frame and barrier storage are disjoint',
                       'the compiled normal path reaches its return; barrier-loop termination is not proved'],
        'unresolved': ['anonymous caller discriminator and class selection', 'patched values',
                       'barrier global state/effects and loop termination', 'actual invocation and runtime values']}
