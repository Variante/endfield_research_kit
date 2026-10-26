"""Fresh finite ordinary Param children for generated ActionMap routes.

The registry selects existing independent source algorithms, never a wire
shape from a name/width. Unknown references and failed enum classifications
remain individual gaps. No saved report or injected component enters derive.
"""
import copy
import json

from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX, CAP_PREFIX

SCHEMA = 'endfield.actionmap-ordinary-param-registry.v1'
LABEL = 'actionmapParamRegistry'


def need(check, value):
    if not value:
        raise ValueError(LABEL + '.' + check)


def parameter_value(name):
    need('literal-ordinary-Param-name', type(name) is str and name.startswith(PREFIX)
         and name.endswith('>') and len(name) > len(PREFIX) + 1)
    return name[len(PREFIX):-1]


def codec_for_schema(schema):
    from scripts.game_data.memorypack.levelscript_action_output_components import SCHEMA as OUTPUT
    if schema == OUTPUT:
        from scripts.game_data.codecs.levelscript import current_action_output_param
        return current_action_output_param
    from scripts.game_data.memorypack.levelscript_action_dedicated_param_components import SCHEMA as DEDICATED
    if schema == DEDICATED:
        from scripts.game_data.codecs.levelscript import current_action_dedicated_param
        return current_action_dedicated_param
    from scripts.game_data.codecs.levelscript.current_game_condition import _param_codec
    return _param_codec(schema)


def validate(registry, pins):
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
    need('owned-registry', type(registry) is dict and registry.get('schema') == SCHEMA
         and registry.get('nativeInputs') == pins and registry.get('parentFieldAdmitted') is False
         and registry.get('wholeOwnerAdmitted') is False)
    selected = {}
    for component in registry['components']:
        need('same-child-build', component.get('nativeInputs') == pins)
        for key, cap in component.get('capabilities', {}).items():
            _validate_capability(component, key)
            name = cap['typeName']
            need('exact-unique-ordinary-Param', parameter_value(name) == cap['valueType']
                 and key == CAP_PREFIX + name and name not in selected)
            owners = [row for row in component['owners'] if row.get('typeName') == name]
            need('one-complete-canonical-child', len(owners) == 1
                 and owners[0].get('status') == 'validated-conditional-Param-child'
                 and owners[0].get('capability') == cap
                 and owners[0].get('proof', {}).get('closedCarrier', {}).get('type') == name)
            selected[name] = (component, key)
    expected = {name: dict(componentSchema=component['schema'], capability=key)
                for name, (component, key) in selected.items()}
    need('same-registry-projection', registry['byType'] == expected)
    owners = registry['owners']
    need('distinct-registry-outcomes', type(owners) is list
         and len({row['typeName'] for row in owners}) == len(owners))
    need('only-validated-outcomes-have-capabilities',
         {row['typeName'] for row in owners if row.get('status') == 'validated'} == set(selected))
    return selected


def derive(image, pins, *, parameter_types):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import levelscript_condition_param_sources as primitive
    from scripts.game_data.memorypack import levelscript_condition_storage_param_components as storage
    from scripts.game_data.memorypack import levelscript_condition_list_param_components as listing
    from scripts.game_data.memorypack import levelscript_condition_enum_param_components as enum
    from scripts.game_data.memorypack import levelscript_int2_param_sources as int2
    from scripts.game_data.memorypack import levelscript_script_task_param_sources as task
    from scripts.game_data.memorypack import levelscript_action_dedicated_param_components as dedicated
    from scripts.game_data.memorypack.levelscript_condition_list_param_sources import LIST, ELEMENTS
    need('finite-distinct-request', type(parameter_types) is list and 0 < len(parameter_types) <= 256
         and all(type(n) is str for n in parameter_types)
         and len(set(parameter_types)) == len(parameter_types))
    _publication_gate(image, pins)
    ctx = NativeReferenceContext(image)
    groups = {key: [] for key in ('primitive', 'storage', 'list', 'enum', 'int2', 'task', 'dedicated')}
    pending = {}
    current = {}
    for wrapper in image.memorypack_wrappers.values():
        current.setdefault(wrapper.wrapped_type, []).append(wrapper)
    for name in parameter_types:
        value = parameter_value(name)
        try:
            need('one-actual-Param-wrapper', len(current.get(name, [])) == 1)
            if value in primitive.PRIMITIVES:
                key = 'primitive'
            elif value in storage.TYPES:
                key = 'storage'
            elif value in {LIST + element + '>' for element in ELEMENTS}:
                key = 'list'
            elif name == int2.TYPE:
                key = 'int2'
            elif name == task.TYPE:
                key = 'task'
            elif value in dedicated.SPECS:
                key = 'dedicated'
            elif value in ctx.index.types and ctx.is_enum(value):
                key = 'enum'
            else:
                raise ValueError(LABEL + '.independent-own-constant-source-and-canonical-bridge-required:' + value)
            groups[key].append(name)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            pending[name] = str(error)[:1800]
    components = []
    calls = {
        'primitive': lambda names: primitive.derive_many(image, pins, [parameter_value(n) for n in names]),
        'storage': lambda names: storage.derive_many(image, pins, [parameter_value(n) for n in names]),
        'list': lambda names: listing.derive_many(image, pins, element_types=[parameter_value(n)[len(LIST):-1] for n in names]),
        'enum': lambda names: enum.derive_many(image, pins, names),
        'int2': lambda names: int2.derive(image, pins),
        'task': lambda names: task.derive(image, pins),
        'dedicated': lambda names: dedicated.derive_many(image, pins, parameter_types=names),
    }
    for kind, names in groups.items():
        if not names:
            continue
        try:
            component = calls[kind](names)
            need('same-fresh-child-native-inputs', component.get('nativeInputs') == pins)
            admitted = {cap['typeName'] for cap in component.get('capabilities', {}).values()}
            need('no-unrequested-child-capabilities', admitted <= set(names))
            components.append(component)
            for name in names:
                if name not in admitted:
                    rows = [row for row in component.get('owners', []) if row.get('typeName') == name]
                    pending[name] = str(rows[0].get('reason', rows[0]) if len(rows) == 1 else 'missing-independent-child-outcome')[:1800]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            for name in names:
                pending[name] = str(error)[:1800]
    by_type = {cap['typeName']: dict(componentSchema=component['schema'], capability=key)
               for component in components for key, cap in component.get('capabilities', {}).items()}
    result = dict(schema=SCHEMA, nativeInputs=pins, components=components, byType=by_type,
        owners=[dict(typeName=name, status='validated' if name in by_type else 'pendingReview',
                     **({} if name in by_type else dict(reason=pending.get(name, 'missing-child'))))
                for name in parameter_types], parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    validate(result, pins)
    _publication_gate(image, pins)
    return json.loads(json.dumps(result))


def bind_parents(image, pins, source, registry):
    """Bind every admitted child at the caller's actual context and E8."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import derive_binding
    selected = validate(registry, pins)
    children = {}
    usages = {}
    for read in source['orderedSourceReads']:
        name = read['declaredType']
        if name not in selected:
            continue
        component, key = selected[name]
        if name not in children:
            children[name] = copy.copy(component)
            children[name]['capabilities'] = {key: component['capabilities'][key]}
            children[name]['owners'] = [row for row in component['owners'] if row.get('typeName') == name]
            children[name]['parentBindings'] = {}
        usage = derive_typed_usage_context(image, read['context']['instructionRva'], label=LABEL + '.actualParent')
        binding = derive_binding(image, pins, typed_request=usage,
            source_target=image.pe.image_base + read['sourceTargetRva'], source_instruction=read['instruction'],
            component=children[name], capability=key)
        site = str(usage['instructionRva'])
        need('unique-actual-parent-site', site not in children[name]['parentBindings'])
        children[name]['parentBindings'][site] = binding
        usages[read['memberIndex']] = usage
    return children, usages


def bind_output_parents(image,pins,source,component):
    """Output's T has no wire grammar; use only its separate complete owner."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.levelscript_action_output_components import PREFIX as OUTPUT,CAP_PREFIX as KEY
    from scripts.game_data.memorypack.levelscript_action_output_bindings import derive_binding
    children={};usages={}
    need('same-output-registry-native-inputs',component.get('nativeInputs')==pins)
    for read in source['orderedSourceReads']:
        name=read['declaredType'];key=KEY+name
        if not name.startswith(OUTPUT)or key not in component.get('capabilities',{}):continue
        if name not in children:
            children[name]=copy.copy(component)
            children[name]['capabilities']={key:component['capabilities'][key]}
            children[name]['owners']=[o for o in component['owners']if o.get('typeName')==name]
            children[name]['parentBindings']={}
        usage=derive_typed_usage_context(image,read['context']['instructionRva'],label=LABEL+'.actualOutputParent')
        bound=derive_binding(image,pins,typed_request=usage,source_target=image.pe.image_base+read['sourceTargetRva'],
            source_instruction=read['instruction'],component=children[name],capability=key)
        site=str(usage['instructionRva']);need('unique-output-parent-site',site not in children[name]['parentBindings'])
        children[name]['parentBindings'][site]=bound;usages[read['memberIndex']]=usage
    return children,usages
