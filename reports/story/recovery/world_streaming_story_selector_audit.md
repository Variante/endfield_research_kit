# World-streaming Story selector audit

## Scope

- target roots: 3; registered resource paths: 34
- exact byte patterns: 142 (142 identities)
- VFS blocks: `Streaming`, `DynamicStreaming`

The byte patterns cover each root and registered resource path as UTF-8/ASCII and UTF-16LE, plus both byte orders of every registered 64-bit StringPathHash value.

## Complete Unity-object indexes

- `StreamingAssets`: 1,218,871 objects / 1,018 MonoScripts / 0 ordered-system matches
- `Persistent`: 116,579 objects / 1,018 MonoScripts / 0 ordered-system matches

The match requires a resolved script/type name containing `Encounter`, `BattlerStage`, or `BossBattlerData`, or an exact distinctive serialized leaf such as `operaSegments`, `stageDataList`, or `completeDelayMode`.

## Skipped world-streaming bytes

- `streaming`: 53,206 files / 752,851,287 bytes / 0 exact hits / SHA-256 `4f5a28a2150568fdf1cafef5596728cdddb45cd155a178078acc4d74d71acb48`
- `persistent`: 53,206 files / 752,882,465 bytes / 0 exact hits / SHA-256 `5bf968c504a3a93a92879bdea6c64307ed84b633b8672329a3c1042c38280001`

## Conclusion

The complete current Unity-object indexes contain no typed Encounter/BattlerStage authoring object or distinctive nested field, and the skipped current world-streaming corpora contain no exact unresolved root, registered resource path, or StringPathHash representation.

This closes exact current client-side selectors in the audited Unity-object and world-streaming surfaces. It does not rule out compressed or transformed identities inside an unknown nested format, indirect runtime construction, server-provided state, or future build data. No file co-location or system capability may be promoted into mission ownership or chronology.
