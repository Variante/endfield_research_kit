"""Finite typed animation dictionaries joined to independent callback owners.

Ordered serialized entries and duplicate keys are preserved. This does not
reconstruct the final mutable Dictionary or infer a Clear on reused outputs.
The actual containing local/field/frame and AnimationConfig owner remain with
their separate source composer; provider, MethodInfo and insertion effects
are explicit normal-path conditions.
"""
import json

from scripts.game_data.memorypack import animation_custom_dictionary_sources as source
from scripts.game_data.memorypack import animation_custom_dictionary_callbacks as callbacks

SCHEMA = 'endfield.animation-custom-dictionary-components.v1'
CAPABILITIES = {
    'montages': 'animation-custom-montage-dictionary',
    'syncGroupCurves': 'animation-custom-string-curve-dictionary',
    'timeRefCurves': 'animation-custom-int-curve-dictionary',
}
MONTAGE = 'animation-montage-selected-union'
CURVE = 'beyond-curve-value'


def need(check, condition):
    if not condition:
        raise ValueError('animationCustomDictionaryComponents.'+check)


def normalized(value):
    return json.loads(json.dumps(value))


def replay_source(actual, pins):
    domain = actual.get('domain'); need('finite-source-domain', domain in source.DOMAINS)
    _, key, value, profile = source.DOMAINS[domain]
    need('exact-own-source', actual.get('schema') == source.SCHEMA
        and actual.get('status') == 'validated-conditional-static-out-animation-source'
        and actual.get('nativeInputs') == pins and actual.get('typeName') == source.type_name(domain)
        and (actual.get('keyType'), actual.get('valueType')) == (key, value)
        and actual.get('resultAbi') == 'void-byref-reference8' and actual.get('referenceBytes') == 8
        and actual.get('actualSourceProved') is True and actual.get('closedPointerEquivalenceProved') is False
        and actual.get('callbackGrammarAdmitted') is False and actual.get('wholeOwnerAdmitted') is False
        and type(actual.get('sourceTargetRva')) is int and actual['sourceTargetRva'] > 0)
    p = actual['proof']; request = p.get('request', {})
    source.request_shape(request.get('typedRequest', {}), domain)
    need('same-static-definition-and-ABI', request.get('methodInfoRegister') == 'r8'
        and request.get('resultAbi') == actual['resultAbi'] and request.get('typeName') == actual['typeName']
        and request['typedRequest']['methodSpec'][0] == actual.get('staticReaderMethodDefinition'))
    programs = p.get('programs', [])
    need('complete-source-witness-set', len(programs) == 5 and programs[0].get('selectedBytes'))
    base = programs[0]['selectedBytes'][0][0]-actual['sourceTargetRva']
    need('explicit-selected-native-base', type(base) is int and base >= 2**32)
    parent = p.get('actualParent', {})
    need('own-actual-parent-call-scope', parent.get('typeName') == source.PARENT
        and parent.get('memberIndex') == source.DOMAINS[domain][0] and parent.get('fieldName') == domain
        and parent.get('originalField', [])[:2] == [source.PARENT, actual['typeName']]
        and parent.get('actualTypedCallProved') is True and parent.get('zeroLocalProved') is False
        and parent.get('parentFieldAdmitted') is False and parent.get('enclosingFrameAdmitted') is False)
    caller_raw = callbacks.regions(parent['windows'], parent['regions'], base, 'dictionary-parent')
    need('exact-actual-R8-E8-call-replay', normalized(source.caller_program(caller_raw,
        request['typedRequest'], base+actual['sourceTargetRva'], base=base)) == parent.get('program'))
    raw = callbacks.regions(p['actualWindows'], p['actualSourceRegions'], base, 'dictionary')
    symbols, checked = source.programs(raw, base+actual['sourceTargetRva'], p['readerOffsets'], profile)
    need('all-complete-source-byte-programs', normalized(checked) == programs
        and {k:v-base for k,v in symbols.items()} == p.get('symbolRvas'))
    counted = source.induction(checked, count_limit=p['induction']['maxCount'])
    need('same-exact-counted-source', normalized(counted) == p['induction'])
    return base


def replay_callback(callback, pins):
    name = callback.get('typeName'); integer = name == 'int'
    need('own-nominal-key-callback', name in ('string', 'int')
        and callback.get('schema') == ('endfield.animation-custom-Int32-callback.v1' if integer
            else 'endfield.animation-custom-pooled-string-callback.v1')
        and callback.get('status') == 'validated-conditional-callback' and callback.get('nativeInputs') == pins
        and callback.get('wireBytes') == 4 and callback.get('outputBytes') == (4 if integer else 8)
        and callback.get('callbackSlot') == 5 and callback.get('actualRuntimeSelectionObserved') is False
        and all(type(callback.get(k)) is int and callback[k] > 0 for k in ('callbackMethodDefinition', 'callbackTargetRva'))
        and isinstance(callback.get('conditions'), list) and len(callback['conditions']) == 2)
    p = callback['proof']
    if integer:
        from scripts.game_data.memorypack.int_list_sources import integer as integer_program
        registration = p['registration']; base = registration['pointer']-callback['callbackTargetRva']
        args = registration['classInstantiation']['arguments']
        need('independent-closed-Int32-registration', registration.get('methodDefinitionIndices') == [callback['callbackMethodDefinition']]
            and len(args) == 1 and bytes.fromhex(args[0]['raw_type_record_hex'])[10:12] == bytes((8, 128))
            and bytes.fromhex(p['readerParameterRawHex'])[10:12] == bytes((17, 32))
            and bytes.fromhex(p['outputParameterRawHex'])[10:12] == bytes((19, 32))
            and p['outputParameterOwner'].get('ordinal') == 0 and callback.get('numericConversion') is False)
        raw = callbacks.regions(p['windows'], p['regions'], base, 'Int32-callback')
        need('own-whole-Int32-callback-replay', normalized(integer_program(raw, base+callback['callbackTargetRva'],
            p['readerOffsets'])) == p['program'])
    else:
        from scripts.game_data.memorypack.pooled_string_list_sources import pooled_string
        programs = p.get('programs', [])
        need('exact-pooled-string-domain', callback.get('encoding') == 'int32-pool-index'
            and callback.get('emptyIndex') == -1 and callback.get('nullIndex') == -2 and len(programs) == 3)
        fact = p.get('reviewedStringFact', {})
        methods = [m for m in fact.get('methods', []) if m[1:3] == ['MemoryPack.BeyondStringFormatter', 'Deserialize']]
        windows = [w for w in fact.get('programs', []) if w.get('role') == 'string']
        need('same-owned-string-method-and-window', fact.get('nativeInputs') == pins and len(methods) == len(windows) == 1
            and methods[0][0] == callback['callbackMethodDefinition']
            and methods[0][3] == windows[0].get('entryRva') == callback['callbackTargetRva']
            and windows[0].get('windows') == p.get('windows'))
        base = programs[0]['selectedBytes'][0][0]-callback['callbackTargetRva']
        raw = callbacks.regions(p['windows'], p['regions'], base, 'string-callback')
        symbols = {k:base+v for k,v in p['symbolRvas'].items()}
        checked = [pooled_string(raw, base+callback['callbackTargetRva'], symbols, mode=mode)
            for mode in ('lookup', 'empty', 'null')]
        need('own-whole-pooled-string-callback-replay', normalized(checked) == programs)
    return base


def replay_key_dispatch(actual, callback, dispatch, base):
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    need('actual-key-dispatch-identity', dispatch.get('sourceTargetRva') == actual['proof']['symbolRvas'].get('keyDispatch')
        and dispatch.get('callbackTargetRva') == callback['callbackTargetRva']
        and dispatch.get('callbackSelectionConditional') is True and dispatch.get('runtimeSelectionObserved') is False)
    raw = callbacks.regions(dispatch['windows'], dispatch['regions'], base, 'key-dispatch')
    chunks = dispatch['program']['selectedBytes']; at = next(a for a,h in chunks if h == 'e8')
    operand = bytes.fromhex(dict(chunks).get(at+1, ''))
    need('complete-actual-preparation-E8', len(operand) == 4)
    prepare = at+5+int.from_bytes(operand, 'little', signed=True)
    target = base+dispatch['sourceTargetRva']; selected = base+callback['callbackTargetRva']
    if actual['keyType'] == 'int':
        from scripts.game_data.memorypack.int_list_sources import dispatcher
        checked = dispatcher(raw, target, actual['proof']['readerOffsets'], prepare=prepare, callback=selected)
    else:
        checked = deserialize_slot(raw, target, prepare=prepare, callback=selected)
    need('whole-actual-key-dispatch-replay', normalized(checked) == dispatch['program'])


def curve_child(component, pins, actual, base):
    from scripts.game_data.memorypack.beyond_curve_value_components import compose
    from scripts.game_data.memorypack.skill_root_tag_query_transfer import adapter16_program
    need('independent-strong-BeyondCurve', component.get('schema') == 'endfield.beyond-curve-value-components.v1'
        and component.get('status') == 'validated-conditional-beyond-curve-value-components'
        and component.get('nativeInputs') == pins)
    caps = compose(pins, component['proof']['value'])
    need('complete-BeyondCurve-capability-retained', caps == component.get('capabilities'))
    cap = caps[CURVE]; typed = component['proof']['value']['proof']['typedSource']; p = typed['proof']
    helper = actual['proof']['helpers']['valueDispatch']
    need('actual-dispatcher-not-Reader-frontend', actual['proof']['symbolRvas']['valueDispatch']
        == helper['entryRva'] == cap['valueDispatcherTargetRva']
        and helper['windows'] == p['actualSourceWindows']['dispatch'])
    raw = callbacks.regions(helper['windows'], helper['regions'], base, 'BeyondCurve-dispatch')
    symbols = {k:base+v for k,v in p['adapter']['proof']['symbolRvas'].items()}
    programs = [adapter16_program(raw, base+helper['entryRva'], symbols, dispatch=True, **options)
        for options in ({}, {'create':False}, {'null':True})]
    need('all-actual-value-dispatch-paths', normalized(programs) == p['dispatchPaths']
        and all(row.get('selectorRead') is False for row in programs))
    return caps, CURVE, p['adapter']['proof']['symbolRvas']['adapter'], []


def montage_child(component, pins):
    from scripts.game_data.memorypack.animation_union_components import compose
    need('independent-selected-Montage-union', component.get('schema') == 'endfield.animation-selected-union-components.v1'
        and component.get('status') == 'validated-conditional-selected-animation-union-components'
        and component.get('nativeInputs') == pins and component.get('family') == 'montage')
    p = component['proof']; rebuilt = compose(p['unionSource'], p['records'], family='montage')
    need('complete-Montage-child-shapes-retained', rebuilt['capabilities'] == component.get('capabilities')
        and rebuilt['requiredExternalCapabilities'] == component.get('requiredExternalCapabilities'))
    adapter = p['unionSource']['families']['montage']['adapter']; binding = adapter['callbackBinding']
    need('own-canonical-reference-callback-condition', adapter.get('typeName') == 'Beyond.Montage.AnimMontageData'
        and adapter.get('nativeInputs') == pins and binding.get('actualCallbackEqualsCanonicalRequired') is True
        and binding.get('runtimeSelectionObserved') is False and binding.get('closedPointerEquivalenceProved') is False
        and type(binding.get('canonicalTargetRva')) is int and binding['canonicalTargetRva'] > 0)
    return rebuilt['capabilities'], MONTAGE, binding['canonicalTargetRva'], rebuilt['requiredExternalCapabilities']


def compose(pins, actual, key_callback, value_component, *, key_dispatch=None):
    """Pure replay/shape join. The fresh native builder owns its inputs."""
    base = replay_source(actual, pins); key_base = replay_callback(key_callback, pins)
    need('same-native-base-and-key-domain', base == key_base and key_callback['typeName'] == actual['keyType'])
    domain = actual['domain']
    if domain == 'montages':
        need('direct-slot5-no-invented-dispatch', key_dispatch is None)
        children, value_cap, callback, requirements = montage_child(value_component, pins)
    else:
        need('own-actual-key-dispatch-required', isinstance(key_dispatch, dict))
        replay_key_dispatch(actual, key_callback, key_dispatch, base)
        children, value_cap, callback, requirements = curve_child(value_component, pins, actual, base)
    required = sorted(set(requirements) | {'byte-payload'} if actual['keyType'] == 'string' else set(requirements))
    cap = dict(typeName=actual['typeName'], keyType=actual['keyType'], valueType=actual['valueType'],
        staticReaderMethodDefinition=actual['staticReaderMethodDefinition'], staticReaderTargetRva=actual['sourceTargetRva'],
        resultAbi='void-byref-reference8', referenceBytes=8, wholeGrammarAdmitted=True, staticOutReferenceAdmitted=True,
        ordinaryOriginalReadValueAdmitted=False, nullable=True, nullMarker=255, nullWireBytes=1,
        positiveMarkerDomain=[0, 254], nativePositiveHeaderOneEnforced=False, countEncoding='signed-int32',
        countBytes=4, minimumCount=0, countLimit=actual['proof']['induction']['maxCount'], nodeLimit=16384,
        positiveCountsAdmitted=True, keyWireBytes=4, valueWireBytes=None,
        keyCallback={k:key_callback[k] for k in ('typeName', 'wireBytes', 'outputBytes', 'callbackSlot',
            'callbackMethodDefinition', 'callbackTargetRva', 'actualRuntimeSelectionObserved', 'conditions')},
        valueCapability=value_cap, valueCallbackTargetRva=callback, requiredChildCapabilities=children,
        requiredExternalCapabilities=required, callbackSelectionConditional=True,
        initiallyNullOutputRequired=True, clearExistingDictionaryAdmitted=False,
        orderedEntriesPreserved=True, duplicateKeysPreserved=True, finalMutableDictionaryReconstructed=False,
        actualRuntimeSelectionObserved=False, parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        conditions=key_callback['conditions']+[actual['evidenceBoundary']['conditional'], __doc__])
    from scripts.game_data.memorypack.animation_custom_dictionary_codec import require_capability
    require_capability(cap, domain)
    return dict(capabilities={**children, CAPABILITIES[domain]:cap}, requiredExternalCapabilities=required)


def _derive_on_children(image, pins, *, requests, montage, curve, count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image, pins)
    need('all-and-only-three-actual-requests', isinstance(requests, dict) and set(requests) == set(source.DOMAINS))
    string = callbacks.derive_string(image, pins); integer = callbacks.derive_integer(image, pins)
    caps = {}; proofs = {}; required = set()
    for domain, request in requests.items():
        actual = source.derive(image, pins, domain=domain, typed_request=request['typedRequest'],
            source_target=request['sourceTarget'], count_limit=count_limit)
        key = integer if domain == 'timeRefCurves' else string
        dispatch = None if domain == 'montages' else callbacks.bind_dispatch(image, pins, actual, key)
        value = montage if domain == 'montages' else curve
        joined = compose(pins, actual, key, value, key_dispatch=dispatch)
        for name, cap in joined['capabilities'].items():
            need('coherent-overlapping-child-capability', name not in caps or caps[name] == cap)
            caps[name] = cap
        required.update(joined['requiredExternalCapabilities'])
        proofs[domain] = dict(source=actual, keyDispatch=dispatch)
    _publication_gate(image, pins)
    return normalized(dict(schema=SCHEMA, status='validated-conditional-animation-custom-dictionaries', nativeInputs=dict(pins),
        capabilities=caps, requiredExternalCapabilities=sorted(required),
        proof=dict(dictionaries=proofs, stringCallback=string, integerCallback=integer, montage=montage, curve=curve),
        parentFieldAdmitted=False, wholeOwnerAdmitted=False, evidenceBoundary=dict(exact='Three independently typed source/slot5/dispatcher/child joins with bounded counted wire programs.', conditional=__doc__)))


def derive(image, pins, *, requests, curve_request, curve_source_target, count_limit=4096):
    from scripts.game_data.memorypack import animation_record_components, animation_union_sources, animation_union_components
    from scripts.game_data.memorypack import beyond_curve_value_components
    records = animation_record_components.derive(image, pins,
        type_names=['Beyond.Montage.ClipMontageData', 'Beyond.Montage.SequenceMontageData'])
    need('both-complete-independent-Montage-records', len(records.get('owners',[])) == 2
        and all(row.get('status') == 'validated-conditional-animation-record-components' for row in records['owners']))
    owners = [row['proof'] for row in records['owners']]
    montage = animation_union_components.compose(animation_union_sources.derive(image, pins, families=['montage']), owners, family='montage')
    curve = beyond_curve_value_components.derive(image, pins, typed_request=curve_request, source_target=curve_source_target)
    return _derive_on_children(image, pins, requests=requests, montage=montage, curve=curve, count_limit=count_limit)
