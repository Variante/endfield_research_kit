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
      missions: "missions",
      quests: "quests",
      connectedStory: "Story connected",
      unlinkedStory: "Story unassigned",
      nativePlaybackGaps: "exact-native gaps",
      rootPlaybackAliases: "root playback aliases",
      definitionOnlyStory: "definition-only black text",
      nonMissionContentStory: "non-mission content",
      nonMissionContentStoryHint: "Story ids proven to be authored non-mission content: speaker radio continuation, character SNS topics, or exact factory tutorial guide actions. The evidence serializes no mission or quest owner. Authored fields and typed consumers admit a key; filenames never do.",
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
      activationFrontier: "offline activation frontier",
      activationClass: "static activation class",
      startPolicy: "LevelScript start policy",
      levelDataContainer: "validated LevelData container",
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
      serializedMissionIdTokens: "serialized MissionRuntime ID tokens",
      taskConditionEvidence: "fully decoded task conditions",
      taskConditionBoundary: "task evaluation dependency, not mission ownership or execution order",
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
      dynamicSceneCrossReferences: "DynamicScene identity cross-references",
      dynamicSceneCrossReferencesHint: "A DynamicScene object co-carries mission/quest state conditions, and its exact numeric logic id equals an exported LevelScript script id containing Story playback. The current native systems resolve those ids through separate registries, so this is candidate context—not mission ownership, playback causality, or order.",
      dynamicSceneLogicId: "DynamicScene logic id",
      levelScriptId: "LevelScript script id",
      missionStateConditions: "co-carried state conditions",
      candidateContextOnly: "candidate context only",
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
      maxTypedDepth: "maximum custom-type depth",
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
      or: "or",
      nativeDirectCallers: "native direct callers",
      runtimeObjectCandidates: "runtime/object candidates",
      unreviewedCandidates: "unreviewed candidates",
      trackingContextOnly: "HUD/map tracking context only",
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
      strongEdges: "strong order edges",
      weakEdges: "context-only edges",
      orderCycles: "source cycles",
      unknownPairs: "unordered pairs",
      partialFrontier: "partial-order frontier",
      causalEdges: "reduced causal edges",
      forkMerge: "Authored forks and joins",
      questFork: "quest fork",
      questMerge: "quest join",
      nativeSplitFanout: "native Split fan-out",
      nativeIfElseBranch: "native If/Else branch",
      nativeSwitchBranch: "native Switch branch",
      nativeControlMerge: "native branch convergence",
      nativeEventSelector: "event selector",
      nativePredicate: "predicate",
      nativePredicateOpaque: "inline predicate not semantically decoded",
      optionBranches: "dialog option branches",
      optionDirectContinuation: "direct shared continuation",
      isolatedScenes: "isolated Story files",
      weakOnlyScenes: "weak-context-only files",
      orderCycleHint: "Files in one cyclic component have no proven internal total order.",
      orderEvidence: "order evidence",
      exactFinishes: "exact finishes",
      serverPlaceholders: "server gates",
      graph: "Quest graph",
      nativeBoundary: "Native boundary",
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
      subGameBindingsHint: "The shipped typed row carries mission id and bound LevelScript id together. Native code proves WorldChallenge quit can use bindScriptId to end that script, but the audited start paths do not read it. No quest, scene, or Story identity is added from co-membership; OCR, manual, and gameplay cross-references cannot create this edge.",
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
      relationFailureCondition: "Story state participates in failure guard",
      relationClientStart: "quest start launches Story action",
      relationClientSucceed: "quest success launches Story action",
      relationClientFailed: "quest failure launches Story action",
      relationLevelData: "LevelData explicitly places Story on this quest",
      relationLevelScript: "quest condition scopes this LevelScript Story call",
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
      relationAirWallMissionState: "one exact LevelData AirWall co-carries typed mission/quest-state predicates and this pushback radio; synchronized state controls the wall, then later player contact can play the radio (context, not transition causality, ownership, or order)",
      relationNarrativeInteractiveMissionState: "one counted LevelInteractiveData entity co-carries the popup consumer id and mission-state FX key; the original narrative template and native component prove the local playback dependency (not ownership)",
      relationNativeEventShellPlayback: "a typed custom-event producer reaches this unique Story listener and the producer belongs to one validated mission LevelData shell (mission context, not one quest)",
      relationManualGuideCompletionPlayback: "an exact client-only guide-group start reaches this completion listener and its producer belongs to one mission-named LevelData shell (mission context, not one quest or a server exchange)",
      relationVariantRuntime: "variant MissionRuntime attaches this Story file",
      relationNpcProxy: "unique NPC proxy resolves to this Story file",
      relationNpcProxyEx: "exact mission + NPC proxy resolves to this quest",
      relationNpcProxyMission: "NpcProxyEx explicitly scopes this Story file to the mission",
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
      triggerDependency: "dependency only",
      triggerUnresolved: "trigger known · owner unresolved",
      triggerPlaybackAlias: "root playback alias · owner unresolved",
      triggerPlaybackAliasConnected: "root playback alias · owner connected",
      triggerDefinition: "definition only · no consumer",
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
      triggerNativeAction: "playback action",
      triggerStoryRoot: "CutsceneRoot Story key",
      triggerStory: "Story file",
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
      relationRootPlaybackAliasComposed: "\u72ec\u7acb\u5df2\u8fde\u63a5\u7684\u539f\u751f\u6839\u64ad\u653e\u901a\u8fc7 CutsceneRoot director \u6267\u884c\u8be5\u7cbe\u786e TimelineAsset\uff08\u5f52\u5c5e\u4e0a\u4e0b\u6587\uff0c\u975e\u5267\u60c5\u987a\u5e8f\uff09",
      relationMissionTrackedWorldEntityLevelScript: "精确的本地队长触发器播放脚本引用了仅由一个任务跟踪的世界实体（仅共享的脚本/实体创作上下文；候选任务节点不证明触发门、激活、播放、完成或所有权）",
      relationMissionTrackedWorldEntityLevelScriptStage: "服务器先同步该 LevelScript 阶段，再进入精确的本地 StageChanged 播放路径；类型化世界实体跟踪只确定唯一任务上下文，不证明任何候选任务节点写入了该阶段",
      relationQuestProgressLockedInteractive: "每个播放实例都由精确的交互实体事件路径触发；该实体的强类型进度锁等待此任务达到已完成状态（仅为本地上下文，不证明剧情归属，也不证明任务激活、播放或完成因果）",
      subGameBindings: "原始数据 SubGame 运行时外壳",
      subGameBindingsHint: "游戏内置的类型化记录同时包含使命 ID 与绑定的 LevelScript ID。原生代码证明 WorldChallenge 退出时可用 bindScriptId 结束该脚本，但已审计的启动路径并不读取它。共同出现不会补出任务、场景或剧情身份；OCR、人工记录和实机交叉参考都不能创建这条边。",
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
      missions: "个任务",
      quests: "个任务节点",
      connectedStory: "已连接剧情",
      unlinkedStory: "未分配剧情",
      nativePlaybackGaps: "原生路径缺口",
      definitionOnlyStory: "仅有定义的黑屏文本",
      nonMissionContentStory: "非使命内容",
      nonMissionContentStoryHint: "这些剧情 ID 已由原生数据证明属于非使命内容：按说话人分的电台续播语音、角色 SNS 话题，或工厂教程资产中的精确动作。证据没有序列化使命或任务归属。仅依据原生字段和强类型消费者判定，绝不依据文件名。",
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
      exactReceiverNodesHint: "每个节点都来自原始 LevelScript 事件选择器，并有到剧情播放的精确控制路径；它能组织更多恢复文件，但不声明使命或任务所有者。",
      activationFrontier: "离线激活边界",
      activationClass: "静态激活分类",
      startPolicy: "LevelScript 启动策略",
      levelDataContainer: "已验证的 LevelData 容器",
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
      dynamicSceneCrossReferences: "DynamicScene 身份交叉引用",
      dynamicSceneCrossReferencesHint: "DynamicScene 对象携带任务状态条件，其精确数字逻辑 ID 与包含剧情播放的 LevelScript 脚本 ID 相同。当前原生系统通过不同注册表解析这两个 ID，因此这里只显示候选上下文，不表示任务所有权、播放因果或顺序。",
      dynamicSceneLogicId: "DynamicScene 逻辑 ID",
      levelScriptId: "LevelScript 脚本 ID",
      missionStateConditions: "同对象携带的状态条件",
      candidateContextOnly: "仅候选上下文",
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
      maxTypedDepth: "最大自定义类型深度",
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
      or: "或",
      nativeDirectCallers: "原生直接调用者",
      runtimeObjectCandidates: "运行时/对象候选",
      unreviewedCandidates: "未审查候选",
      trackingContextOnly: "仅 HUD/地图追踪上下文",
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
      relationNpcProxyTrackingDialog: "任务导航跟踪该精确 NPC 代理；其当前注册的交互对话包含类型化后续对话路线（仅导航/配置上下文）",
      relationNpcProxyLazyDestroyDialog: "任务导航跟踪该精确 NPC 代理；原生停用流程会把其配置的延迟销毁对话应用为交互覆盖（仅配置上下文，不证明任务激活或播放因果）",
      relationMissionTrackedNpcPatrol: "类型化 LevelData 解析检查点监听器的 NPC 别名与巡逻路线；同场景任务导航在唯一任务中跟踪该精确世界实体（仅任务上下文；候选任务节点不代表激活、播放、完成或所有权）",
      relationNpcProxySegmentShell: "被跟踪 NPC 代理位于精确的原始注册表片段中，片段全局 ID 与该剧情播放脚本一致（仅使命外壳，不代表 NPC 触发）",
      relationMissionStateDependency: "该使命已同步到客户端的精确状态参与选择剧情动作的原生 IfElse 路径（依赖，不代表归属）",
      relationTaskMissionStateDependency: "同一条原始 LevelScript 同时包含精确的 taskMap 使命状态条件和剧情播放，但序列化控制路径并未连接两者（仅依赖证据）",
      relationMissionStateProcessing: "精确原生 true 分支在该使命等于 Processing 时播放此剧情动作（使命上下文，不代表任务因果）",
      relationRadioTriggerMissionState: "同一条强类型 LevelData 广播触发区记录同时携带该广播与使命状态边界；原生 OnEnter 在播放前检查该状态（上下文，不代表任务归属）",
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
      triggerRoute: "\u6062\u590d\u7684\u89e6\u53d1\u8def\u5f84",
      triggerPlayback: "\u64ad\u653e\u89e6\u53d1",
      triggerCondition: "\u5b8c\u6210\u6761\u4ef6",
      triggerContext: "\u4ec5\u4e0a\u4e0b\u6587",
      triggerDependency: "\u4ec5\u4f9d\u8d56",
      triggerUnresolved: "\u89e6\u53d1\u5df2\u77e5 \u00b7 \u5f52\u5c5e\u672a\u89e3\u6790",
      triggerPlaybackAlias: "\u6839\u64ad\u653e\u522b\u540d \u00b7 \u5f52\u5c5e\u672a\u89e3\u6790",
      triggerPlaybackAliasConnected: "\u6839\u64ad\u653e\u522b\u540d \u00b7 \u5f52\u5c5e\u5df2\u8fde\u63a5",
      triggerDefinition: "\u4ec5\u5b9a\u4e49 \u00b7 \u65e0\u6d88\u8d39\u8005",
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
      triggerNativeAction: "\u64ad\u653e\u52a8\u4f5c",
      triggerStoryRoot: "CutsceneRoot \u5267\u60c5\u952e",
      triggerStory: "\u5267\u60c5\u6587\u4ef6",
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
      strongEdges: "\u5f3a\u987a\u5e8f\u8fb9",
      weakEdges: "\u4ec5\u4e0a\u4e0b\u6587\u8fb9",
      orderCycles: "\u6e90\u8bc1\u636e\u5faa\u73af",
      unknownPairs: "\u987a\u5e8f\u672a\u77e5\u5bf9",
      partialFrontier: "\u90e8\u5206\u987a\u5e8f\u524d\u6cbf",
      causalEdges: "\u7cbe\u7b80\u56e0\u679c\u8fb9",
      forkMerge: "\u4f5c\u8005\u5206\u652f\u4e0e\u6c47\u5408",
      questFork: "\u4efb\u52a1\u5206\u652f",
      questMerge: "\u4efb\u52a1\u6c47\u5408",
      nativeSplitFanout: "\u539f\u751f Split \u5206\u6d41",
      nativeIfElseBranch: "\u539f\u751f If/Else \u5206\u652f",
      nativeSwitchBranch: "\u539f\u751f Switch \u5206\u652f",
      nativeControlMerge: "\u539f\u751f\u5206\u652f\u6c47\u5408",
      nativeEventSelector: "\u4e8b\u4ef6\u9009\u62e9\u5668",
      nativePredicate: "\u5206\u652f\u6761\u4ef6",
      nativePredicateOpaque: "\u5185\u8054\u6761\u4ef6\u5c1a\u672a\u8bed\u4e49\u89e3\u7801",
      optionBranches: "\u5bf9\u8bdd\u9009\u9879\u5206\u652f",
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
      [storyCounts.rootPlaybackAliasRows, t("rootPlaybackAliases")],
      [storyCounts.missionlessSubGameStoryFiles, t("missionlessSubGameStory")],
      [storyCounts.missionlessNativeRuntimeStoryFiles, t("missionlessRuntimeStory")],
      [storyCounts.unlinkedDefinitionOnlyFiles, t("definitionOnlyStory")],
      [storyCounts.nonMissionContentFiles, t("nonMissionContentStory")],
      [counts.missionGraphPrecedenceEdges, t("missionGraphEdgesStat")],
      [counts.envTalkQuestContextFiles, t("envTalkContextStat")],
      [counts.envTalkStateContextFiles, t("envTalkStateContextStat")],
    ];
    if (state.index?.runtimeTrace) stats.push([runtimeCounts.storyPlaybacks, t("runtimeObserved")]);
    node.innerHTML = stats.map(([value, label]) => `<strong>${Number(value || 0).toLocaleString()}</strong><span>${esc(label)}</span>`).join("");
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
      if (row.direction === "story_to_quest") counts.incoming += 1;
      else if (row.direction === "quest_to_story") counts.outgoing += 1;
      else counts.context += 1;
    }
    return counts;
  }

  function storyRelationLabel(relation) {
    const key = {
      objective_condition: "relationObjectiveCondition",
      failure_condition: "relationFailureCondition",
      client_action_start: "relationClientStart",
      client_action_succeed: "relationClientSucceed",
      client_action_failed: "relationClientFailed",
      leveldata_quest_reference: "relationLevelData",
      levelscript_condition_scope: "relationLevelScript",
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
      airwall_mission_state_radio_dependency: "relationAirWallMissionState",
      airwall_mission_state_radio_playback_context: "relationAirWallMissionState",
      narrative_interactive_mission_state_dependency: "relationNarrativeInteractiveMissionState",
      narrative_interactive_mission_state_playback_context: "relationNarrativeInteractiveMissionState",
      authoritative_scope_native_event_playback_context: "relationNativeEventShellPlayback",
      mission_shell_manual_guide_completion_playback_context: "relationManualGuideCompletionPlayback",
      variant_runtime_attachment: "relationVariantRuntime",
      unique_npc_proxy: "relationNpcProxy",
      npc_proxy_attachment: "relationNpcProxy",
      npc_proxy_ex_attachment: "relationNpcProxyEx",
      npc_proxy_ex_mission_context: "relationNpcProxyMission",
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
      row.phase ? `phase=${row.phase}` : "",
      row.finishId !== undefined ? `finish=${row.finishId}` : "",
      row.actionType ? `${row.actionType} / slot ${row.actionSlot ?? "?"}` : "",
      row.actionName ? row.actionName : "",
      row.nativeAction ? `native action ${row.nativeAction}` : "",
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
      native_action: "triggerNativeAction",
      story_root: "triggerStoryRoot",
      story: "triggerStory",
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
    if (!steps.length) return "";
    return `<div class="mp-trigger-route is-${esc(route.causality || "context")}">
      <header><strong>${esc(t("triggerRoute"))}</strong><span>${esc(triggerCausalityLabel(route.causality))}</span>${route.controlPathCount ? `<b>${esc(route.controlPathCount)} ${esc(t("triggerExactPaths"))}</b>` : ""}</header>
      <div class="mp-trigger-chain">${steps.map((step, index) => `${index ? '<i aria-hidden="true">&rarr;</i>' : ""}${triggerStepHtml(step)}`).join("")}</div>
      ${paths.length ? `<section class="mp-trigger-events"><header><strong>${esc(t("triggerEvents"))}</strong><small>${esc(t("triggerEventsHint"))}</small></header><div>${paths.map(nativePathHtml).join("")}</div></section>` : ""}
    </div>`;
  }

  function storyConnectionLink(row, className, questId = "") {
    const details = storyConnectionDetails(row);
    const routeHtml = storyTriggerRoutes(row, questId).map(triggerRouteHtml).join("");
    const rejectionHtml = storyPlaybackRejections(row).map(playbackRejectionHtml).join("");
    const evidence = [row.confidence, row.source || row.evidence].filter(Boolean).join(" · ");
    return `<a class="is-${className}" href="${esc(storyHref(row.key))}" title="${esc(`${t("openInStory")} · ${evidence}`)}">
      <span>${esc(storyDisplayKind(row))}</span><code>${esc(row.key)}</code><b aria-hidden="true">→</b>
      <em>${esc(details.join(" · "))}</em>${evidence ? `<small>${esc(evidence)}</small>` : ""}
      ${routeHtml}
      ${rejectionHtml}
    </a>`;
  }

  function composedRootPlaybackAliasRowsForMission() {
    const missionId = String(
      state.missionId || state.mission?.mission?.id || "",
    );
    const manifest = state.index?.storyCoverage?.storyTriggerManifest || {};
    const rows = [];
    Object.values(manifest).forEach((entry) => {
      (entry?.routes || []).forEach((route) => {
        if (
          route?.causality !== "playback_alias_owner_connected"
          || route.ownerStatus !== "connected"
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
    const connectedAliasKeys = new Set(
      composedRootPlaybackAliasRowsForMission().map((row) => row.key),
    );
    return (state.localized?.flow?.unlinked || [])
      .filter((key) => key && !connectedAliasKeys.has(key));
  }

  function missionStoryConnectionsHtml() {
    const unique = new Map();
    [
      ...(state.localized?.flow?.missionStoryConnections || []),
      ...composedRootPlaybackAliasRowsForMission(),
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
          return storyConnectionLink({
            key: row.key,
            relation: "non_mission_content",
            direction: "context",
            confidence: guideRuntime
              ? "exact_typed_guide_runtime_non_mission_content"
              : "table_backed_non_mission_content",
            source: guideRuntime
              ? `${row.consumerClass} · ${row.actionCount || 0} actions / ${row.assetCount || 0} guide assets`
              : `${row.table}.${row.field} (keyed by ${row.keyedBy})`,
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

  function storyOrderHtml() {
    const order = state.mission?.storyOrder;
    if (!order?.summary) return "";
    const summary = order.summary;
    const components = new Map((order.components || []).map((row) => [row.id, row]));
    const directEdges = order.directEdges || [];
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
    const questForks = (branches.questForks || []).map((row) => `<div><b>${esc(t("questFork"))}</b><code>${esc(row.questId || "?")}</code><i>&rarr;</i><span>${(row.successorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span></div>`).join("");
    const questMerges = (branches.questMerges || []).map((row) => `<div><b>${esc(t("questMerge"))}</b><span>${(row.predecessorQuestIds || []).map((id) => `<code>${esc(id)}</code>`).join(" ")}</span><i>&rarr;</i><code>${esc(row.questId || "?")}</code></div>`).join("");
    const nativeBranchLabel = (kind) => t(kind === "splitFanout" ? "nativeSplitFanout" : kind === "ifElse" ? "nativeIfElseBranch" : "nativeSwitchBranch");
    const nativeParamText = (label, param) => {
      if (!param || typeof param !== "object") return "";
      const source = param.path || (param.paramSource != null ? `source ${param.paramSource}` : "");
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
      const sourceDetail = predicate.sourceGetter?.getterInt || {};
      const details = [
        predicate.getterName || "",
        predicate.getterLocalId != null ? `#${predicate.getterLocalId}` : "",
        predicate.getterUnionTag || "",
        predicate.detailKind || "",
        missionState.missionId || "",
        compare.comparerName || "",
        compare.valueBStateName || "",
        detail.comparerName || detail.operation || "",
        detail.genderName || "",
        detail.propertyKey || "",
        detail.scriptPtr?.mode || detail.targetScript?.mode || "",
        detail.scriptPtr?.scriptId || detail.targetScript?.scriptId || "",
        nativeParamText("A", detail.valueA),
        nativeParamText("B", detail.valueB),
        nativeParamText("min", detail.minimum),
        nativeParamText("max", detail.maximum),
        nativeParamText("value", detail.value),
        nativeParamText("gender", detail.gender),
        predicate.sourceGetter?.getterName || "",
        nativeParamText("source", sourceDetail.value),
        nativeParamText("value", predicate.param),
        ...(predicate.getterTexts || predicate.texts || []),
        ...(predicate.sourceGetter?.getterTexts || []),
      ].filter(Boolean);
      return `<p class="mp-native-predicate"><b>${esc(t("nativePredicate"))}</b>${details.length ? details.map((value) => `<code>${esc(value)}</code>`).join(" ") : `<span>${esc(t("nativePredicateOpaque"))}</span>`}</p>`;
    };
    const nativeBranches = (branches.nativeControlBranches || []).map((row) => `<details><summary><b>${esc(nativeBranchLabel(row.kind))}</b> <code>${esc(row.levelId || "?")}/${esc(row.scriptId || "?")}#${esc(row.branchLocalId ?? "?")}</code></summary><small>${esc(row.eventName || "")}</small>${nativeEventDetailHtml(row.eventDetail)}${nativePredicateHtml(row.predicate)}${(row.arms || []).map((arm) => `<div><code>${esc(arm.edge || "?")} &rarr; #${esc(arm.entryLocalId ?? "?")}</code><span>${(arm.storyKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span></div>`).join("")}</details>`).join("");
    const nativeMerges = (branches.nativeControlMerges || []).map((row) => `<div><b>${esc(t("nativeControlMerge"))}</b><code>#${esc(row.branchLocalId ?? "?")}</code><i>&rarr;</i><code>#${esc(row.mergeLocalId ?? "?")}</code><span>${(row.downstreamStoryKeys || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span></div>`).join("");
    const sceneOptions = (branches.sceneGraphOptions || []).map((row) => `<div><b>${esc(t("optionBranches"))}</b><a href="${esc(storyHref(row.from))}"><code>${esc(row.from || "?")}</code></a><i>&rarr;</i><span>${(row.arms || []).flatMap((arm) => arm.targets || []).map((key) => `<a href="${esc(storyHref(key))}"><code>${esc(key)}</code></a>`).join(" ")}</span></div>`).join("");
    const dialogOptions = (branches.dialogLineOptions || []).map((row) => `<details><summary><code>${esc(row.storyKey || "?")}</code> 路 ${esc(t("optionBranches"))} ${esc(row.group ?? "?")}</summary>${(row.options || []).map((option) => {
      const branchLines = option.branchLineIds || [];
      const directContinuation = option.directContinuation && option.continuationLineId
        ? `<small>${esc(t("optionDirectContinuation"))}</small> <code>${esc(option.continuationLineId)}</code>`
        : "";
      return `<div><code>${esc(option.optionId || "?")}</code><i>&rarr;</i><span>${branchLines.map((line) => `<code>${esc(line)}</code>`).join(" ")}${directContinuation}</span></div>`;
    }).join("")}</details>`).join("");
    const cycles = (order.cycles || []).map((component) => componentHtml(component.id)).join("");
    return `<details class="mp-mission-story mp-story-order" data-weight="${Number(summary.strongEdgeCount) ? "strong" : "context"}"${Number(summary.strongEdgeCount) ? " open" : ""}>
      <summary>${esc(t("storyOrder"))} <span>${Number(summary.sceneCount || 0).toLocaleString()}</span></summary>
      <p>${esc(t("storyOrderHint"))}</p>
      <div class="mp-order-metrics"><span><b>${Number(summary.strongEdgeCount || 0).toLocaleString()}</b>${esc(t("strongEdges"))}</span><span><b>${Number(summary.weakEdgeCount || 0).toLocaleString()}</b>${esc(t("weakEdges"))}</span><span><b>${Number(summary.cycleCount || 0).toLocaleString()}</b>${esc(t("orderCycles"))}</span><span><b>${Number(summary.unorderedScenePairs || 0).toLocaleString()}</b>${esc(t("unknownPairs"))}</span></div>
      ${causalEdges ? `<section><h4>${esc(t("causalEdges"))}</h4><div class="mp-order-edges">${causalEdges}</div></section>` : ""}
      ${frontiers ? `<details class="mp-order-frontiers"><summary>${esc(t("partialFrontier"))}</summary>${frontiers}</details>` : ""}
      ${cycles ? `<section class="mp-order-cycles"><h4>${esc(t("orderCycles"))}</h4><p>${esc(t("orderCycleHint"))}</p>${cycles}</section>` : ""}
      ${questForks || questMerges || nativeBranches || nativeMerges || sceneOptions ? `<section><h4>${esc(t("forkMerge"))}</h4><div class="mp-order-branches">${questForks}${questMerges}${nativeBranches}${nativeMerges}${sceneOptions}</div></section>` : ""}
      ${dialogOptions ? `<section><h4>${esc(t("optionBranches"))}</h4><div class="mp-order-dialog-branches">${dialogOptions}</div></section>` : ""}
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

  function renderMissionSummary() {
    const target = byId("mp-mission-summary");
    if (!target || !state.mission) return;
    const mission = state.mission.mission || {};
    const row = state.index?.missions?.find((item) => item.id === mission.id) || {};
    const caseStudy = state.mission.caseStudy;
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
      <div class="mp-case${caseStudy ? " has-case" : ""}">
        <span class="mp-case-icon" aria-hidden="true">${caseStudy ? "◎" : "○"}</span>
        <div><strong>${esc(caseStudy?.title || t("evidence"))}</strong><p>${esc(caseStudy?.summary || t("noCase"))}</p>${caseStudy ? `<span class="mp-confidence">${esc(t("confidence"))}: ${esc(caseStudy.confidence)}</span>` : ""}</div>
      </div>
      <div class="mp-mission-handshake">
        <strong>${esc(t("missionHandshake"))}</strong>
        <span class="is-outbound">${esc(t("acceptRequest"))}</span>
        <i aria-hidden="true">⇄</i>
        <span class="is-inbound">${esc(t("acceptReturn"))}</span>
        <small>${esc(t("acceptCaveat"))}</small>
      </div>
      ${summarySectionsHtml()}`;
    applySummarySection();
  }

  // The nine evidence blocks used to render as one flat stack of collapsibles.
  // They are grouped into four named bands purely for navigation: every block
  // keeps its own summary, hints and boundary notes verbatim, and the order
  // inside each band is the order it had in the flat stack.
  const SUMMARY_SECTIONS = [
    ["structure", "summarySectionStructure", () => [missionGraphHtml(), storyOrderHtml()]],
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
    const receiverNodes = (state.index?.storyCoverage?.missionlessNativeRuntimeNodes || [])
      .filter((row) => row && row.eventName && row.selector && (row.storyFiles || []).length);
    const rows = [...(contract.outbound || []), ...(contract.inbound || [])];
    const localRows = (contract.localOnly || []).filter((row) => row && row.event);
    const protocolOnlyRows = (contract.protocolOnly || []).filter((row) => row && row.message);
    const missionOptionAudit = contract.missionOptionCarrierAudit || null;
    const missionPropertyAudit = contract.missionPropertyScriptPtrAudit || null;
    const paramSourceAudit = contract.paramSourceMissionContextAudit || null;
    const managedCarrierCensus = contract.managedIdentityCarrierCensus || null;
    const nestedCarrierCensus = contract.nestedManagedIdentityCarrierCensus || null;
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
      ${localRows.length ? `<section class="mp-local-only"><header><strong>${esc(t("localOnlyPaths"))}</strong><span>${esc(t("noServerExchange"))}</span></header><div>${localRows.map((row) => `<article class="mp-contract-card is-local-only"><span>LOCAL · ${esc(row.confidence || "native_proven")}</span><strong>${esc(row.event)}</strong><div class="mp-contract-tags"><b>${esc(t("noServerExchange"))}</b></div>${(row.fields || []).length ? `<small><b>${esc(t("protocolFields"))}:</b> ${(row.fields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</small>` : ""}<code>${esc(row.handler || "")}${row.address ? ` @ ${esc(row.address)}` : ""}</code><p>${esc(row.effect || "")}</p></article>`).join("")}</div></section>` : ""}
      ${protocolOnlyRows.length ? `<section class="mp-local-only mp-protocol-capabilities"><header><strong>${esc(protocolLabel("capability"))}</strong><span>${esc(protocolLabel("schemaOnly"))}</span></header><div>${protocolOnlyRows.map((row) => `<article class="mp-contract-card"><span>${esc(protocolLabel(row.boundary === "runtime_unconfirmed" ? "runtimeUnconfirmed" : "senderUnconfirmed"))}</span><strong>${esc(row.message)}</strong><div class="mp-contract-tags"><b>${esc(row.confidence || "protocol_schema_only")}</b></div>${(row.fields || []).length ? `<small><b>${esc(t("protocolFields"))}:</b> ${(row.fields || []).map((field) => `<code>${esc(field)}</code>`).join(" ")}</small>` : ""}${row.possibleServerPush ? `<small><b>${esc(protocolLabel("possible"))}:</b> <code>${esc(row.possibleServerPush)}</code></small>` : ""}<p>${esc(row.effect || "")}</p></article>`).join("")}</div></section>` : ""}
      ${missionOptionAudit?.finding || missionPropertyAudit?.finding || paramSourceAudit?.finding || managedCarrierCensus?.finding || nestedCarrierCensus?.finding ? `<section class="mp-local-only mp-carrier-audits"><header><strong>${esc(t("carrierAudit"))}</strong><span>${esc(t("noGraphEdges"))}</span></header><div>
        ${missionOptionAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(missionOptionAudit.classification || "schema_only")}</span><strong>${esc(missionOptionAudit.managedCarrier?.type || "MissionOptionData")}</strong><div class="mp-contract-tags"><b>${esc(t("alternateActions"))}</b><b>${esc(t("currentAuthoredInstances"))}: ${Number(missionOptionAudit.authoredInstanceSearch?.matches || 0).toLocaleString()}</b></div><small><b>${esc(t("protocolFields"))}:</b> ${(missionOptionAudit.managedCarrier?.fields || []).map((field) => `<code>${esc(`${field.name}@${field.offset}`)}</code>`).join(" ")}</small><code>${esc(missionOptionAudit.nativeConsumer?.symbol || "")}${missionOptionAudit.nativeConsumer?.address ? ` @ ${esc(missionOptionAudit.nativeConsumer.address)}` : ""}</code><p>${esc(missionOptionAudit.finding)}</p><small>${esc(missionOptionAudit.boundary || "")}</small></article>` : ""}
        ${missionPropertyAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(missionPropertyAudit.classification || "runtime_context_only")}</span><strong>MissionRuntimeAsset.properties → MissionData.propertyDict → ParamVariable.m_scriptPtr</strong><div class="mp-contract-tags"><b>${esc(t("runtimeContextOnly"))}</b><b>${esc(t("authoredPropertyRows"))}: ${Number(missionPropertyAudit.authoredMissionProperties?.propertyRows || 0).toLocaleString()}</b></div><small><b>${esc(t("protocolFields"))}:</b> <code>properties@${esc(missionPropertyAudit.managedLayout?.MissionRuntimeAsset?.properties?.offset || "")}</code> <code>propertyDic@${esc(missionPropertyAudit.managedLayout?.MissionRuntimeAsset?.propertyDic?.offset || "")}</code> <code>m_scriptPtr@${esc(missionPropertyAudit.managedLayout?.ParamVariable?.m_scriptPtr?.offset || "")}</code></small><code>${esc((missionPropertyAudit.missionPropertyWriters || []).map((row) => row.symbol).join(" · "))} → ToVariable</code><p>${esc(missionPropertyAudit.finding)}</p><small>${esc(missionPropertyAudit.boundary || "")}</small></article>` : ""}
        ${paramSourceAudit?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(paramSourceAudit.classification || "implicit_context_only")}</span><strong>ParamSource.CURRENT_MISSION_ID = ${Number(paramSourceAudit.managedContract?.currentMissionId || 0)}</strong><div class="mp-contract-tags"><b>${esc(t("implicitMissionContext"))}</b><b>${esc(t("missionRuntimeUses"))}: ${Number(paramSourceAudit.authoredMissionRuntime?.currentMissionIdOccurrences || 0).toLocaleString()}</b><b>${esc(t("levelScriptUses"))}: ${Number(paramSourceAudit.authoredLevelScripts?.validatedParamTails || 0).toLocaleString()}</b></div><small><b>${esc(t("protocolFields"))}:</b> <code>Param&lt;T&gt;.paramSource ${esc(paramSourceAudit.managedContract?.paramSourceFieldToken || "")}</code> <code>get_isCurrentMissionId ${esc(paramSourceAudit.managedContract?.currentMissionGetterToken || "")}</code></small><code>${Number(paramSourceAudit.authoredLevelScripts?.levelScriptFiles || 0).toLocaleString()} LevelScripts · ${Number(paramSourceAudit.authoredLevelScripts?.uidRecords || 0).toLocaleString()} UID records</code><p>${esc(paramSourceAudit.finding)}</p><small>${esc(paramSourceAudit.boundary || "")}</small></article>` : ""}
        ${managedCarrierCensus?.finding ? `<article class="mp-contract-card is-boundary-only"><span>${esc(managedCarrierCensus.classification || "all_direct_managed_identity_carriers_reviewed")}</span><strong>${esc(t("directManagedCandidates"))}: ${Number(managedCarrierCensus.metadata?.directCandidateTypes || 0).toLocaleString()}</strong><div class="mp-contract-tags"><b>${esc(t("runtimeObjectCandidates"))}: ${Number(managedCarrierCensus.metadata?.runtimeObjectCandidates || 0).toLocaleString()}</b><b>${esc(t("unreviewedCandidates"))}: ${Number(managedCarrierCensus.metadata?.unreviewedCandidates || 0).toLocaleString()}</b><b>${esc(t("trackingContextOnly"))}</b></div><small><b>${esc(t("protocolFields"))}:</b> <code>missionId ${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.missionId?.token || "")}@${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.missionId?.offset || "")}</code> <code>sceneId ${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.sceneId?.token || "")}@${esc(managedCarrierCensus.trackingClosure?.commonTrackingFields?.sceneId?.offset || "")}</code></small><code>${(managedCarrierCensus.trackingClosure?.nativeConsumers || []).map((row) => `${esc(row.symbol || "")}${row.address ? ` @ ${esc(row.address)}` : ""}`).join(" · ")}</code><p>${esc(managedCarrierCensus.finding)}</p><small>${esc(managedCarrierCensus.trackingClosure?.finding || "")}</small><small>${esc(managedCarrierCensus.boundary || "")}</small></article>` : ""}
        ${nestedCarrierCensus?.finding ? `<article class="mp-contract-card is-boundary-only">
          <span>${esc(nestedCarrierCensus.classification || "all_nested_managed_identity_carriers_reviewed")}</span>
          <strong>${esc(t("nestedManagedCandidates"))}: ${Number(nestedCarrierCensus.metadata?.candidateTypes || 0).toLocaleString()}</strong>
          <div class="mp-contract-tags">
            <b>${esc(t("nestedDependentCandidates"))}: ${Number(nestedCarrierCensus.metadata?.nestedDependentCandidateTypes || 0).toLocaleString()}</b>
            <b>${esc(t("maxTypedDepth"))}: ${Number(nestedCarrierCensus.metadata?.maxCustomTypeDepth || 0).toLocaleString()}</b>
            <b>${esc(t("unreviewedCandidates"))}: ${Number(nestedCarrierCensus.metadata?.unreviewedCandidateTypes || 0).toLocaleString()}</b>
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
          <small>${esc(nestedCarrierCensus.pendingItemSubmitterClosure?.finding || "")}</small>
          <small>${esc(nestedCarrierCensus.boundary || "")}</small>
        </article>` : ""}
      </div></section>` : ""}
      ${dynamicSceneRows.length ? `<section class="mp-missionless-runtime mp-dynamic-scene-crossrefs">
        <header><strong>${esc(t("dynamicSceneCrossReferences"))} <span>${dynamicSceneRows.length}</span></strong><p>${esc(t("dynamicSceneCrossReferencesHint"))}</p></header>
        <div class="mp-missionless-runtime-grid">${dynamicSceneRows.map((row) => {
          const conditions = (row.conditions || []).filter((condition) => condition?.identifier);
          const stories = (row.storyOccurrences || []).filter((story) => story?.storyKey);
          return `<article>
            <header><code>${esc(row.scene || "?")}</code><b>${esc(t("candidateContextOnly"))}</b></header>
            <div class="mp-runtime-chain"><span>${esc(t("dynamicSceneLogicId"))}</span><code>${esc(row.logicId || "?")}</code><i aria-hidden="true">=</i><span>${esc(t("levelScriptId"))}</span><code>${esc(row.scriptId || "?")}</code><i aria-hidden="true">⇢</i><b>Story</b></div>
            <p><span>${esc(t("missionStateConditions"))}</span><code>${esc(conditions.map((condition) => `${condition.identifier} ${condition.isSame ? "=" : "!="} ${condition.state ?? "?"}`).join(" · "))}</code></p>
            <div class="mp-missionless-story-links">${stories.map((story) => `<a href="${esc(storyHref(story.storyKey))}" title="${esc(story.sourceFile || "")}"><span>${esc(story.actionName || "Story")}</span><code>${esc(story.storyKey)}</code><b aria-hidden="true">→</b><small>${esc(`${story.levelId || "?"}/${story.scriptId || "?"} @ ${story.recordOffset ?? "?"}`)}</small></a>`).join("")}</div>
            <div class="mp-runtime-associations"><strong>${esc(t("noMissionOwner"))}</strong><div><span>${esc(dynamicSceneAudit.classification || row.classification || "")}</span><b>${esc(t("noGraphEdges"))}</b><small>${esc(dynamicSceneAudit.boundary || dynamicSceneAudit.finding || "")}</small></div></div>
          </article>`;
        }).join("")}</div>
      </section>` : ""}
      ${eventFamilies.length ? `<section class="mp-gap-queue">
        <header><strong>${esc(t("nativeGapQueue"))}</strong><p>${esc(t("nativeGapQueueHint"))}</p></header>
        ${coveragePolicy ? `<p class="mp-gap-policy"><b>${esc(t("evidencePolicy"))}:</b> ${esc(coveragePolicy)}</p>` : ""}
        <div class="mp-gap-family-list">${eventFamilies.map(([eventName, count]) => `<div class="mp-gap-family-row"><code>${esc(eventName)}</code><span><i style="width:${Math.max(4, Math.round((Number(count) / maxEventFamilyCount) * 100))}%"></i></span><b>${Number(count).toLocaleString()}</b></div>`).join("")}</div>
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
        <div class="mp-missionless-runtime-grid">${receiverNodes.map((row) => {
          const selector = row.selector || {};
          const activation = row.activationFrontier || {};
          const activationHosts = (activation.levelDataHosts || [])
            .filter((host) => host && host.fileName);
          const activationDungeonContexts = (activation.dungeonSceneContexts || [])
            .filter((context) => context && context.subGameId && context.sceneId);
          const activationAssociationLabel = (relation) => ({
            subgame_unlock_quest_prerequisite: t("unlockQuestPrerequisite"),
            subgame_unlock_mission_prerequisite: t("unlockMissionPrerequisite"),
            subgame_unlock_previous_game_mechanic: t("unlockPreviousSubGame"),
          })[relation] || t("nonOwningCrossReference");
          const activationTasks = (activation.decodedTaskMap?.tasks || [])
            .filter((task) => task && task.taskKey);
          const activationConsumers = (activation.missionRuntimeScriptConsumers || [])
            .filter((consumer) => consumer && (consumer.missionId || consumer.questId));
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
                ].filter(Boolean);
                const taskLabel = `${t("taskConditionEvidence")} · ${task.taskKey} / objective ${conditionRow.objectiveEnum ?? "?"}${taskSources.length ? ` · ${taskSources.join(" · ")}` : ""}`;
                return `<div><span>${esc(taskLabel)}</span><i aria-hidden="true">→</i><code>${esc(condition.type || "unresolved")}</code><b>${esc(condition.conditionUnionTag || "")}</b>${detail ? `<small>${esc(detail)}</small>` : ""}</div>`;
              })).join("")}
              ${activationTasks.length ? `<small>${esc(t("taskConditionBoundary"))}</small>` : ""}
              <div><span>${esc(t("activationClass"))}</span><i aria-hidden="true">→</i><code>${esc(String(activation.activationClass).replaceAll("_", " "))}</code><b>${esc(t("noMissionOwner"))}</b></div>
              <div><span>${esc(t("startPolicy"))}</span><i aria-hidden="true">→</i><code>${esc(`${activation.startTypeName || "unresolved"} · shapes ${activation.startShapeListStatus || "unresolved"}/${activation.startShapeListCount ?? 0} · taskMap ${activation.taskMapStatus || "unresolved"}/${activation.taskMapCount ?? 0}`)}</code></div>
              ${activationHosts.map((host) => `<div><span>${esc(t("levelDataContainer"))}</span><i aria-hidden="true">→</i><code>${esc(host.fileName)}</code><b>${esc(host.hostMissionId || "generic")}</b><small>${esc(`${host.dictionaryEntryCount ?? "?"} LevelScripts`)}</small></div>`).join("")}
              ${(activation.subGameIds || []).map((subGameId) => `<div><span>SubGame bindScriptId</span><i aria-hidden="true">→</i><code>${esc(subGameId)}</code><b>${esc(t("noMissionOwner"))}</b></div>`).join("")}
              ${activationDungeonContexts.flatMap((context) => [
                `<div><span>${esc(t("dungeonSceneContext"))}</span><i aria-hidden="true">→</i><code>${esc(`${context.subGameId} · ${context.sceneId}`)}</code><b>${esc(context.receiverIsBoundScript ? t("boundReceiverScript") : t("siblingReceiverScript"))}</b><small>${esc([context.dungeonSeriesId, `bindScriptId ${context.bindScriptId}`].filter(Boolean).join(" · "))}</small></div>`,
                ...(context.dungeonMissionContext?.missionId ? [`<div class="is-boundary"><span>${esc(t("dungeonMissionShellContext"))}</span><i aria-hidden="true">⇢</i><code>${esc(context.dungeonMissionContext.missionId)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(context.dungeonMissionContext.finding || "")}</small></div>`] : []),
                ...(context.associations || []).filter((association) => association && association.targetId).map((association) => `<div class="is-boundary"><span>${esc(activationAssociationLabel(association.relation))}</span><i aria-hidden="true">⇢</i><code>${esc(association.targetId)}</code><b>${esc(t("noMissionOwner"))}</b><small>${esc(association.finding || "")}</small></div>`),
              ]).join("")}
              ${activationDungeonContexts.length ? `<small>${esc(t("dungeonSceneBoundary"))}</small>` : ""}
              ${(activation.serializedMissionRuntimeIdTokens || []).length ? `<div><span>${esc(t("serializedMissionIdTokens"))}</span><i aria-hidden="true">→</i><code>${esc(activation.serializedMissionRuntimeIdTokens.join(", "))}</code><b>${esc(t("nonOwningCrossReference"))}</b></div>` : ""}
              ${activationConsumers.map((consumer) => {
                const identity = [consumer.missionId, consumer.questId].filter(Boolean).join("/");
                const objective = consumer.objectiveIndex !== null && consumer.objectiveIndex !== undefined
                  ? ` · objective ${consumer.objectiveIndex}`
                  : "";
                const conditions = (consumer.conditionTypes || []).filter(Boolean).join(", ");
                return `<div class="is-boundary"><span>${esc(t("questObserver"))}</span><i aria-hidden="true">⇢</i><code>${esc(`${identity}${objective}`)}</code><b>${esc(t("observationOnly"))}</b><small>${esc([conditions, consumer.evidenceBoundary || t("questObserverBoundary")].filter(Boolean).join(" · "))}</small></div>`;
              }).join("")}
              <small>${esc(`${t("missionRuntimeConsumers")}: ${activation.missionRuntimeObjectiveConsumerCount ?? 0} · ${t("literalCrossScriptControls")}: ${activation.incomingLiteralCrossControlCount ?? 0} · ${t("exactStartShapeAreaMatches")}: ${activation.exactStartShapeMissionAreaMatchCount ?? 0}`)}</small>
            </div>` : ""}
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
    const tooltip = [objectiveText(node, localizedMap), description.text, activitySummary, runtimeSummary, storySummary].filter(Boolean).join("\n\n");
    return `<button class="${classes.join(" ")}" type="button" data-quest="${esc(node.id)}" aria-pressed="${selected}" style="left:${position.x}px;top:${position.y}px" title="${esc(tooltip)}">
      <span class="mp-card-top"><code>${esc(questShortLabel(node.id))}</code><span class="mp-card-badges">${node.mainPath ? `<span>${esc(t("main"))}</span>` : ""}${isHiddenQuest(node) ? `<span class="is-hidden">${esc(t("hidden"))}</span>` : ""}${storyCounts.incoming ? `<span class="is-story is-incoming">${esc(t("storyIncomingBadge"))} ${storyCounts.incoming}</span>` : ""}${storyCounts.outgoing ? `<span class="is-story is-outgoing">${esc(t("storyOutgoingBadge"))} ${storyCounts.outgoing}</span>` : ""}${storyCounts.context ? `<span class="is-story is-context">${esc(t("storyContextBadge"))} ${storyCounts.context}</span>` : ""}${runtimeObservations.length ? `<span class="is-runtime">${esc(t("runtimeObserved"))} ${runtimeObservations.length}</span>` : ""}${runtimeActions.length ? `<span>${esc(t("openUiAction"))} ${runtimeActions.length}</span>` : ""}<span>${esc(t("flow"))} ${Number(node.flowIndex || 0)}</span></span></span>
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
    return `<article class="mp-objective"><header><strong>${esc(t("objectives"))} ${objective.index}</strong><span class="mp-authority is-${esc(objective.authority)}">${esc(objective.authority)}</span></header>
      <p>${esc(objective.descriptionKey || t("noObjective"))}</p>
      <div class="mp-objective-special">${finishRows}${stateRows}${placeholderRows}${submissionRows}${submissionCoGates}${submissionLevelScriptCoGates}</div>
      ${renderConditionTree(objective.condition)}
    </article>`;
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
      const rows = connections.filter((row) => (row.direction || "context") === direction);
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
    const actionHtml = (node.clientActions || []).map((action) => `<div class="mp-action"><code>${esc(action.type)}</code><span>ID ${esc(action.id ?? "?")} · ${esc(action.triggerName || `trigger ${action.trigger ?? "?"}`)} · ${esc(t("actionChainStep"))} ${esc(Number(action.chainIndex || 0) + 1)}</span></div>`).join("");
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
      ${storyFilesHtml(node)}
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
