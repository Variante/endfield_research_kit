# The shipped HIRC parser, read out of the engine

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, audio lane.** The parser ships with the game, so the object types can be
read from the engine rather than guessed from bytes. That also settles, in the
negative, which types the engine never parses at all -- which is why the files
after this one rely on byte framing for those.

## THE NODE FRAME AND ITS CONTAINER TAILS, NAMED FROM THE SDK DESERIALIZER

The installed Wwise 2023.1.17 SDK ships `AkSoundEngine.lib` and `AkMusicEngine.lib`
with PDBs, so the version-150 readers can be disassembled with their own symbol
names and their virtual calls resolved through each class's vtable relocations
(recipe and annotated dumps: `scratch/reverse_engineering/wwise_sdk/`). This
supersedes every "anonymous group" statement below and in the reports: the group
letters remain the report keys, and the extents the corpus gates proved did not
move by a byte. What the read settled, in `CAkParameterNodeBase::SetNodeBaseParams`
call order:

| group | SDK reader | layout |
| --- | --- | --- |
| A | `CAkParameterNode::SetInitialFxParams` | `u8 bIsOverrideParentFX`, `u8 uNumFx`; if nonzero `u8 bitsFXBypass`, then `uNumFx` x `{u8 uFXIndex, u32 fxID, u8 flags}` (bit0 bypass, bit1 bIsShareSet, bit2 bIsRendered) -- the "mask byte plus six-byte slots" reading, confirmed |
| B | `SetInitialMetadataParams` | `u8 bOverrideParentMetadata`, `u8 uNumFx`, then `uNumFx` x `{u8 uFXIndex, u32 fxID, u8 bIsShareSet}` -- the unresolved width is **6** |
| -- | `SetNodeBaseParams` itself | `u32 OverrideBusId` (0 = none, resolved in the bus index), `u32 DirectParentID` (0 = none, `AddChildInternal`), `u8 byBitVector` (bit0 bPriorityOverrideParent, bit1 bPriorityApplyDistFactor, bits 2-5 MIDI overrides) -- the "nine anonymous scalars" |
| C, D | `CAkParameterNode::SetInitialParams` | `u8 cProps`, `cProps` x `u8 AkPropID`, `cProps` x `u32 value`; then the ranged bundle: `u8 cProps`, keys, `cProps` x `{f32 min, f32 max}` -- two parallel runs each, not interleaved pairs |
| E | `CAkParameterNodeBase::SetPositioningParams` | `u8 uBitsPositioning`: bit0 override, bit1 bHasListenerRelativeRouting, bits 2-3 panner type, bits 5-6 e3DPositionType. **Returns when bit0 is clear, then when bit1 is clear**, so the extension needs both: `u8 uBits3D`; then only for e3DPositionType 1 or 2: `u8 ePathMode`, `s32 TransitionTime`, `u32 n` x 16-byte `AkPathVertex`, `u32 m` x 8-byte playlist item, then `m` x 12-byte `{xRange,yRange,zRange}` |
| F | `CAkParameterNodeBase::SetAuxParams` | `u8 byBitVector` (bit0 bOverrideGameAuxSends, bit1 bUseGameAuxSends, bit2 bOverrideUserAuxSends, bit3 bHasAux, bit4 bOverrideReflectionsAuxBus); bit3 gates 4 x `u32 auxID`; then always `u32 reflectionsAuxBus` |
| G | `CAkParameterNode::SetAdvSettingsParams` | `u8 byBitVector` (bit0 bKillNewest, bit1 bUseVirtualBehavior, bit2 bIgnoreParentMaxNumInst, bit3 bIsGlobalLimit, bit4 bVVoicesOptOverrideParent), `u8 eVirtualQueueBehavior`, `u16 u16MaxNumInstance`, `u8 eBelowThresholdBehavior`, `u8 byBitVector2` |
| H | `CAkStateAware::ReadStateChunk` (through `CAkParamNodeStateAware`) | varint `ulNumStateProps` x `{varint AkPropID, u8 accumType, u8 inDb}`; varint `ulNumStateGroups` x `{u32 ulStateGroupID, u8 eStateSyncType, varint ulNumStates x {u32 ulStateID, u16 count, count x u16 AkPropID, count x u32 value}}` -- the "six-byte element" is one property as two parallel runs; the engine rejects a state whose ids are not strictly increasing |
| I | `AK::RTPC::ReadRtpcCurves<T>` | `u16 uNumCurves` x `{u32 RTPCID, u8 rtpcType, u8 rtpcAccum, varint ParamID, u32 rtpcCurveID, u8 eScaling, u16 ulSize x {f32 from, f32 to, u32 interp}}` |

Two reader corrections fell out. Every count in group H is a seven-bit continuation
value, and the corpus only ever spends one byte on each, so the byte widths were
degenerate cases again; the reader now reads varints there, pinned by fixture. And
the engine accumulates every varint **most-significant group first**
(`v = (v << 7) | (b & 0x7F)`), with no width cap, while the repo reader decodes
little-endian with a five-byte cap: extents agree, decoded multi-byte values do not,
and no value is published yet.

The five types that share the frame, and what each reads after it:

| type | class | after the node frame |
| --- | --- | --- |
| `0x02` | `CAkSound` | *before* the frame: `CAkBankMgr::LoadSource` -- `u32 ulPluginID`, `u8 StreamType` (0 in-bank, 1-2 streamed, else error), `u32 sourceID`, `u32 uInMemoryMediaSize`, `u8 uSourceBits` (bit0 bIsLanguageSpecific); if the plug-in type nibble is 2, `u32 uSize` + params. Then the frame, nothing after |
| `0x05` | `CAkRanSeqCntr` | `u16 sLoopCount, u16 sLoopModMin, u16 sLoopModMax, f32 fTransitionTime, f32 min, f32 max, u16 wAvoidRepeatCount, u8 eTransitionMode, u8 eRandomMode, u8 eMode` (1 = sequence), `u8 byBitVector` (bit1 bIsUsingWeight, bit2 bResetPlayListAtEachPlay, bit3 bIsRestartBackward, bit4 bIsContinuous) -- the 24-byte block; `u32 ulNumChilds` x `u32`; `u16 ulPlayListItem` x `{u32 ulPlayID, u32 weight}` (weight 50000 is the default) |
| `0x06` | `CAkSwitchCntr` | `u8 eGroupType` (1 = state), `u32 ulGroupID`, `u32 ulDefaultSwitch`, `u8 bIsContinuousValidation` -- the ten-byte head; `u32 ulNumChilds` x `u32`; `u32 ulNumSwitchGroups` x `{u32 ulSwitchID, u32 n x u32 nodeID}`; `u32 ulNumSwitchParams` x `{u32 ulNodeID, u8 bits (bIsFirstOnly, bContinuePlayback), u8 eOnSwitchMode, s32 FadeOutTime, s32 FadeInTime}`. The group items and param node ids are stored without an index lookup, which is why some never match a bank object |
| `0x07` | `CAkActorMixer` | `u32 ulNumChilds` x `u32` |
| `0x09` | `CAkLayerCntr` + `CAkLayer::SetInitialValues` | `u32 ulNumChilds` x `u32`; `u32 ulNumLayers` x `{u32 ulLayerID, InitialRTPC (group I, same template), u32 rtpcID, u8 rtpcType, u32 ulNumAssoc x {u32 ulAssociatedChildID, u32 ulCurveSize x 12-byte points}}`; `u8 bIsContinuousValidation`. The "sub-list inside the layer header" that fenced four bodies was the layer's own curve list |

`0x09` is now a shipped body lane (`hirc_type09_body_current_latest`), framed by the
same census as the other four; its child ids are not yet offered to the reference
graph, which is a deliberate separate step because it changes the published edge
counts. The game DLL addresses recorded further down map onto these symbols:
`0x1800dcfd0` is `SetNodeBaseParams`, `0x180160450` is
`CAkLayerCntr::SetInitialValues`, and the vtable slots differ from the stock SDK
(`+0x1f0/+0x1f8/+0x200` there against `+0x218/+0x220/+0x228` here), which is the
in-house modification showing through without changing the byte layout.

**The music types are framed from the same witness, and all four close.**
`AkMusicEngine.lib` reads them through `AkMusicBank::LoadBankItem`, the hook the
sound engine's dispatch consults before skipping a music payload (see the section
on `0x0A`-`0x0D` below: the shipped game DLL carries no music-engine strings, so
the earlier reading that it skips them stands, and the layouts are the SDK's).
`CAkMusicNode::SetMusicNodeParams` is `u8 uFlags`, then the node frame -- the
music types **do** open with it, one byte in, which is why every offset-0 attempt
failed -- then `u32` children, the 23-byte `AkMeterInfo` (`f64 fGridPeriod, f64
fGridOffset, f32 fTempo, u8 beats/bar, u8 beat value, u8 flag`) and `u32` stingers
of 24 bytes (`u32 TriggerID, u32 SegmentID, u32 SyncPlayAt, u32 uCueFilterHash, s32
DontRepeatTime, u32 numSegmentLookAhead`). `CAkMusicTransAware::SetMusicTransNodeParams`
adds `u32` rules of `{u32 n x u32 srcID, u32 m x u32 dstID, 21-byte source rule,
26-byte destination rule, u8 bAllocTransObjectFlag [+ 30-byte transition object]}`.

| type | class | after that |
| --- | --- | --- |
| `0x0A` | `CAkMusicSegment` | `f64 fDuration`; `u32` markers of `{u32 id, f64 fPosition, NUL-terminated name}` -- the variable-length name is why no stride ever fit, and the "names at fixed distances from the end" were these |
| `0x0B` | `CAkMusicTrack` | **the node frame comes last here**: `u8 uFlags`; `u32` sources x the type `0x02` source record (`CAkBankMgr::LoadSource`, plug-in params included); `u32` playlist items of 44 bytes (`u32 trackID, u32 sourceID, u32 eventID, f64 fPlayAt, f64 fBeginTrimOffset, f64 fEndTrimOffset, f64 fSrcDuration`); `u32 numSubTrack` **only when the playlist is nonempty** (two shipped bodies have none); `u32` clip automations of `{u32 uClipIndex, u32 eAutoType, u32 n x 12-byte points}`; the node frame; `u8 eTrackType`, and for type 3 `u8 eGroupType, u32 uGroupID, u32 uDefaultSwitch, u32 n x u32 assoc` plus a 32-byte transition block; `s32 iLookAheadTime` -- the "terminator, always 100" was this |
| `0x0C` | `CAkMusicSwitchCntr` | transition rules; `u8 bIsContinuePlayback`; `u32 uTreeDepth`, that many `u32` group ids then that many `u8` group types; `u32 uTreeDataSize`, `u8 uMode`, the tree bytes handed whole to `AkDecisionTree::SetTree` (12-byte nodes, not framed here) |
| `0x0D` | `CAkMusicRanSeqCntr` | transition rules; `u32` playlist items of 30 bytes (`u32 SegmentID, u32 playlistItemID, u32 NumChildren, u32 eRSType, s16 Loop, s16 LoopMin, s16 LoopMax, u32 Weight, u16 wAvoidRepeatCount, u8 bIsUsingWeight, u8 bIsShuffle`), nested by `NumChildren` in the engine and read flat |

All four are shipped lanes (`hirc_type0a/0b/0c/0d_body_current_latest`): 4,158,
4,325, 742 and 2,431 bodies, every one exact. The earlier fitted `0x0B` census
(`type11*` in the reader and the former `audio_hirc_curves.md`) is removed: every
"entry header", "element", "trailer" and "step-back" in that reading was a
playlist item, a clip automation, the node frame or the switch block seen through
a wrong stride, and the lesson it leaves is the one recorded for `0x09` -- a
corpus-only fit cannot tell right from wrong without the reader that wrote the
bytes.

**The rest of the object types, from the same witness.** Every remaining class
reads as follows; the fenced `0x10`/`0x11` census and the small-type census are
retired in favour of lanes, and the lanes close exactly on the current input set: `0x10` 453, `0x11` 2,645, `0x13` 4, `0x14` 9, `0x15` 5 and `0x16` 778 bodies. No `0x0F` object ships, so that framer waits for a corpus that carries one.

| type | class | layout |
| --- | --- | --- |
| `0x03` | `CAkAction::SetInitialValues` | `u16 actionType` (the `AkActionType` enum: high byte operation, low byte scope), `u32 idExt`, `u8 idExt_4` (bit0 bIsBus), the property bundle and the ranged bundle (`AkPropID_DelayTime` and `_TransitionTime` are converted from ms), then the per-class params: Play `u8 eFadeCurve, u32 bankID, u32 bankType`; SetState `u32 group, u32 state`; SetSwitch `u32 group, u32 switch`; the Active/SetValue family `u8 eFadeCurve`, class params, then exceptions `varint n x {u32 id, u8 bIsBus}` -- SetAkProp `u8 eValueMeaning, f32 base, f32 min, f32 max`; SetGameParameter `u8 bBypassTransition` then the same four; Stop/Pause/Resume one bit byte (bit1 bApplyToStateTransitions, bit2 bApplyToDynamicSequence); Seek `u8 bIsSeekRelativeToDuration, f32 value, f32 min, f32 max, u8 bSnapToNearestMarker`; SetFX `u8 bIsAudioDeviceElement, u8 uSlot, u32 fxID, u8 bIsShared`; BypassFX `u8 bIsBypass, u8 uTargetMask`; Release, PlayEvent, ResetPlaylist, Break, Trigger, Mute, UseState nothing beyond the family |
| `0x04` | `CAkEvent` | varint `ulActionListSize` x `u32 actionID` -- a varint, so the one-byte count the type `0x04` lane reads is the short form |
| `0x08`, `0x12` | `CAkBus` (aux bus is the same class) | `u32 OverrideBusId`, and `u32 idDeviceShareset` only when that is 0; `CAkBus::SetInitialParams`: the property bundle (no ranged bundle), PositioningParams (group E), AuxParams (group F), `u8 byBitVector` (bit0 bKillNewest, bit1 bUseVirtualBehavior, bit2 bIgnoreParentMaxNumInst, bit3 bIsGlobalLimit), `u16 u16MaxNumInstance`, `u32 uChannelConfig`, `u8 byBitVector` (HDR bits, bit3 bBackgroundMusic); then `s32 recoveryTime` (ms), `f32 fMaxDuckVolume`, `u32 ulDucks` x 18 bytes (`u32 id, f32 fDuckVolume, s32 fadeOut, s32 fadeIn, u8 eFadeCurve, u8 eTargetProp`), group A, group B, group I, then the StateChunk (group H) **after** group I |
| `0x0E` | `CAkAttenuation` | `u8 bIsHeightSpreadEnabled`, `u8 bIsConeEnabled`, with the cone `f32 InsideDegrees, f32 OutsideDegrees, f32 OutsideVolume, f32 LoPass, f32 HiPass`; `u8 curveToUse[19]` (one per `AkAttenuationCurveType`); `u8 numCurves` x `{u8 eScaling, u16 n x 12-byte points}`; group I. The "21-byte head" was the two flags and the nineteen curve indices |
| `0x0F` | `CAkDialogueEvent` | `u8 uProbability`, `u32 uTreeDepth`, that many `u32` argument ids then `u8` types, `u32 uTreeDataSize`, `u8 uMode`, the tree, then the two bundles |
| `0x10`, `0x11` | `CAkFxBase` | `u32 fxID`, `u32 uSize` + params, `u8 numBankData x {u8 index, u32 sourceID}`, group I, group H, `u16 numValues x {varint AkPropID, u8 rtpcAccum, f32 value}`. The "terminator" and "tied optional block" were group I, the state chunk and the value list |
| `0x13`, `0x14`, `0x16` | `CAkModulator` | the property bundle (`AkModulatorPropID` keys), the ranged bundle, group I. The "one anonymous byte" in the old `0x16` frame was the ranged bundle's count |
| `0x15` | `CAkAudioDevice` | `CAkFxBase` then `AkOwnedEffectSlots::SetInitialValues`: `u8 uNumFx`, `u8 bitsFXBypass` when nonzero, `uNumFx x {u8 index, u32 fxID, u8 flags}` |
| decision tree | `AkDecisionTree::SetTree` / `ResolvePath` | the blob is copied whole; a node is 12 bytes: `u32 key`, `u32 audioNodeId` or `{u16 childrenIdx, u16 childrenCount}`, `u16 weight`, `u16 probability` (0..100) |

**Three corrections the PDB forced.** The enum type records name every property
and operation; the values now live in `scripts/game_data/contracts/wwise_sdk_enums.json`
(32 enums, with the PDB hashes as provenance). (1) The RTPC and state `ParamID`
**is the `AkPropID`** -- the PDB carries no separate RTPC id enum -- so the repo's
older RTPC label table (wwiser's pre-2019 numbering, where 6 meant InitialDelay
and 12 MidiVelocityOffset) was wrong for v150 and now aliases the initial-property
table; the one-byte keys in the main bank are `MakeUpGain`, `Volume`,
`GameAuxSendVolume`, `LPF`, `Positioning_Pan_X_2D`, `MaxNumInstances`, `BypassFX`
and so on. (2) Every varint is accumulated most-significant group first; both
readers now do that. The shipped two-byte keys prove it: `82 30` and `84 30`
decode to `0x130` and `0x230`, that is effect slot 1 and 2 of `AkPropID_BypassFX`
(`0x30`) with the slot in the high byte, whereas the little-endian reading gave
6146 and 6148, which name nothing. (3) The music track's `numSubTrack` is read
only when its playlist is nonempty. The repo's other label tables (curve
interpolation, RTPC accumulation, curve scaling, sync type, bank type, plug-in
type, source type, value meaning, initial properties) agree with the PDB up to
spelling.

## THE HIRC TYPE DISPATCH, READ OUT OF THE SHIPPED PARSER

The warning was about *strings*. The **code** is a different matter, and it is readable
without a disassembler library -- the dispatch is a plain compare-and-jump chain.

**Locating it.** The bank chunk switch is at file `0xf4b60` and is literally
`cmp eax,'DATA' / je`, `cmp eax,'DIDX'`, `cmp eax,'HIRC' / je +0x35`, `cmp eax,'STID'`,
`cmp eax,'STMG'`. Following the `HIRC` branch reaches a `call` at `0xf4bdb` whose target
is the HIRC section parser at **file `0xf70a0`, VA `0x1800f7ca0`** -- confirmed by a
textbook prologue (`push rbp/rbx/rsi/rdi/r12/r14/r15; mov rbp,rsp; sub rsp,0x40`).

**The per-item dispatch**, at `0xf7147`:

```
movzx eax, byte [rbp-0x14]          ; the HIRC item's type byte
add   eax, -2                       ; type - 2
cmp   eax, 0x14                     ; 21 entries
ja    default
mov   ecx, [r13 + rax*4 + 0xf8008]  ; jump table at VA 0x1800f8008
add   rcx, r13
jmp   rcx
```

**21 entries covering types `0x02`-`0x16` exactly** -- the same range this project's
reader covers. Each arm writes a small constant to `[rbp+0x58]` and calls a per-type
constructor:

| class id | types |
| --- | --- |
| 0 | `0x02`, `0x05`, `0x06`, `0x07`, `0x09` |
| 1 | `0x08`, `0x12` |
| 2 | `0x03`, `0x04` |
| 5 | `0x0E` |
| **6** | **`0x13`, `0x14`, `0x16`** |
| 8 | `0x0F` |
| 9 | `0x11` |
| 10 | `0x10` |
| 11 | `0x15` |
| *(none)* | `0x0A`, `0x0B`, `0x0C`, `0x0D` |

**18 distinct constructors for 21 types**, each at a known address (`0x02` ->
`0x1800f0b90`, `0x09` -> `0x1800f2d30`, `0x10` -> `0x1800f2750`, `0x11` -> `0x1800f2460`,
`0x12` -> `0x1800f1850`, and so on).

***The result that bears on an open question.*** **Types `0x0A`, `0x0B`, `0x0C` and
`0x0D` share a single jump-table target** -- one handler, identical code, no per-type
constant. They are therefore parsed *the same way*, so **whatever `0x0B`'s layout is, it
is also `0x0A`'s, `0x0C`'s and `0x0D`'s**, and evidence gathered on any of them transfers
to the rest. The `0x0B` fenced-body question has been worked on in isolation; it need not
be.

**And every stuck type now has a located constructor.** The note above says the Wwise SDK
headers would settle `0x11`'s 21-versus-27 tie, `0x09`'s second run, `0x10`'s `0x7F`
variant and `0x12` outright. Those four constructors are at `0x1800f2460`, `0x1800f2d30`,
`0x1800f2750` and `0x1800f1850` in a shipped, unpacked binary.

**What is *not* claimed.** These are addresses and groupings, not decoded layouts. The
`[rbp+0x58]` value is a per-type constant handed to a shared tail; **calling it a class
selector is a reading, and only the grouping is a fact of the code.** No struct field has
been recovered here.

### The address map, and where hand-decoding stops being reliable

Everything above lives in `.text`, where `VA = file + 0x180000C00`. **That delta is
section-specific and does not generalise** -- applying it to a `.data` reference put a
global 0xC00 bytes wrong and landed it in `.pdata`, i.e. in exception-unwind data, which
is how the error announced itself. The real section map:

| section | VA | file | raw |
| --- | --- | --- | --- |
| `.text` | `0x180001000` | `0x400` | 2,662,400 |
| `.rdata` | `0x18028b000` | `0x28a400` | 652,288 |
| `.data` | `0x18032b000` | `0x329800` | 72,192 |
| `.pdata` | `0x18034b000` | `0x33b200` | 150,528 |

The dispatch table above is unaffected -- every address in it is a `.text` address and each
target was confirmed against a real function prologue.

***Where hand-decoding stops.*** Reading handler *bodies* by hand goes wrong quietly: a
first pass mis-read a rip-relative operand as a `call` by starting mid-instruction, and the
`.data` global needed exactly the section mapping that was wrong.

**capstone 5.0.7 is installed** -- a note elsewhere recording its absence is stale -- and
re-running under it shows the hand-decoded *instruction stream* was right all along; only
the address resolution was wrong. So the reading below is the one that was provisionally
discarded, now verified.

## HIRC `0x0A`-`0x0D` ARE NOT PARSED: THE ENGINE SKIPS THEM

The shared arm, disassembled:

```
mov  rax, [rip + 0x24ca0f]      ; global hook, .data VA 0x180344998
test rax, rax ; je default
lea  r9,[rbp-0x20] ; mov rdx,rdi ; lea r8,[rbp+0x58] ; lea rcx,[rbp-0x14]
call rax                         ; registered handler, if any
cmp  eax, 3 ; jne done           ; 3 == "not handled, fall through"
default:
mov  edx, [rbp-0x13]             ; the item's declared SIZE
lea  rcx, [rsi+8] ; lea r8,[rbp-0x18] ; mov [rbp-0x18], 0
call 0x1800ef2b0                 ; advance the read stream by `size`
cmp  [rbp-0x18], [rbp-0x13] ; cmovne ebx, 7    ; short read -> error 7
inc  r14d ; cmp r14d,[rbp-0x1c] ; jb loop      ; next item
```

`0x1800ef2b0` is a **buffered-stream skip**, not a parser: it takes `min(remaining,
requested)` against `[rbx + rax*4 + 0x18]`, advances `[rbx+0x50]`/`[rbx+0x10]`, calls a
virtual refill at `[rax+0x68]` when a buffer empties, and returns bytes consumed.

**So in this build, absent a registered hook, HIRC types `0x0A`, `0x0B`, `0x0C` and `0x0D`
are consumed as opaque payloads of their declared size**, with the only check being that
the skip consumed exactly `size` bytes.

***This changes the `0x0B` question rather than answering it.*** The open item -- the 210
multi-entry `0x0B` bodies -- has been looking for a structure that **the shipped reader
never imposes**. Six mechanisms were swept and excluded from the bytes; the reader explains
why none of them was found in the reader's own behaviour: *there is no `0x0B` layout in
this engine to recover.* Whatever structure those bodies have is imposed by the optional
hook or by the authoring tool, not by the runtime.

### AND IT ANSWERS "WHERE IS MUSIC DRIVEN FROM" -- IN THE NEGATIVE

`0x0A`-`0x0D` are precisely the four music types this document has analysed at length
elsewhere: the offset-9 parent rule, the one-to-one `0x0A` -> `0x0B` edge, the symmetric
same-bank reference relation, the tempo-ranged floats. **All of that structure is real and
none of it is read by this engine.** The four share one jump-table arm that consults an
optional global hook and otherwise *skips the payload wholesale*.

Two independent lines now agree:

| line | finding |
| --- | --- |
| corpus (earlier) | the music family is **unreachable** from anything in the bank format |
| **reader (here)** | the music family is **not parsed** by the bank reader |

*Unreachable and unparsed are different claims from different evidence, and they point the
same way.* **The bank's music hierarchy does not drive music in this build.** The bodies
carry authored structure -- the corpus work established that beyond doubt -- but the
runtime path that would consume it is absent.

**The honest boundary.** The arm does call a registered hook first, so a plug-in *could*
parse these types at runtime; what is shown is that **no built-in parser exists**, not that
nothing can ever read them. That distinction matters because it names exactly what a
future answer would have to be: a registered handler, discovered at runtime, not a
structure recoverable from the bank bytes.

### The `+12` / `+20` words inherit this, and it re-files them

The maintained reader's `Type11EntryPairFirstOffset = 12` / second at 20 are entry-header
words in **numeric type 11, which is `0x0B`** -- one of the four the engine skips. So the
open question about those two words sits inside a body **the runtime never parses**, and
the status recorded for it (blocked on a namespace outside the shipped files) is not the
real obstacle.

***What this rules out, and what it leaves.*** No engine-side evidence can ever name these
words, because no engine code reads them -- that route is closed, not merely unexplored.
But `0x0B` bodies are demonstrably *not* noise: the same reader already resolves their
source records, whose word at `+5` names a declared media id in **all 4,447** of `0x0B`'s
bodies and closed 1,276 media that nothing else accounted for. **That worked because it
had an external anchor -- the AKPK media declarations -- rather than an engine parser.**

So the `+12`/`+20` question is answerable in exactly one way: *another external anchor, of
the kind that resolved the source records.* Ten populations have already been eliminated
against the bytes alone; the lesson from the source-record success is that the missing
ingredient is a second table to join against, not a better sweep of the same bodies.

**Two candidate anchors have now been checked and ruled out.**

***The decoded intermediate does not carry object bodies.***
`tmp/audio/hirc_action_current/audio_audit.json` (325 MB) is the only decoded view of the banks
on disk, and its rows hold per-package structural summaries -- sector byte counts, bank counts,
`bnkBankIds` lists -- with a type breakdown that is counts only (`"0x0B": 2130`). It cannot
supply a property enumeration.

***Nor can it supply the media-size join.*** The better idea was to skip the enumeration
entirely: every `0x0B` body's source record names a declared media id, so *if those words are
durations they must correlate with the media's byte size* -- a genuine external anchor of the
kind that resolved the source records. **The audit has no media sizes.** Its 41,752
`offset`/`declaredSize` pairs are **BNK section headers** (`BKHD`, `HIRC`), not media entries,
because it was generated with `mediaVerification: "skipped"`.

***So every anchor reachable from the shipped artefacts is now exhausted.*** The shipped reader
skips types `0x0A`-`0x0D` outright, the metadata has no bodies, and the media table has no sizes.
**Closing this needs either the Wwise SDK's structure definitions or a bounded runtime
observation** -- and the latter is an account-affecting action on a client that ships
`AntiCheatExpert`, so *it is the user's call and must not be taken without an explicit request.*
**This item is blocked on an input, not on analysis effort**, and should not be re-attempted
against the corpus alone.

### What *is* established about those words, pooled over the corpus

"Ten populations eliminated" understates the positive characterisation. Pooling the
type-`0x0B` entry-header census across all 25 packages:

| property | holds | control |
| --- | --- | --- |
| the two words are **equal to each other** | **78.98%** | -- |
| read as floats, **inside the bounded band** | **4,371 / 4,371 = 100%** | 480 / 5,932 = **8.09%** |
| plausible as **gains** | **2,123 / 2,123 = 100%** | 150 / 3,530 = **4.25%** |
| **fractions are small** | 3,405 / 3,530 = 96.46% | **0.00%** |
| the pair forms a **symmetric range** | 1,466 / 2,004 = 73.15% | **0.00%** |

**Every control is at or near zero while every claim is at or near 100%**, so the words are
not unstructured: they are floats in a bounded band, frequently equal, and when unequal they
form a symmetric range about their centre. *That is a full description of their values -- it
is only their referent that is missing.*

**Which sharpens what an anchor has to supply.** Not "what are these bytes" -- that is
answered -- but *which quantity in this engine is a symmetric float range, usually
degenerate to a point, attached to a source entry inside a node type the runtime never
reads.*

***And it rules out every table in this corpus, on type grounds.*** The obvious next
anchor is `STMG`, which is framed byte-exactly and carries the switch/state vocabulary.
It cannot serve: pooled over all 25 packages `STMG` holds **4 sections, 15 distinct entry
ids, 45 records** -- and those are **ids**, while `+12`/`+20` are **floats**. *A float does
not join to an id table*, and the same objection retires the bank ids, media ids and object
ids at a stroke. **The corpus's anchors are all identifier-keyed; this question needs a
float-valued one**, which is why ten population sweeps found nothing and an eleventh would
not either.

That is a stronger statement of the blocker than "needs an external anchor": the anchor has
to be a **property enumeration** -- the Wwise SDK's, or a bounded runtime observation --
because nothing in the shipped data associates a float range with a name.

### The chunk switch in full, and what it says about the "unowned" media

Disassembled properly, the bank dispatch is a flat fourcc chain:

```
cmp eax, 'DATA' ; je            cmp eax, 'DIDX' ; jne (other)
cmp eax, 'ENVS' ; ja / je
cmp eax, 'DATA' ; je 0x1800f57e5
cmp eax, 'HIRC' ; je -> call 0x1800f7ca0      <- confirms the HIRC parser address
cmp eax, 'STID' ; je -> call 0x1800f81e0
cmp eax, 'STMG' ; jne 0x1800f5831 -> the DIDX/DATA media path
```

The media path runs the same `0x1800ef2b0` stream advance with the same
consumed-versus-declared check and error 7, then allocates the media block (flags
`0x20000003`, size stored at `[rdx+0x28]`) through the same `0x1800ef040` /`0x1800ef120`
helpers the node loaders use.

***It never touches the HIRC section.*** Media declared in `DIDX` and carried in `DATA` are
allocated and registered **by id, straight from the chunk**, with no consultation of any
source record.

**So "unowned" is a property of the join, not an anomaly in the data.** The open item
counts media that no HIRC source record names, and 7 of the 8 were already characterised as
the Init bank's `DIDX`-embedded media. The reader explains *why that is the expected state*:
**a bank-embedded media needs no HIRC owner to be loadable**, because the chunk path is
self-sufficient. A media with no source record is not a dangling reference; it is a media
that happens not to be reached that way.

*That reframes the remaining question from "why are these 8 unowned" to "what, if anything,
distinguishes the 1 that is not Init-bank embedded" -- a much smaller question, and one the
existing censuses can be pointed at directly.*

**Incidentally recovered:** the HIRC item header is `u8 type` at `[rbp-0x14]` followed by
`u32 size` at `[rbp-0x13]`, with the section's item count at `[rbp-0x1c]` and the loop
index in `r14d` -- which is exactly the framing this project's reader already uses,
now confirmed against the engine.

### Where the per-type field reads actually happen

Following the `0x11` arm (the 21-versus-27 tie) down: the arm **does not parse anything**.
It allocates via `0x1800ef040`, returns error `0x38` if that fails, then takes a refcounted
lock on a global registry at `[rip+0x252510] + 0x318`. The field reads are further on,
behind a **virtual call**:

```
mov  rax, [rbx]            ; vtable
mov  rcx, rbx              ; this
lea  rdx, [rsp+0x30]       ; cursor
lea  r8,  [rsp+0x20]       ; size (stored on entry from edx)
call qword ptr [rax+0x28]  ; <- the deserializer
```

**`vtable[+0x28]` is the field deserializer**, uniform across the type handlers -- the
single entry point any layout recovery has to go through. That is the useful, transferable
part: it applies to `0x09`, `0x10`, `0x11` and `0x12` alike, not just the one traced.

***What is left, stated precisely so the next attempt starts in the right place.*** Getting
a concrete layout needs the per-type **vtable address**, and that is not stored inline in
the arm -- it is written by a nested constructor, two or more calls down. A shortcut of
scanning `.rdata` for runs of code pointers **does not work as written**: it finds 94 runs
but merges adjacent tables, reporting 290-, 385- and 609-slot "vtables" that are plainly
concatenations. Splitting them needs the RTTI `type_info` pointer that precedes each real
vtable -- and this binary's RTTI is stripped to 12 `std::` descriptors, so that boundary is
not available either. **The remaining route is to follow the nested constructors, not to
scan for vtables.**

## THE CHAIN COMPLETED, AND HIRC `0x11`'s LAYOUT READ FROM THE ENGINE

Following the constructors rather than scanning did work, in four hops:

1. the `0x11` arm looks a node up in an **id-keyed chain** (`cmp [rbx+0x10], esi` /
   `mov rbx, [rbx+8]`, refcount at `+0x14`, vtable at `+0x0`);
2. when absent it calls the **type-`0x11` factory at `0x18014aee0`**, which allocates
   **`0xa8` bytes** from pool 2, runs a base constructor, and **stores vtable
   `0x1802992d0`** at `[rbx]` (plus a secondary at `[rbx+0x18]`);
3. `vtable[+0x28]` is therefore `0x18014c250`;
4. that function is the deserializer, and it is short enough to read outright.

```
add  qword ptr [rdx], 4     ; cursor += 4   -- the node id, already consumed
mov  ebp, [rax]             ; FIELD A : u32
mov  [rdx], rsi             ; cursor += 4
mov  r14d, [rsi]            ; FIELD B : u32
add  rsi, 4 ; mov [rdx], rsi
cmp  ebp, -1 ; je done      ; A == 0xFFFFFFFF -> read nothing further
lea  rcx, [rip+0x1e38a5] ; mov edx, ebp ; call 0x18011e060    ; look A up
mov  rcx,[rsp+0x68] ; mov rax,[rcx] ; mov r9d, r14d ; mov r8, rsi
call qword ptr [rax + 0x18]  ; hand the REST of the payload to the plug-in
```

**So the engine parses exactly twelve bytes of a `0x11` body** -- the node id, then `A`,
then `B` -- and everything after that is passed to a plug-in **selected by `A`**, with `B`
handed over as a parameter. `A == 0xFFFFFFFF` means no plug-in and no further reading.

***This settles the `0x11` tie.*** The open item was a 21-versus-27 ambiguity in the body
length, undecidable from the bank bytes. It is undecidable *because the format does not fix
it*: **the engine-defined part is 12 bytes and the tail length is whatever the selected
plug-in consumes.** Two body lengths are not two candidate readings of one structure -- they
are two plug-ins. *A tie that will not break under more corpus evidence is often a tie the
format never had a side in.*

### Running the recipe on the other types -- and a correction it caught

The four hops were automated and run over `0x09`, `0x10`, `0x12` **and `0x11` again as a
control**. The control earned its place immediately: it disagreed with the hand trace.

| type | factory | alloc | vtable | `vtable[+0x28]` |
| --- | --- | --- | --- | --- |
| `0x10` | `0x18014af30` | 0xa8 | `0x180299200` | **`0x18014c250`** |
| `0x11` | `0x18014aee0` | 0xa8 | `0x1802992d0` | **`0x18014c250`** |
| `0x09` | *recipe found none* | -- | -- | -- |
| `0x12` | *recipe found none* | -- | -- | -- |

***The correction.*** An earlier version of the note above gave `0x11`'s factory as
`0x18014af30` with vtable `0x180299200`. **Those are `0x10`'s.** The cause was reading a
`tail`-truncated disassembly: the listing began after `0x18014aee0`'s body and showed the
*next* function, whose vtable store was then attributed to the wrong type. *The deserializer
address was right, which is exactly why the error survived -- a wrong path to a right answer
looks like a right path.*

**The substantive finding is unaffected and in fact broadens.** `0x10` and `0x11` have
**different vtables but the same deserializer**, `0x18014c250`, so the 12-byte prefix plus
plug-in tail describes **both** types -- which fits them being the two plug-in-bearing node
kinds.

**`0x09` and `0x12` needed a wider scan, not a different method.** Searching *every* direct
call target in each loader for the factory signature finds exactly one per type:

| type | loader | factory | alloc | vtable |
| --- | --- | --- | --- | --- |
| `0x02` | `0x1800f0b90` | `0x180150c50` | 264 | `0x180299498` |
| `0x05` | `0x1800f3040` | `0x18013b6d0` | 304 | `0x1802984c8` |
| `0x09` | `0x1800f2d30` | `0x18015ea90` | 304 | `0x18029a3b0` |
| `0x10` | `0x1800f2750` | `0x18014af30` | 168 | `0x180299200` |
| `0x11` | `0x1800f2460` | `0x18014aee0` | 168 | `0x1802992d0` |
| `0x12` | `0x1800f1850` | `0x18015b170` | 400 | `0x180299cf0` |

### CORRECTION: the deserializer slot is *not* uniform

An earlier note here said `vtable[+0x28]` is the field deserializer "uniform across the type
handlers... it applies to `0x09`, `0x10`, `0x11` and `0x12` alike". **That was generalised
from one loader and is false.** Reading the indirect calls each loader actually makes:

| slot called | types |
| --- | --- |
| `[rax+0x28]` | `0x10`, `0x11`, `0x15` |
| `[rax+0x278]` | `0x12` |
| neither | `0x02`, `0x05`, `0x09`, `0x13` |

***Why the wrong claim looked right.*** Slot `+0x28` **resolves to a real function on every
one of these vtables** -- for `0x02`, `0x05`, `0x09` and `0x12` it is `0x1800dacd0`, which
disassembles to a parent/flag setter (`bts`/`btr` on bits 13-15 of `[rbx+0x90]`, a virtual
at `[rax+0x260]`), **not a payload parser at all**. *A slot that resolves cleanly for every
type looks uniform; resolving is not the same as meaning the same thing, and only reading
the callers shows which slot is actually invoked.*

**`0x12`'s real deserializer is `0x180109030`** (`vtable[+0x278]`). It guards on a virtual
`[rax+0x78]`, bails with error `0x5b` unless that returns 0 or 0xA, then takes the cursor
and `add rax, 4` past the node id -- the same "id already consumed" convention as `0x11`.

## HIRC `0x12`'s FIELD SEQUENCE, READ FROM THE DESERIALIZER

```
add  rax, 4                      ; cursor += 4   -- node id, consumed by the caller
mov  r14d, [rax] ; add rax,4     ; FIELD 1 : u32
test r14d, r14d ; je skip        ; 0 means "none"
  mov  rbx, [rip+0x23b911]       ; global object manager
  div  dword ptr [rbx+0xa0]      ; FIELD 1 % bucketCount
  mov  rax, [rbx+0x98]           ; bucket array
  mov  rdi, [rax+rdx*8]          ; chain head
  cmp  [rdi+0x10], r14d / mov rdi,[rdi+8]    ; walk, key at +0x10, next at +0x8
skip:
mov  ecx, [rax] ; add rax,4      ; FIELD 2 : u32  -> stored at object +0x188
call qword ptr [rax + 0x1f0]     ; nested parse, cursor passed by reference
cmp  eax, 1 ; jne fail
movsxd rcx, dword ptr [rax]      ; FIELD 3 : i32
imul   rcx, [rip+0x2267ee]       ; x a global rate
movabs rax, 0x20c49ba5e353f7cf ; imul ; sar rdx,7    ; / 1000
```

| field | width | what the code does with it |
| --- | --- | --- |
| node id | 4 | consumed by the caller, skipped here |
| **1** | 4 | an **object id**, resolved through the global id-keyed hash table (`0` = none) -- the same `+0x10` key / `+0x8` chain structure the loaders walk |
| **2** | 4 | stored at object offset `0x188` |
| *(nested)* | -- | virtual `[vt+0x1f0]` parses a further block, advancing the shared cursor |
| **3** | 4 | signed, multiplied by a global rate then divided by 1000 -- **a millisecond duration converted to samples** |

The divide is the standard `0x20c49ba5e353f7cf` / `sar 7` reciprocal for 1000, which is what
makes the units legible rather than guessed.

*So `0x12` is a node carrying one outbound reference, one stored word, a nested block and a
millisecond duration* -- recovered from the reader, not inferred from the corpus.

## `0x09`: CALLED DIRECTLY, NOT THROUGH A VTABLE

*Superseded in part by the SDK read above: `0x180160450` is
`CAkLayerCntr::SetInitialValues` and `0x1800dcfd0` is
`CAkParameterNodeBase::SetNodeBaseParams`; the layer grammar is now framed in code.*

The slot search found nothing for `0x09` because **there is no slot** -- its loader calls
the parser as a direct `call 0x180160450`. *A search for an indirect call cannot find a
direct one, and the empty result reads exactly like "this type has no parser".*

`0x180160450` has the same shape as `0x12`'s:

```
mov  rax,[rcx] ; call qword ptr [rax + 0x78]   ; type tag check
cmp  eax, 5 ; jne error                        ; 0x09 requires 5   (0x12 requires 0 or 0xA)
  ... log via 0x180036490, return 0x5b
add  qword ptr [rsp+0x78], 4                   ; cursor += 4 -- node id, as everywhere
lea  r8,[rsp+0x80] ; xor r9d,r9d ; lea rdx,[rsp+0x78]
call 0x1800dcfd0                               ; shared sub-parser (this, &cursor, &out, 0)
```

So the three conventions now confirmed across types are: **the node id is consumed by the
caller and skipped by the deserializer; a `[vt+0x78]` tag check gates entry with error
`0x5b`; and the cursor is passed by reference so nested parsers advance it.**

### Status of the four types the notes called SDK-only

| type | reached | result |
| --- | --- | --- |
| `0x10` | `vtable[+0x28]` -> `0x18014c250` | 12-byte prefix, then a plug-in tail |
| `0x11` | `vtable[+0x28]` -> `0x18014c250` | same deserializer as `0x10` |
| `0x12` | `vtable[+0x278]` -> `0x180109030` | ref id, stored word, nested block, ms duration |
| `0x09` | **direct call** -> `0x180160450` | tag must be 5, delegates to `0x1800dcfd0`; **closed** from the SDK read above |

plus `0x0A`-`0x0D`, which are not parsed at all. **The obstacle recorded for these was a
licence; it was never the licence.**

## THE SHARED SUB-PARSER, AND THE REGISTRY BOTH TYPES RESOLVE AGAINST

`0x1800dcfd0` -- what `0x09` delegates to -- is the common block:

```
call qword ptr [rax + 0x1f8]     ; per-class step 1, must return 1
test bl, bl ; jne done           ; the flag the caller passes in r9b (0x09 passes 0)
call qword ptr [rax + 0x200]     ; per-class step 2, cursor by reference
mov  ebp, [rcx] ; add rcx,4 ; mov [r15], rcx      ; read a u32
test ebp, ebp ; je skip                            ; 0 == none
mov  rbx, [rip+0x267983]         ; global object manager
lock cmpxchg [rbx+0x58] ...      ; refcount
div  dword ptr [rbx+0xa0]        ; id % bucketCount, then walk the chain
```

So the shared block reads **one u32 object reference, resolved through the global node
registry**, bracketed by two per-class virtuals at `[vt+0x1f8]` and `[vt+0x200]`.

***The registries are the same one, which is checkable rather than assumed.*** `0x12`'s
parser reaches it as `[rip+0x23b911]` from `0x1801090c7` and the shared block as
`[rip+0x267983]` from `0x1800dd055`. Both resolve to **`0x1803449d8`**. *Two different
displacements from two different call sites landing on one address is the kind of
arithmetic that either agrees exactly or is wrong* -- and it agrees.

**So `0x09` and `0x12` both carry an outbound object reference as their first parsed field
after the node id, and both resolve it against the same registry.**

## THE PER-CLASS BLOCKS, AND `0x12`'s LAYOUT IN FULL

Both per-class virtuals open identically -- `movzx <r>, byte ptr [rax] ; inc rax ;
mov [rdx], rax` -- a **u8** taken from the shared cursor.

**`0x09`, `[vt+0x200]` -> `0x1800ffb50`** *(an earlier draft of this note said `[vt+0x1f8]`;
the slots are distinct -- `[+0x1f8]` is `0x1800ff980` and is not the function read here)*.
It reads **two** bytes and then a table:

```
movzx r9d, byte [rax] ; inc rax          ; FLAG : u8
mov  r8,[rcx+0x90] ; and/or with bit 54 ; cmove ; mov [rbp+0x90], r8   ; -> flags bit 54
movzx ecx, byte [rax] ; inc rax          ; B : u8 count
test cl,cl ; je done ; call 0x1800d70b0  ; reserve B
loop x B:
   movzx r10d, byte [rcx]      ; entry +0 : u8
   mov   r8d,  dword [rcx+1]   ; entry +1 : u32
   movzx r9d,  byte [rcx+5]    ; entry +5 : u8
   cursor += 6
   test r8d,r8d ; je next      ; the u32 being 0 skips the entry
   call 0x1800dcf90
```

**`u8` flag, `u8` count `B`, then `B` six-byte entries of `{u8, u32, u8}`** -- the cursor
advances 1, 4, 1 per entry, so the stride is read rather than assumed.

***And three types share one implementation.*** `0x02`, `0x05` and `0x09` have **identical**
per-class slots -- `[+0x1f0]` `0x1800ffc60`, `[+0x1f8]` `0x1800ff980`, `[+0x200]`
`0x1800ffb50` -- while `0x12` has its own trio. So this block is not `0x09`'s; **it is the
shared block of a three-type class family**, and anything established for one holds for the
other two.

### The family's other two blocks, and a shape that appears twice independently

**`[+0x1f0]` -> `0x1800ffc60`.** `u8 N`, then `align = (N+4) & ~3`, allocate
`align + N*4`, store `N` at the head, fill from the cursor, and keep the block at
`[+0x88]`. **That is the same `N` bytes then `N` dwords structure as `0x12`'s `[+0x1f0]`**
(`0x180108d10`) -- *two different functions, compiled separately, producing an identical
serialized shape and storing it at the identical object offset.* A layout inferred once
could be a misreading; the same layout reached twice by independent code is the format.

**`[+0x1f8]` -> `0x1800ff980`.** A single `u8`, folded into the flag word at `[+0x90]` with
mask `0x3000000000000` -- **bits 48 and 49 together**, set or cleared as a pair. Note this
differs from `[+0x200]`'s byte, which drives the single bit 54: *three bytes in three blocks
all land in one flag word at different bit positions*, which is why they cannot be told
apart by value and only the code separates them.

### The `0x02` / `0x05` / `0x09` node body, as far as the engine reads it

| block | content |
| --- | --- |
| `[+0x1f0]` | `u8 N`, `N` x byte, `N` x dword -> object `+0x88` |
| `[+0x1f8]` | `u8` -> flag bits 48-49 |
| `[+0x200]` | `u8` -> flag bit 54; `u8 B`; `B` x `{u8, u32, u8}` |
| shared tail | `u32` object reference, `0` = none, resolved via the registry at `0x1803449d8` |

*All three types carry this identically -- it is one class, reached from three jump-table
arms.*

### `0x12`'s trio beside it -- same shapes, three precise differences

| block | `0x02` / `0x05` / `0x09` | `0x12` |
| --- | --- | --- |
| `[+0x1f0]` | `u8 N`, `N` x byte, `N` x dword -> `+0x88` | **same shape**, different function |
| `[+0x1f8]` | `u8` read, sets *or clears* bits 48-49 | **reads nothing**; ORs bits 48-49 **unconditionally** |
| `[+0x200]` | `u8` flag -> bit 54, **then** `u8 B` | **no flag byte** -- the first byte *is* `B` |
| entries | `B` x `{u8, u32, u8}`, stride 6, skip when the u32 is 0 | **identical**, same callee `0x1800dcf90` |

***The entry block is now confirmed three times over.*** `0x1800ffb50` and `0x180108c30`
are separately compiled functions that read the same six-byte record with the same 1/4/1
cursor advance and the same skip-on-zero rule, and `[+0x1f0]`'s `N`/bytes/dwords block
likewise appears in two independent implementations. *Three independent arrivals at one
layout is about as far from a lucky fit as byte-level work gets.*

**And the difference that matters for reading bodies:** `0x12` spends **one byte fewer**
in `[+0x200]` than the family does, and **zero bytes** in `[+0x1f8]` where the family
spends one. Two types whose blocks look interchangeable differ by exactly two bytes of
payload -- *which is the kind of discrepancy that makes a corpus-derived stride look
"nearly right" across a mixed population and never quite fit.*

**`0x12`, `[vt+0x1f0]` -> `0x180108d10`.** The byte is a **count**, and what follows is a
parallel-array block:

```
movzx ebx, byte [rax] ; inc rax          ; N
lea  r15d,[rbx+4] ; and r15d, 0xfffffffc ; align = (N+4) & ~3
lea  r8d,[r15 + rbx*4] ; call alloc      ; block size = align + N*4   (0x34 on failure)
mov  byte ptr [rax], bl                  ; N stored at the block head
memcpy(block + 1,     cursor, N)     ; cursor += N        ; N x u8
memcpy(block + align, cursor, N*4)   ; cursor += N*4      ; N x u32
mov  [rdi+0x88], r14                     ; block stored on the object
```

**`u8 N`, then `N` bytes, then `N` dwords** -- two parallel arrays of equal length, which is
a shape no amount of staring at body lengths would have separated from a single array of
5-byte records.

### HIRC `0x12` complete

| order | field | width |
| --- | --- | --- |
| 1 | node id | u32 *(consumed by the caller)* |
| 2 | object reference, `0` = none | u32 |
| 3 | word stored at object `+0x188` | u32 |
| 4 | `N` | u8 |
| 5 | `N` x byte | N |
| 6 | `N` x dword | 4N |
| 7 | duration, `x rate / 1000` -- **milliseconds** | i32 |

*Read end to end from the engine's own deserializer.*
- **Numeric type `0x12` is the one HIRC type with no framing at all, and these
  readings are ruled out.** 251 bodies, 15,175 bytes. It is not the `0x10`/`0x11`
  grammar -- its word at offset 4 fails `range_section` on all 251. It is not the
  `0x16` shape (0 of 251). Chained counted blocks after a four-byte lead close only
  8 of 251 at any chain depth from 1 to 4.
- Its leading 32-bit word names a same-bank object in 132 of 251 bodies and names
  nothing in the other 119, so unlike types `0x08`, `0x0A`, `0x0C` and `0x0D` it is
  **not** a reference field and must not be gated as one.
- A "fixed 21-byte tail" reading looked convincing on two sample bodies -- the float
  `9a 99 c0 c2` sat exactly 21 bytes from the end in both -- and is **wrong**: only
  100 of 251 bodies have it there. Two samples agreeing on an offset is not
  evidence; this corpus has now punished that three times.
- What the end-aligned census supports as a *shape hypothesis* only: counting back
  from EOF, bytes -5, -4 and -3 are zero in every body, byte -6 takes seven small
  values, and bytes -12 and -11 look like the high half of a float.
- **The fixed-trailer reading that hypothesis suggests has now been tested and
  fails.** Sweeping every trailer width from 0 to 39 against a four-byte lead and
  a block chain of any depth, the best is 33 bytes explaining 143 of 251. So the
  bytes before the trailer are not a block chain, or the trailer is not fixed, or
  both.
- Four further readings are eliminated, bringing the total to eight. Group I does
  not appear: scanning every offset, only 34 bodies have one landing within eight
  bytes of EOF and those start at two fixed offsets, which is coincidence rather
  than structure. TLV records -- a key byte, a size of one, two or four bytes, then
  that many bytes, with zero to two bytes of padding -- reach 84 of 251 at best.
  And the length is not predicted by flags: the best single byte fixes it for 26%
  of bodies and the best pair for 26%, against 100% for the `0x0E` flag byte, so
  `0x12` is not a fixed layout with flag-gated optional parts either.
- Taken together these say the body is **not** a linear sequence of self-describing
  records, which is what every model tried so far assumed.
- **The size-field premise that suggested has now been tried too, and also fails.**
  Testing every offset 0..23 at 16 and 32 bits for a value that sizes a following
  region gives at best 30% agreement on the leftover; repeating it relative to the
  end of a one-, two- or three-block chain gives at best 33%. In both sweeps the
  "agreeing" leftovers cluster at 76/72/32 bodies, which is exactly the body-length
  histogram -- so the agreement is an artifact of a few common lengths, not a field.
  **Check a candidate field's hit distribution against the length histogram before
  believing it**; these two sweeps looked like 30% signal and were 0%.
- Ten readings are now eliminated. I have no further structural hypothesis for
  `0x12` that this corpus can test, and would rather say so than keep sweeping.
  The Wwise 2023.1.17 SDK would settle it outright; short of that, a genuinely new
  premise is needed, not another parameterisation of an old one.
- **Numeric types `0x13`, `0x14` and `0x15` are framed byte-exact: 18 bodies, 685
  bytes, all of them.** `0x13` and `0x14` are a counted block of four-byte values,
  a counted block of **eight**-byte values, then two bytes; keys and values are
  parallel runs in both, the same shape `0x16` uses. `0x15` instead shares the
  eight-byte header `0x10` and `0x11` use and closes with eight further bytes.
- **Treat these as weak claims and keep the witness counts in view.** Four, nine
  and five bodies is not a corpus -- plenty of layouts consume four bodies. What
  distinguishes the eight-byte second-block width from a four-byte one is that 6
  bodies actually carry a nonempty second block (11 entries in total), and the
  gate refuses a corpus where every second block is empty precisely so the width
  cannot pass unwitnessed. If these types ever grow, re-check the width first.
- They were only findable because the shapes were already known: the block came
  from `0x16`, the header from `0x10`/`0x11`. That is now four types closed by
  reuse rather than decode.
- **Numeric type `0x10` shares type `0x11`'s grammar exactly, and was never
  decoded separately.** Its header matched (`u16`, `u16`, `u32` size), so the
  existing grammar was tried and 430 of its 453 bodies closed at once. That is now
  the third time "check whether another type already closes this" paid off, after
  `0x16` reusing group I and `0x11` doing the same.
- The 23 `0x10` bodies that do not close all carry third byte `0x7F`, and group I
  fails to parse in their tail at every offset tried. They are fenced under their
  own reason, `type10_variant7F`, not blamed on the shared grammar. The reader
  applies that rule to type `0x10` only -- a `0x7F` third byte on a `0x11` body is
  normal, and a test pins that so the rule cannot leak across types.
- Both types now report through one census with a **named reason for every fenced
  body**, and the gate requires the reasons to account for every fence. A fence
  without a reason is indistinguishable from a body quietly dropped.
- **Numeric type `0x11` is framed for 2,553 of its 2,645 bodies (208,891 of
  213,491 bytes); the other 92 are fenced because a width genuinely ties.**
  Layout: an eight-byte header whose second word sizes an opaque section, one
  byte, the node frame's group I structure, a 16-bit flag, then a counted run of
  six-byte elements. Group I is reused, not re-derived -- the third type now to
  end with it, after `0x16` and the node-frame types.
- **The tie is the important part, and it must not be broken by picking.** When
  the flag is set an extra block appears, and two widths consume *every* flagged
  body exactly: 21 and 27. They are the same bytes read two ways -- 27 swallows
  the run's single element and reads a zero count, 21 leaves it as one element.
  The flag is never greater than 1 anywhere in the corpus, so no body can separate
  them; a body with flag 2 would, and none exists. This is underdetermined in the
  same sense as type `0x09`, not merely undecoded, so those 92 bodies are not
  framed at all. Their fence reason is named `tiedOptionalBlockWidth`, beside
  `0x10`'s `type10_variant7F`; `0x10` and `0x11` are gated together as one
  grammar, and the gate requires the two named reasons to account for every
  fenced body of the pair. Failures are forbidden and fencing everything is
  refused.
- The gate for this type forbids failures outright and allows only the fenced
  outcome, which is counted separately from both success and failure. Fencing
  everything would make the claim vacuous and is rejected too.
  See [`reports/animestudio/hirc_reference_graph_current_latest.md`](../../reports/animestudio/hirc_reference_graph_current_latest.md).
- **Numeric type `0x08`'s leading 32-bit word is null or names exactly one
  same-bank object -- never a non-null value that names nothing.** 161 bodies: 157
  resolve, 4 are null, 0 unresolved. Null is a real outcome for this type, so the
  gate permits it and forbids only the third case; an all-null corpus would make
  the claim vacuous and does not count as closed either.
- **What that reference points AT, measured: `0x12` mostly names `0x08`.** Over both
  types' 412 bodies: `0x12` -> `0x08` **201**, `0x08` -> `0x08` **154**, `0x12` ->
  `0x12` **48**, plus 3 and 2 naming type `0x15` and 4 nulls. So the two types form a
  hierarchy with `0x08` beneath `0x12`, and `0x08` also nests within itself. No edge
  from either to `0x0B`.
