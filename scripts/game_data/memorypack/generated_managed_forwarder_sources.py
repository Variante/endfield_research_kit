"""Own closed Query16 forwarder, separate from its padded wire grammar.

The caller supplies no MethodInfo. The actual helper supplies its own exact
ReadValue<Query> request and preserves both incoming pointers across that call.
Only the width-independent forwarder byte lemma is shared with vector sources;
the nominal managed value and provider/adapter proof come from the Query owner.
"""
from scripts.game_data.memorypack.generated_vector3_source import forwarder_program

TYPE = 'Beyond.Gameplay.Core.GameplayTagQuery'
LABEL = 'generatedManagedForwarder'


def need(key, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + key + ':' + str(detail)[:700])


def context_shape(context, type_name):
    raw = bytes.fromhex(context.get('argumentRawHex', '')) if isinstance(context, dict) else b''
    need('exact-finite-Query-ReadValue-context', type_name == TYPE and isinstance(context, dict)
         and context.get('methodOwner') == 'MemoryPack.MemoryPackReader'
         and context.get('methodName') == 'ReadValue' and context.get('fullTypeName') == TYPE
         and context.get('typeKind') == 17 and context.get('register') == 'r8'
         and len(raw) == 16 and raw[10:12] == bytes((17, 128)))


def derive(image, pins, *, source_target, type_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_action_sources as actions, pointer_param
    from scripts.game_data.memorypack.skill_nominal_value_read_sources import derive as nominal_read

    _publication_gate(image, pins)
    need('literal-actual-source-and-type', type_name == TYPE and type(source_target) is int
         and source_target > image.pe.image_base)
    base = image.pe.image_base
    body = pointer_param.owned(image, source_target)
    program = forwarder_program(body['regions'], source_target)
    contexts, skipped = actions._contexts(image, body['rows'])
    need('one-internal-owned-context', len(contexts) == 1)
    context, = contexts
    context_shape(context, type_name)
    need('same-actual-context-instruction', context['instructionRva'] == program['contextInstructionVa'] - base)
    usage = derive_typed_usage_context(image, context['instructionRva'], label=LABEL + '.actualMethodInfo')
    need('same-current-context-bytes-and-spec', usage['instructionHex'] == context['instructionHex']
         and usage['methodSpec'] == context['methodSpec'])
    nested = nominal_read(image, pins, typed_request=usage, source_target=program['nestedTargetVa'])
    need('complete-independent-Query-nested-source', nested['nativeInputs'] == pins and nested['typeName'] == TYPE
         and nested['managedBytes'] == 16 and nested['resultAbi'] == 'hidden-local'
         and nested['actualSourceProved'] is True and nested['wireGrammarAdmitted'] is False
         and nested['sourceTargetRva'] == program['nestedTargetVa'] - base
         and nested['readerMethodDefinition'] == context['methodSpec'][0])
    _publication_gate(image, pins)
    result = dict(nested)
    result.update(schema='endfield.generated-managed-closed-forwarder-source.v1',
        status='proved-conditional-owned-Query-ReadValue-forwarder', sourceTargetRva=source_target - base,
        sourceContextMode='owned-closed-forwarder', contextMode='owned-closed-forwarder',
        actualSourceProved=True, pointerAliasClaimed=False, managedEntryIdentityClaimed=False,
        parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        proof=dict(nested['proof'], internalContext=context, forwarderProgram=program,
                   actualFamily=image.unwind_index.family(source_target - base), actualWindows=body['windows'],
                   actualSourceRegions=[[at,raw.hex().upper()]for at,raw in body['regions']],
                   nestedSource=nested, skippedRuntimeCells=skipped),
        evidenceBoundary='Exact owned forwarder supplies its own Query ReadValue MethodInfo and forwards unchanged incoming Reader/output; the independently fresh padded Query source/provider/adapter owns the nested program. No Vector3 layout, raw16 wire, pointer alias, enclosing field/frame or runtime provider selection is inferred.')
    return result
