(() => {
  const ROW_HEIGHT = 66;
  const OVERSCAN_PX = 260;
  const INDEX_PATH = (language) => `data/lang/${encodeURIComponent(language)}/audio/index.json`;
  const PANE_STORAGE_KEY = "webui_audio_splitter_width";
  const FILTER_HEIGHT_STORAGE_KEY = "webui_filter_splitter_height_audio";
  const FILTER_PANEL_STORAGE_KEY = "audio_browser_filters_collapsed";
  const NOTES_OVERRIDE_PATH = "overrides/audio_notes.json";
  const NOTES_OVERRIDE_SCHEMA = "audioNotes.v1";
  const PLAYER_COLLAPSE_THRESHOLD = 20;
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";

  const TEXT = {
    en: {
      title: "Audio System",
      underConstruction: "Under construction",
      countLabel: "records",
      events: "Events",
      media: "Media",
      hideFilters: "Hide filters",
      showFilters: "Show filters",
      reset: "Reset filters",
      basicFilters: "Basic filters",
      search: "Search event / media / bank / category / manual note",
      manualNote: "Manual note",
      manualNotePlaceholder: "Add a note for this audio record, then choose Save note.",
      manualNoteSave: "Save note",
      manualNoteUnsaved: "Unsaved changes",
      manualNoteSaving: "Saving override…",
      manualNoteSaved: "Saved to override",
      manualNoteStorageError: "Could not save overrides/audio_notes.json.",
      hasManualNote: "Has manual note",
      sort: "Sort",
      sortPurposePriority: "Unknown purpose first",
      sortTitle: "File title (A-Z)",
      sortDurationDesc: "Duration (longest first)",
      sortDurationAsc: "Duration (shortest first)",
      category: "Category",
      eventType: "Event type",
      mediaPurpose: "Media purpose",
      relatedEventTypes: "Related Event types",
      categorySfx: "Sound effects",
      categoryMusic: "Music",
      categoryVoice: "Voice",
      categoryAmbience: "Ambience",
      categoryUi: "UI",
      categoryCue: "Audio cue",
      categoryControl: "Control",
      categoryStoryVoice: "Story voice",
      categoryCharacterVoice: "Character voice",
      categoryEnemyVoice: "Enemy voice",
      categoryVoiceEvents: "Wwise voice Event media",
      context: "Context",
      relation: "Media relation",
      recovery: "Recovery status",
      scope: "Scope",
      source: "Source",
      shown: "shown",
      event: "event",
      mediaItem: "media",
      loading: "Loading audio-system data…",
      loadingEvents: "Loading audio event shards…",
      loadingMedia: "Loading audio media shards…",
      loadError: "Audio-system data could not be loaded.",
      shardError: "This audio dataset could not be loaded.",
      retry: "Retry",
      noMatches: "No audio records match these filters.",
      noData: "No records were emitted for this audio dataset.",
      runtimeSystem: "Runtime system",
      runtimeBoundary: "Evidence boundary",
      runtimeComponents: "Runtime components",
      hircInventory: "Wwise HIRC inventory",
      controlCatalog: "Audio controls / cue catalog",
      physicsAudioCatalog: "Physics / environment audio definitions",
      modelViewStateAudioCatalog: "ModelView state audio behaviors",
      cueOperands: "Cue expression operands",
      globalMusicCues: "Global music cue references",
      rtpcParameters: "RTPC parameters",
      physicsAudioRtpcParameters: "Physics / environment RTPC parameters",
      modelViewStateRtpcParameters: "ModelView state RTPC parameters",
      modelViewStateSpatialControls: "ModelView state spatial controls",
      modelViewStateCustomAudioControls: "ModelView custom-audio controls (unresolved)",
      levelScriptCueInvocations: "LevelScript cue invocations",
      levelScriptDynamicBindings: "LevelScript dynamic Event bindings",
      levelScriptControls: "LevelScript audio controls",
      levelScriptDynamicControls: "LevelScript dynamic control bindings",
      levelEventConditions: "LevelEvent audio conditions",
      wwiseSelectorGroups: "Wwise selector runtime joins",
      wwiseInitialRtpcParameters: "Named Initial RTPC curve parameters",
      wwiseActionControls: "Wwise Action control joins",
      levelScriptRadioCatalog: "LevelScript radio triggers",
      unresolvedRadioIds: "Unresolved radio IDs",
      unresolvedRadioLines: "Unresolved radio lines",
      dynamicRadioBindings: "Dynamic radio ID bindings",
      radioTableLines: "RadioTable dialog lines",
      radioTriggerContexts: "Exact LevelScript radio contexts",
      radioTriggerContextCoverage: "Radio trigger context coverage",
      corpus: "Corpus",
      selectRecord: "Select an event or media record from the left.",
      overview: "Overview",
      details: "Details",
      playableMedia: "Playable media",
      playbackLocation: "Playback location",
      postProcessRoutes: "Serialized post-process routes",
      postProcessBuses: "Output bus paths",
      postProcessBusSemantics: "Serialized Bus processing",
      postProcessEffects: "Effect buses",
      postProcessDirectEffects: "Direct node effects",
      postProcessEffectChain: "Serialized effect chain",
      postProcessBusControls: "Serialized Bus controls",
      postProcessBusDucks: "Serialized Bus ducking",
      postProcessAuxSends: "Serialized Aux sends",
      postProcessProperties: "Serialized node properties",
      postProcessRanges: "Serialized property ranges",
      postProcessRtpcControls: "Serialized RTPC controls",
      postProcessStateControls: "Serialized State overrides",
      wwiseMediaRelations: "Serialized Wwise media edges",
      wwiseMediaPaths: "Serialized selection paths",
      wwiseMediaRootActions: "Serialized root Actions",
      postProcessUnresolved: "Unresolved bus processing",
      postProcessSelection: "Runtime selection boundary",
      postProcessStatus: "Serialized route status",
      postProcessNoExplicitBus: "No explicit output Bus was serialized; default or parent routing remains unresolved.",
      postProcessBusUnresolved: "An output-bus node was serialized, but its typed route was not resolved.",
      triggerContexts: "Serialized trigger contexts",
      triggerKinds: "Trigger semantic kinds",
      triggerRoles: "Trigger roles",
      triggerOwners: "Trigger owners",
      triggerSituations: "Trigger situations",
      triggerSelection: "Trigger selection boundary",
      eventContextSummary: "Event context (possible media set)",
      eventContextKinds: "Event context kinds",
      eventContextRoles: "Event context roles",
      eventContextOwners: "Event context owners",
      eventContextSituations: "Event context situations",
      storyLineBindings: "Exact story-line bindings",
      purposeStatus: "Purpose status",
      libraryBankEvent: "Authored Event in the same bank",
      locationDirectDialogMedia: "Direct dialog media",
      locationAuthoredEventContext: "Recovered authored Event context",
      locationEventRelationOnly: "Event relation recovered; playback location unknown",
      locationUnknown: "Unknown",
      recoveryLibraryResolved: "Resolved to a Wwise Event object",
      recoveryLibraryUnresolved: "Unresolved to an audio-library object",
      recoveryTriggerNameUnknown: "Wwise Event object; authored trigger unknown",
      purposeUnknown: "Purpose unknown — investigate",
      purposePartial: "Partial purpose evidence",
      purposeKnown: "Purpose known",
      purposeStoryTerminal: "Story-line bound — terminal",
      scannedBankSet: "Scanned bank set",
      recoveryBoundary: "Recovery coverage",
      unresolvedEventBoundary: "This authored Event reference has a recovered trigger context, but no matching Wwise Event object was found in the current audio-library index. No media or playback branch is inferred.",
      unknownLocationBoundary: "This decoded file is browser-playable, but no authored Event relation or direct dialog placement was recovered. Its presence in an audio package does not identify where the game plays it.",
      eventOnlyLocationBoundary: "This decoded file is reachable from a Wwise Event, but that Event has no recovered authored trigger context. The Event relation does not identify a gameplay, story, animation, or level placement.",
      unknownTriggerBoundary: "This hash is an exact Wwise Event object from the scanned banks, but no authored name, numeric trigger field, or trigger callsite has been recovered. Its typed playback graph and possible media are real library relations; gameplay or story ownership remains unknown.",
      identityOnlyBoundary: "The authored Event name is recovered by exact skill-id dictionary and SkillData-file identity, and its hash resolves to this Wwise Event object. No audio consumer or Event-hash field was found in the SkillData payload, so the skill is not claimed as its playback trigger or owner.",
      definitionOnlyMediaBoundary: "This decoded file resolves to an exact typed Wwise Sound codec-media object, but no Event in the scanned bank set reaches that Sound/container branch. The audio-library definition is real; its authored playback trigger and runtime location remain unknown.",
      orphanExternalIdentityBoundary: "This 64-bit External Source id has one exact authored path preimage in the bounded d4 mission-voice namespace, recovering the media identity. The current AudioDialog table and source graph contain no definition or trigger for that path, so no dialog, speaker, Event, or playback location is claimed.",
      expandToLoadPlayer: "expand to load player",
      noPlayableMedia: "No browser-playable media path is attached to this record.",
      mediaIds: "Media IDs",
      eventIds: "Event IDs",
      actions: "Actions / objects",
      recordType: "Record type",
      playbackEvent: "Playback event",
      wwiseEvent: "Wwise Event",
      unnamedWwiseEvent: "Wwise Event (authored trigger unknown)",
      authoredEventReference: "Event unresolved to an audio-library object",
      controlEvent: "Control event",
      decodedMedia: "Decoded media",
      contextGroups: "Semantic contexts",
      contextEvidence: "Context evidence",
      contextGameplay: "Gameplay",
      contextCutscene: "Cutscene / story",
      contextTimeline: "Timeline / LevelSequence",
      levelSequenceAudioCatalog: "LevelSequence audio ownership",
      dialogLifecycleAudioCatalog: "Dialog lifecycle audio hooks",
      levelSequenceTimelineContexts: "Timeline contexts",
      levelSequenceExactContexts: "Exact Timeline + LevelScript joins",
      levelSequenceInferredContexts: "Inferred trigger contexts",
      levelSequenceGapContexts: "Ownership gaps",
      levelSequenceRuntimeBoundary: "Timeline runtime boundary",
      audioTriggerContextCatalog: "Authored trigger-context coverage",
      enemyTriggerVoiceActionCatalog: "Enemy trigger-voice action mapping",
      contextAnimation: "Animation",
      contextSharedPlayableAnimation: "Shared playable-character animation",
      contextFootstepSystem: "Footstep / material system",
      customFootstepParameters: "OnCustomFootStep parameters",
      customFootstepRuntime: "Footstep runtime boundary",
      customFootstepNativeAnchors: "Current-build native anchors",
      contextOwnerUnresolvedAnimation: "Animation owner unresolved",
      contextScripted: "LevelScript",
      contextLevelScriptTrigger: "Scripted audio trigger",
      contextRadioTrigger: "Exact LevelScript radio trigger",
      contextExactSkillTrigger: "Exact skill-config Event reference",
      contextInferredSkillTrigger: "Inferred skill ownership",
      contextAuthoredPlaySoundAction: "Authored PlaySound action",
      contextProjectileTrigger: "Projectile lifecycle sound",
      contextSpawnerPreWarn: "Enemy-spawner pre-warning",
      contextNpcPatrolTrigger: "NPC patrol-point audio",
      contextCharacterInteraction: "Character interaction perform",
      contextPhysicsEnvironment: "Physics / environment",
      contextModelViewState: "ModelView state behavior",
      contextComponentAudioId: "Serialized component AudioId",
      contextInteractiveTrigger: "Interactive object trigger",
      contextGlobalLifecycle: "Global audio lifecycle",
      contextDialogLifecycle: "Dialog lifecycle hook",
      contextResponsiveVoice: "Responsive voice route",
      contextAbilityVoiceTrigger: "Ability voice trigger",
      contextVoiceEventRoute: "Voice Event template / override",
      contextTypedUiEvent: "UI / activity audio route",
      contextSnsVoice: "SNS voice message",
      contextAudioCueTrigger: "Audio cue behavior Event",
      contextAuthoredConfig: "Authored config",
      contextManagedRuntime: "Managed-code literal",
      contextNativeTrigger: "Native custom-state callsite",
      contextLuaRuntime: "Lua PostEvent callsite",
      contextWwiseObjectOnly: "Wwise Event object; authored trigger unknown",
      contextDialogMedia: "Dialog media",
      contextEventRelationOnly: "Event relation only; authored placement unknown",
      contextNone: "Playback location unknown",
      relationRuntimeSelected: "Typed runtime-selected branches",
      relationMultipleUnknown: "Multiple possible files; relation unresolved",
      relationSingle: "Single possible file",
      relationSingleTopology: "Single decoded leaf by complete topology (runtime branch unobserved)",
      relationNoDecodedMedia: "Wwise event; no decoded media leaf",
      relationControlOnly: "Wwise control event; no media playback action",
      relationUnresolvedEvent: "No matching Wwise Event object",
      relationEventCandidate: "Wwise event media leaf",
      relationDirectDialogMedia: "Direct dialog media",
      relationUnlinkedMedia: "Playback event unknown",
      relationPartialGraph: "Partial typed graph",
      relationMultipleRoots: "Multiple Play roots",
      relationRandom: "Random alternatives",
      relationSequence: "Sequence items",
      relationSwitch: "Switch / State branches",
      relationLayer: "Layer branches",
      relationDirectSound: "Direct Sound leaf",
      relationMusicSwitch: "Music Switch branches",
      relationMusicPlaylist: "Music playlist branches",
      relationMusicTrack: "Music tracks",
      relationMusicSource: "Music track sources",
      relationExternalSource: "Runtime external source",
      relationSynthesizedSource: "Synthesized / plugin source",
      musicSwitchContainer: "Music Switch container",
      musicRandomSequenceContainer: "Music Random / Sequence container",
      musicSegment: "Music segment",
      musicTrack: "Music track",
      possibleMedia: "Possible media",
      playRoots: "Play roots",
      typedTraversal: "Typed traversal",
      selectorEvidence: "Selector evidence",
      sourceEvidence: "Wwise source evidence",
      actionDispatch: "Action dispatch",
      actionOrdinal: "Action",
      serializedNoDelay: "no serialized delay",
      probabilityGate: "probability gate",
      transitionTime: "transition",
      fadeCurve: "fade curve",
      uniqueContent: "Unique decoded content",
      equivalentContent: "Content-equivalent leaves",
      hotfixMediaReplacement: "Hotfix media-ID replacement",
      rawRecord: "Raw record",
      id: "ID",
      hash: "Hash",
      bank: "Bank",
      path: "Path",
      format: "Format",
      bytes: "Bytes",
      duration: "Duration",
      bitrate: "Bitrate",
      generated: "Generated",
      language: "Language",
      unknown: "unknown",
    },
    zh: {
      title: "\u97f3\u9891\u7cfb\u7edf",
      underConstruction: "\u5efa\u8bbe\u4e2d",
      countLabel: "\u6761\u8bb0\u5f55",
      events: "\u4e8b\u4ef6",
      media: "\u5a92\u4f53",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      showFilters: "\u663e\u793a\u7b5b\u9009",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      search: "\u641c\u7d22\u4e8b\u4ef6 / \u5a92\u4f53 / \u97f3\u9891\u5305 / \u5206\u7c7b / \u624b\u52a8\u5907\u6ce8",
      manualNote: "\u624b\u52a8\u5907\u6ce8",
      manualNotePlaceholder: "\u4e3a\u8fd9\u6761\u97f3\u9891\u6dfb\u52a0\u5907\u6ce8\uff0c\u7136\u540e\u70b9\u51fb\u4fdd\u5b58\u5907\u6ce8\u3002",
      manualNoteSave: "\u4fdd\u5b58\u5907\u6ce8",
      manualNoteUnsaved: "\u6709\u672a\u4fdd\u5b58\u7684\u66f4\u6539",
      manualNoteSaving: "\u6b63\u5728\u4fdd\u5b58 override\u2026",
      manualNoteSaved: "\u5df2\u4fdd\u5b58\u5230 override",
      manualNoteStorageError: "\u65e0\u6cd5\u4fdd\u5b58 overrides/audio_notes.json\u3002",
      hasManualNote: "\u6709\u624b\u52a8\u5907\u6ce8",
      sort: "\u6392\u5e8f",
      sortPurposePriority: "\u672a\u77e5\u7528\u9014\u4f18\u5148",
      sortTitle: "\u6587\u4ef6\u6807\u9898 (A-Z)",
      sortDurationDesc: "\u65f6\u957f\uff08\u4ece\u957f\u5230\u77ed\uff09",
      sortDurationAsc: "\u65f6\u957f\uff08\u4ece\u77ed\u5230\u957f\uff09",
      category: "\u5206\u7c7b",
      eventType: "Event \u7c7b\u578b",
      mediaPurpose: "\u5a92\u4f53\u7528\u9014",
      relatedEventTypes: "\u5173\u8054 Event \u7c7b\u578b",
      categorySfx: "\u97f3\u6548",
      categoryMusic: "\u97f3\u4e50",
      categoryVoice: "\u8bed\u97f3",
      categoryAmbience: "\u73af\u5883\u97f3",
      categoryUi: "UI",
      categoryCue: "Audio Cue",
      categoryControl: "\u63a7\u5236",
      categoryStoryVoice: "\u5267\u60c5\u8bed\u97f3",
      categoryCharacterVoice: "\u89d2\u8272\u8bed\u97f3",
      categoryEnemyVoice: "\u654c\u4eba\u8bed\u97f3",
      categoryVoiceEvents: "Wwise \u8bed\u97f3 Event \u5a92\u4f53",
      context: "\u4e0a\u4e0b\u6587",
      relation: "\u5a92\u4f53\u5173\u7cfb",
      recovery: "\u6062\u590d\u72b6\u6001",
      scope: "\u8303\u56f4",
      source: "\u6765\u6e90",
      shown: "\u5df2\u663e\u793a",
      event: "\u4e8b\u4ef6",
      mediaItem: "\u5a92\u4f53",
      loading: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e…",
      loadingEvents: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u4e8b\u4ef6\u5206\u7247…",
      loadingMedia: "\u6b63\u5728\u52a0\u8f7d\u97f3\u9891\u5a92\u4f53\u5206\u7247…",
      loadError: "\u65e0\u6cd5\u52a0\u8f7d\u97f3\u9891\u7cfb\u7edf\u6570\u636e\u3002",
      shardError: "\u65e0\u6cd5\u52a0\u8f7d\u8be5\u97f3\u9891\u6570\u636e\u96c6\u3002",
      retry: "\u91cd\u8bd5",
      noMatches: "\u6ca1\u6709\u97f3\u9891\u8bb0\u5f55\u7b26\u5408\u5f53\u524d\u7b5b\u9009\u3002",
      noData: "\u8be5\u97f3\u9891\u6570\u636e\u96c6\u6ca1\u6709\u751f\u6210\u8bb0\u5f55\u3002",
      runtimeSystem: "\u8fd0\u884c\u65f6\u7cfb\u7edf",
      runtimeBoundary: "\u8bc1\u636e\u8fb9\u754c",
      runtimeComponents: "\u8fd0\u884c\u65f6\u7ec4\u4ef6",
      hircInventory: "Wwise HIRC \u5e93\u5b58",
      controlCatalog: "\u97f3\u9891\u63a7\u5236 / Cue \u76ee\u5f55",
      physicsAudioCatalog: "\u7269\u7406 / \u73af\u5883\u97f3\u9891\u5b9a\u4e49",
      modelViewStateAudioCatalog: "ModelView \u72b6\u6001\u97f3\u9891\u884c\u4e3a",
      cueOperands: "Cue \u8868\u8fbe\u5f0f\u64cd\u4f5c\u6570",
      globalMusicCues: "\u5168\u5c40\u97f3\u4e50 Cue \u5f15\u7528",
      rtpcParameters: "RTPC \u53c2\u6570",
      physicsAudioRtpcParameters: "\u7269\u7406 / \u73af\u5883 RTPC \u53c2\u6570",
      modelViewStateRtpcParameters: "ModelView \u72b6\u6001 RTPC \u53c2\u6570",
      modelViewStateSpatialControls: "ModelView \u72b6\u6001\u7a7a\u95f4\u97f3\u9891\u63a7\u5236",
      modelViewStateCustomAudioControls: "ModelView \u81ea\u5b9a\u4e49\u97f3\u9891\u63a7\u5236\uff08\u672a\u89e3\u6790\uff09",
      levelScriptCueInvocations: "LevelScript Cue \u8c03\u7528",
      levelScriptDynamicBindings: "LevelScript \u52a8\u6001 Event \u7ed1\u5b9a",
      levelScriptControls: "LevelScript \u97f3\u9891\u63a7\u5236",
      levelScriptDynamicControls: "LevelScript \u52a8\u6001\u63a7\u5236\u7ed1\u5b9a",
      levelEventConditions: "LevelEvent \u97f3\u9891\u6761\u4ef6",
      wwiseSelectorGroups: "Wwise \u9009\u62e9\u5668\u8fd0\u884c\u65f6\u8fde\u63a5",
      wwiseInitialRtpcParameters: "\u5df2\u547d\u540d\u7684 Initial RTPC \u66f2\u7ebf\u53c2\u6570",
      wwiseActionControls: "Wwise Action \u63a7\u5236\u8bed\u4e49\u8fde\u63a5",
      levelScriptRadioCatalog: "LevelScript \u65e0\u7ebf\u7535\u89e6\u53d1",
      unresolvedRadioIds: "\u672a\u89e3\u6790\u7684\u65e0\u7ebf\u7535 ID",
      unresolvedRadioLines: "\u672a\u89e3\u6790\u7684\u65e0\u7ebf\u7535\u53f0\u8bcd",
      dynamicRadioBindings: "\u52a8\u6001\u65e0\u7ebf\u7535 ID \u7ed1\u5b9a",
      radioTableLines: "RadioTable \u5bf9\u8bdd\u884c",
      radioTriggerContexts: "\u7cbe\u786e LevelScript \u65e0\u7ebf\u7535\u4e0a\u4e0b\u6587",
      radioTriggerContextCoverage: "\u65e0\u7ebf\u7535\u89e6\u53d1\u4e0a\u4e0b\u6587\u8986\u76d6",
      corpus: "\u6570\u636e\u96c6",
      selectRecord: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u4e8b\u4ef6\u6216\u5a92\u4f53\u8bb0\u5f55\u3002",
      overview: "\u6982\u89c8",
      details: "\u8be6\u7ec6\u4fe1\u606f",
      playableMedia: "\u53ef\u64ad\u653e\u5a92\u4f53",
      playbackLocation: "\u64ad\u653e\u4f4d\u7f6e",
      postProcessRoutes: "\u5df2\u5e8f\u5217\u5316\u540e\u5904\u7406\u8def\u7531",
      postProcessBuses: "\u8f93\u51fa Bus \u8def\u5f84",
      postProcessBusSemantics: "\u5df2\u5e8f\u5217\u5316 Bus \u5904\u7406",
      postProcessEffects: "\u6548\u679c Bus",
      postProcessDirectEffects: "\u8282\u70b9\u76f4\u63a5\u6548\u679c",
      postProcessEffectChain: "\u5e8f\u5217\u5316\u6548\u679c\u94fe",
      postProcessBusControls: "\u5e8f\u5217\u5316 Bus \u63a7\u5236",
      postProcessBusDucks: "\u5e8f\u5217\u5316 Bus \u538b\u4f4e",
      postProcessAuxSends: "\u5e8f\u5217\u5316 Aux \u53d1\u9001",
      postProcessProperties: "\u5e8f\u5217\u5316\u8282\u70b9\u5c5e\u6027",
      postProcessRanges: "\u5e8f\u5217\u5316\u5c5e\u6027\u8303\u56f4",
      postProcessRtpcControls: "\u5e8f\u5217\u5316 RTPC \u63a7\u5236",
      postProcessStateControls: "\u5e8f\u5217\u5316 State \u8986\u76d6",
      eventContextSummary: "Event \u4e0a\u4e0b\u6587（\u53ef\u80fd\u5a92\u4f53\u96c6\u5408）",
      eventContextKinds: "Event \u4e0a\u4e0b\u6587\u7c7b\u578b",
      eventContextRoles: "Event \u4e0a\u4e0b\u6587\u89d2\u8272",
      eventContextOwners: "Event \u4e0a\u4e0b\u6587\u6240\u6709\u8005",
      eventContextSituations: "Event \u4e0a\u4e0b\u6587\u60c5\u5883",
      wwiseMediaRelations: "\u5e8f\u5217\u5316 Wwise \u5a92\u4f53\u8fb9",
      wwiseMediaPaths: "\u5e8f\u5217\u5316\u9009\u62e9\u8def\u5f84",
      wwiseMediaRootActions: "\u5e8f\u5217\u5316\u6839 Action",
      postProcessUnresolved: "\u672a\u89e3\u6790\u7684 Bus \u5904\u7406",
      postProcessSelection: "\u8fd0\u884c\u65f6\u9009\u62e9\u8bc1\u636e\u8fb9\u754c",
      postProcessStatus: "\u5df2\u5e8f\u5217\u5316\u8def\u7531\u72b6\u6001",
      postProcessNoExplicitBus: "\u5e8f\u5217\u5316\u6570\u636e\u4e2d\u6ca1\u6709\u663e\u5f0f\u8f93\u51fa Bus\uff1b\u9ed8\u8ba4\u6216\u7236\u7ea7\u8def\u7531\u4ecd\u672a\u89e3\u6790\u3002",
      postProcessBusUnresolved: "\u5df2\u5e8f\u5217\u5316\u8f93\u51fa Bus \u8282\u70b9\uff0c\u4f46\u5176\u7c7b\u578b\u5316\u8def\u7531\u672a\u89e3\u6790\u3002",
      triggerContexts: "\u5df2\u5e8f\u5217\u5316\u89e6\u53d1\u4e0a\u4e0b\u6587",
      triggerKinds: "\u89e6\u53d1\u8bed\u4e49类型",
      triggerRoles: "\u89e6\u53d1\u89d2\u8272",
      triggerOwners: "\u89e6\u53d1所有者",
      triggerSituations: "\u89e6\u53d1情境",
      triggerSelection: "\u89e6\u53d1选\u62e9证据\u8fb9\u754c",
      storyLineBindings: "\u7cbe\u786e\u5267\u60c5\u53f0\u8bcd\u7ed1\u5b9a",
      purposeStatus: "\u7528\u9014\u72b6\u6001",
      libraryBankEvent: "\u540c\u4e00 bank \u5185\u7684\u521b\u4f5c Event",
      locationDirectDialogMedia: "\u76f4\u63a5\u5bf9\u8bdd\u5a92\u4f53",
      locationAuthoredEventContext: "\u5df2\u6062\u590d\u521b\u4f5c Event \u4e0a\u4e0b\u6587",
      locationEventRelationOnly: "\u5df2\u6062\u590d Event \u5173\u7cfb\uff0c\u4f46\u4e0d\u77e5\u9053\u64ad\u653e\u4f4d\u7f6e",
      locationUnknown: "\u4e0d\u77e5\u9053\u64ad\u653e\u4f4d\u7f6e",
      recoveryLibraryResolved: "\u5df2\u89e3\u6790\u5230 Wwise Event \u5bf9\u8c61",
      recoveryLibraryUnresolved: "\u672a\u89e3\u6790\u5230\u97f3\u9891\u5e93\u5bf9\u8c61",
      recoveryTriggerNameUnknown: "Wwise Event \u5bf9\u8c61\u5b58\u5728\uff0c\u521b\u4f5c\u89e6\u53d1\u672a\u77e5",
      purposeUnknown: "\u7528\u9014\u672a\u77e5\uff0c\u4f18\u5148\u8c03\u67e5",
      purposePartial: "\u4ec5\u6709\u90e8\u5206\u7528\u9014\u8bc1\u636e",
      purposeKnown: "\u7528\u9014\u5df2\u77e5",
      purposeStoryTerminal: "\u5df2\u7ed1\u5b9a\u5267\u60c5\u53f0\u8bcd\uff0c\u7ec8\u6001",
      scannedBankSet: "\u5df2\u626b\u63cf bank \u96c6\u5408",
      recoveryBoundary: "\u6062\u590d\u8986\u76d6",
      enemyTriggerVoiceActionCatalog: "\u654c\u4eba\u8bed\u97f3\u89e6\u53d1\u52a8\u4f5c\u6620\u5c04",
      unresolvedEventBoundary: "\u8be5\u521b\u4f5c Event \u5f15\u7528\u6709\u5df2\u6062\u590d\u7684\u89e6\u53d1\u4e0a\u4e0b\u6587\uff0c\u4f46\u5f53\u524d\u97f3\u9891\u5e93\u7d22\u5f15\u4e2d\u6ca1\u6709\u627e\u5230\u5bf9\u5e94\u7684 Wwise Event \u5bf9\u8c61\u3002\u4e0d\u4f1a\u56e0\u6b64\u63a8\u65ad\u5a92\u4f53\u6216\u64ad\u653e\u5206\u652f\u3002",
      unknownLocationBoundary: "\u8be5\u6587\u4ef6\u5df2\u89e3\u7801\u4e14\u53ef\u5728\u6d4f\u89c8\u5668\u4e2d\u64ad\u653e\uff0c\u4f46\u6ca1\u6709\u6062\u590d\u51fa\u521b\u4f5c Event \u5173\u7cfb\u6216\u76f4\u63a5\u5bf9\u8bdd\u4f4d\u7f6e\u3002\u6587\u4ef6\u5b58\u5728\u4e8e\u97f3\u9891\u5305\u4e2d\u4e0d\u80fd\u8bf4\u660e\u6e38\u620f\u5728\u54ea\u91cc\u64ad\u653e\u5b83\u3002",
      eventOnlyLocationBoundary: "\u8be5\u6587\u4ef6\u53ef\u4ece Wwise Event \u5230\u8fbe\uff0c\u4f46\u8be5 Event \u6ca1\u6709\u5df2\u6062\u590d\u7684\u521b\u4f5c\u89e6\u53d1\u4e0a\u4e0b\u6587\u3002Event \u5173\u7cfb\u4e0d\u80fd\u786e\u5b9a\u5176\u73a9\u6cd5\u3001\u5267\u60c5\u3001\u52a8\u753b\u6216\u5173\u5361\u4f4d\u7f6e\u3002",
      unknownTriggerBoundary: "\u8be5\u54c8\u5e0c\u662f\u5df2\u626b\u63cf bank \u4e2d\u7684\u7cbe\u786e Wwise Event \u5bf9\u8c61\uff0c\u4f46\u5c1a\u672a\u6062\u590d\u521b\u4f5c\u540d\u79f0\u3001\u6570\u503c\u89e6\u53d1\u5b57\u6bb5\u6216\u89e6\u53d1\u8c03\u7528\u4f4d\u7f6e\u3002\u7c7b\u578b\u5316\u64ad\u653e\u56fe\u548c\u53ef\u80fd\u5a92\u4f53\u662f\u771f\u5b9e\u97f3\u9891\u5e93\u5173\u7cfb\uff0c\u73a9\u6cd5\u6216\u5267\u60c5\u5f52\u5c5e\u4ecd\u672a\u77e5\u3002",
      identityOnlyBoundary: "\u5df2\u901a\u8fc7\u7cbe\u786e\u7684 skill_id \u5b57\u5178\u548c\u540c\u540d SkillData \u6587\u4ef6\u6062\u590d Event \u540d\u79f0\uff0c\u4e14\u54c8\u5e0c\u6307\u5411\u8be5 Wwise Event \u5bf9\u8c61\u3002SkillData \u8f7d\u8377\u4e2d\u672a\u627e\u5230\u97f3\u9891\u6d88\u8d39\u8005\u6216 Event \u54c8\u5e0c\u5b57\u6bb5\uff0c\u56e0\u6b64\u4e0d\u4f1a\u5c06\u8be5\u6280\u80fd\u58f0\u79f0\u4e3a\u64ad\u653e\u89e6\u53d1\u5668\u6216\u6240\u6709\u8005\u3002",
      definitionOnlyMediaBoundary: "\u8be5\u89e3\u7801\u6587\u4ef6\u5df2\u7cbe\u786e\u89e3\u6790\u5230\u7c7b\u578b\u5316 Wwise Sound \u7f16\u89e3\u7801\u5a92\u4f53\u5bf9\u8c61\uff0c\u4f46\u5df2\u626b\u63cf bank \u4e2d\u6ca1\u6709 Event \u5230\u8fbe\u8be5 Sound / \u5bb9\u5668\u5206\u652f\u3002\u97f3\u9891\u5e93\u5b9a\u4e49\u662f\u771f\u5b9e\u7684\uff0c\u5176\u521b\u4f5c\u64ad\u653e\u89e6\u53d1\u548c\u8fd0\u884c\u65f6\u4f4d\u7f6e\u4ecd\u672a\u77e5\u3002",
      orphanExternalIdentityBoundary: "\u8be5 64 \u4f4d External Source ID \u5728\u6709\u754c d4 \u4efb\u52a1\u8bed\u97f3\u547d\u540d\u7a7a\u95f4\u4e2d\u53ea\u6709\u4e00\u4e2a\u7cbe\u786e\u521b\u4f5c\u8def\u5f84\u539f\u50cf\uff0c\u56e0\u6b64\u53ef\u6062\u590d\u5a92\u4f53\u8eab\u4efd\u3002\u5f53\u524d AudioDialog \u8868\u548c\u6e90\u56fe\u4e2d\u90fd\u6ca1\u6709\u8be5\u8def\u5f84\u7684\u5b9a\u4e49\u6216\u89e6\u53d1\uff0c\u56e0\u6b64\u4e0d\u58f0\u79f0\u5bf9\u8bdd\u3001\u8bf4\u8bdd\u4eba\u3001Event \u6216\u64ad\u653e\u4f4d\u7f6e\u3002",
      expandToLoadPlayer: "\u5c55\u5f00\u540e\u52a0\u8f7d\u64ad\u653e\u5668",
      noPlayableMedia: "\u8be5\u8bb0\u5f55\u672a\u9644\u52a0\u6d4f\u89c8\u5668\u53ef\u64ad\u653e\u7684\u5a92\u4f53\u8def\u5f84\u3002",
      mediaIds: "\u5a92\u4f53 ID",
      eventIds: "\u4e8b\u4ef6 ID",
      actions: "\u52a8\u4f5c / \u5bf9\u8c61",
      recordType: "\u8bb0\u5f55\u7c7b\u578b",
      playbackEvent: "\u64ad\u653e\u4e8b\u4ef6",
      wwiseEvent: "Wwise Event",
      unnamedWwiseEvent: "Wwise Event\uff08\u521b\u4f5c\u89e6\u53d1\u672a\u77e5\uff09",
      authoredEventReference: "\u672a\u89e3\u6790\u5230\u97f3\u9891\u5e93\u5bf9\u8c61\u7684\u4e8b\u4ef6",
      controlEvent: "\u63a7\u5236\u4e8b\u4ef6",
      decodedMedia: "\u5df2\u89e3\u7801\u5a92\u4f53",
      contextGroups: "\u8bed\u4e49\u4e0a\u4e0b\u6587",
      contextEvidence: "\u4e0a\u4e0b\u6587\u8bc1\u636e",
      contextGameplay: "\u73a9\u6cd5",
      contextCutscene: "\u8fc7\u573a / \u5267\u60c5",
      contextTimeline: "Timeline / LevelSequence",
      levelSequenceAudioCatalog: "LevelSequence \u97f3\u9891\u5f52\u5c5e",
      dialogLifecycleAudioCatalog: "\u5bf9\u8bdd\u751f\u547d\u5468\u671f\u97f3\u9891\u94a9\u5b50",
      levelSequenceTimelineContexts: "Timeline \u4e0a\u4e0b\u6587",
      levelSequenceExactContexts: "\u7cbe\u786e Timeline + LevelScript \u8fde接",
      levelSequenceInferredContexts: "\u63a8断触发\u4e0a\u4e0b\u6587",
      levelSequenceGapContexts: "\u5f52属缺口",
      levelSequenceRuntimeBoundary: "Timeline \u8fd0行时证据边界",
      audioTriggerContextCatalog: "音频触发情境覆盖",
      contextAnimation: "\u52a8\u753b",
      contextSharedPlayableAnimation: "\u53ef\u73a9\u89d2\u8272\u5171\u7528\u52a8\u753b",
      contextFootstepSystem: "\u811a\u6b65 / \u6750\u8d28\u7cfb\u7edf",
      customFootstepParameters: "OnCustomFootStep \u53c2\u6570",
      customFootstepRuntime: "\u811a\u6b65\u8fd0\u884c\u65f6\u8bc1\u636e\u8fb9\u754c",
      customFootstepNativeAnchors: "\u5f53\u524d\u7248\u672c\u539f\u751f\u951a\u70b9",
      contextOwnerUnresolvedAnimation: "\u52a8\u753b\u5f52\u5c5e\u672a\u89e3\u6790",
      contextScripted: "LevelScript \u811a\u672c",
      contextLevelScriptTrigger: "\u811a\u672c\u97f3\u9891\u89e6\u53d1",
      contextRadioTrigger: "\u7cbe\u786e LevelScript \u65e0\u7ebf\u7535\u89e6\u53d1",
      contextExactSkillTrigger: "\u7cbe\u786e\u6280\u80fd\u914d\u7f6e Event \u5f15\u7528",
      contextInferredSkillTrigger: "\u63a8\u65ad\u6280\u80fd\u5f52\u5c5e",
      contextAuthoredPlaySoundAction: "\u521b\u4f5c PlaySound \u52a8\u4f5c",
      contextProjectileTrigger: "\u6295\u5c04\u7269\u751f\u547d\u5468\u671f\u97f3\u6548",
      contextSpawnerPreWarn: "\u654c\u4eba\u751f\u6210\u5668\u9884\u8b66\u97f3\u6548",
      contextNpcPatrolTrigger: "NPC \u5de1\u903b\u70b9\u97f3\u9891",
      contextCharacterInteraction: "\u89d2\u8272\u4ea4\u4e92\u8868\u6f14",
      contextPhysicsEnvironment: "\u7269\u7406 / \u73af\u5883",
      contextModelViewState: "ModelView \u72b6\u6001\u884c\u4e3a",
      contextComponentAudioId: "\u5e8f\u5217\u5316\u7ec4\u4ef6 AudioId",
      contextInteractiveTrigger: "\u4ea4\u4e92\u7269\u4ef6\u89e6\u53d1",
      contextGlobalLifecycle: "\u5168\u5c40\u97f3\u9891\u751f\u547d\u5468\u671f",
      contextDialogLifecycle: "\u5bf9\u8bdd\u751f\u547d\u5468\u671f\u94a9\u5b50",
      contextResponsiveVoice: "\u54cd\u5e94\u8bed\u97f3\u89e6\u53d1\u94fe",
      contextAbilityVoiceTrigger: "\u6280\u80fd\u8bed\u97f3\u89e6\u53d1",
      contextVoiceEventRoute: "\u8bed\u97f3 Event \u6a21\u677f / \u8986\u76d6\u8def\u7531",
      contextTypedUiEvent: "UI / \u6d3b\u52a8\u97f3\u9891\u8def\u7531",
      contextSnsVoice: "SNS \u8bed\u97f3\u6d88\u606f",
      contextAudioCueTrigger: "Audio Cue \u884c\u4e3a Event",
      contextAuthoredConfig: "\u914d\u7f6e\u8868",
      contextManagedRuntime: "\u6258\u7ba1\u4ee3\u7801\u5b57\u9762\u91cf",
      contextNativeTrigger: "原生自定义状态调用点",
      contextLuaRuntime: "Lua PostEvent \u8c03\u7528\u4f4d\u7f6e",
      contextWwiseObjectOnly: "Wwise Event \u5bf9\u8c61\uff0c\u521b\u4f5c\u89e6\u53d1\u672a\u77e5",
      contextDialogMedia: "\u5bf9\u8bdd\u5a92\u4f53",
      contextEventRelationOnly: "\u5df2\u6062\u590d Event \u5173\u7cfb\uff0c\u521b\u4f5c\u89e6\u53d1\u4f4d\u7f6e\u672a\u77e5",
      contextNone: "\u4e0d\u77e5\u9053\u64ad\u653e\u4f4d\u7f6e",
      relationRuntimeSelected: "\u7c7b\u578b\u5316\u8fd0\u884c\u65f6\u5206\u652f",
      relationMultipleUnknown: "\u591a\u4e2a\u53ef\u80fd\u6587\u4ef6\uff0c\u5173\u7cfb\u672a\u89e3\u6790",
      relationSingle: "\u5355\u4e00\u53ef\u80fd\u6587\u4ef6",
      relationSingleTopology: "\u5b8c\u6574\u62d3\u6251\u4e2d\u4ec5\u6709\u4e00\u4e2a\u89e3\u7801\u53f6\uff08\u8fd0\u884c\u65f6\u5206\u652f\u4ecd\u672a\u89c2\u6d4b\uff09",
      relationNoDecodedMedia: "Wwise \u4e8b\u4ef6\uff0c\u65e0\u5df2\u89e3\u7801\u5a92\u4f53\u53f6",
      relationControlOnly: "Wwise \u63a7\u5236\u4e8b\u4ef6\uff0c\u65e0\u5a92\u4f53\u64ad\u653e\u52a8\u4f5c",
      relationUnresolvedEvent: "\u672a\u627e\u5230\u5bf9\u5e94\u7684 Wwise Event \u5bf9\u8c61",
      relationEventCandidate: "Wwise \u4e8b\u4ef6\u5a92\u4f53\u53f6",
      relationDirectDialogMedia: "\u76f4\u63a5\u5bf9\u8bdd\u5a92\u4f53",
      relationUnlinkedMedia: "\u4e0d\u77e5\u9053\u7531\u54ea\u4e2a\u4e8b\u4ef6\u64ad\u653e",
      relationPartialGraph: "\u90e8\u5206\u7c7b\u578b\u5316\u56fe",
      relationMultipleRoots: "\u591a\u4e2a Play \u6839",
      relationRandom: "\u968f\u673a\u5907\u9009",
      relationSequence: "\u5e8f\u5217\u9879",
      relationSwitch: "Switch / State \u5206\u652f",
      relationLayer: "Layer \u5206\u652f",
      relationDirectSound: "\u76f4\u63a5 Sound \u53f6",
      relationMusicSwitch: "\u97f3\u4e50 Switch \u5206\u652f",
      relationMusicPlaylist: "\u97f3\u4e50\u64ad\u653e\u5217\u8868\u5206\u652f",
      relationMusicTrack: "\u97f3\u4e50\u8f68\u9053",
      relationMusicSource: "\u97f3\u4e50\u8f68\u9053\u97f3\u6e90",
      relationExternalSource: "\u8fd0\u884c\u65f6\u5916\u90e8\u97f3\u6e90",
      relationSynthesizedSource: "\u5408\u6210 / \u63d2\u4ef6\u97f3\u6e90",
      musicSwitchContainer: "\u97f3\u4e50 Switch \u5bb9\u5668",
      musicRandomSequenceContainer: "\u97f3\u4e50\u968f\u673a / \u5e8f\u5217\u5bb9\u5668",
      musicSegment: "\u97f3\u4e50\u7247\u6bb5",
      musicTrack: "\u97f3\u4e50\u8f68\u9053",
      possibleMedia: "\u53ef\u80fd\u5a92\u4f53",
      playRoots: "Play \u6839",
      typedTraversal: "\u7c7b\u578b\u5316\u904d\u5386",
      selectorEvidence: "\u9009\u62e9\u5668\u8bc1\u636e",
      sourceEvidence: "Wwise \u97f3\u6e90\u8bc1\u636e",
      actionDispatch: "Action \u6d3e\u53d1",
      actionOrdinal: "Action",
      serializedNoDelay: "\u672a\u5e8f\u5217\u5316\u5ef6\u8fdf",
      probabilityGate: "\u6982\u7387\u95e8",
      transitionTime: "\u8fc7\u6e21",
      fadeCurve: "\u6de1\u5165\u66f2\u7ebf",
      uniqueContent: "\u552f\u4e00\u89e3\u7801\u5185\u5bb9",
      equivalentContent: "\u5185\u5bb9\u7b49\u4ef7\u53f6",
      hotfixMediaReplacement: "Hotfix \u540c media ID \u66ff\u6362",
      rawRecord: "\u539f\u59cb\u8bb0\u5f55",
      id: "ID",
      hash: "\u54c8\u5e0c",
      bank: "\u97f3\u9891\u5305",
      path: "\u8def\u5f84",
      format: "\u683c\u5f0f",
      bytes: "\u5b57\u8282",
      duration: "\u65f6\u957f",
      bitrate: "\u6bd4\u7279\u7387",
      generated: "\u751f\u6210\u65f6\u95f4",
      language: "\u8bed\u8a00",
      unknown: "\u672a\u77e5",
    },
  };

  const state = {
    initialized: false,
    container: null,
    language: "CN",
    uiLocale: "zh",
    index: null,
    indexPromise: null,
    indexController: null,
    loadToken: 0,
    datasets: { events: null, media: null },
    datasetPromises: { events: null, media: null },
    datasetControllers: { events: [], media: [] },
    mode: "events",
    filtered: [],
    rows: [],
    selected: null,
    query: "",
    sort: "purpose-priority",
    filters: { categories: new Set(), contexts: new Set(), relations: new Set(), recovery: new Set(), scopes: new Set(), sources: new Set() },
    eventTaxonomyById: new Map(),
    gameParameterNameById: new Map(),
    eventDetailCache: new Map(),
    eventDetailPromises: new Map(),
    notes: {},
    notesPromise: null,
    filterPanel: null,
    renderFrame: 0,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const locale = () => String(window.WEBUI_UI_LOCALE || state.uiLocale || document.documentElement.lang || "zh").toLowerCase().startsWith("en") ? "en" : "zh";
  const t = (key) => (TEXT[locale()] || TEXT.en)[key] || TEXT.en[key] || key;
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
  const normalize = (value) => String(value ?? "").trim();
  const normalizeLower = (value) => normalize(value).toLowerCase();
  const asArray = (value) => Array.isArray(value) ? value : (value === undefined || value === null || value === "" ? [] : [value]);
  const isMobileLayout = () => !!window.matchMedia?.(MOBILE_LAYOUT_QUERY).matches;
  const parsePixels = (value, fallback = 0) => {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  function currentLanguage() {
    return String($("#language")?.value || state.language || "CN").toUpperCase();
  }

  function formatNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString() : normalize(value);
  }

  function formatBytes(value) {
    let bytes = Number(value);
    if (!Number.isFinite(bytes) || bytes < 0) return normalize(value);
    const units = ["B", "KB", "MB", "GB"];
    let unit = 0;
    while (bytes >= 1024 && unit < units.length - 1) {
      bytes /= 1024;
      unit += 1;
    }
    const digits = unit === 0 || bytes >= 100 ? 0 : bytes >= 10 ? 1 : 2;
    return `${bytes.toFixed(digits)} ${units[unit]}`;
  }

  function recordDuration(record) {
    const duration = Number(record?.duration ?? record?.durationSeconds);
    return Number.isFinite(duration) && duration > 0 ? duration : null;
  }

  function recordBitrate(record) {
    const bitrate = Number(record?.bitrate ?? record?.bitRate);
    if (Number.isFinite(bitrate) && bitrate > 0) return bitrate;
    const duration = recordDuration(record);
    const bytes = Number(record?.bytes);
    return duration && Number.isFinite(bytes) && bytes > 0 ? bytes * 8 / duration : null;
  }

  function formatDuration(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds <= 0) return "";
    if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
    const whole = Math.round(seconds);
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    const remainder = whole % 60;
    return hours
      ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`
      : `${minutes}:${String(remainder).padStart(2, "0")}`;
  }

  function formatBitrate(value) {
    const bitrate = Number(value);
    if (!Number.isFinite(bitrate) || bitrate <= 0) return "";
    const kbps = bitrate / 1000;
    return `${kbps.toFixed(kbps < 100 ? 1 : 0)} kbps`;
  }

  function recordId(record, kind = state.mode) {
    const raw = kind === "events"
      ? (record?.eventId ?? record?.id ?? record?.name ?? record?.eventHash ?? record?.hash)
      : (record?.mediaId ?? record?.id ?? record?.name ?? record?.rel ?? record?.src);
    return normalize(raw);
  }

  function uniqueMediaEventId(record) {
    const eventIds = collectIds(record, ["eventIds", "events", "eventId"]);
    return eventIds.length === 1 ? eventIds[0] : "";
  }

  function recordTitle(record, kind = state.mode) {
    if (kind === "events") return normalize(record?.eventName ?? record?.name ?? record?.eventId ?? record?.id ?? record?.eventHash) || t("unknown");
    const eventId = uniqueMediaEventId(record);
    if (eventId) return eventId;
    return normalize(record?.name ?? record?.title ?? record?.mediaId ?? record?.id ?? fileName(record?.rel ?? record?.path ?? record?.src)) || t("unknown");
  }

  function recordCategory(record) {
    return normalize(record?.eventCategory ?? record?.semanticCategory ?? record?.audioCategory ?? record?.category ?? record?.kind) || t("unknown");
  }

  async function loadNotes(force = false) {
    if (state.notesPromise && !force) return state.notesPromise;
    const promise = (async () => {
      try {
        const response = await fetch(NOTES_OVERRIDE_PATH, { cache: "no-store" });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        const payload = await response.json();
        state.notes = payload?.notes && typeof payload.notes === "object" && !Array.isArray(payload.notes) ? { ...payload.notes } : {};
      } catch (error) {
        console.warn(`Unable to load ${NOTES_OVERRIDE_PATH}`, error);
        state.notes = state.notes || {};
      }
      return state.notes;
    })().finally(() => {
      state.notesPromise = null;
    });
    state.notesPromise = promise;
    return promise;
  }

  async function persistNotes(notes = state.notes) {
    const payload = {
      _schema: NOTES_OVERRIDE_SCHEMA,
      _note: "Manual searchable notes for Audio Event/media records. Keys use <LANG>:<events|media>:<record id>. Edited from the Audio page UI.",
      notes,
    };
    const response = await fetch(NOTES_OVERRIDE_PATH, {
      method: "PUT",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: `${JSON.stringify(payload, null, 2)}\n`,
    });
    if (!response.ok) {
      let message = "";
      try {
        message = String((await response.json())?.error || "");
      } catch (_error) {
        message = "";
      }
      throw new Error(message || `HTTP ${response.status}`);
    }
    return true;
  }

  function noteKey(record) {
    return `${state.language}:${record?.kind || state.mode}:${record?.key || ""}`;
  }

  function recordNote(record) {
    return normalize(state.notes[noteKey(record)]);
  }

  function notesWithRecordUpdate(record, value) {
    const notes = { ...state.notes };
    const key = noteKey(record);
    const note = normalize(value);
    if (note) notes[key] = note;
    else delete notes[key];
    return notes;
  }

  function firstNoteLine(record) {
    return recordNote(record).split(/\r?\n/, 1)[0].trim();
  }

  const CATEGORY_LABEL_KEYS = {
    sfx: "categorySfx", music: "categoryMusic", voice: "categoryVoice",
    ambience: "categoryAmbience", ui: "categoryUi", cue: "categoryCue",
    cues: "categoryCue", control: "categoryControl", story_voice: "categoryStoryVoice",
    character_voice: "categoryCharacterVoice", enemy_voice: "categoryEnemyVoice",
    voice_events: "categoryVoiceEvents", unknown: "unknown",
  };

  function categoryLabel(value) {
    const normalized = normalize(value);
    return t(CATEGORY_LABEL_KEYS[normalized] || normalized || "unknown");
  }

  function recordScope(record) {
    const direct = normalize(record?.audioScope ?? record?.scope ?? record?.storageRoot);
    if (direct) return direct;
    const values = [...new Set(asArray(record?.media).map((row) => normalize(row?.audioScope ?? row?.storageRoot)).filter(Boolean))];
    return values.length === 1 ? values[0] : values.length > 1 ? "mixed" : t("unknown");
  }

  function recordSource(record) {
    const direct = normalize(record?.sourceBlockLabel ?? record?.sourceBlock ?? record?.sourceBank ?? record?.source);
    if (direct) return direct;
    const evidenceSource = asArray(record?.evidence).map((row) => normalize(row?.source)).find(Boolean);
    if (evidenceSource) return evidenceSource;
    const mediaSource = asArray(record?.media).map((row) => normalize(row?.sourceBlockLabel ?? row?.sourceBlock ?? row?.sourceBank)).find(Boolean);
    return mediaSource || t("unknown");
  }

  const CONTEXT_LABEL_KEYS = {
    gameplay: "contextGameplay",
    cutscene: "contextCutscene",
    timeline: "contextTimeline",
    animation: "contextAnimation",
    sharedPlayableAnimation: "contextSharedPlayableAnimation",
    footstepSystem: "contextFootstepSystem",
    ownerUnresolvedAnimation: "contextOwnerUnresolvedAnimation",
    scripted: "contextScripted",
    levelScriptTrigger: "contextLevelScriptTrigger",
    radioTrigger: "contextRadioTrigger",
    exactSkillTrigger: "contextExactSkillTrigger",
    inferredSkillTrigger: "contextInferredSkillTrigger",
    authoredPlaySoundAction: "contextAuthoredPlaySoundAction",
    projectileTrigger: "contextProjectileTrigger",
    spawnerPreWarnTrigger: "contextSpawnerPreWarn",
    npcPatrolTrigger: "contextNpcPatrolTrigger",
    characterInteraction: "contextCharacterInteraction",
    physicsEnvironment: "contextPhysicsEnvironment",
    modelViewState: "contextModelViewState",
    componentAudioId: "contextComponentAudioId",
    interactiveTrigger: "contextInteractiveTrigger",
    globalLifecycle: "contextGlobalLifecycle",
    dialogLifecycle: "contextDialogLifecycle",
    responsiveVoice: "contextResponsiveVoice",
    abilityVoiceTrigger: "contextAbilityVoiceTrigger",
    voiceEventRoute: "contextVoiceEventRoute",
    typedUiEvent: "contextTypedUiEvent",
    snsVoice: "contextSnsVoice",
    audioCueTrigger: "contextAudioCueTrigger",
    authoredConfig: "contextAuthoredConfig",
    managedRuntime: "contextManagedRuntime",
    luaRuntime: "contextLuaRuntime",
    wwiseObjectOnly: "contextWwiseObjectOnly",
    dialogMedia: "contextDialogMedia",
    eventRelationOnly: "contextEventRelationOnly",
    none: "contextNone",
  };

  const RELATION_LABEL_KEYS = {
    runtimeSelected: "relationRuntimeSelected",
    multipleUnknown: "relationMultipleUnknown",
    single: "relationSingle",
    singleTopology: "relationSingleTopology",
    noDecodedMedia: "relationNoDecodedMedia",
    controlOnly: "relationControlOnly",
    unresolvedEvent: "relationUnresolvedEvent",
    eventCandidate: "relationEventCandidate",
    directDialogMedia: "relationDirectDialogMedia",
    unlinkedMedia: "relationUnlinkedMedia",
    partialGraph: "relationPartialGraph",
    multipleRoots: "relationMultipleRoots",
    randomAlternative: "relationRandom",
    sequenceItem: "relationSequence",
    switchCandidate: "relationSwitch",
    layerChild: "relationLayer",
    directSound: "relationDirectSound",
    musicSwitchCandidate: "relationMusicSwitch",
    musicPlaylistCandidate: "relationMusicPlaylist",
    musicTrack: "relationMusicTrack",
    musicTrackSource: "relationMusicSource",
    externalSource: "relationExternalSource",
    synthesizedSource: "relationSynthesizedSource",
  };

  function taxonomyLabel(value) {
    return t(CONTEXT_LABEL_KEYS[value] || RELATION_LABEL_KEYS[value] || value);
  }

  function playbackLocationLabel(value) {
    return t({
      directDialogMedia: "locationDirectDialogMedia",
      authoredContext: "locationAuthoredEventContext",
      authoredEventContext: "locationAuthoredEventContext",
      eventRelationOnly: "locationEventRelationOnly",
      unknown: "locationUnknown",
    }[normalize(value)] || "locationUnknown");
  }

  function recoveryLabel(value) {
    return t({
      libraryResolved: "recoveryLibraryResolved",
      libraryUnresolved: "recoveryLibraryUnresolved",
      triggerNameUnknown: "recoveryTriggerNameUnknown",
      purposeUnknown: "purposeUnknown",
      purposePartial: "purposePartial",
      purposeKnown: "purposeKnown",
      purposeStoryTerminal: "purposeStoryTerminal",
      directDialogMedia: "locationDirectDialogMedia",
      authoredEventContext: "locationAuthoredEventContext",
      eventRelationOnly: "locationEventRelationOnly",
      unknown: "locationUnknown",
    }[normalize(value)] || value);
  }

  function purposeRecoveryTag(record) {
    const priority = normalize(record?.purposeInvestigationPriority);
    if (priority === "resolvedTerminal" || Number(record?.storyLineBindingCount || 0) > 0) return "purposeStoryTerminal";
    if (priority === "highest") return "purposeUnknown";
    if (priority === "secondary") return "purposePartial";
    if (priority === "resolved") return "purposeKnown";
    return "";
  }

  function recordType(record, kind) {
    if (kind === "media") return "decodedMedia";
    if (record?.playbackRole === "controlOnly" || recordCategory(record) === "control") return "controlEvent";
    if (record?.eventIdentityStatus === "wwiseObjectWithoutRecoveredTriggerName") return "unnamedWwiseEvent";
    return record?.foundInWwise ? "wwiseEvent" : "authoredEventReference";
  }

  function contextGroup(kind) {
    if (["characterSkill", "enemySkill", "buffPlaySoundAction", "projectileSoundField", "abilityVoiceTriggerAction"].includes(kind)) return "gameplay";
    if (kind === "cutsceneTimeline") return "cutscene";
    if (kind === "levelSequenceAudio") return "timeline";
    if (kind === "timelineAudioCueBehaviorEvent") return "timeline";
    if (["characterAnimation", "enemyAnimation", "animationCallbackOwnerUnresolved"].includes(kind)) return "animation";
    if (["levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent", "levelScriptRadioTrigger"].includes(kind)) return "scripted";
    if (["table", "tableEventHash", "dialogLifecycle", "interactiveAudioTrigger", "interactiveComponentTrigger", "interactiveComponentPropertyAudio", "interactivePropertyMapAudio", "interactiveTemplateConfigAudio", "interactiveTemplateActionAudio", "interactiveEmbeddedActionAudio", "binaryManagedLiteralCallsite", "nativeCustomStateCallsite", "physicsAudioComponentEvent", "modelViewStateAudioEvent", "modelViewStatePositionAudioEvent", "monoBehaviourAudioIdField", "audioGlobalConfigEvent", "audioGlobalConfigEventHash", "audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent", "spawnerPreWarnAudio", "patrolSubActionPlayAudio", "charInteractAudioEvent", "audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant", "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent", "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent", "responsiveVoiceEventTemplate", "voiceTableWwiseEvent", "uiAnimationOpenEvent", "activityPushPopupBgmEvent", "activityCenterBgmEvent", "uiVideoAudioEvent", "domainRegionSwitchEvent", "domainUpgradeAnimationEvent", "typedUiTableWwiseEvent", "snsVoiceMessageEvent"].includes(kind)) return "authoredConfig";
    if (kind === "binaryManagedLiteral") return "managedRuntime";
    if (kind === "luaPostEvent") return "luaRuntime";
    return "";
  }

  function recordContextTags(record, kind) {
    const tags = new Set(asArray(record?.contextGroups).filter(Boolean));
    if (record?.eventIdentityStatus === "wwiseObjectWithoutRecoveredTriggerName") tags.add("wwiseObjectOnly");
    const addContextKindTags = (contextKind) => {
      if (contextKind === "projectileSoundField") tags.add("projectileTrigger");
      if (contextKind === "levelSequenceAudio") tags.add("timeline");
      if (contextKind === "timelineAudioCueBehaviorEvent") tags.add("timeline");
      if (contextKind === "spawnerPreWarnAudio") tags.add("spawnerPreWarnTrigger");
      if (contextKind === "patrolSubActionPlayAudio") tags.add("npcPatrolTrigger");
      if (contextKind === "charInteractAudioEvent") tags.add("characterInteraction");
      if (contextKind === "physicsAudioComponentEvent") tags.add("physicsEnvironment");
      if (["modelViewStateAudioEvent", "modelViewStatePositionAudioEvent"].includes(contextKind)) tags.add("modelViewState");
      if (contextKind === "monoBehaviourAudioIdField") tags.add("componentAudioId");
      if (["audioCueBehaviorEvent", "audioGlobalMusicCueBehaviorEvent", "levelScriptAudioCueBehaviorEvent", "timelineAudioCueBehaviorEvent"].includes(contextKind)) tags.add("audioCueTrigger");
      if (["interactiveAudioTrigger", "interactiveComponentTrigger", "interactiveComponentPropertyAudio", "interactivePropertyMapAudio", "interactiveTemplateConfigAudio", "interactiveTemplateActionAudio", "interactiveEmbeddedActionAudio"].includes(contextKind)) tags.add("interactiveTrigger");
      if (["audioGlobalConfigEvent", "audioGlobalConfigEventHash", "audioGlobalMusicCueBehaviorEvent"].includes(contextKind)) tags.add("globalLifecycle");
      if (contextKind === "dialogLifecycle") tags.add("dialogLifecycle");
      if (["audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant", "voiceDefaultWwiseEvent", "voiceNarratingChannelEvent", "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent", "responsiveVoiceEventTemplate", "voiceTableWwiseEvent"].includes(contextKind)) tags.add("responsiveVoice");
      if (contextKind === "abilityVoiceTriggerAction") tags.add("abilityVoiceTrigger");
      if (["voiceDefaultWwiseEvent", "voiceNarratingChannelEvent", "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent", "responsiveVoiceEventTemplate", "voiceTableWwiseEvent"].includes(contextKind)) tags.add("voiceEventRoute");
      if (["uiAnimationOpenEvent", "activityPushPopupBgmEvent", "activityCenterBgmEvent", "uiVideoAudioEvent", "domainRegionSwitchEvent", "domainUpgradeAnimationEvent", "typedUiTableWwiseEvent"].includes(contextKind)) tags.add("typedUiEvent");
      if (contextKind === "snsVoiceMessageEvent") tags.add("snsVoice");
      if (contextKind === "animationCallbackOwnerUnresolved") tags.add("ownerUnresolvedAnimation");
      if (["levelScriptAudioAction", "levelScriptAudioCueBehaviorEvent", "levelScriptRadioTrigger"].includes(contextKind)) tags.add("levelScriptTrigger");
      if (contextKind === "levelScriptRadioTrigger") tags.add("radioTrigger");
      if (contextKind === "luaPostEvent") tags.add("luaRuntime");
      if (contextKind === "nativeCustomStateCallsite") tags.add("nativeTrigger");
    };
    for (const contextKind of asArray(record?.contextKinds)) addContextKindTags(contextKind);
    for (const status of asArray(record?.triggerBindingStatuses)) {
      if (status === "exactSkillConfig") tags.add("exactSkillTrigger");
      else if (status === "inferredSkillConfigOwner") tags.add("inferredSkillTrigger");
    }
    if (Number(record?.triggerPlaySoundActionCount || 0) > 0) tags.add("authoredPlaySoundAction");
    for (const context of asArray(record?.contexts)) {
      if (!context || typeof context !== "object") continue;
      const group = contextGroup(normalize(context.kind));
      if (group) tags.add(group);
      if (context.triggerBindingStatus === "exactSkillConfig") tags.add("exactSkillTrigger");
      else if (context.triggerBindingStatus === "inferredSkillConfigOwner") tags.add("inferredSkillTrigger");
      if (Number(context.triggerPlaySoundActionCount || 0) > 0) tags.add("authoredPlaySoundAction");
      addContextKindTags(context.kind);
    }
    for (const context of asArray(record?.radioTriggerContexts)) {
      if (!context || typeof context !== "object") continue;
      const group = contextGroup(normalize(context.kind));
      if (group) tags.add(group);
      addContextKindTags(context.kind);
    }
    if (Number(record?.radioTriggerContextCount || 0) > 0) {
      tags.add("scripted");
      tags.add("levelScriptTrigger");
      tags.add("radioTrigger");
    }
    if (Number(record?.playableCharacterAnimationOwnerCount || 0) > 1 || record?.animationContextScope === "sharedPlayableCharacters") {
      tags.add("sharedPlayableAnimation");
    }
    if (asArray(record?.animationFunctions).includes("OnCustomFootStep")) tags.add("footstepSystem");
    if (kind === "media") {
      if (record?.audioDialogKey || record?.audioDialogPath) tags.add("dialogMedia");
      const inheritedMediaTags = new Set([
        "gameplay", "cutscene", "timeline", "animation", "scripted", "authoredConfig", "managedRuntime", "luaRuntime", "wwiseObjectOnly",
        "sharedPlayableAnimation", "footstepSystem", "ownerUnresolvedAnimation", "levelScriptTrigger", "radioTrigger", "projectileTrigger", "spawnerPreWarnTrigger", "npcPatrolTrigger", "characterInteraction", "physicsEnvironment", "modelViewState", "componentAudioId", "interactiveTrigger", "globalLifecycle", "audioCueTrigger", "snsVoice",
      ]);
      for (const eventId of asArray(record?.eventIds)) {
        for (const tag of state.eventTaxonomyById.get(normalizeLower(eventId)) || []) {
          if (inheritedMediaTags.has(tag)) tags.add(tag);
        }
      }
      if (record?.playbackLocationStatus === "unknown") tags.add("none");
      else if (record?.playbackLocationStatus === "eventRelationOnly") tags.add("eventRelationOnly");
    }
    if (!tags.size) tags.add("none");
    return [...tags];
  }

  function recordRelationTags(record, kind) {
    if (kind === "media") {
      if (record?.audioDialogKey || record?.audioDialogPath) return ["directDialogMedia"];
      if (asArray(record?.eventIds).length || Number(record?.eventCount) > 0) return ["eventCandidate"];
      return ["unlinkedMedia"];
    }
    const evidence = asArray(record?.evidence).filter((value) => value && typeof value === "object");
    const foundInWwise = record?.foundInWwise === true || (record?.foundInWwise !== false && evidence.length > 0);
    const candidates = Number(record?.possibleMediaCount ?? record?.candidateCount ?? record?.resolvedMediaCount ?? record?.mediaCount)
      || asArray(record?.media).length;
    if (!foundInWwise) return ["unresolvedEvent"];
    const tags = [];
    const sourceKinds = new Set([
      ...asArray(record?.sourceKinds),
      ...evidence.flatMap((row) => Object.keys(row?.sourceObjectSummary?.sourceKindCounts || {})),
    ]);
    if (sourceKinds.has("externalSourceCodec")) tags.push("externalSource");
    if (sourceKinds.has("synthesizedSource")) tags.push("synthesizedSource");
    if (!candidates) {
      tags.push(record?.playbackRole === "controlOnly" ? "controlOnly" : "noDecodedMedia");
      return [...new Set(tags)];
    }
    if (record?.traversalStatus === "partial") tags.push("partialGraph");
    if (Number(record?.playRootCount) > 1) tags.push("multipleRoots");
    const hasTypedSelector = asArray(record?.selectionContainerTypes).length > 0;
    const hasOneCompleteTopologyLeaf = hasTypedSelector
      && candidates === 1
      && record?.traversalStatus === "complete"
      && Number(record?.unresolvedNodeCount || 0) === 0;
    if (hasOneCompleteTopologyLeaf) tags.push("singleTopology");
    for (const relation of asArray(record?.mediaRelationTypes)) {
      if (RELATION_LABEL_KEYS[relation]) tags.push(relation);
    }
    if (asArray(record?.selectionContainerTypes).length && !tags.some((value) => ["randomAlternative", "sequenceItem", "switchCandidate", "layerChild"].includes(value))) tags.push("runtimeSelected");
    if (!tags.length) tags.push(candidates === 1 ? "single" : "multipleUnknown");
    return [...new Set(tags)];
  }

  function recordMeta(record, kind = state.mode, taxonomy = {}, { includeFileStats = true } = {}) {
    const parts = [
      t(taxonomy.objectType || recordType(record, kind)),
      `${t(kind === "events" ? "eventType" : "mediaPurpose")}: ${categoryLabel(recordCategory(record))}`,
    ];
    if (kind === "media") {
      const relatedEventTypes = asArray(record?.relatedEventCategories).filter(Boolean);
      if (relatedEventTypes.length) {
        parts.push(`${t("relatedEventTypes")}: ${relatedEventTypes.map(categoryLabel).join(" + ")}`);
      }
    }
    const contexts = asArray(taxonomy.contextTags);
    if (contexts.length) parts.push(contexts.map(taxonomyLabel).join(" + "));
    const relations = asArray(taxonomy.relationTags);
    if (relations.length) parts.push(relations.slice(0, 2).map(taxonomyLabel).join(" + "));
    const purposeTag = purposeRecoveryTag(record);
    if (purposeTag) parts.push(`${t("purposeStatus")}: ${recoveryLabel(purposeTag)}`);
    if (kind === "events") {
      const count = Number(record?.possibleMediaCount ?? record?.resolvedMediaCount ?? record?.mediaCount ?? record?.candidateCount)
        || asArray(record?.mediaIds).length
        || asArray(record?.media).length;
      if (count) parts.push(`${formatNumber(count)} ${t("media")}`);
    } else if (includeFileStats && record?.bytes !== undefined) {
      parts.push(formatBytes(record.bytes));
      const duration = recordDuration(record);
      const bitrate = recordBitrate(record);
      if (duration) parts.push(formatDuration(duration));
      if (bitrate) parts.push(formatBitrate(bitrate));
    }
    return [...new Set(parts.filter(Boolean))].join(" · ");
  }

  function recordFileStats(record, kind = state.mode) {
    if (kind !== "media") return "";
    return [
      formatDuration(recordDuration(record)),
      record?.bytes !== undefined ? formatBytes(record.bytes) : "",
      formatBitrate(recordBitrate(record)),
    ].filter(Boolean).join(" / ");
  }

  function searchText(record, kind, taxonomy = {}) {
    const numericHashes = [record?.hash, record?.eventHash].filter((value) => Number.isInteger(Number(value)));
    const values = [
      recordTitle(record, kind), recordId(record, kind), recordCategory(record), recordScope(record), recordSource(record),
      record?.name, record?.title,
      ...asArray(record?.relatedEventCategories).flatMap((value) => [value, categoryLabel(value)]),
      record?.hash, record?.eventHash, ...numericHashes.map((value) => `0x${(Number(value) >>> 0).toString(16).padStart(8, "0")}`),
      record?.mediaId, record?.bankId, record?.bank, record?.rel, record?.path, record?.src,
      ...asArray(record?.eventIds), ...asArray(record?.mediaIds), ...asArray(record?.actionIds), ...asArray(record?.visitedObjectIds),
      ...asArray(record?.contextSearch), ...asArray(record?.radioTriggerSearch), ...asArray(record?.radioTriggerActions),
      ...asArray(record?.radioTriggerRoles), ...asArray(record?.bankPackages),
      ...asArray(record?.sourceKinds), ...asArray(record?.sourcePluginIds),
      ...asArray(taxonomy.contextTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(taxonomy.relationTags).flatMap((value) => [value, taxonomyLabel(value)]),
      ...asArray(record?.contexts).flatMap((context) => context && typeof context === "object" ? [
        context.kind, context.ownerId, context.groupId, context.storyKey, context.table, context.path,
        context.consumerType, context.consumerMethod, context.playbackCall, context.triggerRole,
        context.customStateName, context.switchMethod, context.switchMethodVa, context.callsiteVa,
        context.staticArgumentVa, context.metadataUsageWord, context.metadataStringLiteralIndex,
        context.selectorType, context.selectorMethod, context.selectorMethodVa, context.selectorLoadVa, context.selectorCallVa,
        context.selectorField, context.selectorFieldOffset, context.additionalConsumerMethod,
        context.additionalMethodVa, context.additionalSelectorLoadVa, context.additionalSelectorCallVa, context.additionalPlaybackCallVa,
        context.methodVa, context.literalLoadVa, context.playbackCallVa, context.targetBinding,
        context.playbackParameter, context.literalArgumentRegister,
        context.literalArgumentInstruction, context.branchCondition,
        context.playbackHashCall, context.playbackHashCallVa, context.playbackHashInvocationVa,
        context.playbackSink, context.playbackSinkVa, context.playbackSinkInvocationVa, context.playbackInvocationVa,
        context.configKind, context.configId, context.ownerLinkStatus,
        context.semanticRole, context.confidence, context.animationOwnershipScope, context.possibleMediaScope,
        context.modelId, context.subTemplateId, context.triggerStateId, context.triggerStateName,
        context.triggerCustomState, context.ownerKind, context.stateDirection, context.audioStateMask, context.description,
        context.enemyTriggerVoiceActionStatus,
        ...Object.values(context.enemyTriggerVoiceAction || {}),
        context.authoredFieldRole, context.serializedFieldPath, context.componentName,
        context.authoredEventName, context.authoredEventNameEvidence,
        context.gameObjectName, ...asArray(context.hierarchyPath), context.serializedFile,
        context.objectIndexSource, context.rawJsonSource, context.sourceAssetFile,
        ...Object.entries(context.serializedPlaybackControls || {}).flat(),
        context.componentIndex, context.componentType, context.componentTag, context.sourceOffset,
        context.propertyMapOffset, context.audioPropertyKey, context.audioAction, context.audioActionRole,
        context.audioSourceField, context.actionMapRole, context.actionLocalId, context.actionUid,
        context.actionUnionTag, context.actionMapOffset, context.actionRecordOffset, context.actionPayloadOffset,
        context.targetBindingKind, context.targetParamSource,
        context.sourceFingerprint, ...asArray(context.sourcePaths),
        context.authoredEventId, context.spawnerConfigId, context.enemyLibraryIndex, context.enemyId,
        context.bornTemplateId, context.enemyLevel, context.spawnerEnemyKey, context.preWarnTime,
        context.preWarnEffectKey, ...asArray(context.preWarnEffectFixedRotation), ...asArray(context.bornBuffIds),
        context.charInteractPerformId, context.actionPhase, context.actionIndex, context.logicId,
        context.attachedActorType, context.charIndex, context.runtimeOwnerStatus,
        context.attachedActorResolutionStatus,
        context.definitionOwnerId, context.templatePath, context.componentTag, context.componentTagHex,
        context.componentOccurrenceIndex,
        context.propertyCount, context.authoredProperty, context.runtimeField,
        ...asArray(context.consumerIds), ...asArray(context.consumerAliasIds),
        ...asArray(context.interactiveTemplateIds), context.interactiveTemplatePath,
        ...asArray(context.interactiveConsumerIds), context.templateAssociationStatus,
        ...asArray(context.interactiveTableSourcePaths), context.interactiveTableSha256,
        context.action, context.levelScriptId, context.sourcePath, context.sourceSha256,
        context.recordUid, context.recordLocalId, context.actionMapRole, context.eventName,
        context.triggerRole, context.sourceField,
        context.clipReachability, context.triggerBindingStatus, ...asArray(context.skillIds), ...asArray(context.actionKinds),
        ...asArray(context.triggerRequestEvidence), ...asArray(context.triggerRuntimeActivationStatuses),
        ...asArray(context.triggerRelationTypes), ...asArray(context.triggerOwnershipMethods),
        ...asArray(context.triggerEvidenceKinds), ...asArray(context.triggerBuffIds), ...asArray(context.triggerSourcePaths),
        ...asArray(context.triggerPlaySoundActions).flatMap((action) => action && typeof action === "object" ? Object.values(action).flat() : []),
        ...asArray(context.animationFunctions), ...asArray(context.animationClipContexts), ...asArray(context.animationClips),
      ] : []),
      ...asArray(record?.radioTableLineIdentities).flatMap((line) => line && typeof line === "object" ? [
        line.radioId, line.lineId, line.lineOrdinal, line.authoredIndex, line.audioOverride,
        line.actorNameId, line.is3D === true ? "3D" : (line.is3D === false ? "2D" : ""),
        line.source, line.audioOverrideIdentityKind, line.wwiseEventStatus,
      ] : []),
      ...asArray(record?.radioTriggerContexts).flatMap((context) => context && typeof context === "object" ? [
        context.kind, context.radioId, context.action, context.triggerRole, context.levelScriptId,
        context.sourcePath, context.sourceField, context.actionMapRole, context.audioDialogMatchEvidence,
        context.runtimeActivationStatus, context.wwiseEventStatus,
        ...Object.values(context.radioDefinition || {}), ...Object.values(context.radioLine || {}),
      ] : []),
    ];
    return values.filter((value) => value !== undefined && value !== null).join("\n").toLowerCase();
  }

  function normalizeRecord(record, kind, index) {
    const raw = record && typeof record === "object" ? record : { id: record };
    const contextTags = recordContextTags(raw, kind);
    const relationTags = recordRelationTags(raw, kind);
    const objectType = recordType(raw, kind);
    const taxonomy = { contextTags, relationTags, objectType };
    const purposeTag = purposeRecoveryTag(raw);
    const recoveryTags = kind === "events"
      ? [
          raw.foundInWwise ? "libraryResolved" : "libraryUnresolved",
          ...(raw.eventIdentityStatus === "wwiseObjectWithoutRecoveredTriggerName" ? ["triggerNameUnknown"] : []),
          ...(purposeTag ? [purposeTag] : []),
        ]
      : [normalize(raw.playbackLocationStatus) || "unknown", ...(purposeTag ? [purposeTag] : [])];
    return {
      raw,
      kind,
      key: recordId(raw, kind) || `${kind}-${index}`,
      title: recordTitle(raw, kind),
      category: recordCategory(raw),
      scope: recordScope(raw),
      source: recordSource(raw),
      contextTags,
      relationTags,
      recoveryTags,
      objectType,
      meta: recordMeta(raw, kind, taxonomy),
      listMeta: recordMeta(raw, kind, taxonomy, { includeFileStats: false }),
      fileStats: recordFileStats(raw, kind),
      search: [
        searchText(raw, kind, taxonomy),
        ...recoveryTags.flatMap((value) => [value, recoveryLabel(value)]),
      ].join("\n").toLowerCase(),
    };
  }

  function rebuildEventTaxonomy(records) {
    state.eventTaxonomyById = new Map();
    for (const record of records || []) {
      const keys = [recordId(record.raw, "events"), record.raw?.name, record.raw?.eventId, record.raw?.id]
        .map(normalizeLower).filter(Boolean);
      for (const key of keys) state.eventTaxonomyById.set(key, record.contextTags || ["none"]);
    }
  }

  function dedupeRecords(records, kind) {
    const seen = new Set();
    const output = [];
    for (const [index, record] of records.entries()) {
      const normalized = normalizeRecord(record, kind, index);
      let key = normalized.key;
      if (seen.has(key)) key = `${key}#${index}`;
      seen.add(key);
      normalized.key = key;
      output.push(normalized);
    }
    return output;
  }

  function recordsFromPayload(payload, kind) {
    if (Array.isArray(payload)) return payload;
    if (!payload || typeof payload !== "object") return [];
    for (const key of [kind, "entries", "records", "items", "data"]) {
      if (Array.isArray(payload[key])) return payload[key];
    }
    return [];
  }

  function shardSpecs(value) {
    if (!value) return [];
    if (typeof value === "string") return [{ path: value }];
    if (Array.isArray(value)) return value.flatMap(shardSpecs);
    if (typeof value !== "object") return [];
    const path = value.path || value.file || value.url || value.src;
    if (path) return [{ ...value, path: String(path) }];
    for (const key of ["files", "parts", "shards"]) {
      if (value[key]) return shardSpecs(value[key]);
    }
    return [];
  }

  function shardUrl(path, indexPath) {
    const value = normalize(path).replace(/\\/g, "/");
    if (!value) return "";
    if (/^(?:https?:)?\/\//i.test(value) || value.startsWith("/") || value.startsWith("data/")) return value;
    return new URL(value, new URL(indexPath, window.location.href)).toString();
  }

  async function ensureEventDetail(record) {
    const shard = normalize(record?.raw?.detailShard);
    if (!shard || record?.raw?._detailLoaded) return record?.raw;
    let records = state.eventDetailCache.get(shard);
    if (!records) {
      let promise = state.eventDetailPromises.get(shard);
      if (!promise) {
        const token = state.loadToken;
        const url = shardUrl(shard, INDEX_PATH(state.language));
        promise = fetch(url).then((response) => {
          if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
          return response.json();
        }).then((payload) => {
          if (token !== state.loadToken) return new Map();
          const rows = new Map(recordsFromPayload(payload, "events").map((row) => [normalizeLower(recordId(row, "events")), row]));
          state.eventDetailCache.set(shard, rows);
          return rows;
        }).finally(() => state.eventDetailPromises.delete(shard));
        state.eventDetailPromises.set(shard, promise);
      }
      records = await promise;
    }
    const detail = records?.get(normalizeLower(recordId(record.raw, "events")));
    if (!detail) return record.raw;
    record.raw = { ...record.raw, ...detail, _detailLoaded: true };
    record.contextTags = recordContextTags(record.raw, record.kind);
    record.relationTags = recordRelationTags(record.raw, record.kind);
    record.meta = recordMeta(record.raw, record.kind, record);
    record.listMeta = recordMeta(record.raw, record.kind, record, { includeFileStats: false });
    record.fileStats = recordFileStats(record.raw, record.kind);
    record.search = searchText(record.raw, record.kind, record);
    if (state.selected === record) renderDetail();
    return record.raw;
  }

  function abortDataset(kind) {
    for (const controller of state.datasetControllers[kind] || []) controller.abort();
    state.datasetControllers[kind] = [];
    state.datasetPromises[kind] = null;
  }

  function abortAll() {
    state.indexController?.abort();
    abortDataset("events");
    abortDataset("media");
  }

  async function ensureDataset(kind, { token = state.loadToken, force = false, progressBase = 0, progressSpan = 1 } = {}) {
    if (!force && state.datasets[kind]) return state.datasets[kind];
    if (!force && state.datasetPromises[kind]) return state.datasetPromises[kind];
    abortDataset(kind);

    const inline = recordsFromPayload(state.index?.[kind], kind);
    const specs = shardSpecs(state.index?.shards?.[kind]);
    if (!specs.length) {
      const records = dedupeRecords(inline, kind);
      if (kind === "events") rebuildEventTaxonomy(records);
      state.datasets[kind] = records;
      return records;
    }

    const indexPath = INDEX_PATH(state.language);
    const progress = specs.map(() => 0);
    const controllers = specs.map(() => new AbortController());
    state.datasetControllers[kind] = controllers;
    const label = t(kind === "events" ? "loadingEvents" : "loadingMedia");
    const updateProgress = () => {
      const ratio = progress.reduce((total, value) => total + value, 0) / Math.max(1, progress.length);
      window.WebUI?.updateLoader?.("audio", progressBase + ratio * progressSpan, label);
    };

    const promise = Promise.all(specs.map(async (spec, index) => {
      const url = shardUrl(spec.path, indexPath);
      if (!url) return [];
      const response = await window.WebUI.fetchWithProgress(url, {
        signal: controllers[index].signal,
        cache: force ? "reload" : "default",
        onProgress: (ratio) => {
          if (ratio !== null && Number.isFinite(ratio)) progress[index] = Math.max(progress[index], Math.min(0.98, ratio));
          updateProgress();
        },
      });
      if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
      const payload = await response.json();
      progress[index] = 1;
      updateProgress();
      return recordsFromPayload(payload, kind);
    })).then((parts) => {
      if (token !== state.loadToken) return null;
      const records = dedupeRecords([...inline, ...parts.flat()], kind);
      if (kind === "events") rebuildEventTaxonomy(records);
      state.datasets[kind] = records;
      return records;
    }).finally(() => {
      if (token === state.loadToken) {
        state.datasetPromises[kind] = null;
        state.datasetControllers[kind] = [];
      }
    });
    state.datasetPromises[kind] = promise;
    return promise;
  }

  async function load(language = currentLanguage(), { force = false } = {}) {
    init();
    const nextLanguage = String(language || "CN").toUpperCase();
    if (!force && state.index && state.language === nextLanguage && state.datasets.events) return state.index;
    if (!force && state.indexPromise && state.language === nextLanguage) return state.indexPromise;

    abortAll();
    const token = ++state.loadToken;
    state.language = nextLanguage;
    state.mode = "events";
    state.index = null;
    state.datasets = { events: null, media: null };
    state.datasetPromises = { events: null, media: null };
    state.eventTaxonomyById = new Map();
    state.gameParameterNameById = new Map();
    state.eventDetailCache = new Map();
    state.eventDetailPromises = new Map();
    state.selected = null;
    state.indexController = new AbortController();
    resetFilters({ render: false });
    syncModeButtons();
    renderLoadingList();
    renderDetail();
    window.WebUI?.clearShellStatus?.("audio");
    window.WebUI?.setViewBusy?.("audio", true);
    window.WebUI?.showLoader?.("audio", t("loading"));

    const promise = (async () => {
      try {
        await loadNotes(force);
        const path = INDEX_PATH(nextLanguage);
        const response = await window.WebUI.fetchWithProgress(path, {
          signal: state.indexController.signal,
          cache: force ? "reload" : "default",
          onProgress: (ratio) => window.WebUI?.updateLoader?.("audio", ratio === null ? null : ratio * 0.25, t("loading")),
        });
        if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
        const payload = await response.json();
        if (token !== state.loadToken) return null;
        state.index = payload && typeof payload === "object" ? payload : {};
        state.gameParameterNameById = new Map(asArray(
          state.index?.hircSummary?.postProcessSummary?.gameParameterNameEvidence?.entries,
        ).filter((row) => row && typeof row === "object").map((row) => [
          Number(row.parameterId),
          String(row.metadataField || "").split(".").pop() || "GameParameter",
        ]).filter(([id]) => Number.isFinite(id)));
        applyIndexHeader();
        renderDetail();
        await ensureDataset("events", { token, force, progressBase: 0.25, progressSpan: 0.75 });
        if (token !== state.loadToken) return null;
        const requestedKind = requestedSelectionKind();
        if (requestedKind === "media") {
          state.mode = "media";
          syncModeButtons();
          renderLoadingList();
          await ensureDataset("media", { token, force, progressBase: 0.25, progressSpan: 0.75 });
          if (token !== state.loadToken) return null;
        }
        buildFilterChips();
        applyFilters({ resetScroll: true });
        applyRequestedSelection();
        window.WebUI?.updateLoader?.("audio", 1, t("loadingEvents"));
        return state.index;
      } catch (error) {
        if (token !== state.loadToken || error?.name === "AbortError") return null;
        renderLoadError(error, { index: true });
        throw error;
      } finally {
        if (token === state.loadToken) {
          state.indexPromise = null;
          state.indexController = null;
          window.WebUI?.setViewBusy?.("audio", false);
          window.WebUI?.hideLoader?.("audio");
        }
      }
    })();
    state.indexPromise = promise;
    return promise;
  }

  async function switchMode(kind) {
    if (!["events", "media"].includes(kind) || state.mode === kind) return;
    state.mode = kind;
    state.selected = null;
    resetFilters({ render: false });
    syncModeButtons();
    renderLoadingList();
    renderDetail();
    clearSelectionFromUrl();
    if (state.datasets[kind]) {
      buildFilterChips();
      applyFilters({ resetScroll: true });
      return;
    }
    window.WebUI?.setViewBusy?.("audio", true);
    window.WebUI?.showLoader?.("audio", t(kind === "events" ? "loadingEvents" : "loadingMedia"));
    try {
      const records = await ensureDataset(kind, { token: state.loadToken });
      if (state.mode !== kind || !records) return;
      buildFilterChips();
      applyFilters({ resetScroll: true });
    } catch (error) {
      if (error?.name !== "AbortError") renderLoadError(error, { index: false });
    } finally {
      window.WebUI?.setViewBusy?.("audio", false);
      window.WebUI?.hideLoader?.("audio");
    }
  }

  function renderShell() {
    if (!state.container) return;
    state.container.innerHTML = `
      <div class="audio-page-shell">
        <div id="audio-construction-banner" class="construction-banner" role="note"></div>
        <div class="audio-shell">
        <aside id="audio-left">
          <header>
            <h1 id="audio-title"></h1>
            <div id="audio-stats"><span id="audio-count">?</span> <span id="audio-count-label"></span></div>
            <div class="sidebar-header-actions">
              <button id="audio-filter-toggle" class="panel-toggle" type="button" aria-controls="audio-filter-panel" aria-expanded="true"></button>
              <button id="audio-reset" type="button"></button>
            </div>
          </header>
          <div class="audio-mode-switch" role="group" aria-label="Audio dataset">
            <button id="audio-events-mode" class="audio-mode-button is-active" type="button" data-audio-mode="events" aria-pressed="true"></button>
            <button id="audio-media-mode" class="audio-mode-button" type="button" data-audio-mode="media" aria-pressed="false"></button>
          </div>
          <div id="audio-filter-panel" class="filters">
            <section class="filter-section filter-section-basic" data-filter-section="audio-basic" data-fixed-open="1">
              <div class="filter-section-title"><span id="audio-basic-filter-label"></span></div>
              <div class="filter-section-body filter-section-body-stack">
                <input id="audio-q" type="search" autocomplete="off">
                <div id="audio-sort-row" class="filter-control-row" hidden>
                  <label id="audio-sort-label" for="audio-sort"></label>
                  <select id="audio-sort" aria-labelledby="audio-sort-label">
                    <option id="audio-sort-purpose-priority" value="purpose-priority"></option>
                    <option id="audio-sort-title" value="title"></option>
                    <option id="audio-sort-duration-desc" value="duration-desc"></option>
                    <option id="audio-sort-duration-asc" value="duration-asc"></option>
                  </select>
                </div>
              </div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-category" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-category-filter-body"><span id="audio-category-label"></span></button>
              <div id="audio-category-filter-body" class="filter-section-body" hidden><div id="audio-category-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-context" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-context-filter-body"><span id="audio-context-label"></span></button>
              <div id="audio-context-filter-body" class="filter-section-body" hidden><div id="audio-context-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-relation" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-relation-filter-body"><span id="audio-relation-label"></span></button>
              <div id="audio-relation-filter-body" class="filter-section-body" hidden><div id="audio-relation-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-recovery" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-recovery-filter-body"><span id="audio-recovery-label"></span></button>
              <div id="audio-recovery-filter-body" class="filter-section-body" hidden><div id="audio-recovery-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-scope" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-scope-filter-body"><span id="audio-scope-label"></span></button>
              <div id="audio-scope-filter-body" class="filter-section-body" hidden><div id="audio-scope-filter" class="chips" data-multi="1"></div></div>
            </section>
            <section class="filter-section is-collapsed" data-filter-section="audio-source" data-default-collapsed="1">
              <button class="filter-section-toggle" type="button" aria-expanded="false" aria-controls="audio-source-filter-body"><span id="audio-source-label"></span></button>
              <div id="audio-source-filter-body" class="filter-section-body" hidden><div id="audio-source-filter" class="chips" data-multi="1"></div></div>
            </section>
          </div>
          <div id="audio-filter-splitter" class="filter-splitter" role="separator" aria-label="Resize audio filters" aria-orientation="horizontal" tabindex="0"></div>
          <div id="audio-list-meta"><span id="audio-shown">0</span> / <span id="audio-total">0</span> <span id="audio-shown-label"></span></div>
          <div id="audio-list-wrap"><div id="audio-list-spacer"></div><div id="audio-list"></div></div>
        </aside>
        <div id="audio-splitter" class="pane-splitter" role="separator" aria-label="Resize audio sidebar" aria-orientation="vertical" tabindex="0"></div>
        <main id="audio-right">
          <header class="audio-detail-header">
            <div id="audio-detail-eyebrow" class="audio-detail-eyebrow"></div>
            <h1 id="audio-detail-title"></h1>
            <div id="audio-detail-subtitle"></div>
          </header>
          <div id="audio-detail-body"></div>
        </main>
        </div>
      </div>`;
    bindShellEvents();
    bindFilterSections();
    setupFilterPanel();
    setupSplitters();
    applyUiText();
    syncModeButtons();
  }

  function bindShellEvents() {
    $("#audio-q", state.container)?.addEventListener("input", (event) => {
      state.query = event.target.value;
      applyFilters({ resetScroll: true });
    });
    $("#audio-sort", state.container)?.addEventListener("change", (event) => {
      state.sort = event.target.value;
      applyFilters({ resetScroll: true });
    });
    $("#audio-reset", state.container)?.addEventListener("click", () => resetFilters());
    state.container.querySelectorAll("[data-audio-mode]").forEach((button) => {
      button.addEventListener("click", () => switchMode(button.dataset.audioMode));
    });
    $("#audio-list-wrap", state.container)?.addEventListener("scroll", scheduleListRender, { passive: true });
    $("#audio-list", state.container)?.addEventListener("click", (event) => {
      const row = event.target.closest(".audio-row[data-index]");
      if (!row) return;
      selectRecord(state.filtered[Number(row.dataset.index)]);
    });
    $("#audio-list", state.container)?.addEventListener("keydown", (event) => {
      if (!["Enter", " "].includes(event.key)) return;
      const row = event.target.closest(".audio-row[data-index]");
      if (!row) return;
      event.preventDefault();
      selectRecord(state.filtered[Number(row.dataset.index)]);
    });
  }

  function bindFilterSections() {
    state.container.querySelectorAll(".filter-section-toggle").forEach((button) => {
      button.addEventListener("click", () => {
        const section = button.closest(".filter-section");
        const body = section?.querySelector(".filter-section-body");
        if (!section || !body) return;
        const collapsed = !section.classList.contains("is-collapsed");
        section.classList.toggle("is-collapsed", collapsed);
        body.hidden = collapsed;
        button.setAttribute("aria-expanded", String(!collapsed));
        window.dispatchEvent(new Event("resize"));
      });
    });
  }

  function setupFilterPanel() {
    state.filterPanel = window.WebUI?.filters?.createPanelToggle?.({
      panel: "#audio-filter-panel",
      toggle: "#audio-filter-toggle",
      left: "#audio-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => t(collapsed ? "showFilters" : "hideFilters"),
      onChange: () => window.dispatchEvent(new Event("resize")),
    }) || null;
  }

  function setupSplitters() {
    const setup = window.WebUI?.setupSplitter;
    const utils = window.WebUI?.splitterUtils;
    const shell = $(".audio-shell", state.container);
    const sidebar = $("#audio-left", state.container);
    const pane = $("#audio-splitter", state.container);
    const panel = $("#audio-filter-panel", state.container);
    const filter = $("#audio-filter-splitter", state.container);
    const list = $("#audio-list-wrap", state.container);
    if (!setup || !utils || !shell || !sidebar || !pane || !panel || !filter || !list) return;

    let paneWasMobile = isMobileLayout();
    setup({
      handle: pane,
      storageKey: PANE_STORAGE_KEY,
      bodyDragClass: "is-resizing-pane",
      client: (event) => event.clientX,
      keys: { decrease: ["ArrowLeft"], increase: ["ArrowRight"] },
      enabled: () => !isMobileLayout(),
      bounds: () => {
        const min = parsePixels(getComputedStyle(sidebar).minWidth, 300);
        return { min, max: Math.max(min, shell.getBoundingClientRect().width - pane.getBoundingClientRect().width - 320) };
      },
      read: () => parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width),
      write: (width) => { sidebar.style.width = `${Math.round(width)}px`; },
      clear: () => { sidebar.style.removeProperty("width"); },
      sync: (controller) => {
        if (isMobileLayout()) {
          paneWasMobile = true;
          controller.clear({ commit: false });
          return;
        }
        if (shell.getBoundingClientRect().width < 48) return;
        let width = parsePixels(sidebar.style.width, sidebar.getBoundingClientRect().width);
        if (paneWasMobile || !sidebar.style.width) width = utils.readStoredNumber(PANE_STORAGE_KEY) ?? width;
        paneWasMobile = false;
        controller.set(width, { persist: false, commit: false });
      },
    });

    const minPanelHeight = 56;
    const minListHeight = 160;
    let filterWasMobile = isMobileLayout();
    const naturalHeight = () => {
      const previous = panel.style.height;
      const resized = panel.classList.contains("is-filter-resized");
      panel.style.removeProperty("height");
      panel.classList.remove("is-filter-resized");
      const height = Math.ceil(panel.getBoundingClientRect().height);
      if (previous) panel.style.height = previous;
      panel.classList.toggle("is-filter-resized", resized);
      return Math.max(minPanelHeight, height);
    };
    const controller = setup({
      handle: filter,
      storageKey: FILTER_HEIGHT_STORAGE_KEY,
      bodyDragClass: "is-resizing-filter",
      client: (event) => event.clientY,
      keys: { decrease: ["ArrowUp"], increase: ["ArrowDown"] },
      enabled: () => !isMobileLayout() && !panel.hidden,
      bounds: () => {
        let fixed = 0;
        for (const child of sidebar.children) if (child !== panel && child !== list) fixed += child.getBoundingClientRect().height;
        const available = Math.max(minPanelHeight, sidebar.getBoundingClientRect().height - fixed - minListHeight);
        return { min: minPanelHeight, max: Math.max(minPanelHeight, Math.min(available, naturalHeight())) };
      },
      read: () => panel.getBoundingClientRect().height,
      write: (height) => {
        panel.style.height = `${Math.round(height)}px`;
        panel.classList.add("is-filter-resized");
      },
      clear: () => {
        panel.style.removeProperty("height");
        panel.classList.remove("is-filter-resized");
      },
      sync: (ctrl) => {
        if (isMobileLayout() || panel.hidden) {
          filterWasMobile = isMobileLayout();
          ctrl.clear({ commit: false });
          return;
        }
        if (sidebar.getBoundingClientRect().height < 48) return;
        const stored = utils.readStoredNumber(FILTER_HEIGHT_STORAGE_KEY);
        if (stored !== null) {
          filterWasMobile = false;
          ctrl.set(stored, { persist: false, commit: false });
        } else {
          if (filterWasMobile) ctrl.clear({ commit: false });
          filterWasMobile = false;
          ctrl.syncAria();
        }
      },
    });
    if (window.MutationObserver && controller) {
      const observer = new MutationObserver(controller.requestSync);
      observer.observe(panel, { attributes: true, attributeFilter: ["hidden"] });
      observer.observe(panel, { childList: true, subtree: true });
    }
  }

  function applyUiText() {
    const pairs = {
      "audio-construction-banner": "underConstruction", "audio-title": "title", "audio-count-label": "countLabel", "audio-filter-toggle": state.filterPanel?.collapsed ? "showFilters" : "hideFilters",
      "audio-reset": "reset", "audio-events-mode": "events", "audio-media-mode": "media", "audio-basic-filter-label": "basicFilters",
      "audio-sort-label": "sort", "audio-sort-purpose-priority": "sortPurposePriority", "audio-sort-title": "sortTitle", "audio-sort-duration-desc": "sortDurationDesc", "audio-sort-duration-asc": "sortDurationAsc",
      "audio-context-label": "context", "audio-relation-label": "relation", "audio-recovery-label": "recovery",
      "audio-scope-label": "scope", "audio-source-label": "source", "audio-shown-label": "shown",
    };
    for (const [id, key] of Object.entries(pairs)) {
      const node = $(`#${id}`, state.container);
      if (node) node.textContent = t(key);
    }
    const categoryLabelNode = $("#audio-category-label", state.container);
    if (categoryLabelNode) categoryLabelNode.textContent = t(state.mode === "events" ? "eventType" : "mediaPurpose");
    const search = $("#audio-q", state.container);
    if (search) search.placeholder = t("search");
    syncSortControl();
    for (const records of Object.values(state.datasets)) {
      for (const record of records || []) {
        record.meta = recordMeta(record.raw, record.kind, record);
        record.listMeta = recordMeta(record.raw, record.kind, record, { includeFileStats: false });
        record.fileStats = recordFileStats(record.raw, record.kind);
        record.search = searchText(record.raw, record.kind, record);
      }
    }
    applyIndexHeader();
    buildFilterChips();
    renderList();
    renderDetail();
  }

  function applyIndexHeader() {
    const records = state.datasets[state.mode];
    const count = records ? records.length : indexCount(state.mode);
    const node = $("#audio-count", state.container);
    if (node) node.textContent = count === null ? "?" : formatNumber(count);
  }

  function indexCount(kind) {
    const counts = state.index?.counts || state.index?.summary?.counts || {};
    const keys = kind === "events"
      ? ["events", "eventCount", "namedEvents", "audioEvents"]
      : ["media", "mediaCount", "decodedMedia", "files", "audioFiles"];
    for (const key of keys) {
      const value = counts[key] ?? state.index?.shards?.[kind]?.count;
      if (Number.isFinite(Number(value))) return Number(value);
    }
    return null;
  }

  function syncModeButtons() {
    state.container?.querySelectorAll("[data-audio-mode]").forEach((button) => {
      const active = button.dataset.audioMode === state.mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    const categoryLabelNode = $("#audio-category-label", state.container);
    if (categoryLabelNode) categoryLabelNode.textContent = t(state.mode === "events" ? "eventType" : "mediaPurpose");
    syncSortControl();
    applyIndexHeader();
  }

  function syncSortControl() {
    const row = $("#audio-sort-row", state.container);
    const select = $("#audio-sort", state.container);
    if (row) row.hidden = state.mode !== "media";
    if (select) select.value = state.sort;
  }

  function resetFilters({ render = true } = {}) {
    state.query = "";
    state.sort = "purpose-priority";
    state.filters.categories.clear();
    state.filters.contexts.clear();
    state.filters.relations.clear();
    state.filters.recovery.clear();
    state.filters.scopes.clear();
    state.filters.sources.clear();
    const search = $("#audio-q", state.container);
    if (search) search.value = "";
    syncSortControl();
    if (render) {
      buildFilterChips();
      applyFilters({ resetScroll: true });
    }
  }

  function countValues(records, field) {
    const counts = new Map();
    for (const record of records || []) {
      for (const value of new Set(asArray(record[field]).filter(Boolean))) counts.set(value, (counts.get(value) || 0) + 1);
    }
    return counts;
  }

  function buildFilterChips() {
    const records = state.datasets[state.mode] || [];
    const build = window.WebUI?.filters?.buildChips;
    if (!build) return;
    const groups = [
      ["#audio-category-filter", "category", state.filters.categories, categoryLabel],
      ["#audio-context-filter", "contextTags", state.filters.contexts, taxonomyLabel],
      ["#audio-relation-filter", "relationTags", state.filters.relations, taxonomyLabel],
      ["#audio-recovery-filter", "recoveryTags", state.filters.recovery, recoveryLabel],
      ["#audio-scope-filter", "scope", state.filters.scopes, null],
      ["#audio-source-filter", "source", state.filters.sources, null],
    ];
    for (const [selector, field, active, label] of groups) {
      const counts = countValues(records, field);
      const values = [...counts.keys()].filter(Boolean).sort((a, b) => (label ? label(a) : a).localeCompare(label ? label(b) : b, undefined, { numeric: true }));
      build(selector, values, {
        active,
        count: counts,
        className: "audio-filter-chip",
        label: label || undefined,
        onToggle: () => applyFilters({ resetScroll: true }),
      });
    }
  }

  function syncFilterCounts() {
    window.WebUI?.setFilterSectionActiveCounts?.({
      "audio-basic": state.query.trim() ? 1 : 0,
      "audio-category": state.filters.categories.size,
      "audio-context": state.filters.contexts.size,
      "audio-relation": state.filters.relations.size,
      "audio-recovery": state.filters.recovery.size,
      "audio-scope": state.filters.scopes.size,
      "audio-source": state.filters.sources.size,
    });
  }

  function applyFilters({ resetScroll = false } = {}) {
    const records = state.datasets[state.mode] || [];
    const tokens = normalizeLower(state.query).split(/\s+/).filter(Boolean);
    state.filtered = records.filter((record) => {
      const searchable = `${record.search}\n${normalizeLower(recordNote(record))}`;
      if (tokens.length && !tokens.every((token) => searchable.includes(token))) return false;
      if (state.filters.categories.size && !state.filters.categories.has(record.category)) return false;
      if (state.filters.contexts.size && !record.contextTags.some((value) => state.filters.contexts.has(value))) return false;
      if (state.filters.relations.size && !record.relationTags.some((value) => state.filters.relations.has(value))) return false;
      if (state.filters.recovery.size && !record.recoveryTags.some((value) => state.filters.recovery.has(value))) return false;
      if (state.filters.scopes.size && !state.filters.scopes.has(record.scope)) return false;
      if (state.filters.sources.size && !state.filters.sources.has(record.source)) return false;
      return true;
    }).sort((a, b) => {
      if (state.mode === "events" || state.sort === "purpose-priority") {
        const priority = { highest: 0, secondary: 1, resolved: 2, resolvedTerminal: 3 };
        const left = priority[a.raw?.purposeInvestigationPriority] ?? 2;
        const right = priority[b.raw?.purposeInvestigationPriority] ?? 2;
        if (left !== right) return left - right;
      }
      if (state.mode === "media" && state.sort.startsWith("duration-")) {
        const left = recordDuration(a.raw);
        const right = recordDuration(b.raw);
        if (left !== null || right !== null) {
          if (left === null) return 1;
          if (right === null) return -1;
          if (left !== right) return state.sort === "duration-desc" ? right - left : left - right;
        }
      }
      return a.title.localeCompare(b.title, undefined, { numeric: true }) || a.key.localeCompare(b.key, undefined, { numeric: true });
    });
    state.rows = state.filtered.map((record, index) => ({ record, index, top: index * ROW_HEIGHT }));
    const spacer = $("#audio-list-spacer", state.container);
    if (spacer) spacer.style.height = `${state.rows.length * ROW_HEIGHT}px`;
    const wrap = $("#audio-list-wrap", state.container);
    if (resetScroll && wrap) wrap.scrollTop = 0;
    $("#audio-shown", state.container).textContent = formatNumber(state.filtered.length);
    $("#audio-total", state.container).textContent = formatNumber(records.length);
    applyIndexHeader();
    syncFilterCounts();
    renderList();
  }

  function scheduleListRender() {
    if (state.renderFrame) return;
    state.renderFrame = requestAnimationFrame(() => {
      state.renderFrame = 0;
      renderList();
    });
  }

  function firstVisibleRow(top) {
    return Math.max(0, Math.min(state.rows.length, Math.floor(top / ROW_HEIGHT)));
  }

  function renderList() {
    const wrap = $("#audio-list-wrap", state.container);
    const list = $("#audio-list", state.container);
    if (!wrap || !list) return;
    if (!state.datasets[state.mode]) return;
    if (!state.rows.length) {
      list.innerHTML = `<div class="audio-empty-list">${esc((state.datasets[state.mode] || []).length ? t("noMatches") : t("noData"))}</div>`;
      return;
    }
    const startTop = Math.max(0, wrap.scrollTop - OVERSCAN_PX);
    const endTop = wrap.scrollTop + wrap.clientHeight + OVERSCAN_PX;
    const fragment = document.createDocumentFragment();
    let index = firstVisibleRow(startTop);
    while (index < state.rows.length && state.rows[index].top < endTop) {
      const row = state.rows[index];
      const button = document.createElement("button");
      button.type = "button";
      button.className = `audio-row${state.selected?.kind === state.mode && state.selected?.key === row.record.key ? " is-selected" : ""}`;
      button.dataset.index = String(row.index);
      button.style.top = `${row.top}px`;
      button.style.height = `${ROW_HEIGHT}px`;
      const fileStats = row.record.fileStats ? `<span class="audio-row-file-stats">${esc(row.record.fileStats)}</span>` : "";
      const noteLine = firstNoteLine(row.record);
      const noteMarker = noteLine ? `<span class="audio-row-note-marker" title="${esc(t("hasManualNote"))}" aria-label="${esc(t("hasManualNote"))}">\u270e</span>` : "";
      const noteTitle = noteLine ? `<span class="audio-row-note-title">\u2014 ${esc(noteLine)}</span>` : "";
      button.innerHTML = `<span class="audio-row-title-line"><span class="audio-row-kind">${esc(state.mode === "events" ? t("event") : t("mediaItem"))}</span><span class="audio-row-title">${esc(row.record.title)}</span>${noteTitle}${noteMarker}${fileStats}</span><span class="audio-row-meta">${esc(row.record.listMeta)}</span>`;
      fragment.appendChild(button);
      index += 1;
    }
    list.replaceChildren(fragment);
  }

  function renderLoadingList() {
    const list = $("#audio-list", state.container);
    const spacer = $("#audio-list-spacer", state.container);
    if (spacer) spacer.style.height = "0px";
    if (list) list.innerHTML = `<div class="audio-empty-list">${esc(t(state.mode === "events" ? "loadingEvents" : "loadingMedia"))}</div>`;
    const shown = $("#audio-shown", state.container);
    const total = $("#audio-total", state.container);
    if (shown) shown.textContent = "0";
    if (total) total.textContent = "?";
  }

  function selectRecord(record, { updateUrl = true } = {}) {
    if (!record) return;
    state.selected = record;
    if (updateUrl) updateSelectionUrl(record);
    const detail = $("#audio-right", state.container);
    if (detail) detail.scrollTop = 0;
    renderList();
    renderDetail();
    if (record.kind === "events") ensureEventDetail(record).catch((error) => {
      if (state.selected === record) window.WebUI?.showShellStatus?.("audio", `${t("shardError")} ${error.message || error}`, "error");
    });
  }

  function requestedSelection() {
    const params = new URLSearchParams(window.location.search || "");
    return normalize(params.get("audio"));
  }

  function requestedSelectionKind() {
    const params = new URLSearchParams(window.location.search || "");
    return params.get("audioKind") === "media" ? "media" : "events";
  }

  function applyRequestedSelection() {
    const requested = requestedSelection();
    const kind = requestedSelectionKind();
    if (!requested || state.mode !== kind) return;
    const record = (state.datasets[kind] || []).find((candidate) => candidate.key === requested || recordId(candidate.raw, kind) === requested);
    if (record) selectRecord(record, { updateUrl: false });
  }

  function updateSelectionUrl(record) {
    const url = new URL(window.location.href);
    url.searchParams.set("audio", record.key);
    url.searchParams.set("audioKind", record.kind);
    url.hash = "#audio";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function clearSelectionFromUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete("audio");
    url.searchParams.delete("audioKind");
    if (document.body.dataset.activeView === "audio") url.hash = "#audio";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function renderDetail() {
    const eyebrow = $("#audio-detail-eyebrow", state.container);
    const title = $("#audio-detail-title", state.container);
    const subtitle = $("#audio-detail-subtitle", state.container);
    const body = $("#audio-detail-body", state.container);
    if (!eyebrow || !title || !subtitle || !body) return;
    const selected = state.selected;
    eyebrow.textContent = selected ? (selected.kind === "events" ? t("event") : t("mediaItem")) : t("overview");
    title.textContent = selected ? selected.title : t("runtimeSystem");
    subtitle.textContent = selected ? selected.meta : indexSubtitle();
    body.replaceChildren();
    if (selected) {
      body.appendChild(recordPanel(selected));
    } else {
      body.appendChild(runtimePanel());
      const empty = document.createElement("p");
      empty.className = "audio-detail-note";
      empty.textContent = t("selectRecord");
      body.appendChild(empty);
    }
  }

  function indexSubtitle() {
    const parts = [state.index?.language || state.language, state.index?.generated].filter(Boolean);
    return parts.join(" · ");
  }

  function runtimePanel() {
    const runtimeCandidate = state.index?.runtimeSystem || state.index?.runtimeModel;
    const runtime = runtimeCandidate && typeof runtimeCandidate === "object" ? runtimeCandidate : {};
    const panel = document.createElement("section");
    panel.className = "audio-panel audio-boundary";
    const heading = document.createElement("h2");
    heading.textContent = t("runtimeSystem");
    panel.appendChild(heading);
    const descriptionCandidate = runtime.overview ?? runtime.description ?? runtime.summary ?? runtime.evidenceBoundary;
    const description = ["string", "number", "boolean"].includes(typeof descriptionCandidate) ? normalize(descriptionCandidate) : "";
    if (description) {
      const note = document.createElement("p");
      note.className = "audio-runtime-note";
      note.textContent = description;
      panel.appendChild(note);
    }

    const stats = runtime.counts && typeof runtime.counts === "object"
      ? runtime.counts
      : (runtime.stats && typeof runtime.stats === "object" ? runtime.stats : (state.index?.counts || {}));
    const statEntries = Object.entries(stats).filter(([, value]) => ["string", "number", "boolean"].includes(typeof value)).slice(0, 18);
    if (statEntries.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      if (description) grid.style.marginTop = "12px";
      for (const [label, value] of statEntries) grid.appendChild(statNode(humanize(label), typeof value === "number" ? formatNumber(value) : value));
      panel.appendChild(grid);
    }
    const recoveryCounts = state.index?.counts || {};
    const recoveryStats = [
      [`${t("purposeUnknown")} / ${t("event")}`, recoveryCounts.purposeUnknownEvents],
      [`${t("purposeUnknown")} / ${t("mediaItem")}`, recoveryCounts.purposeUnknownMedia],
      [`${t("purposePartial")} / ${t("event")}`, recoveryCounts.purposePartialEvents],
      [`${t("purposePartial")} / ${t("mediaItem")}`, recoveryCounts.purposePartialMedia],
      [`${t("purposeKnown")} / ${t("event")}`, recoveryCounts.purposeKnownEvents],
      [`${t("purposeKnown")} / ${t("mediaItem")}`, recoveryCounts.purposeKnownMedia],
      [t("purposeStoryTerminal"), recoveryCounts.purposeStoryTerminalMedia],
      [t("recoveryLibraryUnresolved"), recoveryCounts.authoredEventsUnresolvedToWwise],
      [t("recoveryTriggerNameUnknown"), recoveryCounts.wwiseEventObjectsWithoutRecoveredAuthoredTrigger],
      [t("locationUnknown"), recoveryCounts.mediaPlaybackLocationUnknown],
      [t("locationEventRelationOnly"), recoveryCounts.mediaWithEventRelationOnly],
      [t("locationAuthoredEventContext"), recoveryCounts.mediaWithAuthoredEventContext],
      [t("locationDirectDialogMedia"), recoveryCounts.directDialogMedia],
    ].filter(([, value]) => Number.isFinite(Number(value)));
    if (recoveryStats.length) {
      const heading = document.createElement("h3");
      heading.textContent = t("recoveryBoundary");
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of recoveryStats) grid.appendChild(statNode(label, formatNumber(value)));
      panel.append(heading, grid);
    }

    const components = asArray(runtime.components ?? runtime.layers).map((value) => typeof value === "object" ? (value.name ?? value.id ?? value.type) : value).filter(Boolean);
    if (components.length) panel.appendChild(chipSection(t("runtimeComponents"), components));
    const hirc = state.index?.hircSummary;
    if (hirc && typeof hirc === "object" && Object.keys(hirc).length) panel.appendChild(hircInventorySection(hirc));
    const metadataEventSymbols = state.index?.metadataEventSymbolAliases;
    if (metadataEventSymbols && typeof metadataEventSymbols === "object") {
      const entries = asArray(metadataEventSymbols.entries).map((row) => [
        row.eventHashHex || "?",
        row.name || row.metadataField || "Event",
        row.metadataDeclaringType || "",
      ].filter(Boolean).join(" / "));
      if (entries.length) {
        panel.appendChild(chipSection("Named Event symbols (IL2CPP field evidence)", entries));
        if (metadataEventSymbols.evidenceBoundary) {
          panel.appendChild(noteSection("Event symbol evidence boundary", metadataEventSymbols.evidenceBoundary));
        }
      }
    }
    const controlCatalog = state.index?.controlCatalog;
    if (controlCatalog && typeof controlCatalog === "object") panel.appendChild(controlCatalogSection(controlCatalog));
    const physicsAudioCatalog = state.index?.triggerCatalog?.physicsAudio;
    if (physicsAudioCatalog && typeof physicsAudioCatalog === "object") panel.appendChild(physicsAudioCatalogSection(physicsAudioCatalog));
    const modelViewStateCatalog = state.index?.triggerCatalog?.modelViewStateAudio;
    if (modelViewStateCatalog && typeof modelViewStateCatalog === "object") panel.appendChild(modelViewStateAudioCatalogSection(modelViewStateCatalog));
    const levelScriptRadioCatalog = state.index?.triggerCatalog?.levelScriptRadio;
    if (levelScriptRadioCatalog && typeof levelScriptRadioCatalog === "object") panel.appendChild(levelScriptRadioCatalogSection(levelScriptRadioCatalog));
    const levelSequenceAudioCatalog = state.index?.triggerCatalog?.levelSequenceAudio;
    if (levelSequenceAudioCatalog && typeof levelSequenceAudioCatalog === "object") panel.appendChild(levelSequenceAudioCatalogSection(levelSequenceAudioCatalog));
    const dialogLifecycleCoverage = state.index?.triggerContexts?.coverage?.dialogLifecycle;
    if (dialogLifecycleCoverage && typeof dialogLifecycleCoverage === "object") panel.appendChild(dialogLifecycleCatalogSection(dialogLifecycleCoverage));
    const triggerContextCatalog = state.index?.triggerContexts;
    if (triggerContextCatalog && typeof triggerContextCatalog === "object") panel.appendChild(triggerContextCatalogSection(triggerContextCatalog));
    const enemyTriggerVoiceActionCatalog = state.index?.triggerCatalog?.enemyTriggerVoiceAction;
    if (enemyTriggerVoiceActionCatalog && typeof enemyTriggerVoiceActionCatalog === "object") {
      panel.appendChild(enemyTriggerVoiceActionCatalogSection(enemyTriggerVoiceActionCatalog));
    }
    const systems = asArray(runtime.systems).filter((value) => value && typeof value === "object");
    if (systems.length) panel.appendChild(runtimeSystemsSection(systems));
    const boundaryCandidate = runtime.boundary ?? state.index?.evidenceBoundary;
    const boundary = ["string", "number", "boolean"].includes(typeof boundaryCandidate) ? normalize(boundaryCandidate) : "";
    if (boundary && boundary !== description) panel.appendChild(noteSection(t("runtimeBoundary"), boundary));
    if (boundaryCandidate && typeof boundaryCandidate === "object" && !Array.isArray(boundaryCandidate)) {
      const boundaryEntries = Object.entries(boundaryCandidate).filter(([, value]) => ["string", "number", "boolean"].includes(typeof value));
      if (boundaryEntries.length) panel.appendChild(boundaryGrid(boundaryEntries));
    }
    if (!description && !statEntries.length && !components.length && !boundary) {
      const note = document.createElement("p");
      note.className = "audio-runtime-note";
      note.textContent = t("noData");
      panel.appendChild(note);
    }
    return panel;
  }

  function hircInventorySection(hirc) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("hircInventory");
    const grid = document.createElement("div");
    grid.className = "audio-stat-grid";
    const versions = Object.entries(hirc.bankVersions || {}).map(([version, count]) => `${version}: ${formatNumber(count)}`).join(", ");
    const facts = [
      ["PCK packages", hirc.packageCount],
      ["Embedded banks", hirc.embeddedBankCount],
      ["HIRC objects", hirc.hircObjectCount],
      ["Bank versions", versions],
      [t("scannedBankSet"), hirc.packageFingerprint ? `${hirc.packageCount || 0} PCK / ${String(hirc.packageFingerprint).slice(0, 16)}…` : ""],
    ];
    for (const [label, value] of facts) if (value !== undefined && value !== null && value !== "") grid.appendChild(statNode(label, typeof value === "number" ? formatNumber(value) : value));
    section.append(heading, grid);
    const labels = hirc.objectTypeLabels || {};
    const typeCounts = Object.entries(hirc.objectTypeCounts || {}).map(([type, count]) => `${labels[type] || `type${type}`} (${type}): ${formatNumber(count)}`);
    if (typeCounts.length) section.appendChild(chipSection("Object families", typeCounts));
    const processing = hirc.postProcessSummary && typeof hirc.postProcessSummary === "object" ? hirc.postProcessSummary : {};
    if (processing.parserStatus) {
      const processingFacts = [
        ["Direct-processing nodes", processing.parsedNodeCount],
        ["Nodes with effects", processing.effectNodeCount],
        ["Effect slots", processing.effectSlotCount],
        ["Plug-in references", processing.effectReferenceCount],
        ["Authored effect bypass bits", processing.effectBypassSlotCount],
        ["Authored effect ShareSet bits", processing.effectShareSetSlotCount],
        ["Authored effect rendered bits", processing.effectRenderedSlotCount],
        ["Effect slots with unknown flag bits", processing.effectUnknownFlagBitsCount],
        ["Decoded effect parameters", processing.decodedEffectParameterDefinitionCount],
        ["Exact authored semantics", processing.exactEffectParameterDefinitionCount],
        ["Partial authored semantics", processing.partialEffectParameterDefinitionCount],
        ["Opaque effect parameters", processing.opaqueEffectParameterDefinitionCount],
        ["Effect definitions with plug-in media", processing.pluginMediaDependencyDefinitionCount],
        ["Plug-in media definition occurrences", processing.pluginMediaDependencyDefinitionOccurrenceCount],
        ["Plug-in media dependency occurrences", processing.pluginMediaDependencyReferenceOccurrenceCount],
        ["Unique plug-in media IDs", processing.uniquePluginMediaIdCount],
        ["Decoded parameter references", processing.decodedEffectParameterReferenceCount],
        ["Exact semantic references", processing.exactEffectParameterReferenceCount],
        ["Partial semantic references", processing.partialEffectParameterReferenceCount],
        ["Empty effect slots", processing.emptyEffectSlotCount],
        ["Explicit output-bus routes", processing.outputBusNodeCount],
        ["Unique output buses", processing.uniqueOutputBusIds],
        ["Typed Aux Send nodes", processing.auxSendParserStatusCounts?.typedExactV150NodeAuxParams],
        ["Game-Defined send use bits", processing.gameDefinedAuxSendUseBitNodeCount],
        ["Game-Defined send override bits", processing.gameDefinedAuxSendOverrideBitNodeCount],
        ["User-Defined Aux slot nodes", processing.userDefinedAuxSlotNodeCount],
        ["User-Defined Aux Bus references", processing.userDefinedAuxBusReferenceCount],
        ["Unique User-Defined Aux Buses", processing.uniqueUserDefinedAuxBusIds],
        ["Early Reflections Aux Bus references", processing.reflectionsAuxBusReferenceCount],
        ["Authored base property values", processing.authoredPropertyValueCount],
        ["Authored base property ranges", processing.authoredRangedPropertyValueCount],
        ["Nodes with authored base properties", processing.authoredPropertyNodeCount],
        ["Typed State/RTPC nodes", processing.stateRtpcParserStatusCounts?.typedExactV150NodeStateAndRtpc],
        ["State Group references", processing.stateGroupReferenceCount],
        ["Unique State Group IDs", processing.uniqueStateGroupIds],
        ["Authored State values", processing.stateValueCount],
        ["Initial RTPC curves", processing.rtpcCurveCount],
        ["Initial RTPC curve points", processing.rtpcPointCount],
        ["Unique RTPC IDs", processing.uniqueRtpcIds],
        ["Audio/Aux Bus definitions", processing.busDefinitionCount],
        ["Recovered bus effect slots", processing.busEffectSlotCount],
        ["Bus effect bypass bits", processing.busEffectBypassSlotCount],
        ["Bus effect ShareSet bits", processing.busEffectShareSetSlotCount],
        ["Bus effect rendered bits", processing.busEffectRenderedSlotCount],
        ["Bus effect slots with unknown flag bits", processing.busEffectUnknownFlagBitsCount],
        ["Decoded bus effect settings", processing.decodedBusEffectParameterCount],
        ["Typed Bus State/RTPC definitions", processing.busStateRtpcParserStatusCounts?.typedExactV150BusInitialRtpcAndState],
        ["Bus Initial RTPC curves", processing.busRtpcCurveCount],
        ["Bus Initial RTPC curve points", processing.busRtpcPointCount],
        ["Bus State groups", processing.busStateGroupCount],
        ["Bus authored State values", processing.busStateValueCount],
      ];
      for (const [label, value] of processingFacts) if (value !== undefined && value !== null) grid.appendChild(statNode(label, formatNumber(value)));
      const plugins = Object.entries(processing.effectPluginReferenceCounts || {}).map(([name, count]) => `${name}: ${formatNumber(count)}`);
      if (plugins.length) section.appendChild(chipSection("Recovered DSP plug-ins", plugins));
      const parameterSchemas = Object.entries(processing.effectParameterSchemaCounts || {}).map(([name, count]) => `${humanize(name)}: ${formatNumber(count)}`);
      if (parameterSchemas.length) section.appendChild(chipSection("Decoded authored DSP settings", parameterSchemas));
      const pluginMedia = asArray(processing.pluginMediaDependencies).map((row) => [
        row.pluginName || row.pluginClassIdHex || "plug-in",
        `data ${row.pluginDataIndex ?? "?"}`,
        row.mediaIdHex || row.mediaId,
        humanize(row.semanticRole || "plugin media"),
      ].filter((value) => value !== undefined && value !== null && value !== "").join(" / "));
      if (pluginMedia.length) section.appendChild(chipSection("Plug-in media dependencies (not playable WEM)", pluginMedia));
      const resolutions = Object.entries(processing.effectResolutionCounts || {}).map(([status, count]) => `${humanize(status)}: ${formatNumber(count)}`);
      if (resolutions.length) section.appendChild(chipSection("Effect definition resolution", resolutions));
      const busParents = Object.entries(processing.busParentResolutionCounts || {}).map(([status, count]) => `${humanize(status)}: ${formatNumber(count)}`);
      if (busParents.length) section.appendChild(chipSection("Bus hierarchy resolution", busParents));
      const auxResolutions = Object.entries(processing.auxiliaryBusResolutionCounts || {}).map(([status, count]) => `${humanize(status)}: ${formatNumber(count)}`);
      if (auxResolutions.length) section.appendChild(chipSection("Auxiliary Send bus resolution", auxResolutions));
      const stateParameters = Object.entries(processing.stateParameterCounts || {}).map(([name, count]) => `${parameterLabelText(name)}: ${formatNumber(count)}`);
      if (stateParameters.length) section.appendChild(chipSection("Authored State-controlled properties", stateParameters));
      const rtpcTypes = Object.entries(processing.rtpcTypeCounts || {}).map(([name, count]) => `${humanize(name)}: ${formatNumber(count)}`);
      if (rtpcTypes.length) section.appendChild(chipSection("Initial RTPC control types", rtpcTypes));
      const rtpcParameters = Object.entries(processing.rtpcParameterCounts || {}).map(([name, count]) => `${parameterLabelText(name)}: ${formatNumber(count)}`);
      if (rtpcParameters.length) section.appendChild(chipSection("RTPC-controlled properties", rtpcParameters));
      const namedGameParameters = asArray(processing.gameParameterNameEvidence?.entries).map((row) => {
        const field = String(row.metadataField || "").split(".").pop() || "GameParameter";
        const nodeCurves = formatNumber(row.nodeRtpcCurveCount || 0);
        const busCurves = formatNumber(row.busRtpcCurveCount || 0);
        return `${row.parameterIdHex || "?"} / ${field} / node curves ${nodeCurves} / bus curves ${busCurves}`;
      });
      if (namedGameParameters.length) {
        section.appendChild(chipSection("Named GameParameter IDs (IL2CPP field evidence)", namedGameParameters));
        if (processing.gameParameterNameEvidence?.evidenceBoundary) {
          section.appendChild(noteSection("GameParameter evidence boundary", processing.gameParameterNameEvidence.evidenceBoundary));
        }
      }
      const authoredProperties = Object.entries(processing.authoredPropertyCounts || {}).map(([name, count]) => `${humanize(name)}: ${formatNumber(count)}`);
      if (authoredProperties.length) section.appendChild(chipSection("Authored base properties", authoredProperties));
      const authoredPropertyRanges = Object.entries(processing.authoredRangedPropertyCounts || {}).map(([name, count]) => `${humanize(name)}: ${formatNumber(count)}`);
      if (authoredPropertyRanges.length) section.appendChild(chipSection("Authored base property ranges", authoredPropertyRanges));
      const busEffectParsers = Object.entries(processing.busEffectParserCounts || {}).map(([status, count]) => `${humanize(status)}: ${formatNumber(count)}`);
      if (busEffectParsers.length) section.appendChild(chipSection("Bus effect recovery", busEffectParsers));
      const busStateRtpcParsers = Object.entries(processing.busStateRtpcParserStatusCounts || {}).map(([status, count]) => `${humanize(status)}: ${formatNumber(count)}`);
      if (busStateRtpcParsers.length) section.appendChild(chipSection("Bus State/RTPC recovery", busStateRtpcParsers));
      const busStateParameters = Object.entries(processing.busStateParameterCounts || {}).map(([name, count]) => `${parameterLabelText(name)}: ${formatNumber(count)}`);
      if (busStateParameters.length) section.appendChild(chipSection("Bus State-controlled properties", busStateParameters));
      const busRtpcParameters = Object.entries(processing.busRtpcParameterCounts || {}).map(([name, count]) => `${parameterLabelText(name)}: ${formatNumber(count)}`);
      if (busRtpcParameters.length) section.appendChild(chipSection("Bus RTPC-controlled properties", busRtpcParameters));
      const busPlugins = Object.entries(processing.busEffectPluginCounts || {}).map(([name, count]) => `${name}: ${formatNumber(count)}`);
      if (busPlugins.length) section.appendChild(chipSection("Recovered bus DSP plug-ins", busPlugins));
      if (processing.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), processing.evidenceBoundary));
    }
    const packages = asArray(hirc.packageInventory).map((row) => [
      row.blockType || row.vfsSource || "export",
      row.fileName || row.source,
      `${formatNumber(row.embeddedBankCount || 0)} banks`,
      `${formatNumber(row.eventObjectCount || 0)} Events`,
      row.sha256 ? String(row.sha256).slice(0, 16) : "",
    ].filter(Boolean).join(" / "));
    if (packages.length) section.appendChild(chipSection(t("scannedBankSet"), packages));
    if (hirc.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), hirc.evidenceBoundary));
    return section;
  }

  function controlCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("controlCatalog");
    section.appendChild(heading);
    const counts = catalog.counts && typeof catalog.counts === "object" ? catalog.counts : {};
    if (Object.keys(counts).length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [key, value] of Object.entries(counts)) grid.appendChild(statNode(humanize(key), typeof value === "number" ? formatNumber(value) : value));
      section.appendChild(grid);
    }
    const formatControlFields = (row) => Object.entries(row.fields || {}).map(([name, field]) => {
      let value = field?.value;
      if (field?.bindingKind === "dynamic" || field?.bindingKind === "output") {
        value = field.path || `${humanize(field.bindingKind)} source ${field.paramSource ?? "?"}`;
      } else if (field?.present === false) {
        value = "null";
      } else if (value && typeof value === "object") {
        value = JSON.stringify(value);
      }
      return `${name}=${value ?? "?"}`;
    }).join(", ");
    const groups = [
      ["rtpcParameters", asArray(catalog.rtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${row.field || humanize(row.evidence || "")}`],
      ["physicsAudioRtpcParameters", asArray(catalog.physicsAudioRtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${humanize(row.controlRole || "")} / ${row.definitionOwnerId || row.ownerId || "?"} / ${row.authoredProperty || "?"} -> ${row.runtimeField || "?"}`],
      ["modelViewStateRtpcParameters", asArray(catalog.modelViewStateRtpcParameters), (row) => `${row.parameterName || t("unknown")} / ${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / mode ${row.rtpcBehaviourType ?? "?"} / ${row.dependFloatKey || "no blackboard key"}`],
      ["modelViewStateSpatialControls", asArray(catalog.modelViewStateSpatialControls), (row) => `${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / direct ${String(Boolean(row.directSet))} / target ${row.targetClosePercentage ?? "?"} / ${row.dependFloatKey || "no blackboard key"}`],
      ["modelViewStateCustomAudioControls", asArray(catalog.modelViewStateCustomAudioControls), (row) => `${row.controlValue || '""'} / ${row.behaviorTagHex || "tag ?"} / ${row.controllerId || "?"} / ${row.modelAnimatorName || "?"} / ${row.layerName || "?"} / ${row.stateName || "?"} / ${humanize(row.wwiseEventStatus || "unresolved")}`],
      ["globalMusicCues", asArray(catalog.audioGlobalMusicCueRefs), (row) => `${row.field || t("unknown")} / ${row.cueHex || row.cueId || "?"} / ${humanize(row.definitionStatus || "unknown")}`],
      ["cueOperands", asArray(catalog.audioCueExpressionOperands), (row) => `${row.stringValue || t("unknown")} / ${row.cueHex || "?"} / ${humanize(row.expressionSide || "")} / ${row.expressionPath || ""}`],
      ["levelScriptCueInvocations", asArray(catalog.levelScriptAudioCueInvocations), (row) => `${row.cueName || t("unknown")} / ${row.cueHex || "?"} / ${humanize(row.definitionStatus || "unknown")} / ${row.levelScriptId || "?"} / ${humanize(row.action || "")}`],
      ["levelScriptDynamicBindings", asArray(catalog.levelScriptDynamicAudioBindings), (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
      ["levelScriptControls", asArray(catalog.levelScriptAudioControls), (row) => `${humanize(row.action || "")} / ${humanize(row.controlRole || "")} / ${row.levelScriptId || "?"} / ${formatControlFields(row)}`],
      ["levelScriptDynamicControls", asArray(catalog.levelScriptDynamicControlBindings), (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
      ["levelEventConditions", asArray(catalog.levelEventAudioConditions), (row) => `${row.type || row.id || t("unknown")} / union ${row.unionTagHex || "?"} / event key ${row.eventKey ?? "?"} / ${humanize(row.relationType || "")} / ${row.predicate || "?"} / authored occurrences ${formatNumber(row.authoredOccurrenceCount || 0)} / ${humanize(row.playbackRequestStatus || "")}`],
      ["wwiseSelectorGroups", asArray(catalog.wwiseSelectorGroups), (row) => {
        const values = asArray(row.values).map((value) => {
          const input = `${value.valueIdHex || value.valueId || "?"}=${value.semanticName || humanize(value.semanticNameStatus || "unresolved")}`;
          const resolved = value.resolvedValueIdHex
            ? ` -> ${value.resolvedValueIdHex}${value.resolvedValueName ? `=${value.resolvedValueName}` : ""}`
            : "";
          return `${input}${resolved}`;
        });
        return `${row.groupIdHex || "?"} / ${row.semanticLabel || humanize(row.semanticRole || "unknown")} / ${humanize(row.semanticEvidence || "unknown")} / ${humanize(row.groupType || "unknown")} / ${humanize(row.runtimeScope || "scope unresolved")}${values.length ? ` / values ${values.join(", ")}` : ""} / ${humanize(row.runtimeObservationStatus || "")}`;
      }],
      ["wwiseInitialRtpcParameters", asArray(catalog.wwiseInitialRtpcParameters), (row) => [
        row.rtpcIdHex || "?",
        row.parameterName || humanize(row.semanticNameStatus || "unresolved"),
        `${formatNumber(row.curveCount || 0)} curves / ${formatNumber(row.pointCount || 0)} points`,
        asArray(row.eventIds).slice(0, 4).join(", "),
        Object.entries(row.controlledProperties || {}).map(([key, value]) => `${key} ${formatNumber(value)}`).join(" / "),
        asArray(row.triggerRoles).join(" / "),
      ].filter(Boolean).join(" / ")],
      ["wwiseActionControls", asArray(catalog.wwiseActionControls?.referencedGroups), (row) => `${row.groupIdHex || "?"} / ${row.semanticLabel || humanize(row.semanticRole || "unknown")} / ${humanize(row.groupType || "unknown")} / ${humanize(row.runtimeObservationStatus || "")}`],
    ];
    for (const [labelKey, rows, formatRow] of groups) {
      if (!rows.length) continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      summary.textContent = `${t(labelKey)} (${formatNumber(rows.length)})`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const row of rows) {
        const chip = document.createElement("span");
        chip.textContent = formatRow(row);
        values.appendChild(chip);
      }
      details.append(summary, values);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function physicsAudioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("physicsAudioCatalog");
    section.appendChild(heading);
    const facts = [
      ["Definitions", catalog.physicsAudioDefinitions],
      ["Event requests", catalog.physicsAudioEventContexts],
      ["RTPC controls", catalog.physicsAudioRtpcControls],
      ["Configured consumers", catalog.physicsAudioConsumerIdentities],
      ["Aliases", catalog.physicsAudioAliasIdentities],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, formatNumber(value)));
      section.appendChild(grid);
    }
    for (const definition of asArray(catalog.definitions)) {
      if (!definition || typeof definition !== "object") continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      const consumers = asArray(definition.consumerIds).filter(Boolean);
      summary.textContent = `${definition.definitionOwnerId || t("unknown")} / ${definition.componentTagHex || definition.componentTag || "?"} / ${formatNumber(definition.propertyCount || 0)} properties / ${formatNumber(consumers.length)} consumers`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const property of asArray(definition.properties)) {
        if (!property || typeof property !== "object") continue;
        const chip = document.createElement("span");
        const rawValue = property.value === "" ? '""' : property.value;
        chip.textContent = `${property.authoredKey || "?"} -> ${property.runtimeField || "?"} = ${rawValue ?? "null"}`;
        values.appendChild(chip);
      }
      const evidence = document.createElement("p");
      evidence.className = "audio-detail-note";
      evidence.textContent = [
        consumers.length ? `consumers ${consumers.join(", ")}` : "",
        definition.sourceSha256 ? `SHA-256 ${definition.sourceSha256}` : "",
        definition.sourceOffset !== undefined ? `component 0x${Number(definition.sourceOffset).toString(16)}-0x${Number(definition.endOffset).toString(16)}` : "",
        ...asArray(definition.sourcePaths),
      ].filter(Boolean).join(" / ");
      details.append(summary, values, evidence);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function modelViewStateAudioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("modelViewStateAudioCatalog");
    section.appendChild(heading);
    const facts = [
      ["Controllers decoded", catalog.controllersDecoded],
      ["Controllers with audio", catalog.controllersWithAudio],
      ["Event behaviors (tag 0x0001)", catalog.eventBehaviorCount],
      ["Position Event behaviors (tag 0x0002)", catalog.positionEventBehaviorCount],
      ["RTPC behaviors (tag 0x0003)", catalog.rtpcBehaviorCount],
      ["Spatial behaviors (tag 0x0004)", catalog.spatialBehaviorCount],
      ["Custom-audio controls", catalog.customAudioControlCount],
      ["Exact InteractiveData associations", catalog.controllersWithTemplateAssociations],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, typeof value === "number" ? formatNumber(value) : value));
      section.appendChild(grid);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function levelSequenceAudioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("levelSequenceAudioCatalog");
    section.appendChild(heading);
    const facts = [
      [t("levelSequenceTimelineContexts"), catalog.timelineContexts],
      [t("levelSequenceExactContexts"), catalog.eventsWithExactLevelSequenceAction],
      [t("levelSequenceInferredContexts"), catalog.eventsWithInferredTimelineTrigger],
      [t("levelSequenceGapContexts"), catalog.eventsWithoutTimelineCarrier],
      ["Timeline parents", catalog.timelineParents],
      ["PlayableDirector links", catalog.exactPlayableDirectorLinks],
      ["LevelScript ids", catalog.uniquePlayLevelSequenceIds],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, formatNumber(value)));
      section.appendChild(grid);
    }
    const boundary = [
      catalog.evidenceBoundary,
      catalog.playActionEvidenceBoundary,
      catalog.timelineOwnershipEvidenceBoundary,
    ].filter(Boolean).join(" ");
    if (boundary) section.appendChild(noteSection(t("levelSequenceRuntimeBoundary"), boundary));
    return section;
  }

  function dialogLifecycleCatalogSection(coverage) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("dialogLifecycleAudioCatalog");
    section.appendChild(heading);
    const facts = [
      ["Stored hooks", coverage.storedTriggerContextRows],
      ["Current Wwise events", coverage.rowsWithCurrentWwiseEvent],
      ["No decoded media leaf", coverage.rowsWithNoDecodedMediaLeaf],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, formatNumber(value)));
      section.appendChild(grid);
    }
    const phaseCounts = coverage.phaseCounts && typeof coverage.phaseCounts === "object"
      ? Object.entries(coverage.phaseCounts).map(([phase, count]) => `${phase}: ${formatNumber(count)}`)
      : [];
    if (phaseCounts.length) section.appendChild(chipSection("Lifecycle phases", phaseCounts));
    const consumer = coverage.runtimeConsumer && typeof coverage.runtimeConsumer === "object" ? coverage.runtimeConsumer : {};
    const methods = consumer.methods && typeof consumer.methods === "object"
      ? Object.values(consumer.methods).map((method) => {
        if (!method || typeof method !== "object") return "";
        return [method.name, method.token].filter(Boolean).join(" ");
      }).filter(Boolean)
      : [];
    if (consumer.type || methods.length) {
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      summary.textContent = consumer.type || "AudioGameplayStatusSystem";
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const method of methods) {
        const chip = document.createElement("span");
        chip.textContent = method;
        values.appendChild(chip);
      }
      details.append(summary, values);
      section.appendChild(details);
    }
    section.appendChild(noteSection(t("runtimeBoundary"), "Dialog lifecycle dispatch and Wwise PostEvent execution were not observed; these rows are authored hooks only."));
    return section;
  }

  function triggerContextCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("audioTriggerContextCatalog");
    section.appendChild(heading);
    const counts = catalog.counts && typeof catalog.counts === "object" ? catalog.counts : {};
    const facts = [
      ["Total contexts", counts.total],
      ["Playable media", counts.withPlayableMedia],
      ["Runtime observed", counts.runtimeExecutionObserved],
      ["Runtime unobserved", counts.runtimeExecutionUnobserved],
    ].filter(([, value]) => value !== undefined && value !== null);
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, formatNumber(value)));
      section.appendChild(grid);
    }
    const coverage = catalog.coverage && typeof catalog.coverage === "object" ? catalog.coverage : {};
    for (const [kind, row] of Object.entries(coverage)) {
      if (!row || typeof row !== "object") continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      const stored = row.storedTriggerContextRows;
      summary.textContent = `${humanize(kind)}${stored !== undefined ? ` (${formatNumber(stored)})` : ""}`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const [key, value] of Object.entries(row)) {
        if (key === "source" || value === null || value === undefined) continue;
        if (value && typeof value === "object" && !Array.isArray(value)) {
          const scalarEntries = Object.entries(value).filter(([, nested]) => (
            nested !== null
            && nested !== undefined
            && ["string", "number", "boolean"].includes(typeof nested)
          ));
          for (const [nestedKey, nestedValue] of scalarEntries) {
            const chip = document.createElement("span");
            chip.textContent = `${humanize(key)} / ${humanize(nestedKey)}: ${typeof nestedValue === "number" ? formatNumber(nestedValue) : String(nestedValue)}`;
            values.appendChild(chip);
          }
          continue;
        }
        if (typeof value === "object") continue;
        const chip = document.createElement("span");
        chip.textContent = `${humanize(key)}: ${typeof value === "number" ? formatNumber(value) : String(value)}`;
        values.appendChild(chip);
      }
      if (row.source) {
        const source = document.createElement("p");
        source.className = "audio-detail-note";
        source.textContent = String(row.source);
        details.append(summary, values, source);
      } else {
        details.append(summary, values);
      }
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function enemyTriggerVoiceActionCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("enemyTriggerVoiceActionCatalog");
    section.appendChild(heading);
    const facts = [
      ["Consumer", [catalog.consumerType, catalog.consumerMethod].filter(Boolean).join(".")],
      ["Method", [catalog.methodVa, catalog.methodIndex !== undefined ? `index ${catalog.methodIndex}` : ""].filter(Boolean).join(" / ")],
      ["Playback", [catalog.playbackCall, catalog.playbackInvocationVa].filter(Boolean).join(" / ")],
      ["Mappings", asArray(catalog.voiceTypes).length],
    ].filter(([, value]) => value !== undefined && value !== null && value !== "");
    if (facts.length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [label, value] of facts) grid.appendChild(statNode(label, typeof value === "number" ? formatNumber(value) : value));
      section.appendChild(grid);
    }
    const mappings = asArray(catalog.voiceTypes).filter((row) => row && typeof row === "object");
    if (mappings.length) {
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const row of mappings) {
        const chip = document.createElement("span");
        chip.textContent = [
          `voiceType ${row.voiceType ?? "?"} -> ${row.triggerKey || "?"}`,
          row.literalLoadVa ? `literal ${row.literalLoadVa}` : "",
          row.mappingAddInvocationVa ? `dictionary add ${row.mappingAddInvocationVa}` : "",
        ].filter(Boolean).join(" / ");
        values.appendChild(chip);
      }
      section.appendChild(values);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function levelScriptRadioCatalogSection(catalog) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("levelScriptRadioCatalog");
    section.appendChild(heading);
    const counts = catalog.counts && typeof catalog.counts === "object" ? catalog.counts : {};
    if (Object.keys(counts).length) {
      const grid = document.createElement("div");
      grid.className = "audio-stat-grid";
      for (const [key, value] of Object.entries(counts)) {
        grid.appendChild(statNode(humanize(key), typeof value === "number" ? formatNumber(value) : value));
      }
      section.appendChild(grid);
    }
    const boundedGroups = [
      ["unresolvedRadioIds", catalog.unresolvedRadioIds, (row) => `${row.radioId || t("unknown")} / ${formatNumber(row.invocationCount || 0)} invocations / ${asArray(row.triggerRoles).map(humanize).join(", ") || "role unknown"}`],
      ["unresolvedRadioLines", catalog.unresolvedRadioLines, (row) => `${row.radioId || t("unknown")} / line ${Number(row.lineOrdinal ?? 0) + 1} / ${row.audioOverride || "audioOverride missing"} / ${humanize(row.resolutionStatus || "")}`],
      ["dynamicRadioBindings", catalog.dynamicRadioBindings, (row) => `${row.levelScriptId || "?"} / ${humanize(row.action || "")} / ${humanize(row.triggerRole || "")} / ${row.sourceField || "?"} / ${row.binding?.path || humanize(row.resolutionStatus || "")}`],
    ];
    for (const [labelKey, bounded, formatRow] of boundedGroups) {
      if (!bounded || typeof bounded !== "object") continue;
      const rows = asArray(bounded.items).filter((row) => row && typeof row === "object");
      const total = Number(bounded.totalCount || 0);
      if (!rows.length && !total) continue;
      const details = document.createElement("details");
      details.className = "audio-runtime-system";
      const summary = document.createElement("summary");
      summary.textContent = `${t(labelKey)} (${formatNumber(rows.length)} / ${formatNumber(total)}${bounded.truncated ? ", truncated" : ""})`;
      const values = document.createElement("div");
      values.className = "audio-chip-list";
      for (const row of rows) {
        const chip = document.createElement("span");
        chip.textContent = formatRow(row);
        values.appendChild(chip);
      }
      details.append(summary, values);
      section.appendChild(details);
    }
    if (catalog.evidenceBoundary) section.appendChild(noteSection(t("runtimeBoundary"), catalog.evidenceBoundary));
    return section;
  }

  function boundaryGrid(entries) {
    const section = document.createElement("div");
    section.style.marginTop = "12px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("runtimeBoundary");
    const grid = document.createElement("div");
    grid.className = "audio-runtime-boundaries";
    for (const [key, value] of entries.slice(0, 12)) {
      const item = document.createElement("div");
      item.className = "audio-runtime-boundary";
      item.innerHTML = `<strong>${esc(humanize(key))}</strong><span>${esc(value)}</span>`;
      grid.appendChild(item);
    }
    section.append(heading, grid);
    return section;
  }

  function runtimeSystemsSection(systems) {
    const section = document.createElement("div");
    section.style.marginTop = "14px";
    const heading = document.createElement("div");
    heading.className = "audio-fact-label";
    heading.textContent = t("runtimeComponents");
    const list = document.createElement("div");
    list.className = "audio-runtime-systems";
    for (const system of systems) {
      const card = document.createElement("article");
      card.className = "audio-runtime-system";
      const type = normalize(system.type ?? system.name ?? system.id) || t("unknown");
      const layer = normalize(system.layer);
      const meaning = normalize(system.meaning ?? system.description);
      const counts = [];
      if (asArray(system.fields).length) counts.push(`${asArray(system.fields).length} fields`);
      if (asArray(system.methods).length) counts.push(`${asArray(system.methods).length} methods`);
      if (system.enumValues && typeof system.enumValues === "object") counts.push(`${Object.keys(system.enumValues).length} enum values`);
      if (asArray(system.nativeAnchors).length) counts.push(`${asArray(system.nativeAnchors).length} native anchors`);
      if (asArray(system.nativeCallChains).length) counts.push(`${asArray(system.nativeCallChains).length} native call chains`);
      if (asArray(system.nativeStateGroups).length) counts.push(`${asArray(system.nativeStateGroups).length} Wwise state groups`);
      if (asArray(system.nativeStateTransitions).length) counts.push(`${asArray(system.nativeStateTransitions).length} audio-state masks`);
      card.innerHTML = `<div class="audio-runtime-system-head"><code>${esc(type)}</code>${layer ? `<span>${esc(layer)}</span>` : ""}</div>${meaning ? `<p>${esc(meaning)}</p>` : ""}${counts.length ? `<small>${esc(counts.join(" · "))}</small>` : ""}`;
      const layout = system.serializedLayout && typeof system.serializedLayout === "object" ? system.serializedLayout : null;
      const anchors = asArray(system.nativeAnchors).filter((row) => row && typeof row === "object");
      const callChains = asArray(system.nativeCallChains).filter((row) => row && typeof row === "object");
      const stateGroups = asArray(system.nativeStateGroups).filter((row) => row && typeof row === "object");
      const stateTransitions = asArray(system.nativeStateTransitions).filter((row) => row && typeof row === "object");
      const enumEntries = system.enumValues && typeof system.enumValues === "object"
        ? Object.entries(system.enumValues)
        : [];
      if (layout || anchors.length || callChains.length || stateGroups.length || stateTransitions.length || enumEntries.length) {
        const values = document.createElement("div");
        values.className = "audio-chip-list";
        if (layout) {
          const chip = document.createElement("span");
          chip.textContent = `${layout.unionTagHex || `tag ${layout.unionTag ?? "?"}`} / mc${layout.memberCount ?? "?"} / behavior type ${layout.behaviorType ?? "?"} / ${layout.dataType || "serialized data"}`;
          values.appendChild(chip);
        }
        for (const [name, value] of enumEntries) {
          const chip = document.createElement("span");
          const numeric = Number(value);
          const hex = Number.isFinite(numeric) ? ` / 0x${(numeric >>> 0).toString(16).padStart(8, "0")}` : "";
          chip.textContent = `${name} = ${value}${hex}`;
          values.appendChild(chip);
        }
        for (const anchor of anchors) {
          const chip = document.createElement("span");
          chip.textContent = `${anchor.role || "native"} / method ${anchor.methodIndex ?? "?"} / ${anchor.token || "token ?"} / VA ${anchor.virtualAddress || "?"}${anchor.type ? ` / ${anchor.type}` : ""}`;
          values.appendChild(chip);
        }
        if (system.runtimeExecutionStatus) {
          const chip = document.createElement("span");
          chip.textContent = `runtime execution ${humanize(system.runtimeExecutionStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeAnchorStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native anchors ${humanize(system.nativeAnchorStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeCallChainStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native call chains ${humanize(system.nativeCallChainStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeStateGroupStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native state groups ${humanize(system.nativeStateGroupStatus)}`;
          values.appendChild(chip);
        }
        if (system.nativeStateTransitionStatus) {
          const chip = document.createElement("span");
          chip.textContent = `native state transitions ${humanize(system.nativeStateTransitionStatus)}`;
          values.appendChild(chip);
        }
        card.appendChild(values);
        for (const group of stateGroups) {
          const groupCard = document.createElement("div");
          groupCard.className = "audio-runtime-state-group";
          const recoveredName = normalize(group.recoveredName);
          const identity = recoveredName || normalize(group.field) || humanize(group.role || "state group");
          const title = document.createElement("strong");
          title.textContent = `${humanize(group.role || "state group")} · ${identity} · ${group.groupIdHex || group.groupId || "unknown id"}`;
          const detail = document.createElement("small");
          detail.textContent = [
            normalize(group.enumType),
            normalize(group.setterMethod),
            group.methodIndex !== undefined ? `method ${group.methodIndex}` : "",
            normalize(group.virtualAddress) ? `VA ${group.virtualAddress}` : "",
            humanize(group.nameEvidence || ""),
          ].filter(Boolean).join(" · ");
          groupCard.append(title, detail);
          card.appendChild(groupCard);
        }
        for (const transition of stateTransitions) {
          const transitionCard = document.createElement("div");
          transitionCard.className = "audio-runtime-state-group";
          const names = asArray(transition.stateNames).map(normalize).filter(Boolean);
          const title = document.createElement("strong");
          title.textContent = `${names.length ? names.join(" + ") : "audio state mask"} / ${transition.stateMaskHex || transition.stateMask || "unknown mask"}`;
          const detail = document.createElement("small");
          detail.textContent = [
            `${transition.registrationCount || 0} registrations`,
            asArray(transition.actionOrders).length ? `orders ${asArray(transition.actionOrders).join(" / ")}` : "",
            transition.isOneShot === false ? "persistent" : "",
            asArray(transition.registrationCallOffsets).length ? `call offsets ${asArray(transition.registrationCallOffsets).join(" / ")}` : "",
            humanize(transition.callbackTargetStatus || ""),
            humanize(transition.conditionInterpretationStatus || ""),
          ].filter(Boolean).join(" / ");
          transitionCard.append(title, detail);
          const registrations = asArray(transition.registrations).filter((row) => row && typeof row === "object");
          if (registrations.length) {
            const callbackList = document.createElement("div");
            callbackList.className = "audio-chip-list";
            for (const registration of registrations) {
              const chip = document.createElement("span");
              chip.textContent = [
                humanize(registration.conditionType || `condition ${registration.conditionTypeRaw ?? "?"}`),
                `order ${registration.actionOrder ?? "?"}`,
                normalize(registration.callbackMethod),
                registration.callbackMethodIndex !== undefined ? `method ${registration.callbackMethodIndex}` : "",
                normalize(registration.callbackVirtualAddress) ? `VA ${registration.callbackVirtualAddress}` : "",
                asArray(registration.directStateSetters).length
                  ? `direct setters ${asArray(registration.directStateSetters).join(" / ")}`
                  : "",
              ].filter(Boolean).join(" / ");
              callbackList.appendChild(chip);
            }
            transitionCard.appendChild(callbackList);
          }
          card.appendChild(transitionCard);
        }
        for (const chain of callChains) {
          const chainCard = document.createElement("div");
          chainCard.className = "audio-runtime-call-chain";
          const label = normalize(chain.label ?? chain.id) || "Native call chain";
          const stages = asArray(chain.stages).filter((row) => row && typeof row === "object");
          const alternateEntryPoints = asArray(chain.alternateEntryPoints)
            .filter((row) => row && typeof row === "object");
          const branches = asArray(chain.branches).filter((row) => row && typeof row === "object");
          const title = document.createElement("strong");
          title.textContent = `${label}${stages.length ? ` · ${stages.length} stages` : ""}`;
          chainCard.appendChild(title);
          const stageList = document.createElement("div");
          stageList.className = "audio-chip-list";
          for (const stage of stages) {
            const chip = document.createElement("span");
            const identity = [normalize(stage.type), normalize(stage.method)].filter(Boolean).join(".");
            const anchor = [
              stage.methodIndex !== undefined ? `method ${stage.methodIndex}` : "",
              normalize(stage.virtualAddress) ? `VA ${stage.virtualAddress}` : "",
            ].filter(Boolean).join(" / ");
            chip.textContent = [
              humanize(stage.role || "stage"), identity, anchor, normalize(stage.relation),
            ].filter(Boolean).join(" · ");
            stageList.appendChild(chip);
          }
          for (const entry of alternateEntryPoints) {
            const chip = document.createElement("span");
            chip.textContent = [
              `alternate ${humanize(entry.role || "entry point")}`,
              [normalize(entry.type), normalize(entry.method)].filter(Boolean).join("."),
              normalize(entry.virtualAddress) ? `VA ${entry.virtualAddress}` : "",
              normalize(entry.relation),
            ].filter(Boolean).join(" 路 ");
            stageList.appendChild(chip);
          }
          for (const branch of branches) {
            const chip = document.createElement("span");
            chip.textContent = [
              `branch ${normalize(branch.label ?? branch.id) || "unknown"}`,
              normalize(branch.relation),
            ].filter(Boolean).join(" / ");
            stageList.appendChild(chip);
          }
          chainCard.appendChild(stageList);
          if (chain.boundary) {
            const boundary = document.createElement("small");
            boundary.textContent = normalize(chain.boundary);
            chainCard.appendChild(boundary);
          }
          card.appendChild(chainCard);
        }
      }
      list.appendChild(card);
    }
    section.append(heading, list);
    return section;
  }

  function contextEvidenceLabel(context) {
    const kind = normalize(context?.kind);
    const group = contextGroup(kind);
    const parts = [group ? taxonomyLabel(group) : humanize(kind), humanize(kind)];
    if (context?.ownerId) parts.push(context.ownerId);
    if (context?.groupId) parts.push(context.groupId);
    if (context?.storyKey) parts.push(context.storyKey);
    if (context?.table) parts.push(context.table);
    if (context?.path) parts.push(context.path);
    if (kind === "luaPostEvent") {
      if (context?.source) parts.push(context.source);
      if (context?.line !== undefined) parts.push(`line ${context.line}`);
      if (context?.expression) parts.push(context.expression);
      parts.push("runtime branch execution unobserved");
    }
    if (kind === "monoBehaviourAudioIdField") {
      if (context?.authoredFieldRole) parts.push(`AudioId role ${humanize(context.authoredFieldRole)}`);
      if (context?.serializedFieldPath) parts.push(context.serializedFieldPath);
      if (context?.componentName) parts.push(`component ${context.componentName}`);
      if (context?.gameObjectName) parts.push(`GameObject ${context.gameObjectName}`);
      const hierarchy = asArray(context?.hierarchyPath).filter(Boolean);
      if (hierarchy.length) parts.push(`hierarchy ${hierarchy.join(" / ")}`);
      if (context?.worldPosition && typeof context.worldPosition === "object") {
        const { x, y, z } = context.worldPosition;
        parts.push(`world position ${x ?? "?"}, ${y ?? "?"}, ${z ?? "?"} / ${humanize(context.worldPositionStatus || "status unknown")}`);
      }
      if (context?.serializedFile || context?.pathId !== undefined) parts.push(`object ${context.serializedFile || "?"} / PathID ${context.pathId ?? "?"}`);
      if (context?.managedReferenceClass) parts.push(`managed ${context.managedReferenceNamespace ? `${context.managedReferenceNamespace}.` : ""}${context.managedReferenceClass}`);
      if (context?.managedReferenceLayout) parts.push(`managed layout ${context.managedReferenceLayout}`);
      if (context?.managedReferencePayloadLength !== undefined) parts.push(`managed payload ${context.managedReferencePayloadLength} bytes`);
      if (context?.managedReferenceDecodeStatus) parts.push(humanize(context.managedReferenceDecodeStatus));
      const controls = context?.serializedPlaybackControls && typeof context.serializedPlaybackControls === "object"
        ? context.serializedPlaybackControls
        : {};
      const controlSummary = Object.entries(controls).map(([key, value]) => `${humanize(key)} ${String(value)}`);
      if (controlSummary.length) parts.push(`serialized controls ${controlSummary.join(" / ")}`);
      if (context?.objectIndexSource) parts.push(context.objectIndexSource);
      if (context?.rawJsonSource) parts.push(context.rawJsonSource);
      parts.push("component/state execution unobserved");
    }
    if (["audioDialogVoiceDefinition", "responsiveDialogVoice", "voiceToneVariant"].includes(kind)) {
      if (context?.audioDialogPath) parts.push(`AudioDialog ${context.audioDialogPath}`);
      if (context?.voiceId !== undefined) parts.push(`voice id ${context.voiceId}`);
      if (context?.speakerId || context?.speakerChannel) parts.push(`speaker ${context.speakerId || context.speakerChannel}`);
      if (context?.triggerKey) parts.push(`trigger ${context.triggerKey}`);
      if (context?.sentenceType) parts.push(`sentence type ${context.sentenceType}`);
      if (context?.triggerTypeId !== undefined) parts.push(`trigger type ${context.triggerTypeId}`);
      if (context?.responseIndex !== undefined) parts.push(`response ${context.responseIndex}`);
      if (context?.baseVoiceId !== undefined) parts.push(`base voice ${context.baseVoiceId}`);
      if (context?.variantIndex !== undefined) parts.push(`tone variant ${context.variantIndex}`);
      if (context?.runtimeRoute) parts.push(context.runtimeRoute);
      if (context?.runtimeSelectionStatus) parts.push(humanize(context.runtimeSelectionStatus));
      if (context?.playbackPlacementStatus) parts.push(humanize(context.playbackPlacementStatus));
      const enemyAction = context?.enemyTriggerVoiceAction;
      if (enemyAction && typeof enemyAction === "object") {
        parts.push(`EnemyTriggerVoiceAction voice type ${enemyAction.voiceType ?? "?"} -> ${enemyAction.triggerKey || context.triggerKey || "?"}`);
        if (enemyAction.literalLoadVa || enemyAction.mappingAddInvocationVa) {
          parts.push(`native dictionary load ${enemyAction.literalLoadVa || "?"} / add ${enemyAction.mappingAddInvocationVa || "?"}`);
        }
      }
      if (context?.enemyTriggerVoiceActionStatus) parts.push(humanize(context.enemyTriggerVoiceActionStatus));
    }
    if (kind === "abilityVoiceTriggerAction") {
      if (context?.configId) parts.push(`SkillData ${context.configId}`);
      if (context?.triggerKey) parts.push(`trigger ${context.triggerKey}`);
      if (context?.speakerType !== undefined) parts.push(`speaker type ${context.speakerType}`);
      if (context?.canInterruptTimeMs !== undefined) parts.push(`interrupt ${context.canInterruptTimeMs} ms`);
      if (context?.actionUnionTag) parts.push(`union ${context.actionUnionTag} / ${context.serializedMemberCount ?? "?"} members`);
      if (context?.runtimeRoute) parts.push(context.runtimeRoute);
      if (context?.runtimeActivationStatus) parts.push(humanize(context.runtimeActivationStatus));
      if (context?.playbackPlacementStatus) parts.push(humanize(context.playbackPlacementStatus));
    }
    if (["voiceDefaultWwiseEvent", "voiceNarratingChannelEvent", "voiceRadioChannelEvent", "audioDialogOverrideWwiseEvent", "responsiveVoiceEventTemplate", "voiceTableWwiseEvent"].includes(kind)) {
      if (context?.field) parts.push(`field ${context.field}`);
      if (context?.routeKind) parts.push(humanize(context.routeKind));
      if (context?.occurrenceCount !== undefined) parts.push(`${formatNumber(context.occurrenceCount)} authored row${Number(context.occurrenceCount) === 1 ? "" : "s"}`);
      const rowPaths = asArray(context?.rowPathSamples).filter(Boolean);
      if (rowPaths.length) parts.push(`rows ${rowPaths.join(" / ")}${context?.rowPathsTruncated ? " / ..." : ""}`);
      if (context?.runtimeRoute) parts.push(context.runtimeRoute);
      if (context?.runtimeSelectionStatus) parts.push(humanize(context.runtimeSelectionStatus));
      if (context?.playbackPlacementStatus) parts.push(humanize(context.playbackPlacementStatus));
    }
    if (["uiAnimationOpenEvent", "activityPushPopupBgmEvent", "activityCenterBgmEvent", "uiVideoAudioEvent", "domainRegionSwitchEvent", "domainUpgradeAnimationEvent", "typedUiTableWwiseEvent"].includes(kind)) {
      if (context?.field) parts.push(`field ${context.field}`);
      if (context?.routeKind) parts.push(humanize(context.routeKind));
      if (context?.occurrenceCount !== undefined) parts.push(`${formatNumber(context.occurrenceCount)} authored row${Number(context.occurrenceCount) === 1 ? "" : "s"}`);
      const rowPaths = asArray(context?.rowPathSamples).filter(Boolean);
      if (rowPaths.length) parts.push(`rows ${rowPaths.join(" / ")}${context?.rowPathsTruncated ? " / ..." : ""}`);
      if (context?.runtimeRoute) parts.push(context.runtimeRoute);
      const consumers = asArray(context?.consumerEvidence).filter(Boolean);
      if (consumers.length) parts.push(`consumers ${consumers.join(" / ")}`);
      if (context?.runtimeExecutionStatus) parts.push(humanize(context.runtimeExecutionStatus));
      if (context?.playbackPlacementStatus) parts.push(humanize(context.playbackPlacementStatus));
    }
    if (kind === "snsVoiceMessageEvent") {
      if (context?.dialogId) parts.push(`dialog ${context.dialogId}`);
      if (context?.contentId !== undefined) parts.push(`content ${context.contentId}`);
      if (context?.speaker) parts.push(`speaker ${context.speaker}`);
      if (context?.durationSeconds !== undefined) parts.push(`authored duration ${context.durationSeconds}s`);
      if (context?.contentTypeName || context?.contentType !== undefined) parts.push(`content type ${context.contentTypeName || context.contentType}`);
      if (context?.runtimeRoute) parts.push(context.runtimeRoute);
      const consumers = asArray(context?.consumerEvidence).filter(Boolean);
      if (consumers.length) parts.push(`consumers ${consumers.join(" / ")}`);
      if (context?.runtimeExecutionStatus) parts.push(humanize(context.runtimeExecutionStatus));
      if (context?.playbackPlacementStatus) parts.push(humanize(context.playbackPlacementStatus));
    }
    if (context?.semanticRole) parts.push(humanize(context.semanticRole));
    if (kind === "gameplayConfigAudioReference") {
      if (context?.configKind || context?.configId) parts.push(`${context.configKind || "gameplay config"} ${context.configId || ""}`.trim());
      if (context?.triggerBindingStatus) parts.push(humanize(context.triggerBindingStatus));
      if (context?.ownerLinkStatus) parts.push(`gameplay owner ${humanize(context.ownerLinkStatus)}`);
      parts.push("config member, activation, Event posting, and runtime owner unobserved");
    }
    if (context?.confidence) parts.push(context.confidence);
    if (context?.modelId) parts.push(`model ${context.modelId}`);
    if (context?.subTemplateId) parts.push(`sub-template ${context.subTemplateId}`);
    if (context?.triggerStateName || context?.triggerStateId !== undefined) {
      parts.push(`trigger state ${context.triggerStateName || "unknown"} (${context.triggerStateId ?? "?"})`);
    }
    if (context?.triggerCustomState) parts.push(`custom state ${context.triggerCustomState}`);
    if (context?.ownerKind) parts.push(`${context.ownerKind} ${context.ownerId || ""}`.trim());
    if (context?.componentIndex !== undefined) parts.push(`component ${context.componentIndex}`);
    if (context?.sourceOffset !== undefined) parts.push(`source offset 0x${Number(context.sourceOffset).toString(16)}`);
    if (context?.stateDirection) parts.push(`${context.stateDirection} state mask ${context.audioStateMask ?? "?"}`);
    if (context?.description) parts.push(context.description);
    if (kind === "levelSequenceAudio" || kind === "timelineAudioCueBehaviorEvent") {
      if (context?.levelSequenceId) parts.push(`LevelSequence ${context.levelSequenceId}`);
      if (context?.timelineAssetName) parts.push(`Timeline ${context.timelineAssetName}`);
      if (context?.timelineParentNameStatus) parts.push(humanize(context.timelineParentNameStatus));
      if (context?.timelineTrackName || context?.timelineClipIndex !== undefined) {
        parts.push(`track ${context.timelineTrackName || "?"} / clip ${context.timelineClipIndex ?? "?"}`);
      }
      if (context?.timelineClipStartSec !== undefined || context?.timelineClipDurationSec !== undefined) {
        const start = context.timelineClipStartSec !== undefined ? formatNumber(context.timelineClipStartSec) : "?";
        const duration = context.timelineClipDurationSec !== undefined ? formatNumber(context.timelineClipDurationSec) : "?";
        parts.push(`clip time ${start}s / ${duration}s`);
      }
      if (context?.audioPlayableType) parts.push(`playable ${context.audioPlayableType}`);
      if (context?.audioPlayableRuntimeContractId) {
        parts.push(`runtime contract ${context.audioPlayableRuntimeContractId} (static metadata)`);
      }
      if (context?.audioPlayableKeyStatus) parts.push(humanize(context.audioPlayableKeyStatus));
      if (context?.authoredEventName) parts.push(`authored Event ${context.authoredEventName}`);
      if (context?.authoredEventNameEvidence) parts.push(humanize(context.authoredEventNameEvidence));
      if (context?.audioPlayableIsCue !== undefined) parts.push(`isCue ${context.audioPlayableIsCue ? "yes" : "no"}`);
      if (context?.audioPlayableStopEventAtClipEnd !== undefined) {
        parts.push(`stop-at-clip-end ${context.audioPlayableStopEventAtClipEnd ? "yes" : "no"}`);
      }
      if (context?.audioPlayableStopOnDisable !== undefined) {
        parts.push(`stop-on-disable ${context.audioPlayableStopOnDisable ? "yes" : "no"}`);
      }
      if (context?.audioPlayableEnableSeek !== undefined) parts.push(`seek ${context.audioPlayableEnableSeek ? "yes" : "no"}`);
      if (context?.audioPlayableIs2D !== undefined) parts.push(`2D ${context.audioPlayableIs2D ? "yes" : "no"}`);
      if (context?.playableDirectorCount !== undefined) {
        parts.push(`${formatNumber(context.playableDirectorCount)} PlayableDirector${Number(context.playableDirectorCount) === 1 ? "" : "s"}`);
      }
      const directorNames = asArray(context?.playableDirectorNames).filter(Boolean);
      if (directorNames.length) parts.push(`Director ${directorNames.join(" / ")}`);
      const directorIds = asArray(context?.playableDirectorPathIds).filter((value) => value !== undefined && value !== null);
      if (directorIds.length) parts.push(`Director PathIDs ${directorIds.join(" / ")}`);
      if (context?.levelScriptActionCount !== undefined) {
        parts.push(`${formatNumber(context.levelScriptActionCount)} LevelScript PlayLevelSequence record${Number(context.levelScriptActionCount) === 1 ? "" : "s"}`);
      }
      const levelScriptIds = asArray(context?.levelScriptIds).filter(Boolean);
      if (levelScriptIds.length) parts.push(`LevelScript ${levelScriptIds.join(" / ")}`);
      const levelScriptSources = asArray(context?.levelScriptSourcePaths).filter(Boolean);
      if (levelScriptSources.length) parts.push(levelScriptSources.join(" / "));
      const levelSequenceOffsets = asArray(context?.levelSequenceFieldOffsets).filter(Boolean);
      if (levelSequenceOffsets.length) parts.push(`_levelSeqId offset ${levelSequenceOffsets.join(" / ")}`);
      if (context?.ownershipEvidenceLevel) parts.push(humanize(context.ownershipEvidenceLevel));
      if (context?.triggerEvidenceLevel) parts.push(humanize(context.triggerEvidenceLevel));
      if (context?.timelineOwnershipStatus) parts.push(humanize(context.timelineOwnershipStatus));
      if (context?.evidenceBoundary) parts.push(context.evidenceBoundary);
    }
    if (context?.cueHex || context?.cueId !== undefined) parts.push(`cue ${context.cueHex || context.cueId}`);
    if (context?.globalMusicCueField) parts.push(`global cue ${context.globalMusicCueField}`);
    if (context?.handlerScope) parts.push(`${context.handlerScope} handler${context.levelId ? ` / level ${context.levelId}` : ""}`);
    if (context?.expressionPath) parts.push(`${context.expressionSide || "expression"} type ${context.exprType ?? "?"} / ${context.expressionPath}`);
    if (context?.projectileId) parts.push(`projectile ${context.projectileId}`);
    if (context?.projectileKey) parts.push(context.projectileKey);
    if (context?.soundField) parts.push(`${humanize(context.soundField)} / ${humanize(context.triggerPhase || "")}`);
    if (context?.spawnerConfigId) parts.push(`spawner ${context.spawnerConfigId}`);
    if (context?.enemyId) parts.push(`enemy ${context.enemyId}`);
    if (context?.bornTemplateId) parts.push(`born template ${context.bornTemplateId}`);
    if (context?.enemyLevel !== undefined) parts.push(`enemy level ${context.enemyLevel}`);
    if (context?.spawnerEnemyKey) parts.push(`spawn key ${context.spawnerEnemyKey}`);
    if (context?.preWarnTime !== undefined) parts.push(`pre-warning time ${context.preWarnTime}`);
    if (context?.preWarnEffectKey) parts.push(`effect ${context.preWarnEffectKey}`);
    if (context?.patrolId !== undefined) parts.push(`NPC patrol ${context.patrolId}`);
    if (context?.pointIndex !== undefined) parts.push(`point ${context.pointIndex} / action ${context.actionIndex ?? "?"}`);
    if (context?.patrolSubActionType !== undefined) parts.push(`patrol action type ${context.patrolSubActionType} / union ${context.subActionUnionTagHex || context.subActionUnionTag || "?"}`);
    if (context?.nativeConsumer) parts.push(context.nativeConsumer);
    if (context?.charInteractPerformId) parts.push(`perform ${context.charInteractPerformId}`);
    if (context?.actionPhase) parts.push(`${humanize(context.actionPhase)} action ${context.actionIndex ?? "?"}`);
    if (context?.logicId !== undefined) parts.push(`logic ${context.logicId}`);
    if (context?.attachedActorType !== undefined) parts.push(`attached actor type ${context.attachedActorType} / char index ${context.charIndex ?? "?"}`);
    if (context?.endStop !== undefined || context?.is2D !== undefined) parts.push(`end stop ${String(Boolean(context.endStop))} / 2D ${String(Boolean(context.is2D))}`);
    const preWarnRotation = asArray(context?.preWarnEffectFixedRotation);
    if (preWarnRotation.length) parts.push(`effect rotation ${preWarnRotation.join(", ")}`);
    if (context?.definitionOwnerId) parts.push(`physics definition ${context.definitionOwnerId}`);
    if (context?.templatePath) parts.push(context.templatePath);
    if (context?.interactiveTemplatePath) parts.push(`InteractiveData ${context.interactiveTemplatePath}`);
    if (context?.componentType) parts.push(`${context.componentType}${context.componentTag ? ` (${context.componentTag})` : ""}`);
    if (context?.componentResolutionStatus) parts.push(humanize(context.componentResolutionStatus));
    if (context?.audioPropertyKey) parts.push(`audio property ${context.audioPropertyKey}`);
    if (context?.propertyMapOffset) parts.push(`property map offset ${context.propertyMapOffset}`);
    if (context?.audioAction) parts.push(`${context.audioAction} / ${context.audioActionRole || "audio"} / ${context.audioSourceField || "event field"}`);
    if (context?.actionMapRole) parts.push(`${context.actionMapRole} / local ${context.actionLocalId ?? "?"} / UID ${context.actionUid || "?"}`);
    if (context?.actionUnionTag) parts.push(`action union ${context.actionUnionTag} / mc${context.actionSerializedMemberCount ?? "?"}`);
    if (context?.actionMapOffset) parts.push(`embedded action map ${context.actionMapOffset}`);
    if (context?.actionRecordOffset) parts.push(`action record ${context.actionRecordOffset} / payload ${context.actionPayloadOffset || "?"}`);
    if (context?.stopOnRelease !== undefined) parts.push(`stop on release ${String(Boolean(context.stopOnRelease))}`);
    if (context?.targetBindingKind) parts.push(`target ${context.targetBindingKind} / source ${context.targetParamSource ?? "?"}`);
    if (context?.consumerType || context?.consumerMethod) parts.push(`${context.consumerType || "managed consumer"}.${context.consumerMethod || "?"}`);
    if (context?.customStateName) parts.push(`custom state ${context.customStateName} / switch ${context.switchMethod || "?"} ${context.switchMethodVa || "?"} / callsite ${context.callsiteVa || "?"}`);
    if (context?.selectorType || context?.selectorMethod) parts.push(`selector ${context.selectorType || "managed selector"}.${context.selectorMethod || "?"} ${context.selectorMethodVa || "?"} / load ${context.selectorLoadVa || "?"} / call ${context.selectorCallVa || "?"}`);
    if (context?.selectorField) parts.push(`selector field ${context.selectorField} ${context.selectorFieldOffset || "?"}`);
    if (context?.additionalConsumerMethod) parts.push(`additional path ${context.additionalConsumerMethod} ${context.additionalMethodVa || "?"} / load ${context.additionalSelectorLoadVa || "?"} / selector call ${context.additionalSelectorCallVa || "?"} / playback call ${context.additionalPlaybackCallVa || "?"}`);
    if (context?.playbackCall) parts.push(`${context.playbackCall} / ${humanize(context.triggerRole || "managed playback")}`);
    if (context?.playbackHashCall || context?.playbackSink) parts.push(`${context.playbackHashCall || "hash"} ${context.playbackHashCallVa || "?"} -> ${context.playbackSink || "playback sink"} ${context.playbackSinkVa || "?"}`);
    if (context?.playbackInvocationVa || context?.playbackHashInvocationVa || context?.playbackSinkInvocationVa) parts.push(`invocation ${context.playbackInvocationVa || "?"} / hash ${context.playbackHashInvocationVa || "?"} / sink ${context.playbackSinkInvocationVa || "?"}`);
    if (context?.playbackParameter || context?.literalArgumentRegister) parts.push(`${context.literalArgumentInstruction || "load"} literal -> ${context.playbackParameter || "playback argument"} (${context.literalArgumentRegister || "register unknown"})`);
    if (context?.branchCondition) parts.push(`branch ${context.branchCondition}`);
    if (context?.methodVa || context?.playbackCallVa) parts.push(`method ${context.methodVa || "?"} / literal ${context.literalLoadVa || "?"} / call ${context.playbackCallVa || "?"}`);
    if (context?.targetBinding) parts.push(`target ${humanize(context.targetBinding)}`);
    const physicsConsumers = asArray(context?.consumerIds).filter(Boolean);
    if (physicsConsumers.length) parts.push(`configured consumers ${physicsConsumers.join(", ")}`);
    if (context?.componentTagHex || context?.componentTag !== undefined) {
      parts.push(`component tag ${context.componentTagHex || context.componentTag} / mc${context.serializedMemberCount ?? "?"}`);
    }
    if (context?.componentOccurrenceIndex !== undefined) parts.push(`PhysicsAudio occurrence ${context.componentOccurrenceIndex}`);
    if (context?.authoredProperty) parts.push(`${context.authoredProperty} -> ${context.runtimeField || "runtime field unknown"}`);
    if (context?.propertySourceOffset !== undefined) parts.push(`property offset 0x${Number(context.propertySourceOffset).toString(16)}`);
    if (context?.interactiveTableSha256) parts.push(`InteractiveTable SHA-256 ${context.interactiveTableSha256}`);
    if (context?.controllerId) parts.push(`ModelView controller ${context.controllerId}`);
    const animatorControllers = asArray(context?.animatorControllerContexts).filter((row) => row && typeof row === "object");
    for (const controller of animatorControllers.slice(0, 8)) {
      const stateRefs = asArray(controller.authoredStateReferences).filter((row) => row && typeof row === "object");
      const stateSummary = stateRefs.slice(0, 4).map((row) => `SM${row.stateMachineIndex ?? "?"}/S${row.stateIndex ?? "?"}/clip${row.clipSlot ?? "?"}`).join(", ");
      parts.push(`AnimatorController ${controller.name || "?"} / ${humanize(controller.resolutionStatus || "unresolved")} / clips ${(asArray(controller.clipSlots)).join(", ") || "?"} / authored states ${stateSummary || controller.authoredStateReferenceCount || 0} / runtime execution unobserved`);
    }
    if (animatorControllers.length > 8) parts.push(`+${animatorControllers.length - 8} AnimatorControllers`);
    if (context?.modelAnimatorName) parts.push(`model animator ${context.modelAnimatorName}`);
    if (context?.layerName || context?.layerFsmIndex !== undefined) parts.push(`layer ${context.layerName || "?"} / FSM ${context.layerFsmIndex ?? "?"}`);
    if (context?.stateName || context?.stateIndex !== undefined) parts.push(`state ${context.stateName || "?"} / index ${context.stateIndex ?? "?"} / type ${context.stateType ?? "?"}`);
    if (context?.behaviorTagHex || context?.behaviorTag !== undefined) parts.push(`behavior ${context.behaviorTagHex || context.behaviorTag} / mc${context.serializedMemberCount ?? "?"} / type ${context.behaviorType ?? "?"} / index ${context.behaviorIndex ?? "?"}`);
    if (context?.behaviorTime !== undefined) parts.push(`authored behavior time ${context.behaviorTime} / time-flow switch ${context.timeFlowSwitch ?? "?"}`);
    if (context?.audioNodeName) parts.push(`audio node ${context.audioNodeName}`);
    if (context?.normalAudioId !== undefined) parts.push(`normalAudioId int32 ${context.normalAudioId}`);
    if (context?.eAudioTriggerState !== undefined) parts.push(`audio trigger state ${context.eAudioTriggerState}`);
    const modelViewTemplates = asArray(context?.interactiveTemplateIds).filter(Boolean);
    if (modelViewTemplates.length) parts.push(`serialized InteractiveData associations ${modelViewTemplates.length === 1 ? modelViewTemplates[0] : `${modelViewTemplates[0]} +${modelViewTemplates.length - 1}`}`);
    const modelViewConsumers = asArray(context?.interactiveConsumerIds).filter(Boolean);
    if (modelViewConsumers.length) parts.push(`associated interactive identities ${modelViewConsumers.length === 1 ? modelViewConsumers[0] : `${modelViewConsumers[0]} +${modelViewConsumers.length - 1}`}`);
    if (context?.templateAssociationStatus) parts.push(humanize(context.templateAssociationStatus));
    const modelViewFingerprints = asArray(context?.sourceFingerprints).filter(Boolean);
    if (modelViewFingerprints.length) parts.push(`controller SHA-256 ${modelViewFingerprints.join(" / ")}`);
    if (kind === "levelScriptRadioTrigger") {
      const radioDefinition = context?.radioDefinition && typeof context.radioDefinition === "object" ? context.radioDefinition : {};
      const radioLine = context?.radioLine && typeof context.radioLine === "object" ? context.radioLine : {};
      if (context?.radioId) parts.push(`radio ${context.radioId}`);
      if (context?.action || context?.triggerRole) parts.push(`${humanize(context.action || "radio action")} / ${humanize(context.triggerRole || "role unknown")}`);
      if (context?.levelScriptId) parts.push(`LevelScript ${context.levelScriptId}`);
      const lifecycle = [];
      if (radioDefinition.radioType !== undefined) lifecycle.push(`type ${radioDefinition.radioType}`);
      if (radioDefinition.priority !== undefined) lifecycle.push(`priority ${radioDefinition.priority}`);
      if (radioDefinition.continueAfterDialog !== undefined) lifecycle.push(`continue after dialog ${String(Boolean(radioDefinition.continueAfterDialog))}`);
      if (radioDefinition.continueAfterRadio !== undefined) lifecycle.push(`continue after radio ${String(Boolean(radioDefinition.continueAfterRadio))}`);
      if (lifecycle.length) parts.push(`authored lifecycle ${lifecycle.join(" / ")}`);
      if (radioLine.is3D !== undefined) parts.push(`authored routing ${radioLine.is3D ? "3D" : "2D"}`);
      if (radioLine.actorNameId) parts.push(`actor ${radioLine.actorNameId}`);
      if (radioLine.lineOrdinal !== undefined) {
        const lineCount = Number(radioDefinition.lineCount);
        parts.push(`line order ${Number(radioLine.lineOrdinal) + 1}${Number.isFinite(lineCount) && lineCount > 0 ? ` / ${lineCount}` : ""} / ordinal ${radioLine.lineOrdinal}`);
      }
      if (radioLine.authoredIndex !== undefined) parts.push(`authored line index ${radioLine.authoredIndex}`);
      if (radioLine.lineId) parts.push(`line ${radioLine.lineId}`);
      if (radioLine.audioOverride) parts.push(`direct dialog media ${radioLine.audioOverride}`);
      if (context?.audioDialogMatchEvidence) parts.push(humanize(context.audioDialogMatchEvidence));
      if (context?.radioIdentityKind) parts.push(humanize(context.radioIdentityKind));
      if (context?.wwiseEventStatus || radioLine.wwiseEventStatus) parts.push(`Wwise Event ${humanize(context.wwiseEventStatus || radioLine.wwiseEventStatus)}`);
      if (radioDefinition.source) parts.push(radioDefinition.source);
      if (radioLine.source && radioLine.source !== radioDefinition.source) parts.push(radioLine.source);
    } else {
      if (context?.levelScriptId) parts.push(`LevelScript ${context.levelScriptId}`);
      if (context?.action) parts.push(humanize(context.action));
      if (context?.triggerRole) parts.push(`request role ${humanize(context.triggerRole)}`);
    }
    if (context?.sourceField) parts.push(context.sourceField);
    if (context?.actionMapRole) parts.push(context.actionMapRole);
    if (context?.recordUid || context?.recordLocalId !== undefined) parts.push(`record ${context.recordUid || "?"} / local ${context.recordLocalId ?? "?"}`);
    if (context?.sourcePath) parts.push(context.sourcePath);
    if (context?.sourceSha256) parts.push(`SHA-256 ${context.sourceSha256}`);
    for (const [fieldName, field] of Object.entries(context?.fields || {})) {
      if (!field || typeof field !== "object") continue;
      const value = field.value !== undefined
        ? (typeof field.value === "object" ? JSON.stringify(field.value) : String(field.value))
        : field.path || "";
      parts.push(`${field.sourceField || fieldName}: ${humanize(field.bindingKind || "unknown")}${value ? ` = ${value}` : ""}`);
    }
    if (context?.eventHash !== undefined) parts.push(`Event 0x${Number(context.eventHash).toString(16).padStart(8, "0")}`);
    if (context?.signedValue !== undefined) parts.push(`serialized int32 ${context.signedValue}`);
    if (context?.runtimeActivationStatus) parts.push(humanize(context.runtimeActivationStatus));
    const authoredSkillIds = asArray(context?.authoredSkillIds).filter(Boolean);
    if (authoredSkillIds.length) parts.push(`projectile template skills: ${authoredSkillIds.length === 1 ? authoredSkillIds[0] : `${authoredSkillIds[0]} +${authoredSkillIds.length - 1}`}`);
    if (context?.skillOwnershipStatus) parts.push(humanize(context.skillOwnershipStatus));
    if (context?.sourceJsonPath) parts.push(context.sourceJsonPath);
    if (context?.sourceRoot || context?.sourcePathId) parts.push(`${context.sourceRoot || "source"} PathID ${context.sourcePathId || "?"}`);
    if (context?.sourceFile) parts.push(`CAB ${context.sourceFile}`);
    if (context?.sourceVfsPath) parts.push(context.sourceVfsPath);
    if (context?.sourceFingerprint) parts.push(`source SHA-256 ${context.sourceFingerprint}`);
    if (context?.semanticPath) parts.push(context.semanticPath);
    const sourcePaths = asArray(context?.sourcePaths).filter(Boolean);
    if (sourcePaths.length) parts.push(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths[0]} +${sourcePaths.length - 1}`);
    if (context?.triggerBindingStatus) parts.push(humanize(context.triggerBindingStatus));
    const requestEvidence = asArray(context?.triggerRequestEvidence).filter(Boolean);
    if (requestEvidence.length) parts.push(requestEvidence.map(humanize).join(" / "));
    const activationStatuses = asArray(context?.triggerRuntimeActivationStatuses).filter(Boolean);
    if (activationStatuses.length) parts.push(activationStatuses.map(humanize).join(" / "));
    const triggerRelations = asArray(context?.triggerRelationTypes).filter(Boolean);
    if (triggerRelations.length) parts.push(triggerRelations.map(humanize).join(" / "));
    const triggerMethods = asArray(context?.triggerOwnershipMethods).filter(Boolean);
    if (triggerMethods.length) parts.push(triggerMethods.map(humanize).join(" / "));
    const triggerKinds = asArray(context?.triggerEvidenceKinds).filter(Boolean);
    if (triggerKinds.length) parts.push(triggerKinds.map(humanize).join(" / "));
    const triggerBuffIds = asArray(context?.triggerBuffIds).filter(Boolean);
    if (triggerBuffIds.length) parts.push(triggerBuffIds.length === 1 ? triggerBuffIds[0] : `${triggerBuffIds[0]} +${triggerBuffIds.length - 1}`);
    const triggerSourcePaths = asArray(context?.triggerSourcePaths).filter(Boolean);
    if (triggerSourcePaths.length) parts.push(triggerSourcePaths.length === 1 ? triggerSourcePaths[0] : `${triggerSourcePaths[0]} +${triggerSourcePaths.length - 1}`);
    const playSoundActions = asArray(context?.triggerPlaySoundActions).filter((value) => value && typeof value === "object");
    for (const action of playSoundActions) {
      const actionParts = [
        `PlaySound frame ${action.startFrame ?? "?"}-${action.endFrame ?? "?"}`,
        action.stopOnEnd ? `stop on end / ${action.stopFadeDurationMs ?? 0} ms fade` : "not stopped by this action's end",
        action.useTempEmitter ? "temporary emitter" : "",
        action.followMountPoint ? `follow mount ${action.mountPoint || "(unnamed)"}` : "",
        action.useWeaponMountPoint ? `weapon ${action.weaponIndex ?? "?"} / ${action.weaponMountPoint || "mount"}` : "",
        action.targetSelector ? `target ${action.targetSelector}` : "target settings unresolved",
        action.useTimeDilationPauseAndSeek ? "time-dilation pause/seek" : "",
      ].filter(Boolean);
      parts.push(actionParts.join(" / "));
    }
    const skillIds = asArray(context?.skillIds).filter(Boolean);
    if (skillIds.length) parts.push(skillIds.length === 1 ? skillIds[0] : `${skillIds[0]} +${skillIds.length - 1}`);
    const actionKinds = asArray(context?.actionKinds).filter(Boolean);
    if (actionKinds.length) parts.push(actionKinds.map(humanize).join(" / "));
    if (Number(context?.animationOwnerCount || 0) > 1) {
      parts.push(`${context.animationOwnerCount} ${kind === "characterAnimation" ? "playable character" : "enemy template"} animation owners`);
    }
    if (context?.animationOwnershipScope) parts.push(humanize(context.animationOwnershipScope));
    if (context?.possibleMediaScope) parts.push(humanize(context.possibleMediaScope));
    const functions = asArray(context?.animationFunctions).filter(Boolean);
    if (functions.length) parts.push(functions.join(" / "));
    if (Number(context?.customFootstepOccurrenceCount || 0) > 0) {
      parts.push(`OnCustomFootStep ${formatNumber(context.customFootstepOccurrenceCount)} callbacks / ${asArray(context.customFootstepParameterVariants).length} parameter variants`);
    }
    const clipContexts = asArray(context?.animationClipContexts).filter(Boolean);
    if (clipContexts.length) parts.push(clipContexts.map(humanize).join(" / "));
    if (context?.clipReachability) parts.push(`clip reachability: ${context.clipReachability}`);
    const clips = asArray(context?.animationClips).filter(Boolean);
    if (clips.length) parts.push(clips.length === 1 ? clips[0] : `${clips[0]} +${clips.length - 1}`);
    return [...new Set(parts.filter(Boolean))].join(" · ");
  }

  function radioTableLineLabel(line) {
    const parts = [];
    if (line?.radioId) parts.push(`radio ${line.radioId}`);
    if (line?.lineOrdinal !== undefined) parts.push(`line order ${Number(line.lineOrdinal) + 1} / ordinal ${line.lineOrdinal}`);
    if (line?.authoredIndex !== undefined) parts.push(`authored index ${line.authoredIndex}`);
    if (line?.lineId) parts.push(`line ${line.lineId}`);
    if (line?.actorNameId) parts.push(`actor ${line.actorNameId}`);
    if (line?.is3D !== undefined) parts.push(`authored routing ${line.is3D ? "3D" : "2D"}`);
    if (line?.audioOverride) parts.push(`direct dialog media ${line.audioOverride}`);
    if (line?.audioOverrideIdentityKind) parts.push(humanize(line.audioOverrideIdentityKind));
    if (line?.wwiseEventStatus) parts.push(`Wwise Event ${humanize(line.wwiseEventStatus)}`);
    if (line?.source) parts.push(line.source);
    return parts.join(" / ");
  }

  function selectorEvidenceSummary(record) {
    const actions = new Map();
    const containers = new Map();
    const musicNodes = new Map();
    const actionDetails = [];
    let initialRtpcActionJoins = 0;
    const selector = {
      nodes: 0, exact: 0, unresolved: 0, continuous: 0,
      packages: 0, nonEmptyPackages: 0, strictSubsetPackages: 0,
      packageChildRefs: 0, associations: 0, continuePlayback: 0,
      isFirstOnly: 0, nonzeroFadeOut: 0, nonzeroFadeIn: 0,
      defaultMissing: 0, outsideChildren: 0, unmappedChildren: 0,
      groupTypes: new Map(), switchModes: new Map(), parserStatuses: new Map(),
      groupIds: new Set(), groupIdsTruncated: false,
      semanticGroupMatches: 0, semanticValueMatches: 0,
      semanticValues: new Map(), semanticValuesTruncated: false,
    };
    const randomSequence = {
      nodes: 0, exact: 0, unresolved: 0, playlistItems: 0,
      orderDiffers: 0, nonDefaultWeightItems: 0, nonDefaultWeightNodes: 0,
      nonUniformWeightNodes: 0, nonDefaultAvoid: 0, maxAvoid: 0,
      nonDefaultLoop: 0, globalScope: 0, continuous: 0, resetPlaylist: 0,
      ownedNotInPlaylist: 0, duplicateItems: 0, emptyPlaylists: 0,
      modes: new Map(), randomModes: new Map(), transitions: new Map(), statuses: new Map(),
      memberships: new Map(),
    };
    const layerBlend = {
      nodes: 0, exact: 0, unresolved: 0, definitions: 0,
      initialCurves: 0, associations: 0, points: 0, continuous: 0,
      outsideChildren: 0, statuses: new Map(), proof: new Map(),
      assignments: new Map(), rtpcTypes: new Map(), rtpcIds: new Set(),
      rtpcIdsTruncated: false,
    };
    const postProcess = {
      parsedNodes: 0, effectNodes: 0, effectSlots: 0, effectReferences: 0,
      effectBypassSlots: 0, effectShareSetSlots: 0, effectRenderedSlots: 0,
      effectUnknownFlagBits: 0,
      decodedParameterReferences: 0, exactParameterReferences: 0,
      partialParameterReferences: 0, emptySlots: 0, outputBusNodes: 0, metadataSlots: 0,
      parsedAuxNodes: 0, failedAuxNodes: 0, authoredAuxFlagNodes: 0,
      gameDefinedUseNodes: 0, userDefinedReferences: 0, reflectionsReferences: 0,
      parsedStateRtpcNodes: 0, failedStateRtpcNodes: 0, stateRtpcNodes: 0,
      stateGroupReferences: 0, stateValues: 0, rtpcCurves: 0, rtpcPoints: 0,
      authoredPropertyValues: 0, authoredRangedPropertyValues: 0,
      plugins: new Map(), resolutions: new Map(), busResolutions: new Map(),
      auxBusResolutions: new Map(), parameterSchemas: new Map(), buses: new Map(),
      auxiliaryBuses: new Map(), stateGroups: new Map(), rtpcIds: new Map(),
      rtpcTypes: new Map(), rtpcParameters: new Map(), propertyCounts: new Map(),
      rangedPropertyCounts: new Map(),
      effectRows: [], auxRows: [], propertyRows: [], stateRtpcRows: [], boundaries: new Set(),
    };
    const busDefinitions = new Map(asArray(state.index?.hircSummary?.postProcessSummary?.busDefinitions)
      .filter((row) => row && typeof row === "object" && (row.busIdHex || row.busId))
      .map((row) => [normalize(row.busIdHex || row.busId).toLowerCase(), row]));
    let unresolved = 0;
    for (const evidence of asArray(record?.evidence)) {
      const dispatch = evidence?.actionDispatchEvidence;
      if (dispatch && typeof dispatch === "object" && dispatch.timingClass) {
        actionDetails.push([
          `${t("actionDispatch")}: ${humanize(dispatch.timingClass)}`,
          `${formatNumber(dispatch.playbackActionCount || 0)} playback actions`,
          dispatch.controlActionCount ? `${formatNumber(dispatch.controlActionCount)} control actions` : "",
          dispatch.typedControlActionCount ? `${formatNumber(dispatch.typedControlActionCount)} control payloads exact` : "",
          dispatch.failedControlActionCount ? `${formatNumber(dispatch.failedControlActionCount)} control payloads unresolved` : "",
          dispatch.explicitDelayActionCount ? `${formatNumber(dispatch.explicitDelayActionCount)} delayed` : "",
          dispatch.explicitTransitionActionCount ? `${formatNumber(dispatch.explicitTransitionActionCount)} transitions` : "",
          dispatch.probabilityGatedActionCount ? `${formatNumber(dispatch.probabilityGatedActionCount)} probability gates` : "",
        ].filter(Boolean).join(" / "));
      }
      for (const action of asArray(evidence?.actionEvidence)) {
        const operation = humanize(action?.operation || "unknown action");
        actions.set(operation, (actions.get(operation) || 0) + 1);
        const serializedPath = asArray(action?.serializedPathTypeLabels)
          .map((value) => humanize(value))
          .join(" -> ");
        const target = action?.targetTypeLabel
          ? `target ${humanize(action.targetTypeLabel)}${action.targetId !== undefined && action.targetId !== null ? ` 0x${Number(action.targetId).toString(16)}` : ""}`
          : "";
        const pathEvidence = [target, serializedPath ? `serialized path ${serializedPath}` : ""]
          .filter(Boolean)
          .join(" / ");
        if (action?.actionControlParserStatus === "typedExactV150") {
          const groupSemantic = action?.controlGroupSemantic || {};
          const valueSemantic = action?.controlValueSemantic || {};
          const groupLabel = groupSemantic.semanticLabel
            ? `${groupSemantic.semanticLabel} (${action.groupIdHex || "?"})`
            : (action.groupIdHex || "?");
          const valueLabel = valueSemantic.resolvedValueName || valueSemantic.semanticName
            ? `${valueSemantic.resolvedValueName || valueSemantic.semanticName} (${action.stateIdHex || action.switchIdHex || "?"})`
            : (action.stateIdHex || action.switchIdHex || "?");
          const control = action?.operation === "setState"
            ? `state group ${groupLabel} -> ${valueLabel}`
            : action?.operation === "setSwitch"
              ? `switch group ${groupLabel} -> ${valueLabel}`
              : action?.operation === "setGameParameter" || action?.operation === "resetGameParameter"
                ? `parameter ${action.idExtHex || "?"} / ${action.valueRange ? `${action.valueRange.base} (${action.valueMeaningLabel || "value"})` : "reset"}`
                : action?.operation === "setBypassFXSlot" || action?.operation === "resetBypassFXSlot"
                  ? `FX slot ${action.fxSlot ?? "?"} / bypass ${action.bypass ? "on" : "off"}`
                  : action?.operation === "stop" || action?.operation === "pause" || action?.operation === "resume"
                    ? `flags 0x${Number(action.actionBitVectorRaw || 0).toString(16).padStart(2, "0")}`
                    : action?.operation === "seek"
                      ? `seek ${action.seekValue ?? "?"}${action.seekRelativeToDuration ? " relative" : ""}`
                    : action?.operation;
          const initialRtpc = action?.initialRtpcSemantic;
          if (initialRtpc && typeof initialRtpc === "object") initialRtpcActionJoins += 1;
          const initialRtpcEvidence = initialRtpc
            ? `Initial RTPC ${initialRtpc.rtpcIdHex || "?"} / ${formatNumber(initialRtpc.curveCount || 0)} curve${Number(initialRtpc.curveCount || 0) === 1 ? "" : "s"}`
            : "";
          actionDetails.push(`${t("actionOrdinal")} ${Number(action.eventActionOrdinal || 0) + 1} (${operation}): ${control}${pathEvidence ? ` / ${pathEvidence}` : ""}${initialRtpcEvidence ? ` / ${initialRtpcEvidence}` : ""}`);
        }
        if (action?.actionParserStatus !== "typedExactV150" || !["play", "playEvent"].includes(action?.operation)) continue;
        const delay = asArray(action?.delay?.baseValuesMs);
        const delayRanges = asArray(action?.delay?.modifierRangesMs);
        const transition = asArray(action?.transition?.baseValuesMs);
        const probability = asArray(action?.probability?.baseValuesPercent);
        const detail = [
          delay.length ? `delay ${delay.join(" / ")} ms` : t("serializedNoDelay"),
          delayRanges.length ? `delay range ${delayRanges.map((row) => `${row.minimum}-${row.maximum} ms`).join(" / ")}` : "",
          transition.length ? `${t("transitionTime")} ${transition.join(" / ")} ms` : "",
          probability.length ? `${t("probabilityGate")} ${probability.join(" / ")}%` : "",
          action?.fade?.curveLabel ? `${t("fadeCurve")} ${action.fade.curveLabel}` : "",
          pathEvidence,
        ].filter(Boolean).join(" / ");
        actionDetails.push(`${t("actionOrdinal")} ${Number(action.eventActionOrdinal || 0) + 1} (${operation}): ${detail}`);
      }
      for (const container of asArray(evidence?.containerEvidence)) {
        const relation = normalize(container?.edgeKind) || "unknown";
        const current = containers.get(relation) || { count: 0, children: 0 };
        current.count += Number(container?.nodeCount || 1);
        current.children += Number(container?.childCount || 0);
        containers.set(relation, current);
        selector.nodes += Number(container?.selectorNodeCount || 0);
        selector.exact += Number(container?.typedSelectorNodeCount || 0);
        selector.unresolved += Number(container?.unresolvedSelectorNodeCount || 0);
        selector.continuous += Number(container?.continuousValidationNodeCount || 0);
        selector.packages += Number(container?.selectorPackageCount || 0);
        selector.nonEmptyPackages += Number(container?.nonEmptySelectorPackageCount || 0);
        selector.strictSubsetPackages += Number(container?.strictSubsetSelectorPackageCount || 0);
        selector.packageChildRefs += Number(container?.selectorPackageChildReferenceCount || 0);
        selector.associations += Number(container?.selectorAssociationCount || 0);
        selector.continuePlayback += Number(container?.continuePlaybackAssociationCount || 0);
        selector.isFirstOnly += Number(container?.isFirstOnlyAssociationCount || 0);
        selector.nonzeroFadeOut += Number(container?.nonzeroFadeOutAssociationCount || 0);
        selector.nonzeroFadeIn += Number(container?.nonzeroFadeInAssociationCount || 0);
        selector.defaultMissing += Number(container?.defaultValueMissingPackageCount || 0);
        selector.outsideChildren += Number(container?.mappedChildOutsideChildrenCount || 0)
          + Number(container?.associationChildOutsideChildrenCount || 0);
        selector.unmappedChildren += Number(container?.unmappedSelectorChildCount || 0);
        for (const [key, count] of Object.entries(container?.selectorGroupTypes || {})) {
          selector.groupTypes.set(key, (selector.groupTypes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.selectorSwitchModes || {})) {
          selector.switchModes.set(key, (selector.switchModes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.selectorParserStatuses || {})) {
          selector.parserStatuses.set(key, (selector.parserStatuses.get(key) || 0) + Number(count || 0));
        }
        for (const groupId of asArray(container?.selectorGroupIdsHex)) selector.groupIds.add(groupId);
        selector.groupIdsTruncated ||= !!container?.selectorGroupIdsTruncated;
        selector.semanticGroupMatches += Number(container?.selectorSemanticGroupMatchCount || 0);
        selector.semanticValueMatches += Number(container?.selectorSemanticValueMatchCount || 0);
        selector.semanticValuesTruncated ||= !!container?.selectorSemanticValuesTruncated;
        for (const semanticValue of asArray(container?.selectorSemanticValues)) {
          if (!semanticValue || typeof semanticValue !== "object") continue;
          const key = `${normalize(semanticValue.groupIdHex || "?").toLowerCase()}:${normalize(semanticValue.valueIdHex || "?").toLowerCase()}`;
          selector.semanticValues.set(key, semanticValue);
        }
        randomSequence.nodes += Number(container?.randomSequenceNodeCount || 0);
        randomSequence.exact += Number(container?.typedRandomSequenceNodeCount || 0);
        randomSequence.unresolved += Number(container?.unresolvedRandomSequenceNodeCount || 0);
        randomSequence.playlistItems += Number(container?.randomSequencePlaylistItemCount || 0);
        randomSequence.orderDiffers += Number(container?.playlistOrderDiffersFromChildrenCount || 0);
        randomSequence.ownedNotInPlaylist += Number(container?.randomSequenceOwnedChildNotInPlaylistCount || 0);
        randomSequence.duplicateItems += Number(container?.randomSequenceDuplicatePlaylistItemCount || 0);
        randomSequence.emptyPlaylists += Number(container?.randomSequenceEmptyPlaylistNodeCount || 0);
        randomSequence.nonDefaultWeightItems += Number(container?.nonDefaultWeightItemCount || 0);
        randomSequence.nonDefaultWeightNodes += Number(container?.nonDefaultWeightNodeCount || 0);
        randomSequence.nonUniformWeightNodes += Number(container?.nonUniformWeightNodeCount || 0);
        randomSequence.nonDefaultAvoid += Number(container?.nonDefaultAvoidRepeatNodeCount || 0);
        randomSequence.maxAvoid = Math.max(randomSequence.maxAvoid, Number(container?.maxAvoidRepeatCount || 0));
        randomSequence.nonDefaultLoop += Number(container?.nonDefaultLoopNodeCount || 0);
        randomSequence.globalScope += Number(container?.globalScopeRandomSequenceNodeCount || 0);
        randomSequence.continuous += Number(container?.continuousRandomSequenceNodeCount || 0);
        randomSequence.resetPlaylist += Number(container?.resetPlaylistNodeCount || 0);
        for (const [key, count] of Object.entries(container?.randomSequenceModes || {})) {
          randomSequence.modes.set(key, (randomSequence.modes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomModes || {})) {
          randomSequence.randomModes.set(key, (randomSequence.randomModes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomTransitionModes || {})) {
          randomSequence.transitions.set(key, (randomSequence.transitions.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomSequenceParserStatuses || {})) {
          randomSequence.statuses.set(key, (randomSequence.statuses.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.randomSequenceMembershipStatuses || {})) {
          randomSequence.memberships.set(key, (randomSequence.memberships.get(key) || 0) + Number(count || 0));
        }
        layerBlend.nodes += Number(container?.layerNodeCount || 0);
        layerBlend.exact += Number(container?.typedLayerNodeCount || 0);
        layerBlend.unresolved += Number(container?.unresolvedLayerNodeCount || 0);
        layerBlend.definitions += Number(container?.layerDefinitionCount || 0);
        layerBlend.initialCurves += Number(container?.layerInitialRtpcCurveCount || 0);
        layerBlend.associations += Number(container?.layerAssociationCount || 0);
        layerBlend.points += Number(container?.layerCurvePointCount || 0);
        layerBlend.continuous += Number(container?.continuousLayerNodeCount || 0);
        layerBlend.outsideChildren += Number(container?.layerAssociationOutsideChildrenCount || 0);
        for (const [key, count] of Object.entries(container?.layerParserStatuses || {})) {
          layerBlend.statuses.set(key, (layerBlend.statuses.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.layerProofStatuses || {})) {
          layerBlend.proof.set(key, (layerBlend.proof.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.layerAssignmentStatuses || {})) {
          layerBlend.assignments.set(key, (layerBlend.assignments.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(container?.layerRtpcTypes || {})) {
          layerBlend.rtpcTypes.set(key, (layerBlend.rtpcTypes.get(key) || 0) + Number(count || 0));
        }
        for (const rtpcId of asArray(container?.layerRtpcIdsHex)) layerBlend.rtpcIds.add(rtpcId);
        layerBlend.rtpcIdsTruncated ||= !!container?.layerRtpcIdsTruncated;
      }
      for (const node of asArray(evidence?.musicNodeEvidence)) {
        const kind = normalize(node?.nodeKind) || `musicType${node?.objectType ?? "?"}`;
        const current = musicNodes.get(kind) || {
          count: 0, children: 0, sources: 0, selectionTypes: new Set(),
          structureStatuses: new Map(), selectorStatuses: new Map(),
          ownedNotSelected: 0, recursiveOwned: 0, unboundLeaves: 0,
          unresolvedLeafObjects: 0,
        };
        current.count += 1;
        current.children += Number(node?.childCount || 0);
        current.sources += Number(node?.sourceCount || 0);
        const structureStatus = normalize(node?.structureStatus);
        if (structureStatus) current.structureStatuses.set(structureStatus, (current.structureStatuses.get(structureStatus) || 0) + 1);
        const selectorStatus = normalize(node?.selectorValidation?.status);
        if (selectorStatus) current.selectorStatuses.set(selectorStatus, (current.selectorStatuses.get(selectorStatus) || 0) + 1);
        current.ownedNotSelected += asArray(node?.selectorValidation?.reciprocalChildrenWithoutTreeLeaf).length;
        current.ownedNotSelected += asArray(node?.selectorValidation?.reciprocalChildrenWithoutPlaylistTerminal).length;
        current.recursiveOwned += asArray(node?.selectorValidation?.recursiveOwnedDescendantIds).length;
        current.unboundLeaves += asArray(node?.selectorValidation?.zeroUnboundLeafIds).length;
        current.unresolvedLeafObjects += asArray(node?.selectorValidation?.sameBankMissingLeafIds).length;
        current.unresolvedLeafObjects += asArray(node?.selectorValidation?.localOtherParentLeafIds).length;
        current.unresolvedLeafObjects += asArray(node?.selectorValidation?.playlistTerminalSegmentIdsOutsideReciprocalChildren).length;
        for (const label of asArray(node?.selectionTypeLabels).filter(Boolean)) current.selectionTypes.add(humanize(label));
        musicNodes.set(kind, current);
      }
      const processing = evidence?.postProcessSummary;
      if (processing && typeof processing === "object") {
        postProcess.parsedNodes += Number(processing.parsedNodeCount || 0);
        postProcess.effectNodes += Number(processing.effectNodeCount || 0);
        postProcess.effectSlots += Number(processing.effectSlotCount || 0);
        postProcess.effectReferences += Number(processing.effectReferenceCount || 0);
        postProcess.effectBypassSlots += Number(processing.effectBypassSlotCount || 0);
        postProcess.effectShareSetSlots += Number(processing.effectShareSetSlotCount || 0);
        postProcess.effectRenderedSlots += Number(processing.effectRenderedSlotCount || 0);
        postProcess.effectUnknownFlagBits += Number(processing.effectUnknownFlagBitsCount || 0);
        postProcess.decodedParameterReferences += Number(processing.decodedEffectParameterReferenceCount || 0);
        postProcess.exactParameterReferences += Number(processing.exactEffectParameterReferenceCount || 0);
        postProcess.partialParameterReferences += Number(processing.partialEffectParameterReferenceCount || 0);
        postProcess.emptySlots += Number(processing.emptyEffectSlotCount || 0);
        postProcess.outputBusNodes += Number(processing.outputBusNodeCount || 0);
        postProcess.metadataSlots += Number(processing.metadataSlotCount || 0);
        postProcess.parsedAuxNodes += Number(processing.parsedAuxSendNodeCount || 0);
        postProcess.failedAuxNodes += Number(processing.failedAuxSendNodeCount || 0);
        postProcess.authoredAuxFlagNodes += Number(processing.authoredAuxFlagNodeCount || 0);
        postProcess.gameDefinedUseNodes += Number(processing.gameDefinedAuxSendUseBitNodeCount || 0);
        postProcess.userDefinedReferences += Number(processing.userDefinedAuxSendReferenceCount || 0);
        postProcess.reflectionsReferences += Number(processing.earlyReflectionsAuxSendReferenceCount || 0);
        postProcess.parsedStateRtpcNodes += Number(processing.parsedStateRtpcNodeCount || 0);
        postProcess.failedStateRtpcNodes += Number(processing.failedStateRtpcNodeCount || 0);
        postProcess.stateRtpcNodes += Number(processing.stateRtpcNodeCount || 0);
        postProcess.stateGroupReferences += Number(processing.stateGroupReferenceCount || 0);
        postProcess.stateValues += Number(processing.stateValueCount || 0);
        postProcess.rtpcCurves += Number(processing.rtpcCurveCount || 0);
        postProcess.rtpcPoints += Number(processing.rtpcPointCount || 0);
        postProcess.authoredPropertyValues += Number(processing.authoredPropertyValueCount || 0);
        postProcess.authoredRangedPropertyValues += Number(processing.authoredRangedPropertyValueCount || 0);
        for (const [key, count] of Object.entries(processing.effectPluginReferenceCounts || {})) {
          postProcess.plugins.set(key, (postProcess.plugins.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.effectResolutionCounts || {})) {
          postProcess.resolutions.set(key, (postProcess.resolutions.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.effectParameterSchemaReferenceCounts || {})) {
          postProcess.parameterSchemas.set(key, (postProcess.parameterSchemas.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.outputBusResolutionCounts || {})) {
          postProcess.busResolutions.set(key, (postProcess.busResolutions.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.auxiliaryBusResolutionCounts || {})) {
          postProcess.auxBusResolutions.set(key, (postProcess.auxBusResolutions.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.rtpcTypeCounts || {})) {
          postProcess.rtpcTypes.set(key, (postProcess.rtpcTypes.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.rtpcParameterCounts || {})) {
          postProcess.rtpcParameters.set(key, (postProcess.rtpcParameters.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.authoredPropertyCounts || {})) {
          postProcess.propertyCounts.set(key, (postProcess.propertyCounts.get(key) || 0) + Number(count || 0));
        }
        for (const [key, count] of Object.entries(processing.authoredRangedPropertyCounts || {})) {
          postProcess.rangedPropertyCounts.set(key, (postProcess.rangedPropertyCounts.get(key) || 0) + Number(count || 0));
        }
        for (const bus of asArray(processing.outputBuses)) {
          if (!bus || typeof bus !== "object") continue;
          const key = normalize(bus.busIdHex || bus.busId || "unknown");
          const current = postProcess.buses.get(key) || {
            count: 0,
            status: bus.resolutionStatus,
            labels: bus.objectTypeLabels,
            path: asArray(bus.busPathIdHexes),
            pathStatus: bus.busPathResolutionStatus,
            unresolvedProcessing: asArray(bus.unresolvedBusProcessingIdHexes),
          };
          current.count += Number(bus.nodeCount || 0);
          postProcess.buses.set(key, current);
        }
        for (const bus of asArray(processing.auxiliaryBuses)) {
          if (!bus || typeof bus !== "object") continue;
          const busId = normalize(bus.busIdHex || bus.busId || "unknown");
          const key = `${normalize(bus.sendKind || "auxiliary")}:${busId}`;
          const current = postProcess.auxiliaryBuses.get(key) || {
            sendKind: normalize(bus.sendKind || "auxiliary"),
            busId,
            count: 0,
            status: bus.resolutionStatus,
            labels: bus.objectTypeLabels,
            path: asArray(bus.busPathIdHexes),
            pathStatus: bus.busPathResolutionStatus,
            unresolvedProcessing: asArray(bus.unresolvedBusProcessingIdHexes),
          };
          current.count += Number(bus.referenceCount || 0);
          postProcess.auxiliaryBuses.set(key, current);
        }
        for (const node of asArray(processing.auxSendNodes)) {
          if (node && typeof node === "object") postProcess.auxRows.push(node);
        }
        for (const node of asArray(processing.propertyNodes)) {
          if (node && typeof node === "object") postProcess.propertyRows.push(node);
        }
        for (const group of asArray(processing.stateGroups)) {
          if (!group || typeof group !== "object") continue;
          const key = normalize(group.groupIdHex || group.groupId || "unknown");
          const current = postProcess.stateGroups.get(key) || { nodeCount: 0, valueCount: 0 };
          current.nodeCount += Number(group.nodeCount || 0);
          current.valueCount += Number(group.valueCount || 0);
          postProcess.stateGroups.set(key, current);
        }
        for (const rtpc of asArray(processing.rtpcIds)) {
          if (!rtpc || typeof rtpc !== "object") continue;
          const key = normalize(rtpc.rtpcIdHex || rtpc.rtpcId || "unknown");
          postProcess.rtpcIds.set(key, (postProcess.rtpcIds.get(key) || 0) + Number(rtpc.curveCount || 0));
        }
        for (const node of asArray(processing.stateRtpcNodes)) {
          if (node && typeof node === "object") postProcess.stateRtpcRows.push(node);
        }
        for (const node of asArray(processing.effectNodes)) {
          if (node && typeof node === "object") {
            postProcess.effectRows.push(node);
            for (const slot of asArray(node.effects)) {
              if (slot?.parameterSemanticBoundary) {
                postProcess.boundaries.add(slot.parameterSemanticBoundary);
              }
            }
          }
        }
        if (processing.evidenceBoundary) postProcess.boundaries.add(processing.evidenceBoundary);
      }
      unresolved += asArray(evidence?.unresolvedNodes).length;
    }
    const values = [...actions].map(([operation, count]) => `${operation} × ${formatNumber(count)}`);
    for (const [relation, value] of containers) {
      values.push(`${taxonomyLabel(relation)}: ${formatNumber(value.count)} nodes / ${formatNumber(value.children)} child edges`);
    }
    if (selector.nodes) {
      const groupTypes = [...selector.groupTypes]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      const statuses = [...selector.parserStatuses]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      const groupIds = [...selector.groupIds];
      values.push([
        `Wwise Switch/State selectors: ${formatNumber(selector.nodes)} nodes`,
        `${formatNumber(selector.exact)} typed exact`,
        selector.unresolved ? `${formatNumber(selector.unresolved)} unresolved` : "",
        groupTypes,
        selector.continuous ? `${formatNumber(selector.continuous)} continuous-validation` : "",
        statuses,
      ].filter(Boolean).join(" / "));
      if (selector.semanticGroupMatches || selector.semanticValueMatches) {
        values.push([
          `Native semantic selector joins: ${formatNumber(selector.semanticGroupMatches)} group mappings`,
          `${formatNumber(selector.semanticValueMatches)} package values`,
          [...selector.semanticValues.values()].slice(0, 12).map((row) =>
            `${row.groupIdHex || "?"} -> ${row.semanticName || row.resolvedValueName || row.valueIdHex || "?"}`
          ).join(" / "),
          selector.semanticValuesTruncated || selector.semanticValues.size > 12 ? "more omitted" : "",
        ].filter(Boolean).join(" / "));
      }
      values.push([
        `Selector packages: ${formatNumber(selector.packages)}`,
        `${formatNumber(selector.nonEmptyPackages)} non-empty`,
        `${formatNumber(selector.strictSubsetPackages)} strict child subsets`,
        `${formatNumber(selector.packageChildRefs)} mapped child references`,
        selector.defaultMissing ? `${formatNumber(selector.defaultMissing)} defaults absent from packages` : "",
        selector.outsideChildren ? `${formatNumber(selector.outsideChildren)} references outside reciprocal Children` : "",
        selector.unmappedChildren ? `${formatNumber(selector.unmappedChildren)} reciprocal Children unmapped` : "",
      ].filter(Boolean).join(" / "));
      values.push([
        `Selector associations: ${formatNumber(selector.associations)}`,
        [...selector.switchModes].map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`).join(" / "),
        selector.continuePlayback ? `${formatNumber(selector.continuePlayback)} continue playback` : "",
        selector.isFirstOnly ? `${formatNumber(selector.isFirstOnly)} first-only` : "",
        selector.nonzeroFadeOut ? `${formatNumber(selector.nonzeroFadeOut)} nonzero fade-out` : "",
        selector.nonzeroFadeIn ? `${formatNumber(selector.nonzeroFadeIn)} nonzero fade-in` : "",
      ].filter(Boolean).join(" / "));
      if (groupIds.length) {
        const runtimeGroups = new Map(asArray(state.index?.controlCatalog?.wwiseSelectorGroups)
          .filter((row) => row && typeof row === "object" && row.groupIdHex)
          .map((row) => [normalize(row.groupIdHex).toLowerCase(), row]));
        const labeledGroupIds = groupIds.slice(0, 12).map((groupId) => {
          const runtimeGroup = runtimeGroups.get(normalize(groupId).toLowerCase());
          if (!runtimeGroup) return groupId;
          return `${groupId} (${runtimeGroup.semanticLabel || humanize(runtimeGroup.semanticRole || "unknown")} / ${humanize(runtimeGroup.semanticEvidence || "unknown")})`;
        });
        values.push(`Selector group ids: ${labeledGroupIds.join(" / ")}${selector.groupIdsTruncated || groupIds.length > 12 ? " / more omitted" : ""}`);
      }
      values.push("Runtime selector value and audio-object state were not observed; every mapped child remains only a possible branch.");
    }
    if (randomSequence.nodes) {
      const summarizeCounts = (counts) => [...counts]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      values.push([
        `Wwise Random/Sequence policy: ${formatNumber(randomSequence.nodes)} nodes`,
        `${formatNumber(randomSequence.exact)} typed exact`,
        randomSequence.unresolved ? `${formatNumber(randomSequence.unresolved)} unresolved` : "",
        summarizeCounts(randomSequence.modes),
        summarizeCounts(randomSequence.randomModes),
        summarizeCounts(randomSequence.transitions),
        summarizeCounts(randomSequence.statuses),
        summarizeCounts(randomSequence.memberships),
      ].filter(Boolean).join(" / "));
      values.push([
        `Playlists: ${formatNumber(randomSequence.playlistItems)} weighted items`,
        randomSequence.orderDiffers ? `${formatNumber(randomSequence.orderDiffers)} playlist orders differ from Children` : "",
        randomSequence.duplicateItems ? `${formatNumber(randomSequence.duplicateItems)} repeated playlist items` : "",
        randomSequence.emptyPlaylists ? `${formatNumber(randomSequence.emptyPlaylists)} empty playlists with owned Children preserved` : "",
        randomSequence.ownedNotInPlaylist ? `${formatNumber(randomSequence.ownedNotInPlaylist)} owned Children not referenced by the playlist` : "",
        randomSequence.nonDefaultWeightItems ? `${formatNumber(randomSequence.nonDefaultWeightItems)} non-default weights across ${formatNumber(randomSequence.nonDefaultWeightNodes)} nodes` : "",
        randomSequence.nonUniformWeightNodes ? `${formatNumber(randomSequence.nonUniformWeightNodes)} non-uniform pools` : "",
        randomSequence.nonDefaultAvoid ? `${formatNumber(randomSequence.nonDefaultAvoid)} non-default avoid-repeat nodes (max ${formatNumber(randomSequence.maxAvoid)})` : "",
        randomSequence.nonDefaultLoop ? `${formatNumber(randomSequence.nonDefaultLoop)} non-default loop nodes` : "",
        randomSequence.globalScope ? `${formatNumber(randomSequence.globalScope)} global-scope nodes` : "",
        randomSequence.continuous ? `${formatNumber(randomSequence.continuous)} continuous nodes` : "",
        randomSequence.resetPlaylist ? `${formatNumber(randomSequence.resetPlaylist)} reset-on-play nodes` : "",
      ].filter(Boolean).join(" / "));
      values.push("Reciprocal Children prove container ownership; playlist rows prove selector membership and may repeat, omit, or leave the owned set empty. Runtime random seed, shuffle history, avoid-repeat history, Sequence cursor, and reset timing were not observed; playlist rows describe policy, not a selected leaf.");
    }
    if (layerBlend.nodes) {
      const summarizeCounts = (counts) => [...counts]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      const rtpcIds = [...layerBlend.rtpcIds];
      values.push([
        `Wwise Layer/Blend structure: ${formatNumber(layerBlend.nodes)} nodes`,
        `${formatNumber(layerBlend.exact)} typed exact`,
        layerBlend.unresolved ? `${formatNumber(layerBlend.unresolved)} unresolved` : "",
        summarizeCounts(layerBlend.assignments),
        summarizeCounts(layerBlend.proof),
        summarizeCounts(layerBlend.statuses),
      ].filter(Boolean).join(" / "));
      values.push([
        `Layer curves: ${formatNumber(layerBlend.definitions)} layers`,
        `${formatNumber(layerBlend.associations)} child associations`,
        `${formatNumber(layerBlend.points)} curve points`,
        layerBlend.initialCurves ? `${formatNumber(layerBlend.initialCurves)} initial RTPC curves` : "",
        layerBlend.continuous ? `${formatNumber(layerBlend.continuous)} continuous-validation nodes` : "",
        summarizeCounts(layerBlend.rtpcTypes),
        layerBlend.outsideChildren ? `${formatNumber(layerBlend.outsideChildren)} associations outside Children` : "",
      ].filter(Boolean).join(" / "));
      if (rtpcIds.length) {
        values.push(`Layer RTPC ids: ${rtpcIds.slice(0, 12).join(" / ")}${layerBlend.rtpcIdsTruncated || rtpcIds.length > 12 ? " / more omitted" : ""}`);
      }
      values.push("Layer curves prove authored RTPC-driven blend/crossfade policy. The live RTPC value, per-child gain, audible layers, and selected media were not observed; zero-layer assignments remain structural child relations only.");
    }
    if (initialRtpcActionJoins) {
      values.push(`Initial RTPC same-ID joins: ${formatNumber(initialRtpcActionJoins)} action${initialRtpcActionJoins === 1 ? "" : "s"} -> authored curve target`);
    }
    if (postProcess.effectSlots || postProcess.outputBusNodes || postProcess.metadataSlots || postProcess.authoredAuxFlagNodes || postProcess.authoredPropertyValues || postProcess.authoredRangedPropertyValues || postProcess.stateRtpcNodes) {
      const counted = (items) => [...items]
        .map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`)
        .join(" / ");
      values.push([
        `Wwise direct processing: ${formatNumber(postProcess.parsedNodes)} nodes`,
        `${formatNumber(postProcess.effectNodes)} nodes with ${formatNumber(postProcess.effectSlots)} effect slots`,
        `${formatNumber(postProcess.effectReferences)} plug-in references`,
        postProcess.effectBypassSlots ? `${formatNumber(postProcess.effectBypassSlots)} effect bypass bits` : "",
        postProcess.effectShareSetSlots ? `${formatNumber(postProcess.effectShareSetSlots)} effect ShareSet bits` : "",
        postProcess.effectRenderedSlots ? `${formatNumber(postProcess.effectRenderedSlots)} effect rendered bits` : "",
        postProcess.effectUnknownFlagBits ? `${formatNumber(postProcess.effectUnknownFlagBits)} effect slots with unknown flag bits` : "",
        postProcess.emptySlots ? `${formatNumber(postProcess.emptySlots)} empty slots` : "",
        postProcess.metadataSlots ? `${formatNumber(postProcess.metadataSlots)} metadata slots` : "",
        `${formatNumber(postProcess.outputBusNodes)} explicit output-bus routes`,
        postProcess.authoredAuxFlagNodes ? `${formatNumber(postProcess.authoredAuxFlagNodes)} nodes with authored Aux flags` : "",
        postProcess.gameDefinedUseNodes ? `${formatNumber(postProcess.gameDefinedUseNodes)} Game-Defined send use bits` : "",
        postProcess.userDefinedReferences ? `${formatNumber(postProcess.userDefinedReferences)} User-Defined Aux Bus references` : "",
        postProcess.reflectionsReferences ? `${formatNumber(postProcess.reflectionsReferences)} Early Reflections Aux Bus references` : "",
        postProcess.failedAuxNodes ? `${formatNumber(postProcess.failedAuxNodes)} Aux parsers failed closed` : "",
        postProcess.authoredPropertyValues ? `${formatNumber(postProcess.authoredPropertyValues)} authored base property values` : "",
        postProcess.authoredRangedPropertyValues ? `${formatNumber(postProcess.authoredRangedPropertyValues)} authored base property ranges` : "",
        postProcess.stateRtpcNodes ? `${formatNumber(postProcess.stateRtpcNodes)} nodes with State/RTPC control` : "",
        postProcess.stateGroupReferences ? `${formatNumber(postProcess.stateGroupReferences)} State Group references / ${formatNumber(postProcess.stateValues)} values` : "",
        postProcess.rtpcCurves ? `${formatNumber(postProcess.rtpcCurves)} Initial RTPC curves / ${formatNumber(postProcess.rtpcPoints)} points` : "",
        postProcess.failedStateRtpcNodes ? `${formatNumber(postProcess.failedStateRtpcNodes)} State/RTPC parsers failed closed` : "",
      ].filter(Boolean).join(" / "));
      if (postProcess.plugins.size) values.push(`DSP plug-ins: ${counted(postProcess.plugins)}`);
      if (postProcess.decodedParameterReferences) values.push(
        `Decoded authored DSP settings: ${formatNumber(postProcess.decodedParameterReferences)} references`
        + (postProcess.partialParameterReferences
          ? ` / ${formatNumber(postProcess.exactParameterReferences)} exact semantics / ${formatNumber(postProcess.partialParameterReferences)} partial semantics`
          : "")
        + ` / ${counted(postProcess.parameterSchemas)}`
      );
      if (postProcess.resolutions.size) values.push(`Effect definition resolution: ${counted(postProcess.resolutions)}`);
      const busRows = [...postProcess.buses].slice(0, 16).map(([busId, bus]) => {
        const path = bus.path.length ? bus.path : [busId];
        const chain = path.map((pathId) => {
          const definition = busDefinitions.get(normalize(pathId).toLowerCase());
          if (!definition) return pathId;
          const effects = asArray(definition.effects).map((slot) => [
            `slot ${slot.slotIndex ?? slot.ordinal ?? "?"}`,
            slot.pluginName || slot.pluginClassIdHex || slot.effectIdHex || "effect",
            slot.parameterSummary || "",
          ].filter(Boolean).join(" / "));
          const details = [
            humanize(definition.objectTypeLabel || "bus"),
            effects.length ? effects.join("; ") : "",
            ["nonEmptyEffectChunkNotLocated", "ambiguousCrossCorrelatedEffectChunks"].includes(definition.effectParserStatus) ? "effect list unresolved" : "",
            definition.effectParserStatus === "exactTypedV150EffectChunkWithUnresolvedReferences" ? "effect reference unresolved" : "",
            ["exactCrossCorrelatedEmptyEffectChunk", "exactTypedV150EmptyEffectChunk"].includes(definition.effectParserStatus) ? "serialized effect list empty" : "",
            definition.serializedDuckCount ? `${formatNumber(definition.serializedDuckCount)} authored duck(s)` : "",
          ].filter(Boolean);
          return details.length ? `${pathId} [${details.join(" / ")}]` : pathId;
        }).join(" → ");
        return `${formatNumber(bus.count)} nodes / ${chain} / ${humanize(bus.pathStatus || bus.status || "unknown")}`;
      });
      if (busRows.length) values.push(`Output buses: ${busRows.join(" / ")}${postProcess.buses.size > 16 ? " / more omitted" : ""}`);
      const auxBusRows = [...postProcess.auxiliaryBuses.values()].slice(0, 16).map((bus) => {
        const path = bus.path.length ? bus.path : [bus.busId];
        const chain = path.map((pathId) => {
          const definition = busDefinitions.get(normalize(pathId).toLowerCase());
          if (!definition) return pathId;
          const effects = asArray(definition.effects).map((slot) => [
            `slot ${slot.slotIndex ?? slot.ordinal ?? "?"}`,
            slot.pluginName || slot.pluginClassIdHex || slot.effectIdHex || "effect",
            slot.parameterSummary || "",
          ].filter(Boolean).join(" / "));
          const details = [
            humanize(definition.objectTypeLabel || "bus"),
            effects.length ? effects.join("; ") : "",
            ["nonEmptyEffectChunkNotLocated", "ambiguousCrossCorrelatedEffectChunks"].includes(definition.effectParserStatus) ? "effect list unresolved" : "",
            definition.effectParserStatus === "exactTypedV150EffectChunkWithUnresolvedReferences" ? "effect reference unresolved" : "",
            ["exactCrossCorrelatedEmptyEffectChunk", "exactTypedV150EmptyEffectChunk"].includes(definition.effectParserStatus) ? "serialized effect list empty" : "",
            definition.serializedDuckCount ? `${formatNumber(definition.serializedDuckCount)} authored duck(s)` : "",
          ].filter(Boolean);
          return details.length ? `${pathId} [${details.join(" / ")}]` : pathId;
        }).join(" -> ");
        return `${humanize(bus.sendKind)} x ${formatNumber(bus.count)} / ${chain} / ${humanize(bus.pathStatus || bus.status || "unknown")}`;
      });
      if (auxBusRows.length) values.push(`Serialized Auxiliary Send slots: ${auxBusRows.join(" / ")}${postProcess.auxiliaryBuses.size > 16 ? " / more omitted" : ""}`);
      if (postProcess.gameDefinedUseNodes) values.push("Game-Defined send enablement is authored here; the runtime assigns Aux Bus IDs, listeners, and control values, so no static wet path is invented.");
      if (postProcess.propertyCounts.size) values.push(`Authored base properties: ${counted(postProcess.propertyCounts)}`);
      if (postProcess.rangedPropertyCounts.size) values.push(`Authored base property ranges: ${counted(postProcess.rangedPropertyCounts)}`);
      const formatPropertyValue = (prop) => {
        const label = prop.propertyLabel || prop.propertyIdHex || `property ${prop.propertyId ?? "?"}`;
        const floatValue = prop.floatValue;
        const value = String(prop.valueEncoding || "").startsWith("u32")
          ? `${prop.rawU32 ?? "?"}${prop.valueEncoding === "u32Id" && prop.rawHex ? ` (${prop.rawHex})` : ""}`
          : floatValue !== null && floatValue !== undefined && Number.isFinite(Number(floatValue))
            ? Number(floatValue).toPrecision(7).replace(/\.?0+$/, "")
            : prop.rawHex || prop.rawU32 || "?";
        return `${label} ${value}`;
      };
      const formatPropertyRange = (prop) => {
        const label = prop.propertyLabel || prop.propertyIdHex || `property ${prop.propertyId ?? "?"}`;
        const minimum = prop.minimumFloat !== null && prop.minimumFloat !== undefined && Number.isFinite(Number(prop.minimumFloat))
          ? Number(prop.minimumFloat).toPrecision(7).replace(/\.?0+$/, "")
          : prop.minimumRawHex || "?";
        const maximum = prop.maximumFloat !== null && prop.maximumFloat !== undefined && Number.isFinite(Number(prop.maximumFloat))
          ? Number(prop.maximumFloat).toPrecision(7).replace(/\.?0+$/, "")
          : prop.maximumRawHex || "?";
        return `${label} ${minimum}..${maximum}`;
      };
      for (const node of postProcess.propertyRows.slice(0, 20)) {
        const properties = asArray(node.properties).map(formatPropertyValue);
        const ranges = asArray(node.rangedProperties).map(formatPropertyRange);
        values.push([
          `Base-property node ${node.objectId ?? "?"} (${humanize(node.objectTypeLabel || `type ${node.objectType ?? "?"}`)})`,
          properties.length ? properties.join(", ") : "",
          ranges.length ? `ranges ${ranges.join(", ")}` : "",
        ].filter(Boolean).join(" / "));
      }
      if (postProcess.propertyRows.length > 20) values.push(`${formatNumber(postProcess.propertyRows.length - 20)} more base-property nodes omitted from this compact view.`);
      for (const node of postProcess.auxRows.slice(0, 20)) {
        const sends = asArray(node.userDefinedAuxSends).map((send) => `slot ${send.slotIndex ?? "?"} -> ${send.busIdHex || send.busId}`).join("; ");
        values.push([
          `Aux node ${node.objectId ?? "?"} (${humanize(node.objectTypeLabel || `type ${node.objectType ?? "?"}`)})`,
          `flags 0x${Number(node.auxFlagsRaw || 0).toString(16).padStart(2, "0")}`,
          node.overrideUserDefinedAuxSends ? "User-Defined override bit on" : "User-Defined override bit off",
          sends || "no populated User-Defined slots",
          node.useGameDefinedAuxSends ? "Game-Defined sends enabled (runtime target)" : "",
          node.overrideEarlyReflectionsAuxBus ? "override Early Reflections bus" : "",
        ].filter(Boolean).join(" / "));
      }
      if (postProcess.auxRows.length > 20) values.push(`${formatNumber(postProcess.auxRows.length - 20)} more Aux nodes omitted from this compact view.`);
      if (postProcess.stateRtpcNodes) {
        const selectorGroups = new Map(asArray(state.index?.controlCatalog?.wwiseSelectorGroups)
          .filter((row) => row && typeof row === "object" && row.groupIdHex)
          .map((row) => [normalize(row.groupIdHex).toLowerCase(), row]));
        const knownRtpcNames = new Map();
        const fnv1Hex = (name) => {
          let hash = 0x811c9dc5;
          for (const character of String(name || "").toLowerCase()) {
            const code = character.codePointAt(0);
            if (code > 0x7f) return "";
            hash = Math.imul(hash, 0x01000193) >>> 0;
            hash = (hash ^ code) >>> 0;
          }
          return `0x${hash.toString(16).padStart(8, "0")}`;
        };
        for (const key of ["rtpcParameters", "physicsAudioRtpcParameters", "modelViewStateRtpcParameters"]) {
          for (const row of asArray(state.index?.controlCatalog?.[key])) {
            const name = normalize(row?.parameterName);
            const hash = fnv1Hex(name);
            if (!name || !hash) continue;
            if (!knownRtpcNames.has(hash)) knownRtpcNames.set(hash, name);
            else if (knownRtpcNames.get(hash) !== name) knownRtpcNames.set(hash, "");
          }
        }
        const stateGroupRows = [...postProcess.stateGroups].slice(0, 16).map(([groupId, group]) => {
          const catalog = selectorGroups.get(normalize(groupId).toLowerCase());
          return [
            groupId,
            catalog?.semanticLabel || humanize(catalog?.semanticRole || ""),
            `${formatNumber(group.nodeCount)} nodes`,
            `${formatNumber(group.valueCount)} property values`,
          ].filter(Boolean).join(" / ");
        });
        if (stateGroupRows.length) values.push(`State Groups: ${stateGroupRows.join("; ")}${postProcess.stateGroups.size > 16 ? "; more omitted" : ""}`);
        const rtpcRows = [...postProcess.rtpcIds].slice(0, 20).map(([rtpcId, count]) => {
          const name = knownRtpcNames.get(normalize(rtpcId).toLowerCase());
          return `${rtpcId}${name ? ` (${name})` : ""} / ${formatNumber(count)} curves`;
        });
        if (rtpcRows.length) values.push(`Initial RTPC IDs: ${rtpcRows.join("; ")}${postProcess.rtpcIds.size > 20 ? "; more omitted" : ""}`);
        if (postProcess.rtpcTypes.size) values.push(`Initial RTPC control types: ${counted(postProcess.rtpcTypes)}`);
        if (postProcess.rtpcParameters.size) values.push(`RTPC-controlled properties: ${counted(postProcess.rtpcParameters)}`);
        for (const node of postProcess.stateRtpcRows.slice(0, 20)) {
          const groupDetails = asArray(node.stateGroups).map((group) => {
            const groupId = normalize(group.groupIdHex || group.groupId || "unknown");
            const catalog = selectorGroups.get(groupId.toLowerCase());
            const valueNames = new Map(asArray(catalog?.values)
              .filter((row) => row && typeof row === "object" && row.valueIdHex)
              .map((row) => [normalize(row.valueIdHex).toLowerCase(), row.semanticName || row.semanticNameStatus || ""]));
            const states = asArray(group.states).map((stateRow) => {
              const stateId = normalize(stateRow.stateIdHex || stateRow.stateId || "unknown");
              const stateName = valueNames.get(stateId.toLowerCase());
              const properties = asArray(stateRow.values).map((entry) => `${rtpcParameterText(entry)} ${Number(entry.value).toPrecision(6).replace(/\.?0+$/, "")}`).join(", ");
              return `${stateId}${stateName ? ` (${stateName})` : ""}: ${properties || "no property values"}`;
            });
            return `${groupId}${catalog?.semanticLabel ? ` (${catalog.semanticLabel})` : ""} / ${humanize(group.syncTypeLabel || "unknown sync")} / ${states.join("; ") || "no active state rows"}`;
          });
          const curves = asArray(node.rtpcCurves).map((curve) => {
            const rtpcId = normalize(curve.rtpcIdHex || curve.rtpcId || "unknown");
            const name = knownRtpcNames.get(rtpcId.toLowerCase());
            const points = asArray(curve.points).map((point) => `${Number(point.from).toPrecision(6).replace(/\.?0+$/, "")} -> ${Number(point.to).toPrecision(6).replace(/\.?0+$/, "")} ${humanize(point.interpolationLabel || "")}`).join(", ");
            return `${rtpcId}${name ? ` (${name})` : ""} / ${humanize(curve.rtpcTypeLabel || "unknown")} / ${rtpcParameterText(curve)} / ${humanize(curve.accumLabel || "unknown")} / ${humanize(curve.scalingLabel || "none")} / ${points}`;
          });
          values.push([
            `State/RTPC node ${node.objectId ?? "?"} (${humanize(node.objectTypeLabel || `type ${node.objectType ?? "?"}`)})`,
            groupDetails.length ? `State ${groupDetails.join(" | ")}` : "",
            curves.length ? `RTPC ${curves.join(" | ")}` : "",
          ].filter(Boolean).join(": "));
        }
        if (postProcess.stateRtpcRows.length > 20) values.push(`${formatNumber(postProcess.stateRtpcRows.length - 20)} more State/RTPC nodes omitted from this compact view.`);
        values.push("State and RTPC rows are authored control policy. Live values, inherited effective properties, effect bypass, and audibility were not observed.");
      }
      for (const node of postProcess.effectRows.slice(0, 20)) {
        const slots = asArray(node.effects).map((slot) => {
          const pluginMedia = asArray(slot.pluginMediaDependencies)
            .map((row) => `${row.mediaIdHex || row.mediaId} (${humanize(row.semanticRole || "plugin media")})`)
            .join(" + ");
          const nativeTuning = [
            ...asArray(slot.parameterValues?.internalTuningParameters),
            ...asArray(slot.parameterValues?.unresolvedParameters),
          ]
            .filter((row, index, rows) => row && row.nativeUseRole
              && rows.findIndex((candidate) => candidate === row) === index)
            .map((row) => {
              const value = Number.isFinite(Number(row.value))
                ? Number(row.value).toPrecision(6).replace(/\.?0+$/, "")
                : row.value ?? (row.rawCode !== undefined ? `0x${Number(row.rawCode).toString(16)}` : "?");
              const consumers = asArray(row.nativeConsumerRvas).join(", ");
              const setParam = row.setParamId === null || row.setParamId === undefined
                ? `byte ${row.serializedOffset ?? "?"}`
                : `SetParam ${row.setParamId}`;
              const nativeOffset = row.nativeStructOffset !== undefined
                ? ` native +0x${Number(row.nativeStructOffset).toString(16)}`
                : "";
              const wrapperOffset = row.wrapperOffset !== undefined
                ? ` wrapper +0x${Number(row.wrapperOffset).toString(16)}`
                : "";
              const status = row.nativeUseStatus && row.nativeUseStatus !== "exactNativeUseRolePublicNameUnresolved"
                ? ` / ${humanize(row.nativeUseStatus)}`
                : "";
              const detail = row.nativeUseDetail ? ` — ${row.nativeUseDetail}` : "";
              return `${setParam}=${value}${nativeOffset}${wrapperOffset}: ${humanize(row.nativeUseRole)}${status}`
                + (consumers ? ` (${consumers})` : "")
                + detail;
            })
            .join("; ");
          return [
            `slot ${slot.slotIndex ?? slot.ordinal ?? "?"}`,
            slot.pluginName || slot.pluginClassIdHex || slot.effectIdHex || "empty",
            humanize(slot.objectTypeLabel || slot.resolutionStatus || "unknown"),
            slot.parameterByteLength !== undefined ? `${formatNumber(slot.parameterByteLength)} parameter bytes` : "",
            slot.parameterSummary || "",
            pluginMedia ? `plug-in media ${pluginMedia}` : "",
            nativeTuning ? `native tuning ${nativeTuning}` : "",
            slot.effectBypass !== undefined ? `bypass ${slot.effectBypass ? "on" : "off"}` : "",
            slot.effectShareSet !== undefined ? (slot.effectShareSet ? "ShareSet" : "custom/inline") : "",
            slot.effectRendered !== undefined && slot.effectRendered !== null ? `rendered ${slot.effectRendered ? "on" : "off"}` : "",
            slot.unknownFlagBits ? `unknown flag bits 0x${Number(slot.unknownFlagBits).toString(16)}` : "",
            `flags ${slot.flagsRaw ?? "?"}`,
          ].filter(Boolean).join(" / ");
        });
        values.push(`Node ${node.objectId ?? "?"} (${humanize(node.objectTypeLabel || `type ${node.objectType ?? "?"}`)}): ${slots.join("; ")}`);
      }
      if (postProcess.effectRows.length > 20) values.push(`${formatNumber(postProcess.effectRows.length - 20)} more effect nodes omitted from this compact view.`);
      for (const boundary of postProcess.boundaries) values.push(boundary);
    }
    for (const detail of actionDetails) values.push(detail);
    for (const [kind, value] of musicNodes) {
      const detail = [
        `${formatNumber(value.count)} nodes`,
        value.children ? `${formatNumber(value.children)} children` : "",
        value.sources ? `${formatNumber(value.sources)} sources` : "",
        value.selectionTypes.size ? [...value.selectionTypes].join(" / ") : "",
        [...value.structureStatuses].map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`).join(" / "),
        [...value.selectorStatuses].map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`).join(" / "),
        value.ownedNotSelected ? `${formatNumber(value.ownedNotSelected)} owned Children outside selector membership` : "",
        value.recursiveOwned ? `${formatNumber(value.recursiveOwned)} selector leaves are recursively owned descendants` : "",
        value.unboundLeaves ? `${formatNumber(value.unboundLeaves)} explicit zero/unbound leaves` : "",
        value.unresolvedLeafObjects ? `${formatNumber(value.unresolvedLeafObjects)} selector leaves have unresolved object ownership` : "",
      ].filter(Boolean).join(" / ");
      values.push(`${taxonomyLabel(kind)}: ${detail}`);
    }
    if (unresolved) values.push(`${t("relationPartialGraph")}: ${formatNumber(unresolved)} unresolved nodes`);
    return values;
  }

  function sourceEvidenceSummary(record) {
    const sourceKinds = new Map();
    const plugins = new Map();
    const streamTypes = new Map();
    const flags = new Map();
    let references = 0;
    let objects = 0;
    let decoded = 0;
    let unresolvedCodec = 0;
    const nonMediaSources = [];
    for (const evidence of asArray(record?.evidence)) {
      const summary = evidence?.sourceObjectSummary;
      if (!summary || typeof summary !== "object") continue;
      references += Number(summary.sourceReferenceCount || 0);
      objects += Number(summary.uniqueSourceObjectCount || 0);
      decoded += Number(summary.decodedCodecSourceCount || 0);
      unresolvedCodec += Number(summary.unresolvedCodecSourceCount || 0);
      for (const [key, count] of Object.entries(summary.sourceKindCounts || {})) sourceKinds.set(key, (sourceKinds.get(key) || 0) + Number(count || 0));
      for (const [key, count] of Object.entries(summary.pluginCounts || {})) plugins.set(key, (plugins.get(key) || 0) + Number(count || 0));
      for (const [key, count] of Object.entries(summary.streamTypeCounts || {})) streamTypes.set(key, (streamTypes.get(key) || 0) + Number(count || 0));
      for (const [key, count] of Object.entries(summary.sourceFlagCounts || {})) flags.set(key, (flags.get(key) || 0) + Number(count || 0));
      for (const source of asArray(evidence?.nonMediaSourceEvidence)) if (source && typeof source === "object") nonMediaSources.push(source);
    }
    if (!references && !nonMediaSources.length) return [];
    const counted = (values) => [...values].map(([key, count]) => `${humanize(key)} ${formatNumber(count)}`).join(" / ");
    const rows = [
      `AkBankSourceData: ${formatNumber(references)} routed references / ${formatNumber(objects)} source objects / ${counted(sourceKinds)}`,
      `Source plugins: ${counted(plugins)} / buffering ${counted(streamTypes)}${flags.size ? ` / flags ${counted(flags)}` : ""}`,
      `Codec resolution: ${formatNumber(decoded)} decoded-index matches / ${formatNumber(unresolvedCodec)} unresolved codec sources`,
    ];
    for (const source of nonMediaSources.slice(0, 16)) {
      rows.push([
        source.pluginName || source.pluginIdHex || "unknown plugin",
        humanize(source.sourceKind || "unknown"),
        `source ${source.sourceId ?? "?"}`,
        humanize(source.streamTypeLabel || "unknown buffering"),
        humanize(source.mediaLocationStatus || "unknown location"),
        `object ${source.objectId ?? "?"}`,
      ].join(" / "));
    }
    if (nonMediaSources.length > 16) rows.push(`${formatNumber(nonMediaSources.length - 16)} more non-media source records omitted from this compact view.`);
    rows.push("External Source and synthesized plugin records prove a Wwise playback source, not a fixed recoverable WEM. Stream type is a buffering policy, not a physical PCK location; runtime instantiation and audibility were not observed.");
    return rows;
  }

  function customFootstepParameterSummary(record) {
    return asArray(record?.customFootstepParameterVariants)
      .filter((variant) => variant && typeof variant === "object")
      .map((variant) => {
        const fields = [
          `${formatNumber(variant.occurrenceCount || 0)} callbacks`,
          `raw int ${variant.rawInt ?? "?"}`,
          `raw float ${variant.rawFloat ?? "?"}`,
          `foot ${variant.footSide || "?"}`,
          `VFX ${variant.vfxType || "?"}`,
          `filter ${variant.playbackFilter || "?"}`,
          variant.customWeightThreshold !== null && variant.customWeightThreshold !== undefined
            ? `custom weight >= ${variant.customWeightThreshold}`
            : "float inactive for playback filter",
          `VFX weight >= ${variant.runtimeVfxWeightThreshold ?? 0.5}`,
        ];
        if (variant.decodeStatus && variant.decodeStatus !== "exactCurrentBuild") fields.push(humanize(variant.decodeStatus));
        return fields.join(" / ");
      });
  }

  function customFootstepRuntimeSummary() {
    const model = state.index?.customFootstepModel;
    if (!model || typeof model !== "object") return [];
    const corpus = model.corpus || {};
    const values = [
      `${formatNumber(corpus.occurrenceCount || 0)} callbacks / ${formatNumber(corpus.eventCount || 0)} canonical Events / ${formatNumber(corpus.parameterVariantCount || 0)} raw parameter variants`,
    ];
    for (const anchor of asArray(model.nativeAnchors)) {
      if (!anchor || typeof anchor !== "object") continue;
      values.push(`${anchor.type || "native"}.${anchor.method || "?"} ${anchor.token || ""} @ ${anchor.virtualAddress || "?"}`.trim());
    }
    return values;
  }

  function mediaPostProcessEffectSummary(raw) {
    const ids = asArray(raw?.postProcessEffectBusIds).map((value) => normalize(value).toLowerCase()).filter(Boolean);
    if (!ids.length) return [];
    const definitions = new Map(asArray(state.index?.hircSummary?.postProcessSummary?.busDefinitions)
      .filter((row) => row && typeof row === "object")
      .map((row) => [normalize(row.busIdHex || row.busId).toLowerCase(), row]));
    const rows = [];
    const seen = new Set();
    for (const id of ids) {
      const definition = definitions.get(id);
      for (const slot of asArray(definition?.effects)) {
        if (!slot || typeof slot !== "object") continue;
        const label = [
          id,
          `slot ${slot.slotIndex ?? "?"}`,
          slot.pluginName || slot.pluginClassIdHex || slot.effectIdHex || "effect",
          slot.parameterSummary || "authored parameters unavailable",
        ].join(" / ");
        if (!seen.has(label)) {
          seen.add(label);
          rows.push(label);
        }
      }
    }
    return rows;
  }

  function mediaPostProcessDirectEffectSummary(raw) {
    return asArray(raw?.postProcessDirectEffects)
      .filter((row) => row && typeof row === "object")
      .map((row) => [
        row.effectIdHex || "effect",
        row.pluginName || row.pluginClassIdHex || "plugin",
        row.slotIndex !== undefined ? `slot ${row.slotIndex}` : "",
        row.objectId !== undefined ? `node ${row.objectId}` : "",
        row.effectBypass !== undefined ? `bypass ${row.effectBypass ? "on" : "off"}` : "",
        row.effectShareSet !== undefined ? `ShareSet ${row.effectShareSet ? "on" : "off"}` : "",
        row.effectRendered !== undefined ? `rendered ${row.effectRendered ? "on" : "off"}` : "",
        row.parameterSummary || "authored parameters unavailable",
      ].filter(Boolean).join(" / "));
  }

  function mediaPostProcessEffectChainSummary(raw) {
    const definitions = new Map(asArray(state.index?.hircSummary?.postProcessSummary?.busDefinitions)
      .filter((row) => row && typeof row === "object")
      .map((row) => [normalize(row.busIdHex || row.busId).toLowerCase(), row]));
    return asArray(raw?.postProcessEffectChain)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const busSlot = row.stage === "bus"
          ? asArray(definitions.get(normalize(row.busIdHex).toLowerCase())?.effects)
            .find((slot) => slot && typeof slot === "object"
              && (row.slotIndex === undefined || Number(slot.slotIndex) === Number(row.slotIndex))
              && (!row.effectIdHex || normalize(slot.effectIdHex).toLowerCase() === normalize(row.effectIdHex).toLowerCase()))
          : null;
        const effect = busSlot || row;
        return [
          row.stage === "bus" ? "Bus" : "direct node",
          row.stage === "bus" ? (row.busIdHex || "bus") : (row.objectId !== undefined ? `node ${row.objectId}` : "node"),
          row.stage === "bus" && row.pathDepth !== undefined ? `depth ${row.pathDepth}` : "",
          row.slotIndex !== undefined ? `slot ${row.slotIndex}` : "",
          effect.pluginName || effect.pluginClassIdHex || row.effectIdHex || "effect",
          effect.effectBypass !== undefined ? `bypass ${effect.effectBypass ? "on" : "off"}` : "",
          effect.effectShareSet !== undefined ? `ShareSet ${effect.effectShareSet ? "on" : "off"}` : "",
          effect.effectRendered !== undefined ? `rendered ${effect.effectRendered ? "on" : "off"}` : "",
          effect.parameterSummary || "authored parameters in Bus catalog",
        ].filter(Boolean).join(" / ");
      });
  }

  function mediaPostProcessBusControlSummary(raw) {
    const definitions = new Map(asArray(state.index?.hircSummary?.postProcessSummary?.busDefinitions)
      .filter((row) => row && typeof row === "object")
      .map((row) => [normalize(row.busIdHex || row.busId).toLowerCase(), row]));
    return asArray(raw?.postProcessBusControls)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const pathIndexes = asArray(row.pathIndexes).map((value) => `#${value}`).join(", ");
        const pathDepths = asArray(row.pathDepths).map((value) => `d${value}`).join(", ");
        const definitionCurves = asArray(definitions.get(normalize(row.busIdHex).toLowerCase())
          ?.serializedStateAndRtpc?.rtpcCurves);
        const rtpc = (definitionCurves.length ? definitionCurves : asArray(row.rtpcIds).map((id) => ({ rtpcIdHex: id }))).map((curve) => [
          curve.rtpcIdHex || "RTPC",
          rtpcParameterText(curve),
          `${formatNumber(curve.pointCount || 0)}pt`,
        ].filter(Boolean).join(" ")).join(", ");
        const states = asArray(row.stateControls).map((state) => [
          state.groupIdHex || "group",
          state.stateIdHex || "state",
          rtpcParameterText(state),
          state.value !== undefined && state.value !== null ? String(state.value) : "",
        ].filter(Boolean).join(" ")).join(", ");
        return [
          row.busIdHex || "bus",
          pathIndexes ? `paths ${pathIndexes}` : "",
          pathDepths ? `depths ${pathDepths}` : "",
          row.rtpcCurveCount ? `RTPC ${formatNumber(row.rtpcCurveCount)} / ${formatNumber(row.rtpcPointCount || 0)}pt` : "",
          rtpc ? `[${rtpc}${row.rtpcControlsTruncated ? ", ..." : ""}]` : "",
          row.stateGroupCount ? `State ${formatNumber(row.stateGroupCount)} groups / ${formatNumber(row.stateValueCount || 0)} values` : "",
          states ? `[${states}${row.stateControlsTruncated ? ", ..." : ""}]` : "",
        ].filter(Boolean).join(" / ");
      });
  }

  function mediaPostProcessBusDuckSummary(raw) {
    return asArray(raw?.postProcessBusDucks)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const pathIndexes = asArray(row.pathIndexes).map((value) => `#${value}`).join(", ");
        const pathDepths = asArray(row.pathDepths).map((value) => `d${value}`).join(", ");
        const ducks = asArray(row.ducks).map((duck) => [
          duck.targetBusIdHex || "target bus",
          duck.duckVolumeDb !== undefined ? `${duck.duckVolumeDb} dB` : "",
          duck.targetPropertyLabel || duck.targetPropertyIdHex || "",
          duck.fadeOutMs !== undefined || duck.fadeInMs !== undefined
            ? `fade ${duck.fadeOutMs ?? "?"}/${duck.fadeInMs ?? "?"} ms`
            : "",
          duck.fadeCurve !== undefined ? `curve ${duck.fadeCurve}` : "",
        ].filter(Boolean).join(" ")).join(", ");
        return [
          row.busIdHex || "bus",
          pathIndexes ? `paths ${pathIndexes}` : "",
          pathDepths ? `depths ${pathDepths}` : "",
          `${formatNumber(row.duckCount || 0)} duck(s)`,
          row.maxDuckVolumeDb !== undefined ? `max ${row.maxDuckVolumeDb} dB` : "",
          ducks ? `[${ducks}${row.ducksTruncated ? ", ..." : ""}]` : "",
        ].filter(Boolean).join(" / ");
      });
  }

  function mediaPostProcessAuxSendSummary(raw) {
    return asArray(raw?.postProcessAuxSends)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const routes = asArray(row.busRoutes).map((route) => [
          asArray(route.busPathIdHexes).join(" -> "),
          asArray(route.effectBusIdHexes).length
            ? `effect ${asArray(route.effectBusIdHexes).join(",")}`
            : "",
          route.busPathResolutionStatus || route.resolutionStatus || "",
        ].filter(Boolean).join(" ")).join(", ");
        return [
          row.busIdHex || "Aux Bus",
          row.slotIndex !== undefined ? `slot ${row.slotIndex}` : "",
          row.sourceObjectCount ? `${formatNumber(row.sourceObjectCount)} source node(s)` : "",
          asArray(row.sourceObjectTypeLabels).join(", "),
          asArray(row.auxFlagsRawValues).length
            ? `flags ${asArray(row.auxFlagsRawValues).join(", ")}`
            : "",
          asArray(row.overrideUserDefinedAuxSends).length
            ? `override ${asArray(row.overrideUserDefinedAuxSends).join(", ")}`
            : "",
          asArray(row.useGameDefinedAuxSends).length
            ? `game-defined ${asArray(row.useGameDefinedAuxSends).join(", ")}`
            : "",
          asArray(row.serializationStatuses).join(", "),
          routes ? `route ${routes}` : "",
        ].filter(Boolean).join(" / ");
      });
  }

  function mediaPostProcessPropertySummary(raw) {
    return asArray(raw?.postProcessProperties)
      .filter((row) => row && typeof row === "object")
      .map((row) => [
        row.propertyLabel || row.propertyIdHex || "property",
        row.valueEncoding === "float" && row.floatValue !== undefined && row.floatValue !== null
          ? String(row.floatValue)
          : (row.rawHex || row.rawU32 || ""),
        row.valueEncoding || "",
        row.sourceOccurrenceCount ? `${formatNumber(row.sourceOccurrenceCount)} occurrence(s)` : "",
      ].filter(Boolean).join(" / "));
  }

  function mediaPostProcessRangeSummary(raw) {
    return asArray(raw?.postProcessRanges)
      .filter((row) => row && typeof row === "object")
      .map((row) => [
        row.propertyLabel || row.propertyIdHex || "range",
        `${row.minimumFloat ?? row.minimumRawHex ?? "?"}..${row.maximumFloat ?? row.maximumRawHex ?? "?"}`,
        row.valueEncoding || "",
        row.sourceOccurrenceCount ? `${formatNumber(row.sourceOccurrenceCount)} occurrence(s)` : "",
      ].filter(Boolean).join(" / "));
  }

  function mediaPostProcessRtpcSummary(raw) {
    return asArray(raw?.postProcessRtpcControls)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const points = asArray(row.points).map((point) => {
          if (!point || typeof point !== "object") return "";
          const from = point.from !== undefined ? Number(point.from).toPrecision(5) : "?";
          const to = point.to !== undefined ? Number(point.to).toPrecision(5) : "?";
          return `${point.pointIndex ?? "?"}: ${from}->${to}${point.interpolationLabel ? ` ${point.interpolationLabel}` : ""}`;
        }).filter(Boolean).join(", ");
        return [
          row.rtpcIdHex || "RTPC",
          row.objectTypeLabel || (row.objectId !== undefined ? `node ${row.objectId}` : "node"),
          row.objectId !== undefined ? `node ${row.objectId}` : "",
          rtpcParameterText(row),
          row.rtpcTypeLabel || "",
          row.accumLabel || "",
          row.scalingLabel || "",
          `${formatNumber(row.pointCount || 0)} pt${row.pointsTruncated ? " (points truncated)" : ""}`,
          points ? `[${points}]` : "",
        ].filter(Boolean).join(" / ");
      });
  }

  function mediaPostProcessStateSummary(raw) {
    return asArray(raw?.postProcessStateControls)
      .filter((row) => row && typeof row === "object")
      .map((row) => {
        const value = row.value !== undefined && row.value !== null
          ? Number(row.value).toPrecision(6).replace(/\.?0+$/, "")
          : "?";
        return [
          row.groupIdHex || "group",
          row.stateIdHex || "state",
          row.objectId !== undefined ? `node ${row.objectId}` : "",
          rtpcParameterText(row),
          value,
        ].filter(Boolean).join(" / ");
      });
  }

  function recordPanel(record) {
    const panel = document.createElement("section");
    panel.className = "audio-panel";
    const heading = document.createElement("h2");
    heading.textContent = t("details");
    panel.appendChild(heading);
    const raw = record.raw;
    const players = playableRecords(raw, record.kind);
    const playerSection = document.createElement("section");
    playerSection.style.marginTop = "14px";
    const playerHeading = document.createElement("h3");
    playerHeading.textContent = t("playableMedia");
    playerSection.appendChild(playerHeading);
    if (raw.detailShard && !raw._detailLoaded) {
      const note = document.createElement("p");
      note.className = "audio-detail-note";
      note.textContent = t("loadingEvents");
      playerSection.appendChild(note);
    } else if (players.length) renderPlayers(playerSection, players, { eager: record.kind === "media" });
    else {
      const note = document.createElement("p");
      note.className = "audio-detail-note";
      note.textContent = t("noPlayableMedia");
      playerSection.appendChild(note);
    }
    panel.appendChild(playerSection);
    panel.appendChild(manualNoteSection(record));
    const facts = record.kind === "events"
      ? [
          [t("recordType"), t(record.objectType)], [t("id"), raw.eventId ?? raw.id], [t("hash"), raw.eventHash ?? raw.hash], [t("eventType"), categoryLabel(record.category)],
          ["Category evidence", raw.categoryEvidence],
          ["Name category evidence", raw.categoryNameEvidence],
          ["Library resolution", humanize(raw.audioLibraryResolutionStatus || "")],
          ["Wwise playback role", humanize(raw.playbackRole || "")],
          ["Wwise Action operations", asArray(raw.wwiseActionOperations).map(humanize).join(" / ")],
          ["Wwise Action types", asArray(raw.wwiseActionOperationTypesHex).join(" / ")],
          [t("playbackLocation"), playbackLocationLabel(raw.playbackLocationStatus)],
          [t("purposeStatus"), humanize(raw.purposeKnowledgeStatus || "")],
          ["Event identity", humanize(raw.eventIdentityStatus || "")],
          ["Event name evidence", humanize(raw.eventNameEvidence || "")],
          ["Event name source", humanize(raw.eventNameSourceKind || "")],
          ["IL2CPP metadata field", raw.eventNameMetadataField],
          ["IL2CPP declaring type", raw.eventNameMetadataDeclaringType],
          ["IL2CPP field token", raw.eventNameMetadataFieldToken],
          ["Event collection sources", asArray(raw.eventNameCollectionSources).map(humanize).join(" / ")],
          ["Library output relation", humanize(raw.audioLibraryPlaybackTargetStatus || "")],
          ["Equivalent authored Events", asArray(raw.audioLibraryEquivalentEventIds).join(" / ")],
          ["Equivalent output categories", asArray(raw.audioLibraryEquivalentCategories).map(categoryLabel).join(" / ")],
          ["Library purpose boundary", humanize(raw.audioLibraryPurposeHintStatus || "")],
          ["Library media-leaf relation", humanize(raw.audioLibraryMediaLeafStatus || "")],
          ["Media-equivalent authored Events", asArray(raw.audioLibraryMediaEquivalentEventIds).join(" / ")],
          ["Media-equivalent categories", asArray(raw.audioLibraryMediaEquivalentCategories).map(categoryLabel).join(" / ")],
          ["Shared Wwise media IDs", asArray(raw.audioLibrarySharedMediaIds).join(" / ")],
          ["Media-leaf evidence boundary", humanize(raw.audioLibraryMediaPurposeHintStatus || "")],
          ["Identity-only placement", humanize(raw.identityOnlyPlaybackPlacementStatus || "")],
          ["Numeric skill IDs", asArray(raw.identityNumericSkillIds).join(" / ")],
          ["Authored Event hash", raw.authoredEventHashHex],
          [t("scannedBankSet"), raw.scannedBankPackageFingerprint
            ? `${formatNumber(raw.scannedBankPackageCount || 0)} PCK / ${String(raw.scannedBankPackageFingerprint).slice(0, 16)}…`
            : ""],
          [t("scope"), record.scope], [t("source"), record.source], [t("bank"), raw.bank ?? raw.sourceBank ?? raw.bankId ?? raw.evidence?.[0]?.bank],
          ["Wwise", raw.foundInWwise], [t("typedTraversal"), raw.traversalStatus], [t("playRoots"), raw.playRootCount],
          [t("possibleMedia"), raw.possibleMediaCount ?? raw.candidateCount], [t("uniqueContent"), raw.uniqueDecodedContentCount],
          [t("equivalentContent"), raw.contentEquivalentLeafCount], ["Runtime selection", raw.runtimeSelection], ["Contexts", raw.contextCount],
          ["Playable animation owners", raw.playableCharacterAnimationOwnerCount], ["Animation scope", raw.animationContextScope],
          ["Animation callbacks", asArray(raw.animationFunctions).join(" / ")],
        ]
      : [
          [t("recordType"), t(record.objectType)], [t("id"), raw.mediaId ?? raw.id], [t("mediaPurpose"), categoryLabel(record.category)],
          ["Semantic category evidence", raw.semanticCategoryEvidence],
          ["Trigger-context categories", asArray(raw.semanticCategoryContextCategories).map(categoryLabel).join(" / ")],
          ["Semantic field roles", asArray(raw.semanticCategoryFieldRoles).join(" / ")],
          [t("relatedEventTypes"), asArray(raw.relatedEventCategories).map(categoryLabel).join(" / ")], [t("scope"), record.scope],
          [t("source"), record.source], [t("path"), raw.rel ?? raw.path ?? raw.src], [t("format"), raw.format],
          [t("duration"), formatDuration(recordDuration(raw))], [t("bitrate"), formatBitrate(recordBitrate(raw))],
          [t("bytes"), raw.bytes !== undefined ? formatBytes(raw.bytes) : ""], [t("bank"), raw.bank ?? raw.sourceBank ?? raw.bankId],
          ["Library object", humanize(raw.audioLibraryObjectStatus || "")],
          ["Wwise Sound objects", asArray(raw.wwiseDefinitionEvidence).map((row) => row?.soundObjectId).filter((value) => value !== undefined).join(" / ")],
          [t("libraryBankEvent"), asArray(raw.audioLibraryBankEventIds).join(" / ")],
          ["Recovered external audio ID", raw.externalAuthoredAudioId],
          ["Recovered external path", raw.externalAuthoredPath],
          ["External identity evidence", humanize(raw.externalIdentityEvidence || "")],
          [t("radioTableLines"), raw.radioTableLineCount],
          [t("playbackLocation"), playbackLocationLabel(raw.playbackLocationStatus)],
          [t("storyLineBindings"), raw.storyLineBindingCount],
          [t("purposeStatus"), humanize(raw.purposeKnowledgeStatus || "")],
          [t("radioTriggerContextCoverage"), raw.radioTriggerContextCount !== undefined
            ? `${formatNumber(raw.radioTriggerContextStoredCount || 0)} stored / ${formatNumber(raw.radioTriggerContextCount || 0)} total${raw.radioTriggerContextsTruncated ? " / truncated" : ""}`
            : ""],
          [t("triggerContexts"), raw.triggerContextCount !== undefined
            ? `${formatNumber(raw.triggerContextCount)} context(s)${raw.triggerContextSummaryTruncated ? " / truncated" : ""}`
            : ""],
          [t("eventContextSummary"), raw.eventContextCount
            ? `${formatNumber(raw.eventContextCount)} context(s)${raw.eventContextSummaryTruncated ? " / truncated" : ""}`
            : ""],
          [t("wwiseMediaRelations"), asArray(raw.wwiseMediaRelationTypes).join(" / ")],
          [t("wwiseMediaPaths"), raw.wwiseMediaSelectionPathCount
            ? `${formatNumber(raw.wwiseMediaSelectionPathCount)} path(s)${raw.wwiseMediaSelectionPathsTruncated ? " / truncated" : ""}`
            : ""],
          [t("wwiseMediaRootActions"), asArray(raw.wwiseMediaRootActionIds).join(" / ")],
          [t("postProcessRoutes"), raw.postProcessRouteCount
            ? `${formatNumber(raw.postProcessRouteCount)} route(s) / ${formatNumber(raw.postProcessBusPathCount || 0)} bus path(s)`
            : asArray(raw.postProcessRouteStatuses).map(humanize).join(" / ")],
          [t("postProcessEffects"), asArray(raw.postProcessEffectBusIds).join(" / ")],
          [t("postProcessDirectEffects"), raw.postProcessDirectEffectCount
            ? `${formatNumber(raw.postProcessDirectEffectCount)} effect(s) / ${formatNumber(raw.postProcessDirectEffectOccurrences || 0)} slot occurrence(s)`
            : ""],
          [t("postProcessEffectChain"), raw.postProcessEffectChainCount
            ? `${formatNumber(raw.postProcessEffectChainCount)} authored stage(s)${raw.postProcessEffectChainTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessBusControls"), raw.postProcessBusControlCount
            ? `${formatNumber(raw.postProcessBusControlCount)} Bus control set(s)${raw.postProcessBusControlsTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessBusDucks"), raw.postProcessBusDuckCount
            ? `${formatNumber(raw.postProcessBusDuckCount)} ducking Bus(es)`
            : ""],
          [t("postProcessAuxSends"), raw.postProcessAuxSendCount
            ? `${formatNumber(raw.postProcessAuxSendCount)} Aux target(s) / ${formatNumber(raw.postProcessAuxSendOccurrences || 0)} occurrence(s)${raw.postProcessAuxSendsTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessProperties"), raw.postProcessPropertyCount
            ? `${formatNumber(raw.postProcessPropertyCount)} value signature(s) / ${formatNumber(raw.postProcessPropertyOccurrences || 0)} occurrence(s)${raw.postProcessPropertiesTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessRanges"), raw.postProcessRangeCount
            ? `${formatNumber(raw.postProcessRangeCount)} range signature(s) / ${formatNumber(raw.postProcessRangeOccurrences || 0)} occurrence(s)${raw.postProcessRangesTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessRtpcControls"), raw.postProcessRtpcControlCount
            ? `${formatNumber(raw.postProcessRtpcControlCount)} curve(s)${raw.postProcessRtpcControlsTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessStateControls"), raw.postProcessStateControlCount
            ? `${formatNumber(raw.postProcessStateControlCount)} override(s)${raw.postProcessStateControlsTruncated ? " / truncated" : ""}`
            : ""],
          [t("postProcessUnresolved"), asArray(raw.postProcessUnresolvedBusProcessingIds).join(" / ")],
          [t("postProcessSelection"), asArray(raw.postProcessSelectionStatuses).map(humanize).join(" / ")],
        ];
    const grid = document.createElement("div");
    grid.className = "audio-facts";
    for (const [label, value] of facts) if (value !== undefined && value !== null && value !== "") grid.appendChild(factNode(label, value));
    panel.appendChild(grid);

    if (record.contextTags.length) panel.appendChild(chipSection(t("contextGroups"), record.contextTags.map(taxonomyLabel)));
    if (record.relationTags.length) panel.appendChild(chipSection(t("relation"), record.relationTags.map(taxonomyLabel)));
    if (record.kind === "media" && asArray(raw.relatedEventCategories).length) {
      panel.appendChild(chipSection(t("relatedEventTypes"), asArray(raw.relatedEventCategories).map(categoryLabel)));
    }
    if (record.kind === "media" && asArray(raw.triggerSemanticKinds).length) {
      panel.appendChild(chipSection(t("triggerKinds"), asArray(raw.triggerSemanticKinds).map(humanize)));
    }
    if (record.kind === "media" && asArray(raw.triggerRoles).length) {
      panel.appendChild(chipSection(t("triggerRoles"), asArray(raw.triggerRoles).map(humanize)));
    }
    if (record.kind === "media" && asArray(raw.triggerOwnerValues).length) {
      panel.appendChild(chipSection(t("triggerOwners"), asArray(raw.triggerOwnerValues)));
    }
    if (record.kind === "media" && asArray(raw.triggerSituationValues).length) {
      panel.appendChild(chipSection(t("triggerSituations"), asArray(raw.triggerSituationValues)));
    }
    if (record.kind === "media" && asArray(raw.eventContextKinds).length) {
      panel.appendChild(chipSection(
        `${t("eventContextKinds")}${raw.eventContextSummaryTruncated ? " (truncated)" : ""}`,
        asArray(raw.eventContextKinds).map(humanize),
      ));
    }
    if (record.kind === "media" && asArray(raw.eventContextRoles).length) {
      panel.appendChild(chipSection(t("eventContextRoles"), asArray(raw.eventContextRoles).map(humanize)));
    }
    if (record.kind === "media" && asArray(raw.eventContextOwnerValues).length) {
      panel.appendChild(chipSection(t("eventContextOwners"), asArray(raw.eventContextOwnerValues)));
    }
    if (record.kind === "media" && asArray(raw.eventContextSituationValues).length) {
      panel.appendChild(chipSection(t("eventContextSituations"), asArray(raw.eventContextSituationValues)));
    }
    if (record.kind === "media" && asArray(raw.wwiseMediaRelationTypes).length) {
      panel.appendChild(chipSection(
        `${t("wwiseMediaRelations")}${raw.wwiseMediaRelationTypesTruncated ? " (truncated)" : ""}`,
        asArray(raw.wwiseMediaRelationTypes).map(humanize),
      ));
    }
    if (record.kind === "media" && asArray(raw.wwiseMediaSelectionPaths).length) {
      panel.appendChild(chipSection(
        `${t("wwiseMediaPaths")}${raw.wwiseMediaSelectionPathsTruncated ? " (truncated)" : ""}`,
        asArray(raw.wwiseMediaSelectionPaths).map((path) => (
          Array.isArray(path) ? path.join(" -> ") : String(path || "")
        )).filter(Boolean),
      ));
    }
    if (record.kind === "media" && asArray(raw.wwiseMediaRootActionIds).length) {
      panel.appendChild(chipSection(
        `${t("wwiseMediaRootActions")}${raw.wwiseMediaRootActionIdsTruncated ? " (truncated)" : ""}`,
        asArray(raw.wwiseMediaRootActionIds).map((value) => `0x${Number(value).toString(16).padStart(8, "0")}`),
      ));
    }
    if (record.kind === "media" && asArray(raw.postProcessBusPaths).length) {
      const pathRows = asArray(raw.postProcessBusPaths).map((path) => (
        Array.isArray(path) ? path.join(" -> ") : String(path || "")
      )).filter(Boolean);
      if (pathRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessBuses")}${raw.postProcessBusPathsTruncated ? " (truncated)" : ""}`,
          pathRows,
        ));
      }
      const mediaBusDefinitions = new Map(asArray(state.index?.hircSummary?.postProcessSummary?.busDefinitions)
        .filter((row) => row && typeof row === "object")
        .map((row) => [normalize(row.busIdHex || row.busId).toLowerCase(), row]));
      const busIds = [...new Set(asArray(raw.postProcessBusPaths)
        .flatMap((path) => Array.isArray(path) ? path : [path])
        .map((value) => normalize(value).toLowerCase())
        .filter(Boolean))];
      const busSemanticRows = busIds.map((busId) => {
        const definition = mediaBusDefinitions.get(busId);
        if (!definition) return `${busId} / definition unavailable`;
        const properties = asArray(definition.serializedProperties).map((prop) => {
          const label = prop.propertyLabel || prop.propertyIdHex || `property ${prop.propertyId ?? "?"}`;
          const value = String(prop.valueEncoding || "").startsWith("u32")
            ? (prop.rawHex || prop.rawU32 || "?")
            : prop.floatValue !== null && prop.floatValue !== undefined
              ? Number(prop.floatValue).toPrecision(6).replace(/\.?0+$/, "")
              : (prop.rawHex || "?");
          return `${label} ${value}`;
        }).slice(0, 8);
        const status = definition.effectParserStatus === "exactTypedV150EmptyEffectChunk"
          ? "serialized InitialFX empty"
          : definition.effectParserStatus === "exactTypedV150NonEmptyEffectChunk"
            ? `${formatNumber(definition.effectSlotCount || 0)} serialized InitialFX slot(s)`
            : humanize(definition.effectParserStatus || "unknown");
        const stateRtpc = definition.serializedStateAndRtpc || {};
        const stateRtpcParts = [];
        if (stateRtpc.parserStatus === "typedExactV150BusInitialRtpcAndState") {
          if (stateRtpc.rtpcCurveCount) {
            const rtpcLabels = asArray(stateRtpc.rtpcCurves)
              .map((curve) => `${rtpcParameterText(curve)} ${formatNumber(curve.pointCount || 0)}pt`)
              .slice(0, 4);
            stateRtpcParts.push(`RTPC ${formatNumber(stateRtpc.rtpcCurveCount)}${rtpcLabels.length ? ` (${rtpcLabels.join(", ")})` : ""}`);
          }
          if (stateRtpc.stateGroupCount) {
            stateRtpcParts.push(`State ${formatNumber(stateRtpc.stateGroupCount)} group(s) / ${formatNumber(stateRtpc.stateCount || 0)} state(s)`);
          }
        } else if (stateRtpc.parserStatus) {
          stateRtpcParts.push(`State/RTPC ${humanize(stateRtpc.parserStatus)}`);
        }
        return [
          busId,
          humanize(definition.objectTypeLabel || "bus"),
          status,
          definition.serializedDuckCount ? `${formatNumber(definition.serializedDuckCount)} duck(s)` : "",
          definition.serializedMaxDuckVolumeDb !== undefined ? `max duck ${definition.serializedMaxDuckVolumeDb} dB` : "",
          properties.length ? properties.join(", ") : "",
          ...stateRtpcParts,
        ].filter(Boolean).join(" / ");
      });
      if (busSemanticRows.length) {
        panel.appendChild(chipSection(
          t("postProcessBusSemantics"),
          busSemanticRows.slice(0, 32),
        ));
      }
    }
    if (record.kind === "media" && asArray(raw.postProcessRouteStatuses).length) {
      panel.appendChild(chipSection(
        t("postProcessStatus"),
        asArray(raw.postProcessRouteStatuses).map(humanize),
      ));
    }
    if (record.kind === "media") {
      const effectRows = mediaPostProcessEffectSummary(raw);
      if (effectRows.length) panel.appendChild(chipSection(t("postProcessEffects"), effectRows));
      const effectChainRows = mediaPostProcessEffectChainSummary(raw);
      if (effectChainRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessEffectChain")}${raw.postProcessEffectChainTruncated ? " (truncated)" : ""}`,
          effectChainRows,
        ));
      }
      const busControlRows = mediaPostProcessBusControlSummary(raw);
      if (busControlRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessBusControls")}${raw.postProcessBusControlsTruncated ? " (truncated)" : ""}`,
          busControlRows,
        ));
      }
      const busDuckRows = mediaPostProcessBusDuckSummary(raw);
      if (busDuckRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessBusDucks")}${raw.postProcessBusDucksTruncated ? " (truncated)" : ""}`,
          busDuckRows,
        ));
      }
      const auxSendRows = mediaPostProcessAuxSendSummary(raw);
      if (auxSendRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessAuxSends")}${raw.postProcessAuxSendsTruncated ? " (truncated)" : ""}`,
          auxSendRows,
        ));
      }
      const propertyRows = mediaPostProcessPropertySummary(raw);
      if (propertyRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessProperties")}${raw.postProcessPropertiesTruncated ? " (truncated)" : ""}`,
          propertyRows,
        ));
      }
      const rangeRows = mediaPostProcessRangeSummary(raw);
      if (rangeRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessRanges")}${raw.postProcessRangesTruncated ? " (truncated)" : ""}`,
          rangeRows,
        ));
      }
      const directEffectRows = mediaPostProcessDirectEffectSummary(raw);
      if (directEffectRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessDirectEffects")}${raw.postProcessDirectEffectsTruncated ? " (truncated)" : ""}`,
          directEffectRows,
        ));
      }
      const rtpcRows = mediaPostProcessRtpcSummary(raw);
      if (rtpcRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessRtpcControls")}${raw.postProcessRtpcControlsTruncated ? " (truncated)" : ""}`,
          rtpcRows,
        ));
      }
      const stateRows = mediaPostProcessStateSummary(raw);
      if (stateRows.length) {
        panel.appendChild(chipSection(
          `${t("postProcessStateControls")}${raw.postProcessStateControlsTruncated ? " (truncated)" : ""}`,
          stateRows,
        ));
      }
    }
    if (record.kind === "media" && raw.postProcessRouteEvidence) {
      const routeStatuses = asArray(raw.postProcessRouteStatuses);
      const boundary = routeStatuses.includes("noExplicitOutputBusSerialized")
        ? t("postProcessNoExplicitBus")
        : routeStatuses.includes("outputBusNodeUnresolved")
          ? t("postProcessBusUnresolved")
          : "The route is an authored Event-graph relation; live branch choice and audibility were not observed.";
      panel.appendChild(noteSection(
        t("postProcessRoutes"),
        `${raw.postProcessRouteEvidence}: ${t("postProcessSelection")} ${asArray(raw.postProcessSelectionStatuses).map(humanize).join(" / ") || humanize("unresolved")}. `
          + boundary,
      ));
    }
    if (record.kind === "media" && raw.postProcessEffectChainEvidence) {
      panel.appendChild(noteSection(
        t("postProcessEffectChain"),
        `${raw.postProcessEffectChainEvidence}: direct-node effects precede each serialized leaf-to-root Bus path and Bus slots keep serialized order; this is authored evidence, not observed runtime DSP order, inherited values, branch choice, or audibility.`,
      ));
    }
    if (record.kind === "media" && raw.postProcessBusControlEvidence) {
      panel.appendChild(noteSection(
        t("postProcessBusControls"),
        `${raw.postProcessBusControlEvidence}: Bus InitialRTPC curves and State values are exact serialized control shapes attached to a possible media route; live parameter values, inherited resolution, selected branches, platform DSP, and audibility were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.postProcessBusDuckEvidence) {
      panel.appendChild(noteSection(
        t("postProcessBusDucks"),
        `${raw.postProcessBusDuckEvidence}: Bus duck targets, attenuation, fades, and target properties are exact serialized authored records on a possible route; the runtime triggering Bus, active duck state, inherited values, and audible result were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.postProcessAuxSendEvidence) {
      panel.appendChild(noteSection(
        t("postProcessAuxSends"),
        `${raw.postProcessAuxSendEvidence}: User-Defined Aux Bus IDs are exact serialized NodeBase send slots projected onto the Event's possible media set; Game-Defined Aux IDs, live send levels, runtime activation, inherited values, and audibility were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.postProcessPropertyEvidence) {
      panel.appendChild(noteSection(
        `${t("postProcessProperties")} / ${t("postProcessRanges")}`,
        `${raw.postProcessPropertyEvidence}: authored NodeBase property values and ranges are exact serialized settings on a possible Event path; inherited resolution, live modifiers, branch selection, platform DSP, and audibility were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.postProcessControlEvidence) {
      panel.appendChild(noteSection(
        `${t("postProcessRtpcControls")} / ${t("postProcessStateControls")}`,
        `${raw.postProcessControlEvidence}: these are authored serialized State/InitialRTPC controls on a possible Event path; live parameter updates, branch selection, inherited values, platform DSP, and audibility were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.wwiseMediaGraphEvidence) {
      panel.appendChild(noteSection(
        t("wwiseMediaRelations"),
        `${raw.wwiseMediaGraphEvidence}: the edge/path is exact serialized Wwise graph evidence; runtime branch choice, caller identity, and audibility were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.eventContextSummaryEvidence) {
      panel.appendChild(noteSection(
        t("eventContextSummary"),
        `${raw.eventContextSummaryEvidence}: the authored context belongs to the Event's possible media set; the specific selected leaf and runtime execution were not observed.`,
      ));
    }
    if (record.kind === "media" && raw.triggerContextSummaryEvidence) {
      panel.appendChild(noteSection(
        t("triggerContexts"),
        `${raw.triggerContextSummaryEvidence}: ${t("triggerSelection")} ${asArray(raw.triggerSelectionStatuses).map(humanize).join(" / ") || humanize("unresolved")}. `
          + "The serialized context identifies an authored request or placement; runtime execution and live branch choice were not observed.",
      ));
    }
    const selectorEvidence = selectorEvidenceSummary(raw);
    if (selectorEvidence.length) panel.appendChild(chipSection(t("selectorEvidence"), selectorEvidence));
    const sourceEvidence = sourceEvidenceSummary(raw);
    if (sourceEvidence.length) panel.appendChild(chipSection(t("sourceEvidence"), sourceEvidence));
    const customFootstepParameters = customFootstepParameterSummary(raw);
    if (customFootstepParameters.length) {
      panel.appendChild(chipSection(t("customFootstepParameters"), customFootstepParameters));
      panel.appendChild(chipSection(t("customFootstepNativeAnchors"), customFootstepRuntimeSummary()));
      const boundary = state.index?.customFootstepModel?.runtimeSelectorBoundary;
      if (boundary) panel.appendChild(noteSection(t("customFootstepRuntime"), boundary));
    }
    if (record.kind === "events" && raw.foundInWwise !== true) {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("unresolvedEventBoundary")));
    } else if (record.kind === "events" && raw.eventIdentityStatus === "wwiseObjectWithoutRecoveredTriggerName") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("unknownTriggerBoundary")));
    } else if (record.kind === "events" && raw.identityOnlyPlaybackPlacementStatus === "identityOnlyNoAudioConsumer") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("identityOnlyBoundary")));
    } else if (record.kind === "media" && raw.externalMediaIdentityStatus === "recoveredAuthoredPathHash") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("orphanExternalIdentityBoundary")));
    } else if (record.kind === "media" && raw.audioLibraryObjectStatus === "wwiseSoundDefinitionWithoutEventPath") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("definitionOnlyMediaBoundary")));
    } else if (record.kind === "media" && raw.playbackLocationStatus === "unknown") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("unknownLocationBoundary")));
    } else if (record.kind === "media" && raw.playbackLocationStatus === "eventRelationOnly") {
      panel.appendChild(noteSection(t("runtimeBoundary"), t("eventOnlyLocationBoundary")));
    }

    const evidence = asArray(raw.evidence).filter((value) => value && typeof value === "object");
    const mediaIds = [...new Set([
      ...collectIds(raw, ["mediaIds", "mediaId"]),
      ...evidence.flatMap((row) => collectIds(row, ["mediaIds", "mediaId"])),
    ])];
    const eventIds = collectIds(raw, ["eventIds", "events", "eventId"]);
    const actionIds = [...new Set([
      ...collectIds(raw, ["actionIds", "visitedObjectIds", "actions"]),
      ...evidence.flatMap((row) => collectIds(row, ["actionIds", "visitedObjectIds", "actions"])),
    ])];
    if (mediaIds.length) panel.appendChild(chipSection(t("mediaIds"), mediaIds));
    if (record.kind === "media" && eventIds.length) panel.appendChild(chipSection(t("eventIds"), eventIds));
    if (actionIds.length) panel.appendChild(chipSection(t("actions"), actionIds));
    const contexts = asArray(raw.contexts).filter((value) => value && typeof value === "object").map(contextEvidenceLabel).filter(Boolean);
    if (contexts.length) panel.appendChild(chipSection(t("contextEvidence"), contexts));
    const radioTableLines = asArray(raw.radioTableLineIdentities)
      .filter((value) => value && typeof value === "object")
      .map(radioTableLineLabel)
      .filter(Boolean);
    if (radioTableLines.length) panel.appendChild(chipSection(t("radioTableLines"), radioTableLines));
    const radioTriggerContexts = asArray(raw.radioTriggerContexts)
      .filter((value) => value && typeof value === "object")
      .map(contextEvidenceLabel)
      .filter(Boolean);
    if (radioTriggerContexts.length) panel.appendChild(chipSection(t("radioTriggerContexts"), radioTriggerContexts));
    if (radioTableLines.length || Number(raw.radioTriggerContextCount || 0) > 0) {
      const radioBoundary = state.index?.triggerCatalog?.levelScriptRadio?.evidenceBoundary;
      if (radioBoundary) panel.appendChild(noteSection(t("runtimeBoundary"), radioBoundary));
    }

    const details = document.createElement("details");
    details.style.marginTop = "14px";
    const summary = document.createElement("summary");
    summary.textContent = t("rawRecord");
    const pre = document.createElement("pre");
    pre.className = "audio-raw-record";
    const json = JSON.stringify(raw, null, 2) || "{}";
    pre.textContent = json.length > 50000 ? `${json.slice(0, 50000)}\n…` : json;
    details.append(summary, pre);
    panel.appendChild(details);
    return panel;
  }

  function collectIds(record, keys) {
    const values = [];
    for (const key of keys) {
      for (const value of asArray(record?.[key])) {
        const id = typeof value === "object" ? (value.id ?? value.eventId ?? value.mediaId ?? value.actionId ?? value.objectId) : value;
        if (id !== undefined && id !== null && id !== "") values.push(String(id));
      }
    }
    return [...new Set(values)].slice(0, 120);
  }

  function playableRecords(raw, kind) {
    const candidates = [];
    const add = (value) => {
      if (!value) return;
      if (typeof value === "string") candidates.push({ src: value });
      else if (typeof value === "object") candidates.push(value);
    };
    if (kind === "media") add(raw);
    for (const key of ["media", "mediaEntries", "playableMedia", "audio", "candidates", "outputs"]) asArray(raw?.[key]).forEach(add);
    const seen = new Set();
    return candidates.map((candidate) => {
      const src = audioSource(candidate, raw);
      const id = normalize(candidate.mediaId ?? candidate.id ?? fileName(src));
      const wwise = asArray(candidate?.wwiseMediaEvidence).filter((row) => row && typeof row === "object");
      const rootActionIds = [...new Set(wwise.flatMap((row) => asArray(row.rootActionIds)).filter((value) => Number.isInteger(value)))].sort((a, b) => a - b);
      const relationTypes = [...new Set(wwise.flatMap((row) => asArray(row.relationTypes)).filter(Boolean))].sort();
      const soundObjectCount = wwise.reduce((total, row) => total + Number(row.soundObjectCount || 0), 0);
      return {
        raw: candidate, src, id, title: kind === "media" ? recordTitle(raw, "media") : id, bytes: candidate.bytes, format: candidate.format,
        rootActionIds, relationTypes, soundObjectCount,
        contentSha256: normalize(candidate.contentSha256),
        contentEquivalentCount: Number(candidate.contentEquivalentCount || 0),
        hotfixMediaReplacement: candidate.hotfixMediaReplacement === true,
      };
    }).filter((candidate) => {
      if (!candidate.src) return false;
      const identity = `${candidate.id}\u0000${candidate.src}`;
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    });
  }

  function audioSource(candidate, parent = {}) {
    let raw = normalize(candidate?.src ?? candidate?.audioSrc ?? candidate?.path ?? candidate?.rel);
    if (!raw) return "";
    raw = raw.replace(/\\/g, "/");
    if (/^(?:https?:|blob:|data:)/i.test(raw) || raw.startsWith("/")) return raw;
    raw = raw.replace(/^\.\//, "").replace(/^\/+/, "");
    if (raw.startsWith("export_full/")) return `/${raw}`;
    if (raw.startsWith("structured/Audio/")) return `/export_full/${raw}`;
    const root = normalize(candidate?.storageRoot ?? parent?.storageRoot ?? candidate?.audioScope ?? parent?.audioScope);
    if (root === "shared") return `/export_full/structured/Audio/shared/${encodePath(raw)}`;
    return `/export_full/structured/Audio/${encodeURIComponent(state.language)}/${encodePath(raw)}`;
  }

  function encodePath(path) {
    return String(path || "").split("/").filter(Boolean).map(encodeURIComponent).join("/");
  }

  function renderPlayers(parent, players, { eager = false } = {}) {
    const list = document.createElement("div");
    list.className = "audio-player-list";
    const groups = new Map();
    for (const candidate of players) {
      const groupKey = `${candidate.rootActionIds.join(",")}|${candidate.relationTypes.join(",")}`;
      if (!groups.has(groupKey)) groups.set(groupKey, []);
      groups.get(groupKey).push(candidate);
    }
    for (const candidates of groups.values()) {
      const exemplar = candidates[0];
      const collapsePlayers = candidates.length > PLAYER_COLLAPSE_THRESHOLD;
      const groupTitle = document.createElement("div");
      groupTitle.className = "audio-fact-label";
      const rootLabel = exemplar.rootActionIds.length
        ? `${t("playRoots")}: ${exemplar.rootActionIds.join(" / ")}`
        : (parent?.audioDialogKey || parent?.audioDialogPath)
          ? t("relationDirectDialogMedia")
          : asArray(parent?.eventIds).length || parent?.eventId
            ? ""
            : t("relationUnlinkedMedia");
      const relationLabel = exemplar.relationTypes.map(taxonomyLabel).join(" + ");
      groupTitle.textContent = [rootLabel, relationLabel, `${formatNumber(candidates.length)} ${t("possibleMedia")}`].filter(Boolean).join(" · ");
      list.appendChild(groupTitle);
      for (const candidate of candidates) {
      const card = document.createElement("details");
      card.className = "audio-player-card";
      const head = document.createElement("summary");
      head.className = "audio-player-head";
      const title = document.createElement("div");
      title.className = "audio-player-title";
      title.textContent = candidate.title || candidate.id || fileName(candidate.src);
      const meta = document.createElement("div");
      meta.className = "audio-player-meta";
      meta.textContent = [
        candidate.format,
        candidate.bytes !== undefined ? formatBytes(candidate.bytes) : "",
      ].filter(Boolean).join(" 路 ");
      const evidence = document.createElement("div");
      evidence.className = "audio-player-meta";
      evidence.textContent = [
        candidate.soundObjectCount ? `${candidate.soundObjectCount} Sound objects` : "",
        candidate.contentEquivalentCount > 1 ? `${t("equivalentContent")} × ${candidate.contentEquivalentCount}` : "",
        candidate.hotfixMediaReplacement ? t("hotfixMediaReplacement") : "",
        ...candidate.relationTypes.map(taxonomyLabel),
        collapsePlayers ? t("expandToLoadPlayer") : "",
      ].filter(Boolean).join(" · ");
      meta.textContent = [meta.textContent, evidence.textContent].filter(Boolean).join(" / ");
      head.append(title, meta);
      const playerHost = document.createElement("div");
      playerHost.className = "audio-player-host";
      let materialized = false;
      card.addEventListener("toggle", () => {
        if (!card.open || materialized) return;
        materializePlayer();
      });
      const materializePlayer = () => {
        if (materialized) return;
        materialized = true;
        const audio = document.createElement("audio");
        audio.preload = "none";
        audio.controls = true;
        audio.src = candidate.src;
        const player = window.WebUI?.createMediaPlayer
          ? window.WebUI.createMediaPlayer(audio, { waveform: true })
          : audio;
        const sourceLink = document.createElement("a");
        sourceLink.className = "audio-source-link";
        sourceLink.href = candidate.src;
        sourceLink.target = "_blank";
        sourceLink.rel = "noopener";
        sourceLink.textContent = candidate.src;
        sourceLink.title = candidate.src;
        playerHost.append(player, sourceLink);
      };
      if (eager || !collapsePlayers) {
        card.open = true;
        materializePlayer();
      }
      card.append(head, playerHost);
      list.appendChild(card);
      }
    }
    parent.appendChild(list);
  }

  function statNode(label, value) {
    const node = document.createElement("div");
    node.className = "audio-stat";
    node.innerHTML = `<span class="audio-stat-label">${esc(label)}</span><span class="audio-stat-value">${esc(value)}</span>`;
    return node;
  }

  function factNode(label, value) {
    const node = document.createElement("div");
    node.className = "audio-fact";
    node.innerHTML = `<span class="audio-fact-label">${esc(label)}</span><span class="audio-fact-value">${esc(value)}</span>`;
    return node;
  }

  function chipSection(label, values) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "12px";
    const title = document.createElement("div");
    title.className = "audio-fact-label";
    title.textContent = label;
    const list = document.createElement("div");
    list.className = "audio-chip-list";
    for (const value of values) {
      const chip = document.createElement("span");
      chip.className = "audio-data-chip";
      chip.textContent = String(value);
      list.appendChild(chip);
    }
    wrap.append(title, list);
    return wrap;
  }

  function noteSection(label, value) {
    const wrap = document.createElement("div");
    wrap.style.marginTop = "12px";
    const title = document.createElement("div");
    title.className = "audio-fact-label";
    title.textContent = label;
    const note = document.createElement("p");
    note.className = "audio-runtime-note";
    note.textContent = value;
    wrap.append(title, note);
    return wrap;
  }

  function renderLoadError(error, { index = false } = {}) {
    const message = `${t(index ? "loadError" : "shardError")} ${normalize(error?.message || error)}`.trim();
    const html = `<div class="audio-inline-error" role="alert"><strong>${esc(message)}</strong><br><button class="audio-retry" type="button">${esc(t("retry"))}</button></div>`;
    const list = $("#audio-list", state.container);
    if (list) list.innerHTML = html;
    const body = $("#audio-detail-body", state.container);
    if (body) body.innerHTML = html;
    state.container.querySelectorAll(".audio-retry").forEach((button) => {
      button.addEventListener("click", () => window.dispatchEvent(new CustomEvent("webui:retry-view", { detail: { view: "audio", language: state.language } })));
    });
  }

  function humanize(value) {
    return String(value || "").replace(/[_-]+/g, " ").replace(/([a-z0-9])([A-Z])/g, "$1 $2").trim();
  }

  function manualNoteSection(record) {
    const section = document.createElement("section");
    section.className = "audio-manual-note";
    const label = document.createElement("label");
    label.htmlFor = "audio-manual-note-input";
    label.textContent = t("manualNote");
    const textarea = document.createElement("textarea");
    textarea.id = "audio-manual-note-input";
    textarea.rows = 3;
    textarea.placeholder = t("manualNotePlaceholder");
    textarea.value = recordNote(record);
    let savedValue = textarea.value;
    const actions = document.createElement("div");
    actions.className = "audio-manual-note-actions";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "audio-manual-note-save";
    save.textContent = t("manualNoteSave");
    save.disabled = true;
    const status = document.createElement("span");
    status.className = "audio-manual-note-status";
    textarea.addEventListener("input", () => {
      const dirty = textarea.value !== savedValue;
      save.disabled = !dirty;
      status.textContent = dirty ? t("manualNoteUnsaved") : "";
      status.classList.remove("is-error");
    });
    save.addEventListener("click", async () => {
      const value = textarea.value;
      const nextNotes = notesWithRecordUpdate(record, value);
      save.disabled = true;
      status.textContent = t("manualNoteSaving");
      status.classList.remove("is-error");
      try {
        await persistNotes(nextNotes);
        state.notes = nextNotes;
        savedValue = value;
        const dirty = textarea.value !== savedValue;
        save.disabled = !dirty;
        status.textContent = dirty ? t("manualNoteUnsaved") : t("manualNoteSaved");
        applyFilters();
      } catch (error) {
        console.warn(`Unable to save ${NOTES_OVERRIDE_PATH}`, error);
        status.textContent = `${t("manualNoteStorageError")} ${normalize(error?.message || error)}`;
        status.classList.add("is-error");
        save.disabled = textarea.value === savedValue;
      }
    });
    actions.append(save, status);
    section.append(label, textarea, actions);
    return section;
  }

  function rtpcParameterText(row) {
    const label = normalize(row?.parameterLabel);
    const parameterId = Number(row?.parameterId);
    const rtpcId = Number(row?.rtpcId);
    const rtpcIdHex = normalize(row?.rtpcIdHex).toLowerCase();
    const namedGameParameter = Number.isFinite(rtpcId)
      ? state.gameParameterNameById.get(rtpcId)
      : (rtpcIdHex.startsWith("0x")
        ? state.gameParameterNameById.get(Number.parseInt(rtpcIdHex, 16))
        : "");
    const gameParameterSuffix = namedGameParameter
      ? ` / GameParameter ${namedGameParameter}`
      : "";
    if (!Number.isFinite(parameterId)) return `${label || "parameter ?"}${gameParameterSuffix}`;
    if (label && !/^parameter\d+$/i.test(label)) return `${label}${gameParameterSuffix}`;
    const hex = `0x${Math.trunc(parameterId).toString(16).padStart(4, "0")}`;
    // Wwise v150's standard AkPropID table ends at 0x55.  Preserve higher
    // values as an explicit custom/internal boundary instead of inventing a
    // DSP property name from a coincidental numeric ID.
    return `${label || `parameter ${Math.trunc(parameterId)}`} [custom/internal ${hex}]${gameParameterSuffix}`;
  }

  function parameterLabelText(label) {
    const value = normalize(label);
    const match = /^parameter(\d+)$/i.exec(value);
    if (!match) return humanize(value);
    const parameterId = Number(match[1]);
    const hex = Number.isFinite(parameterId)
      ? `0x${Math.trunc(parameterId).toString(16).padStart(4, "0")}`
      : "?";
    return `${value} [custom/internal ${hex}]`;
  }

  function fileName(value) {
    const clean = normalize(value).replace(/\\/g, "/").split(/[?#]/)[0];
    return clean.split("/").pop() || "";
  }

  function init() {
    if (state.initialized) return true;
    state.container = $("#audio-app");
    if (!state.container) return false;
    state.initialized = true;
    state.uiLocale = locale();
    renderShell();
    renderLoadingList();
    renderDetail();
    window.addEventListener("webui:ui-locale-changed", (event) => {
      state.uiLocale = normalize(event.detail?.locale) || state.uiLocale;
      applyUiText();
    });
    window.addEventListener("resize", scheduleListRender);
    return true;
  }

  window.WebUI = window.WebUI || {};
  window.WebUI.audio = { init, load, retry: () => load(state.language, { force: true }) };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
