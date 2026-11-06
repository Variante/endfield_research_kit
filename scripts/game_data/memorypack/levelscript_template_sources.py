"""Fresh template and ActionMap callers joined to independently proved children.

The selected initialized source programs prove nominal calls, field stores and
returns. Child callbacks, stable disjoint buffered storage and disabled collector
remain explicit conditions; runtime provider selection is never inferred.
"""
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack import generated_reader_sources, levelscript_owner_sources
from scripts.game_data.memorypack.pointer_param import owned

TEMPLATE = 'Beyond.Gameplay.LevelScriptTemplateData'
ASSET = 'Beyond.Gameplay.Actions.ActionMapAssetRaw'
MAP = 'Beyond.Gameplay.Actions.ActionSerializedMap'
FIELDS = ('actionMap', 'maxStage', 'properties', 'propertyIdToKeyMap', 'taskMap', 'templateId')
LISTS = (('actionList', 'Beyond.Gameplay.Actions.ActionBase'),
         ('getterList', 'Beyond.Gameplay.Actions.PureGetter'),
         ('headerList', 'Beyond.Gameplay.Actions.ActionHeader'))


def need(gate, condition, actual=None):
    if not condition:
        raise ValueError('currentLevelScriptTemplate.' + gate + ':' + str(actual)[:1600])


def call(read):
    site, text = read['instruction']; raw = bytes.fromhex(text)
    need('actual-owned-E8', len(raw) == 5 and raw[0] == 232
         and site + 5 + int.from_bytes(raw[1:], 'little', signed=True) == read['sourceTargetRva'])


def nominal(read, name, method):
    call(read); context = read.get('context', {})
    need('exact-closed-child-request', read.get('declaredType') == name
         and (context.get('methodOwner'), context.get('methodName'), context.get('fullTypeName'), context.get('register'))
         == ('MemoryPack.MemoryPackReader', method, name, 'rdx')
         and isinstance(context.get('methodSpec'), list) and len(context['methodSpec']) == 3, read)
    return context


def compose_callers(proofs, owners, pins, *, image_base, task_cap):
    """Check parent relationships only; derive supplies every fresh native fact."""
    need('same-three-complete-source-owners', set(proofs) == {TEMPLATE, ASSET, MAP})
    for name, proof in proofs.items():
        need('complete-current-caller', proof.get('wrappedType') == name and proof.get('nativeInputs') == pins
             and proof.get('completeSelectedCallerAdmitted') is True and proof.get('childGrammarAdmitted') is False
             and proof.get('wholeOwnerAdmitted') is False and len(proof.get('programs', [])) == 4, name)
    template = proofs[TEMPLATE]['orderedSourceReads']
    need('six-ordered-root-fields', [r['fieldName'] for r in template] == list(FIELDS))
    root = owners['owners'][levelscript_owner_sources.ROOT]
    need('independent-same-current-root', owners.get('nativeInputs') == pins and owners.get('wholeOwnerAdmitted') is False)
    joins = {}
    for read in template:
        field = read['fieldName']
        if field in ('maxStage', 'templateId'):
            need('root-scalar-source', (read['declaredType'], read.get('wireBytes')) ==
                 (('int', 4) if field == 'maxStage' else ('string', 4)), read)
            continue
        context = nominal(read, read['declaredType'], 'ReadValue' if field == 'actionMap' else 'ReadPackable')
        original = next(r for r in root['program']['orderedReads'] if r['fieldName'] == field)
        declared = next(f for f in root['fields'] if f['name'] == field)
        usage = next(u for u in root['typedUsages'] if u['instructionRva'] == original['typedUsage']['instruction'] - image_base)
        need('same-closed-root-specialization', declared['typeName'] == read['declaredType']
             and usage['methodArguments'] == [read['declaredType']] and usage['classArguments'] == []
             and usage['methodSpec'] == context['methodSpec'] and usage['methodName'] == context['methodName']
             and original['sourceTarget'] - image_base == read['sourceTargetRva'], field)
        if field == 'taskMap':
            binding = task_cap['rootBinding']
            need('same-independent-Task-dictionary', binding['typeName'] == read['declaredType']
                 and binding['typedRequest']['methodSpec'] == context['methodSpec']
                 and binding['sourceTargetRva'] == read['sourceTargetRva'], field)
        joins[field] = dict(typeName=read['declaredType'], methodSpec=context['methodSpec'],
                            sourceTargetRva=read['sourceTargetRva'], sourceInstruction=read['instruction'])
    asset = proofs[ASSET]['orderedSourceReads']; serialized = proofs[MAP]['orderedSourceReads']
    need('exact-asset-plan', [(r['fieldName'], r['declaredType']) for r in asset] ==
         [('dataMap', MAP), ('paramBlackboard', 'Beyond.Gameplay.ParamListForGraph')])
    need('exact-three-nominal-lists', [(r['fieldName'], r['declaredType']) for r in serialized] ==
         [(field, 'System.Collections.Generic.List`1<' + element + '>') for field, element in LISTS])
    for read in asset:
        context = nominal(read, read['declaredType'], 'ReadValue')
        # Same freshly proved reference ReadValue program, separate closed type;
        # no erased-reference or field-name equivalence grants a child grammar.
        parent = joins['actionMap']
        need('same-reference-source-ABI', context['methodSpec'][0] == parent['methodSpec'][0]
             and read['sourceTargetRva'] == parent['sourceTargetRva'])
    for read in serialized: nominal(read, read['declaredType'], 'ReadPackable')
    return joins


def derive(image, pins, *, task_cap):
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    from scripts.game_data.memorypack.scalar_param_native import reader_offsets
    from scripts.game_data.levelscript_param_list_native import validate_param_list_for_graph_native_contract
    wrappers = image.memorypack_wrappers
    names = []
    for name in (TEMPLATE, ASSET, MAP):
        selected = [w.name for w in wrappers.values() if w.wrapped_type == name]
        need('unique-current-wrapper', len(selected) == 1, name); names.extend(selected)
    result = generated_reader_sources.derive_many(image, pins, names)
    need('complete-current-callers', all(r['status'] == 'complete-reader-source-proved' for r in result['owners']),
         [dict(status=r['status'], reason=r.get('reason')) for r in result['owners']])
    proofs = {r['proof']['wrappedType']: r['proof'] for r in result['owners']}
    owners = levelscript_owner_sources.derive(image, pins)
    joins = compose_callers(proofs, owners, pins, image_base=image.pe.image_base, task_cap=task_cap)
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    offsets = reader_offsets(image, 'currentLevelScriptTemplate')
    offsets['totalLength'] = NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2] - 16
    lists = {}
    for read, (field, element) in zip(proofs[MAP]['orderedSourceReads'], LISTS, strict=True):
        usage = derive_typed_usage_context(image, read['context']['instructionRva'], label='currentLevelScriptTemplate.list')
        need('same-actual-list-MethodInfo', usage['methodSpec'] == read['context']['methodSpec']
             and usage['methodArguments'] == [read['declaredType']])
        component = derive_reference_list_component(image, pins, typed_request=usage,
            call_target=image.pe.image_base + read['sourceTargetRva'], element_type=element, count_limit=2)
        body = owned(image, component['entry']['pointer'])
        induction = reference_list_induction(body['regions'], body['pointer'], offsets,
            {key: image.pe.image_base + value for key, value in component['symbols'].items()})
        need('all-positive-list-loop', induction.get('countProfile') == 'all-positive-Int32'
             and induction.get('headerBytes') == 4 and induction.get('elementRuntimeBytes') == 8)
        lists[field] = dict(elementType=element, typeName=read['declaredType'], countLimit=4096,
            headerBytes=4, counts='-1-or-nonnegative', actualCallbackEqualsProvedChildRequired=True,
            typedRequest=usage, sourceInstruction=read['instruction'], sourceTargetRva=read['sourceTargetRva'])
    blackboard = validate_param_list_for_graph_native_contract(gameassembly=image.gameassembly,
                                                            metadata=image.metadata_path)
    need('independent-current-blackboard', blackboard.get('status') == 'validated'
         and blackboard.get('nativeInputs') == pins, blackboard)
    return dict(schema='endfield.current-levelscript-template-source.v1', nativeInputs=pins,
        fieldOrder=list(FIELDS), memberCount=6, parentJoins=joins, actionMapLists=lists,
        storedGrammarAdmitted=True, actualCallbackEqualsProvedChildRequired=True,
        runtimeProviderSelectionObserved=False, wholeOwnerAdmitted=False,
        evidenceBoundary=__doc__)
