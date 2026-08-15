# Character Info 入场效果：视频—源数据对齐索引（2026-08-15）

## 结论先行

`videos/2026-08-15_10-32-32.mkv` 可以可靠地提供 Character Info 入场的
时间和可见层验收条件，但不能单独证明 Unity prefab、材质、挂点、Timeline
或 Lua/native producer。当前唯一完成“视频身份 → 角色源数据 → Animator/
Prefab/clip”闭合的是 **庄方仪（`chr_0030_zhuangfy`）**，时间为视频绝对
`102.5–109.5 s`（约 `01:42.5–01:49.5`）。

其它时间段下面只使用外观标签；这些标签不是角色 token，也不用于推导
owner。视频中可见的共同层和角色特有层必须分开记录：

| 层 | 视频能证明什么 | 当前源数据边界 |
|---|---|---|
| Character Info 舞台/UI | 灰白舞台、固定 UI、短暂清场/残影 | `PhaseCharInfo._PlayModelEffect` 的共享 `charEffect` 已闭合；它不是角色专属 VFX |
| 身体/服装/头发/武器动作 | 每个槽位有自己的入场和 idle 过渡 | 31 个 Overview AnimatorController JSON 已导出；具体槽位仍需身份 join 才能归属 |
| 外部粒子、带状/几何层、局部光晕 | 只可记录出现时间、屏幕位置、持续区间 | 除共享 `CharEffect` 外，大多数槽位没有角色专属 prefab/material/Timeline owner |
| 伴生物/道具 | 可见独立对象及其动作 | 没有源链时不能把其外观归给某个角色资产 |
| 亮度/bloom/残影 | 局部时序和衰减 | 不足以证明全局曝光、后处理或某个 shader pass |

## 可复核的庄方仪闭合槽位

### 视频时间与视觉层

源：`scratch/character_recovery/video_entry_timing/zhuangfy_overview_video_timing.md`
及其 `keyframes/`、`contact_entry_102p5_109p5.jpg`。

| 视频绝对时间 | 相对首个干净庄方仪画面 | 可见层 | 置信度 |
|---|---:|---|---|
| `102.5–102.8` | `-0.3–0.0 s` | UI/流式切换残影、横向块状断裂；不能当作 authored VFX 起点 | 直接观察；实现未定 |
| `102.8–103.3` | `0.0–0.5 s` | 角色清晰出现；白色半透明带/弧与绿色局部发光同时出现 | 直接观察；层身份未定 |
| `103.3–105.1` | `0.5–2.3 s` | 白色带状/碎片层达到最大屏占比；角色旋转/展开；绿色局部层靠近手/躯干移动 | 直接观察；不区分 `trail01`、`piaodai` 或其它层 |
| `105.1–105.6` | `2.3–2.8 s` | 白色主轮廓快速减弱，绿色胸口/手部局部仍留存 | 直接观察；衰减边界约 ±0.2 s |
| `105.6–108.0` | `2.8–5.2 s` | 身体进入 idle；绿色小立方/局部线条在手部附近持续或移动 | 直接观察；不能命名为 `finger_lightning` |
| `108.0–108.7` | `5.2–5.9 s` | 手/画面左侧短暂白绿局部 flare 与少量条带 | 直接观察；不能因此启用 `baofa` |
| `108.8–109.5` | `6.0–6.7 s` | 局部光和小立方衰减，回到干净 idle | 直接观察；视频未给出 prefab 生命周期 |

### 源数据交叉验证

以下链条是源数据闭合的，但只闭合身体/共享效果；不能把 Gacha 效果
自动升级为 Overview owner：

| 证据 | 结果 |
|---|---|
| `AnimatorController#1012921_p4E9FDAF73497547E.json` | `chr_0030_zhuangfy_controller`，1 layer、40 states；`Overview.FromOveview → A_actor_zhuangfy_ui_overview_start_01`，并有 `Overview.OverviewIdle` |
| `Zhuangfy/zhuangfy_ui_recovery_manifest.json` | 主身体、`chr_0030_zhuangfy_deco_1/2/3` 私有 DecoItem、Overview start/loop 和场景 camera/light/portrait 输入均有记录 |
| Overview body start clip | 仅有 `PostAudioEvent("au_actor_zhuangfy_ui_overview_start")`，时间 `0.1125`；没有 effect-spawn AnimationEvent |
| Overview loop / audited private widget clips | 无 effect-spawn AnimationEvent |
| `CharInfo` serialized owner reports | `PhaseCharInfo._PlayModelEffect` 重新挂载共享 `sceneObject.view.charEffect` 到 `singleEffects/effect<height>`；`M_UI_charChoose_12` / `HGRP/Effect/VFXRefract` 是共享层 |
| `zhuangfy_gacha_timeline_entity_vfx_contract.json` | `piaodai`、`jianqiang`、`finger_lightning`、`baofa` 等 Gacha Timeline/EntityVFX 数据准确存在，但 owner 是 Gacha；不能由视频把它们提升为 Overview owner |

因此，庄方仪槽位当前最准确的分类是：

```text
body Overview animation       source-closed
shared Character Info CharEffect source-closed
Gacha piaodai/etc.             source-closed, but Gacha-only
Overview-specific white/green VFX owner unresolved
```

## 全片逐时段视觉层索引

下表沿用 `scratch/character_recovery/entrance_video_analysis/report.md` 的
绝对 PTS。标签是外观描述，不是角色识别；只有庄方仪槽位有源数据身份标记。
`shared` 表示所有 Character Info 槽位都可接受的共享层，不表示它解释了
该行的角色特效。

| 绝对时间（s） | 外观槽位标签 | 视觉层（按可见事实） | 源对齐状态 |
|---:|---|---|---|
| `0–5` | 深绿短发男性 | 身体 idle、弱接地阴影、固定 UI | shared；角色 owner 未 join |
| `5–13` | 白发青绿色 | 青绿矩形/带状层、手臂/长发/衣摆动作、局部 bloom | 特效 owner 未解析 |
| `24–32` | 黑红男性/红翼 | 红色披风/翼状大 alpha 层、碎片、手臂动作 | 特效 owner 未解析 |
| `38–47` | 青绿色重复入场 | 身体动作、前方和两侧能量带 | 特效 owner 未解析 |
| `48–55` | 红狐耳/紫红 | 紫红爆发、粒子衰减、手部/武器动作 | 特效 owner 未解析 |
| `64–73` | 双马尾红黑服 | 旋转展开、长发/披风/飘带 | 身体/布料层未 join |
| `77–87` | 紫蓝猫耳 | 粉紫软光晕/粒子、窄幅 idle | 特效 owner 未解析 |
| `88–101` | 白粉发与伴生物 | 粉色圆形/食物样伴生物、手部道具动作 | 伴生物 owner 未解析 |
| `102.5–109.5` | **庄方仪** | 横向 glitch、白色带/碎片、绿色局部层、idle 衰减 | **身份与 body/controller 闭合；特效仅 shared + Gacha 交叉参考，Overview owner 未闭合** |
| `114–129` | 粉发与大型粉色球 | 大型伴生物悬浮/摆动、张臂/转身 | 伴生物 owner 未解析 |
| `130–148` | 灰黑短发 | 主要是身体姿势、服装摆动，弱外部 VFX | 角色身份/owner 未 join |
| `148–162` | 白发长外套男性 | 灰色几何/hologram 叠层、回到中性 idle | 几何层 owner 未解析 |
| `163–173` | 黑白服 | 手旁金橙圆球/光环、短 bloom | 局部光 owner 未解析 |
| `174–184` | 蓝灰发 | 低位水平模糊/滑入、抬手 | 可能是运动/残影；shader/producer 未证实 |
| `188–198` | 红发男性 | 红色刀光/能量线、手部火光、挥动 | 武器/局部光 owner 未解析 |
| `200–209` | 青绿色服男性 | 长刀/大剑横向动作，少外部粒子 | 身体/武器 owner 未 join |
| `210–228` | 金发兽耳白服 | 纸张/道具与手部动作，低 VFX | 道具 owner 未解析 |
| `229–236` | 白色兜帽 | 淡入、小幅 idle、低 VFX | 角色身份/owner 未 join |
| `237–244` | 黄绿发 | 短暂金色全身/手部光脉冲 | 光脉冲 owner 未解析 |
| `244–254` | 红发重装 | 烟雾、橙红局部光、枪械姿态 | 烟雾/枪械 owner 未解析 |
| `254–270` | 粉发与粉色 blob | 横向残影、大型透明伴生物漂浮 | 伴生物 owner 未解析 |
| `270–283` | 蓝青长发 | 大幅头发/飘带展开、满幅构图 | 头发/飘带 owner 未解析 |
| `283–296` | 熊猫 | 横向块状残影、低位道具姿态、少彩色 VFX | 残影实现/道具 owner 未解析 |
| `296–308` | 绿发 | 横向扫描残影、红色警告文字样板、半透明屏幕层 | hologram/UI owner 未解析 |
| `308–319` | 白发蓝护目镜/兜帽 | 白雾/烟尘、低位落地/抬身 | 雾层/动作 owner 未解析 |
| `319–330` | 黄黑工作服男性 | 工具/武器操作、弯身/抬臂、少 VFX | 道具/动作 owner 未 join |
| `330–340` | 红发白黑服 | 空舞台出现、抬臂/转身、低 VFX | 角色身份/owner 未 join |
| `340–350` | 角状头饰黑红服 | 低位/转身出现、服饰/武器 | 角色身份/owner 未 join |
| `350–361` | 白发尖角男性 | 近静态入场、弱特效 | 静态基线；owner 未 join |
| `360–370` | 绿发兜帽 | 转身/手臂、布料、弱阴影 | 角色身份/owner 未 join |
| `370–378.367` | 蓝发兽耳男性 | 抬臂展示后 idle，视频结束 | 角色身份/owner 未 join |

## 角色源 roster 与负证据

当前 targeted controller audit 的 31 个 actor token 是：

```text
endminm endminf pelica chen wolfgd ikut azrila seraph avywen aglina
aurora lifeng laevat yvonne dapan karin meurs whiten bounda antal deepfin
ardelia lastrite pograni tangtang wulfa zhuangfy mifu lizhiyan camille liino
```

这只证明这些 token 的 Overview AnimatorController/clip 引用可被审计，
不证明视频中每一个视觉槽位已经与其中一个 token 对齐。当前 controller
恢复统计为 `31 actors / 31 main Overview / 636 controller-proven widget
states`；完整 Viewer prefab catalog 仍有 Endminm 缺口（此前 verifier 为
`30/31`），所以不能把 controller 数量写成完整 prefab 恢复。

已确认的负证据：

1. 庄方仪和诀的 Overview body start clip 只有音频 AnimationEvent；loop
   和已审计私有 widget clip 没有 VFX/effect-spawn event。
2. 当前审计没有闭合 retail Overview 的 `AnimatorPlayEffectHelper` 或
   角色专属 `EffectSetting` producer chain。
3. `piaodai`、`baofa`、`finger_lightning` 等名字在 Gacha Timeline/请求中
   出现，不能由视频颜色、相似形状或时间重合证明是 Overview owner。
4. 视频是屏幕录制，清场/横向 glitch/残影可能来自页面切换、流式边界、
   动画或后处理；不能直接解释为 RenderTexture 清屏、某个 shader pass
   或 prefab 生命周期。
5. 除庄方仪外，本索引没有把某个观察槽位分配给洛茜或任何其它角色；
   现有 source plan 中洛茜仍缺 playable prefab/controller/clip/camera/light
   join，不从视频推导其身份。

## Unity 恢复使用方式

视频可作为 acceptance oracle：

- 固定 Character Info UI/灰白舞台，不因入场改变屏幕空间布局；
- 庄方仪清晰出现后约 `0.3–0.8 s` 已有白色半透明带和绿色局部层；
- 白色主轮廓约在相对 `2.3–2.8 s` 退出主导；
- 手/躯干局部绿色层可持续到相对 `5.2 s`，约 `5.2–5.9 s` 有疑似局部 flare；
- 对其它角色只验证身体/道具/布料和各自的可见时序，直到出现完整
  prefab/material/Timeline/consumer 源链才添加角色专属 VFX。

主要证据入口：

- `scratch/character_recovery/entrance_video_analysis/report.md`
- `scratch/character_recovery/entrance_video_audit/report.md`
- `scratch/character_recovery/video_entry_timing/zhuangfy_overview_video_timing.md`
- `scratch/character_recovery/overview_character_effect_owners/ownership_index.json`
- `scratch/character_recovery/overview_animator_controllers/controller_audit.json`
- `reports/assets/character_recovery/overview_char_effect_vfxrefract_scenemv_contract_20260815.md`
- `reports/assets/character_recovery/overview_char_effect_serialized_owner_20260815.md`

本报告没有修改 Unity、memory 或任何源数据，也没有将视频外观推断为
未闭合的 owner。
