"""Internal ActionMap bridges to one freshly authenticated Story operation.

The operation already owns the complete Task/GameCondition source graph.
These readers reuse that exact graph and its pool, without accepting a proof
argument or deriving a second graph for each node. The enclosing ActionMap
route still owns its tag, declaration, actual child call and field framing.
"""
from scripts.game_data.codecs.levelscript.param_graph import Reader


def _need(check, condition):
    if not condition:
        raise ValueError('currentActionMapChild.' + check)


def condition_capability(current_owner, *, strings):
    """Return only the active exact operation's already admitted condition cap."""
    from scripts.game_data.memorypack.levelscript_current_source import require_framing_owner
    from scripts.game_data.memorypack.levelscript_task_game_condition_sources import CAP_SCHEMA
    from scripts.game_data.codecs.levelscript.current_game_condition import SCHEMA
    require_framing_owner(current_owner, strings=strings)
    proof = current_owner.proof
    task = current_owner.task_caps
    _need('same-fresh-operation-Task-proof', isinstance(proof, dict)
          and proof.get('status') == 'validated' and proof.get('tasks') is task
          and isinstance(task, dict) and task.get('schema') == CAP_SCHEMA
          and task.get('positiveGameConditionAdmitted') is True
          and task.get('storedTaskMapGrammarAdmitted') is True
          and task.get('runtimeConditionEvaluationAdmitted') is False
          and task.get('liveFormatterSelectionObserved') is False)
    graph = task.get('condition')
    _need('complete-current-GameCondition-graph', isinstance(graph, dict)
          and graph.get('schema') == SCHEMA and graph.get('typeName') == 'Beyond.Gameplay.GameCondition'
          and graph.get('storedGraphGrammarAdmitted') is True
          and graph.get('actualWrapperCallbackEqualsProvedConcreteRequired') is True
          and graph.get('actualRecursiveCallbackEqualsProvedBaseRequired') is True
          and graph.get('runtimeConditionEvaluationAdmitted') is False
          and graph.get('liveFormatterSelectionObserved') is False
          and isinstance(graph.get('records'), dict) and isinstance(graph.get('params'), dict))
    return graph


def decode_game_condition_string(data, offset, layout, *, field, current_owner, strings):
    """Read an exact concrete condition field through its compiled pool source."""
    from scripts.game_data.codecs.levelscript.current_game_condition import validate_record
    graph = condition_capability(current_owner, strings=strings)
    _need('explicit-selected-condition-layout', isinstance(layout, dict))
    selected = graph['records'].get(layout.get('wrapperName'))
    _need('owned-concrete-condition-wrapper', isinstance(selected, dict))
    validate_record(selected, graph['params'])
    fields = layout.get('fields')
    _need('same-complete-condition-field-order', isinstance(fields, (list, tuple))
          and len(fields) == selected['memberCount']
          and type(layout.get('memberCount')) is int and layout['memberCount'] == selected['memberCount']
          and all(isinstance(row, (list, tuple)) and len(row) == 2
                  and type(row[0]) is str and type(row[1]) is str for row in fields)
          and [row[0] for row in fields] == [row['fieldName'].lstrip('_') for row in selected['fields']])
    matches = [(declaration, read) for declaration, read in zip(selected['fields'], selected['program']['reads'], strict=True)
               if declaration['fieldName'].lstrip('_') == field]
    _need('one-own-pooled-condition-field', len(matches) == 1 and [field, 'string'] in [list(row) for row in fields])
    declaration, read = matches[0]
    _need('own-compiled-pooled-condition-source', declaration['declaredType'] == 'string'
          and read.get('kind') == 'byte-payload' and read.get('childCapability') == 'byte-payload')
    reader = Reader(data, offset, strings, field)
    return reader.string(field), reader.offset


def decode_script_task_ptr_param(data, offset, *, field, current_owner, strings):
    """Reuse ScriptTaskPtr's own MC1/default8 and nullable four-field Param."""
    from scripts.game_data.memorypack.levelscript_script_task_param_sources import SCHEMA, CAPABILITY
    from scripts.game_data.codecs.levelscript import current_condition_script_task_param as codec
    graph = condition_capability(current_owner, strings=strings)
    child = graph['params'].get(CAPABILITY)
    _need('own-ScriptTask-Param-component', isinstance(child, dict) and child.get('componentSchema') == SCHEMA)
    capability = child.get('capability')
    codec.validate(capability)
    reader = Reader(data, offset, strings, field)
    value = codec.read(reader, field, capability)
    if value is not None:
        # Preserve the existing ActionMap field vocabulary; the independent
        # default-value marker remains explicit inside the constant value.
        value = dict(value=value['constValue'], idRef=value['idRef'],
                     paramSource=value['paramSource'], path=value['path'])
    return value, reader.offset
