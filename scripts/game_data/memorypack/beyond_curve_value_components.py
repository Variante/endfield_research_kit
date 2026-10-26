"""Fresh Beyond curve value transfer joined to its own bounded wire grammar."""
import json
from scripts.game_data.memorypack.beyond_curve_value_codec import (
    TYPE, WRAPPER, CAPABILITY, KEY_FIELDS, ORDER, require_capability)


def need(key, condition):
    if not condition:
        raise ValueError('beyondCurveValueComponents.' + key)


def compose(pins, source):
    need('own-actual-value-source', source.get('schema') == 'endfield.beyond-curve-value-source.v1'
         and source.get('status') == 'proved-conditional-beyond-curve-value'
         and source.get('nativeInputs') == pins and source.get('typeName') == TYPE
         and source.get('wrapperName') == WRAPPER and source.get('managedBytes') == 16
         and source.get('referenceLaneOffset') == 0 and source.get('readMethod') == 'ReadValue'
         and source.get('actualSourceProved') is True and source.get('resultAbi') == 'hidden-local'
         and source.get('providerSelectionObserved') is False
         and source.get('parentFieldAdmitted') is False and source.get('wholeOwnerAdmitted') is False)
    limit = source.get('keyCountLimit')
    need('finite-key-domain', type(limit) is int and 1 <= limit <= 10000)
    proof = source.get('proof', {})
    wrapper = proof.get('wrapper', {})
    typed = proof.get('typedSource', {})
    need('independent-complete-wrapper-and-transfer', wrapper.get('status') == 'validated-conditional-beyond-curve-wrapper'
         and wrapper.get('nativeInputs') == pins and wrapper.get('typeName') == TYPE
         and wrapper.get('wrapperName') == WRAPPER and wrapper.get('wrapperWireGrammarAdmitted') is True
         and wrapper.get('ordinaryOriginalAdapterAdmitted') is False and wrapper.get('positiveKeyCountLimit') == limit
         and typed.get('schema') == 'endfield.managed-value16-read-source.v1'
         and typed.get('status') == 'proved-conditional-typed-managed16-read'
         and typed.get('nativeInputs') == pins and typed.get('typeName') == TYPE
         and typed.get('wrapperName') == WRAPPER and typed.get('managedBytes') == 16
         and typed.get('actualSourceProved') is True and typed.get('wireGrammarAdmitted') is False
         and typed.get('readerMethodDefinition') == source.get('readerMethodDefinition')
         and typed.get('sourceTargetRva') == source.get('sourceTargetRva'))
    types = wrapper.get('proof', {}).get('types', {})
    expected_curve = [['keys', 'Beyond.FKeyframe[]', 16], ['preWrapMode', 'UnityEngine.WrapMode', 24],
                      ['postWrapMode', 'UnityEngine.WrapMode', 28]]
    need('own-nominal-stored-layouts', types.get(TYPE, {}).get('managedBytes') == 16
         and types[TYPE].get('fields') == expected_curve
         and types.get('Beyond.FKeyframe', {}).get('managedBytes') == 32
         and types['Beyond.FKeyframe'].get('fields') == [[n, t, 16+i*4] for i, (n, t) in enumerate(KEY_FIELDS)])
    wire = dict(null=dict(headerBytes=1, marker=255, output='default zero16'),
                positive=dict(headerBytes=1, memberCount=3, fields=[
                    dict(name='keys', kind='raw-array', signedCountBytes=4, nullCount=-1, emptyCount=0,
                         positiveCountLimit=limit, elementBytes=32, elementHeaders=False,
                         order=[n for n, _ in KEY_FIELDS]),
                    dict(name='postWrapMode', kind='enum32-bits', bytes=4),
                    dict(name='preWrapMode', kind='enum32-bits', bytes=4)]))
    need('exact-separate-variable-wire-program', source.get('wireProgram') == wire
         and source.get('nullAdmitted') is True and source.get('positiveAdmitted') is True
         and source.get('nullMarker') == 255 and source.get('serializedMemberCount') == 3)
    wp = wrapper['proof']
    leaves = {row.get('method', [None, None, None])[2]: row for row in wp.get('wrapperValueMethods', [])}
    need('own-value-default-and-getter', set(leaves) == {'.ctor', 'CreateInstance', 'GetValue'}
         and all(row.get('method', [None, None])[1] == WRAPPER for row in leaves.values())
         and all(leaves[n].get('program', {}).get('holderOffset') == 16
                 and leaves[n]['program'].get('zeroedBytes') == 16
                 and leaves[n]['program'].get('ordinaryReturn') is True for n in ('.ctor', 'CreateInstance'))
         and leaves['GetValue'].get('program', {}).get('sourceHolderOffset') == 16
         and leaves['GetValue']['program'].get('outputBytes') == 16
         and leaves['GetValue']['program'].get('sameOutputReturnedInRax') is True)
    programs = wp.get('programs', [])
    need('all-four-concrete-wrapper-paths', len(programs) == 4
         and sum(p.get('nullWrapper') is True for p in programs) == 2
         and {p.get('newWrapper') for p in programs if p.get('nullWrapper') is False} == {False, True}
         and all(p.get('normalFrameAndReturn') is True and p.get('headerBytes') == 1
                 and (p.get('nullWrapper') is True or p.get('nativeWireOrder') ==
                      ['keys.rawArray32', 'postWrapMode.raw4', 'preWrapMode.raw4']) for p in programs))
    if limit > 8:
        domain = wp.get('countDomain', {})
        need('complete-positive-key-copy-domain', domain.get('countMinimum') == -1
             and domain.get('countMaximum') == limit and domain.get('elementBytes') == 32
             and domain.get('maximumPayloadBytes') == 32*limit
             and all(domain.get(k) is True for k in ('copyBoundCoversEveryPayload',
                 'allPositiveShiftResultsExactNonnegativeSignedInt32', 'allocationCountUnchanged',
                 'sourceProgramAdmitted', 'copyProgramAdmitted', 'allPositiveCountsUseSameCompleteSourceProgram'))
             and domain.get('unsupportedNegativeCountsAdmitted') is False)
    else:
        need('all-finite-copy-witnesses', [p.get('countWitness') for p in wp.get('arrayPrograms', [])]
             == list(range(-1, limit+1)))
    tp = typed.get('proof', {})
    adapter = tp.get('adapter', {})
    need('own-canonical-value-default-and-callback', adapter.get('schema') == 'endfield.managed-value16-adapter-source.v1'
         and adapter.get('status') == 'proved-conditional-managed16-adapter'
         and adapter.get('nativeInputs') == pins and adapter.get('typeName') == TYPE
         and adapter.get('wrapperName') == WRAPPER and adapter.get('managedBytes') == 16
         and adapter.get('referenceLaneOffset') == 0 and adapter.get('canonicalCallbackAdmitted') is True
         and adapter.get('layout') == [dict(name=n, typeName=t, offset=o, managedBytes=w)
                                      for (n, t, o), w in zip(expected_curve, (8, 4, 4))]
         and tp.get('selectedCallbackEqualsCanonicalIsCondition') is True
         and tp.get('actualReaderRegisteredPointerEqualityInferred') is False)
    request = tp.get('typedRequest', {})
    need('actual-own-hidden-ReadValue-context', request.get('tag') == 6
         and request.get('typeName') == 'MemoryPack.MemoryPackReader'
         and request.get('methodName') == 'ReadValue' and request.get('classArguments') == []
         and request.get('methodArguments') == [TYPE] and len(request.get('methodSpec', [])) == 3
         and request['methodSpec'][0] == source.get('readerMethodDefinition'))
    # The actual frontend's matched dispatcher can have a separate entry from
    # the canonical adapter. Its identity belongs to the proved source body.
    paths = tp.get('dispatchPaths', [])
    need('all-matched-dispatcher-paths', len(paths) == 3
         and {(p.get('ff'), p.get('createWrapper')) for p in paths} == {(False, True), (False, False), (True, None)}
         and all(p.get('normalReturn') is True and p.get('entryRspRestored') is True
                 and p.get('managedOutputBytes') == 16
                 and p.get('defaultZeroBytes') == (16 if p.get('ff') is True else 0) for p in paths))
    actual_dispatch = tp.get('actualSourceWindows', {}).get('dispatch', [])
    need('literal-actual-dispatcher-window', bool(actual_dispatch)
         and type(actual_dispatch[0].get('startRva')) is int and actual_dispatch[0]['startRva'] > 0)
    dispatch = actual_dispatch[0]['startRva']
    cap = dict(typeName=TYPE, wrapperName=WRAPPER, memberCount=3, managedBytes=16,
        referenceLaneOffsets=[0], paddingByteRanges=[], nullable=True, nullMarker=255, nullWireBytes=1,
        nullReturnsDefaultValue=True, wireBytes=None, positiveWireBytes=None, orderedReads=ORDER,
        keyframeTypeName='Beyond.FKeyframe', keyframeBytes=32, elementHeaders=False,
        keyframeFields=[dict(fieldName=n, declaredType=t, wireOffset=i*4, bytes=4) for i, (n, t) in enumerate(KEY_FIELDS)],
        collectionCounts=[-1, 0], countLimit=limit, positiveCountsAdmitted=True, rawKeyCopyDomainProved=True,
        wholeGrammarAdmitted=True, ownConcreteGetterSemanticsProved=True, ownConcreteFactorySemanticsProved=True,
        actualValueReadValueAdmitted=True, ordinaryOriginalReadValueAdmitted=False,
        valueReaderMethodDefinition=source.get('readerMethodDefinition'), valueSourceTargetRva=source.get('sourceTargetRva'),
        valueDispatcherTargetRva=dispatch, callbackSelectionConditional=True, wholeOwnerAdmitted=False)
    require_capability(cap)
    return {CAPABILITY: cap}


def derive(image, pins, *, typed_request, source_target, count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.beyond_curve_value_sources import derive as source
    _publication_gate(image, pins)
    value = source(image, pins, typed_request=typed_request, source_target=source_target, count_limit=count_limit)
    capabilities = compose(pins, value)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.beyond-curve-value-components.v1',
        status='validated-conditional-beyond-curve-value-components', nativeInputs=pins, capabilities=capabilities,
        proof=dict(value=value), parentFieldAdmitted=False, wholeOwnerAdmitted=False)))
