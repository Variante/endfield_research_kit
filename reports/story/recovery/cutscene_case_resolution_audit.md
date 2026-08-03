# Cutscene case-resolution audit

- Lua literal: `Cutscene_e0m0_1`
- Canonical Story key: `cutscene_e0m0_1`
- Native case resolution: **case_sensitive**
- Playback binding: **reject_case_mismatch_no_playback_binding**
- Mission ownership: **none**

## Build scope

- GameAssembly SHA-256: `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- Metadata SHA-256: `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- IFix patch SHA-256: `737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21`

## Proven native chain

- `Beyond.Gameplay.Actions.GameAction.PlayCutsceneAndGetHandle` `0x1875e6aac` calls `Beyond.Gameplay.Core.CutsceneManager.PlayCutscene` `0x186db94cc`.
- `Beyond.Gameplay.Core.CutsceneManager.PlayCutscene` `0x186db94cc` calls `Beyond.Gameplay.Core.CutsceneManager.CheckCanPlay` `0x186db8a94`.
- `Beyond.Gameplay.Core.CutsceneManager.CheckCanPlay` `0x186db8a94` calls `Beyond.Gameplay.NarrativeUtils.GetGenderedCutsceneId` `0x1835fd630`.
- `Beyond.Gameplay.Core.CutsceneManager.CheckCanPlay` `0x186db8a94` calls `Beyond.Gameplay.Core.CinematicTimelineManagerBase.TryGetCinematicData` `0x1848511c0`.
- `Beyond.Gameplay.Core.CinematicTimelineManagerBase.TryGetCinematicData` `0x1848511c0` calls `Beyond.Gameplay.Core.CinematicTimelineManagerBase._TryLoadCutsceneDataByName` `0x184495b60`.
- `Beyond.Gameplay.Core.CinematicTimelineManagerBase._TryLoadCutsceneDataByName` `0x184495b60` calls `Beyond.Resource.CachedPathAssetLoader.TryLoad` `0x18304bb40`.
- `Beyond.Resource.CachedPathAssetLoader.TryLoad` `0x18304bb40` calls `Beyond.Resource.CachedPathAssetLoader.TryLoad` `0x18304bbd0`.

The final typed loader converts the constructed path directly through `StringPathHash(string)`. The reviewed hash path receives and hashes the original string; neither it nor `GetGenderedCutsceneId` performs case folding.

## Conclusion

The original Lua spelling is preserved through gender selection and resource-path construction, then converted directly to StringPathHash without case folding. The mismatched spelling therefore cannot prove playback of the lowercase registry key in this build.

This rejects one playback edge for the reviewed installed build. It does not infer mission ownership, and it must be rerun and reviewed after any binary, metadata, Lua-audit, or IFix fingerprint changes.
