"""Join actual context calls and compatible class/record/pair declarations.

The caller supplies freshly checked complete programs. Equality of their
stored offsets is a static join; every actual receiver/class/table equality,
child effect and live method selection remains conditional or unresolved.
"""
LABEL = 'contextDispatchJoins'


def join_context_dispatch_programs(fallback, dispatch_contract, scan_contract, sources, dispatch_proof, scan_proof):
    required_dispatch = ('completeOwnedPrepareAndResolverControlChecked',
        'prepareActualPointerLoadAndTailTransferProved', 'resolverOriginalReceiverContextAndUInt16SelectorProved',
        'resolverNonnullFirstOrPermittedAlternateResultReturnedProved', 'resolverFailureCallFollowedByInt3Proved')
    required_scan = ('completeOwnedResolverCodeAndDataPartitionChecked',
        'allActualDirectAndIndirectTableTargetsChecked', 'zeroResultOnMissingContextOrRecordExhaustionProved')
    source_complete = (sources['selfPointer'].get('freshAllocationRaxStoredIntoItsOwnQwordProved') is True
        and sources['interfaceRecordCount'].get('namedInterfaceOffsetsCountCopiedToAllocationProved') is True
        and sources.get('storesDominateEveryNormalLocalReturn') is True)
    if not source_complete or not fallback.get('completeOwnedControlProved') or any(dispatch_proof.get(k) is not True for k in required_dispatch) or any(scan_proof.get(k) is not True for k in required_scan):
        raise ValueError(LABEL + '.complete-caller-child-programs-required')
    dc, rc = dispatch_contract, scan_contract
    checks = {
        'actual-prepare-call': (fallback['preparationCall']['targetRva'], dc['prepareEntryTransfer']['entryRva']),
        'actual-resolver-call': (fallback['resolverCall']['targetRva'], dc['programs']['resolver']['entryRva']),
        'actual-direct-search': (dc['calls']['resolverFirst'], rc['entryRva']),
        'actual-search-preparation': (rc['calls']['prepare'], dc['programs']['prepareTail']['entryRva']),
        'entry-preparation-self-offset': (dc['layout']['prepareArgumentPointer'], sources['selfPointer']['allocationByteOffset']),
        'search-preparation-self-offset': (rc['layout']['prepareArgumentPointer'], sources['selfPointer']['allocationByteOffset']),
        'caller-interface-record-count': (fallback['freshWordCountLoad']['receiverByteOffset'], sources['interfaceRecordCount']['allocationWordOffset']),
        'search-interface-record-count': (rc['layout']['recordCount'], sources['interfaceRecordCount']['allocationWordOffset']),
        'shared-record-array-offset': (rc['layout']['recordStorage'], fallback['freshArrayPointerLoad']['receiverByteOffset']),
        'shared-record-stride': (1 << rc['layout']['recordStrideShift'], fallback['scan']['recordStrideBytes']),
        'shared-record-offset-dword': (rc['layout']['recordOffsetWord'], fallback['matchedPairAddress']['offsetRecordByteOffset']),
        'shared-method-slot': (fallback['resolverCall']['r8d'], fallback['matchedPairAddress']['slot']),
        'search-pair-bias': (rc['layout']['pairBiasUnits'], fallback['matchedPairAddress']['bias']),
        'search-pair-shift': (rc['layout']['pairScaleShift'], fallback['matchedPairAddress']['shift']),
        'allocation-pair-bias': (sources['allocationRequest']['bias'], fallback['matchedPairAddress']['bias']),
        'allocation-pair-shift': (sources['allocationRequest']['shift'], fallback['matchedPairAddress']['shift']),
    }
    for name, (left, right) in checks.items():
        if left != right: raise ValueError(LABEL + '.'+name+': expected='+str(right)+' actual='+str(left))
    slot = fallback['resolverCall']['r8d']
    if type(slot) is not int or not 0 <= slot <= 0xffff:
        raise ValueError(LABEL + '.slot-unchanged-by-uint16-narrowing')
    return {'actualPreparationResolverAndDirectSearchTargetsJoined': True,
        'sharedSelfCountRecordAndPairDeclarationsJoined': True, 'slotUnchangedByBothChildUInt16Narrowings': True,
        'preparationEntry': {'classSelfPointerByteOffset': dc['layout']['prepareArgumentPointer'],
            'allocatedSelfSourceProved': sources['selfPointer']['freshAllocationRaxStoredIntoItsOwnQwordProved'],
            'normalLoadedPointerEqualsAllocationConditionalOnNoninterference': True},
        'resolverFirstSearch': {'query': 'captured comparison/interface QWORD', 'methodSlot': slot,
            'receiver': 'fresh first QWORD reloaded from original object inside resolver',
            'receiverEqualsOuterSavedClassProved': False,
            'queryParameterContextByteOffset': rc['layout']['parameterContext'],
            'nullQueryParameterContextReturnsZeroProved': True,
            'positivePathRetainsCompleteRecordParameterAndTableGuards': True},
        'resolverNormalOutcome': {'firstNonzeroResult': 'fresh direct-search RAX',
            'alternate': 'fresh alternate child RAX retained across actual continuation',
            'failure': 'actual failure helper followed by INT3',
            'failureIsZeroOrSafeNormalDefault': False},
        'childMutations': {'preparationSecondReceivesAddressOfSlotInitializedWithGlobalAddress': True,
            'subsequentPreparationThirdReloadsPotentiallyChangedSlot': True,
            'slotUnchangedProved': False, 'payloadWritesOrOtherChildEffectsProvedAbsent': False},
        'runtimePreparedClassInterfaceArrayPairIdentityProved': False,
        'preparationOrResolverEffectsAndTerminationProved': False,
        'wholeConditionExecutionProved': False, 'wholeRootAdmitted': False,
        'conditions': ['Coherent initialized compatible class/interface/record/pair state and stable object header.',
            'Allocated self/count match these receiver loads and remain unchanged by aliases or child calls.',
            'Readable storage, compatible normal child returns, and all original child conditions remain required.']}
