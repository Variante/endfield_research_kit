"""Own AlphaBlend managed56 transfer and complete MC3/Beyond curve closure.

All wrapper paths, default56 and full copies are proved before this joins the
three serialized fields. The seven unserialized floats and padding are never
read from wire bytes. Parent local/setter/frame admission remains separate.
"""
import json
from scripts.game_data.memorypack.alpha_blend_value_sources import TYPE, WRAPPER
from scripts.game_data.memorypack.alpha_blend_value_codec import CAPABILITY, ORDER, require_capability
from scripts.game_data.memorypack.beyond_curve_value_components import compose as compose_curve
from scripts.game_data.memorypack.beyond_curve_value_codec import CAPABILITY as CURVE_CAPABILITY

SLICES = [[0, 16], [16, 16], [32, 16], [48, 8]]


def need(key, condition):
    if not condition:
        raise ValueError('alphaBlendValueComponents.' + key)


def compose(pins, transfer):
    need('own-current-hidden56-value-transfer', transfer.get('schema') == 'endfield.alpha-blend-value-transfer.v1'
         and transfer.get('status') == 'proved-conditional-alpha-blend-value56-read'
         and transfer.get('nativeInputs') == pins and transfer.get('typeName') == TYPE
         and transfer.get('wrapperName') == WRAPPER and transfer.get('managedBytes') == 56
         and transfer.get('resultAbi') == 'hidden-local' and transfer.get('actualSourceProved') is True
         and transfer.get('referenceLaneOffsets') == [8] and transfer.get('paddingByteRanges') == [[52, 56]]
         and transfer.get('wireGrammarAdmitted') is False and transfer.get('parentFieldAdmitted') is False
         and transfer.get('wholeOwnerAdmitted') is False)
    proof = transfer.get('proof', {})
    child = proof.get('childSource', {})
    need('own-complete-four-static-wrapper-paths', child.get('schema') == 'endfield.alpha-blend-wrapper-source.v1'
         and child.get('status') == 'proved-conditional-alpha-blend-wrapper-source'
         and child.get('nativeInputs') == pins and child.get('typeName') == TYPE
         and child.get('wrapperName') == WRAPPER and child.get('managedBytes') == 56
         and child.get('serializedMemberCount') == 3 and child.get('referenceLaneOffsets') == [8]
         and child.get('paddingByteRanges') == [[52, 56]]
         and child.get('completeStaticWrapperPathsProved') is True
         and child.get('canonicalAdapterAdmitted') is False)
    cp = child.get('proof', {})
    layout = cp.get('layout', {})
    expected_fields = [['_blendTime', 'float', 16],
                       ['_blendOption', 'Beyond.Gameplay.View.Animation.AlphaBlendOption', 20],
                       ['_customCurve', 'Beyond.FAnimationCurve', 24]] + [
        [n, 'float', o] for n, o in zip(('m_alphaLerp', 'm_alphaBlend', 'm_blendTimeRemaining',
            'm_blendedValue', 'm_beginValue', 'm_desiredValue', 'm_cachedDesiredBlendedValue'), range(40, 68, 4))]
    need('all-ten-own-fields-and-embedded-holder', type(layout.get('typeDefinition')) is int
         and layout['typeDefinition'] >= 0 and layout.get('fields') == expected_fields
         and layout.get('holder') == [WRAPPER, TYPE, 16])
    programs = cp.get('programs', [])
    positive = [p for p in programs if p.get('nullMarkerSelected') is False]
    nulls = [p for p in programs if p.get('nullMarkerSelected') is True]
    need('exact-static-positive-reuse-new-and-FF', len(programs) == 4 and len(positive) == len(nulls) == 2
         and {p.get('newWrapper') for p in positive} == {False, True}
         and all(p.get('headerBytes') == 1 and p.get('memberCount') == 3
                 and p.get('allFourHeaderReaderUpdatesProved') is True
                 and p.get('normalFrameAndNonvolatilesRestored') is True for p in programs)
         and all(p.get('serializedManagedSlices') == [[4, 4], [0, 4], [8, 16]]
                 and p.get('curveHiddenLocal') == dict(displacement=32, bytes=16)
                 and p.get('referenceBarrierPayloadOffset') == 8
                 and (p.get('freshDefaultPayloadBytes') == 56 if p.get('newWrapper') is True
                      else p.get('existingUnserializedStatePreserved') is True) for p in positive)
         and all(p.get('outputClearedBytes') == 8 and p.get('serializedManagedSlices') == [] for p in nulls))
    leaves = {row.get('method', [None, None, None])[2]: row for row in cp.get('leaves', [])}
    need('own-concrete-default-and-whole-getter', set(leaves) == {'.ctor', 'CreateInstance', 'GetValue'}
         and all(row.get('method', [None, None])[1] == WRAPPER for row in leaves.values())
         and all(leaves[n].get('program', {}).get('zeroedSlices') == SLICES
                 and leaves[n]['program'].get('completePayloadZeroed') is True for n in ('.ctor', 'CreateInstance'))
         and leaves['GetValue'].get('program', {}).get('sourceSlices') == SLICES
         and leaves['GetValue']['program'].get('completePayloadBitsCopied') is True
         and leaves['GetValue']['program'].get('returnsSameOutputRax') is True)
    for name, kind, result in (('enumSource', 'int32', 'eax'), ('singleSource', 'float32', 'xmm0-low32')):
        primitive = cp.get(name, {})
        need('complete-serialized-' + name, primitive.get('kind') == kind
             and primitive.get('wireBytes') == 4 and primitive.get('resultRegister') == result
             and all(primitive.get(k) is True for k in
                     ('completeBufferedProgram', 'entryRspRestored', 'nonvolatilesRestored')))
    curve = cp.get('curveSource', {})
    curve_caps = compose_curve(pins, curve)
    contexts = cp.get('contexts', [])
    need('own-distinct-enum-and-Beyond-contexts', len(contexts) == 2
         and [(c.get('fullTypeName'), c.get('methodOwner'), c.get('methodName'), c.get('register')) for c in contexts] == [
             ('Beyond.Gameplay.View.Animation.AlphaBlendOption', 'MemoryPack.MemoryPackReader', 'ReadUnmanaged', 'rdx'),
             ('Beyond.FAnimationCurve', 'MemoryPack.MemoryPackReader', 'ReadValue', 'r8')])
    curve_request = curve['proof']['typedSource']['proof']['typedRequest']
    need('exact-child-request-and-actual-source-binding', contexts[1].get('instructionRva') == curve_request.get('instructionRva')
         and contexts[1].get('methodSpec') == curve_request.get('methodSpec')
         and curve_caps[CURVE_CAPABILITY]['valueReaderMethodDefinition'] == curve_request['methodSpec'][0])
    reader = proof.get('readerProgram', {})
    need('whole-own-Reader-output-and-normal-frame', reader.get('managedBytes') == 56
         and reader.get('zeroedOutputSlices') == SLICES and reader.get('wireWidthAdmitted') is False
         and all(reader.get(k) is True for k in ('sameIncomingReaderAndHiddenOutput', 'sameOutputReturnedInRax',
             'initializedClosedContextRequired', 'matchingNonnullFormatterRequired', 'normalReturn',
             'entryRspRestored', 'allIntegerNonvolatilesRestored')))
    paths = proof.get('paths', {})
    for name in ('adapter', 'dispatch'):
        selected = paths.get(name, [])
        need('own-all-' + name + '-paths', len(selected) == 3
             and {(p.get('ff'), p.get('createWrapper')) for p in selected} == {(False, True), (False, False), (True, None)}
             and all(p.get('managedBytes') == 56 and p.get('dispatch') is (name == 'dispatch')
                     and p.get('defaultZeroBytes') == (56 if p.get('ff') is True else 0)
                     and all(p.get(k) is True for k in ('nullConsumptionDelegatedToOwnedReadIsNull',
                         'sameIncomingReaderAndHiddenOutput', 'entryRspRestored', 'normalReturn',
                         'callbackSelectionConditional')) for p in selected))
    nonnull = paths.get('nonnull', [])
    conversion = paths.get('conversion', {})
    need('own-whole-interface-copy-and-wrapper-null-default', len(nonnull) == 2
         and {p.get('wrapperNull') for p in nonnull} == {False, True}
         and all(p.get('managedBytes') == 56 and p.get('referenceBarrierOffset') == 8
                 and p.get('copiedSlices') == ([] if p.get('wrapperNull') is True else SLICES)
                 and p.get('defaultZeroBytes') == (56 if p.get('wrapperNull') is True else 0)
                 and p.get('conversionSelectorDxZero') is True and p.get('normalReturn') is True for p in nonnull)
         and conversion.get('managedBytes') == 56 and conversion.get('copiedSlices') == SLICES
         and all(conversion.get(k) is True for k in ('requiresIncomingDxZero', 'getterReturnsSameOutputPointer',
             'returnsSameIncomingHiddenOutput', 'normalReturn', 'entryRspRestored', 'allIntegerNonvolatilesRestored'))
         and proof.get('closedWrapperPointerEqualityInferred') is False
         and proof.get('runtimeSelectionObserved') is False)
    request = proof.get('typedRequest', {})
    need('actual-own-hidden56-request', request.get('tag') == 6
         and request.get('typeName') == 'MemoryPack.MemoryPackReader' and request.get('methodName') == 'ReadValue'
         and request.get('classArguments') == [] and request.get('methodArguments') == [TYPE]
         and len(request.get('methodSpec', [])) == 3
         and request['methodSpec'][0] == transfer.get('readerMethodDefinition'))
    dispatch = proof.get('symbolRvas', {}).get('dispatch')
    cap = dict(typeName=TYPE, wrapperName=WRAPPER, memberCount=3, managedBytes=56,
        referenceLaneOffsets=[8], paddingByteRanges=[[52, 56]], nullable=True, nullMarker=255, nullWireBytes=1,
        nullReturnsDefaultValue=True, wireBytes=None, positiveWireBytes=None, orderedReads=ORDER,
        wholeGrammarAdmitted=True, actualValueReadValueAdmitted=True, ordinaryOriginalReadValueAdmitted=False,
        ownConcreteGetterSemanticsProved=True, ownConcreteFactorySemanticsProved=True,
        unserializedStatePreservedOnWrapperReuse=True, callbackSelectionConditional=True,
        valueReaderMethodDefinition=transfer.get('readerMethodDefinition'), valueSourceTargetRva=transfer.get('sourceTargetRva'),
        valueDispatcherTargetRva=dispatch, wholeOwnerAdmitted=False)
    require_capability(cap)
    return dict(capabilities={CAPABILITY: cap, **curve_caps}, requiredExternalCapabilities=[],
                ownNestedCapabilities=[CURVE_CAPABILITY])


def derive(image, pins, *, typed_request, source_target, count_limit=10000):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.alpha_blend_value_transfer import derive as transfer_source
    _publication_gate(image, pins)
    transfer = transfer_source(image, pins, typed_request=typed_request, source_target=source_target, count_limit=count_limit)
    selected = compose(pins, transfer)
    _publication_gate(image, pins)
    return json.loads(json.dumps(dict(schema='endfield.alpha-blend-value-components.v1',
        status='validated-conditional-alpha-blend-value-components', nativeInputs=pins, **selected,
        proof=dict(transfer=transfer), parentFieldAdmitted=False, wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own actual managed56 Reader/default/canonical adapter/interface/GetValue joins all four MC3 wrapper paths, exact option/float helpers and the separately complete Beyond MC3/raw-key-array32 value grammar.',
            conditional=__doc__, structuralOnly='Stored blend configuration and raw key bits.',
            unresolved=['parent local/setter/frame', 'whole enclosing owner/EOF', 'live provider/callback selection', 'animation behavior']))))
