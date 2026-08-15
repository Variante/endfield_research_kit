# Character Info / Overview 入场动画原始所有权（2026-08-15）

## 结论（最窄可证范围）

在当前选定客户端 build 上，Character Info 的 Overview 进入不是 Gacha 的
`PlayableDirector`/Timeline 播放协议，而是 `PhaseCharInfo` 驱动的参数化
Animator 状态机：写入 `FromIndex`、`ToIndex`，再触发 `EnableSwitch`。Overview
的状态索引为 `0`，出厂状态名为拼写错误的 `FromOveview`。角色本体及私有
deco Animator 都沿用这组条件和状态哈希。

选角事件、旧根清理、异步替换和入口状态的源闭环如下：

```text
CharInfoSwitchChar.Execute
  -> GUIDE_CHAR_INFO_CHANGE_CHAR (event key @ instance offset 0x428)
  -> CharInfoCtrl.GuideChangeChar / _ChangeSelectIndex
  -> CHAR_INFO_SELECT_CHAR_CHANGE
  -> PhaseCharInfo.OnSelectCharChange
  -> RemoveAllPhaseCharItems + 取消 pending model load
  -> CreatePhaseCharItem (异步 ModelLoader)
  -> load callback: _SwitchCharacterControllerState
       FromIndex / ToIndex / EnableSwitch
  -> body Animator + private DecoItem Animator mirror
  -> ForceUpdateAnimator
  -> _PlayModelEffect（仅通用 charEffect，按身高 bucket 挂 parent）
  -> LateTick LookAt-IK cross-fade（不是 Timeline 或 VFX spawn）
```

因此，本证据集没有闭合一个“Overview 专属 actor entrance-VFX spawner”。
`PhaseCharInfo._PlayModelEffect` 是唯一找到的通用 Overview 入口效果路径：它
把 `sceneObject.view.charEffect` 重新挂到 `singleEffects/effect<height>`，归零
变换后调用 `effect:Play()`。角色专属 `piaodai`、`_01`、`baofa`、
`finger_lightning` 请求只存在于实验性生成 prefab 的请求表；仓库没有
`IEndfieldOverviewEffectSpawner` 的实现，故不能把这些请求当作运行时所有权。

## 原生输入 gate

所有下列原生地址、body hash 和语义判断均先通过
`scripts.common.check_installed_native_inputs()`，并且只针对这一个显式输入
对：

```text
GameAssembly.dll
  D:/Program Files/Endfield Game/GameAssembly.dll
  size 280,436,712
  sha256 0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce

global-metadata.dat
  D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat
  size 62,925,560
  sha256 90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e

gate status: validated
```

缺少、路径不一致或 hash 不匹配时，本报告的原生结论必须视为
`missing`/`mismatched`，不能降级为另一 build 的地址推断。

## 选角与 Animator 的原始证据

证据文件：

- `unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/overview_animator_native_recovery.json`
- `unity_endfield_graph_shader_lab/scratch/character_recovery/charinfo_switch_owner/lua_full/Lua/Data/LuaScripts/UI/Panels/CharInfo/CharInfoCtrl.lua`
- 同目录 `Phase/CharInfo/PhaseCharInfo.lua`、`Phase/PhaseItem/PhaseCharItem.lua`、`Phase/Core/PhaseBase.lua`
- `.../Common/Core/LuaUpdate.lua`、`LuaUpdateGroup.lua`、`Coroutine.lua`、`Const/UIConst.lua`

关键原生 owner 事实：

- `Beyond.Gameplay.Actions.CharInfoSwitchChar.Execute` VA `0x18764ea60`
  的语义是读取 `_charId`，取 `GUIDE_CHAR_INFO_CHANGE_CHAR`，再调用
  `EventManager.SendGlobal<string>(eventKey, charId)`；它不创建模型、不持有
  Animator 或 Timeline。
- `CharUIModelMono.PlayAnimatorState(string)` 的语义是 hash 后调用整数重载；
  整数重载对 body Animator 和每个 `DecoItemBundle` 调用 `Animator.Play`。
  但 1290 个 Lua 文件没有对该方法的调用，也没有对
  `PhaseCharItem.PlayAnimByState` 的 caller；hash 重载仅见一个 native direct
  caller（VA `0x186c27dd1`）。所以已安装的选角路径由 Animator 参数驱动，不能
  从 Lua 证成一个 `PlayAnimatorState` 直接入口。
- `CharUIModelMono.Tick` 首先更新 deco 可见性；每个 deco 读取
  `hideCurveHash`，以 `0.1f > value` 调用 `SetVisible`。这属于 clip/状态消费，
  不是额外 VFX owner。
- `ActiveRotationRootMotion`/`_OnAnimatorMove` 只消费 `deltaRotation`；没有
  `deltaPosition` 的 Overview 位移入口。

`UIConst.lua` 的稳定序列化契约是：

```text
FromIndex = "FromIndex", ToIndex = "ToIndex", trigger = "EnableSwitch"
OVERVIEW = 0
state names = FromOveview, FromWeapon, FromSkill, FromUpgrade, FromBreak, FromEquip
```

当前 31 个角色的 main controller 审计均为 `main_overview_exact`；状态条件和
start/loop 入口来自各自 AnimatorController JSON。以 Zhuang 为例，start 为
`A_actor_zhuangfy_ui_overview_start_01`，loop 为
`A_actor_zhuangfy_ui_overview_loop_01`，并有 24 个私有 widget clip；这些是
角色 prefab/controller 的动画资源，不是一个共享的 Timeline Director。

## 旧根清理、异步替换和 LateTick

`PhaseCharInfo._RefreshCharModel` 在创建替代角色前调用
`RemoveAllPhaseCharItems()`。`PhaseBase` 的实现会对每个旧 item 调用
`item:Destroy()`、从 phase 映射移除、取消所有未完成 ModelLoader 请求并清空
coroutine/request 映射；`PhaseCharItem._OnDestroy` 再调用
`modelLoader:UnloadModel(self.go)` 并清空 `go/uiModelMono/animator`。随后才开始
新的 `LoadModelAsync`。这使得源级结论是“旧 item 先卸载、替代 item 后异步
创建”，而不是 roster 常驻双根。

`_HandleLookAtIK` 在目标是 Overview 且不是 skip-in 时注册 `LuaUpdate:Add`
的 `LateTick`。它只等待当前 Animator 的 Overview state 到达
`LOOK_AT_CROSS_FADE_STATE_NORMALIZED_TIME`，再 tween LookAt 权重并移除 callback；
如果 Animator 已不存在，也会移除 callback。`LuaUpdate` 本身按 action group
执行回调，但这组 Lua 源没有把 Unity Animator sampling 与实际渲染提交的帧
边界闭合。因此可以证明 LateTick 是 look-at 时序，不可以证明它会 spawn VFX
或让旧、新根同帧渲染。既有运行时观察仅支持“动画/Timeline sampling 后的
follower LateTick；旧根销毁前的同更新 LateTick 是窄调度边界”，不支持双演员
渲染结论。

## 与 Gacha `baofa` 的分离

Gacha 代码明确走另一条协议（`UI/Panels/GachaChar/GachaCharCtrl.lua`）：

1. 从 `UIConst.GACHA_CHAR_TIMELINE_PATH` 加载 per-character prefab，挂到房间
   `TimelineRoot`；
2. 创建 `GachaCharTLHelper` 及独立 AdditionalLights、CameraTracks prefab；
3. `SampleToBeginning()` 后由 timer 调 `PlayFromStart()`；
4. `_ClearCurAsset` 调 helper dispose 并 `GameObject.Destroy(m_curCharObj)`。

原始 `gacha_char_zhuangfy_Effect` Timeline（PathID
`5154919875066767714`，Director PathID `3160965858571562263`）是 16 tracks、
7 ControlTracks、4 AnimationTracks、5 EntityVFX tracks 的独立序列化资产。
其中 `baofa` 是 Effect track order 3；`piaodai`、`finger_lightning`、
`trail01`、`jianqiang` 也绑定在该 Gacha prefab 的 Effect 树，orders 9–13 的
EntityVFX 绑定同一 Gacha actor deco。故 `baofa` 的具体 prefab/ControlTrack
所有权可以闭合为 Gacha，不能转借给 Overview。Overview controller 中出现
同名请求（如 Zhuang 实验 prefab）不改变这一来源边界。

## 验证结果与未闭合项

- `verify_charinfo_switch_owner_recovery.py`：通过；输出确认
  `GUIDE_CHAR_INFO_CHANGE_CHAR@0x428`、native VA `0x18764ea60`、Lua 1290
  文件和 IFix `0x85ad` 外部边界。
- `verify_overview_animator_native_recovery.py`：native source/hash gate 通过
  后，在生成审计层以 `KeyError: 'transition_duration_fixed'` 失败。
  这是 `character_ui_controller_audit.json` 与 verifier schema 的漂移，不能
  当作 native body/hash 失败；修复/兼容该字段后应重跑完整 verifier。
- `unity_endfield_graph_shader_lab/.../EndfieldOverviewPlayback.cs` 定义了
  `IEndfieldOverviewEffectSpawner` 接口和 request publish/finish callsite，
  但仓库无任何实现。该 lab 代码是实验播放器，不是已证实的 retail
  Overview runtime owner；不要用它把 `baofa` 等请求提升为结论。

下一步最窄探针：

1. 在同一 gated build 上跟踪 `UIModelLoader.LoadModelAsync/UnloadModel`、
   `LuaManagerInst.actionLateTick` 与 Unity Animator sampling/render commit，
   才能回答旧根销毁与 LateTick 的实际 frame 边界；
2. 反查 Character Info 的专属 effect prefab/config 或 effect-manager native
   callsite，必须同时证明 source path、owner、mount、start/stop 条件后才能
   实现/认领 Overview VFX；
3. 修正 `transition_duration_fixed` 审计 schema 漂移，重新执行 31-controller
   native/serialized verification；在此之前保持 actor-specific entrance VFX
   请求 fail-closed。

