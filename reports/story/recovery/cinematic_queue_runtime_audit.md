# Cinematic Queue Runtime Audit

- GameAssembly SHA-256: `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- IL2CPP metadata SHA-256: `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- queue base: `Beyond.Gameplay.Core.CinematicQueueItemDataBase`
- queue handle: `Beyond.Gameplay.Core.CinematicQueueManager+CinematicQueueItemHandle`
- native one-handle dispatchers: `7`
- polymorphic payload types: `7`
- native enqueue producers: `10`
- typed serialized action routes: `16`

## General Contract

Every queue item inherits the original `cinematicId` carrier and a typed `queueItemType` getter. The native queue manager allocates one handle, copies the item into its `data` field, and forwards that handle to Lua. Lua dispatches the same handle by queue type; these calls are runtime execution branches, not seven independently authored Story references.

## Native Dispatchers

- `Beyond.Gameplay.Actions.GameAction::DoPlayCutsceneByHandle` token=`0x06008057` VA=`0x1875e0620`
- `Beyond.Gameplay.Actions.GameAction::DoPlayDialogByHandle` token=`0x0600803a` VA=`0x1875e0818`
- `Beyond.Gameplay.Actions.GameAction::DoPlayForceSNSByHandle` token=`0x0600804a` VA=`0x1875e09f0`
- `Beyond.Gameplay.Actions.GameAction::PlayCGByHandle` token=`0x06008060` VA=`0x1875e68e4`
- `Beyond.Gameplay.Actions.GameAction::ShowNarrativeBlackScreenByHandle` token=`0x0600802c` VA=`0x1875ec3e8`
- `Beyond.Gameplay.Actions.GameAction::ShowUIReadingPopPanelByHandle` token=`0x060080ae` VA=`0x1875ec800`
- `Beyond.Gameplay.Actions.GameAction::StartRemoteCommByHandle` token=`0x06008065` VA=`0x1875edbfc`

## Payload Identity Accessors

- `Beyond.Gameplay.Core.CutsceneQueueItemData`: `get_cutsceneId`
- `Beyond.Gameplay.Core.DialogQueueItemData`: `get_dialogId`
- `Beyond.Gameplay.Core.FMVQueueItemData`: `get_videoId`
- `Beyond.Gameplay.Core.ForceSNSQueueItemData`: `get_chatId`
- `Beyond.Gameplay.Core.NarrativeBlackScreenQueueItemData`: none
- `Beyond.Gameplay.Core.ReadingPopQueueItemData`: `get_readingPopupId`
- `Beyond.Gameplay.Core.RemoteCommQueueItemData`: `get_remoteCommId`

## Original-Data Producer Join

- `Beyond.Gameplay.Actions.ComplexNarrativeBlackScreenAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::ShowNarrativeBlackScreen`
- `Beyond.Gameplay.Actions.NarrativeBlackScreenAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::ShowNarrativeBlackScreen`
- `Beyond.Gameplay.Actions.PlayCutsceneAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::PlayCutscene`
- `Beyond.Gameplay.Actions.PlayCutsceneIgnoreCinematicQueue::Execute` -> `Beyond.Gameplay.Actions.GameAction::PlayCutscene`
- `Beyond.Gameplay.Actions.PlayDialogAndHideSceneObjectAction::PlayCinematic` -> `Beyond.Gameplay.Actions.GameAction::StartDialog`
- `Beyond.Gameplay.Actions.PlayFmvAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::PlayFmv`
- `Beyond.Gameplay.Actions.PlayRemoteComm::Execute` -> `Beyond.Gameplay.Actions.GameAction::StartRemoteComm`
- `Beyond.Gameplay.Actions.ShowUIReadingPopPanel::Execute` -> `Beyond.Gameplay.Actions.GameAction::ShowUIReadingPopPanel`
- `Beyond.Gameplay.Actions.StartCutsceneAndControlSceneObjectAction::PlayCinematic` -> `Beyond.Gameplay.Actions.GameAction::PlayCutscene`
- `Beyond.Gameplay.Actions.StartCutsceneAndHideSceneObjectAction::PlayCinematic` -> `Beyond.Gameplay.Actions.GameAction::PlayCutscene`
- `Beyond.Gameplay.Actions.StartCutsceneAndTeleportAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::PlayCutscene`
- `Beyond.Gameplay.Actions.StartDialogAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::StartDialog`
- `Beyond.Gameplay.Actions.StartDialogAndTeleportAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::StartDialog`
- `Beyond.Gameplay.Actions.StartFmvAndTeleportAction::Execute` -> `Beyond.Gameplay.Actions.GameAction::PlayFmv`
- `Beyond.Gameplay.Actions.StartNarrativeBlackScreenAndTeleport::Execute` -> `Beyond.Gameplay.Actions.GameAction::ShowNarrativeBlackScreen`
- `Beyond.Gameplay.Actions.StartRemoteCommAndTeleport::Execute` -> `Beyond.Gameplay.Actions.GameAction::StartRemoteComm`

## Evidence Boundary

The original binary proves the handle and payload contract, but a Lua dispatcher call contains no static mission or quest identity. Mission ownership must be recovered from the serialized action row that calls the producer. Those exact LevelScript rows and their owning event/control paths may attach files to a mission; queue order and code address order create no Story-order edge.
