"""Direct ActionMap condition fields joined to one active Story operation.

The native parent audit is freshly derived on that operation's selected image.
Its exact actual ordinary ReadValue request and source/frame program join the
independently admitted Task condition reader. No direct binding admits a List,
no nominal match selects a route, and no constructor accepts proof arguments.
"""
import struct

from scripts.game_data.codecs.levelscript.current_actionmap_children import condition_capability, _need
from scripts.game_data.codecs.levelscript.param_graph import Reader

BINDING_SCHEMA = 'endfield.actionmap-condition-parent-bindings.v1'
BASE = 'Beyond.Gameplay.GameCondition'


def _audit_identity(current_owner, audit, bindings):
    _need('own-operation-condition-parent-source', isinstance(audit, dict)
          and audit.get('schema') == BINDING_SCHEMA and audit.get('status') == 'validated'
          and audit.get('nativeInputs') == current_owner.proof.get('nativeInputs')
          and audit.get('nativeSources') == current_owner.proof.get('nativeSources')
          and isinstance(audit.get('nativeInputs'), dict) and isinstance(audit.get('nativeSources'), dict)
          and set(audit['nativeInputs']) == {'GameAssembly.dll', 'global-metadata.dat', 'UnityPlayer.dll'}
          and all(type(v) is str and len(v) == 64 for v in audit['nativeInputs'].values())
          and set(audit['nativeSources']) == {'GameAssembly.dll', 'global-metadata.dat'}
          and all(type(v) is str and v for v in audit['nativeSources'].values())
          and isinstance(bindings, dict) and bindings is audit.get('bindings'))


def _source_audit(current_owner, wrapper, member):
    key = wrapper+'::'+member
    from scripts.game_data import levelscript_action_condition_parents_native as native
    from scripts.game_data.memorypack.operation_native_validation import validate_native
    root = getattr(current_owner, 'game_root', None)
    _need('explicit-operation-selected-root', root is not None)
    fresh = validate_native(native.validate, wrapper_name=wrapper, game_root=root)
    if not isinstance(fresh, dict) or fresh.get('status') != 'validated':
        import json
        detail = {k: fresh.get(k) for k in ('status', 'detail', 'diagnostic')} if isinstance(fresh, dict) else type(fresh).__name__
        raise ValueError('currentActionMapChild.fresh-condition-parent-source:'+json.dumps(detail, sort_keys=True)[:2200])
    _audit_identity(current_owner, fresh, fresh.get('bindings'))
    _need('fresh-immediate-condition-parent', key in fresh['bindings']
          and all(row.get('wrapperName') == wrapper for row in fresh['bindings'].values()))
    # Successful reuse belongs to validate_native's lexical source epoch.
    # Operation attributes cannot inject retained facts or outlive an entry.
    return fresh


def _condition_parent(current_owner, strings, parent_layout, member):
    _need('operation-pool-present', strings is not None)
    graph = condition_capability(current_owner, strings=strings)
    _need('explicit-immediate-condition-parent', isinstance(parent_layout, dict)
          and type(parent_layout.get('wrapperName')) is str and type(member) is str)
    fields = parent_layout.get('fields')
    _need('literal-parent-field-order', isinstance(fields, (list, tuple)) and fields
          and all(isinstance(f, (list, tuple)) and len(f) == 2 and all(type(v) is str for v in f) for f in fields))
    indexes = [index for index, f in enumerate(fields) if f[0] == member]
    _need('one-actual-direct-condition-field', len(indexes) == 1 and fields[indexes[0]][1] == 'GameCondition')
    wrapper = parent_layout['wrapperName']; key = wrapper+'::'+member
    audit = _source_audit(current_owner, wrapper, member); bindings = audit['bindings']
    binding = bindings.get(key)
    _need('same-owned-immediate-parent-field', isinstance(binding, dict)
          and binding.get('wrapperName') == wrapper and binding.get('fieldName', '').lstrip('_') == member
          and type(binding.get('memberIndex')) is int and binding['memberIndex'] == indexes[0]
          and binding.get('typeName') == BASE and binding.get('parentSourceAndFrameProved') is True
          and type(binding.get('parentMemberCount')) is int and binding['parentMemberCount'] == len(fields)
          and binding.get('parentFieldOrder') == [f[0] for f in fields])
    usage = binding.get('typedRequest'); context = binding.get('sourceContext')
    _need('complete-actual-condition-Reader-request', isinstance(usage, dict) and isinstance(context, dict)
          and (usage.get('tag'), usage.get('typeName'), usage.get('methodName'), usage.get('classArguments'), usage.get('methodArguments'))
          == (6, 'MemoryPack.MemoryPackReader', 'ReadValue', [], [BASE])
          and isinstance(usage.get('methodSpec'), list) and len(usage['methodSpec']) == 3
          and all(type(n) is int for n in usage['methodSpec'])
          and usage['methodSpec'][0] >= 0 and usage['methodSpec'][1] == -1 and usage['methodSpec'][2] >= 0
          and type(usage.get('instructionRva')) is int and usage['instructionRva'] >= 0
          and type(usage.get('instructionHex')) is str)
    raw_usage = bytes.fromhex(usage['instructionHex'])
    raw_type = bytes.fromhex(context.get('argumentRawHex', ''))
    _need('actual-RDX-ordinary-CLASS18-condition', len(raw_usage) == 7 and raw_usage[:3] == bytes.fromhex('488b15')
          and len(raw_type) == 16 and raw_type[10:12] == bytes((18, 0))
          and (context.get('methodOwner'), context.get('methodName'), context.get('fullTypeName'), context.get('register'))
          == ('MemoryPack.MemoryPackReader', 'ReadValue', BASE, 'rdx')
          and (context.get('instructionRva'), context.get('instructionHex'), context.get('methodSpec'))
          == (usage['instructionRva'], usage['instructionHex'], usage['methodSpec']))
    target = binding.get('sourceTargetRva'); instruction = binding.get('sourceInstruction')
    _need('actual-condition-E8-shape', type(target) is int and target > 0
          and isinstance(instruction, list) and len(instruction) == 2
          and type(instruction[0]) is int and instruction[0] >= usage['instructionRva']+7
          and type(instruction[1]) is str)
    raw = bytes.fromhex(instruction[1])
    task_binding = current_owner.task_caps.get('conditionBinding')
    _need('same-independent-Task-condition-reader', len(raw) == 5 and raw[0] == 232
          and instruction[0]+5+int.from_bytes(raw[1:], 'little', signed=True) == target
          and isinstance(task_binding, dict) and task_binding.get('typeName') == BASE
          and (binding.get('readerMethodDefinition'), target) ==
              (task_binding.get('readerMethodDefinition'), task_binding.get('sourceTargetRva'))
          and usage['methodSpec'][0] == binding['readerMethodDefinition'])
    return graph


def _param(value):
    if value is None:
        return None
    constant = value['constValue']
    if isinstance(constant, dict) and set(constant) == {'value', 'rawByte'}:
        constant = constant['value']
    elif isinstance(constant, dict) and set(constant) == {'rawHex', 'values', 'finite'}:
        constant = constant['values'][0] if len(constant['values']) == 1 else list(constant['values'])
    return dict(value=constant, idRef=value['idRef'], paramSource=value['paramSource'], path=value['path'])


def _legacy_condition(value, graph):
    if value is None:
        return None
    top = value; current = value; wrapper = graph['rootWrapper']; chain = []
    while wrapper in graph['unions']:
        route = graph['unions'][wrapper]['routes'][str(current['tag'])]
        chain.append(dict(wrapperName=wrapper, unionTag=current['tag'], typeName=route['typeName']))
        wrapper = route['wrapperName']; current = current['value']
        if current is None:
            return dict(sourceOffset=top['startOffset'], endOffset=top['endOffset'], unionTag=top['tag'],
                        memberCount=255 if wrapper in graph['records'] else None,
                        wrapperName=wrapper, fields=None, currentConditionValue=top, conditionUnionPath=chain)
    record = graph['records'][wrapper]; fields = {}; spans = {}; types = {}
    for declaration, read in zip(record['fields'], record['program']['reads'], strict=True):
        source_name = declaration['fieldName']; name = source_name.lstrip('_'); kind = read['kind']
        _need('unambiguous-normalized-condition-fields', name not in fields)
        item = current[source_name]
        if kind == 'scalar32':
            bits = item['unsignedBits']
            item = bits if declaration['declaredType'] == 'uint' else struct.unpack('<i', struct.pack('<I', bits))[0]
        elif kind == 'bool-byte': item = item['value']
        elif kind == 'condition-param': item = _param(item)
        elif kind == 'game-condition-list' and item is not None:
            item = [_legacy_condition(v, graph) for v in item]
        fields[name] = item; spans[name] = current['fieldRanges'][source_name]; types[name] = declaration['declaredType']
    return dict(sourceOffset=top['startOffset'], endOffset=top['endOffset'], unionTag=top['tag'],
                memberCount=record['memberCount'], wrapperName=wrapper, fields=fields,
                fieldRanges=spans, fieldTypes=types, currentConditionValue=top, conditionUnionPath=chain)


def decode_condition(data, offset, *, field, parent_layout, member, current_owner, strings):
    from scripts.game_data.codecs.levelscript.current_game_condition import read
    graph = _condition_parent(current_owner, strings, parent_layout, member)
    reader = Reader(data, offset, strings, field)
    value = read(reader, field, graph)
    return _legacy_condition(value, graph), reader.offset
