# Character Info `CharEffect` / VFXRefract / SceneMV 执行边界

日期：2026-08-15
范围：固定客户端中的 `M_UI_charChoose_12`、`HGRP/Effect/VFXRefract`、
`_USE_RBOFFSET`、`_RefractTex`，以及它们进入粒子渲染、Distortion、透明队列
和 SceneMV 的最小 source-closed 语义。

## 结论

`M_UI_charChoose_12` 是 Character Info 共用 `CharEffect` prefab 的一个
**queue 3000、LightMode=Distortion 的主 Distortion pass**。queue 3000 不能把它
送入 after-DOF 透明列表；后者由独立的约 `3660..3740` 队列范围和
`TransparentAfterDOF` native pass 管理。它也不是普通 color-only transparent
对象：原始 `VFXRefract` 程序同时写 `SV_Target0` 和 `SV_Target1`，必须在
SceneColor snapshot + SceneMV Load/Store 的 MRT pass 中执行。

当前可以给出的最小实现语义是：

```text
CharInfo sceneObject.view.charEffect
  -> CharEffect/trail ParticleSystemRenderer (唯一 enabled renderer)
  -> M_UI_charChoose_12 (identity-gated material)
  -> HGRP/Effect/VFXRefract, pass Refraction, LightMode=Distortion
  -> main Distortion renderer list, queue 3000
  -> source SceneColor snapshot + SceneMV target 1 Load/Store
  -> t0 = _RefractTex (T_fx_mask_01_M), t1 = incoming _SceneColorTexture
  -> _USE_RBOFFSET compiled branch: base + offset SceneColor samples
  -> Target0 distortion/refracted color, Target1 selected transparent MV
```

这只闭合选定材质的身份、shader pass、纹理输入、queue/pass 选择和 MRT
接口；不闭合运行时粒子实例的 frame、culling、screen-size、VFX globals 或
物理 RT alias。Unity lab 仍应对未满足全部 gate 的路径 fail-closed。

## 固定 native gate

本报告先通过 `scripts.common.check_installed_native_inputs()`，原生结论只适用
以下显式输入对：

```text
GameAssembly.dll
  D:/Program Files/Endfield Game/GameAssembly.dll
  sha256 0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce

global-metadata.dat
  D:/Program Files/Endfield Game/Endfield_Data/il2cpp_data/Metadata/global-metadata.dat
  sha256 90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e

status: validated
```

GameAssembly/metadata 缺失、路径漂移或 hash 不匹配时，下面的地址和 native
执行判断全部失效，不得回退到另一 build。

## 序列化 owner 与 Material identity

来源：

- `reports/assets/character_recovery/overview_char_effect_serialized_owner_20260815.md`
- `export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material/M_UI_charChoose_12_p3CE8306B7872A127.json`
- `export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/Shader/HGRP_Effect_VFXRefract_p6BC753C54B47D1ED.shader`
- `export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Texture2D/T_fx_mask_01_M_p9E34304E227EA66A.png`

Material JSON SHA-256：

```text
M_UI_charChoose_12 JSON  531854EC624FB21B74A2793FC6A10A5FEA739CEB2A8D432C2CCDCCD3815BE1A6
VFXRefract LOD600 blob   C18D2F942CDB6A4CC921FE81C43A7E560EC0A46C9C812DAD0E894465F16D2F0D
T_fx_mask_01_M PNG       78B75041D63840BC322E254EC60FC821A613A222D7A85B874FC816A2A53EF29D
```

精确对象关系：

| 对象 | source identity / state |
|---|---|
| Prefab | `assets/beyond/dynamicassets/gameplay/prefabs/charinfo/charinfochar.prefab`，serialized CAB `45edfbd38d2a68534810c905ce39aff4` |
| Root `CharEffect` | ParticleSystemRenderer disabled；其 child `trail` 是实际可见 renderer |
| `CharEffect/trail` | ParticleSystem + enabled ParticleSystemRenderer |
| Material | `M_UI_charChoose_12`, PathID `4388811075012960551` |
| Shader | `HGRP/Effect/VFXRefract`, PathID `7766268189260370413` |
| Texture | `_RefractTex = T_fx_mask_01_M`, PathID `-7046954404783675798`，scale `(1,1)`、offset `(0,0)` |
| Material queue/tags | custom queue `3000`; `RenderType=Transparent` |
| Disabled passes | `DepthOnly`, `GBuffer` |
| Keywords | valid `_USE_RBOFFSET`; invalid keywords none |

对当前材质最重要的序列化数值：

```text
_SurfaceType=1 (Transparent), _CullMode=2, _ZTest=4, _ZWrite=0
_SrcBlend=5, _DstBlend=10, _AlphaSrcBlend=1, _AlphaDstBlend=10
_EnableTransparentMV=0, _MVSrcColorBlend=3, _MVDstColorBlend=6
_Intensity=0.087, _TintColorAlpha=1, _ProcedureAlpha=1
_RefractIsNormal=0, _RefractDir=(-2,-0.1,0,0)
_UseMainTexAsMask=1, _UseRBOffset=1, _RBIntensity=1
_RBOffset=(5,0,0,0), _UseRGBOffset=0
_RefractUseRBOffset=0, _UseMask=0, _UseDissolve=0
_UseNearCameraFade=0, _RefractUVSpeed=(0,0,0,0)
```

`_RefractUseRBOffset` 和 `_UseRBOffset` 是两个不同的 serialized control：
后者打开 shader keyword `_USE_RBOFFSET`，前者在 refraction-direction 分支中
仍为 0，不能把它们合并成一个开关。

## 原始 shader / PSO 边界

AnimeStudio 导出的 VFXRefract LOD600 blob 声明 D3D11、Vulkan 各 334 个
program entries。SubShader/Pass 的转换文本为：

```text
SubShader LOD 600
  Queue=Transparent
  RenderPipeline=HGRenderPipeline
  RenderType=HGUnlitShader
Pass "Refraction"
  LightMode=Distortion
  Queue=Transparent
  Blend 0 Zero Zero, Zero One
  Blend 1 Zero Zero, One One
  ZTest Off, ZWrite Off, Cull Off
  outputs: SV_Target0 + SV_Target1
```

这些 `Zero/Off` 是转换器对 property-bound `m_State` 字段的有损默认值，
不是 live PSO。解析后的原始状态把 Target0/Target1 color blend、ZTest、
ZWrite 和 Cull 分别绑定到材质属性；Target0/Target1 alpha blend 才分别固定为
`Zero/One` 与 `One/One`。完整裁决见
`overview_vfxrefract_live_state_boundary_20260815.md`。

固定材质在 D3D11 的相关 program 是 `HG_ENABLE_MV + _USE_RBOFFSET` 变体，
其 fragment DXBC snippet hash 为 `f905de094d0261d5`（shader blob 内
`Endfield DXBC snippet 1`，offset `0xB0`，size `0xDE0`）。该变体声明：

```text
t0 = material texture sample path (_RefractTex)
t1 = incoming scene-color sample path (_SceneColorTexture)
cb1[26].x = program mip-bias input
SV_Target0 = reconstructed scene-color sample(s)
SV_Target1 = encoded current-frame transparent motion value
```

非 `_USE_RBOFFSET` 变体只从 `t1` 取一个 scene-color sample；
`_USE_RBOFFSET` 变体会在基础 screen UV 外再构造一个 `_RBOffset` 偏移 UV，
分别采样两处 scene color，并按 compiled 常量中的 RGB channel masks/权重
合成后写 Target0。不能用一个普通 `_SceneColorTexture` 单采样近似替代该变体。

选定 fragment 的 source-closed 操作形状是：

1. 由粒子顶点 UV、custom stream 和 UV speed/rotate 计算 `_RefractTex` UV，
   用 `SampleBias` 读取 `T_fx_mask_01_M`；
2. 以 `_RefractIsNormal=0` 选择固定 `_RefractDir=(-2,-0.1)` 分支，结合
   `_Intensity=0.087`、粒子顶点 alpha 和屏幕位置，得到基础 scene-color UV；
3. 因 `_USE_RBOFFSET`，使用 `_RBOffset=(5,0)` 形成第二 scene-color UV，
   对两次 `t1` 采样应用 compiled RGB offset 合成；
4. Target0 颜色 clamp 到 `[0,1000]`，alpha 受近相机淡入代码控制；本材质
   `_UseNearCameraFade=0`，不能从序列化数据推断出额外距离衰减；
5. Target1 的 fragment 末端明确写 `o1.zw=(1,0)`。透明 SurfaceType 和
   `_EnableTransparentMV=0` gate 使选定材质的 XY 为零，因此最窄目标语义是
   `Target1=(0,0,1,0)`，并以该 MRT attachment 的 indexed blend/Load/Store
   规则保留先前 SceneMV 的 motion RG。

上述 fragment 方程来自导出 shader 的 DXBC 反汇编，仍不等于 retail
renderer-list/culling/runtime-global 已全部闭合。

## Native HGRP route、queue 与 SceneMV

当前 build 的 native report 已定位主透明/Distortion 调度符号：

| native method | VA |
|---|---:|
| `ForwardPassUtils.PrepareForwardTransparentRendererList(cullResults, hgCamera, passNames, ...)` | `0x189babb58` |
| `ForwardPassUtils.PrepareForwardTransparentRendererList(hgrp, camera, ...)` | `0x189bab94c` |
| `ForwardPassUtils.PrepareTransparentPassData(...)` | `0x189bac2f8` |
| `ForwardPassUtils.RenderForwardTransparent(context, data)` | `0x189bacfcc` |
| `HGRenderPathScene.RenderPostProcessPhase1(...)` | `0x189bffeb0` |
| `TransparentAfterDOFPassConstructor.ConstructPass(...)` | `0x189bb2e40` |

source-closed 的选定场景顺序为：

```text
GBuffer / SceneMV neutral clear
  -> ForwardOpaque
  -> main ForwardOnly transparent
  -> main Distortion（M_UI_charChoose_12 在此，queue 3000）
  -> Phase 1 post（DOF/MotionBlur/...）
  -> after-DOF ForwardOnly（独立 queue range 3660..3740）
  -> Phase 2 post
```

因此：

- queue 3000 是透明排序 key，不是 after-DOF 开关；
- `LightMode=Distortion` 才是把该 renderer 送进主 Distortion list 的关键；
- `DepthOnly/GBuffer` disabled 意味着它不会成为 GBuffer 或独立 depth pass
  的 producer；
- `ForwardPassUtils.RenderForwardTransparent` 的 pass-local source-color、
  depth、SceneMV、blit 资源必须由当前 incoming SceneColor snapshot 和现有
  SceneMV attachment 提供；它不能自己制造 SceneMV 或环境 globals；
- after-DOF pass 不能接收此材质，除非另有 source-verified material/pass
  identity，同时满足其独立 queue/tag gate。

`sceneMV` 当前 build 的资源格式/生命周期已由既有 native audit 闭合为：

```text
format A2B10G10R10_UNormPack32
neutral clear (0.5,0.5,0,0) 只发生在首次 owner
main transparent/Distortion 使用 target 1 Load/Store
_SceneColorTexture = draw 前 incoming SceneColor snapshot
depth: Distortion 子通道 read/write；ForwardOnly 子通道 read-only
```

M_UI 选定 program 的 Target1 `(0,0,1,0)` 不表示可以省略 MRT。Target1 的
attachment 仍需 Load/Store，以保留此前 opaque/character writers 的 SceneMV
RG，并保留 B=1 的 selected transparent contract。

## Unity 可实现的最小 source-closed 单元

只有以下 identity tuple 全部匹配时才允许实现该单元：

```text
material PathID 4388811075012960551
material name M_UI_charChoose_12
shader PathID 7766268189260370413 / HGRP/Effect/VFXRefract
valid keyword exactly {_USE_RBOFFSET}
custom queue 3000 + RenderType Transparent
disabled passes exactly includes DepthOnly, GBuffer
_RefractTex PathID -7046954404783675798
selected D3D11 program HG_ENABLE_MV + _USE_RBOFFSET
```

执行时的最小条件：

1. 保留 draw 前 SceneColor 作为 `_SceneColorTexture` snapshot，并 clone 真实
   SceneColor descriptor 作为 Target0；不能用固定 `DefaultHDR` 猜 descriptor；
2. 绑定已有 SceneMV 为 Target1，格式为 `A2B10G10R10_UNormPack32`，使用
   Load/Store；不要因为 `_EnableTransparentMV=0` 改成 single-RT；
3. Distortion 子通道以 source-closed depth access 执行，不能把普通透明
   `DrawRenderers` 直接当作该 pass；
4. 绑定 `_SceneColorTexture` 为 incoming snapshot、`_RefractTex` 为精确
   `T_fx_mask_01_M`，传入粒子顶点 UV/color/custom stream 和 shader 所需
   camera/VFX globals；
5. 选择 `HG_ENABLE_MV + _USE_RBOFFSET` program，保留两次 SceneColor sample、
   `_RBOffset` 和 compiled channel mask 方程；
6. pass 结束后发布新的 active SceneColor handle；下游 post/bloom 读取新的
   handle，旧 snapshot 只能在最后一个 consumer 结束后释放；
7. 缺少 SceneMV、显式 depth、真实 descriptor、shader variant、粒子 stream
   或 live globals 时，拒绝绘制而不是退回 `EndfieldVFXRefractRecovered` 的
   单 RTV 近似。

## 未闭合边界与下一探针

- 当前离线证据证明 serialized owner、shader blob、Material/texture identity、
  LightMode/queue 和 MRT 输出接口，但没有证明某一帧 retail particle
  instance 的 culling、sorting tie、simulation time、screen-size 和
  `_VFXParams` live contents。
- shader blob 有原始 D3D11/Vulkan program，但当前 lab 没有等价的 native
  HG renderer-list producer、SceneColor handle chain 和 explicit depth owner；
  因此不能仅替换 shader 文件就宣称 VFXRefract 已恢复。
- 解析后的 shader `m_State` 已证明 color blend、depth 与 cull 是材质属性绑定；
  当前最窄状态使用 `_SrcBlend=5/_DstBlend=10`、
  `_MVSrcColorBlend=3/_MVDstColorBlend=6`、`_ZTest=4`、`_ZWrite=0`、
  `_CullMode=2`。最终 D3D12 PSO 及可能的 RenderStateBlock override 仍需
  RenderDoc/native pass capture 闭合。
- 需要在同一 gated build 上捕获：Material/Renderer 实例进入
  `PrepareTransparentPassData` 的 renderer list、Distortion subpass 的实际
  attachment descriptors、Target0/Target1 blend state、以及 `_SceneColorTexture`
  与 SceneMV 资源 alias；没有这些 live facts 时保持 fail-closed。

既有 supporting reports：

- `reports/assets/character_recovery/overview_char_effect_serialized_owner_20260815.md`
- `reports/assets/character_recovery/glow902_native_scene_mv_queue_20260815.md`
- `reports/assets/character_recovery/gacha_scene_mv_motion_contract.md`
- `unity_endfield_graph_shader_lab/scratch/character_recovery/vfx_mrt_lab_gap/README.md`
- `unity_endfield_graph_shader_lab/scratch/character_recovery/vfx_mrt_implementation_design/README.md`
