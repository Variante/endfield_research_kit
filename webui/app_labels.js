// Endfield conversation browser - shared label/type helpers.

const UI_TEXTS = {
  zh: {
    suiteTitle: "\u7ec8\u672b\u5730\u7814\u7a76\u5de5\u5177",
    storyTab: "\u5267\u60c5",
    mapRecoveryTab: "\u5730\u56fe",
    assetsTab: "\u8d44\u6e90",
    gameplayTab: "\u73a9\u6cd5",
    audioTab: "\u97f3\u9891",
    charactersTab: "\u4eba\u7269",
    referenceTab: "\u6587\u672c",
    updatesTab: "\u66f4\u65b0",
    uiLanguage: "\u754c\u9762",
    uiLanguageChinese: "\u4e2d\u6587",
    uiLanguageEnglish: "English",
    siteTitle: "\u7ec8\u672b\u5730\u7814\u7a76\u5de5\u5177",
    pageTitle: "\u5267\u60c5\u5bf9\u8bdd \u00b7 \u7ec8\u672b\u5730\u7814\u7a76\u5de5\u5177",
    storyPageTitle: "\u5267\u60c5\u5bf9\u8bdd",
    charactersPageTitle: "\u4eba\u7269",
    gameplayPageTitle: "\u73a9\u6cd5\u6570\u636e",
    audioPageTitle: "\u97f3\u9891\u7cfb\u7edf",
    mapRecoveryPageTitle: "\u5730\u56fe",
    assetsPageTitle: "\u5bfc\u51fa\u8d44\u6e90",
    referencePageTitle: "\u6587\u672c\u8868",
    updatesPageTitle: "\u6570\u636e\u66f4\u65b0",
    appTitle: "\u5267\u60c5\u5bf9\u8bdd",
    countLabel: "\u6761\u4f1a\u8bdd",
    searchPlaceholder: "\u641c\u7d22 ID / \u4efb\u52a1 / \u89d2\u8272 / \u6587\u672c",
    basicFilters: "\u57fa\u7840\u7b5b\u9009",
    searchFilter: "\u641c\u7d22",
    language: "\u8bed\u8a00",
    kind: "\u7c7b\u578b",
    type: "\u5267\u60c5\u7ebf",
    mediaFilter: "\u5a92\u4f53",
    storyIssueFilter: "\u6062\u590d\u95ee\u9898",
    recoveryMethodFilter: "\u6062\u590d\u65b9\u5f0f",
    storyIssueMissingLineOrder: "\u7f3a\u5c11\u884c\u987a\u5e8f",
    storyIssuePartialLineOrder: "\u90e8\u5206\u987a\u5e8f",
    storyIssueFallbackLineOrder: "\u56de\u9000\u987a\u5e8f",
    storyIssueUncoveredLines: "\u672a\u8986\u76d6\u53f0\u8bcd",
    storyIssueInferredOptionLayout: "\u9009\u9879\u4f4d\u7f6e\u672a\u5206\u7c7b",
    storyIssueTableOnlyOptionLayout: "\u672a\u6ce8\u518c\u8868\u6570\u636e\u9009\u9879\u4f4d\u7f6e",
    storyIssueKeyedOptionLayout: "\u9009\u9879\u4f4d\u7f6e\u6309\u952e\u540d\u5339\u914d",
    storyIssueGapOptionLayout: "\u9009\u9879\u4f4d\u7f6e\u6309\u884c\u53f7\u7f3a\u53e3\u6062\u590d",
    storyIssueLastLineOptionLayout: "\u9009\u9879\u4f4d\u7f6e\u4e3a\u672b\u884c\u56de\u9000",
    storyIssueUnanchoredOptionLayout: "\u9009\u9879\u4f4d\u7f6e\u672a\u77e5",
    storyIssueInferredOptionResponse: "\u9009\u9879\u56de\u5e94\u4e3a\u63a8\u6d4b",
    storyIssueDuplicateTimestamps: "\u65f6\u95f4\u6233\u91cd\u590d",
    storyIssueTimelineTimestampRegression: "Timeline \u65f6\u95f4\u56de\u9000",
    storyIssueOverrided: "\u9009\u9879\u5df2\u624b\u52a8\u8986\u76d6",
    storyIssueNotOverrided: "\u4ecd\u9700\u624b\u52a8\u8986\u76d6",
    recoveryMethodLinePrefix: "\u884c\u987a\u5e8f",
    recoveryMethodOptionPrefix: "\u9009\u9879",
    recoveryMethodOptionLayoutAuthored: "\u6388\u6743\u951a\u70b9",
    recoveryMethodOptionLayoutPartial: "\u90e8\u5206\u6388\u6743\u951a\u70b9",
    recoveryMethodOptionLayoutFallback: "\u56de\u9000\u5b9a\u4f4d",
    recoveryMethodOptionLayoutNoAnchor: "\u7f3a\u5c11\u6388\u6743\u951a\u70b9",
    recoveryMethodOptionLayoutTableOnly: "\u672a\u6ce8\u518c\u8868\u6570\u636e\u663e\u793a\u4f4d\u7f6e",
    recoveryMethodOptionLayoutKeyMatched: "\u952e\u540d\u884c\u53f7\u5339\u914d",
    recoveryMethodOptionLayoutSparseGap: "\u539f\u59cb\u884c\u53f7\u7f3a\u53e3",
    recoveryMethodOptionLayoutSiblingTimeline: "\u5144\u5f1f Timeline \u4f4d\u7f6e",
    recoveryMethodOptionLayoutLastLine: "\u672b\u884c\u56de\u9000",
    recoveryMethodOptionLayoutUnanchored: "\u672a\u77e5\u4f4d\u7f6e",
    recoveryMethodOptionSceneGraph: "SceneGraph \u5206\u652f",
    recoveryMethodOptionDialogTreeFragment: "DialogTree \u7247\u6bb5",
    recoveryMethodOptionRuntimeJump: "Runtime Jump \u5206\u652f",
    recoveryMethodOptionRawIndexMatched: "\u7d22\u5f15\u5339\u914d",
    recoveryMethodOptionTimelineAdjacent: "Timeline \u76f8\u90bb\u884c\u63a8\u6d4b",
    recoveryMethodOptionCommonContinuation: "\u5171\u540c\u540e\u7eed",
    recoveryMethodOptionContinuationOption: "\u540e\u7eed\u9009\u9879",
    recoveryMethodOptionSiblingSceneHint: "\u5144\u5f1f\u573a\u666f\u63d0\u793a",
    recoveryMethodOptionSiblingSceneText: "\u5144\u5f1f\u573a\u666f\u6587\u672c\u5206\u652f",
    recoveryMethodOptionManualOverride: "\u624b\u52a8\u8986\u76d6",
    sort: "\u6392\u5e8f",
    sortNatural: "\u6309\u7c7b\u578b\u548c\u540d\u79f0",
    sortStory: "\u6309\u5267\u60c5\u6392\u5e8f",
    sortLinesDesc: "\u6309\u884c\u6570\u4ece\u591a\u5230\u5c11",
    sortLinesAsc: "\u6309\u884c\u6570\u4ece\u5c11\u5230\u591a",
    sortKey: "\u6309\u952e\u503c (A-Z)",
    storyTodoTag: "\u5f85\u529e",
    storyTodoText: "\u6062\u590d\u540c\u4e00\u4efb\u52a1\u5185\u7684\u573a\u666f\u987a\u5e8f",
    storyTriggerHeading: "\u5267\u60c5\u89e6\u53d1",
    storyTriggerListLabel: "\u89e6\u53d1",
    storyTriggerLoading: "\u6b63\u5728\u52a0\u8f7d\u539f\u59cb\u6570\u636e\u89e6\u53d1\u8bc1\u636e",
    storyTriggerUnavailable: "\u89e6\u53d1\u8bc1\u636e\u6570\u636e\u4e0d\u53ef\u7528",
    storyTriggerUnknown: "\u539f\u59cb\u6e38\u620f\u6570\u636e\u4e2d\u672a\u6062\u590d\u64ad\u653e\u89e6\u53d1",
    storyTriggerNativePlayback: "\u539f\u59cb\u6570\u636e\u64ad\u653e\u89e6\u53d1",
    storyTriggerNativePlaybackUnresolved: "\u539f\u59cb\u6570\u636e\u64ad\u653e\u89e6\u53d1\uff08\u4efb\u52a1\u5f52\u5c5e\u672a\u89e3\u6790\uff09",
    storyTriggerPlayback: "\u4efb\u52a1/\u8282\u70b9\u64ad\u653e\u89e6\u53d1",
    storyTriggerPlaybackUnresolved: "\u64ad\u653e\u89e6\u53d1\uff08\u5f52\u5c5e\u672a\u89e3\u6790\uff09",
    storyTriggerCondition: "\u672a\u6062\u590d\u64ad\u653e\u89e6\u53d1\uff1b\u6b64\u6587\u4ef6\u7528\u4f5c\u4efb\u52a1\u6761\u4ef6",
    storyTriggerContext: "\u672a\u8bc1\u660e\u64ad\u653e\u89e6\u53d1\uff1b\u4ec5\u6709\u4efb\u52a1/\u8282\u70b9\u4e0a\u4e0b\u6587",
    storyTriggerContextOwnerUnresolved: "\u7cbe\u786e\u8f7d\u4f53\u4e0a\u4e0b\u6587\uff1b\u4efb\u52a1/\u8282\u70b9\u5f52\u5c5e\u672a\u89e3\u6790",
    storyTriggerDependency: "\u672a\u6062\u590d\u64ad\u653e\u89e6\u53d1\uff1b\u4ec5\u6709\u4f9d\u8d56\u5173\u7cfb",
    storyTriggerDefinition: "\u672a\u627e\u5230\u8fd0\u884c\u65f6\u6d88\u8d39\u8005\uff1b\u4ec5\u6709\u5b9a\u4e49",
    storyTriggerOfflineExhausted: "\u5f53\u524d\u7248\u672c\u7684\u79bb\u7ebf\u8f7d\u4f53\u641c\u7d22\u5df2\u8017\u5c3d\uff1b\u672a\u751f\u6210\u5f52\u5c5e\u6216\u987a\u5e8f\u8fb9",
    storyTriggerNonMissionContent: "\u975e\u4f7f\u547d\u5185\u5bb9\uff08\u539f\u751f\u8868\u6216\u6559\u7a0b\u8d44\u4ea7\uff09",
    storyTriggerAmbientWorldContent: "\u73af\u5883\u4e16\u754c\u5185\u5bb9\uff08\u65e0\u4f7f\u547d\u5f52\u5c5e\uff09",
    storyTriggerExactPaths: "\u6761\u7cbe\u786e\u8def\u5f84",
    storyTriggerEvent: "\u4e8b\u4ef6",
    storyTriggerAction: "\u52a8\u4f5c",
    storyTriggerOwner: "\u5f52\u5c5e",
    storyTriggerRoute: "\u8bc1\u636e\u8def\u5f84",
    storyTriggerSource: "\u539f\u59cb\u6765\u6e90",
    storyTriggerSelector: "\u9009\u62e9\u5668",
    storyTriggerOwnershipContext: "\u64ad\u653e\u8def\u5f84\u7cbe\u786e\uff1b\u4efb\u52a1\u5f52\u5c5e\u4ec5\u4e3a\u4e0a\u4e0b\u6587",
    storyOrderBadgeTitle: "\u539f\u59cb\u6570\u636e\u6062\u590d\u987a\u5e8f",
    storyOrderLockMission: "\u9501\u5b9a",
    storyOrderUnlockMission: "\u89e3\u9501",
    storyOrderMissionLocked: "\u5df2\u9501\u5b9a",
    storyOrderMissionEditable: "\u53ef\u7f16\u8f91",
    storyOrderLockMissionTitle: "\u53ef\u7f16\u8f91\u2014\u2014\u70b9\u51fb\u9501\u5b9a\u8be5\u4efb\u52a1\u7684\u987a\u5e8f\uff0c\u7981\u6b62\u624b\u52a8\u8c03\u6574",
    storyOrderUnlockMissionTitle: "\u5df2\u9501\u5b9a\u2014\u2014\u70b9\u51fb\u89e3\u9501\u4ee5\u62d6\u52a8\u8c03\u6574\u987a\u5e8f",
    storyOrderMoveUnusedToEnd: "\u672a\u4f7f\u7528\u7f6e\u5e95",
    storyOrderMoveUnusedToEndTitle: "\u5c06\u8be5\u4efb\u52a1\u6240\u6709\u6807\u8bb0\u4e3a\u201c\u53ef\u80fd\u672a\u4f7f\u7528\u201d\u7684\u6587\u4ef6\u79fb\u5230\u672b\u5c3e",
    storyOrderMoveUnusedToEndNone: "\u8be5\u4efb\u52a1\u6ca1\u6709\u6807\u8bb0\u4e3a\u201c\u53ef\u80fd\u672a\u4f7f\u7528\u201d\u7684\u6587\u4ef6",
    storyOrderDragHandle: "\u62d6\u52a8\u8c03\u6574\u987a\u5e8f",
    storyOrderConfStrong: "\u8bc1\u636e\u652f\u6301",
    storyOrderConfWeak: "\u5f31\u8bc1\u636e",
    storyOrderConfGuess: "\u63a8\u6d4b",
    storyOrderConfTitle: "\u6062\u590d\u987a\u5e8f\u7f6e\u4fe1\u5ea6\uff1a",
    storyOrderPhasePrefix: "\u9636\u6bb5",
    storyOrderPhaseTitle: "\u4efb\u52a1\u9636\u6bb5\uff08\u7c97\u6392\u5e8f\u5206\u7ec4\uff09",
    storyOrderUnverifiedBadge: "\u672a\u6838\u5bf9",
    storyOrderUnverifiedTitle: "\u8be5\u4efb\u52a1\u987a\u5e8f\u672a\u7ecf\u4eba\u5de5\u6838\u5bf9\uff08\u53ef\u80fd\u7531 OCR / \u81ea\u52a8\u6062\u590d\u751f\u6210\uff0c\u6309\u7ea6\u5b9a\u4e0d\u53ef\u4fe1\uff09",
    storyOrderReviewJump: "\u5f85\u6838\u5bf9",
    storyOrderReviewJumpTitle: "\u8df3\u8f6c\u5230\u4e0b\u4e00\u6761\u4f4e\u7f6e\u4fe1\u5ea6\uff08\u9700\u4eba\u5de5\u786e\u8ba4\u987a\u5e8f\uff09\u7684\u884c",
    storyOrderCompareTitle: "\u573a\u666f\u987a\u5e8f\u5bf9\u6bd4",
    storyOrderCompareCurrent: "\u5f53\u524d\u8986\u76d6",
    storyOrderCompareRecovered: "\u9759\u6001\u6062\u590d",
    storyOrderCompareOcr: "OCR",
    storyOrderOcrRankTitle: "data/story_order_ocr.json OCR rank",
    storyOrderCompareAdopt: "\u91c7\u7528",
    storyOrderCompareLocked: "\u8be5\u4efb\u52a1\u5df2\u9501\u5b9a",
    storyOrderCompareLoading: "\u52a0\u8f7d\u4e2d",
    storyOrderCompareMissing: "\u672a\u751f\u6210",
    storyOrderCompareIdentical: "\u4e00\u81f4",
    storyOrderCompareDiff: "{moved} \u5f02\u5e8f / {missing} \u7f3a\u5931 / {added} \u65b0\u589e",
    storyOrderCompareCount: "{count} \u6761",
    storyOrderCompareMore: "+{count}",
    storyOrderCompareBaseline: "\u5267\u60c5\u5217\u8868",
    storyOrderBuilderTitle: "\u8986\u76d6\u8349\u7a3f",
    storyOrderMatrixTitle: "\u6765\u6e90\u6761\u76ee",
    storyOrderMatrixItem: "\u6761\u76ee",
    storyOrderBuilderUseSource: "\u4f7f\u7528 {source}",
    storyOrderBuilderAppendSource: "+ {source}",
    storyOrderBuilderSave: "\u4fdd\u5b58\u8986\u76d6",
    storyOrderBuilderReset: "\u91cd\u7f6e\u8349\u7a3f",
    storyOrderBuilderClear: "\u6e05\u7a7a",
    storyOrderBuilderAdd: "\u52a0\u5165",
    storyOrderBuilderRemove: "\u79fb\u9664",
    storyOrderBuilderSelect: "\u9009\u62e9",
    storyOrderBuilderSelectAll: "\u5168\u9009",
    storyOrderBuilderClearSelection: "\u6e05\u9009",
    storyOrderBuilderSelectedCount: "\u5df2\u9009 {count}",
    storyOrderBuilderMoveTop: "\u7f6e\u9876",
    storyOrderBuilderMoveUp: "\u4e0a\u79fb",
    storyOrderBuilderMoveDown: "\u4e0b\u79fb",
    storyOrderBuilderMoveBottom: "\u7f6e\u5e95",
    storyOrderBuilderMoveHere: "\u79fb\u5230\u6b64\u5904",
    storyOrderBuilderRemoveSelected: "\u79fb\u9664\u9009\u4e2d",
    storyOrderBuilderEmpty: "\u8349\u7a3f\u4e3a\u7a7a",
    storyOrderSaveSaving: "\u4fdd\u5b58\u4e2d",
    storyOrderSaveSaved: "\u5df2\u4fdd\u5b58",
    storyOrderSaveFailed: "\u4fdd\u5b58\u5931\u8d25",
    storyOrderPossiblyUnusedBadge: "\u53ef\u80fd\u672a\u4f7f\u7528",
    storyOrderPossiblyUnusedTitle: "\u53ef\u80fd\u672a\u5728\u6700\u7ec8\u7248\u672c\u4e2d\u4f7f\u7528",
    storyAutomaticUnusedBadge: "\u672a\u4f7f\u7528",
    storyAutomaticUnusedTitle: "\u5f53\u524d\u7248\u672c\u7684\u5b8c\u6574\u64ad\u653e\u8f7d\u4f53\u626b\u63cf\u672a\u53d1\u73b0\u4f7f\u7528\u8be5\u8fc7\u573a\u52a8\u753b\u7684\u8bc1\u636e",
    storyOrderBranchBadge: "\u5206\u652f",
    storyOrderBranchTitle: "\u6807\u8bb0\u4e3a\u5206\u652f\u5267\u60c5\u6587\u4ef6",
    storyOrderTagMarkBranch: "\u6807\u8bb0\u4e3a\u5206\u652f",
    storyOrderTagMarkUnused: "\u6807\u8bb0\u4e3a\u53ef\u80fd\u672a\u4f7f\u7528",
    storyOrderTagClear: "\u6e05\u9664\u6807\u8bb0",
    storyOrderTagMarkBranchTitle: "\u6807\u8bb0\u4e3a\u5206\u652f\u5267\u60c5\u6587\u4ef6",
    storyOrderTagMarkUnusedTitle: "\u6807\u8bb0\u4e3a\u53ef\u80fd\u672a\u5728\u6210\u54c1\u4e2d\u4f7f\u7528",
    storyOrderTagClearTitle: "\u6e05\u9664\u201c\u5206\u652f / \u53ef\u80fd\u672a\u4f7f\u7528\u201d\u6807\u8bb0",
    storyOrderUnusedMark: "\u6807\u8bb0\u4e3a\u672a\u4f7f\u7528",
    storyOrderUnusedClear: "\u53d6\u6d88\u672a\u4f7f\u7528\u6807\u8bb0",
    storyOrderUnusedMarkTitle: "\u6807\u8bb0\u4e3a\u53ef\u80fd\u672a\u5728\u6210\u54c1\u4e2d\u4f7f\u7528",
    storyOrderUnusedClearTitle: "\u6e05\u9664\u201c\u53ef\u80fd\u672a\u4f7f\u7528\u201d\u6807\u8bb0",
    storyOrderRemoveFromMission: "\u4ece\u8be5\u4efb\u52a1\u79fb\u9664",
    storyOrderRemoveFromMissionTitle: "\u6587\u4ef6\u540d\u4e0d\u5305\u542b\u4efb\u52a1\u4ee3\u7801 {mission}\u2014\u2014\u70b9\u51fb\u4ece\u8be5\u4efb\u52a1\u987a\u5e8f\u4e2d\u79fb\u9664",
    reset: "\u91cd\u7f6e\u7b5b\u9009",
    listUnit: "\u6761",
    lineUnit: "\u884c",
    emptyConversation: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u6bb5\u5bf9\u8bdd",
    revealCurrent: "\u5b9a\u4f4d\u5f53\u524d\u6587\u4ef6",
    showEmpty: "\u663e\u793a\u7a7a\u767d\u5bf9\u8bdd\u884c",
    showRaw: "\u663e\u793a\u539f\u59cb JSON / \u6587\u672c\u6765\u6e90",
    showDebug: "\u663e\u793a\u8c03\u8bd5\u4fe1\u606f",
    inlineTagMode: "\u663e\u793a\u6807\u7b7e\u539f\u6587",
    genderVariant: "\u7ba1\u7406\u5458\u6027\u522b\u7248\u672c",
    genderVariantFemale: "\u5973",
    genderVariantMale: "\u7537",
    genderVariantNote: "\u5bf9\u8bdd\u6587\u672c\u3001\u8bed\u97f3\u3001\u56fe\u7247\u3001\u89c6\u9891\u4e0e\u6027\u522b\u9650\u5b9a\u8fc7\u573a\u8ddf\u968f\u6b64\u9009\u62e9\uff0c\u5e76\u4e0e\u73a9\u6cd5\u9875\u4fdd\u6301\u540c\u6b65\u3002",
    showFilters: "\u663e\u793a\u7b5b\u9009",
    hideFilters: "\u9690\u85cf\u7b5b\u9009",
    loading: "\u52a0\u8f7d\u4e2d\u2026",
    loadErrorPrefix: "\u52a0\u8f7d\u5931\u8d25: ",
    emptyPreview: "(\u65e0\u9884\u89c8)",
    systemSpeaker: "(\u7cfb\u7edf)",
    radioSpeaker: "(\u7535\u53f0)",
    linkedMission: "\u94fe\u63a5\u4efb\u52a1",
    summary: "\u5267\u60c5\u6982\u8981",
    hints: "\u6279\u6ce8",
    metadata: "Metadata",
    sourceEvidence: "\u6765\u6e90\u8bc1\u636e",
    sourceEvidenceMore: "\u8fd8\u6709 {count} \u6761",
    narrativeVideo: "\u5267\u60c5\u89c6\u9891",
    narrativeVideoMore: "\u8fd8\u6709 {count} \u4e2a\u89c6\u9891",
    narrativeVideoInlineLabel: "\u89c6\u9891",
    recoveredAudio: "\u6062\u590d\u97f3\u9891",
    dialogLifecycleAudio: "\u5bf9\u8bdd\u751f\u547d\u5468\u671f\u97f3\u9891",
    dialogLifecycle_preloadEvents: "\u9884\u52a0\u8f7d",
    dialogLifecycle_postEnterEvents: "\u8fdb\u5165\u5bf9\u8bdd\u540e",
    dialogLifecycleAudioNote: "\u8fd9\u662f\u7cbe\u786e\u7684\u5bf9\u8bdd ID \u4e0e\u751f\u547d\u5468\u671f\u9636\u6bb5\u914d\u7f6e\uff1b\u5b9e\u9645\u8c03\u5ea6\u3001Wwise \u5206\u652f\u4e0e\u64ad\u653e\u4ecd\u672a\u89c2\u6d4b\u3002",
    recoveredAudioMedia: "\u5a92\u4f53",
    recoveredAudioBytes: "\u5b57\u8282",
    wikiImages: "\u56fe\u7247",
    wikiMedia: "\u5a92\u4f53",
    missionNotes: "\u4efb\u52a1\u5907\u6ce8",
    missionTimelineRecovery: "\u4efb\u52a1\u65f6\u95f4\u7ebf\u6062\u590d",
    missionTimelineQuests: "\u4efb\u52a1",
    missionTimelineBranches: "\u5206\u652f",
    missionTimelineEdges: "\u573a\u666f\u8fb9",
    missionTimelineQuestSpatialTrack: "\u4efb\u52a1\u5730\u56fe\u8f68\u8ff9",
    missionTimelineSpatialHint: "\u5730\u56fe/\u8d44\u6e90\u5143\u6570\u636e\u4ec5\u4f5c\u5b9a\u4f4d\u7ebf\u7d22\u3002",
    missionTimelineSourceScripts: "\u6765\u6e90\u811a\u672c",
    missionTimelineSpatialCandidates: "\u7a7a\u95f4\u5019\u9009",
    missionTimelineSpatialMatches: "\u7a7a\u95f4\u5339\u914d",
    cutsceneInfo: "\u8fc7\u573a\u4fe1\u606f",
    cutscenePlacement: "\u4f4d\u7f6e\u7ebf\u7d22",
    cutsceneVariants: "\u53d8\u4f53\u6587\u4ef6",
    cutsceneVideos: "\u89c6\u9891",
    cutscenePaths: "\u8def\u5f84",
    cutsceneMetadata: "\u5143\u6570\u636e",
    cutsceneShapeUnityTimeline: "Unity \u5b9e\u65f6\u6f14\u51fa",
    cutsceneShapeUnityTimelineWithIndependentFmv: "\u5b9e\u65f6\u6f14\u51fa + \u72ec\u7acb\u5267\u60c5\u89c6\u9891",
    cutsceneShapeTimelineComponentsWithoutRoot: "\u6f14\u51fa\u7ec4\u4ef6\uff08\u6839\u5b9a\u4e49\u7f3a\u5931\uff09",
    cutsceneShapeLevelscriptFmv: "\u9884\u6e32\u67d3\u5267\u60c5\u89c6\u9891",
    cutsceneShapeTextOnlyUnconfirmed: "\u4ec5\u6587\u672c\u5019\u9009",
    cutsceneShapeUnityTimelineHint: "\u5df2\u6062\u590d Unity Timeline \u6839\u548c\u6f14\u51fa\u7ec4\u4ef6\u3002\u8fd9\u662f\u521b\u4f5c\u7ed3\u6784\uff0c\u4e0d\u7b49\u4e8e\u672c\u6b21\u6e38\u620f\u4e2d\u5df2\u6267\u884c\u3002",
    cutsceneShapeUnityTimelineWithIndependentFmvHint: "\u540c\u4e00 Story \u9879\u4e0b\u540c\u65f6\u5b58\u5728 Unity Timeline \u548c\u72ec\u7acb LevelScript \u89c6\u9891\u64ad\u653e\u8bf7\u6c42\uff1b\u5c1a\u4e0d\u80fd\u8bc1\u660e\u4e24\u8005\u7684\u5305\u542b\u6216\u5148\u540e\u5173\u7cfb\u3002",
    cutsceneShapeTimelineComponentsWithoutRootHint: "\u627e\u5230\u4e86 Actor/Audio/Effect/Light/Others \u5b50 Timeline\uff0c\u4f46\u5f53\u524d\u5bfc\u51fa\u4e2d\u6ca1\u6709\u5bf9\u5e94\u7684\u6839\u5b9a\u4e49\uff0c\u56e0\u6b64\u4e0d\u89c6\u4e3a\u5b8c\u6574\u53ef\u64ad\u653e\u6f14\u51fa\u3002",
    cutsceneShapeLevelscriptFmvHint: "\u8fd9\u662f LevelScript PlayFmvAction \u6307\u5411\u7684\u72ec\u7acb\u9884\u6e32\u67d3\u89c6\u9891\uff0c\u4e0d\u662f Unity Timeline cutscene \u6839\u3002",
    cutsceneShapeTextOnlyUnconfirmedHint: "\u4ec5\u627e\u5230 cutscene \u547d\u540d\u7684\u672c\u5730\u5316\u6587\u672c\uff1b\u6682\u65e0\u6f14\u51fa\u8d44\u4ea7\u3001\u5267\u60c5\u89c6\u9891\u6216\u7cbe\u786e\u6765\u6e90\u94fe\u8bc1\u660e\u5b83\u53ef\u64ad\u653e\u3002",
    cutsceneLocalizedTextWithoutTrack: "\u5b57\u5e55\u65f6\u95f4\u672a\u6062\u590d",
    cutsceneLocalizedTextWithoutTrackHint: "\u5df2\u627e\u5230\u672c\u5730\u5316\u6587\u672c\uff0c\u4f46\u6ca1\u6709 authored subtitle track \u5c06\u5b83\u653e\u5230\u6f14\u51fa\u65f6\u95f4\u7ebf\u4e0a\u3002",
    missionTimelineSceneGraph: "\u573a\u666f\u8fb9\u56fe",
    missionTimelineEdgeList: "\u8fb9\u5217\u8868",
    missionTimelineComponent: "\u8fde\u901a\u5206\u91cf",
    missionTimelineNodes: "\u8282\u70b9",
    missionTimelineEvidence: "\u65f6\u95f4\u7ebf\u8bc1\u636e",
    missionTimelineUnresolved: "\u672a\u89e3\u6790",
    missionTimelineSource: "\u6765\u6e90",
    missionTimelineObjectives: "\u76ee\u6807",
    missionTimelineObjectiveInstructions: "\u4efb\u52a1\u6307\u5f15",
    missionTimelineScenes: "\u573a\u666f",
    missionTimelineResources: "\u8d44\u6e90",
    missionTimelineMapPins: "\u5730\u56fe\u70b9",
    missionTimelineGraphLinks: "\u573a\u666f\u94fe\u63a5",
    missionTimelineFlow: "\u6d41\u7a0b",
    missionTimelinePrev: "\u524d\u7f6e",
    timelineActions: "\u65f6\u95f4\u7ebf\u52a8\u4f5c",
    timelineActionsStatus: "\u52a8\u4f5c\u987a\u5e8f",
    timelineActionsTimelineStatus: "Timeline \u987a\u5e8f",
    timelineActionsFlows: "\u6d41\u7a0b",
    timelineActionsLines: "\u884c",
    timelineActionsLinked: "\u94fe\u63a5\u52a8\u4f5c",
    timelineActionsDecoded: "\u5df2\u89e3\u6790",
    timelineActionsUnparsed: "\u672a\u89e3\u6790",
    timelineActionsKinds: "\u7c7b\u578b",
    timelineActionsLayouts: "\u5e03\u5c40",
    timelineActionsLineDetails: "\u884c\u52a8\u4f5c",
    timelineActionsMore: "\u8fd8\u6709 {count} \u884c",
    timelineActionsStatusAgrees: "\u4e00\u81f4",
    timelineActionsStatusPartial: "\u90e8\u5206\u4e00\u81f4",
    timelineActionsStatusConflict: "\u51b2\u7a81",
    timelineActionsStatusMissingTimeline: "\u7f3a\u5c11 Timeline \u987a\u5e8f",
    timelineActionsStatusMissingAction: "\u7f3a\u5c11\u52a8\u4f5c",
    timelineActionsStatusMissing: "\u7f3a\u5c11",
    lineOrderRecovery: "\u884c\u987a\u5e8f\u6062\u590d",
    lineOrderNotNeeded: "\u5355\u884c\u573a\u666f\uff0c\u65e0\u9700\u989d\u5916\u7684\u884c\u987a\u5e8f\u6062\u590d\u3002",
    lineOrderMissing: "\u672a\u6062\u590d\u51fa\u660e\u786e\u7684\u884c\u987a\u5e8f\u3002",
    lineOrderModeDialogTree: "\u76f4\u63a5\u4f7f\u7528 DialogTree \u987a\u5e8f",
    lineOrderModeDialogTreeFragment: "\u4f7f\u7528\u5176\u4ed6 DialogTree \u6b8b\u7247\u7684\u6388\u6743\u987a\u5e8f",
    lineOrderModeDialogTreeExtraConfig: "\u4f7f\u7528 extra_config \u7684\u6388\u6743\u987a\u5e8f",
    lineOrderModeDialogTreeCinematicTimeline: "\u4f7f\u7528 DialogTree \u5267\u60c5\u8282\u70b9\u62fc\u63a5 Timeline",
    lineOrderModeAuthoredBlend: "\u6df7\u5408\u591a\u4e2a\u6388\u6743\u6765\u6e90",
    lineOrderModeAuthoredNumericStitch: "\u6309\u6388\u6743\u6570\u5b57\u987a\u5e8f\u62fc\u63a5",
    lineOrderModeDialogTimeline: "\u4f7f\u7528 dialogTimeline \u7684\u6388\u6743\u987a\u5e8f",
    lineOrderModeCompoundNumericSuffix: "\u6309\u590d\u5408\u6570\u5b57\u540e\u7f00\u62fc\u63a5",
    lineOrderModeLineIdSuffix: "\u56de\u9000\u884c\u987a\u5e8f",
    lineOrderModeRuntimeRowIteration: "\u8fd0\u884c\u65f6\u884c\u8fed\u4ee3",
    lineOrderModeUnregisteredScene: "\u672a\u5728 DialogIdTable \u6ce8\u518c",
    lineOrderRegistryRegistered: "DialogIdTable: \u5df2\u6ce8\u518c",
    lineOrderRegistryUnregistered: "DialogIdTable: \u672a\u6ce8\u518c",
    lineOrderRegistryTrunks: "DialogIdTable: {trunks} trunk / {lines} \u884c\u5f15\u7528",
    lineOrderRegistryDeltaPositive: "DialogIdTable: webui \u591a {count} \u884c",
    lineOrderRegistryDeltaNegative: "DialogIdTable: webui \u5c11 {count} \u884c",
    lineOrderModeFallback: "\u56de\u9000\u987a\u5e8f",
    lineOrderModeMissing: "\u7f3a\u5c11\u884c\u987a\u5e8f\u5757",
    lineOrderConfirmed: "\u4fdd\u6301\u5f53\u524d\u987a\u5e8f",
    lineOrderReordered: "\u91cd\u6392 {moved}/{total}",
    lineOrderSource: "\u6765\u6e90",
    lineOrderCoverage: "\u8986\u76d6 {count} \u884c",
    lineOrderTree: "DialogTree",
    lineOrderTreeContribution: "\u8d21\u732e\u7684\u884c",
    lineOrderSequence: "\u6700\u7ec8\u8f93\u51fa\u987a\u5e8f",
    lineOrderPreviewEmpty: "(\u65e0\u6587\u672c\u9884\u89c8)",
    lineOrderFile: "\u6587\u4ef6",
    lineOrderConversationFlow: "\u6062\u590d\u51fa\u7684\u5bf9\u8bdd\u6d41\u7a0b",
    lineOrderConversationFlowNote: "\u8fd9\u91cc\u628a\u4e3b\u5e72\u53f0\u8bcd\u3001\u9009\u9879\u7ec4\u4ee5\u53ca sceneGraphLinks \u91cc\u7684\u8df3\u8f6c / \u56de\u73af\u5408\u5e76\u6210\u4e00\u68f5\u53ef\u8bfb\u7684 DialogTree \u5bf9\u8bdd\u6811\u3002",
    lineOrderBeforeScene: "\u5f00\u573a\u524d",
    lineOrderAfterLine: "\u63a5\u5728",
    lineOrderPlacementUncertain: "\u4f4d\u7f6e\u5f85\u786e\u8ba4",
    lineOrderPlacementUnknown: "\u4f4d\u7f6e\u4e0d\u660e",
    lineOrderOption: "\u9009\u9879",
    lineOrderCommonContinuation: "\u5171\u540c\u540e\u7eed",
    lineOrderContinueInScene: "\u7ee7\u7eed\u5f53\u524d\u573a\u666f",
    lineOrderJumpToScene: "\u8df3\u8f6c\u5230\u573a\u666f",
    lineOrderLoopToLine: "\u56de\u5230\u524d\u9762\u7684\u53f0\u8bcd",
    lineOrderLoopToScene: "\u56de\u5230\u5f53\u524d\u573a\u666f",
    lineOrderSubmenu: "\u5b50\u83dc\u5355",
    lineOrderTerminal: "\u7ec8\u70b9",
    lineOrderPathLineIds: "\u8def\u5f84\u884c ID",
    lineOrderOutcome: "\u7ed3\u679c",
    lineOrderMethod: "\u6062\u590d\u65b9\u5f0f",
    lineOrderLineIdReference: "\u884c ID \u987a\u5e8f",
    lineOrderLineIdReferenceNote: "",
    lineOrderDiffersFromLineIdOrder: "\u4e0d\u540c\u4e8e\u884c ID \u987a\u5e8f",
    lineOrderAddedCount: "\u5e76\u5165 {count} \u884c",
    lineOrderModeDetailDialogTree: "\u6cbf\u5f53\u524d\u573a\u666f\u7684 DialogTree \u4e3b\u5e72\u4e0e\u5206\u652f\u6062\u590d\u987a\u5e8f\u3002",
    lineOrderModeDetailDialogTreeFragment: "\u501f\u7528\u6307\u5411\u5f53\u524d\u573a\u666f\u7684\u5176\u4ed6 DialogTree \u6b8b\u7247\u6765\u8865\u9f50\u6388\u6743\u987a\u5e8f\u3002",
    lineOrderModeDetailDialogTreeExtraConfig: "\u4f7f\u7528 extra_config \u91cc\u58f0\u660e\u7684\u6388\u6743\u987a\u5e8f\u3002",
    lineOrderModeDetailDialogTreeCinematicTimeline: "\u6309 DialogTree \u4e2d\u7684\u5267\u60c5\u8282\u70b9\u628a\u5c40\u90e8 Timeline \u53f0\u8bcd\u63d2\u56de\u4e3b\u5e72\u987a\u5e8f\u3002",
    lineOrderModeDetailAuthoredBlend: "\u6309\u8986\u76d6\u7387\u548c\u4f18\u5148\u7ea7\u5408\u5e76\u591a\u4e2a\u6388\u6743\u6765\u6e90\u3002",
    lineOrderModeDetailAuthoredNumericStitch: "\u4e3b DialogTree \u7ed9\u51fa\u90e8\u5206\u987a\u5e8f\uff0c\u7f3a\u53e3\u884c\u6309\u6570\u5b57\u540e\u7f00\u63d2\u56de\u3002",
    lineOrderModeDetailDialogTimeline: "\u4f7f\u7528 dialogTimeline \u91cc\u8bb0\u5f55\u7684\u6388\u6743\u987a\u5e8f\u3002",
    lineOrderModeDetailLineIdSuffix: "\u5f53\u524d\u573a\u666f\u6ca1\u6709\u6062\u590d\u51fa\u53ef\u7528\u7684\u6388\u6743\u884c\u987a\u5e8f\u6765\u6e90\u3002",
    lineOrderModeDetailFallback: "\u4f7f\u7528\u56de\u9000\u7b56\u7565 {mode} \u6062\u590d\u987a\u5e8f\u3002",
    optionGroup: "\u7b2c {group} \u7ec4\u9009\u9879",
    relatedScenesHeading: "\u5171\u7528 Unity Timeline",
    gameplayLinkHeading: "\u5b9e\u6218\u6570\u636e",
    openGameplayData: "\u5728\u5b9e\u6218\u9875\u6253\u5f00",
    archiveLinksHeading: "\u6863\u6848\u5173\u8054",
    archiveReports: "\u62a5\u544a",
    archiveMaterials: "\u76f8\u5173\u6863\u6848",
    archiveDuplicateDocuments: "\u540c\u6587\u6863\u6848",
    archivePopupTexts: "\u4efb\u52a1\u5f39\u7a97",
    archiveMissionFiles: "\u4efb\u52a1\u6587\u4ef6",
    branchHintLabel: "\u2192 \u8df3\u8f6c\u5230",
    optTargetMenu: "\u2192 \u7b2c {g} \u7ec4\u9009\u9879",
    optTargetReturnsToMenu: "\u21a9 \u8fd4\u56de\u7b2c {g} \u7ec4",
    optTargetSelfMenu: "\u21ba \u91cd\u542f\u672c\u7ec4\u9009\u9879",
    optTargetScene: "\u2192 {key}",
    optTargetSceneSubmenu: "\u2192 \u5b50\u573a\u666f {key}",
    optTargetTerminal: "\u25a0 \u7ed3\u675f\u5267\u60c5",
    optJumpLine: "\u2192 {line}",
    optJumpLineTitle: "\u8be5\u9009\u9879\u8fdb\u5165\u7684\u7b2c\u4e00\u884c\uff1a{line}\u3002",
    optJumpLineTree: "Tree \u2192 {line}",
    optJumpLineTitleTree: "DialogTree \u660e\u786e\u6307\u5411\u7684\u7b2c\u4e00\u884c\uff1a{line}\u3002",
    optJumpLineTimeline: "Timeline \u2192 {line}",
    optJumpLineTitleTimeline: "Runtime Jump Track \u6062\u590d\u7684\u8be5\u9009\u9879\u8def\u5f84\u7b2c\u4e00\u884c\uff1a{line}\u3002",
    optJumpLineShared: "\u5171\u4eab \u2192 {line}",
    optJumpLineTitleShared: "\u6240\u6709\u9009\u9879\u5408\u6d41\u5230\u540c\u4e00\u884c\uff1a{line}\u3002",
    optJumpLineInferred: "\u63a8\u6d4b \u2192 {line}",
    optJumpLineTitleInferred: "\u76ee\u6807\u884c\u7531 Timeline \u987a\u5e8f\u63a8\u6d4b\uff1a{line}\u3002",
    optJumpLoopLine: "\u21ba \u5faa\u73af {line}",
    optJumpLoopLineTitle: "\u8be5\u9009\u9879\u8def\u5f84\u4f1a\u5728\u6b64\u884c\u540e\u56de\u5230\u5faa\u73af\u5f00\u59cb\u4f4d\u7f6e\uff1a{line}\u3002",
    optTargetAccessedFrom: "\u2190 \u4ece",
    optRiskRawIndexMatchedLine: "\u7d22\u5f15\u5339\u914d",
    optRiskRawIndexMatchedLineTitle: "\u6e90\u6570\u636e\u6ca1\u6709\u660e\u786e\u5199\u51fa\u8be5\u9009\u9879\u7684\u76ee\u6807\u53f0\u8bcd\uff1b\u4f46 Timeline raw optionIndex \u4e0e\u9009\u9879\u5e8f\u53f7\u5339\u914d\uff0c\u56de\u590d\u884c\u6062\u590d\u5230 {line}\u3002\u8fd9\u4ecd\u7136\u5c5e\u4e8e\u6062\u590d\u63a8\u65ad\uff0c\u4f46\u6bd4\u76f8\u90bb\u884c\u63a8\u6d4b\u66f4\u5f3a\u3002",
    optRiskInferredFollowingLine: "\u63a8\u6d4b\u56de\u5e94",
    optRiskInferredFollowingLineTitle: "\u6e90\u6570\u636e\u6ca1\u6709\u660e\u786e\u5199\u51fa\u8be5\u9009\u9879\u7684\u76ee\u6807\u53f0\u8bcd\uff1b\u6309 Timeline \u987a\u5e8f\u63a8\u6d4b\u53ef\u80fd\u5bf9\u5e94 {line}\u3002",
    optManualOverride: "\u624b\u52a8\u8986\u76d6",
    optManualOverrideTitle: "\u8be5\u7ed3\u679c\u7531\u672c\u5730\u624b\u52a8\u8986\u76d6\u6587\u4ef6\u63d0\u4f9b\uff1a{source}{note}",
    preDialogOptions: "\u5bf9\u8bdd\u9009\u9879\uff08\u5f00\u573a\u524d\uff09",
    uncertainDialogOptions: "\u5bf9\u8bdd\u9009\u9879\uff08\u4f4d\u7f6e\u5f85\u786e\u8ba4\uff09",
    orphanDialogOptions: "\u5bf9\u8bdd\u9009\u9879\uff08\u4f4d\u7f6e\u4e0d\u660e\uff09",
    radio: "\u8bed\u97f3\u901a\u8baf",
    envTalk: "\u73af\u5883\u5bf9\u8bdd",
    warningTitle: "\u63d0\u793a",
    warningInferredOptionLayoutTitle: "\u9009\u9879\u4f4d\u7f6e\u63d0\u793a",
    warningInferredOptionLayoutBody: "\u6240\u6709\u9009\u9879\u7ec4\u90fd\u663e\u793a\u5728\u5df2\u6062\u590d\u7684\u4f4d\u7f6e\u3002\u4e0b\u65b9\u4f1a\u533a\u5206\u952e\u540d\u5339\u914d\u3001\u884c\u53f7\u7f3a\u53e3\u6062\u590d\u3001\u672b\u884c\u56de\u9000\u548c\u771f\u6b63\u672a\u77e5\u7684\u4f4d\u7f6e\u3002",
    optionPlacementKeyMatched: "\u952e\u540d\u5339\u914d\u4f4d\u7f6e",
    optionPlacementSparseGap: "\u884c\u53f7\u7f3a\u53e3\u4f4d\u7f6e",
    optionPlacementSiblingTimeline: "\u5144\u5f1f\u573a\u666f\u4f4d\u7f6e",
    optionPlacementLastLine: "\u672b\u884c\u56de\u9000",
    optionPlacementUnknown: "\u4f4d\u7f6e\u672a\u77e5",
    warningInferredOptionResponseTitle: "\u9009\u9879\u56de\u5e94\u63d0\u793a",
    warningInferredOptionResponseBody: "\u90e8\u5206\u9009\u9879\u7684\u56de\u5e94\u53f0\u8bcd\u6765\u81ea Timeline \u987a\u5e8f\u63a8\u6d4b\u3002",
    warningDuplicateTimestampsTitle: "\u65f6\u95f4\u6233\u63d0\u793a",
    warningDuplicateTimestampsBody: "\u672c\u573a\u666f\u6709\u591a\u884c\u663e\u793a\u4e3a\u76f8\u540c\u7684\u65f6\u95f4\u6233\uff0c\u53ef\u80fd\u662f Timeline \u6062\u590d\u51b2\u7a81\u3002",
    warningDuplicateTimestampLines: "\u91cd\u590d\u884c",
    warningTimelineTimestampRegressionTitle: "Timeline \u65f6\u95f4\u987a\u5e8f\u63d0\u793a",
    warningTimelineTimestampRegressionBody: "\u672c\u573a\u666f\u7684\u5df2\u6062\u590d Timeline \u65f6\u95f4\u6233\u5728\u5f53\u524d\u884c\u987a\u5e8f\u4e2d\u51fa\u73b0\u56de\u9000\uff0c\u53ef\u80fd\u8868\u793a\u6b21\u7ea7 Timeline \u662f\u5c40\u90e8\u62fc\u63a5\u8bc1\u636e\uff0c\u800c\u4e0d\u662f\u7edd\u5bf9\u573a\u666f\u65f6\u95f4\u3002",
    warningTimelineTimestampRegressionLines: "\u56de\u9000\u884c",
    warningNarrativeVideoUnplacedTitle: "\u89c6\u9891\u4f4d\u7f6e\u672a\u6062\u590d",
    warningNarrativeVideoUnplacedBody: "\u672c\u573a\u666f\u5173\u8054\u4e86\u89c6\u9891\uff0c\u4f46\u672a\u80fd\u4ece Timeline \u4e2d\u6062\u590d\u5176\u64ad\u653e\u4f4d\u7f6e\uff0c\u4e0b\u65b9\u4ec5\u4f5c\u4e3a\u9644\u4ef6\u5c55\u793a\u3002",
    warningRemotecommNarrativeVideoMissingTitle: "\u8fdc\u7a0b\u901a\u8baf\u89c6\u9891\u7f3a\u5931",
    warningRemotecommNarrativeVideoMissingBody: "\u6e90\u6570\u636e\u6307\u5411\u8fd9\u4e9b RemoteComm \u89c6\u9891\u6bb5\uff0c\u4f46\u5bfc\u51fa\u76ee\u5f55\u4e2d\u6ca1\u6709\u5bf9\u5e94 MP4 \u6587\u4ef6\u3002",
    warningSceneOrderDisorderTitle: "\u987a\u5e8f\u63d0\u793a",
    warningSceneOrderDisorderBody: "\u672c\u573a\u666f\u7684\u987a\u5e8f\u6216\u9009\u9879\u5b9a\u4f4d\u4e0d\u662f\u5b8c\u6574\u6388\u6743\u7ed3\u679c\u3002",
    warningAspectLineOrder: "\u884c\u987a\u5e8f",
    warningAspectOptionLayout: "\u9009\u9879\u4f4d\u7f6e",
    warningStatusDirect: "\u5df2\u6709\u6388\u6743\u987a\u5e8f",
    warningStatusPartial: "\u90e8\u5206\u6388\u6743\u8986\u76d6",
    warningStatusFallback: "\u56de\u9000\u6062\u590d",
    warningStatusMissing: "\u7f3a\u5c11\u987a\u5e8f\u5757",
    warningStatusAuthored: "\u5df2\u6709\u6388\u6743\u951a\u70b9",
    warningStatusInferred: "\u4f4d\u7f6e\u4e3a\u63a8\u65ad",
    warningStatusNotNeeded: "\u65e0\u9700\u5206\u6790",
    warningLineOrderSummaryLineIdSuffix: "\u672a\u627e\u5230\u6388\u6743\u884c\u987a\u5e8f",
    warningLineOrderDetailLineIdSuffix: "",
    warningLineOrderSummaryMissing: "\u672a\u627e\u5230\u884c\u987a\u5e8f\u6570\u636e",
    warningLineOrderDetailMissing: "",
    warningLineOrderSummaryFallback: "\u4f7f\u7528\u56de\u9000\u987a\u5e8f",
    warningLineOrderDetailFallback: "",
    warningLineOrderSummaryPartial: "\u6388\u6743\u987a\u5e8f\u53ea\u8986\u76d6\u4e86\u90e8\u5206\u53f0\u8bcd",
    warningLineOrderDetailPartial: "",
    lineOrderUncoveredCount: "\u672a\u8986\u76d6 {count} \u884c",
    lineOrderUncoveredLines: "\u672a\u8986\u76d6\u884c",
    lineOrderUncoveredBadge: "uncovered",
    duplicateTimestampBadge: "\u65f6\u95f4\u6233\u91cd\u590d",
    warningOptionLayoutSummaryNoTreeReference: "\u9009\u9879\u4f4d\u7f6e\u5168\u90e8\u6765\u81ea\u56de\u9000",
    warningOptionLayoutDetailNoTreeReference: "",
    warningOptionLayoutSummaryNoAuthoredGroupAnchor: "\u9009\u9879\u4f4d\u7f6e\u7f3a\u5c11\u6388\u6743\u951a\u70b9",
    warningOptionLayoutDetailNoAuthoredGroupAnchor: "",
    warningOptionLayoutSummaryPartialAuthoredCoverage: "\u53ea\u6709\u90e8\u5206\u9009\u9879\u4f4d\u7f6e\u6709\u6388\u6743\u951a\u70b9",
    warningOptionLayoutDetailPartialAuthoredCoverage: "",
    warningOptionLayoutSummaryInferred: "\u9009\u9879\u4f4d\u7f6e\u6765\u81ea\u63a8\u65ad",
    warningOptionLayoutDetailInferred: "",
  },
  en: {
    suiteTitle: "Endfield Research Kit",
    storyTab: "Story",
    mapRecoveryTab: "Map",
    assetsTab: "Assets",
    gameplayTab: "Gameplay",
    audioTab: "Audio",
    charactersTab: "Characters",
    referenceTab: "Reference",
    updatesTab: "Updates",
    uiLanguage: "UI",
    uiLanguageChinese: "Chinese",
    uiLanguageEnglish: "English",
    siteTitle: "Endfield Research Kit",
    pageTitle: "Story Dialogue \u00b7 Endfield Research Kit",
    storyPageTitle: "Story Dialogue",
    charactersPageTitle: "Characters & NPCs",
    gameplayPageTitle: "Gameplay Data",
    audioPageTitle: "Audio System",
    mapRecoveryPageTitle: "Map",
    assetsPageTitle: "Exported Assets",
    referencePageTitle: "Text Tables",
    updatesPageTitle: "Data Updates",
    appTitle: "Story Dialogue",
    countLabel: "conversations",
    searchPlaceholder: "Search ID / mission / actor / text",
    basicFilters: "Basic Filters",
    searchFilter: "Search",
    language: "Language",
    kind: "Type",
    type: "Storyline",
    mediaFilter: "Media",
    storyIssueFilter: "Recovery Issue",
    recoveryMethodFilter: "Recovery Method",
    storyIssueMissingLineOrder: "Missing order",
    storyIssuePartialLineOrder: "Partial order",
    storyIssueFallbackLineOrder: "Fallback order",
    storyIssueUncoveredLines: "Uncovered lines",
    storyIssueInferredOptionLayout: "Unclassified option placement",
    storyIssueTableOnlyOptionLayout: "Table-only option position",
    storyIssueKeyedOptionLayout: "Key-based option position",
    storyIssueGapOptionLayout: "Gap-based option position",
    storyIssueLastLineOptionLayout: "End-of-scene option guess",
    storyIssueUnanchoredOptionLayout: "Unknown option position",
    storyIssueInferredOptionResponse: "Inferred reply",
    storyIssueDuplicateTimestamps: "Duplicate timestamps",
    storyIssueTimelineTimestampRegression: "Timeline regression",
    storyIssueOverrided: "Option manually overridden",
    storyIssueNotOverrided: "Needs manual override",
    recoveryMethodLinePrefix: "Line order",
    recoveryMethodOptionPrefix: "Option",
    recoveryMethodOptionLayoutAuthored: "authored anchors",
    recoveryMethodOptionLayoutPartial: "partial authored anchors",
    recoveryMethodOptionLayoutFallback: "fallback placement",
    recoveryMethodOptionLayoutNoAnchor: "missing authored anchors",
    recoveryMethodOptionLayoutTableOnly: "unregistered table display placement",
    recoveryMethodOptionLayoutKeyMatched: "table-key match",
    recoveryMethodOptionLayoutSparseGap: "original line-number gap",
    recoveryMethodOptionLayoutSiblingTimeline: "sibling Timeline position",
    recoveryMethodOptionLayoutLastLine: "end-of-scene fallback",
    recoveryMethodOptionLayoutUnanchored: "unknown position",
    recoveryMethodOptionSceneGraph: "SceneGraph branches",
    recoveryMethodOptionDialogTreeFragment: "DialogTree fragments",
    recoveryMethodOptionRuntimeJump: "Runtime Jump branches",
    recoveryMethodOptionRawIndexMatched: "index matched",
    recoveryMethodOptionTimelineAdjacent: "Timeline adjacent inference",
    recoveryMethodOptionCommonContinuation: "shared continuation",
    recoveryMethodOptionContinuationOption: "continuation option",
    recoveryMethodOptionSiblingSceneHint: "sibling scene hint",
    recoveryMethodOptionSiblingSceneText: "sibling scene text branches",
    recoveryMethodOptionManualOverride: "manual override",
    sort: "Sort",
    sortNatural: "Type and name",
    sortStory: "Story order",
    sortLinesDesc: "Line count (high to low)",
    sortLinesAsc: "Line count (low to high)",
    sortKey: "Key (A-Z)",
    storyTodoTag: "TODO",
    storyTodoText: "Recover scene orders within a mission",
    storyTriggerHeading: "Story trigger",
    storyTriggerListLabel: "Trigger",
    storyTriggerLoading: "Loading original-data trigger evidence",
    storyTriggerUnavailable: "Trigger evidence data is unavailable",
    storyTriggerUnknown: "Playback trigger not recovered from original game data",
    storyTriggerNativePlayback: "Original-data playback trigger",
    storyTriggerNativePlaybackUnresolved: "Original-data playback trigger (mission owner unresolved)",
    storyTriggerPlayback: "Mission/quest playback trigger",
    storyTriggerPlaybackUnresolved: "Playback trigger (owner unresolved)",
    storyTriggerCondition: "Playback trigger not recovered; this file is used as a quest condition",
    storyTriggerContext: "Playback trigger not proven; mission/quest context only",
    storyTriggerContextOwnerUnresolved: "Exact carrier context; mission/quest owner unresolved",
    storyTriggerDependency: "Playback trigger not recovered; dependency only",
    storyTriggerDefinition: "No runtime consumer recovered; definition only",
    storyTriggerOfflineExhausted: "Current-build offline carrier search exhausted; no owner or order edge",
    storyTriggerNonMissionContent: "Non-mission content (authored table or tutorial asset)",
    storyTriggerAmbientWorldContent: "Ambient world content (no mission owner)",
    storyTriggerExactPaths: "exact paths",
    storyTriggerEvent: "Event",
    storyTriggerAction: "Action",
    storyTriggerOwner: "Owner",
    storyTriggerRoute: "Evidence route",
    storyTriggerSource: "Original source",
    storyTriggerSelector: "Selector",
    storyTriggerOwnershipContext: "Playback path exact; mission ownership is context only",
    storyOrderBadgeTitle: "Recovered game-data order",
    storyOrderLockMission: "Lock",
    storyOrderUnlockMission: "Unlock",
    storyOrderMissionLocked: "Locked",
    storyOrderMissionEditable: "Editable",
    storyOrderLockMissionTitle: "Editable 鈥?click to lock this mission and disable manual reordering",
    storyOrderUnlockMissionTitle: "Locked 鈥?click to unlock so you can drag rows to reorder",
    storyOrderMoveUnusedToEnd: "unused 鈫?end",
    storyOrderMoveUnusedToEndTitle: "Move every \"possibly unused\" entry in this mission to the bottom of its order",
    storyOrderMoveUnusedToEndNone: "No entries are marked \"possibly unused\" in this mission",
    storyOrderDragHandle: "Drag to reorder",
    storyOrderConfStrong: "source-backed",
    storyOrderConfWeak: "weak",
    storyOrderConfGuess: "guess",
    storyOrderConfTitle: "Recovered order confidence:",
    storyOrderPhasePrefix: "P",
    storyOrderPhaseTitle: "Quest phase (coarse order bucket)",
    storyOrderUnverifiedBadge: "unverified",
    storyOrderUnverifiedTitle: "Order not human-verified (may be OCR/auto-recovered; treated as untrusted by policy)",
    storyOrderReviewJump: "review",
    storyOrderReviewJumpTitle: "Jump to the next low-confidence row needing human confirmation",
    storyOrderCompareTitle: "Story order compare",
    storyOrderCompareCurrent: "Current override",
    storyOrderCompareRecovered: "Static recovery",
    storyOrderCompareOcr: "OCR",
    storyOrderOcrRankTitle: "data/story_order_ocr.json OCR rank",
    storyOrderCompareAdopt: "Adopt",
    storyOrderCompareLocked: "Mission locked",
    storyOrderCompareLoading: "Loading",
    storyOrderCompareMissing: "Not generated",
    storyOrderCompareIdentical: "matches current",
    storyOrderCompareDiff: "{moved} moved / {missing} missing / {added} added",
    storyOrderCompareCount: "{count} entries",
    storyOrderCompareMore: "+{count}",
    storyOrderCompareBaseline: "Story list",
    storyOrderBuilderTitle: "Override draft",
    storyOrderMatrixTitle: "Source items",
    storyOrderMatrixItem: "Item",
    storyOrderBuilderUseSource: "Use {source}",
    storyOrderBuilderAppendSource: "+ {source}",
    storyOrderBuilderSave: "Save override",
    storyOrderBuilderReset: "Reset draft",
    storyOrderBuilderClear: "Clear",
    storyOrderBuilderAdd: "Add",
    storyOrderBuilderRemove: "Remove",
    storyOrderBuilderSelect: "Select",
    storyOrderBuilderSelectAll: "Select all",
    storyOrderBuilderClearSelection: "Clear selection",
    storyOrderBuilderSelectedCount: "{count} selected",
    storyOrderBuilderMoveTop: "Top",
    storyOrderBuilderMoveUp: "Move up",
    storyOrderBuilderMoveDown: "Move down",
    storyOrderBuilderMoveBottom: "Bottom",
    storyOrderBuilderMoveHere: "Move here",
    storyOrderBuilderRemoveSelected: "Remove selected",
    storyOrderBuilderEmpty: "Draft is empty",
    storyOrderSaveSaving: "Saving",
    storyOrderSaveSaved: "Saved",
    storyOrderSaveFailed: "Save failed",
    storyOrderPossiblyUnusedBadge: "possibly unused",
    storyOrderPossiblyUnusedTitle: "Marked as possibly not used in the final game",
    storyAutomaticUnusedBadge: "unused",
    storyAutomaticUnusedTitle: "The complete current-build playback-carrier scan found no evidence that uses this cutscene",
    storyOrderBranchBadge: "branch",
    storyOrderBranchTitle: "Marked as a branch story entry",
    storyOrderTagMarkBranch: "mark branch",
    storyOrderTagMarkUnused: "mark unused",
    storyOrderTagClear: "clear tag",
    storyOrderTagMarkBranchTitle: "Mark this entry as a branch story file",
    storyOrderTagMarkUnusedTitle: "Mark this entry as possibly not used in the final game",
    storyOrderTagClearTitle: "Clear the branch / possibly unused tag",
    storyOrderUnusedMark: "mark unused",
    storyOrderUnusedClear: "unused",
    storyOrderUnusedMarkTitle: "Mark this entry as possibly not used in the final game",
    storyOrderUnusedClearTitle: "Clear the \"possibly unused\" flag",
    storyOrderRemoveFromMission: "remove from mission",
    storyOrderRemoveFromMissionTitle: "Filename does not contain mission code {mission} 鈥?click to remove it from this mission's order",
    reset: "Reset filters",
    listUnit: "items",
    lineUnit: "lines",
    emptyConversation: "Choose a conversation from the left",
    revealCurrent: "Reveal current file",
    showEmpty: "Show empty rows",
    showRaw: "Show raw JSON / text sources",
    showDebug: "Show debug info",
    inlineTagMode: "Show raw tags",
    genderVariant: "Endministrator variant",
    genderVariantFemale: "Female",
    genderVariantMale: "Male",
    genderVariantNote: "Dialogue text, voice, images, video, and gender-specific cutscenes follow this selection and stay synchronized with Gameplay.",
    showFilters: "Show filters",
    hideFilters: "Hide filters",
    loading: "Loading...",
    loadErrorPrefix: "Load error: ",
    emptyPreview: "(no preview)",
    systemSpeaker: "(System)",
    radioSpeaker: "(Radio)",
    linkedMission: "Linked mission",
    summary: "Scene Summary",
    hints: "Annotations",
    metadata: "Metadata",
    sourceEvidence: "Source Evidence",
    sourceEvidenceMore: "{count} more",
    narrativeVideo: "Narrative Video",
    narrativeVideoMore: "{count} more videos",
    narrativeVideoInlineLabel: "Video",
    recoveredAudio: "Recovered Audio",
    dialogLifecycleAudio: "Dialog lifecycle audio",
    dialogLifecycle_preloadEvents: "Preload",
    dialogLifecycle_postEnterEvents: "After dialog entry",
    dialogLifecycleAudioNote: "The dialog id and lifecycle phase are exact authored configuration; runtime dispatch, Wwise branch selection, and playback remain unobserved.",
    recoveredAudioMedia: "media",
    recoveredAudioBytes: "bytes",
    wikiImages: "Images",
    wikiMedia: "Media",
    missionNotes: "Mission Notes",
    missionTimelineRecovery: "Mission Timeline Recovery",
    missionTimelineQuests: "quests",
    missionTimelineBranches: "branches",
    missionTimelineEdges: "scene edges",
    missionTimelineQuestSpatialTrack: "Quest Map Track",
    missionTimelineSpatialHint: "Map/resource metadata is a diagnostic placement hint.",
    missionTimelineSourceScripts: "source scripts",
    missionTimelineSpatialCandidates: "spatial candidates",
    missionTimelineSpatialMatches: "spatial matches",
    cutsceneInfo: "Cutscene Info",
    cutscenePlacement: "Placement",
    cutsceneVariants: "Variants",
    cutsceneVideos: "Videos",
    cutscenePaths: "Paths",
    cutsceneMetadata: "Metadata",
    cutsceneShapeUnityTimeline: "Unity real-time cutscene",
    cutsceneShapeUnityTimelineWithIndependentFmv: "Real-time cutscene + separate FMV",
    cutsceneShapeTimelineComponentsWithoutRoot: "Cutscene components (root missing)",
    cutsceneShapeLevelscriptFmv: "Pre-rendered narrative video",
    cutsceneShapeTextOnlyUnconfirmed: "Text-only candidate",
    cutsceneShapeUnityTimelineHint: "A Unity Timeline root and its authored cutscene components were recovered. This is authored structure, not proof of execution in a gameplay session.",
    cutsceneShapeUnityTimelineWithIndependentFmvHint: "This Story row has both a Unity Timeline and a separate LevelScript video playback request. Their containment and relative order are not yet proven.",
    cutsceneShapeTimelineComponentsWithoutRootHint: "Actor/Audio/Effect/Light/Others child Timelines exist, but the corresponding root definition is absent from the current export, so this is not treated as a complete playable cutscene.",
    cutsceneShapeLevelscriptFmvHint: "An exact LevelScript PlayFmvAction targets this pre-rendered video; it is not a Unity Timeline cutscene root.",
    cutsceneShapeTextOnlyUnconfirmedHint: "Only localized cutscene-named text was found; no cutscene asset, narrative video, or exact source link currently confirms a playable scene.",
    cutsceneLocalizedTextWithoutTrack: "Subtitle timing unrecovered",
    cutsceneLocalizedTextWithoutTrackHint: "Localized text exists, but no authored subtitle track places it on the cutscene timeline.",
    missionTimelineSceneGraph: "Scene Edge Graph",
    missionTimelineEdgeList: "Edge list",
    missionTimelineComponent: "Component",
    missionTimelineNodes: "nodes",
    missionTimelineEvidence: "timeline evidence",
    missionTimelineUnresolved: "unresolved",
    missionTimelineSource: "source",
    missionTimelineObjectives: "objectives",
    missionTimelineObjectiveInstructions: "instructions",
    missionTimelineScenes: "scenes",
    missionTimelineResources: "resources",
    missionTimelineMapPins: "map pins",
    missionTimelineGraphLinks: "scene links",
    missionTimelineFlow: "flow",
    missionTimelinePrev: "prev",
    timelineActions: "Timeline Actions",
    timelineActionsStatus: "action order",
    timelineActionsTimelineStatus: "Timeline order",
    timelineActionsFlows: "flows",
    timelineActionsLines: "lines",
    timelineActionsLinked: "linked actions",
    timelineActionsDecoded: "decoded",
    timelineActionsUnparsed: "unparsed",
    timelineActionsKinds: "kinds",
    timelineActionsLayouts: "layouts",
    timelineActionsLineDetails: "Line actions",
    timelineActionsMore: "{count} more line(s)",
    timelineActionsStatusAgrees: "agrees",
    timelineActionsStatusPartial: "partial",
    timelineActionsStatusConflict: "conflict",
    timelineActionsStatusMissingTimeline: "missing Timeline order",
    timelineActionsStatusMissingAction: "missing action order",
    timelineActionsStatusMissing: "missing",
    lineOrderRecovery: "Line-Order Recovery",
    lineOrderNotNeeded: "Single-line scene; explicit line-order recovery is not needed.",
    lineOrderMissing: "No explicit line-order recovery was found for this scene.",
    lineOrderModeDialogTree: "direct dialogTree order",
    lineOrderModeDialogTreeFragment: "authored order via dialogTreeFragment",
    lineOrderModeDialogTreeExtraConfig: "authored order via dialogTreeExtraConfig",
    lineOrderModeDialogTreeCinematicTimeline: "dialogTree cinematic timeline stitch",
    lineOrderModeAuthoredBlend: "authored blend",
    lineOrderModeAuthoredNumericStitch: "authored numeric stitch",
    lineOrderModeDialogTimeline: "authored order via dialogTimeline",
    lineOrderModeCompoundNumericSuffix: "compound numeric suffix stitch",
    lineOrderModeLineIdSuffix: "fallback line order",
    lineOrderModeRuntimeRowIteration: "runtime row iteration",
    lineOrderModeUnregisteredScene: "not registered in DialogIdTable",
    lineOrderRegistryRegistered: "DialogIdTable: registered",
    lineOrderRegistryUnregistered: "DialogIdTable: not registered",
    lineOrderRegistryTrunks: "DialogIdTable: {trunks} trunk(s) / {lines} line ref(s)",
    lineOrderRegistryDeltaPositive: "DialogIdTable: +{count} webui line(s)",
    lineOrderRegistryDeltaNegative: "DialogIdTable: -{count} webui line(s)",
    lineOrderModeFallback: "fallback order",
    lineOrderModeMissing: "missing line-order block",
    lineOrderConfirmed: "kept current order",
    lineOrderReordered: "reordered {moved}/{total}",
    lineOrderSource: "Source",
    lineOrderCoverage: "covers {count} line(s)",
    lineOrderTree: "DialogTree",
    lineOrderTreeContribution: "Recovered line path",
    lineOrderSequence: "Final emitted order",
    lineOrderPreviewEmpty: "(no text preview)",
    lineOrderFile: "File",
    lineOrderConversationFlow: "Recovered conversation flow",
    lineOrderConversationFlowNote: "This merges the recovered trunk lines, anchored option groups, and sceneGraphLinks jumps/loopbacks into one readable dialogTree conversation.",
    lineOrderBeforeScene: "before scene",
    lineOrderAfterLine: "after",
    lineOrderPlacementUncertain: "placement uncertain",
    lineOrderPlacementUnknown: "placement unknown",
    lineOrderOption: "Option",
    lineOrderCommonContinuation: "shared continuation",
    lineOrderContinueInScene: "continues in scene",
    lineOrderJumpToScene: "jumps to scene",
    lineOrderLoopToLine: "loops back to earlier line",
    lineOrderLoopToScene: "re-enters current scene",
    lineOrderSubmenu: "Submenu",
    lineOrderTerminal: "Terminal",
    lineOrderPathLineIds: "Path line IDs",
    lineOrderOutcome: "Outcome",
    lineOrderMethod: "Recovery method",
    lineOrderLineIdReference: "Line ID order",
    lineOrderLineIdReferenceNote: "",
    lineOrderDiffersFromLineIdOrder: "differs from line ID order",
    lineOrderAddedCount: "added {count}",
    lineOrderModeDetailDialogTree: "Recovered from the current scene's DialogTree trunk and branch traversal.",
    lineOrderModeDetailDialogTreeFragment: "Borrowed authored ordering from other DialogTree fragments that point into this scene.",
    lineOrderModeDetailDialogTreeExtraConfig: "Used the authored ordering declared in extra_config.",
    lineOrderModeDetailDialogTreeCinematicTimeline: "Inserted local Timeline dialog clips at their parent DialogTree cinematic nodes.",
    lineOrderModeDetailAuthoredBlend: "Merged multiple authored sources by coverage and priority.",
    lineOrderModeDetailAuthoredNumericStitch: "The main DialogTree supplies partial order; numeric suffixes place the uncovered gap rows back into the sequence.",
    lineOrderModeDetailDialogTimeline: "Used the authored ordering recorded in dialogTimeline.",
    lineOrderModeDetailLineIdSuffix: "No usable authored line-order source was recovered for this scene.",
    lineOrderModeDetailFallback: "Recovered order via fallback strategy {mode}.",
    optionGroup: "Option Group {group}",
    relatedScenesHeading: "Shared Unity Timeline",
    gameplayLinkHeading: "Gameplay Data",
    openGameplayData: "Open in Gameplay",
    archiveLinksHeading: "Archive Links",
    archiveReports: "Reports",
    archiveMaterials: "Connected Files",
    archiveDuplicateDocuments: "Matching Archive Files",
    archivePopupTexts: "Popup Text",
    archiveMissionFiles: "Mission Files",
    branchHintLabel: "jumps to",
    optTargetMenu: "Menu {g}",
    optTargetReturnsToMenu: "back to Menu {g}",
    optTargetSelfMenu: "repeats this menu",
    optTargetScene: "{key}",
    optTargetSceneSubmenu: "submenu {key}",
    optTargetTerminal: "ends story",
    optJumpLine: "-> {line}",
    optJumpLineTitle: "First line entered by this option: {line}.",
    optJumpLineTree: "tree -> {line}",
    optJumpLineTitleTree: "DialogTree explicitly points this option to {line}.",
    optJumpLineTimeline: "timeline -> {line}",
    optJumpLineTitleTimeline: "Runtime Jump Track recovers this option path's first line: {line}.",
    optJumpLineShared: "shared -> {line}",
    optJumpLineTitleShared: "All options converge to the same continuation line: {line}.",
    optJumpLineInferred: "inferred -> {line}",
    optJumpLineTitleInferred: "The target line is inferred from Timeline order: {line}.",
    optJumpLoopLine: "loop {line}",
    optJumpLoopLineTitle: "This option path returns to the beginning of the loop after {line}.",
    optTargetAccessedFrom: "from",
    optRiskRawIndexMatchedLine: "index matched",
    optRiskRawIndexMatchedLineTitle: "The source data does not name an explicit target line for this option, but Timeline raw optionIndex matches the option index and recovers the reply at {line}. This is still recovered inference, but stronger than adjacent-line inference.",
    optRiskInferredFollowingLine: "inferred reply",
    optRiskInferredFollowingLineTitle: "The source data does not name an explicit target line for this option; Timeline order suggests it may correspond to {line}.",
    optManualOverride: "manual override",
    optManualOverrideTitle: "This result comes from a local manual override file: {source}{note}",
    preDialogOptions: "Dialogue Options (Before Scene)",
    uncertainDialogOptions: "Dialogue Options (Placement Uncertain)",
    orphanDialogOptions: "Dialogue Options (Unknown Position)",
    radio: "Radio",
    envTalk: "Ambient Talk",
    warningTitle: "Display Warning",
    warningInferredOptionLayoutTitle: "Option placement note",
    warningInferredOptionLayoutBody: "Every option group is shown at its recovered position. The note below distinguishes table-key matches, line-gap recovery, end-of-scene fallback, and any truly unknown position.",
    optionPlacementKeyMatched: "table-key position",
    optionPlacementSparseGap: "line-gap position",
    optionPlacementSiblingTimeline: "sibling-scene position",
    optionPlacementLastLine: "end fallback",
    optionPlacementUnknown: "position unknown",
    warningInferredOptionResponseTitle: "Option reply note",
    warningInferredOptionResponseBody: "Some option reply lines are inferred from Timeline order.",
    warningDuplicateTimestampsTitle: "Timestamp note",
    warningDuplicateTimestampsBody: "Multiple lines in this scene render with the same timeline timestamp, which may indicate a Timeline recovery conflict.",
    warningDuplicateTimestampLines: "Duplicate lines",
    warningTimelineTimestampRegressionTitle: "Timeline order note",
    warningTimelineTimestampRegressionBody: "Recovered Timeline timestamps move backward in the current line order. A secondary Timeline may be local stitch evidence rather than absolute scene time.",
    warningTimelineTimestampRegressionLines: "Regression lines",
    warningNarrativeVideoUnplacedTitle: "Video timeline position unknown",
    warningNarrativeVideoUnplacedBody: "Narrative video is bound to this scene, but no timeline position was recovered. The file is listed below for reference only.",
    warningRemotecommNarrativeVideoMissingTitle: "RemoteComm video missing",
    warningRemotecommNarrativeVideoMissingBody: "Source data points to these RemoteComm video segments, but no matching MP4 files were exported.",
    warningSceneOrderDisorderTitle: "Order note",
    warningSceneOrderDisorderBody: "Scene order or option placement is not fully authored here.",
    warningAspectLineOrder: "Line order",
    warningAspectOptionLayout: "Option placement",
    warningStatusDirect: "authored order present",
    warningStatusPartial: "partial coverage",
    warningStatusFallback: "fallback recovery",
    warningStatusMissing: "missing order block",
    warningStatusAuthored: "authored anchors present",
    warningStatusInferred: "placement inferred",
    warningStatusNotNeeded: "not needed",
    warningLineOrderSummaryLineIdSuffix: "no authored line order found",
    warningLineOrderDetailLineIdSuffix: "",
    warningLineOrderSummaryMissing: "no line-order data found",
    warningLineOrderDetailMissing: "",
    warningLineOrderSummaryFallback: "using fallback line order",
    warningLineOrderDetailFallback: "",
    warningLineOrderSummaryPartial: "authored order covers only part of the scene",
    warningLineOrderDetailPartial: "",
    lineOrderUncoveredCount: "{count} line(s) not covered",
    lineOrderUncoveredLines: "Uncovered lines",
    lineOrderUncoveredBadge: "uncovered",
    duplicateTimestampBadge: "Duplicate timestamp",
    warningOptionLayoutSummaryNoTreeReference: "option positions lack authored anchors",
    warningOptionLayoutDetailNoTreeReference: "",
    warningOptionLayoutSummaryNoAuthoredGroupAnchor: "option positions are missing authored anchors",
    warningOptionLayoutDetailNoAuthoredGroupAnchor: "",
    warningOptionLayoutSummaryPartialAuthoredCoverage: "only part of the option layout is authored",
    warningOptionLayoutDetailPartialAuthoredCoverage: "",
    warningOptionLayoutSummaryInferred: "option placement is inferred",
    warningOptionLayoutDetailInferred: "",
  },
};

const KIND_LABELS = {
  zh: {
    dlg: { name: "\u5267\u60c5\u5bf9\u8bdd", cls: "badge-dlg" },
    sns: { name: "\u7ec8\u7aef\u6d88\u606f", cls: "badge-sns" },
    cutscene: { name: "\u8fc7\u573a\u6f14\u51fa", cls: "badge-cutscene" },
    video: { name: "\u5267\u60c5\u89c6\u9891", cls: "badge-video" },
    cg: { name: "\u5267\u60c5CG", cls: "badge-video" },
    black: { name: "\u9ed1\u5c4f\u5b57\u5e55", cls: "badge-black" },
    remotecomm: { name: "\u8fdc\u7a0b\u901a\u8bdd", cls: "badge-remotecomm" },
    radio: { name: "\u8bed\u97f3\u901a\u8baf", cls: "badge-radio" },
    text: { name: "\u5f39\u51fa\u6587\u672c", cls: "badge-text" },
    reading: { name: "\u5f55\u97f3", cls: "badge-reading" },
    mail: { name: "\u90ae\u4ef6", cls: "badge-mail" },
    prts: { name: "\u6863\u6848\u5e93", cls: "badge-prts" },
    wiki: { name: "\u63cf\u8ff0\u6587\u672c", cls: "badge-wiki" },
    responsive: { name: "\u4eba\u7269\u53cd\u5e94", cls: "badge-responsive" },
    env: { name: "\u73af\u5883\u4f1a\u8bdd", cls: "badge-env" },
    misc: { name: "\u6742\u9879", cls: "badge-misc" },
  },
  en: {
    dlg: { name: "Story", cls: "badge-dlg" },
    sns: { name: "Terminal Message", cls: "badge-sns" },
    cutscene: { name: "Cutscene", cls: "badge-cutscene" },
    video: { name: "Video", cls: "badge-video" },
    cg: { name: "CG Image", cls: "badge-video" },
    black: { name: "Black Screen", cls: "badge-black" },
    remotecomm: { name: "Remote Comm", cls: "badge-remotecomm" },
    radio: { name: "Radio", cls: "badge-radio" },
    text: { name: "Popup Text", cls: "badge-text" },
    reading: { name: "Recording", cls: "badge-reading" },
    mail: { name: "Mail", cls: "badge-mail" },
    prts: { name: "Archive", cls: "badge-prts" },
    wiki: { name: "Text Description", cls: "badge-wiki" },
    responsive: { name: "Character Reactions", cls: "badge-responsive" },
    env: { name: "Ambient Talk", cls: "badge-env" },
    misc: { name: "Misc", cls: "badge-misc" },
  },
};

const STRUCTURED_LABEL_ACRONYMS = {
  ai: "AI",
  db: "DB",
  dm: "DM",
  gm: "GM",
  id: "ID",
  npc: "NPC",
  prts: "Archive",
  sns: "SNS",
  ui: "UI",
};

const SPECIAL_SIM_ACTOR_IDS = new Set(["endmin", "endminf", "endminm"]);
const PRTS_CATEGORY_KEYS = new Set(["collection", "digital", "document", "media", "paper", "report", "research_report"]);
// Keep PRTS categories aligned with the metadata-tag reading order.
const PRTS_CATEGORY_ORDER = ["collection", "document", "paper", "digital", "media", "report", "research_report"];
const PRTS_PAGE_CATEGORY_PRIORITY = ["report", "paper", "digital", "document", "collection", "media", "research_report"];
const PRTS_CATEGORY_ALIASES = {
  multi_media: "media",
};
const PRTS_CATEGORY_DISPLAY_LABELS = {
  zh: {
    collection: "\u6863\u6848\u5e93 - \u85cf\u54c1",
    digital: "\u6863\u6848\u5e93 - \u7535\u5b50\u6863\u6848",
    document: "\u6863\u6848\u5e93 - \u4e2d\u67a2\u6863\u6848",
    media: "\u6863\u6848\u5e93 - \u591a\u5a92\u4f53",
    paper: "\u6863\u6848\u5e93 - \u7eb8\u8d28\u8bb0\u5f55",
    report: "\u6863\u6848\u5e93 - \u62a5\u544a",
    research_report: "\u6863\u6848\u5e93 - \u62a5\u544a",
  },
  en: {
    collection: "Archive - Peculiars",
    digital: "Archive - E-Files",
    document: "Archive - Nexus Files",
    media: "Archive - Multimedia",
    paper: "Archive - Manuscripts",
    report: "Archive - Reports",
    research_report: "Archive - Reports",
  },
};

const WORLD_TEXT_TYPE_KEYS = new Set(["env", "map", "settlement", "worldtext", "tablefamily:worldtext", "prtscat:collection"]);
const OTHER_TYPE_FAMILIES = new Set([
  "activity", "battlepass", "cashshop", "dungeon", "enemy", "error", "factory",
  "gachapool", "gamemechanic", "generalability", "instruction", "loading",
  "richcontent", "spaceship", "text",
]);

const TABLE_TYPE_FAMILY_RULES = [
  { prefix: "battlepass", family: "battlepass" },
  { prefix: "gamesystem", family: "system" },
  { prefix: "systemjump", family: "item" },
  { prefix: "gamemechanic", family: "gamemechanic" },
  { prefix: "richcontent", family: "richcontent" },
  { prefix: "errorcode", family: "error" },
  { prefix: "instructionbook", family: "instruction" },
  { prefix: "intro", family: "instruction" },
  { prefix: "loading", family: "loading" },
  { prefix: "weekraid", family: "dungeon" },
  { prefix: "worldenergy", family: "worldtext" },
  { prefix: "qualitysubsetting", family: "quality" },
  { prefix: "useitem", family: "item" },
  { prefix: "aibark", family: "aibark" },
  { prefix: "activity", family: "activity" },
  { prefix: "achievement", family: "achievement" },
  { prefix: "adventure", family: "battlepass" },
  { prefix: "attribute", family: "gamemechanic" },
  { prefix: "cashshop", family: "cashshop" },
  { prefix: "recharge", family: "cashshop" },
  { prefix: "character", family: "gamemechanic" },
  { prefix: "chargrowth", family: "gamemechanic" },
  { prefix: "char", family: "gamemechanic" },
  { prefix: "checkin", family: "checkin" },
  { prefix: "doodad", family: "worldtext" },
  { prefix: "distribution", family: "worldtext" },
  { prefix: "dialog", family: "dialog" },
  { prefix: "displayenemytype", family: "enemy" },
  { prefix: "domain", family: "worldtext" },
  { prefix: "dungeon", family: "dungeon" },
  { prefix: "enemy", family: "enemy" },
  { prefix: "equip", family: "item" },
  { prefix: "fac", family: "factory" },
  { prefix: "factory", family: "factory" },
  { prefix: "friendchat", family: "friendchat" },
  { prefix: "foodsubmitstageid", family: "activity" },
  { prefix: "gachacharpool", family: "gachapool" },
  { prefix: "giftpackcashshop", family: "cashshop" },
  { prefix: "gacha", family: "gachapool" },
  { prefix: "gamepad", family: "gamepad" },
  { prefix: "gem", family: "gamemechanic" },
  { prefix: "highdifficulty", family: "activity" },
  { prefix: "ethersubmitbuffshow", family: "worldtext" },
  { prefix: "hyperlink", family: "instruction" },
  { prefix: "importantreward", family: "item" },
  { prefix: "item", family: "item" },
  { prefix: "kitestation", family: "worldtext" },
  { prefix: "level", family: "dungeon" },
  { prefix: "mail", family: "mail" },
  { prefix: "map", family: "worldtext" },
  { prefix: "missionextra", family: "mission" },
  { prefix: "money", family: "money" },
  { prefix: "picture", family: "picture" },
  { prefix: "planting", family: "worldtext" },
  { prefix: "potential", family: "potential" },
  { prefix: "prtsdocument", family: "prtsdocument" },
  { prefix: "prts", family: "prts" },
  { prefix: "radio", family: "radio" },
  { prefix: "readingpopup", family: "reading" },
  { prefix: "recyclebin", family: "worldtext" },
  { prefix: "socialbuilding", family: "social" },
  { prefix: "settlement", family: "worldtext" },
  { prefix: "skill", family: "gamemechanic" },
  { prefix: "shop", family: "worldtext" },
  { prefix: "snapshot", family: "generalability" },
  { prefix: "sns", family: "sns" },
  { prefix: "spaceship", family: "spaceship" },
  { prefix: "submititem", family: "worldtext" },
  { prefix: "system", family: "system" },
  { prefix: "tag", family: "tag" },
  { prefix: "text", family: "text" },
  { prefix: "training", family: "training" },
  { prefix: "generalability", family: "generalability" },
  { prefix: "weapon", family: "wiki" },
  { prefix: "wiki", family: "wiki" },
];

const TABLE_TYPE_FAMILY_LABELS = {
  zh: {
    activity: "\u6d3b\u52a8\u6587\u672c",
    achievement: "\u8680\u523b\u7ae0",
    adventure: "\u5192\u9669",
    aibark: "AI Bark",
    attribute: "\u5c5e\u6027",
    battlepass: "\u901a\u884c\u8bc1\u6587\u672c",
    cashshop: "\u5546\u57ce",
    character: "\u5e72\u5458\u6218\u6597\u6587\u672c",
    checkin: "\u7b7e\u5230",
    dialog: "\u5bf9\u8bdd",
    domain: "\u533a\u57df\u7b49\u7ea7\u4e0e\u8d27\u8fd0\u6587\u672c",
    dungeon: "\u526f\u672c",
    enemy: "\u654c\u4eba",
    equip: "\u88c5\u5907",
    error: "\u9519\u8bef",
    factory: "\u96c6\u6210\u5de5\u4e1a\u6587\u672c",
    distribution: "\u5206\u53d1",
    doodad: "\u6446\u4ef6",
    friendchat: "\u597d\u53cb\u804a\u5929",
    gachapool: "\u62bd\u5361\u6c60\u6587\u672c",
    giftpackcashshop: "\u793c\u5305\u5546\u5e97\u6587\u672c",
    gamepad: "\u624b\u67c4\u64cd\u4f5c\u6587\u672c",
    generalability: "\u4e00\u822c\u80fd\u529b",
    gem: "\u57fa\u8d28",
    gamemechanic: "\u6e38\u620f\u673a\u5236",
    hyperlink: "\u8d85\u94fe\u63a5\u6587\u672c",
    importantreward: "\u8d35\u91cd\u5956\u52b1\u6587\u672c",
    instruction: "\u6307\u5357",
    item: "\u7269\u54c1",
    kitestation: "\u73af\u5883\u76d1\u6d4b\u7ad9\u6587\u672c",
    level: "\u5173\u5361",
    loading: "\u63d0\u793a",
    mail: "\u90ae\u4ef6",
    map: "\u5730\u56fe",
    mission: "\u4efb\u52a1",
    money: "\u8c03\u5ea6\u5238\u53d8\u5316\u6587\u672c",
    picture: "\u56fe\u7247",
    planting: "\u79cd\u690d\u6587\u672c",
    potential: "\u6f5c\u80fd",
    prtsdocument: "\u6863\u6848\u5e93",
    prts: "\u6863\u6848\u5e93",
    radio: "\u65e0\u7ebf\u7535",
    quality: "\u753b\u8d28",
    reading: "\u5f55\u97f3",
    recycle: "\u56de\u6536",
    richcontent: "\u5bcc\u6587\u672c",
    settlement: "\u805a\u843d",
    skill: "\u6e38\u620f\u673a\u5236",
    shop: "\u5546\u5e97",
    snapshot: "\u4e00\u822c\u80fd\u529b",
    social: "\u793e\u4ea4",
    sns: "\u7ec8\u7aef\u804a\u5929\u4f1a\u8bdd\u540d",
    spaceship: "\u5e1d\u6c5f\u53f7\u6587\u672c",
    system: "\u7cfb\u7edf",
    systemjump: "\u7269\u54c1\u83b7\u53d6\u6e20\u9053\u6587\u672c",
    tag: "\u6807\u7b7e",
    text: "\u6587\u672c",
    training: "\u8bad\u7ec3",
    weapon: "\u6b66\u5668",
    weekraid: "\u5468\u5e38\u526f\u672c",
    wiki: "\u767e\u79d1",
    worldenergy: "\u4e16\u754c\u80fd\u91cf",
    worldtext: "\u5927\u4e16\u754c",
  },
  en: {
    activity: "Activity Text",
    achievement: "Achievement",
    adventure: "Adventure",
    aibark: "AI Bark",
    attribute: "Attribute",
    battlepass: "Battle Pass Text",
    cashshop: "Cash Shop",
    character: "Operator Combat Text",
    checkin: "Check-In",
    dialog: "Dialog",
    domain: "Area Level and Freight Text",
    dungeon: "Dungeon",
    enemy: "Enemy",
    equip: "Equipment",
    error: "Error",
    factory: "Integrated Industry Text",
    distribution: "Distribution",
    doodad: "Doodad",
    friendchat: "Friend Chat",
    gachapool: "Gacha Pool Text",
    giftpackcashshop: "Gift Pack Shop Text",
    gamepad: "Gamepad Operation Text",
    generalability: "General Ability",
    gem: "Substrate",
    gamemechanic: "Game Mechanic",
    hyperlink: "Hyperlink Text",
    importantreward: "Important Reward Text",
    instruction: "Instruction",
    item: "Item",
    kitestation: "Environmental Monitoring Station Text",
    level: "Level",
    loading: "Tip",
    mail: "Mail",
    map: "Map",
    mission: "Mission",
    money: "Dispatch Ticket Change Text",
    picture: "Picture",
    planting: "Planting Text",
    potential: "Potential",
    prtsdocument: "Archive",
    prts: "Archive",
    radio: "Radio",
    quality: "Quality",
    reading: "Recording",
    recycle: "Recycle",
    richcontent: "Rich Content",
    settlement: "Settlement",
    skill: "Game Mechanic",
    shop: "Shop",
    snapshot: "General Ability",
    social: "Social",
    sns: "Terminal Chat Session Name",
    spaceship: "Dijiang Text",
    system: "System",
    systemjump: "Item Acquisition Channel Text",
    tag: "Tag",
    text: "Text",
    training: "Training",
    weapon: "Weapon",
    weekraid: "Weekly Raid",
    wiki: "Wiki",
    worldenergy: "World Energy",
    worldtext: "Open World",
  },
};

const DEFAULT_DATA_TYPE_KEY = "other";
const DEFAULT_METADATA_TAG_KEY = "other";

const DATA_TYPE_LABELS = {
  zh: {
    e: "\u4e3b\u7ebf\u4efb\u52a1 (e)",
    a: "\u6d3b\u52a8\u4efb\u52a1 (a)",
    c: "\u4e2a\u4eba\u4efb\u52a1 (c)",
    topic: "\u7ec8\u7aef\u804a\u5929",
    gm: "\u91cd\u8981\u4efb\u52a1 (gm)",
    sm: "\u6b21\u8981\u4efb\u52a1 (sm)",
    m: "\u65e5\u5e38\u4efb\u52a1 (m)",
    f: "\u57fa\u5efa\u636e\u70b9\u4efb\u52a1 (f)",
    db: "\u8680\u50cf\u5bfb\u9057 (db)",
    dm: "dm \u7cfb\u5217",
    indie: "\u72ec\u7acb\u573a\u666f (indie)",
    map: "\u5927\u4e16\u754c",
    sim: "\u5e72\u5458",
    timeline: "\u6a21\u62df\u7a7a\u95f4 (blackbox)",
    env: "\u5927\u4e16\u754c",
    sns: "\u7ec8\u7aef\u804a\u5929\u4f1a\u8bdd\u540d",
    mail: "\u90ae\u4ef6 (mail)",
    prts: "\u6863\u6848\u5e93",
    wiki: "\u767e\u79d1",
    eny: "Boss\u6218",
    responsive: "\u4eba\u7269\u53cd\u5e94",
    table_blocdatatable: "\u52bf\u529b\u540d\u79f0",
    table_commondeathtips: "\u63d0\u793a",
    table_compositeattributeshowconfigtable: "\u8bcd\u6761\u540d",
    table_displayenemytypetable: "\u654c\u4eba",
    table_ethersubmitbuffshowtable: "\u919a\u8d28\u63d0\u4ea4\u589e\u76ca",
    spaceship: "\u5e1d\u6c5f\u53f7\u6587\u672c",
    dungeon: "\u526f\u672c",
    worldtext: "\u5927\u4e16\u754c",
    task: "\u4efb\u52a1",
    test: "\u6d4b\u8bd5 (test)",
    blackbox: "Blackbox",
    other: "\u63cf\u8ff0\u6587\u672c",
    x: "\u63cf\u8ff0\u6587\u672c",
  },
  en: {
    e: "Main Story Mission (e)",
    a: "Event Mission (a)",
    c: "Character Story (c)",
    topic: "Terminal Chat",
    gm: "Major Mission (gm)",
    sm: "Minor Mission (sm)",
    m: "Daily Mission (m)",
    f: "Base Outpost Mission (f)",
    db: "db Series",
    dm: "dm Series",
    indie: "Indie",
    map: "Open World",
    sim: "Operator",
    timeline: "Blackbox (timeline)",
    env: "Open World",
    sns: "Terminal Chat Session Name",
    mail: "Mail",
    prts: "Archive",
    wiki: "Wiki",
    eny: "Boss Battle",
    responsive: "Character Reactions",
    table_blocdatatable: "Faction Names",
    table_commondeathtips: "Tip",
    table_compositeattributeshowconfigtable: "Attribute Terms",
    table_displayenemytypetable: "Enemy",
    table_ethersubmitbuffshowtable: "Ether Submission Buffs",
    spaceship: "Dijiang Text",
    dungeon: "Dungeon",
    worldtext: "Open World",
    task: "Task",
    test: "Test (test)",
    blackbox: "Blackbox",
    other: "Text Description",
    x: "Text Description",
  },
};

const MEDIA_TYPE_FILTER_KEYS = ["media:video", "media:image", "media:sticker", "media:emoji"];
const MEDIA_TYPE_TAG_BY_KEY = {
  "media:video": "mediaVideo",
  "media:image": "mediaImage",
  "media:sticker": "mediaSticker",
  "media:emoji": "mediaEmoji",
};
const MEDIA_TYPE_FILTER_LABELS = {
  zh: {
    "media:video": "\u542b\u89c6\u9891",
    "media:image": "\u542b\u56fe\u7247",
    "media:sticker": "\u542b\u8d34\u7eb8 (\u975e\u8868\u60c5)",
    "media:emoji": "\u542b\u8868\u60c5",
  },
  en: {
    "media:video": "Has video",
    "media:image": "Has image",
    "media:sticker": "Has sticker (not emoji)",
    "media:emoji": "Has emoji",
  },
};

const METADATA_TAG_ORDER = [
  "achievement",
  "archive",
  "growth",
  "skillPatch",
  "gameMechanic",
  "tutorialStep",
  "errorCode",
  "enemyAbility",
  "wikiType",
  "activity",
  "battlePass",
  "character",
  "dungeon",
  "enemy",
  "factory",
  "worldtext",
  "item",
  "money",
  "system",
  "systemJump",
  "document",
  "paper",
  "digital",
  "picture",
  "text",
  "summary",
  "sceneGraph",
  "graphFragment",
  "levelBinding",
  "envTalk",
  "radio",
  "cutscene",
  "other",
];

const METADATA_TAG_KEEP = new Set(METADATA_TAG_ORDER);

const METADATA_TAG_LABELS = {
  zh: {
    achievement: "\u8680\u523b\u7ae0",
    archive: "\u6863\u6848",
    growth: "\u6210\u957f",
    skillPatch: "\u6280\u80fd\u8bcd\u6761",
    gameMechanic: "\u6e38\u620f\u673a\u5236",
    tutorialStep: "\u6559\u7a0b\u6b65\u9aa4",
    errorCode: "\u9519\u8bef\u7801",
    enemyAbility: "\u654c\u4eba\u80fd\u529b",
    wikiType: "\u767e\u79d1 (wiki)",
    activity: "\u6d3b\u52a8\u6587\u672c",
    battlePass: "\u901a\u884c\u8bc1\u6587\u672c",
    character: "\u5e72\u5458\u6218\u6597\u6587\u672c",
    dungeon: "\u526f\u672c",
    enemy: "\u654c\u4eba",
    factory: "\u5de5\u5382",
    worldtext: "\u5927\u4e16\u754c",
    item: "\u7269\u54c1",
    money: "\u8c03\u5ea6\u5238\u53d8\u5316\u6587\u672c",
    system: "\u7cfb\u7edf",
    systemJump: "\u7269\u54c1\u83b7\u53d6\u6e20\u9053\u6587\u672c",
    document: "\u6587\u6863",
    paper: "\u7eb8\u8d28\u8d44\u6599",
    digital: "\u6570\u5b57\u8d44\u6599",
    picture: "\u56fe\u50cf",
    text: "\u6587\u672c",
    summary: "\u6982\u8981",
    sceneGraph: "\u573a\u666f\u56fe",
    graphFragment: "\u56fe\u788e\u7247",
    levelBinding: "\u5173\u5361\u7ed1\u5b9a",
    envTalk: "\u73af\u5883\u5bf9\u8bdd",
    radio: "\u65e0\u7ebf\u7535",
    cutscene: "\u8fc7\u573a",
    responsive: "\u4eba\u7269\u53cd\u5e94",
    other: "\u5176\u5b83",
  },
  en: {
    achievement: "Achievement",
    archive: "Archive",
    growth: "Growth",
    skillPatch: "Skill Patch",
    gameMechanic: "Game Mechanic",
    tutorialStep: "Tutorial Step",
    errorCode: "Error Code",
    enemyAbility: "Enemy Ability",
    wikiType: "Wiki",
    activity: "Activity Text",
    battlePass: "Battle Pass Text",
    character: "Operator Combat Text",
    dungeon: "Dungeon",
    enemy: "Enemy",
    factory: "Factory",
    worldtext: "Open World",
    item: "Item",
    money: "Dispatch Ticket Change Text",
    system: "System",
    systemJump: "Item Acquisition Channel Text",
    document: "Document",
    paper: "Paper",
    digital: "Digital",
    picture: "Picture",
    text: "Text",
    summary: "Summary",
    sceneGraph: "Scene Graph",
    graphFragment: "Graph Fragment",
    levelBinding: "Level Binding",
    envTalk: "Ambient Talk",
    radio: "Radio",
    cutscene: "Cutscene",
    responsive: "Character Reactions",
    other: "Other",
  },
};

const STORY_ISSUE_ORDER = [
  "missingLineOrder",
  "fallbackLineOrder",
  "uncoveredLines",
  "duplicateTimestamps",
  "timelineTimestampRegression",
  "unanchoredOptionLayout",
  "tableOnlyOptionLayout",
  "lastLineOptionLayout",
  "gapOptionLayout",
  "keyedOptionLayout",
  "inferredOptionLayout",
  "inferredOptionResponse",
  "overrided",
  "notOverrided",
];

const STORY_RECOVERY_METHOD_ORDER = [
  "lineOrder:dialogTree",
  "lineOrder:dialogTreeFragment",
  "lineOrder:dialogTreeExtraConfig",
  "lineOrder:dialogTreeCinematicTimeline",
  "lineOrder:authoredBlend",
  "lineOrder:authoredNumericStitch",
  "lineOrder:dialogTimeline",
  "lineOrder:runtimeRowIteration",
  "lineOrder:unregisteredScene",
  "lineOrder:compoundNumericSuffix",
  "lineOrder:lineIdSuffix",
  "lineOrder:missing",
  "optionLayout:authored",
  "optionLayout:partialAuthoredCoverage",
  "optionLayout:fallback",
  "optionLayout:noAuthoredGroupAnchor",
  "optionLayout:tableOnlyCutContent",
  "optionLayout:keyMatched",
  "optionLayout:sparseGap",
  "optionLayout:siblingTimelinePosition",
  "optionLayout:lastLine",
  "optionLayout:unanchored",
  "optionBranch:sceneGraph",
  "optionBranch:dialogTreeFragment",
  "optionBranch:runtimeJump",
  "optionBranch:rawIndexMatched",
  "optionBranch:timelineAdjacent",
  "optionBranch:commonContinuation",
  "optionBranch:continuationOption",
  "optionBranch:siblingSceneText",
  "optionBranch:siblingSceneHint",
  "optionBranch:manualOverride",
];

function uiText(key) {
  const locale = UI_TEXTS[STATE.uiLocale] || UI_TEXTS.en;
  return locale[key] || UI_TEXTS.en[key] || key;
}

function localeTable(source) {
  return source[STATE.uiLocale] || source.en || {};
}

function localeValue(source, key, fallback = "") {
  const localeEntries = source[STATE.uiLocale] || {};
  const englishEntries = source.en || {};
  return localeEntries[key] || englishEntries[key] || fallback;
}

function kindLabels() {
  const localeLabels = localeTable(KIND_LABELS);
  const labels = { ...KIND_LABELS.en, ...localeLabels };
  if (!localeLabels.radio) labels.radio = { name: uiText("radio"), cls: "badge-radio" };
  return labels;
}

function dataTypeLabels() {
  return localeTable(DATA_TYPE_LABELS);
}

function formatStructuredLabel(value) {
  let raw = String(value || "").trim();
  if (!raw) return "Misc";
  if (raw.startsWith("table_")) raw = raw.slice("table_".length);
  raw = raw.replace(/^wiki_/, "");
  raw = raw.replace(/_/g, " ");
  raw = raw.replace(/(?<=[a-z0-9])(?=[A-Z])/g, " ");
  raw = raw.replace(/\s+/g, " ").trim();
  if (!raw) return "Misc";
  return raw
    .split(" ")
    .filter(Boolean)
    .map((part) => {
      const lower = part.toLowerCase();
      if (STRUCTURED_LABEL_ACRONYMS[lower]) return STRUCTURED_LABEL_ACRONYMS[lower];
      return lower.slice(0, 1).toUpperCase() + lower.slice(1);
    })
    .join(" ");
}

function tableTypeFamilyValue(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw) return "";
  if (raw.startsWith("tablefamily:")) return raw.slice("tablefamily:".length);
  if (!raw.startsWith("table_")) return "";
  const stem = raw.slice("table_".length);
  for (const rule of TABLE_TYPE_FAMILY_RULES) {
    if (stem.startsWith(rule.prefix)) return rule.family;
  }
  return "";
}

function tableTypeFamilyKey(value) {
  const family = tableTypeFamilyValue(value);
  return family ? `tablefamily:${family}` : "";
}

function tableTypeFamilyLabel(value) {
  const family = tableTypeFamilyValue(value);
  if (!family) return "";
  return localeValue(TABLE_TYPE_FAMILY_LABELS, family, formatStructuredLabel(family));
}

function prtsCategoryDisplayLabels() {
  return localeTable(PRTS_CATEGORY_DISPLAY_LABELS);
}

function kindMeta(kind) {
  const labels = kindLabels();
  if (labels[kind]) return labels[kind];
  const isTable = String(kind || "").startsWith("table_");
  return {
    name: isTable ? (labels.wiki?.name || formatStructuredLabel(kind)) : formatStructuredLabel(kind),
    cls: isTable ? "badge-wiki" : "badge-misc",
  };
}

function prtsCategoryLabel(type) {
  const raw = String(type || "");
  if (!raw.startsWith("prtscat:")) return "";
  const categoryKey = normalizePrtsCategoryKey(raw.slice("prtscat:".length));
  if (!categoryKey) return "";
  const labels = prtsCategoryDisplayLabels();
  return labels[categoryKey]
    || PRTS_CATEGORY_DISPLAY_LABELS.en[categoryKey]
    || STATE.prtsCategoryLabels[categoryKey]
    || formatStructuredLabel(categoryKey);
}

function dataTypeLabel(dataType) {
  const dynamicPrtsLabel = prtsCategoryLabel(dataType);
  if (dynamicPrtsLabel) return dynamicPrtsLabel;
  const familyLabel = tableTypeFamilyLabel(dataType);
  if (familyLabel) return familyLabel;
  const labels = dataTypeLabels();
  return labels[dataType] || formatStructuredLabel(dataType);
}

function isMediaTypeFilterKey(key) {
  return MEDIA_TYPE_FILTER_KEYS.includes(String(key || ""));
}

function mediaTypeFilterLabel(key) {
  const labels = localeTable(MEDIA_TYPE_FILTER_LABELS);
  return labels[key] || MEDIA_TYPE_FILTER_LABELS.en[key] || formatStructuredLabel(key);
}

function typeFilterLabel(key) {
  return isMediaTypeFilterKey(key) ? mediaTypeFilterLabel(key) : dataTypeLabel(key);
}

function compareDataTypeKeys(a, b, counts = null) {
  if (a === DEFAULT_DATA_TYPE_KEY && b !== DEFAULT_DATA_TYPE_KEY) return 1;
  if (b === DEFAULT_DATA_TYPE_KEY && a !== DEFAULT_DATA_TYPE_KEY) return -1;
  const aPinned = pinnedContentTypeRank(a);
  const bPinned = pinnedContentTypeRank(b);
  if (aPinned !== bPinned) return aPinned - bPinned;
  if (counts && !Number.isFinite(aPinned)) {
    const aCount = counts[a] || 0;
    const bCount = counts[b] || 0;
    if (aCount !== bCount) return bCount - aCount;
  }
  return dataTypeLabel(a).localeCompare(dataTypeLabel(b), undefined, { numeric: true });
}

function compareTypeFilterKeys(a, b, counts = null) {
  const aMedia = isMediaTypeFilterKey(a);
  const bMedia = isMediaTypeFilterKey(b);
  if (aMedia && bMedia) return MEDIA_TYPE_FILTER_KEYS.indexOf(a) - MEDIA_TYPE_FILTER_KEYS.indexOf(b);
  if (aMedia !== bMedia) return aMedia ? -1 : 1;
  return compareDataTypeKeys(a, b, counts);
}

const CONTENT_TYPE_PIN_ORDER = ["e", "a", "gm", "c", "sm", "m", "f"];
const MISSION_STORY_TYPE_KEYS = new Set(["e", "a", "gm", "c", "sm", "m", "f", "db", "dm"]);

function pinnedContentTypeRank(type) {
  const normalized = String(type || "").trim();
  const directIndex = CONTENT_TYPE_PIN_ORDER.indexOf(normalized);
  if (directIndex !== -1) return directIndex;
  if (normalized === "prts") return CONTENT_TYPE_PIN_ORDER.length;
  if (normalized.startsWith("prtscat:")) {
    const categoryKey = normalizePrtsCategoryKey(normalized.slice("prtscat:".length));
    const categoryIndex = PRTS_CATEGORY_ORDER.indexOf(categoryKey);
    return CONTENT_TYPE_PIN_ORDER.length + 1 + (categoryIndex === -1 ? PRTS_CATEGORY_ORDER.length : categoryIndex);
  }
  return Number.POSITIVE_INFINITY;
}

function metadataTagLabels() {
  return localeTable(METADATA_TAG_LABELS);
}

function metadataTagLabel(tag) {
  const labels = metadataTagLabels();
  return labels[tag] || METADATA_TAG_LABELS.en[tag] || tag;
}

function storyIssueLabel(code) {
  if (code === "missingLineOrder") return uiText("storyIssueMissingLineOrder");
  if (code === "partialLineOrder") return uiText("storyIssuePartialLineOrder");
  if (code === "fallbackLineOrder") return uiText("storyIssueFallbackLineOrder");
  if (code === "uncoveredLines") return uiText("storyIssueUncoveredLines");
  if (code === "duplicateTimestamps") return uiText("storyIssueDuplicateTimestamps");
  if (code === "timelineTimestampRegression") return uiText("storyIssueTimelineTimestampRegression");
  if (code === "tableOnlyOptionLayout") return uiText("storyIssueTableOnlyOptionLayout");
  if (code === "keyedOptionLayout") return uiText("storyIssueKeyedOptionLayout");
  if (code === "gapOptionLayout") return uiText("storyIssueGapOptionLayout");
  if (code === "lastLineOptionLayout") return uiText("storyIssueLastLineOptionLayout");
  if (code === "unanchoredOptionLayout") return uiText("storyIssueUnanchoredOptionLayout");
  if (code === "inferredOptionLayout") return uiText("storyIssueInferredOptionLayout");
  if (code === "inferredOptionResponse") return uiText("storyIssueInferredOptionResponse");
  if (code === "overrided") return uiText("storyIssueOverrided");
  if (code === "notOverrided") return uiText("storyIssueNotOverrided");
  return formatStructuredLabel(code);
}

function entryStoryIssues(entry) {
  if (!entry || !Array.isArray(entry.storyIssues)) return [];
  return entry.storyIssues.filter(Boolean);
}

function entryMatchesStoryIssueFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  const issues = new Set(entryStoryIssues(entry));
  for (const code of filters) {
    if (!issues.has(code)) return false;
  }
  return true;
}

function recoveryMethodLabel(method) {
  const raw = String(method || "");
  const withPrefix = (prefixKey, text) => `${uiText(prefixKey)}: ${text}`;
  if (raw === "lineOrder:dialogTree") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeDialogTree"));
  if (raw === "lineOrder:dialogTreeFragment") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeDialogTreeFragment"));
  if (raw === "lineOrder:dialogTreeExtraConfig") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeDialogTreeExtraConfig"));
  if (raw === "lineOrder:dialogTreeCinematicTimeline") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeDialogTreeCinematicTimeline"));
  if (raw === "lineOrder:authoredBlend") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeAuthoredBlend"));
  if (raw === "lineOrder:authoredNumericStitch") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeAuthoredNumericStitch"));
  if (raw === "lineOrder:dialogTimeline") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeDialogTimeline"));
  if (raw === "lineOrder:runtimeRowIteration") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeRuntimeRowIteration"));
  if (raw === "lineOrder:unregisteredScene") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeUnregisteredScene"));
  if (raw === "lineOrder:compoundNumericSuffix") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeCompoundNumericSuffix"));
  if (raw === "lineOrder:lineIdSuffix") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeLineIdSuffix"));
  if (raw === "lineOrder:missing") return withPrefix("recoveryMethodLinePrefix", uiText("lineOrderModeMissing"));
  if (raw === "optionLayout:authored") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutAuthored"));
  if (raw === "optionLayout:partialAuthoredCoverage") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutPartial"));
  if (raw === "optionLayout:fallback") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutFallback"));
  if (raw === "optionLayout:noAuthoredGroupAnchor") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutNoAnchor"));
  if (raw === "optionLayout:tableOnlyCutContent") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutTableOnly"));
  if (raw === "optionLayout:keyMatched") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutKeyMatched"));
  if (raw === "optionLayout:sparseGap") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutSparseGap"));
  if (raw === "optionLayout:siblingTimelinePosition") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutSiblingTimeline"));
  if (raw === "optionLayout:lastLine") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutLastLine"));
  if (raw === "optionLayout:unanchored") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionLayoutUnanchored"));
  if (raw === "optionBranch:sceneGraph") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionSceneGraph"));
  if (raw === "optionBranch:dialogTreeFragment") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionDialogTreeFragment"));
  if (raw === "optionBranch:runtimeJump") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionRuntimeJump"));
  if (raw === "optionBranch:rawIndexMatched") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionRawIndexMatched"));
  if (raw === "optionBranch:timelineAdjacent") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionTimelineAdjacent"));
  if (raw === "optionBranch:commonContinuation") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionCommonContinuation"));
  if (raw === "optionBranch:continuationOption") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionContinuationOption"));
  if (raw === "optionBranch:siblingSceneText") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionSiblingSceneText"));
  if (raw === "optionBranch:siblingSceneHint") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionSiblingSceneHint"));
  if (raw === "optionBranch:manualOverride") return withPrefix("recoveryMethodOptionPrefix", uiText("recoveryMethodOptionManualOverride"));
  return formatStructuredLabel(raw);
}

function compareRecoveryMethodKeys(a, b, counts = null) {
  const ar = STORY_RECOVERY_METHOD_ORDER.indexOf(a);
  const br = STORY_RECOVERY_METHOD_ORDER.indexOf(b);
  const aKnown = ar !== -1;
  const bKnown = br !== -1;
  if (aKnown && bKnown && ar !== br) return ar - br;
  if (aKnown !== bKnown) return aKnown ? -1 : 1;
  if (counts) {
    const delta = (counts[b] || 0) - (counts[a] || 0);
    if (delta) return delta;
  }
  return recoveryMethodLabel(a).localeCompare(recoveryMethodLabel(b), undefined, { numeric: true });
}

function entryRecoveryMethods(entry) {
  if (!entry || !Array.isArray(entry.recoveryMethods)) return [];
  return entry.recoveryMethods.filter(Boolean);
}

function entryMatchesRecoveryMethodFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  const methods = new Set(entryRecoveryMethods(entry));
  for (const method of filters) {
    if (!methods.has(method)) return false;
  }
  return true;
}

function entryHasTag(entry, tag) {
  if (!entry || !Array.isArray(entry.tags)) return false;
  return entry.tags.includes(tag);
}

function entryHasSourceTag(entry) {
  return entryHasTag(entry, "source_streaming") || entryHasTag(entry, "source_persistent");
}

function normalizeMetadataTag(rawTag) {
  const tag = String(rawTag || "").trim();
  const lowerTag = tag.toLowerCase();
  if (!tag) return "";
  if (tag === "loadingTip" || tag === "tip" || tag === "task") return DEFAULT_METADATA_TAG_KEY;
  if (tag === "snsChat") return DEFAULT_METADATA_TAG_KEY;
  if (tag === "mail") return "";
  if (lowerTag === "dungeon") return "";
  if (lowerTag === "worldtext" || tag === "collection") return "worldtext";
  if (tag === "systemJump") return "item";
  if (tag === "character" || tag === "attribute" || tag === "gem") return "gameMechanic";
  if (tag === "kitestation" || tag === "ethersubmitbuffshow") return "worldtext";
  if (tag === "money") return "";
  if (tag === "wiki" || tag === "variant") return "";
  if (tag === "source_streaming" || tag === "source_persistent") return "";
  if (tag.startsWith("source_")) return "";
  if (tag.startsWith("table_") || tag.startsWith("group_") || tag.startsWith("category_")) return "";
  if (/^[a-z0-9]+_stage_\d+$/i.test(tag)) return "";
  if (tag.startsWith("wiki_type_")) {
    return "wikiType";
  }
  return METADATA_TAG_KEEP.has(tag) ? tag : "";
}

function compareMetadataTags(a, b) {
  const ai = METADATA_TAG_ORDER.indexOf(a);
  const bi = METADATA_TAG_ORDER.indexOf(b);
  if (ai === -1 && bi === -1) {
    return metadataTagLabel(a).localeCompare(metadataTagLabel(b));
  }
  if (ai === -1) return 1;
  if (bi === -1) return -1;
  return ai - bi;
}

function entryMetadataTags(entry) {
  if (!entry) return [];
  if (Array.isArray(entry._metadataTagsNormalized)) return entry._metadataTagsNormalized;
  const out = [];
  const seen = new Set();
  const taskLike = entryTaskLike(entry);
  const wikiCollectionGroup = entryWikiCollectionGroup(entry);
  for (const rawTag of (entry.tags || [])) {
    const tag = normalizeMetadataTag(rawTag);
    if (tag === "achievement" && (entry.d === "table_achievementtable" || entry.t === "table_achievementtable")) {
      continue;
    }
    if (tag === "worldtext" && (taskLike || wikiCollectionGroup)) continue;
    if (!tag || seen.has(tag)) continue;
    seen.add(tag);
    out.push(tag);
  }
  if ((taskLike || wikiCollectionGroup) && !seen.has(DEFAULT_METADATA_TAG_KEY)) {
    seen.add(DEFAULT_METADATA_TAG_KEY);
    out.push(DEFAULT_METADATA_TAG_KEY);
  }
  if (!out.length) {
    out.push(DEFAULT_METADATA_TAG_KEY);
  }
  out.sort(compareMetadataTags);
  entry._metadataTagsNormalized = out;
  return out;
}

function entryMetadataTagSummary(entry, limit = 5) {
  const labels = entryMetadataTags(entry).map(metadataTagLabel);
  if (!labels.length) return "";
  if (labels.length <= limit) return labels.join(", ");
  return `${labels.slice(0, limit).join(", ")} +${labels.length - limit}`;
}

function groupedKindKey(kind) {
  const raw = String(kind || "");
  if (raw === "misc") return "dlg";
  if (raw === "table_prtsreading" || raw === "table_readingpopuptable") return "reading";
  if (raw === "wiki" || raw.startsWith("table_")) return "wiki";
  return String(kind || "");
}

function entryGroupedKindKey(entry) {
  if (!entry) return "";
  const key = String(entry.k || "");
  if (key.startsWith("misc_")) return "dlg";
  return groupedKindKey(entry.d);
}

function shouldSuppressKindChip(kind) {
  const raw = String(kind || "");
  return raw.startsWith("table_activity") || raw === "responsive";
}

function kindFilterToken(kind) {
  return `kind:${kind}`;
}

function entryKindFilterTokens(entry) {
  const tokens = new Set();
  if (!entry) return tokens;

  const kindKey = entryGroupedKindKey(entry);
  if (kindKey) tokens.add(kindFilterToken(kindKey));
  return tokens;
}

function pruneFilterSet(set, availableValues) {
  if (!set || !(set instanceof Set)) return;
  for (const value of Array.from(set)) {
    if (!availableValues.has(value)) set.delete(value);
  }
}

function entryMatchesKindFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  for (const token of entryKindFilterTokens(entry)) {
    if (filters.has(token)) return true;
  }
  return false;
}

function normalizeGroupedTagLabel(label) {
  return String(label || "")
    .replace(/\/\s*(?:Streaming|Persistent)\s*\/\s*/gi, "/ ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+\/\s+/g, " / ")
    .trim();
}

function normalizeGroupedTagKey(value) {
  return String(value || "")
    .replace(/\/\s*(?:Streaming|Persistent)\s*\/\s*/gi, "/")
    .replace(/(^|[_/\s-])(streaming|persistent)(?=([_/\s-]|$))/gi, "$1")
    .replace(/[\/\s-]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .trim()
    .toLowerCase();
}

function sourceGroupSubtitle(entry) {
  if (!entry || !Array.isArray(entry.tags)) return "";
  const entryTypeKey = String(entry.t || entry.d || "");
  if (entryTypeKey !== "table_ethersubmitbuffshowtable") return "";
  const groupTag = entry.tags.find((tag) => String(tag || "").startsWith("group_"));
  if (!groupTag) return "";
  return String(groupTag)
    .slice("group_".length)
    .replace(/_\d+$/i, "")
    .trim();
}

function normalizeActorNames(raw) {
  // Accept legacy {aid: "name"} or current {aid: ["name", ...]}.
  const out = {};
  for (const [k, v] of Object.entries(raw)) {
    if (Array.isArray(v)) out[k] = v.slice();
    else if (v) out[k] = [v];
    else out[k] = [];
  }
  return out;
}

function computeSimActorIds(entries) {
  const out = new Set();
  for (const actorId of SPECIAL_SIM_ACTOR_IDS) out.add(actorId);
  for (const entry of entries || []) {
    const actorId = simCharacterId(entry);
    if (actorId) out.add(actorId);
  }
  return out;
}

function computeRawStoryTypes(entries) {
  const out = new Set();
  for (const entry of entries || []) {
    const rawType = String(entry && entry.t || "").trim();
    if (rawType) out.add(rawType);
  }
  return out;
}

function normalizePrtsCategoryKey(raw) {
  let value = String(raw || "").trim().toLowerCase();
  if (!value) return "";
  if (value.startsWith("category_")) value = value.slice("category_".length);
  value = PRTS_CATEGORY_ALIASES[value] || value;
  for (const key of PRTS_CATEGORY_KEYS) {
    if (value === key) return key;
    if (value.startsWith(`${key}_`)) return key;
    if (value.includes(`nar_${key}_`)) return key;
  }
  return "";
}

function isPrtsArchiveEntry(entry) {
  if (!entry) return false;
  const kind = String(entry.d || "");
  const type = String(entry.t || "");
  return kind === "prts" || kind.startsWith("table_prts") || type === "prts" || type.startsWith("table_prts");
}

function normalizePrtsPageCategoryKey(raw) {
  const key = normalizePrtsCategoryKey(raw);
  return key === "research_report" ? "report" : key;
}

function entryArchiveMetadata(entryOrKey) {
  if (typeof STATE === "undefined" || !STATE || !STATE.archiveMetadataByKey) return null;
  const key = typeof entryOrKey === "string"
    ? entryOrKey
    : String(entryOrKey && entryOrKey.k || "");
  return key ? (STATE.archiveMetadataByKey.get(key) || null) : null;
}

function entryPrtsTagPageKey(entry) {
  if (!entry || !Array.isArray(entry.tags)) return "";
  const tagCategories = new Set();
  for (const rawTag of entry.tags) {
    const category = normalizePrtsPageCategoryKey(rawTag);
    if (category) tagCategories.add(category);
  }
  for (const category of PRTS_PAGE_CATEGORY_PRIORITY) {
    if (tagCategories.has(normalizePrtsPageCategoryKey(category))) {
      return normalizePrtsPageCategoryKey(category);
    }
  }
  return "";
}

function entryPrtsKeyPageKey(entry) {
  if (!entry) return "";
  for (const value of [entry.m, entry.k]) {
    const category = normalizePrtsPageCategoryKey(value);
    if (category) return category;
  }
  return "";
}

function entryPrtsPageKey(entry) {
  if (!isPrtsArchiveEntry(entry)) return "";
  const metadata = entryArchiveMetadata(entry);
  const metadataPage = normalizePrtsPageCategoryKey(metadata && metadata.page);
  if (metadataPage) return metadataPage;
  return entryPrtsTagPageKey(entry) || entryPrtsKeyPageKey(entry);
}

function normalizeArchiveResearchId(value) {
  return String(value || "").trim();
}

function inferArchiveResearchId(entry) {
  const text = [entry && entry.k, entry && entry.m].map((part) => String(part || "")).join(" ");
  let match = text.match(/research_[a-z0-9_]+/i);
  if (match) return match[0];
  match = text.match(/map\d+_research\d+/i);
  return match ? match[0] : "";
}

function entryArchiveResearchInfo(entry) {
  if (!isPrtsArchiveEntry(entry)) return null;
  const metadata = entryArchiveMetadata(entry);
  const primaryResearchId = normalizeArchiveResearchId(
    metadata && (metadata.primaryResearchId || (metadata.researchIds && metadata.researchIds[0]))
  ) || inferArchiveResearchId(entry);
  if (!primaryResearchId) return null;

  const group = typeof STATE !== "undefined" && STATE && STATE.archiveResearchById
    ? STATE.archiveResearchById.get(primaryResearchId)
    : null;
  const title = (group && group.title) || (metadata && metadata.researchTitle) || "";
  const desc = (group && group.desc) || (metadata && metadata.researchDesc) || "";
  return {
    id: primaryResearchId,
    title,
    desc,
  };
}

function isArchiveReportDataType(dataType) {
  const raw = String(dataType || "");
  if (!raw.startsWith("prtscat:")) return false;
  const category = normalizePrtsPageCategoryKey(raw.slice("prtscat:".length));
  return category === "report";
}

function entryPrtsCategoryKey(entry) {
  if (!isPrtsArchiveEntry(entry)) return "";
  const resolved = entryPrtsPageKey(entry);
  if (resolved) {
    return resolved;
  }
  return "";
}

function entryPrtsDataType(entry) {
  if (!isPrtsArchiveEntry(entry)) return "";
  const categoryKey = entryPrtsCategoryKey(entry);
  return categoryKey ? `prtscat:${categoryKey}` : "prts";
}

function computePrtsCategoryLabels(entries) {
  const out = {};
  for (const entry of entries || []) {
    if (String(entry && entry.d || "") !== "table_prtscategory") continue;
    const categoryKey = entryPrtsCategoryKey(entry);
    if (!categoryKey) continue;
    const title = cleanDisplayTitle(entry.title || "", entry.m || "") || String(entry.title || "").trim();
    if (title) out[categoryKey] = title;
  }
  return out;
}

function hasRawStoryType(type) {
  const rawType = String(type || "").trim();
  return !!rawType && STATE.rawStoryTypes.has(rawType);
}

function actorDisplay(aid) {
  const v = STATE.actorNames[aid];
  if (!v || !v.length) return aid;
  if (String(aid).startsWith("sns_")) {
    return selectSnsActorDisplay(v) || aid;
  }
  const names = v
    .map((name) => stripBraceSegments(name) || String(name || "").trim())
    .filter(Boolean);
  const displayNames = names.filter((name) => !isQuestionMarkOnlyName(name));
  return (displayNames.length ? displayNames : names)
    .filter((name, index, values) => values.indexOf(name) === index)
    .join(" / ") || aid;
}

function characterTailFromMissionId(missionId) {
  const m = String(missionId || "").match(/^chr_\d+_(.+)$/);
  return m ? m[1] : "";
}

function computeCharacterNames(entries) {
  const names = {};
  const priorities = {};
  for (const entry of entries || []) {
    const missionId = String(entry && entry.m || "").trim();
    const characterId = characterTailFromMissionId(missionId);
    if (!characterId) continue;

    const key = String(entry && entry.k || "").trim();
    const tags = Array.isArray(entry && entry.tags) ? entry.tags : [];
    const isCharacterReference = key.startsWith("wiki_chr_") || tags.includes("character");
    if (!isCharacterReference) continue;

    const title = String(entry && entry.title || "").trim();
    if (!title || title === key || title === missionId || title === characterId) continue;

    // Prefer the direct CharacterTable archive page over secondary character
    // references when more than one index entry carries the same character id.
    const priority = key.startsWith("wiki_chr_") ? 2 : 1;
    if ((priorities[missionId] || 0) > priority) continue;
    names[missionId] = title;
    names[characterId] = title;
    priorities[missionId] = priority;
  }
  return names;
}

function characterDisplayFromActorId(aid, preferExplicit = false) {
  const actorId = String(aid || "");
  if (!actorId) return "";
  const names = STATE.actorNames[actorId] || [];
  if (preferExplicit) {
    for (const rawName of names) {
      const explicit = extractExplicitBraceText(rawName);
      if (explicit) return explicit;
    }
  }
  if (names.length) return actorDisplay(actorId);
  const indexedName = STATE.characterNames[actorId] || "";
  if (indexedName) {
    if (preferExplicit) {
      const explicit = extractExplicitBraceText(indexedName);
      if (explicit) return explicit;
    }
    return stripBraceSegments(indexedName) || String(indexedName || "").trim();
  }
  if (/^endmin(?:[fm])?$/.test(actorId)) return "\u7ba1\u7406\u5458";
  return "";
}

function characterDisplayFromMissionId(missionId, preferExplicit = false) {
  const mid = String(missionId || "");
  if (!mid.startsWith("chr_")) return "";

  const characterId = characterTailFromMissionId(mid);
  const indexedName = STATE.characterNames[mid] || STATE.characterNames[characterId] || "";
  if (indexedName) {
    if (preferExplicit) {
      const explicit = extractExplicitBraceText(indexedName);
      if (explicit) return explicit;
    }
    return stripBraceSegments(indexedName) || String(indexedName || "").trim();
  }

  const missionName = STATE.missionNames[mid] || "";
  if (missionName && missionName !== mid) {
    if (preferExplicit) {
      const explicit = extractExplicitBraceText(missionName);
      if (explicit) return explicit;
    }
    return stripBraceSegments(missionName) || String(missionName || "").trim();
  }

  return characterDisplayFromActorId(characterId, preferExplicit);
}

function continueActorIdFromMissionId(missionId) {
  const m = String(missionId || "").match(/^continue_(?:self|other)_([a-z0-9_]+)$/i);
  return m ? String(m[1] || "").toLowerCase() : "";
}

function continueActorDisplayFromMissionId(missionId, preferExplicit = false) {
  const actorId = continueActorIdFromMissionId(missionId);
  if (!actorId) return "";
  return characterDisplayFromActorId(actorId, preferExplicit) || actorDisplay(actorId);
}

function missionDisplay(mid, typeHint = "") {
  const missionId = String(mid || "");
  if (!missionId) return "";
  void typeHint;
  const chrName = characterDisplayFromMissionId(missionId, true);
  if (chrName) return chrName;
  const continueName = continueActorDisplayFromMissionId(missionId, true);
  if (continueName) return continueName;
  return STATE.missionNames[missionId] || "";
}

function isExplicitTestEntryKey(value) {
  const key = String(value || "").trim().toLowerCase();
  if (!key) return false;
  return key.startsWith("test") || key.endsWith("test");
}

function hasEmbeddedTestSegment(value) {
  return /(?:^|_)test(?:_|$)/i.test(String(value || "").trim());
}

function missionTypeFromId(mid) {
  const missionId = String(mid || "");
  if (!missionId) return "";
  if (missionId.startsWith("topic_")) return "topic";
  if (missionId.startsWith("blackbox")) return "timeline";
  if (missionId.startsWith("sr_")) return "f";
  const m = missionId.match(/^([a-z]+)(\d+)?/);
  if (!m) return "";
  return m[1] || "";
}

function storyMissionTypeFromId(mid) {
  const missionType = missionTypeFromId(mid);
  return MISSION_STORY_TYPE_KEYS.has(missionType) ? missionType : "";
}

function entryFoldStoryMissionId(entry, ignoreStoryMission = false) {
  if (!entry) return "";
  const missionId = String((ignoreStoryMission ? entry.m : (entry.storyMission || entry.m)) || "").trim().toLowerCase();
  return storyMissionTypeFromId(missionId) ? missionId : "";
}

function entryStoryMissionId(entry) {
  return entryFoldStoryMissionId(entry);
}

function entryWikiCollectionGroup(entry) {
  return String(entry && entry.m || "").trim().toLowerCase().startsWith("wiki_collection_");
}

function entrySnsChatTableGroup(entry) {
  return String(entry && entry.m || "").trim().toLowerCase() === "snschattable";
}

function foldedEntryTypeKey(typeKey, entry, { ignoreStoryMission = false } = {}) {
  const normalized = String(typeKey || "").trim().toLowerCase();
  const family = normalized.startsWith("tablefamily:") ? normalized.slice("tablefamily:".length) : normalized;
  if (!normalized || normalized === "?") return DEFAULT_DATA_TYPE_KEY;
  const storyMissionId = entryFoldStoryMissionId(entry, ignoreStoryMission);
  if (storyMissionId) return storyMissionTypeFromId(storyMissionId);
  if (isMissionlessCutscene(entry, ignoreStoryMission)) return "worldtext";
  if (entryWikiCollectionGroup(entry)) return "other";
  if (entrySnsChatTableGroup(entry)) return "other";
  if (entryTaskLike(entry)) return "other";
  if (normalized === "tip" || normalized === "task" || family === "tip" || family === "task") return "other";
  if (entryHasTag(entry, "collection") || WORLD_TEXT_TYPE_KEYS.has(normalized)) return "worldtext";
  if (normalized === "x" || OTHER_TYPE_FAMILIES.has(family)) return "other";
  return typeKey;
}

function isMissionlessCutscene(entry, ignoreStoryMission = false) {
  if (!entry || String(entry.d || "") !== "cutscene") return false;
  return !entryFoldStoryMissionId(entry, ignoreStoryMission);
}

function entryTaskLike(entry) {
  if (entryHasTag(entry, "task")) return true;
  const text = [entry && entry.k, entry && entry.m, entry && entry.d, entry && entry.t]
    .map((part) => String(part || "").toLowerCase())
    .join(" ");
  return /(?:^|[_:-])task(?:[_:-]|$)|tasktable/.test(text);
}

function entryDataType(entry, { ignoreStoryMission = false } = {}) {
  if (!entry) return DEFAULT_DATA_TYPE_KEY;
  const entryKey = String(entry.k || "");
  const rawDataKind = String(entry.d || "").trim();
  const rawType = String(entry.t || "").trim();
  const normalizedType = rawType.toLowerCase();
  const fold = (typeKey) => foldedEntryTypeKey(typeKey, entry, { ignoreStoryMission });

  if (entryKey.startsWith("misc_sr_") || String(entry.m || "").startsWith("sr_")) return fold("tablefamily:spaceship");
  if (rawDataKind === "sns") return "topic";
  if (rawDataKind === "mail" || normalizedType === "mail") return fold("mail");
  if (isExplicitTestEntryKey(entryKey) || entryKey.startsWith("sns_test_")) return fold("test");
  if (normalizedType === "teammate" || normalizedType === "transition") return fold("test");
  if (rawDataKind === "table_valuabledepot" || normalizedType === "table_valuabledepot") return fold("test");
  if (rawDataKind === "cutscene" && /(?:^|_)transition(?:_|$)/i.test(entryKey)) return fold("test");
  if ((rawDataKind === "dlg" || rawDataKind === "radio") && normalizedType === "test") return fold("test");
  if ((normalizedType === "enemy" || normalizedType === "seamless") && hasEmbeddedTestSegment(entryKey)) return fold("test");
  if (normalizedType === "blackbox") return fold("timeline");
  if (normalizedType === "lv") return fold("eny");
  if (normalizedType === "dung") return fold("tablefamily:dungeon");
  if (
    rawDataKind === "table_commondeathtips" ||
    normalizedType === "table_commondeathtips" ||
    rawDataKind === "table_loadingtipstable" ||
    normalizedType === "table_loadingtipstable"
  ) return fold("other");
  if (
    (rawDataKind === "table_prtsreading" || rawDataKind === "table_readingpopuptable")
    && (!rawType || normalizedType.startsWith("table_"))
  ) {
    const missionType = missionTypeFromId(entry.m);
    if (missionType && hasRawStoryType(missionType)) return fold(missionType);
  }
  if (
    rawDataKind === "responsive" ||
    (rawDataKind === "table_aibarktext" && (!rawType || rawType === rawDataKind))
  ) return fold("sim");
  if (continueActorIdFromMissionId(entry.m) || pairedSimActorId(entry) || linkedSimActorId(entry)) return fold("sim");
  const prtsCategory = entryPrtsCategoryKey(entry);
  if (prtsCategory) return fold(`prtscat:${prtsCategory}`);
  const tableFamily = tableTypeFamilyKey(rawType || rawDataKind);
  if (tableFamily === "tablefamily:sns") return fold("other");
  if (tableFamily) return fold(tableFamily);
  if (rawDataKind === "env") {
    const missionType = missionTypeFromId(entry.m);
    if (missionType && missionType !== "env" && hasRawStoryType(missionType)) return fold(missionType);
  }
  if (normalizedType === "test" && !isExplicitTestEntryKey(entryKey)) return fold(rawDataKind || "");
  return fold(rawType || DEFAULT_DATA_TYPE_KEY);
}

function entryMissionLinkedNativeDataTypes(entry) {
  if (!entry || !entryStoryMissionId(entry)) return [];
  if (!entryKeepsNativeGroupWhenMissionLinked(entry)) return [];

  const out = [];
  const seen = new Set();
  const add = (typeKey) => {
    const key = String(typeKey || "").trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    out.push(key);
  };
  add(entryDataType(entry, { ignoreStoryMission: true }));
  add(entryOriginalEnvTalkDataType(entry, { ignoreStoryMission: true }));
  add(entryPrtsDataType(entry));
  return out;
}

function entryKeepsNativeGroupWhenMissionLinked(entry) {
  if (!entry || !entryStoryMissionId(entry)) return false;
  if (isPrtsArchiveEntry(entry)) return true;
  if (entryHasTag(entry, "wiki") || entryHasTag(entry, "archive")) return true;
  if (entryHasTag(entry, "envTalk")) return true;
  return String(entry.k || "").startsWith("env_envTalk_");
}

function entryUsesMissionLinkedNativeDataType(entry, dataType) {
  const key = String(dataType || "").trim();
  if (!key) return false;
  const storyMissionId = entryStoryMissionId(entry);
  const storyType = storyMissionId ? storyMissionTypeFromId(storyMissionId) : "";
  if (storyType && key === storyType) return false;
  return entryMissionLinkedNativeDataTypes(entry).includes(key);
}

function entryDataTypes(entry) {
  if (!entry) return [DEFAULT_DATA_TYPE_KEY];
  if (Array.isArray(entry._dataTypesNormalized)) return entry._dataTypesNormalized;

  const out = [];
  const seen = new Set();
  const add = (typeKey, fallbackToDefault = false) => {
    const raw = String(typeKey || "").trim();
    if (!raw && !fallbackToDefault) return;
    const key = raw || DEFAULT_DATA_TYPE_KEY;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(key);
  };

  add(entryDataType(entry), true);
  add(entryOriginalEnvTalkDataType(entry));
  add(entryPrtsDataType(entry));
  for (const dataType of entryMissionLinkedNativeDataTypes(entry)) add(dataType);
  if (String(entry.d || "").trim() === "sns") {
    const storyMissionId = entryStoryMissionId(entry);
    if (storyMissionId) add(storyMissionTypeFromId(storyMissionId));
  }

  entry._dataTypesNormalized = out;
  return out;
}

function entryOriginalEnvTalkDataType(entry, { ignoreStoryMission = false } = {}) {
  if (!entry || String(entry.d || "").trim() !== "env") return "";
  if (!String(entry.k || "").startsWith("env_envTalk_")) return "";
  if (!pairedSimActorId(entry)) return "";

  const rawType = String(entry.t || "").trim();
  return foldedEntryTypeKey(rawType || "worldtext", entry, { ignoreStoryMission });
}

function entryMediaTypeFilterKeys(entry) {
  if (!entry) return [];
  if (Array.isArray(entry._mediaTypeFilterKeys)) return entry._mediaTypeFilterKeys;
  const tags = new Set((entry.tags || []).map((tag) => String(tag || "")));
  const out = [];
  for (const key of MEDIA_TYPE_FILTER_KEYS) {
    const tag = MEDIA_TYPE_TAG_BY_KEY[key];
    if (!tag || !tags.has(tag)) continue;
    out.push(key);
  }
  if (!out.includes("media:video") && (tags.has("narrativeVideo") || entry.vid)) out.unshift("media:video");
  entry._mediaTypeFilterKeys = out;
  return out;
}

function entryTypeFilterKeys(entry) {
  return [...entryDataTypes(entry), ...entryMediaTypeFilterKeys(entry)];
}

function entryMatchesDataTypeFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  return entryDataTypes(entry).some((dataType) => filters.has(dataType));
}

function entryMatchesTypeFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  return entryTypeFilterKeys(entry).some((key) => filters.has(key));
}

function entryMatchesMediaFilters(entry, filters) {
  if (!filters || !filters.size) return true;
  const keys = new Set(entryMediaTypeFilterKeys(entry));
  for (const key of filters) {
    if (!keys.has(key)) return false;
  }
  return true;
}

function extractBraceText(text) {
  if (!text) return "";
  const m = String(text).match(/\{([^{}]+)\}/);
  return m ? m[1] : String(text);
}

function extractExplicitBraceText(text) {
  if (!text) return "";
  const m = String(text).match(/\{([^{}]+)\}/);
  return m ? m[1].trim() : "";
}

function stripBraceSegments(text) {
  return String(text || "")
    .replace(/\{[^{}]*\}/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function formatDlgSpeakerName(name, fallback = "") {
  const original = String(name || fallback || "").trim();
  if (!original) {
    return { display: fallback || "", original: "" };
  }

  const display = stripBraceSegments(original) || fallback || original;
  return {
    display,
    original: display === original ? "" : original,
  };
}

function appendSpeakerLabel(container, displayName, {
  originalName = "",
  aid = "",
  nameClass = "speaker-name",
  aidClass = "actor-id",
} = {}) {
  const name = document.createElement("span");
  name.className = nameClass;
  name.textContent = displayName;
  if (originalName) {
    name.classList.add("speaker-name-with-popup");
    name.tabIndex = 0;

    const popup = document.createElement("span");
    popup.className = "speaker-name-popup";
    popup.textContent = originalName;
    name.appendChild(popup);
  }
  container.appendChild(name);

  if (aid) {
    const aidNode = document.createElement("span");
    aidNode.className = aidClass;
    aidNode.textContent = aid;
    container.appendChild(aidNode);
  }
}

function resolveLineId(line) {
  if (!line || typeof line !== "object") return "";
  if (line.id) return String(line.id);
  if (line.cid !== undefined && line.cid !== null && line.cid !== "") {
    return `cid:${line.cid}`;
  }
  return "";
}

function appendLineId(container, line, className = "line-id") {
  const lineId = resolveLineId(line);
  if (!lineId) return;

  const node = document.createElement("div");
  node.className = className;
  if (typeof highlightTextFragment === "function" && typeof STATE !== "undefined") {
    node.innerHTML = highlightTextFragment(lineId, STATE.filters && STATE.filters.q);
  } else {
    node.textContent = lineId;
  }
  container.appendChild(node);
}

function appendUncoveredLineBadge(container, className = "line-coverage-badge") {
  const node = document.createElement("span");
  node.className = className;
  node.textContent = uiText("lineOrderUncoveredBadge");
  container.appendChild(node);
}

function appendDuplicateTimestampBadge(container, className = "line-coverage-badge line-duplicate-timestamp-badge") {
  const node = document.createElement("span");
  node.className = className;
  node.textContent = uiText("duplicateTimestampBadge");
  container.appendChild(node);
}

function resolveOptionId(option) {
  if (!option || typeof option !== "object") return "";
  if (option.id) return String(option.id);
  if (option.optionId) return String(option.optionId);
  return "";
}

function appendOptionId(container, option, className = "option-id") {
  const optionId = resolveOptionId(option);
  if (!optionId) return;

  const node = document.createElement("div");
  node.className = className;
  if (typeof highlightTextFragment === "function" && typeof STATE !== "undefined") {
    node.innerHTML = highlightTextFragment(optionId, STATE.filters && STATE.filters.q);
  } else {
    node.textContent = optionId;
  }
  container.appendChild(node);
}

function isQuestionMarkOnlyName(text) {
  return /^[?\uFF1F\s]+$/.test(String(text || "").trim());
}

function selectSnsActorDisplay(names) {
  let fallback = "";
  for (const rawName of names) {
    const originalName = String(rawName || "").trim();
    if (!originalName) continue;

    const name = stripBraceSegments(originalName) || originalName;
    if (!name) continue;
    if (isQuestionMarkOnlyName(name)) continue;
    if (!fallback || name.length < fallback.length) fallback = name;
  }
  return fallback;
}

function displayNamedKey(title, key, fallbackMissionId = "") {
  const cleanTitle = cleanDisplayTitle(title || "", fallbackMissionId);
  if (cleanTitle && cleanTitle !== key) return `${cleanTitle} (${key})`;
  return key || cleanTitle;
}

function cleanDisplayTitle(text, fallbackMissionId = "") {
  const raw = String(text || "").trim();
  if (!raw) return "";

  const explicit = extractExplicitBraceText(raw);
  if (explicit) {
    const suffix = raw.replace(/^.*?\{[^{}]+\}/, "").trim();
    return `${explicit}${suffix ? " " + suffix : ""}`.trim();
  }

  const chrName = characterDisplayFromMissionId(fallbackMissionId, true);
  if (chrName && raw.startsWith(String(fallbackMissionId || ""))) {
    return `${chrName}${raw.slice(String(fallbackMissionId || "").length)}`.trim();
  }

  return raw;
}

function snsChannelDisplayTitle(item) {
  const chatType = Number(item && item.chatType);
  if (chatType !== 2) return "";
  const missionId = String(item && (item.m || item.mission) || "");
  return cleanDisplayTitle(item && item.chatTitle || "", missionId);
}

function displaySnsTitle(item, fallback = "") {
  const missionId = String(item && (item.m || item.mission) || "");
  const baseTitle = cleanDisplayTitle(item && item.title || fallback, missionId);
  const chatTitle = snsChannelDisplayTitle(item);
  if (chatTitle && baseTitle && chatTitle !== baseTitle) return `${chatTitle} - ${baseTitle}`;
  return chatTitle || baseTitle;
}

function displayEntryTitle(entry) {
  if (String(entry && entry.d || "") === "sns") {
    return displaySnsTitle(entry, entry && entry.k || "");
  }
  return cleanDisplayTitle(entry.title || entry.k || "", entry && entry.m ? entry.m : "");
}

function displayConvTitle(conv) {
  const missionTitle = conv.mission ? missionDisplay(conv.mission, conv.kind) : "";
  if (conv.kind === "sns") return displayNamedKey(displaySnsTitle(conv, conv.key || ""), conv.key, conv.mission || "");
  if (["mail", "prts", "wiki", "responsive"].includes(conv.kind) || String(conv.kind || "").startsWith("table_")) {
    return displayNamedKey(conv.title || missionTitle || "", conv.key, conv.mission || "");
  }
  return displayNamedKey(
    missionTitle || conv.title || "",
    conv.key,
    conv.mission || ""
  );
}

function simCharacterId(entry) {
  const key = String(entry && entry.k || "");
  let m = key.match(/^misc_sim_(?:gift|talk|rest|work)_([^_]+)/);
  if (m) return m[1];
  m = key.match(/^env_greetEnvTalk_([^_]+)/);
  return m ? m[1] : "";
}

function isKnownSimActorId(actorId) {
  const normalized = String(actorId || "").trim().toLowerCase();
  if (!normalized) return false;
  return SPECIAL_SIM_ACTOR_IDS.has(normalized) || STATE.simActorIds.has(normalized);
}

function actorNameKeys(actorId) {
  const out = new Set();
  for (const name of STATE.actorNames[String(actorId || "").trim().toLowerCase()] || []) {
    for (const value of [name, stripBraceSegments(name), extractExplicitBraceText(name)]) {
      const text = String(value || "").trim().toLowerCase();
      if (text) out.add(text);
    }
  }
  return out;
}

function sameNamedSimActorId(actorId) {
  const sourceId = String(actorId || "").trim().toLowerCase();
  const sourceNames = actorNameKeys(sourceId);
  if (!sourceNames.size) return "";
  const matches = [];
  for (const candidate of STATE.simActorIds) {
    if (candidate === sourceId || SPECIAL_SIM_ACTOR_IDS.has(candidate)) continue;
    for (const name of actorNameKeys(candidate)) {
      if (sourceNames.has(name)) {
        matches.push(candidate);
        break;
      }
    }
  }
  return matches.length === 1 ? matches[0] : "";
}

function linkedSimActorId(entry) {
  if (!entry) return "";
  const actorId = characterTailFromMissionId(entry.m);
  if (!actorId) return "";
  return isKnownSimActorId(actorId) ? actorId : "";
}

function normalizedEntryActorId(rawActorId) {
  let raw = String(rawActorId || "").trim().toLowerCase();
  if (!raw) return "";
  if (STATE.actorNames[raw]) return sameNamedSimActorId(raw) || raw;
  for (;;) {
    let changed = false;
    if (raw.startsWith("sns_")) {
      raw = raw.slice(4);
      changed = true;
    }
    if (raw.startsWith("npc_")) {
      raw = raw.slice(4);
      changed = true;
    }
    const chrMatch = raw.match(/^chr_\d+_(.+)$/);
    if (chrMatch) {
      raw = chrMatch[1];
      changed = true;
    }
    if (!changed) break;
    if (STATE.actorNames[raw]) return sameNamedSimActorId(raw) || raw;
  }
  if (raw.includes("_")) return raw.split("_").pop() || "";
  return raw;
}

function addPairedOperatorCandidate(rawActorId, operatorCandidates, adminCandidates) {
  const actorId = normalizedEntryActorId(rawActorId);
  if (!actorId) return;
  if (!isKnownSimActorId(actorId)) return;
  if (SPECIAL_SIM_ACTOR_IDS.has(actorId)) adminCandidates.add(actorId);
  else operatorCandidates.add(actorId);
}

function scanPairedOperatorCandidates(rawText, operatorCandidates, adminCandidates) {
  const raw = String(rawText || "").toLowerCase();
  if (!raw) return;

  for (const match of raw.matchAll(/(?:sns_)?chr_\d+_([a-z0-9_]+)/g)) {
    addPairedOperatorCandidate(match[0], operatorCandidates, adminCandidates);
    addPairedOperatorCandidate(match[1], operatorCandidates, adminCandidates);
  }

  const tokens = raw.split(/[^a-z0-9_]+/).filter(Boolean);
  for (const token of tokens) {
    addPairedOperatorCandidate(token, operatorCandidates, adminCandidates);
    for (const part of token.split("_")) {
      addPairedOperatorCandidate(part, operatorCandidates, adminCandidates);
    }
  }
}

function entryHasChrStyleOperatorHint(entry) {
  if (!entry) return false;
  const values = [entry.k, entry.m, ...(entry.tags || [])];
  return values.some((value) => /(?:^|[^a-z0-9])(?:sns_)?chr_\d+_[a-z0-9_]+/i.test(String(value || "")));
}

function entryWorldTextLike(entry) {
  const rawType = String(entry && (entry.t || entry.d) || "").trim().toLowerCase();
  return WORLD_TEXT_TYPE_KEYS.has(rawType) || entryHasTag(entry, "worldtext") || entryHasTag(entry, "collection");
}

function entryCanPairWithSimActor(entry) {
  if (!entry) return false;
  if (String(entry.k || "").startsWith("wiki_chr_")) return true;
  if (String(entry.m || "").startsWith("chr_")) return true;
  if (String(entry.d || "") === "sns" && String(entry.k || "").startsWith("sns_topic_")) return true;
  if (entryWorldTextLike(entry) && Array.isArray(entry.c) && entry.c.length) return true;
  if (entryHasChrStyleOperatorHint(entry)) return true;
  const rawTableType = String(entry.t || entry.d || "").trim().toLowerCase();
  if (/^table_(?:character|chargrowth|char|potential)/.test(rawTableType)) return true;
  if (Array.isArray(entry.tags) && entry.tags.includes("character")) return true;
  return false;
}

function pairedSimActorId(entry) {
  if (!entryCanPairWithSimActor(entry)) return "";
  if (entry && Object.prototype.hasOwnProperty.call(entry, "_pairedSimActorId")) {
    return entry._pairedSimActorId || "";
  }

  const operatorCandidates = new Set();
  const adminCandidates = new Set();
  addPairedOperatorCandidate(simCharacterId(entry), operatorCandidates, adminCandidates);
  addPairedOperatorCandidate(linkedSimActorId(entry), operatorCandidates, adminCandidates);
  addPairedOperatorCandidate(aiBarkSimActorId(entry), operatorCandidates, adminCandidates);
  addPairedOperatorCandidate(continueActorIdFromMissionId(entry && entry.m), operatorCandidates, adminCandidates);

  for (const rawActorId of (entry.c || [])) {
    addPairedOperatorCandidate(rawActorId, operatorCandidates, adminCandidates);
  }
  for (const rawText of [entry.k, entry.m, ...(entry.tags || [])]) {
    scanPairedOperatorCandidates(rawText, operatorCandidates, adminCandidates);
  }

  let resolved = "";
  if (operatorCandidates.size === 1) {
    resolved = Array.from(operatorCandidates)[0];
  } else if (!operatorCandidates.size && adminCandidates.size === 1) {
    resolved = Array.from(adminCandidates)[0];
  }
  if (entry) entry._pairedSimActorId = resolved;
  return resolved;
}

function aiBarkSimActorId(entry) {
  if (!entry || (entry.d !== "table_aibarktext" && entry.d !== "responsive")) return "";
  for (const rawActorId of (entry.c || [])) {
    const actorId = normalizedEntryActorId(rawActorId);
    if (!actorId) continue;
    if (isKnownSimActorId(actorId)) return actorId;
    if (/^endmin(?:[fm])?$/.test(actorId)) return actorId;
    if ((STATE.actorNames[actorId] || []).length) return actorId;
  }
  return "";
}

