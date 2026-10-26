"""Compile complete generated ActionMap callers with independent child facts.

Public derivation accepts only literal family/tag selectors and freshly reads
the actual switch, wrapper, four source paths and children on the caller's
selected image. Metadata inventories and retained reports are not inputs.
"""
import json
from pathlib import Path

from scripts.game_data.levelscript_route_deserialize_native import LAYOUT_PATH
from scripts.game_data.memorypack.levelscript_condition_param_sources import PREFIX, CAP_PREFIX

SCHEMA = 'endfield.generated-actionmap-route-components.v1'
CAP_SCHEMA = 'endfield.generated-actionmap-route-capability.v1'
LABEL = 'generatedActionmapRoute'
OPERATIONS = frozenset(('bool-byte', 'byte', 'scalar32', 'scalar64-bits',
                       'float32-bits', 'float64-bits', 'byte-payload', 'condition-param', 'actionmap-param-output', 'actionmap-param-array'))


def need(check, value):
    if not value:
        raise ValueError(LABEL + '.' + check)


def select_routes(image, layouts, requests):
    """Read only requested family switches; tag rank/names never supply a case."""
    from scripts.game_data.memorypack.levelscript_action_route_sources import BASES, _declaration
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    need('reviewed-layout-schema', layouts.get('schema') == 'endfield.action-map-layouts.v5')
    reviewed = {(row['family'], row['wrapperName']) for row in layouts['layouts']}
    need('distinct-reviewed-layouts', len(reviewed) == len(layouts['layouts']))
    inventory = list(image.memorypack_wrappers.values())
    wrappers = {wrapper.type_definition: wrapper for wrapper in inventory}
    need('distinct-current-wrapper-identities', len(wrappers) == len(inventory)
         and len({w.name for w in inventory}) == len(inventory))
    switches = {}
    routes = {}
    for family in dict.fromkeys(request['family'] for request in requests):
        need('finite-dispatcher-family', family in BASES)
        switch = read_union_switch(image, BASES[family], wrappers=wrappers)
        entries = switch['entries']
        need('actual-complete-distinct-family-switch', type(switch['entryCount']) is int
             and switch['entryCount'] == len(entries)
             and len({e['tag'] for e in entries}) == len(entries)
             and len({e['wrapperName'] for e in entries}) == len(entries))
        switches[family] = switch
        for entry in entries:
            need('literal-actual-union-tag', type(entry['tag']) is int and 0 <= entry['tag'] <= 65535)
            wrapper = wrappers[entry['typeDefinition']]
            need('same-actual-wrapper-definition', wrapper.name == entry['wrapperName'])
            if (family, wrapper.name) in reviewed:
                continue
            routes[(family, entry['tag'])] = dict(family=family, tag=entry['tag'], **_declaration(wrapper),
                unionIdentity=dict(dispatcherVa=switch['dispatcherVa'], tableVa=switch['tableVa'],
                                   entryCount=switch['entryCount'], **entry))
    need('all-selectors-are-current-missing-routes', all((r['family'], r['tag']) in routes for r in requests))
    return switches, [routes[(r['family'], r['tag'])] for r in requests]


def compile_route(route, source, pins, *, param_children, typed_requests, pooled_sources, array_children=None):
    """Pure composition; native authority belongs only to fresh derive below."""
    from scripts.game_data.memorypack.generated_record_components import compile_member_program
    from scripts.game_data.memorypack.levelscript_action_route_sources import _join_source
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
    from scripts.game_data.memorypack import levelscript_action_output_components as output
    from scripts.game_data.memorypack.levelscript_action_output_bindings import _capability as output_capability
    from scripts.game_data.memorypack import levelscript_vector_param_array_sources as vector_arrays
    _join_source(route, source, pins)
    references = {}
    params = {}
    arrays={};array_children={}if array_children is None else array_children
    for index,component in array_children.items():
        need('exact-finite-array-child',type(index)is int and index==7
            and source['orderedSourceReads'][index]['declaredType']==vector_arrays.TYPE)
        cap=vector_arrays.validate_component(component,pins)
        arrays[vector_arrays.TYPE]=(vector_arrays.CAPABILITY,vector_arrays.WIRE,vector_arrays.CAPABILITY)
        params[vector_arrays.CAPABILITY]=dict(componentSchema=component['schema'],capability=cap)
    for name, component in param_children.items():
        if component.get('schema')==output.SCHEMA:
            key=output.CAP_PREFIX+name;cap,_=output_capability(component,key);wire=output.WIRE
            need('same-independent-output-name',cap['typeName']==name and name.startswith(output.PREFIX))
        else:
            key = CAP_PREFIX + name
            cap = _validate_capability(component, key);wire='condition-param'
            need('same-independent-ordinary-Param-name', cap['typeName'] == name and name.startswith(PREFIX))
        references[name] = (key, wire, key)
        params[key] = dict(componentSchema=component['schema'], capability=cap)
    for read in source['orderedSourceReads']:
        if read['kind'] != 'byte-payload':
            continue
        proof = pooled_sources.get(str(read['memberIndex']), {})
        need('own-actual-pooled-index-source', read['declaredType'] == 'string'
             and proof.get('status') == 'validated' and proof.get('nativeInputs') == pins
             and proof.get('wireEncoding') == 'int32-pool-index'
             and proof.get('sourceHelpers') == [read['sourceTargetRva']])
    program, pending = compile_member_program(source, pins,
        wrapper_name=route['wrapperName'], type_name=route['typeName'], value4={},
        references=references, reference_children=param_children, typed_requests=typed_requests,
        reference_binder=bind_reference,arrays=arrays,array_children=array_children)
    if pending:
        return None, pending
    unsupported = [dict(memberIndex=read['memberIndex'], fieldName=read['fieldName'], kind=read['kind'],
                        reason='independent finite route codec operation required')
                   for read in program['reads'] if read['kind'] not in OPERATIONS]
    if unsupported:
        return None, unsupported
    used = {read['childCapability'] for read in program['reads'] if read['kind'] in ('condition-param',output.WIRE,vector_arrays.WIRE)}
    need('exact-child-capability-set', used == set(params))
    cap = dict(schema=CAP_SCHEMA, family=route['family'], tag=route['tag'], wrapperName=route['wrapperName'],
        typeName=route['typeName'], memberCount=program['memberCount'],
        fields=[dict(memberIndex=read['memberIndex'], fieldName=read['fieldName'], declaredType=read['declaredType'])
                for read in source['orderedSourceReads']], program=program, params=params,
        nullAdmitted=True, positiveAdmitted=True, wholeRecordGrammarAdmitted=True,
        selectedCurrentUnionCaseProved=True, liveFormatterSelectionObserved=False,
        wholeOwnerAdmitted=False, runtimeExecutionAdmitted=False)
    return cap, []


def bind_reference(pins,join,component,capability):
    from scripts.game_data.memorypack import levelscript_action_output_components as output
    if component.get('schema')==output.SCHEMA:
        return output.bind_reference(pins,join,component,capability)
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import bind_reference as ordinary
    return ordinary(pins,join,component,capability)


def derive_many(image, pins, *, requests, layout_path=LAYOUT_PATH, progress=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import generated_reader_sources, pooled_source_helper
    from scripts.game_data.memorypack import levelscript_action_param_registry as registry_owner
    from scripts.game_data.memorypack import levelscript_action_output_components as output_owner
    from scripts.game_data.memorypack import levelscript_vector_param_array_sources as vector_arrays
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.levelscript_action_route_sources import _join_source
    need('bounded-distinct-route-selectors', type(requests) is list and 0 < len(requests) <= 256
         and all(type(r) is dict and set(r) == {'family', 'tag'}
                 and type(r['family']) is str and type(r['tag']) is int and 0 <= r['tag'] <= 65535 for r in requests)
         and len({(r['family'], r['tag']) for r in requests}) == len(requests))
    _publication_gate(image, pins)
    path = Path(layout_path)
    raw = path.read_bytes()
    switches, selected = select_routes(image, json.loads(raw), requests)
    sources = generated_reader_sources.derive_many(image, pins, [r['wrapperName'] for r in selected])
    need('same-fresh-source-batch', sources.get('nativeInputs') == pins and len(sources['owners']) == len(selected))
    names = sorted({read['declaredType'] for owner in sources['owners']
                    if owner.get('status') == 'complete-reader-source-proved'
                    for read in owner['proof']['orderedSourceReads'] if read['declaredType'].startswith(PREFIX)
                    and read['declaredType'].endswith('>')})
    registry = registry_owner.derive(image, pins, parameter_types=names) if names else dict(
        schema=registry_owner.SCHEMA, nativeInputs=pins, components=[], byType={}, owners=[],
        parentFieldAdmitted=False, wholeOwnerAdmitted=False)
    registry_owner.validate(registry, pins)
    outputs=sorted({read['declaredType']for owner in sources['owners']if owner.get('status')=='complete-reader-source-proved'
        for read in owner['proof']['orderedSourceReads']if read['declaredType'].startswith(output_owner.PREFIX)
        and read['declaredType'].endswith('>')})
    output_registry=output_owner.derive_many(image,pins,parameter_types=outputs)if outputs else dict(
        schema=output_owner.SCHEMA,nativeInputs=pins,capabilities={},owners=[],parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    owners = []
    pool = {}
    for route, outcome in zip(selected, sources['owners'], strict=True):
        try:
            if outcome.get('status') != 'complete-reader-source-proved':
                raise ValueError(LABEL+'.complete-selected-caller:'+str(outcome.get('reason',outcome.get('status')))[:1800])
            source = outcome['proof']
            _join_source(route, source, pins)
            children, usages = registry_owner.bind_parents(image, pins, source, registry)
            output_children,output_usages=registry_owner.bind_output_parents(image,pins,source,output_registry)
            need('disjoint-ordinary-and-output-domains',not(set(children)&set(output_children))and not(set(usages)&set(output_usages)))
            children.update(output_children);usages.update(output_usages)
            array_children={}
            for read in source['orderedSourceReads']:
                if read['declaredType']==vector_arrays.TYPE:
                    index=read['memberIndex']
                    array_children[index]=vector_arrays.derive_member(image,pins,source,member_index=index)
                    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label=LABEL+'.vectorParamArray')
                    need('disjoint-array-and-reference-requests',index not in usages)
                    usages[index]=usage
            pooled = {}
            for read in source['orderedSourceReads']:
                if read['kind'] == 'byte-payload':
                    target = read['sourceTargetRva']
                    if target not in pool:
                        pool[target] = pooled_source_helper.validate_on_image(image, image.pe.image_base + target, pins)
                    pooled[str(read['memberIndex'])] = pool[target]
            cap, pending = compile_route(route, source, pins, param_children=children,
                typed_requests=usages, pooled_sources=pooled,array_children=array_children)
            if pending:
                owners.append(dict(family=route['family'], tag=route['tag'], wrapperName=route['wrapperName'],
                    status='pendingReview', pending=pending, proof=dict(source=source), wholeOwnerAdmitted=False))
            else:
                owners.append(dict(family=route['family'], tag=route['tag'], wrapperName=route['wrapperName'],
                    status='validated', capability=cap, proof=dict(source=source,
                        selectedUnionCase=route['unionIdentity'], paramChildren=children, arrayChildren=array_children,pooledSources=pooled),
                    wholeOwnerAdmitted=False))
        except (ValueError, KeyError, IndexError, TypeError) as error:
            owners.append(dict(family=route['family'], tag=route['tag'], wrapperName=route['wrapperName'],
                status='pendingReview', reason=str(error)[:2200], sourceOutcome=outcome, wholeOwnerAdmitted=False))
        if progress is not None:
            progress(dict(stage='compiled-generated-actionmap-route', family=route['family'], tag=route['tag'],
                          status=owners[-1]['status']))
    need('reviewed-layout-bookend', path.read_bytes() == raw)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema=SCHEMA, nativeInputs=pins, unionSwitches=switches,
        paramRegistry=registry, outputRegistry=output_registry, owners=owners, wholeOwnerAdmitted=False, runtimeExecutionAdmitted=False)))


def derive(image, pins, *, family, tag, progress=None):
    batch = derive_many(image, pins, requests=[dict(family=family, tag=tag)], progress=progress)
    owner, = batch['owners']
    return dict(schema=SCHEMA, nativeInputs=pins, **owner)
