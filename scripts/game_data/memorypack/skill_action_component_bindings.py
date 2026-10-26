"""Pure disjoint extension joins for source-proved current action programs.

The native owner must freshly derive the transport and every selected concrete
source first. Existing finite routes retain their own proof and field labels;
an exclusion is only a consistency check, never a new grammar admission. The
caller must bind the returned external identities before appending any rows.
"""
import json

from scripts.game_data.memorypack.skill_action_union_sources import TYPE,WRAPPER
from scripts.game_data.memorypack.skill_timeline_current_sequence import validate_program

LABEL='skillActionComponentBindings'


def need(check,valid):
    if not valid:raise ValueError(LABEL+'.'+check)


def transport_routes(transport,pins):
    need('selected-transport',transport.get('schema')=='endfield.skill-action-union-source.v1'
        and transport.get('status')=='validated-current-action-union-transport'and transport.get('nativeInputs')==pins
        and transport.get('typeName')==TYPE and transport.get('wrapperName')==WRAPPER
        and transport.get('baseGetterSemanticsAdmitted')is True
        and transport.get('concreteChildGrammarAdmitted')is False and transport.get('wholeUnionAdmitted')is False)
    routes=transport['programs'];by_name={r['wrapperName']:r for r in routes}
    need('transport-bijection',len(by_name)==len(routes)==len({r['tag']for r in routes})
        and all(type(r.get('tag'))is int and 0<=r['tag']<=65535 and r.get('family')=='AbilityActionData'for r in routes))
    return by_name


def extension_names(transport,pins,existing,inventory):
    """Exclude independently owned routes only after actual identity checks."""
    routes=transport_routes(transport,pins);seen=set();tags=set()
    for row in existing:
        if row['family']!='AbilityActionData':continue
        validate_program(row);name=row['wrapperName'];need('distinct-existing-routes',name not in seen and row['tag']not in tags)
        seen.add(name);tags.add(row['tag']);actual=routes.get(name,{})
        need('existing-current-transport-identity',(actual.get('tag'),actual.get('wrappedType'))==(row['tag'],row['wrappedType']))
        selected=inventory.get(name,{})
        need('existing-current-member-count',type(selected.get('memberCount'))is int
            and selected['memberCount']==row['memberCount']and selected.get('abstract')is False)
    need('complete-selected-metadata-inventory',set(routes)<=set(inventory))
    for name in routes:
        row=inventory[name]
        need('literal-metadata-candidate',type(row.get('abstract'))is bool and type(row.get('memberCount'))is int and row['memberCount']>=0)
    return [name for name in routes if name not in seen and not inventory[name]['abstract']]


def prepare_extension(component,pins,caps,existing):
    """Return rows and exact external obligations; this mutates no aggregate."""
    need('finite-action-scope',component.get('schema')=='endfield.skill-action-components.v5'
        and component.get('status')=='validated-finite-current-action-components'and component.get('nativeInputs')==pins
        and component.get('wholeUnionAdmitted')is False and component.get('wholeSkillDataAdmitted')is False)
    routes=transport_routes(component['proof']['transport'],pins)
    programs=component['programs'];selected=component['selectedWrappers'];pending=component['pendingRoutes']
    names=[row['wrapperName']for row in programs];held=[row['wrapperName']for row in pending]
    need('selected-source-result-bijection',len(selected)==len(set(selected))and len(names)==len(set(names))
        and len(held)==len(set(held))and not set(names)&set(held)and set(selected)==set(names)|set(held)
        and set(selected)<=set(routes))
    sources={row['wrapperName']:row for row in component['proof']['concreteReaders']}
    need('complete-admitted-source-bijection',len(sources)==len(component['proof']['concreteReaders'])and set(sources)==set(names))
    previous_names={row['wrapperName']for row in existing};previous_tags={(row['family'],row['tag'])for row in existing}
    need('disjoint-selected-wrapper-scope',not set(selected)&previous_names)
    from scripts.game_data.memorypack.skill_root_children_codec import LISTS,POOLED_STRINGS
    from scripts.game_data.memorypack.skill_root_child_bindings import collection_identity
    from scripts.game_data.memorypack.skill_action_managed_value_bindings import TYPES,require_wire_capability
    managed=component.get('requiredExternalManagedValueIdentities');managed_used=set()
    static=component.get('requiredExternalStaticReferenceIdentities');static_used=set()
    from scripts.game_data.memorypack import skill_gait_dictionary_components as gait
    from scripts.game_data.memorypack.skill_gait_dictionary_bindings import bind as bind_static
    need('finite-static-reference-identity-map',isinstance(static,dict)and set(static)<={gait.CAPABILITY})
    need('finite-managed-value-identity-map',isinstance(managed,dict)and set(managed)<={row[0]for row in TYPES.values()})
    requirements={};used=set();declared=component['routeRequirements']
    need('admitted-requirements-bijection',set(declared)==set(names))
    for row in programs:
        validate_program(row);name=row['wrapperName'];source=sources[name];actual=routes[name]
        need('actual-action-identity',row['family']=='AbilityActionData'and(row['family'],row['tag'])not in previous_tags
            and row['sourceOwner']=='skill_timeline_current_sequence_native.json'and row['wrapperNullAdmitted']is True
            and(row['tag'],row['wrappedType'])==(actual['tag'],actual['wrappedType']))
        need('complete-own-concrete-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
            and source.get('nativeInputs')==pins and source.get('wrappedType')==row['wrappedType']
            and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False
            and source.get('wholeOwnerAdmitted')is False and len(source['orderedSourceReads'])==row['memberCount'])
        children=sorted({read['childCapability']for read in row['reads']if read['childCapability']is not None})
        need('actual-ordered-child-obligations',declared[name]==children
            and all(cap in caps and (cap in LISTS or cap==POOLED_STRINGS or cap in managed
                or caps[cap].get('wholeGrammarAdmitted')is True)for cap in children))
        for read in row['reads']:
            index=read['memberIndex'];actual_read=source['orderedSourceReads'][index]
            if actual_read.get('mode')=='typed-static-out-reference':
                need('exact-static-reference-wire-operation',read['kind']==gait.WIRE and read['childCapability']==gait.CAPABILITY
                    and static.get(gait.CAPABILITY)==caps.get(gait.CAPABILITY))
                candidates=[c for c in component['proof'].get('staticReferenceChildren',[])if c.get('proof',{}).get('source')==
                    source['sourceScope'].get('staticReferenceSources',{}).get(str(index))]
                need('one-own-static-reference-child',len(candidates)==1)
                binding=bind_static(source,source['sourceScope'],actual_read,pins,actual_read['context']['typedRequest'],candidates[0],gait.CAPABILITY)
                need('actual-static-reference-field-binding',binding in component['proof']['childBindings'].get(name,[])
                    and binding['staticReferenceCapabilityShape']==static[gait.CAPABILITY])
                static_used.add(gait.CAPABILITY)
            if not actual_read.get('kind','').startswith('managed:'):continue
            nominal=actual_read.get('declaredType');need('finite-managed-read-domain',nominal in TYPES)
            capability,wire,operation=TYPES[nominal];need('exact-managed-wire-operation',
                read['kind']==wire and read['childCapability']==operation and operation in managed and managed[operation]==caps.get(operation))
            require_wire_capability(dict(nativeInputs=pins,capabilities={capability:caps[operation]}),pins,nominal,capability)
            bindings=[b for b in component['proof']['childBindings'].get(name,[])if b.get('fieldName')==read['fieldName']
                and b.get('capability')==capability and b.get('typeName')==nominal]
            need('exactly-one-managed-domain-binding',len(bindings)==1)
            binding,=bindings
            context=actual_read.get('context',{})
            if actual_read.get('sourceContextMode')=='owned-closed-forwarder':
                from scripts.game_data.memorypack.generated_managed_forwarder_components import TYPE,require_source
                actual_source=source['sourceScope'].get('managedValueSources',{}).get(str(index),{})
                usage=actual_source.get('proof',{}).get('typedRequest',{})
                need('finite-managed-forwarder-identity',nominal==TYPE)
                require_source(actual_source,actual_read,pins,usage)
                context=actual_source['proof']['internalContext']
            need('actual-managed-source-and-whole-transfer-binding',binding.get('managedValueCapabilityShape')==managed[operation]
                and binding.get('managedValueTransfer',{}).get('completeFieldTransferAndFrameProved')is True
                and binding.get('ordinaryReferenceIdentityClaimed')is False
                and type(binding.get('readerMethodDefinition'))is int
                and binding['readerMethodDefinition']==context.get('methodSpec',[None])[0]
                and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==actual_read.get('sourceTargetRva'))
            managed_used.add(operation)
        requirements['AbilityActionData:'+str(row['tag'])]=children;used.update(children)
    need('complete-external-obligations',component.get('requiredExternalCapabilities')==sorted(used))
    need('complete-managed-value-identity-scope',set(managed)==managed_used)
    need('complete-static-reference-identity-scope',set(static)==static_used)
    if managed_used:
        value_children=component['proof'].get('managedValueChildren',{})
        for nominal,(capability,wire,operation)in TYPES.items():
            if operation not in managed_used:continue
            child=value_children.get(nominal,{})
            need('same-managed-wire-owner-inputs:'+nominal,child.get('nativeInputs')==pins)
            need('same-managed-wire-owner-capability:'+nominal,child.get('capabilities',{}).get(capability)==managed[operation])
            need('same-managed-wire-descendant-closure:'+nominal,
                all(shape==caps.get(name)for name,shape in child['capabilities'].items()))
    collections={cap for cap in used if cap in LISTS or cap==POOLED_STRINGS}
    identities=component.get('requiredExternalCollectionIdentities')
    need('complete-collection-identity-scope',isinstance(identities,dict)and set(identities)==collections)
    for capability in sorted(collections):
        expected=collection_identity(dict(capabilities=caps),capability)
        need('exact-selected-collection-identity:'+capability,identities[capability]==expected)
    return json.loads(json.dumps(dict(programs=programs,routeRequirements=requirements,
        requiredExternalCapabilities=sorted(used),requiredExternalCapabilityIdentities=component['requiredExternalCapabilityIdentities'],
        requiredExternalCollectionIdentities=identities,requiredExternalManagedValueIdentities=managed,
        requiredExternalStaticReferenceIdentities=static)))
