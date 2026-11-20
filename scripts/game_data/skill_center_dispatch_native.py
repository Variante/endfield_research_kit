"""Conditional shared FSM dispatch fragments; no live closed-instance selection.

Registers and opcodes form the semantic grammar. Build-specific displacements,
slots, stack layout, registrations and reviewed bytes live in the contract.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.game_data.il2cpp.formatter_composition import _vtable
from scripts.game_data.skill_pending_storage_native import _match
from scripts.game_data.skill_timing_runtime_native import _require

SCHEMA='endfield.skill-center-dispatch-native-contract.v9'
AUDIT_SCHEMA='endfield.skill-center-dispatch-native-audit.v9'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_dispatch_native.json'

def _same(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def _rules():return dict(originalPathOnly=True,normalWin64CallsRequired=True,
    switchFragmentStartsAtLookupReturn=True,lookupNullReturnsWithoutCallbacks=True,
    exitUsesRequestedStateIdBits32=True,exitPrecedesCurrentStore=True,
    currentReloadedAfterExit=True,currentReloadedAfterBarrier=True,
    oldAfterExitCheckedBeforeEnterTarget=True,oldIdReadAfterBothNullChecks=True,
    enterUsesOldAfterExitStateIdBits32=True,noFinalCurrentReadAfterEnter=True,
    genericInitializerNormalReturnRequired=True,opaqueVirtualDispatchRequired=True,
    enumVirtualFallbackPreservesReceiverAndId=True,enumVirtualFallbackUsesSelectedMethodInfo=True,
    enumVirtualFallbackRequiresThreeTargetMismatches=True,
    centerStateAndCanonicalStateIdSignedInt32=True,
    tickChecksRunningAtEntry=True,tickFirstTransitionDoesNotRecheckRunning=True,
    tickNullFirstTransitionRequestsStateUpdate=True,tickReloadsStateAfterUpdate=True,
    tickSecondTransitionRequiresRunningReload=True,tickNullCurrentBeforeFirstSelectionReturns=True,
    tickReachedNullStateForUpdateOrSecondSelectionIsExceptional=True,
    tickSelectorAndExecutorHelperEffectsRequired=True,
    transitionExecutorFragmentProved=True,transitionExitUsesInitialFromAndToId=True,
    transitionTargetReloadedAfterExitForStore=True,transitionFromAndToReloadedAfterBarrier=True,
    transitionNullablePostExitTargetStored=True,transitionEnterIsTailRequest=True,
    centerSkillOnEnterNominalFallbackTargetProved=True,
    actualVirtualTargetEqualsNamedMethodPointerRequired=True,
    addStateWritesTwoContextReferencesBeforeDictionaryRequest=True,
    addStateBarrierPreservesMachineCarrier=True,addStateReloadsSourceAfterFirstBarrier=True,
    addStateReadsIdAfterContextInitialization=True,addStateDictionaryAddIsTailRequest=True,
    addStateDictionaryEffectsRequired=True,lookupContainsFalseReturnsNull=True,lookupReloadsDictionaryAfterContains=True,
    lookupGetItemUsesOriginalIdBits32=True,lookupContainsAndGetItemEffectsRequired=True,
    conditionAbsentCheckerReturnsTrue=True,conditionFallbackRequiresThreeTargetMismatches=True,
    conditionFallbackForwardsStoredTargetAndMethodInfo=True,conditionActualDelegateTargetRequired=True,
    selectorLoopReturnsFirstTrueYieldedItem=True,selectorNullYieldedItemIsExceptional=True,
    selectorMoveNextFalseReturnsNull=True,selectorNullReceiverCannotReturnNormally=True,
    selectorInitializesEnumeratorListIndexVersionCurrent=True,
    moveNextComparesVersionBeforeUnsignedIndex=True,moveNextSuccessfulYieldIncrementsIndex=True,
    moveNextEndClearsCurrentAndSetsSizePlusOne=True,moveNextVersionMismatchIsExceptional=True,
    selectorInitializedEnumeratorCarrierRequired=False,staticProvidedContextDeclarationsProved=True,
    runtimeRgctxSlotsProved=False,transitionPrioritySortOrderProved=False,
    callbackReentrancyExcluded=False,currentPhysicalSlotNominalOwnershipProved=False,
    compiledClosedCenterMethodIdentityProved=False,liveReceiverTypeProved=False,
    selectedOnEnterActualCalleeProved=False,fullFSMDispatchProved=False,
    sameLiveWriterConsumerBlackboardProved=False)

def _registrations(image,rows):
    reg=image.registration;pe=image.pe;md=image.metadata
    code=image.mapper.code_registration_summary(pe,image.code_registration)
    table=int(reg['genericMethodTable'],16);specs=int(reg['methodSpecs'],16)
    pointers=int(code['genericMethodPointers'],16);seen={}
    expected={'switch':('Beyond.Gameplay.StateMachine`2','SwitchState'),
              'lookup':('Beyond.Gameplay.StateMachine`2','GetState'),
              'add':('Beyond.Gameplay.StateMachine`2','AddState'),
              'tick':('Beyond.Gameplay.StateMachine`2','Tick'),
              'executor':('Beyond.Gameplay.FSMTransition`1','Transit'),
              'selector':('Beyond.Gameplay.FSMState`1','CheckTransition'),
              'condition':('Beyond.Gameplay.FSMTransition`1','CheckCondition')}
    for row in rows:
        role=row['id'];_require(role in expected and role not in seen,'dispatch-registration-role',sorted(expected),role)
        ti=row['tableIndex'];si=row['methodSpecIndex'];pi=row['pointerIndex']
        _require(all(type(v)is int and v>=0 for v in (ti,si,pi))and ti<reg['genericMethodTableCount']and si<reg['methodSpecsCount']and pi<code['genericMethodPointersCount'],'dispatch-registration-bounds','bounded ordinary indices',row)
        actual=struct.unpack('<iiii',pe.bytes_at_va(table+ti*16,16))
        _require(actual[0]==si and actual[1]==pi,'dispatch-registration-row',(si,pi),actual)
        mi,ci,method_inst=struct.unpack('<iii',pe.bytes_at_va(specs+si*12,12))
        _require(0<=mi<len(md.methods)and ci>=0 and method_inst==-1,'dispatch-method-spec','class-only generic MethodSpec',(mi,ci,method_inst))
        m=md.methods[mi]
        # The method's declaring type is authenticated by the named type's range.
        td=image.named_types[expected[role][0]]
        _require(td.method_start<=mi<td.method_start+td.method_count and md.string(m.name_index)==expected[role][1]and mi==row['methodIndex'],'dispatch-method-owner',expected[role],(mi,md.string(m.name_index)))
        args=[runtime_type_name(pe,md,a.type_pointer_va)for a in image.instantiations.resolve(ci).arguments]
        rva=pe.u64_at_va(pointers+pi*8)-pe.image_base
        expected_args=['System.Int32Enum']if role in ('executor','selector','condition')else['System.Int32Enum','object']
        _require(args==expected_args and args==row['classArguments']and rva==row['entryRva'],'dispatch-canonical-shared-binding',row,dict(args=args,rva=rva))
        seen[role]=row
    _require(set(seen)==set(expected),'dispatch-registration-coverage',sorted(expected),sorted(seen));return seen

def _programs(c):
    h=bytes.fromhex;O=lambda k,w=1:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    programs={
      'switchLookupCall':[h('488b47'),O('methodInfoClassOffset'),h('8bd6488bcb4c8b80'),O('rgctxOffset',4),h('4d8b40'),O('lookupContextOffset'),h('e8'),R('lookupRva')],
      'switchAfterLookup':[h('488be84885c074'),R('switchReturnRva',1),h('488b53'),O('currentOffset'),h('4885d274'),R('switchNullRva',1),h('b9'),O('exitSlot',4),h('448bc6e8'),R('virtualEnumRva'),h('488b73'),O('currentOffset'),h('488d4b'),O('currentOffset'),h('48896b'),O('currentOffset'),h('e8'),R('barrierRva'),h('488b5b'),O('currentOffset'),h('4885f674'),R('switchNullRva',1)],
      'switchContext':[h('488b47'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b81'),O('stateContextOffset',4),h('488378'),O('initializerOffset'),h('000f84'),R('switchInitializerRva')],
      'switchEnter':[h('4885db74'),R('switchNullRva',1),h('448b46'),O('stateIdOffset'),h('b9'),O('enterSlot',4),h('488bd3e8'),R('virtualEnumRva')],
      'switchReturn':[h('488b5c24'),O('restoreRbx'),h('488b6c24'),O('restoreRbp'),h('488b7424'),O('restoreRsi'),h('4883c4'),O('frameSize'),h('5fc3')],
      'switchNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'switchInitializer':[h('488b47'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b81'),O('stateContextOffset',4),h('ff1090e9'),R('switchEnterRva')],
      'enumVirtualPrefix':[h('40535741574881ec'),O('virtualFrame',4),h('0fb7d9458bf8488b0a488bfae8'),R('classPrepareRva'),h('488b07488d4b'),O('vtablePairBase'),h('4803c94c8b0cc84c8b44c8'),O('vtableMethodInfoOffset'),h('488d05'),R('inlineTarget1'),h('4c3bc875'),R('enumCompare2Rva',1)],
      'enumCompare2':[h('488d05'),R('inlineTarget2'),h('4c3bc875'),R('enumCompare3Rva',1)],
      'enumCompare3':[h('488d05'),R('inlineTarget3'),h('4c3bc80f85'),R('enumFallbackRva')],
      'enumFallback':[h('418bd7488bcf41ffd14881c4'),O('virtualFrame',4),h('415f5f5bc3')],
    }
    mi=[h('488b47'),O('methodInfoClassOffset')]
    programs.update({
      'tickEntry':[h('48895c24'),O('tickSaveRbx'),h('574883ec'),O('tickFrame'),h('8079'),O('runningOffset'),h('00498bf80f297424'),O('tickSaveXmm6'),h('488bd90f28f10f84'),R('tickShortReturnRva'),h('488b51'),O('blackboardOffset'),h('4885d274'),R('tickFirstRva',1),h('b9'),O('blackboardTickSlot',4),h('0f28d1e8'),R('virtualFloatRva')],
      'tickFirst':[h('48837b'),O('currentOffset'),h('000f84'),R('tickShortReturnRva'),*mi,h('48896c24'),O('tickSaveRbp'),h('48897424'),O('tickSaveRsi'),h('488b73'),O('currentOffset'),h('488b90'),O('rgctxOffset',4),h('488b42'),O('selectorContextOffset'),h('488378'),O('initializerOffset'),h('000f84'),R('tickInitializeFirstRva'),*mi,h('488bce488b90'),O('rgctxOffset',4),h('488b52'),O('selectorContextOffset'),h('e8'),R('selectorRva'),h('488be84885c075'),R('tickExecuteFirstRva',1)],
      'tickUpdate':[h('488b53'),O('currentOffset'),h('4885d20f84'),R('tickNullRva'),h('b9'),O('stateUpdateSlot',4),h('0f28d6e8'),R('virtualFloatRva'),h('488b73'),O('currentOffset'),h('4885f60f84'),R('tickNullRva')],
      'tickSecond':[*mi,h('488b90'),O('rgctxOffset',4),h('488b42'),O('selectorContextOffset'),h('483968'),O('initializerOffset'),h('0f84'),R('tickInitializeSecondRva'),*mi,h('488bce488b90'),O('rgctxOffset',4),h('488b52'),O('selectorContextOffset'),h('e8'),R('selectorRva'),h('807b'),O('runningOffset'),h('00488bf074'),R('tickReturnRva',1),h('4885c075'),R('tickExecuteSecondRva',1)],
      'tickReturn':[h('488b6c24'),O('tickSaveRbp'),h('488b7424'),O('tickSaveRsi')],
      'tickShortReturn':[h('488b5c24'),O('tickRestoreRbx'),h('0f287424'),O('tickSaveXmm6'),h('4883c4'),O('tickFrame'),h('5fc3')],
      'tickExecuteFirst':[*mi,h('488b88'),O('rgctxOffset',4),h('488b41'),O('executorContextOffset'),h('488378'),O('initializerOffset'),h('000f84'),R('tickInitializeExecuteFirstRva'),h('488bcd'),*mi,h('488d53'),O('currentOffset'),h('4c8b80'),O('rgctxOffset',4),h('4d8b40'),O('executorContextOffset'),h('e8'),R('executorRva'),h('eb'),R('tickReturnRva',1)],
      'tickExecuteSecond':[h('488b4f'),O('methodInfoClassOffset'),h('488b91'),O('rgctxOffset',4),h('488b4a'),O('executorContextOffset'),h('488379'),O('initializerOffset'),h('000f84'),R('tickInitializeExecuteSecondRva'),h('488bceeb'),R('tickSharedExecuteRva',1)],
      'tickNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'tickInitializeFirst':[*mi,h('488b90'),O('rgctxOffset',4),h('488b42'),O('selectorContextOffset'),h('ff1090e9'),R('tickFirstCallPrepRva')],
      'tickInitializeSecond':[*mi,h('488b90'),O('rgctxOffset',4),h('488b42'),O('selectorContextOffset'),h('ff1090e9'),R('tickSecondCallPrepRva')],
      'tickInitializeExecuteFirst':[*mi,h('488b88'),O('rgctxOffset',4),h('488b41'),O('executorContextOffset'),h('ff1090e9'),R('tickFirstExecutePrepRva')],
      'tickInitializeExecuteSecond':[h('488b4f'),O('methodInfoClassOffset'),h('488b91'),O('rgctxOffset',4),h('488b42'),O('executorContextOffset'),h('ff1090e9'),R('tickSecondExecutePrepRva')],
    })
    programs.update({
      'selectorEntry':[h('48895424'),O('selectorSaveMethodInfo'),h('534883ec'),O('selectorFrame'),h('0f57c033c00f114424'),O('selectorEnumLocal'),h('48894424'),O('selectorCurrentLocal'),h('488b59'),O('stateTransitionsOffset'),h('4885db0f84'),R('selectorListNullRva')],
      'selectorLoop':[h('488b4424'),O('selectorMethodInfoLocal'),h('488b48'),O('methodInfoClassOffset'),h('488b91'),O('rgctxOffset',4),h('488b52'),O('moveNextContextOffset'),h('488d4c24'),O('selectorEnumLocal'),h('e8'),R('moveNextRva'),h('84c074'),R('selectorNoMoreRva',1),h('488b5c24'),O('selectorCurrentLocal'),h('4885db74'),R('selectorItemNullRva',1),h('488b5424'),O('selectorMethodInfoLocal'),h('488b42'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('conditionContextOffset'),h('488378'),O('initializerOffset'),h('0075'),R('selectorConditionPrepRva',1),h('488b42'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('conditionContextOffset'),h('ff10488b5424'),O('selectorMethodInfoLocal'),h('488b42'),O('methodInfoClassOffset'),h('488b90'),O('rgctxOffset',4),h('488b52'),O('conditionContextOffset'),h('488bcbe8'),R('conditionRva'),h('84c074'),R('selectorLoopRva',1)],
      'selectorFound':[h('488bc34883c4'),O('selectorFrame'),h('5bc3')],
      'selectorNoMore':[h('eb'),R('selectorNullReturnRva',1)],
      'selectorNullReturn':[h('33c04883c4'),O('selectorFrame'),h('5bc3')],
      'selectorListNull':[h('e8'),R('nullHelperRva'),h('90')],
      'selectorItemNull':[h('e8'),R('selectorNullItemHelperRva'),h('90')],
      'selectorCleanup':[h('e8'),R('selectorCleanupHelperRva'),h('cc')],
    })
    programs.update({
      'executorEntry':[h('48895c24'),O('executorSaveRbx'),h('48896c24'),O('executorSaveRbp'),h('48897424'),O('executorSaveRsi'),h('48897c24'),O('executorSaveRdi'),h('41564883ec'),O('executorFrame'),h('488b79'),O('transitionToOffset'),h('498bf0488b69'),O('transitionFromOffset'),h('4c8bf2488bd94885ff0f84'),R('executorNullRva'),h('498b40'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('transitionTypeContextOffset'),h('488378'),O('initializerOffset'),h('000f84'),R('executorInitializeFirstRva')],
      'executorExit':[h('4885ed74'),R('executorNullRva',1),h('448b47'),O('stateIdOffset'),h('b9'),O('exitSlot',4),h('488bd5e8'),R('virtualEnumRva'),h('488b43'),O('transitionToOffset'),h('498bce498906e8'),R('barrierRva'),h('488b7b'),O('transitionToOffset'),h('488b5b'),O('transitionFromOffset'),h('4885db74'),R('executorNullRva',1),h('488b46'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('transitionTypeContextOffset'),h('488378'),O('initializerOffset'),h('000f84'),R('executorInitializeSecondRva')],
      'executorEnter':[h('4885ff74'),R('executorNullRva',1),h('448b43'),O('stateIdOffset'),h('b9'),O('enterSlot',4),h('488bd7488b5c24'),O('executorRestoreRbx'),h('488b6c24'),O('executorRestoreRbp'),h('488b7424'),O('executorRestoreRsi'),h('488b7c24'),O('executorRestoreRdi'),h('4883c4'),O('executorFrame'),h('415ee9'),R('virtualEnumRva')],
      'executorNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'executorInitializeFirst':[h('498b40'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('transitionTypeContextOffset'),h('ff1090e9'),R('executorExitRva')],
      'executorInitializeSecond':[h('488b46'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('transitionTypeContextOffset'),h('ff1090e9'),R('executorEnterRva')],
    })
    programs.update({
      'lookupEntry':[h('48895c24'),O('lookupSaveRbx'),h('48896c24'),O('lookupSaveRbp'),h('48897424'),O('lookupSaveRsi'),h('574883ec'),O('frameSize'),h('488b71'),O('dictionaryOffset'),h('498bd88bea488bf94885f60f84'),R('lookupNullRva'),h('498b40'),O('methodInfoClassOffset'),h('4c8b80'),O('rgctxOffset',4),h('498b80'),O('containsContextOffset',4),h('488378'),O('initializerOffset'),h('000f84'),R('lookupInitContainsRva')],
      'lookupContains':[h('488b43'),O('methodInfoClassOffset'),h('8bd5488bce4c8b80'),O('rgctxOffset',4),h('4d8b80'),O('containsContextOffset',4),h('e8'),R('containsRva'),h('84c074'),R('lookupFalseRva',1),h('488b7f'),O('dictionaryOffset'),h('4885ff74'),R('lookupNullRva',1),h('488b43'),O('methodInfoClassOffset'),h('488b90'),O('rgctxOffset',4),h('488b82'),O('itemContextOffset',4),h('488378'),O('initializerOffset'),h('000f84'),R('lookupInitItemRva')],
      'lookupItem':[h('488b43'),O('methodInfoClassOffset'),h('8bd5488bcf4c8b80'),O('rgctxOffset',4),h('4d8b80'),O('itemContextOffset',4),h('e8'),R('itemRva')],
      'lookupReturn':[h('488b5c24'),O('restoreRbx'),h('488b6c24'),O('restoreRbp'),h('488b7424'),O('restoreRsi'),h('4883c4'),O('frameSize'),h('5fc3')],
      'lookupNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'lookupFalse':[h('33c0eb'),R('lookupReturnRva',1)],
      'lookupInitContains':[h('488b43'),O('methodInfoClassOffset'),h('488b90'),O('rgctxOffset',4),h('488b82'),O('containsContextOffset',4),h('ff1090e9'),R('lookupContainsRva')],
      'lookupInitItem':[h('488b43'),O('methodInfoClassOffset'),h('488b90'),O('rgctxOffset',4),h('488b82'),O('itemContextOffset',4),h('ff1090e9'),R('lookupItemRva')],
      'conditionEntry':[h('4883ec'),O('conditionFrame'),h('488379'),O('checkerOffset'),h('000f84'),R('conditionTrueRva'),h('488b42'),O('methodInfoClassOffset'),h('48895c24'),O('conditionSaveRbx'),h('488b59'),O('checkerOffset'),h('48897c24'),O('conditionSaveRdi'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('checkerContextOffset'),h('488378'),O('initializerOffset'),h('000f84'),R('conditionInitRva')],
      'conditionDispatch':[h('488b43'),O('delegatePointerOffset'),h('488d0d'),R('conditionInline1'),h('488b53'),O('delegateMethodInfoOffset'),h('488b7b'),O('delegateTargetOffset'),h('48896c24'),O('conditionSaveRbp'),h('48897424'),O('conditionSaveRsi'),h('483bc174'),R('conditionInlineBranch1',1),h('488d0d'),R('conditionInline2'),h('483bc10f84'),R('conditionInlineBranch2'),h('488d0d'),R('conditionInline3'),h('483bc10f84'),R('conditionInlineBranch3'),h('488bcfffd0')],
      'conditionRestore':[h('488b7424'),O('conditionSaveRsi'),h('488b6c24'),O('conditionSaveRbp'),h('488b5c24'),O('conditionSaveRbx'),h('488b7c24'),O('conditionSaveRdi')],
      'conditionReturn':[h('4883c4'),O('conditionFrame'),h('c3')],
      'conditionTrue':[h('b001e9'),R('conditionReturnRva')],
      'conditionInit':[h('488b42'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('checkerContextOffset'),h('ff1090e9'),R('conditionDispatchRva')],
    })
    programs.update({
      'addEntry':[h('48895c24'),O('lookupSaveRbx'),h('48896c24'),O('lookupSaveRbp'),h('48897424'),O('lookupSaveRsi'),h('574883ec'),O('frameSize'),h('488b41'),O('machineContext1Offset'),h('498bf8488bda4c8bd14885d20f84'),R('addNullRva'),h('488d4a'),O('stateContext1Offset'),h('488942'),O('stateContext1Offset'),h('e8'),R('barrierRva'),h('4d8b4a'),O('machineContext2Offset'),h('488d4b'),O('stateContext2Offset'),h('4c894b'),O('stateContext2Offset'),h('e8'),R('barrierRva'),h('488b47'),O('methodInfoClassOffset'),h('498b72'),O('dictionaryOffset'),h('488b88'),O('rgctxOffset',4),h('488b81'),O('addStateTypeContextOffset',4),h('488378'),O('initializerOffset'),h('000f84'),R('addInitStateRva')],
      'addReadId':[h('8b6b'),O('stateIdOffset'),h('4885f674'),R('addNullRva',1),h('488b47'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b81'),O('addContextOffset',4),h('488378'),O('initializerOffset'),h('000f84'),R('addInitDictionaryRva')],
      'addTail':[h('488b47'),O('methodInfoClassOffset'),h('4c8bc38bd5488bce4c8b88'),O('rgctxOffset',4),h('4d8b89'),O('addContextOffset',4),h('488b5c24'),O('restoreRbx'),h('488b6c24'),O('restoreRbp'),h('488b7424'),O('restoreRsi'),h('4883c4'),O('frameSize'),h('5fe9'),R('dictionaryAddRva')],
      'addNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'addInitState':[h('488b47'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b81'),O('addStateTypeContextOffset',4),h('ff1090e9'),R('addReadIdRva')],
      'addInitDictionary':[h('488b47'),O('methodInfoClassOffset'),h('4c8b80'),O('rgctxOffset',4),h('498b80'),O('addContextOffset',4),h('ff1090e9'),R('addTailRva')],
    })
    programs.update({
      'selectorInitContext':[h('488b42'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('enumeratorContextOffset'),h('488378'),O('initializerOffset'),h('0075'),R('selectorInitLocalRva',1),h('488b42'),O('methodInfoClassOffset'),h('488b88'),O('rgctxOffset',4),h('488b41'),O('enumeratorContextOffset'),h('ff10')],
      'selectorInitLocal':[h('0f57c0f30f7f4424'),O('selectorTempIndex'),h('48895c24'),O('selectorTempList'),h('833d'),R('selectorBarrierEnabledRelativeEnd'),h('0074'),R('selectorInitFieldsRva',1)],
      'selectorInitBarrier':[h('4c8d4424'),O('selectorTempList'),h('49c1e80c4181e0ffff1f00418bc048c1e806488d0d'),R('selectorBitmapBase'),h('488d14c14183e03f0f0d0a0f1f00488b02488bc84c0fabc1f0480fb10a75'),R('selectorBarrierLoopRva',1)],
      'selectorInitFields':[h('33c9894c24'),O('selectorTempIndex'),h('4885db0f84'),R('selectorInitNullRva'),h('8b43'),O('listVersionOffset'),h('894424'),O('selectorTempVersion'),h('33c048894424'),O('selectorTempCurrent'),h('0f104424'),O('selectorTempList'),h('0f114424'),O('selectorEnumLocal'),h('f20f104c24'),O('selectorTempCurrent'),h('f20f114c24'),O('selectorCurrentLocal'),h('48894c24'),O('selectorTempList'),h('488d4424'),O('selectorEnumLocal'),h('48894424'),O('selectorTempIndex'),h('488d4424'),O('selectorMethodInfoLocal'),h('48894424'),O('selectorTempCurrent'),h('0f1f00')],
      'selectorInitNull':[h('e8'),R('selectorNullItemHelperRva'),h('cc')],
      'moveNextEntry':[h('48895c24'),O('moveSaveRbx'),h('48896c24'),O('moveSaveRbp'),h('48897424'),O('moveSaveRsi'),h('574883ec'),O('moveFrame'),h('488b39488bd98b71'),O('enumVersionOffset'),h('4885ff0f84'),R('moveNextNullRva'),h('3b77'),O('listVersionOffset'),h('0f85'),R('moveNextSlowRva'),h('8b47'),O('listSizeOffset'),h('3941'),O('enumIndexOffset'),h('0f83'),R('moveNextSlowRva'),h('488b7f'),O('listItemsOffset'),h('486371'),O('enumIndexOffset'),h('4885ff0f84'),R('moveNextItemsNullRva'),h('3b77'),O('arrayLengthOffset'),h('0f83'),R('moveNextBoundsRva'),h('833d'),R('moveBarrierEnabledRelativeEnd'),h('00488b44f7'),O('arrayDataOffset'),h('488941'),O('enumCurrentOffset'),h('74'),R('moveNextIncrementRva',1)],
      'moveNextBarrier':[h('4c8d41'),O('enumCurrentOffset'),h('49c1e80c488d0d'),R('moveBitmapBase'),h('4181e0ffff1f00418bc048c1e8064183e03f488d14c10f0d0a90488b02488bc84c0fabc1f0480fb10a75'),R('moveBarrierLoopRva',1)],
      'moveNextIncrement':[h('ff43'),O('enumIndexOffset'),h('b001')],
      'moveNextReturn':[h('488b5c24'),O('moveRestoreRbx'),h('488b6c24'),O('moveRestoreRbp'),h('488b7424'),O('moveRestoreRsi'),h('4883c4'),O('moveFrame'),h('5fc3')],
      'moveNextSlow':[h('488b4a'),O('methodInfoClassOffset'),h('f681'),O('moveClassFlagOffset',4),h('0175'),R('moveNextRecheckRva',1),h('e8'),R('moveClassPrepareRva')],
      'moveNextRecheck':[h('488b034885c074'),R('moveNextSlowNullRva',1),h('8b40'),O('listVersionOffset'),h('3943'),O('enumVersionOffset'),h('75'),R('moveNextVersionFailureRva',1),h('488b038b48'),O('listSizeOffset'),h('ffc133c0894b'),O('enumIndexOffset'),h('488943'),O('enumCurrentOffset'),h('eb'),R('moveNextReturnRva',1)],
      'moveNextSlowNull':[h('e8'),R('selectorNullItemHelperRva'),h('cc')],
      'moveNextNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'moveNextItemsNull':[h('e8'),R('nullHelperRva'),h('cc')],
      'moveNextBounds':[h('e8'),R('moveBoundsHelperRva'),h('cc')],
      'moveNextVersionFailure':[h('33c9e8'),R('moveVersionHelperRva'),h('cc')],
    })
    return programs

def _validate(image,c):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    cx=NativeReferenceContext(image)
    enums=['System.Int32Enum','Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterState']
    _require(c['stateIdEnums']==enums,'dispatch-state-id-enums',enums,c['stateIdEnums'])
    for name in enums:
        fields=[f for f in image.metadata.fields_for(image.named_types[name])if image.metadata.string(f.name_index)=='value__']
        _require(len(fields)==1 and cx.type_name(fields[0].type_index)=='int','dispatch-state-id-backing','sole signed Int32 backing',name)
        cx.require_ordinary_kind(fields[0].type_index,8)
    declarations={'OnEnter':4,'OnLeave':5,'OnUpdate':6}
    td=image.named_types['Beyond.Gameplay.FSMState`1']
    for name,slot in declarations.items():
        found=[m for m in image.metadata.methods[td.method_start:td.method_start+td.method_count]if image.metadata.string(m.name_index)==name]
        _require(len(found)==1 and found[0].slot==slot,'dispatch-nominal-state-slot',dict(name=name,slot=slot),[m.slot for m in found])
    cb=c['skillOnEnter'];owner='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterSkillState'
    _require(cb['identity'][1:3]==[owner,'OnEnter']and type(cb['slot'])is int and cb['slot']==4,'dispatch-skill-enter-role','concrete CenterSkillState.OnEnter slot4',cb)
    index=image.validate_method_row(cb['identity'],label='skillCenterDispatch')
    _require(image.metadata.methods[index].slot==4,'dispatch-skill-enter-slot',4,image.metadata.methods[index].slot)
    _vtable(image,image.named_types[owner].index,4,index,'skillCenterDispatch')
    rows=_registrations(image,c['registrations']);image.check_windows(c['codeWindows'],label='skillCenterDispatch')
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols,validate_claims
    context_roles={'Beyond.Gameplay.StateMachine`2':{5:('Beyond.Gameplay.StateMachine`2','GetState'),9:('Beyond.Gameplay.FSMState`1','CheckTransition'),11:('Beyond.Gameplay.FSMTransition`1','Transit'),25:('System.Collections.Generic.Dictionary`2','Add'),26:('System.Collections.Generic.Dictionary`2','ContainsKey'),27:('System.Collections.Generic.Dictionary`2','get_Item')},'Beyond.Gameplay.FSMState`1':{10:('System.Collections.Generic.List`1','GetEnumerator'),13:('Beyond.Gameplay.FSMTransition`1','CheckCondition'),14:('System.Collections.Generic.List`1+Enumerator','MoveNext')},'Beyond.Gameplay.FSMTransition`1':{1:('Beyond.Gameplay.FSMState`1','GetStateId'),3:('Beyond.Gameplay.FSMTransition`1+ConditionChecker','Invoke')}}
    _require(len(c['contextClaims'])==len(context_roles)and {r['typeName']for r in c['contextClaims']}==set(context_roles),'dispatch-context-coverage','selected nominal class contexts',c['contextClaims'])
    symbols=ContextSymbols(image)
    for claim in c['contextClaims']:
        owner=claim['typeName'];slots=sorted(context_roles[owner]);actual=symbols.context(image.named_types[owner].index,slots=slots)
        validate_claims(claim,actual,label='skillCenterDispatch.staticContext')
        _require(len(actual['entries'])==len(slots)and [(r['relativeSlot'],r['kind'],r['typeName'],r.get('methodName'))for r in actual['entries']]==[(s,3,*context_roles[owner][s])for s in slots],'dispatch-context-nominal-role',context_roles[owner],actual['entries'])
    owners={role:row['entryRva']for role,row in rows.items()};owners['enumVirtual']=c['operands']['virtualEnumRva'];owners['moveNext']=c['operands']['moveNextRva']
    for role,entry in owners.items():
        actual=[x['runtimeTriple'][:2]for x in image.unwind_index.family(entry)['ranges']]
        expected=[[w['startRva'],w['endRva']]for w in c['codeWindows']if w['owner']==role]
        _require(actual==expected,'dispatch-window-ownership',actual,expected)
    op=c['operands'];_require(all(type(v)is int for v in op.values()),'dispatch-operands','ordinary integer operands',op)
    spans={r['id']:r for r in c['spans']};programs=_programs(c)
    _require(len(spans)==len(c['spans'])and set(spans)==set(programs),'dispatch-program-coverage',sorted(programs),sorted(spans))
    targets=dict(op);raws={}
    for key,r in spans.items():
        raw=bytes.fromhex(r['hex']);end=r['rva']+len(raw)
        cursor=r['rva']
        for a,b in sorted((w['startRva'],w['endRva'])for w in c['codeWindows']if w['owner']==r['owner']):
            if a<=cursor<b:cursor=min(b,end)
        _require(cursor==end and r['owner']==('enumVirtual'if key.startswith('enum')else'tick'if key.startswith('tick')else'executor'if key.startswith('executor')else'selector'if key.startswith('selector')else'lookup'if key.startswith('lookup')else'condition'if key.startswith('condition')else'add'if key.startswith('add')else'moveNext'if key.startswith('moveNext')else'switch'),'dispatch-span-owner','selected physical family',r)
        _require(image.pe.bytes_at_va(image.pe.image_base+r['rva'],len(raw))==raw and _match(raw,r['rva'],programs[key],{},op,targets),'dispatch-semantic-program',key,raw.hex());raws[key]=raw
    chain=['switchAfterLookup','switchContext','switchEnter','switchReturn','switchNull']
    for left,right in zip(chain,chain[1:]):_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-contiguous-edge',left,right)
    for key in ['switchEnter','switchReturn','switchNull','switchInitializer']:_require(op[key+'Rva']==spans[key]['rva'],'dispatch-branch-target',key,op)
    _require(op['lookupRva']==rows['lookup']['entryRva']and spans['switchLookupCall']['rva']+len(raws['switchLookupCall'])==spans['switchAfterLookup']['rva'],'dispatch-lookup-join','canonical lookup returns to selected fragment',rows)
    _require(op['exitSlot']==5 and op['enterSlot']==4,'dispatch-virtual-slot-role','Exit slot5/Enter slot4',op)
    _require(cb['identity'][3]not in [op[k]for k in ['inlineTarget1','inlineTarget2','inlineTarget3']],'dispatch-skill-enter-fallback','named original method pointer reaches fallback',cb)
    for key in ['enumCompare2','enumCompare3','enumFallback']:_require(op[key+'Rva']==spans[key]['rva'],'dispatch-virtual-edge',key,op)
    _require(spans['enumVirtualPrefix']['rva']==op['virtualEnumRva']and op['vtablePairBase']*16==c['physicalVtable']['baseOffset']and op['vtableMethodInfoOffset']==c['physicalVtable']['methodInfoOffset']and type(c['physicalVtable']['stride'])is int and c['physicalVtable']['stride']==16,'dispatch-virtual-layout','selected physical class vtable pair indexing',op)
    chain=['tickEntry','tickFirst','tickUpdate','tickSecond','tickReturn','tickShortReturn','tickExecuteFirst','tickExecuteSecond','tickNull']
    for left,right in zip(chain,chain[1:]):_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-tick-contiguous-edge',left,right)
    for key in chain+['tickInitializeFirst','tickInitializeSecond','tickInitializeExecuteFirst','tickInitializeExecuteSecond']:_require(op[key+'Rva']==spans[key]['rva'],'dispatch-tick-branch-target',key,op)
    _require(spans['tickEntry']['rva']==rows['tick']['entryRva']and op['stateUpdateSlot']==declarations['OnUpdate'],'dispatch-tick-entry-slot','canonical tick entry and update slot',op)
    _require(spans['executorEntry']['rva']==rows['executor']['entryRva']==op['executorRva'],'dispatch-executor-entry','canonical transition overload',rows['executor'])
    _require(rows['selector']['entryRva']==op['selectorRva'],'dispatch-selector-callee','canonical FSMState.CheckTransition',rows['selector'])
    _require(rows['condition']['entryRva']==op['conditionRva']and spans['selectorEntry']['rva']==op['selectorRva'],'dispatch-selector-condition-entry','canonical selector/condition entries',rows)
    for key in ['selectorLoop','selectorNoMore','selectorNullReturn','selectorListNull','selectorItemNull']:_require(spans[key]['rva']==op[key+'Rva'],'dispatch-selector-branch-target',key,op)
    _require(spans['selectorLoop']['rva']+len(raws['selectorLoop'])==spans['selectorFound']['rva']and spans['selectorFound']['rva']+len(raws['selectorFound'])==spans['selectorNoMore']['rva'],'dispatch-selector-loop-edge','first true returns saved yielded item',spans['selectorLoop'])
    for left,right in [('selectorListNull','selectorItemNull'),('selectorItemNull','selectorCleanup')]:_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-selector-exception-edge',left,right)
    for left,right in [('executorEntry','executorExit'),('executorExit','executorEnter'),('executorEnter','executorNull')]:_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-executor-contiguous-edge',left,right)
    for key in ['executorExit','executorEnter','executorNull','executorInitializeFirst','executorInitializeSecond']:_require(spans[key]['rva']==op[key+'Rva'],'dispatch-executor-branch-target',key,op)
    for prefix,entry in [('lookup','lookupRva'),('condition','conditionRva')]:
        _require(spans[prefix+'Entry']['rva']==op[entry],'dispatch-extra-entry',prefix,op[entry])
    for chain in [['lookupEntry','lookupContains','lookupItem','lookupReturn','lookupNull','lookupFalse'],['conditionEntry','conditionDispatch','conditionRestore','conditionReturn']]:
        for left,right in zip(chain,chain[1:]):_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-extra-contiguous-edge',left,right)
    for key in ['lookupNull','lookupFalse','lookupReturn','lookupInitContains','lookupInitItem','lookupContains','lookupItem','conditionTrue','conditionInit','conditionDispatch','conditionReturn']:
        _require(spans[key]['rva']==op[key+'Rva'],'dispatch-extra-branch-target',key,op[key+'Rva'])
    _require(spans['addEntry']['rva']==rows['add']['entryRva'],'dispatch-add-entry','canonical AddState',rows['add'])
    for left,right in [('addEntry','addReadId'),('addReadId','addTail'),('addTail','addNull')]:
        _require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-add-contiguous-edge',left,right)
    for key in ['addNull','addReadId','addTail','addInitState','addInitDictionary']:
        _require(spans[key]['rva']==op[key+'Rva'],'dispatch-add-branch-target',key,op[key+'Rva'])
    init_chain=['selectorEntry','selectorInitContext','selectorInitLocal','selectorInitBarrier','selectorInitFields','selectorLoop']
    move_chain=['moveNextEntry','moveNextBarrier','moveNextIncrement','moveNextReturn','moveNextSlow','moveNextRecheck','moveNextSlowNull','moveNextNull','moveNextItemsNull','moveNextBounds','moveNextVersionFailure']
    for chain in [init_chain,move_chain]:
        for left,right in zip(chain,chain[1:]):_require(spans[left]['rva']+len(raws[left])==spans[right]['rva'],'dispatch-enumerator-contiguous-edge',left,right)
    for key in ['selectorInitLocal','selectorInitFields','selectorInitNull']+move_chain[2:]:
        _require(spans[key]['rva']==op[key+'Rva'],'dispatch-enumerator-branch-target',key,op[key+'Rva'])
    _require(spans['moveNextEntry']['rva']==op['moveNextRva'],'dispatch-enumerator-entry','selected direct MoveNext',op)
    _require(op['selectorTempIndex']==op['selectorTempList']+op['enumIndexOffset']and op['selectorTempVersion']==op['selectorTempList']+op['enumVersionOffset']and op['selectorTempCurrent']==op['selectorTempList']+op['enumCurrentOffset']and op['selectorCurrentLocal']==op['selectorEnumLocal']+op['enumCurrentOffset'],'dispatch-enumerator-carrier-layout','same copied list/index/version/current carrier',op)
    expected_bindings=[]
    roles=[('switchLookup','switchLookupCall','lookupRva',None),('switchExitRequest','switchAfterLookup','virtualEnumRva',5),('switchEnterRequest','switchEnter','virtualEnumRva',4),('tickBlackboardRequest','tickEntry','virtualFloatRva',None),('tickFirstSelector','tickFirst','selectorRva',None),('tickStateUpdateRequest','tickUpdate','virtualFloatRva',None),('tickSecondSelector','tickSecond','selectorRva',None),('tickTransitionRequest','tickExecuteFirst','executorRva',None)]
    for role,key,target,slot in roles:
        cursor=spans[key]['rva'];previous=None;sites=[]
        for part in programs[key]:
            if isinstance(part,bytes):cursor+=len(part);previous=part[-1]if part else previous
            else:
                kind,name,width=part
                if kind=='relative'and name==target and previous==0xe8:sites.append(cursor-1)
                cursor+=width;previous=None
        _require(len(sites)==1,'dispatch-callsite-consumption',role,sites)
        binding=dict(role=role,callRva=sites[0],returnRva=sites[0]+5,targetRva=op[target])
        if slot is not None:binding['virtualSlot']=slot
        expected_bindings.append(binding)
    _require(_same(c['callerBindings'],expected_bindings),'dispatch-caller-bindings',expected_bindings,c['callerBindings'])
    _require(_same(c['rules'],_rules()),'dispatch-rules',_rules(),c['rules']);return _rules()

def _call_sites(c):
    """Derive indirect call ends only after the selected semantic programs pass."""
    spans={r['id']:r for r in c['spans']}
    span=spans['conditionDispatch'];raw=bytes.fromhex(span['hex'])
    _require(raw.endswith(bytes.fromhex('488bcfffd0')),'dispatch-condition-fallback-call','mov rcx,rdi; call rax',raw[-5:].hex())
    end=span['rva']+len(raw)
    return [dict(role='conditionDelegateFallback',callRva=end-2,returnRva=end,
        callHex=raw[-2:].hex(),callKind='indirect',target='stored delegate pointer',
        receiver='stored delegate target',methodInfo='stored delegate MethodInfo',
        boundary='Selected original CheckCondition fallback call; actual delegate identity requires observed callee evidence.')]

def load_skill_center_dispatch(contract_path=CONTRACT_PATH,*,gameassembly=None,metadata=None):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],nativeInputs={},failures=[],callSites=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillCenterDispatch');pins=c['nativeInputs'];gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        image=open_native_image(gate.gameassembly,gate.metadata)
        from scripts.game_data import skill_center_lifecycle_native as lifecycle
        dep_path=CONTRACTS_DIR/'skill_center_lifecycle_native.json'
        dep,dep_digest=read_reviewed_contract(dep_path,schema=lifecycle.SCHEMA,status='reviewed',label='skillCenterDispatch.barrier')
        _require(_same(dep['nativeInputs'],pins),'dispatch-barrier-native-inputs','same selected build',dep['nativeInputs'])
        image.check_windows(dep['codeWindows'],label='skillCenterDispatch.barrier')
        barrier=lifecycle._programs(dep)
        _require(barrier['barrierEntryRva']==c['operands']['barrierRva']and lifecycle._rules()['barrierPreservesR10R11']is True,'dispatch-add-barrier-join','proved same barrier preserves R10',barrier)
        rules=_validate(image,c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest and hashlib.sha256(dep_path.read_bytes()).hexdigest().upper()==dep_digest,'dispatch-input-bookend','unchanged selected sources',after.detail)
        audit.update(status='validated-conditional-fragments',detail='',nativeInputs=dict(pins),rules=rules,rows=[dict(id=key,evidence='conditional',rules=rules)for key in ['switchAfterLookup','tickDecisionFragments','transitionExecutor','selectorLoop','lookupDictionary','conditionDelegateFallback','addStateDictionaryRequest','selectorEnumeratorInitialization','enumeratorMoveNext']],boundaries=c['boundaries'],callerBindings=c['callerBindings'],skillOnEnter=c['skillOnEnter'],callSites=_call_sites(c))
    except(OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError,struct.error,StopIteration)as exc:audit.update(status='validation_failed',detail=str(exc)[:1200],rules={},rows=[],nativeInputs={},callSites=[],failures=[dict(check=str(exc).split(':',1)[0],detail=str(exc)[:1200])])
    return audit



