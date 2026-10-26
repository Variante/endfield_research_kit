"""Finite complete ActionMap callers of the current GameCondition reader.

A declaration selector names one wrapper, never supplies a proof or layout.
This authenticates actual parent source/context/frame only. The independently
owned condition graph and the enclosing ActionMap union remain separate.
"""
import json

SCHEMA = 'endfield.actionmap-condition-parent-bindings.v1'
BASE = 'Beyond.Gameplay.GameCondition'
WRAPPERS = frozenset('Beyond.MemoryPack.Beyond_Gameplay_Actions_'+name+'ForMemoryPack'
                     for name in ('WaitForCondition', 'GetConditionResult'))


def need(check, condition):
    if not condition:
        raise ValueError('actionConditionParents.'+check)


def require_source(source, pins, wrapper_name, type_name, fields):
    need('complete-own-generated-source', isinstance(source, dict)
         and source.get('schema') == 'endfield.generated-concrete-reader-source.v1'
         and source.get('nativeInputs') == pins and source.get('wrapperName') == wrapper_name
         and source.get('wrappedType') == type_name and source.get('completeSelectedCallerAdmitted') is True
         and source.get('childGrammarAdmitted') is False and source.get('wholeOwnerAdmitted') is False)
    reads = source.get('orderedSourceReads')
    need('same-complete-metadata-and-source-field-order', isinstance(reads, list) and len(reads) == len(fields)
         and all(type(r.get('memberIndex')) is int and r['memberIndex'] == index
                 and (r.get('fieldName'), r.get('declaredType')) == tuple(field)
                 for index, (r, field) in enumerate(zip(reads, fields, strict=True))))
    programs = source.get('programs')
    need('all-four-complete-parent-frames', isinstance(programs, list) and len(programs) == 4
         and all(type(p.get('existing')) is bool and type(p.get('wrapperNull')) is bool
                 and p.get('frame', {}).get('entryRspRestored') is True
                 and p.get('frame', {}).get('allWin64IntegerNonvolatilesRestored') is True for p in programs)
         and {(p['existing'], p['wrapperNull']) for p in programs} == {(False, False), (True, False), (False, True), (True, True)})


def binding(source, read, usage):
    context = read.get('context', {})
    raw_type = bytes.fromhex(context.get('argumentRawHex', ''))
    spec = usage.get('methodSpec')
    need('actual-closed-ordinary-ReadValue-request', read.get('declaredType') == BASE
         and (usage.get('tag'), usage.get('typeName'), usage.get('methodName'), usage.get('classArguments'), usage.get('methodArguments'))
         == (6, 'MemoryPack.MemoryPackReader', 'ReadValue', [], [BASE])
         and isinstance(spec, list) and len(spec) == 3 and all(type(n) is int for n in spec)
         and spec[0] >= 0 and spec[1] == -1 and spec[2] >= 0
         and len(raw_type) == 16 and raw_type[10:12] == bytes((18, 0))
         and (context.get('methodOwner'), context.get('methodName'), context.get('fullTypeName'), context.get('register'))
         == ('MemoryPack.MemoryPackReader', 'ReadValue', BASE, 'rdx')
         and (context.get('instructionRva'), context.get('instructionHex'), context.get('methodSpec'))
         == (usage.get('instructionRva'), usage.get('instructionHex'), spec))
    raw_usage = bytes.fromhex(usage.get('instructionHex', ''))
    instruction = read.get('instruction'); target = read.get('sourceTargetRva')
    need('owned-context-load-and-E8', len(raw_usage) == 7 and raw_usage[:3] == bytes.fromhex('488b15')
         and isinstance(instruction, list) and len(instruction) == 2 and type(instruction[0]) is int
         and type(usage.get('instructionRva')) is int and instruction[0] >= usage['instructionRva']+7
         and type(target) is int and target > 0)
    raw = bytes.fromhex(instruction[1])
    need('exact-E8-target', len(raw) == 5 and raw[0] == 232
         and instruction[0]+5+int.from_bytes(raw[1:], 'little', signed=True) == target)
    fields = source['orderedSourceReads']
    return dict(wrapperName=source['wrapperName'], fieldName=read['fieldName'], memberIndex=read['memberIndex'],
                typeName=BASE, parentMemberCount=len(fields), parentFieldOrder=[r['fieldName'].lstrip('_') for r in fields],
                typedRequest=usage, sourceContext=context, sourceInstruction=instruction,
                sourceTargetRva=target, readerMethodDefinition=spec[0], parentSourceAndFrameProved=True,
                conditionGrammarAdmitted=False, unionSelectionAdmitted=False, runtimeConditionEvaluationAdmitted=False)


def derive(image, pins, *, wrapper_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_reader_sources
    need('finite-wrapper-selector', type(wrapper_name) is str and wrapper_name in WRAPPERS)
    _publication_gate(image, pins)
    wrappers = [w for w in image.memorypack_wrappers.values() if w.name == wrapper_name]
    need('one-actual-current-wrapper', len(wrappers) == 1)
    wrapper = wrappers[0]; fields = [(m.name, m.declared_type) for m in wrapper.members]
    need('declared-direct-condition-field', any(t == BASE for n, t in fields))
    outcomes = generated_reader_sources.derive_many(image, pins, [wrapper_name])
    need('one-same-image-source-outcome', outcomes.get('nativeInputs') == pins and len(outcomes.get('owners', [])) == 1)
    owner = outcomes['owners'][0]
    if owner.get('status') != 'complete-reader-source-proved':
        raise ValueError('actionConditionParents.complete-selected-reader:wrapper='+wrapper_name+':'+
                         str(owner.get('reason', owner.get('diagnostic', owner.get('status'))))[:2200])
    source = owner['proof']
    require_source(source, pins, wrapper_name, wrapper.wrapped_type, fields)
    bindings = {}
    for read in source['orderedSourceReads']:
        if read['declaredType'] != BASE:
            continue
        usage = derive_typed_usage_context(image, read['context']['instructionRva'], label='actionConditionParents.actual')
        image.check_instruction_windows([read['instruction']], label='actionConditionParents.actualE8')
        result = binding(source, read, usage)
        key = wrapper_name+'::'+read['fieldName'].lstrip('_')
        need('unique-normalized-parent-field', key not in bindings)
        bindings[key] = result
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, status='validated', nativeInputs=pins, bindings=bindings,
        parentSources={wrapper_name: source}, conditionGrammarAdmitted=False, unionSelectionAdmitted=False,
        wholeOwnerAdmitted=False, runtimeConditionEvaluationAdmitted=False)))
