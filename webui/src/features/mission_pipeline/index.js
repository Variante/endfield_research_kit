(() => {
  const SVG_NS = "http://www.w3.org/2000/svg";
  const CARD_W = 252;
  const CARD_H = 164;
  const state = {
    initialized: false,
    language: "CN",
    index: null,
    names: {},
    filtered: [],
    missionId: "e7m3",
    mission: null,
    localized: null,
    selectedQuestId: "",
    missionCache: new Map(),
    localizedCache: new Map(),
    indexPromise: null,
    request: 0,
    missionRequest: 0,
    controller: null,
    transform: { x: 24, y: 24, scale: 1 },
    layout: null,
    dragging: null,
    suppressGraphClickUntil: 0,
    expandedMissionTypes: new Set(["e"]),
    // Which summary band the reader is focused on. "all" keeps every block
    // rendered and visible; focusing only hides sibling sections.
    summarySection: "all",
  };

  const TEXT = {
    en: {
      relationQuestProgressLockedInteractive: "every playback occurrence is rooted at an exact interactive entity whose typed progress lock waits for this quest to be Completed (local context, not Story ownership or quest activation/playback/completion causality)",
      eyebrow: "EXPERIMENTAL · CLIENT / SERVER EVIDENCE",
      title: "Mission Pipeline",
      scope: "Authored quest structure with an explicit native client/server boundary.",
      warning: "Predecessor arrows are client-visible prerequisites. The server still decides which quest state to synchronize next.",
      missionSource: "MissionRuntime source",
      sourceCompletePersistent: "complete Persistent override",
      sourceStreamingFallback: "StreamingAssets fallback",
      sourceExplicitRoot: "explicit mission root",
      sourceChangedFiles: "changed base files",
      sourceMissingFiles: "missing base files",
      missions: "missions",
      quests: "quests",
      connectedStory: "Story connected",
      unlinkedStory: "Story unassigned",
      nativePlaybackGaps: "exact-native gaps",
      luaPlaybackAccepted: "Lua playback admitted",
      luaTablePlaybackAccepted: "Lua table-owned playback",
      luaPlaybackRejected: "Lua case rejected",
      luaHandleDispatchers: "Lua runtime dispatch branches",
      luaPlaybackAudit: "Shipped-Lua census",
      cinematicProducer: "Original-binary producer",
      rootPlaybackAliases: "root playback aliases",
      exactDialogRootAlias: "exact DialogTree root alias",
      exactDialogRootAliasBoundary: "byte-identical payload; no activation or server branch-selection claim",
      definitionOnlyStory: "definition-only black text",
      nonMissionContentStory: "non-mission content",
      nonMissionContentStoryHint: "Story ids proven to be authored non-mission content: speaker radio continuation, character SNS topics, factory tutorial actions, operator profile voices, typed spacecraft DialogTrees, or complete actor/family definitions absent from every related typed tree. Definition gaps prove neither playback nor order. Authored fields and typed consumers admit a key; filenames never do.",
      missionGraph: "Cross-mission relations",
      missionGraphUpstream: "upstream",
      missionGraphDownstream: "downstream",
      missionGraphRequiresCompleted: "requires completed",
      missionGraphRequiresProcessing: "requires in progress",
      missionGraphAbortsOnCompleted: "aborts when completed",
      missionGraphUnclassified: "unclassified operands",
      missionGraphInterleaving: "Interleaved with",
      missionGraphHint: "Recovered from authored quest conditions that read another mission's or another mission's quest's state. Only \"requires completed\" is precedence; \"requires in progress\" is a co-active window and \"aborts when completed\" is mutual exclusion. Mission unlock order is server-authored, so a missing relation is not evidence that two missions are unordered.",
      missionGraphEdgesStat: "cross-mission precedence",
      envTalkContext: "Mission-related ambient envTalk",
      envTalkContextStat: "quest-tracked envTalk",
      envTalkStateContextStat: "state-conditioned envTalk",
      envTalkContextBoundary: "Navigation/state context, not playback",
      envTalkContextHint: "Two exact non-owning paths are shown: a typed NpcProxyTrackingInfo can steer a quest to a proxy carrying ambient lines, while an atmospheric switcher condition can gate the unique same-level NPC group containing an envTalk cluster. These paths explain navigation or world-state availability; they do not play, own, start, or complete the lines, and prove no chronology or server exchange.",
      relationEnvTalkTrackedProxy: "ambient lines on a quest-tracked NPC proxy",
      relationEnvTalkSwitcherState: "ambient cluster under a mission/quest-conditioned NPC switcher",
      relationEnvTalkMultipleContext: "multiple exact ambient context paths",
      trackedByQuests: "tracked by",
      missionlessSubGameStory: "SubGame-scoped Story",
      missionlessRuntimeStory: "runtime-receiver Story",
      nativeGapQueue: "Unlinked original-binary trigger queue",
      nativeGapQueueHint: "Exact playback exists, but a mission/quest identity is still missing. Counts are unique Story files and can overlap event families.",
      missionlessSubGameNodes: "Missionless original-data runtime nodes",
      missionlessSubGameNodesHint: "These are exact SubGame → bindScriptId → native playback → Story chains. They add structure to unlinked files but do not count as mission-owned Story bindings.",
      noMissionOwner: "no mission owner",
      exactPlayback: "exact native playback",
      exactReceiverNodes: "Exact serialized runtime receivers",
      exactReceiverNodesHint: "Each node is an original LevelScript event selector with an exact control path to Story playback. It organizes more recovered files without claiming a mission or quest owner.",
      playbackGate: "exact receiver playback gate",
      playbackGateTrue: "playback allowed when true",
      playbackGateBoundary: "This original-binary predicate controls only this receiver playback. It does not prove mission ownership, order between Story files, or a later server-side state write.",
      postPlaybackControl: "exact post-playback control flow",
      postPlaybackBranch: "typed local branch points",
      postPlaybackServerHandoff: "server handoff (handler unresolved)",
      postPlaybackBoundary: "Typed successor fields prove the local action graph after playback. Callback labels do not identify a server handler, mission/quest owner, state write, or cross-Story chronology.",
      postPlaybackActionNameAudit: "Complete binary ActionBase naming",
      postPlaybackFormatterTags: "validated formatter union tags",
      postPlaybackFormatterNamed: "formatter-named action placements",
      nativeTransitionNamedEndpoints: "named native transition endpoints",
      postPlaybackOutsideActionBase: "unresolved action shapes",
      postPlaybackActionNameBoundary: "Action names come from all 1,313 contiguous union tags recovered from the installed MemoryPack formatter. The compact unionTag plus serialized member count is authoritative; legacy combined raw opcodes remain provenance only. Class names do not select branches, establish mission ownership, or order Story files.",
      callServerCallbackAudit: "Binary-validated CallServer callback branches",
      callServerActionsDecoded: "CallServer actions decoded",
      callServerCallbackHeaders: "exact callback headers",
      callServerStoryCallbacks: "Story-bearing callback headers",
      callServerDanglingCallbacks: "dangling callback UIDs",
      callServerUnownedSurface: "callback UIDs on unresolved post-playback handoffs",
      callServerPostPlaybackContracts: "exact post-playback handoff contracts",
      callServerSelfUidContracts: "self-UID correlation labels",
      callServerArgumentPaths: "mission/quest argument paths",
      callServerSerializedContract: "serialized handoff contract",
      callServerCallbackBoundary: "The installed binary proves the complete six-field CallServer shape and that each non-empty output string is a possible subexecutor header UID. Exact source/local-action joins recover every post-playback handoff contract; event names and argument parameters do not become mission ownership or Story order without an independent original-data foreign key.",
      postPlaybackLevelSequenceAudit: "Exact post-playback LevelSequence files",
      postPlaybackLevelSequenceActions: "typed sequence action placements",
      postPlaybackLevelSequenceAssets: "exact original TextAssets",
      postPlaybackLevelSequenceUnresolved: "unresolved serialized sequence IDs",
      postPlaybackLevelSequenceFile: "related original LevelSequence file",
      postPlaybackLevelSequenceValidationFailure: "excluded source identity mismatch",
      postPlaybackLevelSequenceBoundary: "The action class comes from the installed binary formatter and the file joins only when the serialized ID equals the exported m_Name, Name, and decoded cutsceneName. It does not prove mission ownership or order separate Story files.",
      postPlaybackVariableBridge: "Post-playback variable bridge audit",
      postPlaybackVariableSetterStat: "typed post-playback variable setters",
      postPlaybackVariableListeners: "exact variable-listener rows",
      postPlaybackVariableMatches: "exact same-script/key matches",
      postPlaybackVariableClosed: "route closed",
      postPlaybackVariableBoundary: "Setter and listener keys come from exact current-build serialization. A join still cannot become Story order until Set<T>.Execute proves its notification family; this build has no exact same-level, same-script, same-key join at all.",
      activationFrontier: "offline activation frontier",
      nominalMissionHostCheck: "nominal-mission LevelData check",
      nominalMissionHostExcludes: "validated host excludes receiver script",
      noSameLevelNominalMissionHost: "no same-level nominal-mission host",
      nominalMissionCandidateBoundary: "filename/index candidate only; no mission owner or graph edge",
      activationClass: "static activation class",
      startPolicy: "LevelScript start policy",
      binaryStartPolicy: "binary-validated start transition",
      binaryStartPolicyBoundary: "The current binary proves that an Active, unfinished SameWithActive script enters PreStart without the area/manual gate. It does not identify the mission or server transition that activated the script, and it does not order Story files.",
      binaryManualSelfControl: "binary-validated self-start carrier",
      binaryManualSelfControlBoundary: "The current binary and metadata prove the CURRENT_LEVEL_ID/CURRENT_SCRIPT_ID target generally. This row also has an original serialized event-header link into ManualStart. It proves local self-start, not a mission owner, selected branch, or cross-Story order.",
      binaryPublicStateControl: "binary-validated public state carriers",
      binaryPublicStateControlBoundary: "The current client has exactly two direct server-derived public-state inputs: the full-scene LevelScript snapshot and the incremental state notification. They prove that Enabled is server-supplied, but neither carries mission, quest, Story, or branch-reason identity, and neither orders Story files.",
      binaryClientActiveRequest: "binary-validated client Active request selector",
      binaryClientActiveRequestBoundary: "The original LevelData type selects this generic runtime branch. The server supplies Enabled through the validated snapshot/notification carriers, but the server-side selection rule remains unavailable; this also does not prove a particular spatial result, server acceptance of Active, mission ownership, event firing, or Story order.",
      binaryActiveVolume: "original authored activation volume",
      binaryActiveVolumeBoundary: "This geometry is decoded directly from the original LevelScriptData and the gate behavior from the current game binary. It does not prove player position, the runtime gate result, mission ownership, event firing, or Story order.",
      binaryClientStartRequest: "binary-validated client start request lifecycle",
      binaryClientStartRequestBoundary: "The current client proves ManualStart flag → PreStart → typed CS start request → PreStartActionRunning. The public network sender APIs have zero direct current-AOT callers; this row still has no authored static carrier or resolved mission/server selector.",
      binaryActivePhaseReceiver: "binary-validated Active-phase receiver",
      binaryActivePhaseReceiverBoundary: "The exact original header is serialized for Active, not Start. The current binary registers the trigger graph during Setup and enables Active receivers in ActiveBegin. This proves availability without ManualStart, not who selected public Active, whether the event fired, mission ownership, branching, or Story order.",
      binarySubGameManualStart: "binary-validated SubGame start carrier",
      binarySubGameManualStartBoundary: "The current binary and typed original row prove SubGame id → bindScriptId → LevelScript lookup → ManualStart. This is an interaction start carrier, not mission ownership, selected branching, or cross-Story order.",
      levelDataContainer: "validated LevelData container",
      encounterController: "binary-proven Encounter controller",
      encounterModuleNamespace: "Encounter LsmPtr module namespace",
      moduleMatchesReceiver: "module id matches receiver id",
      relatedModuleNamespace: "related module id",
      encounterSpawner: "typed Encounter spawner",
      noConfiguredSpawner: "no configured spawner",
      relatedOriginalFile: "related original-data file",
      encounterControllerBoundary: "Encounter type and related files are exact; mission ownership, Story activation, branching, and order remain unresolved.",
      dungeonSceneContext: "exact Dungeon/SubGame scene context",
      boundReceiverScript: "receiver is bound script",
      siblingReceiverScript: "receiver is a sibling script",
      dungeonMissionShellContext: "typed dungeon mission shell context",
      dungeonSceneBoundary: "Same-scene hosting and availability prerequisites are context only; they do not identify the Story owner, trigger, or order.",
      missionRuntimeConsumers: "typed MissionRuntime objective consumers",
      questObserver: "Quest observer",
      observationOnly: "observation only",
      questObserverBoundary: "MissionRuntime reads this LevelScript as an objective operand. This does not prove that the quest starts or owns the Story, or that the playback handoff sets the observed property.",
      literalCrossScriptControls: "literal cross-script manual controls",
      exactStartShapeAreaMatches: "exact complete start-shape / MissionArea matches",
      serializedMissionIdTokens: "serialized mission-like string tokens",
      authoredPropertyContract: "authored LevelData property contract",
      missionObservedProperty: "exact MissionRuntime property observer",
      unobservedProperty: "no exact mission-side observer",
      propertyContractBoundary: "Property names and exact mission reads are visible context only. They do not identify the writer, Story owner, or scene-file order.",
      taskConditionEvidence: "fully decoded task conditions",
      taskConditionBoundary: "task evaluation dependency, not mission ownership or execution order",
      taskRuntimeAuthority: "binary-validated task lifecycle authority",
      taskRuntimeAuthorityBoundary: "Server and client task traffic identifies only scene, LevelScript, task, and condition/progress state. It carries no mission, quest, or Story identity and therefore supplies no ownership or file-order edge.",
      taskProgressProperties: "exact LevelData task progress properties",
      taskProgressPropertiesBoundary: "The lt:p/lt:mp pair persists this task condition's progress. It repeats task identity but does not identify the mission owner or playback order.",
      taskOperandSources: "exact authored operand sources",
      taskMissionConsumers: "typed MissionRuntime operand consumers",
      exactRuntimeTarget: "exact original-data runtime target",
      encounterModule: "Encounter module",
      modulePointer: "level-script module pointer",
      activationSlot: "activation trigger slot",
      battleExitSlot: "battle exit trigger slot",
      localEntitySlots: "local enemy slots",
      missingOwnershipBridge: "missing mission / quest foreign key",
      serializedSelector: "serialized selector",
      localEvent: "local event",
      serverBackedEvent: "server-backed event",
      localProducerChain: "exact local producer chain",
      abilityProducer: "Ability producer",
      literalSignal: "literal signal / value",
      noServerRequestOrReturn: "no server request / return",
      sameScriptDependency: "same authored LevelScript only",
      noPlaybackControlPath: "not linked to the Story playback control path",
      producerBoundaryHint: "The receiver matches only the literal signal. It does not select the producer sender, entity, spawner, mission, or quest; this chain adds causality, not ownership.",
      mainTasks: "main task ids",
      exactLevelHost: "exact level host",
      exactSceneHost: "exact scene host",
      localOnlyPaths: "native local-only paths",
      noServerExchange: "no server exchange",
      carrierAudit: "Closed managed-carrier candidates",
      noGraphEdges: "zero mission graph edges",
      nativeCrossSystemConsumers: "Native cross-system consumer census",
      crossSystemCallers: "cross-system callers",
      missionDynamicConsumers: "mission-state → DynamicScene consumers",
      missionLevelScriptConsumers: "MissionSystem → LevelScript consumers",
      tripleSystemConsumers: "three-system consumers",
      unreviewedConsumers: "unreviewed consumers",
      closureReachableMethods: "reachable consumer methods",
      closureDirectEdges: "direct closure edges",
      deferredAvailabilityRefresh: "Deferred DynamicScene availability refresh",
      pendingRefreshField: "pending refresh field",
      availabilityOnlyNoOrder: "availability refresh only; no Story binding, mission ownership, or order",
      fullMissionRuntimeSurface: "Full mission/quest runtime surface",
      missionIdentityTypes: "mission/quest identity types",
      crossFamilySignatures: "mission + LevelScript method signatures",
      trackingMissionWrites: "tracking missionId writes",
      trackingSceneWrites: "tracking sceneId writes",
      trackingContextOnly: "tracking UI context only; no receiver activation or order",
      managedCallableSurface: "Managed delegate/callback carrier surface",
      callableFields: "callable fields",
      missionCallableFields: "mission-runtime callable fields",
      levelScriptCallableFields: "LevelScript callable fields",
      callableEntryMethods: "typed binding entry methods",
      directBindingCalls: "direct native binding calls",
      crossFamilyBindings: "mission + LevelScript bindings",
      callableNoActivation: "typed callbacks remain family-local; no receiver activation or order",
      visualContextConsumers: "Story ↔ DynamicScene visual-context consumers",
      dynamicSceneCrossReferences: "DynamicScene identity cross-references",
      dynamicSceneCrossReferencesHint: "A DynamicScene object co-carries mission/quest state conditions, and its exact numeric logic id equals an exported LevelScript script id containing Story playback. One current row also has a typed LevelScript target and shared local Story path; the mission-condition-to-trigger activation edge is still missing, so no row gains mission ownership, playback causality, or order.",
      dynamicSceneLogicId: "DynamicScene logic id",
      levelScriptId: "LevelScript script id",
      missionStateConditions: "co-carried state conditions",
      candidateContextOnly: "candidate context only",
      exactDynamicSceneLocalContext: "exact local control context",
      typedDynamicSceneTargetAction: "typed DynamicScene target action",
      exactLocalTriggerVolume: "exact embedded LevelScript trigger volume",
      noTriggerForeignIdentity: "local geometry only; no DynamicScene, mission, quest, or foreign entity identity",
      triggerVolumePosition: "position",
      triggerVolumeRadius: "radius",
      sameSerializedControlPath: "same serialized control path",
      missionActivationGap: "mission condition to trigger activation remains unresolved",
      alternateActions: "mutually exclusive actions",
      currentAuthoredInstances: "current authored instances",
      runtimeContextOnly: "runtime subscription context only",
      authoredPropertyRows: "authored property rows",
      implicitMissionContext: "implicit current-mission context only",
      missionRuntimeUses: "MissionRuntime uses",
      levelScriptUses: "LevelScript uses",
      directManagedCandidates: "direct managed candidates",
      nestedManagedCandidates: "typed managed candidates",
      nestedDependentCandidates: "nested-dependent candidates",
      maxTypedDepth: "maximum shortest type path",
      fixedPointTraversal: "cycle-safe fixed point",
      runtimeEntityHubCandidates: "runtime Entity-hub candidates",
      sharedAggregateCandidates: "mixed runtime-aggregate candidates",
      exactSerializedInstances: "exact indexed type labels",
      indexedOriginalObjects: "indexed original objects",
      truncatedScalarObjects: "truncated scalar projections",
      shippedLuaProducer: "shipped XLua producer",
      authoredSubmitItemActions: "typed SubmitItem actions",
      concreteQuestIds: "concrete authored quest ids",
      missionSubmissionChecks: "mission submission checks",
      submissionDialogCoGates: "same-AND dialog co-gates",
      submissionLevelScriptCoGates: "same-AND LevelScript co-gates",
      submitOpenUiOverlap: "SubmitItem OpenUI overlap",
      submissionRequirement: "submission requirement",
      submissionDialogCoGate: "same AND objective with dialog finish",
      submissionDialogCoGateHint: "Authored co-gate only; it does not prove this dialog opens the submission UI.",
      submissionLevelScriptCoGate: "same AND objective with LevelScript stage max",
      submissionLevelScriptCoGateHint: "Exact authored co-gate only. The LevelScript can provide dialog playback context, but this does not prove it opens or owns the submission UI.",
      levelScriptTaskDependency: "exact LevelScript task dependency",
      levelScriptTaskDependencyHint: "The authored mission objective waits for this exact task tuple. It does not prove that the mission activates the script, owns its Story playback, or selects a Story branch.",
      levelScriptSource: "original LevelScript condition source",
      levelScriptExactEmptyMap: "exact empty executable map",
      levelScriptExecutableMap: "serialized executable map",
      levelScriptTailRecords: "non-executable tail records",
      taskMetadata: "task metadata",
      or: "or",
      nativeDirectCallers: "native direct callers",
      runtimeObjectCandidates: "runtime/object candidates",
      unreviewedCandidates: "unreviewed candidates",
      trackingContextOnly: "HUD/map tracking context only",
      trackingTargets: "Authored tracking targets",
      trackingTargetsHint: "Quest-marker and HUD navigation configuration only. Mission-variable filters are evaluated locally against server-synchronized property values; the server producer and timing remain unknown, and no playback, completion, ownership, or ordering edge is created.",
      trackingFilter: "marker visibility filter",
      missionProperties: "Authored mission variables",
      missionPropertiesHint: "Serialized initial values only. This block does not identify the runtime writer, trigger, or Story owner.",
      nonOwningCrossReference: "non-owning original-data cross-reference",
      unlockQuestPrerequisite: "unlock quest prerequisite",
      unlockMissionPrerequisite: "unlock mission-state prerequisite",
      unlockPreviousSubGame: "prior challenge prerequisite",
      activityStageAssociation: "activity-stage association",
      activityStageLevel: "exact activity quest level",
      activityStageLevelHint: "Typed original stage configuration links this quest to a level; it does not attach Story playback.",
      runtimeActions: "Non-Story runtime actions",
      openUiAction: "Open UI terminal",
      notStoryFile: "typed action resource; not a Story file",
      evidencePolicy: "Evidence policy",
      search: "Search missions",
      searchPlaceholder: "Mission id, name, level, or condition",
      structure: "Structure",
      anyStructure: "Any structure",
      caseStudies: "Evidence case studies",
      fanout: "Has fan-out",
      joins: "Has joins",
      exactFinish: "Exact dialog finish",
      serverOwned: "Server placeholder",
      failure: "Failure condition",
      shown: "shown",
      selectMission: "Select a mission to inspect its pipeline.",
      showHidden: "Show internal/hidden quests",
      dependencies: "Show quest-state condition edges",
      edgeLabels: "Show edge meaning labels",
      controlHelp: "Internal/hidden includes showMode=1000 quests. Quest-state condition edges are dashed CheckQuestState references, not progression arrows. Edge meaning labels name prerequisite and condition edges.",
      orientation: "Orientation",
      auto: "Auto",
      leftRight: "Left → right",
      topBottom: "Top → bottom",
      fit: "Fit graph",
      zoomOut: "Zoom out",
      zoomIn: "Zoom in",
      center: "Center selected",
      dragHint: "Drag anywhere on the graph to pan. Scroll to zoom.",
      serverGateway: "S",
      serverGatewayTitle: "Server-authoritative transition: completion does not prove which successor the server will start.",
      predecessor: "authored predecessor",
      conditionDependency: "quest-state condition",
      externalDependency: "external mission",
      main: "main",
      hidden: "hidden",
      flow: "flow",
      flowCaveat: "Authored lane tag; not proof of exclusivity.",
      clientToServerDialog: "C→S dialog",
      clientToServerProgress: "C→S progress",
      serverGate: "server gate",
      unresolvedSend: "C→S ?",
      serverToClient: "S→C state",
      noObjective: "No exported objective",
      inspectQuest: "Quest runtime trace",
      authority: "Condition authority",
      authoredFields: "Authored fields",
      objectives: "Objectives and gates",
      dialogTreeDefinitions: "Original DialogTree definitions",
      dialogTreeDefinitionHint: "The quest observes completion of this exact current-game DialogTree. Its internal nodes and branches are original-data evidence; the client action that starts it remains unknown unless separately shown.",
      dialogTreeLines: "lines",
      dialogTreeNodes: "nodes",
      dialogTreeConnections: "connections",
      dialogTreeBranchGroups: "multi-option groups",
      dialogTreeNoOrder: "Definition/internal graph only · no cross-file order promotion",
      dialogTreeObserver: "Mission observer",
      dialogTreeObjectiveObserver: "objective",
      dialogTreeFailureObserver: "failure guard",
      clientActions: "Client actions after synchronized state",
      source: "Source",
      protocol: "Selected quest network pipeline",
      asyncCaveat: "These are asynchronous state messages, not a proven synchronous request/response pair.",
      playerWorld: "Player / world",
      client: "Unity client",
      server: "Game server",
      activation: "Activation",
      observe: "Observe / act",
      outbound: "Outbound",
      resolve: "Authoritative decision",
      returnState: "Return state",
      successor: "Next activation",
      activationMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 2 }",
      activationHandler: "StartQuest binds objectives and callbacks",
      worldEvent: "Player/world event satisfies or changes an objective condition.",
      synchronizedHistory: "Reads server-synchronized dialog history.",
      synchronizedState: "Reads server-synchronized quest/mission state.",
      clientObserved: "A client evaluator observes this condition; final completion remains server-authoritative.",
      mixedAuthority: "Combines conditions from more than one authority source.",
      unknownAuthority: "Evaluation ownership is not proven.",
      dialogSend: "CS_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      dialogSendDetail: "Exact outbound payload shape proven in the native client.",
      serverOwnedDetail: "The installed-build GameConditionServerPlaceHolder fallback returns int.MaxValue, not ClientOnly, so StartQuest does not bind a client progress callback.",
      serverPlaceholderKey: "Server objective key",
      serverPlaceholderNoSend: "No condition-specific client request. This placeholder does not send CS_UPDATE_QUEST_OBJECTIVE on the native fallback path.",
      serverPlaceholderReturn: "SC_QUEST_OBJECTIVES_UPDATE { questId, questObjectives[{ conditionId, extraDetails, values, isComplete, descriptionIndex }] }",
      serverPlaceholderReturnDetail: "The server applies progress by the composite (questId, conditionId) identity; conditionId alone is not globally unique.",
      unresolvedDetail: "The exact condition-specific progress/request packet has not been mapped. Do not infer it from a local callback.",
      opaquePolicy: "Validate progress and choose successor(s). Policy is not present in the examined client methods.",
      succeedMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 3 }",
      succeedHandler: "SucceedQuest marks the local quest complete",
      failMessage: "SC_QUEST_FAILED → FailQuest when applicable",
      successorDetail: "A later state = 2 update starts each server-selected successor.",
      exact: "exact",
      anyFinish: "any finish",
      finish: "finish",
      dialog: "dialog",
      state: "state",
      condition: "condition",
      evidence: "Evidence overlay",
      confidence: "confidence",
      noCase: "No curated original-data case note for this mission; the authored graph remains available.",
      missionHandshake: "Mission-level handshake",
      acceptRequest: "C→S  CS_ACCEPT_MISSION { missionId }",
      acceptReturn: "S→C  SC_MISSION_STATE_UPDATE { missionState, succeedId, properties… }",
      acceptCaveat: "No paired SC_ACCEPT_MISSION exists in this protocol; wait for the asynchronous mission-state push.",
      loading: "Loading mission pipeline…",
      loadingMission: "Loading mission…",
      loadError: "Mission pipeline data could not be loaded.",
      retry: "Retry",
      noMatches: "No missions match these filters.",
      noVisibleQuests: "No quests are visible with the current graph filters.",
      join: "join",
      activeJoin: "active AND",
      roots: "entries",
      branches: "fan-outs",
      storyOrder: "Source-proven Story order",
      storyOrderHint: "This is a partial causal graph. It preserves branches, joins, cycles, and unknown pairs; it is not a guessed total file sequence.",
      missionObservedScriptContexts: "Mission-observed LevelScript contexts",
      missionObservedScriptContextsHint: "An original typed mission objective reads the same level and LevelScript that contains native Story playback. This is related-file context, not ownership, activation, or order evidence.",
      observedProperties: "Observed properties",
      propertyWriterUnresolved: "Property writer unresolved",
      embeddedStory: "Nested Story playback",
      embeddedStoryHint: "Original DialogTree connections place this child content at an exact line, entry, or finish boundary in the parent. This is containment, not a complete file-order edge or proof of the parent mission trigger.",
      embeddedBetween: "between parent lines",
      embeddedAtEntry: "at parent entry",
      embeddedAtFinish: "at parent finish",
      readingPopup: "Reading popup",
      strongEdges: "strong order edges",
      questSucceedLifecycle: "Binary-proven quest-success order",
      questSucceedLifecycleHint: "An exact objective Story completion precedes the same quest's authored succeed client action. The installed binary proves the success dispatch; it does not prove that the quest succeeds or which successor branch the server selects.",
      questSucceedLifecyclePath: "objective Story completed → server success state → succeed client action",
      questSucceedLifecycleEdges: "quest-success edges",
      questStartDefinitions: "quest-start definitions",
      questStartDefinitionsTitle: "Authored quest-start Story actions",
      questStartDefinitionsHint: "These rows exist in the original MissionRuntime data, but the complete current AOT census finds no slot-1 dispatcher. They are attached evidence, not scene-order edges.",
      questActionStartNoDispatch: "authored definition · no current AOT dispatch",
      questActionBinaryDispatch: "binary-proven lifecycle dispatch",
      questSucceedLifecycleOriginals: "original lifecycle evidence files",
      weakEdges: "context-only edges",
      orderCycles: "source cycles",
      unknownPairs: "unordered pairs",
      partialFrontier: "partial-order frontier",
      causalEdges: "reduced causal edges",
      forkMerge: "Authored forks and joins",
      dialogConditionalBranch: "Dialog condition branch",
      dialogConditionalTrueArm: "condition true",
      dialogConditionalFalseArm: "condition false",
      dialogConditionalNativeProof: "Native branch selection",
      questFork: "quest fork",
      questForkStructure: "Authored quest-fork structure",
      questForkStructureHint: "Arm roles, guards, terminal shape, and reconvergence come from the original MissionRuntime file. Server activation and exclusivity remain unresolved.",
      questForkMainPathArm: "main-path arm",
      questForkAuxiliaryArm: "auxiliary arm",
      questForkGuardedArm: "typed failure guard",
      questForkObjectiveConditions: "completion conditions",
      questForkReconverges: "first common descendant",
      questForkTerminal: "terminal",
      questForkContinues: "continues",
      questForkFlowSort: "display flow",
      questForkQuestType: "binary quest type",
      questForkShowMode: "binary visibility mode",
      questSemanticFields: "Quest type and visibility semantics",
      questSemanticFieldsHint: "These installed-binary enum names describe client presentation and post-state behavior. They do not select a successor arm.",
      questEnumComparisons: "exact enum comparisons",
      questBlockNotification: "post-lifecycle Block notification",
      questOptionalObjectiveFlag: "Optional objective presentation flag",
      structuredIdentityCensus: "Original structured identity census",
      structuredIdentityCensusCounts: "candidate files / records / direct carriers",
      structuredIdentityReceiverMatches: "receiver matches / unreviewed shapes",
      questForkArmCorridor: "sibling-exclusive quest corridor",
      questForkArmStoryEvidence: "exact related Story evidence",
      questForkArmOriginalFiles: "arm-related original files",
      questForkArmEvidenceBoundary: "These files and Story relations occur on quests reachable only from this sibling arm. They do not prove that the server selected the arm or that sibling arms are mutually exclusive.",
      questForkServerPolicy: "server activation unresolved",
      questForkServerApplication: "Server-applied arm identity",
      questForkServerApplicationHint: "The original binary applies the server-supplied quest identity and state; it does not choose a successor arm.",
      questForkServerApplicationBoundary: "This proves client-side application after server selection, not the server-only selection policy, sibling exclusivity, or Story-file order.",
      questForkEnableApplication: "Validated enable / pause routes",
      questForkEnableApplicationHint: "The original handler combines the packet enable flag with the current runtime pause flag. The serialized previous-state field is not read.",
      questForkEnableRoute: "packet enable / current pause",
      questForkUnreadControls: "serialized but unread",
      questForkStateTransitions: "Validated state routes",
      questForkPacketShape: "Server packet",
      questForkMainPathAuxiliary: "main path + auxiliary",
      questForkAllAuxiliary: "all auxiliary",
      questForkMultipleMainPath: "multiple main-path arms",
      questForkOpenDivergence: "open divergence",
      questForkDivergentTerminals: "divergent terminals",
      questForkMixedTerminal: "terminal + continuing",
      questForkReconverging: "reconverging",
      questForkAuthority: "Quest fork authority",
      serverSelectedStart: "server-selected start; prerequisite topology only",
      questStartReadEvidence: "StartQuest field reads",
      questForkAuthorityHint: "The client initializes the one quest identity selected by the server. This fan-out does not prove that every arm starts or that exactly one arm is exclusive.",
      wholeClientTopologyConsumers: "Whole-client topology consumers",
      verifiedQuestInfoCalls: "verified GetQuestInfo calls",
      activePredecessorConsumers: "active predecessor consumers",
      nonSortFlowConsumers: "non-sort flowIndex consumers",
      topologyLifecycleCalls: "topology-driven lifecycle calls",
      topologyConsumerMethods: "Native field-consumer methods",
      displaySortOnly: "two-row display sort",
      deprecatedDescriptionOnly: "deprecated description fallback",
      mainPathContextOnly: "level/description context selection",
      mainPathCacheOnly: "derived main-path membership cache",
      questVisibilityPresentation: "visibility/tracker presentation",
      questTypePresentation: "quest-type query/presentation",
      questTypePostLifecycle: "quest type read after lifecycle application",
      questTypeBlockNotification: "Block notification after lifecycle application",
      questMerge: "quest join",
      nativeSplitFanout: "native Split fan-out",
      nativeIfElseBranch: "native If/Else branch",
      nativeSwitchBranch: "native Switch branch",
      nativeControlMerge: "native branch convergence",
      nativeMissionStateBranches: "Mission-state Story alternatives",
      nativeMissionStateBranchesHint: "The original LevelScript and installed native getter/comparer mapping prove which Story files occupy each state-controlled arm, including files nominally grouped under another mission. These are alternatives, not Story order or ownership.",
      nativeMissionStateExternal: "cross-mission alternative",
      nativeCrossBoundaryBranch: "complete cross-boundary branch",
      nativeCrossBoundaryStories: "cross-boundary branches",
      nativeCrossBoundaryExternal: "outside nominal mission",
      nativeCrossBoundaryParallelHint: "The original LevelScript paths and installed Split scheduler prove Story-bearing sibling fan-out from one event. Nominal mission grouping does not prove ownership, and sibling slots are not chronological order.",
      nativeCrossBoundaryConditionalHint: "The original LevelScript cases and installed native control mapping prove Story-bearing alternatives from one event. Nominal mission grouping does not prove ownership or order among alternatives.",
      nativeFullArmCoverage: "complete serialized arms",
      nativeSerializedArms: "serialized arms",
      nativeNonStoryArm: "non-Story action arm",
      nativeInactiveArm: "inactive serialized target",
      nativeRuntimeTerminalArm: "runtime terminal",
      nativeArmEntryAction: "entry action",
      nativeArmExclusiveActions: "arm-exclusive actions",
      nativeSharedDownstream: "shared downstream actions",
      nativeFullArmHint: "Every slot is decoded from the runtime-active action map in the original LevelScript and checked against the installed binary mapping. Non-Story sibling actions do not establish Story ownership, chronology, or mission membership.",
      nativeOrderedSequence: "native ordered action sequence",
      nativeSequenceContext: "serialized Branch sequence context",
      nativeSequenceContextHint: "Exact Story paths reach these Branch arms. The other serialized arms stay visible as unresolved runtime context; this projection does not create Story order or ownership.",
      nativeSequenceContextNotAdmitted: "order edge not admitted",
      nativeSequenceContextObserved: "observed Story arm",
      nativeSerializedBranchInventory: "corpus serialized Branch census",
      nativeSerializedBranchInventoryHint: "Both original LevelScript roots are hashed and deduplicated. Exact playback action records are joined to every serialized Branch arm; this inventory is context-only and does not assign mission ownership or file order.",
      nativeSerializedBranchGroups: "serialized Branch groups",
      nativeSerializedBranchArms: "serialized Branch slots",
      nativeSerializedPlaybackArms: "playback-bearing arms",
      nativeSerializedMultiPlaybackArms: "multi-playback groups",
      nativeSerializedBranchMatched: "mission-matching census rows",
      nativeSerializedBranchArmPlayback: "exact playback",
      nativeSerializedBranchReachable: "reachable actions",
      nativeSerializedBranchActions: "reachable native actions",
      nativeSerializedBranchClasses: "decoded record classes",
      nativeSerializedNestedControls: "nested typed controls",
      nativeSerializedNestedArms: "nested serialized arms",
      nativeSerializedNestedPlayback: "nested exact playback",
      nativeSerializedNestedPlaybackArms: "nested playback arms",
      nativeSerializedNestedMultiPlayback: "multi-playback controls",
      nativeSerializedNestedPlaybackControls: "playback controls",
      nativeSerializedNestedPredicateGaps: "playback predicate gaps",
      nativeSerializedNestedControlRefs: "reachable typed controls",
      nativeSerializedNestedControlReferences: "nested control references",
      nativeSerializedNestedSlots: "nested slots",
      nativeSerializedNestedActive: "nested active slots",
      nativeSerializedNestedInactive: "nested inactive slots",
      nativeSerializedNestedUnavailable: "nested unavailable slots",
      nativeSerializedPredicateConflicts: "predicate conflicts",
      nativeSerializedNestedPredicate: "binary predicate",
      nativeStoryTransitions: "Exact native Story transitions",
      nativeStoryTransitionsHint: "Each edge is an original LevelScript path-prefix relation. The typed suffix shows whether playback continues linearly or crosses a parallel, conditional, outcome, or ordered branch.",
      nativeStoryTransitionLinear: "linear",
      nativeStoryTransitionParallel: "parallel fan-out",
      nativeStoryTransitionConditional: "conditional branch",
      nativeStoryTransitionOutcome: "success/failure branch",
      nativeStoryTransitionOrdered: "ordered sequence",
      nativeStoryTransitionOrderedExit: "after ordered sequence",
      nativeStoryTransitionBranching: "branch-bearing transitions",
      nativeRelatedActionGraphs: "Related original LevelScript graphs",
      nativeRelatedActionGraphsHint: "Each file is attached only because an exact serialized event-to-Story path reaches a Story file already in this mission. Its remaining actions are file-local context, not extra mission order.",
      nativeControlReachability: "exact typed downstream reachability",
      nativeControlPath: "control path",
      nativeEventSelector: "event selector",
      nativePredicate: "predicate",
      nativePredicateOpaque: "inline predicate not semantically decoded",
      optionBranches: "dialog option branches",
      typedStorySelectors: "typed system selectors",
      typedStorySelectorHint: "Original typed tables group these Story files as alternatives for one runtime selector. This creates no order edge between alternatives or selector groups.",
      optionDirectContinuation: "direct shared continuation",
      isolatedScenes: "isolated Story files",
      weakOnlyScenes: "weak-context-only files",
      orderCycleHint: "Files in one cyclic component have no proven internal total order.",
      orderEvidence: "order evidence",
      exactFinishes: "exact finishes",
      serverPlaceholders: "server gates",
      graph: "Quest graph",
      nativeBoundary: "Native boundary",
      stateApplicationContract: "Who selects the next quest?",
      serverSelectedIdentity: "server-selected identity/state control",
      stateApplicationValidated: "typed paths validated",
      noClientSuccessorSelector: "no client successor selector",
      lifecycleIdentityFlow: "same packet identity",
      extraThreadScheduler: "Parallel branch runtime authority",
      extraThreadSchedulerValidated: "binary writer shapes validated",
      extraThreadSiblingBoundary: "sibling slots are not chronological order",
      extraThreadDirectCalls: "direct scheduler calls",
      exchanges: "exchanges",
      asynchronousExchange: "asynchronous",
      boundaryOnly: "native boundary only",
      notQuestAttached: "not attached to quest nodes",
      protocolFields: "fields",
      exchangeRequest: "request",
      exchangeRequestAfterLocalEvent: "request after local event",
      exchangeResponse: "response",
      exchangeServerUpdateOrConfirmation: "server update / conditional confirmation",
      exchangeServerPush: "server push",
      exchangeCompletionAcknowledgement: "completion acknowledgement",
      openEvidence: "Show native evidence",
      nativeConfidence: "installed build · native + IFix audit",
      actionChainStep: "action-chain step",
      dialogExchange: "Dialog history",
      dialogEcho: "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      progressSend: "CS_UPDATE_QUEST_OBJECTIVE { questId, conditionId, value, isAdd=false }",
      progressReturn: "SC_QUEST_OBJECTIVES_UPDATE { questId, conditionId, extraDetails, values, isComplete, descriptionIndex }",
      progressCaveat: "Sent when a bound client-side subcondition callback changes; the later state=3 push remains authoritative completion.",
      progressNative: "OnSubConditionProgressChanged (0x183a6fc20) constructs and sends this absolute-value operation.",
      missionDescription: "Mission description",
      descriptionInherited: "mission-level text",
      descriptionOverride: "quest-specific override",
      noDescription: "No localized mission description is exported.",
      storyFiles: "Quest ↔ Story connections",
      missionStoryFiles: "Mission lifecycle ↔ Story connections",
      missionStoryHint: "These files attach to mission acceptance or mission-wide authored context, not to an arbitrary quest block.",
      missionStateDependencies: "Native mission-state → Story dependencies",
      missionStateDependenciesHint: "These exact local mission-state gates are shown independently from quest ownership. Reading synchronized state sends nothing; any separate interaction request is stated on its own evidence row.",
      missionStateDependencyBoundary: "Dependency evidence is counted separately from coverage bindings",
      subGameBindings: "Original-data SubGame runtime shell",
      subGameBindingsHint: "The shipped typed row carries mission id and bound LevelScript id together. The current binary proves that InteractiveLogicChallengeStartPoint resolves this row by SubGame id, reads bindScriptId, looks up the LevelScript, and calls ManualStart. That exact start carrier still does not establish mission or Story ownership; OCR, manual, and gameplay cross-references cannot create that edge.",
      subGameScript: "bound LevelScript",
      subGameMode: "runtime mode",
      subGameNetworkKey: "network-authored key",
      subGameStartSend: "send start request",
      subGameStartReturn: "expect asynchronous enter/start pushes",
      subGameCompleteReturn: "server-authored completion/reward pushes",
      subGameStopSend: "send stop request",
      subGameStopReturn: "expect asynchronous leave push",
      subGameLifecycle: "proven lifecycle use",
      subGameLifecycleHint: "WorldChallengeGame.SendQuit: bindScriptId @ +0x50 → TryGetLevelScript → ManualEnd → stop request",
      noStoryBinding: "0 Story bindings added",
      unassignedStory: "Unassigned Story",
      unassignedStoryHint: "Source files owned by this mission that still lack evidence for a mission lifecycle or quest attachment. They remain visible instead of being guessed onto a block.",
      storyCount: "Story",
      storyToQuest: "Story → Quest",
      questToStory: "Quest → Story",
      storyContext: "Scoped context",
      storyIncomingBadge: "S→Q",
      storyOutgoingBadge: "Q→S",
      storyContextBadge: "CTX",
      relationObjectiveCondition: "objective waits on Story state",
      relationObjectiveTrackingStory: "objective tracking references this Story file (attachment only; not playback or order)",
      relationFailureCondition: "Story state participates in failure guard",
      relationClientStart: "quest start launches Story action",
      relationClientSucceed: "quest success launches Story action",
      relationClientFailed: "quest failure launches Story action",
      relationLevelData: "LevelData explicitly places Story on this quest",
      relationLevelScript: "quest condition scopes this LevelScript Story call",
      relationLevelScriptPropertyConsumer: "quest and Story playback share one exact LevelScript property-change trigger",
      relationQuestObjectiveLevelScriptScope: "the quest objective reads the unique LevelScript that hosts this Story occurrence (shared scope only; not playback ownership or order)",
      relationLevelScriptMission: "LevelScript action and separate script evidence scope this Story file to the mission",
      relationLevelDataScriptHost: "mission-named LevelData contains this validated typed-playback script brief (asset context)",
      relationWorldEntityQuestPlayback: "the quest condition and this leader-trigger playback script reference the same uniquely resolved WorldEntity set (exact foreign-key context, not quest/server activation)",
      relationMissionAreaLevelDataHost: "typed mission-area parent root scopes this validated LevelData script shell",
      relationMissionAreaTriggerContext: "mission-area shape exactly matches the Leader trigger that reaches this Story playback (shared trigger context, not a quest gate)",
      relationAuthoritativeScopeLevelDataHost: "an authoritative mission script and this playback script are siblings in one validated LevelData shell (mission context, not a quest trigger)",
      relationEntityTrackedInteractive: "quest navigation targets an exact script entity whose InteractiveTable narrative template and type_id configure this Story file (context, not playback)",
      relationEntityTrackedScript: "quest navigation targets an entity in the exact script containing this typed Story control path (context, no slot bridge)",
      relationEntityTrackedNativeEvent: "the tracked entity is compared on an exact native event path that raises the custom event playing this Story file (playback context; objective completion remains opaque)",
      relationEntityTrackedProperty: "quest navigation and an exact SavePropertyChanged listener target the same uniquely resolved world entity (property context; server-placeholder completion remains opaque)",
      relationEntityTrackedWorldDialog: "quest navigation targets the exact world entity whose counted componentProperties[94] configures this mission and Dialog Story id (navigation/configuration context, not ownership, playback, completion, or a server exchange)",
      relationSpawnerConfigMission: "an exact server spawner-completion event reaches this Story file and the sole same-level SpawnerConfig names one MissionRuntime (mission context, not one quest)",
      relationHpSpawnerConfigMission: "an exact spawner spawn → entity-list writer → local HP-threshold playback chain and the sole same-level SpawnerConfig name one MissionRuntime (mission context, not one quest)",
      relationMissionGlobalVarPlayback: "a client-global-variable event reaches this Story playback and the exact variable key belongs to one mission (mission context, not one quest)",
      relationRootPlaybackAliasComposed: "an independently connected native root playback executes this exact TimelineAsset through the CutsceneRoot director (owner context, not Story order)",
      relationNpcReadyPlayback: "an exact WaitForNpcProxyReady path reaches this Story playback and the tracked proxy belongs to one mission (mission context, not one quest)",
      relationNpcTargetPlayback: "Play3DRadio explicitly targets this tracked NPC proxy in the same scene (mission context, not proof that the quest starts playback)",
      relationNpcProxySegmentShell: "the tracked NPC proxy occupies the exact authored registry segment whose global id is this Story playback script (mission shell only, not NPC activation)",
      relationMissionStateDependency: "this mission's exact synchronized client state participates in the native IfElse path selecting the Story action (dependency, not ownership)",
      relationTaskMissionStateDependency: "the same authored LevelScript contains an exact taskMap mission-state condition and Story playback, but no serialized control path links them (dependency only)",
      relationMissionStateProcessing: "the exact native true branch plays this Story action while the named mission equals Processing (mission context, not quest causality)",
      relationRadioTriggerMissionState: "one typed LevelData radio-trigger zone co-carries this radio and the named mission-state boundary; native OnEnter checks that state before playback (context, not quest ownership)",
      relationNpcPatrolRadioPlayback: "one typed NPC patrol action contains this radio and maps to the installed native patrol-radio consumer (playback context only; the patrol serializes no mission, quest, or relative Story order)",
      relationAirWallMissionState: "one exact LevelData AirWall co-carries typed mission/quest-state predicates and this pushback radio; synchronized state controls the wall, then later player contact can play the radio (context, not transition causality, ownership, or order)",
      relationNarrativeInteractiveMissionState: "one counted LevelInteractiveData entity co-carries the popup consumer id and mission-state FX key; the original narrative template and native component prove the local playback dependency (not ownership)",
      relationLevelScriptInteractiveNarrative: "exact counted LevelScript interactive configuration binds this Story file to a local narrative object; activation and order remain unresolved",
      relationLevelDataInteractiveNarrative: "exactly bounded LevelData interactive configuration binds this Story file to a local narrative-capable object through either component 94 or a validated int_horn dialog_id property; final records require a nonempty BriefData boundary or the complete empty-script suffix through EOF, and decoded progress locks are availability evidence rather than Story ownership or order",
      relationNativeEventShellPlayback: "a typed custom-event producer reaches this unique Story listener and the producer belongs to one validated mission LevelData shell (mission context, not one quest)",
      relationManualGuideCompletionPlayback: "an exact client-only guide-group start reaches this completion listener and its producer belongs to one mission-named LevelData shell (mission context, not one quest or a server exchange)",
      relationVariantRuntime: "variant MissionRuntime attaches this Story file",
      relationNpcProxy: "unique NPC proxy resolves to this Story file",
      relationNpcProxyEx: "exact mission + NPC proxy resolves to this quest",
      relationNpcProxyMission: "NpcProxyEx explicitly scopes this Story file to the mission",
      relationUniqueMissionTrackedNpcProxyDialog: "all typed tracking uses of this exact NPC proxy agree on the mission; the server selects one registered interaction dialog row (shared mission context, not quest selection or Story order)",
      relationNpcProxyTrackingDialog: "quest navigation tracks this exact NPC proxy; its current registered interaction dialog contains a typed next-dialog route (navigation/configuration context only)",
      relationNpcProxyLazyDestroyDialog: "quest navigation tracks this exact NPC proxy; native deactivation applies its authored lazy-destroy dialog as an interaction override (configuration context, not quest activation or playback causality)",
      relationMissionTrackedNpcPatrol: "typed LevelData resolves the checkpoint listener's NPC alias and patrol, while same-scene quest navigation tracks that exact world entity in one mission (mission context only; candidate quests are not activation, playback, completion, or ownership)",
      relationMissionTrackedWorldEntityLevelScript: "an exact local Leader-trigger playback script references world entities tracked by only one mission (shared authored script/entity context only; candidate quests do not prove the trigger gate, activation, playback, completion, or ownership)",
      relationMissionTrackedWorldEntityLevelScriptStage: "the server synchronizes this LevelScript stage before an exact local StageChanged playback path; typed world-entity tracking identifies one mission context, but no candidate quest is proven to write the stage",
      relationFocusModeRadio: "FocusMode explicitly scopes its interaction-locked radio to this mission",
      relationSnsMissionLink: "SNS row explicitly links this conversation to the mission",
      relationTimelineBlack: "serialized Timeline contains this black-screen Story inside a dialog root",
      relationTimelineBlackUnresolved: "serialized Timeline root is proven; its dialog/mission anchor is unresolved",
      relationDialogNarrativeAction: "typed DialogTree action presents this black-screen text inside its parent dialog",
      relationDialogNarrativeActionUnscoped: "typed DialogTree containment is exact; parent mission/quest placement is unresolved",
      relationDialogLeftSubtitleAction: "typed DialogTree action presents this text in the local left-subtitle UI",
      relationDialogLeftSubtitleActionUnscoped: "left-subtitle containment is exact; parent mission/quest placement is unresolved",
      relationDialogStoryPlayback: "binary-proven DialogTree carrier can play this Story file from the parent dialog",
      relationDialogStoryPlaybackUnscoped: "binary-proven DialogTree playback is exact; parent mission/quest placement is unresolved",
      relationDialogPrimeStoryPlayback: "binary-proven prime-node route can reach this Story carrier; the quest only observes the parent dialog's completion (dependency, not playback trigger or ownership)",
      relationDefinitionOnly: "original text definition; no current-build playback consumer recovered",
      relationMissionAccept: "NPC dialog accepts this mission",
      relationMissionArea: "Story id is embedded in this objective's mission-area id",
      relationStoryGraphBranch: "authored dialog route shares this quest anchor",
      relationLevelScriptSequence: "LevelScript next-id chain shares this quest anchor",
      relationQuestProcessingAction: "quest Processing event launches this client Story action",
      relationQuestCompletedAction: "quest-completed LevelScript action launches Story",
      relationQuestStateGate: "triggered LevelScript playback is gated by this quest being Processing",
      relationNativeBlackAction: "native client black-screen action plays these exact serialized text lines",
      relationNativePlaybackUnscoped: "native playback action is proven; mission/quest trigger unresolved",
      relationUnassignedStory: "no evidence-backed pipeline attachment yet",
      relationRuntimeReference: "direct runtime reference; timing unresolved",
      openInStory: "Open in Story",
      storyEvidence: "Arrow direction comes from runtime semantics: conditions are Story → Quest; native QuestAction slots and gated completed-quest LevelScript actions are Quest → Story. LevelData, scoped LevelScript, variant-runtime, authored one-hop routes, exact NPC-proxy joins, and unique typed WorldEntity-set joins are context. A shared WorldEntity set does not prove quest or server activation. Typed DialogTree narrative masks are local presentation, never a server exchange. Mission acceptance stays on the mission shell. Spatial and file-order guesses are never promoted.",
      triggerRoute: "Recovered trigger route",
      triggerPlayback: "playback",
      triggerCondition: "condition",
      triggerContext: "context only",
      triggerContextOwnerUnresolved: "exact carrier context · owner unresolved",
      triggerDependency: "dependency only",
      triggerUnresolved: "trigger known · owner unresolved",
      triggerPlaybackAlias: "root playback alias · owner unresolved",
      triggerPlaybackAliasConnected: "root playback alias · owner connected",
      triggerDefinition: "definition only · no consumer",
      offlineRecoveryBoundary: "Offline recovery boundary",
      projectAuthoredBoundary: "Project-authored WebUI content",
      projectAuthoredEvidence: "Excluded from original-game recovery",
      partialRecoveryBoundary: "Partial registered carrier",
      runtimeContextRecoveryBoundary: "Exact runtime context boundary",
      offlineRecoveryNoGraphEdge: "no ownership or order edge",
      offlineRecoveryConsumer: "Consumer boundary",
      runtimeRecoveryActivation: "Activation boundary",
      runtimeRecoveryPlayback: "Playback boundary",
      offlineRecoveryOrder: "Order boundary",
      offlineRecoveryReopen: "Reopen when",
      offlineRecoverySources: "Original-data files",
      projectAuthoredSources: "Project source files",
      runtimeRecoveryNominalMission: "Nominal Story mission",
      runtimeRecoveryContextMission: "Validated runtime shell",
      runtimeRecoveryContextMissions: "Validated runtime contexts",
      runtimeRecoveryContextBoundary: "Context boundary",
      runtimeRecoveryParentDialogDependency: "Exact parent DialogTree carrier dependency - activation/order unknown",
      runtimeRecoveryNpcDialogContext: "Exact NPC dialog context - no playback owner or order edge",
      runtimeRecoveryNpcSelectionContext: "Exact NPC runtime selection context - no relative order",
      runtimeRecoveryNpcCrossMissionContext: "Exact cross-mission NPC runtime context - no ownership or order edge",
      runtimeRecoveryNpcMultiMissionContext: "Exact multi-mission NPC runtime contexts - alternatives, not chronology",
      runtimeRecoveryQuestAnchors: "Shell quest anchors",
      runtimeRecoveryGate: "Decoded gate",
      runtimeRecoveryNativePaths: "Exact native path",
      runtimeRecoveryPlaybackRoots: "Exact playback root",
      runtimeRecoveryCarrierParents: "Exact carrier parents",
      runtimeRecoverySnsLink: "Authored SNS mission link",
      offlineRecoveryRelatedOriginalData: "Related original-data bundle",
      offlineRecoveryPrtsOrder: "terminal order",
      offlineRecoveryPrtsCarrier: "Exact PRTS archive carrier (catalog order, not mission chronology)",
      offlineRecoveryDialogSummary: "Exact dialog summary artifact (not playback evidence)",
      offlineRecoveryStoryRelation: "Story relation",
      offlineRecoveryMissionTextRows: "mission/objective text rows",
      offlineRecoveryGaps: "source-bounded activation gaps",
      offlineRecoveryGapsHint: "These rows are source-bounded and add no mission-order edge. Original-game rows expose exact definitions or runtime contexts without a recovered mission activator; project-authored rows are explicitly not game data. OCR and manual order are not used here.",
      offlineRecoveryInternalTimeline: "internal Timeline",
      offlineRecoveryLines: "lines",
      offlineRecoveryDefinedOptions: "Defined options (route unresolved)",
      offlineRecoveryDefinedOptionsResolved: "Defined options",
      offlineRecoveryTableOnlyRegistration: "DialogId table-only registration",
      offlineRecoveryPrintableTokens: "Printable-only DialogId tokens (not branch targets)",
      offlineRecoveryDialogTreeAbsent: "DialogTree asset absent",
      offlineRecoveryDialogTreeExact: "exact DialogTree asset",
      offlineRecoveryDialogTreeBranches: "Internal DialogTree branches",
      offlineRecoveryParentDialogTrees: "Registered parent DialogTrees",
      offlineRecoveryParentTreeBranches: "internal branch groups",
      offlineRecoveryInternalLineConnections: "Exact internal line connections",
      offlineRecoveryParentLevelContexts: "Exact parent level/dungeon asset shells",
      offlineRecoveryParentLevelBoundary: "Related original files only; this does not prove activation, ownership, branching, or order.",
      offlineRecoveryDungeonCatalogMetadata: "Dungeon catalog metadata (not chronology)",
      offlineRecoveryRelatedLevelFiles: "Related level files",
      offlineRecoverySubGameRuntime: "Exact BlackBox SubGame runtime shell",
      offlineRecoverySubGameBindScript: "bound LevelScript",
      offlineRecoverySubGameTaskLanes: "Authored task lanes (not Story order)",
      offlineRecoverySubGameMainTasks: "main",
      offlineRecoverySubGameExtraTasks: "extra",
      offlineRecoverySubGameFailTasks: "fail",
      offlineRecoverySubGameParentPlayback: "Exact parent playback",
      offlineRecoverySubGameDefinitionOnlyParents: "Definition-only in bound script",
      offlineRecoverySubGamePlaybackCoverage: "parent playback coverage",
      offlineRecoverySubGameTaskTopology: "Exact task completion topology",
      offlineRecoverySubGameTaskTopologyNull: "No authored task map",
      offlineRecoverySubGameTasks: "tasks",
      offlineRecoverySubGameConditions: "conditions",
      offlineRecoverySubGameTracked: "tracked",
      offlineRecoverySubGameInternal: "internal",
      offlineRecoverySubGameConditionTypes: "condition families",
      offlineRecoverySubGameCombineExpressions: "serialized formulas",
      offlineRecoverySubGameTaskDescriptions: "display objectives",
      offlineRecoverySubGameTopologyBoundary: "Task conditions and main/extra/fail lanes are exact original-data structure. They serialize no task-successor or Story-file order edge.",
      offlineRecoverySubGameActionTopology: "Exact runtime control graph",
      offlineRecoverySubGameActionTopologyEmpty: "Empty authored action map",
      offlineRecoverySubGameActionEvents: "event roots",
      offlineRecoverySubGameActionPhysicalEvents: "physical event rows",
      offlineRecoverySubGameActionEventSlot: "active indexed listener",
      offlineRecoverySubGameActionEventPriority: "listener priority",
      offlineRecoverySubGameActionEventTriggerActive: "active-during mode",
      offlineRecoverySubGameActionEventFilter: "filter",
      offlineRecoverySubGameActionNodes: "actions",
      offlineRecoverySubGameActionEdges: "edges",
      offlineRecoverySubGameActionFanouts: "typed fan-outs",
      offlineRecoverySubGameActionSequences: "ordered sequences",
      offlineRecoverySubGameActionChoices: "conditional choices",
      offlineRecoverySubGameActionLoops: "loops",
      offlineRecoverySubGameActionConvergence: "convergences",
      offlineRecoverySubGameActionCycles: "cycles",
      offlineRecoverySubGameActionShadowed: "runtime-shadowed records",
      offlineRecoverySubGameActionTerminals: "missing-slot terminals",
      offlineRecoverySubGameActionActiveSlot: "active runtime slot",
      offlineRecoverySubGameActionEventTypes: "event families",
      offlineRecoverySubGameActionTypes: "action families",
      offlineRecoverySubGameActionStoryTargets: "typed Story targets",
      offlineRecoverySubGameActionTopologyBoundary: "Edges are exact within one LevelScript. Header, action, and getter IDs all use the last serialized indexed slot, and absent positive action slots end normally. Event roots are independently invoked listeners: physical list order and listener priority are not Story chronology. Control flow orders Story files only when a typed action explicitly targets one.",
      offlineRecoveryEvidenceParentTreePartition: "Exact registered parent-tree line partition",
      partialRecoveryEvidenceParentTreePartition: "Partial registered parent-tree line partition",
      partialRecoveryCoverage: "Registered coverage",
      partialRecoveryUnmatchedRows: "Unmatched authored rows",
      partialRecoveryRowIdPositions: "Table row-id positions (cross-reference only, not order)",
      offlineRecoveryAuthoredSplit: "authored split",
      offlineRecoveryAuthoredConvergence: "authored convergence",
      offlineRecoveryTerminalOptions: "Terminal option routes",
      offlineRecoveryFinishId: "serialized finishId",
      offlineRecoveryFinishIdAbsent: "finishId not serialized",
      offlineRecoveryEvidenceResultBranch: "Exact result branch",
      offlineRecoveryEvidenceTrackedNpc: "Mission-tracked NPC dialog — playback owner unknown",
      offlineRecoveryEvidenceEmptyHost: "Definition only \u2014 mission script empty",
      offlineRecoveryEmptyHost: "Exact empty mission host",
      offlineRecoveryEmptyHostBoundary: "The mission-named LevelData contains one propertyless LevelScript. Its action list, UID records, and task maps are empty, so it cannot activate or order these Story definitions.",
      offlineRecoveryEvidenceDefinitionOnly: "Definition only — activator unknown",
      offlineRecoveryEvidenceUnregistered: "Unregistered definition — no runtime consumer",
      offlineRecoveryEvidenceRadioOnly: "Radio definition only — consumer unknown",
      offlineRecoveryEvidenceBinaryRadio: "Definition only — no consumer on current original-data surfaces",
      offlineRecoveryEvidenceNpcProxyConsumer: "Native NPC-proxy consumer - mission activation unknown",
      offlineRecoveryEvidenceBinarySns: "SNS definition only - no consumer on current original-data surfaces",
      offlineRecoveryEvidenceBinaryReadingPopup: "Readable definition only - no activator on current original-data surfaces",
      offlineRecoveryEvidenceBinaryUnregisteredDialog: "Unregistered dialog definition - no consumer on current original-data surfaces",
      offlineRecoveryEvidenceBinaryRegisteredDialogTree: "Registered DialogTree definition - no activator on current original-data surfaces",
      offlineRecoveryEvidenceMissionlessNativePlayback: "Exact local playback - mission bridge and order unknown",
      runtimeRecoveryEvidenceSameMissionLevelDataPlayback: "Exact native playback in this mission shell - quest trigger and order unknown",
      runtimeRecoveryEvidenceLuaControllerPlayback: "Exact shipped-Lua playback - mission owner and order unknown",
      runtimeRecoveryEvidenceDialogTreePlaybackContext: "Exact DialogTree playback in quest context - relative order unknown",
      runtimeRecoveryEvidenceQuestStateGate: "Exact quest-state-gated playback - relative order unknown",
      runtimeRecoveryLuaController: "Shipped Lua controller",
      runtimeRecoveryLuaCall: "Typed Lua playback call",
      runtimeRecoveryEvidenceCrossMissionLevelDataPlayback: "Exact native playback in a related mission shell - ownership and order unknown",
      offlineRecoveryEvidenceCutsceneRoot: "Cutscene root resolved - mission activator unknown",
      offlineRecoveryEvidenceCutsceneAlias: "Exact cutscene root/playable alias - mission activator unknown",
      offlineRecoveryCutsceneAlias: "Exact root/playable identity",
      offlineRecoveryCutsceneAliasRootRole: "root definition",
      offlineRecoveryCutsceneAliasPlayableRole: "played timeline asset",
      offlineRecoveryNativeConsumer: "Original-binary consumer",
      offlineRecoverySnsDefinition: "SNS internal definition",
      offlineRecoveryMissingAudio: "audio ids absent",
      offlineRecoveryAudioMembership: "audio membership",
      offlineRecoveryCarrierAudit: "typed carrier audit",
      offlineRecoveryBinaryRootToken: "original-binary root token",
      offlineRecoveryMissionTracking: "Mission NPC tracking context (navigation only)",
      offlineRecoveryNpcProxyConsumer: "Exact missionless NpcProxyEx row (index is not chronology)",
      offlineRecoveryTrackedQuests: "tracked quests",
      offlineRecoveryRuntimeMission: "runtime mission",
      offlineRecoveryMissionBranch: "Mission fork/join context (Story arm unresolved)",
      offlineRecoveryMissionSequence: "Authored linear quest context (Story placement unresolved)",
      offlineRecoveryMissionTopology: "Exact authored mission topology",
      offlineRecoveryParallelRendezvous: "Parallel prerequisites with AND rendezvous (not a player choice)",
      offlineRecoveryObjectiveConjunction: "AND-gated objective conditions",
      offlineRecoveryObjectiveConjunctionBoundary: "All predicates are required, but their evaluation order and Story placement are not serialized.",
      offlineRecoveryLevelScriptPlaybackInventory: "Exact related LevelScript playback",
      offlineRecoveryLevelScriptPlaybackPresent: "independent playback roots",
      offlineRecoveryLevelScriptPlaybackAbsent: "absent targets",
      offlineRecoveryLevelScriptPlaybackBoundary: "These are independent action-list roots. Serialized list position is not execution order, and absent targets receive no playback or Story placement edge.",
      offlineRecoveryLinearTopology: "linear quest chain",
      offlineRecoveryMainPath: "authored main path",
      offlineRecoveryQuestStateDependency: "authored quest-state dependency",
      offlineRecoveryQuestFailureGuard: "authored one-way quest failure guard",
      offlineRecoveryDialogFailureGuard: "authored dialog-completion failure guard",
      offlineRecoveryConditionPath: "condition path",
      offlineRecoveryMissionTopologyBoundary: "Quest predecessor links and main-path membership are exact; Story placement, branch exclusivity, and server successor selection remain unresolved.",
      offlineRecoveryTalkDependency: "LevelScript talk-completion dependency (not playback)",
      offlineRecoveryDialogResultBranch: "Exact LevelData / LevelScript dialog branch",
      offlineRecoveryDialogStart: "Configured start dialog",
      offlineRecoveryDialogResult: "result case",
      offlineRecoveryControlPath: "serialized control path",
      offlineRecoveryMissionRuntimeAbsent: "nominal MissionRuntime asset absent",
      offlineRecoveryDialogBranchBoundary: "Cases are mutually exclusive outcomes. The local custom-event producer and a nominal MissionRuntime quest owner are not serialized here.",
      offlineRecoveryPostDialogAction: "Post-dialog local action",
      offlineRecoveryTestStub: "Exact test popup stub; no RichContent payload",
      offlineRecoveryCrossMissionTracking: "Cross-mission SNS tracking (navigation only)",
      offlineMissionShell: "Story-only recovery shell",
      offlineMissionShellHint: "No MissionRuntimeAsset exists in the current export. This page exposes exact table definitions and current-build negative carrier evidence only; it has no quest, ownership, playback, handshake, or order edge.",
      storyAggregateShell: "Declared Story variant aggregate",
      storyAggregateShellHint: "This Story namespace combines exact serialized evidence from its declared mission variants. It is not a MissionRuntime mission and does not establish mission ownership, quest ownership, branch selection, or extra chronology.",
      storyAggregateVariants: "Declared mission variants",
      storyAggregateOriginals: "Variant MissionRuntime source files",
      questAttachmentDiagnostic: "Story ownership unresolved",
      questAttachmentDiagnosticHint: "Exact offline evidence closes this broad Story co-membership as non-owning. It does not create a quest-to-Story or order edge.",
      questAttachmentDiagnosticStories: "Diagnostic Story context",
      questAttachmentDiagnosticFiles: "Related original-data files",
      questAttachmentDiagnosticProperty: "Exact property record",
      questAttachmentDiagnosticProxy: "Tracked NPC proxy",
      rejectedPlaybackCandidate: "Rejected playback candidate",
      rejectedPlaybackBoundary: "binary-proven boundary · no graph edge",
      rejectedPlaybackLiteral: "Lua literal",
      rejectedPlaybackStoryKey: "exported Story key",
      rejectedPlaybackCaseReason: "case-sensitive native resource lookup",
      triggerQuest: "quest",
      triggerMission: "mission",
      triggerOwnershipGap: "missing mission / quest owner",
      triggerServerMessage: "server message",
      triggerNativeEvent: "native event",
      triggerLevelScript: "LevelScript",
      triggerLevelData: "LevelData",
      triggerAvailabilityCondition: "interactive availability condition",
      triggerNarrativeInteractive: "narrative interactive",
      triggerDialogDefinition: "dialog definition",
      triggerNativeAction: "playback action",
      triggerParentStory: "parent Story file",
      triggerDialogTimeline: "dialog Timeline",
      triggerStoryRoot: "CutsceneRoot Story key",
      triggerStory: "Story file",
      triggerLuaController: "Lua controller",
      triggerNativePlayback: "native playback",
      triggerOriginalTableRow: "original table row",
      triggerExactPaths: "exact native paths",
      triggerEvents: "Triggering events",
      triggerEventsHint: "Each row is one exact serialized event-to-action path. Multiple rows are alternatives or distinct occurrences; they are not a guessed sequence.",
      triggerListener: "listener",
      triggerActionChain: "action chain",
      triggerLocalTransport: "local dispatch",
      triggerServerTransport: "server-backed dispatch",
      triggerUnknownTransport: "transport unresolved",
      noStoryFiles: "No evidence-backed Story connection is attached to this quest block.",
      runtimeObserved: "observed runtime playbacks",
      runtimeTraceOverlay: "Observed runtime trace",
      runtimeTraceHint: "Captured execution is shown as an observational overlay. Active quest state is temporal context, not authored Story ownership, and observed sequence does not replace the source-proven partial order.",
      exactRuntimeChains: "exact event/action/playback chains",
      observedForks: "observed forks",
      observedMerges: "observed merges",
      activeQuestContext: "active quest context",
      noAuthoredPromotion: "no authored ownership/order promotion",
      observedRoute: "captured route",
      runtimeSession: "session",
      observedSequence: "observed sequence",
      summarySections: "Summary sections",
      summaryFocusAll: "All",
      summarySectionStructure: "Mission structure & order",
      summarySectionRuntime: "Native & observed runtime",
      summarySectionStory: "Story attachments",
      summarySectionQueues: "Unassigned & boundary queues",
    },
    zh: {
      rootPlaybackAliases: "\u6839\u64ad\u653e\u522b\u540d",
      exactDialogRootAlias: "\u7cbe\u786e DialogTree \u6839\u522b\u540d",
      exactDialogRootAliasBoundary: "\u5b57\u8282\u5b8c\u5168\u76f8\u540c\u7684\u8f7d\u8377\uff1b\u4e0d\u58f0\u79f0\u6fc0\u6d3b\u65b9\u6216\u670d\u52a1\u5668\u5206\u652f\u9009\u62e9",
      relationRootPlaybackAliasComposed: "\u72ec\u7acb\u5df2\u8fde\u63a5\u7684\u539f\u751f\u6839\u64ad\u653e\u901a\u8fc7 CutsceneRoot director \u6267\u884c\u8be5\u7cbe\u786e TimelineAsset\uff08\u5f52\u5c5e\u4e0a\u4e0b\u6587\uff0c\u975e\u5267\u60c5\u987a\u5e8f\uff09",
      relationMissionTrackedWorldEntityLevelScript: "精确的本地队长触发器播放脚本引用了仅由一个任务跟踪的世界实体（仅共享的脚本/实体创作上下文；候选任务节点不证明触发门、激活、播放、完成或所有权）",
      relationMissionTrackedWorldEntityLevelScriptStage: "服务器先同步该 LevelScript 阶段，再进入精确的本地 StageChanged 播放路径；类型化世界实体跟踪只确定唯一任务上下文，不证明任何候选任务节点写入了该阶段",
      relationQuestProgressLockedInteractive: "每个播放实例都由精确的交互实体事件路径触发；该实体的强类型进度锁等待此任务达到已完成状态（仅为本地上下文，不证明剧情归属，也不证明任务激活、播放或完成因果）",
      subGameBindings: "原始数据 SubGame 运行时外壳",
      subGameBindingsHint: "游戏内置的类型化记录同时包含使命 ID 与绑定的 LevelScript ID。当前二进制证明 InteractiveLogicChallengeStartPoint 会按 SubGame ID 解析该记录、读取 bindScriptId、查找 LevelScript 并调用 ManualStart。这个精确启动载体仍不证明使命或剧情所有权；OCR、人工记录和实机交叉参考都不能创建这条边。",
      subGameScript: "绑定的 LevelScript",
      subGameMode: "运行模式",
      subGameNetworkKey: "网络原始键",
      subGameStartSend: "发送启动请求",
      subGameStartReturn: "等待异步进入/启动推送",
      subGameCompleteReturn: "服务器决定的完成/奖励推送",
      subGameStopSend: "发送停止请求",
      subGameStopReturn: "等待异步离开推送",
      subGameLifecycle: "已证明的生命周期用途",
      subGameLifecycleHint: "WorldChallengeGame.SendQuit：bindScriptId @ +0x50 → TryGetLevelScript → ManualEnd → 停止请求",
      noStoryBinding: "新增剧情绑定：0",
      evidencePolicy: "证据政策",
      eyebrow: "实验视图 · 客户端 / 服务器证据",
      title: "任务流程",
      scope: "展示任务节点结构，并明确标出原生客户端与服务器之间的边界。",
      warning: "前置箭头只表示客户端可见的条件关系；下一个同步到客户端的任务状态仍由服务器决定。",
      missionSource: "MissionRuntime 来源",
      sourceCompletePersistent: "完整 Persistent 覆盖",
      sourceStreamingFallback: "StreamingAssets 回退",
      sourceExplicitRoot: "显式任务根目录",
      sourceChangedFiles: "已变更基础文件",
      sourceMissingFiles: "缺少基础文件",
      missions: "个任务",
      quests: "个任务节点",
      connectedStory: "已连接剧情",
      unlinkedStory: "未分配剧情",
      nativePlaybackGaps: "原生路径缺口",
      luaPlaybackAccepted: "已采纳 Lua 播放",
      luaTablePlaybackAccepted: "Lua 表归属播放",
      luaPlaybackRejected: "Lua 大小写拒绝",
      luaHandleDispatchers: "Lua 运行时分派分支",
      luaPlaybackAudit: "随游戏发布的 Lua 普查",
      cinematicProducer: "原始二进制播放生产者",
      definitionOnlyStory: "仅有定义的黑屏文本",
      nonMissionContentStory: "非使命内容",
      nonMissionContentStoryHint: "这些剧情 ID 已由原生数据证明属于非使命内容：按说话人分的电台续播语音、角色 SNS 话题、工厂教程动作、干员档案语音、舰船系统强类型对话树，或在所有相关强类型树中均无载体的完整角色/类别定义。定义缺口不证明播放或顺序；仅依据原生字段和强类型消费者判定，绝不依据文件名。",
      missionGraph: "跨使命关系",
      missionGraphUpstream: "上游",
      missionGraphDownstream: "下游",
      missionGraphRequiresCompleted: "需已完成",
      missionGraphRequiresProcessing: "需进行中",
      missionGraphAbortsOnCompleted: "完成即中止",
      missionGraphUnclassified: "操作数未定性",
      missionGraphInterleaving: "与之交错",
      missionGraphHint: "来自读取其他使命（或其他使命任务）状态的原始任务条件。只有“需已完成”表示先后顺序；“需进行中”是并行窗口，“完成即中止”是互斥关系。使命解锁顺序由服务端决定，因此没有关系并不能说明两个使命之间没有顺序。",
      missionGraphEdgesStat: "跨使命先后关系",
      envTalkContext: "使命相关的环境对话",
      envTalkContextStat: "任务追踪的环境对话",
      envTalkStateContextStat: "状态条件关联的环境对话",
      envTalkContextBoundary: "导航/状态上下文，非播放归属",
      envTalkContextHint: "这里展示两条精确但不表示归属的路径：带类型的 NpcProxyTrackingInfo 可把任务引导到配置了环境台词的 NPC 代理；环境 NPC 切换器条件则可控制包含某个环境对话簇的、同关卡内唯一匹配的 NPC 组。它们只说明导航或世界状态可用性，不会播放、拥有、启动或完成这些台词，也不能证明时序或服务端交互。",
      relationEnvTalkTrackedProxy: "任务追踪 NPC 代理上的环境台词",
      relationEnvTalkSwitcherState: "受使命/任务状态条件控制的环境 NPC 簇",
      relationEnvTalkMultipleContext: "多条精确环境对话上下文路径",
      trackedByQuests: "追踪任务",
      missionlessSubGameStory: "SubGame 范围剧情",
      missionlessRuntimeStory: "运行时接收器范围剧情",
      nativeGapQueue: "未连接的原始二进制触发队列",
      nativeGapQueueHint: "播放路径已经精确恢复，但仍缺少使命/任务身份。数量按唯一剧情文件统计，不同事件族可能重叠。",
      missionlessSubGameNodes: "无使命所有者的原始数据运行时节点",
      missionlessSubGameNodesHint: "这些是精确的 SubGame → bindScriptId → 原生播放 → 剧情链。它们为未连接文件补充结构，但不计为使命拥有的剧情绑定。",
      noMissionOwner: "无使命所有者",
      exactPlayback: "精确原生播放",
      exactReceiverNodes: "精确序列化运行时接收器",
      playbackGate: "精确接收器播放条件",
      playbackGateTrue: "条件为真时允许播放",
      playbackGateBoundary: "该原始二进制条件只控制此接收器的播放；它不能证明任务归属、Story 文件之间的顺序或后续服务器状态写入。",
      postPlaybackControl: "精确的播放后控制流",
      postPlaybackBranch: "类型化本地分支点",
      postPlaybackServerHandoff: "服务器交接（处理器未解析）",
      postPlaybackBoundary: "类型化后继字段只证明播放后的本地动作图。回调标签不能识别服务器处理器、使命/任务归属、状态写入或跨 Story 时序。",
      postPlaybackVariableBridge: "播放后变量桥接审计",
      postPlaybackVariableSetterStat: "类型化播放后变量写入",
      postPlaybackVariableListeners: "精确变量监听器行",
      postPlaybackVariableMatches: "同脚本/键精确匹配",
      postPlaybackVariableClosed: "路径已关闭",
      postPlaybackVariableBoundary: "写入器和监听器键来自当前版本的精确序列化。在 Set<T>.Execute 的通知类型得到证明前，连接仍不能成为 Story 顺序证据；当前版本完全没有同关卡、同脚本、同键的精确连接。",
      exactReceiverNodesHint: "每个节点都来自原始 LevelScript 事件选择器，并有到剧情播放的精确控制路径；它能组织更多恢复文件，但不声明使命或任务所有者。",
      activationFrontier: "离线激活边界",
      nominalMissionHostCheck: "名义使命 LevelData 检查",
      nominalMissionHostExcludes: "已验证宿主不包含接收脚本",
      noSameLevelNominalMissionHost: "同关卡不存在名义使命宿主",
      nominalMissionCandidateBoundary: "仅文件名/索引候选；不表示使命所有者或图边",
      activationClass: "静态激活分类",
      startPolicy: "LevelScript 启动策略",
      binaryStartPolicy: "二进制已验证的启动转换",
      binaryStartPolicyBoundary: "当前二进制证明：处于 Active 且尚未结束的 SameWithActive 脚本会绕过区域/手动门进入 PreStart。它不识别激活该脚本的使命或服务器转换，也不排列 Story 文件。",
      binaryManualSelfControl: "二进制已验证的自启动载体",
      binaryManualSelfControlBoundary: "当前二进制与元数据通用地证明 CURRENT_LEVEL_ID/CURRENT_SCRIPT_ID 目标；本行另有原始序列化事件头指向 ManualStart。它只证明本地自启动，不证明使命所有者、所选分支或跨 Story 顺序。",
      binaryPublicStateControl: "二进制已验证的公共状态载体",
      binaryPublicStateControlBoundary: "当前客户端只有两条直接来自服务器的公共状态输入：完整场景 LevelScript 快照与增量状态通知。它们证明 Enabled 由服务器提供，但都不携带使命、任务、Story 或分支原因，也不排列 Story 文件。",
      binaryClientActiveRequest: "二进制已验证的客户端 Active 请求选择器",
      binaryClientActiveRequestBoundary: "原始 LevelData 类型选择这条通用运行时分支。已验证的快照/通知载体证明 Enabled 由服务器提供，但服务器端选择规则仍不可见；它也不证明某次空间结果、服务端是否接受 Active、任务归属、事件是否发生或 Story 顺序。",
      binaryActiveVolume: "原始创作激活范围",
      binaryActiveVolumeBoundary: "该几何直接解码自原始 LevelScriptData，门控行为来自当前游戏二进制。它不证明玩家位置、运行时门控结果、使命归属、事件是否发生或 Story 顺序。",
      binaryClientStartRequest: "二进制已验证的客户端启动请求生命周期",
      binaryClientStartRequestBoundary: "当前客户端证明 ManualStart 标记 → PreStart → 类型化 CS 启动请求 → PreStartActionRunning。公共网络发送 API 在当前 AOT 中没有直接调用者；此行仍无已创作的静态载体，也未解析使命/服务器选择器。",
      binaryActivePhaseReceiver: "二进制已验证的 Active 阶段接收器",
      binaryActivePhaseReceiverBoundary: "该精确原始事件头序列化为 Active，而非 Start。当前二进制证明触发图在 Setup 期间注册，并在 ActiveBegin 中启用 Active 接收器。这只证明无需 ManualStart 即可用，不证明谁选择了公共 Active、事件是否发生、使命归属、分支或 Story 顺序。",
      binarySubGameManualStart: "二进制已验证的 SubGame 启动载体",
      binarySubGameManualStartBoundary: "当前二进制与类型化原始记录证明 SubGame ID → bindScriptId → LevelScript 查找 → ManualStart。它是交互启动载体，不证明使命所有权、所选分支或跨 Story 顺序。",
      levelDataContainer: "已验证的 LevelData 容器",
      encounterController: "二进制已证实的遭遇战控制器",
      encounterModuleNamespace: "遭遇战 LsmPtr 模块命名空间",
      moduleMatchesReceiver: "模块 ID 与接收脚本 ID 相同",
      relatedModuleNamespace: "相关模块 ID",
      encounterSpawner: "强类型遭遇战生成器",
      noConfiguredSpawner: "未配置生成器",
      relatedOriginalFile: "相关原始数据文件",
      encounterControllerBoundary: "遭遇战类型及相关文件已有精确证据；使命归属、剧情激活、分支和顺序仍未解决。",
      dungeonSceneContext: "精确 Dungeon/SubGame 场景上下文",
      boundReceiverScript: "接收器就是绑定脚本",
      siblingReceiverScript: "接收器是同场景兄弟脚本",
      dungeonMissionShellContext: "类型化地下城使命外壳上下文",
      dungeonSceneBoundary: "同场景宿主和可用性前置条件仅提供上下文，不识别剧情所有者、触发器或顺序。",
      exactRuntimeTarget: "精确原始数据运行时目标",
      encounterModule: "遭遇战模块",
      modulePointer: "关卡脚本模块指针",
      activationSlot: "激活触发器槽位",
      battleExitSlot: "战斗退出触发器槽位",
      localEntitySlots: "本地敌人槽位",
      missingOwnershipBridge: "缺少使命 / 任务外键",
      serializedSelector: "序列化选择器",
      localEvent: "本地事件",
      serverBackedEvent: "服务器事件",
      localProducerChain: "精确本地生产者链",
      abilityProducer: "Ability 生产者",
      literalSignal: "字面信号 / 数值",
      noServerRequestOrReturn: "无服务器请求或返回",
      sameScriptDependency: "仅限同一条原始 LevelScript",
      noPlaybackControlPath: "未连接到剧情播放控制路径",
      producerBoundaryHint: "接收器只匹配字面信号，不选择生产者发送者、实体、生成器、使命或任务；该链只增加因果证据，不增加所有权。",
      mainTasks: "主任务 ID",
      exactLevelHost: "精确关卡宿主",
      exactSceneHost: "精确场景宿主",
      localOnlyPaths: "原生纯本地路径",
      noServerExchange: "不与服务器交换",
      carrierAudit: "已关闭的托管载体候选",
      noGraphEdges: "使命图边为零",
      nativeCrossSystemConsumers: "原生跨系统消费者普查",
      crossSystemCallers: "跨系统调用者",
      missionDynamicConsumers: "任务状态 → DynamicScene 消费者",
      missionLevelScriptConsumers: "MissionSystem → LevelScript 消费者",
      tripleSystemConsumers: "三系统消费者",
      unreviewedConsumers: "未审查消费者",
      closureReachableMethods: "可达消费者方法",
      closureDirectEdges: "直接调用闭包边",
      deferredAvailabilityRefresh: "延迟 DynamicScene 可用性刷新",
      pendingRefreshField: "待刷新字段",
      availabilityOnlyNoOrder: "仅证明可用性刷新；不证明剧情绑定、任务归属或顺序",
      fullMissionRuntimeSurface: "完整任务/任务节点运行时表面",
      missionIdentityTypes: "任务身份类型",
      crossFamilySignatures: "任务 + LevelScript 方法签名",
      trackingMissionWrites: "追踪对象 missionId 写入",
      trackingSceneWrites: "追踪对象 sceneId 写入",
      trackingContextOnly: "仅为追踪界面上下文；不证明接收器激活或顺序",
      managedCallableSurface: "托管委托/回调载体表面",
      callableFields: "可调用字段",
      missionCallableFields: "任务运行时可调用字段",
      levelScriptCallableFields: "LevelScript 可调用字段",
      callableEntryMethods: "类型化绑定入口方法",
      directBindingCalls: "原生直接绑定调用",
      crossFamilyBindings: "任务 + LevelScript 绑定",
      callableNoActivation: "类型化回调仅在各自系统内绑定；不证明接收器激活或顺序",
      visualContextConsumers: "剧情 ↔ DynamicScene 视觉上下文消费者",
      dynamicSceneCrossReferences: "DynamicScene 身份交叉引用",
      dynamicSceneCrossReferencesHint: "DynamicScene 对象携带任务状态条件，其精确数字逻辑 ID 与包含剧情播放的 LevelScript 脚本 ID 相同。当前一行还具有类型化 LevelScript 目标和共享的本地剧情路径；任务条件到触发器激活的链路仍缺失，因此所有行都不表示任务所有权、播放因果或顺序。",
      dynamicSceneLogicId: "DynamicScene 逻辑 ID",
      levelScriptId: "LevelScript 脚本 ID",
      missionStateConditions: "同对象携带的状态条件",
      candidateContextOnly: "仅候选上下文",
      exactDynamicSceneLocalContext: "精确本地控制上下文",
      typedDynamicSceneTargetAction: "类型化 DynamicScene 目标动作",
      exactLocalTriggerVolume: "精确嵌入的 LevelScript 触发区域",
      noTriggerForeignIdentity: "仅本地几何；不含 DynamicScene、使命、任务或外部实体身份",
      triggerVolumePosition: "位置",
      triggerVolumeRadius: "半径",
      sameSerializedControlPath: "相同序列化控制路径",
      missionActivationGap: "任务条件到触发器激活的链路仍未解析",
      alternateActions: "互斥动作分支",
      currentAuthoredInstances: "当前原始实例",
      runtimeContextOnly: "仅运行时订阅上下文",
      authoredPropertyRows: "原始属性行",
      implicitMissionContext: "仅隐式当前任务上下文",
      missionRuntimeUses: "任务运行时用例",
      levelScriptUses: "关卡脚本用例",
      directManagedCandidates: "直接托管候选",
      nestedManagedCandidates: "托管类型路径候选",
      nestedDependentCandidates: "依赖嵌套路径的候选",
      maxTypedDepth: "最短类型路径最大深度",
      fixedPointTraversal: "循环安全不动点",
      runtimeEntityHubCandidates: "运行时实体枢纽候选",
      sharedAggregateCandidates: "混合运行时聚合候选",
      exactSerializedInstances: "精确索引类型标签",
      indexedOriginalObjects: "已索引原始对象",
      truncatedScalarObjects: "标量投影截断对象",
      shippedLuaProducer: "已发布 XLua 生产者",
      authoredSubmitItemActions: "类型化提交物品动作",
      concreteQuestIds: "具体原始 questId",
      missionSubmissionChecks: "任务提交物品条件",
      submissionDialogCoGates: "同一 AND 目标的对话条件",
      submissionLevelScriptCoGates: "同一 AND 目标的关卡脚本条件",
      submitOpenUiOverlap: "提交物品 OpenUI 重叠",
      submissionRequirement: "提交物品需求",
      submissionDialogCoGate: "与对话完成条件同属 AND 目标",
      submissionDialogCoGateHint: "仅表示原始条件共同成立；不证明该对话会打开提交界面。",
      submissionLevelScriptCoGate: "与关卡脚本阶段完成同属 AND 目标",
      submissionLevelScriptCoGateHint: "仅表示精确的原始条件共门。关卡脚本可提供对话播放上下文，但不证明它会打开或拥有提交界面。",
      levelScriptTaskDependency: "精确的关卡脚本任务依赖",
      levelScriptTaskDependencyHint: "原始使命目标等待这个精确任务元组。它不证明使命会激活该脚本、拥有其剧情播放或选择剧情分支。",
      levelScriptSource: "原始关卡脚本条件来源",
      levelScriptExactEmptyMap: "精确的空可执行映射",
      levelScriptExecutableMap: "序列化可执行映射",
      levelScriptTailRecords: "不可执行尾部记录",
      taskMetadata: "任务元数据",
      or: "或",
      nativeDirectCallers: "原生直接调用者",
      runtimeObjectCandidates: "运行时/对象候选",
      unreviewedCandidates: "未审查候选",
      trackingContextOnly: "仅 HUD/地图追踪上下文",
      trackingTargets: "原始追踪目标",
      trackingTargetsHint: "仅表示任务标记和 HUD 导航配置。使命变量条件会在本地读取服务器同步的属性值，但服务器写入规则与时机仍未知，也不会创建播放、完成、归属或顺序边。",
      trackingFilter: "标记可见性条件",
      missionProperties: "原始使命变量",
      missionPropertiesHint: "这里只显示序列化初始值，不识别运行时写入者、触发器或剧情归属。",
      nonOwningCrossReference: "不表示所有权的原始数据交叉参考",
      unlockQuestPrerequisite: "解锁任务前置条件",
      unlockMissionPrerequisite: "解锁使命状态前置条件",
      unlockPreviousSubGame: "前一挑战前置条件",
      activityStageAssociation: "活动阶段关联",
      search: "搜索任务",
      searchPlaceholder: "任务 ID、名称、关卡或条件",
      structure: "结构",
      anyStructure: "全部结构",
      caseStudies: "证据案例",
      fanout: "包含分流",
      joins: "包含汇合",
      exactFinish: "精确对话结局",
      serverOwned: "服务器占位条件",
      failure: "失败条件",
      shown: "已显示",
      selectMission: "选择一个任务以检查其执行管线。",
      showHidden: "显示内部/隐藏节点",
      dependencies: "显示任务状态条件线",
      edgeLabels: "显示连线含义标签",
      controlHelp: "内部/隐藏节点包含 showMode=1000 的作者节点；任务状态条件线是 CheckQuestState 产生的紫色虚线，不是任务推进箭头；连线含义标签会标明前置关系或条件引用。",
      orientation: "方向",
      auto: "自动",
      leftRight: "从左到右",
      topBottom: "从上到下",
      fit: "适配画布",
      zoomOut: "缩小",
      zoomIn: "放大",
      center: "居中当前节点",
      dragHint: "拖动图中任意位置平移；直接滚动鼠标滚轮缩放。",
      serverGateway: "服",
      serverGatewayTitle: "服务器控制的状态转换：完成前置节点不等于客户端能够决定后继节点。",
      predecessor: "前置任务关系",
      conditionDependency: "任务状态条件",
      externalDependency: "外部任务",
      main: "主线",
      hidden: "隐藏",
      flow: "流",
      flowCaveat: "这是作者设置的分层标签，不代表互斥。",
      clientToServerDialog: "客→服 对话",
      clientToServerProgress: "客→服 进度",
      serverGate: "服务端条件",
      unresolvedSend: "客→服 ?",
      serverToClient: "服→客 状态",
      noObjective: "没有导出的目标",
      inspectQuest: "任务运行轨迹",
      authority: "条件归属",
      authoredFields: "原始字段",
      objectives: "目标与条件门",
      dialogTreeDefinitions: "原始 DialogTree 定义",
      dialogTreeDefinitionHint: "该任务监听这个当前游戏版本中精确 DialogTree 的完成状态。内部节点和分支属于原始数据证据；除非另有证据，启动它的客户端动作仍然未知。",
      dialogTreeLines: "行",
      dialogTreeNodes: "节点",
      dialogTreeConnections: "连接",
      dialogTreeBranchGroups: "多选项组",
      dialogTreeNoOrder: "仅定义与内部图 · 不提升为跨文件顺序",
      dialogTreeObserver: "任务监听条件",
      dialogTreeObjectiveObserver: "目标",
      dialogTreeFailureObserver: "失败条件",
      clientActions: "状态同步后的客户端动作",
      source: "来源",
      protocol: "所选任务节点的网络管线",
      asyncCaveat: "这些是异步状态消息，不应理解为已证明的同步请求/响应对。",
      playerWorld: "玩家 / 世界",
      client: "Unity 客户端",
      server: "游戏服务器",
      activation: "激活",
      observe: "观察 / 操作",
      outbound: "发往服务器",
      resolve: "权威判定",
      returnState: "返回状态",
      successor: "后继激活",
      activationMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 2 }",
      activationHandler: "StartQuest 绑定目标和回调",
      worldEvent: "玩家或世界事件满足、改变任务条件。",
      synchronizedHistory: "读取服务器同步的对话完成历史。",
      synchronizedState: "读取服务器同步的任务/使命状态。",
      clientObserved: "客户端条件器观察此条件；最终完成状态仍由服务器决定。",
      mixedAuthority: "组合了多个不同归属来源的条件。",
      unknownAuthority: "尚未证明条件的执行归属。",
      dialogSend: "CS_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      dialogSendDetail: "原生客户端已证明的精确出站字段。",
      serverOwnedDetail: "已安装版本中 GameConditionServerPlaceHolder 的回退路径返回 int.MaxValue，而不是 ClientOnly，因此 StartQuest 不会绑定客户端进度回调。",
      serverPlaceholderKey: "服务端目标键",
      serverPlaceholderNoSend: "没有该条件专属的客户端请求；原生回退路径不会由此占位条件发送 CS_UPDATE_QUEST_OBJECTIVE。",
      serverPlaceholderReturn: "SC_QUEST_OBJECTIVES_UPDATE { questId, questObjectives[{ conditionId, extraDetails, values, isComplete, descriptionIndex }] }",
      serverPlaceholderReturnDetail: "服务器按 (questId, conditionId) 组合身份应用进度；conditionId 本身不是全局唯一。",
      unresolvedDetail: "尚未定位该条件对应的精确进度/请求消息；不能从本地回调推断网络协议。",
      opaquePolicy: "验证进度并选择后继节点；检查过的客户端方法中没有这项策略。",
      succeedMessage: "SC_QUEST_STATE_UPDATE { questId, questState = 3 }",
      succeedHandler: "SucceedQuest 在客户端标记完成",
      failMessage: "适用时：SC_QUEST_FAILED → FailQuest",
      successorDetail: "服务器之后为每个选中的后继节点发送 state = 2。",
      exact: "精确",
      anyFinish: "任意结局",
      finish: "结局",
      dialog: "对话",
      state: "状态",
      condition: "条件",
      evidence: "证据叠加",
      confidence: "置信度",
      noCase: "此任务没有整理好的原始游戏数据案例注释，但原始结构仍可查看。",
      missionHandshake: "任务级握手",
      acceptRequest: "客→服  CS_ACCEPT_MISSION { missionId }",
      acceptReturn: "服→客  SC_MISSION_STATE_UPDATE { missionState, succeedId, properties… }",
      acceptCaveat: "协议中没有配对的 SC_ACCEPT_MISSION；客户端异步等待任务状态推送。",
      loading: "正在加载任务管线…",
      loadingMission: "正在加载任务…",
      loadError: "无法加载任务管线数据。",
      retry: "重试",
      noMatches: "没有匹配筛选条件的任务。",
      noVisibleQuests: "当前图筛选条件下没有可见节点。",
      join: "汇合",
      activeJoin: "主动 AND",
      roots: "入口",
      branches: "分流",
      exactFinishes: "精确结局",
      serverPlaceholders: "服务端条件",
      graph: "任务节点图",
      nativeBoundary: "原生实现边界",
      stateApplicationContract: "下一任务由谁选择？",
      serverSelectedIdentity: "服务端选择的标识与状态控制",
      stateApplicationValidated: "已验证类型路径",
      noClientSuccessorSelector: "客户端无后继选择器",
      lifecycleIdentityFlow: "同一数据包标识",
      extraThreadScheduler: "并行分支运行时权威",
      extraThreadSchedulerValidated: "已验证原生写入形状",
      extraThreadSiblingBoundary: "同级槽位不是时间顺序",
      extraThreadDirectCalls: "直接调度器调用",
      exchanges: "项消息",
      asynchronousExchange: "异步",
      boundaryOnly: "仅原生边界",
      notQuestAttached: "不附加到任意任务节点",
      protocolFields: "字段",
      exchangeRequest: "请求",
      exchangeRequestAfterLocalEvent: "本地事件后的请求",
      exchangeResponse: "响应",
      exchangeServerUpdateOrConfirmation: "服务端更新 / 条件确认",
      exchangeServerPush: "服务端推送",
      exchangeCompletionAcknowledgement: "完成确认",
      openEvidence: "显示原生证据",
      nativeConfidence: "已安装版本 · 原生与 IFix 审计",
      actionChainStep: "动作链步骤",
      dialogExchange: "对话历史同步",
      dialogEcho: "SC_FINISH_DIALOG { dialogId, optionIds[], finishNums[] }",
      progressSend: "CS_UPDATE_QUEST_OBJECTIVE { questId, conditionId, value, isAdd=false }",
      progressReturn: "SC_QUEST_OBJECTIVES_UPDATE { questId, conditionId, extraDetails, values, isComplete, descriptionIndex }",
      progressCaveat: "绑定的客户端子条件回调变化时发送；之后的 state=3 推送仍是权威完成状态。",
      progressNative: "OnSubConditionProgressChanged（0x183a6fc20）构造并发送这个绝对值操作。",
      missionDescription: "任务详细描述",
      descriptionInherited: "任务级描述",
      descriptionOverride: "节点专用描述",
      noDescription: "没有导出本地化的任务详细描述。",
      storyFiles: "任务 ↔ 剧情连接",
      missionStoryFiles: "使命生命周期 ↔ 剧情连接",
      missionStoryHint: "这些文件连接到使命接受流程或使命级作者上下文，不会被强行归入任意任务节点。",
      missionStateDependencies: "原生使命状态 → 剧情依赖",
      missionStateDependenciesHint: "这里单独展示精确的本地使命状态门控，不把它们视为任务归属。读取同步状态本身不会发送数据；若交互流程另有请求，会在对应证据行中单独说明。",
      missionStateDependencyBoundary: "依赖证据与覆盖绑定分开计数",
      unassignedStory: "未分配剧情",
      unassignedStoryHint: "这些源文件属于该使命，但仍缺少可连接到使命生命周期或任务节点的证据；界面保留显示，不会猜测归位。",
      storyCount: "剧情",
      storyToQuest: "剧情 → 任务",
      questToStory: "任务 → 剧情",
      storyContext: "作用域上下文",
      storyIncomingBadge: "剧→任",
      storyOutgoingBadge: "任→剧",
      storyContextBadge: "上下文",
      relationObjectiveCondition: "任务目标等待剧情状态",
      relationFailureCondition: "剧情状态参与失败条件",
      relationClientStart: "任务开始时触发剧情动作",
      relationClientSucceed: "任务成功后触发剧情动作",
      relationClientFailed: "任务失败后触发剧情动作",
      relationLevelData: "LevelData 明确把剧情放到此任务节点",
      relationLevelScript: "任务条件限定了这条 LevelScript 剧情调用",
      relationLevelScriptPropertyConsumer: "任务与剧情播放共享同一个精确的 LevelScript 属性变化触发器",
      relationLevelScriptMission: "LevelScript 动作与独立脚本证据共同将剧情限定到该使命",
      relationLevelDataScriptHost: "使命命名的 LevelData 包含经过结构验证的剧情脚本简表（资源上下文）",
      relationWorldEntityQuestPlayback: "任务条件与该剧情播放脚本引用同一组唯一解析的世界实体（精确外键上下文，不证明任务或服务器触发）",
      relationMissionAreaLevelDataHost: "类型化使命区域父根将此已验证 LevelData 脚本外壳限定到使命",
      relationEntityTrackedInteractive: "任务导航精确指向脚本实体，其 type_id 配置此剧情文件（仅上下文，不代表播放）",
      relationEntityTrackedScript: "任务导航指向包含该类型化剧情控制路径的同一脚本（仅上下文，未证明槽位桥接）",
      relationEntityTrackedProperty: "任务导航与精确的 SavePropertyChanged 监听器指向同一个唯一解析的世界实体（属性上下文；服务端占位目标的完成逻辑仍不透明）",
      relationEntityTrackedWorldDialog: "任务导航指向精确的世界实体，其带计数边界的 componentProperties[94] 同时配置使命与 Dialog 剧情 ID（仅导航/配置上下文，不代表归属、播放、完成或服务端交换）",
      relationSpawnerConfigMission: "精确的服务端生成器完成事件到达此剧情文件，且同关卡唯一 SpawnerConfig 只指向一个 MissionRuntime（使命上下文，不指定任务节点）",
      relationHpSpawnerConfigMission: "精确的生成器出生 → 实体列表写入 → 本地生命值阈值播放链与同关卡唯一 SpawnerConfig 共同指向一个 MissionRuntime（使命上下文，不指定任务节点）",
      relationVariantRuntime: "变体 MissionRuntime 将剧情连接到此节点",
      relationNpcProxy: "唯一 NPC 代理解析到此剧情文件",
      relationNpcProxyEx: "精确使命与 NPC 代理共同解析到此任务节点",
      relationNpcProxyMission: "NpcProxyEx 将此剧情文件明确限定到该使命",
      relationUniqueMissionTrackedNpcProxyDialog: "该 NPC 代理的所有类型化跟踪均指向同一使命；服务器选择一个已注册的交互对话行（共享使命上下文，不代表任务选择或剧情顺序）",
      relationNpcProxyTrackingDialog: "任务导航跟踪该精确 NPC 代理；其当前注册的交互对话包含类型化后续对话路线（仅导航/配置上下文）",
      relationNpcProxyLazyDestroyDialog: "任务导航跟踪该精确 NPC 代理；原生停用流程会把其配置的延迟销毁对话应用为交互覆盖（仅配置上下文，不证明任务激活或播放因果）",
      relationMissionTrackedNpcPatrol: "类型化 LevelData 解析检查点监听器的 NPC 别名与巡逻路线；同场景任务导航在唯一任务中跟踪该精确世界实体（仅任务上下文；候选任务节点不代表激活、播放、完成或所有权）",
      relationNpcProxySegmentShell: "被跟踪 NPC 代理位于精确的原始注册表片段中，片段全局 ID 与该剧情播放脚本一致（仅使命外壳，不代表 NPC 触发）",
      relationMissionStateDependency: "该使命已同步到客户端的精确状态参与选择剧情动作的原生 IfElse 路径（依赖，不代表归属）",
      relationTaskMissionStateDependency: "同一条原始 LevelScript 同时包含精确的 taskMap 使命状态条件和剧情播放，但序列化控制路径并未连接两者（仅依赖证据）",
      relationMissionStateProcessing: "精确原生 true 分支在该使命等于 Processing 时播放此剧情动作（使命上下文，不代表任务因果）",
      relationRadioTriggerMissionState: "同一条强类型 LevelData 广播触发区记录同时携带该广播与使命状态边界；原生 OnEnter 在播放前检查该状态（上下文，不代表任务归属）",
      relationNpcPatrolRadioPlayback: "一条强类型 NPC 巡逻动作包含该广播，并映射到当前安装版本的原生巡逻广播消费者（仅为播放上下文；巡逻数据不序列化使命、任务或相对剧情顺序）",
      relationAirWallMissionState: "同一条精确 LevelData 空气墙记录同时携带类型化的使命/任务状态条件与击退广播；同步状态只控制空气墙，玩家之后接触时才可能播放广播（上下文，不代表状态切换因果、归属或顺序）",
      relationNarrativeInteractiveMissionState: "同一条带计数边界的 LevelInteractiveData 实体同时携带弹窗消费端 ID 与使命状态特效键；原始叙事模板及原生组件证明本地播放依赖（不代表归属）",
      relationFocusModeRadio: "FocusMode 将交互锁定广播明确限定到该使命",
      relationSnsMissionLink: "SNS 原始表记录将该会话明确连接到此使命",
      relationTimelineBlack: "序列化 Timeline 将该黑屏剧情包含在对话根节点中",
      relationTimelineBlackUnresolved: "已证明序列化 Timeline 根节点，但尚未解析对话或使命锚点",
      relationDialogNarrativeAction: "类型化 DialogTree 动作在父对话中呈现该黑屏文本",
      relationDialogNarrativeActionUnscoped: "DialogTree 包含关系精确，但父对话的使命或任务位置尚未解析",
      relationDialogLeftSubtitleAction: "类型化 DialogTree 动作在本地左侧字幕界面中呈现该文本",
      relationDialogLeftSubtitleActionUnscoped: "左侧字幕包含关系精确，但父对话的使命或任务位置尚未解析",
      relationDialogStoryPlayback: "二进制已证明的 DialogTree 载体可从父对话播放此剧情文件",
      relationDialogStoryPlaybackUnscoped: "DialogTree 播放载体已由二进制证明，但父对话的使命或任务位置尚未解析",
      relationDialogPrimeStoryPlayback: "二进制证明该 DialogTree 从首节点可到达此剧情播放载体；任务只监听父对话完成状态（依赖关系，不代表任务触发播放或剧情归属）",
      relationDefinitionOnly: "原始文本定义存在；当前构建未恢复到播放消费端",
      relationMissionAccept: "NPC 对话接受该使命",
      relationMissionArea: "目标区域标识中嵌入了剧情 ID",
      relationStoryGraphBranch: "作者对话路线与此任务锚点相连",
      relationLevelScriptSequence: "LevelScript next-id 链与此任务锚点相连",
      relationQuestProcessingAction: "任务进入 Processing 状态时启动该客户端剧情动作",
      relationQuestCompletedAction: "任务完成事件的 LevelScript 动作启动剧情",
      relationQuestStateGate: "触发的 LevelScript 播放以此任务处于进行中为门控条件",
      relationNativeBlackAction: "原生客户端黑屏动作播放这些精确序列化文本行",
      relationNativePlaybackUnscoped: "已证明原生播放动作；使命或任务触发源仍未解析",
      relationUnassignedStory: "尚无证据支持的管线连接",
      relationRuntimeReference: "直接运行时引用；触发时机未解析",
      openInStory: "在剧情页打开",
      storyEvidence: "箭头方向来自运行时语义：条件是“剧情 → 任务”，原生 QuestAction 槽位与严格门控的任务完成事件是“任务 → 剧情”。LevelData、限定作用域的 LevelScript、变体运行时、作者单跳路线、精确 NPC 代理连接和唯一的类型化世界实体集合连接属于上下文；共享世界实体集合不证明任务或服务器触发。类型化 DialogTree 叙事遮罩只是本地呈现，不会产生服务器交换；使命接受对话保留在使命外壳。空间邻近与文件顺序猜测绝不会升级为连接。",
      noStoryFiles: "这个任务节点没有可由证据支持的剧情连接。",
      relationLevelScriptInteractiveNarrative: "\u5e26\u7cbe\u786e\u8ba1\u6570\u8fb9\u754c\u7684 LevelScript \u4ea4\u4e92\u914d\u7f6e\u5c06\u6b64\u5267\u60c5\u6587\u4ef6\u7ed1\u5b9a\u5230\u672c\u5730\u53d9\u4e8b\u5bf9\u8c61\uff1b\u6fc0\u6d3b\u65f6\u673a\u4e0e\u987a\u5e8f\u4ecd\u672a\u89e3\u6790",
      relationObjectiveTrackingStory: "\u4efb\u52a1\u76ee\u6807\u8ffd\u8e2a\u5f15\u7528\u6b64\u5267\u60c5\u6587\u4ef6\uff08\u4ec5\u8fde\u63a5\uff0c\u4e0d\u4ee3\u8868\u64ad\u653e\u6216\u987a\u5e8f\uff09",
      relationLevelDataInteractiveNarrative: "\u5177\u6709\u7cbe\u786e\u8fb9\u754c\u7684 LevelData \u4ea4\u4e92\u914d\u7f6e\u901a\u8fc7\u7ec4\u4ef6 94 \u6216\u5df2\u9a8c\u8bc1\u7684 int_horn dialog_id \u5c5e\u6027\uff0c\u5c06\u6b64\u5267\u60c5\u6587\u4ef6\u7ed1\u5b9a\u5230\u672c\u5730\u53d9\u4e8b\u5bf9\u8c61\uff1b\u6700\u540e\u8bb0\u5f55\u5fc5\u987b\u7531\u975e\u7a7a BriefData \u8fb9\u754c\u6216\u5230 EOF \u7684\u5b8c\u6574\u7a7a\u811a\u672c\u540e\u7f00\u9a8c\u8bc1\uff0c\u5df2\u89e3\u6790\u7684\u8fdb\u5ea6\u9501\u4ec5\u662f\u53ef\u7528\u6027\u8bc1\u636e\uff0c\u4e0d\u662f\u5267\u60c5\u5f52\u5c5e\u6216\u987a\u5e8f",
      triggerRoute: "\u6062\u590d\u7684\u89e6\u53d1\u8def\u5f84",
      triggerPlayback: "\u64ad\u653e\u89e6\u53d1",
      triggerCondition: "\u5b8c\u6210\u6761\u4ef6",
      triggerContext: "\u4ec5\u4e0a\u4e0b\u6587",
      triggerContextOwnerUnresolved: "\u7cbe\u786e\u8f7d\u4f53\u4e0a\u4e0b\u6587 \u00b7 \u5f52\u5c5e\u672a\u89e3\u6790",
      triggerDependency: "\u4ec5\u4f9d\u8d56",
      triggerUnresolved: "\u89e6\u53d1\u5df2\u77e5 \u00b7 \u5f52\u5c5e\u672a\u89e3\u6790",
      triggerPlaybackAlias: "\u6839\u64ad\u653e\u522b\u540d \u00b7 \u5f52\u5c5e\u672a\u89e3\u6790",
      triggerPlaybackAliasConnected: "\u6839\u64ad\u653e\u522b\u540d \u00b7 \u5f52\u5c5e\u5df2\u8fde\u63a5",
      triggerDefinition: "\u4ec5\u5b9a\u4e49 \u00b7 \u65e0\u6d88\u8d39\u8005",
      offlineRecoveryBoundary: "\u79bb\u7ebf\u6062\u590d\u8fb9\u754c",
      projectAuthoredBoundary: "WebUI \u9879\u76ee\u81ea\u5efa\u5185\u5bb9",
      projectAuthoredEvidence: "\u5df2\u4ece\u539f\u59cb\u6e38\u620f\u6062\u590d\u4e2d\u6392\u9664",
      partialRecoveryBoundary: "\u90e8\u5206\u5df2\u6ce8\u518c\u8f7d\u4f53",
      runtimeContextRecoveryBoundary: "\u7cbe\u786e\u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587\u8fb9\u754c",
      offlineRecoveryNoGraphEdge: "\u4e0d\u751f\u6210\u5f52\u5c5e\u6216\u987a\u5e8f\u8fb9",
      offlineRecoveryConsumer: "\u6d88\u8d39\u8005\u8fb9\u754c",
      runtimeRecoveryActivation: "\u6fc0\u6d3b\u8fb9\u754c",
      runtimeRecoveryPlayback: "\u64ad\u653e\u8fb9\u754c",
      offlineRecoveryOrder: "\u987a\u5e8f\u8fb9\u754c",
      offlineRecoveryReopen: "\u91cd\u65b0\u8c03\u67e5\u6761\u4ef6",
      offlineRecoverySources: "\u539f\u59cb\u6570\u636e\u6587\u4ef6",
      projectAuthoredSources: "\u9879\u76ee\u6e90\u6587\u4ef6",
      runtimeRecoveryNominalMission: "\u5267\u60c5\u6587\u4ef6\u540d\u4e49\u4efb\u52a1",
      runtimeRecoveryContextMission: "\u5df2\u9a8c\u8bc1\u8fd0\u884c\u65f6\u5916\u58f3",
      runtimeRecoveryContextMissions: "\u5df2\u9a8c\u8bc1\u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587",
      runtimeRecoveryContextBoundary: "\u4e0a\u4e0b\u6587\u8fb9\u754c",
      runtimeRecoveryParentDialogDependency: "\u7cbe\u786e\u7236 DialogTree \u8f7d\u4f53\u4f9d\u8d56\uff0c\u6fc0\u6d3b\u4e0e\u76f8\u5bf9\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryNpcDialogContext: "\u7cbe\u786e NPC \u5bf9\u8bdd\u4e0a\u4e0b\u6587\uff0c\u4e0d\u8bc1\u660e\u64ad\u653e\u5f52\u5c5e\u6216\u987a\u5e8f\u8fb9",
      runtimeRecoveryNpcSelectionContext: "\u7cbe\u786e NPC \u8fd0\u884c\u65f6\u9009\u62e9\u4e0a\u4e0b\u6587\uff0c\u4e0d\u8bc1\u660e\u76f8\u5bf9\u987a\u5e8f",
      runtimeRecoveryNpcCrossMissionContext: "\u7cbe\u786e\u8de8\u4efb\u52a1 NPC \u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587\uff0c\u4e0d\u8bc1\u660e\u5f52\u5c5e\u6216\u987a\u5e8f\u8fb9",
      runtimeRecoveryNpcMultiMissionContext: "\u7cbe\u786e\u591a\u4efb\u52a1 NPC \u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587\uff0c\u8868\u793a\u5019\u9009\u800c\u975e\u65f6\u5e8f",
      runtimeRecoveryQuestAnchors: "\u5916\u58f3\u4efb\u52a1\u8282\u70b9",
      runtimeRecoveryGate: "\u5df2\u89e3\u7801\u95e8\u63a7",
      runtimeRecoveryNativePaths: "\u7cbe\u786e\u539f\u751f\u8def\u5f84",
      runtimeRecoveryPlaybackRoots: "\u7cbe\u786e\u64ad\u653e\u6839\u8282\u70b9",
      runtimeRecoveryCarrierParents: "\u7cbe\u786e\u8f7d\u4f53\u7236\u8282\u70b9",
      runtimeRecoverySnsLink: "\u539f\u59cb SNS \u4efb\u52a1\u94fe\u63a5",
      offlineRecoveryRelatedOriginalData: "\u76f8\u5173\u539f\u59cb\u6570\u636e\u675f",
      offlineRecoveryPrtsOrder: "\u7ec8\u7aef\u987a\u5e8f",
      offlineRecoveryPrtsCarrier: "\u7cbe\u786e PRTS \u6863\u6848\u8f7d\u4f53\uff08\u76ee\u5f55\u987a\u5e8f\uff0c\u975e\u4efb\u52a1\u65f6\u5e8f\uff09",
      offlineRecoveryDialogSummary: "\u7cbe\u786e\u5bf9\u8bdd\u6458\u8981\u8d44\u6599\uff08\u975e\u64ad\u653e\u8bc1\u636e\uff09",
      offlineRecoveryStoryRelation: "\u5267\u60c5\u5173\u7cfb",
      offlineRecoveryMissionTextRows: "\u4f7f\u547d/\u76ee\u6807\u6587\u672c\u884c",
      offlineRecoveryGaps: "\u539f\u59cb\u6570\u636e\u9650\u5b9a\u7684\u6fc0\u6d3b\u7f3a\u53e3",
      offlineRecoveryGapsHint: "\u8fd9\u4e9b\u8bb0\u5f55\u90fd\u6709\u660e\u786e\u7684\u6765\u6e90\u8fb9\u754c\uff0c\u4e14\u4e0d\u65b0\u589e\u4efb\u52a1\u987a\u5e8f\u8fb9\u3002\u539f\u59cb\u6e38\u620f\u8bb0\u5f55\u4ec5\u4fdd\u7559\u5df2\u9a8c\u8bc1\u7684\u5b9a\u4e49\u6216\u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587\uff0c\u9879\u76ee\u81ea\u5efa\u8bb0\u5f55\u5219\u660e\u786e\u4e0d\u5c5e\u4e8e\u6e38\u620f\u6570\u636e\u3002\u6b64\u5904\u4e0d\u4f7f\u7528 OCR \u6216\u624b\u52a8\u987a\u5e8f\u4f5c\u4e3a\u8bc1\u636e\u3002",
      offlineRecoveryInternalTimeline: "\u5185\u90e8 Timeline",
      offlineRecoveryLines: "\u884c",
      offlineRecoveryDefinedOptions: "\u5df2\u5b9a\u4e49\u9009\u9879\uff08\u8def\u7531\u672a\u89e3\u6790\uff09",
      offlineRecoveryDefinedOptionsResolved: "\u5df2\u5b9a\u4e49\u9009\u9879",
      offlineRecoveryTableOnlyRegistration: "\u4ec5 DialogId \u8868\u6ce8\u518c",
      offlineRecoveryPrintableTokens: "\u4ec5\u53ef\u6253\u5370\u7684 DialogId \u6807\u8bb0\uff08\u975e\u5206\u652f\u76ee\u6807\uff09",
      offlineRecoveryDialogTreeAbsent: "\u7f3a\u5c11 DialogTree \u8d44\u4ea7",
      offlineRecoveryDialogTreeExact: "\u7cbe\u786e DialogTree \u8d44\u4ea7",
      offlineRecoveryDialogTreeBranches: "DialogTree \u5185\u90e8\u5206\u652f",
      offlineRecoveryParentDialogTrees: "\u5df2\u6ce8\u518c\u7684\u7236 DialogTree",
      offlineRecoveryParentTreeBranches: "\u5185\u90e8\u5206\u652f\u7ec4",
      offlineRecoveryInternalLineConnections: "\u7cbe\u786e\u5185\u90e8\u53f0\u8bcd\u8fde\u63a5",
      offlineRecoveryParentLevelContexts: "\u7cbe\u786e\u7684\u7236\u5bf9\u8bdd\u5173\u8054\u5173\u5361/\u5730\u7262\u8d44\u4ea7\u5916\u58f3",
      offlineRecoveryParentLevelBoundary: "\u4ec5\u8868\u793a\u76f8\u5173\u539f\u59cb\u6587\u4ef6\uff1b\u4e0d\u8bc1\u660e\u6fc0\u6d3b\u3001\u5f52\u5c5e\u3001\u5206\u652f\u6216\u987a\u5e8f\u3002",
      offlineRecoveryDungeonCatalogMetadata: "\u5730\u7262\u76ee\u5f55\u5143\u6570\u636e\uff08\u975e\u65f6\u5e8f\uff09",
      offlineRecoveryRelatedLevelFiles: "\u76f8\u5173\u5173\u5361\u6587\u4ef6",
      offlineRecoverySubGameRuntime: "\u7cbe\u786e\u9ed1\u76d2 SubGame \u8fd0\u884c\u5916\u58f3",
      offlineRecoverySubGameBindScript: "\u7ed1\u5b9a LevelScript",
      offlineRecoverySubGameTaskLanes: "\u539f\u59cb\u4efb\u52a1\u901a\u9053\uff08\u4e0d\u662f\u5267\u60c5\u987a\u5e8f\uff09",
      offlineRecoverySubGameMainTasks: "\u4e3b\u4efb\u52a1",
      offlineRecoverySubGameExtraTasks: "\u989d\u5916\u4efb\u52a1",
      offlineRecoverySubGameFailTasks: "\u5931\u8d25\u4efb\u52a1",
      offlineRecoverySubGameParentPlayback: "\u7cbe\u786e\u7236\u5bf9\u8bdd\u64ad\u653e",
      offlineRecoverySubGameDefinitionOnlyParents: "\u5728\u7ed1\u5b9a\u811a\u672c\u4e2d\u4ec5\u5b9a\u4e49",
      offlineRecoverySubGamePlaybackCoverage: "\u7236\u5bf9\u8bdd\u64ad\u653e\u8986\u76d6",
      offlineRecoverySubGameTaskTopology: "\u7cbe\u786e\u4efb\u52a1\u5b8c\u6210\u62d3\u6251",
      offlineRecoverySubGameTaskTopologyNull: "\u6ca1\u6709\u539f\u751f\u4efb\u52a1\u6620\u5c04",
      offlineRecoverySubGameTasks: "\u4efb\u52a1",
      offlineRecoverySubGameConditions: "\u6761\u4ef6",
      offlineRecoverySubGameTracked: "\u53ef\u8ffd\u8e2a",
      offlineRecoverySubGameInternal: "\u5185\u90e8",
      offlineRecoverySubGameConditionTypes: "\u6761\u4ef6\u7c7b\u578b",
      offlineRecoverySubGameCombineExpressions: "\u5e8f\u5217\u5316\u516c\u5f0f",
      offlineRecoverySubGameTaskDescriptions: "\u663e\u793a\u76ee\u6807",
      offlineRecoverySubGameTopologyBoundary: "\u4efb\u52a1\u6761\u4ef6\u4e0e\u4e3b/\u989d\u5916/\u5931\u8d25\u901a\u9053\u5747\u662f\u7cbe\u786e\u539f\u59cb\u6570\u636e\u7ed3\u6784\uff0c\u4f46\u5b83\u4eec\u6ca1\u6709\u5e8f\u5217\u5316\u4efb\u52a1\u540e\u7ee7\u8fb9\u6216\u5267\u60c5\u6587\u4ef6\u987a\u5e8f\u8fb9\u3002",
      offlineRecoverySubGameActionTopology: "\u7cbe\u786e\u8fd0\u884c\u65f6\u63a7\u5236\u56fe",
      offlineRecoverySubGameActionTopologyEmpty: "\u539f\u751f\u52a8\u4f5c\u6620\u5c04\u4e3a\u7a7a",
      offlineRecoverySubGameActionEvents: "\u4e8b\u4ef6\u6839",
      offlineRecoverySubGameActionPhysicalEvents: "\u7269\u7406\u4e8b\u4ef6\u884c",
      offlineRecoverySubGameActionEventSlot: "\u6d3b\u52a8\u7d22\u5f15\u76d1\u542c\u5668",
      offlineRecoverySubGameActionEventPriority: "\u76d1\u542c\u5668\u4f18\u5148\u7ea7",
      offlineRecoverySubGameActionEventTriggerActive: "\u6d3b\u52a8\u671f\u95f4\u6a21\u5f0f",
      offlineRecoverySubGameActionEventFilter: "\u8fc7\u6ee4\u5668",
      offlineRecoverySubGameActionNodes: "\u52a8\u4f5c",
      offlineRecoverySubGameActionEdges: "\u8fb9",
      offlineRecoverySubGameActionFanouts: "\u7c7b\u578b\u5316\u5206\u53d1",
      offlineRecoverySubGameActionSequences: "\u6709\u5e8f\u5e8f\u5217",
      offlineRecoverySubGameActionChoices: "\u6761\u4ef6\u9009\u62e9",
      offlineRecoverySubGameActionLoops: "\u5faa\u73af",
      offlineRecoverySubGameActionConvergence: "\u6c47\u5408",
      offlineRecoverySubGameActionCycles: "\u73af",
      offlineRecoverySubGameActionShadowed: "\u8fd0\u884c\u65f6\u8986\u76d6\u8bb0\u5f55",
      offlineRecoverySubGameActionTerminals: "\u7f3a\u5931\u69fd\u7ec8\u70b9",
      offlineRecoverySubGameActionActiveSlot: "\u6d3b\u52a8\u8fd0\u884c\u65f6\u69fd",
      offlineRecoverySubGameActionEventTypes: "\u4e8b\u4ef6\u7c7b\u578b",
      offlineRecoverySubGameActionTypes: "\u52a8\u4f5c\u7c7b\u578b",
      offlineRecoverySubGameActionStoryTargets: "\u7c7b\u578b\u5316\u5267\u60c5\u76ee\u6807",
      offlineRecoverySubGameActionTopologyBoundary: "\u8fb9\u4ec5\u5728\u540c\u4e00 LevelScript \u5185\u662f\u7cbe\u786e\u7684\u3002\u4e8b\u4ef6\u5934\u3001\u52a8\u4f5c\u548c getter ID \u90fd\u4f7f\u7528\u6700\u540e\u4e00\u6761\u5e8f\u5217\u5316\u7d22\u5f15\u69fd\uff0c\u7f3a\u5931\u7684\u6b63\u6570\u52a8\u4f5c\u69fd\u4f1a\u6b63\u5e38\u7ed3\u675f\u3002\u4e8b\u4ef6\u6839\u662f\u72ec\u7acb\u8c03\u7528\u7684\u76d1\u542c\u5668\uff1a\u7269\u7406\u5217\u8868\u987a\u5e8f\u548c\u76d1\u542c\u5668\u4f18\u5148\u7ea7\u90fd\u4e0d\u662f\u5267\u60c5\u65f6\u5e8f\u3002\u53ea\u6709\u7c7b\u5316\u52a8\u4f5c\u660e\u786e\u6307\u5411\u5267\u60c5\u6587\u4ef6\u65f6\uff0c\u63a7\u5236\u6d41\u624d\u5bf9\u5176\u6392\u5e8f\u3002",
      offlineRecoveryEvidenceParentTreePartition: "\u7cbe\u786e\u7684\u5df2\u6ce8\u518c\u7236\u6811\u53f0\u8bcd\u5206\u533a",
      partialRecoveryEvidenceParentTreePartition: "\u90e8\u5206\u5df2\u6ce8\u518c\u7236\u6811\u53f0\u8bcd\u5206\u533a",
      partialRecoveryCoverage: "\u5df2\u6ce8\u518c\u8986\u76d6",
      partialRecoveryUnmatchedRows: "\u672a\u5339\u914d\u7684\u539f\u59cb\u53f0\u8bcd\u884c",
      partialRecoveryRowIdPositions: "\u8868\u884c ID \u4f4d\u7f6e\uff08\u4ec5\u4ea4\u53c9\u53c2\u8003\uff0c\u975e\u987a\u5e8f\u8bc1\u636e\uff09",
      offlineRecoveryAuthoredSplit: "\u539f\u751f\u5206\u6d41",
      offlineRecoveryAuthoredConvergence: "\u539f\u751f\u5408\u6d41",
      offlineRecoveryTerminalOptions: "\u7ec8\u6b62\u9009\u9879\u8def\u7531",
      offlineRecoveryFinishId: "\u5df2\u5e8f\u5217\u5316 finishId",
      offlineRecoveryFinishIdAbsent: "\u672a\u5e8f\u5217\u5316 finishId",
      offlineRecoveryEvidenceResultBranch: "\u7cbe\u786e\u7ed3\u679c\u5206\u652f",
      offlineRecoveryEvidenceTrackedNpc: "\u4efb\u52a1\u8ffd\u8e2a NPC \u5bf9\u8bdd\uff0c\u64ad\u653e\u5f52\u5c5e\u672a\u77e5",
      offlineRecoveryEvidenceEmptyHost: "\u4ec5\u5b9a\u4e49 \u2014 \u4efb\u52a1\u811a\u672c\u4e3a\u7a7a",
      offlineRecoveryEmptyHost: "\u7cbe\u786e\u7a7a\u4efb\u52a1\u5bbf\u4e3b",
      offlineRecoveryEmptyHostBoundary: "\u8fd9\u4e2a\u4efb\u52a1\u547d\u540d\u7684 LevelData \u53ea\u5305\u542b\u4e00\u4e2a\u65e0\u5c5e\u6027\u7684 LevelScript\u3002\u5176\u52a8\u4f5c\u5217\u8868\u3001UID \u8bb0\u5f55\u548c\u4efb\u52a1\u6620\u5c04\u5747\u4e3a\u7a7a\uff0c\u56e0\u6b64\u4e0d\u80fd\u6fc0\u6d3b\u6216\u6392\u5217\u8fd9\u4e9b Story \u5b9a\u4e49\u3002",
      offlineRecoveryEvidenceDefinitionOnly: "\u4ec5\u5b9a\u4e49\uff0c\u6fc0\u6d3b\u5668\u672a\u77e5",
      offlineRecoveryEvidenceUnregistered: "\u672a\u6ce8\u518c\u5b9a\u4e49 \u2014 \u65e0\u8fd0\u884c\u65f6\u6d88\u8d39\u8005",
      offlineRecoveryEvidenceRadioOnly: "\u4ec5\u65e0\u7ebf\u7535\u5b9a\u4e49\uff0c\u6d88\u8d39\u8005\u672a\u77e5",
      offlineRecoveryEvidenceBinaryRadio: "\u4ec5\u5b9a\u4e49 \u2014 \u5f53\u524d\u539f\u59cb\u6570\u636e\u8868\u9762\u672a\u627e\u5230\u6d88\u8d39\u8005",
      offlineRecoveryEvidenceNpcProxyConsumer: "\u539f\u59cb\u4e8c\u8fdb\u5236 NPC \u4ee3\u7406\u6d88\u8d39\u8005\uff0c\u4efb\u52a1\u6fc0\u6d3b\u65f6\u673a\u672a\u77e5",
      offlineRecoveryEvidenceBinarySns: "\u4ec5 SNS \u5b9a\u4e49 \u2014 \u5f53\u524d\u539f\u59cb\u6570\u636e\u8868\u9762\u672a\u627e\u5230\u6d88\u8d39\u8005",
      offlineRecoveryEvidenceBinaryReadingPopup: "\u4ec5\u53ef\u8bfb\u5185\u5bb9\u5b9a\u4e49 \u2014 \u5f53\u524d\u539f\u59cb\u6570\u636e\u8868\u9762\u672a\u627e\u5230\u6fc0\u6d3b\u5668",
      offlineRecoveryEvidenceBinaryUnregisteredDialog: "\u672a\u6ce8\u518c\u5bf9\u8bdd\u5b9a\u4e49 \u2014 \u5f53\u524d\u539f\u59cb\u6570\u636e\u8868\u9762\u672a\u627e\u5230\u6d88\u8d39\u8005",
      offlineRecoveryEvidenceBinaryRegisteredDialogTree: "\u5df2\u6ce8\u518c DialogTree \u5b9a\u4e49 \u2014 \u5f53\u524d\u539f\u59cb\u6570\u636e\u8868\u9762\u672a\u627e\u5230\u6fc0\u6d3b\u5668",
      offlineRecoveryEvidenceMissionlessNativePlayback: "\u5df2\u7cbe\u786e\u6062\u590d\u672c\u5730\u64ad\u653e\uff0c\u4efb\u52a1\u6865\u63a5\u4e0e\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryEvidenceSameMissionLevelDataPlayback: "\u5df2\u7cbe\u786e\u6062\u590d\u672c\u4efb\u52a1\u5916\u58f3\u5185\u7684\u539f\u751f\u64ad\u653e\uff0c\u4efb\u52a1\u8282\u70b9\u4e0e\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryEvidenceLuaControllerPlayback: "\u5df2\u7cbe\u786e\u6062\u590d\u968f\u6e38\u620f\u53d1\u5e03\u7684 Lua \u64ad\u653e\uff0c\u4efb\u52a1\u5f52\u5c5e\u4e0e\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryEvidenceDialogTreePlaybackContext: "\u5df2\u7cbe\u786e\u6062\u590d\u4efb\u52a1\u4e0a\u4e0b\u6587\u4e2d\u7684 DialogTree \u64ad\u653e\uff0c\u76f8\u5bf9\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryEvidenceQuestStateGate: "\u5df2\u7cbe\u786e\u6062\u590d\u4efb\u52a1\u72b6\u6001\u95e8\u63a7\u64ad\u653e\uff0c\u76f8\u5bf9\u987a\u5e8f\u672a\u77e5",
      runtimeRecoveryLuaController: "\u968f\u6e38\u620f\u53d1\u5e03\u7684 Lua \u63a7\u5236\u5668",
      runtimeRecoveryLuaCall: "\u7c7b\u578b\u5316 Lua \u64ad\u653e\u8c03\u7528",
      runtimeRecoveryEvidenceCrossMissionLevelDataPlayback: "\u5df2\u7cbe\u786e\u6062\u590d\u76f8\u5173\u4efb\u52a1\u5916\u58f3\u5185\u7684\u539f\u751f\u64ad\u653e\uff0c\u5f52\u5c5e\u4e0e\u987a\u5e8f\u672a\u77e5",
      offlineRecoveryEvidenceCutsceneRoot: "\u5df2\u89e3\u6790\u8fc7\u573a\u6839\u8282\u70b9 \u2014 \u4efb\u52a1\u6fc0\u6d3b\u5668\u672a\u77e5",
      offlineRecoveryEvidenceCutsceneAlias: "\u5df2\u786e\u8ba4\u8fc7\u573a\u6839\u8282\u70b9/\u64ad\u653e\u8d44\u4ea7\u522b\u540d \u2014 \u4efb\u52a1\u6fc0\u6d3b\u5668\u672a\u77e5",
      offlineRecoveryCutsceneAlias: "\u7cbe\u786e\u6839\u8282\u70b9/\u64ad\u653e\u8d44\u4ea7\u8eab\u4efd",
      offlineRecoveryCutsceneAliasRootRole: "\u6839\u5b9a\u4e49",
      offlineRecoveryCutsceneAliasPlayableRole: "\u88ab\u64ad\u653e\u7684\u65f6\u95f4\u7ebf\u8d44\u4ea7",
      offlineRecoveryNativeConsumer: "\u539f\u59cb\u4e8c\u8fdb\u5236\u6d88\u8d39\u8005",
      offlineRecoverySnsDefinition: "SNS \u5185\u90e8\u5b9a\u4e49",
      offlineRecoveryMissingAudio: "\u4e2a\u97f3\u9891 ID \u7f3a\u5931",
      offlineRecoveryAudioMembership: "\u97f3\u9891\u6210\u5458\u72b6\u6001",
      offlineRecoveryCarrierAudit: "\u7c7b\u578b\u5316\u8f7d\u4f53\u5ba1\u8ba1",
      offlineRecoveryBinaryRootToken: "\u539f\u59cb\u4e8c\u8fdb\u5236\u6839\u6807\u8bb0",
      offlineRecoveryMissionTracking: "\u4efb\u52a1 NPC \u8ffd\u8e2a\u4e0a\u4e0b\u6587\uff08\u4ec5\u5bfc\u822a\uff09",
      offlineRecoveryNpcProxyConsumer: "\u7cbe\u786e\u65e0\u4efb\u52a1 NpcProxyEx \u884c\uff08\u7d22\u5f15\u4e0d\u662f\u5267\u60c5\u987a\u5e8f\uff09",
      offlineRecoveryTrackedQuests: "\u8ffd\u8e2a\u4efb\u52a1\u8282\u70b9",
      offlineRecoveryRuntimeMission: "\u8fd0\u884c\u65f6\u4efb\u52a1",
      offlineRecoveryMissionBranch: "\u4efb\u52a1\u5206\u6d41/\u6c47\u5408\u4e0a\u4e0b\u6587\uff08\u5267\u60c5\u5206\u652f\u5f52\u5c5e\u672a\u89e3\u6790\uff09",
      offlineRecoveryMissionSequence: "\u539f\u59cb\u7ebf\u6027\u4efb\u52a1\u94fe\uff08\u5267\u60c5\u6587\u4ef6\u4f4d\u7f6e\u672a\u89e3\u6790\uff09",
      offlineRecoveryMissionTopology: "\u7cbe\u786e\u539f\u751f\u4efb\u52a1\u62d3\u6251",
      offlineRecoveryParallelRendezvous: "\u5e76\u884c\u524d\u7f6e\u4efb\u52a1\u4e0e AND \u6c47\u5408\uff08\u975e\u73a9\u5bb6\u9009\u9879\uff09",
      offlineRecoveryObjectiveConjunction: "AND \u6c47\u5408\u7684\u76ee\u6807\u6761\u4ef6",
      offlineRecoveryObjectiveConjunctionBoundary: "\u6240\u6709\u6761\u4ef6\u90fd\u5fc5\u987b\u6ee1\u8db3\uff0c\u4f46\u6761\u4ef6\u8bc4\u4f30\u987a\u5e8f\u4e0e Story \u4f4d\u7f6e\u672a\u5728\u539f\u59cb\u6570\u636e\u4e2d\u5e8f\u5217\u5316\u3002",
      offlineRecoveryLevelScriptPlaybackInventory: "\u76f8\u5173 LevelScript \u7684\u7cbe\u786e\u64ad\u653e\u8bb0\u5f55",
      offlineRecoveryLevelScriptPlaybackPresent: "\u72ec\u7acb\u64ad\u653e\u6839\u8282\u70b9",
      offlineRecoveryLevelScriptPlaybackAbsent: "\u7f3a\u5931\u7684\u76ee\u6807",
      offlineRecoveryLevelScriptPlaybackBoundary: "\u8fd9\u4e9b\u662f\u72ec\u7acb\u7684 action-list \u6839\u8282\u70b9\u3002\u5e8f\u5217\u5316\u5217\u8868\u4f4d\u7f6e\u4e0d\u662f\u6267\u884c\u987a\u5e8f\uff0c\u7f3a\u5931\u76ee\u6807\u4e0d\u4f1a\u83b7\u5f97\u64ad\u653e\u6216 Story \u4f4d\u7f6e\u8fb9\u3002",
      offlineRecoveryLinearTopology: "\u7ebf\u6027\u4efb\u52a1\u94fe",
      offlineRecoveryMainPath: "\u539f\u751f\u4e3b\u8def\u5f84",
      offlineRecoveryQuestStateDependency: "\u539f\u751f\u4efb\u52a1\u72b6\u6001\u4f9d\u8d56",
      offlineRecoveryQuestFailureGuard: "\u539f\u751f\u5355\u5411\u4efb\u52a1\u5931\u8d25\u6761\u4ef6",
      offlineRecoveryDialogFailureGuard: "\u539f\u751f\u5bf9\u8bdd\u5b8c\u6210\u5931\u8d25\u6761\u4ef6",
      offlineRecoveryConditionPath: "\u6761\u4ef6\u8def\u5f84",
      offlineRecoveryMissionTopologyBoundary: "\u4efb\u52a1\u524d\u7f6e\u8fde\u63a5\u4e0e\u4e3b\u8def\u5f84\u5f52\u5c5e\u5df2\u7cbe\u786e\u6062\u590d\uff1b\u5267\u60c5\u6587\u4ef6\u4f4d\u7f6e\u3001\u5206\u652f\u4e92\u65a5\u6027\u53ca\u670d\u52a1\u5668\u540e\u7ee7\u9009\u62e9\u4ecd\u672a\u89e3\u6790\u3002",
      offlineRecoveryTalkDependency: "LevelScript \u5bf9\u8bdd\u5b8c\u6210\u4f9d\u8d56\uff08\u975e\u64ad\u653e\u8bc1\u636e\uff09",
      offlineRecoveryDialogResultBranch: "\u7cbe\u786e LevelData / LevelScript \u5bf9\u8bdd\u5206\u652f",
      offlineRecoveryDialogStart: "\u914d\u7f6e\u7684\u8d77\u59cb\u5bf9\u8bdd",
      offlineRecoveryDialogResult: "result \u5206\u652f\u503c",
      offlineRecoveryControlPath: "\u5e8f\u5217\u5316\u63a7\u5236\u8def\u5f84",
      offlineRecoveryMissionRuntimeAbsent: "\u7f3a\u5c11\u540d\u4e49 MissionRuntime \u8d44\u4ea7",
      offlineRecoveryDialogBranchBoundary: "\u8fd9\u4e9b case \u662f\u4e92\u65a5\u7ed3\u679c\u3002\u6b64\u5904\u672a\u5e8f\u5217\u5316\u672c\u5730\u81ea\u5b9a\u4e49\u4e8b\u4ef6\u7684\u4ea7\u751f\u8005\uff0c\u4e5f\u6ca1\u6709\u540d\u4e49 MissionRuntime \u4efb\u52a1\u6240\u6709\u8005\u3002",
      offlineRecoveryPostDialogAction: "\u5bf9\u8bdd\u540e\u672c\u5730\u52a8\u4f5c",
      offlineRecoveryTestStub: "\u539f\u59cb\u6d4b\u8bd5\u5f39\u7a97\u5360\u4f4d\uff1b\u65e0 RichContent \u5185\u5bb9",
      offlineRecoveryCrossMissionTracking: "\u8de8\u4efb\u52a1 SNS \u8ffd\u8e2a\uff08\u4ec5\u5bfc\u822a\uff09",
      offlineMissionShell: "\u4ec5\u5267\u60c5\u6062\u590d\u7684\u4efb\u52a1\u5916\u58f3",
      offlineMissionShellHint: "\u5f53\u524d\u5bfc\u51fa\u4e2d\u6ca1\u6709 MissionRuntimeAsset\u3002\u672c\u9875\u4ec5\u5c55\u793a\u7cbe\u786e\u8868\u5b9a\u4e49\u548c\u5f53\u524d\u7248\u672c\u7684\u8f7d\u4f53\u8d1f\u8bc1\u636e\uff1b\u4e0d\u4ea7\u751f\u4efb\u52a1\u8282\u70b9\u3001\u5f52\u5c5e\u3001\u64ad\u653e\u3001\u63e1\u624b\u6216\u987a\u5e8f\u8fb9\u3002",
      storyAggregateShell: "\u58f0\u660e\u7684 Story \u53d8\u4f53\u805a\u5408",
      storyAggregateShellHint: "\u8be5 Story \u547d\u540d\u7a7a\u95f4\u6c47\u603b\u4e86\u5176\u58f0\u660e\u7684\u4efb\u52a1\u53d8\u4f53\u4e2d\u7684\u7cbe\u786e\u5e8f\u5217\u5316\u8bc1\u636e\u3002\u5b83\u672c\u8eab\u4e0d\u662f MissionRuntime \u4efb\u52a1\uff0c\u4e5f\u4e0d\u8bc1\u660e\u4efb\u52a1\u5f52\u5c5e\u3001\u8282\u70b9\u5f52\u5c5e\u3001\u5206\u652f\u9009\u62e9\u6216\u989d\u5916\u65f6\u5e8f\u3002",
      storyAggregateVariants: "\u5df2\u58f0\u660e\u7684\u4efb\u52a1\u53d8\u4f53",
      storyAggregateOriginals: "\u53d8\u4f53 MissionRuntime \u539f\u59cb\u6587\u4ef6",
      questAttachmentDiagnostic: "\u5267\u60c5\u5f52\u5c5e\u672a\u89e3\u6790",
      questAttachmentDiagnosticHint: "\u7cbe\u786e\u79bb\u7ebf\u8bc1\u636e\u5c06\u8fd9\u4e2a\u5bbd\u6cdb\u5267\u60c5\u5171\u73b0\u5173\u7cfb\u95ed\u5408\u4e3a\u975e\u5f52\u5c5e\u8bca\u65ad\uff1b\u4e0d\u751f\u6210\u4efb\u52a1\u5230\u5267\u60c5\u6216\u987a\u5e8f\u8fb9\u3002",
      questAttachmentDiagnosticStories: "\u8bca\u65ad\u5267\u60c5\u4e0a\u4e0b\u6587",
      questAttachmentDiagnosticFiles: "\u76f8\u5173\u539f\u59cb\u6570\u636e\u6587\u4ef6",
      questAttachmentDiagnosticProperty: "\u7cbe\u786e\u5c5e\u6027\u8bb0\u5f55",
      questAttachmentDiagnosticProxy: "\u8ddf\u8e2a\u7684 NPC \u4ee3\u7406",
      rejectedPlaybackCandidate: "\u5df2\u62d2\u7edd\u7684\u64ad\u653e\u5019\u9009",
      rejectedPlaybackBoundary: "\u4e8c\u8fdb\u5236\u5df2\u8bc1\u8fb9\u754c \u00b7 \u4e0d\u751f\u6210\u56fe\u8fb9",
      rejectedPlaybackLiteral: "Lua \u5b57\u9762\u91cf",
      rejectedPlaybackStoryKey: "\u5bfc\u51fa\u7684\u5267\u60c5\u952e",
      rejectedPlaybackCaseReason: "\u533a\u5206\u5927\u5c0f\u5199\u7684\u539f\u751f\u8d44\u6e90\u67e5\u627e",
      triggerQuest: "\u4efb\u52a1",
      triggerMission: "\u4f7f\u547d",
      triggerOwnershipGap: "\u7f3a\u5c11\u4f7f\u547d / \u4efb\u52a1\u5f52\u5c5e",
      triggerServerMessage: "\u670d\u52a1\u5668\u6d88\u606f",
      triggerNativeEvent: "\u539f\u751f\u4e8b\u4ef6",
      triggerLevelScript: "LevelScript",
      triggerLevelData: "LevelData",
      triggerAvailabilityCondition: "\u4ea4\u4e92\u53ef\u7528\u6761\u4ef6",
      triggerNarrativeInteractive: "\u53d9\u4e8b\u4ea4\u4e92\u5bf9\u8c61",
      triggerDialogDefinition: "\u5bf9\u8bdd\u5b9a\u4e49",
      triggerNativeAction: "\u64ad\u653e\u52a8\u4f5c",
      triggerParentStory: "\u7236\u5267\u60c5\u6587\u4ef6",
      triggerDialogTimeline: "\u5bf9\u8bdd Timeline",
      triggerStoryRoot: "CutsceneRoot \u5267\u60c5\u952e",
      triggerStory: "\u5267\u60c5\u6587\u4ef6",
      triggerLuaController: "Lua \u63a7\u5236\u5668",
      triggerNativePlayback: "\u539f\u751f\u64ad\u653e",
      triggerOriginalTableRow: "\u539f\u59cb\u8868\u884c",
      triggerExactPaths: "\u7cbe\u786e\u539f\u751f\u8def\u5f84",
      triggerEvents: "\u89e6\u53d1\u4e8b\u4ef6",
      triggerEventsHint: "\u6bcf\u884c\u90fd\u662f\u4e00\u6761\u7cbe\u786e\u7684\u5e8f\u5217\u5316\u4e8b\u4ef6\u5230\u52a8\u4f5c\u8def\u5f84\u3002\u591a\u884c\u8868\u793a\u5907\u9009\u8def\u5f84\u6216\u4e0d\u540c\u53d1\u751f\u4f4d\u7f6e\uff0c\u4e0d\u4ee3\u8868\u731c\u6d4b\u7684\u987a\u5e8f\u3002",
      triggerListener: "\u76d1\u542c\u5668",
      triggerActionChain: "\u52a8\u4f5c\u94fe",
      triggerLocalTransport: "\u672c\u5730\u6d3e\u53d1",
      triggerServerTransport: "\u670d\u52a1\u5668\u652f\u6301\u7684\u6d3e\u53d1",
      triggerUnknownTransport: "\u4f20\u8f93\u8fb9\u754c\u672a\u89e3\u6790",
      storyOrder: "\u6e90\u6570\u636e\u8bc1\u660e\u7684\u5267\u60c5\u987a\u5e8f",
      storyOrderHint: "\u8fd9\u662f\u90e8\u5206\u56e0\u679c\u56fe\uff1a\u4fdd\u7559\u5206\u652f\u3001\u6c47\u5408\u3001\u5faa\u73af\u548c\u672a\u77e5\u987a\u5e8f\uff0c\u4e0d\u731c\u6d4b\u552f\u4e00\u6587\u4ef6\u5e8f\u5217\u3002",
      missionObservedScriptContexts: "\u4efb\u52a1\u89c2\u6d4b\u5230\u7684 LevelScript \u4e0a\u4e0b\u6587",
      missionObservedScriptContextsHint: "\u539f\u59cb\u7c7b\u578b\u5316\u4efb\u52a1\u76ee\u6807\u8bfb\u53d6\u4e86\u540c\u4e00\u5173\u5361\u548c LevelScript\uff0c\u800c\u8be5\u811a\u672c\u5305\u542b\u539f\u751f\u5267\u60c5\u64ad\u653e\u3002\u8fd9\u53ea\u662f\u5173\u8054\u6587\u4ef6\u4e0a\u4e0b\u6587\uff0c\u4e0d\u662f\u5f52\u5c5e\u3001\u6fc0\u6d3b\u6216\u987a\u5e8f\u8bc1\u636e\u3002",
      observedProperties: "\u88ab\u89c2\u6d4b\u5c5e\u6027",
      propertyWriterUnresolved: "\u5c5e\u6027\u5199\u5165\u65b9\u672a\u89e3\u6790",
      embeddedStory: "\u5d4c\u5957\u5267\u60c5\u64ad\u653e",
      embeddedStoryHint: "\u539f\u59cb DialogTree \u8fde\u63a5\u5c06\u5b50\u5185\u5bb9\u7cbe\u786e\u653e\u5728\u7236\u5bf9\u8bdd\u7684\u884c\u3001\u5165\u53e3\u6216\u7ed3\u675f\u8fb9\u754c\u3002\u8fd9\u662f\u5305\u542b\u5173\u7cfb\uff0c\u4e0d\u662f\u5b8c\u6574\u6587\u4ef6\u987a\u5e8f\u8fb9\uff0c\u4e5f\u4e0d\u8bc1\u660e\u7236\u5bf9\u8bdd\u7684\u4efb\u52a1\u89e6\u53d1\u3002",
      embeddedBetween: "\u7236\u5bf9\u8bdd\u884c\u4e4b\u95f4",
      embeddedAtEntry: "\u7236\u5bf9\u8bdd\u5165\u53e3",
      embeddedAtFinish: "\u7236\u5bf9\u8bdd\u7ed3\u675f\u5904",
      readingPopup: "\u9605\u8bfb\u5f39\u7a97",
      strongEdges: "\u5f3a\u987a\u5e8f\u8fb9",
      questSucceedLifecycle: "\u4e8c\u8fdb\u5236\u5df2\u8bc1\u7684\u4efb\u52a1\u6210\u529f\u987a\u5e8f",
      questSucceedLifecycleHint: "\u7cbe\u786e\u7684\u76ee\u6807 Story \u5b8c\u6210\u5148\u4e8e\u540c\u4e00\u4efb\u52a1\u4e2d\u4f5c\u8005\u5b9a\u4e49\u7684\u6210\u529f\u5ba2\u6237\u7aef\u52a8\u4f5c\u3002\u5b89\u88c5\u7684\u4e8c\u8fdb\u5236\u8bc1\u660e\u4e86\u6210\u529f\u6d3e\u53d1\uff1b\u4e0d\u8bc1\u660e\u8be5\u4efb\u52a1\u5fc5\u7136\u6210\u529f\uff0c\u4e5f\u4e0d\u8bc1\u660e\u670d\u52a1\u7aef\u9009\u62e9\u4e86\u54ea\u4e2a\u540e\u7ee7\u5206\u652f\u3002",
      questSucceedLifecyclePath: "\u76ee\u6807 Story \u5b8c\u6210 \u2192 \u670d\u52a1\u5668\u6210\u529f\u72b6\u6001 \u2192 \u6210\u529f\u5ba2\u6237\u7aef\u52a8\u4f5c",
      questSucceedLifecycleEdges: "\u4efb\u52a1\u6210\u529f\u987a\u5e8f\u8fb9",
      questStartDefinitions: "\u4efb\u52a1\u5f00\u59cb\u5b9a\u4e49",
      questStartDefinitionsTitle: "\u5df2\u7f16\u5199\u7684\u4efb\u52a1\u5f00\u59cb Story \u52a8\u4f5c",
      questStartDefinitionsHint: "\u8fd9\u4e9b\u884c\u5b58\u5728\u4e8e\u539f\u59cb MissionRuntime \u6570\u636e\u4e2d\uff0c\u4f46\u5f53\u524d AOT \u5b8c\u6574\u679a\u4e3e\u672a\u627e\u5230 slot-1 \u8c03\u5ea6\u5668\u3002\u5b83\u4eec\u662f\u9644\u52a0\u8bc1\u636e\uff0c\u4e0d\u662f\u573a\u666f\u987a\u5e8f\u8fb9\u3002",
      questActionStartNoDispatch: "\u5df2\u7f16\u5199\u5b9a\u4e49 \u00b7 \u5f53\u524d\u65e0 AOT \u8c03\u5ea6",
      questActionBinaryDispatch: "\u4e8c\u8fdb\u5236\u5df2\u8bc1\u5b9e\u7684\u751f\u547d\u5468\u671f\u8c03\u5ea6",
      questSucceedLifecycleOriginals: "\u539f\u59cb\u751f\u547d\u5468\u671f\u8bc1\u636e\u6587\u4ef6",
      weakEdges: "\u4ec5\u4e0a\u4e0b\u6587\u8fb9",
      orderCycles: "\u6e90\u8bc1\u636e\u5faa\u73af",
      unknownPairs: "\u987a\u5e8f\u672a\u77e5\u5bf9",
      partialFrontier: "\u90e8\u5206\u987a\u5e8f\u524d\u6cbf",
      causalEdges: "\u7cbe\u7b80\u56e0\u679c\u8fb9",
      forkMerge: "\u4f5c\u8005\u5206\u652f\u4e0e\u6c47\u5408",
      dialogConditionalBranch: "Dialog \u6761\u4ef6\u5206\u652f",
      dialogConditionalTrueArm: "\u6761\u4ef6\u4e3a\u771f",
      dialogConditionalFalseArm: "\u6761\u4ef6\u4e3a\u5047",
      dialogConditionalNativeProof: "\u539f\u751f\u5206\u652f\u9009\u62e9",
      questFork: "\u4efb\u52a1\u5206\u652f",
      questForkStructure: "\u539f\u59cb\u4efb\u52a1\u5206\u652f\u7ed3\u6784",
      questForkStructureHint: "\u5206\u652f\u89d2\u8272\u3001\u5b88\u536b\u6761\u4ef6\u3001\u7ec8\u70b9\u5f62\u72b6\u548c\u518d\u6c47\u5408\u5747\u6765\u81ea\u539f\u59cb MissionRuntime \u6587\u4ef6\uff1b\u670d\u52a1\u7aef\u542f\u52a8\u4e0e\u4e92\u65a5\u7b56\u7565\u4ecd\u672a\u77e5\u3002",
      questForkMainPathArm: "\u4e3b\u8def\u5f84\u5206\u652f",
      questForkAuxiliaryArm: "\u8f85\u52a9\u5206\u652f",
      questForkGuardedArm: "\u7c7b\u578b\u5316\u5931\u8d25\u5b88\u536b",
      questForkObjectiveConditions: "\u5b8c\u6210\u6761\u4ef6",
      questForkReconverges: "\u9996\u4e2a\u516c\u5171\u540e\u7ee7",
      questForkTerminal: "\u7ec8\u70b9",
      questForkContinues: "\u7ee7\u7eed",
      questForkFlowSort: "\u663e\u793a\u987a\u5e8f",
      questForkQuestType: "\u539f\u751f\u4efb\u52a1\u7c7b\u578b",
      questForkShowMode: "\u539f\u751f\u53ef\u89c1\u6a21\u5f0f",
      questSemanticFields: "\u4efb\u52a1\u7c7b\u578b\u4e0e\u53ef\u89c1\u6027\u8bed\u4e49",
      questSemanticFieldsHint: "\u8fd9\u4e9b\u539f\u59cb\u5ba2\u6237\u7aef\u679a\u4e3e\u540d\u79f0\u4ec5\u63cf\u8ff0\u663e\u793a\u4e0e\u72b6\u6001\u5e94\u7528\u540e\u884c\u4e3a\uff0c\u4e0d\u9009\u62e9\u540e\u7ee7\u5206\u652f\u3002",
      questEnumComparisons: "\u7cbe\u786e\u679a\u4e3e\u6bd4\u8f83",
      questBlockNotification: "\u751f\u547d\u5468\u671f\u5e94\u7528\u540e\u7684 Block \u901a\u77e5",
      questOptionalObjectiveFlag: "Optional \u76ee\u6807\u663e\u793a\u6807\u5fd7",
      structuredIdentityCensus: "\u539f\u59cb\u7ed3\u6784\u5316\u8eab\u4efd\u5168\u91cf\u5ba1\u8ba1",
      structuredIdentityCensusCounts: "\u5019\u9009\u6587\u4ef6 / \u8bb0\u5f55 / \u76f4\u63a5\u8f7d\u4f53",
      structuredIdentityReceiverMatches: "\u63a5\u6536\u811a\u672c\u5339\u914d / \u672a\u5ba1\u6838\u5f62\u72b6",
      questForkArmCorridor: "\u540c\u7ea7\u5206\u652f\u72ec\u6709\u4efb\u52a1\u8d70\u5eca",
      questForkArmStoryEvidence: "\u7cbe\u786e\u76f8\u5173 Story \u8bc1\u636e",
      questForkArmOriginalFiles: "\u5206\u652f\u76f8\u5173\u539f\u59cb\u6587\u4ef6",
      questForkArmEvidenceBoundary: "\u8fd9\u4e9b\u6587\u4ef6\u4e0e Story \u5173\u7cfb\u4f4d\u4e8e\u4ec5\u80fd\u4ece\u8be5\u540c\u7ea7\u5206\u652f\u5230\u8fbe\u7684\u4efb\u52a1\u4e0a\uff1b\u5b83\u4eec\u4e0d\u8bc1\u660e\u670d\u52a1\u7aef\u9009\u4e2d\u4e86\u8be5\u5206\u652f\uff0c\u4e5f\u4e0d\u8bc1\u660e\u540c\u7ea7\u5206\u652f\u4e92\u65a5\u3002",
      questForkServerPolicy: "\u670d\u52a1\u7aef\u542f\u52a8\u7b56\u7565\u672a\u89e3",
      questForkServerApplication: "\u670d\u52a1\u7aef\u4e0b\u53d1\u7684\u5206\u652f\u4efb\u52a1\u8eab\u4efd",
      questForkServerApplicationHint: "\u539f\u59cb\u4e8c\u8fdb\u5236\u53ea\u5e94\u7528\u670d\u52a1\u7aef\u4e0b\u53d1\u7684\u4efb\u52a1\u8eab\u4efd\u4e0e\u72b6\u6001\uff0c\u4e0d\u5728\u5ba2\u6237\u7aef\u9009\u62e9\u540e\u7ee7\u5206\u652f\u3002",
      questForkServerApplicationBoundary: "\u8fd9\u53ea\u8bc1\u660e\u5ba2\u6237\u7aef\u5728\u670d\u52a1\u7aef\u9009\u62e9\u540e\u5e94\u7528\u72b6\u6001\uff1b\u4e0d\u8bc1\u660e\u670d\u52a1\u7aef\u9009\u62e9\u7b56\u7565\u3001\u540c\u7ea7\u5206\u652f\u4e92\u65a5\u6027\u6216 Story \u6587\u4ef6\u987a\u5e8f\u3002",
      questForkEnableApplication: "\u5df2\u9a8c\u8bc1\u7684\u542f\u7528 / \u6682\u505c\u8def\u7531",
      questForkEnableApplicationHint: "\u539f\u59cb\u5904\u7406\u51fd\u6570\u5c06\u6570\u636e\u5305\u542f\u7528\u6807\u5fd7\u4e0e\u5f53\u524d\u8fd0\u884c\u65f6\u6682\u505c\u6807\u5fd7\u7ec4\u5408\u3002\u5e8f\u5217\u5316\u7684\u524d\u4e00\u72b6\u6001\u5b57\u6bb5\u672a\u88ab\u8bfb\u53d6\u3002",
      questForkEnableRoute: "\u6570\u636e\u5305\u542f\u7528 / \u5f53\u524d\u6682\u505c",
      questForkUnreadControls: "\u5df2\u5e8f\u5217\u5316\u4f46\u672a\u8bfb\u53d6",
      questForkStateTransitions: "\u5df2\u9a8c\u8bc1\u72b6\u6001\u8def\u7531",
      questForkPacketShape: "\u670d\u52a1\u7aef\u6570\u636e\u5305",
      questForkMainPathAuxiliary: "\u4e3b\u8def\u5f84 + \u8f85\u52a9\u5206\u652f",
      questForkAllAuxiliary: "\u5168\u90e8\u4e3a\u8f85\u52a9\u5206\u652f",
      questForkMultipleMainPath: "\u591a\u4e2a\u4e3b\u8def\u5f84\u5206\u652f",
      questForkOpenDivergence: "\u5f00\u653e\u5206\u6d41",
      questForkDivergentTerminals: "\u5206\u6d41\u7ec8\u70b9",
      questForkMixedTerminal: "\u7ec8\u70b9 + \u7ee7\u7eed",
      questForkReconverging: "\u518d\u6c47\u5408",
      questForkAuthority: "\u4efb\u52a1\u5206\u652f\u6743\u5a01\u8fb9\u754c",
      serverSelectedStart: "\u670d\u52a1\u7aef\u9009\u62e9\u542f\u52a8\uff1b\u4ec5\u8868\u793a\u524d\u7f6e\u62d3\u6251",
      questStartReadEvidence: "StartQuest \u5b57\u6bb5\u8bfb\u53d6",
      questForkAuthorityHint: "\u5ba2\u6237\u7aef\u53ea\u521d\u59cb\u5316\u670d\u52a1\u7aef\u5df2\u9009\u4e2d\u7684\u5355\u4e2a\u4efb\u52a1\u6807\u8bc6\u3002\u8be5\u5206\u6d41\u4e0d\u80fd\u8bc1\u660e\u6240\u6709\u5206\u652f\u90fd\u4f1a\u542f\u52a8\uff0c\u4e5f\u4e0d\u80fd\u8bc1\u660e\u5fc5\u7136\u53ea\u9009\u4e00\u6761\u3002",
      wholeClientTopologyConsumers: "\u5168\u5ba2\u6237\u7aef\u62d3\u6251\u5b57\u6bb5\u6d88\u8d39\u8005",
      verifiedQuestInfoCalls: "\u5df2\u9a8c\u8bc1 GetQuestInfo \u8c03\u7528",
      activePredecessorConsumers: "\u6d3b\u52a8\u524d\u7f6e\u6d88\u8d39\u8005",
      nonSortFlowConsumers: "\u975e\u6392\u5e8f flowIndex \u6d88\u8d39\u8005",
      topologyLifecycleCalls: "\u62d3\u6251\u9a71\u52a8\u7684\u4efb\u52a1\u751f\u547d\u5468\u671f\u8c03\u7528",
      topologyConsumerMethods: "\u539f\u751f\u5b57\u6bb5\u6d88\u8d39\u65b9\u6cd5",
      displaySortOnly: "\u4e24\u884c\u663e\u793a\u6392\u5e8f",
      deprecatedDescriptionOnly: "\u5df2\u5e9f\u5f03\u7684\u63cf\u8ff0\u56de\u9000",
      mainPathContextOnly: "\u5173\u5361/\u63cf\u8ff0\u4e0a\u4e0b\u6587\u9009\u62e9",
      mainPathCacheOnly: "\u6d3e\u751f\u4e3b\u8def\u5f84\u6210\u5458\u7f13\u5b58",
      questVisibilityPresentation: "\u53ef\u89c1\u6027/\u8ddf\u8e2a\u663e\u793a",
      questTypePresentation: "\u4efb\u52a1\u7c7b\u578b\u67e5\u8be2/\u663e\u793a",
      questTypePostLifecycle: "\u751f\u547d\u5468\u671f\u72b6\u6001\u5e94\u7528\u540e\u8bfb\u53d6\u4efb\u52a1\u7c7b\u578b",
      questTypeBlockNotification: "\u751f\u547d\u5468\u671f\u72b6\u6001\u5e94\u7528\u540e\u53d1\u9001 Block \u901a\u77e5",
      questMerge: "\u4efb\u52a1\u6c47\u5408",
      nativeSplitFanout: "\u539f\u751f Split \u5206\u6d41",
      nativeIfElseBranch: "\u539f\u751f If/Else \u5206\u652f",
      nativeSwitchBranch: "\u539f\u751f Switch \u5206\u652f",
      nativeControlMerge: "\u539f\u751f\u5206\u652f\u6c47\u5408",
      nativeMissionStateBranches: "\u4efb\u52a1\u72b6\u6001 Story \u5019\u9009\u5206\u652f",
      nativeMissionStateBranchesHint: "\u539f\u59cb LevelScript \u4e0e\u5df2\u5b89\u88c5\u5ba2\u6237\u7aef\u7684 getter/comparer \u6620\u5c04\u7cbe\u786e\u8bc1\u660e\u6bcf\u4e2a\u72b6\u6001\u5206\u652f\u4e0a\u7684 Story \u6587\u4ef6\uff0c\u5305\u62ec\u540d\u4e49\u4e0a\u5f52\u5165\u5176\u4ed6\u4efb\u52a1\u7684\u6587\u4ef6\u3002\u5b83\u4eec\u662f\u4e92\u65a5\u5019\u9009\uff0c\u4e0d\u662f Story \u987a\u5e8f\u6216\u5f52\u5c5e\u3002",
      nativeMissionStateExternal: "\u8de8\u4efb\u52a1\u5019\u9009",
      nativeCrossBoundaryBranch: "\u5b8c\u6574\u8de8\u4efb\u52a1\u5206\u652f",
      nativeCrossBoundaryStories: "\u8de8\u4efb\u52a1\u5206\u652f",
      nativeCrossBoundaryExternal: "\u540d\u4e49\u4efb\u52a1\u5916",
      nativeCrossBoundaryParallelHint: "\u539f\u59cb LevelScript \u8def\u5f84\u4e0e\u5df2\u5b89\u88c5\u5ba2\u6237\u7aef\u7684 Split \u8c03\u5ea6\u5668\u8bc1\u660e\u540c\u4e00\u4e8b\u4ef6\u542f\u52a8\u542b Story \u7684\u540c\u7ea7\u5206\u6d41\u3002\u540d\u4e49\u4efb\u52a1\u5206\u7ec4\u4e0d\u8bc1\u660e\u5f52\u5c5e\uff0c\u540c\u7ea7\u69fd\u4f4d\u4e5f\u4e0d\u662f\u65f6\u95f4\u987a\u5e8f\u3002",
      nativeCrossBoundaryConditionalHint: "\u539f\u59cb LevelScript \u5206\u652f\u503c\u4e0e\u5df2\u5b89\u88c5\u5ba2\u6237\u7aef\u7684\u539f\u751f\u63a7\u5236\u6620\u5c04\u8bc1\u660e\u540c\u4e00\u4e8b\u4ef6\u7684 Story \u5019\u9009\u5206\u652f\u3002\u540d\u4e49\u4efb\u52a1\u5206\u7ec4\u4e0d\u8bc1\u660e\u5f52\u5c5e\u6216\u5019\u9009\u987a\u5e8f\u3002",
      nativeFullArmCoverage: "\u5b8c\u6574\u5e8f\u5217\u5316\u5206\u652f",
      nativeSerializedArms: "\u5e8f\u5217\u5316\u5206\u652f",
      nativeNonStoryArm: "\u975e Story \u52a8\u4f5c\u5206\u652f",
      nativeInactiveArm: "\u672a\u542f\u7528\u7684\u5e8f\u5217\u5316\u76ee\u6807",
      nativeRuntimeTerminalArm: "\u8fd0\u884c\u65f6\u7ec8\u70b9",
      nativeArmEntryAction: "\u5165\u53e3\u52a8\u4f5c",
      nativeArmExclusiveActions: "\u5206\u652f\u72ec\u6709\u52a8\u4f5c",
      nativeSharedDownstream: "\u5171\u4eab\u4e0b\u6e38\u52a8\u4f5c",
      nativeFullArmHint: "\u6bcf\u4e2a\u69fd\u4f4d\u90fd\u6765\u81ea\u539f\u59cb LevelScript \u7684\u8fd0\u884c\u65f6\u6709\u6548\u52a8\u4f5c\u8868\uff0c\u5e76\u4e0e\u5df2\u5b89\u88c5\u5ba2\u6237\u7aef\u7684\u4e8c\u8fdb\u5236\u6620\u5c04\u6821\u9a8c\u3002\u975e Story \u540c\u7ea7\u52a8\u4f5c\u4e0d\u8bc1\u660e Story \u5f52\u5c5e\u3001\u65f6\u5e8f\u6216\u4efb\u52a1\u6210\u5458\u5173\u7cfb\u3002",
      nativeOrderedSequence: "\u539f\u751f\u6709\u5e8f\u52a8\u4f5c\u5e8f\u5217",
      nativeSequenceContext: "\u5e8f\u5217\u5316 Branch \u5e8f\u5217\u4e0a\u4e0b\u6587",
      nativeSequenceContextHint: "\u7cbe\u786e Story \u8def\u5f84\u5230\u8fbe\u8fd9\u4e9b Branch \u5206\u652f\u3002\u5176\u4f59\u5e8f\u5217\u5316\u5206\u652f\u4f5c\u4e3a\u672a\u89e3\u51b3\u7684\u8fd0\u884c\u65f6\u4e0a\u4e0b\u6587\u4fdd\u7559\uff1b\u8be5\u6295\u5f71\u4e0d\u4f1a\u521b\u5efa Story \u987a\u5e8f\u6216\u5f52\u5c5e\u3002",
      nativeSequenceContextNotAdmitted: "\u672a\u63a5\u7eb3\u987a\u5e8f\u8fb9",
      nativeSequenceContextObserved: "\u5df2\u89c2\u6d4b Story \u5206\u652f",
      nativeSerializedBranchInventory: "\u5168\u91cf\u5e8f\u5217\u5316 Branch \u666e\u67e5",
      nativeSerializedBranchInventoryHint: "\u4e24\u4e2a\u539f\u59cb LevelScript \u6839\u76ee\u5f55\u90fd\u8fdb\u884c\u54c8\u5e0c\u5e76\u53bb\u91cd\u3002\u7cbe\u786e\u7684\u64ad\u653e\u52a8\u4f5c\u8bb0\u5f55\u4e0e\u6bcf\u4e2a\u5e8f\u5217\u5316 Branch \u69fd\u4f4d\u5173\u8054\uff1b\u8be5\u666e\u67e5\u4ec5\u662f\u4e0a\u4e0b\u6587\uff0c\u4e0d\u5206\u914d\u4efb\u52a1\u5f52\u5c5e\u6216\u6587\u4ef6\u987a\u5e8f\u3002",
      nativeSerializedBranchGroups: "\u5e8f\u5217\u5316 Branch \u7ec4",
      nativeSerializedBranchArms: "\u5e8f\u5217\u5316 Branch \u69fd\u4f4d",
      nativeSerializedPlaybackArms: "\u542b\u64ad\u653e\u7684\u5206\u652f",
      nativeSerializedMultiPlaybackArms: "\u591a\u64ad\u653e\u5206\u652f\u7ec4",
      nativeSerializedBranchMatched: "\u4efb\u52a1\u5339\u914d\u7684\u666e\u67e5\u884c",
      nativeSerializedBranchArmPlayback: "\u7cbe\u786e\u64ad\u653e",
      nativeSerializedBranchReachable: "\u53ef\u8fbe\u52a8\u4f5c",
      nativeSerializedBranchActions: "\u53ef\u8fbe\u539f\u751f\u52a8\u4f5c",
      nativeSerializedBranchClasses: "\u89e3\u7801\u8bb0\u5f55\u7c7b\u522b",
      nativeSerializedNestedControls: "\u5d4c\u5957\u7c7b\u578b\u63a7\u5236",
      nativeSerializedNestedArms: "\u5d4c\u5957\u5e8f\u5217\u5316\u5206\u652f",
      nativeSerializedNestedPlayback: "\u5d4c\u5957\u7cbe\u786e\u64ad\u653e",
      nativeSerializedNestedPlaybackArms: "\u5d4c\u5957\u64ad\u653e\u5206\u652f",
      nativeSerializedNestedMultiPlayback: "\u591a\u64ad\u653e\u63a7\u5236",
      nativeSerializedNestedPlaybackControls: "\u64ad\u653e\u63a7\u5236",
      nativeSerializedNestedPredicateGaps: "\u64ad\u653e\u8c13\u8bcd\u7f3a\u53e3",
      nativeSerializedNestedControlRefs: "\u53ef\u8fbe\u7c7b\u578b\u63a7\u5236",
      nativeSerializedNestedControlReferences: "\u5d4c\u5957\u63a7\u5236\u5f15\u7528",
      nativeSerializedNestedSlots: "\u5d4c\u5957\u69fd\u4f4d",
      nativeSerializedNestedActive: "\u5d4c\u5957\u6d3b\u52a8\u69fd\u4f4d",
      nativeSerializedNestedInactive: "\u5d4c\u5957\u7981\u7528\u69fd\u4f4d",
      nativeSerializedNestedUnavailable: "\u5d4c\u5957\u4e0d\u53ef\u7528\u69fd\u4f4d",
      nativeSerializedPredicateConflicts: "\u8c13\u8bcd\u51b2\u7a81",
      nativeSerializedNestedPredicate: "\u539f\u751f\u8c13\u8bcd",
      nativeStoryTransitions: "\u7cbe\u786e\u539f\u751f Story \u8f6c\u79fb",
      nativeStoryTransitionsHint: "\u6bcf\u6761\u8fb9\u90fd\u662f\u539f\u59cb LevelScript \u8def\u5f84\u524d\u7f00\u5173\u7cfb\u3002\u7c7b\u578b\u5316\u540e\u7f00\u4f1a\u663e\u793a\u64ad\u653e\u662f\u7ebf\u6027\u7ee7\u7eed\uff0c\u8fd8\u662f\u7ecf\u8fc7\u5e76\u884c\u3001\u6761\u4ef6\u3001\u6210\u529f/\u5931\u8d25\u6216\u6709\u5e8f\u5206\u652f\u3002",
      nativeStoryTransitionLinear: "\u7ebf\u6027",
      nativeStoryTransitionParallel: "\u5e76\u884c\u5206\u6d41",
      nativeStoryTransitionConditional: "\u6761\u4ef6\u5206\u652f",
      nativeStoryTransitionOutcome: "\u6210\u529f/\u5931\u8d25\u5206\u652f",
      nativeStoryTransitionOrdered: "\u6709\u5e8f\u5e8f\u5217",
      nativeStoryTransitionOrderedExit: "\u6709\u5e8f\u5e8f\u5217\u4e4b\u540e",
      nativeStoryTransitionBranching: "\u542b\u5206\u652f\u7684\u8f6c\u79fb",
      nativeRelatedActionGraphs: "\u76f8\u5173\u539f\u59cb LevelScript \u56fe",
      nativeRelatedActionGraphsHint: "\u4ec5\u5f53\u7cbe\u786e\u5e8f\u5217\u5316\u4e8b\u4ef6\u5230\u5267\u60c5\u8def\u5f84\u5230\u8fbe\u672c\u4efb\u52a1\u7684\u5267\u60c5\u6587\u4ef6\u65f6\u624d\u9644\u52a0\u6b64\u6587\u4ef6\uff1b\u5176\u4f59\u52a8\u4f5c\u53ea\u662f\u6587\u4ef6\u5185\u4e0a\u4e0b\u6587\uff0c\u4e0d\u662f\u989d\u5916\u4efb\u52a1\u987a\u5e8f\u3002",
      nativeControlReachability: "\u7cbe\u786e\u7c7b\u578b\u5316\u4e0b\u6e38\u53ef\u8fbe\u6027",
      nativeControlPath: "\u63a7\u5236\u8def\u5f84",
      nativeEventSelector: "\u4e8b\u4ef6\u9009\u62e9\u5668",
      nativePredicate: "\u5206\u652f\u6761\u4ef6",
      nativePredicateOpaque: "\u5185\u8054\u6761\u4ef6\u5c1a\u672a\u8bed\u4e49\u89e3\u7801",
      optionBranches: "\u5bf9\u8bdd\u9009\u9879\u5206\u652f",
      typedStorySelectors: "\u7c7b\u578b\u5316\u7cfb\u7edf\u9009\u62e9\u5668",
      typedStorySelectorHint: "\u539f\u59cb\u7c7b\u578b\u5316\u8868\u628a\u8fd9\u4e9b\u5267\u60c5\u6587\u4ef6\u7ed1\u5b9a\u4e3a\u540c\u4e00\u8fd0\u884c\u65f6\u9009\u62e9\u5668\u7684\u5019\u9009\u9879\uff0c\u4e0d\u4f1a\u5728\u5019\u9009\u9879\u6216\u9009\u62e9\u5668\u7ec4\u4e4b\u95f4\u521b\u5efa\u987a\u5e8f\u8fb9\u3002",
      optionDirectContinuation: "\u76f4\u63a5\u8fdb\u5165\u5171\u4eab\u540e\u7eed",
      isolatedScenes: "\u5b64\u7acb\u5267\u60c5\u6587\u4ef6",
      weakOnlyScenes: "\u4ec5\u5f31\u4e0a\u4e0b\u6587\u6587\u4ef6",
      orderCycleHint: "\u540c\u4e00\u5faa\u73af\u5206\u91cf\u5185\u6ca1\u6709\u5df2\u8bc1\u660e\u7684\u552f\u4e00\u987a\u5e8f\u3002",
      orderEvidence: "\u987a\u5e8f\u8bc1\u636e",
      activityStageLevel: "\u7cbe\u786e\u6d3b\u52a8\u4efb\u52a1\u5173\u5361",
      activityStageLevelHint: "\u7c7b\u578b\u5316\u539f\u59cb\u6d3b\u52a8\u9636\u6bb5\u914d\u7f6e\u5c06\u6b64\u4efb\u52a1\u8fde\u5230\u5173\u5361\uff0c\u4f46\u4e0d\u9644\u52a0\u5267\u60c5\u64ad\u653e\u3002",
      runtimeActions: "\u975e\u5267\u60c5\u8fd0\u884c\u65f6\u52a8\u4f5c",
      openUiAction: "\u6253\u5f00\u754c\u9762\u7ec8\u7aef",
      notStoryFile: "\u7c7b\u578b\u5316\u52a8\u4f5c\u8d44\u6e90\uff1b\u4e0d\u662f\u5267\u60c5\u6587\u4ef6",
      runtimeObserved: "\u5df2\u89c2\u6d4b\u8fd0\u884c\u65f6\u64ad\u653e",
      runtimeTraceOverlay: "\u5df2\u89c2\u6d4b\u8fd0\u884c\u65f6\u8ffd\u8e2a",
      runtimeTraceHint: "\u5b9e\u9645\u6267\u884c\u4ec5\u4f5c\u4e3a\u89c2\u6d4b\u8986\u76d6\u5c42\u5c55\u793a\u3002\u6d3b\u52a8\u4efb\u52a1\u72b6\u6001\u662f\u65f6\u5e8f\u4e0a\u4e0b\u6587\uff0c\u4e0d\u662f\u5267\u60c5\u5f52\u5c5e\uff1b\u89c2\u6d4b\u987a\u5e8f\u4e0d\u4f1a\u53d6\u4ee3\u6e90\u8bc1\u636e\u504f\u5e8f\u3002",
      exactRuntimeChains: "\u7cbe\u786e\u4e8b\u4ef6/\u52a8\u4f5c/\u64ad\u653e\u94fe",
      observedForks: "\u5df2\u89c2\u6d4b\u5206\u652f",
      observedMerges: "\u5df2\u89c2\u6d4b\u6c47\u5408",
      activeQuestContext: "\u6d3b\u52a8\u4efb\u52a1\u4e0a\u4e0b\u6587",
      noAuthoredPromotion: "\u4e0d\u63d0\u5347\u4e3a\u521b\u4f5c\u5f52\u5c5e/\u987a\u5e8f",
      observedRoute: "\u5df2\u6355\u83b7\u8def\u5f84",
      runtimeSession: "\u4f1a\u8bdd",
      observedSequence: "\u5df2\u89c2\u6d4b\u987a\u5e8f",
      summarySections: "\u6458\u8981\u5206\u533a",
      summaryFocusAll: "\u5168\u90e8",
      summarySectionStructure: "\u4f7f\u547d\u7ed3\u6784\u4e0e\u987a\u5e8f",
      summarySectionRuntime: "\u539f\u751f\u4e0e\u5b9e\u673a\u8fd0\u884c\u65f6",
      summarySectionStory: "\u5267\u60c5\u5173\u8054",
      summarySectionQueues: "\u672a\u5206\u914d\u4e0e\u8fb9\u754c\u961f\u5217",
    },
  };

  const SELECTOR_FIELD_LABELS = {
    en: {
      levelId: "level",
      listenerScriptId: "listener LevelScript",
      listenerHeaderLocalId: "receiver header ID",
      entitySlotId: "entity slot",
      entityLogicId: "entity logic ID",
      entityPropertyPath: "entity property path",
      entityPropertySource: "entity parameter source",
      entityListPropertyPath: "entity-list property path",
      entityListPropertySource: "entity-list parameter source",
      entityListFilter: "entity-list filter",
      entityFilter: "entity filter",
      entityFilters: "entity filters",
      npcEntityPropertyPath: "NPC entity path",
      npcEntityPropertySource: "NPC parameter source",
      npcEntitySlotId: "NPC entity slot",
      npcEntityLogicId: "NPC entity logic ID",
      spawnerFilterId: "spawner ID",
      groupKeyFilter: "spawner group key",
      waveKeyFilter: "spawner wave key",
      triggerSlotIdFilter: "trigger-volume slot",
      eventKey: "event key",
      signalId: "battle signal",
      guideIdFilter: "guide group ID",
      newStageFilter: "script stage",
      actionIdFilter: "action ID",
      dialogIdFilter: "dialog ID",
      npcProxyIdFilter: "NPC proxy ID",
      checkpointFilter: "checkpoint",
      patrolIdFilter: "patrol ID",
      checkpointIndexFilter: "checkpoint index",
      hpRatio: "HP threshold",
      changedDirectionName: "threshold direction",
      entityTemplateIdFilter: "entity template ID",
      blackboardKeyFilter: "blackboard key",
      propertyKeyFilter: "script property key",
      scriptedCharEventKeyFilter: "scripted-character event key",
      levelScriptVariableFilter: "LevelScript variable pointer",
      isMonsterFilter: "monster-only filter",
      filterByList: "use authored entity list",
      targetScriptId: "target LevelScript",
    },
    zh: {
      levelId: "\u5173\u5361",
      listenerScriptId: "\u76d1\u542c LevelScript",
      listenerHeaderLocalId: "\u63a5\u6536\u5668\u5934 ID",
      entitySlotId: "\u5b9e\u4f53\u69fd\u4f4d",
      entityLogicId: "\u5b9e\u4f53\u903b\u8f91 ID",
      entityPropertyPath: "\u5b9e\u4f53\u5c5e\u6027\u8def\u5f84",
      entityPropertySource: "\u5b9e\u4f53\u53c2\u6570\u6765\u6e90",
      entityListPropertyPath: "\u5b9e\u4f53\u5217\u8868\u5c5e\u6027\u8def\u5f84",
      entityListPropertySource: "\u5b9e\u4f53\u5217\u8868\u53c2\u6570\u6765\u6e90",
      entityListFilter: "\u5b9e\u4f53\u5217\u8868\u7b5b\u9009",
      entityFilter: "\u5b9e\u4f53\u7b5b\u9009",
      entityFilters: "\u5b9e\u4f53\u7b5b\u9009\u5217\u8868",
      npcEntityPropertyPath: "NPC \u5b9e\u4f53\u8def\u5f84",
      npcEntityPropertySource: "NPC \u53c2\u6570\u6765\u6e90",
      npcEntitySlotId: "NPC \u5b9e\u4f53\u69fd\u4f4d",
      npcEntityLogicId: "NPC \u5b9e\u4f53\u903b\u8f91 ID",
      spawnerFilterId: "\u751f\u6210\u5668 ID",
      groupKeyFilter: "\u751f\u6210\u7ec4\u952e",
      waveKeyFilter: "\u751f\u6210\u6ce2\u6b21\u952e",
      triggerSlotIdFilter: "\u89e6\u53d1\u533a\u5b9e\u4f53\u69fd\u4f4d",
      eventKey: "\u4e8b\u4ef6\u952e",
      signalId: "\u6218\u6597\u4fe1\u53f7",
      guideIdFilter: "\u5f15\u5bfc\u7ec4 ID",
      newStageFilter: "\u811a\u672c\u9636\u6bb5",
      actionIdFilter: "\u52a8\u4f5c ID",
      dialogIdFilter: "\u5bf9\u8bdd ID",
      npcProxyIdFilter: "NPC \u4ee3\u7406 ID",
      checkpointFilter: "\u68c0\u67e5\u70b9",
      patrolIdFilter: "\u5de1\u903b ID",
      checkpointIndexFilter: "\u68c0\u67e5\u70b9\u5e8f\u53f7",
      hpRatio: "HP \u9608\u503c",
      changedDirectionName: "\u9608\u503c\u65b9\u5411",
      entityTemplateIdFilter: "\u5b9e\u4f53\u6a21\u677f ID",
      blackboardKeyFilter: "\u9ed1\u677f\u952e",
      propertyKeyFilter: "\u811a\u672c\u5c5e\u6027\u952e",
      scriptedCharEventKeyFilter: "\u5267\u60c5\u89d2\u8272\u4e8b\u4ef6\u952e",
      levelScriptVariableFilter: "LevelScript \u53d8\u91cf\u6307\u9488",
      isMonsterFilter: "\u4ec5\u602a\u7269",
      filterByList: "\u4f7f\u7528\u4f5c\u8005\u5b9e\u4f53\u5217\u8868",
      targetScriptId: "\u76ee\u6807 LevelScript",
    },
  };
  const PROTOCOL_LABELS = {
    en: {
      expected: "expected asynchronous server traffic",
      possible: "possible server traffic (pairing unproven)",
      capability: "Protocol-capable schemas",
      schemaOnly: "schema evidence only",
      senderUnconfirmed: "native sender unconfirmed",
      runtimeUnconfirmed: "native runtime path unconfirmed",
    },
    zh: {
      expected: "\u9884\u671f\u7684\u5f02\u6b65\u670d\u52a1\u5668\u6d88\u606f",
      possible: "\u53ef\u80fd\u7684\u670d\u52a1\u5668\u6d88\u606f\uff08\u672a\u8bc1\u660e\u914d\u5bf9\uff09",
      capability: "\u534f\u8bae\u5df2\u5b9a\u4e49\u7684\u6d88\u606f",
      schemaOnly: "\u4ec5\u534f\u8bae\u6a21\u5f0f\u8bc1\u636e",
      senderUnconfirmed: "\u672a\u786e\u8ba4\u539f\u751f\u53d1\u9001\u8def\u5f84",
      runtimeUnconfirmed: "\u672a\u786e\u8ba4\u539f\u751f\u8fd0\u884c\u8def\u5f84",
    },
  };

  const app = () => document.querySelector("#mission-pipeline-app");
  const byId = (id) => document.querySelector(`#${id}`);
  const locale = () => String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  const t = (key) => (TEXT[locale()] || TEXT.en)[key] || TEXT.en[key] || key;
  const selectorFieldLabel = (field) => (SELECTOR_FIELD_LABELS[locale()] || SELECTOR_FIELD_LABELS.en)[field]
    || SELECTOR_FIELD_LABELS.en[field]
    || String(field).replace(/([a-z0-9])([A-Z])/g, "$1 $2").toLowerCase();
  const protocolLabel = (key) => (PROTOCOL_LABELS[locale()] || PROTOCOL_LABELS.en)[key]
    || PROTOCOL_LABELS.en[key]
    || key;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const normalize = (value) => String(value || "").trim().toLowerCase();
  const plainText = (value) => String(value || "")
    .replace(/<@[^>]*>/g, "")
    .replace(/<\/[^>]+>/g, "")
    .replace(/<[^>]+>/g, "")
    .replaceAll("\\n", " ")
    .trim();

  function naturalQuestNumber(id) {
    const match = String(id || "").match(/_q#(\d+)/);
    return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
  }

  function questShortLabel(id) {
    const suffix = String(id || "").split("_q#")[1];
    if (!suffix) return String(id || "?");
    return /^\d+$/.test(suffix) ? `Q${suffix}` : suffix;
  }

  function init() {
    if (state.initialized || !app()) return Boolean(app());
    state.initialized = true;
    app().innerHTML = `
      <div class="mp-shell">
        <header class="mp-hero">
          <div class="mp-hero-copy">
            <p id="mp-eyebrow" class="mp-eyebrow"></p>
            <div class="mp-title-line"><h1 id="mp-title"></h1><span class="mp-experimental">EXPERIMENTAL</span></div>
            <p id="mp-scope" class="mp-scope"></p>
          </div>
          <div id="mp-corpus" class="mp-corpus" role="status" aria-live="polite"></div>
        </header>
        <div id="mp-warning" class="mp-boundary-warning" role="note"></div>
        <div id="mp-source-provenance" class="mp-source-provenance" role="note" hidden></div>
        <div id="mp-non-mission-overview" class="mp-non-mission-overview"></div>
        <div class="mp-layout">
          <aside class="mp-browser" aria-label="Mission browser">
            <div class="mp-browser-controls">
              <label class="mp-field"><span id="mp-search-label"></span><input id="mp-search" type="search" autocomplete="off"></label>
              <label class="mp-field"><span id="mp-structure-label"></span><select id="mp-structure"></select></label>
            </div>
            <p id="mp-results" class="mp-results" role="status" aria-live="polite"></p>
            <div id="mp-mission-list" class="mp-mission-list" role="tree" aria-label="Mission tree"></div>
          </aside>
          <main class="mp-workspace">
            <section id="mp-mission-summary" class="mp-mission-summary"></section>
            <section class="mp-graph-panel" aria-labelledby="mp-graph-title">
              <div class="mp-graph-toolbar">
                <div class="mp-graph-heading"><h2 id="mp-graph-title"></h2><span id="mp-graph-meta"></span></div>
                <div class="mp-toolbar-controls">
                  <label class="mp-check"><input id="mp-show-hidden" type="checkbox" checked><span id="mp-show-hidden-label"></span></label>
                  <label class="mp-check"><input id="mp-show-dependencies" type="checkbox" checked><span id="mp-show-dependencies-label"></span></label>
                  <label class="mp-check"><input id="mp-show-edge-labels" type="checkbox"><span id="mp-show-edge-labels-label"></span></label>
                  <label class="mp-orientation"><span id="mp-orientation-label"></span><select id="mp-orientation"></select></label>
                  <div class="mp-zoom-buttons" role="group" aria-label="Graph zoom">
                    <button id="mp-zoom-out" type="button" aria-label="Zoom out">−</button>
                    <button id="mp-fit" type="button"></button>
                    <button id="mp-zoom-in" type="button" aria-label="Zoom in">+</button>
                    <button id="mp-center" type="button"></button>
                  </div>
                </div>
              </div>
              <p id="mp-control-help" class="mp-control-help"></p>
              <div class="mp-graph-body">
                <div id="mp-viewport" class="mp-viewport" tabindex="0" aria-label="Mission quest flow graph">
                  <div id="mp-plane" class="mp-plane">
                    <div id="mp-lanes" class="mp-lanes"></div>
                    <svg id="mp-edges" class="mp-edges" aria-hidden="true"></svg>
                    <div id="mp-nodes" class="mp-nodes"></div>
                  </div>
                  <div id="mp-empty-graph" class="mp-empty" hidden></div>
                </div>
                <aside id="mp-inspector" class="mp-inspector" aria-live="polite"></aside>
              </div>
              <p id="mp-drag-hint" class="mp-drag-hint"></p>
            </section>
          </main>
        </div>
      </div>`;
    bind();
    applyUiText();
    return true;
  }

  function bind() {
    byId("mp-search")?.addEventListener("input", applyMissionFilters);
    byId("mp-structure")?.addEventListener("change", applyMissionFilters);
    byId("mp-mission-list")?.addEventListener("click", (event) => {
      const group = event.target.closest("button[data-mission-type]");
      if (group) {
        toggleMissionType(group.dataset.missionType);
        return;
      }
      const button = event.target.closest("button[data-mission]");
      if (button) selectMission(button.dataset.mission);
    });
    byId("mp-mission-list")?.addEventListener("keydown", listKeydown);
    // Cross-mission graph links live in the summary pane, outside the mission
    // list's delegation scope, so they need their own handler.
    byId("mp-mission-summary")?.addEventListener("click", (event) => {
      const section = event.target.closest("button[data-mp-section]");
      if (section) {
        state.summarySection = section.dataset.mpSection;
        applySummarySection();
        return;
      }
      const button = event.target.closest("button[data-mission]");
      if (button) selectMission(button.dataset.mission);
    });
    ["mp-show-hidden", "mp-show-dependencies", "mp-show-edge-labels", "mp-orientation"].forEach((id) => {
      byId(id)?.addEventListener("change", () => {
        if (id === "mp-show-hidden" || id === "mp-orientation") {
          const plane = byId("mp-plane");
          if (plane) plane.dataset.fittedMission = "";
        }
        renderGraph();
      });
    });
    byId("mp-fit")?.addEventListener("click", fitGraph);
    byId("mp-zoom-out")?.addEventListener("click", () => zoomGraph(0.82));
    byId("mp-zoom-in")?.addEventListener("click", () => zoomGraph(1.22));
    byId("mp-center")?.addEventListener("click", centerSelected);
    byId("mp-nodes")?.addEventListener("click", (event) => {
      if (performance.now() < state.suppressGraphClickUntil) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      const button = event.target.closest("button[data-quest]");
      if (button) selectQuest(button.dataset.quest, { focus: false });
    });
    byId("mp-nodes")?.addEventListener("keydown", graphKeydown);
    const viewport = byId("mp-viewport");
    viewport?.addEventListener("pointerdown", beginPan);
    viewport?.addEventListener("pointermove", movePan);
    viewport?.addEventListener("pointerup", endPan);
    viewport?.addEventListener("pointercancel", endPan);
    viewport?.addEventListener("wheel", graphWheel, { passive: false });
    window.addEventListener("resize", () => {
      if (document.body.dataset.activeView === "mission-pipeline" && state.layout) applyTransform();
    });
    window.addEventListener("webui:ui-locale-changed", () => {
      applyUiText();
      // The corpus bar is otherwise only rendered by load(), which is keyed on
      // the data language, so a UI-locale switch used to leave its stat labels
      // in the previous language.
      updateCorpus();
      renderNonMissionOverview();
      renderMissionList();
      if (state.mission) renderMission();
    });
  }

  function applyUiText() {
    const values = {
      "mission-pipeline-tab": t("title"),
      "mp-eyebrow": t("eyebrow"), "mp-title": t("title"), "mp-scope": t("scope"),
      "mp-warning": t("warning"), "mp-search-label": t("search"), "mp-structure-label": t("structure"),
      "mp-show-hidden-label": t("showHidden"), "mp-show-dependencies-label": t("dependencies"),
      "mp-show-edge-labels-label": t("edgeLabels"), "mp-orientation-label": t("orientation"),
      "mp-fit": t("fit"), "mp-center": t("center"), "mp-graph-title": t("graph"), "mp-drag-hint": t("dragHint"),
      "mp-control-help": t("controlHelp"),
    };
    Object.entries(values).forEach(([id, value]) => { const node = byId(id); if (node) node.textContent = value; });
    const search = byId("mp-search");
    if (search) search.placeholder = t("searchPlaceholder");
    const structure = byId("mp-structure");
    if (structure) {
      const selected = structure.value;
      structure.innerHTML = [
        ["", "anyStructure"], ["case", "caseStudies"], ["fanout", "fanout"], ["joins", "joins"],
        ["finish", "exactFinish"], ["server", "serverOwned"], ["failure", "failure"],
      ].map(([value, key]) => `<option value="${value}">${esc(t(key))}</option>`).join("");
      structure.value = selected;
    }
    const orientation = byId("mp-orientation");
    if (orientation) {
      const selected = orientation.value || "auto";
      orientation.innerHTML = [["auto", "auto"], ["lr", "leftRight"], ["tb", "topBottom"]]
        .map(([value, key]) => `<option value="${value}">${esc(t(key))}</option>`).join("");
      orientation.value = selected;
    }
    const zoomOut = byId("mp-zoom-out");
    const zoomIn = byId("mp-zoom-in");
    if (zoomOut) zoomOut.title = t("zoomOut");
    if (zoomIn) zoomIn.title = t("zoomIn");
  }

  async function fetchJson(url, signal, cache = "default") {
    const response = await fetch(url, { signal, cache });
    if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
    return response.json();
  }

  async function load(language = "CN", { force = false } = {}) {
    init();
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.index && state.language === nextLanguage) return state.index;
    if (!force && state.indexPromise && state.language === nextLanguage) return state.indexPromise;
    const request = ++state.request;
    state.controller?.abort();
    state.controller = new AbortController();
    state.language = nextLanguage;
    renderLoading();
    const cache = force ? "reload" : "default";
    const promise = Promise.all([
      state.index && !force ? Promise.resolve(state.index) : fetchJson("data/mission_pipeline/index.json", state.controller.signal, cache),
      fetchJson(`data/lang/${encodeURIComponent(nextLanguage)}/missions.json`, state.controller.signal, cache).catch(() => ({ missionNames: {} })),
    ]).then(async ([index, names]) => {
      if (request !== state.request) return null;
      state.index = index;
      state.names = names?.missionNames || {};
      state.missionCache.clear();
      state.localizedCache.clear();
      updateCorpus();
      renderNonMissionOverview();
      applyMissionFilters();
      const preferred = index.missions?.some((row) => row.id === state.missionId) ? state.missionId : (index.missions?.[0]?.id || "");
      if (preferred) await selectMission(preferred, { force });
      return index;
    }).catch((error) => {
      if (request !== state.request || error?.name === "AbortError") return null;
      renderError(error);
      throw error;
    }).finally(() => {
      if (request === state.request) state.indexPromise = null;
    });
    state.indexPromise = promise;
    return promise;
  }

  function renderLoading() {
    const list = byId("mp-mission-list");
    if (list) list.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
    const summary = byId("mp-mission-summary");
    if (summary) summary.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
    const inspector = byId("mp-inspector");
    if (inspector) inspector.innerHTML = `<div class="mp-loading">${esc(t("loading"))}</div>`;
  }

  function renderError(error) {
    const message = `${t("loadError")} ${error?.message || ""}`.trim();
    const html = `<div class="mp-error" role="alert"><strong>${esc(message)}</strong><button id="mp-retry" type="button">${esc(t("retry"))}</button></div>`;
    const list = byId("mp-mission-list");
    if (list) list.innerHTML = html;
    byId("mp-retry")?.addEventListener("click", () => load(state.language, { force: true }));
  }

  function updateCorpus() {
    const counts = state.index?.counts || {};
    const storyCounts = state.index?.storyCoverage?.counts || {};
    const runtimeCounts = state.index?.runtimeTrace?.summary || {};
    const node = byId("mp-corpus");
    if (!node) return;
    const stats = [
      [counts.missions, t("missions")],
      [counts.quests, t("quests")],
      [counts.serverPlaceholderConditions, t("serverPlaceholders")],
      [storyCounts.connectedUniqueStoryFiles, t("connectedStory")],
      [storyCounts.unlinkedUniqueStoryFiles, t("unlinkedStory")],
      [storyCounts.unlinkedNativePlaybackFiles, t("nativePlaybackGaps")],
      [storyCounts.acceptedLuaExactPlaybackCalls, t("luaPlaybackAccepted")],
      [storyCounts.acceptedLuaTableCarrierCalls, t("luaTablePlaybackAccepted")],
      [storyCounts.rejectedLuaCaseMismatchCalls, t("luaPlaybackRejected")],
      [storyCounts.runtimeLuaHandleDispatcherCalls, t("luaHandleDispatchers")],
      [storyCounts.rootPlaybackAliasRows, t("rootPlaybackAliases")],
      [storyCounts.missionlessSubGameStoryFiles, t("missionlessSubGameStory")],
      [storyCounts.missionlessNativeRuntimeStoryFiles, t("missionlessRuntimeStory")],
      [storyCounts.postPlaybackFormatterNamedActions, t("postPlaybackFormatterNamed")],
      [storyCounts.postPlaybackLevelSequenceExactAssets, t("postPlaybackLevelSequenceAssets")],
      [storyCounts.postPlaybackVariableSetters, t("postPlaybackVariableSetterStat")],
      [storyCounts.unlinkedDefinitionOnlyFiles, t("definitionOnlyStory")],
      [storyCounts.nonMissionContentFiles, t("nonMissionContentStory")],
      [counts.missionGraphPrecedenceEdges, t("missionGraphEdgesStat")],
      [counts.envTalkQuestContextFiles, t("envTalkContextStat")],
      [counts.envTalkStateContextFiles, t("envTalkStateContextStat")],
    ];
    if (state.index?.runtimeTrace) stats.push([runtimeCounts.storyPlaybacks, t("runtimeObserved")]);
    node.innerHTML = stats.map(([value, label]) => `<strong>${Number(value || 0).toLocaleString()}</strong><span>${esc(label)}</span>`).join("");

    const sourceNode = byId("mp-source-provenance");
    const source = state.index?.missionRuntimeSource;
    if (!sourceNode) return;
    if (!source?.selectedRoot) {
      sourceNode.hidden = true;
      sourceNode.innerHTML = "";
      return;
    }
    const selectionLabels = {
      complete_persistent_override: t("sourceCompletePersistent"),
      streaming_assets_fallback: t("sourceStreamingFallback"),
      explicit_mission_root: t("sourceExplicitRoot"),
    };
    const changedFiles = Array.isArray(source.persistentChangedBaseFiles)
      ? source.persistentChangedBaseFiles
      : [];
    const missingFiles = Array.isArray(source.persistentMissingBaseFiles)
      ? source.persistentMissingBaseFiles
      : [];
    sourceNode.hidden = false;
    sourceNode.innerHTML = `
      <strong>${esc(t("missionSource"))}: ${esc(selectionLabels[source.selection] || source.selection || "?")}</strong>
      <code>${esc(source.selectedRoot)}</code>
      <span>${esc(t("sourceChangedFiles"))}: ${Number(source.persistentChangedBaseFileCount || changedFiles.length).toLocaleString()} / ${Number(source.streamingFileCount || 0).toLocaleString()}</span>
      ${changedFiles.length ? `<code>${esc(changedFiles.join(", "))}</code>` : ""}
      <span>${esc(t("sourceMissingFiles"))}: ${Number(missingFiles.length).toLocaleString()}</span>
      ${state.index?.storyCoverage?.luaStoryPlaybackEvidence?.status ? `<span>${esc(t("luaPlaybackAudit"))}: <strong>${esc(state.index.storyCoverage.luaStoryPlaybackEvidence.status)}</strong> · ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.scannedPlaybackCalls || 0).toLocaleString()} calls · ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.acceptedTableCarrierCalls || 0).toLocaleString()} table-owned · ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.runtimeHandleDispatcherCallCount || 0).toLocaleString()} runtime branches / ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.runtimeHandleDispatcherFamilyCount || 0).toLocaleString()} queue family · ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.runtimeHandleContract?.nativeProducerCount || 0).toLocaleString()} native producers / ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.runtimeHandleContract?.typedActionProducerTypeCount || 0).toLocaleString()} typed actions · ${Number(state.index.storyCoverage.counts?.nativeCinematicProducerRouteAttachments || 0).toLocaleString()} mission-route attachments · ${Number(state.index.storyCoverage.luaStoryPlaybackEvidence.unresolvedPlaybackCalls || 0).toLocaleString()} authored unresolved · <code>${esc(state.index.storyCoverage.luaStoryPlaybackEvidence.auditSha256 || "")}</code></span>` : ""}
    `;
  }

  function missionName(id) {
    return state.names[id] || id;
  }

  function missionTypeKey(id) {
    if (typeof storyMissionTypeFromId === "function") {
      const storyType = storyMissionTypeFromId(id);
      if (storyType) return storyType;
    }
    return String(id || "").match(/^([a-z]+)/i)?.[1]?.toLowerCase() || "other";
  }

  function missionTypeLabel(type) {
    if (typeof dataTypeLabel === "function") return dataTypeLabel(type);
    return type === "other" ? "Other" : type.toUpperCase();
  }

  function compareMissionTypes(a, b) {
    if (typeof compareDataTypeKeys === "function") return compareDataTypeKeys(a, b);
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  }

  function compareMissions(a, b) {
    if (typeof missionSort === "function") return missionSort(a.id, b.id);
    return String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
  }

  function toggleMissionType(type) {
    if (!type) return;
    if (state.expandedMissionTypes.has(type)) state.expandedMissionTypes.delete(type);
    else state.expandedMissionTypes.add(type);
    renderMissionList();
    byId("mp-mission-list")?.querySelector(`button[data-mission-type="${CSS.escape(type)}"]`)?.focus();
  }

  function missionMatchesStructure(row, value) {
    if (value === "case") return Boolean(row.caseStudy);
    if (value === "fanout") return Number(row.fanoutCount) > 0;
    if (value === "joins") return Number(row.multiPrevJoinCount) > 0 || Number(row.activeJoinCount) > 0;
    if (value === "finish") return Number(row.exactFinishCount) > 0;
    if (value === "server") return Number(row.serverPlaceholderCount) > 0;
    if (value === "failure") return Number(row.failureConditionCount) > 0;
    return true;
  }

  function applyMissionFilters() {
    if (!state.index) return;
    const query = normalize(byId("mp-search")?.value);
    const structure = byId("mp-structure")?.value || "";
    state.filtered = (state.index.missions || []).filter((row) => {
      if (!missionMatchesStructure(row, structure)) return false;
      if (!query) return true;
      return normalize([row.id, missionName(row.id), row.levelId, ...(row.conditionTypes || [])].join(" ")).includes(query);
    });
    renderMissionList();
  }

  function missionBadges(row) {
    const badges = [];
    if (row.offlineRecoveryShell) badges.push(`<span class="mp-list-badge is-evidence">${esc(t("offlineMissionShell"))}</span>`);
    if (row.storyAggregateShell) badges.push(`<span class="mp-list-badge is-evidence">${esc(t("storyAggregateShell"))}</span>`);
    if (row.caseStudy) badges.push(`<span class="mp-list-badge is-evidence">${esc(t("evidence"))}</span>`);
    if (row.fanoutCount) badges.push(`<span class="mp-list-badge">${row.fanoutCount} ${esc(t("branches"))}</span>`);
    if (row.multiPrevJoinCount || row.activeJoinCount) badges.push(`<span class="mp-list-badge">${row.multiPrevJoinCount + row.activeJoinCount} ${esc(t("join"))}</span>`);
    if (row.exactFinishCount) badges.push(`<span class="mp-list-badge is-dialog">${row.exactFinishCount} ${esc(t("exactFinishes"))}</span>`);
    if (row.serverPlaceholderCount) badges.push(`<span class="mp-list-badge is-server">${row.serverPlaceholderCount} ${esc(t("serverPlaceholders"))}</span>`);
    return badges.join("");
  }

  function renderMissionList() {
    const list = byId("mp-mission-list");
    if (!list) return;
    const results = byId("mp-results");
    if (results) results.textContent = `${state.filtered.length.toLocaleString()} ${t("shown")}`;
    if (!state.filtered.length) {
      list.innerHTML = `<div class="mp-empty-list">${esc(t("noMatches"))}</div>`;
      return;
    }
    const queryActive = Boolean(normalize(byId("mp-search")?.value));
    const grouped = new Map();
    for (const row of state.filtered) {
      const type = missionTypeKey(row.id);
      if (!grouped.has(type)) grouped.set(type, []);
      grouped.get(type).push(row);
    }
    list.innerHTML = [...grouped.keys()].sort(compareMissionTypes).map((type) => {
      const rows = grouped.get(type).sort(compareMissions);
      const expanded = queryActive || state.expandedMissionTypes.has(type);
      const missions = expanded ? rows.map((row) => {
        const selected = row.id === state.missionId;
        return `<button class="mp-mission-row${selected ? " is-selected" : ""}" type="button" role="treeitem" aria-level="2" aria-selected="${selected}" data-mission="${esc(row.id)}">
          <span class="mp-mission-row-head"><strong>${esc(missionName(row.id))}</strong><code>${esc(row.id)}</code></span>
          <span class="mp-mission-row-meta">${esc(row.levelId || "—")} · ${row.questCount} ${esc(t("quests"))}</span>
          <span class="mp-list-badges">${missionBadges(row)}</span>
        </button>`;
      }).join("") : "";
      return `<section class="mp-mission-type${expanded ? " is-expanded" : ""}" role="none">
        <button class="mp-mission-type-row" type="button" role="treeitem" aria-level="1" aria-expanded="${expanded}" data-mission-type="${esc(type)}">
          <span class="mp-mission-type-twisty" aria-hidden="true">${expanded ? "v" : ">"}</span>
          <span class="mp-mission-type-main"><strong>${esc(missionTypeLabel(type))}</strong><code>${esc(type)}</code></span>
          <span class="mp-mission-type-count">${rows.length}</span>
        </button>
        ${expanded ? `<div class="mp-mission-type-items" role="group">${missions}</div>` : ""}
      </section>`;
    }).join("");
  }

  function listKeydown(event) {
    if (!event.target.matches("button[data-mission]")) return;
    const buttons = Array.from(byId("mp-mission-list")?.querySelectorAll("button[data-mission]") || []);
    const index = buttons.indexOf(event.target);
    let target = null;
    if (event.key === "ArrowDown") target = buttons[index + 1] || buttons[0];
    else if (event.key === "ArrowUp") target = buttons[index - 1] || buttons.at(-1);
    else if (event.key === "Home") target = buttons[0];
    else if (event.key === "End") target = buttons.at(-1);
    if (target) { event.preventDefault(); target.focus(); target.scrollIntoView({ block: "nearest" }); }
  }

  async function selectMission(id, { force = false } = {}) {
    if (!id || !state.index) return null;
    state.missionId = id;
    state.expandedMissionTypes.add(missionTypeKey(id));
    renderMissionList();
    const summary = byId("mp-mission-summary");
    if (summary) summary.innerHTML = `<div class="mp-loading">${esc(t("loadingMission"))}</div>`;
    const request = ++state.missionRequest;
    const coreKey = id;
    const localizedKey = `${state.language}:${id}`;
    try {
      const corePromise = !force && state.missionCache.has(coreKey)
        ? Promise.resolve(state.missionCache.get(coreKey))
        : fetchJson(`data/mission_pipeline/missions/${encodeURIComponent(id)}.json`, null, force ? "reload" : "default");
      const localizedPromise = !force && state.localizedCache.has(localizedKey)
        ? Promise.resolve(state.localizedCache.get(localizedKey))
        : fetchJson(`data/lang/${encodeURIComponent(state.language)}/mission/${encodeURIComponent(id)}.json`, null, force ? "reload" : "default").catch(() => null);
      const [mission, localized] = await Promise.all([corePromise, localizedPromise]);
      if (request !== state.missionRequest || id !== state.missionId) return null;
      state.missionCache.set(coreKey, mission);
      state.localizedCache.set(localizedKey, localized);
      state.mission = mission;
      state.localized = localized;
      const visibleIds = new Set((mission.nodes || []).map((row) => row.id));
      state.selectedQuestId = visibleIds.has(state.selectedQuestId)
        ? state.selectedQuestId
        : (mission.mission?.mainPath?.find((questId) => visibleIds.has(questId)) || mission.nodes?.[0]?.id || "");
      renderMission();
      return mission;
    } catch (error) {
      if (request !== state.missionRequest) return null;
      if (summary) summary.innerHTML = `<div class="mp-error" role="alert">${esc(t("loadError"))} ${esc(error?.message || "")}</div>`;
      throw error;
    }
  }

  function localizedQuestMap() {
    const map = new Map();
    for (const quest of state.localized?.flow?.quests || []) map.set(quest.id, quest);
    return map;
  }

  function objectiveText(node, localizedMap = localizedQuestMap()) {
    const localized = localizedMap.get(node.id);
    const texts = (localized?.objectiveInstructions || []).map((row) => plainText(row.text)).filter(Boolean);
    if (texts.length) return [...new Set(texts)].join(" / ");
    const keys = (node.objectives || []).map((row) => row.descriptionKey).filter(Boolean);
    return keys.join(" / ") || t("noObjective");
  }

  function missionDescriptionInfo(node, localizedMap = localizedQuestMap()) {
    const localizedQuest = localizedMap.get(node.id);
    const row = localizedQuest?.missionDescription || state.localized?.flow?.missionDescription || null;
    return {
      key: String(row?.key || ""),
      text: plainText(row?.text || ""),
      source: String(row?.source || "mission"),
    };
  }

  function questStoryFiles(node, localizedMap = localizedQuestMap()) {
    const rows = localizedMap.get(node.id)?.storyFiles || [];
    return rows.filter((row) => row && row.key);
  }

  function questRuntimeActions(node, localizedMap = localizedQuestMap()) {
    const rows = localizedMap.get(node.id)?.runtimeActions || [];
    return rows.filter((row) => row && row.kind === "dialog_tree_action");
  }

  function questStoryConnections(node, localizedMap = localizedQuestMap()) {
    const localized = localizedMap.get(node.id) || {};
    const localizedRows = (localized.storyConnections || []).filter((row) => row && row.key);
    const fallbackRows = localizedRows.length
      ? []
      : questStoryFiles(node, localizedMap).map((row) => ({
          ...row,
          relation: "runtime_reference",
          direction: "context",
          phase: "unknown",
          confidence: "direct_untyped",
          source: row.evidence || "quest Story reference",
        }));
    const scopeRows = (node.storyScopeContexts || []).filter((row) => row && row.key);
    const unique = new Map();
    for (const row of [...localizedRows, ...fallbackRows, ...scopeRows]) {
      const signature = [
        row.key,
        row.relation || "",
        row.sourceRelation || "",
        (row.scriptIds || []).join(","),
      ].join("\u0000");
      if (!unique.has(signature)) unique.set(signature, row);
    }
    return [...unique.values()];
  }

  function storyConnectionCounts(node, localizedMap = localizedQuestMap()) {
    const counts = { incoming: 0, outgoing: 0, context: 0 };
    for (const row of questStoryConnections(node, localizedMap)) {
      const direction = storyConnectionDirectionGroup(row);
      if (direction === "story_to_quest") counts.incoming += 1;
      else if (direction === "quest_to_story") counts.outgoing += 1;
      else counts.context += 1;
    }
    return counts;
  }

  function storyConnectionDirectionGroup(row) {
    const direction = row?.direction || "context";
    return direction === "story_to_quest" || direction === "quest_to_story"
      ? direction
      : "context";
  }

  function storyRelationLabel(relation) {
    const key = {
      objective_condition: "relationObjectiveCondition",
      objective_tracking_story_reference: "relationObjectiveTrackingStory",
      failure_condition: "relationFailureCondition",
      client_action_start: "relationClientStart",
      client_action_succeed: "relationClientSucceed",
      client_action_failed: "relationClientFailed",
      leveldata_quest_reference: "relationLevelData",
      levelscript_condition_scope: "relationLevelScript",
      levelscript_property_story_consumer: "relationLevelScriptPropertyConsumer",
      quest_objective_levelscript_scope_context: "relationQuestObjectiveLevelScriptScope",
      levelscript_mission_context: "relationLevelScriptMission",
      leveldata_levelscript_mission_context: "relationLevelDataScriptHost",
      leveldata_world_entity_quest_playback_context: "relationWorldEntityQuestPlayback",
      quest_progress_locked_interactive_playback_context: "relationQuestProgressLockedInteractive",
      mission_area_leveldata_mission_context: "relationMissionAreaLevelDataHost",
      mission_area_trigger_volume_story_context: "relationMissionAreaTriggerContext",
      authoritative_scope_leveldata_mission_context: "relationAuthoritativeScopeLevelDataHost",
      entity_tracking_interactive_story_target: "relationEntityTrackedInteractive",
      entity_tracking_native_playback_context: "relationEntityTrackedScript",
      entity_tracking_native_event_playback_context: "relationEntityTrackedNativeEvent",
      entity_tracking_native_property_playback_context: "relationEntityTrackedProperty",
      entity_tracking_world_interactive_dialog_context: "relationEntityTrackedWorldDialog",
      spawner_config_authored_mission_context: "relationSpawnerConfigMission",
      hp_spawner_config_authored_mission_context: "relationHpSpawnerConfigMission",
      mission_global_var_native_playback_context: "relationMissionGlobalVarPlayback",
      cutscene_root_playback_alias_composed: "relationRootPlaybackAliasComposed",
      npc_proxy_wait_native_playback_context: "relationNpcReadyPlayback",
      npc_proxy_target_native_playback_context: "relationNpcTargetPlayback",
      npc_proxy_segment_levelscript_mission_context: "relationNpcProxySegmentShell",
      mission_state_getter_native_dependency: "relationMissionStateDependency",
      levelscript_task_mission_state_dependency: "relationTaskMissionStateDependency",
      mission_state_processing_native_playback_context: "relationMissionStateProcessing",
      radio_trigger_zone_mission_state_dependency: "relationRadioTriggerMissionState",
      radio_trigger_zone_mission_state_playback_context: "relationRadioTriggerMissionState",
      npc_patrol_action_radio_playback_context: "relationNpcPatrolRadioPlayback",
      airwall_mission_state_radio_dependency: "relationAirWallMissionState",
      airwall_mission_state_radio_playback_context: "relationAirWallMissionState",
      narrative_interactive_mission_state_dependency: "relationNarrativeInteractiveMissionState",
      narrative_interactive_mission_state_playback_context: "relationNarrativeInteractiveMissionState",
      levelscript_interactive_narrative_config: "relationLevelScriptInteractiveNarrative",
      leveldata_interactive_narrative_config: "relationLevelDataInteractiveNarrative",
      authoritative_scope_native_event_playback_context: "relationNativeEventShellPlayback",
      mission_shell_manual_guide_completion_playback_context: "relationManualGuideCompletionPlayback",
      variant_runtime_attachment: "relationVariantRuntime",
      unique_npc_proxy: "relationNpcProxy",
      npc_proxy_attachment: "relationNpcProxy",
      npc_proxy_ex_attachment: "relationNpcProxyEx",
      npc_proxy_ex_mission_context: "relationNpcProxyMission",
      unique_mission_tracked_npc_proxy_dialog_context: "relationUniqueMissionTrackedNpcProxyDialog",
      npc_proxy_tracking_dialog_navigation_context: "relationNpcProxyTrackingDialog",
      npc_proxy_lazy_destroy_dialog_context: "relationNpcProxyLazyDestroyDialog",
      mission_tracked_npc_patrol_entity_context: "relationMissionTrackedNpcPatrol",
      mission_tracked_world_entity_levelscript_context: "relationMissionTrackedWorldEntityLevelScript",
      mission_tracked_world_entity_levelscript_stage_context: "relationMissionTrackedWorldEntityLevelScriptStage",
      focus_mode_interact_locked_radio: "relationFocusModeRadio",
      sns_authored_mission_link: "relationSnsMissionLink",
      timeline_dialog_contains_black: "relationTimelineBlack",
      timeline_black_root_unresolved: "relationTimelineBlackUnresolved",
      dialog_tree_narrative_action: "relationDialogNarrativeAction",
      dialog_tree_narrative_action_unscoped: "relationDialogNarrativeActionUnscoped",
      dialog_tree_left_subtitle_action: "relationDialogLeftSubtitleAction",
      dialog_tree_left_subtitle_action_unscoped: "relationDialogLeftSubtitleActionUnscoped",
      dialog_tree_reachable_story_playback: "relationDialogStoryPlayback",
      dialog_tree_reachable_story_playback_unscoped: "relationDialogStoryPlaybackUnscoped",
      dialog_tree_prime_reachable_story_playback_dependency: "relationDialogPrimeStoryPlayback",
      original_text_definition_without_consumer: "relationDefinitionOnly",
      mission_accept_dialog: "relationMissionAccept",
      mission_area_story_reference: "relationMissionArea",
      story_graph_branch: "relationStoryGraphBranch",
      levelscript_story_sequence: "relationLevelScriptSequence",
      levelscript_quest_processing_action: "relationQuestProcessingAction",
      levelscript_quest_completed_action: "relationQuestCompletedAction",
      levelscript_quest_state_gate: "relationQuestStateGate",
      levelscript_native_black_action: "relationNativeBlackAction",
      native_story_playback_unscoped: "relationNativePlaybackUnscoped",
      native_black_playback_unscoped: "relationNativePlaybackUnscoped",
      unassigned_story: "relationUnassignedStory",
      runtime_reference: "relationRuntimeReference",
      env_talk_quest_tracked_proxy: "relationEnvTalkTrackedProxy",
      env_talk_atmospheric_switcher_state_context: "relationEnvTalkSwitcherState",
      env_talk_multiple_context: "relationEnvTalkMultipleContext",
    }[relation];
    return key ? t(key) : String(relation || t("relationRuntimeReference"));
  }

  function storyDisplayKind(row) {
    const key = String(row?.key || "");
    if (key.startsWith("dlg_") || key.startsWith("misc_dlg_")) return "dialog";
    if (key.startsWith("radio_")) return "radio";
    if (key.startsWith("cutscene_")) return "cutscene";
    if (key.startsWith("remotecomm_")) return "remotecomm";
    if (key.startsWith("sns_")) return "sns";
    if (key.startsWith("black_")) return "black";
    if (key.startsWith("text_")) return "text";
    if (key.startsWith("env_")) return "envtalk";
    return String(row?.kind || "story");
  }

  function storyHref(key) {
    const params = new URLSearchParams();
    params.set("lang", state.language || "CN");
    params.set("ui", locale());
    params.set("story", key);
    return `?${params.toString()}#story`;
  }

  function storyConnectionDetails(row) {
    return [
      storyRelationLabel(row.relation),
      row.rootDialogId ? `${t("exactDialogRootAlias")} ${row.rootDialogId} \u2192 ${row.key}` : "",
      row.rootPayloadAlias?.payloadIdentity === true ? t("exactDialogRootAliasBoundary") : "",
      row.rootPayloadAlias?.decodedScriptSha256 ? `m_Script SHA-256 ${row.rootPayloadAlias.decodedScriptSha256}` : "",
      row.phase ? `phase=${row.phase}` : "",
      row.finishId !== undefined ? `finish=${row.finishId}` : "",
      row.actionType ? `${row.actionType} / slot ${row.actionSlot ?? "?"}` : "",
      row.actionName ? row.actionName : "",
      row.nativeAction ? `native action ${row.nativeAction}` : "",
      row.nativeEventName ? `native event ${row.nativeEventName}` : "",
      (row.nativeActions || []).length ? `native action ${(row.nativeActions || []).join(", ")}` : "",
      (row.opcodes || []).length ? `opcode ${(row.opcodes || []).join(", ")}` : "",
      (row.nativeActionTags || []).length ? `MemoryPack action tag ${(row.nativeActionTags || []).join(", ")}` : "",
      (row.nativeEventNames || []).length ? `native event ${(row.nativeEventNames || []).join(", ")}` : "",
      (row.nativeEventTags || []).length ? `MemoryPack event tag ${(row.nativeEventTags || []).join(", ")}` : "",
      (row.nativeEventOpcodes || []).length ? `legacy decoded pair ${(row.nativeEventOpcodes || []).join(", ")}` : "",
      (row.nativeEventTexts || []).length ? `event payload ${(row.nativeEventTexts || []).join(", ")}` : "",
      (row.nativeEventSummaries || []).length ? `event condition ${(row.nativeEventSummaries || []).join(", ")}` : "",
      (row.triggerSlotIds || []).length ? `trigger slots ${(row.triggerSlotIds || []).join(", ")}` : "",
      (row.stageFilters || []).length ? `stage filters ${(row.stageFilters || []).join(", ")}` : "",
      row.nativeControlPathCount ? `exact control paths ${row.nativeControlPathCount}` : "",
      row.nativeEventOwnerStatus ? `event owner ${row.nativeEventOwnerStatus}` : "",
      row.nativeEventProducerStatus ? `event producer ${row.nativeEventProducerStatus}` : "",
      (row.producerAssetIds || []).length ? `producer assets ${(row.producerAssetIds || []).join(", ")}` : "",
      (row.producerDomains || []).length ? `producer domains ${(row.producerDomains || []).join(", ")}` : "",
      (row.producerSignals || []).length ? `literal signals ${(row.producerSignals || []).join(", ")}` : "",
      (row.producerValues || []).length ? `signal values ${(row.producerValues || []).join(", ")}` : "",
      (row.questIds || []).length ? `${t("trackedByQuests")} ${(row.questIds || []).join(", ")}` : "",
      row.scriptId ? `LevelScript ${row.scriptId}` : "",
      (row.scriptIds || []).length ? `scripts ${(row.scriptIds || []).join(", ")}` : "",
      (row.producerScriptIds || []).length ? `producer scripts ${(row.producerScriptIds || []).join(", ")}` : "",
      (row.listenerScriptIds || []).length ? `listener scripts ${(row.listenerScriptIds || []).join(", ")}` : "",
      (row.producerActions || []).length ? `producer actions ${(row.producerActions || []).join(", ")}` : "",
      (row.raisedEventKeys || []).length ? `raised events ${(row.raisedEventKeys || []).join(", ")}` : "",
      (row.producerReceiverModes || []).length ? `event receivers ${(row.producerReceiverModes || []).join(", ")}` : "",
      row.conditionKey ? `condition ${row.conditionKey}` : "",
      row.conditionValue !== undefined ? `condition value ${row.conditionValue}` : "",
      row.taskKey ? `task ${row.taskKey}` : "",
      row.taskEntryOffsetHex ? `task offset ${row.taskEntryOffsetHex}` : "",
      row.conditionOffsetHex ? `condition offset ${row.conditionOffsetHex}` : "",
      row.sameScriptOnly === true ? t("sameScriptDependency") : "",
      row.controlPathLinked === false ? t("noPlaybackControlPath") : "",
      row.conditionComparer ? `comparer ${row.conditionComparer}` : "",
      row.conditionQuestState !== undefined ? `quest state ${row.conditionQuestState}` : "",
      row.questStateName ? `quest state ${row.questStateName}` : "",
      row.executionSide ? `executes on ${row.executionSide}` : "",
      row.networkRole ? `network role ${row.networkRole}` : "",
      row.serverEvidenceStatus ? `server evidence ${row.serverEvidenceStatus}` : "",
      row.nativeFallbackCaveat ? `native fallback ${row.nativeFallbackCaveat}` : "",
      row.consumerSearchStatus ? `consumer search ${row.consumerSearchStatus}` : "",
      (row.searchedConsumerKinds || []).length ? `searched consumers ${(row.searchedConsumerKinds || []).join(", ")}` : "",
      row.bindingStatus ? `binding ${row.bindingStatus}` : "",
      row.nominalStoryGroup ? `nominal Story group ${row.nominalStoryGroup}` : "",
      row.serverMessage ? `server message ${row.serverMessage}` : "",
      (row.serverFields || []).length ? `server fields ${(row.serverFields || []).join(", ")}` : "",
      (row.upstreamServerStateSources || []).length ? `independent upstream pushes ${(row.upstreamServerStateSources || []).join(", ")}` : "",
      row.upstreamServerStateRole ? row.upstreamServerStateRole : "",
      row.clientRequest === false ? "no paired client request" : "",
      row.expectedClientReply === false ? "no expected client reply" : "",
      row.expectedReturn ? `expected return ${row.expectedReturn}` : "",
      row.levelScriptMissionId ? `scoped mission ${row.levelScriptMissionId}` : "",
      row.levelDataHostMissionId ? `LevelData asset host ${row.levelDataHostMissionId}` : "",
      row.missionAreaHostMissionId ? `mission-area asset host ${row.missionAreaHostMissionId}` : "",
      row.trackingMissionId ? `tracking mission ${row.trackingMissionId}` : "",
      (row.candidateQuestIds || []).length ? `tracking quest context ${(row.candidateQuestIds || []).join(", ")}` : "",
      row.worldEntityId ? `world entity ${row.worldEntityId}` : "",
      (row.worldEntityIds || []).length > 1 ? `world entities ${(row.worldEntityIds || []).join(", ")}` : "",
      (row.worldEntityResolutionModes || []).length ? `world-entity join ${(row.worldEntityResolutionModes || []).join(", ")}` : "",
      (row.levelDataEntityPropertyNames || []).length ? `LevelData entity properties ${(row.levelDataEntityPropertyNames || []).join(", ")}` : "",
      (row.npcEntityPropertyPaths || []).length ? `LevelData NPC alias ${(row.npcEntityPropertyPaths || []).join(", ")}` : "",
      (row.patrolIds || []).length ? `patrol ${(row.patrolIds || []).join(", ")}` : "",
      (row.checkpointIndices || []).length ? `checkpoint ${(row.checkpointIndices || []).join(", ")}` : "",
      (row.localScriptIds || []).length ? `local scripts ${(row.localScriptIds || []).join(", ")}` : "",
      (row.entitySlotIds || []).length ? `tracked entity slots ${(row.entitySlotIds || []).join(", ")}` : "",
      (row.entityLogicIds || []).length ? `entity logic ids ${(row.entityLogicIds || []).join(", ")}` : "",
      (row.trackedLocalEntityLogicIds || []).length ? `tracked local entity ids ${(row.trackedLocalEntityLogicIds || []).join(", ")}` : "",
      (row.entityDetailIds || []).length ? `registry details ${(row.entityDetailIds || []).join(", ")}` : "",
      (row.entityTemplateIds || []).length ? `InteractiveTable templates ${(row.entityTemplateIds || []).join(", ")}` : "",
      (row.entityTemplatePaths || []).length ? `narrative template paths ${(row.entityTemplatePaths || []).join(", ")}` : "",
      row.interactivePropertyKey ? `interactive property ${row.interactivePropertyKey}` : "",
      (row.propertyKeys || []).length ? `property keys ${(row.propertyKeys || []).join(", ")}` : "",
      row.interactiveEntryOffset !== undefined ? `interactive entry offset ${row.interactiveEntryOffset}` : "",
      row.interactivePropertyOffset !== undefined ? `property offset ${row.interactivePropertyOffset}` : "",
      row.trackedSlotBridgeStatus ? `slot bridge ${row.trackedSlotBridgeStatus}` : "",
      row.producerEventName ? `producer event ${row.producerEventName}` : "",
      row.producerHeaderLocalId !== undefined ? `producer header local ${row.producerHeaderLocalId}` : "",
      row.raiseActionLocalId !== undefined ? `raise action local ${row.raiseActionLocalId}` : "",
      row.raisedEventKey ? `raised event ${row.raisedEventKey}` : "",
      row.guideGroupId ? `guide group ${row.guideGroupId}` : "",
      row.producerActionLocalId !== undefined ? `producer action local ${row.producerActionLocalId}` : "",
      row.missionGlobalVarKey ? `client global var ${row.missionGlobalVarKey}` : "",
      row.missionStateId ? `mission-state getter ${row.missionStateId}` : "",
      (row.missionStateGateRoles || []).length ? `selected mission-state branch ${(row.missionStateGateRoles || []).join(", ")}` : "",
      (row.missionStateGatePredicates || []).length ? `exact predicates ${(row.missionStateGatePredicates || []).join("; ")}` : "",
      row.radioTriggerId ? `radio-trigger zone ${row.radioTriggerId}` : "",
      row.useRadioTriggerOnce === true ? "one-shot radio trigger" : "",
      row.patrolId ? `NPC patrol ${row.patrolId}` : "",
      row.patrolPointCount !== undefined ? `patrol points ${row.patrolPointCount}` : "",
      row.patrolPointIndex !== undefined && row.patrolPointIndex !== null
        ? `exact patrol point ${row.patrolPointIndex}`
        : row.patrolEnvelopeStatus === "exact_typed_neighbor_boundaries_partial_point_decode"
          ? "patrol point unresolved; exact typed neighbor boundaries retained"
          : "",
      row.patrolPointActionIndex !== undefined && row.patrolPointActionIndex !== null
        ? `point action ${row.patrolPointActionIndex}`
        : "",
      row.patrolEnvelopeStatus ? `patrol envelope ${row.patrolEnvelopeStatus}` : "",
      row.radioActionRecordOffset !== undefined
        ? `radio action bytes ${row.radioActionRecordOffset}-${row.radioActionRecordEndOffset}`
        : "",
      row.radioRadius !== undefined ? `radio radius ${row.radioRadius}` : "",
      row.readingPopupId ? `ReadingPopUp ${row.readingPopupId}` : "",
      row.interactiveListCount ? `LevelInteractiveData list count ${row.interactiveListCount}` : "",
      row.interactiveRecordIndex !== undefined ? `interactive record index ${row.interactiveRecordIndex}` : "",
      row.interactiveParamMapOffset !== undefined ? `ParamValue map offset ${row.interactiveParamMapOffset}` : "",
      row.spawnerConfigMissionId ? `SpawnerConfig mission ${row.spawnerConfigMissionId}` : "",
      (row.spawnerIds || []).length ? `spawner ids ${(row.spawnerIds || []).join(", ")}` : "",
      (row.authoredSpawnerTokens || []).length ? `authored spawner ids ${(row.authoredSpawnerTokens || []).join(", ")}` : "",
      (row.nativeControlPathStatuses || []).length ? `control path status ${(row.nativeControlPathStatuses || []).join(", ")}` : "",
      row.entityCompareBridge ? `entity comparison ${JSON.stringify(row.entityCompareBridge)}` : "",
      row.variantMission ? `variant ${row.variantMission}` : "",
      row.attachmentKind ? `attachment ${row.attachmentKind}` : "",
      row.npcProxyId ? `NPC ${row.npcProxyId}` : "",
      (row.npcProxyIds || []).length ? `NPC proxies ${(row.npcProxyIds || []).join(", ")}` : "",
      row.activeRowIndex !== undefined && row.activeRowIndex !== null ? `one-based active row ${row.activeRowIndex}` : "",
      (row.configuredDialogIds || []).length ? `configured proxy dialogs ${(row.configuredDialogIds || []).join(", ")}` : "",
      row.selectionOrderStatus ? `order boundary ${row.selectionOrderStatus}` : "",
      (row.segmentIdsGlobal || []).length ? `authored segment scripts ${(row.segmentIdsGlobal || []).join(", ")}` : "",
      row.npcProxyMissionId ? `mission ${row.npcProxyMissionId}` : "",
      row.focusModeId ? `FocusMode ${row.focusModeId}` : "",
      row.focusModeMissionId ? `mission ${row.focusModeMissionId}` : "",
      row.focusModeField ? `field ${row.focusModeField}` : "",
      row.snsDialogId ? `SNS ${row.snsDialogId}` : "",
      row.snsMissionId ? `mission ${row.snsMissionId}` : "",
      (row.snsContentIds || []).length ? `content ${(row.snsContentIds || []).join(", ")}` : "",
      row.parentStoryKey ? `parent Story ${row.parentStoryKey}` : "",
      row.dependencyOnly === true ? "dependency only; no Story ownership" : "",
      (row.primeNodeIds || []).length ? `prime nodes ${(row.primeNodeIds || []).join(", ")}` : "",
      row.parentStoryOutKey ? `parent Story output ${row.parentStoryOutKey}` : "",
      (row.parentStoryKeys || []).length ? `candidate parents ${(row.parentStoryKeys || []).join(", ")}` : "",
      (row.allParentStoryKeys || []).length > 1 ? `all authored parents ${(row.allParentStoryKeys || []).join(", ")}` : "",
      (row.unscopedParentStoryKeys || []).length ? `unresolved parent uses ${(row.unscopedParentStoryKeys || []).join(", ")}` : "",
      row.scopeCompleteness ? `scope ${row.scopeCompleteness}` : "",
      row.parentStatus ? `parent status ${row.parentStatus}` : "",
      (row.textIds || []).length ? `text ${(row.textIds || []).join(", ")}` : "",
      (row.actionKinds || []).length ? `narrative action ${(row.actionKinds || []).join(", ")}` : "",
      (row.actionTypes || []).length ? `typed class ${(row.actionTypes || []).join(", ")}` : "",
      (row.actionPaths || []).length ? `DialogTree path ${(row.actionPaths || []).join(", ")}` : "",
      (row.sourcePathIds || []).length ? `asset PathID ${(row.sourcePathIds || []).join(", ")}` : "",
      row.evidenceTier ? `evidence tier ${row.evidenceTier}` : "",
      row.serverExchange === false
        ? (row.clientNavigationOnly
          ? "local navigation context; no server exchange"
          : row.networkRole === "local_trigger_context"
            ? "local trigger context; no server exchange"
          : row.networkRole === "local_asset_shell_context"
              ? "local asset-shell context; no server exchange"
              : row.networkRole === "local_mission_event_context"
                ? "local mission-event context; no decoded server exchange"
                : row.networkRole === "local_npc_ready_context"
                  ? "local NPC-readiness context; no decoded server exchange"
                  : row.networkRole === "local_tracked_entity_event_context"
                    ? "local tracked-entity playback context; objective server response is opaque"
                    : row.networkRole === "local_navigation_and_property_event_context"
                      ? "local tracked-entity property context; objective server response is opaque"
                    : row.networkRole === "local_npc_playback_target_context"
                      ? "local Play3DRadio NPC-emitter context; no server exchange"
                      : row.networkRole === "local_asset_shell_custom_event_context"
                        ? "local asset-shell custom-event playback route; no server exchange"
                      : row.networkRole === "local_levelscript_event_dispatch"
                        ? "local LevelScript custom-event dispatch; no server request or response"
                      : row.networkRole === "local_authored_trigger_volume_event"
                        ? "local authored trigger-volume event; no server request or response"
                      : row.networkRole === "local_entity_property_event"
                        ? "local entity-property event; no packet join proven"
                      : row.networkRole === "reads_synchronized_local_mission_state"
                        ? "reads the synchronized local MissionSystem cache; this gate sends no request and expects no direct response"
                      : row.networkRole === "local_narrative_mission_state_context"
                        ? "the FX gate reads synchronized local mission state; ClientCollectNarrative is local, while _CollectNarrative may separately request interaction (exact protocol reply not proven)"
                      : row.networkRole === "local_authored_segment_context"
                        ? "local authored NPC-proxy segment identity; no server request or response"
                      : row.networkRole === "local_client_only_guide_group_context"
                        ? "local client-only guide completion route; CS_COMPLETE_GUIDE_GROUP is skipped"
                      : row.networkRole === "local_npc_patrol_runtime_event"
                        ? "local NPC patrol checkpoint event; no client request, server push, or expected reply"
              : "local presentation; no server exchange")
        : "",
      (row.timelines || []).length ? `Timeline ${(row.timelines || []).join(", ")}` : "",
      (row.rootPaths || []).length ? `root ${(row.rootPaths || []).join(", ")}` : "",
      row.storyOwnerMission ? `Story owner ${row.storyOwnerMission}` : "",
      row.occurrenceCount ? `occurrences ${row.occurrenceCount}` : "",
      row.allOccurrenceCount && row.allOccurrenceCount !== row.occurrenceCount ? `all occurrences ${row.allOccurrenceCount}` : "",
      row.hasUnscopedOccurrences ? "some occurrences remain unscoped" : "",
      row.hasUnscopedOrOtherMissionOccurrences ? "some occurrences have other or unresolved mission scope" : "",
      row.levelDataHostStatus ? `LevelData host ${row.levelDataHostStatus}` : "",
      (row.scopeEvidenceKinds || []).length ? `scope ${(row.scopeEvidenceKinds || []).join(", ")}` : "",
      row.questTriggerStatus ? `quest trigger ${row.questTriggerStatus}` : "",
      row.orderStatus ? `order boundary ${row.orderStatus}` : "",
      row.nativeMappingId ? `mapping ${row.nativeMappingId}` : "",
      row.acceptModeType ? row.acceptModeType : "",
      (row.anchors || []).length ? `anchor ${(row.anchors || []).join(", ")}` : "",
      (row.edgeKinds || []).length ? `edge ${(row.edgeKinds || []).join(", ")}` : "",
      (row.levelIds || []).length ? `level ${(row.levelIds || []).join(", ")}` : "",
      (row.levelNums || []).length ? `level number ${(row.levelNums || []).join(", ")}` : "",
      (row.missionAreaIds || []).length ? `area ${(row.missionAreaIds || []).join(", ")}` : "",
      row.triggerVolumeType ? `trigger volume ${row.triggerVolumeType}` : "",
      row.triggerVolumeOffset !== undefined ? `trigger volume offset ${row.triggerVolumeOffset}` : "",
      row.triggerShapeOffset !== undefined ? `trigger shape offset ${row.triggerShapeOffset}` : "",
      row.triggerShape ? `Leader trigger shape ${JSON.stringify(row.triggerShape)}` : "",
      row.missionAreaShape ? `MissionArea shape ${JSON.stringify(row.missionAreaShape)}` : "",
      (row.subDataParentIds || []).length ? `sub-data roots ${(row.subDataParentIds || []).join(", ")}` : "",
      (row.conditionTypes || []).length ? `condition type ${(row.conditionTypes || []).join(", ")}` : "",
      (row.objectiveConditionTypes || []).length ? `objective condition ${(row.objectiveConditionTypes || []).join(", ")}` : "",
      (row.levelDataFiles || []).length ? `LevelData ${(row.levelDataFiles || []).join(", ")}` : "",
      (row.levelDataDictionaryEntryCounts || []).length ? `LevelData script entries ${(row.levelDataDictionaryEntryCounts || []).join(", ")}` : "",
      (row.authoritativeScopeKinds || []).length ? `authoritative mission scope ${(row.authoritativeScopeKinds || []).join(", ")}` : "",
      (row.anchorQuestIds || []).length ? `scope anchor quests ${(row.anchorQuestIds || []).join(", ")}` : "",
      (row.anchorScriptIds || []).length ? `scope anchor scripts ${(row.anchorScriptIds || []).join(", ")}` : "",
      (row.interactiveTableSourceFiles || []).length ? `InteractiveTable ${(row.interactiveTableSourceFiles || []).join(", ")}` : "",
      (row.missionAreaSourceFiles || []).length ? `mission-area source ${(row.missionAreaSourceFiles || []).join(", ")}` : "",
      (row.producerSourceFiles || []).length ? `producer source ${(row.producerSourceFiles || []).join(", ")}` : "",
      (row.sourceFiles || []).length ? `source ${(row.sourceFiles || []).join(", ")}` : "",
    ].filter(Boolean);
  }

  function storyTriggerRoutes(row, questId = "") {
    const manifest = state.index?.storyCoverage?.storyTriggerManifest || {};
    const routes = (manifest[row?.key]?.routes || []).filter((route) => route && route.storyKey === row?.key);
    if (!routes.length) return [];
    const missionId = String(state.missionId || state.mission?.mission?.id || "");
    const exact = routes.filter((route) => (
      (!missionId || route.missionId === missionId)
      && (!questId || route.questId === questId)
      && (!row.relation || route.relation === row.relation)
    ));
    if (exact.length) return exact;
    const scoped = routes.filter((route) => (
      (!missionId || route.missionId === missionId)
      && (!questId || !route.questId || route.questId === questId)
    ));
    return scoped.length ? scoped : routes;
  }

  function storyPlaybackRejections(row) {
    const manifest = state.index?.storyCoverage?.storyTriggerManifest || {};
    return (manifest[row?.key]?.rejectedPlaybackCandidates || [])
      .filter((candidate) => candidate && candidate.storyKey === row?.key);
  }

  const exactBlackCarrierRelations = new Set([
    "timeline_dialog_contains_black",
    "dialog_tree_narrative_action",
  ]);
  const exactSameMissionRuntimeRelations = new Set([
    "airwall_mission_state_radio_playback_context",
    "leveldata_levelscript_mission_context",
  ]);
  const exactNpcProxyRuntimeRelations = new Set([
    "npc_proxy_ex_mission_context",
    "npc_proxy_tracking_dialog_navigation_context",
    "npc_proxy_lazy_destroy_dialog_context",
  ]);
  const exactConnectedContextRelations = new Set([
    "dialog_tree_reachable_story_playback",
    "levelscript_quest_state_gate",
  ]);

  function runtimeRecoveryEvidenceLabel(row) {
    const status = row?.evidenceKind || row?.recoveryStatus || "";
    return ({
      closed_exact_same_mission_leveldata_playback_context_no_relative_order:
        t("runtimeRecoveryEvidenceSameMissionLevelDataPlayback"),
      closed_exact_cross_mission_leveldata_playback_context_no_relative_order:
        t("runtimeRecoveryEvidenceCrossMissionLevelDataPlayback"),
      closed_exact_parent_dialog_dependency_no_relative_order:
        t("runtimeRecoveryParentDialogDependency"),
      closed_exact_non_owning_dialog_context_no_relative_order:
        t("runtimeRecoveryNpcDialogContext"),
      closed_exact_runtime_config_no_relative_order:
        t("runtimeRecoveryNpcSelectionContext"),
      closed_exact_cross_mission_runtime_config_no_relative_order:
        t("runtimeRecoveryNpcCrossMissionContext"),
      closed_exact_multi_mission_runtime_config_no_relative_order:
        t("runtimeRecoveryNpcMultiMissionContext"),
      closed_exact_lua_controller_playback_no_mission_owner_or_relative_order:
        t("runtimeRecoveryEvidenceLuaControllerPlayback"),
      closed_exact_composed_root_playback_context_no_relative_order:
        t("relationRootPlaybackAliasComposed"),
      closed_exact_connected_dialog_tree_playback_context_no_relative_order:
        t("runtimeRecoveryEvidenceDialogTreePlaybackContext"),
      closed_exact_quest_state_gated_playback_context_no_relative_order:
        t("runtimeRecoveryEvidenceQuestStateGate"),
      cutscene_root_playable_alias_without_recovered_activator:
        t("offlineRecoveryEvidenceCutsceneAlias"),
    })[status] || status;
  }

  function offlineRecoveryHtml(row) {
    const coverage = state.index?.storyCoverage || {};
    const manifest = coverage.storyTriggerManifest || {};
    const overlay = coverage.offlineRecoveryEvidence?.storyTriggerManifestOverlay || {};
    const offlineRecovery = (
      manifest[row?.key]?.offlineRecovery
      || overlay[row?.key]?.offlineRecovery
    );
    const partialRecovery = (
      manifest[row?.key]?.partialRecovery
      || overlay[row?.key]?.partialRecovery
    );
    const runtimeRecovery = manifest[row?.key]?.runtimeContextRecovery;
    const contentProvenance = (
      manifest[row?.key]?.contentProvenance
      || overlay[row?.key]?.contentProvenance
    );
    const recovery = offlineRecovery || partialRecovery || runtimeRecovery || contentProvenance;
    if (!recovery || recovery.graphEffect !== "none") return "";
    const sourceFiles = [...new Set([
      ...(recovery.definitionSourceFiles || []),
      ...(recovery.sourceFiles || []),
      ...(recovery.originalBinaryFiles || []),
      ...(recovery.originalGameFiles || []),
    ].filter(Boolean))];
    const related = recovery.missionRelatedOriginalData;
    const relatedEntries = (related?.entries || []).map((entry) => (
      `<code>#${esc(entry.order)} ${esc(entry.contentId || "?")} / ${esc(entry.prtsId || "?")}</code>`
    )).join(" ");
    const relatedSources = (related?.sourceFiles || []).map((path) => `<code>${esc(path)}</code>`).join("<br>");
    const nativePaths = [
      ...(recovery.nativeEventPaths || []),
      ...(recovery.nativePaths || []),
    ].map((path) => {
      const header = path?.headerName || path?.eventName || path?.eventDetail?.type || "?";
      const actions = (path?.path || path?.steps || []).map((step) => step?.actionName || step?.recordClass).filter(Boolean);
      return `<code>${esc([header, ...actions].join(" → "))}</code>`;
    }).join("<br>");
    const runtimeDetails = runtimeRecovery ? [
      recovery.relation === "lua_controller_playback"
        ? `<small><strong>${esc(t("runtimeRecoveryLuaController"))}:</strong> <code>${esc(recovery.luaFile || "?")}</code>${recovery.luaLine ? `:${Number(recovery.luaLine)}` : ""}</small><small><strong>${esc(t("runtimeRecoveryLuaCall"))}:</strong> <code>${esc(recovery.luaCall || "?")}</code></small>`
        : "",
      recovery.nominalStoryMissionId
        ? `<small><strong>${esc(t("runtimeRecoveryNominalMission"))}:</strong> <code>${esc(recovery.nominalStoryMissionId)}</code></small>`
        : "",
      recovery.contextMissionId
        ? `<small><strong>${esc(t("runtimeRecoveryContextMission"))}:</strong> <code>${esc(recovery.contextMissionId)}</code></small>`
        : "",
      (recovery.contextMissionIds || []).length
        ? `<small><strong>${esc(t("runtimeRecoveryContextMissions"))}:</strong> ${(recovery.contextMissionIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>`
        : "",
      (recovery.anchorQuestIds || []).length
        ? `<small><strong>${esc(t("runtimeRecoveryQuestAnchors"))}:</strong> ${(recovery.anchorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>`
        : "",
      recovery.questId
        ? `<small><strong>${esc(t("runtimeRecoveryQuestAnchors"))}:</strong> <code>${esc(recovery.questId)}</code></small>`
        : "",
      recovery.parentStoryKey
        ? `<small><strong>${esc(t("runtimeRecoveryCarrierParents"))}:</strong> <code>${esc(recovery.parentStoryKey)}</code></small>`
        : "",
      recovery.relation === "levelscript_quest_state_gate"
        ? `<small><strong>Gate:</strong> <code>${esc(recovery.conditionType || "?")}(${esc(recovery.conditionComparer || "?")}, ${Number(recovery.conditionQuestState) === 2 ? "Processing" : esc(recovery.conditionQuestState ?? "?")})</code> ${(recovery.eventNames || []).map((id) => `<code>${esc(id)}</code>`).join(" ")} ${(recovery.actionNames || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>`
        : "",
      (recovery.rootStoryKeys || []).length
        ? `<small><strong>${esc(t("runtimeRecoveryPlaybackRoots"))}:</strong> ${(recovery.rootStoryKeys || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>`
        : "",
      nativePaths
        ? `<small><strong>${esc(t("runtimeRecoveryNativePaths"))}:</strong><br>${nativePaths}</small>`
        : "",
      recovery.relation === "sns_authored_mission_link"
        ? `<small><strong>${esc(t("runtimeRecoverySnsLink"))}:</strong> <code>${esc(recovery.missionId || "?")}</code>${(recovery.snsContentIds || []).length ? ` · content ${(recovery.snsContentIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}` : ""}</small>`
        : "",
    ].filter(Boolean).join("") : "";
    const boundaries = [
      runtimeDetails,
      recovery.rootPlaybackAlias
        ? `<small><strong>${esc(t("offlineRecoveryCutsceneAlias"))}:</strong> <code>${esc(recovery.rootPlaybackAlias.rootStoryKey || "?")}</code> &rarr; <code>${esc(recovery.rootPlaybackAlias.playableAssetStoryKey || "?")}</code> · ${esc(t(recovery.cutsceneAliasRole === "cutscene_root" ? "offlineRecoveryCutsceneAliasRootRole" : "offlineRecoveryCutsceneAliasPlayableRole"))}</small>`
        : "",
      recovery.activationBoundary
        ? `<small><strong>${esc(t("runtimeRecoveryActivation"))}:</strong> ${esc(recovery.activationBoundary)}</small>`
        : "",
      recovery.playbackBoundary
        ? `<small><strong>${esc(t("runtimeRecoveryPlayback"))}:</strong> ${esc(recovery.playbackBoundary)}</small>`
        : "",
      recovery.consumerBoundary
        ? `<small><strong>${esc(t("offlineRecoveryConsumer"))}:</strong> ${esc(recovery.consumerBoundary)}</small>`
        : "",
      recovery.contextBoundary
        ? `<small><strong>${esc(t("runtimeRecoveryContextBoundary"))}:</strong> ${esc(recovery.contextBoundary)}</small>`
        : "",
      recovery.orderBoundary
        ? `<small><strong>${esc(t("offlineRecoveryOrder"))}:</strong> ${esc(recovery.orderBoundary)}</small>`
        : "",
      recovery.reopenWhen
        ? `<small><strong>${esc(t("offlineRecoveryReopen"))}:</strong> ${esc(recovery.reopenWhen)}</small>`
        : "",
      partialRecovery
        ? `<small><strong>${esc(t("partialRecoveryCoverage"))}:</strong> ${Number(recovery.coveredLineCount || 0).toLocaleString()} / ${Number(recovery.lineCount || 0).toLocaleString()} ${esc(t("offlineRecoveryLines"))}</small>`
        : "",
      partialRecovery && (recovery.missingLineIds || []).length
        ? `<small><strong>${esc(t("partialRecoveryUnmatchedRows"))}:</strong> ${(recovery.missingLineIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>`
        : "",
      sourceFiles.length
        ? `<small><strong>${esc(t(contentProvenance ? "projectAuthoredSources" : "offlineRecoverySources"))}:</strong><br>${sourceFiles.map((path) => `<code>${esc(path)}</code>`).join("<br>")}</small>`
        : "",
      related
        ? `<small><strong>${esc(t("offlineRecoveryRelatedOriginalData"))}:</strong> <code>${esc(related.groupId || "?")}</code>${related.levelId ? ` · <code>${esc(related.levelId)}</code>` : ""}<br><strong>${esc(t("offlineRecoveryPrtsOrder"))}:</strong> ${relatedEntries}<br><strong>${esc(t("offlineRecoveryStoryRelation"))}:</strong> ${esc(related.storyRelationStatus || "")}<br>${esc(related.orderBoundary || "")}${relatedSources ? `<br>${relatedSources}` : ""}</small>`
        : "",
    ].filter(Boolean).join("");
    return `<div class="mp-playback-rejection mp-offline-recovery">
      <header><strong>${esc(t(contentProvenance ? "projectAuthoredBoundary" : runtimeRecovery ? "runtimeContextRecoveryBoundary" : partialRecovery ? "partialRecoveryBoundary" : "offlineRecoveryBoundary"))}</strong><span>${esc(t("offlineRecoveryNoGraphEdge"))}</span></header>
      <b>${esc(contentProvenance ? t("projectAuthoredEvidence") : partialRecovery ? t("partialRecoveryEvidenceParentTreePartition") : runtimeRecoveryEvidenceLabel(recovery))}</b>
      ${boundaries}
      ${recovery.nativeMappingId ? `<em><code>${esc(recovery.nativeMappingId)}</code></em>` : ""}
    </div>`;
  }

  function offlineRecoveryRowsForMission() {
    const coverage = state.index?.storyCoverage || {};
    const manifest = coverage.storyTriggerManifest || {};
    const overlay = coverage.offlineRecoveryEvidence?.storyTriggerManifestOverlay || {};
    const missionId = String(state.missionId || state.mission?.mission?.id || "");
    const rows = new Map();
    [...Object.values(manifest), ...Object.values(overlay)].forEach((entry) => {
      const offlineRecovery = entry?.offlineRecovery;
      const partialRecovery = entry?.partialRecovery;
      const runtimeRecovery = entry?.runtimeContextRecovery;
      const contentProvenance = entry?.contentProvenance;
      const crossMissionRuntimeRecovery = runtimeRecovery
        && String(runtimeRecovery.nominalStoryMissionId || "") === missionId
        && String(runtimeRecovery.contextMissionId || "") !== missionId;
      const authoredSnsMissionRecovery = runtimeRecovery
        && runtimeRecovery.relation === "sns_authored_mission_link"
        && String(runtimeRecovery.missionId || "") === missionId;
      const composedRootPlaybackRecovery = runtimeRecovery
        && runtimeRecovery.relation === "cutscene_root_playback_alias_composed"
        && String(runtimeRecovery.missionId || "") === missionId;
      const luaControllerPlaybackRecovery = runtimeRecovery
        && runtimeRecovery.relation === "lua_controller_playback"
        && String(entry.nominalMissionId || "") === missionId;
      const exactBlackCarrierRecovery = runtimeRecovery
        && exactBlackCarrierRelations.has(runtimeRecovery.relation)
        && String(runtimeRecovery.nominalStoryMissionId || "") === missionId;
      const exactSameMissionRuntimeRecovery = runtimeRecovery
        && exactSameMissionRuntimeRelations.has(runtimeRecovery.relation)
        && String(runtimeRecovery.missionId || entry.nominalMissionId || "") === missionId;
      const exactNpcProxyRuntimeRecovery = runtimeRecovery
        && exactNpcProxyRuntimeRelations.has(runtimeRecovery.relation)
        && String(runtimeRecovery.missionId || runtimeRecovery.nominalStoryMissionId || entry.nominalMissionId || "") === missionId;
      const exactConnectedContextRecovery = runtimeRecovery
        && exactConnectedContextRelations.has(runtimeRecovery.relation)
        && String(runtimeRecovery.missionId || entry.nominalMissionId || "") === missionId;
      const displayRuntimeRecovery = crossMissionRuntimeRecovery
        || authoredSnsMissionRecovery
        || composedRootPlaybackRecovery
        || luaControllerPlaybackRecovery
        || exactBlackCarrierRecovery
        || exactSameMissionRuntimeRecovery
        || exactNpcProxyRuntimeRecovery
        || exactConnectedContextRecovery;
      const recovery = offlineRecovery || partialRecovery || contentProvenance || (displayRuntimeRecovery ? runtimeRecovery : null);
      if (!entry?.key || !recovery || recovery.graphEffect !== "none") return;
      const owner = String(recovery.missionId || recovery.nominalStoryMissionId || entry.nominalMissionId || "");
      if (owner !== missionId) return;
      rows.set(entry.key, {
        key: entry.key,
        nominalMissionId: entry.nominalMissionId,
        ...recovery,
        runtimeContextRecovery: Boolean(displayRuntimeRecovery),
        partialRecovery: Boolean(partialRecovery),
        contentProvenance: Boolean(contentProvenance),
      });
    });
    return [...rows.values()].sort((a, b) => String(a.key).localeCompare(
      String(b.key),
      undefined,
      {numeric: true},
    ));
  }

  function questAttachmentDiagnostic(node) {
    const rows = state.index?.storyCoverage?.offlineRecoveryEvidence?.questAttachmentDiagnostics || {};
    const row = rows[node?.id];
    return row?.graphEffect === "none" ? row : null;
  }

  function questAttachmentDiagnosticHtml(node) {
    const row = questAttachmentDiagnostic(node);
    if (!row) return "";
    const storyKeys = (row.diagnosticStoryKeys || []).map((key) => `<code>${esc(key)}</code>`).join(" ");
    const sourceFiles = [...new Set([
      ...(row.relatedSourceFiles || []),
      row.sourceFile,
      row.levelScriptFile,
      row.levelDataFile,
    ].filter(Boolean))];
    const sourceFilesHtml = sourceFiles.map((path) => `<code>${esc(path)}</code>`).join("<br>");
    const property = row.propertyRecord && Object.keys(row.propertyRecord).length
      ? row.propertyRecord
      : null;
    const propertyOffset = property?.start ?? property?.recordStart;
    const propertyHtml = property
      ? `<small><strong>${esc(t("questAttachmentDiagnosticProperty"))}:</strong> <code>${esc(property.membership || "")}</code> · offset <code>${esc(propertyOffset == null ? "" : `0x${Number(propertyOffset).toString(16)}`)}</code> · <code>${esc((property.texts || []).join(", "))}</code></small>`
      : "";
    return `<div class="mp-playback-rejection mp-offline-recovery">
      <header><strong>${esc(t("questAttachmentDiagnostic"))}</strong><span>${esc(t("offlineRecoveryNoGraphEdge"))}</span></header>
      <p>${esc(t("questAttachmentDiagnosticHint"))}</p>
      <small><strong>${esc(t("offlineRecoveryConsumer"))}:</strong> ${esc(row.attachmentBoundary || "")}</small>
      <small><strong>${esc(t("offlineRecoveryOrder"))}:</strong> ${esc(row.orderBoundary || "")}</small>
      ${storyKeys ? `<small><strong>${esc(t("questAttachmentDiagnosticStories"))}:</strong> ${storyKeys}</small>` : ""}
      ${row.npcProxyId ? `<small><strong>${esc(t("questAttachmentDiagnosticProxy"))}:</strong> <code>${esc(row.npcProxyId)}</code></small>` : ""}
      ${propertyHtml}
      ${sourceFilesHtml ? `<small><strong>${esc(t("questAttachmentDiagnosticFiles"))}:</strong><br>${sourceFilesHtml}</small>` : ""}
      <small><strong>${esc(t("offlineRecoveryReopen"))}:</strong> ${esc(row.reopenWhen || "")}</small>
      ${row.nativeMappingId ? `<em><code>${esc(row.nativeMappingId)}</code></em>` : ""}
    </div>`;
  }

  function playbackRejectionHtml(candidate) {
    const reason = candidate.reason === "case_sensitive_native_resource_lookup"
      ? t("rejectedPlaybackCaseReason")
      : candidate.reason;
    const provenance = [
      candidate.luaFile,
      candidate.luaCall,
      candidate.auditReport,
    ].filter(Boolean);
    return `<div class="mp-playback-rejection" title="${esc(candidate.auditReport || "")}">
      <header><strong>${esc(t("rejectedPlaybackCandidate"))}</strong><span>${esc(t("rejectedPlaybackBoundary"))}</span></header>
      <div class="mp-trigger-chain">
        <span><small>${esc(t("rejectedPlaybackLiteral"))}</small><code>${esc(candidate.luaLiteral || "?")}</code></span>
        <i aria-hidden="true">&#8603;</i>
        <span><small>${esc(t("rejectedPlaybackStoryKey"))}</small><code>${esc(candidate.storyKey || "?")}</code></span>
      </div>
      <b>${esc(reason || "")}</b>
      ${candidate.note ? `<small>${esc(candidate.note)}</small>` : ""}
      ${provenance.length ? `<em>${provenance.map((value) => `<code>${esc(value)}</code>`).join(" · ")}</em>` : ""}
    </div>`;
  }

  function triggerCausalityLabel(causality) {
    return t(({
      playback: "triggerPlayback",
      condition: "triggerCondition",
      context: "triggerContext",
      context_owner_unresolved: "triggerContextOwnerUnresolved",
      dependency: "triggerDependency",
      playback_owner_unresolved: "triggerUnresolved",
      playback_alias_owner_unresolved: "triggerPlaybackAlias",
      playback_alias_owner_connected: "triggerPlaybackAliasConnected",
      definition_only: "triggerDefinition",
    })[causality] || "triggerContext");
  }

  function triggerStepLabel(kind) {
    return t(({
      quest: "triggerQuest",
      mission: "triggerMission",
      ownership_gap: "triggerOwnershipGap",
      server_message: "triggerServerMessage",
      native_event: "triggerNativeEvent",
      levelscript: "triggerLevelScript",
      leveldata: "triggerLevelData",
      availability_condition: "triggerAvailabilityCondition",
      narrative_interactive: "triggerNarrativeInteractive",
      dialog_definition: "triggerDialogDefinition",
      native_action: "triggerNativeAction",
      parent_story: "triggerParentStory",
      dialog_timeline: "triggerDialogTimeline",
      story_root: "triggerStoryRoot",
      story: "triggerStory",
      luaController: "triggerLuaController",
      nativePlayback: "triggerNativePlayback",
      originalTableRow: "triggerOriginalTableRow",
    })[kind] || "triggerContext");
  }

  function triggerStepValue(step) {
    const values = (step.ids || []).filter(Boolean);
    if (values.length) return values.join(", ");
    return String(step.id || "?");
  }

  function triggerStepHtml(step) {
    const summaries = (step.summaries || []).filter(Boolean);
    return `<span class="is-${esc(step.kind)}">
      <small>${esc(triggerStepLabel(step.kind))}</small>
      <code>${esc(triggerStepValue(step))}</code>
      ${summaries.length ? `<em>${summaries.map(esc).join(" · ")}</em>` : ""}
    </span>`;
  }

  function selectorLabel(key) {
    return String(key || "")
      .replace(/IdFilter$/, " ID")
      .replace(/Id$/, " ID")
      .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
      .replace(/^./, (value) => value.toUpperCase());
  }

  function selectorValue(value) {
    if (Array.isArray(value)) return value.join(", ");
    if (value && typeof value === "object") return JSON.stringify(value);
    return String(value);
  }

  function nativePathHtml(path) {
    const actions = (path.steps || []).filter(Boolean);
    const selectorEntries = Object.entries(path.selector || {}).filter(([key, value]) => (
      value !== null
      && value !== undefined
      && !["levelId", "listenerHeaderLocalId", "listenerScriptId"].includes(key)
    ));
    const transportLabel = path.serverExchange === true
      ? t("triggerServerTransport")
      : path.serverExchange === false
        ? t("triggerLocalTransport")
        : t("triggerUnknownTransport");
    const listenerId = path.scriptId || path.selector?.listenerScriptId || "?";
    const listenerMeta = [
      path.levelId,
      path.headerLocalId !== null && path.headerLocalId !== undefined ? `header #${path.headerLocalId}` : "",
    ].filter(Boolean).join(" · ");
    return `<div class="mp-trigger-event-path ${path.serverExchange === true ? "is-server" : path.serverExchange === false ? "is-local" : "is-unknown"}" title="${esc(path.sourceFile || "")}">
      <div class="mp-trigger-event-node">
        <small>${esc(t("triggerNativeEvent"))}</small>
        <code>${esc(path.eventName || "?")}</code>
        ${path.eventSummary ? `<strong>${esc(path.eventSummary)}</strong>` : ""}
        ${selectorEntries.length ? `<div class="mp-trigger-selector">${selectorEntries.map(([key, value]) => `<span><b>${esc(selectorLabel(key))}</b>${esc(selectorValue(value))}</span>`).join("")}</div>` : ""}
        <em>${esc(transportLabel)}${path.transport ? ` · ${esc(path.transport)}` : ""}</em>
      </div>
      <i aria-hidden="true">&rarr;</i>
      <div class="mp-trigger-listener-node">
        <small>${esc(t("triggerListener"))}</small>
        <code>${esc(listenerId)}</code>
        ${listenerMeta ? `<strong>${esc(listenerMeta)}</strong>` : ""}
      </div>
      ${actions.map((step) => {
        const name = step.actionName || step.recordClass || step.edge || "action";
        const meta = [
          step.localId !== null && step.localId !== undefined ? `#${step.localId}` : "",
          step.edge,
          step.unionTag,
        ].filter(Boolean).join(" · ");
        return `<i aria-hidden="true">&rarr;</i><div class="mp-trigger-action-node">
          <small>${esc(t("triggerActionChain"))}</small>
          <code>${esc(name)}</code>
          ${meta ? `<strong>${esc(meta)}</strong>` : ""}
        </div>`;
      }).join("")}
    </div>`;
  }

  function triggerRouteHtml(route) {
    const steps = (route.steps || []).filter((step) => step && step.kind);
    const paths = (route.nativePaths || []).filter(Boolean);
    const producers = (route.nativeCinematicProducerRoutes || []).filter(Boolean);
    const sources = (route.sourceFiles || []).filter(Boolean);
    if (!steps.length) return "";
    return `<div class="mp-trigger-route is-${esc(route.causality || "context")}">
      <header><strong>${esc(t("triggerRoute"))}</strong><span>${esc(triggerCausalityLabel(route.causality))}</span>${route.controlPathCount ? `<b>${esc(route.controlPathCount)} ${esc(t("triggerExactPaths"))}</b>` : ""}</header>
      <div class="mp-trigger-chain">${steps.map((step, index) => `${index ? '<i aria-hidden="true">&rarr;</i>' : ""}${triggerStepHtml(step)}`).join("")}</div>
      ${paths.length ? `<section class="mp-trigger-events"><header><strong>${esc(t("triggerEvents"))}</strong><small>${esc(t("triggerEventsHint"))}</small></header><div>${paths.map(nativePathHtml).join("")}</div></section>` : ""}
      ${producers.length ? `<small><strong>${esc(t("cinematicProducer"))}:</strong> ${producers.map((row) => `<code>${esc(`${row.actionType || "action"}::${row.actionMethod || "?"} -> ${row.producerType || "producer"}::${row.producerMethod || "?"}`)}</code>`).join(" ")}</small>` : ""}
      ${sources.length ? `<small><strong>${esc(t("source"))}:</strong> ${sources.map((source) => `<code>${esc(source)}</code>`).join(" ")}</small>` : ""}
    </div>`;
  }

  function storyConnectionLink(row, className, questId = "") {
    const details = storyConnectionDetails(row);
    const routeHtml = storyTriggerRoutes(row, questId).map(triggerRouteHtml).join("");
    const rejectionHtml = storyPlaybackRejections(row).map(playbackRejectionHtml).join("");
    const offlineHtml = offlineRecoveryHtml(row);
    const evidence = [row.confidence, row.source || row.evidence].filter(Boolean).join(" · ");
    return `<a class="is-${className}" href="${esc(storyHref(row.key))}" title="${esc(`${t("openInStory")} · ${evidence}`)}">
      <span>${esc(storyDisplayKind(row))}</span><code>${esc(row.key)}</code><b aria-hidden="true">→</b>
      <em>${esc(details.join(" · "))}</em>${evidence ? `<small>${esc(evidence)}</small>` : ""}
      ${routeHtml}
      ${rejectionHtml}
      ${offlineHtml}
    </a>`;
  }

  function manifestOwnedStoryRowsForMission() {
    const missionId = String(
      state.missionId || state.mission?.mission?.id || "",
    );
    const manifest = state.index?.storyCoverage?.storyTriggerManifest || {};
    const rows = [];
    Object.values(manifest).forEach((entry) => {
      (entry?.routes || []).forEach((route) => {
        if (
          route?.ownerStatus !== "connected"
          || route.missionId !== missionId
        ) return;
        rows.push({
          key: route.storyKey,
          relation: route.relation,
          direction: route.direction,
          confidence: route.confidence,
          nativeActions: route.actionNames || [],
          nativeEventNames: route.eventNames || [],
          scriptIds: route.scriptIds || [],
          source: (route.sourceFiles || []).join("; "),
        });
      });
    });
    return rows;
  }

  function missionUnassignedStoryKeys() {
    const connectedManifestKeys = new Set(
      manifestOwnedStoryRowsForMission().map((row) => row.key),
    );
    return (state.localized?.flow?.unlinked || [])
      .filter((key) => key && !connectedManifestKeys.has(key));
  }

  function missionStoryConnectionsHtml() {
    const unique = new Map();
    [
      ...(state.localized?.flow?.missionStoryConnections || []),
      ...manifestOwnedStoryRowsForMission(),
    ].filter((row) => row && row.key).forEach((row) => {
      const signature = `${row.key}\u0000${row.relation || ""}`;
      if (!unique.has(signature)) unique.set(signature, row);
    });
    const rows = [...unique.values()];
    if (!rows.length) return "";
    const acceptRows = rows.filter((row) => row.relation === "mission_accept_dialog");
    const contextRows = rows.filter((row) => row.relation !== "mission_accept_dialog");
    return `<details class="mp-mission-story" data-weight="${acceptRows.length ? "strong" : "context"}"${acceptRows.length ? " open" : ""}>
      <summary>${esc(t("missionStoryFiles"))} <span>${rows.length}</span></summary>
      <div class="mp-story-files">
        ${acceptRows.length ? `<section class="mp-story-group is-incoming"><h4>${esc(t("relationMissionAccept"))} <span>${acceptRows.length}</span></h4>${acceptRows.map((row) => storyConnectionLink(row, "incoming")).join("")}</section>` : ""}
        ${contextRows.length ? `<section class="mp-story-group is-context"><h4>${esc(t("storyContext"))} <span>${contextRows.length}</span></h4>${contextRows.map((row) => storyConnectionLink(row, "context")).join("")}</section>` : ""}
      </div>
      <small>${esc(t("missionStoryHint"))}</small>
    </details>`;
  }

  function missionStateDependenciesHtml() {
    const rows = (state.localized?.flow?.missionStateStoryDependencies || [])
      .filter((row) => row && row.key);
    if (!rows.length) return "";
    return `<details class="mp-mission-story mp-runtime-bindings mp-state-dependencies" data-weight="context">
      <summary>${esc(t("missionStateDependencies"))} <span>${rows.length}</span></summary>
      <div class="mp-story-files"><section class="mp-story-group is-context">
        ${rows.map((row) => storyConnectionLink(row, "context")).join("")}
      </section></div>
      <small><strong>${esc(t("missionStateDependencyBoundary"))}.</strong> ${esc(t("missionStateDependenciesHint"))}</small>
    </details>`;
  }

  function nativeRuntimeBindingsHtml() {
    const rows = (state.mission?.mission?.nativeRuntimeBindings || []).filter((row) => row && row.subGameId && row.bindScriptId);
    if (!rows.length) return "";
    return `<details class="mp-mission-story mp-runtime-bindings mp-subgame-bindings" data-weight="strong" open>
      <summary>${esc(t("subGameBindings"))} <span>${rows.length}</span></summary>
      <div class="mp-runtime-binding-grid">${rows.map((row) => { const network = row.networkIdentity || {}; return `<article>
        <header><code>${esc(row.subGameId)}</code><b>${esc(row.confidence || "typed_original_data")}</b></header>
        <p><span>${esc(t("subGameScript"))}</span><code>${esc(row.bindScriptId)}</code></p>
        <p><span>${esc(t("subGameMode"))}</span><code>${esc(row.modeId || row.runtimeType || "—")}</code></p>
        <p><span>${esc(t("subGameNetworkKey"))}</span><code>${esc(network.authoredKeyField || "gameId")}=${esc(network.authoredKeyValue || row.subGameId)}</code></p>
        <div class="mp-runtime-protocol">
          <p class="is-send"><span>C → S · ${esc(t("subGameStartSend"))}</span><code>${esc(network.startRequest || "CS_GAME_MECHANICS_REQ_START")}</code></p>
          <p class="is-return"><span>S → C · ${esc(t("subGameStartReturn"))}</span><code>${esc(network.enterPush || "SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST")} → ${esc(network.challengeStartPush || "SC_GAME_MECHANICS_SYNC_CHALLENGE_START")}</code></p>
          <p class="is-return"><span>S → C · ${esc(t("subGameCompleteReturn"))}</span><code>${esc(network.challengeCompletePush || "SC_GAME_MECHANICS_SYNC_CHALLENGE_COMPLETE")} → ${esc(network.completionRewardPush || "SC_GAME_MECHANICS_SYNC_COMPLETION_REWARD")}</code></p>
          <p class="is-send"><span>C → S · ${esc(t("subGameStopSend"))}</span><code>${esc(network.stopRequest || "CS_GAME_MECHANICS_REQ_STOP")}</code></p>
          <p class="is-return"><span>S → C · ${esc(t("subGameStopReturn"))}</span><code>${esc(network.leavePush || "SC_GAME_MECHANICS_SYNC_LEAVE_GAME_INST")}</code></p>
        </div>
        <small>${esc(row.runtimeType || "")}</small>
        <small><b>${esc(t("subGameLifecycle"))}:</b> ${esc(t("subGameLifecycleHint"))}</small>
      </article>`; }).join("")}</div>
      <small><strong>${esc(t("noStoryBinding"))}.</strong> ${esc(t("subGameBindingsHint"))}</small>
    </details>`;
  }

  // Relations recovered from authored cross-mission state conditions. Only
  // requiresCompleted is precedence; the rest are co-active or exclusive and
  // are rendered in their own groups so they are never read as ordering.
  const MISSION_GRAPH_RELATIONS = [
    ["requiresCompleted", "missionGraphRequiresCompleted", true],
    ["requiresProcessing", "missionGraphRequiresProcessing", false],
    ["abortsOnCompleted", "missionGraphAbortsOnCompleted", false],
    ["unclassified", "missionGraphUnclassified", false],
  ];

  function missionGraphHtml() {
    const graph = state.mission?.missionGraph || {};
    const upstream = graph.upstream || {};
    const downstream = graph.downstream || {};
    const total = MISSION_GRAPH_RELATIONS.reduce(
      (sum, [relation]) =>
        sum + (upstream[relation] || []).length + (downstream[relation] || []).length,
      0,
    );
    if (!total) return "";
    const interleavings = (state.index?.missionGraph?.interleavings || [])
      .filter((row) => (row.missions || []).includes(state.mission?.mission?.id));
    const group = (relation, labelKey, isPrecedence, missions, direction) => {
      if (!missions.length) return "";
      return `<section class="mp-story-group ${isPrecedence ? "is-incoming" : "is-context"}">
        <h4>${esc(t(direction === "upstream" ? "missionGraphUpstream" : "missionGraphDownstream"))} · ${esc(t(labelKey))} <span>${missions.length}</span></h4>
        ${missions.map((id) => {
          const name = missionName(id);
          return `<button class="mp-graph-link" type="button" data-mission="${esc(id)}"><code>${esc(id)}</code>${name && name !== id ? `<b>${esc(name)}</b>` : ""}</button>`;
        }).join("")}
      </section>`;
    };
    const precedenceCount = (upstream.requiresCompleted || []).length + (downstream.requiresCompleted || []).length;
    return `<details class="mp-mission-story mp-mission-graph" data-weight="${precedenceCount ? "strong" : "context"}" open>
      <summary>${esc(t("missionGraph"))} <span>${total}</span></summary>
      <div class="mp-story-files">
        ${MISSION_GRAPH_RELATIONS.map(([relation, labelKey, isPrecedence]) =>
          group(relation, labelKey, isPrecedence, upstream[relation] || [], "upstream"),
        ).join("")}
        ${MISSION_GRAPH_RELATIONS.map(([relation, labelKey, isPrecedence]) =>
          group(relation, labelKey, isPrecedence, downstream[relation] || [], "downstream"),
        ).join("")}
      </div>
      ${interleavings.length ? `<p class="mp-mission-graph-note">${esc(t("missionGraphInterleaving"))}: ${interleavings.map((row) => (row.missions || []).map((id) => `<code>${esc(id)}</code>`).join(" ⇄ ")).join("; ")}</p>` : ""}
      <small>${esc(t("missionGraphHint"))}</small>
    </details>`;
  }

  function envTalkContextHtml() {
    const rows = (state.mission?.envTalkContext || []).filter((row) => row && row.storyKey);
    if (!rows.length) return "";
    // One envTalk file can have several exact navigation/state context paths;
    // list the file once while retaining every typed proxy and switcher join.
    const byKey = new Map();
    rows.forEach((row) => {
      if (!byKey.has(row.storyKey)) {
        byKey.set(row.storyKey, {
          row,
          quests: new Set(),
          proxies: new Set(),
          switcherGroups: new Set(),
          clusters: new Set(),
          levels: new Set(),
          hasTrackedProxy: false,
          hasSwitcherState: false,
        });
      }
      const entry = byKey.get(row.storyKey);
      if (row.questId) entry.quests.add(row.questId);
      (row.questIds || []).forEach((questId) => entry.quests.add(questId));
      if (row.npcProxyId) entry.proxies.add(row.npcProxyId);
      if (row.switcherGroupId) entry.switcherGroups.add(row.switcherGroupId);
      if (row.clusterId) entry.clusters.add(row.clusterId);
      if (row.levelId) entry.levels.add(row.levelId);
      entry.hasTrackedProxy ||= row.relation === "questTrackedNpcProxy";
      entry.hasSwitcherState ||= row.relation === "atmosphericSwitcherStateContext";
    });
    return `<details class="mp-mission-story mp-envtalk-context" data-weight="context">
      <summary>${esc(t("envTalkContext"))} <span>${byKey.size}</span></summary>
      <div class="mp-story-files"><section class="mp-story-group is-context">
        ${[...byKey.values()].map((entry) => {
          const relation = entry.hasTrackedProxy && entry.hasSwitcherState
            ? "env_talk_multiple_context"
            : entry.hasSwitcherState
              ? "env_talk_atmospheric_switcher_state_context"
              : "env_talk_quest_tracked_proxy";
          const sources = [];
          if (entry.proxies.size) {
            sources.push(`NpcProxyTrackingInfo → ${[...entry.proxies].join(", ")}`);
          }
          if (entry.switcherGroups.size) {
            sources.push(
              `AtmosphericNpcSwitcher ${[...entry.switcherGroups].join(", ")} → cluster ${[...entry.clusters].join(", ")}`,
            );
          }
          if (entry.levels.size) sources.push(`level ${[...entry.levels].join(", ")}`);
          return storyConnectionLink({
            key: entry.row.storyKey,
            relation,
            direction: "context",
            confidence: "exact_typed_context",
            questIds: [...entry.quests].sort(),
            source: sources.join(" · "),
          }, "context");
        }).join("")}
      </section></div>
      <small><strong>${esc(t("envTalkContextBoundary"))}.</strong> ${esc(t("envTalkContextHint"))}</small>
    </details>`;
  }

  function nonMissionContentByKey() {
    const rows = state.index?.storyCoverage?.nonMissionContentKeys || [];
    return new Map(rows.filter((row) => row && row.key).map((row) => [row.key, row]));
  }

  function nonMissionContentHtml(rows) {
    if (!rows.length) return "";
    return `<details class="mp-mission-story mp-non-mission-content" data-weight="context">
      <summary>${esc(t("nonMissionContentStory"))} <span>${rows.length}</span></summary>
      <div class="mp-story-files"><section class="mp-story-group is-context">
        ${rows.map((row) => {
          const guideRuntime = row.evidenceKind === "guide_runtime_asset";
          const spaceshipRuntime = [
            "spaceship_dialog_tree",
            "character_profile_voice",
            "spaceship_dialog_definition_without_tree_carrier",
          ].includes(row.evidenceKind);
          const spaceshipDefinitionGap = row.evidenceKind
            === "spaceship_dialog_definition_without_tree_carrier";
          const spaceshipConsumers = [
            ...(row.consumerClasses || []),
            ...(row.characterIds || []),
            ...(row.dialogTreeRoots || []),
          ];
          return storyConnectionLink({
            key: row.key,
            relation: "non_mission_content",
            direction: "context",
            confidence: spaceshipDefinitionGap
              ? "exact_typed_spaceship_definition_gap"
              : spaceshipRuntime
                ? "exact_typed_spaceship_non_mission_content"
              : guideRuntime
                ? "exact_typed_guide_runtime_non_mission_content"
                : "table_backed_non_mission_content",
            source: guideRuntime
              ? `${row.consumerClass} · ${row.actionCount || 0} actions / ${row.assetCount || 0} guide assets`
              : spaceshipRuntime
                ? `${spaceshipConsumers.join(", ")} · ${(row.sourceFiles || []).join("; ")}`
                : `${row.table}.${row.field} (keyed by ${row.keyedBy})`,
            sourceFiles: row.sourceFiles || [],
            nativeMappingId: row.nativeMappingId,
          }, "context");
        }).join("")}
      </section></div>
      <small>${esc(t("nonMissionContentStoryHint"))}</small>
    </details>`;
  }

  function unassignedStoryHtml() {
    const nonMissionContent = nonMissionContentByKey();
    const allKeys = missionUnassignedStoryKeys();
    // Table-proven non-mission content is reported as its own class rather than
    // sitting in the unassigned queue: no mission can ever own those rows.
    const nonMissionRows = allKeys
      .filter((key) => nonMissionContent.has(key))
      .map((key) => nonMissionContent.get(key));
    const keys = allKeys.filter((key) => !nonMissionContent.has(key));
    if (!keys.length) return nonMissionContentHtml(nonMissionRows);
    const nativePlaybackByKey = new Map(
      (state.localized?.flow?.unlinkedNativePlayback || [])
        .filter((row) => row && row.key)
        .map((row) => [row.key, row]),
    );
    const timelineContainmentByKey = new Map(
      (state.localized?.flow?.unlinkedTimelineContainment || [])
        .filter((row) => row && row.key)
        .map((row) => [row.key, row]),
    );
    const dialogTreeContainmentByKey = new Map(
      (state.localized?.flow?.unlinkedDialogTreeNarrativeActions || [])
        .filter((row) => row && row.key)
        .map((row) => [row.key, row]),
    );
    const definitionOnlyByKey = new Map(
      (state.localized?.flow?.unlinkedDefinitionOnly || [])
        .filter((row) => row && row.key)
        .map((row) => [row.key, row]),
    );
    return `<details class="mp-mission-story mp-unassigned-story" data-weight="context">
      <summary>${esc(t("unassignedStory"))} <span>${keys.length}</span></summary>
      <div class="mp-story-files"><section class="mp-story-group is-context">
        ${keys.map((key) => {
          const nativeRow = nativePlaybackByKey.get(key);
          const timelineRow = timelineContainmentByKey.get(key);
          const dialogTreeRow = dialogTreeContainmentByKey.get(key);
          const containmentRow = dialogTreeRow || timelineRow;
          const evidenceRow = containmentRow ? {
            ...(nativeRow || {}),
            ...containmentRow,
            nativeActions: nativeRow?.nativeActions || [],
            opcodes: nativeRow?.opcodes || [],
            nativeMappingId: nativeRow?.nativeMappingId || "",
            source: [containmentRow.source, nativeRow?.source].filter(Boolean).join("; "),
          } : (nativeRow || definitionOnlyByKey.get(key));
          return storyConnectionLink(evidenceRow || {
            key,
            relation: "unassigned_story",
            direction: "context",
            confidence: "unassigned",
            source: t("unassignedStoryHint"),
          }, "context");
        }).join("")}
      </section></div>
      <small>${esc(t("unassignedStoryHint"))}</small>
    </details>${nonMissionContentHtml(nonMissionRows)}`;
  }

  function questTopologyHtml() {
    const topology = state.mission?.questTopology;
    const forks = topology?.forks || [];
    if (!forks.length) return "";
    const semanticFields = state.index?.runtimeContract?.stateUpdateApplicationAudit
      ?.questTopologyFieldConsumers?.questSemanticFields || {};
    const questTypeNames = new Map(
      (semanticFields.questType?.values || []).map((row) => [Number(row.id), row.name]),
    );
    const showModeNames = new Map(
      (semanticFields.showMode?.values || []).map((row) => [Number(row.id), row.name]),
    );
    const structureLabel = (value) => t(({
      main_path_plus_auxiliary: "questForkMainPathAuxiliary",
      all_auxiliary: "questForkAllAuxiliary",
      multiple_main_path_successors: "questForkMultipleMainPath",
      multiple_main_path_plus_auxiliary: "questForkMultipleMainPath",
    })[value] || "questForkStructure");
    const outcomeLabel = (value) => t(({
      reconverging: "questForkReconverging",
      divergent_terminals: "questForkDivergentTerminals",
      mixed_terminal_and_continuing: "questForkMixedTerminal",
      open_divergence: "questForkOpenDivergence",
    })[value] || "questForkOpenDivergence");
    const armHtml = (arm) => {
      const conditions = arm.objectiveConditionTypes || [];
      const guard = arm.failedCondition || null;
      const corridor = arm.siblingExclusiveQuestIds || [];
      const storyEvidence = arm.storyEvidence || [];
      const relatedOriginalFiles = arm.relatedOriginalFiles || [];
      const questTypeName = questTypeNames.get(Number(arm.questType));
      const showModeName = showModeNames.get(Number(arm.showMode));
      return `<section class="mp-quest-fork-arm ${arm.role === "main_path" ? "is-main-path" : "is-auxiliary"}">
        <header><code>${esc(arm.questId || "?")}</code><b>${esc(t(arm.role === "main_path" ? "questForkMainPathArm" : "questForkAuxiliaryArm"))}</b><span>${esc(t(arm.terminal ? "questForkTerminal" : "questForkContinues"))}</span></header>
        <p><code>${esc(t("questForkFlowSort"))}=${Number(arm.flowIndex || 0)}</code>${questTypeName ? `<code>${esc(t("questForkQuestType"))}: ${esc(questTypeName)} (${Number(arm.questType)})</code>` : ""}${showModeName ? `<code>${esc(t("questForkShowMode"))}: ${esc(showModeName)} (${Number(arm.showMode)})</code>` : ""}${arm.mainPathOrder != null ? `<code>mainPath #${Number(arm.mainPathOrder) + 1}</code>` : ""}${(arm.successorQuestIds || []).map((id) => `<code>&rarr; ${esc(id)}</code>`).join(" ")}</p>
        ${corridor.length ? `<div class="mp-quest-fork-corridor"><strong>${esc(t("questForkArmCorridor"))}:</strong>${corridor.map((id) => `<code>${esc(id)}</code>`).join(" ")}</div>` : ""}
        ${conditions.length ? `<p><strong>${esc(t("questForkObjectiveConditions"))}:</strong>${conditions.map((name) => `<code>${esc(name)}</code>`).join(" ")}</p>` : ""}
        ${guard ? `<div class="mp-quest-fork-guard"><strong>${esc(t("questForkGuardedArm"))}:</strong>${renderConditionTree(guard)}</div>` : ""}
        ${storyEvidence.length ? `<details class="mp-quest-fork-story"><summary>${esc(t("questForkArmStoryEvidence"))} <span>${storyEvidence.length}</span></summary>${storyEvidence.map((row) => `<div><a href="${esc(storyHref(row.key || ""))}"><code>${esc(row.key || "?")}</code></a><code>${esc(row.questId || "?")}</code><b>${esc(row.relation || row.confidence || "typed relation")}</b><small>${esc([row.confidence, row.actionType, row.conditionType, row.direction].filter(Boolean).join(" · "))}</small></div>`).join("")}</details>` : ""}
        ${relatedOriginalFiles.length ? `<details class="mp-quest-fork-files"><summary>${esc(t("questForkArmOriginalFiles"))} <span>${relatedOriginalFiles.length}</span></summary>${relatedOriginalFiles.map((related) => `<small><code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("")}</details>` : ""}
        ${(corridor.length || storyEvidence.length) ? `<small class="mp-quest-fork-arm-boundary">${esc(arm.storyEvidenceBoundary || arm.corridorEvidenceBoundary || t("questForkArmEvidenceBoundary"))}</small>` : ""}
      </section>`;
    };
    const serverApplicationHtml = (fork) => {
      const stateContract = fork.serverQuestStateApplication || null;
      const enableContract = fork.serverQuestEnableApplication || null;
      if (!stateContract && !enableContract) return "";
      const message = stateContract?.message || enableContract?.message || {};
      const transitions = stateContract?.transitions || [];
      const enableMessage = enableContract?.message || {};
      const enableRoutes = enableContract?.routes || [];
      const enableField = enableMessage.consumedControlFields?.[0] || "isEnable";
      const pauseField = enableContract?.runtimeControl?.field || "isPaused";
      const identities = (fork.arms || [])
        .map((arm) => arm.serverApplicationIdentity)
        .filter(Boolean);
      const files = stateContract?.relatedOriginalFiles || enableContract?.relatedOriginalFiles || [];
      return `<article class="mp-order-branch is-boundary mp-quest-server-application">
        <header><strong>${esc(t("questForkServerApplication"))}</strong><code>${esc(message.type || "?")} #${Number(message.messageId || 0)}</code></header>
        <p><strong>${esc(t("questForkPacketShape"))}:</strong> <code>${esc(message.identityField || "questId")}</code> <code>${esc(message.stateField || "questState")}</code>${(message.successorLikeFields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</p>
        <p>${identities.map((identity) => `<code>${esc(identity.field || "questId")}=${esc(identity.value || "?")}</code>`).join(" ")}</p>
        <p><strong>${esc(t("questForkStateTransitions"))}:</strong> ${transitions.map((route) => `<code>${esc(route.stateName || "?")} (${Number(route.state)}) &rarr; ${(route.reachableLifecycleCalls || []).map((call) => esc(call.method || "?")).join(" + ")}</code>`).join(" ")}</p>
        <code>${esc(message.handler?.symbol || "")}${message.handler?.va ? ` @ ${esc(message.handler.va)}` : ""}</code>
        <p>${esc(t("questForkServerApplicationHint"))}</p>
        ${enableContract ? `<section class="mp-quest-enable-routes"><strong>${esc(t("questForkEnableApplication"))}</strong><p>${enableRoutes.map((route) => {
          const values = route.values || {};
          const calls = (route.reachableLifecycleCalls || []).map((call) => call.method || "?").join(" + ");
          return `<code>${esc(`${enableField}=${String(values[enableField])} / ${pauseField}=${String(values[pauseField])} → ${calls}`)}</code>`;
        }).join(" ")}</p><code>${esc(enableMessage.handler?.symbol || "")}${enableMessage.handler?.va ? ` @ ${esc(enableMessage.handler.va)}` : ""}</code>${(enableMessage.unreadControlFields || []).length ? `<p><strong>${esc(t("questForkUnreadControls"))}:</strong> ${(enableMessage.unreadControlFields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</p>` : ""}<p>${esc(t("questForkEnableApplicationHint"))}</p></section>` : ""}
        ${files.length ? `<details class="mp-quest-fork-files"><summary>${esc(t("relatedOriginalFile"))} <span>${files.length}</span></summary>${files.map((related) => `<small><code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("")}</details>` : ""}
        <small>${esc(t("questForkServerApplicationBoundary"))}</small>
      </article>`;
    };
    return `<details class="mp-mission-story mp-quest-topology" data-weight="strong" open>
      <summary>${esc(t("questForkStructure"))} <span>${forks.length}</span></summary>
      <p>${esc(t("questForkStructureHint"))}</p>
      <div class="mp-quest-fork-list">${forks.map((fork) => `<details class="mp-quest-fork-detail"><summary><code>${esc(fork.questId || "?")}</code><i>&rarr;</i>${(fork.successorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}<b>${esc(structureLabel(fork.structure))}</b><b>${esc(outcomeLabel(fork.outcome))}</b></summary>
        ${serverApplicationHtml(fork)}
        <div class="mp-quest-fork-arms">${(fork.arms || []).map(armHtml).join("")}</div>
        ${fork.firstCommonDescendant ? `<p><strong>${esc(t("questForkReconverges"))}:</strong><code>${esc(fork.firstCommonDescendant.questId || "?")}</code>${Object.entries(fork.firstCommonDescendant.distanceByArm || {}).map(([id, distance]) => `<code>${esc(id)} +${Number(distance)}</code>`).join(" ")}</p>` : ""}
        <small>${esc(t("questForkServerPolicy"))}</small>
        ${(fork.relatedOriginalFiles || []).map((related) => `<small><strong>${esc(t("relatedOriginalFile"))}:</strong> <code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("")}
        <small>${esc(fork.evidenceBoundary || topology.evidenceBoundary || "")}</small>
      </details>`).join("")}</div>
    </details>`;
  }

  function storyOrderHtml() {
    const order = state.mission?.storyOrder;
    if (!order?.summary) return "";
    const summary = order.summary;
    const components = new Map((order.components || []).map((row) => [row.id, row]));
    const directEdges = order.directEdges || [];
    const missionObservedContexts = (order.missionObservedLevelScriptContexts || []).map((row) => {
      const stories = (row.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ");
      const conditions = (row.conditionTypes || []).map((name) => `<code>${esc(name)}</code>`).join(" ");
      const properties = (row.propertyKeys || []).map((name) => `<code>${esc(name)}</code>`).join(" ");
      const files = (row.relatedOriginalFiles || []).map((related) => `<small><code>${esc(related.kind || "file")}</code> <code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("");
      return `<article class="mp-order-branch is-boundary"><header><code>${esc(row.questId || "?")}</code><i>&rarr;</i><code>${esc(row.levelId || "?")} / ${esc(row.scriptId || "?")}</code><i>&harr;</i>${stories}</header><p>${conditions}${properties ? ` <strong>${esc(t("observedProperties"))}:</strong> ${properties}` : ""}</p><small><strong>${esc(t("propertyWriterUnresolved"))}</strong> ${esc(row.evidenceBoundary || "")}</small>${files ? `<details><summary>${esc(t("relatedOriginalFile"))} <span>${(row.relatedOriginalFiles || []).length}</span></summary>${files}</details>` : ""}</article>`;
    }).join("");
    const componentHtml = (componentId) => {
      const component = components.get(componentId) || {id: componentId, sceneKeys: []};
      const files = (component.sceneKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join("");
      return `<span class="mp-order-component${component.cyclic ? " is-cycle" : ""}"><b>${esc(component.id)}</b>${files}</span>`;
    };
    const causalEdges = (order.reducedComponentEdges || []).map((edge) => {
      const evidenceRows = (edge.evidenceEdgeIndexes || []).map((index) => directEdges[index]).filter(Boolean);
      const evidence = [...new Set(evidenceRows.map((row) => row.kind).filter(Boolean))];
      return `<div class="mp-order-edge">${componentHtml(edge.from)}<i aria-hidden="true">&rarr;</i>${componentHtml(edge.to)}<small>${esc(t("orderEvidence"))}: ${evidence.map((kind) => `<code>${esc(kind)}</code>`).join(" ")}</small></div>`;
    }).join("");
    const frontiers = (order.topologicalLayers || []).map((layer, index) => `<div class="mp-order-frontier"><b>${esc(t("partialFrontier"))} ${index + 1}</b><span>${(layer || []).map(componentHtml).join("")}</span></div>`).join("");
    const branches = order.branches || {};
    const questForkAuthority = branches.questForkAuthority || null;
    const questStartReads = questForkAuthority?.fieldReadCounts || {};
    const topologyConsumers = questForkAuthority?.topologyFieldConsumers || null;
    const semanticFields = topologyConsumers?.questSemanticFields || null;
    const questConsumerCensus = topologyConsumers?.questInfoConsumers || {};
    const topologyConsumerRows = [
      ...(questConsumerCensus.rows || []),
      ...(topologyConsumers?.missionRuntimeConsumers || []),
    ];
    const topologyClassificationLabel = (classification) => ({
      two_value_display_sort_comparator: t("displaySortOnly"),
      deprecated_description_fallback: t("deprecatedDescriptionOnly"),
      level_or_description_context_selection: t("mainPathContextOnly"),
      derived_main_path_membership_cache: t("mainPathCacheOnly"),
      quest_visibility_or_tracker_presentation: t("questVisibilityPresentation"),
      quest_type_query_or_presentation: t("questTypePresentation"),
      post_lifecycle_quest_type_behavior: t("questTypePostLifecycle"),
      post_lifecycle_block_notification: t("questTypeBlockNotification"),
    })[classification] || String(classification || "typed field consumer").replaceAll("_", " ");
    const topologyConsumerFields = (row) => {
      const questReads = Object.entries(row.fieldReads || {}).map(([name, reads]) => `${name}:${(reads || []).length}`);
      const missionAccesses = Object.entries(row.fieldAccesses || {}).map(([name, kinds]) => `${name}:${Object.entries(kinds || {}).map(([kind, accesses]) => `${kind}=${(accesses || []).length}`).join("/")}`);
      return [...questReads, ...missionAccesses];
    };
    const optionalFlag = semanticFields?.optionalObjectiveFlag || null;
    const optionalObservation = optionalFlag?.observation || {};
    const semanticFieldsHtml = semanticFields ? `<section class="mp-quest-semantic-fields"><p><strong>${esc(t("questSemanticFields"))}:</strong> ${(semanticFields.questType?.values || []).map((row) => `<code>${esc(row.name || "?")}=${Number(row.id)}</code>`).join(" ")} ${(semanticFields.showMode?.values || []).map((row) => `<code>${esc(row.name || "?")}=${Number(row.id)}</code>`).join(" ")}</p><p><code>questType consumers=${Number(semanticFields.questType?.consumerCount || 0)}</code> <code>post-lifecycle=${Number(semanticFields.questType?.postLifecycleConsumerCount || 0)}</code> <code>${esc(t("questBlockNotification"))}=${Number(semanticFields.questType?.blockNotificationConsumerCount || 0)}</code> <code>showMode consumers=${Number(semanticFields.showMode?.consumerCount || 0)}</code> <code>lifecycle=${Number(semanticFields.showMode?.lifecycleConsumerCount || 0)}</code></p><p><strong>${esc(t("questEnumComparisons"))}:</strong> ${Object.entries(semanticFields.questType?.comparisonCounts || {}).map(([name, count]) => `<code>${esc(name)}=${Number(count)}</code>`).join(" ")} ${Object.entries(semanticFields.showMode?.comparisonCounts || {}).map(([name, count]) => `<code>${esc(name)}=${Number(count)}</code>`).join(" ")}</p>${optionalFlag ? `<div class="mp-quest-optional-flag"><strong>${esc(t("questOptionalObjectiveFlag"))}</strong><code>${esc(optionalFlag.validation?.status || "unvalidated")}</code>${optionalObservation.objectiveShowDataType ? `<code>${esc(optionalObservation.objectiveShowDataType)}.optional @ ${esc(optionalObservation.optionalFieldOffset || "?")}</code>` : ""}${optionalObservation.caller?.token ? `<code>${esc(optionalObservation.caller.token)} @ ${esc(optionalObservation.caller.va || "?")}</code>` : ""}${optionalObservation.comparison?.readText ? `<code>${esc(optionalObservation.comparison.readText)}</code>` : ""}${optionalObservation.optionalFieldWrite?.text ? `<code>${esc(optionalObservation.optionalFieldWrite.text)}</code>` : ""}<small>${esc(optionalFlag.finding || "")}</small><small>${esc(optionalFlag.boundary || "")}</small></div>` : ""}<small>${esc(semanticFields.finding || t("questSemanticFieldsHint"))}</small><small>${esc(semanticFields.boundary || "")}</small></section>` : "";
    const topologyConsumersHtml = topologyConsumers ? `<section class="mp-topology-consumer-audit">
      <p><strong>${esc(t("wholeClientTopologyConsumers"))}:</strong> <code>${Number(questConsumerCensus.verifiedDirectCallCount || 0)} / ${Number(questConsumerCensus.rawE8CandidateCount || 0)}</code> ${esc(t("verifiedQuestInfoCalls"))} <code>${esc(t("activePredecessorConsumers"))}=${Number(topologyConsumers.activePredecessorConsumerCount || 0)}</code> <code>${esc(t("nonSortFlowConsumers"))}=${Number(topologyConsumers.flowIndexNonSortConsumerCount || 0)}</code> <code>${esc(t("topologyLifecycleCalls"))}=${(topologyConsumers.topologyLifecycleCalls || []).length}</code></p>
      ${topologyConsumerRows.length ? `<details><summary><strong>${esc(t("topologyConsumerMethods"))}</strong> <span>${topologyConsumerRows.length}</span></summary>${topologyConsumerRows.map((row) => `<p><code>${esc(row.caller?.type || "")}.${esc(row.caller?.method || "")}</code> <code>${esc(row.caller?.token || "")}</code> <b>${esc(topologyClassificationLabel(row.classification))}</b>${topologyConsumerFields(row).map((field) => `<code>${esc(field)}</code>`).join(" ")}</p>`).join("")}</details>` : ""}
      ${semanticFieldsHtml}<small>${esc(topologyConsumers.finding || "")}</small><small>${esc(topologyConsumers.boundary || "")}</small>
    </section>` : "";
    const questForkAuthorityHtml = questForkAuthority ? `<details open class="mp-quest-fork-authority"><summary><b>${esc(t("questForkAuthority"))}</b><span>${esc(t("serverSelectedStart"))}</span></summary>
      <p>${esc(questForkAuthority.finding || t("questForkAuthorityHint"))}</p>
      <p><strong>${esc(t("questStartReadEvidence"))}:</strong> <code>objectiveList=${Number(questStartReads.objectiveList || 0)}</code> <code>questType=${Number(questStartReads.questType || 0)}</code> <code>showMode=${Number(questStartReads.showMode || 0)}</code> <code>prevQuestIdList=${Number(questStartReads.prevQuestIdList || 0)}</code> <code>flowIndex=${Number(questStartReads.flowIndex || 0)}</code> <code>topology calls=${(questForkAuthority.topologyTraversalCalls || []).length}</code></p>
      ${questForkAuthority.startQuest?.symbol ? `<p><code>${esc(questForkAuthority.startQuest.symbol)}</code> <code>${esc(questForkAuthority.startQuest.token || "")}</code> <code>${esc(questForkAuthority.startQuest.va || "")}</code></p>` : ""}
      <small>${esc(questForkAuthority.boundary || t("questForkAuthorityHint"))}</small>
      ${topologyConsumersHtml}
      ${(questForkAuthority.relatedOriginalFiles || []).map((related) => `<small><strong>${esc(t("relatedOriginalFile"))}:</strong> <code>${esc(related.sourceFile || "")}</code> / SHA-256 <code>${esc(related.sha256 || "")}</code></small>`).join("")}
    </details>` : "";
    const typedSelectors = (branches.typedStorySelectorGroups || []).map((row) => `<details><summary><b>${esc(t("typedStorySelectors"))}</b> <code>${esc(row.selectorGroupId || "?")}</code></summary><p>${esc(t("typedStorySelectorHint"))}</p>${(row.alternatives || []).map((alternative) => `<div><code>${esc(alternative.role || "?")}</code><i>&rarr;</i><a href="${esc(storyHref(alternative.key))}"><code>${esc(alternative.key || "?")}</code></a></div>`).join("")}${(row.sourceFiles || []).length ? `<small>${row.sourceFiles.map((source) => `<code>${esc(source)}</code>`).join(" ")}</small>` : ""}</details>`).join("");
    const questForks = (branches.questForks || []).map((row) => `<div><b>${esc(t("questFork"))}</b><code>${esc(row.questId || "?")}</code><i>&rarr;</i><span>${(row.successorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>${questForkAuthority ? `<small>${esc(t("serverSelectedStart"))}</small>` : ""}</div>`).join("");
    const questMerges = (branches.questMerges || []).map((row) => `<div><b>${esc(t("questMerge"))}</b><span>${(row.predecessorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span><i>&rarr;</i><code>${esc(row.questId || "?")}</code></div>`).join("");
    const nativeBranchLabel = (kind) => t(kind === "splitFanout" ? "nativeSplitFanout" : kind === "ifElse" ? "nativeIfElseBranch" : "nativeSwitchBranch");
    const nativeParamText = (label, param) => {
      if (!param || typeof param !== "object") return "";
      const source = param.getterLocalId != null
        ? `getter #${param.getterLocalId}`
        : (param.path || (param.paramSource != null ? `source ${param.paramSource}` : ""));
      const value = param.value != null ? String(param.value) : "";
      return [label, source, value].filter(Boolean).join(":");
    };
    const nativeEventDetailHtml = (detail) => {
      if (!detail || typeof detail !== "object" || !Object.keys(detail).length) return "";
      const values = [
        detail.summary,
        detail.eventKey,
        detail.signalId,
        detail.dialogIdFilter,
        detail.triggerSlotIdFilter != null ? `slot ${detail.triggerSlotIdFilter}` : "",
        detail.newStageFilter != null ? `stage ${detail.newStageFilter}` : "",
        detail.questId,
      ].filter(Boolean);
      return `<p class="mp-native-predicate"><b>${esc(t("nativeEventSelector"))}</b>${values.map((value) => `<code>${esc(value)}</code>`).join(" ")}</p>`;
    };
    const nativePredicateHtml = (predicate) => {
      if (!predicate || !Object.keys(predicate).length) return "";
      const compare = predicate.compareMissionState || {};
      const missionState = predicate.sourceGetter?.getMissionState || {};
      const detail = predicate.detail || {};
      const gameCondition = detail.condition || {};
      const sourceDetail = predicate.sourceGetter?.getterInt || {};
      const sourceSemanticDetail = predicate.sourceGetter?.detail || {};
      const details = [
        predicate.getterName || "",
        predicate.getterLocalId != null ? `#${predicate.getterLocalId}` : "",
        predicate.getterUnionTag || "",
        predicate.detailKind || "",
        missionState.missionId || "",
        compare.comparerName || "",
        compare.valueBStateName || "",
        detail.comparerName || detail.operation || "",
        detail.targetKind || "",
        detail.missionOrQuestId || "",
        detail.completedStateName || "",
        detail.genderName || "",
        detail.propertyKey || "",
        gameCondition.type || "",
        gameCondition.fmvId?.value || "",
        gameCondition.key?.value != null ? String(gameCondition.key.value) : "",
        gameCondition.comparerName || "",
        gameCondition.targetValue?.value != null ? String(gameCondition.targetValue.value) : "",
        gameCondition.scriptId?.mode || "",
        gameCondition.scriptId?.scriptId || "",
        gameCondition.value?.value != null ? String(gameCondition.value.value) : "",
        detail.scriptPtr?.mode || detail.targetScript?.mode || "",
        detail.scriptPtr?.scriptId || detail.targetScript?.scriptId || "",
        nativeParamText("A", detail.valueA),
        nativeParamText("B", detail.valueB),
        nativeParamText("min", detail.minimum),
        nativeParamText("max", detail.maximum),
        nativeParamText("value", detail.value),
        detail.expectedStage?.value != null ? `stage ${detail.expectedStage.value}` : "",
        nativeParamText("gender", detail.gender),
        predicate.sourceGetter?.getterName || "",
        predicate.sourceGetter?.detailKind || "",
        nativeParamText("source", sourceDetail.value),
        nativeParamText("source min", sourceSemanticDetail.minimum),
        nativeParamText("source max", sourceSemanticDetail.maximum),
        nativeParamText("value", predicate.param),
        ...(predicate.getterTexts || predicate.texts || []),
        ...(predicate.sourceGetter?.getterTexts || []),
      ].filter(Boolean);
      return `<p class="mp-native-predicate"><b>${esc(t("nativePredicate"))}</b>${details.length ? details.map((value) => `<code>${esc(value)}</code>`).join(" ") : `<span>${esc(t("nativePredicateOpaque"))}</span>`}</p>`;
    };
    const nativeSourcesHtml = (row) => (row.sourceFiles || []).length
      ? `<small><strong>${esc(t("source"))}:</strong> ${(row.sourceFiles || []).map((source) => `<code>${esc(source)}</code>`).join(" ")}</small>`
      : "";
    const relatedOriginalFilesHtml = (row) => (row.relatedOriginalFiles || []).length
      ? `<details><summary>${esc(t("relatedOriginalFile"))} <span>${row.relatedOriginalFiles.length}</span></summary>${row.relatedOriginalFiles.map((related) => `<small><code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("")}</details>`
      : "";
    const nativeTransitionKindLabel = (kind) => t(({
      linear: "nativeStoryTransitionLinear",
      parallelFanout: "nativeStoryTransitionParallel",
      conditionalBranch: "nativeStoryTransitionConditional",
      outcomeBranch: "nativeStoryTransitionOutcome",
      orderedSequence: "nativeStoryTransitionOrdered",
      orderedSequenceExit: "nativeStoryTransitionOrderedExit",
    })[kind] || "nativeStoryTransitionLinear");
    const nativeTransitions = directEdges
      .filter((row) => row.kind === "levelscriptNativeControlPath")
      .map((row) => {
        const kinds = row.transitionKinds || [];
        const evidence = (row.events || []).map((event) => {
          const steps = (event.transitionSteps || []).map((step) => {
            const source = `${step.sourceActionName || step.sourceActionClass || "action"} #${step.sourceLocalId ?? "?"}`;
            const target = `${step.targetActionName || step.targetActionClass || "action"} #${step.targetLocalId ?? "?"}`;
            return `<div><code>${esc(source)}</code><i>&rarr;</i><code>${esc(step.edge || "?")}</code><i>&rarr;</i><code>${esc(target)}</code><b>${esc(nativeTransitionKindLabel(step.transitionKind))}</b>${step.runtimeSemantics === "binary_proven_extra_thread_launch" && step.siblingOrderEvidence === false ? `<b title="${esc(step.runtimeAuthoritySource || "")}">${esc(t("extraThreadSchedulerValidated"))}</b><small>${esc(t("extraThreadSiblingBoundary"))}</small>` : ""}${nativePredicateHtml(step.predicate)}</div>`;
          }).join("");
          return `<section><small><code>${esc(event.levelId || "?")}/${esc(event.scriptId || "?")}#${esc(event.headerLocalId ?? "?")}</code> ${esc(event.eventName || "")}</small>${nativeEventDetailHtml((event.eventDetails || [])[0])}${steps}</section>`;
        }).join("");
        return `<details${row.branchingTransition ? " open" : ""}><summary><a href="${esc(storyHref(row.from))}"><code>${esc(row.from || "?")}</code></a><i>&rarr;</i><a href="${esc(storyHref(row.to))}"><code>${esc(row.to || "?")}</code></a>${kinds.map((kind) => `<b>${esc(nativeTransitionKindLabel(kind))}</b>`).join("")}</summary>${evidence}${nativeSourcesHtml(row)}</details>`;
      }).join("");
    const questSucceedLifecycleEdges = directEdges
      .filter((row) => row.kind === "questSucceedLifecycle")
      .map((row) => {
        const objective = row.objectiveStoryRelation || {};
        const succeed = row.succeedStoryRelation || {};
        const contract = row.nativeLifecycleContract || {};
        const action = (contract.succeedActionCalls || [])[0] || {};
        const questIds = (row.questIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ");
        const relationDetail = [
          objective.conditionType,
          objective.objectiveIndex != null ? `objective ${objective.objectiveIndex}` : "",
          succeed.actionType,
          succeed.actionId != null ? `action #${succeed.actionId}` : "",
        ].filter(Boolean).map((value) => `<code>${esc(value)}</code>`).join(" ");
        const originals = (row.relatedOriginalFiles || []).map((related) => `<small><code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("");
        return `<details open class="mp-quest-succeed-lifecycle"><summary><a href="${esc(storyHref(row.from))}"><code>${esc(row.from || "?")}</code></a><i>&rarr;</i><a href="${esc(storyHref(row.to))}"><code>${esc(row.to || "?")}</code></a></summary><p><b>${esc(t("questSucceedLifecyclePath"))}</b> ${questIds}</p><p>${relationDetail}</p><small><code>${esc(contract.succeedQuest?.symbol || "SucceedQuest")}</code> <code>${esc(contract.succeedQuest?.token || "")}</code> <code>${esc(action.questActionName || "OnSucceedClientAction")}</code></small><small>${esc(contract.boundary || t("questSucceedLifecycleHint"))}</small>${originals ? `<details class="mp-quest-lifecycle-files"><summary>${esc(t("questSucceedLifecycleOriginals"))} <span>${(row.relatedOriginalFiles || []).length}</span></summary>${originals}</details>` : ""}</details>`;
      }).join("");
    const questLifecycleDefinitions = (order.questLifecycleDefinitions || []).map((row) => {
      const originals = (row.relatedOriginalFiles || []).map((related) => `<small><code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("");
      return `<details open class="mp-quest-succeed-lifecycle"><summary><code>${esc(row.questId || "?")}</code><i>&rarr;</i><a href="${esc(storyHref(row.storyKey))}"><code>${esc(row.storyKey || "?")}</code></a><b>${esc(t("questActionStartNoDispatch"))}</b></summary><p><code>${esc(row.actionSlot || "OnStartClientAction")}</code> <code>${esc(row.actionType || "?")} #${esc(row.actionId ?? "?")}</code></p><small>${esc(row.boundary || t("questStartDefinitionsHint"))}</small>${originals ? `<details class="mp-quest-lifecycle-files"><summary>${esc(t("questSucceedLifecycleOriginals"))} <span>${(row.relatedOriginalFiles || []).length}</span></summary>${originals}</details>` : ""}</details>`;
    }).join("");
    const nativeBranches = (branches.nativeControlBranches || []).map((row) => {
      const external = new Set(row.externalStoryKeys || []);
      const boundary = row.crossBoundary
        ? t(row.branchSemantics === "binary_validated_parallel_story_fanout" ? "nativeCrossBoundaryParallelHint" : "nativeCrossBoundaryConditionalHint")
        : "";
      const displayArms = row.fullArms || row.arms || [];
      const armRows = displayArms.map((arm) => {
        const storyLinks = (arm.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>${external.has(key) ? `<b>${esc(t("nativeCrossBoundaryExternal"))}</b>` : ""}`).join(" ");
        const entry = arm.entryAction
          ? `<span><b>${esc(t("nativeArmEntryAction"))}</b> <code>#${esc(arm.entryAction.localId ?? "?")} ${esc(arm.entryAction.actionName || arm.entryAction.recordClass || "?")}</code></span>`
          : "";
        const status = !storyLinks && arm.targetStatus === "exact_active_action"
          ? `<b>${esc(t("nativeNonStoryArm"))}</b>`
          : arm.targetStatus === "inactive_serialized_target"
            ? `<b>${esc(t("nativeInactiveArm"))}</b>`
            : arm.targetStatus === "missing_runtime_action_slot"
              ? `<b>${esc(t("nativeRuntimeTerminalArm"))}</b>`
              : "";
        const exclusive = (arm.exclusiveActions || []).length
          ? `<details><summary>${esc(t("nativeArmExclusiveActions"))}: ${Number(arm.exclusiveActionCount || 0).toLocaleString()}</summary>${(arm.exclusiveActions || []).map((action) => `<code>#${esc(action.localId ?? "?")} ${esc(action.actionName || action.recordClass || "?")}</code>`).join(" ")}</details>`
          : "";
        return `<div><code>${esc(arm.edge || "?")} &rarr; #${esc(arm.entryLocalId ?? "inactive")}</code><span>${storyLinks}${status}</span>${entry}${exclusive}</div>`;
      }).join("");
      const coverage = row.fullArmCoverageStatus === "exact_complete_active_action_map"
        ? `<p><b>${esc(t("nativeFullArmCoverage"))}</b><span>${Number(row.serializedArmCount || 0).toLocaleString()} ${esc(t("nativeSerializedArms"))}</span>${row.nonStoryArmCount ? `<span>${Number(row.nonStoryArmCount).toLocaleString()} ${esc(t("nativeNonStoryArm"))}</span>` : ""}${row.inactiveTargetArmCount ? `<span>${Number(row.inactiveTargetArmCount).toLocaleString()} ${esc(t("nativeInactiveArm"))}</span>` : ""}${row.runtimeTerminalArmCount ? `<span>${Number(row.runtimeTerminalArmCount).toLocaleString()} ${esc(t("nativeRuntimeTerminalArm"))}</span>` : ""}</p>`
        : "";
      const shared = (row.sharedDownstreamActionLocalIds || []).length
        ? `<small><b>${esc(t("nativeSharedDownstream"))}</b> ${(row.sharedDownstreamActionLocalIds || []).map((localId) => `<code>#${esc(localId)}</code>`).join(" ")}</small>`
        : "";
      const fullBoundary = row.fullArmCoverageStatus === "exact_complete_active_action_map"
        ? `<small>${esc(t("nativeFullArmHint"))}</small>`
        : "";
      return `<details${row.crossBoundary ? " open" : ""}><summary><b>${esc(nativeBranchLabel(row.kind))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}#${esc(row.branchLocalId ?? "?")}</code>${row.crossBoundary ? `<b>${esc(t("nativeCrossBoundaryBranch"))}</b>` : ""}</summary><small>${esc(row.eventName || "")}</small>${nativeEventDetailHtml(row.eventDetail)}${nativePredicateHtml(row.predicate)}${row.nativeMappingId ? `<small><code>${esc(row.nativeMappingId)}</code></small>` : ""}${coverage}${armRows}${shared}${fullBoundary}${boundary ? `<small>${esc(boundary)}</small>` : ""}${nativeSourcesHtml(row)}${relatedOriginalFilesHtml(row)}</details>`;
    }).join("");
    const nativeMissionStateBranches = (branches.nativeMissionStateBranches || []).map((row) => {
      const external = new Set(row.externalStoryKeys || []);
      const arms = (row.arms || []).map((arm) => `<div><code>${esc(arm.edge || "?")} &rarr; #${esc(arm.entryLocalId ?? "?")}</code><span>${(arm.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>${external.has(key) ? `<b>${esc(t("nativeMissionStateExternal"))}</b>` : ""}`).join(" ")}</span></div>`).join("");
      return `<details open data-mission-state-branch="${esc(row.missionStateId || "")}"><summary><b>${esc(t("nativeMissionStateBranches"))}</b> <code>${esc(row.missionStateId || "?")}</code> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}#${esc(row.branchLocalId ?? "?")}</code></summary><small>${esc(row.eventName || "")}</small>${nativeEventDetailHtml(row.eventDetail)}${nativePredicateHtml(row.predicate)}${arms}<small>${esc(t("nativeMissionStateBranchesHint"))}</small>${nativeSourcesHtml(row)}${relatedOriginalFilesHtml(row)}</details>`;
    }).join("");
    const nativeMerges = (branches.nativeControlMerges || []).map((row) => `<details><summary><b>${esc(t("nativeControlMerge"))}</b><code>#${esc(row.branchLocalId ?? "?")}</code><i>&rarr;</i><code>#${esc(row.mergeLocalId ?? "?")}</code></summary><small>${esc(row.convergenceStatus === "exact_serialized_downstream_control_convergence" ? t("nativeControlReachability") : row.convergenceStatus || "")}</small><span>${(row.downstreamStoryKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span>${(row.mergePaths || []).map((path) => `<div><b>${esc(t("nativeControlPath"))}</b>${path.map((localId) => `<code>#${esc(localId)}</code>`).join(" &rarr; ")}</div>`).join("")}${nativeSourcesHtml(row)}</details>`).join("");
    const nativeSequences = (branches.nativeOrderedSequences || []).map((row) => `<details open><summary><b>${esc(t("nativeOrderedSequence"))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}#${esc(row.branchLocalId ?? "?")}</code></summary><small>${esc(row.eventName || "")}</small>${(row.arms || []).map((arm, index) => `<div><code>${index + 1}. ${esc(arm.edge || "?")}</code><span>${(arm.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span></div>`).join("")}${(row.nativeConsumers || []).map((consumer) => `<small><code>${esc(consumer.method || "?")} @ ${esc(consumer.address || "?")}</code> ${esc(consumer.contract || "")}</small>`).join("")}${nativeSourcesHtml(row)}</details>`).join("");
    const serializedBranchInventory = state.index?.storyOrder?.nativeSerializedBranchInventory || null;
    const serializedBranchInventorySummary = serializedBranchInventory?.summary || {};
    const missionStoryKeys = new Set((order.nodes || []).map((row) => (
      typeof row === "string" ? row : row?.key
    )).filter(Boolean));
    const serializedBranchInventoryRows = (serializedBranchInventory?.rows || [])
      .filter((row) => (row.playbackStoryKeys || []).some((key) => missionStoryKeys.has(key)));
    const serializedBranchInventoryArmHtml = (row) => (row.arms || []).map((arm) => {
      const playback = (arm.playbackStoryKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ");
      const action = arm.entryAction
        ? `<code>#${esc(arm.entryAction.localId ?? "?")} ${esc(arm.entryAction.actionName || arm.entryAction.recordClass || "?")}</code>`
        : "";
      const actionNames = (arm.reachableActionNames || [])
        .map((name) => `<code>${esc(name)}</code>`).join(" ");
      const recordClasses = (arm.reachableRecordClasses || [])
        .map((name) => `<code>${esc(name)}</code>`).join(" ");
      const semanticSummary = [
        actionNames
          ? `<small>${esc(t("nativeSerializedBranchActions"))}: ${actionNames}</small>`
          : "",
        recordClasses
          ? `<small>${esc(t("nativeSerializedBranchClasses"))}: ${recordClasses}</small>`
          : "",
      ].join("");
      const nestedControlsHtml = (arm.nestedControls || []).map((control) => {
        const nestedArms = (control.arms || []).map((nestedArm) => {
          const nestedPlayback = (nestedArm.playbackStoryKeys || [])
            .map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`)
            .join(" ");
          const nestedNames = (nestedArm.reachableActionNames || [])
            .map((name) => `<code>${esc(name)}</code>`).join(" ");
          const nestedControlRefs = (nestedArm.reachableControlLocalIds || [])
            .map((localId) => `<code>#${esc(localId)}</code>`).join(" ");
          return `<div><code>${esc(nestedArm.edge || "?")} &rarr; #${esc(nestedArm.entryLocalId ?? "inactive")}</code><span>${nestedPlayback || `<small>${esc(nestedArm.targetStatus || "")}</small>`}</span><small>${esc(t("nativeSerializedBranchReachable"))}: ${Number(nestedArm.reachableActionCount || 0).toLocaleString()}${nestedPlayback ? ` / ${esc(t("nativeSerializedNestedPlayback"))}: ${nestedPlayback}` : ""}</small>${nestedNames ? `<small>${esc(t("nativeSerializedBranchActions"))}: ${nestedNames}</small>` : ""}${nestedControlRefs ? `<small>${esc(t("nativeSerializedNestedControlRefs"))}: ${nestedControlRefs}</small>` : ""}</div>`;
        }).join("");
        const detail = control.controlDetail
          ? `<small><code>${esc(JSON.stringify(control.controlDetail))}</code></small>`
          : "";
        const predicate = control.predicate
          ? `<small>${esc(t("nativeSerializedNestedPredicate"))}: <code>${esc(JSON.stringify(control.predicate))}</code></small>`
          : "";
        const nestedPlaybackCount = Number(control.playbackArmCount || 0);
        const nestedPlaybackSummary = nestedPlaybackCount
          ? `<span>${nestedPlaybackCount.toLocaleString()} ${esc(t("nativeSerializedNestedPlaybackArms"))}</span>`
          : "";
        const nestedBranchingSummary = control.branchingStatus === "multi_playback_arms"
          ? `<b>${esc(t("nativeSerializedNestedMultiPlayback"))}</b>`
          : "";
        const nestedPredicateGap = control.playbackPredicateStatus === "unresolved_playback_predicate"
          ? `<b>${esc(t("nativeSerializedNestedPredicateGaps"))}</b>`
          : "";
        return `<details><summary><b><code>#${esc(control.localId ?? "?")} ${esc(control.actionName || control.recordClass || "?")}</code></b><span>${Number(control.serializedArmCount || 0).toLocaleString()} ${esc(t("nativeSerializedNestedArms"))}</span>${nestedPlaybackSummary}${nestedBranchingSummary}${nestedPredicateGap}</summary>${detail}${predicate}${nestedArms}</details>`;
      }).join("");
      const nestedSummary = nestedControlsHtml
        ? `<small>${esc(t("nativeSerializedNestedControls"))}: ${(arm.nestedControls || []).length.toLocaleString()}</small>${nestedControlsHtml}`
        : "";
      return `<div><code>${esc(arm.edge || "?")} &rarr; #${esc(arm.entryLocalId ?? "inactive")}</code><span>${playback || `<small>${esc(arm.targetStatus || "")}</small>`}</span>${action ? `<small>${esc(t("nativeArmEntryAction"))}: ${action}</small>` : ""}<small>${esc(t("nativeSerializedBranchReachable"))}: ${Number(arm.reachableActionCount || 0).toLocaleString()}${playback ? ` / ${esc(t("nativeSerializedBranchArmPlayback"))}: ${playback}` : ""}</small>${semanticSummary}${nestedSummary}</div>`;
    }).join("");
    const serializedBranchInventoryRowsHtml = serializedBranchInventoryRows.map((row) => `<details open><summary><b>${esc(t("nativeSerializedBranchInventory"))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}#${esc(row.branchLocalId ?? "?")}</code><span>${Number(row.serializedArmCount || 0).toLocaleString()} ${esc(t("nativeSerializedBranchArms"))}</span><span>${Number(row.playbackArmCount || 0).toLocaleString()} ${esc(t("nativeSerializedPlaybackArms"))}</span></summary><p>${(row.sourceContexts || []).map((context) => `<code>${esc(context.levelId || "?")}/${esc(context.scriptId || "?")}</code>`).join(" ")}</p>${(row.eventRoots || []).length ? `<small>${esc(t("triggerEvents"))}: ${(row.eventRoots || []).map((event) => `<code>#${esc(event.localId ?? "?")} ${esc(event.headerName || "?")} &rarr; #${esc(event.nextActionLocalId ?? "?")}</code>`).join(" ")}</small>` : ""}${serializedBranchInventoryArmHtml(row)}${row.exit ? `<small><code>${esc(row.exit.edge || "ActionBase.nextId")}</code> &rarr; #${esc(row.exit.entryLocalId ?? "inactive")} <code>${esc(row.exit.targetStatus || "")}</code></small>` : ""}${relatedOriginalFilesHtml(row)}<small>${esc(row.evidenceBoundary || "")}</small></details>`).join("");
    const serializedBranchInventoryHtml = serializedBranchInventory?.schema
      ? `<section class="mp-native-serialized-branch-inventory"><h4>${esc(t("nativeSerializedBranchInventory"))}</h4><p>${esc(t("nativeSerializedBranchInventoryHint"))}</p><div class="mp-order-metrics"><span><b>${Number(serializedBranchInventorySummary.serializedBranchGroupCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedBranchGroups"))}</span><span><b>${Number(serializedBranchInventorySummary.serializedBranchArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedBranchArms"))}</span><span><b>${Number(serializedBranchInventorySummary.playbackArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedPlaybackArms"))}</span><span><b>${Number(serializedBranchInventorySummary.multiPlaybackBranchCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedMultiPlaybackArms"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedControlCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedControls"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedPlaybackArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedPlaybackArms"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedMultiPlaybackControlCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedMultiPlayback"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedPlaybackControlCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedPlaybackControls"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedPlaybackPredicateGapCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedPredicateGaps"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedControlReferenceCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedControlReferences"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedSerializedArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedSlots"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedExactActiveArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedActive"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedInactiveArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedInactive"))}</span><span><b>${Number(serializedBranchInventorySummary.nestedUnavailableArmCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedNestedUnavailable"))}</span><span><b>${Number(serializedBranchInventorySummary.controlPredicateConflictCount || 0).toLocaleString()}</b>${esc(t("nativeSerializedPredicateConflicts"))}</span></div><small><code>${esc(serializedBranchInventory.status || "unavailable")}</code> / ${Number(serializedBranchInventorySummary.sourcePathCount || 0).toLocaleString()} source paths / ${Number(serializedBranchInventorySummary.uniqueContentFileCount || 0).toLocaleString()} unique hashes</small>${serializedBranchInventoryRowsHtml ? `<p><strong>${esc(t("nativeSerializedBranchMatched"))}: ${serializedBranchInventoryRows.length.toLocaleString()}</strong></p><div class="mp-order-branches">${serializedBranchInventoryRowsHtml}</div>` : `<small>${esc(t("nativeSerializedBranchMatched"))}: 0</small>`}${serializedBranchInventory.validationFailures?.length ? `<small>${esc(t("nativeSerializedBranchInventory"))} validation failures: ${serializedBranchInventory.validationFailures.length}</small>` : ""}<small>${esc(serializedBranchInventory.evidenceBoundary || "")}</small></section>`
      : "";
    const relatedActionTopologies = (branches.nativeRelatedActionTopologies || []).map((row) => {
      const selectedEvents = (row.selectedEventRoots || []).map((event) => {
        const metadata = [
          event.priority != null ? `${t("offlineRecoverySubGameActionEventPriority")}: ${event.priority}` : "",
          event.triggerActiveDuring != null ? `${t("offlineRecoverySubGameActionEventTriggerActive")}: ${String(event.triggerActiveDuring)}` : "",
          event.filterMode != null ? `${t("offlineRecoverySubGameActionEventFilter")}: ${event.filterMode}` : "",
        ].filter(Boolean).map((value) => `<small>${esc(value)}</small>`).join("");
        return `<div><code>#${esc(event.localId ?? "?")}</code><b>${esc(event.headerName || event.eventName || "?")}</b><span>&rarr; #${esc(event.nextActionLocalId ?? "?")}</span>${metadata}</div>`;
      }).join("");
      const controls = (row.controlActions || []).map((action) => {
        const shadowed = (action.runtimeShadowedRecordOffsets || []).length
          ? `<small>${(action.runtimeShadowedRecordOffsets || []).length} ${esc(t("offlineRecoverySubGameActionShadowed"))}; ${esc(t("offlineRecoverySubGameActionActiveSlot"))}</small>`
          : "";
        return `<div><code>#${esc(action.localId ?? "?")}</code><b>${esc(action.actionName || "?")}</b><span>${esc(action.controlKind || "")}</span>${shadowed}</div>`;
      }).join("");
      const sequenceContexts = (row.orderedSequenceContexts || []).map((context) => {
        const arms = (context.arms || []).map((arm) => {
          const stories = (arm.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ");
          const observed = Number(arm.observedRouteCount || 0) > 0
            ? `<b>${esc(t("nativeSequenceContextObserved"))}</b>`
            : "";
          return `<div><code>${esc(arm.edge || "?")} &rarr; #${esc(arm.entryLocalId ?? "inactive")}</code><span>${stories || observed || ""}</span></div>`;
        }).join("");
        const reason = context.admissionReason || t("nativeSequenceContextNotAdmitted");
        return `<details open><summary><b>${esc(t("nativeSequenceContext"))}</b> <code>#${esc(context.branchLocalId ?? "?")}</code><span>${Number(context.storyBearingArmCount || 0).toLocaleString()} / ${Number(context.serializedArmCount || 0).toLocaleString()} Story arms</span><b>${esc(t("nativeSequenceContextNotAdmitted"))}</b></summary><small>${esc(reason)}</small>${arms}${(context.nativeConsumers || []).map((consumer) => `<small><code>${esc(consumer.method || "?")} @ ${esc(consumer.address || "?")}</code> ${esc(consumer.contract || "")}</small>`).join("")}</details>`;
      }).join("");
      const terminals = (row.runtimeTerminalTargets || []).map((target) => `<div><code>#${esc(target.sourceLocalId ?? "?")}</code><span>${esc(target.relation || "edge")} &rarr; #${esc(target.targetActionLocalId ?? "?")}</span><small>${esc(t("offlineRecoverySubGameActionTerminals"))}</small></div>`).join("");
      const stories = (row.relatedStoryKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ");
      return `<details><summary><code>${esc(row.sourceFile || "?")}</code><span>${Number(row.eventRootCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionEvents"))}</span>${Number(row.physicalHeaderRecordCount || 0) !== Number(row.eventRootCount || 0) ? `<span>${Number(row.physicalHeaderRecordCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionPhysicalEvents"))}</span>` : ""}<span>${Number(row.actionNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionNodes"))}</span>${Number(row.runtimeShadowedIndexedRecordCount || 0) ? `<span>${Number(row.runtimeShadowedIndexedRecordCount).toLocaleString()} ${esc(t("offlineRecoverySubGameActionShadowed"))}</span>` : ""}${Number(row.runtimeTerminalTargetCount || 0) ? `<span>${Number(row.runtimeTerminalTargetCount).toLocaleString()} ${esc(t("offlineRecoverySubGameActionTerminals"))}</span>` : ""}</summary><p>${stories}</p><p><span>${Number(row.orderedSequenceNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionSequences"))}</span> <span>${Number(row.parallelFanoutNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionFanouts"))}</span> <span>${Number(row.conditionalBranchNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionChoices"))}</span> <span>${Number(row.loopNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionLoops"))}</span></p>${selectedEvents}${sequenceContexts ? `<p><strong>${esc(t("nativeSequenceContext"))}</strong></p><p>${esc(t("nativeSequenceContextHint"))}</p>${sequenceContexts}` : ""}${controls}${terminals}${relatedOriginalFilesHtml(row)}<small>${esc(row.relationshipBoundary || "")}</small></details>`;
    }).join("");
    const sceneOptions = (branches.sceneGraphOptions || []).map((row) => `<div><b>${esc(t("optionBranches"))}</b><a href="${esc(storyHref(row.from))}"><code>${esc(row.from || "?")}</code></a><i>&rarr;</i><span>${(row.arms || []).flatMap((arm) => arm.targets || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span></div>`).join("");
    const dialogConditionalBranches = directEdges.filter((row) => row.kind === "dialogTreeCrossStoryConditionalBranch").map((row) => {
      const condition = row.condition || {};
      const predicate = [
        condition.mapId,
        condition.scriptId != null ? `script ${condition.scriptId}` : "",
        condition.key,
        condition.value != null ? `= ${String(condition.value)}` : "",
      ].filter(Boolean).map((value) => `<code>${esc(value)}</code>`).join(" ");
      const nativeProof = (row.nativeConsumers || []).map((consumer) => `<code>${esc(consumer.method || "?")} ${esc(consumer.token || "")} @ ${esc(consumer.address || "?")}</code>`).join(" ");
      return `<details open><summary><b>${esc(t("dialogConditionalBranch"))}</b> <a href="${esc(storyHref(row.from))}"><code>${esc(row.from || "?")}</code></a> <i>&rarr;</i> <a href="${esc(storyHref(row.to))}"><code>${esc(row.to || "?")}</code></a></summary><p class="mp-native-predicate"><b>${esc(t("nativePredicate"))}</b>${predicate}</p><div><b>${esc(t("dialogConditionalTrueArm"))}</b><code>index ${esc(row.conditionTrueConnectionIndex ?? "?")}</code><span>${(row.childArmLineIds || []).map((lineId) => `<code>${esc(lineId)}</code>`).join(" ")}</span></div><div><b>${esc(t("dialogConditionalFalseArm"))}</b><code>index ${esc(row.conditionFalseConnectionIndex ?? "?")}</code><span>${(row.parentArmLineIds || []).map((lineId) => `<code>${esc(lineId)}</code>`).join(" ")}</span></div><small><strong>${esc(t("dialogConditionalNativeProof"))}:</strong> ${nativeProof}</small><small>${(row.sourceFiles || []).map((source) => `<code>${esc(source)}</code>`).join(" ")}</small></details>`;
    }).join("");
    const dialogOptions = (branches.dialogLineOptions || []).map((row) => `<details><summary><code>${esc(row.storyKey || "?")}</code> 路 ${esc(t("optionBranches"))} ${esc(row.group ?? "?")}</summary>${(row.options || []).map((option) => {
      const branchLines = option.branchLineIds || [];
      const directContinuation = option.directContinuation && option.continuationLineId
        ? `<small>${esc(t("optionDirectContinuation"))}</small> <code>${esc(option.continuationLineId)}</code>`
        : "";
      return `<div><code>${esc(option.optionId || "?")}</code><i>&rarr;</i><span>${branchLines.map((line) => `<code>${esc(line)}</code>`).join(" ")}${directContinuation}</span></div>`;
    }).join("")}</details>`).join("");
    const offlineRows = offlineRecoveryRowsForMission();
    const offlineGaps = offlineRows.map((row) => {
      const timeline = row.sharedTimelineContext?.timeline;
      const lineCount = (row.sharedTimelineContext?.lineIds || []).length;
      const sources = [
        ...(row.sourceFiles || []),
        ...(row.definitionSourceFiles || []),
        ...(row.originalBinaryFiles || []),
        ...(row.originalGameFiles || []),
        ...(row.definitionAssets || []),
        ...(row.definitionTables || []),
        row.definitionTable,
        row.audioMembershipTable,
        row.runtimeRegistry,
        row.npcProxyConsumers?.length ? "NpcProxyExDataTable" : "",
        row.missionNpcProxyTracking?.sourceFile,
        row.missionQuestBranchContext?.sourceFile,
        row.missionQuestSequenceContext?.sourceFile,
        row.missionQuestTopologyContext?.sourceFile,
        ...(row.missionQuestTopologyContext?.objectiveConjunctions || [])
          .flatMap((conjunction) => conjunction.relatedSourceFiles || []),
        ...(row.missionQuestTopologyContext?.levelScriptPlaybackInventories || [])
          .map((inventory) => inventory.sourceFile),
        row.levelScriptTaskConsumer?.sourceFile,
        row.levelDataDialogBranchContext?.levelDataFile,
        row.levelDataDialogBranchContext?.levelScriptFile,
        row.emptyLevelScriptContext?.levelDataFile,
        row.emptyLevelScriptContext?.levelScriptFile,
        row.runtimeTrackingContext?.sourceFile,
        row.nonOwningContext?.sourceFile,
        row.allowedNonOwningRoute?.file,
        row.prtsDefinition?.rowId,
        row.prtsReadingDefinition?.rowId,
        row.summaryDefinition?.summaryId,
        ...(row.missionRelatedOriginalData?.sourceFiles || []),
      ].filter(Boolean);
      const popupRowIds = (row.readingPopupRowIds || []).filter(Boolean);
      const popup = popupRowIds.length
        ? `<p>${popupRowIds.map((rowId) => `<code>ReadingPopUpTable/${esc(rowId)}</code>`).join(" ")}${row.richContentStatus === "absent" ? "" : `<code>RichContentTable/${esc(row.key)}</code>`}</p>`
        : "";
      const optionIds = Array.isArray(row.optionIds) ? row.optionIds : [];
      const branchGroups = Array.isArray(row.dialogTreeBranchGroups)
        ? row.dialogTreeBranchGroups
        : [];
      const terminalOptionGroups = Array.isArray(row.dialogTreeTerminalOptionRoutes)
        ? row.dialogTreeTerminalOptionRoutes
        : [];
      const dialogTreeRoutesRecovered = String(
        row.dialogTreeRouteStatus || "",
      ).startsWith("authored_");
      const options = optionIds.length
        ? `<p><strong>${esc(t(dialogTreeRoutesRecovered ? "offlineRecoveryDefinedOptionsResolved" : "offlineRecoveryDefinedOptions"))}</strong>${optionIds.map((optionId) => `<code>${esc(optionId)}</code>`).join(" ")}</p>`
        : "";
      const printableOnlyTokens = Array.isArray(row.printableOnlyDialogTokens)
        ? row.printableOnlyDialogTokens
        : [];
      const printableTokenBoundary = printableOnlyTokens.length
        ? `<p><strong>${esc(t("offlineRecoveryPrintableTokens"))}</strong>${printableOnlyTokens.map((token) => `<code>${esc(token)}</code>`).join(" ")}</p>`
        : "";
      const internalBranches = branchGroups.length
        ? `<div class="mp-order-dialog-branches"><strong>${esc(t("offlineRecoveryDialogTreeBranches"))}</strong>${branchGroups.map((group) => `<details open><summary><code>#${esc(group.optionGroup ?? "?")}</code> ${esc(t(group.routeKind === "authored_convergence" ? "offlineRecoveryAuthoredConvergence" : "offlineRecoveryAuthoredSplit"))}</summary>${(group.optionIds || []).map((optionId, index) => `<div><code>${esc(optionId)}</code><i>&rarr;</i><code>${esc((group.targetLineIds || [])[index] || "?")}</code></div>`).join("")}</details>`).join("")}</div>`
        : "";
      const terminalOptions = terminalOptionGroups.length
        ? `<div class="mp-order-dialog-branches"><strong>${esc(t("offlineRecoveryTerminalOptions"))}</strong>${terminalOptionGroups.map((group) => `<details open><summary><code>#${esc(group.optionGroup ?? "?")}</code></summary>${(group.routes || []).map((route) => `<div><code>${esc(route.optionId || "?")}</code><i>&rarr;</i><span>${route.finishIdSerialized ? `${esc(t("offlineRecoveryFinishId"))} <code>${esc(route.finishId)}</code>` : esc(t("offlineRecoveryFinishIdAbsent"))}</span></div>`).join("")}</details>`).join("")}</div>`
        : "";
      const recoveredLineCount = Array.isArray(row.lineIds) ? row.lineIds.length : 0;
      const missionTracking = row.missionNpcProxyTracking;
      const missionTrackingContext = missionTracking
        ? `<p><strong>${esc(t("offlineRecoveryMissionTracking"))}</strong>${missionTracking.crossMission ? `<span>${esc(t("offlineRecoveryRuntimeMission"))}: <code>${esc(missionTracking.missionId || "?")}</code></span>` : ""}<code>${esc(missionTracking.proxyId || "?")}</code><code>${esc(missionTracking.levelId || "?")}</code>${(missionTracking.questIds || []).length ? `<span>${esc(t("offlineRecoveryTrackedQuests"))}: ${(missionTracking.questIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" ")}</span>` : ""}</p>`
        : "";
      const npcProxyConsumers = Array.isArray(row.npcProxyConsumers)
        ? row.npcProxyConsumers
        : [];
      const npcProxyConsumerContext = npcProxyConsumers.length
        ? `<p><strong>${esc(t("offlineRecoveryNpcProxyConsumer"))}</strong>${npcProxyConsumers.map((consumer) => {
          const proxyId = consumer.proxyId || consumer.npcProxyId || "?";
          const rowIndex = consumer.entryIndex ?? consumer.activeRowIndex ?? "?";
          const identity = [consumer.npcNameId, consumer.npcId, consumer.levelId].filter(Boolean);
          return `<code>${esc(proxyId)} [index=${esc(rowIndex)}]</code><i>&rarr;</i><code>${esc(consumer.dialogId || row.key || "?")}</code>${identity.length ? `<span>${identity.map((value) => `<code>${esc(value)}</code>`).join(" ")}</span>` : ""}`;
        }).join(" ")}</p>`
        : "";
      const nativeConsumerMethods = Array.isArray(row.nativeConsumerMethods)
        ? row.nativeConsumerMethods
        : [];
      const nativeConsumerContext = nativeConsumerMethods.length
        ? `<p><strong>${esc(t("offlineRecoveryNativeConsumer"))}</strong>${nativeConsumerMethods.map((method) => `<code>${esc(method.method || "?")} ${esc(method.token || "")} @ ${esc(method.address || "?")}</code>${method.selectionField ? `<span>${esc(method.selectionField)}</span>` : ""}`).join(" ")}</p>`
        : "";
      const snsDefinitionContext = row.chatId
        ? `<p><strong>${esc(t("offlineRecoverySnsDefinition"))}</strong><code>${esc(row.chatId)}</code><span>${Number(row.contentCount || 0).toLocaleString()} content</span>${(row.contentParams || []).map((value) => `<code>${esc(value)}</code>`).join(" ")}</p>`
        : "";
      const missionBranch = row.missionQuestBranchContext;
      const missionBranchContext = missionBranch
        ? `<p><strong>${esc(t("offlineRecoveryMissionBranch"))}</strong><code>${esc(missionBranch.fork?.questId || "?")}</code><i>&rarr;</i>${(missionBranch.fork?.successorQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" ")}<span>${(missionBranch.merge?.predecessorQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" ")} &rarr; <code>${esc(missionBranch.merge?.questId || "?")}</code></span></p>`
        : "";
      const missionSequence = row.missionQuestSequenceContext;
      const missionSequenceContext = missionSequence
        ? `<p><strong>${esc(t("offlineRecoveryMissionSequence"))}</strong>${(missionSequence.questSequence || []).map((questId) => `<code>${esc(questId)}</code>`).join('<i>&rarr;</i>')}</p>`
        : "";
      const missionTopology = row.missionQuestTopologyContext;
      const formatObjectiveCondition = (condition) => {
        const host = `${condition.mapId || "?"}/${condition.scriptId ?? "?"}`;
        if (condition.stageValue !== undefined) {
          return `${host}:stage op=${condition.compareOperator ?? "?"} target=${condition.stageValue}`;
        }
        return `${host}:${condition.key || "?"}=${condition.value ?? "?"}`;
      };
      const missionTopologyShape = missionTopology
        ? (((missionTopology.forks || []).length || (missionTopology.merges || []).length)
          ? `${(missionTopology.forks || []).length.toLocaleString()} ${esc(t("questFork"))} / ${(missionTopology.merges || []).length.toLocaleString()} ${esc(t("questMerge"))}`
          : esc(t("offlineRecoveryLinearTopology")))
        : "";
      const missionTopologyContext = missionTopology
        ? `<details><summary><strong>${esc(t("offlineRecoveryMissionTopology"))}</strong> ${missionTopologyShape}</summary><p><strong>${esc(t("offlineRecoveryMainPath"))}</strong>${(missionTopology.mainPathQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join('<i>&rarr;</i>')}</p>${(missionTopology.parallelRendezvous || []).map((join) => `<p><strong>${esc(t("offlineRecoveryParallelRendezvous"))}</strong><code>${esc(join.forkQuestId || "?")}</code><i>&rarr;</i>${(join.parallelQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" + ")}<i>&rarr;</i><code>${esc(join.mergeQuestId || "?")}</code></p>`).join("")}${(missionTopology.objectiveConjunctions || []).map((join) => `<p><strong>${esc(t("offlineRecoveryObjectiveConjunction"))}</strong><code>${esc(join.questId || "?")}</code><span>${(join.subConditions || []).map((condition) => `<code>${esc(formatObjectiveCondition(condition))}</code>`).join(" + ")}</span><small>${esc(t("offlineRecoveryObjectiveConjunctionBoundary"))}</small></p>`).join("")}${(missionTopology.levelScriptPlaybackInventories || []).map((inventory) => `<p><strong>${esc(t("offlineRecoveryLevelScriptPlaybackInventory"))}</strong><span>${esc(t("offlineRecoveryLevelScriptPlaybackPresent"))}: ${(inventory.playbackRecords || []).map((record) => `<code>${esc(record.storyKey || "?")}</code>`).join(" ")}</span><span>${esc(t("offlineRecoveryLevelScriptPlaybackAbsent"))}: ${(inventory.absentStoryKeys || []).map((storyKey) => `<code>${esc(storyKey)}</code>`).join(" ")}</span><small>${esc(t("offlineRecoveryLevelScriptPlaybackBoundary"))}</small></p>`).join("")}${(missionTopology.failedQuestStateGuards || []).map((guard) => `<p><strong>${esc(t("offlineRecoveryQuestFailureGuard"))}</strong><code>${esc(guard.questId || "?")}</code><i>&larr;</i><code>${esc(guard.targetQuestId || "?")} state=${esc(guard.targetQuestState ?? "?")}</code></p>`).join("")}${(missionTopology.failedDialogGuards || []).map((guard) => `<p><strong>${esc(t("offlineRecoveryDialogFailureGuard"))}</strong><code>${esc(guard.questId || "?")}</code><i>&larr;</i><span>${(guard.dialogFinishes || []).map((finish) => `<code>${esc(finish.dialogId || "?")} finish=${esc(finish.finishId ?? "?")}</code>`).join(" " + esc(guard.conditionEvalString || "or") + " ")}</span></p>`).join("")}${(missionTopology.questStateDependencies || []).map((dependency) => `<p><strong>${esc(t("offlineRecoveryQuestStateDependency"))}</strong><code>${esc(dependency.questId || "?")}</code><i>&larr;</i><code>${esc(dependency.targetQuestId || "?")} state=${esc(dependency.targetQuestState ?? "?")}</code>${(dependency.conditionIndexPath || []).length ? `<span>${esc(t("offlineRecoveryConditionPath"))}: <code>${esc(dependency.conditionIndexPath.join("."))}</code></span>` : ""}</p>`).join("")}${(missionTopology.forks || []).map((fork) => `<p><code>${esc(fork.questId || "?")}</code><i>&rarr;</i>${(fork.successorQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" ")}</p>`).join("")}${(missionTopology.merges || []).map((merge) => `<p>${(merge.predecessorQuestIds || []).map((questId) => `<code>${esc(questId)}</code>`).join(" ")}<i>&rarr;</i><code>${esc(merge.questId || "?")}</code></p>`).join("")}<small>${esc(t("offlineRecoveryMissionTopologyBoundary"))}</small></details>`
        : "";
      const prtsCarrierContext = row.prtsDefinition
        ? `<p><strong>${esc(t("offlineRecoveryPrtsCarrier"))}</strong><code>${esc(row.prtsDefinition.rowId || "?")}</code><code>${esc(row.prtsDefinition.firstLvId || "?")}</code><span>order=${esc(row.prtsDefinition.order ?? "?")}</span></p>`
        : "";
      const dialogSummaryContext = row.summaryDefinition
        ? `<p><strong>${esc(t("offlineRecoveryDialogSummary"))}</strong><code>${esc(row.summaryDefinition.summaryId || "?")}</code><code>textId=${esc(row.summaryDefinition.textId ?? "?")}</code></p>`
        : "";
      const taskConsumer = row.levelScriptTaskConsumer;
      const taskConsumerContext = taskConsumer
        ? `<p><strong>${esc(t("offlineRecoveryTalkDependency"))}</strong><code>${esc(taskConsumer.levelId || "?")}/${esc(taskConsumer.scriptId || "?")}</code><code>${esc(taskConsumer.conditionType || "?")}</code><code>${esc(taskConsumer.dialogId || "?")}</code>${taskConsumer.postDialogAction ? `<span><strong>${esc(t("offlineRecoveryPostDialogAction"))}</strong><code>${esc(taskConsumer.postDialogAction.actionName || "?")}</code></span>` : ""}</p>`
        : "";
      const dialogResultBranch = row.levelDataDialogBranchContext;
      const dialogResultBranchContext = dialogResultBranch
        ? `<details open><summary><strong>${esc(t("offlineRecoveryDialogResultBranch"))}</strong> <code>${esc(dialogResultBranch.levelId || "?")}/${esc(dialogResultBranch.scriptId || "?")}</code></summary><p><strong>${esc(t("offlineRecoveryDialogStart"))}</strong><code>${esc(dialogResultBranch.startDialogListener?.dialogId || "?")}</code><code>${esc(dialogResultBranch.startDialogListener?.propertyPath || "?")}</code></p>${dialogResultBranch.runtimeMissionAssetStatus === "absent_for_nominal_mission" ? `<p><span>${esc(t("offlineRecoveryMissionRuntimeAbsent"))}</span></p>` : ""}${(dialogResultBranch.resultBranches || []).map((branch) => `<p><strong>${esc(t("offlineRecoveryDialogResult"))} ${esc(branch.resultValue ?? "?")}</strong><code>${esc(branch.propertyPath || "?")}</code><i>&rarr;</i><a href="${esc(storyHref(branch.dialogId))}"><code>${esc(branch.dialogId || "?")}</code></a>${(branch.controlPath?.pathLocalIds || []).length ? `<span>${esc(t("offlineRecoveryControlPath"))}: <code>${esc(branch.controlPath.pathLocalIds.map((id) => `#${id}`).join(" "))}</code></span>` : ""}</p>`).join("")}<small>${esc(t("offlineRecoveryDialogBranchBoundary"))}</small></details>`
        : "";
      const emptyHost = row.emptyLevelScriptContext;
      const emptyHostContext = emptyHost
        ? `<details open><summary><strong>${esc(t("offlineRecoveryEmptyHost"))}</strong> <code>${esc(emptyHost.levelId || "?")}/${esc(emptyHost.scriptId || "?")}</code></summary><p><code>properties ${esc(emptyHost.propertyCount ?? "?")}</code><code>UID records ${esc(emptyHost.uidRecordCount ?? "?")}</code><code>actions ${esc(emptyHost.actionListRecordCount ?? "?")}</code><code>tasks ${esc(emptyHost.taskMapCount ?? "?")}</code></p><small>${esc(t("offlineRecoveryEmptyHostBoundary"))}</small></details>`
        : "";
      const runtimeTracking = row.runtimeTrackingContext;
      const runtimeTrackingContext = runtimeTracking
        ? `<p><strong>${esc(t("offlineRecoveryCrossMissionTracking"))}</strong><code>${esc(runtimeTracking.runtimeMissionId || "?")}</code><code>${esc(runtimeTracking.questId || "?")}</code></p>`
        : "";
      const relatedOriginalData = row.missionRelatedOriginalData;
      const relatedOriginalDataContext = relatedOriginalData
        ? `<details open><summary><strong>${esc(t("offlineRecoveryRelatedOriginalData"))}</strong> <code>${esc(relatedOriginalData.groupId || "?")}</code></summary><p><strong>${esc(t("offlineRecoveryPrtsOrder"))}</strong>${(relatedOriginalData.entries || []).map((entry) => `<code>#${esc(entry.order ?? "?")} ${esc(entry.contentId || "?")} / ${esc(entry.prtsId || "?")}</code>`).join(" ")}</p><p><strong>${esc(t("offlineRecoveryMissionTextRows"))}</strong>${(relatedOriginalData.missionTextRowKeys || []).map((key) => `<code>${esc(key)}</code>`).join(" ")}</p><small><strong>${esc(t("offlineRecoveryStoryRelation"))}:</strong> ${esc(relatedOriginalData.storyRelationStatus || "")}</small><small>${esc(relatedOriginalData.orderBoundary || "")}</small></details>`
        : "";
      const definitionFacts = [
        row.dialogIdRegistrationStatus === "present_table_only"
          ? t("offlineRecoveryTableOnlyRegistration")
          : "",
        row.dialogIdRegistrationStatus === "memorypack_root_registered"
          ? "MemoryPack DialogId root registered"
          : "",
        row.dialogTreeAssetStatus === "absent"
          ? t("offlineRecoveryDialogTreeAbsent")
          : "",
        row.dialogTreeAssetStatus === "present_exact_definition"
          ? t("offlineRecoveryDialogTreeExact")
          : "",
        row.richContentStatus === "absent"
          ? t("offlineRecoveryTestStub")
          : "",
        recoveredLineCount
          ? `${recoveredLineCount.toLocaleString()} ${t("offlineRecoveryLines")}`
          : "",
        Array.isArray(row.missingAudioIds) && row.missingAudioIds.length
          ? `${row.missingAudioIds.length.toLocaleString()} ${t("offlineRecoveryMissingAudio")}`
          : "",
        row.audioMembershipStatus
          ? `${t("offlineRecoveryAudioMembership")}: ${row.audioMembershipStatus}`
          : "",
        row.carrierAuditStatus
          ? `${t("offlineRecoveryCarrierAudit")}: ${row.carrierAuditStatus}`
          : "",
        row.binaryRootTokenStatus
          ? `${t("offlineRecoveryBinaryRootToken")}: ${row.binaryRootTokenStatus}`
          : "",
        row.partialRecovery
          ? `${t("partialRecoveryCoverage")}: ${Number(row.coveredLineCount || 0).toLocaleString()} / ${Number(row.lineCount || 0).toLocaleString()} ${t("offlineRecoveryLines")}`
          : "",
      ].filter(Boolean);
      const facts = definitionFacts.length
        ? `<p>${definitionFacts.map((fact) => `<span>${esc(fact)}</span>`).join("")}</p>`
        : "";
      const parentDialogTrees = Array.isArray(row.parentDialogTrees)
        ? row.parentDialogTrees
        : [];
      const parentDialogTreeContext = parentDialogTrees.length
        ? `<details${row.emittedGroupKind === "direct_numbered_dialog_scene" || row.partialRecovery ? " open" : ""}><summary><strong>${esc(t("offlineRecoveryParentDialogTrees"))}</strong> ${parentDialogTrees.length.toLocaleString()} · ${Number(row.branchingParentDialogTreeCount || 0).toLocaleString()} ${esc(t("offlineRecoveryParentTreeBranches"))}</summary>${parentDialogTrees.map((tree) => {
          const connections = (tree.lineConnections || []).map((edge) => (
            `<code>${esc(edge.fromLineId || "?")} &rarr; ${esc(edge.toLineId || "?")}</code>`
          )).join(" ");
          return `<p><code>${esc(tree.sceneKey || tree.assetName || "?")}</code><span>${Number((tree.lineIds || []).length).toLocaleString()} ${esc(t("offlineRecoveryLines"))}</span><span>${Number(tree.branchingOptionGroupCount || 0).toLocaleString()} ${esc(t("offlineRecoveryParentTreeBranches"))}</span></p>${connections ? `<small><strong>${esc(t("offlineRecoveryInternalLineConnections"))}:</strong> ${connections}</small>` : ""}`;
        }).join("")}${row.partialRecovery && (row.missingLineIds || []).length ? `<small><strong>${esc(t("partialRecoveryUnmatchedRows"))}:</strong> ${(row.missingLineIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</small>` : ""}</details>`
        : "";
      const parentLevelContexts = Array.isArray(row.parentLevelContexts)
        ? row.parentLevelContexts
        : [];
      const parentLevelContext = parentLevelContexts.length
        ? `<details${row.partialRecovery ? " open" : ""}><summary><strong>${esc(t("offlineRecoveryParentLevelContexts"))}</strong> ${parentLevelContexts.length.toLocaleString()}</summary><p>${esc(t("offlineRecoveryParentLevelBoundary"))}</p>${parentLevelContexts.map((context) => {
          const parents = (context.parentDialogTreeIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ");
          const files = (context.sourceFiles || []).map((source) => `<code>${esc(source)}</code>`).join(" ");
          const mapAssets = (context.mapTextAssets || []).map((asset) => `<code>${esc(asset.sourceFile || "?")}</code>${asset.sourcePathId ? `<span>PathID ${esc(asset.sourcePathId)}</span>` : ""}`).join(" ");
          const runtime = context.subGameRuntime && typeof context.subGameRuntime === "object"
            ? context.subGameRuntime
            : null;
          const runtimeContext = runtime ? (() => {
            const lane = (label, tasks) => (Array.isArray(tasks) && tasks.length
              ? `<span><strong>${esc(label)}:</strong> ${tasks.map((task) => `<code>${esc(task.taskId || "?")}</code>${task.levelScriptId == null ? "" : `<code>${esc(task.levelScriptId)}</code>`}`).join(" ")}</span>`
              : "");
            const taskLanes = [
              lane(t("offlineRecoverySubGameMainTasks"), runtime.mainTasks),
              lane(t("offlineRecoverySubGameExtraTasks"), runtime.extraTasks),
              lane(t("offlineRecoverySubGameFailTasks"), runtime.failTasks),
            ].filter(Boolean).join(" ");
            const topology = runtime.taskTopology && typeof runtime.taskTopology === "object"
              ? runtime.taskTopology
              : null;
            const topologyContext = topology ? (() => {
              if (topology.status === "exact_null_task_map") {
                return `<details class="mp-subgame-task-topology"><summary><strong>${esc(t("offlineRecoverySubGameTaskTopology"))}</strong><span>${esc(t("offlineRecoverySubGameTaskTopologyNull"))}</span></summary><small>${esc(t("offlineRecoverySubGameTopologyBoundary"))}</small></details>`;
              }
              if (topology.status !== "exact_complete_task_map") {
                const diagnostic = (topology.decoderDiagnostics || [])[0] || {};
                return `<details class="mp-subgame-task-topology is-unavailable"><summary><strong>${esc(t("offlineRecoverySubGameTaskTopology"))}</strong><span>${esc(topology.status || "unavailable")}</span></summary>${diagnostic.gate ? `<small><code>${esc(diagnostic.gate)}</code> <code>${esc(diagnostic.conditionUnionTag || "?")}</code></small>` : ""}</details>`;
              }
              const laneLabel = (value) => ({
                main: t("offlineRecoverySubGameMainTasks"),
                extra: t("offlineRecoverySubGameExtraTasks"),
                fail: t("offlineRecoverySubGameFailTasks"),
                internal: t("offlineRecoverySubGameInternal"),
              }[value] || value || t("offlineRecoverySubGameInternal"));
              const conditionValue = (value) => {
                if (value == null) return "∅";
                if (["string", "number", "boolean"].includes(typeof value)) return String(value);
                if (Object.prototype.hasOwnProperty.call(value, "value")) return value.value == null ? "∅" : String(value.value);
                if (value.taskKey != null) return String(value.taskKey);
                if (value.scriptId != null) return String(value.scriptId || value.mode || "current");
                if (Array.isArray(value.values)) return `${value.values.length} values`;
                return "";
              };
              const ignoredConditionFields = new Set([
                "type", "conditionUnionTag", "conditionUnionTagEncoding", "serializedMemberCount",
                "conditionOffset", "conditionOffsetHex", "conditionEndOffset", "conditionEndOffsetHex",
                "scopeMask", "uniqueId", "useCurrentScope", "useGraphScope", "nativeMappingId",
              ]);
              const taskRows = (topology.tasks || []).map((task) => {
                const descriptions = Object.values(task.displayInfo?.trackingInfoDict || {})
                  .map((row) => row?.description?.key)
                  .filter(Boolean);
                const conditions = (task.conditions || []).map((row) => {
                  const condition = row.condition || {};
                  const fields = Object.entries(condition)
                    .filter(([key]) => !ignoredConditionFields.has(key) && !key.endsWith("Name") && key !== "conditionEvalString" && key !== "subConditionCount")
                    .map(([key, value]) => [key, conditionValue(value)])
                    .filter(([, value]) => value !== "")
                    .slice(0, 5)
                    .map(([key, value]) => `<span><b>${esc(key)}</b>=<code>${esc(value)}</code></span>`)
                    .join(" ");
                  const expression = condition.conditionEvalString
                    ? `<em>${esc(condition.conditionEvalString)}</em>`
                    : "";
                  return `<li><code>${esc(condition.type || "?")}</code><small>${esc(row.conditionKey || "?")}</small>${expression}${fields ? `<p>${fields}</p>` : ""}</li>`;
                }).join("");
                return `<details${task.registeredInSubGame ? " open" : ""}><summary><code>${esc(task.taskId || "?")}</code><b>${esc(laneLabel(task.lane))}</b>${task.canBeTracked ? `<span>${esc(t("offlineRecoverySubGameTracked"))}</span>` : ""}<small>${Number(task.conditionCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameConditions"))}</small></summary>${descriptions.length ? `<p><strong>${esc(t("offlineRecoverySubGameTaskDescriptions"))}:</strong> ${descriptions.map((key) => `<code>${esc(key)}</code>`).join(" ")}</p>` : ""}${conditions ? `<ol>${conditions}</ol>` : ""}</details>`;
              }).join("");
              const typeCounts = Object.entries(topology.conditionTypeCounts || {})
                .map(([type, count]) => `<span><code>${esc(type)}</code> ${Number(count || 0).toLocaleString()}</span>`)
                .join(" ");
              const formulas = (topology.combineExpressions || [])
                .map((row) => `<span><code>${esc(row.taskId || "?")}</code> <em>${esc(row.expression || "?")}</em></span>`)
                .join(" ");
              return `<details class="mp-subgame-task-topology" open><summary><strong>${esc(t("offlineRecoverySubGameTaskTopology"))}</strong><span>${Number(topology.decodedTaskCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameTasks"))}</span><span>${Number(topology.conditionCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameConditions"))}</span></summary>${typeCounts ? `<p><strong>${esc(t("offlineRecoverySubGameConditionTypes"))}:</strong> ${typeCounts}</p>` : ""}${formulas ? `<p><strong>${esc(t("offlineRecoverySubGameCombineExpressions"))}:</strong> ${formulas}</p>` : ""}<div>${taskRows}</div><small>${esc(t("offlineRecoverySubGameTopologyBoundary"))}</small></details>`;
            })() : "";
            const actionTopology = runtime.actionTopology && typeof runtime.actionTopology === "object"
              ? runtime.actionTopology
              : null;
            const actionTopologyContext = actionTopology ? (() => {
              if (["exact_empty_action_map", "exact_no_action_map"].includes(actionTopology.status)) {
                return `<details class="mp-subgame-task-topology mp-subgame-action-topology"><summary><strong>${esc(t("offlineRecoverySubGameActionTopology"))}</strong><span>${esc(t("offlineRecoverySubGameActionTopologyEmpty"))}</span></summary><small>${esc(t("offlineRecoverySubGameActionTopologyBoundary"))}</small></details>`;
              }
              if (!["exact_complete_action_map", "exact_complete_action_map_with_runtime_shadowing"].includes(actionTopology.status)) {
                const diagnostic = actionTopology.validatorDiagnostic || {};
                return `<details class="mp-subgame-task-topology mp-subgame-action-topology is-unavailable"><summary><strong>${esc(t("offlineRecoverySubGameActionTopology"))}</strong><span>${esc(actionTopology.status || "unavailable")}</span></summary>${diagnostic.gate ? `<small><code>${esc(diagnostic.gate)}</code></small>` : ""}</details>`;
              }
              const countTags = (counts) => Object.entries(counts || {})
                .map(([name, count]) => `<span><code>${esc(name)}</code> ${Number(count || 0).toLocaleString()}</span>`)
                .join(" ");
              const eventTypes = countTags(actionTopology.eventTypeCounts);
              const actionTypes = countTags(actionTopology.actionTypeCounts);
              const outgoing = new Map();
              for (const edge of actionTopology.edges || []) {
                const key = `${edge.sourceKind || "?"}:${edge.sourceLocalId}`;
                if (!outgoing.has(key)) outgoing.set(key, []);
                outgoing.get(key).push(edge);
              }
              const terminals = new Map();
              for (const target of actionTopology.runtimeTerminalTargets || []) {
                const key = `${target.sourceKind || "?"}:${target.sourceLocalId}`;
                if (!terminals.has(key)) terminals.set(key, []);
                terminals.get(key).push(target);
              }
              const eventRows = (actionTopology.eventRoots || []).map((event) => {
                const detail = event.eventDetail || {};
                const detailText = detail.summary || detail.eventKey || detail.guideIdFilter || (detail.triggerSlotIdFilter == null ? "" : `slot ${detail.triggerSlotIdFilter}`);
                const texts = (event.texts || []).map((value) => `<code>${esc(value)}</code>`).join(" ");
                const listenerFields = [
                  event.priority == null ? "" : `<span><b>${esc(t("offlineRecoverySubGameActionEventPriority"))}</b>=<code>${esc(event.priority)}</code></span>`,
                  event.triggerActiveDuring == null ? "" : `<span><b>${esc(t("offlineRecoverySubGameActionEventTriggerActive"))}</b>=<code>${esc(event.triggerActiveDuring)}</code></span>`,
                  event.filterMode == null ? "" : `<span><b>${esc(t("offlineRecoverySubGameActionEventFilter"))}</b>=<code>${esc(event.filterMode)}${event.filterMask == null ? "" : `/${esc(event.filterMask)}`}${event.filterLevel == null ? "" : `/${esc(event.filterLevel)}`}</code></span>`,
                ].filter(Boolean).join(" ");
                const shadowed = event.runtimeShadowedRecordOffsets || [];
                const slotText = shadowed.length ? `<p><strong>${esc(t("offlineRecoverySubGameActionEventSlot"))}:</strong> <code>${esc(event.recordOffsetHex || event.recordOffset || "?")}</code> <span>${shadowed.length} ${esc(t("offlineRecoverySubGameActionShadowed"))}</span> ${shadowed.map((offset) => `<code>0x${Number(offset).toString(16)}</code>`).join(" ")}</p>` : "";
                return `<li><code>#${esc(event.localId)}</code><b>${esc(event.headerName || event.unionTag || "?")}</b><span>&rarr; <code>#${esc(event.nextActionLocalId)}</code></span>${detailText ? `<small>${esc(detailText)}</small>` : ""}${listenerFields ? `<p>${listenerFields}</p>` : ""}${slotText}${texts ? `<p>${texts}</p>` : ""}</li>`;
              }).join("");
              const actionRows = (actionTopology.actions || []).map((action) => {
                const edges = outgoing.get(`action:${action.localId}`) || [];
                const terminalEdges = terminals.get(`action:${action.localId}`) || [];
                const edgeText = edges.map((edge) => `<span><code>${esc(edge.relation || "edge")}</code> &rarr; <code>#${esc(edge.targetActionLocalId)}</code></span>`).join(" ");
                const terminalText = terminalEdges.map((edge) => `<span><code>${esc(edge.relation || "edge")}</code> &rarr; <code>#${esc(edge.targetActionLocalId)}</code> <small>${esc(t("offlineRecoverySubGameActionTerminals"))}</small></span>`).join(" ");
                const storyTargets = (action.storyTargets || []).map((target) => `<code>${esc(target.storyKey || "?")}</code>`).join(" ");
                const texts = (action.texts || []).map((value) => `<code>${esc(value)}</code>`).join(" ");
                const shadowed = action.runtimeShadowedRecordOffsets || [];
                const shadowText = shadowed.length ? `<p><strong>${esc(t("offlineRecoverySubGameActionActiveSlot"))}:</strong> <code>${esc(action.recordOffsetHex || action.recordOffset || "?")}</code> <span>${shadowed.length} ${esc(t("offlineRecoverySubGameActionShadowed"))}</span> ${shadowed.map((offset) => `<code>0x${Number(offset).toString(16)}</code>`).join(" ")}</p>` : "";
                const isFanout = action.controlKind === "parallel_fanout" || action.controlKind === "conditional_choice";
                const isControl = Boolean(action.controlKind);
                return `<details class="${isFanout ? "is-fanout" : ""}"${isControl || storyTargets || shadowed.length || terminalEdges.length ? " open" : ""}><summary><code>#${esc(action.localId)}</code><b>${esc(action.actionName || action.unionTag || "?")}</b>${action.controlKind ? `<small><code>${esc(action.controlKind)}</code></small>` : ""}${edges.length ? `<small>${edges.length} ${esc(t("offlineRecoverySubGameActionEdges"))}</small>` : ""}${shadowed.length ? `<small>${shadowed.length} ${esc(t("offlineRecoverySubGameActionShadowed"))}</small>` : ""}</summary>${storyTargets ? `<p><strong>${esc(t("offlineRecoverySubGameActionStoryTargets"))}:</strong> ${storyTargets}</p>` : ""}${edgeText ? `<p>${edgeText}</p>` : ""}${terminalText ? `<p>${terminalText}</p>` : ""}${shadowText}${texts ? `<p>${texts}</p>` : ""}</details>`;
              }).join("");
              const open = Number(actionTopology.typedBranchNodeCount || 0) + Number(actionTopology.orderedSequenceNodeCount || 0) + Number(actionTopology.loopNodeCount || 0) > 0 ? " open" : "";
              return `<details class="mp-subgame-task-topology mp-subgame-action-topology"${open}><summary><strong>${esc(t("offlineRecoverySubGameActionTopology"))}</strong><span>${Number(actionTopology.eventRootCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionEvents"))}</span>${Number(actionTopology.physicalHeaderRecordCount || 0) !== Number(actionTopology.eventRootCount || 0) ? `<span>${Number(actionTopology.physicalHeaderRecordCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionPhysicalEvents"))}</span>` : ""}<span>${Number(actionTopology.actionNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionNodes"))}</span><span>${Number(actionTopology.edgeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionEdges"))}</span>${Number(actionTopology.runtimeShadowedIndexedRecordCount || 0) ? `<span>${Number(actionTopology.runtimeShadowedIndexedRecordCount).toLocaleString()} ${esc(t("offlineRecoverySubGameActionShadowed"))}</span>` : ""}${Number(actionTopology.runtimeTerminalTargetCount || 0) ? `<span>${Number(actionTopology.runtimeTerminalTargetCount).toLocaleString()} ${esc(t("offlineRecoverySubGameActionTerminals"))}</span>` : ""}<span>${Number(actionTopology.orderedSequenceNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionSequences"))}</span><span>${Number(actionTopology.parallelFanoutNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionFanouts"))}</span><span>${Number(actionTopology.conditionalBranchNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionChoices"))}</span><span>${Number(actionTopology.loopNodeCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionLoops"))}</span><span>${Number(actionTopology.eventEntryConvergenceCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionConvergence"))}</span><span>${Number(actionTopology.cycleCount || 0).toLocaleString()} ${esc(t("offlineRecoverySubGameActionCycles"))}</span></summary>${eventTypes ? `<p><strong>${esc(t("offlineRecoverySubGameActionEventTypes"))}:</strong> ${eventTypes}</p>` : ""}${actionTypes ? `<p><strong>${esc(t("offlineRecoverySubGameActionTypes"))}:</strong> ${actionTypes}</p>` : ""}${eventRows ? `<ol class="mp-subgame-action-events">${eventRows}</ol>` : ""}<div>${actionRows}</div><small>${esc(t("offlineRecoverySubGameActionTopologyBoundary"))}</small></details>`;
            })() : "";
            const playback = (runtime.parentDialogPlayback || []).map((item) => {
              const owners = (item.nativeEventOwners || []).map((owner) => `<code>${esc(owner.headerName || "?")}</code>`).join(" ");
              return `<span><code>${esc(item.parentDialogTreeId || "?")}</code> &larr; <code>${esc(item.actionName || "StartDialogAction")}</code>${owners ? ` ${owners}` : ""}</span>`;
            }).join(" ");
            const definitionOnly = (runtime.definitionOnlyParentDialogTreeIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ");
            return `<section><p><strong>${esc(t("offlineRecoverySubGameRuntime"))}</strong><code>${esc(runtime.subGameId || context.dungeonId || "?")}</code><span>${esc(t("offlineRecoverySubGameBindScript"))}: <code>${esc(runtime.bindScriptId == null ? "?" : runtime.bindScriptId)}</code></span><span>${esc(t("offlineRecoverySubGamePlaybackCoverage"))}: ${esc(runtime.parentPlaybackCoverage || "none")}</span></p>${taskLanes ? `<small><strong>${esc(t("offlineRecoverySubGameTaskLanes"))}:</strong> ${taskLanes}</small>` : ""}${topologyContext}${actionTopologyContext}${playback ? `<small><strong>${esc(t("offlineRecoverySubGameParentPlayback"))}:</strong> ${playback}</small>` : ""}${definitionOnly ? `<small><strong>${esc(t("offlineRecoverySubGameDefinitionOnlyParents"))}:</strong> ${definitionOnly}</small>` : ""}${runtime.taskLaneBoundary ? `<small>${esc(runtime.taskLaneBoundary)}</small>` : ""}${runtime.parentPlaybackBoundary ? `<small>${esc(runtime.parentPlaybackBoundary)}</small>` : ""}</section>`;
          })() : "";
          return `<div><p><code>${esc(context.levelId || "?")}</code><span>${esc(t("offlineRecoveryDungeonCatalogMetadata"))}: <code>${esc(context.dungeonId || "?")}</code>${context.dungeonSortId == null ? "" : ` / sortId ${esc(context.dungeonSortId)}`}</span></p>${parents ? `<small>${parents}</small>` : ""}${runtimeContext}${files || mapAssets ? `<small><strong>${esc(t("offlineRecoveryRelatedLevelFiles"))}:</strong> ${files} ${mapAssets}</small>` : ""}</div>`;
        }).join("")}</details>`
        : "";
      const missingLineFragments = Array.isArray(row.missingLineFragments)
        ? row.missingLineFragments
        : [];
      const missingLineFragmentContext = missingLineFragments.length
        ? `<small><strong>${esc(t("partialRecoveryRowIdPositions"))}:</strong> ${missingLineFragments.map((fragment) => {
          const neighbors = [fragment.nearestLowerCoveredLineId, fragment.nearestUpperCoveredLineId].filter(Boolean).map((id) => `<code>${esc(id)}</code>`).join(" / ");
          return `<span><code>${esc(fragment.lineId || "?")}</code> ${esc(fragment.numericPosition || "?")}${neighbors ? ` (${neighbors})` : ""}</span>`;
        }).join(" ")}</small>`
        : "";
      const evidenceBoundary = [
        row.activationBoundary
          ? `<small><strong>${esc(t("runtimeRecoveryActivation"))}:</strong> ${esc(row.activationBoundary)}</small>`
          : "",
        row.playbackBoundary
          ? `<small><strong>${esc(t("runtimeRecoveryPlayback"))}:</strong> ${esc(row.playbackBoundary)}</small>`
          : "",
        row.consumerBoundary
          ? `<small><strong>${esc(t("offlineRecoveryConsumer"))}:</strong> ${esc(row.consumerBoundary)}</small>`
          : "",
        row.orderBoundary
          ? `<small><strong>${esc(t("offlineRecoveryOrder"))}:</strong> ${esc(row.orderBoundary)}</small>`
          : "",
        row.reopenWhen
          ? `<small><strong>${esc(t("offlineRecoveryReopen"))}:</strong> ${esc(row.reopenWhen)}</small>`
          : "",
      ].filter(Boolean).join("");
      const nativePaths = [
        ...(row.nativeEventPaths || []),
        ...(row.nativePaths || []),
      ].map((path) => {
        const header = path?.headerName || path?.eventName || path?.eventDetail?.type || "?";
        const actions = (path?.path || path?.steps || []).map((step) => step?.actionName || step?.recordClass).filter(Boolean);
        return `<code>${esc([header, ...actions].join(" → "))}</code>`;
      }).join(" ");
      const nativePathEvidence = nativePaths
        ? `<small><strong>${esc(t("runtimeRecoveryNativePaths"))}:</strong> ${nativePaths}</small>`
        : "";
      const runtimeContextMissionIds = (row.contextMissionIds || []).length
        ? row.contextMissionIds
        : [row.contextMissionId || row.missionStateId || row.missionId].filter(Boolean);
      const runtimeContextQuestIds = (row.anchorQuestIds || []).length
        ? row.anchorQuestIds
        : ((row.questIds || []).length ? row.questIds : [row.questId].filter(Boolean));
      const runtimeContext = row.runtimeContextRecovery
        ? row.relation === "sns_authored_mission_link"
          ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoverySnsLink"))}: <code>${esc(row.missionId || "?")}</code></span>${(row.snsContentIds || []).length ? `<span>content ${(row.snsContentIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>` : ""}</p>`
          : row.relation === "cutscene_root_playback_alias_composed"
            ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.missionId || "?")}</code></span>${(row.rootStoryKeys || []).length ? `<span>${esc(t("runtimeRecoveryPlaybackRoots"))}: ${(row.rootStoryKeys || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>` : ""}${nativePaths ? `<span>${esc(t("runtimeRecoveryNativePaths"))}: ${nativePaths}</span>` : ""}</p>`
            : row.relation === "lua_controller_playback"
              ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryLuaController"))}: <code>${esc(row.luaFile || "?")}</code>${row.luaLine ? `:${Number(row.luaLine)}` : ""}</span><span>${esc(t("runtimeRecoveryLuaCall"))}: <code>${esc(row.luaCall || "?")}</code></span></p>`
            : row.relation === "dialog_tree_reachable_story_playback"
              ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.missionId || row.nominalMissionId || "?")}</code></span><span>${esc(t("runtimeRecoveryQuestAnchors"))}: <code>${esc(row.questId || "?")}</code></span><span>${esc(t("runtimeRecoveryCarrierParents"))}: <code>${esc(row.parentStoryKey || "?")}</code></span></p>`
            : row.relation === "levelscript_quest_state_gate"
              ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.missionId || row.nominalMissionId || "?")}</code></span><span>${esc(t("runtimeRecoveryQuestAnchors"))}: <code>${esc(row.questId || "?")}</code></span><span>${esc(t("runtimeRecoveryGate"))}: <code>${esc(row.conditionType || "?")}(${esc(row.conditionComparer || "?")}, ${Number(row.conditionQuestState) === 2 ? "Processing" : esc(row.conditionQuestState ?? "?")})</code> ${(row.eventNames || []).map((id) => `<code>${esc(id)}</code>`).join(" ")} ${(row.actionNames || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span></p>`
            : exactBlackCarrierRelations.has(row.relation)
              ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.nominalStoryMissionId || "?")}</code></span>${(row.parentStoryKeys || []).length ? `<span>${esc(t("runtimeRecoveryCarrierParents"))}: ${(row.parentStoryKeys || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>` : ""}${(row.timelineIds || []).length ? `<span>${esc(t("offlineRecoveryInternalTimeline"))}: ${(row.timelineIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>` : ""}</p>`
              : exactSameMissionRuntimeRelations.has(row.relation)
                ? `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.nominalStoryMissionId || row.missionId || row.nominalMissionId || "?")}</code></span><span>${esc(t("runtimeRecoveryContextMission"))}: <code>${esc(row.contextMissionId || row.missionStateId || "?")}</code></span></p>`
                : `<p><strong>${esc(t("runtimeContextRecoveryBoundary"))}</strong><span>${esc(t("runtimeRecoveryNominalMission"))}: <code>${esc(row.nominalStoryMissionId || row.missionId || row.nominalMissionId || "?")}</code></span><span>${esc(t(runtimeContextMissionIds.length > 1 ? "runtimeRecoveryContextMissions" : "runtimeRecoveryContextMission"))}: ${runtimeContextMissionIds.length ? runtimeContextMissionIds.map((id) => `<code>${esc(id)}</code>`).join(" ") : `<code>?</code>`}</span>${runtimeContextQuestIds.length ? `<span>${esc(t("runtimeRecoveryQuestAnchors"))}: ${runtimeContextQuestIds.map((id) => `<code>${esc(id)}</code>`).join(" ")}</span>` : ""}${nativePaths ? `<span>${esc(t("runtimeRecoveryNativePaths"))}: ${nativePaths}</span>` : ""}</p>`
        : "";
      const evidenceLabel = ({
        leveldata_property_resolved_levelscript_result_branch: t("offlineRecoveryEvidenceResultBranch"),
        mission_tracked_npc_proxy_dialog_context_without_playback_owner: t("offlineRecoveryEvidenceTrackedNpc"),
        registered_dialog_definition_without_recovered_activator: t("offlineRecoveryEvidenceDefinitionOnly"),
        radio_definition_without_recovered_consumer: t("offlineRecoveryEvidenceRadioOnly"),
        radio_definition_binary_consumer_surface_exhausted: t("offlineRecoveryEvidenceBinaryRadio"),
        missionless_npc_proxy_dialog_native_consumer: t("offlineRecoveryEvidenceNpcProxyConsumer"),
        sns_definition_binary_consumer_surface_exhausted: t("offlineRecoveryEvidenceBinarySns"),
        reading_popup_definition_binary_consumer_surface_exhausted: t("offlineRecoveryEvidenceBinaryReadingPopup"),
        unregistered_dialog_definition_binary_consumer_surface_exhausted: t("offlineRecoveryEvidenceBinaryUnregisteredDialog"),
        registered_dialog_tree_definition_binary_consumer_surface_exhausted: t("offlineRecoveryEvidenceBinaryRegisteredDialogTree"),
        exact_missionless_native_event_playback_path: t("offlineRecoveryEvidenceMissionlessNativePlayback"),
        cutscene_root_without_recovered_activator: t("offlineRecoveryEvidenceCutsceneRoot"),
        cutscene_root_playable_alias_without_recovered_activator: t("offlineRecoveryEvidenceCutsceneAlias"),
        dialog_text_table_only_with_empty_levelscript_host: t("offlineRecoveryEvidenceEmptyHost"),
        radio_definition_with_empty_levelscript_host: t("offlineRecoveryEvidenceEmptyHost"),
        dialog_text_table_only_without_registry_asset_or_consumer: t("offlineRecoveryEvidenceUnregistered"),
        registered_dialog_tree_trunk_group_exact_line_partition: t("offlineRecoveryEvidenceParentTreePartition"),
        partial_registered_dialog_tree_trunk_group_line_partition: t("partialRecoveryEvidenceParentTreePartition"),
        project_authored_story_content: t("projectAuthoredEvidence"),
      })[row.evidenceKind] || runtimeRecoveryEvidenceLabel(row);
      const cutsceneAliasContext = row.rootPlaybackAlias
        ? `<p><strong>${esc(t("offlineRecoveryCutsceneAlias"))}</strong><span><code>${esc(row.rootPlaybackAlias.rootStoryKey || "?")}</code> &rarr; <code>${esc(row.rootPlaybackAlias.playableAssetStoryKey || "?")}</code> · ${esc(t(row.cutsceneAliasRole === "cutscene_root" ? "offlineRecoveryCutsceneAliasRootRole" : "offlineRecoveryCutsceneAliasPlayableRole"))}</span></p>`
        : "";
      return `<article><header><a href="${esc(storyHref(row.key))}"><code>${esc(row.key)}</code></a><b>${esc(evidenceLabel)}</b></header>${runtimeContext}${cutsceneAliasContext}${timeline ? `<p><strong>${esc(t("offlineRecoveryInternalTimeline"))}</strong><code>${esc(timeline)}</code>${lineCount ? `<span>${lineCount.toLocaleString()} ${esc(t("offlineRecoveryLines"))}</span>` : ""}</p>` : ""}${facts}${parentDialogTreeContext}${parentLevelContext}${missingLineFragmentContext}${prtsCarrierContext}${dialogSummaryContext}${missionTrackingContext}${npcProxyConsumerContext}${nativeConsumerContext}${snsDefinitionContext}${missionBranchContext}${missionSequenceContext}${missionTopologyContext}${taskConsumerContext}${dialogResultBranchContext}${emptyHostContext}${runtimeTrackingContext}${relatedOriginalDataContext}${options}${printableTokenBoundary}${internalBranches}${terminalOptions}${popup}${nativePathEvidence}${evidenceBoundary}${sources.length ? `<small>${[...new Set(sources)].map((source) => `<code>${esc(source)}</code>`).join(" ")}</small>` : ""}</article>`;
    }).join("");
    const containments = (order.containments || []).map((row) => {
      const after = (row.embeddedAfterLineIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ");
      const before = (row.embeddedBeforeLineIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ");
      const placement = row.boundaryPlacement === "exact_prime_entry_before_parent_trunk"
        ? t("embeddedAtEntry")
        : row.boundaryPlacement === "exact_after_parent_trunk_at_finish"
          ? t("embeddedAtFinish")
          : t("embeddedBetween");
      const leftBoundary = after ? `${after} &rarr; ` : "";
      const rightBoundary = before ? ` &rarr; ${before}` : "";
      const popup = row.readingPopupId
        ? `<small><strong>${esc(t("readingPopup"))}:</strong> <code>${esc(row.readingPopupId)}</code></small>`
        : "";
      const sources = (row.sourceFiles || []).map((source) => `<code>${esc(source)}</code>`).join(" ");
      const parent = row.parentStoryCandidate === false
        ? `<code>${esc(row.parent || "?")}</code>`
        : `<a href="${esc(storyHref(row.parent))}"><code>${esc(row.parent || "?")}</code></a>`;
      return `<div class="mp-order-edge">${parent}<i aria-hidden="true">[${leftBoundary}</i><a href="${esc(storyHref(row.child))}"><code>${esc(row.child || "?")}</code></a><i aria-hidden="true">${rightBoundary}]</i><small><b>${esc(placement)}</b> <code>${esc(row.relation || "")}</code></small>${popup}${sources ? `<small>${sources}</small>` : ""}</div>`;
    }).join("");
    const cycles = (order.cycles || []).map((component) => componentHtml(component.id)).join("");
    return `<details class="mp-mission-story mp-story-order" data-weight="${Number(summary.strongEdgeCount) ? "strong" : "context"}"${Number(summary.strongEdgeCount) || offlineRows.length ? " open" : ""}>
      <summary>${esc(t("storyOrder"))} <span>${Number(summary.sceneCount || 0).toLocaleString()}</span></summary>
      <p>${esc(t("storyOrderHint"))}</p>
      <div class="mp-order-metrics"><span><b>${Number(summary.strongEdgeCount || 0).toLocaleString()}</b>${esc(t("strongEdges"))}</span><span><b>${Number(summary.questSucceedLifecycleEdgeCount || 0).toLocaleString()}</b>${esc(t("questSucceedLifecycleEdges"))}</span><span><b>${Number(summary.questStartActionDefinitionCount || 0).toLocaleString()}</b>${esc(t("questStartDefinitions"))}</span><span><b>${Number(summary.nativeControlPathTransitionEdgeCount || 0).toLocaleString()}</b>${esc(t("nativeStoryTransitions"))}</span><span><b>${Number(summary.nativeControlPathBranchingTransitionEdgeCount || 0).toLocaleString()}</b>${esc(t("nativeStoryTransitionBranching"))}</span>${summary.nativeControlNonStoryArmCount ? `<span><b>${Number(summary.nativeControlNonStoryArmCount).toLocaleString()}</b>${esc(t("nativeNonStoryArm"))}</span>` : ""}${summary.nativeControlCrossBoundaryBranchCount ? `<span><b>${Number(summary.nativeControlCrossBoundaryBranchCount).toLocaleString()}</b>${esc(t("nativeCrossBoundaryStories"))}</span>` : ""}<span><b>${Number(summary.weakEdgeCount || 0).toLocaleString()}</b>${esc(t("weakEdges"))}</span><span><b>${Number(summary.cycleCount || 0).toLocaleString()}</b>${esc(t("orderCycles"))}</span><span><b>${Number(summary.unorderedScenePairs || 0).toLocaleString()}</b>${esc(t("unknownPairs"))}</span><span><b>${offlineRows.length.toLocaleString()}</b>${esc(t("offlineRecoveryGaps"))}</span></div>
      ${missionObservedContexts ? `<section><h4>${esc(t("missionObservedScriptContexts"))}</h4><p>${esc(t("missionObservedScriptContextsHint"))}</p><div class="mp-order-branches">${missionObservedContexts}</div></section>` : ""}
      ${causalEdges ? `<section><h4>${esc(t("causalEdges"))}</h4><div class="mp-order-edges">${causalEdges}</div></section>` : ""}
      ${nativeTransitions ? `<section><h4>${esc(t("nativeStoryTransitions"))}</h4><p>${esc(t("nativeStoryTransitionsHint"))}</p><div class="mp-order-branches">${nativeTransitions}</div></section>` : ""}
      ${nativeMissionStateBranches ? `<section><h4>${esc(t("nativeMissionStateBranches"))}</h4><p>${esc(t("nativeMissionStateBranchesHint"))}</p><div class="mp-order-branches">${nativeMissionStateBranches}</div></section>` : ""}
      ${questSucceedLifecycleEdges ? `<section><h4>${esc(t("questSucceedLifecycle"))}</h4><p>${esc(t("questSucceedLifecycleHint"))}</p><div class="mp-order-branches mp-quest-succeed-lifecycles">${questSucceedLifecycleEdges}</div></section>` : ""}
      ${questLifecycleDefinitions ? `<section><h4>${esc(t("questStartDefinitionsTitle"))}</h4><p>${esc(t("questStartDefinitionsHint"))}</p><div class="mp-order-branches mp-quest-succeed-lifecycles">${questLifecycleDefinitions}</div></section>` : ""}
      ${containments ? `<section><h4>${esc(t("embeddedStory"))}</h4><p>${esc(t("embeddedStoryHint"))}</p><div class="mp-order-edges">${containments}</div></section>` : ""}
      ${frontiers ? `<details class="mp-order-frontiers"><summary>${esc(t("partialFrontier"))}</summary>${frontiers}</details>` : ""}
      ${cycles ? `<section class="mp-order-cycles"><h4>${esc(t("orderCycles"))}</h4><p>${esc(t("orderCycleHint"))}</p>${cycles}</section>` : ""}
      ${questForks || questMerges || nativeBranches || nativeMerges || nativeSequences || sceneOptions || dialogConditionalBranches || typedSelectors ? `<section><h4>${esc(t("forkMerge"))}</h4>${questForkAuthorityHtml}<div class="mp-order-branches">${questForks}${questMerges}${nativeBranches}${nativeMerges}${nativeSequences}${sceneOptions}${dialogConditionalBranches}${typedSelectors}</div></section>` : ""}
      ${serializedBranchInventoryHtml}
      ${relatedActionTopologies ? `<section><h4>${esc(t("nativeRelatedActionGraphs"))}</h4><p>${esc(t("nativeRelatedActionGraphsHint"))}</p><div class="mp-order-branches">${relatedActionTopologies}</div></section>` : ""}
      ${dialogOptions ? `<section><h4>${esc(t("optionBranches"))}</h4><div class="mp-order-dialog-branches">${dialogOptions}</div></section>` : ""}
      ${offlineGaps ? `<details class="mp-order-recovery-gaps" open><summary>${esc(t("offlineRecoveryGaps"))} <span>${offlineRows.length.toLocaleString()}</span></summary><p>${esc(t("offlineRecoveryGapsHint"))}</p><div>${offlineGaps}</div></details>` : ""}
      <small>${esc(t("isolatedScenes"))}: ${Number(summary.isolatedSceneCount || 0).toLocaleString()} 路 ${esc(t("weakOnlyScenes"))}: ${Number(summary.weakOnlySceneCount || 0).toLocaleString()}</small>
    </details>`;
  }

  function renderMission() {
    renderMissionSummary();
    renderGraph();
    renderInspector();
  }

  function runtimeObservationHtml(row) {
    const route = (row.route || []).map((step) => {
      const label = step.kind === "levelscript_event"
        ? `${step.eventName || "LevelScript event"} #${step.headerLocalId ?? "?"}`
        : `${step.actionType || "action"} #${step.actionLocalId ?? "?"}`;
      return `<span><small>${esc(step.kind)}</small><code>${esc(label)}</code></span>`;
    }).join('<i aria-hidden="true">&rarr;</i>');
    const detail = [
      `${t("runtimeSession")} ${row.sessionId || "?"} #${row.seq ?? "?"}`,
      row.triggerStatus,
      row.actionType,
      row.scriptId ? `LevelScript ${row.scriptId}` : "",
    ].filter(Boolean).join(" 路 ");
    return `<article class="mp-runtime-observation">
      <header><a href="${esc(storyHref(row.storyKey))}"><code>${esc(row.storyKey)}</code></a><b>${esc(row.playbackType || "Story")}</b></header>
      <p>${esc(detail)}</p>
      ${route ? `<div class="mp-trigger-chain"><span><small>${esc(t("observedRoute"))}</small><code>${esc(row.chainId || "?")}</code></span><i aria-hidden="true">&rarr;</i>${route}<i aria-hidden="true">&rarr;</i><span><small>Story</small><code>${esc(row.storyKey)}</code></span></div>` : ""}
    </article>`;
  }

  function runtimeTraceHtml() {
    const trace = state.mission?.runtimeTrace;
    if (!trace) return "";
    const globalSummary = state.index?.runtimeTrace?.summary || {};
    const contextOnly = (trace.missionContextOnly || []).filter((row) => row && row.storyKey);
    const edges = (trace.observedEdges || []).filter((row) => row && row.source && row.target);
    const edgeHtml = edges.map((row) => `<div class="mp-order-edge"><a href="${esc(storyHref(row.source))}"><code>${esc(row.source)}</code></a><i>&rarr;</i><a href="${esc(storyHref(row.target))}"><code>${esc(row.target)}</code></a><small>${esc(row.context || t("observedSequence"))} 路 ${esc(row.sessionId || "")}</small></div>`).join("");
    return `<details class="mp-mission-story mp-runtime-observed" data-weight="context" open>
      <summary>${esc(t("runtimeTraceOverlay"))} <span>${Number(trace.storyObservationCount || 0).toLocaleString()}</span></summary>
      <p>${esc(t("runtimeTraceHint"))}</p>
      <div class="mp-order-metrics"><span><b>${Number(globalSummary.exactEventActionChains || 0).toLocaleString()}</b>${esc(t("exactRuntimeChains"))}</span><span><b>${Number(globalSummary.observedForks || 0).toLocaleString()}</b>${esc(t("observedForks"))}</span><span><b>${Number(globalSummary.observedMerges || 0).toLocaleString()}</b>${esc(t("observedMerges"))}</span><span><b>${Number(trace.questObservationPlacements || 0).toLocaleString()}</b>${esc(t("activeQuestContext"))}</span></div>
      ${edgeHtml ? `<section><h4>${esc(t("observedSequence"))}</h4><div class="mp-order-edges">${edgeHtml}</div></section>` : ""}
      ${contextOnly.length ? `<section><h4>${esc(t("runtimeObserved"))} 路 ${esc(t("notQuestAttached"))}</h4><div class="mp-runtime-observation-list">${contextOnly.map(runtimeObservationHtml).join("")}</div></section>` : ""}
      <small>${esc(t("noAuthoredPromotion"))}</small>
    </details>`;
  }

  function renderNonMissionOverview() {
    const target = byId("mp-non-mission-overview");
    if (!target) return;
    target.innerHTML = nonMissionContentHtml(
      Array.from(nonMissionContentByKey().values()),
    );
  }

  function missionPropertiesHtml() {
    const properties = state.mission?.mission?.properties || [];
    if (!properties.length) return "";
    const rows = properties.map((row) => `<article class="mp-property-row">
      <code>${esc(row.key || "?")}</code>
      <span>type ${esc(row.type ?? "?")}</span>
      <strong>${esc(JSON.stringify(row.values || []))}</strong>
    </article>`).join("");
    return `<details class="mp-mission-story mp-mission-properties">
      <summary>${esc(t("missionProperties"))} <span>${properties.length.toLocaleString()}</span></summary>
      <p>${esc(t("missionPropertiesHint"))}</p>
      <div class="mp-property-list">${rows}</div>
    </details>`;
  }

  function renderMissionSummary() {
    const target = byId("mp-mission-summary");
    if (!target || !state.mission) return;
    const mission = state.mission.mission || {};
    const row = state.index?.missions?.find((item) => item.id === mission.id) || {};
    const caseStudy = state.mission.caseStudy;
    const offlineShell = mission.offlineRecoveryShell === true;
    const aggregateShell = mission.storyAggregateShell === true;
    const shellLabel = aggregateShell ? t("storyAggregateShell") : t("offlineMissionShell");
    const shellHint = aggregateShell ? t("storyAggregateShellHint") : t("offlineMissionShellHint");
    const aggregateVariants = (mission.variantMissionIds || []).map((id) => `<button class="mp-graph-link" type="button" data-mission="${esc(id)}"><code>${esc(id)}</code></button>`).join("");
    const aggregateOriginals = (mission.relatedOriginalFiles || []).map((related) => `<small><code>${esc(related.variantMissionId || related.kind || "file")}</code> <code>${esc(related.sourceFile || "")}</code>${related.sha256 ? ` / SHA-256 <code>${esc(related.sha256)}</code>` : ""}</small>`).join("");
    const metrics = [
      [row.questCount || state.mission.nodes?.length || 0, t("quests")],
      [row.entryCount || 0, t("roots")],
      [row.fanoutCount || 0, t("branches")],
      [(row.multiPrevJoinCount || 0) + (row.activeJoinCount || 0), t("join")],
      [row.exactFinishCount || 0, t("exactFinishes")],
      [missionUnassignedStoryKeys().length, t("unassignedStory")],
    ];
    if (state.mission.runtimeTrace) metrics.push([
      state.mission.runtimeTrace.storyObservationCount || 0,
      t("runtimeObserved"),
    ]);
    target.innerHTML = `<div class="mp-summary-head">
        <div><p class="mp-summary-kicker">${esc(mission.levelId || "—")}</p><h2>${esc(missionName(mission.id))}</h2><code>${esc(mission.id)}</code></div>
        <div class="mp-summary-metrics">${metrics.map(([value, label]) => `<span><strong>${value}</strong>${esc(label)}</span>`).join("")}</div>
      </div>
      <div class="mp-case${caseStudy || offlineShell || aggregateShell ? " has-case" : ""}">
        <span class="mp-case-icon" aria-hidden="true">${caseStudy ? "◎" : "○"}</span>
        <div><strong>${esc(offlineShell || aggregateShell ? shellLabel : (caseStudy?.title || t("evidence")))}</strong><p>${esc(offlineShell || aggregateShell ? shellHint : (caseStudy?.summary || t("noCase")))}</p>${aggregateVariants ? `<div><b>${esc(t("storyAggregateVariants"))}:</b> ${aggregateVariants}</div>` : ""}${aggregateOriginals ? `<details><summary>${esc(t("storyAggregateOriginals"))} <span>${mission.relatedOriginalFiles.length}</span></summary>${aggregateOriginals}</details>` : ""}${caseStudy ? `<span class="mp-confidence">${esc(t("confidence"))}: ${esc(caseStudy.confidence)}</span>` : ""}</div>
      </div>
      ${offlineShell || aggregateShell ? "" : `<div class="mp-mission-handshake">
        <strong>${esc(t("missionHandshake"))}</strong>
        <span class="is-outbound">${esc(t("acceptRequest"))}</span>
        <i aria-hidden="true">⇄</i>
        <span class="is-inbound">${esc(t("acceptReturn"))}</span>
        <small>${esc(t("acceptCaveat"))}</small>
      </div>`}
      ${summarySectionsHtml()}`;
    applySummarySection();
  }

  // The nine evidence blocks used to render as one flat stack of collapsibles.
  // They are grouped into four named bands purely for navigation: every block
  // keeps its own summary, hints and boundary notes verbatim, and the order
  // inside each band is the order it had in the flat stack.
  const SUMMARY_SECTIONS = [
    ["structure", "summarySectionStructure", () => [missionGraphHtml(), questTopologyHtml(), storyOrderHtml(), missionPropertiesHtml()]],
    ["runtime", "summarySectionRuntime", () => [nativeRuntimeBindingsHtml(), runtimeTraceHtml()]],
    ["story", "summarySectionStory", () => [
      missionStoryConnectionsHtml(),
      missionStateDependenciesHtml(),
      envTalkContextHtml(),
    ]],
    ["queues", "summarySectionQueues", () => [unassignedStoryHtml(), runtimeContractHtml()]],
  ];

  function summarySectionsHtml() {
    const sections = SUMMARY_SECTIONS
      .map(([id, labelKey, build]) => ({ id, labelKey, body: build().filter(Boolean).join("") }))
      .filter((section) => section.body);
    if (!sections.length) return "";
    const nav = sections.length > 1
      ? `<nav class="mp-summary-nav" aria-label="${esc(t("summarySections"))}">
        <button type="button" data-mp-section="all">${esc(t("summaryFocusAll"))}</button>
        ${sections.map((section) => `<button type="button" data-mp-section="${esc(section.id)}">${esc(t(section.labelKey))}</button>`).join("")}
      </nav>`
      : "";
    return `${nav}${sections.map((section) => `<section class="mp-summary-section" data-mp-section-id="${esc(section.id)}">
      <h3 class="mp-summary-section-head">${esc(t(section.labelKey))}</h3>
      <div class="mp-summary-section-body">${section.body}</div>
    </section>`).join("")}`;
  }

  // Focusing a band never re-renders the blocks, so open/closed <details> state
  // and scroll position survive a focus change.
  function applySummarySection() {
    const target = byId("mp-mission-summary");
    if (!target) return;
    const sections = [...target.querySelectorAll("[data-mp-section-id]")];
    let active = state.summarySection || "all";
    if (active !== "all" && !sections.some((node) => node.dataset.mpSectionId === active)) active = "all";
    state.summarySection = active;
    sections.forEach((node) => {
      node.hidden = active !== "all" && node.dataset.mpSectionId !== active;
    });
    target.querySelectorAll("button[data-mp-section]").forEach((node) => {
      const on = node.dataset.mpSection === active;
      node.classList.toggle("is-active", on);
      node.setAttribute("aria-pressed", String(on));
    });
  }

  function runtimeContractHtml() {
    const contract = state.index?.runtimeContract || {};
    const stateApplication = contract.stateUpdateApplicationAudit || null;
    const extraThreadScheduler = contract.actionExtraThreadSchedulerAudit || null;
    const coveragePolicy = state.index?.storyCoverage?.policy || "";
    const dynamicSceneAudit = state.index?.storyCoverage?.dynamicSceneIdentityCrossReferences || {};
    const currentMissionId = String(state.missionId || state.mission?.mission?.id || "");
    const dynamicSceneRows = (dynamicSceneAudit.rows || []).filter((row) => (
      row
      && row.missionGraphAction === "none"
      && row.storyBinding === false
      && row.orderEvidence === false
      && (row.conditions || []).some((condition) => {
        const identifier = String(condition?.identifier || "");
        return identifier === currentMissionId
          || identifier.startsWith(`${currentMissionId}_q#`);
      })
    ));
    const missionlessNodes = (state.index?.storyCoverage?.missionlessSubGamePlaybackNodes || [])
      .filter((row) => row && row.subGameId && row.bindScriptId);
    const missionlessAudit = contract.subGameMissionRegistry?.missionlessPlaybackAudit || {};
    const receiverFrontier = state.index?.storyCoverage?.nativeReceiverActivationFrontier || {};
    const structuredIdentityCensus = receiverFrontier.structuredIdentityCarrierCensus || {};
    const receiverNodes = (state.index?.storyCoverage?.missionlessNativeRuntimeNodes || [])
      .filter((row) => row && row.eventName && row.selector && (row.storyFiles || []).length);
    const variableBridgeAudit = state.index?.storyCoverage?.postPlaybackVariableBridgeAudit || {};
    const variableBridgeSummary = variableBridgeAudit.summary || {};
    const actionNameAudit = state.index?.storyCoverage?.postPlaybackActionNameAudit || {};
    const actionNameSummary = actionNameAudit.summary || {};
    const callServerCallbackAudit = state.index?.storyCoverage?.callServerCallbackAudit || {};
    const callServerCallbackSummary = callServerCallbackAudit.summary || {};
    const callServerCallbackRoutes = callServerCallbackAudit.storyCallbackRoutes || [];
    const postPlaybackCallServerAudit = callServerCallbackAudit.postPlaybackContractAudit || {};
    const postPlaybackCallServerSummary = postPlaybackCallServerAudit.summary || {};
    const storyCoverageCounts = state.index?.storyCoverage?.counts || {};
    const storyOrderSummary = state.index?.storyOrder?.summary || {};
    const levelSequenceAudit = state.index?.storyCoverage?.postPlaybackLevelSequenceAssetAudit || {};
    const levelSequenceSummary = levelSequenceAudit.summary || {};
    const rows = [...(contract.outbound || []), ...(contract.inbound || [])];
    const localRows = (contract.localOnly || []).filter((row) => row && row.event);
    const protocolOnlyRows = (contract.protocolOnly || []).filter((row) => row && row.message);
    const missionOptionAudit = contract.missionOptionCarrierAudit || null;
    const missionPropertyAudit = contract.missionPropertyScriptPtrAudit || null;
    const trackingFilterRuntime = missionPropertyAudit?.trackingPropertyFilterRuntime || null;
    const paramSourceAudit = contract.paramSourceMissionContextAudit || null;
    const managedCarrierCensus = contract.managedIdentityCarrierCensus || null;
    const nestedCarrierCensus = contract.nestedManagedIdentityCarrierCensus || null;
    const crossSystemCensus = contract.nativeCrossSystemConsumerCensus || null;
    const eventFamilies = Object.entries(state.index?.storyCoverage?.nativePlaybackEventFamilies || {})
      .filter(([, count]) => Number(count) > 0)
      .sort((a, b) => Number(b[1]) - Number(a[1]) || a[0].localeCompare(b[0]));
    const maxEventFamilyCount = Math.max(1, ...eventFamilies.map(([, count]) => Number(count)));
    const exchangeRoleLabel = (role) => ({
      request: t("exchangeRequest"),
      request_after_local_event: t("exchangeRequestAfterLocalEvent"),
      response: t("exchangeResponse"),
      server_update_or_confirmation: t("exchangeServerUpdateOrConfirmation"),
      server_push: t("exchangeServerPush"),
      completion_acknowledgement: t("exchangeCompletionAcknowledgement"),
    })[role] || role || "";
    return `<details class="mp-contract-details" data-weight="strong"><summary>${esc(t("nativeBoundary"))} · ${rows.length} ${esc(t("exchanges"))}${localRows.length ? ` · ${localRows.length} ${esc(t("localOnlyPaths"))}` : ""}${protocolOnlyRows.length ? ` · ${protocolOnlyRows.length} ${esc(protocolLabel("capability"))}` : ""}</summary>
      <div class="mp-contract-grid">${rows.map((row) => {
        const role = exchangeRoleLabel(row.exchangeRole);
        const fields = (row.fields || []).filter(Boolean);
        const asyncLabel = row.asynchronous ? `${t("asynchronousExchange")} · ` : "";
        const expectedTraffic = [
          row.expectedConfirmation,
          row.expectedServerPush,
          ...(row.expectedServerPushes || []),
        ].filter(Boolean);
        return `<article class="mp-contract-card is-${esc(row.direction)}${row.questScoped === false ? " is-boundary-only" : ""}">
        <span>${esc(asyncLabel)}${row.direction === "client_to_server" ? "C → S" : "S → C"} · ${esc(row.confidence)}</span>
        <strong>${esc(row.message)}</strong>
        ${role || row.runtimeScope || row.questScoped === false ? `<div class="mp-contract-tags">${role ? `<b>${esc(role)}</b>` : ""}${row.runtimeScope ? `<b>${esc(row.runtimeScope)}</b>` : ""}${row.questScoped === false ? `<b>${esc(t("boundaryOnly"))} · ${esc(t("notQuestAttached"))}</b>` : ""}</div>` : ""}
        ${fields.length ? `<small><b>${esc(t("protocolFields"))}:</b> ${fields.map((field) => `<code>${esc(field)}</code>`).join(" ")}</small>` : ""}
        ${expectedTraffic.length ? `<small><b>${esc(protocolLabel("expected"))}:</b> ${expectedTraffic.map((message) => `<code>${esc(message)}</code>`).join(" ")}</small>` : ""}
        <code>${esc(row.handler)}${row.address ? ` @ ${esc(row.address)}` : ""}</code>
        <p>${esc(row.effect)}</p>
      </article>`; }).join("")}</div>
      ${stateApplication ? `<section class="mp-local-only mp-state-application-contract">
        <header><strong>${esc(t("stateApplicationContract"))}</strong><span>${Number(stateApplication.validatedCandidateCount || 0).toLocaleString()} / ${Number(stateApplication.candidateCount || 0).toLocaleString()} ${esc(t("stateApplicationValidated"))}</span></header>
        <div>${(stateApplication.rows || []).map((row) => {
          const identityOffset = row.fieldOffsets?.[row.identityField] || "?";
          const stateOffset = row.fieldOffsets?.[row.stateField] || "?";
          const lifecycle = (row.lifecycleCalls || []).map((call) => `${call.method}(${call.identityArgumentOrigin || "?"})`).join(" / ");
          return `<article class="mp-contract-card is-server_to_client">
            <span>${esc(t("serverSelectedIdentity"))} / ${esc(row.handler?.token || "")}</span>
            <strong>${esc(`${row.type || ""} (${row.messageId ?? "?"})`)}</strong>
            <div class="mp-contract-tags"><b>${esc(`${row.identityField}@${identityOffset}`)}</b><b>${esc(`${row.stateField}@${stateOffset}`)}</b>${row.clientSuccessorSelectorPresent ? "" : `<b>${esc(t("noClientSuccessorSelector"))}</b>`}</div>
            <code>${esc(`${row.handler?.symbol || ""} @ ${row.handler?.va || ""}`)}</code>
            <p><b>${esc(t("lifecycleIdentityFlow"))}:</b> ${esc(lifecycle)}</p>
          </article>`;
        }).join("")}</div>
        ${stateApplication.questStateLifecycleApplication ? `<article class="mp-contract-card is-server_to_client">
          <span>${esc(stateApplication.questStateLifecycleApplication.classification || "")}</span>
          <strong>${esc(t("questForkServerApplication"))}</strong>
          <div class="mp-contract-tags">${(stateApplication.questStateLifecycleApplication.transitions || []).map((route) => `<b>${esc(route.stateName || "?")} (${Number(route.state)}) &rarr; ${(route.reachableLifecycleCalls || []).map((call) => call.method || "?").join(" + ")}</b>`).join("")}</div>
          <code>${esc(stateApplication.questStateLifecycleApplication.message?.handler?.symbol || "")}${stateApplication.questStateLifecycleApplication.message?.handler?.va ? ` @ ${esc(stateApplication.questStateLifecycleApplication.message.handler.va)}` : ""}</code>
          <p>${esc(stateApplication.questStateLifecycleApplication.finding || "")}</p>
          <small>${esc(stateApplication.questStateLifecycleApplication.boundary || "")}</small>
        </article>` : ""}
        ${stateApplication.questEnableLifecycleApplication ? `<article class="mp-contract-card is-server_to_client">
          <span>${esc(stateApplication.questEnableLifecycleApplication.classification || "")}</span>
          <strong>${esc(t("questForkEnableApplication"))}</strong>
          <div class="mp-contract-tags">${(stateApplication.questEnableLifecycleApplication.routes || []).map((route) => {
            const packetField = stateApplication.questEnableLifecycleApplication.message?.consumedControlFields?.[0] || "isEnable";
            const runtimeField = stateApplication.questEnableLifecycleApplication.runtimeControl?.field || "isPaused";
            const calls = (route.reachableLifecycleCalls || []).map((call) => call.method || "?").join(" + ");
            return `<b>${esc(`${packetField}=${String(route.values?.[packetField])} / ${runtimeField}=${String(route.values?.[runtimeField])} → ${calls}`)}</b>`;
          }).join("")}</div>
          <code>${esc(stateApplication.questEnableLifecycleApplication.message?.handler?.symbol || "")}${stateApplication.questEnableLifecycleApplication.message?.handler?.va ? ` @ ${esc(stateApplication.questEnableLifecycleApplication.message.handler.va)}` : ""}</code>
          ${(stateApplication.questEnableLifecycleApplication.message?.unreadControlFields || []).length ? `<p><strong>${esc(t("questForkUnreadControls"))}:</strong> ${(stateApplication.questEnableLifecycleApplication.message.unreadControlFields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</p>` : ""}
          <p>${esc(stateApplication.questEnableLifecycleApplication.finding || "")}</p>
          <small>${esc(stateApplication.questEnableLifecycleApplication.boundary || "")}</small>
        </article>` : ""}
        <p class="mp-gap-policy">${esc(stateApplication.finding || "")}</p>
        ${(stateApplication.relatedOriginalFiles || []).map((related) => `<p class="mp-gap-policy"><b>${esc(t("relatedOriginalFile"))}:</b> <code>${esc(related.sourceFile || "")}</code> / SHA-256 <code>${esc(related.sha256 || "")}</code></p>`).join("")}
        <p class="mp-contract-boundary">${esc(stateApplication.boundary || "")}</p>
      </section>` : ""}
      ${extraThreadScheduler ? `<section class="mp-local-only mp-extra-thread-scheduler">
        <header><strong>${esc(t("extraThreadScheduler"))}</strong><span>${Number(extraThreadScheduler.extraThreadExecuteMethods?.length || 0).toLocaleString()} ${esc(t("extraThreadSchedulerValidated"))}</span></header>
        <div>${(extraThreadScheduler.extraThreadExecuteMethods || []).map((row) => `<article class="mp-contract-card is-local-only">
          <span>${esc(row.writerShape || "")}</span>
          <strong>${esc(row.symbol || "")}</strong>
          <div class="mp-contract-tags"><b>${esc(t("extraThreadSiblingBoundary"))}</b><b>${Number(row.directSchedulerCalls?.length || 0).toLocaleString()} ${esc(t("extraThreadDirectCalls"))}</b></div>
          <code>${esc(row.token || "")} @ ${esc(row.va || "?")}</code>
          <small>${(row.typedChildFields || []).map((field) => `<code>${esc(`${field.field}@${field.offset}`)}</code>`).join(" ")}</small>
        </article>`).join("")}</div>
        <p class="mp-gap-policy">${esc(extraThreadScheduler.finding || "")}</p>
        ${(extraThreadScheduler.relatedOriginalFiles || []).map((related) => `<p class="mp-gap-policy"><b>${esc(t("relatedOriginalFile"))}:</b> <code>${esc(related.sourceFile || "")}</code> / SHA-256 <code>${esc(related.sha256 || "")}</code></p>`).join("")}
        <p class="mp-contract-boundary">${esc(extraThreadScheduler.boundary || "")}</p>
      </section>` : ""}
      ${localRows.length ? `<section class="mp-local-only"><header><strong>${esc(t("localOnlyPaths"))}</strong><span>${esc(t("noServerExchange"))}</span></header><div>${localRows.map((row) => `<article class="mp-contract-card is-local-only"><span>LOCAL · ${esc(row.confidence || "native_proven")}</span><strong>${esc(row.event)}</strong><div class="mp-contract-tags"><b>${esc(t("noServerExchange"))}</b></div>${(row.fields || []).length ? `<small><b>${esc(t("protocolFields"))}:</b> ${(row.fields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</small>` : ""}<code>${esc(row.handler || "")}${row.address ? ` @ ${esc(row.address)}` : ""}</code><p>${esc(row.effect || "")}</p></article>`).join("")}</div></section>` : ""}
      ${protocolOnlyRows.length ? `<section class="mp-local-only mp-protocol-capabilities"><header><strong>${esc(protocolLabel("capability"))}</strong><span>${esc(protocolLabel("schemaOnly"))}</span></header><div>${protocolOnlyRows.map((row) => `<article class="mp-contract-card"><span>${esc(protocolLabel(row.boundary === "runtime_unconfirmed" ? "runtimeUnconfirmed" : "senderUnconfirmed"))}</span><strong>${esc(row.message)}</strong><div class="mp-contract-tags"><b>${esc(row.confidence || "protocol_schema_only")}</b></div>${(row.fields || []).length ? `<small><b>${esc(t("protocolFields"))}:</b> ${(row.fields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</small>` : ""}${row.possibleServerPush ? `<small><b>${esc(protocolLabel("possible"))}:</b> <code>${esc(row.possibleServerPush)}</code></small>` : ""}<p>${esc(row.effect || "")}</p></article>`).join("")}</div></section>` : ""}
      ${missionOptionAudit?.finding || missionPropertyAudit?.finding || paramSourceAudit?.finding || managedCarrierCensus?.finding || nestedCarrierCensus?.finding ? `<section class="mp-local-only mp-carrier-audits"><header><strong>${esc(t("carrierAudit"))}</strong><span>${esc(t("noGraphEdges"))}</span></header><div>
        ${missionOptionAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(missionOptionAudit.classification || "schema_only")}</span><strong>${esc(missionOptionAudit.managedCarrier?.type || "MissionOptionData")}</strong><div class="mp-contract-tags"><b>${esc(t("alternateActions"))}</b><b>${esc(t("currentAuthoredInstances"))}: ${Number(missionOptionAudit.authoredInstanceSearch?.matches || 0).toLocaleString()}</b></div><small><b>${esc(t("protocolFields"))}:</b> ${(missionOptionAudit.managedCarrier?.fields || []).map((field) => `<code>${esc(`${field.name}@${field.offset}`)}</code>`).join(" ")}</small><code>${esc(missionOptionAudit.nativeConsumer?.symbol || "")}${missionOptionAudit.nativeConsumer?.address ? ` @ ${esc(missionOptionAudit.nativeConsumer.address)}` : ""}</code><p>${esc(missionOptionAudit.finding)}</p><small>${esc(missionOptionAudit.boundary || "")}</small></article>` : ""}
        ${missionPropertyAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(missionPropertyAudit.classification || "runtime_context_only")}</span><strong>MissionRuntimeAsset.properties → MissionData.propertyDict → ParamVariable.m_scriptPtr</strong><div class="mp-contract-tags"><b>${esc(t("runtimeContextOnly"))}</b><b>${esc(t("authoredPropertyRows"))}: ${Number(missionPropertyAudit.authoredMissionProperties?.propertyRows || 0).toLocaleString()}</b>${trackingFilterRuntime ? `<b>${esc(t("trackingFilter"))}: ${Number(trackingFilterRuntime.authoredRows || 0).toLocaleString()}</b>` : ""}</div><small><b>${esc(t("protocolFields"))}:</b> <code>properties@${esc(missionPropertyAudit.managedLayout?.MissionRuntimeAsset?.properties?.offset || "")}</code> <code>propertyDic@${esc(missionPropertyAudit.managedLayout?.MissionRuntimeAsset?.propertyDic?.offset || "")}</code> <code>m_scriptPtr@${esc(missionPropertyAudit.managedLayout?.ParamVariable?.m_scriptPtr?.offset || "")}</code></small><code>${esc((missionPropertyAudit.missionPropertyWriters || []).map((row) => row.symbol).join(" · "))} → ToVariable</code><p>${esc(missionPropertyAudit.finding)}</p>${trackingFilterRuntime ? `<small><b>${esc(t("trackingFilter"))}:</b> <code>${esc(trackingFilterRuntime.evaluator?.symbol || "")}</code> → <code>${esc(trackingFilterRuntime.serverUpdate?.message || "")}</code></small><code>${esc((trackingFilterRuntime.evaluator?.flow || []).join(" → "))}</code><p>${esc(trackingFilterRuntime.finding || "")}</p><small>${esc(trackingFilterRuntime.boundary || "")}</small>` : ""}<small>${esc(missionPropertyAudit.boundary || "")}</small></article>` : ""}
        ${paramSourceAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(paramSourceAudit.classification || "implicit_context_only")}</span><strong>ParamSource.CURRENT_MISSION_ID = ${Number(paramSourceAudit.managedContract?.currentMissionId || 0)}</strong><div class="mp-contract-tags"><b>${esc(t("implicitMissionContext"))}</b><b>${esc(t("missionRuntimeUses"))}: ${Number(paramSourceAudit.authoredMissionRuntime?.currentMissionIdOccurrences || 0).toLocaleString()}</b><b>${esc(t("levelScriptUses"))}: ${Number(paramSourceAudit.authoredLevelScripts?.validatedParamTails || 0).toLocaleString()}</b></div><small><b>${esc(t("protocolFields"))}:</b> <code>Param&lt;T&gt;.paramSource ${esc(paramSourceAudit.managedContract?.paramSourceFieldToken || "")}</code> <code>get_isCurrentMissionId ${esc(paramSourceAudit.managedContract?.currentMissionGetterToken || "")}</code></small><code>${Number(paramSourceAudit.authoredLevelScripts?.levelScriptFiles || 0).toLocaleString()} LevelScripts · ${Number(paramSourceAudit.authoredLevelScripts?.uidRecords || 0).toLocaleString()} UID records</code><p>${esc(paramSourceAudit.finding)}</p><small>${esc(paramSourceAudit.boundary || "")}</small></article>` : ""}
        ${managedCarrierCensus?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(managedCarrierCensus.classification || "all_direct_managed_identity_carriers_reviewed")}</span><strong>${esc(t("directManagedCandidates"))}: ${Number(managedCarrierCensus.metadata?.directCandidateTypes || 0).toLocaleString()}</strong><div class="mp-contract-tags"><b>${esc(t("runtimeObjectCandidates"))}: ${Number(managedCarrierCensus.metadata?.runtimeObjectCandidates || 0).toLocaleString()}</b><b>${esc(t("unreviewedCandidates"))}: ${Number(managedCarrierCensus.metadata?.unreviewedCandidates || 0).toLocaleString()}</b><b>${esc(t("trackingContextOnly"))}</b></div><small><b>${esc(t("protocolFields"))}:</b> <code>missionId ${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.missionId?.token || "")}@${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.missionId?.offset || "")}</code> <code>sceneId ${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.sceneId?.token || "")}@${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.sceneId?.offset || "")}</code></small><code>${(managedCarrierCensus.trackingClosure?.nativeConsumers || []).map((row) => `${esc(row.symbol || "")}${row.address ? ` @ ${esc(row.address)}` : ""}`).join(" · ")}</code><p>${esc(managedCarrierCensus.finding)}</p><small>${esc(managedCarrierCensus.trackingClosure?.finding || "")}</small><small>${esc(managedCarrierCensus.boundary || "")}</small></article>` : ""}
        ${nestedCarrierCensus?.finding ? `<article class="mp-contract-card is-boundary-only">
          <span>${esc(nestedCarrierCensus.classification || "all_nested_managed_identity_carriers_reviewed")}</span>
          <strong>${esc(t("nestedManagedCandidates"))}: ${Number(nestedCarrierCensus.metadata?.candidateTypes || 0).toLocaleString()}</strong>
          <div class="mp-contract-tags">
            <b>${esc(t("nestedDependentCandidates"))}: ${Number(nestedCarrierCensus.metadata?.nestedDependentCandidateTypes || 0).toLocaleString()}</b>
            <b>${esc(t("maxTypedDepth"))}: ${Number(nestedCarrierCensus.metadata?.maximumShortestPathDepth || 0).toLocaleString()}</b>
            <b>${esc(t("fixedPointTraversal"))}</b>
            <b>${esc(t("unreviewedCandidates"))}: ${Number(nestedCarrierCensus.metadata?.unreviewedCandidateTypes || 0).toLocaleString()}</b>
            <b>${esc(t("runtimeEntityHubCandidates"))}: ${Number(nestedCarrierCensus.runtimeEntityHubClosure?.candidateTypes || 0).toLocaleString()}</b>
            <b>${esc(t("sharedAggregateCandidates"))}: ${Number(nestedCarrierCensus.sharedRuntimeAggregateClosure?.candidateTypes || 0).toLocaleString()}</b>
            <b>${esc(t("exactSerializedInstances"))}: ${Number(nestedCarrierCensus.runtimeEntityHubClosure?.exactIndexedTypeLabels || 0).toLocaleString()}</b>
            <b>${esc(t("indexedOriginalObjects"))}: ${Number(nestedCarrierCensus.runtimeEntityHubClosure?.indexedOriginalObjects || 0).toLocaleString()}</b>
            <b>${esc(t("truncatedScalarObjects"))}: ${Number(nestedCarrierCensus.runtimeEntityHubClosure?.objectsWithTruncatedScalars || 0).toLocaleString()}</b>
            <b>${esc(t("shippedLuaProducer"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.shippedLuaProducer?.constructorAndRegistrationCalls || 0).toLocaleString()}</b>
            <b>${esc(t("authoredSubmitItemActions"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.authoredOpenUiActions?.submitItemActions || 0).toLocaleString()}</b>
            <b>${esc(t("concreteQuestIds"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.authoredOpenUiActions?.concreteQuestIdActions || 0).toLocaleString()}</b>
            <b>${esc(t("missionSubmissionChecks"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.authoredMissionObjectives?.conditionCount || 0).toLocaleString()}</b>
            <b>${esc(t("submissionDialogCoGates"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.authoredMissionObjectives?.dialogCoGateCount || 0).toLocaleString()}</b>
            <b>${esc(t("submitOpenUiOverlap"))}: ${Number(nestedCarrierCensus.pendingItemSubmitterClosure?.authoredMissionObjectives?.dialogCoGateOpenUiOverlap || 0).toLocaleString()}</b>
          </div>
          <small><b>${esc(t("protocolFields"))}:</b> <code>m_pendingItemSubmitter ${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fields?.["DialogManager.m_pendingItemSubmitter"]?.token || "")}@${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fields?.["DialogManager.m_pendingItemSubmitter"]?.offset || "")}</code> <code>questId ${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fields?.["InventoryItemSubmitter.questId"]?.token || "")}@${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fields?.["InventoryItemSubmitter.questId"]?.offset || "")}</code></small>
          <code>${(nestedCarrierCensus.pendingItemSubmitterClosure?.methods || []).map((row) => `${esc(row.symbol || "")}${row.address ? ` @ ${esc(row.address)}` : ""} [${Number(row.nativeDirectCallerCount || 0).toLocaleString()} ${esc(t("nativeDirectCallers"))}]`).join(" 路 ")}</code>
          <code>${(nestedCarrierCensus.pendingItemSubmitterClosure?.nativeOpenUiBridge?.callers || []).map((row) => esc(row.symbol || "")).join(" + ")} → ${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.nativeOpenUiBridge?.callee?.symbol || "")}</code>
          <small><code>${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.shippedLuaProducer?.logicalPath || "")}</code></small>
          <small><code>${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fallbackParamFlow?.shippedLuaConsumer?.logicalPath || "")}</code> · ${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.fallbackParamFlow?.finding || "")}</small>
          <p>${esc(nestedCarrierCensus.finding)}</p>
          <small>${esc(nestedCarrierCensus.runtimeEntityHubClosure?.finding || "")}</small>
          <small>${esc(nestedCarrierCensus.sharedRuntimeAggregateClosure?.finding || "")}</small>
          <small>${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.finding || "")}</small>
          ${(nestedCarrierCensus.relatedOriginalFiles || []).map((related) => `<small><b>${esc(t("relatedOriginalFile"))}:</b> <code>${esc(related.sourceFile || "")}</code> / SHA-256 <code>${esc(related.sha256 || "")}</code> / ${esc(related.role || "")}</small>`).join("")}
          <small>${esc(nestedCarrierCensus.boundary || "")}</small>
        </article>` : ""}
      </div></section>` : ""}
      ${crossSystemCensus?.finding ? `<section class="mp-local-only mp-cross-system-census">
        <header><strong>${esc(t("nativeCrossSystemConsumers"))}</strong><span>${esc(t("noGraphEdges"))}</span></header>
        <div><article class="mp-contract-card is-boundary-only">
          <span>${esc(crossSystemCensus.classification || "binary_cross_system_consumers_reviewed")}</span>
          <strong>${Number(crossSystemCensus.counts?.crossSystemCallers || 0).toLocaleString()} ${esc(t("crossSystemCallers"))}</strong>
          <div class="mp-contract-tags">
            <b>${esc(t("missionDynamicConsumers"))}: ${Number(crossSystemCensus.counts?.missionStateDynamicSceneCallers || 0).toLocaleString()}</b>
            <b>${esc(t("missionLevelScriptConsumers"))}: ${Number(crossSystemCensus.counts?.missionLevelScriptCallers || 0).toLocaleString()}</b>
            <b>${esc(t("tripleSystemConsumers"))}: ${Number(crossSystemCensus.counts?.tripleOrGreaterFamilyCallers || 0).toLocaleString()}</b>
            <b>${esc(t("visualContextConsumers"))}: ${Number(crossSystemCensus.counts?.dynamicSceneStoryCallers || 0).toLocaleString()}</b>
            <b>${esc(t("unreviewedConsumers"))}: ${Number(crossSystemCensus.counts?.unreviewedCallers || 0).toLocaleString()}</b>
            <b>${esc(t("closureReachableMethods"))}: ${Number(crossSystemCensus.counts?.closureReachableMethods || 0).toLocaleString()}</b>
            <b>${esc(t("closureDirectEdges"))}: ${Number(crossSystemCensus.counts?.closureDirectEdges || 0).toLocaleString()}</b>
          </div>
          ${crossSystemCensus.deferredRefreshClosure?.chain?.length ? `<div class="mp-runtime-associations">
            <strong>${esc(t("deferredAvailabilityRefresh"))}</strong>
            <div>${crossSystemCensus.deferredRefreshClosure.chain.map((step) => `<code>${esc(step)}</code>`).join('<i aria-hidden="true">→</i>')}</div>
            <small><b>${esc(t("pendingRefreshField"))}:</b> <code>${esc(`${crossSystemCensus.deferredRefreshClosure.pendingField?.name || "?"}@${crossSystemCensus.deferredRefreshClosure.pendingField?.offset || "?"}`)}</code> <code>${esc(crossSystemCensus.deferredRefreshClosure.pendingField?.token || "")}</code></small>
            <small>${esc(t("availabilityOnlyNoOrder"))}</small>
          </div>` : ""}
          ${crossSystemCensus.missionRuntimeSurface?.finding ? `<div class="mp-runtime-associations">
            <strong>${esc(t("fullMissionRuntimeSurface"))}</strong>
            <div class="mp-contract-tags">
              <b>${esc(t("missionIdentityTypes"))}: ${Number(crossSystemCensus.missionRuntimeSurface.counts?.missionIdentityTypes || 0).toLocaleString()}</b>
              <b>${esc(t("crossSystemCallers"))}: ${Number(crossSystemCensus.missionRuntimeSurface.counts?.crossSystemCallers || 0).toLocaleString()}</b>
              <b>${esc(t("crossFamilySignatures"))}: ${Number(crossSystemCensus.missionRuntimeSurface.counts?.crossFamilyMethodSignatures || 0).toLocaleString()}</b>
              <b>${esc(t("trackingMissionWrites"))}: ${Number(crossSystemCensus.missionRuntimeSurface.counts?.trackingMissionFieldWrites || 0).toLocaleString()}</b>
              <b>${esc(t("trackingSceneWrites"))}: ${Number(crossSystemCensus.missionRuntimeSurface.counts?.trackingSceneFieldWrites || 0).toLocaleString()}</b>
            </div>
            <small><code>${esc(`missionId@${crossSystemCensus.missionRuntimeSurface.trackingFieldFlow?.fieldLayout?.missionId?.offset || "?"}`)}</code> <code>${esc(`sceneId@${crossSystemCensus.missionRuntimeSurface.trackingFieldFlow?.fieldLayout?.sceneId?.offset || "?"}`)}</code></small>
            <p>${esc(crossSystemCensus.missionRuntimeSurface.finding)}</p>
            <small>${esc(t("trackingContextOnly"))}</small>
            <small>${esc(crossSystemCensus.missionRuntimeSurface.boundary || "")}</small>
          </div>` : ""}
          ${crossSystemCensus.managedCallableSurface?.finding ? `<div class="mp-runtime-associations">
            <strong>${esc(t("managedCallableSurface"))}</strong>
            <div class="mp-contract-tags">
              <b>${esc(t("callableFields"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.callableFields || 0).toLocaleString()}</b>
              <b>${esc(t("missionCallableFields"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.missionRuntimeCallableFields || 0).toLocaleString()}</b>
              <b>${esc(t("levelScriptCallableFields"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.levelScriptCallableFields || 0).toLocaleString()}</b>
              <b>${esc(t("callableEntryMethods"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.callableEntryMethods || 0).toLocaleString()}</b>
              <b>${esc(t("directBindingCalls"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.directBindingCalls || 0).toLocaleString()}</b>
              <b>${esc(t("crossFamilyBindings"))}: ${Number(crossSystemCensus.managedCallableSurface.counts?.missionLevelScriptBindings || 0).toLocaleString()}</b>
            </div>
            ${(crossSystemCensus.managedCallableSurface.bindings || []).map((binding) => `<div><code>${esc((binding.callers || []).join(" / "))}</code><i aria-hidden="true">→</i><code>${esc((binding.entries || []).map((entry) => `${entry.owner}.${entry.method}`).join(" / "))}</code></div>`).join("")}
            <p>${esc(crossSystemCensus.managedCallableSurface.finding)}</p>
            <small>${esc(t("callableNoActivation"))}</small>
            <small>${esc(crossSystemCensus.managedCallableSurface.boundary || "")}</small>
          </div>` : ""}
          <p>${esc(crossSystemCensus.finding)}</p>
          <small>${esc(crossSystemCensus.method || "")}</small>
          ${(crossSystemCensus.relatedOriginalFiles || []).map((related) => `<small><b>${esc(t("relatedOriginalFile"))}:</b> <code>${esc(related.sourceFile || "")}</code> / SHA-256 <code>${esc(related.sha256 || "")}</code> / ${esc(related.role || "")}</small>`).join("")}
          <small>${esc(crossSystemCensus.boundary || "")}</small>
        </article></div>
      </section>` : ""}
      ${dynamicSceneRows.length ? `<section class="mp-missionless-runtime mp-dynamic-scene-crossrefs">
        <header><strong>${esc(t("dynamicSceneCrossReferences"))} <span>${dynamicSceneRows.length}</span></strong><p>${esc(t("dynamicSceneCrossReferencesHint"))}</p></header>
        <div class="mp-missionless-runtime-grid">${dynamicSceneRows.map((row) => {
          const conditions = (row.conditions || []).filter((condition) => condition?.identifier);
          const stories = (row.storyOccurrences || []).filter((story) => story?.storyKey);
          const bridge = row.localContextBridge || null;
          const bridgeDetails = (bridge?.exactTargetActions || []).flatMap((action) => (
            (action.storyControlPathLinks || []).flatMap((link) => (
              (link.sharedControlPaths || []).map((path) => ({action, link, path}))
            ))
          ));
          const triggerVolumes = (bridge?.exactTargetActions || []).flatMap((action) => (
            action.localTriggerVolumeContext?.triggerVolumes || []
          ));
          return `<article>
            <header><code>${esc(row.scene || "?")}</code><b>${esc(t(bridgeDetails.length ? "exactDynamicSceneLocalContext" : "candidateContextOnly"))}</b></header>
            <div class="mp-runtime-chain"><span>${esc(t("dynamicSceneLogicId"))}</span><code>${esc(row.logicId || "?")}</code><i aria-hidden="true">=</i><span>${esc(t("levelScriptId"))}</span><code>${esc(row.scriptId || "?")}</code><i aria-hidden="true">⇢</i><b>Story</b></div>
            <p><span>${esc(t("missionStateConditions"))}</span><code>${esc(conditions.map((condition) => `${condition.identifier} ${condition.isSame ? "=" : "!="} ${condition.state ?? "?"}`).join(" · "))}</code></p>
            <div class="mp-missionless-story-links">${stories.map((story) => `<a href="${esc(storyHref(story.storyKey))}" title="${esc(story.sourceFile || "")}"><span>${esc(story.actionName || "Story")}</span><code>${esc(story.storyKey)}</code><b aria-hidden="true">→</b><small>${esc(`${story.levelId || "?"}/${story.scriptId || "?"} @ ${story.recordOffset ?? "?"}`)}</small></a>`).join("")}</div>
            ${bridgeDetails.length ? `<div class="mp-runtime-associations"><strong>${esc(t("typedDynamicSceneTargetAction"))}</strong>${bridgeDetails.map(({action, link, path}) => `<div><span>${esc(path.eventSummary || path.headerName || t("sameSerializedControlPath"))}</span><code>${esc(`${path.headerName || "header"} #${path.headerLocalId ?? "?"}${path.triggerSlotId != null ? ` · slot ${path.triggerSlotId}` : ""}`)}</code><i aria-hidden="true">→</i><a href="${esc(storyHref(link.storyKey))}"><code>${esc(link.storyKey || "?")}</code></a><i aria-hidden="true">→</i><code>${esc(`${action.actionName || "action"}(${action.targetDynamicEntityLogicId || "?"}, visible=${String(Boolean(action.visible))})`)}</code><small>${esc(`${t("sameSerializedControlPath")}: ${(path.decorationPathLocalIds || []).map((id) => `#${id}`).join(" → ")}`)}</small></div>`).join("")}<small>${esc(t("missionActivationGap"))}</small></div>` : ""}
            ${triggerVolumes.length ? `<div class="mp-runtime-associations"><strong>${esc(t("exactLocalTriggerVolume"))}</strong>${triggerVolumes.map((volume) => `<div><span>Leader slot ${esc(volume.slotId ?? "?")}</span>${(volume.shapes || []).map((shape) => { const position = shape.position || {}; return `<code>${esc(shape.shapeType || "?")}${shape.radius != null ? ` · ${t("triggerVolumeRadius")} ${shape.radius}` : ""}</code>${position.x != null && position.y != null && position.z != null ? `<small>${esc(`${t("triggerVolumePosition")}: ${position.x}, ${position.y}, ${position.z}`)}</small>` : ""}`; }).join("")}</div>`).join("")}<small>${esc(t("noTriggerForeignIdentity"))}</small></div>` : ""}
            <div class="mp-runtime-associations"><strong>${esc(t("noMissionOwner"))}</strong><div><span>${esc(dynamicSceneAudit.classification || row.classification || "")}</span><b>${esc(t("noGraphEdges"))}</b><small>${esc(dynamicSceneAudit.boundary || dynamicSceneAudit.finding || "")}</small></div></div>
          </article>`;
        }).join("")}</div>
      </section>` : ""}
      ${eventFamilies.length ? `<section class="mp-gap-queue">
        <header><strong>${esc(t("nativeGapQueue"))}</strong><p>${esc(t("nativeGapQueueHint"))}</p></header>
        ${coveragePolicy ? `<p class="mp-gap-policy"><b>${esc(t("evidencePolicy"))}:</b> ${esc(coveragePolicy)}</p>` : ""}
        <div class="mp-gap-family-list">${eventFamilies.map(([eventName, count]) => `<div class="mp-gap-family-row"><code>${esc(eventName)}</code><span><i style="width:${Math.max(4, Math.round((Number(count) / maxEventFamilyCount) * 100))}%"></i></span><b>${Number(count).toLocaleString()}</b></div>`).join("")}</div>
      </section>` : ""}
      ${actionNameAudit.schema ? `<section class="mp-gap-queue mp-action-name-audit">
        <header><strong>${esc(t("postPlaybackActionNameAudit"))}</strong><p>${esc(t("postPlaybackActionNameBoundary"))}</p></header>
        <div class="mp-gap-family-list">
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackFormatterTags"))}</code><span></span><b>${Number(actionNameAudit.formatterTable?.summary?.recoveredTags || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackFormatterNamed"))}</code><span></span><b>${Number(actionNameSummary.formatterNamedActionPlacements || 0).toLocaleString()} / ${Number(actionNameSummary.actionPlacements || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("nativeTransitionNamedEndpoints"))}</code><span></span><b>${Number(storyOrderSummary.nativeControlPathNamedActionEndpoints || 0).toLocaleString()} / ${Number(storyOrderSummary.nativeControlPathTransitionActionEndpoints || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackOutsideActionBase"))}</code><span></span><b>${Number(actionNameSummary.unresolvedOutsideActionBaseShapes || 0).toLocaleString()}</b></div>
        </div>
        ${(actionNameAudit.unresolvedActionShapes || []).length ? `<p class="mp-gap-policy">${actionNameAudit.unresolvedActionShapes.map((row) => `<code>${esc(`${row.opcode} ×${row.count}`)}</code>`).join(" ")}</p>` : ""}
        <p class="mp-gap-policy"><code>${esc(actionNameAudit.formatterTable?.sourceFile || "")}</code> · SHA-256 <code>${esc(actionNameAudit.formatterTable?.sourceSha256 || "")}</code></p>
      </section>` : ""}
      ${callServerCallbackAudit.schema ? `<section class="mp-gap-queue mp-callserver-callback-audit">
        <header><strong>${esc(t("callServerCallbackAudit"))}</strong><p>${esc(t("callServerCallbackBoundary"))}</p></header>
        <div class="mp-gap-family-list">
          <div class="mp-gap-family-row"><code>${esc(t("callServerActionsDecoded"))}</code><span></span><b>${Number(callServerCallbackSummary.decodedCallServerActions || 0).toLocaleString()} / ${Number(callServerCallbackSummary.callServerActions || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerCallbackHeaders"))}</code><span></span><b>${Number(callServerCallbackSummary.exactCallbackHeaders || 0).toLocaleString()} / ${Number(callServerCallbackSummary.callbackOutputUids || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerStoryCallbacks"))}</code><span></span><b>${Number(callServerCallbackSummary.callbackHeadersReachingStory || 0).toLocaleString()} / ${Number(callServerCallbackSummary.callbackStoryTargets || 0).toLocaleString()} Story targets</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerDanglingCallbacks"))}</code><span></span><b>${Number(callServerCallbackSummary.unresolvedCallbackOutputs || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerUnownedSurface"))}</code><span></span><b>${Number(storyCoverageCounts.missionlessNativeRuntimePostPlaybackCallbackHeaderUids || 0).toLocaleString()} / ${Number(storyCoverageCounts.missionlessNativeRuntimePostPlaybackServerHandoffs || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerPostPlaybackContracts"))}</code><span></span><b>${Number(postPlaybackCallServerSummary.exactContracts || 0).toLocaleString()} / ${Number(postPlaybackCallServerSummary.handoffs || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerSelfUidContracts"))}</code><span></span><b>${Number(postPlaybackCallServerSummary.eventNameIdentityDistribution?.["record-uid-prefixed"] || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("callServerArgumentPaths"))}</code><span></span><b>${Number(Object.entries(postPlaybackCallServerSummary.eventArgsParamPathDistribution || {}).filter(([path]) => path !== "<null>").reduce((total, [, count]) => total + Number(count || 0), 0)).toLocaleString()}</b></div>
        </div>
        ${callServerCallbackRoutes.length ? `<div class="mp-missionless-story-links">${callServerCallbackRoutes.map((route) => `<a href="${esc(storyHref((route.storyKeys || [])[0] || ""))}"><span><code>${esc(`${route.levelId || ""}/${route.scriptId || ""}`)}</code> / <code>#${esc(route.callbackHeaderUid || "")}</code></span><small>${esc(route.sourceFile || "")}</small><b aria-hidden="true">-&gt;</b><strong>${esc((route.storyKeys || []).join(", "))}</strong></a>`).join("")}</div>` : ""}
        <p class="mp-gap-policy"><code>${esc(callServerCallbackAudit.nativeContract?.callServer?.executeMethodVa || "")}</code> / <code>${esc(callServerCallbackAudit.source || "")}</code></p>
      </section>` : ""}
      ${levelSequenceAudit.schema ? `<section class="mp-gap-queue mp-level-sequence-audit">
        <header><strong>${esc(t("postPlaybackLevelSequenceAudit"))}</strong><p>${esc(t("postPlaybackLevelSequenceBoundary"))}</p></header>
        <div class="mp-gap-family-list">
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackLevelSequenceActions"))}</code><span></span><b>${Number(levelSequenceSummary.typedActionPlacements || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackLevelSequenceAssets"))}</code><span></span><b>${Number(levelSequenceSummary.exactResolvedLevelSequenceIds || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackLevelSequenceUnresolved"))}</code><span></span><b>${Number(levelSequenceSummary.unresolvedLevelSequenceIds || 0).toLocaleString()}</b></div>
        </div>
        ${(levelSequenceAudit.unresolvedLevelSequenceIds || []).length ? `<p class="mp-gap-policy"><code>${esc(levelSequenceAudit.unresolvedLevelSequenceIds.join(", "))}</code></p>` : ""}
        ${(levelSequenceAudit.sourceIndex?.validationFailures || []).map((failure) => `<p class="mp-gap-policy"><b>${esc(t("postPlaybackLevelSequenceValidationFailure"))}:</b> <code>${esc(failure.sourceFile || "")}</code> · ${esc(failure.actual || failure.gate || "")}</p>`).join("")}
      </section>` : ""}
      ${variableBridgeAudit.schema ? `<section class="mp-gap-queue mp-variable-bridge-audit">
        <header><strong>${esc(t("postPlaybackVariableBridge"))}</strong><p>${esc(t("postPlaybackVariableBoundary"))}</p></header>
        <div class="mp-gap-family-list">
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackVariableSetterStat"))}</code><span></span><b>${Number(variableBridgeSummary.postPlaybackVariableSetters || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackVariableListeners"))}</code><span></span><b>${Number(variableBridgeSummary.exactVariableListenerRows || 0).toLocaleString()}</b></div>
          <div class="mp-gap-family-row"><code>${esc(t("postPlaybackVariableMatches"))}</code><span></span><b>${Number(variableBridgeSummary.exactSetterListenerMatches || 0).toLocaleString()}</b></div>
        </div>
        <p class="mp-gap-policy"><b>${esc(t("postPlaybackVariableClosed"))}:</b> <code>${esc(variableBridgeAudit.status || "")}</code></p>
      </section>` : ""}
      ${missionlessNodes.length ? `<section class="mp-missionless-runtime">
        <header><strong>${esc(t("missionlessSubGameNodes"))} <span>${missionlessNodes.length}</span></strong><p>${esc(t("missionlessSubGameNodesHint"))}${missionlessAudit.finding ? ` ${esc(missionlessAudit.finding)}` : ""}</p></header>
        <div class="mp-missionless-runtime-grid">${missionlessNodes.map((row) => {
          const stories = (row.storyFiles || []).filter((story) => story && story.key);
          const levelIds = [...new Set(stories.flatMap((story) => story.levelIds || []))];
          const associations = (row.associations || []).filter((association) => association && association.targetId);
          const sceneHosts = (row.sceneHosts || []).filter((host) => host && (host.sceneId || host.levelId));
          const associationLabel = (relation) => ({
            subgame_unlock_quest_prerequisite: t("unlockQuestPrerequisite"),
            subgame_unlock_mission_prerequisite: t("unlockMissionPrerequisite"),
            subgame_unlock_previous_game_mechanic: t("unlockPreviousSubGame"),
            activity_stage_mission_association: t("activityStageAssociation"),
          })[relation] || t("nonOwningCrossReference");
          return `<article>
            <header><code>${esc(row.subGameId)}</code><b>${esc(t("noMissionOwner"))}</b></header>
            <div class="mp-runtime-chain"><span>SubGame</span><i>→</i><code>${esc(row.bindScriptId)}</code><i>→</i><span>${esc(t("exactPlayback"))}</span><i>→</i><b>Story</b></div>
            <p><span>${esc(t("subGameMode"))}</span><code>${esc(row.modeId || row.runtimeType || "—")}</code></p>
            ${(row.mainTaskIds || []).length ? `<p><span>${esc(t("mainTasks"))}</span><code>${esc(row.mainTaskIds.join(", "))}</code></p>` : ""}
            ${levelIds.length ? `<p><span>${esc(t("exactLevelHost"))}</span><code>${esc(levelIds.join(", "))}</code></p>` : ""}
            ${sceneHosts.map((host) => `<p><span>${esc(t("exactSceneHost"))}</span><code>${esc([host.sceneId, host.levelId, host.dungeonSeriesId].filter(Boolean).join(" · "))}</code></p>`).join("")}
            <div class="mp-missionless-story-links">${stories.map((story) => `<a href="${esc(storyHref(story.key))}"><span>${esc(story.kind || "story")}</span><code>${esc(story.key)}</code><b aria-hidden="true">↗</b><small>${esc((story.nativeActions || []).join(" · "))}</small></a>`).join("")}</div>
            ${associations.length ? `<div class="mp-runtime-associations"><strong>${esc(t("nonOwningCrossReference"))}</strong>${associations.map((association) => `<div><span>${esc(associationLabel(association.relation))}</span><i aria-hidden="true">⇢</i><code>${esc(association.targetId)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(association.finding || "")}</small></div>`).join("")}</div>` : ""}
          </article>`;
        }).join("")}</div>
      </section>` : ""}
      ${receiverNodes.length ? `<section class="mp-missionless-runtime mp-native-receiver-runtime">
        <header><strong>${esc(t("exactReceiverNodes"))} <span>${receiverNodes.length}</span></strong><p>${esc(t("exactReceiverNodesHint"))}</p></header>
        ${structuredIdentityCensus.schema ? `<aside class="mp-structured-identity-census">
          <strong>${esc(t("structuredIdentityCensus"))}</strong><code>${esc(structuredIdentityCensus.validation?.status || "unvalidated")}</code>
          <span>${esc(t("structuredIdentityCensusCounts"))}: <b>${Number(structuredIdentityCensus.candidateFileCount || 0).toLocaleString()} / ${Number(structuredIdentityCensus.visitedRecordCount || 0).toLocaleString()} / ${Number(structuredIdentityCensus.directCarrierCount || 0).toLocaleString()}</b></span>
          <span>${esc(t("structuredIdentityReceiverMatches"))}: <b>${Number(structuredIdentityCensus.receiverMatchCount || 0).toLocaleString()} / ${Number(receiverFrontier.counts?.structuredUnreviewedIdentityCarriers || 0).toLocaleString()}</b></span>
          <small>${esc(structuredIdentityCensus.finding || "")}</small><small>${esc(structuredIdentityCensus.boundary || "")}</small>
        </aside>` : ""}
        <div class="mp-missionless-runtime-grid">${receiverNodes.map((row) => {
          const selector = row.selector || {};
          const activation = row.activationFrontier || {};
          const activationRelatedFiles = [...new Map(
            (activation.relatedOriginalFiles || [])
              .filter((related) => related && related.sourceFile)
              .map((related) => [related.sourceFile, related]),
          ).values()];
          const activationHosts = (activation.levelDataHosts || [])
            .filter((host) => host && host.fileName);
          const encounterContexts = (activation.encounterControllerContexts || [])
            .filter((context) => context && context.classification);
          const nominalHostComparison = activation.nominalMissionHostComparison || {};
          const nominalStoryCandidates = (nominalHostComparison.storyCandidates || [])
            .filter((candidate) => candidate && candidate.nominalMissionId);
          const nominalMissionHosts = (nominalHostComparison.sameLevelMissionNamedHosts || [])
            .filter((host) => host && host.fileName && host.missionId);
          const activationDungeonContexts = (activation.dungeonSceneContexts || [])
            .filter((context) => context && context.subGameId && context.sceneId);
          const activationAssociationLabel = (relation) => ({
            subgame_unlock_quest_prerequisite: t("unlockQuestPrerequisite"),
            subgame_unlock_mission_prerequisite: t("unlockMissionPrerequisite"),
            subgame_unlock_previous_game_mechanic: t("unlockPreviousSubGame"),
          })[relation] || t("nonOwningCrossReference");
          const activationTasks = (activation.decodedTaskMap?.tasks || [])
            .filter((task) => task && task.taskKey);
          const taskRuntimeAuthority = activation.taskRuntimeAuthority || {};
          const startRuntimePolicy = activation.startRuntimePolicy || {};
          const manualSelfControl = activation.manualSelfControl || {};
          const publicStateControl = activation.publicStateControl || {};
          const publicStateSources = publicStateControl.publicStateSourceFlow || {};
          const clientActiveRequestControl = activation.clientActiveRequestControl || {};
          const activeAreaFlow = clientActiveRequestControl.activeAreaFlow || {};
          const activeShapes = clientActiveRequestControl.activeShapeList?.shapes || [];
          const activeShapeSummary = activeShapes.map((shape) => {
            const center = shape.position || {};
            const centerText = `center ${center.x ?? "?"}/${center.y ?? "?"}/${center.z ?? "?"}`;
            if (shape.type === "SPHERE") return `SPHERE · ${centerText} · radius ${shape.radius ?? "?"}`;
            const size = shape.size || {};
            const rotation = shape.eulerAngles || {};
            return `${shape.type || "?"} · ${centerText} · size ${size.x ?? "?"}/${size.y ?? "?"}/${size.z ?? "?"} · rotation ${rotation.x ?? "?"}/${rotation.y ?? "?"}/${rotation.z ?? "?"}`;
          });
          const clientStartRequestControl = activation.clientStartRequestControl || {};
          const activePhaseReceiverControl = activation.activePhaseReceiverControl || {};
          const activePhaseReceiverHeader = (activePhaseReceiverControl.receiverHeaders || [])
            .find((header) => header?.listenerHeaderLocalId === selector.listenerHeaderLocalId);
          const subGameStartControl = activation.subGameStartControl || {};
          const manualSelfControls = (activation.incomingManualControls || [])
            .filter((control) => control && control.targetResolution === "current_context_self");
          const activationConsumers = (activation.missionRuntimeScriptConsumers || [])
            .filter((consumer) => consumer && (consumer.missionId || consumer.questId));
          const propertyContract = activation.authoredPropertyContract || {};
          const binaryOffset = (value) => Number.isInteger(value)
            ? `0x${value.toString(16)}`
            : (value || "?");
          const authoredPropertyNames = (propertyContract.authoredNames || []).filter(Boolean);
          const missionObservedPropertyNames = (propertyContract.missionObservedNames || []).filter(Boolean);
          const paramValue = (param) => {
            if (!param || typeof param !== "object") return "";
            if (param.value !== null && param.value !== undefined && param.value !== "") return String(param.value);
            if (param.scriptId) return String(param.scriptId);
            if (param.mode === "current_script") return "current script";
            return "";
          };
          const entityValue = (param) => {
            if (!param || typeof param !== "object") return "";
            if (param.logicId && String(param.logicId) !== "0") return `entity ${param.logicId}`;
            if (param.slotId) return `slot ${param.slotId}`;
            return "";
          };
          const conditionDetails = (condition) => {
            if (!condition || typeof condition !== "object") return "";
            const values = [
              ["mission", paramValue(condition.missionId)],
              ["dialog", paramValue(condition.dialogId)],
              ["finish", paramValue(condition.finishId)],
              ["area", paramValue(condition.areaId)],
              ["key", paramValue(condition.key)],
              ["map", paramValue(condition.mapId)],
              ["level", paramValue(condition.levelId)],
              ["scene", paramValue(condition.sceneId)],
              ["script", paramValue(condition.scriptId)],
              ["spawner", paramValue(condition.spawnerId)],
              ["entity", entityValue(condition.entity || condition.entityId)],
              ["compare", paramValue(condition.compareValue || condition.targetValue)],
              ["state", condition.targetMissionStateName || ""],
              ["expression", condition.conditionEvalString || ""],
            ].filter(([, value]) => value);
            const enemies = (condition.enemyIds?.values || [])
              .map((enemy) => entityValue(enemy))
              .filter(Boolean);
            if (enemies.length) values.push(["enemies", enemies.join(", ")]);
            return values.map(([label, value]) => `${label}=${value}`).join(" · ");
          };
          const operandSourceDetail = (source) => {
            if (!source || typeof source !== "object") return "";
            const identity = source.storyKey
              || source.missionAreaId
              || source.spawnerId
              || source.scriptId
              || source.logicId
              || source.entityDetailId
              || "";
            const slotDetail = source.slotId !== null && source.slotId !== undefined
              ? `slot ${source.slotId}${source.entityDetailId ? ` → ${source.entityDetailId}` : ""}`
              : `${identity}${source.entityDetailId && source.entityDetailId !== identity ? ` → ${source.entityDetailId}` : ""}`;
            return `${String(source.kind || "source").replaceAll("_", " ")}=${slotDetail}`;
          };
          const target = row.runtimeTarget && row.runtimeTarget.status === "exact_top_level_encounter_module_target" ? row.runtimeTarget : null;
          const battlePart = target?.battlePart || {};
          const enemySlots = [...new Set((target?.enemyPointers || []).map((pointer) => pointer?.slotId).filter(Boolean))];
          const stories = (row.storyFiles || []).filter((story) => story && story.key);
          const producers = (row.localProducerRoutes || []).filter((producer) => producer && producer.producerAssetId);
          const playbackGates = (row.playbackGates || []).filter((gate) => gate && gate.summary);
          const postPlaybackControls = (row.postPlaybackControls || [])
            .filter((control) => control && control.storyKey && (control.maximalReachablePaths || []).length);
          const selectorRows = Object.entries(selector).filter(([, value]) => value !== "" && value !== null && value !== undefined);
          const selectorValue = (value) => typeof value === "object" ? JSON.stringify(value) : String(value);
          return `<article>
            <header><code>${esc(row.eventName)}</code><b>${esc(t("noMissionOwner"))}</b></header>
            <div class="mp-runtime-chain">${target ? `<span>${esc(t("encounterModule"))}</span><code>${esc(target.levelScriptVariablePtr)}</code><i>→</i><span>LOCAL LsmPtr</span><i>→</i>` : producers.length ? `<span>${esc(t("abilityProducer"))}</span><i>→</i><code>LOCAL ${esc(selector.signalId || "signal")}</code><i>→</i>` : `<span>${esc(t("serializedSelector"))}</span><i>→</i>`}<code>${esc(selector.listenerScriptId || "—")}</code><i>→</i><span>${esc(t("exactPlayback"))}</span><i>→</i><b>Story</b></div>
            <p><span>${esc(row.serverExchange ? t("serverBackedEvent") : t("localEvent"))}</span><code>${esc(row.transport || "—")}</code></p>
            ${row.eventSummary ? `<p><span>${esc(t("evidence"))}</span><small>${esc(row.eventSummary)}</small></p>` : ""}
            <div class="mp-runtime-selector">${selectorRows.map(([field, value]) => `<span title="${esc(field)}"><b>${esc(selectorFieldLabel(field))}</b><code>${esc(selectorValue(value))}</code></span>`).join("")}</div>
            ${activation.activationClass ? `<div class="mp-runtime-associations">
              <strong>${esc(t("activationFrontier"))}</strong>
              ${activationTasks.flatMap((task) => (task.conditions || []).map((conditionRow) => {
                const condition = conditionRow.condition || {};
                const progressContract = task.progressPropertyContract || {};
                const operandSources = (conditionRow.operandSources || [])
                  .map((source) => operandSourceDetail(source))
                  .filter(Boolean);
                const missionConsumers = (conditionRow.missionRuntimeOperandConsumers || [])
                  .map((consumer) => `${consumer.missionId || "?"}/${consumer.questId || "?"}`)
                  .filter(Boolean);
                const detail = [
                  conditionDetails(condition),
                  operandSources.length ? `${t("taskOperandSources")}: ${operandSources.join(", ")}` : "",
                  missionConsumers.length ? `${t("taskMissionConsumers")}: ${missionConsumers.join(", ")}` : "",
                ].filter(Boolean).join(" · ");
                const taskSources = [
                  task.taskExtraInfo?.taskTitleKey || "",
                  ...(task.subGameMainTaskBindings || []).map((binding) => `SubGame ${binding.subGameId || "?"}`),
                  ...(task.missionRuntimeTaskConsumers || []).map((consumer) => `${t("taskMissionConsumers")} ${consumer.missionId || "?"}/${consumer.questId || "?"}`),
                  progressContract.status === "validated"
                    ? `${t("taskProgressProperties")} ${progressContract.matchedPropertyCount || 0}/${progressContract.expectedPropertyCount || 0}`
                    : "",
                ].filter(Boolean);
                const taskLabel = `${t("taskConditionEvidence")} · ${task.taskKey} / objective ${conditionRow.objectiveEnum ?? "?"}${taskSources.length ? ` · ${taskSources.join(" · ")}` : ""}`;
                return `<div><span>${esc(taskLabel)}</span><i aria-hidden="true">→</i><code>${esc(condition.type || "unresolved")}</code><b>${esc(condition.conditionUnionTag || "")}</b>${detail ? `<small>${esc(detail)}</small>` : ""}</div>`;
              })).join("")}
              ${activationTasks.length ? `<small>${esc(t("taskConditionBoundary"))}</small>` : ""}
              ${taskRuntimeAuthority.validation?.status === "validated" ? `<div class="is-boundary"><span>${esc(t("taskRuntimeAuthority"))}</span><i aria-hidden="true">↔</i><code>${esc((taskRuntimeAuthority.identityFields || []).join(" + "))}</code><b>${esc((taskRuntimeAuthority.messages || []).map((message) => message.messageId).join(" / "))}</b><small>${esc(taskRuntimeAuthority.finding || t("taskRuntimeAuthorityBoundary"))}</small></div><small>${esc(taskRuntimeAuthority.evidenceBoundary || t("taskRuntimeAuthorityBoundary"))}</small>` : ""}
              <div><span>${esc(t("activationClass"))}</span><i aria-hidden="true">→</i><code>${esc(String(activation.activationClass).replaceAll("_", " "))}</code><b>${esc(t("noMissionOwner"))}</b></div>
              <div><span>${esc(t("startPolicy"))}</span><i aria-hidden="true">→</i><code>${esc(`${activation.startTypeName || "unresolved"} · shapes ${activation.startShapeListStatus || "unresolved"}/${activation.startShapeListCount ?? 0} · taskMap ${activation.taskMapStatus || "unresolved"}/${activation.taskMapCount ?? 0}`)}</code></div>
              ${startRuntimePolicy.validation?.status === "validated" ? `<div><span>${esc(t("binaryStartPolicy"))}</span><i aria-hidden="true">→</i><code>Active + unfinished + SameWithActive</code><b>PreStart</b><small>${esc([startRuntimePolicy.finding || "", `UpdateRuntimeState ${startRuntimePolicy.methods?.UpdateRuntimeState?.methodPointerVa || ""}`, `startType=${startRuntimePolicy.startTypeGates?.SameWithActive?.comparedValue ?? "?"}`, `state=${startRuntimePolicy.activeStateGate?.comparedValue ?? "?"}`, `PreStart=${startRuntimePolicy.preStartTransition?.runtimeStateValue ?? "?"}`].filter(Boolean).join(" · "))}</small></div><small>${esc(startRuntimePolicy.evidenceBoundary || t("binaryStartPolicyBoundary"))}</small>` : ""}
              ${manualSelfControl.validation?.status === "validated" && manualSelfControls.length ? manualSelfControls.map((control) => `<div><span>${esc(t("binaryManualSelfControl"))}</span><i aria-hidden="true">→</i><code>CURRENT_LEVEL_ID + CURRENT_SCRIPT_ID</code><b>ManualStart → PreStart</b><small>${esc([manualSelfControl.finding || "", `event local ${control.headerLinkedEvent?.localId ?? "?"} → action local ${control.localId ?? "?"}`, `sources=${control.parameterSources?.levelId ?? "?"}/${control.parameterSources?.scriptId ?? "?"}`, `Execute ${manualSelfControl.methods?.Execute?.methodPointerVa || ""}`, `ManualStart ${manualSelfControl.methods?.ManualStart?.methodPointerVa || ""}`].filter(Boolean).join(" · "))}</small></div>`).join("") + `<small>${esc(manualSelfControl.evidenceBoundary || t("binaryManualSelfControlBoundary"))}</small>` : ""}
              ${publicStateControl.validation?.status === "validated" ? `<div class="is-boundary"><span>${esc(t("binaryPublicStateControl"))}</span><i aria-hidden="true">→</i><code>SC ${esc(publicStateControl.selfSceneInfoMessageId ?? "?")} levelScripts[] → ServerSync | SC ${esc(publicStateControl.stateNotifyMessageId ?? "?")} state notify → UpdateState</code><b>server → public state</b><small>${esc([`snapshot ${publicStateControl.selfSceneInfoHandlerMethod?.methodPointerVa || "?"}`, `incremental ${publicStateControl.handlerMethod?.methodPointerVa || "?"}`, `entry callers ${(publicStateSources.managerStateShortDirectCallers || []).length}`, `state writers ${(publicStateSources.publicStateSetterDirectCallers || []).length}`, publicStateControl.publicStateFlow?.setterBeforeRuntimeEvaluation ? "state setter → runtime evaluation" : "unresolved state application"].join(" · "))}</small></div><small>${esc(publicStateControl.evidenceBoundary || t("binaryPublicStateControlBoundary"))}</small>` : ""}
              ${clientActiveRequestControl.status === "validated" ? `<div class="is-boundary"><span>${esc(t("binaryClientActiveRequest"))}</span><i aria-hidden="true">→</i><code>${esc((clientActiveRequestControl.runtimePath || []).join(" → "))}</code><b>${esc(clientActiveRequestControl.levelScriptTypeName || "?")}</b><small>${esc([`type=${clientActiveRequestControl.levelScriptType ?? "?"}`, `type gate +${clientActiveRequestControl.selectorFlow?.inactiveLevelScriptTypeCallOffset ?? "?"}`, `area gate +${clientActiveRequestControl.selectorFlow?.activeAreaGateCallOffset ?? "?"}`, `active=true +${clientActiveRequestControl.selectorFlow?.activeTrueRequestCallOffset ?? "?"}`].join(" · "))}</small></div><small>${esc(clientActiveRequestControl.evidenceBoundary || t("binaryClientActiveRequestBoundary"))}</small>` : ""}
              ${clientActiveRequestControl.spatialGateStatus === "validated_runtime_position_dependent" && activeShapeSummary.length ? `<div class="is-boundary"><span>${esc(t("binaryActiveVolume"))}</span><i aria-hidden="true">→</i><code>${esc(activeShapeSummary.join(" | "))}</code><b>${esc(clientActiveRequestControl.activeShapeList?.status || "?")}</b><small>${esc([`active test +${activeAreaFlow.activeShapeTestCallOffset ?? "?"}`, `outside test +${activeAreaFlow.outsideShapeTestCallOffset ?? "?"}`, `clear +${activeAreaFlow.outsideShapeHitClearOffset ?? "?"}`, `set true +${activeAreaFlow.withinTrueSetterOffset ?? "?"}`].join(" · "))}</small></div><small>${esc(t("binaryActiveVolumeBoundary"))}</small>` : ""}
              ${clientStartRequestControl.validation?.status === "validated" ? `<div class="is-boundary"><span>${esc(t("binaryClientStartRequest"))}</span><i aria-hidden="true">→</i><code>ManualStart flag → PreStart → CS ${esc(clientStartRequestControl.startRequestMessageId ?? "?")}</code><b>PreStartActionRunning</b><small>${esc([`ManualStart ${clientStartRequestControl.manualStartMethod?.methodPointerVa || "?"}`, `runtime sender ${clientStartRequestControl.runtimeSendStartMethod?.methodPointerVa || "?"}`, `network sender ${clientStartRequestControl.networkSetStartMethod?.methodPointerVa || "?"}`, `direct network callers ${clientStartRequestControl.clientRequestFlow?.networkStartDirectCallerCount ?? "?"}`, `runtime request args ${(clientStartRequestControl.clientRequestFlow?.runtimeStartArguments || []).join("/")}`].join(" · "))}</small></div><small>${esc(t("binaryClientStartRequestBoundary"))}</small>` : ""}
              ${activePhaseReceiverControl.status === "validated" && activePhaseReceiverHeader ? `<div class="is-boundary"><span>${esc(t("binaryActivePhaseReceiver"))}</span><i aria-hidden="true">→</i><code>Setup → ActiveBegin → Active(${esc(activePhaseReceiverHeader.triggerActiveDuring ?? "?")})</code><b>header #${esc(activePhaseReceiverHeader.listenerHeaderLocalId)}</b><small>${esc([activePhaseReceiverHeader.headerName || "receiver", `action #${activePhaseReceiverHeader.nextActionLocalId ?? "?"}`, `register +${activePhaseReceiverControl.runtimeFlow?.setupRegisterTriggerCallOffsets?.[0] ?? "?"}`, `enable +${activePhaseReceiverControl.runtimeFlow?.activePhaseEnableCallOffsets?.[0] ?? "?"}`, `Setup ${activePhaseReceiverControl.methods?.Setup?.methodPointerVa || "?"}`].join(" · "))}</small></div><small>${esc(activePhaseReceiverControl.evidenceBoundary || t("binaryActivePhaseReceiverBoundary"))}</small>` : ""}
              ${subGameStartControl.validation?.status === "validated" ? `<div><span>${esc(t("binarySubGameManualStart"))}</span><i aria-hidden="true">→</i><code>SubGame id → bindScriptId → LevelScript</code><b>ManualStart</b><small>${esc([`interaction ${subGameStartControl.challengeMethod?.methodPointerVa || "?"}`, `ManualStart ${subGameStartControl.manualStartMethod?.methodPointerVa || "?"}`, `fields ${binaryOffset(subGameStartControl.fieldOffsets?.["challengeStartPoint.m_subGameId"])}/${binaryOffset(subGameStartControl.fieldOffsets?.["subGameInstanceData.bindScriptId"])}`, subGameStartControl.subGameInteractionFlow?.callsInCarrierOrder ? "lookup calls ordered" : "lookup order unresolved"].join(" · "))}</small></div><small>${esc(subGameStartControl.evidenceBoundary || t("binarySubGameManualStartBoundary"))}</small>` : ""}
              ${activationRelatedFiles.map((related) => `<div><span>${esc(t("relatedOriginalFile"))}</span><i aria-hidden="true">→</i><code>${esc(related.sourceFile)}</code><b>${esc(String(related.kind || "source").replaceAll("_", " "))}</b><small>${esc([String(related.relationship || "").replaceAll("_", " "), related.sha256 ? `SHA-256 ${related.sha256}` : ""].filter(Boolean).join(" · "))}</small></div>`).join("")}
              ${encounterContexts.flatMap((context) => [
                `<div><span>${esc(t("encounterController"))}</span><i aria-hidden="true">→</i><code>${esc(context.runtimeType || "EncounterBase<T>")}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(`${context.dataType || "EncounterData"} · ${context.mappingId || ""}`)}</small></div>`,
                `<div><span>${esc(t("encounterModuleNamespace"))}</span><i aria-hidden="true">→</i><code>${esc(context.moduleId || "—")}</code><b>${esc(context.moduleIdMatchesReceiverScript ? t("moduleMatchesReceiver") : t("relatedModuleNamespace"))}</b><small>${esc(`receiver LevelScript ${context.receiverScriptId || selector.listenerScriptId || "—"}`)}</small></div>`,
                ...(context.spawnerId ? [`<div><span>${esc(t("encounterSpawner"))}</span><i aria-hidden="true">→</i><code>${esc(context.spawnerId)}</code><b>${esc(String(context.spawnerId) === "0" ? t("noConfiguredSpawner") : t("nonOwningCrossReference"))}</b></div>`] : []),
                ...(context.relatedFiles || []).filter((related) => related && related.sourceFile).map((related) => `<div><span>${esc(t("relatedOriginalFile"))}</span><i aria-hidden="true">→</i><code>${esc(related.sourceFile)}</code><b>${esc(String(related.kind || "source").replaceAll("_", " "))}</b><small>${esc(String(related.relationship || "").replaceAll("_", " "))}</small></div>`),
              ]).join("")}
              ${encounterContexts.length ? `<small>${esc(t("encounterControllerBoundary"))}</small>` : ""}
              ${activationHosts.map((host) => `<div><span>${esc(t("levelDataContainer"))}</span><i aria-hidden="true">→</i><code>${esc(host.fileName)}</code><b>${esc(host.hostMissionId || "generic")}</b><small>${esc(`${host.dictionaryEntryCount ?? "?"} LevelScripts`)}</small></div>`).join("")}
              ${nominalStoryCandidates.map((candidate) => {
                const matchingHosts = nominalMissionHosts.filter((host) => host.missionId === candidate.nominalMissionId);
                const excludedHosts = matchingHosts.filter((host) => host.dictionaryValidated && !host.receiverScriptPresent);
                const label = excludedHosts.length ? t("nominalMissionHostExcludes") : t("noSameLevelNominalMissionHost");
                const detail = excludedHosts.length
                  ? excludedHosts.map((host) => `${host.fileName} · ${host.dictionaryEntryCount ?? "?"} LevelScripts`).join(" · ")
                  : t("nominalMissionCandidateBoundary");
                return `<div class="is-boundary"><span>${esc(t("nominalMissionHostCheck"))}</span><i aria-hidden="true">→</i><code>${esc(`${candidate.storyKey || "Story"} → ${candidate.nominalMissionId}`)}</code><b>${esc(label)}</b><small>${esc(detail)}</small></div>`;
              }).join("")}
              ${nominalStoryCandidates.length ? `<small>${esc(t("nominalMissionCandidateBoundary"))}</small>` : ""}
              ${(activation.subGameIds || []).map((subGameId) => `<div><span>SubGame bindScriptId</span><i aria-hidden="true">→</i><code>${esc(subGameId)}</code><b>${esc(t("noMissionOwner"))}</b></div>`).join("")}
              ${activationDungeonContexts.flatMap((context) => [
                `<div><span>${esc(t("dungeonSceneContext"))}</span><i aria-hidden="true">→</i><code>${esc(`${context.subGameId} · ${context.sceneId}`)}</code><b>${esc(context.receiverIsBoundScript ? t("boundReceiverScript") : t("siblingReceiverScript"))}</b><small>${esc([context.dungeonSeriesId, `bindScriptId ${context.bindScriptId}`].filter(Boolean).join(" · "))}</small></div>`,
                ...(context.dungeonMissionContext?.missionId ? [`<div class="is-boundary"><span>${esc(t("dungeonMissionShellContext"))}</span><i aria-hidden="true">⇢</i><code>${esc(context.dungeonMissionContext.missionId)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(context.dungeonMissionContext.finding || "")}</small></div>`] : []),
                ...(context.associations || []).filter((association) => association && association.targetId).map((association) => `<div class="is-boundary"><span>${esc(activationAssociationLabel(association.relation))}</span><i aria-hidden="true">⇢</i><code>${esc(association.targetId)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(association.finding || "")}</small></div>`),
              ]).join("")}
              ${activationDungeonContexts.length ? `<small>${esc(t("dungeonSceneBoundary"))}</small>` : ""}
              ${authoredPropertyNames.length ? `<div class="is-boundary"><span>${esc(t("authoredPropertyContract"))}</span><i aria-hidden="true">⇢</i><code>${esc(authoredPropertyNames.join(", "))}</code><b>${esc(missionObservedPropertyNames.length ? t("missionObservedProperty") : t("unobservedProperty"))}</b>${missionObservedPropertyNames.length ? `<small>${esc(missionObservedPropertyNames.join(", "))}</small>` : ""}</div><small>${esc(propertyContract.evidenceBoundary || t("propertyContractBoundary"))}</small>` : ""}
              ${(activation.serializedMissionRuntimeIdTokens || []).length ? `<div><span>${esc(t("serializedMissionIdTokens"))}</span><i aria-hidden="true">→</i><code>${esc(activation.serializedMissionRuntimeIdTokens.join(", "))}</code><b>${esc(t("nonOwningCrossReference"))}</b></div>` : ""}
              ${activationConsumers.map((consumer) => {
                const identity = [consumer.missionId, consumer.questId].filter(Boolean).join("/");
                const objective = consumer.objectiveIndex !== null && consumer.objectiveIndex !== undefined
                  ? ` · objective ${consumer.objectiveIndex}`
                  : "";
                const conditions = (consumer.conditionTypes || []).filter(Boolean).join(", ");
                const propertyKeys = (consumer.propertyKeys || []).filter(Boolean);
                return `<div class="is-boundary"><span>${esc(t("questObserver"))}</span><i aria-hidden="true">⇢</i><code>${esc(`${identity}${objective}`)}</code><b>${esc(t("observationOnly"))}</b><small>${esc([conditions, propertyKeys.length ? `properties=${propertyKeys.join(", ")}` : "", consumer.evidenceBoundary || t("questObserverBoundary")].filter(Boolean).join(" · "))}</small></div>${consumer.sourceFile ? `<div><span>${esc(t("relatedOriginalFile"))}</span><i aria-hidden="true">→</i><code>${esc(consumer.sourceFile)}</code><b>MissionRuntimeAsset</b><small>${esc(consumer.pipelineSourceFile || "")}</small></div>` : ""}`;
              }).join("")}
              <small>${esc(`${t("missionRuntimeConsumers")}: ${activation.missionRuntimeObjectiveConsumerCount ?? 0} · ${t("literalCrossScriptControls")}: ${activation.incomingLiteralCrossControlCount ?? 0} · ${t("exactStartShapeAreaMatches")}: ${activation.exactStartShapeMissionAreaMatchCount ?? 0}`)}</small>
            </div>` : ""}
            ${playbackGates.length ? `<div class="mp-runtime-associations mp-playback-gates"><strong>${esc(t("playbackGate"))}</strong>${playbackGates.map((gate) => `<div><span>${esc(t("playbackGateTrue"))}</span><i aria-hidden="true">?</i><code>${esc(gate.summary)}</code><b>${esc(String(gate.predicateType || "predicate").replaceAll(/([a-z])([A-Z])/g, "$1 $2"))}</b><small>${esc(`${gate.sourceFile || ""} · header #${gate.headerLocalId ?? "?"} → getter #${gate.getterLocalId ?? "constant"} → action #${gate.headerNextLocalId ?? "?"} · ${gate.predicateNodeCount ?? 1} getter node${gate.predicateNodeCount === 1 ? "" : "s"} · depth ${gate.predicateDepth ?? 1}`)}</small></div>`).join("")}<small>${esc(t("playbackGateBoundary"))}</small></div>` : ""}
            ${postPlaybackControls.length ? `<div class="mp-runtime-associations mp-post-playback"><strong>${esc(t("postPlaybackControl"))}</strong>${postPlaybackControls.map((control) => {
              const pathRows = (control.maximalReachablePaths || []).map((path) => {
                const chain = (path || []).map((step) => `${step.actionName || step.recordClass || step.opcode || "action"} #${step.localId ?? "?"}`).join(" → ");
                return `<div><span><a href="${esc(storyHref(control.storyKey))}"><code>${esc(control.storyKey)}</code></a> #${esc(control.playbackLocalId ?? "?")}</span><i aria-hidden="true">→</i><code>${esc(chain)}</code></div>`;
              }).join("");
              const branches = (control.branchPointLocalIds || []).length ? `<div><span>${esc(t("postPlaybackBranch"))}</span><i aria-hidden="true">→</i><code>${esc(control.branchPointLocalIds.map((id) => `#${id}`).join(", "))}</code></div>` : "";
              const handoffs = (control.serverHandoffs || []).map((handoff) => {
                const handoffContract = handoff.serializedContract || {};
                const eventArgs = handoffContract.eventArgsPtr || {};
                const contractDetail = handoffContract.eventName
                  ? `${handoffContract.eventName} · args=${eventArgs.pathValue || "none"}/${eventArgs.path || "no foreign path"} · custom=${Number(Boolean(handoffContract.useCustomEvent))} wait=${Number(Boolean(handoffContract.waitForCallback))} payload=${Number(Boolean(handoffContract.withEventArgs))}`
                  : (handoff.callbackCorrelationLabels || []).join(", ") || `#${handoff.localId ?? "?"}`;
                const sources = (handoff.relatedOriginalFiles || []).filter((related) => related?.sourceFile);
                return `<div class="is-boundary"><span>${esc(t("postPlaybackServerHandoff"))}</span><i aria-hidden="true">→</i><code>${esc(contractDetail)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(`${t("callServerSerializedContract")} · ${handoff.contractStatus || "unresolved"}`)}</small></div>${sources.map((related) => `<div><span>${esc(t("relatedOriginalFile"))}</span><i aria-hidden="true">→</i><code>${esc(related.sourceFile)}</code><b>CallServer #${esc(handoff.localId ?? "?")}</b><small>${esc(String(related.relationship || "").replaceAll("_", " "))}</small></div>`).join("")}`;
              }).join("");
              const sequenceFiles = (control.actions || []).flatMap((action) => (action.levelSequenceReferences || []).map((reference) => ({action, reference})));
              const sequenceRows = sequenceFiles.map(({action, reference}) => reference.sourceFile
                ? `<div><span>${esc(t("postPlaybackLevelSequenceFile"))}</span><i aria-hidden="true">→</i><code>${esc(reference.levelSequenceId || "")}</code><b>${esc(action.actionName || "LevelSequence")}</b><small>${esc(`${reference.sourceFile}${reference.pathId ? ` · ${reference.pathId}` : ""}`)}</small></div>`
                : `<div class="is-boundary"><span>${esc(t("postPlaybackLevelSequenceUnresolved"))}</span><i aria-hidden="true">⇥</i><code>${esc(reference.levelSequenceId || "")}</code><b>${esc(action.actionName || "LevelSequence")}</b></div>`).join("");
              return `${pathRows}${branches}${handoffs}${sequenceRows}<small>${esc(control.sourceFile || "")}</small>`;
            }).join("")}<small>${esc(t("postPlaybackBoundary"))}</small></div>` : ""}
            ${target ? `<div class="mp-runtime-associations mp-runtime-target"><strong>${esc(t("exactRuntimeTarget"))}</strong><div><span>${esc(t("modulePointer"))}</span><i aria-hidden="true">→</i><code>${esc(target.levelScriptVariablePtr)}</code><b>${esc(target.moduleType || t("encounterModule"))}</b><small>${esc(`${target.sourceFile || ""} @ ${target.dictionaryOffsetHex || "—"} · union ${target.moduleUnionTag || "—"}/${target.serializedMemberCount || "—"}`)}</small></div><div><span>${esc(t("activationSlot"))}</span><i aria-hidden="true">→</i><code>${esc(target.activateTriggerSlotId ?? "—")}</code><b>LOCAL</b><small>${esc(`${t("battleExitSlot")}: ${battlePart.exitTriggerSlotId ?? "—"}${enemySlots.length ? ` · ${t("localEntitySlots")}: ${enemySlots.join(", ")}` : ""}`)}</small></div><div class="is-boundary"><span>${esc(t("missingOwnershipBridge"))}</span><i aria-hidden="true">⇥</i><code>missionId / questId / MissionArea</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(row.ownershipBoundary || target.ownershipBoundary || "")}</small></div><small>${esc(t("noServerRequestOrReturn"))}</small></div>` : ""}
            ${producers.length ? `<div class="mp-runtime-associations"><strong>${esc(t("localProducerChain"))}</strong>${producers.map((producer) => `<div><span>${esc(`${t("abilityProducer")} · ${producer.producerDomain || "AbilityActionData"}`)}</span><i aria-hidden="true">→</i><code>${esc(producer.producerAssetId)}</code><b>LOCAL · ${esc(t("noServerRequestOrReturn"))}</b><small>${esc(`${t("literalSignal")}: ${producer.receiverSignalId || "—"} / ${producer.doubleValue?.value ?? "—"} · ${producer.actionUnionTag || ""}/${producer.serializedMemberCount || ""} · ${producer.producerSourceFile || ""} @ ${producer.actionOffset || "—"}`)}</small></div>`).join("")}<small>${esc(t("producerBoundaryHint"))}</small></div>` : ""}
            <div class="mp-missionless-story-links">${stories.map((story) => `<a href="${esc(storyHref(story.key))}"><span>${esc(story.kind || "story")}</span><code>${esc(story.key)}</code><b aria-hidden="true">→</b><small>${esc((story.nativeActions || []).join(" · "))}</small></a>`).join("")}</div>
          </article>`;
        }).join("")}</div>
      </section>` : ""}
      <p class="mp-contract-boundary">${esc(contract.authority?.boundary || "")}</p>
    </details>`;
  }

  function isHiddenQuest(node) {
    return Number(node.showMode) === 1000;
  }

  function graphNodes() {
    const showHidden = Boolean(byId("mp-show-hidden")?.checked);
    return (state.mission?.nodes || []).filter((node) => showHidden || !isHiddenQuest(node));
  }

  function computeRanks(nodes, edges) {
    const ids = new Set(nodes.map((node) => node.id));
    const incoming = new Map(nodes.map((node) => [node.id, []]));
    const outgoing = new Map(nodes.map((node) => [node.id, []]));
    for (const edge of edges) {
      if (edge.type !== "predecessor" || !ids.has(edge.source) || !ids.has(edge.target)) continue;
      incoming.get(edge.target).push(edge.source);
      outgoing.get(edge.source).push(edge.target);
    }
    const indegree = new Map([...incoming].map(([id, values]) => [id, values.length]));
    const rank = new Map(nodes.map((node) => [node.id, 0]));
    const queue = nodes.filter((node) => indegree.get(node.id) === 0).sort(nodeSort).map((node) => node.id);
    const visited = new Set();
    while (queue.length) {
      const id = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);
      for (const target of outgoing.get(id) || []) {
        rank.set(target, Math.max(rank.get(target) || 0, (rank.get(id) || 0) + 1));
        indegree.set(target, (indegree.get(target) || 1) - 1);
        if (indegree.get(target) === 0) queue.push(target);
      }
    }
    for (const node of nodes) {
      if (visited.has(node.id)) continue;
      const parentRanks = (incoming.get(node.id) || []).map((id) => rank.get(id) || 0);
      rank.set(node.id, parentRanks.length ? Math.max(...parentRanks) + 1 : 0);
    }
    return rank;
  }

  function nodeSort(a, b) {
    const aMain = Number.isFinite(a.mainPathOrder) ? a.mainPathOrder : Number.MAX_SAFE_INTEGER;
    const bMain = Number.isFinite(b.mainPathOrder) ? b.mainPathOrder : Number.MAX_SAFE_INTEGER;
    return aMain - bMain || Number(a.flowIndex || 0) - Number(b.flowIndex || 0) || naturalQuestNumber(a.id) - naturalQuestNumber(b.id) || String(a.id).localeCompare(String(b.id));
  }

  function computeLayout(nodes, edges) {
    const rankMap = computeRanks(nodes, edges);
    const maxRank = Math.max(0, ...rankMap.values());
    const requested = byId("mp-orientation")?.value || "auto";
    const orientation = requested === "auto" ? (maxRank > 14 ? "tb" : "lr") : requested;
    const lanes = [...new Set(nodes.map((node) => Number(node.flowIndex || 0)))].sort((a, b) => a - b);
    const groups = new Map();
    for (const node of [...nodes].sort(nodeSort)) {
      const key = `${rankMap.get(node.id) || 0}:${Number(node.flowIndex || 0)}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    }
    const positions = new Map();
    const bands = [];
    let width = 0;
    let height = 0;
    if (orientation === "lr") {
      const laneHeights = new Map();
      for (const lane of lanes) {
        let maxInRank = 1;
        for (let rank = 0; rank <= maxRank; rank += 1) maxInRank = Math.max(maxInRank, (groups.get(`${rank}:${lane}`) || []).length);
        laneHeights.set(lane, Math.max(186, maxInRank * (CARD_H + 18) + 66));
      }
      const laneTop = new Map();
      let top = 30;
      for (const lane of lanes) { laneTop.set(lane, top); top += laneHeights.get(lane); }
      width = Math.max(780, 150 + (maxRank + 1) * (CARD_W + 56));
      height = top + 30;
      for (const lane of lanes) bands.push({ lane, x: 20, y: laneTop.get(lane), width: width - 40, height: laneHeights.get(lane), orientation });
      for (const node of nodes) {
        const rank = rankMap.get(node.id) || 0;
        const lane = Number(node.flowIndex || 0);
        const group = groups.get(`${rank}:${lane}`) || [];
        const index = group.findIndex((item) => item.id === node.id);
        positions.set(node.id, { x: 126 + rank * (CARD_W + 56), y: laneTop.get(lane) + 48 + index * (CARD_H + 18), rank, lane });
      }
    } else {
      const laneWidths = new Map();
      for (const lane of lanes) {
        let maxInRank = 1;
        for (let rank = 0; rank <= maxRank; rank += 1) maxInRank = Math.max(maxInRank, (groups.get(`${rank}:${lane}`) || []).length);
        laneWidths.set(lane, Math.max(268, maxInRank * (CARD_W + 22) + 68));
      }
      const laneLeft = new Map();
      let left = 30;
      for (const lane of lanes) { laneLeft.set(lane, left); left += laneWidths.get(lane); }
      width = left + 30;
      height = Math.max(680, 130 + (maxRank + 1) * (CARD_H + 54));
      for (const lane of lanes) bands.push({ lane, x: laneLeft.get(lane), y: 20, width: laneWidths.get(lane), height: height - 40, orientation });
      for (const node of nodes) {
        const rank = rankMap.get(node.id) || 0;
        const lane = Number(node.flowIndex || 0);
        const group = groups.get(`${rank}:${lane}`) || [];
        const index = group.findIndex((item) => item.id === node.id);
        positions.set(node.id, { x: laneLeft.get(lane) + 42 + index * (CARD_W + 22), y: 112 + rank * (CARD_H + 54), rank, lane });
      }
    }
    return { orientation, positions, bands, width, height, maxRank };
  }

  function renderGraph() {
    const plane = byId("mp-plane");
    const nodesTarget = byId("mp-nodes");
    const edgesTarget = byId("mp-edges");
    const lanesTarget = byId("mp-lanes");
    const empty = byId("mp-empty-graph");
    if (!plane || !nodesTarget || !edgesTarget || !lanesTarget || !state.mission) return;
    const nodes = graphNodes();
    const ids = new Set(nodes.map((node) => node.id));
    if (nodes.length && !ids.has(state.selectedQuestId)) {
      state.selectedQuestId = nodes.find((node) => node.mainPath)?.id || nodes[0].id;
      requestAnimationFrame(renderInspector);
    }
    const showDependencies = Boolean(byId("mp-show-dependencies")?.checked);
    const edges = (state.mission.edges || []).filter((edge) => ids.has(edge.source) && ids.has(edge.target) && (showDependencies || edge.type !== "condition_dependency"));
    if (!nodes.length) {
      state.selectedQuestId = "";
      nodesTarget.innerHTML = "";
      edgesTarget.innerHTML = "";
      lanesTarget.innerHTML = "";
      const meta = byId("mp-graph-meta");
      if (meta) meta.textContent = `0 ${t("quests")} · 0 edges`;
      plane.hidden = true;
      empty.hidden = false;
      empty.textContent = t("noVisibleQuests");
      return;
    }
    plane.hidden = false;
    empty.hidden = true;
    const layout = computeLayout(nodes, edges);
    state.layout = layout;
    plane.style.width = `${layout.width}px`;
    plane.style.height = `${layout.height}px`;
    edgesTarget.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    edgesTarget.setAttribute("width", String(layout.width));
    edgesTarget.setAttribute("height", String(layout.height));
    lanesTarget.innerHTML = layout.bands.map((band) => `<div class="mp-lane-band is-${band.orientation}" style="left:${band.x}px;top:${band.y}px;width:${band.width}px;height:${band.height}px"><span>${esc(t("flow"))} ${band.lane}<small>${esc(t("flowCaveat"))}</small></span></div>`).join("");
    renderEdges(edges, layout);
    const localizedMap = localizedQuestMap();
    nodesTarget.innerHTML = nodes.map((node) => renderQuestCard(node, layout.positions.get(node.id), localizedMap)).join("");
    const meta = byId("mp-graph-meta");
    if (meta) meta.textContent = `${nodes.length} ${t("quests")} · ${edges.length} edges · ${layout.orientation.toUpperCase()}`;
    requestAnimationFrame(() => {
      if (!state.transform.scale || state.missionId !== plane.dataset.fittedMission) {
        plane.dataset.fittedMission = state.missionId;
        fitGraph();
        if (state.transform.scale < 0.32) {
          state.transform.scale = 0.55;
          centerSelected();
        }
      } else applyTransform();
    });
  }

  function renderQuestCard(node, position, localizedMap) {
    const selected = node.id === state.selectedQuestId;
    const classes = ["mp-quest-card"];
    if (selected) classes.push("is-selected");
    if (node.mainPath) classes.push("is-main");
    if (isHiddenQuest(node)) classes.push("is-hidden-quest");
    if (node.annotation) classes.push("has-annotation");
    if (node.authority === "server") classes.push("is-server-owned");
    const conditions = (node.conditionTypes || []).slice(0, 3);
    const activityLevels = [...new Set(
      (node.activityStageHosts || []).map((row) => row.levelId).filter(Boolean),
    )];
    const runtimeActions = questRuntimeActions(node, localizedMap);
    const runtimeObservations = (node.runtimeStoryObservations || []).filter((row) => row && row.storyKey);
    const attachmentDiagnostic = questAttachmentDiagnostic(node);
    const description = missionDescriptionInfo(node, localizedMap);
    const storyCounts = storyConnectionCounts(node, localizedMap);
    const network = node.network?.outbound;
    const networkLabel = network === "dialog_finish" ? t("clientToServerDialog") : network === "objective_progress" ? t("clientToServerProgress") : network === "server_owned" ? t("serverGate") : t("unresolvedSend");
    const networkClass = network === "dialog_finish" || network === "objective_progress" ? "is-dialog" : network === "server_owned" ? "is-server" : "is-unknown";
    const storySummary = [
      storyCounts.incoming ? `${t("storyToQuest")}: ${storyCounts.incoming}` : "",
      storyCounts.outgoing ? `${t("questToStory")}: ${storyCounts.outgoing}` : "",
      storyCounts.context ? `${t("storyContext")}: ${storyCounts.context}` : "",
      runtimeObservations.length ? `${t("runtimeObserved")}: ${runtimeObservations.length}` : "",
    ].filter(Boolean).join(" · ");
    const activitySummary = activityLevels.length
      ? `${t("activityStageLevel")}: ${activityLevels.join(", ")}`
      : "";
    const runtimeSummary = runtimeActions.map((row) => {
      const activityId = row.paramData?.activityId || row.dialogKey || "";
      return `${t("openUiAction")}: ${activityId}`;
    }).join("; ");
    const tooltip = [objectiveText(node, localizedMap), description.text, activitySummary, runtimeSummary, storySummary, attachmentDiagnostic ? t("questAttachmentDiagnosticHint") : ""].filter(Boolean).join("\n\n");
    return `<button class="${classes.join(" ")}" type="button" data-quest="${esc(node.id)}" aria-pressed="${selected}" style="left:${position.x}px;top:${position.y}px" title="${esc(tooltip)}">
      <span class="mp-card-top"><code>${esc(questShortLabel(node.id))}</code><span class="mp-card-badges">${node.mainPath ? `<span>${esc(t("main"))}</span>` : ""}${isHiddenQuest(node) ? `<span class="is-hidden">${esc(t("hidden"))}</span>` : ""}${storyCounts.incoming ? `<span class="is-story is-incoming">${esc(t("storyIncomingBadge"))} ${storyCounts.incoming}</span>` : ""}${storyCounts.outgoing ? `<span class="is-story is-outgoing">${esc(t("storyOutgoingBadge"))} ${storyCounts.outgoing}</span>` : ""}${storyCounts.context ? `<span class="is-story is-context">${esc(t("storyContextBadge"))} ${storyCounts.context}</span>` : ""}${attachmentDiagnostic ? `<span class="is-story is-context">${esc(t("questAttachmentDiagnostic"))}</span>` : ""}${runtimeObservations.length ? `<span class="is-runtime">${esc(t("runtimeObserved"))} ${runtimeObservations.length}</span>` : ""}${runtimeActions.length ? `<span>${esc(t("openUiAction"))} ${runtimeActions.length}</span>` : ""}<span>${esc(t("flow"))} ${Number(node.flowIndex || 0)}</span></span></span>
      <strong>${esc(objectiveText(node, localizedMap))}</strong>
      <span class="mp-card-description">${esc(description.text || t("noDescription"))}</span>
      <span class="mp-condition-row">${runtimeActions.map((row) => `<span title="${esc(t("notStoryFile"))}">${esc(t("openUiAction"))}: ${esc(row.paramData?.activityId || row.dialogKey || "")}</span>`).join("")}${activityLevels.map((value) => `<span title="${esc(t("activityStageLevelHint"))}">${esc(t("activityStageLevel"))}: ${esc(value)}</span>`).join("")}${conditions.map((value) => `<span>${esc(value)}</span>`).join("")}${(node.conditionTypes || []).length > 3 ? `<span>+${node.conditionTypes.length - 3}</span>` : ""}</span>
      <span class="mp-network-row"><span class="mp-network is-inbound">${esc(t("serverToClient"))}</span><span class="mp-network ${networkClass}">${esc(networkLabel)}</span></span>
      ${node.annotation ? `<span class="mp-annotation-dot" aria-label="${esc(node.annotation)}">◎</span>` : ""}
    </button>`;
  }

  function svg(tag, attrs = {}) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  function renderEdges(edges, layout) {
    const target = byId("mp-edges");
    if (!target) return;
    target.replaceChildren();
    const defs = svg("defs");
    const marker = svg("marker", { id: "mp-arrow", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth" });
    marker.appendChild(svg("path", { d: "M0,0 L8,4 L0,8 z", class: "mp-arrow-head" }));
    const depMarker = svg("marker", { id: "mp-arrow-dep", markerWidth: 8, markerHeight: 8, refX: 7, refY: 4, orient: "auto", markerUnits: "strokeWidth" });
    depMarker.appendChild(svg("path", { d: "M0,0 L8,4 L0,8 z", class: "mp-arrow-head-dep" }));
    defs.append(marker, depMarker);
    target.appendChild(defs);
    const showLabels = Boolean(byId("mp-show-edge-labels")?.checked);
    for (const edge of edges) {
      const from = layout.positions.get(edge.source);
      const to = layout.positions.get(edge.target);
      if (!from || !to) continue;
      const dependency = edge.type === "condition_dependency";
      let start;
      let end;
      let d;
      if (layout.orientation === "lr") {
        start = { x: from.x + CARD_W, y: from.y + CARD_H / 2 };
        end = { x: to.x, y: to.y + CARD_H / 2 };
        const bend = Math.max(50, Math.abs(end.x - start.x) * 0.46);
        d = `M${start.x},${start.y} C${start.x + bend},${start.y} ${end.x - bend},${end.y} ${end.x},${end.y}`;
      } else {
        start = { x: from.x + CARD_W / 2, y: from.y + CARD_H };
        end = { x: to.x + CARD_W / 2, y: to.y };
        const bend = Math.max(42, Math.abs(end.y - start.y) * 0.46);
        d = `M${start.x},${start.y} C${start.x},${start.y + bend} ${end.x},${end.y - bend} ${end.x},${end.y}`;
      }
      const selected = edge.source === state.selectedQuestId || edge.target === state.selectedQuestId;
      const path = svg("path", {
        d,
        class: `mp-edge ${dependency ? "is-dependency" : "is-predecessor"}${selected ? " is-selected" : ""}`,
        "marker-end": dependency ? "url(#mp-arrow-dep)" : "url(#mp-arrow)",
      });
      target.appendChild(path);
      const midpoint = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
      if (!dependency) {
        const gateway = svg("g", { class: `mp-gateway${selected ? " is-selected" : ""}` });
        gateway.appendChild(svg("path", { d: `M${midpoint.x},${midpoint.y - 12} L${midpoint.x + 12},${midpoint.y} L${midpoint.x},${midpoint.y + 12} L${midpoint.x - 12},${midpoint.y} Z` }));
        const label = svg("text", { x: midpoint.x, y: midpoint.y + 4, "text-anchor": "middle" });
        label.textContent = t("serverGateway");
        gateway.appendChild(label);
        const title = svg("title"); title.textContent = t("serverGatewayTitle"); gateway.appendChild(title);
        target.appendChild(gateway);
      }
      if (showLabels) {
        const label = svg("text", { x: midpoint.x + 16, y: midpoint.y - 14, class: `mp-edge-label${dependency ? " is-dependency" : ""}` });
        label.textContent = dependency ? `${t("conditionDependency")} = ${edge.targetState ?? "?"}` : t("predecessor");
        target.appendChild(label);
      }
    }
  }

  function selectQuest(id, { focus = true } = {}) {
    if (!state.mission?.nodes?.some((node) => node.id === id)) return;
    state.selectedQuestId = id;
    renderGraph();
    renderInspector();
    if (focus) byId("mp-nodes")?.querySelector(`button[data-quest="${CSS.escape(id)}"]`)?.focus();
  }

  function graphKeydown(event) {
    const button = event.target.closest("button[data-quest]");
    if (!button || !state.mission) return;
    const node = state.mission.nodes.find((row) => row.id === button.dataset.quest);
    if (!node) return;
    let target = "";
    if (event.key === "ArrowRight" || event.key === "ArrowDown") target = node.successors?.[0] || "";
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") target = node.prev?.[0] || "";
    if (target) { event.preventDefault(); selectQuest(target); centerSelected(); }
  }

  function conditionAuthorityText(authority) {
    if (authority === "synchronized_history") return t("synchronizedHistory");
    if (authority === "synchronized_state") return t("synchronizedState");
    if (authority === "client_observed") return t("clientObserved");
    if (authority === "server") return t("serverOwnedDetail");
    if (authority === "mixed") return t("mixedAuthority");
    return t("unknownAuthority");
  }

  function renderConditionTree(condition) {
    if (!condition) return "";
    const facts = condition.facts || {};
    const factHtml = Object.entries(facts).map(([key, value]) => `<span><b>${esc(key)}</b>: ${esc(typeof value === "object" ? JSON.stringify(value) : value)}</span>`).join("");
    const children = (condition.children || []).map((child) => renderConditionTree(child)).join("");
    return `<div class="mp-condition-tree"><code>${esc(condition.type)}</code>${factHtml ? `<div class="mp-condition-facts">${factHtml}</div>` : ""}${children ? `<div class="mp-condition-children">${children}</div>` : ""}</div>`;
  }

  function objectiveTrackingHtml(tracking) {
    if (!tracking?.length) return "";
    const rows = tracking.map((row) => {
      const facts = Object.entries(row)
        .filter(([key]) => !["index", "type", "filterCondition"].includes(key))
        .map(([key, value]) => `<span><b>${esc(key)}</b>: ${esc(typeof value === "object" ? JSON.stringify(value) : value)}</span>`)
        .join("");
      return `<article class="mp-tracking-row">
        <header><code>${esc(row.type || "TrackingInfo")}</code><small>#${Number(row.index || 0) + 1}</small></header>
        ${facts ? `<div class="mp-condition-facts">${facts}</div>` : ""}
        ${row.filterCondition ? `<div class="mp-tracking-filter"><strong>${esc(t("trackingFilter"))}</strong>${renderConditionTree(row.filterCondition)}</div>` : ""}
      </article>`;
    }).join("");
    return `<details class="mp-objective-tracking" open>
      <summary>${esc(t("trackingTargets"))} <span>${tracking.length.toLocaleString()}</span></summary>
      <p>${esc(t("trackingTargetsHint"))}</p>
      <div class="mp-tracking-list">${rows}</div>
    </details>`;
  }

  function objectiveHtml(objective, questId) {
    const finishRows = (objective.dialogFinishes || []).map((row) => `<span class="mp-finish-chip"><b>${esc(row.dialogId)}</b> · ${row.finishId < 0 ? esc(t("anyFinish")) : `${esc(t("finish"))} ${esc(row.finishId)}`}</span>`).join("");
    const localIds = new Set((state.mission?.nodes || []).map((node) => node.id));
    const stateRows = (objective.questStateRefs || []).map((row) => `<span class="mp-state-chip${localIds.has(row.questId) ? "" : " is-external"}"><b>${esc(row.questId)}</b> · ${esc(t("state"))} ${esc(row.state ?? "?")}${localIds.has(row.questId) ? "" : ` · ${esc(t("externalDependency"))}`}</span>`).join("");
    const placeholderRows = (objective.serverPlaceholderConditionIds || []).map((conditionId) => `<span class="mp-finish-chip"><b>${esc(t("serverPlaceholderKey"))}</b> · <code>(${esc(questId)}, ${esc(conditionId)})</code></span>`).join("");
    const submissionRows = (objective.submissionChecks || []).map((row) => {
      const requirements = (row.requirementGroups || []).map((group) => (group.items || []).map((item) => `${item.itemId} × ${item.count ?? "?"}`).join(" + ")).filter(Boolean).join(` ${t("or")} `);
      return `<span class="mp-finish-chip"><b>${esc(t("submissionRequirement"))}</b> · <code>${esc(row.submissionId || "")}</code>${requirements ? ` · ${esc(requirements)}` : ""}</span>`;
    }).join("");
    const submissionCoGates = (objective.submissionDialogCoGates || []).map((row) => `<span class="mp-state-chip" title="${esc(t("submissionDialogCoGateHint"))}"><b>${esc(t("submissionDialogCoGate"))}</b> · <code>${esc(row.submissionId || "")}</code> + <code>${esc(row.dialogId || "")}</code> · ${row.finishId < 0 ? esc(t("anyFinish")) : `${esc(t("finish"))} ${esc(row.finishId)}`}</span>`).join("");
    const submissionLevelScriptCoGates = (objective.submissionLevelScriptCoGates || []).map((row) => `<span class="mp-state-chip" title="${esc(t("submissionLevelScriptCoGateHint"))}"><b>${esc(t("submissionLevelScriptCoGate"))}</b> · <code>${esc(row.submissionId || "")}</code> + <code>${esc(row.levelId || "")}/${esc(row.scriptId || "")}</code></span>`).join("");
    const taskDependencies = (objective.levelScriptTaskDependencies || []).map((row) => {
      const metadata = row.taskMetadata || {};
      const files = (row.relatedOriginalFiles || []).map((file) => `<small><code>${esc(file.kind || "file")}</code> <code>${esc(file.sourceFile || "")}</code>${file.sha256 ? ` / SHA-256 <code>${esc(file.sha256)}</code>` : ""}</small>`).join("");
      const metadataText = [metadata.titleKey, metadata.descriptionKey, metadata.objectiveCount != null ? `${metadata.objectiveCount} ${t("objectives")}` : ""].filter(Boolean).join(" · ");
      return `<details open class="mp-quest-task-dependency"><summary><b>${esc(t("levelScriptTaskDependency"))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}/${esc(row.taskId || "?")}</code></summary>${metadataText ? `<p><strong>${esc(t("taskMetadata"))}:</strong> ${esc(metadataText)}</p>` : ""}<small>${esc(t("levelScriptTaskDependencyHint"))}</small>${files ? `<details><summary>${esc(t("relatedOriginalFile"))} <span>${(row.relatedOriginalFiles || []).length}</span></summary>${files}</details>` : ""}</details>`;
    }).join("");
    const levelScriptSources = (objective.levelScriptSources || []).map((row) => {
      const counts = row.actionMapListCounts || {};
      const countText = ["actionList", "getterList", "headerList"].map((name) => `${name}=${counts[name] ?? "?"}`).join(" / ");
      const files = (row.relatedOriginalFiles || []).map((file) => `<small><code>${esc(file.sourceFile || "")}</code>${file.sha256 ? ` / SHA-256 <code>${esc(file.sha256)}</code>` : ""}</small>`).join("");
      const statusLabel = row.actionMapStatus === "exact_empty_action_map" ? t("levelScriptExactEmptyMap") : t("levelScriptExecutableMap");
      return `<details${row.actionMapStatus === "exact_empty_action_map" ? " open" : ""} class="mp-quest-task-dependency"><summary><b>${esc(t("levelScriptSource"))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}</code> <span>${esc(statusLabel)}</span></summary><p><code>${esc(countText)}</code>${row.serializedTailRecordCount ? ` 路 ${esc(t("levelScriptTailRecords"))}: ${Number(row.serializedTailRecordCount).toLocaleString()}` : ""}</p><small>${esc(row.evidenceBoundary || "")}</small>${files ? `<details><summary>${esc(t("relatedOriginalFile"))} <span>${(row.relatedOriginalFiles || []).length}</span></summary>${files}</details>` : ""}</details>`;
    }).join("");
    return `<article class="mp-objective"><header><strong>${esc(t("objectives"))} ${objective.index}</strong><span class="mp-authority is-${esc(objective.authority)}">${esc(objective.authority)}</span></header>
      <p>${esc(objective.descriptionKey || t("noObjective"))}</p>
      <div class="mp-objective-special">${finishRows}${stateRows}${placeholderRows}${submissionRows}${submissionCoGates}${submissionLevelScriptCoGates}</div>${levelScriptSources}${taskDependencies}
      ${objectiveTrackingHtml(objective.tracking)}
      ${renderConditionTree(objective.condition)}
    </article>`;
  }

  function dialogTreeDefinitionsHtml(node) {
    const definitions = node.dialogTreeDefinitions || [];
    if (!definitions.length) return "";
    const rows = definitions.map((row) => {
      const facts = [
        `${Number((row.lineIds || []).length)} ${t("dialogTreeLines")}`,
        `${Number(row.nodeCount || 0)} ${t("dialogTreeNodes")}`,
        `${Number(row.connectionCount || 0)} ${t("dialogTreeConnections")}`,
        `${Number(row.branchingOptionGroupCount || 0)} ${t("dialogTreeBranchGroups")}`,
      ];
      const observers = (row.missionObservers || []).map((observer) => {
        const relation = observer.relation === "failed_condition"
          ? t("dialogTreeFailureObserver")
          : `${t("dialogTreeObjectiveObserver")} ${observer.objectiveIndex ?? "?"}`;
        const finish = Object.prototype.hasOwnProperty.call(observer, "finishId")
          ? ` · ${observer.finishId < 0 ? t("anyFinish") : `${t("finish")} ${observer.finishId}`}`
          : "";
        return `${relation} · ${observer.conditionType || "?"}${finish}`;
      });
      return `<article class="mp-action">
        <a href="${esc(storyHref(row.sceneKey || ""))}"><code>${esc(row.sceneKey || "")}</code></a>
        <span>${facts.map(esc).join(" · ")}</span>
        ${observers.map((observer) => `<small>${esc(t("dialogTreeObserver"))}: ${esc(observer)}</small>`).join("")}
        <small><code>${esc(row.sourceFile || "")}</code></small>
        <small>SHA-256 <code>${esc(row.sourceSha256 || "")}</code></small>
        <small>${esc(t("dialogTreeNoOrder"))}</small>
      </article>`;
    }).join("");
    return `<section class="mp-inspector-section mp-dialog-tree-definition-section">
      <h3>${esc(t("dialogTreeDefinitions"))}</h3>
      <p>${esc(t("dialogTreeDefinitionHint"))}</p>
      ${rows}
    </section>`;
  }

  function protocolRow(step, player, client, server, tone = "") {
    return `<div class="mp-protocol-row ${tone}"><div class="mp-step-label">${esc(step)}</div><div class="mp-lane-cell is-player">${player || ""}</div><div class="mp-lane-cell is-client">${client || ""}</div><div class="mp-lane-cell is-server">${server || ""}</div></div>`;
  }

  function protocolHtml(node) {
    const dialogRows = (node.objectives || []).flatMap((objective) => objective.dialogFinishes || []);
    const conditionIds = (node.objectives || []).map((objective) => objective.conditionId).filter(Boolean);
    let observeClient = `<strong>${esc(t("condition"))}</strong><span>${esc(conditionAuthorityText(node.authority))}</span>`;
    let observeServer = "";
    if (node.authority === "server") { observeServer = observeClient; observeClient = `<span>${esc(t("serverOwnedDetail"))}</span>`; }
    const exchangeRows = [];
    if (node.network?.outbound === "dialog_finish") {
      const fields = dialogRows.map((row) => `${row.dialogId} / ${row.finishId < 0 ? t("anyFinish") : `${t("finish")} ${row.finishId}`}`).join("; ");
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("dialogSend"))}</strong><span>${esc(fields)}</span>`, `<span>${esc(t("dialogSendDetail"))}</span>`, "is-known-send"));
      exchangeRows.push(protocolRow(t("dialogExchange"), "", `<span>${esc(t("synchronizedHistory"))}</span>`, `<strong>→ ${esc(t("dialogEcho"))}</strong>`, "is-inbound-step"));
    } else if (node.network?.outbound === "server_owned") {
      const keys = (node.serverPlaceholderKeys || []).map((row) => `(${row.questId}, ${row.conditionId})`).join(", ");
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("serverPlaceholderNoSend"))}</strong>${keys ? `<span>${esc(t("serverPlaceholderKey"))}: ${esc(keys)}</span>` : ""}`, `<strong>${esc(t("serverGate"))}</strong>`, "is-server-step"));
      exchangeRows.push(protocolRow(t("returnState"), "", `<span>${esc(t("serverPlaceholderReturnDetail"))}</span>`, `<strong>→ ${esc(t("serverPlaceholderReturn"))}</strong>`, "is-inbound-step"));
    }
    if (node.network?.outbound !== "server_owned" && (node.objectives || []).length) {
      const ids = conditionIds.length ? conditionIds.join(", ") : "conditionId";
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("progressSend"))}</strong><span>${esc(ids)} · ${esc(t("progressCaveat"))}</span>`, `<span>${esc(t("progressNative"))}</span>`, "is-known-send"));
      exchangeRows.push(protocolRow(t("returnState"), "", `<span>${esc(t("progressCaveat"))}</span>`, `<strong>→ ${esc(t("progressReturn"))}</strong>`, "is-inbound-step"));
    } else if (node.network?.outbound !== "server_owned") {
      exchangeRows.push(protocolRow(t("outbound"), "", `<strong>${esc(t("unresolvedSend"))}</strong><span>${esc(t("unresolvedDetail"))}</span>`, `<span>?</span>`, "is-unknown-send"));
    }
    return `<section class="mp-protocol">
      <header><div><h3>${esc(t("protocol"))}</h3><p>${esc(t("asyncCaveat"))}</p></div><span class="mp-native-badge">${esc(t("nativeConfidence"))}</span></header>
      <div class="mp-protocol-grid">
        <div class="mp-protocol-head"><span></span><strong>${esc(t("playerWorld"))}</strong><strong>${esc(t("client"))}</strong><strong>${esc(t("server"))}</strong></div>
        ${protocolRow(t("activation"), "", `<strong>${esc(t("activationHandler"))}</strong>`, `<strong>→ ${esc(t("activationMessage"))}</strong>`, "is-inbound-step")}
        ${protocolRow(t("observe"), `<span>${esc(t("worldEvent"))}</span>`, observeClient, observeServer)}
        ${exchangeRows.join("")}
        ${protocolRow(t("resolve"), "", "", `<strong>${esc(t("opaquePolicy"))}</strong>`, "is-opaque-step")}
        ${protocolRow(t("returnState"), "", `<strong>${esc(t("succeedHandler"))}</strong>${node.failedCondition ? `<span>${esc(t("failMessage"))}</span>` : ""}`, `<strong>→ ${esc(t("succeedMessage"))}</strong>`, "is-inbound-step")}
        ${protocolRow(t("successor"), "", `<span>${esc(t("successorDetail"))}</span>`, `<strong>${esc((node.successors || []).join(", ") || "—")}</strong>`, "is-opaque-step")}
      </div>
    </section>`;
  }

  function storyFilesHtml(node, localizedMap = localizedQuestMap()) {
    const connections = questStoryConnections(node, localizedMap);
    const groups = [
      ["story_to_quest", t("storyToQuest"), "incoming"],
      ["quest_to_story", t("questToStory"), "outgoing"],
      ["context", t("storyContext"), "context"],
    ];
    const body = connections.length ? `<div class="mp-story-files">${groups.map(([direction, label, className]) => {
      const rows = connections.filter((row) => storyConnectionDirectionGroup(row) === direction);
      if (!rows.length) return "";
      return `<section class="mp-story-group is-${className}"><h4>${esc(label)} <span>${rows.length}</span></h4>${rows.map((row) => storyConnectionLink(row, className, node.id)).join("")}</section>`;
    }).join("")}</div>` : `<p>${esc(t("noStoryFiles"))}</p>`;
    return `<section class="mp-inspector-section mp-story-section"><h3>${esc(t("storyFiles"))}</h3>${body}<small>${esc(t("storyEvidence"))}</small></section>`;
  }

  function renderInspector() {
    const target = byId("mp-inspector");
    if (!target || !state.mission) return;
    const node = state.mission.nodes.find((row) => row.id === state.selectedQuestId);
    if (!node) { target.innerHTML = `<div class="mp-empty-inspector">${esc(t("selectMission"))}</div>`; return; }
    const actionHtml = (node.clientActions || []).map((action) => {
      const dispatchLabel = action.runtimeDispatchStatus === "authored_definition_no_current_aot_dispatch"
        ? t("questActionStartNoDispatch")
        : String(action.runtimeDispatchStatus || "").startsWith("binary_proven_")
          ? t("questActionBinaryDispatch")
          : "";
      return `<div class="mp-action"><code>${esc(action.type)}</code><span>ID ${esc(action.id ?? "?")} · ${esc(action.triggerName || `trigger ${action.trigger ?? "?"}`)} · ${esc(t("actionChainStep"))} ${esc(Number(action.chainIndex || 0) + 1)}</span>${dispatchLabel ? `<b title="${esc(action.runtimeDispatchBoundary || "")}">${esc(dispatchLabel)}</b>` : ""}</div>`;
    }).join("");
    const activityHostHtml = (node.activityStageHosts || []).map((row) => `<div class="mp-action"><code>${esc(row.levelId)}</code><span>${esc(row.table)} · ${esc(row.stageId)} · ${esc(t("nonOwningCrossReference"))}</span></div>`).join("");
    const runtimeActionHtml = questRuntimeActions(node).map((row) => `<div class="mp-action"><code>${esc(row.paramData?.activityId || row.dialogKey || t("openUiAction"))}</code><span>${esc(t("openUiAction"))} · panel ${esc(row.panelType ?? "?")} · ${esc(row.questStateName || row.phase || "")} · ${esc(t("notStoryFile"))}</span><small><code>${esc(row.dialogTreeSource || "")}</code></small></div>`).join("");
    const runtimeObservedHtml = (node.runtimeStoryObservations || []).map(runtimeObservationHtml).join("");
    const nativeEvidence = (state.index?.runtimeContract?.nativeEvidence || []).map((row) => `<li><code>${esc(row.symbol)}</code><span>${esc(row.finding)}</span></li>`).join("");
    const description = missionDescriptionInfo(node);
    target.innerHTML = `<div class="mp-inspector-head">
        <p>${esc(t("inspectQuest"))}</p><h2>${esc(questShortLabel(node.id))}</h2><code>${esc(node.id)}</code>
        <strong>${esc(objectiveText(node))}</strong>
        ${node.annotation ? `<span class="mp-inspector-annotation">◎ ${esc(node.annotation)}</span>` : ""}
      </div>
      <div class="mp-fact-grid">
        <span><b>${esc(t("flow"))}</b>${esc(node.flowIndex)}</span>
        <span><b>showMode</b>${esc(node.showMode ?? "—")}</span>
        <span><b>prev</b>${esc((node.prev || []).length)}</span>
        <span><b>next</b>${esc((node.successors || []).length)}</span>
      </div>
      <p class="mp-flow-caveat">${esc(t("flowCaveat"))}</p>
      <section class="mp-inspector-section mp-description-section"><h3>${esc(t("missionDescription"))}</h3><p>${esc(description.text || t("noDescription"))}</p>${description.text ? `<small>${esc(description.source === "quest_override" ? t("descriptionOverride") : t("descriptionInherited"))} · <code>${esc(description.key)}</code></small>` : ""}</section>
      <section class="mp-inspector-section"><h3>${esc(t("authority"))}</h3><p>${esc(conditionAuthorityText(node.authority))}</p></section>
      ${activityHostHtml ? `<section class="mp-inspector-section"><h3>${esc(t("activityStageLevel"))}</h3><p>${esc(t("activityStageLevelHint"))}</p>${activityHostHtml}</section>` : ""}
      ${runtimeActionHtml ? `<section class="mp-inspector-section"><h3>${esc(t("runtimeActions"))}</h3>${runtimeActionHtml}</section>` : ""}
      <section class="mp-inspector-section"><h3>${esc(t("objectives"))}</h3>${(node.objectives || []).map((objective) => objectiveHtml(objective, node.id)).join("") || `<p>${esc(t("noObjective"))}</p>`}${node.failedCondition ? `<div class="mp-failed-condition"><strong>failedCondition</strong>${renderConditionTree(node.failedCondition)}</div>` : ""}</section>
      ${dialogTreeDefinitionsHtml(node)}
      ${storyFilesHtml(node)}
      ${questAttachmentDiagnosticHtml(node)}
      ${runtimeObservedHtml ? `<section class="mp-inspector-section mp-runtime-observed-section"><h3>${esc(t("runtimeTraceOverlay"))}</h3><p>${esc(t("runtimeTraceHint"))}</p><div class="mp-runtime-observation-list">${runtimeObservedHtml}</div><small>${esc(t("noAuthoredPromotion"))}</small></section>` : ""}
      ${actionHtml ? `<section class="mp-inspector-section"><h3>${esc(t("clientActions"))}</h3>${actionHtml}</section>` : ""}
      ${protocolHtml(node)}
      <details class="mp-native-details"><summary>${esc(t("openEvidence"))}</summary><p>${esc(state.index?.runtimeContract?.authority?.nativeScope || "")}</p><ul>${nativeEvidence}</ul><p><strong>${esc(t("source"))}:</strong> <code>${esc(state.mission.mission?.source || "")}</code></p></details>`;
  }

  function applyTransform() {
    const plane = byId("mp-plane");
    if (!plane) return;
    const { x, y, scale } = state.transform;
    plane.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    const viewport = byId("mp-viewport");
    if (viewport) viewport.dataset.scale = scale.toFixed(2);
  }

  function fitGraph() {
    const viewport = byId("mp-viewport");
    if (!viewport || !state.layout) return;
    const pad = 38;
    const scale = Math.max(0.04, Math.min(1.05, (viewport.clientWidth - pad * 2) / state.layout.width, (viewport.clientHeight - pad * 2) / state.layout.height));
    state.transform = {
      scale,
      x: (viewport.clientWidth - state.layout.width * scale) / 2,
      y: (viewport.clientHeight - state.layout.height * scale) / 2,
    };
    applyTransform();
  }

  function zoomGraph(factor, origin = null) {
    const viewport = byId("mp-viewport");
    if (!viewport || !state.layout) return;
    const old = state.transform.scale;
    const next = Math.max(0.04, Math.min(2.2, old * factor));
    const point = origin || { x: viewport.clientWidth / 2, y: viewport.clientHeight / 2 };
    const worldX = (point.x - state.transform.x) / old;
    const worldY = (point.y - state.transform.y) / old;
    state.transform.scale = next;
    state.transform.x = point.x - worldX * next;
    state.transform.y = point.y - worldY * next;
    applyTransform();
  }

  function centerSelected() {
    const viewport = byId("mp-viewport");
    const position = state.layout?.positions?.get(state.selectedQuestId);
    if (!viewport || !position) return;
    state.transform.x = viewport.clientWidth / 2 - (position.x + CARD_W / 2) * state.transform.scale;
    state.transform.y = viewport.clientHeight / 2 - (position.y + CARD_H / 2) * state.transform.scale;
    applyTransform();
  }

  function beginPan(event) {
    if (event.button !== 0 || event.target.closest("input, select, label, summary, details")) return;
    const viewport = byId("mp-viewport");
    state.dragging = {
      id: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      originX: state.transform.x,
      originY: state.transform.y,
      moved: false,
    };
  }

  function movePan(event) {
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const dx = event.clientX - state.dragging.x;
    const dy = event.clientY - state.dragging.y;
    if (!state.dragging.moved && Math.hypot(dx, dy) < 5) return;
    if (!state.dragging.moved) {
      state.dragging.moved = true;
      const viewport = byId("mp-viewport");
      viewport?.setPointerCapture(event.pointerId);
      viewport?.classList.add("is-panning");
    }
    event.preventDefault();
    state.transform.x = state.dragging.originX + dx;
    state.transform.y = state.dragging.originY + dy;
    applyTransform();
  }

  function endPan(event) {
    if (!state.dragging || state.dragging.id !== event.pointerId) return;
    const moved = state.dragging.moved;
    state.dragging = null;
    byId("mp-viewport")?.classList.remove("is-panning");
    if (moved) state.suppressGraphClickUntil = performance.now() + 350;
  }

  function graphWheel(event) {
    event.preventDefault();
    const viewport = byId("mp-viewport");
    const rect = viewport?.getBoundingClientRect();
    if (!rect) return;
    const unit = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16 : event.deltaMode === WheelEvent.DOM_DELTA_PAGE ? viewport.clientHeight : 1;
    const delta = Math.max(-240, Math.min(240, event.deltaY * unit));
    zoomGraph(Math.exp(-delta * 0.00125), { x: event.clientX - rect.left, y: event.clientY - rect.top });
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.missionPipeline = { init, load, retry: () => load(state.language, { force: true }) };
})();
