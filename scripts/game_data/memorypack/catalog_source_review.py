"""Review allocations for held catalogs from a coherent current native result.

This module projects existing source and normative consumer evidence. It does
not authenticate a native operation, clear an old attribution hold, retire a
consumer or publish a catalog. Every candidate still needs a native projection
of the precise semantic roles the reviewed catalog will declare.
"""
from collections import Counter, deque

SOURCE_SCHEMA = 'endfield.generated-concrete-reader-source.v1'
INVENTORY_SCHEMA = 'endfield.retained-source-inventory.v1'
SCHEMA = 'endfield.current-catalog-source-review.v1'


def need(key, condition, detail=None):
    if not condition:
        raise ValueError('catalogSourceReview.' + key + ':' + str(detail)[:1000])


def _objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _objects(child)


def _source_windows(windows):
    need('literal-owned-source-windows', isinstance(windows, list) and bool(windows)
         and all(isinstance(w, dict) and type(w.get('startRva')) is int and type(w.get('endRva')) is int
                 and 0 < w['startRva'] < w['endRva'] and isinstance(w.get('sha256'), str)
                 and len(w['sha256']) == 64 and all(c in '0123456789abcdefABCDEF' for c in w['sha256'])
                 for w in windows))
    return [{k: w[k] for k in ('startRva', 'endRva', 'sha256')} for w in windows]


def complete_sources(document, pins):
    result = {}
    for proof in _objects(document):
        if proof.get('schema') != SOURCE_SCHEMA:
            continue
        name = proof.get('wrapperName')
        programs = proof.get('programs', [])
        method = proof.get('method', [])
        need('complete-current-general-source', proof.get('nativeInputs') == pins
             and isinstance(name, str) and name and isinstance(proof.get('wrappedType'), str)
             and proof.get('completeSelectedCallerAdmitted') is True
             and proof.get('childGrammarAdmitted') is False
             and len(method) == 4 and method[1:3] == [name, 'Deserialize']
             and type(method[0]) is int and type(method[3]) is int and method[0] >= 0 and method[3] > 0
             and len(programs) == 4
             and {(p.get('existing'), p.get('wrapperNull')) for p in programs}
                 == {(False, False), (False, True), (True, False), (True, True)}
             and all(type(p.get('existing')) is bool and type(p.get('wrapperNull')) is bool
                     and p.get('frame', {}).get('entryRspRestored') is True
                     and p.get('frame', {}).get('allWin64IntegerNonvolatilesRestored') is True for p in programs), name)
        windows = _source_windows(proof.get('codeWindows'))
        row = dict(wrapperName=name, wrappedType=proof['wrappedType'], sourceKind='complete-general-source',
            sourceMethods=[method], codeWindows=windows, allFourCallerPathsProved=True,
            sourceChildRequirements=proof.get('childRequirements', []),
            orderedSourceReads=proof.get('orderedSourceReads', []),
            evidenceBoundary=proof.get('evidenceBoundary'), childGrammarFromSourceAdmitted=False)
        if name in result:
            need('no-conflicting-current-source-identity', result[name]['sourceMethods'] == row['sourceMethods']
                 and result[name]['codeWindows'] == windows and result[name]['wrappedType'] == row['wrappedType'], name)
        result[name] = row
    return result


def _programs(value):
    for row in _objects(value):
        if set(('family', 'tag', 'wrapperName', 'memberCount', 'reads')) <= set(row):
            if (isinstance(row.get('family'), str) and type(row.get('tag')) is int
                    and isinstance(row.get('wrapperName'), str) and type(row.get('memberCount')) is int
                    and isinstance(row.get('reads'), list) and len(row['reads']) == row['memberCount']):
                yield row


def _child_edges(value):
    edges = set()
    for row in _objects(value):
        for key in ('childCapability', 'elementCapability'):
            child = row.get(key)
            if isinstance(child, str) and child:
                edges.add(child)
        for key in ('requiredCapabilities', 'requiredExternalCapabilities'):
            children = row.get(key, [])
            if isinstance(children, list):
                edges.update(n for n in children if isinstance(n, str) and n)
    return edges


def _complete_capability(cap):
    return (isinstance(cap, dict) and (cap.get('wholeGrammarAdmitted') is True
            or cap.get('positiveCountsAdmitted') is True and cap.get('elementGrammarAdmitted') is True))


def consumer_index(aggregate):
    from scripts.game_data.memorypack import catalog_capability_closure as closure,catalog_consumer_domains as domains
    caps = aggregate.get('capabilities', {})
    need('literal-current-capabilities-and-route-requirements', isinstance(caps, dict)
         and all(isinstance(n, str) and n and isinstance(c, dict) for n, c in caps.items())
         and isinstance(aggregate.get('routeRequirements'), dict))
    index = {}
    for program in _programs(aggregate.get('programs', [])):
        route = program['family'] + ':' + str(program['tag'])
        requirements = aggregate['routeRequirements'].get(route)
        need('literal-explicit-route-requirements', requirements is None or isinstance(requirements, list)
             and all(isinstance(n, str) and n for n in requirements), route)
        direct = _child_edges(program.get('reads', []))
        starting = set(requirements or []) | direct
        queue = deque((n, [n]) for n in sorted(starting))
        reached = {}
        closure_modes = {}
        missing = set()
        while queue:
            name, path = queue.popleft()
            if name not in caps:
                missing.add(name)
                continue
            mode=closure.describe(aggregate,name,path)
            if name in reached and(closure_modes[name]['closedLocally']or not mode['closedLocally']):
                continue
            reached[name] = path
            closure_modes[name]=mode
            for child in sorted(_child_edges(caps[name])|set(mode['requiredCapabilities'])):
                queue.append((child, path+[child]))
        incomplete = sorted(name for name in reached if not closure_modes[name]['closedLocally'])
        closed = requirements is not None and not missing and not incomplete
        common = dict(family=program['family'], currentTag=program['tag'], routeKey=route,
            topLevelWrapper=program['wrapperName'], routeClosurePresent=closed,
            missingCapabilities=sorted(missing), incompleteCapabilities=incomplete,
            conditionalCapabilityClosure=[dict(capability=name,**mode)for name,mode in sorted(closure_modes.items())
                if mode['closedLocally']and mode['mode']not in('whole-capability-grammar','selected-positive-collection')],
            explicitRouteRequirements=requirements, historicalTagUsed=False)
        index.setdefault(program['wrapperName'], []).append(dict(common, consumerKind='current-normative-program',
            memberCount=program['memberCount'], actualOrderedReads=program['reads'], capabilityPath=[]))
        for name, path in reached.items():
            cap = caps[name]
            own = dict(common, consumerKind='reachable-current-domain', capability=name, capabilityPath=path,
                       capabilityComplete=closure_modes[name]['closedLocally'])
            wrapper = cap.get('wrapperName')
            if isinstance(wrapper, str) and wrapper:
                index.setdefault(wrapper, []).append(own)
            original = cap.get('typeName')
            if (isinstance(original, str) and original and
                    (cap.get('ordinaryOriginalReadValueAdmitted') is True or cap.get('actualValueReadValueAdmitted') is True)):
                index.setdefault('original:'+original, []).append(dict(own,
                    consumerKind='reachable-exact-original-domain', typeName=original,
                    actualOriginalReadAdmitted=True, wrapperIdentityFromIndependentSourceRequired=True))
            domains.add_original(index,name,cap,caps,path,own)
            for nested in [*_programs(cap.get('programs', [])),*domains.nested_programs(name,cap)]:
                index.setdefault(nested['wrapperName'], []).append(dict(own,
                    consumerKind='reachable-nested-normative-program', nestedFamily=nested['family'],
                    nestedTag=nested['tag'], memberCount=nested['memberCount'], actualOrderedReads=nested['reads']))
    return index


def review(aggregate, inventory, *, dedicated_source_resolver=None, source_documents=None):
    from scripts.game_data.skill_timeline_current_sequence_native import SCHEMA as AGGREGATE_SCHEMA
    need('callable-only-dedicated-source-resolver', dedicated_source_resolver is None or callable(dedicated_source_resolver))
    need('explicit-bounded-retained-source-documents',source_documents is None or isinstance(source_documents,(list,tuple))
         and 0<len(source_documents)<=1024 and all(isinstance(d,dict)for d in source_documents))
    need('one-coherent-current-aggregate', aggregate.get('schema') == AGGREGATE_SCHEMA
         and aggregate.get('status') == 'exact-current-build' and isinstance(aggregate.get('nativeInputs'), dict)
         and bool(aggregate['nativeInputs']))
    pins = aggregate['nativeInputs']
    need('same-selected-native-inventory', inventory.get('schema') == INVENTORY_SCHEMA
         and inventory.get('nativeInputs') == pins and isinstance(inventory.get('catalogs'), list))
    document = aggregate
    if source_documents is None and aggregate.get('proof', {}).get('schema') == 'endfield.skill-contract-provenance.v1':
        from scripts.game_data.memorypack.skill_contract_provenance import expand_proof
        document = dict(aggregate, proof=expand_proof(aggregate['proof']))
    sources = complete_sources(document.get('proof', {}), pins)
    if source_documents is not None:
        for index,owned in enumerate(source_documents):
            need('same-selected-retained-source-document',owned.get('nativeInputs')==pins,index)
            for name,row in complete_sources(owned,pins).items():
                if name in sources:
                    previous=sources[name]
                    need('no-conflicting-current-source-identity',previous['sourceMethods']==row['sourceMethods']
                         and previous['codeWindows']==row['codeWindows']and previous['wrappedType']==row['wrappedType'],name)
                sources[name]=dict(row,retainedSourceDocumentIndex=index)
    consumers = consumer_index(aggregate)
    catalogs = []
    seen = set()
    for catalog in inventory['catalogs']:
        if catalog.get('historicalAttributionStatus') != 'held-current-source-proof-required':
            continue
        name = catalog.get('contract')
        need('distinct-named-held-catalogs', isinstance(name, str) and name and name not in seen, name)
        seen.add(name)
        owners = []
        scopes = catalog.get('exactSourceOwners', [])
        need('nonempty-distinct-current-source-scopes', isinstance(scopes, list) and bool(scopes)
             and len({s.get('wrapperName') for s in scopes}) == len(scopes), name)
        for scope in scopes:
            wrapper = scope.get('wrapperName')
            need('literal-source-wrapper', isinstance(wrapper, str) and bool(wrapper), name)
            source = sources.get(wrapper)
            dedicated = scope.get('dedicatedSourceOwner')
            holds = []
            if source is None and dedicated_source_resolver is not None:
                projected = dedicated_source_resolver(wrapper, document)
                if projected is not NotImplemented:
                    need('exact-dedicated-source-projection', isinstance(projected, dict)
                         and projected.get('nativeInputs') == pins and projected.get('wrapperName') == wrapper
                         and isinstance(projected.get('wrappedType'), str) and bool(projected['wrappedType'])
                         and projected.get('completeSelectedSourceAdmitted') is True
                         and(projected.get('genericReferenceReaderApplicable') is False
                             or projected.get('sourceKind')=='dedicated-reference-domain-source'
                                and projected.get('genericReferenceReaderApplicable')is True
                                and projected.get('genericReferenceReaderUsed')is False
                                and projected.get('genericNotApplicableClaimed')is False
                                and projected.get('originalIsValueType')is False and projected.get('nativeAttributionProved')is True)
                         and projected.get('childGrammarFromSourceAdmitted') is False
                         and isinstance(projected.get('sourceMethods'), list) and bool(projected['sourceMethods'])
                         and isinstance(projected.get('conditions'), list), wrapper)
                    source = dict(projected, codeWindows=_source_windows(projected.get('codeWindows')),
                                  sourceKind='dedicated-source-projection')
            if source is None:
                holds.append('dedicated-source-projection-required' if dedicated else 'complete-current-source-required')
            matches = list(consumers.get(wrapper, []))
            if source is not None:
                matches += consumers.get('original:'+source['wrappedType'], [])
            if not matches:
                holds.append('exact-current-consumer-join-required')
            elif not any(m['routeClosurePresent'] for m in matches):
                holds.append('complete-current-capability-closure-required')
            owners.append(dict(wrapperName=wrapper, currentSource=source, currentConsumers=matches,
                maintainedDedicatedOwner=None if not dedicated else dedicated.get('maintainedOwner'),
                concreteRemainingJoins=holds, historicalAttributionHoldCleared=False))
        candidate = all(not owner['concreteRemainingJoins'] for owner in owners)
        catalogs.append(dict(contract=name, status='current-source-and-consumer-review-candidate' if candidate else 'pending-current-owned-join',
            historicalAttributionHold=catalog.get('historicalAttributionHold'), exactOwners=owners,
            nativeSemanticRoleProjectionRequired=True, reviewedProjectionWritten=False,
            historicalAttributionHoldCleared=False, catalogAdmitted=False))
    groups = {}
    for row in catalogs:
        labels = {join for owner in row['exactOwners'] for join in owner['concreteRemainingJoins']}
        if not labels:
            labels = {'source-and-current-consumer-ready-for-native-role-review'}
        for label in sorted(labels):
            groups.setdefault(label, []).append(row['contract'])
    result=dict(schema=SCHEMA, nativeInputs=pins, catalogs=catalogs, groups=groups,
        counts=dict(heldCatalogs=len(catalogs), reviewCandidates=sum(r['status']=='current-source-and-consumer-review-candidate' for r in catalogs),
            remainingJoinKinds=dict(Counter(j for r in catalogs for o in r['exactOwners'] for j in o['concreteRemainingJoins']))),
        nativeOperationAuthenticated=False, catalogsActivated=0, historicalAttributionHoldsCleared=0,
        evidenceBoundary=__doc__)
    if source_documents is not None:
        result.update(retainedSourceDocumentCount=len(source_documents),aggregateProofMutated=False,
            aggregateSourceDigestExpansionRequired=False,currentConsumerProjectionConditional=True,
            independentNativeSourceAttributionRequired=True,freshFinalNativeOperationRequired=True)
    return result
