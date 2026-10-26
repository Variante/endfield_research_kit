"""Bounded authored entries for three independently selected animation maps.

The marker is one byte; FF is a null reference. Every positive marker is
followed by a separate signed count. Entries preserve wire order and duplicate
keys rather than claiming the final native mutable dictionary contents.
"""
import struct

from scripts.game_data.memorypack.animation_custom_dictionary_sources import DOMAINS, type_name

CAPABILITIES = {
    'montages': 'animation-custom-montage-dictionary',
    'syncGroupCurves': 'animation-custom-string-curve-dictionary',
    'timeRefCurves': 'animation-custom-int-curve-dictionary',
}


def need(check, condition):
    if not condition:
        raise ValueError('animationCustomDictionaryCodec.'+check)


def require_capability(cap, domain):
    need('finite-owned-domain', domain in DOMAINS)
    _, key, value, _ = DOMAINS[domain]
    need('own-static-out-identity', isinstance(cap, dict) and cap.get('typeName') == type_name(domain)
        and (cap.get('keyType'), cap.get('valueType')) == (key, value)
        and cap.get('resultAbi') == 'void-byref-reference8'
        and all(type(cap.get(k)) is int and cap[k] > 0
            for k in ('staticReaderMethodDefinition', 'staticReaderTargetRva', 'valueCallbackTargetRva'))
        and all(type(cap.get(k)) is int and cap[k] == n for k,n in
            (('referenceBytes',8), ('nullMarker',255), ('nullWireBytes',1), ('countBytes',4),
             ('minimumCount',0), ('nodeLimit',16384), ('keyWireBytes',4))))
    need('finite-positive-wire-domain', type(cap.get('countLimit')) is int and 3 <= cap['countLimit'] <= 4096
        and cap.get('positiveMarkerDomain') == [0, 254]
        and all(type(n) is int for n in cap['positiveMarkerDomain'])
        and cap.get('countEncoding') == 'signed-int32' and cap.get('valueWireBytes') is None
        and all(cap.get(k) is True for k in ('wholeGrammarAdmitted', 'staticOutReferenceAdmitted', 'nullable',
            'positiveCountsAdmitted', 'callbackSelectionConditional', 'initiallyNullOutputRequired',
            'orderedEntriesPreserved', 'duplicateKeysPreserved'))
        and all(cap.get(k) is False for k in ('ordinaryOriginalReadValueAdmitted', 'nativePositiveHeaderOneEnforced',
            'clearExistingDictionaryAdmitted', 'finalMutableDictionaryReconstructed',
            'actualRuntimeSelectionObserved', 'parentFieldAdmitted', 'wholeOwnerAdmitted'))
        and isinstance(cap.get('conditions'), list) and bool(cap['conditions'])
        and all(isinstance(c,str) and bool(c) for c in cap['conditions']))
    callback = cap.get('keyCallback', {})
    need('own-key-callback-shape', callback.get('typeName') == key
        and all(type(callback.get(k)) is int and callback[k] == n for k,n in
            (('wireBytes',4), ('outputBytes',4 if key == 'int' else 8), ('callbackSlot',5)))
        and all(type(callback.get(k)) is int and callback[k] > 0 for k in ('callbackMethodDefinition','callbackTargetRva'))
        and callback.get('actualRuntimeSelectionObserved') is False and len(callback.get('conditions', [])) == 2)
    children = cap.get('requiredChildCapabilities')
    need('complete-value-child-map', isinstance(children, dict) and bool(children)
        and all(isinstance(k,str) and bool(k) and isinstance(v,dict) for k,v in children.items()))
    if domain == 'montages':
        from scripts.game_data.memorypack.animation_record_components import PLANS
        selected = children.get('animation-montage-selected-union', {})
        need('whole-selected-Montage-child', cap.get('valueCapability') == 'animation-montage-selected-union'
            and selected.get('typeName') == value and selected.get('declaredUnionEntries') == 2
            and selected.get('allDeclaredTagsCovered') is True
            and all(selected.get(k) is True for k in ('wholeGrammarAdmitted','selectedStoredByteGrammarAdmitted',
                'ordinaryBaseAdapterAdmitted','inheritedBaseConversionsAdmitted','nullable'))
            and selected.get('nullMarker') == 255 and selected.get('tagEncoding') == 'short-byte'
            and selected.get('wideTagsAdmitted') is False)
        routes = selected.get('selectedRoutes', [])
        need('all-and-only-two-Montage-records', len(routes) == 2
            and {(r.get('tag'),r.get('typeName')) for r in routes} ==
                {(0,'Beyond.Montage.ClipMontageData'),(1,'Beyond.Montage.SequenceMontageData')})
        for row in routes:
            key_cap, count = PLANS[row['typeName']]; child = children.get(key_cap, {})
            need('complete-ordinary-Montage-record-shape', row.get('childCapability') == key_cap
                and type(row.get('memberCount')) is int and row['memberCount'] == count
                and child.get('typeName') == row['typeName'] and child.get('wrapperName') == row.get('wrapperName')
                and child.get('memberCount') == count and len(child.get('orderedReads',[])) == count
                and all(child.get(k) is True for k in ('wholeGrammarAdmitted','ordinaryOriginalReadValueAdmitted',
                    'directWrapperGrammarAdmitted','ownConcreteGetterSemanticsProved','ownConcreteFactorySemanticsProved')))
    else:
        from scripts.game_data.memorypack.beyond_curve_value_codec import require_capability as curve_capability
        need('distinct-BeyondCurve-value-child', cap.get('valueCapability') == 'beyond-curve-value')
        curve_capability(children.get('beyond-curve-value'))
    external = cap.get('requiredExternalCapabilities')
    need('explicit-external-capability-set', isinstance(external,list) and external == sorted(set(external))
        and all(isinstance(k,str) and bool(k) for k in external)
        and ('byte-payload' in external if key == 'string' else True))
    return cap


def read(reader, domain, *, budget=None, depth=0):
    """Read one map on the selected animation cursor; no enclosing EOF grant."""
    need('finite-domain-and-depth', domain in CAPABILITIES and type(depth) is int and 0 <= depth < 64)
    cap = require_capability(reader.operation.child(CAPABILITIES[domain]), domain)
    # A null outer marker never bypasses independently required child gates.
    for name, child in cap['requiredChildCapabilities'].items():
        need('same-complete-child-capability:'+name, reader.operation.child(name) == child)
    for name in cap['requiredExternalCapabilities']:
        external = reader.operation.child(name)
        if name == 'byte-payload':
            need('selected-pooled-string-operation', external.get('wholeGrammarAdmitted') is True
                and external.get('encoding') == 'int32-pool-index'
                and external.get('emptyIndex') == -1 and external.get('nullIndex') == -2)
    if budget is None: budget = dict(remaining=cap['nodeLimit'])
    need('literal-shared-node-budget', isinstance(budget,dict) and set(budget) == {'remaining'}
        and type(budget['remaining']) is int and 0 <= budget['remaining'] <= cap['nodeLimit'])
    start = reader.pos; marker = reader.peek(); null = marker == 255; count = None
    if not null:
        need('complete-marker-and-count', start+5 <= reader.limit)
        count = struct.unpack_from('<i', reader.data, start+1)[0]
        need('nonnegative-bounded-count-before-consumption', 0 <= count <= cap['countLimit'])
    required = 1 + (0 if null else count)
    need('shared-node-budget-before-consumption', required <= budget['remaining']); budget['remaining'] -= required
    reader.take(1 if null else 5, CAPABILITIES[domain]+'.marker-count')
    entries = []
    for index in range(0 if null else count):
        at = reader.pos; need('complete-key-bits', at+4 <= reader.limit)
        raw = bytes(reader.data[at:at+4]); key = struct.unpack('<i', raw)[0]
        if cap['keyType'] == 'string':
            pool_index = key; key = reader.operation.pool_index(pool_index)
            need('nonnull-selected-string-key', isinstance(key,str))
            extra = dict(poolIndex=pool_index)
        else: extra = {}
        reader.take(4, CAPABILITIES[domain]+'.key')
        value_start = reader.pos
        if domain == 'montages':
            need('selected-Montage-cursor', callable(getattr(reader,'selected_union',None)))
            value = reader.selected_union(cap['valueCapability'], depth=depth+1)
        else:
            from scripts.game_data.memorypack.beyond_curve_value_codec import read_curve
            value = read_curve(reader)
        entries.append(dict(index=index,start=at,end=reader.pos,key=key,keyRawHex=raw.hex(),
            valueStart=value_start,value=value,**extra))
    row = dict(kind=CAPABILITIES[domain], typeName=cap['typeName'], start=start, end=reader.pos,
        isNull=null, marker=marker, count=count, entries=entries, serializedOrderPreserved=True,
        duplicateKeysPreserved=True, finalMutableDictionaryReconstructed=False,
        containingOwnerClaimed=False, runtimeAnimationProved=False)
    reader.records.append(row); return row
