using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldZhuangfyParticleEffectImporter
    {
        private const string ContractAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_particle_inventory.json";
        private static readonly string[] NativeTextureContractAssetPaths =
        {
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_entity_vfx_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_trail902_903_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_lightning902_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_mode4_dian_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_soft0840_native_texture_payloads.json",
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_specific_lightning901_native_texture_payloads.json",
        };
        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles";
        private const string PrefabRoot = GeneratedRoot + "/Prefabs";
        private const string MaterialRoot = GeneratedRoot + "/Materials";
        private const string MeshRoot = GeneratedRoot + "/Meshes";
        private const string TextureRoot = GeneratedRoot + "/Textures";
        private const string SourceRoot = GeneratedRoot + "/Source";
        private const string FailClosedShaderName =
            "Hidden/Endfield/Recovered/VFXUnavailableFailClosed";
        private const string RecoveredBaseV2ShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT";
        private const string RecoveredRadialBlurShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRadialBlurMRT";
        private const string RecoveredRefractShaderName =
            "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT";
        private const string ExpectedSchema =
            "endfield.zhuangfy-gacha-particle-inventory.v1";
        private const long DeferredLine006Lightning901MaterialPathId =
            -3644022605689571376L;
        private const long DeferredZhuangfyLightning901MaterialPathId =
            6070151493152993176L;
        private const long DeferredDian902MaterialPathId =
            6860781171007043348L;
        private const long DeferredDian901MaterialPathId =
            -5238439183655129709L;
        private const long DeferredDian904MaterialPathId =
            6326079578008630221L;
        private const long DeferredLightning902MaterialPathId =
            -1087199587020585838L;
        private const long Lightning902RendererPathId =
            296863772203003159L;
        private const long Lightning902MeshPathId =
            7440796479737110652L;
        private const long Line006RendererPathIdA =
            -3406688761151443689L;
        private const long Line006RendererPathIdB =
            5716687712887745815L;
        private const long Lightning901ThirdRendererPathId =
            -1642210484143543017L;
        private const long Dian902ManualRendererPathId =
            -7137180953804559081L;
        private const long Dian901FixedManualRendererPathId =
            -2376706058147287785L;
        private const long Dian901MeshPathId =
            -8817602188124735674L;
        private const string Line006ReplayKeyword =
            "_LINE006_EXACT_STEP_REPLAY";
        private const string Line006ScopedMaterialAssetPath =
            MaterialRoot + "/M_fx_ui_lightning_901_line006_renderer_scoped.mat";
        private const string Dian902ManualReplayKeyword =
            "_DIAN902_EXACT_MANUAL_REPLAY";
        private const string Dian902DynamicReplayKeyword =
            "_DIAN902_EXACT_DYNAMIC_REPLAY";
        private const string Dian902ScopedMaterialAssetPath =
            MaterialRoot + "/M_fx_ui_dian_902_manual_renderer_scoped.mat";
        private const string Dian901FixedManualReplayKeyword =
            "_DIAN901_EXACT_FIXED_MANUAL_REPLAY";
        private const string Dian901DynamicReplayKeyword =
            "_DIAN901_EXACT_DYNAMIC_REPLAY";
        private const string Dian901ScopedMaterialAssetPath =
            MaterialRoot + "/M_fx_ui_dian_901_fixed_manual_renderer_scoped.mat";
        private const string Lightning902ReplayKeyword =
            "_LIGHTNING902_EXACT_RUNTIME_REPLAY";
        private const string Lightning902ScopedMaterialAssetPath =
            MaterialRoot + "/M_fx_ui_lightning_902_renderer_scoped.mat";
        private const string Dian904DormantCandidateKeyword =
            "_DIAN904_EXACT_DORMANT_CANDIDATE";
        private const string Dian904DormantCandidateMaterialAssetPath =
            MaterialRoot + "/M_fx_ui_dian_904_dormant_candidate.mat";

        private sealed class SelectedMaterialIdentity
        {
            public long materialPathId;
            public string materialName;
            public long originalShaderPathId;
            public string[] orderedKeywords;
            public int customRenderQueue;
            public string recoveredShaderName;
        }

        // Admission is intentionally all-or-nothing.  These five source facts
        // are read from the hash-pinned original Material JSON.  A row which
        // matches only some facts continues to use the ColorMask-0 shader.
        private static readonly Dictionary<long, SelectedMaterialIdentity> SelectedMaterials =
            new Dictionary<long, SelectedMaterialIdentity>
            {
                [2353741667905894768L] = Selected(
                    2353741667905894768L, "M_fx_ui_zhuangfy_baodian_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                // The separate M_fx_ui_lightning_901 identity used by the
                // candidate Line006 renderers is already unselected. Keep
                // M_fx_ui_zhuangfy_lightning_901 fail-closed as well: neither
                // producer boundary supports material-wide admission.
                [8498796821937393461L] = Selected(
                    8498796821937393461L, "M_fx_ui_zhuangfy_redwave_901",
                    -1430105248647086886L, 3701, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1"),
                [6089760714367974764L] = Selected(
                    6089760714367974764L, "M_fx_ui_zhuangfy_wave_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2"),
                [604984703151022578L] = Selected(
                    604984703151022578L, "M_fx_ui_lizi_904",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName),
                [8923592236562190849L] = Selected(
                    8923592236562190849L, "M_fx_ui_lizi_905",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                [6961237401777914568L] = Selected(
                    6961237401777914568L, "M_fx_ui_lizi_907",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                [372081524135426916L] = Selected(
                    372081524135426916L, "M_fxgp_char_buff_speedup_wind",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [5166293308344537026L] = Selected(
                    5166293308344537026L, "M_fx_ui_power_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-2962584200618057971L] = Selected(
                    -2962584200618057971L, "M_fx_ui_power_902",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [3072984469136739145L] = Selected(
                    3072984469136739145L, "M_fx_ui_power_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-1885790008064284819L] = Selected(
                    -1885790008064284819L, "M_fx_ui_power_904",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-2472780701872448179L] = Selected(
                    -2472780701872448179L, "M_fx_ui_wind_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-2464485149069692213L] = Selected(
                    -2464485149069692213L, "M_fx_ui_wind_902",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-481671530717440526L] = Selected(
                    -481671530717440526L, "M_fx_ui_wind_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
                [-3147485977667327360L] = Selected(
                    -3147485977667327360L, "M_fx_common_teleport_04",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [-558732376733342310L] = Selected(
                    -558732376733342310L, "M_fx_gacha_06",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [-561058327361322829L] = Selected(
                    -561058327361322829L, "M_fx_gacha_06_02",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [1675752963770326212L] = Selected(
                    1675752963770326212L, "M_fx_gacha_07",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [-3804188305816339485L] = Selected(
                    -3804188305816339485L, "M_fx_gacha_08",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [-2076604643738811551L] = Selected(
                    -2076604643738811551L, "M_fx_gacha_09",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName),
                [-6856529186404785087L] = Selected(
                    -6856529186404785087L, "M_fx_ui_air_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName),
                [-4749208371984830935L] = Selected(
                    -4749208371984830935L, "M_fx_ui_lizi_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName),
                [-2029723268514944643L] = Selected(
                    -2029723268514944643L, "M_fx_ui_lizi_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName),
                [2045414994451622063L] = Selected(
                    2045414994451622063L, "M_fx_gacha_06_03",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-3848795757225564597L] = Selected(
                    -3848795757225564597L, "M_fx_ui_center_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-2271797759785840185L] = Selected(
                    -2271797759785840185L, "M_fx_ui_flash_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-1723331352657138430L] = Selected(
                    -1723331352657138430L, "M_fx_ui_line_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-6738056404114238530L] = Selected(
                    -6738056404114238530L, "M_fx_ui_line_902",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-4265278270051512237L] = Selected(
                    -4265278270051512237L, "M_fx_ui_lizi_906",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [2667210918427000667L] = Selected(
                    2667210918427000667L, "M_fx_ui_ray_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-5355010272266028806L] = Selected(
                    -5355010272266028806L, "M_fx_ui_ray_902",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_USE_SOFTBLEND"),
                [-6130217779138746968L] = Selected(
                    -6130217779138746968L, "M_fx_ui_glow_902",
                    -1430105248647086886L, 3005, RecoveredBaseV2ShaderName),
                [-6733847290233698619L] = Selected(
                    -6733847290233698619L, "M_fx_ui_dian_903",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                [-4900439733294365513L] = Selected(
                    -4900439733294365513L, "M_fx_ui_glow_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                [7348089829345858030L] = Selected(
                    7348089829345858030L, "M_fx_ui_glow_904",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_USE_SOFTBLEND"),
                [7274795463222849836L] = Selected(
                    7274795463222849836L, "M_fx_gacha_10",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1"),
                [-3074682495620605321L] = Selected(
                    -3074682495620605321L, "M_fx_gacha_12",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1"),
                [8036637690308906203L] = Selected(
                    8036637690308906203L, "M_fx_ui_lizi_902",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0"),
                [-4430407482763622607L] = Selected(
                    -4430407482763622607L, "M_fx_ui_suidian_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1"),
                [-6260844345225655675L] = Selected(
                    -6260844345225655675L,
                    "M_chen_jiaju_woodenstake_02_901",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_SOFTBLEND"),
                [-5871211190381214596L] = Selected(
                    -5871211190381214596L,
                    "M_fx_ui_rainbow_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_SAMPLE_TEX3", "_USE_POLARUV", "_USE_SCREENUV",
                    "_USE_SOFTBLEND"),
                [4280361687098003775L] = Selected(
                    4280361687098003775L, "M_fx_ui_trail_904",
                    -1430105248647086886L, 3000, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_USE_SOFTBLEND"),
                [-2448277796731839051L] = Selected(
                    -2448277796731839051L, "M_fx_ui_trail_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0"),
                [8004468266757089879L] = Selected(
                    8004468266757089879L, "M_fx_ui_trail_902",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_SOFTBLEND"),
                [6178811703178018719L] = Selected(
                    6178811703178018719L, "M_fx_ui_trail_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2",
                    "_USE_SOFTBLEND"),
                [-3401142303853875048L] = Selected(
                    -3401142303853875048L, "M_fx_ui_tianshiyi_901",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0", "_SAMPLE_TEX1", "_SAMPLE_TEX2"),
                [1921796838698546154L] = Selected(
                    1921796838698546154L, "M_fx_ui_tianshiyi_902",
                    -1430105248647086886L, 3699, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0"),
                [-7041899877744309324L] = Selected(
                    -7041899877744309324L, "M_fx_ui_tianshiyi_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_USE_FRESNEL"),
                [7912425062329828326L] = Selected(
                    7912425062329828326L, "M_fx_ui_tianshiyi_904",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_SAMPLE_TEX0"),
                [-7699805872829903908L] = Selected(
                    -7699805872829903908L, "M_fx_blur_01",
                    -6086025112163724183L, 3000, RecoveredRadialBlurShaderName,
                    "_USE_MASK"),
                [134426115865118089L] = Selected(
                    134426115865118089L, "M_fx_ui_niuqu_901",
                    7766268189260370413L, 3000, RecoveredRefractShaderName,
                    "_USE_DISSOLVE"),
                [-8085556558894828538L] = Selected(
                    -8085556558894828538L, "M_fx_ui_glow_903",
                    -1430105248647086886L, 3700, RecoveredBaseV2ShaderName,
                    "_USE_FRESNEL", "_USE_SOFTBLEND"),
            };

        private static readonly Dictionary<string, string[]> RequiredRecoveredProperties =
            new Dictionary<string, string[]>(StringComparer.Ordinal)
            {
                [RecoveredBaseV2ShaderName] = new[]
                {
                    "_MainTex", "_SampleTex0", "_SampleTex1", "_SampleTex2",
                    "_SampleTex3", "_OffsetTex", "_OffsetMaskTex",
                    "_DisturbTex1", "_DisturbTex2", "_WeightTex", "_MaskTex",
                    "_BlendTex", "_DissolveTex",
                    "_SurfaceType", "_BlendMode", "_Responsive",
                    "_EnableTransparentMV", "_InParticle",
                    "_DisableVertColor", "_DisableParticleInstanceColor",
                    "_TintColor", "_TintColorIntensity",
                    "_TintColorAlpha", "_ExpThreshold", "_ExpIntensity",
                    "_ProcedureAlpha", "_UseMainTexAsAlpha", "_MainTexMipmapBias",
                    "_UseVertexOffset", "_UseVertexOffsetMask", "_Bi_Offset",
                    "_OffsetSwitchDir", "_OffsetUVSet", "_OffsetIntensity",
                    "_OffsetDir", "_OffsetSpeed", "_OffsetMaskPower",
                    "_OffsetMaskSpeed",
                    "_MainTexUVSpeed", "_MainTexUVRotateMat", "_MainTexUVWeights",
                    "_UseSampleTex0", "_UseSampleTex1",
                    "_SampleTex0UseWeight0", "_SampleTex0UseWeight2",
                    "_SampleTex0UseWeight3",
                    "_SampleTex0UseWeight4", "_SampleTex0UseWeight5",
                    "_SampleTex1UseWeight1", "_SampleTex1UseWeight2",
                    "_SampleTex1UseWeight3", "_SampleTex1UseWeight4",
                    "_SampleTex1UseWeight5", "_SampleTex1UseDisturb",
                    "_UseSampleTex2", "_SampleTex2UseWeight4",
                    "_UseSampleTex3", "_UseSampleTex3AsAlpha",
                    "_SampleTex3MipmapBias", "_SampleTex3UVSpeed",
                    "_SampleTex3UVRotateMat", "_SampleTex3UVWeights",
                    "_SampleTex3UseWeight5", "_UsePolarUV", "_UseScreenUV",
                    "_UseDisturb", "_UseDisturb2", "_Bi_Disturb",
                    "_DisturbUseWeight", "_UseParticleDisturb",
                    "_DisturbTex1Normal", "_DisturbUIntensity1",
                    "_DisturbVIntensity1", "_DisturbTex2Normal",
                    "_DisturbUIntensity2", "_DisturbVIntensity2",
                    "_UseNearCameraFade", "_NearCameraFadeDistanceStart",
                    "_NearCameraFadeDistanceEnd",
                    "_NearCameraFadeDistanceStart2",
                    "_NearCameraFadeDistanceEnd2",
                    "_UseBlend", "_BlendTint",
                    "_UseMask", "_UseDissolve", "_DissolveScheduleOffset",
                    "_DissolveEdgeSharp", "_DissolveEmissiveEdge",
                    "_DissolveEmissiveColor", "_UseFresnel", "_FresnelColor", "_FresnelBias",
                    "_FresnelAffectOpacity", "_FresnelPower", "_FresnelFlip",
                    "_UseSoftBlend", "_SoftDistance", "_SoftBias", "_SrcBlend",
                    "_DstBlend", "_AlphaSrcBlend", "_AlphaDstBlend",
                    "_MVSrcColorBlend", "_MVDstColorBlend", "_ZTest", "_ZWrite",
                    "_CullMode", "_RecoveredLODFade",
                },
                [RecoveredRadialBlurShaderName] = new[]
                {
                    "_MaskTex", "_SurfaceType", "_EnableTransparentMV", "_InParticle",
                    "_TintColorAlpha", "_RadialBlurIntensity", "_CanterOffset",
                    "_Power", "_RadialBlurWithScreenDepth", "_UseMaskTexAsAlpha",
                    "_MaskTexUVSpeed", "_MaskTexUVRotate", "_UseNearCameraFade",
                    "_SrcBlend", "_DstBlend", "_AlphaSrcBlend", "_AlphaDstBlend",
                    "_MVSrcColorBlend", "_MVDstColorBlend", "_ZTest", "_ZWrite",
                    "_CullMode",
                },
                [RecoveredRefractShaderName] = new[]
                {
                    "_RefractTex", "_DissolveTex", "_SurfaceType",
                    "_EnableTransparentMV", "_TintColorAlpha", "_ProcedureAlpha",
                    "_RefractIsNormal", "_RefractUVSpeed", "_RefractTexUVRotate",
                    "_RefractDir", "_Intensity", "_Bi_Refract", "_UseDissolve",
                    "_DissolveUVSpeed", "_DissolveUVRotate",
                    "_DissolveScheduleOffset", "_DissolveEdgeSharp",
                    "_DissolveAffectBlend", "_UseNearCameraFade", "_SrcBlend",
                    "_DstBlend", "_MVSrcColorBlend", "_MVDstColorBlend",
                    "_ZTest", "_ZWrite", "_CullMode", "_RecoveredLODFade",
                },
            };

        private static readonly string[] ModuleNames =
        {
            "InitialModule",
            "ShapeModule",
            "EmissionModule",
            "SizeModule",
            "RotationModule",
            "ColorModule",
            "VelocityModule",
            "ClampVelocityModule",
            "NoiseModule",
            "CustomDataModule",
            "TrailModule",
            "UVModule",
        };

        // These members belong to the retail Unity/HGRP fork rather than the
        // stock 2022.3 serialization surface.  Their complete source payload
        // remains in the hash-pinned contract.  A newly encountered missing
        // field is never admitted by this list and therefore aborts import.
        private static readonly HashSet<string> KnownRetailOnlyFields =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "maxAliveDistance",
                "limitAliveDistance",
                "m_CharacterIndex",
                "m_RealtimeShadowCaster",
                "m_SubMeshRenderMode",
                "m_SubsetIndices",
                "m_RayTracingMode",
                "m_RayTraceProcedural",
                "m_RenderFoliageOccluder",
                "m_PlatformSpecificCastShadows",
                "m_ShadowProxyMesh",
                "m_EnableCharacterOutline",
                "m_EnablePerRendererLighting",
                "m_PerRendererLightingOffset",
                "m_PerRendererLightingAnchor",
                "m_LightModeMask",
                "m_RendererSortingFudge",
                "m_EnableHGGPUInstancing",
                "m_RenderInUI",
                "m_UISortingOrder",
                "m_CutoutTexture",
                "m_CutOutTextureOpacityMode",
                "m_CutOutMode",
                "m_CutOutThreshold",
                "m_DisableCutOutAnimation",
                "m_CutoutGeomUV",
                "m_TextureClipThresholdUpper",
            };

        internal sealed class Context
        {
            public Dictionary<long, Material> materials = new Dictionary<long, Material>();
            public Dictionary<long, Mesh> meshes = new Dictionary<long, Mesh>();
            public Dictionary<long, Texture2D> textures = new Dictionary<long, Texture2D>();
            public Dictionary<long, Dictionary<string, object>> nativeTextureRecords =
                new Dictionary<long, Dictionary<string, object>>();
            public Dictionary<long, string> materialNames = new Dictionary<long, string>();
            public Dictionary<long, string> shaderNames = new Dictionary<long, string>();
            public Dictionary<long, long> materialShaderPathIds = new Dictionary<long, long>();
            public Dictionary<long, Dictionary<string, object>> materialSources =
                new Dictionary<long, Dictionary<string, object>>();
            public List<string> retailOnlyFields = new List<string>();
            public Material line006ScopedMaterial;
            public Material dian901ScopedMaterial;
            public Material dian902ScopedMaterial;
            public Material lightning902ScopedMaterial;
            public Material dian904DormantCandidateMaterial;
            public int sourceArtifactCount;
        }

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public string unityVersion;
            public string contractAssetPath;
            public string contractSha256;
            public string dependencyArtifactAggregateSha256;
            public string generatedPrefabAggregateSha256;
            public int effectRootCount;
            public int hierarchyNodeCount;
            public int particleSystemCount;
            public int particleRendererCount;
            public int meshRendererCount;
            public int materialAssetCount;
            public int generatedMaterialAssetCount;
            public int rendererScopedRecoveredMaterialAssetCount;
            public int dian904DormantCandidateMaterialAssetCount;
            public string dian904DormantCandidateBoundary;
            public long[] rendererScopedParticleRendererPathIds;
            public int line006SharedFailClosedRendererCount;
            public string line006ActiveVertexStreams;
            public int dian901FixedManualScopedRendererCount;
            public int dian901FixedManualPlaybackComponentCount;
            public string dian901FixedManualPlaybackBoundary;
            public int dian902ManualScopedRendererCount;
            public string dian902ManualReplayStates;
            public int dian902ManualPlaybackComponentCount;
            public string dian902ManualPlaybackBoundary;
            public int lightning902ScopedRendererCount;
            public string lightning902RuntimeReplayBoundary;
            public int meshAssetCount;
            public int textureAssetCount;
            public int nativeTextureAssetCount;
            public string[] nativeTextureContractAssetPaths;
            public string nativeTextureContractSha256;
            public string nativeTexturePayloadAggregateSha256;
            public int recoveredMaterialAssetCount;
            public int failClosedMaterialAssetCount;
            public int sourceArtifactCount;
            public int perRendererLightingEnabledCount;
            public int outlineDisabledCount;
            public int realtimeShadowCasterCount;
            public int characterIndexOneCount;
            public int inertSubMeshLoopCount;
            public string[] retailOnlyFieldsPreservedInContract;
            public string forkFieldCompatibilityBoundary;
            public string shaderExecutionBoundary;
            public int selectedSceneMvNeutralMaterialCount;
            public string selectedSceneMvBoundary;
            public bool forkFieldCompatibilityBoundaryPassed;
            public bool selectedSceneMvNeutralPassed;
            public bool passed;
        }

        private sealed class ForkFieldFacts
        {
            public int perRendererLightingEnabledCount;
            public int outlineDisabledCount;
            public int realtimeShadowCasterCount;
            public int characterIndexOneCount;
            public int inertSubMeshLoopCount;
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Zhuangfy Gacha Particles (Source Closed)")]
        public static void BuildAndValidate()
        {
            ValidateRecoveredLodFadePacking();
            Dictionary<string, object> contract = LoadContract();
            Context context = BuildDependencies(contract);
            BuildPrefabs(contract, context);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateGenerated(contract, context, true);
        }

        public static void ValidateBatch()
        {
            ValidateRecoveredLodFadePacking();
            Dictionary<string, object> contract = LoadContract();
            Context context = LoadGeneratedDependencies(contract);
            ValidateGenerated(contract, context, true);
        }

        private static void ValidateRecoveredLodFadePacking()
        {
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.Disabled,
                    new Vector4(1000.0f, 0.0f, 0.0f, 0.0f)),
                "Recovered LOD-fade disabled sentinel no longer matches retail");
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.EncodeCustomAlpha(1.0f),
                    new Vector4(0.99899292f, 0.93751431f, 0.0f, 0.0f)),
                "Recovered positive maximum LOD-fade packing no longer matches retail");
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.EncodeCustomAlpha(0.5f),
                    new Vector4(0.49898526f, 0.43750668f, 0.0f, 0.0f)),
                "Recovered lower-half LOD-fade clamp no longer matches retail");
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.EncodeCustomAlpha(0.501f),
                    new Vector4(0.50099945f, 0.50000763f, 0.0f, 0.0f)),
                "Recovered upper-half LOD-fade clamp no longer matches retail");
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.EncodeCustomAlpha(-0.25f),
                    new Vector4(-0.24998856f, -0.18750286f, 0.0f, 0.0f)),
                "Recovered negative LOD-fade packing no longer matches retail");
            Require(
                Nearly(
                    EndfieldRecoveredLodFadePacking.EncodeCustomAlpha(0.0f),
                    new Vector4(-0.00099183642f, 0.0f, 0.0f, 0.0f)),
                "Recovered zero LOD-fade packing no longer matches retail");
        }

        private static Dictionary<string, object> LoadContract()
        {
            string absolute = AssetPathToAbsolute(ContractAssetPath);
            if (!File.Exists(absolute))
                throw new FileNotFoundException("Missing maintained particle inventory", absolute);
            var contract = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(absolute, Encoding.UTF8)));
            Require(Str(contract, "schema") == ExpectedSchema, "Unexpected particle contract schema");
            Require(Str(contract, "status") == "source_closed_inventory_not_runtime_instantiated",
                "Particle contract has an unexpected source status");
            Require(Str(contract, "execution") == "data_only_no_approximate_particle_or_material_runtime",
                "Particle contract execution boundary changed without importer review");

            Dictionary<string, object> summary = Dict(contract["summary"]);
            Require(Int(summary, "particleBearingRootCount") == 6, "Expected six particle-bearing roots");
            Require(Int(summary, "particleSystemCount") == 70, "Expected 70 particle systems");
            Require(Int(summary, "particleRendererCount") == 70, "Expected 70 particle renderers");
            Require(Int(summary, "oneToOnePairCount") == 70, "Particle/renderer pairing is not one-to-one");
            Require(Int(summary, "unresolvedDependencyCount") == 0, "Particle dependencies are unresolved");
            return contract;
        }

        private static Context BuildDependencies(Dictionary<string, object> contract)
        {
            var context = new Context();
            EnsureFolder(GeneratedRoot);
            EnsureFolder(PrefabRoot);
            EnsureFolder(MaterialRoot);
            EnsureFolder(MeshRoot);
            EnsureFolder(TextureRoot);
            EnsureFolder(SourceRoot);
            EnsureFolder(SourceRoot + "/Materials");
            EnsureFolder(SourceRoot + "/Meshes");

            ValidateAllSourceArtifacts(contract, context);
            context.nativeTextureRecords = LoadNativeTextureRecords();
            Dictionary<string, object> dependencies = Dict(contract["dependencies"]);
            Dictionary<string, object> records = Dict(dependencies["records"]);
            Require(List(records["Material"]).Count == 60, "Expected 60 selected materials");
            Require(List(records["Mesh"]).Count == 14, "Expected 14 selected meshes");
            Require(List(records["Texture2D"]).Count == 75, "Expected 75 selected textures");
            Require(List(records["Shader"]).Count == 3, "Expected three selected shaders");

            foreach (object item in List(records["Shader"]))
            {
                Dictionary<string, object> record = Dict(item);
                long pathId = Long(record, "pathID");
                context.shaderNames[pathId] = Str(record, "name");
            }

            foreach (object item in List(records["Texture2D"]))
            {
                Dictionary<string, object> record = Dict(item);
                long pathId = Long(record, "pathID");
                string name = Str(record, "name");
                Dictionary<string, object> png = FindArtifact(record, ".png");
                Dictionary<string, object> jsonArtifact = FindArtifact(record, ".json");
                Dictionary<string, object> textureJson = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(
                        RepoRelativeToAbsolute(Str(jsonArtifact, "path")),
                        Encoding.UTF8)));
                Texture2D texture;
                if (context.nativeTextureRecords.TryGetValue(
                    pathId, out Dictionary<string, object> nativeRecord))
                {
                    string assetPath =
                        TextureRoot + "/" + AssetBaseName(name, pathId) + ".asset";
                    texture = BuildNativeTexture(
                        assetPath, textureJson, nativeRecord, pathId, name);
                }
                else
                {
                    string staleNativePath =
                        TextureRoot + "/" + AssetBaseName(name, pathId) + ".asset";
                    if (AssetDatabase.LoadMainAssetAtPath(staleNativePath) != null)
                        Require(AssetDatabase.DeleteAsset(staleNativePath),
                            "Could not remove stale native Texture2D " + staleNativePath);
                    string source = RepoRelativeToAbsolute(Str(png, "path"));
                    string assetPath =
                        TextureRoot + "/" + AssetBaseName(name, pathId) + ".png";
                    if (CopyIfDifferent(source, AssetPathToAbsolute(assetPath)))
                        AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
                    ApplyOriginalTextureSettings(assetPath, textureJson, name);
                    texture = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
                    Require(texture != null, "Unity did not import texture " + assetPath);
                    ValidateOriginalTextureSettings(assetPath, textureJson, texture, name);
                }
                Require(texture != null, "Unity did not build texture " + name);
                context.textures[pathId] = texture;
            }

            foreach (object item in List(records["Mesh"]))
            {
                Dictionary<string, object> record = Dict(item);
                long pathId = Long(record, "pathID");
                string name = Str(record, "name");
                Dictionary<string, object> jsonArtifact = FindArtifact(record, ".json");
                string source = RepoRelativeToAbsolute(Str(jsonArtifact, "path"));
                string sourceAsset = SourceRoot + "/Meshes/" + AssetBaseName(name, pathId) + ".source.json";
                if (CopyIfDifferent(source, AssetPathToAbsolute(sourceAsset)))
                    AssetDatabase.ImportAsset(sourceAsset, ImportAssetOptions.ForceSynchronousImport);
                string meshAsset = MeshRoot + "/" + AssetBaseName(name, pathId) + ".asset";
                context.meshes[pathId] = BuildMesh(source, meshAsset, name);
            }

            Shader failClosed = Shader.Find(FailClosedShaderName);
            Require(failClosed != null, "Missing fail-closed VFX shader " + FailClosedShaderName);
            var recoveredShaders = SelectedMaterials.Values
                .Select(identity => identity.recoveredShaderName)
                .Distinct(StringComparer.Ordinal)
                .ToDictionary(name => name, name => Shader.Find(name), StringComparer.Ordinal);
            foreach (KeyValuePair<string, Shader> recovered in recoveredShaders)
            {
                Require(recovered.Value != null, "Missing selected VFX shader " + recovered.Key);
                Require(ShaderTag(recovered.Value, "EndfieldSceneMVMRT") ==
                    "ExactSelectedFiftyThree", "Selected VFX shader is missing the MRT identity tag " + recovered.Key);
                foreach (string property in RequiredRecoveredProperties[recovered.Key])
                    Require(ShaderDeclaresProperty(recovered.Value, property),
                        $"Selected VFX shader {recovered.Key} omits required source property {property}");
            }
            foreach (object item in List(records["Material"]))
            {
                Dictionary<string, object> record = Dict(item);
                long pathId = Long(record, "pathID");
                string name = Str(record, "name");
                Dictionary<string, object> jsonArtifact = FindArtifact(record, ".json");
                string source = RepoRelativeToAbsolute(Str(jsonArtifact, "path"));
                string sourceAsset = SourceRoot + "/Materials/" + AssetBaseName(name, pathId) + ".source.json";
                if (CopyIfDifferent(source, AssetPathToAbsolute(sourceAsset)))
                    AssetDatabase.ImportAsset(sourceAsset, ImportAssetOptions.ForceSynchronousImport);
                Dictionary<string, object> materialJson = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(source, Encoding.UTF8)));
                long shaderPathId = Long(Dict(materialJson["m_Shader"]), "m_PathID");
                Require(context.shaderNames.ContainsKey(shaderPathId),
                    $"Material {name} references unselected shader {shaderPathId}");
                string materialAsset = MaterialRoot + "/" + AssetBaseName(name, pathId) + ".mat";
                SelectedMaterialIdentity selectedIdentity = MatchSelectedIdentity(
                    pathId, materialJson);
                Shader targetShader = selectedIdentity == null
                    ? failClosed
                    : recoveredShaders[selectedIdentity.recoveredShaderName];
                Material material = AssetDatabase.LoadAssetAtPath<Material>(materialAsset);
                if (material == null)
                {
                    material = new Material(targetShader);
                    AssetDatabase.CreateAsset(material, materialAsset);
                }
                material.shaderKeywords = Array.Empty<string>();
                material.shader = targetShader;
                material.name = name;
                if (selectedIdentity != null)
                    ApplyRecoveredMaterialPayload(material, materialJson, context);
                material.renderQueue = Int(materialJson, "m_CustomRenderQueue", 3000);
                material.enableInstancing = Bool(materialJson, "m_EnableInstancingVariants");
                EditorUtility.SetDirty(material);
                context.materials[pathId] = material;
                context.materialNames[pathId] = name;
                context.materialShaderPathIds[pathId] = shaderPathId;
                context.materialSources[pathId] = materialJson;
            }
            context.line006ScopedMaterial =
                BuildLine006ScopedMaterial(context, recoveredShaders);
            context.dian901ScopedMaterial =
                BuildDian901ScopedMaterial(context, recoveredShaders);
            context.dian902ScopedMaterial =
                BuildDian902ScopedMaterial(context, recoveredShaders);
            context.lightning902ScopedMaterial =
                BuildLightning902ScopedMaterial(
                    context,
                    recoveredShaders);
            context.dian904DormantCandidateMaterial =
                BuildDian904DormantCandidateMaterial(
                    context,
                    recoveredShaders);
            return context;
        }

        private static Context LoadGeneratedDependencies(Dictionary<string, object> contract)
        {
            var context = new Context();
            ValidateAllSourceArtifacts(contract, context);
            context.nativeTextureRecords = LoadNativeTextureRecords();
            Dictionary<string, object> records = Dict(Dict(contract["dependencies"])["records"]);
            foreach (object item in List(records["Shader"]))
            {
                Dictionary<string, object> record = Dict(item);
                context.shaderNames[Long(record, "pathID")] = Str(record, "name");
            }
            foreach (object item in List(records["Texture2D"]))
            {
                Dictionary<string, object> record = Dict(item);
                long id = Long(record, "pathID");
                bool isNative = context.nativeTextureRecords.TryGetValue(
                    id, out Dictionary<string, object> nativeRecord);
                string path = TextureRoot + "/" + AssetBaseName(Str(record, "name"), id) +
                    (isNative ? ".asset" : ".png");
                Dictionary<string, object> sourceArtifact = FindArtifact(record, ".json");
                Dictionary<string, object> sourceJson = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(
                        RepoRelativeToAbsolute(Str(sourceArtifact, "path")),
                        Encoding.UTF8)));
                Texture2D texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                Require(texture != null, "Generated texture is missing " + path);
                if (isNative)
                    ValidateNativeTexture(texture, sourceJson, nativeRecord, id, Str(record, "name"));
                else
                    ValidateOriginalTextureSettings(
                        path, sourceJson, texture, Str(record, "name"));
                context.textures[id] = texture;
            }
            foreach (object item in List(records["Mesh"]))
            {
                Dictionary<string, object> record = Dict(item);
                long id = Long(record, "pathID");
                string path = MeshRoot + "/" + AssetBaseName(Str(record, "name"), id) + ".asset";
                context.meshes[id] = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            }
            foreach (object item in List(records["Material"]))
            {
                Dictionary<string, object> record = Dict(item);
                long id = Long(record, "pathID");
                string name = Str(record, "name");
                string path = MaterialRoot + "/" + AssetBaseName(name, id) + ".mat";
                context.materials[id] = AssetDatabase.LoadAssetAtPath<Material>(path);
                context.materialNames[id] = name;
                Dictionary<string, object> sourceArtifact = FindArtifact(record, ".json");
                Dictionary<string, object> sourceJson = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(RepoRelativeToAbsolute(Str(sourceArtifact, "path")), Encoding.UTF8)));
                context.materialShaderPathIds[id] = Long(Dict(sourceJson["m_Shader"]), "m_PathID");
                context.materialSources[id] = sourceJson;
            }
            context.line006ScopedMaterial =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Line006ScopedMaterialAssetPath);
            context.dian901ScopedMaterial =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian901ScopedMaterialAssetPath);
            context.dian902ScopedMaterial =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian902ScopedMaterialAssetPath);
            context.lightning902ScopedMaterial =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Lightning902ScopedMaterialAssetPath);
            context.dian904DormantCandidateMaterial =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian904DormantCandidateMaterialAssetPath);
            return context;
        }

        private static Material BuildLine006ScopedMaterial(
            Context context,
            Dictionary<string, Shader> recoveredShaders)
        {
            Require(
                context.materialSources.TryGetValue(
                    DeferredLine006Lightning901MaterialPathId,
                    out Dictionary<string, object> source),
                "Missing Line006 Lightning901 source Material JSON");
            Shader shader = recoveredShaders[RecoveredBaseV2ShaderName];
            Material material =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Line006ScopedMaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(
                    material,
                    Line006ScopedMaterialAssetPath);
            }
            material.shaderKeywords = Array.Empty<string>();
            material.shader = shader;
            material.name =
                "M_fx_ui_lightning_901_line006_renderer_scoped";
            ApplyRecoveredMaterialPayload(material, source, context);
            material.shaderKeywords = material.shaderKeywords
                .Concat(new[] { Line006ReplayKeyword })
                .ToArray();
            material.renderQueue = Int(source, "m_CustomRenderQueue", 3000);
            material.enableInstancing = false;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildDian902ScopedMaterial(
            Context context,
            Dictionary<string, Shader> recoveredShaders)
        {
            Require(
                context.materialSources.TryGetValue(
                    DeferredDian902MaterialPathId,
                    out Dictionary<string, object> source),
                "Missing Dian902 source Material JSON");
            Shader shader = recoveredShaders[RecoveredBaseV2ShaderName];
            Material material =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian902ScopedMaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(
                    material,
                    Dian902ScopedMaterialAssetPath);
            }
            material.shaderKeywords = Array.Empty<string>();
            material.shader = shader;
            material.name =
                "M_fx_ui_dian_902_manual_renderer_scoped";
            ApplyRecoveredMaterialPayload(material, source, context);
            material.shaderKeywords = material.shaderKeywords
                .Concat(new[]
                {
                    Dian902ManualReplayKeyword,
                    Dian902DynamicReplayKeyword,
                })
                .ToArray();
            material.SetFloat("_Dian902ManualReplayIndex", -1.0f);
            material.SetFloat("_Dian902ManualSourceTime", -1.0f);
            material.SetFloat("_Dian902ManualAgePercent", -1.0f);
            material.SetFloat("_Dian902ManualRemainingLifetime", -1.0f);
            material.renderQueue = Int(source, "m_CustomRenderQueue", 3000);
            material.enableInstancing = false;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildDian901ScopedMaterial(
            Context context,
            Dictionary<string, Shader> recoveredShaders)
        {
            Require(
                context.materialSources.TryGetValue(
                    DeferredDian901MaterialPathId,
                    out Dictionary<string, object> source),
                "Missing Dian901 source Material JSON");
            Shader shader = recoveredShaders[RecoveredBaseV2ShaderName];
            Material material =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian901ScopedMaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(
                    material,
                    Dian901ScopedMaterialAssetPath);
            }
            material.shaderKeywords = Array.Empty<string>();
            material.shader = shader;
            material.name =
                "M_fx_ui_dian_901_fixed_manual_renderer_scoped";
            ApplyRecoveredMaterialPayload(material, source, context);
            material.shaderKeywords = material.shaderKeywords
                .Concat(new[]
                {
                    Dian901FixedManualReplayKeyword,
                    Dian901DynamicReplayKeyword,
                })
                .ToArray();
            material.SetFloat("_Dian901ManualReplayValid", 0.0f);
            material.SetFloat("_Dian901ManualReplayMagic", 0.0f);
            material.SetFloat("_Dian901ManualReplaySample", -1.0f);
            material.SetFloat("_Dian901ManualSourceTime", -1.0f);
            material.SetFloat("_Dian901ManualLiveCount", -1.0f);
            material.SetFloat("_Dian901ManualReplayEpoch", -1.0f);
            material.SetFloat("_Dian901ManualPublishFrame", -1.0f);
            material.SetFloat(
                "_Dian901ManualRendererFingerprint",
                0.0f);
            material.SetFloat("_Dian901ManualReplayChecksum", 0.0f);
            material.SetFloat(
                "_Dian901AutomaticSchedulerChecksum",
                0.0f);
            material.SetFloat("_Dian901AutomaticRowChecksum", 0.0f);
            material.renderQueue =
                Int(source, "m_CustomRenderQueue", 3000);
            material.enableInstancing = false;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildLightning902ScopedMaterial(
            Context context,
            Dictionary<string, Shader> recoveredShaders)
        {
            Require(
                context.materialSources.TryGetValue(
                    DeferredLightning902MaterialPathId,
                    out Dictionary<string, object> source),
                "Missing Lightning902 source Material JSON");
            Shader shader = recoveredShaders[RecoveredBaseV2ShaderName];
            Material material =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Lightning902ScopedMaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(
                    material,
                    Lightning902ScopedMaterialAssetPath);
            }
            material.shaderKeywords = Array.Empty<string>();
            material.shader = shader;
            material.name =
                "M_fx_ui_lightning_902_renderer_scoped";
            ApplyRecoveredMaterialPayload(material, source, context);
            material.shaderKeywords = material.shaderKeywords
                .Concat(new[] { Lightning902ReplayKeyword })
                .ToArray();
            material.SetFloat(
                "_Lightning902RetailCustom1X",
                -1.0f);
            material.SetFloat(
                "_Lightning902RetailReplayValid",
                0.0f);
            material.SetFloat(
                "_Lightning902RetailReplayMagic",
                0.0f);
            material.SetFloat(
                "_Lightning902RetailReplayEpoch",
                -1.0f);
            material.SetFloat(
                "_Lightning902RetailPublishFrame",
                -1.0f);
            material.SetFloat(
                "_Lightning902RetailRendererFingerprint",
                0.0f);
            material.SetFloat(
                "_Lightning902RetailReplayChecksum",
                0.0f);
            material.renderQueue =
                Int(source, "m_CustomRenderQueue", 3000);
            material.enableInstancing = false;
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Material BuildDian904DormantCandidateMaterial(
            Context context,
            Dictionary<string, Shader> recoveredShaders)
        {
            Require(
                context.materialSources.TryGetValue(
                    DeferredDian904MaterialPathId,
                    out Dictionary<string, object> source),
                "Missing Dian904 source Material JSON");
            Shader shader = recoveredShaders[RecoveredBaseV2ShaderName];
            Material material =
                AssetDatabase.LoadAssetAtPath<Material>(
                    Dian904DormantCandidateMaterialAssetPath);
            if (material == null)
            {
                material = new Material(shader);
                AssetDatabase.CreateAsset(
                    material,
                    Dian904DormantCandidateMaterialAssetPath);
            }
            material.shaderKeywords = Array.Empty<string>();
            material.shader = shader;
            material.name = "M_fx_ui_dian_904_dormant_candidate";
            ApplyRecoveredMaterialPayload(material, source, context);
            Dictionary<string, object> saved =
                Dict(source["m_SavedProperties"]);
            Dictionary<string, object> colors =
                Dict(saved["m_Colors"]);
            Require(
                colors.TryGetValue("_TintColor", out object rawTintValue),
                "Dian904 source Material JSON lost _TintColor");
            Color rawTint = ColorValue(rawTintValue);
            material.SetVector(
                "_Dian904RawTintColor",
                new Vector4(rawTint.r, rawTint.g, rawTint.b, rawTint.a));
            material.shaderKeywords = material.shaderKeywords
                .Concat(new[] { Dian904DormantCandidateKeyword })
                .ToArray();
            material.renderQueue =
                Int(source, "m_CustomRenderQueue", 3000);
            material.enableInstancing =
                Bool(source, "m_EnableInstancingVariants");
            EditorUtility.SetDirty(material);
            return material;
        }

        private static Dictionary<long, Dictionary<string, object>> LoadNativeTextureRecords()
        {
            var records = new Dictionary<long, Dictionary<string, object>>();
            foreach (string contractAssetPath in NativeTextureContractAssetPaths)
            {
                string contractAbsolute = AssetPathToAbsolute(contractAssetPath);
                Require(File.Exists(contractAbsolute),
                    "Missing native Texture2D payload contract " + contractAssetPath);
                Dictionary<string, object> contract = Dict(ManifestMiniJson.Deserialize(
                    File.ReadAllText(contractAbsolute, Encoding.UTF8)));
                Require(Str(contract, "schema") == "endfield.zhuangfy-native-texture-payloads.v1",
                    "Unexpected native Texture2D payload contract schema");
                Require(Str(contract, "status") == "source_closed_exact_native_payload",
                    "Native Texture2D payload contract is not source-closed");
                Dictionary<string, object> audit = Dict(contract["audit"]);
                ValidateProjectArtifact(
                    Str(audit, "path"), Long(audit, "bytes"), Str(audit, "sha256"));

                foreach (object item in List(contract["records"]))
                {
                    Dictionary<string, object> record = Dict(item);
                    long pathId = Long(record, "pathID");
                    Dictionary<string, object> payload = Dict(record["payload"]);
                    Dictionary<string, object> manifest = Dict(record["manifest"]);
                    ValidateProjectArtifact(
                        Str(payload, "path"), Long(payload, "bytes"), Str(payload, "sha256"));
                    ValidateProjectArtifact(
                        Str(manifest, "path"), Long(manifest, "bytes"), Str(manifest, "sha256"));
                    if (records.TryGetValue(pathId, out Dictionary<string, object> existing))
                    {
                        Dictionary<string, object> existingPayload = Dict(existing["payload"]);
                        Dictionary<string, object> existingManifest = Dict(existing["manifest"]);
                        Require(
                            Str(existing, "name") == Str(record, "name") &&
                            Long(existingPayload, "bytes") == Long(payload, "bytes") &&
                            Str(existingPayload, "sha256") == Str(payload, "sha256") &&
                            Long(existingManifest, "bytes") == Long(manifest, "bytes") &&
                            Str(existingManifest, "sha256") == Str(manifest, "sha256"),
                            "Conflicting duplicate native Texture2D PathID " + pathId);
                        continue;
                    }
                    records[pathId] = record;
                }
            }
            var expected = new HashSet<long>
            {
                1467247550183115646L,
                -246886565338033747L,
                -6317074837101742633L,
                -3232886272640329932L,
                -310221878972884249L,
                2875840231048892458L,
                4998288580770167135L,
                6970530313307194154L,
                -8313390964225652571L,
                -6490048928733971818L,
                1146797628694831720L,
                7049436479442186204L,
                8433073018323172048L,
                4232007063533868099L,
                -2906088910910405840L,
                5477294676579545171L,
                8877138048347760981L,
                -8793387699559065625L,
                -8268050023903468823L,
                -4094667934537615255L,
                -1647025128171678556L,
                1303879328479949420L,
                -7633386150224575418L,
                -2332480959189864971L,
                -1359170491180831178L,
                -1116178976393058562L,
                -6699450956231740061L,
                3985196969940829636L,
                -7922891545440764661L,
                253081788809034347L,
                2958546421766694459L,
            };
            Require(expected.SetEquals(records.Keys),
                "Native Texture2D payload identity set changed");
            return records;
        }

        private static Texture2D BuildNativeTexture(
            string assetPath,
            Dictionary<string, object> sourceJson,
            Dictionary<string, object> nativeRecord,
            long pathId,
            string textureName)
        {
            ValidateNativeTextureDescriptor(sourceJson, nativeRecord, pathId, textureName);
            Dictionary<string, object> descriptor = Dict(nativeRecord["descriptor"]);
            Dictionary<string, object> settings = Dict(descriptor["textureSettings"]);
            Dictionary<string, object> payloadArtifact = Dict(nativeRecord["payload"]);
            byte[] payload = File.ReadAllBytes(
                ProjectRelativeToAbsolute(Str(payloadArtifact, "path")));
            Require(payload.Length == Long(payloadArtifact, "bytes"),
                "Native Texture2D payload byte count changed for " + textureName);
            Require(Sha256(payload) == Str(payloadArtifact, "sha256").ToUpperInvariant(),
                "Native Texture2D payload SHA-256 changed for " + textureName);

            string stalePngPath =
                TextureRoot + "/" + AssetBaseName(textureName, pathId) + ".png";
            if (AssetDatabase.LoadMainAssetAtPath(stalePngPath) != null)
                Require(AssetDatabase.DeleteAsset(stalePngPath),
                    "Could not remove superseded PNG texture " + stalePngPath);
            if (AssetDatabase.LoadMainAssetAtPath(assetPath) != null)
                Require(AssetDatabase.DeleteAsset(assetPath),
                    "Could not replace native Texture2D asset " + assetPath);

            int width = Int(descriptor, "width");
            int height = Int(descriptor, "height");
            int mipCount = Int(descriptor, "mipCount");
            // Unity's serialized Texture2D m_ColorSpace uses 0=linear and
            // 1=sRGB, while this constructor parameter asks the inverse.
            bool linear = Int(descriptor, "colorSpace") == 0;
            var texture = new Texture2D(
                width, height, TextureFormat.BC7, mipCount, linear)
            {
                name = textureName,
                filterMode = (FilterMode)Int(settings, "filterMode"),
                anisoLevel = Int(settings, "aniso"),
                mipMapBias = Float(settings, "mipBias"),
                wrapModeU = (TextureWrapMode)Int(settings, "wrapU"),
                wrapModeV = (TextureWrapMode)Int(settings, "wrapV"),
                wrapModeW = (TextureWrapMode)Int(settings, "wrapW"),
            };
            texture.LoadRawTextureData(payload);
            texture.Apply(false, false);
            AssetDatabase.CreateAsset(texture, assetPath);
            EditorUtility.SetDirty(texture);
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);
            Texture2D loaded = AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
            Require(loaded != null, "Unity did not create native Texture2D " + assetPath);
            ValidateNativeTexture(loaded, sourceJson, nativeRecord, pathId, textureName);
            return loaded;
        }

        private static void ValidateNativeTextureDescriptor(
            Dictionary<string, object> sourceJson,
            Dictionary<string, object> nativeRecord,
            long pathId,
            string textureName)
        {
            Require(Long(nativeRecord, "pathID") == pathId &&
                Str(nativeRecord, "name") == textureName,
                "Native Texture2D identity mismatch for " + textureName);
            Dictionary<string, object> descriptor = Dict(nativeRecord["descriptor"]);
            Require(Str(descriptor, "format") == "BC7" &&
                Int(descriptor, "formatValue") == 25 &&
                Int(descriptor, "mipsStripped") == 0 &&
                Int(descriptor, "imageCount") == 1 &&
                Int(descriptor, "textureDimension") == 2 &&
                Int(descriptor, "colorSpace") == 1,
                "Unsupported native Texture2D descriptor for " + textureName);
            Require(
                Int(descriptor, "width") == Int(sourceJson, "m_Width") &&
                Int(descriptor, "height") == Int(sourceJson, "m_Height") &&
                Int(descriptor, "completeImageSize") ==
                    Int(sourceJson, "m_CompleteImageSize") &&
                Int(descriptor, "mipCount") == Int(sourceJson, "m_MipCount") &&
                Str(sourceJson, "m_TextureFormat") == "BC7",
                "Native Texture2D descriptor disagrees with independent source JSON for " +
                textureName);
            Dictionary<string, object> sourceSettings =
                Dict(sourceJson["m_TextureSettings"]);
            Dictionary<string, object> nativeSettings =
                Dict(descriptor["textureSettings"]);
            Require(
                Int(nativeSettings, "filterMode") == Int(sourceSettings, "m_FilterMode") &&
                Int(nativeSettings, "aniso") == Int(sourceSettings, "m_Aniso") &&
                Nearly(Float(nativeSettings, "mipBias"), Float(sourceSettings, "m_MipBias")) &&
                Int(nativeSettings, "wrapU") == Int(sourceSettings, "m_WrapMode"),
                "Native Texture2D settings disagree with independent source JSON for " +
                textureName);
            int expectedOffset = 0;
            int expectedMip = 0;
            foreach (object item in List(nativeRecord["mipDimensions"]))
            {
                Dictionary<string, object> mip = Dict(item);
                int width = Mathf.Max(1, Int(descriptor, "width") >> expectedMip);
                int height = Mathf.Max(1, Int(descriptor, "height") >> expectedMip);
                int byteSize = Mathf.Max(1, (width + 3) / 4) *
                    Mathf.Max(1, (height + 3) / 4) * 16;
                Require(
                    Int(mip, "mip") == expectedMip &&
                    Int(mip, "width") == width &&
                    Int(mip, "height") == height &&
                    Int(mip, "offset") == expectedOffset &&
                    Int(mip, "byteSize") == byteSize,
                    "Native BC7 mip layout changed for " + textureName);
                expectedOffset += byteSize;
                expectedMip++;
            }
            Require(expectedMip == Int(descriptor, "mipCount") &&
                expectedOffset == Int(descriptor, "completeImageSize"),
                "Native BC7 mip chain does not consume the full payload for " + textureName);
        }

        private static void ValidateNativeTexture(
            Texture2D texture,
            Dictionary<string, object> sourceJson,
            Dictionary<string, object> nativeRecord,
            long pathId,
            string textureName)
        {
            ValidateNativeTextureDescriptor(sourceJson, nativeRecord, pathId, textureName);
            Dictionary<string, object> descriptor = Dict(nativeRecord["descriptor"]);
            Dictionary<string, object> settings = Dict(descriptor["textureSettings"]);
            Require(texture.width == Int(descriptor, "width") &&
                texture.height == Int(descriptor, "height") &&
                texture.mipmapCount == Int(descriptor, "mipCount") &&
                texture.format == TextureFormat.BC7,
                "Generated native Texture2D layout mismatch for " + textureName);
            Require(texture.filterMode == (FilterMode)Int(settings, "filterMode") &&
                texture.anisoLevel == Int(settings, "aniso") &&
                Nearly(texture.mipMapBias, Float(settings, "mipBias")) &&
                texture.wrapModeU == (TextureWrapMode)Int(settings, "wrapU") &&
                texture.wrapModeV == (TextureWrapMode)Int(settings, "wrapV") &&
                texture.wrapModeW == (TextureWrapMode)Int(settings, "wrapW"),
                "Generated native Texture2D settings mismatch for " + textureName);
            SerializedProperty colorSpace =
                new SerializedObject(texture).FindProperty("m_ColorSpace");
            Require(colorSpace != null && colorSpace.intValue == Int(descriptor, "colorSpace"),
                "Generated native Texture2D color space mismatch for " + textureName);
            byte[] actual = texture.GetRawTextureData();
            Dictionary<string, object> payloadArtifact = Dict(nativeRecord["payload"]);
            Require(actual.Length == Long(payloadArtifact, "bytes") &&
                Sha256(actual) == Str(payloadArtifact, "sha256").ToUpperInvariant(),
                "Generated native Texture2D bytes differ from original BC7 payload for " +
                textureName);
        }

        private static void ApplyOriginalTextureSettings(
            string assetPath,
            Dictionary<string, object> textureJson,
            string textureName)
        {
            Dictionary<string, object> settings = Dict(textureJson["m_TextureSettings"]);
            int filterMode = Int(settings, "m_FilterMode");
            int wrapMode = Int(settings, "m_WrapMode");
            int anisoLevel = Int(settings, "m_Aniso");
            float mipMapBias = Float(settings, "m_MipBias");
            Require(filterMode >= (int)FilterMode.Point &&
                filterMode <= (int)FilterMode.Trilinear,
                "Unsupported original filter mode for " + textureName);
            Require(wrapMode >= (int)TextureWrapMode.Repeat &&
                wrapMode <= (int)TextureWrapMode.MirrorOnce,
                "Unsupported original wrap mode for " + textureName);
            Require(anisoLevel >= 0 && anisoLevel <= 16,
                "Unsupported original anisotropy for " + textureName);

            TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            Require(importer != null, "TextureImporter is missing for " + assetPath);
            bool changed =
                importer.filterMode != (FilterMode)filterMode ||
                importer.wrapModeU != (TextureWrapMode)wrapMode ||
                importer.wrapModeV != (TextureWrapMode)wrapMode ||
                importer.wrapModeW != (TextureWrapMode)wrapMode ||
                importer.anisoLevel != anisoLevel ||
                !Nearly(importer.mipMapBias, mipMapBias);
            if (!changed)
                return;

            importer.filterMode = (FilterMode)filterMode;
            importer.wrapModeU = (TextureWrapMode)wrapMode;
            importer.wrapModeV = (TextureWrapMode)wrapMode;
            importer.wrapModeW = (TextureWrapMode)wrapMode;
            importer.anisoLevel = anisoLevel;
            importer.mipMapBias = mipMapBias;
            importer.SaveAndReimport();
        }

        private static void ValidateOriginalTextureSettings(
            string assetPath,
            Dictionary<string, object> textureJson,
            Texture2D texture,
            string textureName)
        {
            Dictionary<string, object> settings = Dict(textureJson["m_TextureSettings"]);
            FilterMode filterMode = (FilterMode)Int(settings, "m_FilterMode");
            TextureWrapMode wrapMode = (TextureWrapMode)Int(settings, "m_WrapMode");
            int anisoLevel = Int(settings, "m_Aniso");
            float mipMapBias = Float(settings, "m_MipBias");
            TextureImporter importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            Require(importer != null, "TextureImporter is missing for " + assetPath);
            Require(
                importer.filterMode == filterMode &&
                importer.wrapModeU == wrapMode &&
                importer.wrapModeV == wrapMode &&
                importer.wrapModeW == wrapMode &&
                importer.anisoLevel == anisoLevel &&
                Nearly(importer.mipMapBias, mipMapBias),
                "Generated TextureImporter settings do not match original " + textureName);
            Require(
                texture.filterMode == filterMode &&
                texture.wrapModeU == wrapMode &&
                texture.wrapModeV == wrapMode &&
                texture.wrapModeW == wrapMode &&
                texture.anisoLevel == anisoLevel &&
                Nearly(texture.mipMapBias, mipMapBias),
                "Generated Texture2D settings do not match original " + textureName);
        }

        private static void BuildPrefabs(Dictionary<string, object> contract, Context context)
        {
            foreach (object rootObject in List(contract["roots"]))
            {
                Dictionary<string, object> root = Dict(rootObject);
                if (Str(root, "inventoryKind") != "particle_effect")
                    continue;
                string effectRoot = Str(root, "effectRoot");
                IList hierarchyNodes = List(root["hierarchyNodes"]);
                IList particlePairs = List(root["particlePairs"]);
                Require(particlePairs.Count > 0, effectRoot + " has no particle pairs");

                var nodesByTransformId = new Dictionary<long, GameObject>();
                var nodeRecordsByTransformId = new Dictionary<long, Dictionary<string, object>>();
                Dictionary<string, object> rootNode = null;
                foreach (object nodeObject in hierarchyNodes)
                {
                    Dictionary<string, object> node = Dict(nodeObject);
                    string hierarchy = Str(node, "hierarchy");
                    if (hierarchy == Str(Dict(root["effectSetting"]), "hierarchy"))
                        rootNode = node;
                    long transformId = Long(node, "transformPathID");
                    Require(!nodesByTransformId.ContainsKey(transformId), "Duplicate transform path ID " + transformId);
                    var go = new GameObject(Str(Dict(node["gameObject"]), "m_Name"));
                    nodesByTransformId[transformId] = go;
                    nodeRecordsByTransformId[transformId] = node;
                }
                Require(rootNode != null, "Missing effect root hierarchy node for " + effectRoot);

                long rootTransformId = Long(rootNode, "transformPathID");
                GameObject prefabRoot = nodesByTransformId[rootTransformId];
                foreach (KeyValuePair<long, GameObject> pair in nodesByTransformId)
                {
                    Dictionary<string, object> node = nodeRecordsByTransformId[pair.Key];
                    Dictionary<string, object> transform = Dict(node["transform"]);
                    long parentId = Long(Dict(transform["m_Father"]), "m_PathID");
                    if (pair.Key != rootTransformId)
                    {
                        Require(nodesByTransformId.TryGetValue(parentId, out GameObject parent),
                            $"{effectRoot} omits the internal parent {parentId} for {Str(node, "hierarchy")}");
                        pair.Value.transform.SetParent(parent.transform, false);
                    }
                    ApplyTransform(pair.Value.transform, transform);
                }

                // The strict hierarchy also contains source MeshRenderer /
                // MeshFilter pairs used by the original rarity AnimationClip.
                // Preserve their exact component/binding targets.  PPtrs which
                // are not in the strict particle dependency closure remain
                // null/empty (source-closed) rather than being substituted.
                foreach (KeyValuePair<long, GameObject> pair in nodesByTransformId)
                {
                    Dictionary<string, object> node = nodeRecordsByTransformId[pair.Key];
                    Dictionary<string, object> gameObject = Dict(node["gameObject"]);
                    Dictionary<string, object> meshRenderer = Dict(
                        gameObject.TryGetValue("m_MeshRenderer", out object meshRendererObject)
                            ? meshRendererObject
                            : null);
                    Dictionary<string, object> meshFilter = Dict(
                        gameObject.TryGetValue("m_MeshFilter", out object meshFilterObject)
                            ? meshFilterObject
                            : null);
                    if (meshRenderer.Count == 0 && meshFilter.Count == 0)
                        continue;
                    Require(meshRenderer.Count > 0 && meshFilter.Count > 0,
                        "Incomplete static renderer pair at " + Str(node, "hierarchy"));
                    long meshId = PPtrId(meshFilter["m_Mesh"]);
                    long[] materialIds = PPtrIds(meshRenderer["m_Materials"]);
                    MeshFilter generatedFilter = pair.Value.AddComponent<MeshFilter>();
                    MeshRenderer generatedRenderer = pair.Value.AddComponent<MeshRenderer>();
                    generatedFilter.sharedMesh = context.meshes.TryGetValue(meshId, out Mesh selectedMesh)
                        ? selectedMesh
                        : null;
                    generatedRenderer.sharedMaterials = materialIds.All(context.materials.ContainsKey)
                        ? materialIds.Select(id => context.materials[id]).ToArray()
                        : Array.Empty<Material>();
                }

                var pairSources = new List<EndfieldRecoveredParticleNodeSource>();
                ParticleSystem dian901FixedManualSystem = null;
                ParticleSystemRenderer dian901FixedManualRenderer = null;
                ParticleSystem dian902ManualSystem = null;
                ParticleSystemRenderer dian902ManualRenderer = null;
                foreach (object pairObject in particlePairs)
                {
                    Dictionary<string, object> particlePair = Dict(pairObject);
                    long gameObjectPathId = Long(particlePair, "gameObjectPathID");
                    Dictionary<string, object> node = hierarchyNodes.Cast<object>().Select(Dict).Single(
                        n => Long(n, "gameObjectPathID") == gameObjectPathId);
                    GameObject go = nodesByTransformId[Long(node, "transformPathID")];
                    ParticleSystem system = go.AddComponent<ParticleSystem>();
                    ParticleSystemRenderer renderer = go.GetComponent<ParticleSystemRenderer>();
                    Require(renderer != null, "Unity did not create a ParticleSystemRenderer on " + Str(particlePair, "hierarchy"));

                    Dictionary<string, object> systemRecord = Dict(particlePair["particleSystem"]);
                    Dictionary<string, object> rendererRecord = Dict(particlePair["renderer"]);
                    var systemSerialized = new SerializedObject(system);
                    DisableAllKnownModules(systemSerialized);
                    ApplyTopLevelDictionary(systemSerialized, Dict(systemRecord["fields"]), context, "ParticleSystem");
                    foreach (KeyValuePair<string, object> module in Dict(systemRecord["enabledModules"]))
                        ApplyNamedDictionary(systemSerialized, module.Key, Dict(module.Value), context, "ParticleSystem." + module.Key);
                    systemSerialized.ApplyModifiedPropertiesWithoutUndo();

                    var rendererSerialized = new SerializedObject(renderer);
                    ApplyTopLevelDictionary(rendererSerialized, Dict(rendererRecord["fields"]), context, "ParticleSystemRenderer");
                    rendererSerialized.ApplyModifiedPropertiesWithoutUndo();
                    long rendererPathId =
                        Long(Dict(rendererRecord["source"]), "pathID");
                    long[] materialIds = PPtrIds(
                        Dict(rendererRecord["fields"])["m_Materials"]);
                    if (IsLine006ScopedRenderer(rendererPathId))
                        ApplyLine006ScopedRenderer(renderer, context);
                    else if (IsDian901FixedManualScopedRenderer(
                        rendererPathId))
                    {
                        Require(
                            dian901FixedManualSystem == null &&
                            dian901FixedManualRenderer == null,
                            "Dian901 fixed/manual renderer identity is not " +
                            "unique within " + effectRoot);
                        ValidateDian901SourceTuple(
                            systemRecord,
                            rendererRecord,
                            materialIds,
                            context,
                            Str(particlePair, "hierarchy"));
                        ApplyDian901FixedManualScopedRenderer(
                            renderer,
                            context);
                        dian901FixedManualSystem = system;
                        dian901FixedManualRenderer = renderer;
                    }
                    else if (IsDian902ManualScopedRenderer(rendererPathId))
                    {
                        ApplyDian902ManualScopedRenderer(renderer, context);
                        Require(
                            dian902ManualSystem == null &&
                            dian902ManualRenderer == null,
                            "Dian902 manual renderer identity is not unique within " +
                            effectRoot);
                        dian902ManualSystem = system;
                        dian902ManualRenderer = renderer;
                    }
                    else if (IsLightning902ScopedRenderer(
                        rendererPathId))
                    {
                        Require(
                            materialIds.SequenceEqual(
                                new[]
                                {
                                    DeferredLightning902MaterialPathId,
                                }),
                            "Lightning902 exact renderer/source material " +
                            "pair drifted at " +
                            Str(particlePair, "hierarchy"));
                        ApplyLightning902ScopedRenderer(
                            renderer,
                            context);
                    }

                    long[] meshIds = new[]
                    {
                        PPtrId(Dict(rendererRecord["fields"])["m_Mesh"]),
                        PPtrId(Dict(rendererRecord["fields"])["m_Mesh1"]),
                        PPtrId(Dict(rendererRecord["fields"])["m_Mesh2"]),
                        PPtrId(Dict(rendererRecord["fields"])["m_Mesh3"]),
                    }.Where(id => id != 0).ToArray();
                    long[] shaderIds = materialIds.Select(id => context.materialShaderPathIds[id]).ToArray();
                    pairSources.Add(new EndfieldRecoveredParticleNodeSource
                    {
                        hierarchy = Str(particlePair, "hierarchy"),
                        gameObjectPathId = gameObjectPathId,
                        transformPathId = Long(node, "transformPathID"),
                        particleSystemPathId = Long(Dict(systemRecord["source"]), "pathID"),
                        particleRendererPathId = rendererPathId,
                        materialPathIds = materialIds,
                        meshPathIds = meshIds,
                        shaderNames = shaderIds.Select(id => context.shaderNames[id]).ToArray(),
                        shaderPathIds = shaderIds,
                        sourceRendererEnabled = Bool(Dict(rendererRecord["fields"]), "m_Enabled"),
                        nativeParticlePayloadApplied = true,
                        nativeRendererPayloadApplied = true,
                        rendererFailClosedForUnrecoveredShader =
                            renderer.sharedMaterials.Any(material =>
                                material != null &&
                                material.shader != null &&
                                material.shader.name == FailClosedShaderName),
                    });
                }

                if (dian901FixedManualRenderer != null)
                {
                    Require(
                        dian901FixedManualSystem != null,
                        "Dian901 fixed/manual playback is missing its " +
                        "ParticleSystem");
                    EndfieldRecoveredDian901FixedManualPlayback playback =
                        prefabRoot.AddComponent<
                            EndfieldRecoveredDian901FixedManualPlayback>();
                    Require(
                        context.meshes.TryGetValue(
                            Dian901MeshPathId,
                            out Mesh sourceMesh) &&
                        sourceMesh != null,
                        "Dian901 source mesh is unavailable");
                    playback.Configure(
                        dian901FixedManualSystem,
                        dian901FixedManualRenderer,
                        context.dian901ScopedMaterial,
                        sourceMesh);
                }

                if (dian902ManualRenderer != null)
                {
                    Require(
                        dian902ManualSystem != null,
                        "Dian902 manual playback is missing its ParticleSystem");
                    EndfieldRecoveredDian902ManualPlayback playback =
                        prefabRoot.AddComponent<
                            EndfieldRecoveredDian902ManualPlayback>();
                    var playbackSerialized =
                        new SerializedObject(playback);
                    SerializedProperty systemProperty =
                        playbackSerialized.FindProperty(
                            "targetParticleSystem");
                    SerializedProperty rendererProperty =
                        playbackSerialized.FindProperty(
                            "targetRenderer");
                    Require(
                        systemProperty != null &&
                        rendererProperty != null,
                        "Dian902 manual playback serialization contract drifted");
                    systemProperty.objectReferenceValue =
                        dian902ManualSystem;
                    rendererProperty.objectReferenceValue =
                        dian902ManualRenderer;
                    playbackSerialized.ApplyModifiedPropertiesWithoutUndo();
                }

                Dictionary<string, object> effectSetting = Dict(root["effectSetting"]);
                Dictionary<string, object> effectSummary = Dict(effectSetting["sourceClosedSummary"]);
                var marker = prefabRoot.AddComponent<EndfieldRecoveredParticleEffectSource>();
                marker.contractSchema = ExpectedSchema;
                marker.effectRoot = effectRoot;
                marker.sourceHierarchy = Str(effectSetting, "hierarchy");
                marker.sourceGameObjectPathId = Long(rootNode, "gameObjectPathID");
                marker.sourceTransformPathId = rootTransformId;
                marker.sourceEffectLoops = Bool(effectSummary, "is_loop");
                marker.sourceEffectDuration = Float(effectSummary, "duration");
                marker.sourceEffectDelay = Float(effectSummary, "delay");
                marker.sourceEffectRandomDelay = Float(effectSummary, "random_delay");
                marker.materialExecutionBoundary =
                    "fifty-two exact material identity tuples use source-selected MRT shader variants behind render/global readiness gates; " +
                    "three exact Lightning901 renderer PathIDs use one renderer-scoped clone with strict Custom1 replay; " +
                    "Dian901 renderer PathID -2376706058147287785 uses one guarded renderer-scoped clone for five exact fixed/manual source-time samples and the source-closed automatic variable-step scheduler; " +
                    "Dian902 renderer PathID -7137180953804559081 uses one guarded renderer-scoped clone for nine exact fixed/manual states and the " +
                    "Lightning902 renderer PathID 296863772203003159 uses one runtime-only renderer-scoped clone with an epoch/frame/checksum draw token; " +
                    "source-closed automatic variable-step scheduler; the shared Lightning901 source material, the separate deferred Lightning901 identity, " +
                    "the Dian901, Dian902, and Lightning902 source materials, and three other retail variants use ColorMask 0";
                marker.hierarchyNodes = nodeRecordsByTransformId
                    .OrderBy(pair => Str(pair.Value, "hierarchy"), StringComparer.Ordinal)
                    .ThenBy(pair => pair.Key)
                    .Select(pair => new EndfieldRecoveredParticleHierarchyNodeSource
                    {
                        hierarchy = Str(pair.Value, "hierarchy"),
                        gameObjectPathId = Long(pair.Value, "gameObjectPathID"),
                        transformPathId = pair.Key,
                        generatedTransform = nodesByTransformId[pair.Key].transform,
                    }).ToArray();
                marker.particleNodes = pairSources.ToArray();

                string prefabPath = PrefabRoot + "/" + Safe(effectRoot) + ".prefab";
                PrefabUtility.SaveAsPrefabAsset(prefabRoot, prefabPath);
                UnityEngine.Object.DestroyImmediate(prefabRoot);
            }
        }

        private static bool IsLine006ScopedRenderer(long rendererPathId)
        {
            return rendererPathId == Line006RendererPathIdA ||
                rendererPathId == Line006RendererPathIdB ||
                rendererPathId == Lightning901ThirdRendererPathId;
        }

        private static bool IsDian902ManualScopedRenderer(long rendererPathId)
        {
            return rendererPathId == Dian902ManualRendererPathId;
        }

        private static bool IsDian901FixedManualScopedRenderer(
            long rendererPathId)
        {
            return rendererPathId == Dian901FixedManualRendererPathId;
        }

        private static bool IsLightning902ScopedRenderer(
            long rendererPathId)
        {
            return rendererPathId == Lightning902RendererPathId;
        }

        private static void ApplyLine006ScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context)
        {
            Require(
                context.line006ScopedMaterial != null &&
                context.line006ScopedMaterial.shader != null &&
                context.line006ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName,
                "Line006 renderer-scoped material is unavailable");
            renderer.sharedMaterials =
                new[] { context.line006ScopedMaterial };
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expectedSource = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expectedSource),
                "Line006 source vertex-stream signature changed");
            streams.Add(ParticleSystemVertexStream.AgePercent);
            streams.Add(ParticleSystemVertexStream.InvStartLifetime);
            renderer.SetActiveVertexStreams(streams);
            renderer.enableGPUInstancing = false;
        }

        private static void ApplyDian902ManualScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context)
        {
            Require(
                context.dian902ScopedMaterial != null &&
                context.dian902ScopedMaterial.shader != null &&
                context.dian902ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName,
                "Dian902 renderer-scoped material is unavailable");
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expectedSource = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expectedSource),
                "Dian902 source vertex-stream signature changed");
            renderer.sharedMaterials =
                new[] { context.dian902ScopedMaterial };
            renderer.enableGPUInstancing = false;
        }

        private static void ApplyDian901FixedManualScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context)
        {
            Require(
                context.dian901ScopedMaterial != null &&
                context.dian901ScopedMaterial.shader != null &&
                context.dian901ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName,
                "Dian901 renderer-scoped material is unavailable");
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expectedSource = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expectedSource),
                "Dian901 source vertex-stream signature changed");
            renderer.sharedMaterials =
                new[] { context.dian901ScopedMaterial };
            renderer.enableGPUInstancing = false;
        }

        private static void ValidateDian901SourceTuple(
            Dictionary<string, object> sourceSystem,
            Dictionary<string, object> sourceRenderer,
            long[] materialIds,
            Context context,
            string hierarchy)
        {
            Dictionary<string, object> systemSource =
                Dict(sourceSystem["source"]);
            Dictionary<string, object> rendererSource =
                Dict(sourceRenderer["source"]);
            Dictionary<string, object> rendererFields =
                Dict(sourceRenderer["fields"]);
            long[] meshIds =
            {
                PPtrId(rendererFields["m_Mesh"]),
                PPtrId(rendererFields["m_Mesh1"]),
                PPtrId(rendererFields["m_Mesh2"]),
                PPtrId(rendererFields["m_Mesh3"]),
            };
            Require(
                Long(systemSource, "pathID") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .ParticleSystemPathId &&
                Str(systemSource, "sourceFile") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .SourceFile &&
                Long(systemSource, "sourceOffset") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .SourceOffset &&
                Str(systemSource, "rawDataSha256") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .ParticleSystemRawSha256 &&
                Long(rendererSource, "pathID") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .RendererPathId &&
                Str(rendererSource, "sourceFile") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .SourceFile &&
                Long(rendererSource, "sourceOffset") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .SourceOffset &&
                Str(rendererSource, "rawDataSha256") ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .RendererRawSha256 &&
                PPtrId(rendererFields["m_GameObject"]) ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .GameObjectPathId &&
                materialIds.SequenceEqual(
                    new[]
                    {
                        EndfieldRecoveredDian901FixedManualPlayback
                            .MaterialPathId,
                    }) &&
                meshIds[0] ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .MeshPathId &&
                meshIds.Skip(1).All(id => id == 0) &&
                Int(rendererFields, "m_RenderMode") == 4 &&
                Int(rendererFields, "m_RenderAlignment") == 2,
                "Dian901 source identity tuple drifted at " + hierarchy);
            Require(
                context.meshes.TryGetValue(
                    Dian901MeshPathId,
                    out Mesh exactMesh) &&
                exactMesh != null,
                "Dian901 exact mesh is unavailable at " + hierarchy);
            Require(
                Sha256(AssetPathToAbsolute(
                    SourceRoot +
                    "/Materials/M_fx_ui_dian_901_pB74D535120BFAD93.source.json")) ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .MaterialJsonSha256 &&
                Sha256(AssetPathToAbsolute(
                    SourceRoot +
                    "/Meshes/Plane002_p85A195870E1E3746.source.json")) ==
                    EndfieldRecoveredDian901FixedManualPlayback
                        .MeshJsonSha256,
                "Dian901 source Material/Mesh JSON hash drifted at " +
                hierarchy);
        }

        private static void ApplyLightning902ScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context)
        {
            Require(
                context.lightning902ScopedMaterial != null &&
                context.lightning902ScopedMaterial.shader != null &&
                context.lightning902ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName,
                "Lightning902 renderer-scoped material is unavailable");
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expectedSource = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expectedSource),
                "Lightning902 source vertex-stream signature changed");
            renderer.sharedMaterials =
                new[] { context.lightning902ScopedMaterial };
            renderer.enableGPUInstancing = false;
        }

        private static void ValidateGenerated(
            Dictionary<string, object> contract,
            Context context,
            bool writeReport)
        {
            int expectedNodes = 0;
            int expectedPairs = 0;
            int expectedMeshRenderers = 0;
            int effects = 0;
            int line006ScopedRendererCount = 0;
            int line006SharedFailClosedRendererCount = 0;
            int dian901FixedManualScopedRendererCount = 0;
            int dian901FixedManualPlaybackComponentCount = 0;
            int dian902ManualScopedRendererCount = 0;
            int dian902ManualPlaybackComponentCount = 0;
            int lightning902ScopedRendererCount = 0;
            var expectedPrefabPaths = new HashSet<string>(StringComparer.Ordinal);
            foreach (object rootObject in List(contract["roots"]))
            {
                Dictionary<string, object> root = Dict(rootObject);
                if (Str(root, "inventoryKind") != "particle_effect")
                    continue;
                effects++;
                expectedNodes += Int(root, "hierarchyNodeCount");
                expectedPairs += Int(root, "particlePairCount");
                expectedMeshRenderers += List(root["hierarchyNodes"])
                    .Cast<object>()
                    .Select(Dict)
                    .Count(node =>
                    {
                        Dictionary<string, object> sourceGameObject = Dict(node["gameObject"]);
                        return Dict(sourceGameObject.TryGetValue("m_MeshRenderer", out object value)
                            ? value
                            : null).Count > 0;
                    });
                string effectRoot = Str(root, "effectRoot");
                string prefabPath = PrefabRoot + "/" + Safe(effectRoot) + ".prefab";
                expectedPrefabPaths.Add(prefabPath);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Require(prefab != null, "Missing generated effect prefab " + prefabPath);
                EndfieldRecoveredParticleEffectSource marker =
                    prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(marker != null, "Missing source marker on " + effectRoot);
                Require(marker.contractSchema == ExpectedSchema, "Marker schema mismatch on " + effectRoot);
                Require(marker.effectRoot == effectRoot, "Marker effect root mismatch on " + effectRoot);
                Require(marker.particleNodes.Length == Int(root, "particlePairCount"),
                    "Marker particle count mismatch on " + effectRoot);
                Require(marker.hierarchyNodes.Length == Int(root, "hierarchyNodeCount"),
                    "Marker hierarchy-node count mismatch on " + effectRoot);
                Require(prefab.GetComponentsInChildren<Transform>(true).Length == Int(root, "hierarchyNodeCount"),
                    "Hierarchy node count mismatch on " + effectRoot);
                ParticleSystem[] systems = prefab.GetComponentsInChildren<ParticleSystem>(true);
                ParticleSystemRenderer[] renderers = prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
                Require(systems.Length == marker.particleNodes.Length, "Particle system count mismatch on " + effectRoot);
                Require(renderers.Length == marker.particleNodes.Length, "Particle renderer count mismatch on " + effectRoot);
                int sourceMeshRendererCount = List(root["hierarchyNodes"])
                    .Cast<object>()
                    .Select(Dict)
                    .Count(node =>
                    {
                        Dictionary<string, object> sourceGameObject = Dict(node["gameObject"]);
                        return Dict(sourceGameObject.TryGetValue("m_MeshRenderer", out object value)
                            ? value
                            : null).Count > 0;
                    });
                Require(prefab.GetComponentsInChildren<MeshRenderer>(true).Length == sourceMeshRendererCount,
                    "Static MeshRenderer count mismatch on " + effectRoot);

                Dictionary<long, Transform> byTransformPathId = marker.hierarchyNodes.ToDictionary(
                    node => node.transformPathId,
                    node => node.generatedTransform);
                EndfieldRecoveredParticleNodeSource dian901Node =
                    marker.particleNodes.SingleOrDefault(node =>
                        node.particleRendererPathId ==
                            Dian901FixedManualRendererPathId);
                EndfieldRecoveredDian901FixedManualPlayback[]
                    dian901Playbacks =
                        prefab.GetComponentsInChildren<
                            EndfieldRecoveredDian901FixedManualPlayback>(
                                true);
                Require(
                    dian901Playbacks.Length ==
                        (dian901Node == null ? 0 : 1),
                    "Dian901 fixed/manual playback component scope drifted " +
                    "on " + effectRoot);
                if (dian901Node != null)
                {
                    EndfieldRecoveredDian901FixedManualPlayback playback =
                        dian901Playbacks[0];
                    Transform target =
                        byTransformPathId[dian901Node.transformPathId];
                    Require(
                        playback.gameObject == prefab &&
                        playback.TargetParticleSystem ==
                            target.GetComponent<ParticleSystem>() &&
                        playback.TargetRenderer ==
                            target.GetComponent<
                                ParticleSystemRenderer>() &&
                        playback.RendererScopedMaterial ==
                            context.dian901ScopedMaterial &&
                        context.meshes.TryGetValue(
                            Dian901MeshPathId,
                            out Mesh sourceMesh) &&
                        playback.SourceMesh == sourceMesh &&
                        playback.SourceFileValue ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .SourceFile &&
                        playback.SourceOffsetValue ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .SourceOffset &&
                        playback.SourceParticleSystemPathId ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .ParticleSystemPathId &&
                        playback.SourceParticleSystemRawSha256 ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .ParticleSystemRawSha256 &&
                        playback.SourceRendererPathId ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .RendererPathId &&
                        playback.SourceRendererRawSha256 ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .RendererRawSha256 &&
                        playback.SourceGameObjectPathId ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .GameObjectPathId &&
                        playback.SourceMaterialPathId ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .MaterialPathId &&
                        playback.SourceMaterialJsonSha256 ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .MaterialJsonSha256 &&
                        playback.SourceMeshPathId ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .MeshPathId &&
                        playback.SourceMeshJsonSha256 ==
                            EndfieldRecoveredDian901FixedManualPlayback
                                .MeshJsonSha256,
                        "Dian901 fixed/manual serialized identity token " +
                        "drifted on " + effectRoot);
                    dian901FixedManualPlaybackComponentCount++;
                }
                EndfieldRecoveredParticleNodeSource dian902Node =
                    marker.particleNodes.SingleOrDefault(node =>
                        node.particleRendererPathId ==
                            Dian902ManualRendererPathId);
                EndfieldRecoveredDian902ManualPlayback[] playbacks =
                    prefab.GetComponentsInChildren<
                        EndfieldRecoveredDian902ManualPlayback>(true);
                Require(
                    playbacks.Length == (dian902Node == null ? 0 : 1),
                    "Dian902 manual playback component scope drifted on " +
                    effectRoot);
                if (dian902Node != null)
                {
                    EndfieldRecoveredDian902ManualPlayback playback =
                        playbacks[0];
                    Transform target =
                        byTransformPathId[dian902Node.transformPathId];
                    Require(
                        playback.gameObject == prefab &&
                        playback.TargetParticleSystem ==
                            target.GetComponent<ParticleSystem>() &&
                        playback.TargetRenderer ==
                            target.GetComponent<
                                ParticleSystemRenderer>(),
                        "Dian902 manual playback target identity drifted on " +
                        effectRoot);
                    dian902ManualPlaybackComponentCount++;
                }
                foreach (object nodeObject in List(root["hierarchyNodes"]))
                {
                    Dictionary<string, object> node = Dict(nodeObject);
                    string hierarchy = Str(node, "hierarchy");
                    long transformPathId = Long(node, "transformPathID");
                    Require(byTransformPathId.TryGetValue(transformPathId, out Transform transform) && transform != null,
                        $"Generated hierarchy is missing Transform PathID {transformPathId} ({hierarchy})");
                    Require(transform.name == Str(Dict(node["gameObject"]), "m_Name"),
                        $"Generated GameObject name mismatch for Transform PathID {transformPathId}");
                    CompareTransform(transform, Dict(node["transform"]), hierarchy);
                    Dictionary<string, object> sourceGameObject = Dict(node["gameObject"]);
                    Dictionary<string, object> sourceMeshRenderer = Dict(
                        sourceGameObject.TryGetValue("m_MeshRenderer", out object sourceMeshRendererObject)
                            ? sourceMeshRendererObject
                            : null);
                    Dictionary<string, object> sourceMeshFilter = Dict(
                        sourceGameObject.TryGetValue("m_MeshFilter", out object sourceMeshFilterObject)
                            ? sourceMeshFilterObject
                            : null);
                    if (sourceMeshRenderer.Count > 0 || sourceMeshFilter.Count > 0)
                    {
                        Require(sourceMeshRenderer.Count > 0 && sourceMeshFilter.Count > 0,
                            "Incomplete source static renderer pair at " + hierarchy);
                        MeshRenderer generatedMeshRenderer = transform.GetComponent<MeshRenderer>();
                        MeshFilter generatedMeshFilter = transform.GetComponent<MeshFilter>();
                        Require(generatedMeshRenderer != null && generatedMeshFilter != null,
                            "Missing generated static renderer pair at " + hierarchy);
                        long meshId = PPtrId(sourceMeshFilter["m_Mesh"]);
                        context.meshes.TryGetValue(meshId, out Mesh expectedMesh);
                        Require(generatedMeshFilter.sharedMesh == expectedMesh,
                            "Static mesh fail-closed identity mismatch at " + hierarchy);
                        long[] materialIds = PPtrIds(sourceMeshRenderer["m_Materials"]);
                        Material[] materials = generatedMeshRenderer.sharedMaterials;
                        bool allMaterialsSelected = materialIds.All(context.materials.ContainsKey);
                        Require(materials.Length == (allMaterialsSelected ? materialIds.Length : 0),
                            "Static material fail-closed count mismatch at " + hierarchy);
                        for (int materialIndex = 0; allMaterialsSelected && materialIndex < materialIds.Length; materialIndex++)
                        {
                            Require(context.materials.TryGetValue(materialIds[materialIndex], out Material expectedMaterial) &&
                                materials[materialIndex] == expectedMaterial,
                                "Static material identity mismatch at " + hierarchy);
                        }
                    }
                }
                foreach (object pairObject in List(root["particlePairs"]))
                {
                    Dictionary<string, object> pair = Dict(pairObject);
                    string hierarchy = Str(pair, "hierarchy");
                    long gameObjectPathId = Long(pair, "gameObjectPathID");
                    Dictionary<string, object> hierarchyNode = List(root["hierarchyNodes"])
                        .Cast<object>().Select(Dict).Single(node =>
                            Long(node, "gameObjectPathID") == gameObjectPathId);
                    Transform transform = byTransformPathId[Long(hierarchyNode, "transformPathID")];
                    ParticleSystem system = transform.GetComponent<ParticleSystem>();
                    ParticleSystemRenderer renderer = transform.GetComponent<ParticleSystemRenderer>();
                    Require(system != null && renderer != null, "Missing generated pair at " + hierarchy);
                    Require(
                        context.dian904DormantCandidateMaterial == null ||
                        !renderer.sharedMaterials.Contains(
                            context.dian904DormantCandidateMaterial),
                        "Dian904 dormant shader candidate escaped onto a " +
                        "generated renderer at " + hierarchy);
                    Dictionary<string, object> sourceSystem = Dict(pair["particleSystem"]);
                    Dictionary<string, object> sourceRenderer = Dict(pair["renderer"]);
                    VerifyTopLevelDictionary(new SerializedObject(system), Dict(sourceSystem["fields"]), context, "ParticleSystem");
                    foreach (KeyValuePair<string, object> module in Dict(sourceSystem["enabledModules"]))
                        VerifyNamedDictionary(new SerializedObject(system), module.Key, Dict(module.Value), context, "ParticleSystem." + module.Key);
                    long sourceRendererPathId =
                        Long(Dict(sourceRenderer["source"]), "pathID");
                    bool line006Scoped =
                        IsLine006ScopedRenderer(sourceRendererPathId);
                    bool dian901FixedManualScoped =
                        IsDian901FixedManualScopedRenderer(
                            sourceRendererPathId);
                    bool dian902ManualScoped =
                        IsDian902ManualScopedRenderer(sourceRendererPathId);
                    bool lightning902Scoped =
                        IsLightning902ScopedRenderer(
                            sourceRendererPathId);
                    if (line006Scoped)
                    {
                        VerifyTopLevelDictionaryExcept(
                            new SerializedObject(renderer),
                            Dict(sourceRenderer["fields"]),
                            context,
                            "ParticleSystemRenderer",
                            "m_Materials",
                            "m_VertexStreams",
                            "m_EnableGPUInstancing");
                        ValidateLine006ScopedRenderer(
                            renderer,
                            context,
                            hierarchy);
                        line006ScopedRendererCount++;
                    }
                    else if (dian901FixedManualScoped)
                    {
                        VerifyTopLevelDictionaryExcept(
                            new SerializedObject(renderer),
                            Dict(sourceRenderer["fields"]),
                            context,
                            "ParticleSystemRenderer",
                            "m_Materials",
                            "m_EnableGPUInstancing");
                        ValidateDian901FixedManualScopedRenderer(
                            renderer,
                            system,
                            sourceRenderer,
                            sourceSystem,
                            context,
                            hierarchy);
                        dian901FixedManualScopedRendererCount++;
                    }
                    else if (dian902ManualScoped)
                    {
                        VerifyTopLevelDictionaryExcept(
                            new SerializedObject(renderer),
                            Dict(sourceRenderer["fields"]),
                            context,
                            "ParticleSystemRenderer",
                            "m_Materials",
                            "m_EnableGPUInstancing");
                        ValidateDian902ManualScopedRenderer(
                            renderer,
                            context,
                            hierarchy);
                        dian902ManualScopedRendererCount++;
                    }
                    else if (lightning902Scoped)
                    {
                        VerifyTopLevelDictionaryExcept(
                            new SerializedObject(renderer),
                            Dict(sourceRenderer["fields"]),
                            context,
                            "ParticleSystemRenderer",
                            "m_Materials",
                            "m_EnableGPUInstancing");
                        ValidateLightning902ScopedRenderer(
                            renderer,
                            system,
                            sourceRenderer,
                            sourceSystem,
                            context,
                            hierarchy);
                        lightning902ScopedRendererCount++;
                    }
                    else
                    {
                        VerifyTopLevelDictionary(
                            new SerializedObject(renderer),
                            Dict(sourceRenderer["fields"]),
                            context,
                            "ParticleSystemRenderer");
                    }
                    long[] sourceMaterialIds = PPtrIds(Dict(sourceRenderer["fields"])["m_Materials"]);
                    foreach (Material material in renderer.sharedMaterials)
                    {
                        Require(material != null, "Null source material on " + hierarchy);
                        Require(material.shader != null,
                            "Source VFX material has no shader on " + hierarchy);
                    }
                    EndfieldRecoveredParticleNodeSource markerNode = marker.particleNodes.Single(
                        node => node.gameObjectPathId == gameObjectPathId);
                    bool hasUnrecoveredMaterial = sourceMaterialIds.Any(id =>
                        context.materials.TryGetValue(id, out Material sourceMaterial) &&
                        sourceMaterial != null && sourceMaterial.shader != null &&
                        sourceMaterial.shader.name == FailClosedShaderName);
                    bool actualFailClosed =
                        line006Scoped ||
                        dian901FixedManualScoped ||
                        dian902ManualScoped ||
                        lightning902Scoped
                            ? false
                            : hasUnrecoveredMaterial;
                    Require(markerNode.rendererFailClosedForUnrecoveredShader == actualFailClosed,
                        "Renderer fail-closed marker does not describe its actual materials at " + hierarchy);
                    if (!line006Scoped &&
                        sourceMaterialIds.Contains(
                            DeferredLine006Lightning901MaterialPathId))
                    {
                        Require(hasUnrecoveredMaterial,
                            "The non-admitted shared Line006 renderer escaped fail-closed");
                        line006SharedFailClosedRendererCount++;
                    }
                }
            }
            string[] actualPrefabs = AssetDatabase.FindAssets("t:Prefab", new[] { PrefabRoot })
                .Select(AssetDatabase.GUIDToAssetPath).ToArray();
            Require(actualPrefabs.Length == effects, "Generated prefab root contains stale or missing effects");
            Require(actualPrefabs.All(expectedPrefabPaths.Contains), "Unexpected generated particle prefab exists");
            Require(expectedPairs == 70, "Expected 70 validated particle pairs");
            Require(
                line006ScopedRendererCount == 3 &&
                line006SharedFailClosedRendererCount == 0,
                "Line006 renderer-scoped/fail-closed census changed: " +
                line006ScopedRendererCount + "/" +
                line006SharedFailClosedRendererCount);
            Require(
                dian901FixedManualScopedRendererCount == 1,
                "Dian901 fixed/manual renderer-scoped census changed: " +
                dian901FixedManualScopedRendererCount);
            Require(
                dian901FixedManualPlaybackComponentCount == 1,
                "Dian901 fixed/manual playback component census changed: " +
                dian901FixedManualPlaybackComponentCount);
            Require(
                dian902ManualScopedRendererCount == 1,
                "Dian902 manual renderer-scoped census changed: " +
                dian902ManualScopedRendererCount);
            Require(
                dian902ManualPlaybackComponentCount == 1,
                "Dian902 manual playback component census changed: " +
                dian902ManualPlaybackComponentCount);
            Require(
                lightning902ScopedRendererCount == 1,
                "Lightning902 renderer-scoped census changed: " +
                lightning902ScopedRendererCount);

            int recoveredMaterialCount = 0;
            int failClosedMaterialCount = 0;
            foreach (KeyValuePair<long, Material> pair in context.materials)
            {
                Require(pair.Value != null, "Missing generated material " + pair.Key);
                Require(pair.Value.name == context.materialNames[pair.Key], "Material name mismatch " + pair.Key);
                Require(context.materialSources.TryGetValue(pair.Key, out Dictionary<string, object> sourceMaterial),
                    "Missing source Material JSON " + pair.Key);
                SelectedMaterialIdentity selectedIdentity = MatchSelectedIdentity(pair.Key, sourceMaterial);
                if (selectedIdentity == null)
                {
                    Require(pair.Value.shader != null && pair.Value.shader.name == FailClosedShaderName,
                        "Unselected material escaped fail-closed shader " + pair.Key);
                    failClosedMaterialCount++;
                }
                else
                {
                    Require(pair.Value.shader != null &&
                        pair.Value.shader.name == selectedIdentity.recoveredShaderName,
                        "Selected material uses the wrong recovered shader " + pair.Key);
                    ValidateRecoveredMaterialPayload(pair.Value, sourceMaterial, context, selectedIdentity);
                    recoveredMaterialCount++;
                }
            }
            Require(recoveredMaterialCount == 52 && failClosedMaterialCount == 8,
                $"Selected/fail-closed material census changed: {recoveredMaterialCount}/" +
                failClosedMaterialCount);
            Require(
                context.line006ScopedMaterial != null &&
                context.line006ScopedMaterial.shader != null &&
                context.line006ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName &&
                context.line006ScopedMaterial.shaderKeywords.Length == 2 &&
                new HashSet<string>(
                    context.line006ScopedMaterial.shaderKeywords,
                    StringComparer.Ordinal).SetEquals(
                        new[] { Line006ReplayKeyword, "_SAMPLE_TEX0" }) &&
                context.line006ScopedMaterial.renderQueue == 3705 &&
                !context.line006ScopedMaterial.enableInstancing,
                "Line006 renderer-scoped material identity drifted");
            ValidateRecoveredMaterialPayload(
                context.line006ScopedMaterial,
                context.materialSources[
                    DeferredLine006Lightning901MaterialPathId],
                context,
                new SelectedMaterialIdentity
                {
                    materialPathId =
                        DeferredLine006Lightning901MaterialPathId,
                    orderedKeywords =
                        context.line006ScopedMaterial.shaderKeywords,
                    customRenderQueue = 3705,
                    recoveredShaderName = RecoveredBaseV2ShaderName,
                });
            Require(
                context.dian901ScopedMaterial != null &&
                context.dian901ScopedMaterial.shader != null &&
                context.dian901ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName &&
                context.dian901ScopedMaterial.shaderKeywords.Length == 7 &&
                new HashSet<string>(
                    context.dian901ScopedMaterial.shaderKeywords,
                    StringComparer.Ordinal).SetEquals(
                        new[]
                        {
                            Dian901FixedManualReplayKeyword,
                            Dian901DynamicReplayKeyword,
                            "_SAMPLE_TEX0",
                            "_SAMPLE_TEX1",
                            "_USE_SOFTBLEND",
                            "_USE_VERTOFFSET",
                            "_USE_VERTOFFSETMASK",
                        }) &&
                context.dian901ScopedMaterial.renderQueue == 3700 &&
                !context.dian901ScopedMaterial.enableInstancing &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualReplayValid")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualReplayMagic")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualReplaySample")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualSourceTime")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualLiveCount")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualReplayEpoch")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualPublishFrame")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualRendererFingerprint")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901ManualReplayChecksum")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901AutomaticSchedulerChecksum")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.dian901ScopedMaterial.GetFloat(
                        "_Dian901AutomaticRowChecksum")) == 0,
                "Dian901 renderer-scoped fixed/manual material identity or " +
                "fail-closed defaults drifted");
            ValidateRecoveredMaterialPayload(
                context.dian901ScopedMaterial,
                context.materialSources[DeferredDian901MaterialPathId],
                context,
                new SelectedMaterialIdentity
                {
                    materialPathId = DeferredDian901MaterialPathId,
                    orderedKeywords =
                        context.dian901ScopedMaterial.shaderKeywords,
                    customRenderQueue = 3700,
                    recoveredShaderName = RecoveredBaseV2ShaderName,
                });
            Require(
                context.dian902ScopedMaterial != null &&
                context.dian902ScopedMaterial.shader != null &&
                context.dian902ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName &&
                context.dian902ScopedMaterial.shaderKeywords.Length == 7 &&
                new HashSet<string>(
                    context.dian902ScopedMaterial.shaderKeywords,
                    StringComparer.Ordinal).SetEquals(
                        new[]
                        {
                            Dian902ManualReplayKeyword,
                            Dian902DynamicReplayKeyword,
                            "_SAMPLE_TEX0",
                            "_SAMPLE_TEX1",
                            "_USE_SOFTBLEND",
                            "_USE_VERTOFFSET",
                            "_USE_VERTOFFSETMASK",
                        }) &&
                context.dian902ScopedMaterial.renderQueue == 3700 &&
                !context.dian902ScopedMaterial.enableInstancing &&
                BitConverter.SingleToInt32Bits(
                    context.dian902ScopedMaterial.GetFloat(
                        "_Dian902ManualReplayIndex")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian902ScopedMaterial.GetFloat(
                        "_Dian902ManualSourceTime")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian902ScopedMaterial.GetFloat(
                        "_Dian902ManualAgePercent")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.dian902ScopedMaterial.GetFloat(
                        "_Dian902ManualRemainingLifetime")) ==
                    unchecked((int)0xBF800000u),
                "Dian902 renderer-scoped manual material identity or fail-closed defaults drifted");
            ValidateRecoveredMaterialPayload(
                context.dian902ScopedMaterial,
                context.materialSources[DeferredDian902MaterialPathId],
                context,
                new SelectedMaterialIdentity
                {
                    materialPathId = DeferredDian902MaterialPathId,
                    orderedKeywords =
                        context.dian902ScopedMaterial.shaderKeywords,
                    customRenderQueue = 3700,
                    recoveredShaderName = RecoveredBaseV2ShaderName,
                });
            Require(
                context.lightning902ScopedMaterial != null &&
                context.lightning902ScopedMaterial.shader != null &&
                context.lightning902ScopedMaterial.shader.name ==
                    RecoveredBaseV2ShaderName &&
                context.lightning902ScopedMaterial.shaderKeywords.Length ==
                    3 &&
                new HashSet<string>(
                    context.lightning902ScopedMaterial.shaderKeywords,
                    StringComparer.Ordinal).SetEquals(
                        new[]
                        {
                            Lightning902ReplayKeyword,
                            "_SAMPLE_TEX0",
                            "_USE_SOFTBLEND",
                        }) &&
                context.lightning902ScopedMaterial.renderQueue == 3705 &&
                !context.lightning902ScopedMaterial.enableInstancing &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailCustom1X")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailReplayValid")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailReplayMagic")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailReplayEpoch")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailPublishFrame")) ==
                    unchecked((int)0xBF800000u) &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailRendererFingerprint")) == 0 &&
                BitConverter.SingleToInt32Bits(
                    context.lightning902ScopedMaterial.GetFloat(
                        "_Lightning902RetailReplayChecksum")) == 0,
                "Lightning902 renderer-scoped material identity or " +
                "fail-closed defaults drifted");
            ValidateRecoveredMaterialPayload(
                context.lightning902ScopedMaterial,
                context.materialSources[
                    DeferredLightning902MaterialPathId],
                context,
                new SelectedMaterialIdentity
                {
                    materialPathId =
                        DeferredLightning902MaterialPathId,
                    orderedKeywords =
                        context.lightning902ScopedMaterial.shaderKeywords,
                    customRenderQueue = 3705,
                    recoveredShaderName = RecoveredBaseV2ShaderName,
                });
            Require(
                context.dian904DormantCandidateMaterial != null &&
                context.dian904DormantCandidateMaterial.shader != null &&
                context.dian904DormantCandidateMaterial.shader.name ==
                    RecoveredBaseV2ShaderName &&
                context.dian904DormantCandidateMaterial.shaderKeywords.Length ==
                    3 &&
                new HashSet<string>(
                    context.dian904DormantCandidateMaterial.shaderKeywords,
                    StringComparer.Ordinal).SetEquals(
                        new[]
                        {
                            Dian904DormantCandidateKeyword,
                            "_SAMPLE_TEX0",
                            "_USE_SOFTBLEND",
                        }) &&
                context.dian904DormantCandidateMaterial.renderQueue == 3700 &&
                !context.dian904DormantCandidateMaterial.enableInstancing,
                "Dian904 dormant exact-0858/0859 material identity drifted");
            ValidateRecoveredMaterialPayload(
                context.dian904DormantCandidateMaterial,
                context.materialSources[DeferredDian904MaterialPathId],
                context,
                new SelectedMaterialIdentity
                {
                    materialPathId = DeferredDian904MaterialPathId,
                    orderedKeywords =
                        context.dian904DormantCandidateMaterial.shaderKeywords,
                    customRenderQueue = 3700,
                    recoveredShaderName = RecoveredBaseV2ShaderName,
                });
            Require(!SelectedMaterials.ContainsKey(DeferredLine006Lightning901MaterialPathId) &&
                    !SelectedMaterials.ContainsKey(DeferredZhuangfyLightning901MaterialPathId) &&
                    !SelectedMaterials.ContainsKey(DeferredDian901MaterialPathId) &&
                    !SelectedMaterials.ContainsKey(DeferredDian902MaterialPathId) &&
                    !SelectedMaterials.ContainsKey(DeferredDian904MaterialPathId) &&
                    !SelectedMaterials.ContainsKey(DeferredLightning902MaterialPathId) &&
                    context.materials.TryGetValue(
                        DeferredLine006Lightning901MaterialPathId,
                        out Material deferredLine006Lightning901) &&
                    deferredLine006Lightning901 != null &&
                    deferredLine006Lightning901.shader != null &&
                    deferredLine006Lightning901.shader.name == FailClosedShaderName &&
                    context.materials.TryGetValue(
                        DeferredZhuangfyLightning901MaterialPathId,
                        out Material deferredZhuangfyLightning901) &&
                    deferredZhuangfyLightning901 != null &&
                    deferredZhuangfyLightning901.shader != null &&
                    deferredZhuangfyLightning901.shader.name == FailClosedShaderName &&
                    context.materials.TryGetValue(
                        DeferredDian901MaterialPathId,
                        out Material deferredDian901) &&
                    deferredDian901 != null &&
                    deferredDian901.shader != null &&
                    deferredDian901.shader.name == FailClosedShaderName &&
                    context.materials.TryGetValue(
                        DeferredDian902MaterialPathId,
                        out Material deferredDian902) &&
                    deferredDian902 != null &&
                    deferredDian902.shader != null &&
                    deferredDian902.shader.name == FailClosedShaderName &&
                    context.materials.TryGetValue(
                        DeferredDian904MaterialPathId,
                        out Material deferredDian904) &&
                    deferredDian904 != null &&
                    deferredDian904.shader != null &&
                    deferredDian904.shader.name == FailClosedShaderName &&
                    context.materials.TryGetValue(
                        DeferredLightning902MaterialPathId,
                        out Material deferredLightning902) &&
                    deferredLightning902 != null &&
                    deferredLightning902.shader != null &&
                    deferredLightning902.shader.name ==
                        FailClosedShaderName,
                "Deferred Lightning901, Dian901, Dian902, Dian904, and Lightning902 source " +
                "material identities must remain fail-closed " +
                "after their renderer-scoped admissions");
            Require(SelectedMaterials.Values.All(identity =>
                    !identity.orderedKeywords.Contains(
                        "_USE_VERTOFFSET", StringComparer.Ordinal) &&
                    !identity.orderedKeywords.Contains(
                        "_USE_VERTOFFSETMASK", StringComparer.Ordinal)),
                "The exact 1236 vertex-offset path must remain inactive for the " +
                "current 52 selected material tuples");
            foreach (KeyValuePair<long, Mesh> pair in context.meshes)
                Require(pair.Value != null, "Missing generated mesh " + pair.Key);
            foreach (KeyValuePair<long, Texture2D> pair in context.textures)
                Require(pair.Value != null, "Missing generated texture " + pair.Key);
            ValidateGeneratedDependencyCopies(contract, context);
            ForkFieldFacts forkFields = ValidateForkFieldCompatibilityBoundary(contract);

            if (writeReport)
            {
                var report = new ValidationReport
                {
                    schema = "endfield.zhuangfy-gacha-particle-unity-validation.v1",
                    unityVersion = Application.unityVersion,
                    contractAssetPath = ContractAssetPath,
                    contractSha256 = Sha256(AssetPathToAbsolute(ContractAssetPath)),
                    dependencyArtifactAggregateSha256 = Str(
                        Dict(contract["sourceGate"]), "dependencyArtifactAggregateSha256"),
                    generatedPrefabAggregateSha256 = AggregateAssetSha256(expectedPrefabPaths),
                    effectRootCount = effects,
                    hierarchyNodeCount = expectedNodes,
                    particleSystemCount = expectedPairs,
                    particleRendererCount = expectedPairs,
                    meshRendererCount = expectedMeshRenderers,
                    materialAssetCount = context.materials.Count,
                    generatedMaterialAssetCount =
                        context.materials.Count + 5,
                    rendererScopedRecoveredMaterialAssetCount = 4,
                    dian904DormantCandidateMaterialAssetCount = 1,
                    dian904DormantCandidateBoundary =
                        "M_fx_ui_dian_904 remains a ColorMask-0 source " +
                        "material on every renderer. One unreferenced " +
                        "diagnostic material pins the exact 0858/0859 " +
                        "ForwardOnly keyword, texture, static-sampler, and " +
                        "render-state candidate; it is not an admission.",
                    rendererScopedParticleRendererPathIds =
                        new[]
                        {
                            Line006RendererPathIdA,
                            Line006RendererPathIdB,
                            Lightning901ThirdRendererPathId,
                            Dian901FixedManualRendererPathId,
                            Dian902ManualRendererPathId,
                            Lightning902RendererPathId,
                        },
                    line006SharedFailClosedRendererCount =
                        line006SharedFailClosedRendererCount,
                    line006ActiveVertexStreams =
                        "Position,Normal,Color,UV,UV2,Custom1XYZW," +
                        "AgePercent,InvStartLifetime",
                    dian901FixedManualScopedRendererCount =
                        dian901FixedManualScopedRendererCount,
                    dian901FixedManualPlaybackComponentCount =
                        dian901FixedManualPlaybackComponentCount,
                    dian901FixedManualPlaybackBoundary =
                        "Only exact source-time bits 3C23D70A, 3D4CCCCD, " +
                        "3E19999A, 3EB33333, and 3F266666 are admitted. " +
                        "One effect-root component binds renderer PathID " +
                        "-2376706058147287785 to the exact ParticleSystem, " +
                        "GameObject, Material, mesh, source-file/offset, and " +
                        "raw/JSON hashes. Explicit SimulateExact writes zero, " +
                        "one, or two complete source-closed particle rows, " +
                        "verifies every public carrier bit, and publishes a " +
                        "same-frame epoch/fingerprint/checksum MPB token. " +
                        "Unsupported, stale-frame, partial, disable, and " +
                        "destroy paths clear geometry and revoke the token. " +
                        "A separate dynamic keyword admits the binary-derived " +
                        "automatic variable-step scheduler only through explicit " +
                        "AdvanceExact caller deltas. Its visible rows preserve " +
                        "retail start position/velocity/size/rotation/seed plus " +
                        "direct current Color32 and Custom1. Public lifetime is " +
                        "transport-virtualized to the carrier-oracle exact " +
                        "age-37 pair; arbitrary lifetime inversion is not " +
                        "admitted.",
                    dian902ManualScopedRendererCount =
                        dian902ManualScopedRendererCount,
                    dian902ManualReplayStates =
                        "0=(3F75C28A..3F7AE141 -> canonical 3F75C28F, custom 3EB3C2F4, alpha FF); " +
                        "1=(3F7AE142..3F7FFFF9 -> canonical 3F7AE148, custom 3EB6F0F8, alpha FF); " +
                        "2=(3F7FFFFA..3F828F58 -> canonical 3F800000, custom 3EB95F67, alpha FF); " +
                        "3=(3F828F59..3F851EB4 -> canonical 3F828F5C, custom 3EBCC9B5, alpha 00); " +
                        "4=(3F851EB5..3F87AE10 -> canonical 3F851EB8, custom 3EC2EB52, alpha FF); " +
                        "5=(3F87AE11..3F8A3D6C -> canonical 3F87AE14, custom 3ED9B742, alpha FF); " +
                        "6=(3F8A3D6D..3F8CCCC8 -> canonical 3F8A3D71, custom 3F0B7289, alpha FF); " +
                        "7=(3F8CCCC9..3F8F5C24 -> canonical 3F8CCCCD, custom 3F2FF476, alpha FF); " +
                        "8=(3F8F5C25..3F91EB80 -> canonical 3F8F5C29, custom 3F4BCD10, alpha FF); " +
                        "all Draw colors use exact linear blue bits 3EDADADB",
                    dian902ManualPlaybackComponentCount =
                        dian902ManualPlaybackComponentCount,
                    lightning902ScopedRendererCount =
                        lightning902ScopedRendererCount,
                    lightning902RuntimeReplayBoundary =
                        "Only renderer PathID 296863772203003159 paired " +
                        "with source material PathID -1087199587020585838 " +
                        "uses the runtime clone. Each Timeline Evaluate " +
                        "revokes its MPB token; one same-frame LateUpdate " +
                        "may publish the installed transition function " +
                        "using actual Time.deltaTime when the exact " +
                        "count-one renderer identity remains live. " +
                        "Manual/editor/external evaluation stays clipped.",
                    dian902ManualPlaybackBoundary =
                        "One effect-root component stores only renderer PathID -7137180953804559081 and its paired ParticleSystem. " +
                        "SimulateExact maps nine exact inclusive installed-retail live ranges to canonical representatives, restarts public geometry only at " +
                        "that canonical time and verifies one particle with exact seed, position, degree-space rotation, and currentSize3D bits. Public TRS already matches " +
                        "the closed retail shape/Initial paths, so it is not overwritten. It preserves unrelated MaterialPropertyBlock values. Every unsupported input, disable, " +
                        "or destroy clears geometry and resets four replay carriers to -1. AdvanceExact explicitly models installed automatic subdivision, delay, burst-after-sim, " +
                        "continuous age, hitch floors, death, and compaction; RestartExact returns to pre-delay state. There is no Update or auto-play.",
                    meshAssetCount = context.meshes.Count,
                    textureAssetCount = context.textures.Count,
                    nativeTextureAssetCount = context.nativeTextureRecords.Count,
                    nativeTextureContractAssetPaths = NativeTextureContractAssetPaths,
                    nativeTextureContractSha256 =
                        AggregateAssetSha256(NativeTextureContractAssetPaths),
                    nativeTexturePayloadAggregateSha256 =
                        AggregateNativeTexturePayloadSha256(context.nativeTextureRecords),
                    recoveredMaterialAssetCount = recoveredMaterialCount,
                    failClosedMaterialAssetCount = failClosedMaterialCount,
                    sourceArtifactCount = context.sourceArtifactCount,
                    perRendererLightingEnabledCount = forkFields.perRendererLightingEnabledCount,
                    outlineDisabledCount = forkFields.outlineDisabledCount,
                    realtimeShadowCasterCount = forkFields.realtimeShadowCasterCount,
                    characterIndexOneCount = forkFields.characterIndexOneCount,
                    inertSubMeshLoopCount = forkFields.inertSubMeshLoopCount,
                    retailOnlyFieldsPreservedInContract = context.retailOnlyFields.Distinct().OrderBy(s => s).ToArray(),
                    forkFieldCompatibilityBoundary =
                        "Do not map realtimeShadowCaster to public shadowCastingMode, characterIndex to a material property, " +
                        "or HG per-renderer lighting to light probes. Outline-disabled rows stay outside recovered outlines; " +
                        "the sole SubMeshRenderMode Loop row is inert because source static-batch subMeshCount is zero.",
                    shaderExecutionBoundary =
                        "Fifty-two source materials pass a five-fact identity gate and use their selected two-target shader family; " +
                        "execution additionally requires the pipeline's sceneMV MRT and live VFX-global readiness gates. " +
                        "BASE and soft-only material samplers use original texture-derived state; soft depth uses the original " +
                        "point-clamp static sampler. The selected Fresnel power/wind path executes the source-visible non-instanced RGB/alpha branch. " +
                        "Glow903 admits the exact Fresnel/soft mode-4 Sphere path because its single particle collapses to authored transform constants, " +
                        "its lifetime color is a serialized gradient, and null MainTex binds the shader-declared white default without a synthesized payload. " +
                        "The retail SRP_INSTANCING_ON material-array ABI remains an explicit boundary. " +
                        "All 52 selected materials author _SurfaceType=1 and _EnableTransparentMV=0, so their 15 exact " +
                        "non-instanced fragment signatures gate previous-clip sceneMV XY to neutral. " +
                        "Rainbow901 preserves its per-fragment polar approximation; its compiled screen-UV path is admitted only because " +
                        "the authored screen selector and all five screen-coordinate weights are exactly zero. " +
                        "The shared Line006 Lightning901 source material remains fail-closed. Its three exact renderer PathIDs use one recovered " +
                        "renderer-scoped clone and ordinary expanded particle streams. Two use the strict reciprocal-whitelisted full-lifetime " +
                        "Custom1 replay; the third uses the exact 62-row (InvStartLifetime, stale Custom1) retail-current lookup and scoped precise color round-trip. " +
                        "The Dian901 source material also remains fail-closed. Only renderer PathID -2376706058147287785 uses a separate clone, " +
                        "which clips unless its exact serialized source token and one of five fixed/manual source-time tuples publish a same-frame " +
                        "epoch/fingerprint/checksum token after every complete particle carrier bit verifies. Its distinct dynamic token admits the " +
                        "binary-derived automatic scheduler only when explicit caller deltas, scheduler checksum, row checksum, and direct Color32/Custom1 " +
                        "readback all verify. Automatic public lifetime uses the proven exact age-37 carrier pair while retail lifetime/inverse/age remain CPU/checksum state. " +
                        "The Dian902 source material also remains fail-closed. Only renderer PathID -7137180953804559081 uses its recovered clone, " +
                        "which clips unless one of nine bit-exact fixed/manual canonical tuples is supplied. Those tuples replay installed Custom1.z and exact " +
                        "linear-blue Draw color; state 3 is transparent and the other eight states are opaque. The maintained 1236/1237/native-texture paths remain active. " +
                        "The same renderer-scoped clone additionally admits a strict dynamic tuple only when age is finite/nonnegative/at most 100, normalized age and " +
                        "remaining lifetime recompute bit-exactly, and the explicit AdvanceExact automatic scheduler owns the MPB. The runtime uses canonical public geometry, " +
                        "requires the independently closed stock seed/position/rotation/currentSize3D contract without overwriting it, and preserves unrelated renderer property-block values. " +
                        "There is no Update or auto-play; source material and every other renderer remain fail-closed. " +
                        "Dian904 remains source-material fail-closed on all three mesh choices. Its unreferenced diagnostic clone pins " +
                        "the exact 0858/0859 Sample0+soft specialization, including depth LinearClamp, MainTex LinearRepeat, and " +
                        "SampleTex0 LinearMirror static samplers, but does not claim retail particle-SoA or transform closure. " +
                        "The separate Zhuangfy Lightning901 material and the other three " +
                        "retail variants also render through a ColorMask 0 " +
                        "fail-closed shader. Exact source BC7 blocks and " +
                        "authored mip chains are byte-preserved for the lizi901/lizi906 main textures, all five rainbow901 slots, Trail901 MainTex, " +
                        "the Trail902/903 visible carriers, and all active EntityVFX additive texture slots; other selected texture " +
                        "dependencies remain descriptor-plus-top-level-PNG recovery.",
                    selectedSceneMvNeutralMaterialCount = recoveredMaterialCount,
                    selectedSceneMvBoundary =
                        "Selected sceneMV XY is exact neutral for the identity-gated 52 only. " +
                        "Generic transparent-motion-on transport and non-selected materials remain outside this claim.",
                    forkFieldCompatibilityBoundaryPassed = true,
                    selectedSceneMvNeutralPassed = recoveredMaterialCount == 52,
                    passed = true,
                };
                string reportPath = ProjectRelativeToAbsolute(
                    "scratch/character_recovery/zhuangfy_particle_runtime/unity_validation.json");
                Directory.CreateDirectory(Path.GetDirectoryName(reportPath));
                File.WriteAllText(reportPath, JsonUtility.ToJson(report, true) + Environment.NewLine, Encoding.UTF8);
            }
            Debug.Log($"Validated {effects} Zhuangfy particle effects, {expectedNodes} nodes, " +
                $"{expectedPairs} particle/renderer pairs, {context.materials.Count} materials, " +
                $"including {recoveredMaterialCount} selected MRT variants and {failClosedMaterialCount} fail-closed variants, " +
                $"{context.meshes.Count} meshes, and {context.textures.Count} textures.");
        }

        private static ForkFieldFacts ValidateForkFieldCompatibilityBoundary(
            Dictionary<string, object> contract)
        {
            var facts = new ForkFieldFacts();
            int rendererCount = 0;
            int subMeshLoopCount = 0;
            foreach (object rootObject in List(contract["roots"]))
            {
                foreach (object pairObject in List(Dict(rootObject)["particlePairs"]))
                {
                    Dictionary<string, object> fields = Dict(Dict(Dict(pairObject)["renderer"])["fields"]);
                    rendererCount++;
                    Require(Int(fields, "m_RayTracingMode") == 0 &&
                        Int(fields, "m_RayTraceProcedural") == 0 &&
                        Nearly(Float(fields, "m_RendererSortingFudge"), 0f),
                        "Selected public ray-tracing/sorting defaults changed");

                    if (Bool(fields, "m_EnablePerRendererLighting"))
                    {
                        facts.perRendererLightingEnabledCount++;
                        Dictionary<string, object> offset = Dict(fields["m_PerRendererLightingOffset"]);
                        Dictionary<string, object> anchor = Dict(fields["m_PerRendererLightingAnchor"]);
                        Require(Nearly(Float(offset, "x"), 0f) &&
                            Nearly(Float(offset, "y"), 0f) &&
                            Nearly(Float(offset, "z"), 0f) &&
                            Int(anchor, "m_FileID") == 0 && Long(anchor, "m_PathID") == 0L,
                            "HG per-renderer-lighting origin/anchor boundary changed");
                    }
                    if (!Bool(fields, "m_EnableCharacterOutline"))
                        facts.outlineDisabledCount++;
                    if (Int(fields, "m_RealtimeShadowCaster") == 1)
                    {
                        facts.realtimeShadowCasterCount++;
                        Require(Int(fields, "m_CastShadows") == 0,
                            "Fork realtime shadow must remain independent from public cast-shadows");
                    }
                    int characterIndex = Int(fields, "m_CharacterIndex");
                    Require(characterIndex == 0 || characterIndex == 1,
                        "Unexpected selected character-index value");
                    if (characterIndex == 1)
                        facts.characterIndexOneCount++;
                    int subMeshMode = Int(fields, "m_SubMeshRenderMode");
                    Require(subMeshMode == 0 || subMeshMode == 1,
                        "Unexpected selected submesh-render mode");
                    if (subMeshMode == 1)
                    {
                        subMeshLoopCount++;
                        Require(Int(Dict(fields["m_StaticBatchInfo"]), "subMeshCount") == 0,
                            "Selected SubMeshRenderMode Loop row is no longer inert");
                        facts.inertSubMeshLoopCount++;
                    }
                }
            }
            Require(rendererCount == 70 &&
                facts.perRendererLightingEnabledCount == 70 &&
                facts.outlineDisabledCount == 4 &&
                facts.realtimeShadowCasterCount == 8 &&
                facts.characterIndexOneCount == 1 &&
                subMeshLoopCount == 1 && facts.inertSubMeshLoopCount == 1,
                "Pinned Zhuang particle fork-field census changed");
            return facts;
        }

        private static void ValidateGeneratedDependencyCopies(
            Dictionary<string, object> contract,
            Context context)
        {
            Dictionary<string, object> records = Dict(Dict(contract["dependencies"])["records"]);
            foreach (object recordObject in List(records["Texture2D"]))
            {
                Dictionary<string, object> record = Dict(recordObject);
                long id = Long(record, "pathID");
                if (context.nativeTextureRecords.TryGetValue(
                    id, out Dictionary<string, object> nativeRecord))
                {
                    Dictionary<string, object> jsonArtifact = FindArtifact(record, ".json");
                    Dictionary<string, object> sourceJson = Dict(ManifestMiniJson.Deserialize(
                        File.ReadAllText(
                            RepoRelativeToAbsolute(Str(jsonArtifact, "path")),
                            Encoding.UTF8)));
                    ValidateNativeTexture(
                        context.textures[id], sourceJson, nativeRecord, id, Str(record, "name"));
                }
                else
                {
                    Dictionary<string, object> artifact = FindArtifact(record, ".png");
                    string generated = AssetPathToAbsolute(
                        TextureRoot + "/" + AssetBaseName(Str(record, "name"), id) + ".png");
                    ValidateGeneratedCopy(generated, artifact);
                }
            }
            foreach (object recordObject in List(records["Material"]))
            {
                Dictionary<string, object> record = Dict(recordObject);
                long id = Long(record, "pathID");
                Dictionary<string, object> artifact = FindArtifact(record, ".json");
                string generated = AssetPathToAbsolute(
                    SourceRoot + "/Materials/" + AssetBaseName(Str(record, "name"), id) + ".source.json");
                ValidateGeneratedCopy(generated, artifact);
            }
            foreach (object recordObject in List(records["Mesh"]))
            {
                Dictionary<string, object> record = Dict(recordObject);
                long id = Long(record, "pathID");
                Dictionary<string, object> artifact = FindArtifact(record, ".json");
                string generated = AssetPathToAbsolute(
                    SourceRoot + "/Meshes/" + AssetBaseName(Str(record, "name"), id) + ".source.json");
                ValidateGeneratedCopy(generated, artifact);
                VerifyMeshAgainstSource(context.meshes[id], RepoRelativeToAbsolute(Str(artifact, "path")));
            }
        }

        private static void ValidateGeneratedCopy(
            string generatedAbsolutePath,
            Dictionary<string, object> sourceArtifact)
        {
            Require(File.Exists(generatedAbsolutePath), "Missing generated source copy " + generatedAbsolutePath);
            Require(new FileInfo(generatedAbsolutePath).Length == Long(sourceArtifact, "bytes"),
                "Generated source-copy byte count changed: " + generatedAbsolutePath);
            Require(Sha256(generatedAbsolutePath) == Str(sourceArtifact, "sha256").ToUpperInvariant(),
                "Generated source-copy SHA-256 changed: " + generatedAbsolutePath);
        }

        private static void VerifyMeshAgainstSource(Mesh mesh, string sourceJson)
        {
            Require(mesh != null, "Missing mesh for source verification " + sourceJson);
            Dictionary<string, object> data = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(sourceJson, Encoding.UTF8)));
            int vertexCount = Int(data, "m_VertexCount");
            Require(mesh.name == Str(data, "m_Name"), "Generated mesh name mismatch " + sourceJson);
            Require(mesh.vertexCount == vertexCount, "Generated mesh vertex count mismatch " + sourceJson);
            CompareVectors(mesh.vertices, Vector3Array(List(data["m_Vertices"]), vertexCount, "vertices"), sourceJson + ".vertices");
            CompareVectors(mesh.normals, Vector3Array(List(data["m_Normals"]), vertexCount, "normals", true), sourceJson + ".normals");
            CompareVectors(mesh.uv, Vector2Array(List(data["m_UV0"]), vertexCount, "uv0", true), sourceJson + ".uv0");
            CompareVectors(mesh.tangents, Vector4Array(List(data["m_Tangents"]), vertexCount, "tangents", true), sourceJson + ".tangents");
            CompareColors(mesh.colors, ColorArray(List(data["m_Colors"]), vertexCount, "colors", true), sourceJson + ".colors");
            IList submeshes = List(data["m_SubMeshes"]);
            Require(mesh.subMeshCount == submeshes.Count, "Generated mesh submesh count mismatch " + sourceJson);
            int[] sourceIndices = List(data["m_Indices"]).Cast<object>().Select(Int).ToArray();
            int indexWidth = mesh.indexFormat == IndexFormat.UInt32 ? 4 : 2;
            for (int submesh = 0; submesh < submeshes.Count; submesh++)
            {
                Dictionary<string, object> sourceSubmesh = Dict(submeshes[submesh]);
                int firstIndex = Int(sourceSubmesh, "firstByte") / indexWidth;
                int indexCount = Int(sourceSubmesh, "indexCount");
                int[] expected = sourceIndices.Skip(firstIndex).Take(indexCount).ToArray();
                int[] actual = mesh.GetIndices(submesh, false);
                Require(actual.SequenceEqual(expected), "Generated mesh indices mismatch " + sourceJson);
            }
        }

        private static void CompareVectors(Vector3[] actual, Vector3[] expected, string path)
        {
            Require(actual.Length == expected.Length, "Vector3 stream length mismatch at " + path);
            for (int i = 0; i < actual.Length; i++)
                Require(Nearly(actual[i], expected[i]), "Vector3 stream mismatch at " + path + "[" + i + "]");
        }

        private static void CompareVectors(Vector2[] actual, Vector2[] expected, string path)
        {
            Require(actual.Length == expected.Length, "Vector2 stream length mismatch at " + path);
            for (int i = 0; i < actual.Length; i++)
                Require(Nearly(actual[i], expected[i]), "Vector2 stream mismatch at " + path + "[" + i + "]");
        }

        private static void CompareVectors(Vector4[] actual, Vector4[] expected, string path)
        {
            Require(actual.Length == expected.Length, "Vector4 stream length mismatch at " + path);
            for (int i = 0; i < actual.Length; i++)
                Require(Nearly(actual[i], expected[i]), "Vector4 stream mismatch at " + path + "[" + i + "]");
        }

        private static void CompareColors(Color[] actual, Color[] expected, string path)
        {
            Require(actual.Length == expected.Length, "Color stream length mismatch at " + path);
            for (int i = 0; i < actual.Length; i++)
                Require(Nearly(actual[i], expected[i]), "Color stream mismatch at " + path + "[" + i + "]");
        }

        private static Dictionary<string, Transform> BuildHierarchyLookup(Transform root, string sourceRootHierarchy)
        {
            var result = new Dictionary<string, Transform>(StringComparer.Ordinal);
            foreach (Transform transform in root.GetComponentsInChildren<Transform>(true))
            {
                string relative = RelativePath(root, transform);
                string hierarchy = relative.Length == 0
                    ? sourceRootHierarchy
                    : sourceRootHierarchy + "/" + relative;
                result[hierarchy] = transform;
            }
            return result;
        }

        private static string RelativePath(Transform root, Transform transform)
        {
            if (transform == root)
                return string.Empty;
            var parts = new List<string>();
            Transform cursor = transform;
            while (cursor != null && cursor != root)
            {
                parts.Add(cursor.name);
                cursor = cursor.parent;
            }
            Require(cursor == root, "Transform is outside generated effect root");
            parts.Reverse();
            return string.Join("/", parts);
        }

        internal static void DisableAllKnownModules(SerializedObject serialized)
        {
            foreach (string moduleName in ModuleNames)
            {
                SerializedProperty module = serialized.FindProperty(moduleName);
                if (module == null)
                    continue;
                SerializedProperty enabled = module.FindPropertyRelative("enabled");
                if (enabled != null)
                    enabled.boolValue = false;
            }
        }

        internal static void ApplyTopLevelDictionary(
            SerializedObject serialized,
            Dictionary<string, object> values,
            Context context,
            string owner)
        {
            foreach (KeyValuePair<string, object> pair in values)
            {
                if (pair.Key == "m_GameObject")
                    continue;
                SerializedProperty property = serialized.FindProperty(pair.Key);
                if (property == null)
                {
                    PreserveKnownRetailOnlyField(pair.Key, owner, context);
                    continue;
                }
                ApplyProperty(property, pair.Value, context, owner + "." + pair.Key);
            }
        }

        internal static void ApplyNamedDictionary(
            SerializedObject serialized,
            string name,
            Dictionary<string, object> values,
            Context context,
            string owner)
        {
            SerializedProperty property = serialized.FindProperty(name);
            Require(property != null, "Stock Unity is missing enabled source module " + owner);
            ApplyProperty(property, values, context, owner);
        }

        internal static void VerifyTopLevelDictionary(
            SerializedObject serialized,
            Dictionary<string, object> values,
            Context context,
            string owner)
        {
            serialized.UpdateIfRequiredOrScript();
            foreach (KeyValuePair<string, object> pair in values)
            {
                if (pair.Key == "m_GameObject")
                    continue;
                SerializedProperty property = serialized.FindProperty(pair.Key);
                if (property == null)
                {
                    PreserveKnownRetailOnlyField(pair.Key, owner, context);
                    continue;
                }
                VerifyProperty(property, pair.Value, context, owner + "." + pair.Key);
            }
        }

        private static void VerifyTopLevelDictionaryExcept(
            SerializedObject serialized,
            Dictionary<string, object> values,
            Context context,
            string owner,
            params string[] excludedFields)
        {
            var excluded = new HashSet<string>(
                excludedFields,
                StringComparer.Ordinal);
            serialized.UpdateIfRequiredOrScript();
            foreach (KeyValuePair<string, object> pair in values)
            {
                if (pair.Key == "m_GameObject" ||
                    excluded.Contains(pair.Key))
                    continue;
                SerializedProperty property =
                    serialized.FindProperty(pair.Key);
                if (property == null)
                {
                    PreserveKnownRetailOnlyField(
                        pair.Key,
                        owner,
                        context);
                    continue;
                }
                VerifyProperty(
                    property,
                    pair.Value,
                    context,
                    owner + "." + pair.Key);
            }
        }

        private static void ValidateLine006ScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context,
            string hierarchy)
        {
            Require(
                context.line006ScopedMaterial != null,
                "Missing Line006 renderer-scoped material");
            Require(
                renderer.sharedMaterials.Length == 1 &&
                renderer.sharedMaterials[0] ==
                    context.line006ScopedMaterial,
                "Line006 scoped material identity mismatch at " +
                hierarchy);
            Require(
                !renderer.enableGPUInstancing,
                "Line006 must use the ordinary expanded particle path at " +
                hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expected = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
                ParticleSystemVertexStream.AgePercent,
                ParticleSystemVertexStream.InvStartLifetime,
            };
            Require(
                streams.SequenceEqual(expected),
                "Line006 scoped vertex-stream signature mismatch at " +
                hierarchy + ": " + string.Join(",", streams));
        }

        private static void ValidateDian902ManualScopedRenderer(
            ParticleSystemRenderer renderer,
            Context context,
            string hierarchy)
        {
            Require(
                context.dian902ScopedMaterial != null,
                "Missing Dian902 renderer-scoped material");
            Require(
                renderer.sharedMaterials.Length == 1 &&
                renderer.sharedMaterials[0] ==
                    context.dian902ScopedMaterial,
                "Dian902 scoped material identity mismatch at " +
                hierarchy);
            Require(
                !renderer.enableGPUInstancing,
                "Dian902 manual replay must use the ordinary expanded particle path at " +
                hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expected = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expected),
                "Dian902 scoped vertex-stream signature mismatch at " +
                hierarchy + ": " + string.Join(",", streams));
        }

        private static void ValidateDian901FixedManualScopedRenderer(
            ParticleSystemRenderer renderer,
            ParticleSystem system,
            Dictionary<string, object> sourceRenderer,
            Dictionary<string, object> sourceSystem,
            Context context,
            string hierarchy)
        {
            Require(
                context.dian901ScopedMaterial != null &&
                renderer.sharedMaterials.Length == 1 &&
                renderer.sharedMaterials[0] ==
                    context.dian901ScopedMaterial,
                "Dian901 scoped material identity mismatch at " +
                hierarchy);
            ValidateDian901SourceTuple(
                sourceSystem,
                sourceRenderer,
                PPtrIds(Dict(sourceRenderer["fields"])["m_Materials"]),
                context,
                hierarchy);
            Require(
                renderer.mesh != null &&
                context.meshes.TryGetValue(
                    Dian901MeshPathId,
                    out Mesh sourceMesh) &&
                renderer.mesh == sourceMesh &&
                system.randomSeed == 373373479u &&
                !system.useAutoRandomSeed,
                "Dian901 generated ParticleSystem/mesh identity drifted at " +
                hierarchy);
            Require(
                !renderer.enableGPUInstancing,
                "Dian901 fixed/manual replay must use the ordinary expanded " +
                "particle path at " + hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            var expected = new[]
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expected),
                "Dian901 scoped vertex-stream signature mismatch at " +
                hierarchy + ": " + string.Join(",", streams));
        }

        private static void ValidateLightning902ScopedRenderer(
            ParticleSystemRenderer renderer,
            ParticleSystem system,
            Dictionary<string, object> sourceRenderer,
            Dictionary<string, object> sourceSystem,
            Context context,
            string hierarchy)
        {
            Require(
                context.lightning902ScopedMaterial != null &&
                renderer.sharedMaterials.Length == 1 &&
                renderer.sharedMaterials[0] ==
                    context.lightning902ScopedMaterial,
                "Lightning902 scoped material identity mismatch at " +
                hierarchy);
            long[] sourceMaterials = PPtrIds(
                Dict(sourceRenderer["fields"])["m_Materials"]);
            Require(
                sourceMaterials.SequenceEqual(
                    new[] { DeferredLightning902MaterialPathId }),
                "Lightning902 source material identity drifted at " +
                hierarchy);
            Dictionary<string, object> rendererFields =
                Dict(sourceRenderer["fields"]);
            long[] meshIds =
            {
                PPtrId(rendererFields["m_Mesh"]),
                PPtrId(rendererFields["m_Mesh1"]),
                PPtrId(rendererFields["m_Mesh2"]),
                PPtrId(rendererFields["m_Mesh3"]),
            };
            Require(
                meshIds[0] == Lightning902MeshPathId &&
                meshIds.Skip(1).All(id => id == 0) &&
                context.meshes.TryGetValue(
                    Lightning902MeshPathId,
                    out Mesh exactMesh) &&
                renderer.mesh == exactMesh,
                "Lightning902 mesh identity drifted at " + hierarchy);
            Require(
                Long(Dict(sourceSystem["source"]), "pathID") ==
                    EndfieldRecoveredBaofaTimelineParticleHost
                        .Lightning902ParticleSystemPathId &&
                system.randomSeed == 2991606418u &&
                !system.useAutoRandomSeed &&
                !system.main.loop &&
                system.main.playOnAwake &&
                !system.main.useUnscaledTime &&
                system.main.cullingMode ==
                    ParticleSystemCullingMode.Automatic &&
                BitConverter.SingleToInt32Bits(
                    system.main.duration) ==
                    unchecked((int)0x3F800000u) &&
                BitConverter.SingleToInt32Bits(
                    system.main.simulationSpeed) ==
                    unchecked((int)0x3F800000u) &&
                BitConverter.SingleToInt32Bits(
                    system.main.startLifetime.constant) ==
                    unchecked((int)0x3F19999Au) &&
                BitConverter.SingleToInt32Bits(
                    system.main.startDelay.constant) ==
                    unchecked((int)0x3D4CCCCDu),
                "Lightning902 ParticleSystem identity drifted at " +
                hierarchy);
            ParticleSystem.EmissionModule emission = system.emission;
            ParticleSystem.Burst burst = emission.GetBurst(0);
            Require(
                emission.enabled &&
                emission.burstCount == 1 &&
                BitConverter.SingleToInt32Bits(
                    emission.rateOverTimeMultiplier) == 0 &&
                BitConverter.SingleToInt32Bits(
                    emission.rateOverDistanceMultiplier) == 0 &&
                BitConverter.SingleToInt32Bits(burst.time) == 0 &&
                burst.count.mode ==
                    ParticleSystemCurveMode.Constant &&
                BitConverter.SingleToInt32Bits(
                    burst.count.constant) ==
                    unchecked((int)0x3F800000u) &&
                burst.cycleCount == 1 &&
                !system.subEmitters.enabled &&
                system.subEmitters.subEmittersCount == 0,
                "Lightning902 emission/sub-emitter identity drifted at " +
                hierarchy);
            Require(
                !renderer.enableGPUInstancing,
                "Lightning902 must use the ordinary expanded particle path " +
                "at " + hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            ParticleSystemVertexStream[] expected =
            {
                ParticleSystemVertexStream.Position,
                ParticleSystemVertexStream.Normal,
                ParticleSystemVertexStream.Color,
                ParticleSystemVertexStream.UV,
                ParticleSystemVertexStream.UV2,
                ParticleSystemVertexStream.Custom1XYZW,
            };
            Require(
                streams.SequenceEqual(expected),
                "Lightning902 scoped vertex-stream signature mismatch at " +
                hierarchy + ": " + string.Join(",", streams));
        }

        internal static void VerifyNamedDictionary(
            SerializedObject serialized,
            string name,
            Dictionary<string, object> values,
            Context context,
            string owner)
        {
            serialized.UpdateIfRequiredOrScript();
            SerializedProperty property = serialized.FindProperty(name);
            Require(property != null, "Stock Unity is missing enabled source module " + owner);
            VerifyProperty(property, values, context, owner);
        }

        private static void PreserveKnownRetailOnlyField(string field, string owner, Context context)
        {
            Require(KnownRetailOnlyFields.Contains(field),
                $"Unsupported source field {owner}.{field}; importer fails closed until it is mapped");
            context.retailOnlyFields.Add(owner + "." + field);
        }

        private static void ApplyProperty(
            SerializedProperty property,
            object value,
            Context context,
            string path)
        {
            if (property.propertyType == SerializedPropertyType.ObjectReference)
            {
                property.objectReferenceValue = ResolveObjectReference(value, context, path);
                return;
            }
            if (property.isArray && property.propertyType != SerializedPropertyType.String)
            {
                IList list = List(value);
                property.arraySize = list.Count;
                for (int index = 0; index < list.Count; index++)
                    ApplyProperty(property.GetArrayElementAtIndex(index), list[index], context, path + "[" + index + "]");
                return;
            }
            switch (property.propertyType)
            {
                case SerializedPropertyType.Integer:
                    property.longValue = Long(value);
                    return;
                case SerializedPropertyType.Boolean:
                    property.boolValue = Bool(value);
                    return;
                case SerializedPropertyType.Float:
                    property.floatValue = Float(value);
                    return;
                case SerializedPropertyType.String:
                    property.stringValue = Str(value);
                    return;
                case SerializedPropertyType.Color:
                    property.colorValue = ColorValue(value);
                    return;
                case SerializedPropertyType.Enum:
                    property.enumValueIndex = Int(value);
                    return;
                case SerializedPropertyType.Vector2:
                    property.vector2Value = Vector2Value(value);
                    return;
                case SerializedPropertyType.Vector3:
                    property.vector3Value = Vector3Value(value);
                    return;
                case SerializedPropertyType.Vector4:
                    property.vector4Value = Vector4Value(value);
                    return;
                case SerializedPropertyType.Quaternion:
                    property.quaternionValue = QuaternionValue(value);
                    return;
                case SerializedPropertyType.AnimationCurve:
                    property.animationCurveValue = AnimationCurveValue(value);
                    return;
#if UNITY_2021_2_OR_NEWER
                case SerializedPropertyType.Gradient:
                    property.gradientValue = GradientValue(value);
                    return;
#endif
                case SerializedPropertyType.LayerMask:
                    property.intValue = LayerMaskInt(value, path);
                    return;
                case SerializedPropertyType.Generic:
                    ApplyChildren(property, Dict(value), context, path);
                    return;
                default:
                    throw new NotSupportedException(
                        $"Unsupported serialized property {path} ({property.propertyType})");
            }
        }

        private static void ApplyChildren(
            SerializedProperty property,
            Dictionary<string, object> values,
            Context context,
            string path)
        {
            foreach (KeyValuePair<string, object> pair in values)
            {
                SerializedProperty child = property.FindPropertyRelative(pair.Key);
                if (child == null)
                {
                    PreserveKnownRetailOnlyField(pair.Key, path, context);
                    continue;
                }
                string childPath = path + "." + pair.Key;
                try
                {
                    ApplyProperty(child, pair.Value, context, childPath);
                }
                catch (Exception exception)
                {
                    string valueType = pair.Value == null
                        ? "null"
                        : pair.Value.GetType().FullName;
                    throw new InvalidDataException(
                        "Failed to apply serialized particle field " + childPath +
                        " (propertyType=" + child.propertyType +
                        ", valueType=" + valueType + ")",
                        exception);
                }
            }
        }

        private static void VerifyProperty(
            SerializedProperty property,
            object value,
            Context context,
            string path)
        {
            if (property.propertyType == SerializedPropertyType.ObjectReference)
            {
                Require(property.objectReferenceValue == ResolveObjectReference(value, context, path),
                    "Object reference mismatch at " + path);
                return;
            }
            if (property.isArray && property.propertyType != SerializedPropertyType.String)
            {
                IList list = List(value);
                Require(property.arraySize == list.Count, "Array length mismatch at " + path);
                for (int index = 0; index < list.Count; index++)
                    VerifyProperty(property.GetArrayElementAtIndex(index), list[index], context, path + "[" + index + "]");
                return;
            }
            switch (property.propertyType)
            {
                case SerializedPropertyType.Integer:
                    Require(property.longValue == Long(value), "Integer mismatch at " + path);
                    return;
                case SerializedPropertyType.Boolean:
                    Require(property.boolValue == Bool(value), "Boolean mismatch at " + path);
                    return;
                case SerializedPropertyType.Float:
                    Require(Nearly(property.floatValue, Float(value)), "Float mismatch at " + path);
                    return;
                case SerializedPropertyType.String:
                    Require(property.stringValue == Str(value), "String mismatch at " + path);
                    return;
                case SerializedPropertyType.Color:
                    Require(Nearly(property.colorValue, ColorValue(value)), "Color mismatch at " + path);
                    return;
                case SerializedPropertyType.Enum:
                    Require(property.enumValueIndex == Int(value), "Enum mismatch at " + path);
                    return;
                case SerializedPropertyType.Vector2:
                    Require(Nearly(property.vector2Value, Vector2Value(value)), "Vector2 mismatch at " + path);
                    return;
                case SerializedPropertyType.Vector3:
                    Require(Nearly(property.vector3Value, Vector3Value(value)), "Vector3 mismatch at " + path);
                    return;
                case SerializedPropertyType.Vector4:
                    Require(Nearly(property.vector4Value, Vector4Value(value)), "Vector4 mismatch at " + path);
                    return;
                case SerializedPropertyType.Quaternion:
                    Require(Nearly(property.quaternionValue, QuaternionValue(value)), "Quaternion mismatch at " + path);
                    return;
                case SerializedPropertyType.AnimationCurve:
                    CompareCurves(property.animationCurveValue, AnimationCurveValue(value), path);
                    return;
#if UNITY_2021_2_OR_NEWER
                case SerializedPropertyType.Gradient:
                    CompareGradients(property.gradientValue, GradientValue(value), path);
                    return;
#endif
                case SerializedPropertyType.LayerMask:
                    Require(
                        property.intValue == LayerMaskInt(value, path),
                        "Layer mask mismatch at " + path);
                    return;
                case SerializedPropertyType.Generic:
                    foreach (KeyValuePair<string, object> pair in Dict(value))
                    {
                        SerializedProperty child = property.FindPropertyRelative(pair.Key);
                        if (child == null)
                        {
                            PreserveKnownRetailOnlyField(pair.Key, path, context);
                            continue;
                        }
                        VerifyProperty(child, pair.Value, context, path + "." + pair.Key);
                    }
                    return;
                default:
                    throw new NotSupportedException(
                        $"Unsupported serialized verification property {path} ({property.propertyType})");
            }
        }

        private static UnityEngine.Object ResolveObjectReference(object value, Context context, string path)
        {
            Dictionary<string, object> pptr = Dict(value);
            long pathId = Long(pptr, "m_PathID");
            if (pathId == 0)
                return null;
            if (path.Contains("m_Materials", StringComparison.Ordinal))
            {
                Require(context.materials.TryGetValue(pathId, out Material material),
                    $"Unresolved material {pathId} at {path}");
                return material;
            }
            if (path.Contains("m_Mesh", StringComparison.Ordinal))
            {
                if (context.meshes.TryGetValue(pathId, out Mesh mesh))
                    return mesh;
                // Original default-resource mesh identities are source-closed
                // by the public 2021.3.34f1 oracle in the contract.
                if (pathId == 10207)
                    return BuiltinMesh(PrimitiveType.Sphere, "Sphere");
                if (pathId == 10210)
                    return BuiltinMesh(PrimitiveType.Quad, "Quad");
                throw new InvalidOperationException($"Unresolved mesh {pathId} at {path}");
            }
            if (path.Contains("Texture", StringComparison.Ordinal) || path.Contains("Sprite", StringComparison.Ordinal))
            {
                Require(context.textures.TryGetValue(pathId, out Texture2D texture),
                    $"Unresolved texture {pathId} at {path}");
                return texture;
            }
            throw new InvalidOperationException($"Unsupported non-null PPtr {pathId} at {path}");
        }

        private static Mesh BuiltinMesh(PrimitiveType primitiveType, string expectedName)
        {
            GameObject primitive = GameObject.CreatePrimitive(primitiveType);
            try
            {
                Mesh mesh = primitive.GetComponent<MeshFilter>().sharedMesh;
                Require(mesh != null && mesh.name == expectedName,
                    $"Unity built-in {primitiveType} identity changed (expected {expectedName})");
                return mesh;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(primitive);
            }
        }

        internal static Mesh BuildMesh(string sourceJson, string assetPath, string expectedName)
        {
            Dictionary<string, object> data = Dict(ManifestMiniJson.Deserialize(
                File.ReadAllText(sourceJson, Encoding.UTF8)));
            return BuildMesh(data, assetPath, expectedName, sourceJson);
        }

        internal static Mesh BuildMesh(Dictionary<string, object> data, string assetPath,
            string expectedName, string sourceLabel)
        {
            Require(Str(data, "m_Name") == expectedName, "Mesh name mismatch in " + sourceLabel);
            int vertexCount = Int(data, "m_VertexCount");
            Vector3[] vertices = Vector3Array(List(data["m_Vertices"]), vertexCount, "vertices");
            Vector3[] normals = Vector3Array(List(data["m_Normals"]), vertexCount, "normals", true);
            Vector2[] uv0 = Vector2Array(List(data["m_UV0"]), vertexCount, "uv0", true);
            Vector4[] tangents = Vector4Array(List(data["m_Tangents"]), vertexCount, "tangents", true);
            Color[] colors = ColorArray(List(data["m_Colors"]), vertexCount, "colors", true);
            int[] indices = List(data["m_Indices"]).Cast<object>().Select(Int).ToArray();
            Require(indices.All(i => i >= 0 && i < vertexCount), "Mesh index out of range in " + sourceLabel);
            IList submeshes = List(data["m_SubMeshes"]);
            Require(submeshes.Count > 0, "Mesh has no submeshes " + sourceLabel);
            Require(submeshes.Cast<object>().All(s => Str(Dict(s), "topology") == "Triangles"),
                "Only source triangle topology is admitted in " + sourceLabel);

            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
            if (mesh == null)
            {
                mesh = new Mesh();
                AssetDatabase.CreateAsset(mesh, assetPath);
            }
            mesh.Clear();
            mesh.name = expectedName;
            mesh.indexFormat = indices.Length > 0 && indices.Max() > 65535
                ? IndexFormat.UInt32
                : IndexFormat.UInt16;
            mesh.vertices = vertices;
            if (normals.Length != 0) mesh.normals = normals;
            if (uv0.Length != 0) mesh.uv = uv0;
            if (tangents.Length != 0) mesh.tangents = tangents;
            if (colors.Length != 0) mesh.colors = colors;
            mesh.subMeshCount = submeshes.Count;
            int indexWidth = mesh.indexFormat == IndexFormat.UInt32 ? 4 : 2;
            for (int submesh = 0; submesh < submeshes.Count; submesh++)
            {
                Dictionary<string, object> sourceSubmesh = Dict(submeshes[submesh]);
                int firstIndex = Int(sourceSubmesh, "firstByte") / indexWidth;
                int indexCount = Int(sourceSubmesh, "indexCount");
                Require(firstIndex >= 0 && firstIndex + indexCount <= indices.Length,
                    "Mesh submesh index range is invalid in " + sourceLabel);
                mesh.SetIndices(indices.Skip(firstIndex).Take(indexCount).ToArray(),
                    MeshTopology.Triangles, submesh, false, Int(sourceSubmesh, "baseVertex"));
            }
            mesh.RecalculateBounds();
            EditorUtility.SetDirty(mesh);
            return mesh;
        }

        private static SelectedMaterialIdentity Selected(
            long materialPathId,
            string materialName,
            long originalShaderPathId,
            int customRenderQueue,
            string recoveredShaderName,
            params string[] orderedKeywords)
        {
            return new SelectedMaterialIdentity
            {
                materialPathId = materialPathId,
                materialName = materialName,
                originalShaderPathId = originalShaderPathId,
                orderedKeywords = orderedKeywords,
                customRenderQueue = customRenderQueue,
                recoveredShaderName = recoveredShaderName,
            };
        }

        private static SelectedMaterialIdentity MatchSelectedIdentity(
            long materialPathId,
            Dictionary<string, object> materialJson)
        {
            if (!SelectedMaterials.TryGetValue(materialPathId, out SelectedMaterialIdentity identity))
                return null;
            long shaderPathId = Long(Dict(materialJson["m_Shader"]), "m_PathID");
            string[] keywords = List(materialJson["m_ValidKeywords"])
                .Cast<object>().Select(Str).ToArray();
            return Str(materialJson, "m_Name") == identity.materialName &&
                shaderPathId == identity.originalShaderPathId &&
                keywords.SequenceEqual(identity.orderedKeywords, StringComparer.Ordinal) &&
                Int(materialJson, "m_CustomRenderQueue", -1) == identity.customRenderQueue
                ? identity
                : null;
        }

        private static bool ShaderDeclaresProperty(Shader shader, string propertyName)
        {
            int count = ShaderUtil.GetPropertyCount(shader);
            for (int index = 0; index < count; index++)
            {
                if (ShaderUtil.GetPropertyName(shader, index) == propertyName)
                    return true;
            }
            return false;
        }

        private static string ShaderTag(Shader shader, string tagName)
        {
            var probe = new Material(shader);
            try
            {
                return probe.GetTag(tagName, false, string.Empty);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(probe);
            }
        }

        internal static void ApplyRecoveredMaterialPayload(
            Material material,
            Dictionary<string, object> materialJson,
            Context context)
        {
            if (material.HasProperty("_RecoveredLODFade"))
            {
                material.SetVector(
                    "_RecoveredLODFade",
                    EndfieldRecoveredLodFadePacking.Disabled);
            }
            Dictionary<string, object> saved = Dict(materialJson["m_SavedProperties"]);
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_TexEnvs"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                Dictionary<string, object> textureEnv = Dict(pair.Value);
                long texturePathId = PPtrId(textureEnv["m_Texture"]);
                Texture2D texture = null;
                if (texturePathId != 0)
                {
                    Require(context.textures.TryGetValue(texturePathId, out texture) && texture != null,
                        $"Selected material {material.name} cannot resolve texture {pair.Key} PathID {texturePathId}");
                }
                material.SetTexture(pair.Key, texture);
                material.SetTextureScale(pair.Key, Vector2Value(textureEnv["m_Scale"]));
                material.SetTextureOffset(pair.Key, Vector2Value(textureEnv["m_Offset"]));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Floats"]))
            {
                if (material.HasProperty(pair.Key))
                    material.SetFloat(pair.Key, Float(pair.Value));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Ints"]))
            {
                if (material.HasProperty(pair.Key))
                    material.SetInt(pair.Key, Int(pair.Value));
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Colors"]))
            {
                if (material.HasProperty(pair.Key))
                    material.SetColor(pair.Key, ColorValue(pair.Value));
            }
            material.shaderKeywords = List(materialJson["m_ValidKeywords"])
                .Cast<object>().Select(Str).ToArray();
        }

        private static void ValidateRecoveredMaterialPayload(
            Material material,
            Dictionary<string, object> materialJson,
            Context context,
            SelectedMaterialIdentity identity)
        {
            Require(material.GetTag("EndfieldSceneMVMRT", false, string.Empty) ==
                "ExactSelectedFiftyThree", "Recovered material lost the exact sceneMV MRT tag " + material.name);
            Require(material.shaderKeywords.SequenceEqual(identity.orderedKeywords, StringComparer.Ordinal),
                "Recovered material keyword signature mismatch " + material.name);
            Require(material.renderQueue == identity.customRenderQueue,
                "Recovered material queue mismatch " + material.name);
            Require(material.enableInstancing == Bool(materialJson, "m_EnableInstancingVariants"),
                "Recovered material instancing flag mismatch " + material.name);
            Require(
                Nearly(material.GetFloat("_SurfaceType"), 1f) &&
                Nearly(material.GetFloat("_EnableTransparentMV"), 0f),
                "Selected VFX sceneMV XY gate drifted from the exact authored " +
                "transparent-motion-disabled pair " + material.name);
            if (identity.materialPathId == -5871211190381214596L)
            {
                Require(
                    Nearly(material.GetFloat("_UseScreenUV"), 0f) &&
                    Nearly(material.GetFloat("_UsePolarUV"), 1f) &&
                    Nearly(material.GetFloat("_InParticle"), 1f),
                    "Rainbow901 polar/screen/particle specialization drifted");
                foreach (string property in new[]
                {
                    "_MainTexUVWeights",
                    "_SampleTex0UVWeights",
                    "_SampleTex1UVWeights",
                    "_SampleTex2UVWeights",
                    "_SampleTex3UVWeights",
                })
                {
                    Require(
                        Nearly(material.GetVector(property).w, 0f),
                        "Rainbow901 screen UV ceased to be algebraically dead: " +
                        property);
                }
            }
            if (identity.materialPathId == -2448277796731839051L)
            {
                Require(
                    Nearly(material.GetFloat("_InParticle"), 0f) &&
                    Nearly(material.GetFloat("_UseDissolve"), 1f) &&
                    Nearly(material.GetFloat("_UseDisturb"), 0f) &&
                    Nearly(material.GetFloat("_UseSoftBlend"), 0f) &&
                    Nearly(material.GetFloat("_UseMask"), 0f) &&
                    Nearly(material.GetFloat("_UseBlend"), 0f),
                    "Trail901 algebraically collapsed Sample0 specialization drifted");
                Require(
                    context.nativeTextureRecords.ContainsKey(-310221878972884249L),
                    "Trail901 lost its exact native MainTex payload");
            }
            if (identity.materialPathId == -8085556558894828538L)
            {
                Require(
                    material.GetTexture("_MainTex") == null &&
                    Nearly(material.GetFloat("_InParticle"), 1f) &&
                    Nearly(material.GetFloat("_UseFresnel"), 1f) &&
                    Nearly(material.GetFloat("_UseSoftBlend"), 1f) &&
                    Nearly(material.GetFloat("_UseDissolve"), 0f) &&
                    Nearly(material.GetFloat("_UseMask"), 0f) &&
                    Nearly(material.GetFloat("_UseVertexOffset"), 0f) &&
                    Nearly(material.GetFloat("_FresnelBias"), -0.47f) &&
                    Nearly(material.GetFloat("_FresnelPower"), 7f) &&
                    Nearly(material.GetFloat("_SoftDistance"), 1f),
                    "Glow903 constant-SoA Fresnel/soft specialization drifted");
            }
            if (identity.materialPathId == DeferredDian904MaterialPathId)
            {
                Dictionary<string, object> dian904Saved =
                    Dict(materialJson["m_SavedProperties"]);
                Dictionary<string, object> dian904Colors =
                    Dict(dian904Saved["m_Colors"]);
                Require(
                    dian904Colors.TryGetValue(
                        "_TintColor",
                        out object dian904RawTintValue),
                    "Dian904 source Material JSON lost raw _TintColor");
                Color dian904RawTint = ColorValue(dian904RawTintValue);
                Vector4 dian904RawTintVector =
                    material.GetVector("_Dian904RawTintColor");
                Require(
                    context.textures.TryGetValue(
                        -4094667934537615255L,
                        out Texture2D dian904MainTex) &&
                    context.textures.TryGetValue(
                        1303879328479949420L,
                        out Texture2D dian904SampleTex0) &&
                    material.GetTexture("_MainTex") == dian904MainTex &&
                    material.GetTexture("_SampleTex0") ==
                        dian904SampleTex0 &&
                    Nearly(material.GetFloat("_InParticle"), 1f) &&
                    Nearly(material.GetFloat("_UseSampleTex0"), 1f) &&
                    Nearly(material.GetFloat("_UseSoftBlend"), 1f) &&
                    Nearly(material.GetFloat("_UseDissolve"), 1f) &&
                    Nearly(material.GetFloat("_UseMask"), 0f) &&
                    Nearly(material.GetFloat("_UseVertexOffset"), 0f) &&
                    Nearly(material.GetFloat("_SoftDistance"), 0.1f) &&
                    Nearly(material.GetFloat("_CullMode"), 0f) &&
                    Nearly(material.GetFloat("_ZTest"), 4f) &&
                    Nearly(material.GetFloat("_ZWrite"), 0f) &&
                    Nearly(material.GetFloat("_SrcBlend"), 1f) &&
                    Nearly(material.GetFloat("_DstBlend"), 10f) &&
                    Nearly(material.GetFloat("_AlphaSrcBlend"), 1f) &&
                    Nearly(material.GetFloat("_AlphaDstBlend"), 10f) &&
                    BitConverter.SingleToInt32Bits(dian904RawTint.r) ==
                        unchecked((int)0x3DC51258u) &&
                    BitConverter.SingleToInt32Bits(dian904RawTint.g) ==
                        unchecked((int)0x3F6F233Du) &&
                    BitConverter.SingleToInt32Bits(dian904RawTint.b) ==
                        unchecked((int)0x3F800000u) &&
                    BitConverter.SingleToInt32Bits(dian904RawTint.a) ==
                        unchecked((int)0x3F800000u) &&
                    BitConverter.SingleToInt32Bits(
                        dian904RawTintVector.x) ==
                        BitConverter.SingleToInt32Bits(dian904RawTint.r) &&
                    BitConverter.SingleToInt32Bits(
                        dian904RawTintVector.y) ==
                        BitConverter.SingleToInt32Bits(dian904RawTint.g) &&
                    BitConverter.SingleToInt32Bits(
                        dian904RawTintVector.z) ==
                        BitConverter.SingleToInt32Bits(dian904RawTint.b) &&
                    BitConverter.SingleToInt32Bits(
                        dian904RawTintVector.w) ==
                        BitConverter.SingleToInt32Bits(dian904RawTint.a),
                    "Dian904 dormant exact-0858/0859 payload drifted");
            }
            if (material.HasProperty("_RecoveredLODFade"))
            {
                Require(
                    Nearly(
                        material.GetVector("_RecoveredLODFade"),
                        EndfieldRecoveredLodFadePacking.Disabled),
                    "Recovered material lost the retail disabled LOD-fade sentinel " +
                    material.name);
            }

            Dictionary<string, object> saved = Dict(materialJson["m_SavedProperties"]);
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_TexEnvs"]))
            {
                if (!material.HasProperty(pair.Key))
                    continue;
                Dictionary<string, object> textureEnv = Dict(pair.Value);
                long texturePathId = PPtrId(textureEnv["m_Texture"]);
                Texture2D expectedTexture = null;
                if (texturePathId != 0)
                {
                    Require(context.textures.TryGetValue(texturePathId, out expectedTexture) &&
                        expectedTexture != null,
                        $"Recovered material validation cannot resolve texture {pair.Key} PathID {texturePathId}");
                }
                Require(material.GetTexture(pair.Key) == expectedTexture,
                    "Recovered texture identity mismatch " + material.name + "." + pair.Key);
                Require(Nearly(material.GetTextureScale(pair.Key), Vector2Value(textureEnv["m_Scale"])) &&
                    Nearly(material.GetTextureOffset(pair.Key), Vector2Value(textureEnv["m_Offset"])),
                    "Recovered texture scale/offset mismatch " + material.name + "." + pair.Key);
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Floats"]))
            {
                if (material.HasProperty(pair.Key))
                    Require(Nearly(material.GetFloat(pair.Key), Float(pair.Value)),
                        "Recovered float mismatch " + material.name + "." + pair.Key);
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Ints"]))
            {
                if (material.HasProperty(pair.Key))
                    Require(material.GetInt(pair.Key) == Int(pair.Value),
                        "Recovered int mismatch " + material.name + "." + pair.Key);
            }
            foreach (KeyValuePair<string, object> pair in Dict(saved["m_Colors"]))
            {
                if (material.HasProperty(pair.Key))
                {
                    Color expected = ColorValue(pair.Value);
                    Color actual = material.GetColor(pair.Key);
                    Require(Nearly(actual, expected),
                        $"Recovered color/vector mismatch {material.name}.{pair.Key}: " +
                        $"expected={expected}, actual={actual}");
                }
            }
        }

        private static void ValidateAllSourceArtifacts(Dictionary<string, object> contract, Context context)
        {
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            Action<object> validateSource = value =>
            {
                Dictionary<string, object> descriptor = Dict(value);
                string path = Str(descriptor, "path");
                string sha = Str(descriptor, "jsonSha256");
                if (path.Length == 0 || sha.Length == 0 || !seen.Add(path))
                    return;
                ValidateArtifact(path, Long(descriptor, "jsonBytes"), sha);
            };
            foreach (object rootObject in List(contract["roots"]))
            {
                Dictionary<string, object> root = Dict(rootObject);
                validateSource(Dict(root["effectSetting"])["source"]);
                foreach (object nodeObject in List(root["hierarchyNodes"]))
                {
                    Dictionary<string, object> node = Dict(nodeObject);
                    validateSource(node["gameObjectSource"]);
                    validateSource(node["transformSource"]);
                }
                foreach (object pairObject in List(root["particlePairs"]))
                {
                    Dictionary<string, object> pair = Dict(pairObject);
                    validateSource(Dict(pair["particleSystem"])["source"]);
                    validateSource(Dict(pair["renderer"])["source"]);
                }
            }
            Dictionary<string, object> records = Dict(Dict(contract["dependencies"])["records"]);
            foreach (KeyValuePair<string, object> typeRecords in records)
            {
                foreach (object recordObject in List(typeRecords.Value))
                {
                    foreach (object artifactObject in List(Dict(recordObject)["artifacts"]))
                    {
                        Dictionary<string, object> artifact = Dict(artifactObject);
                        string path = Str(artifact, "path");
                        if (!seen.Add(path))
                            continue;
                        ValidateArtifact(path, Long(artifact, "bytes"), Str(artifact, "sha256"));
                    }
                }
            }
            Dictionary<string, object> sourceGate = Dict(contract["sourceGate"]);
            foreach (string gateName in new[] { "dependencyReport", "dependencyFilter" })
            {
                Dictionary<string, object> artifact = Dict(sourceGate[gateName]);
                string path = Str(artifact, "path");
                if (!seen.Add(path))
                    continue;
                ValidateArtifact(path, Long(artifact, "bytes"), Str(artifact, "sha256"));
            }
            Require(seen.Count == Int(sourceGate, "allSourceCount"),
                $"Source-gate artifact count changed: expected {Int(sourceGate, "allSourceCount")}, got {seen.Count}");
            context.sourceArtifactCount = seen.Count;
        }

        private static void ValidateArtifact(string repoRelativePath, long expectedBytes, string expectedSha)
        {
            string absolute = RepoRelativeToAbsolute(repoRelativePath);
            Require(File.Exists(absolute), "Missing original dependency artifact " + repoRelativePath);
            var info = new FileInfo(absolute);
            Require(info.Length == expectedBytes,
                $"Original dependency byte count changed for {repoRelativePath}");
            Require(Sha256(absolute) == expectedSha.ToUpperInvariant(),
                $"Original dependency SHA-256 changed for {repoRelativePath}");
        }

        private static void ValidateProjectArtifact(
            string projectRelativePath,
            long expectedBytes,
            string expectedSha)
        {
            Require(projectRelativePath.StartsWith("Assets/", StringComparison.Ordinal),
                "Native Texture2D artifact escaped the Unity project: " +
                projectRelativePath);
            string absolute = ProjectRelativeToAbsolute(projectRelativePath);
            Require(File.Exists(absolute),
                "Missing project-local native Texture2D artifact " +
                projectRelativePath);
            var info = new FileInfo(absolute);
            Require(info.Length == expectedBytes,
                "Project-local native Texture2D byte count changed for " +
                projectRelativePath);
            Require(Sha256(absolute) == expectedSha.ToUpperInvariant(),
                "Project-local native Texture2D SHA-256 changed for " +
                projectRelativePath);
        }

        private static Dictionary<string, object> FindArtifact(
            Dictionary<string, object> record,
            string extension)
        {
            List<Dictionary<string, object>> matches = List(record["artifacts"])
                .Cast<object>().Select(Dict)
                .Where(a => Str(a, "path").EndsWith(extension, StringComparison.OrdinalIgnoreCase))
                .ToList();
            Require(matches.Count == 1,
                $"Expected one {extension} artifact for {Str(record, "name")}, found {matches.Count}");
            return matches[0];
        }

        private static void ApplyTransform(Transform target, Dictionary<string, object> source)
        {
            target.localPosition = Vector3Value(source["m_LocalPosition"]);
            target.localRotation = QuaternionValue(source["m_LocalRotation"]);
            target.localScale = Vector3Value(source["m_LocalScale"]);
        }

        private static void CompareTransform(Transform target, Dictionary<string, object> source, string hierarchy)
        {
            Require(Nearly(target.localPosition, Vector3Value(source["m_LocalPosition"])),
                "Local position mismatch at " + hierarchy);
            Require(Nearly(target.localRotation, QuaternionValue(source["m_LocalRotation"])),
                "Local rotation mismatch at " + hierarchy);
            Require(Nearly(target.localScale, Vector3Value(source["m_LocalScale"])),
                "Local scale mismatch at " + hierarchy);
        }

        private static AnimationCurve AnimationCurveValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            var keys = new List<Keyframe>();
            foreach (object keyObject in List(data["m_Curve"]))
            {
                Dictionary<string, object> key = Dict(keyObject);
                var frame = new Keyframe(
                    Float(key, "time"), Float(key, "value"),
                    Float(key, "inSlope"), Float(key, "outSlope"),
                    Float(key, "inWeight"), Float(key, "outWeight"));
                frame.weightedMode = (WeightedMode)Int(key, "weightedMode");
                keys.Add(frame);
            }
            return new AnimationCurve(keys.ToArray())
            {
                preWrapMode = (WrapMode)Int(data, "m_PreInfinity"),
                postWrapMode = (WrapMode)Int(data, "m_PostInfinity"),
            };
        }

        private static Gradient GradientValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            int colorCount = Int(data, "m_NumColorKeys");
            int alphaCount = Int(data, "m_NumAlphaKeys");
            Require(colorCount >= 0 && colorCount <= 8, "Gradient color-key count is out of range");
            Require(alphaCount >= 0 && alphaCount <= 8, "Gradient alpha-key count is out of range");
            var colorKeys = new GradientColorKey[colorCount];
            var alphaKeys = new GradientAlphaKey[alphaCount];
            for (int i = 0; i < colorCount; i++)
            {
                Color color = ColorValue(data["key" + i]);
                colorKeys[i] = new GradientColorKey(color, Int(data, "ctime" + i) / 65535f);
            }
            for (int i = 0; i < alphaCount; i++)
            {
                Color color = ColorValue(data["key" + i]);
                alphaKeys[i] = new GradientAlphaKey(color.a, Int(data, "atime" + i) / 65535f);
            }
            var gradient = new Gradient();
            gradient.mode = (GradientMode)Int(data, "m_Mode");
            gradient.SetKeys(colorKeys, alphaKeys);
            return gradient;
        }

        private static void CompareCurves(AnimationCurve actual, AnimationCurve expected, string path)
        {
            Require(actual != null && actual.length == expected.length, "Curve key count mismatch at " + path);
            Require(actual.preWrapMode == expected.preWrapMode && actual.postWrapMode == expected.postWrapMode,
                "Curve wrap mode mismatch at " + path);
            for (int i = 0; i < actual.length; i++)
            {
                Keyframe a = actual.keys[i];
                Keyframe e = expected.keys[i];
                Require(Nearly(a.time, e.time) && Nearly(a.value, e.value) &&
                        Nearly(a.inTangent, e.inTangent) && Nearly(a.outTangent, e.outTangent) &&
                        Nearly(a.inWeight, e.inWeight) && Nearly(a.outWeight, e.outWeight) &&
                        a.weightedMode == e.weightedMode,
                    "Curve key mismatch at " + path + "[" + i + "]");
            }
        }

        private static void CompareGradients(Gradient actual, Gradient expected, string path)
        {
            Require(actual != null && actual.mode == expected.mode, "Gradient mode mismatch at " + path);
            Require(actual.colorKeys.Length == expected.colorKeys.Length, "Gradient color-key count mismatch at " + path);
            Require(actual.alphaKeys.Length == expected.alphaKeys.Length, "Gradient alpha-key count mismatch at " + path);
            for (int i = 0; i < actual.colorKeys.Length; i++)
                Require(Nearly(actual.colorKeys[i].color, expected.colorKeys[i].color) &&
                        Nearly(actual.colorKeys[i].time, expected.colorKeys[i].time),
                    "Gradient color key mismatch at " + path + "[" + i + "]");
            for (int i = 0; i < actual.alphaKeys.Length; i++)
                Require(Nearly(actual.alphaKeys[i].alpha, expected.alphaKeys[i].alpha) &&
                        Nearly(actual.alphaKeys[i].time, expected.alphaKeys[i].time),
                    "Gradient alpha key mismatch at " + path + "[" + i + "]");
        }

        private static Vector3[] Vector3Array(IList list, int count, string label, bool allowEmpty = false)
        {
            if (allowEmpty && list.Count == 0) return Array.Empty<Vector3>();
            Require(list.Count == count * 3, $"Mesh {label} length mismatch");
            var values = new Vector3[count];
            for (int i = 0; i < count; i++)
                values[i] = new Vector3(Float(list[i * 3]), Float(list[i * 3 + 1]), Float(list[i * 3 + 2]));
            return values;
        }

        private static Vector2[] Vector2Array(IList list, int count, string label, bool allowEmpty = false)
        {
            if (allowEmpty && list.Count == 0) return Array.Empty<Vector2>();
            Require(list.Count == count * 2, $"Mesh {label} length mismatch");
            var values = new Vector2[count];
            for (int i = 0; i < count; i++)
                values[i] = new Vector2(Float(list[i * 2]), Float(list[i * 2 + 1]));
            return values;
        }

        private static Vector4[] Vector4Array(IList list, int count, string label, bool allowEmpty = false)
        {
            if (allowEmpty && list.Count == 0) return Array.Empty<Vector4>();
            Require(list.Count == count * 4, $"Mesh {label} length mismatch");
            var values = new Vector4[count];
            for (int i = 0; i < count; i++)
                values[i] = new Vector4(Float(list[i * 4]), Float(list[i * 4 + 1]),
                    Float(list[i * 4 + 2]), Float(list[i * 4 + 3]));
            return values;
        }

        private static Color[] ColorArray(IList list, int count, string label, bool allowEmpty = false)
        {
            if (allowEmpty && list.Count == 0) return Array.Empty<Color>();
            Require(list.Count == count * 4, $"Mesh {label} length mismatch");
            var values = new Color[count];
            for (int i = 0; i < count; i++)
                values[i] = new Color(Float(list[i * 4]), Float(list[i * 4 + 1]),
                    Float(list[i * 4 + 2]), Float(list[i * 4 + 3]));
            return values;
        }

        private static long[] PPtrIds(object value)
        {
            return List(value).Cast<object>().Select(PPtrId).ToArray();
        }

        private static long PPtrId(object value)
        {
            return Long(Dict(value), "m_PathID");
        }

        private static Color ColorValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            return new Color(FloatEither(data, "r", "R"), FloatEither(data, "g", "G"),
                FloatEither(data, "b", "B"), FloatEither(data, "a", "A", 1f));
        }

        private static Vector2 Vector2Value(object value)
        {
            Dictionary<string, object> data = Dict(value);
            return new Vector2(FloatEither(data, "x", "X"), FloatEither(data, "y", "Y"));
        }

        private static Vector3 Vector3Value(object value)
        {
            Dictionary<string, object> data = Dict(value);
            return new Vector3(FloatEither(data, "x", "X"), FloatEither(data, "y", "Y"),
                FloatEither(data, "z", "Z"));
        }

        private static Vector4 Vector4Value(object value)
        {
            Dictionary<string, object> data = Dict(value);
            return new Vector4(FloatEither(data, "x", "X"), FloatEither(data, "y", "Y"),
                FloatEither(data, "z", "Z"), FloatEither(data, "w", "W"));
        }

        private static Quaternion QuaternionValue(object value)
        {
            Dictionary<string, object> data = Dict(value);
            return new Quaternion(FloatEither(data, "x", "X"), FloatEither(data, "y", "Y"),
                FloatEither(data, "z", "Z"), FloatEither(data, "w", "W", 1f));
        }

        private static bool Nearly(double a, double b) => Math.Abs(a - b) <= 1e-6;
        private static bool Nearly(float a, float b) => Mathf.Abs(a - b) <= 1e-6f;
        private static bool Nearly(Vector2 a, Vector2 b) => (a - b).sqrMagnitude <= 1e-12f;
        private static bool Nearly(Vector3 a, Vector3 b) => (a - b).sqrMagnitude <= 1e-12f;
        private static bool Nearly(Vector4 a, Vector4 b) => (a - b).sqrMagnitude <= 1e-12f;
        private static bool Nearly(Quaternion a, Quaternion b) =>
            Mathf.Abs(a.x - b.x) <= 1e-6f && Mathf.Abs(a.y - b.y) <= 1e-6f &&
            Mathf.Abs(a.z - b.z) <= 1e-6f && Mathf.Abs(a.w - b.w) <= 1e-6f;
        private static bool Nearly(Color a, Color b) =>
            NearlyColorChannel(a.r, b.r) && NearlyColorChannel(a.g, b.g) &&
            NearlyColorChannel(a.b, b.b) && NearlyColorChannel(a.a, b.a);
        private static bool NearlyColorChannel(float a, float b) =>
            Mathf.Abs(a - b) <= 1e-6f * Mathf.Max(1.0f, Mathf.Abs(a), Mathf.Abs(b));

        private static string RepoRoot => Path.GetFullPath(Path.Combine(Application.dataPath, "..", ".."));
        private static string ProjectRoot => Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        private static string AssetPathToAbsolute(string assetPath) =>
            Path.GetFullPath(Path.Combine(Application.dataPath, "..", assetPath));
        private static string RepoRelativeToAbsolute(string path) =>
            Path.GetFullPath(Path.Combine(RepoRoot, path.Replace('/', Path.DirectorySeparatorChar)));
        private static string ProjectRelativeToAbsolute(string path) =>
            Path.GetFullPath(Path.Combine(ProjectRoot, path.Replace('/', Path.DirectorySeparatorChar)));

        private static void EnsureFolder(string assetPath)
        {
            string current = "Assets";
            foreach (string segment in assetPath.Substring("Assets/".Length).Split('/'))
            {
                string next = current + "/" + segment;
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segment);
                current = next;
            }
        }

        private static bool CopyIfDifferent(string source, string destination)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(destination));
            if (File.Exists(destination) && new FileInfo(source).Length == new FileInfo(destination).Length &&
                Sha256(source) == Sha256(destination))
                return false;
            File.Copy(source, destination, true);
            return true;
        }

        private static string Sha256(string path)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", string.Empty);
        }

        private static string Sha256(byte[] payload)
        {
            using (SHA256 hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(payload))
                    .Replace("-", string.Empty);
        }

        private static string AggregateNativeTexturePayloadSha256(
            Dictionary<long, Dictionary<string, object>> records)
        {
            string payload = string.Join("\n", records.OrderBy(
                pair => pair.Key).Select(pair =>
                pair.Key.ToString(CultureInfo.InvariantCulture) + "\t" +
                Str(Dict(pair.Value["payload"]), "sha256").ToUpperInvariant())) + "\n";
            return Sha256(Encoding.UTF8.GetBytes(payload));
        }

        private static string AggregateAssetSha256(IEnumerable<string> assetPaths)
        {
            string payload = string.Join("\n", assetPaths.OrderBy(path => path, StringComparer.Ordinal)
                .Select(path => path + "\t" + Sha256(AssetPathToAbsolute(path)))) + "\n";
            using (SHA256 hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(Encoding.UTF8.GetBytes(payload)))
                    .Replace("-", string.Empty);
        }

        private static string AssetBaseName(string name, long pathId) =>
            Safe(name) + "_p" + unchecked((ulong)pathId).ToString("X16", CultureInfo.InvariantCulture);
        private static string Safe(string value)
        {
            var builder = new StringBuilder(value.Length);
            foreach (char c in value)
                builder.Append(char.IsLetterOrDigit(c) || c == '_' || c == '-' ? c : '_');
            return builder.ToString();
        }

        private static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ?? new Dictionary<string, object>();
        private static IList List(object value) => value as IList ?? Array.Empty<object>();
        private static string Str(object value) => value == null ? string.Empty : Convert.ToString(value, CultureInfo.InvariantCulture);
        private static string Str(Dictionary<string, object> data, string key) =>
            data.TryGetValue(key, out object value) ? Str(value) : string.Empty;
        private static long Long(object value) => value == null ? 0L : Convert.ToInt64(value, CultureInfo.InvariantCulture);
        private static long Long(Dictionary<string, object> data, string key) =>
            data.TryGetValue(key, out object value) ? Long(value) : 0L;
        private static int Int(object value) => value == null ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);
        private static int Int(Dictionary<string, object> data, string key, int fallback = 0) =>
            data.TryGetValue(key, out object value) ? Int(value) : fallback;
        private static float Float(object value) => value == null ? 0f : Convert.ToSingle(value, CultureInfo.InvariantCulture);
        private static float Float(Dictionary<string, object> data, string key, float fallback = 0f) =>
            data.TryGetValue(key, out object value) ? Float(value) : fallback;
        private static double Double(object value) => value == null ? 0d : Convert.ToDouble(value, CultureInfo.InvariantCulture);
        private static bool Bool(object value) => value != null && Convert.ToBoolean(value, CultureInfo.InvariantCulture);
        private static bool Bool(Dictionary<string, object> data, string key) =>
            data.TryGetValue(key, out object value) && Bool(value);
        private static int LayerMaskInt(object value, string path)
        {
            object source = value;
            if (value is Dictionary<string, object> dictionary)
            {
                if (!dictionary.TryGetValue("m_Bits", out source))
                {
                    throw new InvalidOperationException(
                        $"Layer mask source at {path} is an object without required m_Bits.");
                }
            }
            try
            {
                return source == null
                    ? 0
                    : unchecked((int)Convert.ToUInt32(
                        source,
                        CultureInfo.InvariantCulture));
            }
            catch (Exception exception) when (
                exception is InvalidCastException ||
                exception is FormatException ||
                exception is OverflowException)
            {
                string sourceType = source == null
                    ? "<null>"
                    : source.GetType().FullName;
                string sourceValue = source == null
                    ? "<null>"
                    : Convert.ToString(source, CultureInfo.InvariantCulture);
                throw new InvalidOperationException(
                    $"Layer mask source conversion failed at {path}: expected UInt32 " +
                    $"or {{m_Bits: UInt32}}, actual type={sourceType}, value={sourceValue}.",
                    exception);
            }
        }
        private static float FloatEither(
            Dictionary<string, object> data, string lower, string upper, float fallback = 0f) =>
            data.TryGetValue(lower, out object value) ? Float(value) :
            (data.TryGetValue(upper, out value) ? Float(value) : fallback);
        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
