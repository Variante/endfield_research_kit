# Lua Consumer Reference Audit

- Lua roots scanned: `1`
- Lua files scanned across roots: `1290`
- unique Lua modules: `1290`
- duplicate modules with identical bytes: `0` / `0`
- read errors: `0`

## Focus Areas

- `sns` files: `60`
- `remotecomm` files: `37`
- `dialog` files: `35`
- `mapmark` files: `93`
- `mission` files: `111`

## Table Reference Availability

- Exported table files indexed: `693`
- Referenced Lua table names: `560`
- Matched referenced table names: `552`
- Unmatched referenced table names: `8`
- Lua module-to-table edge candidates: `2273`
- Top unmatched: formulaIdToStr (2), i18nTextTable (1), equipTierLevelTable (1), skillLockTable (1), blocShopItemTable (1), settlementOrderDataTable (1), formulaIdToNum (1), factoryProcessorCraftTable (1)

## GameAction Story Playback Census

- all direct `GameAction.*` calls: `72` across `36` methods
- Story-playback calls: `10` across `4` modules
- authored playback references: `3`
- binary-proven runtime handle dispatch branches: `7` in `1` queue family
- registry keys used for exact-case validation: `11348`
- `case_mismatch_registry_match`: `1`
- `exact_registry_match`: `2`
- `runtime_payload_not_static_story_id`: `7`

| module | line | GameAction | first argument | resolution | registry | nearby tables |
| --- | ---: | --- | --- | --- | --- | --- |
| `LuaSystem/CinematicSystem.lua` | 74 | `DoPlayDialogByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 76 | `DoPlayCutsceneByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 78 | `PlayCGByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 80 | `StartRemoteCommByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 82 | `ShowNarrativeBlackScreenByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 84 | `ShowUIReadingPopPanelByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `LuaSystem/CinematicSystem.lua` | 86 | `DoPlayForceSNSByHandle` | `handle` | `runtime_handle_payload` | `runtime_payload_not_static_story_id` |  |
| `Phase/GenderChange/PhaseGenderChange.lua` | 104 | `PlayCutscene` | `CUT_SCENE_ID` | `module_constant` | `exact_registry_match` |  |
| `Phase/GenderSelect/PhaseGenderSelect.lua` | 75 | `PlayCutsceneAndGetHandle` | `EnterCutsceneId` | `module_constant` | `case_mismatch_registry_match` |  |
| `UI/Panels/ActivitySkipChapter1Confirm/ActivitySkipChapter1ConfirmCtrl.lua` | 97 | `StartDialog` | `bindDlgId` | `table_field_singleton` | `exact_registry_match` | skipChapterTable |

Evidence boundary:

- **scope:** All direct GameAction.* calls in each unique Lua module are enumerated. The Story subset is a bounded allowlist of native playback entry points.
- **literalResolution:** Direct quoted arguments and simple local string assignments are resolved. A simple Tables.<name> row field is also resolved when the current original table has exactly one non-empty candidate; multi-row fields, function parameters, concatenation, and general control flow remain unresolved. Calls accepting the binary-proven cinematic queue handle are classified as one runtime dispatcher family, not as unresolved authored Story references.
- **case:** Exact registry spelling is proven separately from a case-folded candidate. A case mismatch is never promoted to a Story binding.
- **ownership:** A Lua call proves that the controller owns playback. It creates no mission/quest attachment unless the same consumed route carries an exact mission or quest identity.
- **nearbyTables:** Table names within a bounded source window are triage hints, not data-flow proof.

## Top References

- `tables`: itemTable (593), spaceshipConst (153), domainDataTable (108), dungeonTable (89), globalConst (89), rewardTable (85), factoryBuildingTable (85), characterTable (63), dungeonConst (55), shopGoodsTable (51)
- `gEnums`: ActivityConditionalStageState.Locked (45), FacBuildingState.Normal (41), ActivityConditionalTaskState.Completed (40), ActivityConditionalStageState.__CastFrom (39), ActivityConditionalTaskState.__CastFrom (36), ActivityConditionalStageState.Completed (34), ActivityConditionalStageState.Rewarded (32), AttributeType.Atk (32), ActivityConditionalStageState.Unlocked (29), SpaceshipRoomType.GrowCabin (28)
- `csBeyond`: CS.Beyond.EnableLogType.MainHudActionQueue (29), CS.Beyond.UI.UIConst.AnimationState.Out (22), CS.Beyond.Gameplay.Core.InteractOptionType.Factory (20), CS.Beyond.Input.ActionOnSetNaviTarget (17), CS.Beyond.UI.UIAnimationWrapper (15), CS.Beyond.Gameplay.RemoteFactory.RemoteFactoryBlueprintSourceType.Gift (15), CS.Beyond.UI.UIScrollList.ScrollAlignType.Top (15), CS.Beyond.EnableLogType.DevOnly (14), CS.Beyond.Gameplay.MissionSystem.QuestState.Completed (14), CS.Beyond.Gameplay.MissionSystem.MissionState.Completed (14)
- `contentParam`: 0 (8), 1 (5)
- `dialogContentData`: dialogContentData (12)
- `remoteCommonData`: RemoteCommonData (1)
- `middleId`: middleId (17)
- `loadSprite`: LoadSprite (877), UIUtils.getSpritePath (15), LoadSpriteAsync (6)
- `videoHelper`: VideoPlayer (58), videoNode (34), videoPath (32), videoImage (28), videoPlayer (24), video (23), videoBorder (22), VideoPreloaderCtrl (16), videoAspectRatio (13), videoExist (13)
- `audioHelper`: PostEvent (596), AudioAdapter (487), AudioManager (147), voiceId (63), Audio (28), audioEvent (26), audioManager (19), audioKey (17), audioEventName (16), audioEventPlayingId (13)

## Focus: sns

- Files: `60`
- `tables`: sNSDialogTable (40), spaceshipConst (29), sNSChatTable (18), globalConst (15), sNSConst (9), itemTable (9), spaceshipMusicTable (9), businessCardTopicTable (8)
- `gEnums`: ActivityConditionalStageState.__CastFrom (13), ActivityStatus.InProgress (12), ActivityConditionalTaskState.__CastFrom (11), ActivityConditionalTaskState.Completed (11), ActivityConditionalStageState.Locked (9), ActivityConditionalStageState.Completed (9), SNSChatType.Group (7), AttributeType.Str (7)
- `csBeyond`: CS.Beyond.Gameplay.FriendBusinessCardUnlockType.BusinessCardTopic (8), CS.Beyond.EnableLogType.MainHudActionQueue (7), CS.Beyond.Gameplay.View.CharUIModelMono.WeaponState.HIDE (6), CS.Beyond.DebugDefines.disableCheckInLoginCheck (4), CS.Beyond.DLogger.FrameCountThreadSafe (4), CS.Beyond.Gameplay.RoleType.Self (4), CS.Beyond.Gameplay.MissionSystem.MissionType (3), CS.Beyond.Gameplay.RemoteFactory.RemoteFactoryBlueprintSourceType.Mine (3)
- `contentParam`: 0 (3), 1 (2)
- `loadSprite`: LoadSprite (39)
- `videoHelper`: Video (5), VideoCover (1), VideoPreview (1), VideoManager (1), videoManager (1), VideoPreloader (1)
- `audioHelper`: PostEvent (28), AudioAdapter (24), AudioManager (9), audioEvent (8), Audio (6), AudioDataContainer (2), audioManager (2), AudioMusicSystem (1)

Top files:
- `Common/Utils/SNSUtils.lua` hits=`72` roots=`LuaScripts`
  - examples: path SNSUtils; L1 SNSUtils; L3 SNSUtils
- `Phase/SNS/PhaseSNS.lua` hits=`35` roots=`LuaScripts`
  - examples: path SNS; path PhaseSNS; L3 SNS
- `UI/Widgets/SNSDialogContentCore.lua` hits=`35` roots=`LuaScripts`
  - examples: L18 sns; L18 sns; L28 SNSUtils
- `UI/Panels/PanelConfig.lua` hits=`26` roots=`LuaScripts`
  - examples: L6799 Friend; L6817 Friend; L6835 Friend
- `UI/Panels/SNSBarker/SNSBarkerCtrl.lua` hits=`20` roots=`LuaScripts`
  - examples: L106 sNSDialogTable; L108 sNSDialogTable; L136 sNSDialogTable
- `UI/Panels/SNSHud/SNSHudCtrl.lua` hits=`14` roots=`LuaScripts`
  - examples: L34 PhaseSNS; L38 PhaseSNS; L101 sNSChatTable
- `UI/RedDot/RedDotConfig.lua` hits=`13` roots=`LuaScripts`
  - examples: L1602 sns; L1617 sns; L1632 SNSUtils
- `UI/Panels/SNSMission/SNSMissionCtrl.lua` hits=`11` roots=`LuaScripts`
  - examples: L60 sNSDialogTable; L71 sNSDialogTable; L72 sns
- `Const/UIConst.lua` hits=`10` roots=`LuaScripts`
  - examples: L10 Friend; L34 SNS; L35 SNS
- `Common/Utils/FriendUtils.lua` hits=`9` roots=`LuaScripts`
  - examples: L513 SNS; L518 SNS; L528 SNS
- `UI/Widgets/SNSDialogContentCoreCell.lua` hits=`9` roots=`LuaScripts`
  - examples: L51 sNSDialogTable; L82 sNSChatTable; L93 sNSChatTable
- `UI/Panels/Watch/WatchCtrl.lua` hits=`7` roots=`LuaScripts`
  - examples: L28 FRIEND; L40 SNS; L118 FRIEND
- `UI/Widgets/SNSContactNpcCell.lua` hits=`7` roots=`LuaScripts`
  - examples: L33 sNSChatTable; L34 sns; L79 sns
- `UI/Widgets/SNSSubDialogCell.lua` hits=`7` roots=`LuaScripts`
  - examples: L62 sNSDialogTable; L76 sns; L84 sNSChatTable
- `UI/Widgets/SNSMissionRelatedDialogCell.lua` hits=`6` roots=`LuaScripts`
  - examples: L40 sNSDialogTable; L42 sNSChatTable; L66 SNSUtils
- `Const/QuickMenuConst.lua` hits=`5` roots=`LuaScripts`
  - examples: L8 sns; L8 sns; L63 sns
- `Phase/PhaseConfig.lua` hits=`5` roots=`LuaScripts`
  - examples: L432 SNS; L437 SNS; L444 sns
- `UI/Panels/SeasonTowerScoreReview/SeasonTowerScoreReviewCtrl.lua` hits=`5` roots=`LuaScripts`
  - examples: L10 friend; L44 friend; L62 friend
- `UI/Panels/FriendList/FriendListCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: L47 Friend; L137 friend; L204 Friend
- `UI/Panels/Mission/MissionCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: L1583 SNS; L1584 SNS; L1586 SNS
- `UI/Widgets/FriendDialogueSendArea.lua` hits=`4` roots=`LuaScripts`
  - examples: L462 SNS; L462 Friend; L471 SNS
- `UI/Widgets/SNSContentVote.lua` hits=`4` roots=`LuaScripts`
  - examples: L49 SNSUtils; L57 sNSChatTable; L81 sns
- `UI/Widgets/SNSContentWithEmojiComp.lua` hits=`4` roots=`LuaScripts`
  - examples: L76 SNSUtils; L82 sNSChatTable; L107 sNSDialogTable
- `UI/Panels/SNSBarkerSide/SNSBarkerSideCtrl.lua` hits=`3` roots=`LuaScripts`
  - examples: L49 sns; L53 sns; L71 SNSUtils
- `UI/Panels/SNSFriend/SNSFriendCtrl.lua` hits=`3` roots=`LuaScripts`
  - examples: L83 Friend; L225 Friend; L334 Friend
- `UI/Panels/SpaceShipFriendHelpList/SpaceShipFriendHelpListCtrl.lua` hits=`3` roots=`LuaScripts`
  - examples: L32 Friend; L127 Friend; L128 Friend
- `Init.lua` hits=`2` roots=`LuaScripts`
  - examples: L256 SNSUtils; L256 SNSUtils
- `Phase/Friend/PhaseFriend.lua` hits=`2` roots=`LuaScripts`
  - examples: path Friend; L2 Friend
- `Phase/Level/PhaseLevel.lua` hits=`2` roots=`LuaScripts`
  - examples: L1151 sns; L1291 sns
- `UI/Panels/BlueprintShareBlackScreen/BlueprintShareBlackScreenCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L105 Friend; L142 SNS

## Focus: remotecomm

- Files: `37`
- `tables`: dungeonConst (18), itemTable (9), radioTable (7), factoryBuildingTable (6), systemJumpTable (5), domainDataTable (5), cinematicConst (5), prtsAllItem (4)
- `gEnums`: AttributeType.Str (7), AttributeType.Agi (7), AttributeType.Wisd (7), AttributeType.Will (7), AttributeType.MaxHp (7), AttributeType.Atk (7), UnlockSystemType.PRTS (6), AttributeType.Def (5)
- `csBeyond`: CS.Beyond.EnableLogType.MainHudActionQueue (7), CS.Beyond.Gameplay.View.CharUIModelMono.WeaponState.HIDE (6), CS.Beyond.EnableLogType.DevOnly (5), CS.Beyond.Gameplay.Scope.Create (4), CS.Beyond.DebugDefines.disableCheckInLoginCheck (4), CS.Beyond.Gameplay.CheckHasInteractOption.Update (4), CS.Beyond.Gameplay.View.VideoManager.TryGetVideoPlayFullPath (4), CS.Beyond.Gameplay.SettlementSystem.EOrderSubmitState.None (3)
- `loadSprite`: LoadSprite (20), UIUtils.getSpritePath (3)
- `videoHelper`: videoImage (26), videoKey (8), VideoManager (4), VideoPreloader (3), videoAnimationWrapper (2), VideoCover (1), VideoPreview (1)
- `audioHelper`: voiceId (37), audioEventPlayingId (13), AudioAdapter (13), PostEvent (12), audioId (9), audioEvent (6), audioEffect (6), Audio (6)

Top files:
- `LuaSystem/RadioSystem.lua` hits=`194` roots=`LuaScripts`
  - examples: path RadioSystem; L2 RadioSystem; L2 RadioSystem
- `UI/Panels/RemoteComm/RemoteCommCtrl.lua` hits=`80` roots=`LuaScripts`
  - examples: path RemoteComm; path RemoteComm; L2 RemoteComm
- `Phase/RemoteComm/PhaseRemoteComm.lua` hits=`70` roots=`LuaScripts`
  - examples: path RemoteComm; path RemoteComm; L2 RemoteComm
- `UI/Panels/RemoteCommHud/RemoteCommHudCtrl.lua` hits=`70` roots=`LuaScripts`
  - examples: path RemoteComm; path RemoteComm; L2 RemoteComm
- `UI/Widgets/PRTSRadio.lua` hits=`32` roots=`LuaScripts`
  - examples: L23 radioTextList; L24 radioTextList; L28 radioTextList
- `UI/Panels/Radio/RadioCtrl.lua` hits=`27` roots=`LuaScripts`
  - examples: path Radio; path RadioCtrl; L2 Radio
- `UI/Panels/Dialog/DialogCtrl.lua` hits=`24` roots=`LuaScripts`
  - examples: L132 radioNode; L132 radioNode; L133 radioNode
- `UI/Widgets/CustomRewardRadioComp.lua` hits=`16` roots=`LuaScripts`
  - examples: L24 radioPartOneBtn; L28 radioPartTwoBtn; L59 radioPartOneTxt
- `UI/Panels/PanelConfig.lua` hits=`11` roots=`LuaScripts`
  - examples: L9878 Radio; L9880 Radio; L9896 RadioEmpty
- `UI/Panels/RadioEmpty/RadioEmptyCtrl.lua` hits=`11` roots=`LuaScripts`
  - examples: path RadioEmpty; path RadioEmptyCtrl; L3 RadioEmpty
- `Const/MessageConst.lua` hits=`9` roots=`LuaScripts`
  - examples: L1050 REMOTE_COMM; L1051 REMOTE_COMM; L1052 REMOTE_COMM
- `Phase/ReadingPopUp/PhaseReadingPopUp.lua` hits=`9` roots=`LuaScripts`
  - examples: L29 radioId; L30 radioTitle; L39 radioTitle
- `Phase/Level/PhaseLevelConfig.lua` hits=`8` roots=`LuaScripts`
  - examples: L31 RadioEmpty; L72 Radio; L85 RadioEmpty
- `UI/Panels/RemoteCommBG/RemoteCommBGCtrl.lua` hits=`8` roots=`LuaScripts`
  - examples: path RemoteComm; path RemoteComm; L3 RemoteComm
- `LuaSystem/LuaSystemManager.lua` hits=`4` roots=`LuaScripts`
  - examples: L26 radioSystem; L26 RadioSystem; L56 radioSystem
- `Phase/Level/PhaseLevel.lua` hits=`4` roots=`LuaScripts`
  - examples: L113 radio; L113 Radio; L114 radio
- `Phase/PhaseConfig.lua` hits=`4` roots=`LuaScripts`
  - examples: L414 RemoteComm; L417 RemoteComm; L418 RemoteComm
- `UI/Panels/DungeonCustomReward/DungeonCustomRewardCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: L123 radioIndex; L124 radioIndex; L161 radioIndex
- `UI/Panels/WorldEnergyPointCustomReward/WorldEnergyPointCustomRewardCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: L171 radioIndex; L172 radioIndex; L252 radioIndex
- `Const/UIConst.lua` hits=`3` roots=`LuaScripts`
  - examples: L83 REMOTE_COMM; L83 RemoteComm; L1373 REMOTE_COMM
- `UI/Panels/PRTSInvestigateReport/PRTSInvestigateReportCtrl.lua` hits=`3` roots=`LuaScripts`
  - examples: L13 Radio; L71 Radio; L127 Radio
- `Const/InputDeviceChangeConst.lua` hits=`2` roots=`LuaScripts`
  - examples: L123 Radio; L124 RadioEmpty
- `Const/PhaseConst.lua` hits=`2` roots=`LuaScripts`
  - examples: L31 RadioEmpty; L61 Radio
- `LuaSystem/CinematicSystem.lua` hits=`2` roots=`LuaScripts`
  - examples: L79 RemoteComm; L80 RemoteComm
- `Phase/FacMachine/PhaseFacMachine.lua` hits=`2` roots=`LuaScripts`
  - examples: L54 RadioRuntimeData; L54 radioId
- `UI/Panels/InteractOption/InteractOptionCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L699 RadioRuntimeData; L699 radioId
- `UI/Panels/PRTSStoryCollDetail/PRTSStoryCollDetailCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L12 Radio; L206 Radio
- `UI/Panels/Reading/ReadingCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L107 radioCfg; L107 radioTable
- `UI/Panels/ReadingPopUp/ReadingPopUpCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L61 radioId; L62 radioId
- `Common/Core/BackgroundMessage.lua` hits=`1` roots=`LuaScripts`
  - examples: L658 RemoteComm

## Focus: dialog

- Files: `35`
- `tables`: sNSDialogTable (21), sNSChatTable (11), sNSConst (9), itemTable (8), systemJumpTable (5), sNSDialogOptionTable (5), domainDataTable (4), levelDescTable (4)
- `gEnums`: AttributeType.Str (7), AttributeType.Agi (7), AttributeType.Wisd (7), AttributeType.Will (7), AttributeType.MaxHp (7), AttributeType.Atk (7), UnlockSystemType.PRTS (6), SNSDialogOptionType.None (5)
- `csBeyond`: CS.Beyond.Gameplay.View.CharUIModelMono.WeaponState.HIDE (6), CS.Beyond.Gameplay.Scope.Create (4), CS.Beyond.Gameplay.MissionSystem.MissionType (4), CS.Beyond.EnableLogType.MainHudActionQueue (4), CS.Beyond.Gameplay.View.VideoManager.TryGetVideoPlayFullPath (4), CS.Beyond.EnableLogType.DevOnly (3), CS.Beyond.Gameplay.SettlementSystem.EOrderSubmitState.None (3), CS.Beyond.Gameplay.CharUtils (3)
- `contentParam`: 0 (8), 1 (5)
- `loadSprite`: LoadSprite (34), UIUtils.getSpritePath (3)
- `videoHelper`: videoImage (26), videoBorder (22), videoKey (8), Video (5), VideoManager (5), VideoPreloader (4), videoName (3), videoAnimationWrapper (2)
- `audioHelper`: AudioAdapter (27), PostEvent (24), voiceId (12), audioId (9), Audio (6), audioEvent (6), AudioManager (2), AudioDataContainer (2)

Top files:
- `UI/Widgets/FriendDialogueSendArea.lua` hits=`44` roots=`LuaScripts`
  - examples: path Dialogue; L3 Dialogue; L3 Dialogue
- `UI/Panels/RemoteComm/RemoteCommCtrl.lua` hits=`17` roots=`LuaScripts`
  - examples: L169 middleId; L169 middleId; L170 middleId
- `Phase/Dialog/PhaseDialog.lua` hits=`12` roots=`LuaScripts`
  - examples: path Dialog; L2 Dialog; L75 DialogConst
- `UI/Panels/PanelConfig.lua` hits=`12` roots=`LuaScripts`
  - examples: L4349 Dialog; L4350 Dialog; L4366 Dialog
- `UI/Panels/SNSFriend/SNSFriendCtrl.lua` hits=`11` roots=`LuaScripts`
  - examples: L111 Dialogue; L112 Dialogue; L113 Dialogue
- `UI/Panels/ReflowFormalDialogue/ReflowFormalDialogueCtrl.lua` hits=`10` roots=`LuaScripts`
  - examples: path Dialogue; path Dialogue; L2 Dialogue
- `UI/Widgets/SNSContentVoice.lua` hits=`10` roots=`LuaScripts`
  - examples: L54 contentParam; L54 contentParam; L55 contentParam
- `Common/Utils/SNSUtils.lua` hits=`8` roots=`LuaScripts`
  - examples: L117 contentParam; L118 contentParam; L124 contentParam
- `Const/UIConst.lua` hits=`4` roots=`LuaScripts`
  - examples: L439 Dialog; L442 Dialog; L443 Dialog
- `UI/Panels/Dialog/DialogCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: path Dialog; L1 Dialog; L3 Dialog
- `UI/Panels/Mission/MissionCtrl.lua` hits=`4` roots=`LuaScripts`
  - examples: L1576 Dialog; L1580 Dialog; L1587 Dialog
- `UI/Widgets/FriendDialogContent.lua` hits=`4` roots=`LuaScripts`
  - examples: L161 Dialogue; L161 Dialogue; L315 Dialogue
- `UI/Widgets/SNSContentPRTS.lua` hits=`4` roots=`LuaScripts`
  - examples: L6 contentParam; L6 contentParam; L7 contentParam
- `UI/Widgets/SNSDialogContentCore.lua` hits=`4` roots=`LuaScripts`
  - examples: L605 dialogContentData; L830 dialogContentData; L1427 dialogContentData
- `UI/Widgets/RichContent.lua` hits=`3` roots=`LuaScripts`
  - examples: L70 ContentParam; L71 ContentParam; L72 ContentParam
- `UI/Widgets/SNSDialogContentCoreCell.lua` hits=`3` roots=`LuaScripts`
  - examples: L52 dialogContentData; L173 dialogContentData; L263 dialogContentData
- `Init.lua` hits=`2` roots=`LuaScripts`
  - examples: L235 DialogConst; L235 DialogConst
- `Phase/PhaseConfig.lua` hits=`2` roots=`LuaScripts`
  - examples: L45 Dialog; L49 Dialog
- `UI/Panels/Dialog/DialogCtrlBase.lua` hits=`2` roots=`LuaScripts`
  - examples: path Dialog; L153 dialogue
- `UI/Panels/DialogTimeline/DialogTimelineCtrl.lua` hits=`2` roots=`LuaScripts`
  - examples: L1 Dialog; L54 Dialog
- `UI/Widgets/SNSContentCard.lua` hits=`2` roots=`LuaScripts`
  - examples: L6 contentParam; L7 contentParam
- `UI/Widgets/SNSContentVideo.lua` hits=`2` roots=`LuaScripts`
  - examples: L6 contentParam; L9 contentParam
- `UI/Widgets/SNSContentWithEmojiComp.lua` hits=`2` roots=`LuaScripts`
  - examples: L107 dialogContentData; L157 contentParam
- `Common/Core/BackgroundMessage.lua` hits=`1` roots=`LuaScripts`
  - examples: L44 Dialog
- `Common/Utils/Utils.lua` hits=`1` roots=`LuaScripts`
  - examples: L558 Dialog
- `Const/DialogConst.lua` hits=`1` roots=`LuaScripts`
  - examples: path DialogConst
- `Const/InputDeviceChangeConst.lua` hits=`1` roots=`LuaScripts`
  - examples: L54 Dialog
- `LuaSystem/CinematicSystem.lua` hits=`1` roots=`LuaScripts`
  - examples: L73 Dialog
- `Phase/ReflowPopup/PhaseReflowPopup.lua` hits=`1` roots=`LuaScripts`
  - examples: L20 Dialogue
- `UI/Widgets/SNSContentBase.lua` hits=`1` roots=`LuaScripts`
  - examples: L25 dialogContentData

## Focus: mapmark

- Files: `93`
- `tables`: itemTable (49), dungeonTable (32), domainDataTable (28), rewardTable (24), spaceshipConst (22), mapMarkTempTable (16), levelDescTable (13), gameMechanicTable (10)
- `gEnums`: ActivityStatus.InProgress (13), ActivityConditionalStageState.__CastFrom (13), ActivityConditionalTaskState.__CastFrom (11), ActivityConditionalTaskState.Completed (11), DomainPoiType.DomainShop (9), ActivityConditionalStageState.Locked (9), ActivityConditionalStageState.Completed (9), DungeonCategoryType.MiniBossRush (8)
- `csBeyond`: CS.Beyond.Gameplay.MissionSystem.QuestState.Completed (7), CS.Beyond.Gameplay.View.CharUIModelMono.WeaponState.HIDE (6), CS.Beyond.Gameplay.MarkLineType.Power (5), CS.Beyond.UI.UIScrollRect (5), CS.Beyond.Gameplay.MarkLineType.Travel (4), CS.Beyond.UI.UIConst.AnimationState.In (4), CS.Beyond.DLogger.FrameCountThreadSafe (4), CS.Beyond.Gameplay.UILevelMapStaticElementType.FacMainRegion (3)
- `loadSprite`: LoadSprite (66), UIUtils.getSpritePath (4), LoadSpriteAsync (2)
- `videoHelper`: VideoPreloader (2), VideoCover (1), VideoPreview (1), VideoManager (1), videoManager (1)
- `audioHelper`: PostEvent (28), AudioAdapter (25), AudioManager (7), Audio (5), audioKey (4), AudioDataContainer (2), audioEventSystem (2), AudioEventLuaSystem (2)

Top files:
- `Phase/Map/PhaseMap.lua` hits=`102` roots=`LuaScripts`
  - examples: L4 MarkType; L4 MarkType; L11 MarkType
- `UI/Widgets/LevelMapMark.lua` hits=`89` roots=`LuaScripts`
  - examples: path MapMark; L4 MapMark; L4 MapMark
- `Common/Utils/MapUtils.lua` hits=`69` roots=`LuaScripts`
  - examples: path MapUtils; L1 MapUtils; L6 MapUtils
- `UI/Panels/Map/MapCtrl.lua` hits=`46` roots=`LuaScripts`
  - examples: L3 MapMark; L3 MapMark; L175 MAP_MARK
- `UI/Panels/PanelConfig.lua` hits=`39` roots=`LuaScripts`
  - examples: L8403 MapMark; L8421 MapMark; L8438 MapMark
- `UI/Widgets/MapMarkDetailCommon.lua` hits=`38` roots=`LuaScripts`
  - examples: path MapMark; L3 MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailSocialBuilding/MapMarkDetailSocialBuildingCtrl.lua` hits=`36` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L4 MapMark
- `UI/Widgets/LevelMapLoader.lua` hits=`30` roots=`LuaScripts`
  - examples: L3 MapUtils; L3 MapUtils; L205 MAP_MARK
- `Common/Utils/DomainPOIUtils.lua` hits=`28` roots=`LuaScripts`
  - examples: L807 mapMark; L843 mapMark; L843 MarkType
- `UI/Panels/MapMarkDetail/MapMarkDetailCtrl.lua` hits=`28` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L2 MapMark
- `UI/Panels/MapMarkDetailBossRush/MapMarkDetailBossRushCtrl.lua` hits=`28` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L2 MapMark
- `UI/Panels/MapMarkDetailDungeon/MapMarkDetailDungeonCtrl.lua` hits=`25` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailDungeonSS/MapMarkDetailDungeonSSCtrl.lua` hits=`24` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailEnemySpawner/MapMarkDetailEnemySpawnerCtrl.lua` hits=`24` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailRecycleBin/MapMarkDetailRecycleBinCtrl.lua` hits=`21` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L2 MapMark
- `UI/Panels/MapMarkDetailDomainShop/MapMarkDetailDomainShopCtrl.lua` hits=`19` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `LuaSystem/MapResourceSystem.lua` hits=`18` roots=`LuaScripts`
  - examples: path MapResource; L3 MapResource; L3 MapResource
- `UI/Panels/DomainPOIOverview/DomainPOIOverviewCtrl.lua` hits=`18` roots=`LuaScripts`
  - examples: L129 MapMark; L129 mapMark; L130 MapUtils
- `UI/Panels/MapCustomMarkDetail/MapCustomMarkDetailCtrl.lua` hits=`18` roots=`LuaScripts`
  - examples: L19 markType; L22 MAP_MARK; L34 MAP_MARK
- `UI/Panels/MapDetectPopUp/MapDetectPopUpCtrl.lua` hits=`18` roots=`LuaScripts`
  - examples: L69 MapMark; L70 MapMark; L71 MapMark
- `UI/Panels/MapMarkDetailContingencyContract/MapMarkDetailContingencyContractCtrl.lua` hits=`18` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailInvalidBuilding/MapMarkDetailInvalidBuildingCtrl.lua` hits=`16` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L2 MapMark
- `UI/Panels/MapMarkDetailSettlement/MapMarkDetailSettlementCtrl.lua` hits=`16` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailCoin/MapMarkDetailCoinCtrl.lua` hits=`15` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L2 MapMark
- `UI/Panels/MapMarkDetailDoodadGroup/MapMarkDetailDoodadGroupCtrl.lua` hits=`15` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailMission/MapMarkDetailMissionCtrl.lua` hits=`15` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailUndergroundPipe/MapMarkDetailUndergroundPipeCtrl.lua` hits=`15` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailCampFire/MapMarkDetailCampFireCtrl.lua` hits=`14` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailGasMinePointTeam/MapMarkDetailGasMinePointTeamCtrl.lua` hits=`14` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark
- `UI/Panels/MapMarkDetailMinePointTeam/MapMarkDetailMinePointTeamCtrl.lua` hits=`14` roots=`LuaScripts`
  - examples: path MapMark; path MapMark; L3 MapMark

## Focus: mission

- Files: `111`
- `tables`: itemTable (73), spaceshipConst (39), dungeonTable (36), domainDataTable (33), activityConst (29), sNSDialogTable (24), rewardTable (23), gameMechanicTable (17)
- `gEnums`: ActivityConditionalTaskState.Completed (26), ActivityConditionalStageState.Completed (24), ActivityConditionalStageState.Locked (24), ActivityConditionalStageState.Rewarded (20), ActivityConditionalTaskState.__CastFrom (20), ActivityConditionalStageState.Unlocked (19), ActivityConditionalStageState.__CastFrom (18), ActivityStatus.InProgress (13)
- `csBeyond`: CS.Beyond.EnableLogType.MainHudActionQueue (25), CS.Beyond.Gameplay.MissionSystem.QuestState.Completed (14), CS.Beyond.Gameplay.MissionSystem.MissionState.Completed (14), CS.Beyond.Gameplay.View.CharUIModelMono.WeaponState.HIDE (13), CS.Beyond.Gameplay.MissionSystem.MissionState.Processing (10), CS.Beyond.Gameplay.MissionSystem.MissionState (9), CS.Beyond.MainHudActionQueueConsts.CINEMATIC_ORDER_FIRST (9), CS.Beyond.EnableLogType.DevOnly (6)
- `contentParam`: 0 (3), 1 (1)
- `loadSprite`: LoadSprite (147), UIUtils.getSpritePath (2), LoadSpriteAsync (1)
- `videoHelper`: videoNode (23), videoPath (13), Video (5), videoPlayer (5), VideoPreloader (3), videoExist (2), playVideoPath (2), VideoCover (1)
- `audioHelper`: PostEvent (108), AudioAdapter (79), AudioManager (34), audioKey (8), audioEvent (6), Audio (4), audioOnOpen (4), AUDIO_SWITCH_TAB_EVENT (4)

Top files:
- `UI/Panels/CommonTaskTrackHud/CommonTaskTrackHudCtrl.lua` hits=`146` roots=`LuaScripts`
  - examples: path TaskTrack; path TaskTrack; L3 TaskTrack
- `UI/Panels/Mission/MissionCtrl.lua` hits=`76` roots=`LuaScripts`
  - examples: path Mission; L3 Mission; L4 Mission
- `UI/Panels/CommonTaskTrackToast/CommonTaskTrackToastCtrl.lua` hits=`62` roots=`LuaScripts`
  - examples: path TaskTrack; path TaskTrack; L3 TaskTrack
- `UI/Panels/WeeklyRaidTaskTrackHud/WeeklyRaidTaskTrackHudCtrl.lua` hits=`59` roots=`LuaScripts`
  - examples: path TaskTrack; path TaskTrack; L2 TaskTrack
- `UI/Panels/MissionHud/MissionHudCtrl.lua` hits=`47` roots=`LuaScripts`
  - examples: L6 MissionSystem; L7 MissionSystem; L10 MissionSystem
- `UI/Panels/CommonTaskTrackCountdown/CommonTaskTrackCountdownCtrl.lua` hits=`41` roots=`LuaScripts`
  - examples: path TaskTrack; path TaskTrack; L2 TaskTrack
- `UI/Panels/WorldLevelUp/WorldLevelUpCtrl.lua` hits=`41` roots=`LuaScripts`
  - examples: L11 MissionSystem; L12 MissionSystem; L22 missionSystem
- `LuaSystem/CommonTaskTrackSystem.lua` hits=`38` roots=`LuaScripts`
  - examples: path TaskTrack; L9 TaskTrack; L9 TaskTrack
- `UI/Panels/ActivityHighDifficulty/ActivityHighDifficultyCtrl.lua` hits=`32` roots=`LuaScripts`
  - examples: L63 task; L64 task; L65 task
- `UI/Panels/ActivityDevelopReturn/ActivityDevelopReturnCtrl.lua` hits=`30` roots=`LuaScripts`
  - examples: L79 task; L80 task; L139 task
- `UI/Panels/ActivityWeeklyTask/ActivityWeeklyTaskCtrl.lua` hits=`25` roots=`LuaScripts`
  - examples: L84 task; L87 task; L90 task
- `UI/Widgets/CommonTaskGoalCell.lua` hits=`22` roots=`LuaScripts`
  - examples: L10 tasktrack; L11 tasktrack; L12 tasktrack
- `UI/Panels/ActivityStaminaDiscount/ActivityStaminaDiscountCtrl.lua` hits=`20` roots=`LuaScripts`
  - examples: L143 task; L154 task; L154 task
- `UI/Panels/MapMarkDetailMission/MapMarkDetailMissionCtrl.lua` hits=`15` roots=`LuaScripts`
  - examples: L9 Mission; L27 missionSystem; L27 mission
- `UI/Panels/DungeonWeeklyRaid/DungeonWeeklyRaidCtrl.lua` hits=`14` roots=`LuaScripts`
  - examples: L84 Mission; L106 mission; L106 MissionSystem
- `UI/Panels/PanelConfig.lua` hits=`14` roots=`LuaScripts`
  - examples: L2904 TaskTrack; L3914 TaskTrack; L3915 TaskTrack
- `UI/Panels/BlackBoxDiffBtn/BlackBoxDiffBtnCtrl.lua` hits=`12` roots=`LuaScripts`
  - examples: L34 TaskTrack; L67 taskTrack; L67 TaskTrack
- `UI/Panels/SnapshotRewardTask/SnapshotRewardTaskCtrl.lua` hits=`12` roots=`LuaScripts`
  - examples: L4 missionSystem; L4 mission; L73 missionSystem
- `UI/Panels/BattlePassTask/BattlePassTaskCtrl.lua` hits=`11` roots=`LuaScripts`
  - examples: L77 TASK; L112 TASK; L131 TASK
- `UI/Panels/SimulationTrainingTrackHud/SimulationTrainingTrackHudCtrl.lua` hits=`11` roots=`LuaScripts`
  - examples: L25 tasktrack; L26 tasktrack; L27 tasktrack
- `Common/Utils/Utils.lua` hits=`10` roots=`LuaScripts`
  - examples: L1409 mission; L1410 MissionSystem; L1418 missionSystem
- `Phase/Level/PhaseLevel.lua` hits=`10` roots=`LuaScripts`
  - examples: L94 TaskTrack; L625 TaskTrack; L638 TaskTrack
- `UI/Panels/RiftDetailInfo/RiftDetailInfoCtrl.lua` hits=`10` roots=`LuaScripts`
  - examples: L4 MissionSystem; L5 MissionSystem; L28 missionSystem
- `UI/Panels/CommonPOIUpgrade/CommonPOIUpgradeCtrl.lua` hits=`9` roots=`LuaScripts`
  - examples: L683 mission; L691 mission; L722 MissionSystem
- `UI/Widgets/BusinessCardProcessNode.lua` hits=`9` roots=`LuaScripts`
  - examples: L2 Mission; L3 Mission; L35 missionSystem
- `Common/Utils/DomainPOIUtils.lua` hits=`8` roots=`LuaScripts`
  - examples: L1225 MissionSystem; L1227 MissionSystem; L1229 mission
- `UI/Widgets/SNSDialogContentCore.lua` hits=`8` roots=`LuaScripts`
  - examples: L34 Task; L50 Task; L836 Task
- `Common/Utils/DungeonUtils.lua` hits=`7` roots=`LuaScripts`
  - examples: L78 mission; L79 Mission; L82 Mission
- `UI/Panels/MapMarkDetailDomainShop/MapMarkDetailDomainShopCtrl.lua` hits=`7` roots=`LuaScripts`
  - examples: L80 MissionSystem; L82 mission; L84 MissionSystem
- `UI/Panels/MissionCompletePop/MissionCompletePopCtrl.lua` hits=`7` roots=`LuaScripts`
  - examples: L5 MissionSystem; L7 Mission; L8 Mission

## Interpretation

- Lua scripts provide concrete consumer evidence for table rows, enum branches, CS API calls, and UI/media helpers. This report does not alter WebUI export behavior; it identifies where source graph or Story/WebUI builders can add edges next.
- Persistent and StreamingAssets Lua modules are expected to duplicate heavily. Use unique module counts for semantic coverage and root file counts for VFS coverage.
