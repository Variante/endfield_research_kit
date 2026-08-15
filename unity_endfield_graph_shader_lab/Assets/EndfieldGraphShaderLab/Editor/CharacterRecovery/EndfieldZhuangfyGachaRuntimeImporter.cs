using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using UnityEngine.Playables;
using UnityEngine.Timeline;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldZhuangfyGachaRuntimeImporter
    {
        private const string PayloadPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_runtime_payload.json";
        private const string TimelineContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_timeline_entity_vfx_contract.json";
        private const string ParticleContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_particle_inventory.json";
        private const string ExpectedPayloadSha256 =
            "962CCC2CF724B15278DA5E4D7E0A774A23795AA6C851072C84DC8266EABDAFFF";
        private const string ExpectedTimelineSha256 =
            "38B4611DEB11E27E7D9ACC11B7EC4B9DE065C57A541AFF98C9EF2F705EE5872B";
        private const string ExpectedParticleSha256 =
            "DA24DA3875B0859E9DD806F7E0FC92566AB3CC0B5956D68CC35DA26B1308AB32";
        private const string ExpectedNativeSha256 =
            "1F7AA6596130D65C2DDD6F99CCE7393FEE607E8942B9B4C001E48C9F82471AD5";
        private const string ExpectedStartOrderSha256 =
            "A95AE5584BEDD692D5E2B70A3C47913B5427A6E5000D7530844536AD947060BA";
        private const string NativeContractRepoPath =
            "scratch/reverse_engineering/zhuangfy_entity_vfx_runtime/entity_vfx_native_runtime_contract.json";
        private const string StartOrderContractRepoPath =
            "scratch/character_recovery/zhuangfy_gacha_start_order/zhuangfy_gacha_start_order_contract.json";
        private const string TimelineParticleHostAuditRepoPath =
            "scratch/reverse_engineering/zhuangfy_dian902_timeline_particle_host/" +
            "timeline_particle_host_audit.json";
        private const string TimelineParticleHostAuditSha256 =
            "7A360720FEF3F832D14C3047982DD8966F0E6ACE94282D5EA1E488CA94D0BBF8";
        private const string Dian901AutomaticRuntimeAuditRepoPath =
            "scratch/reverse_engineering/zhuangfy_dian901_automatic_runtime/" +
            "dian901_automatic_runtime.json";
        private const string Dian901AutomaticRuntimeAuditSha256 =
            "FE2029A7BFD4BE76E92CEE10F6123BD7CE492EC1EE6EC34BECA780FDAF14B8D7";
        private const string Dian901Order4AutomaticOwnerAuditRepoPath =
            "scratch/reverse_engineering/" +
            "zhuangfy_dian901_order4_automatic_owner/" +
            "dian901_order4_automatic_owner.json";
        private const string Dian901Order4AutomaticOwnerAuditSha256 =
            "2E90BD8597FD8457CE77BCDDCD2CA530B0B8AD2BB779C9365A0707D238B1D6D5";
        private const string Dian901DynamicCarrierOracleRepoPath =
            "unity_endfield_graph_shader_lab/scratch/character_recovery/" +
            "zhuangfy_dian901_dynamic_carrier/unity_oracle.json";
        private const string Dian901DynamicCarrierOracleSha256 =
            "E7BB0491FF8083DD3C8694443662E9E2C2D75C3644CC1FB66B9D25C8868D67C7";
        private const string Lightning902RetailRuntimeAuditRepoPath =
            "scratch/reverse_engineering/" +
            "zhuangfy_lightning902_retail_runtime/" +
            "lightning902_retail_runtime_audit.json";
        private const string Lightning902RetailRuntimeAuditSha256 =
            "9FC0BFEF8771BE2B55CCB4EFE7F093970E0DBDBF215F4ED1C24A7B8EBDEEDA66";
        private const string EffectFollowAuditRepoPath =
            "scratch/reverse_engineering/zhuangfy_dian904_effect_follow/" +
            "effect_follow_audit.json";
        private const string EffectFollowAuditSha256 =
            "B47840D96143A31BB39F6E765AB3EB57D06A4AA8690EFD35FAD103FE0EBB0863";
        private const string Dian904ClipInRuntimeAuditRepoPath =
            "scratch/reverse_engineering/zhuangfy_dian904_clipin_runtime/" +
            "dian904_clipin_runtime.json";
        private const string Dian904ClipInRuntimeAuditSha256 =
            "2B068225F391C3BDC4959B5698333DF0C3B4312734D479C5EFEACCD921BC1784";
        private const string ActorTimelineRepoRoot =
            "scratch/animestudio/zhuangfy_gacha_actor_timeline/" +
            "full_timeline_export_json/MonoBehaviour";
        private const string ActorTimelineRepoPath =
            ActorTimelineRepoRoot +
            "/gacha_char_zhuangfy_Actor_p6C109CF8F8DE88D6.json";
        private const string ActorTimelineSha256 =
            "879E285D7596C18AFEF0FF878D04BB9ECACC36E5C60CB38FB4B7C17435F28784";
        private const string ActorLoopTrackRepoPath =
            ActorTimelineRepoRoot +
            "/Loop Track_p5F567FDA428E88D6.json";
        private const string ActorLoopTrackSha256 =
            "29F8595F1F59317993DAD500077A543921A945A452395C3087E108FBE57ACC98";
        private const string ZhuangfyManifestAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/" +
            "Zhuangfy/zhuangfy_ui_recovery_manifest.json";
        private const string Deco3GachaSampleRepoPath =
            "unity_endfield_graph_shader_lab/scratch/character_recovery/" +
            "zhuangfy_gacha_actor_animation_sources/deco3_samples/" +
            "A_Item_widget_zhuangfy_gacha.json";
        private const string Deco3GachaSampleSha256 =
            "6172A5C2CDA2378D1F76B8C2A705A423E65E0B7E112550F2E1B2D929D7418A83";
        private const long SourceEffectTransformPathId =
            3396218687284423959L;

        private const string GeneratedRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaRuntime";
        private const string AnimationRoot = GeneratedRoot + "/Animations";
        private const string ActorAnimationRoot =
            GeneratedRoot + "/ActorAnimations";
        private const string TimelineAssetPath = GeneratedRoot + "/Zhuangfy_Gacha_Recovered.playable";
        private const string ActorCameraTimelineAssetPath =
            GeneratedRoot + "/Zhuangfy_Gacha_ActorCamera_Recovered.playable";
        private const string ActorCameraClipAssetPath =
            GeneratedRoot + "/A_actor_zhuangfy_gacha_cam.asset";
        private const string AudioRoot = GeneratedRoot + "/Audio";
        private const string OverviewAudioRepoPath =
            "export_full/structured/Audio/shared/wwise/unknown/256896424.flac";
        private const string OverviewAudioSha256 =
            "E779A0F01E50C997DE3E34C15D9A9E8DB2DF46EB838AE7B04AE0C95277B618AF";
        private const string RarityAudioRepoPath =
            "export_full/structured/Audio/shared/wwise/unknown/787269389.flac";
        private const string RarityAudioSha256 =
            "3B91682C99CE79DB47803CD9F5E0C5AD741586736CE6DD086366FF10562CD346";
        private const string RuntimePrefabPath = GeneratedRoot + "/Zhuangfy_Gacha_Recovered.prefab";
        private const string CharacterPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Prefabs/Zhuangfy.prefab";
        private const string ParticlePrefabRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles/Prefabs";
        private const string ParticleMaterialRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles/Materials";
        private const string ParticleTextureRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Zhuangfy/Effects/GachaParticles/Textures";
        private const string ReportPath =
            "scratch/character_recovery/zhuangfy_gacha_runtime/unity_validation.json";

        private static readonly int[] ExpectedExcludedBindingCrcs =
            { 103164757, 955800122, 1182179166 };
        private static readonly string[] ExpectedSourceDirectChildOrder =
        {
            "Director", "Actor", "Audio", "Effect", "Light", "Others",
            "ExternalCamera", "UIPosNode", "UIPosNodePad",
        };
        private static readonly string[] ExpectedSourceHelperDirectorOrder =
            { "Actor", "Audio", "Effect", "Light", "Others" };
        private static readonly string[] ExpectedSourceUnimplementedHelperDirectors =
            { "Audio", "Light", "Others" };
        private static readonly string[] RecoveredUnimplementedHelperDirectors =
            Array.Empty<string>();
        private static readonly string[] ExpectedPartiallyRecoveredHelperDirectors =
            { "Actor non-camera tracks remain fail closed" };
        private static readonly string[] RecoveredPartiallyRecoveredHelperDirectors =
            Array.Empty<string>();
        private const string RecoveredExecutionBoundary =
            "Actor camera and three exact non-camera AnimationTracks, exact " +
            "Audio, Effect, and structural empty Light/Others; TailTick, Lua group-6 phase, and " +
            "same-versus-next rendered-frame ordering are not implemented";
        private static readonly long[] ExpectedBaofaParticleSystemPathIds =
        {
            2877823994773024023L,
            7023262706740735255L,
            -5104473644386308841L,
            8968524915615968535L,
            3284696663617744151L,
            7474712015302995223L,
            211230472171859223L,
            -8131524883884167913L,
            -5769714057691812585L,
            896655704363412759L,
            3122679953092488471L,
            359460945832619287L,
            1308144765319097623L,
            3888268013516467479L,
            3978692089213398295L,
            -7957310143760388841L,
            -2455229915935822569L,
            8864411365239794967L,
            -8152024728216687337L,
        };
        private static readonly uint[] ExpectedBaofaAuthoredSeeds =
        {
            8018u,
            8018u,
            186855651u,
            9733u,
            8874u,
            8874u,
            954211343u,
            unchecked((uint)-664248311),
            unchecked((uint)-1027481705),
            unchecked((uint)-715972267),
            unchecked((uint)-1303360878),
            unchecked((uint)-715972267),
            unchecked((uint)-1303360878),
            8874u,
            1998229770u,
            5834u,
            3531u,
            5834u,
            unchecked((uint)-1276018136),
        };

        private sealed class FollowBoneSpec
        {
            public string id;
            public string carrierName;
            public long carrierGameObjectPathId;
            public long carrierTransformPathId;
            public long actorGameObjectPathId;
            public long attachTransformPathId;
            public string exactAttachPath;
            public bool followRotation;
            public Vector3 authoredLocalPosition;
            public Quaternion authoredLocalRotation;
            public string[] children;
        }

        private sealed class ActorAnimationClipSpec
        {
            public string id;
            public string clipName;
            public string sourceJsonRepoPath;
            public string sourceJsonSha256;
            public long sourceClipPathId;
            public string sourceSampleRepoPath;
            public string sourceSampleSha256;
            public string maintainedAnimationAsset;
            public string generatedAssetName;
            public bool loop;
            public bool rebuildFromSample;
        }

        private sealed class ActorAnimationTrackSpec
        {
            public string id;
            public string trackName;
            public long sourceTrackPathId;
            public string sourceTrackRepoPath;
            public string sourceTrackSha256;
            public string bindingPath;
            public ActorAnimationClipSpec entrance;
            public long entrancePlayablePathId;
            public string entrancePlayableRepoPath;
            public string entrancePlayableSha256;
            public ActorAnimationClipSpec loop;
            public long loopPlayablePathId;
            public string loopPlayableRepoPath;
            public string loopPlayableSha256;
        }

        private static readonly ActorAnimationTrackSpec[]
            ExpectedActorAnimationTracks =
        {
            new ActorAnimationTrackSpec
            {
                id = "body",
                trackName = "Animation Track",
                sourceTrackPathId = -4159314823944697642L,
                sourceTrackRepoPath =
                    ActorTimelineRepoRoot +
                    "/Animation Track_pC647253461C288D6.json",
                sourceTrackSha256 =
                    "2B37D07F4A2B6964A7CF66D10DE2BD41211AF8E78CEBA1CE03C2647EECFECE31",
                bindingPath = "Actor",
                entrance = new ActorAnimationClipSpec
                {
                    id = "body_gacha",
                    clipName = "A_actor_zhuangfy_gacha",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "animation_clips/AnimationClip/" +
                        "A_actor_zhuangfy_gacha_pE87492C48C117993.json",
                    sourceJsonSha256 =
                        "5A977B29300BA8991BAD2C5BDAD82EED99C38D07722EBAA2B649061818DC0803",
                    sourceClipPathId = -1696569786750633581L,
                    sourceSampleRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/samples/" +
                        "A_actor_zhuangfy_gacha.json",
                    sourceSampleSha256 =
                        "5271FEE6C466D8A87A743D65C9AB9944C10E16EA9EBAB2FE7AAB070BEA3FC2D5",
                    maintainedAnimationAsset =
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Playable/Zhuangfy/Animations/" +
                        "A_actor_zhuangfy_gacha.anim",
                    generatedAssetName = "A_actor_zhuangfy_gacha",
                },
                entrancePlayablePathId = -6441353244021323562L,
                entrancePlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_pA69BB75A314C88D6.json",
                entrancePlayableSha256 =
                    "55B80868B750786B07C38DFF5BC71FA0517B950ACBB669D8F68ACF1D22461E1E",
                loop = new ActorAnimationClipSpec
                {
                    id = "body_loop",
                    clipName =
                        "A_actor_zhuangfy_ui_overview_loop_01",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "animation_clips/AnimationClip/" +
                        "A_actor_zhuangfy_ui_overview_loop_01_" +
                        "pDCA810D9F64A7993.json",
                    sourceJsonSha256 =
                        "387593A1D02D8D02232101839C1E8E73F0DC30788E5F17DEB2798CB2CE5048F7",
                    sourceClipPathId = -2546767060951991917L,
                    sourceSampleRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/samples/" +
                        "A_actor_zhuangfy_ui_overview_loop_01.json",
                    sourceSampleSha256 =
                        "3BD36A3968FB043E1221AA9F54932A40100C8C9F7F2DF533C3DF1F28F410A80E",
                    maintainedAnimationAsset =
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Playable/Zhuangfy/Animations/" +
                        "A_actor_zhuangfy_ui_overview_loop_01.anim",
                    generatedAssetName =
                        "A_actor_zhuangfy_ui_overview_loop_01",
                    loop = true,
                },
                loopPlayablePathId = 2194876182645475542L,
                loopPlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_p1E75C442588C88D6.json",
                loopPlayableSha256 =
                    "2B24EED5A1488A722E516730FA557E904259213F3F655B79240749AA1F558BED",
            },
            new ActorAnimationTrackSpec
            {
                id = "deco1",
                trackName = "Animation Track (2)",
                sourceTrackPathId = 3988779615299406038L,
                sourceTrackRepoPath =
                    ActorTimelineRepoRoot +
                    "/Animation Track (2)_p375AFDED393D88D6.json",
                sourceTrackSha256 =
                    "F6D61385803BDB727DA1F0E1EADF6AF50F923539504D2127616BF3486216C31B",
                bindingPath =
                    "Actor/RecoveredProps/chr_0030_zhuangfy_deco_1",
                entrance = new ActorAnimationClipSpec
                {
                    id = "deco1_gacha",
                    clipName = "A_item_widget_zhuangfy_gacha",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/animation_clips/AnimationClip/" +
                        "A_item_widget_zhuangfy_gacha_" +
                        "pBD1E71FCEBF210BD.json",
                    sourceJsonSha256 =
                        "6FE03AA6A0D0BFB3B9F58DF0C40841C2E93E9046243A9884CBCE251988408512",
                    sourceClipPathId = -4819289220135644995L,
                    sourceSampleRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/samples/" +
                        "A_item_widget_zhuangfy_gacha.json",
                    sourceSampleSha256 =
                        "66505367019A40953628785A3326120951E12BA33A5FCB5F2D29B249B9A1B189",
                    maintainedAnimationAsset =
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Playable/Zhuangfy/Animations/" +
                        "A_item_widget_zhuangfy_gacha.anim",
                    generatedAssetName =
                        "A_item_widget_zhuangfy_gacha_deco1",
                },
                entrancePlayablePathId = 8140063377146742998L,
                entrancePlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_p70F750837BFF88D6.json",
                entrancePlayableSha256 =
                    "743C3F80473575D58A943B57D7EF5B3BE00644B1FCD31959837F8445FC6E798B",
                loop = new ActorAnimationClipSpec
                {
                    id = "deco1_loop",
                    clipName =
                        "A_Item_widget_zhuangfy_01_ui_overview_loop_01",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/animation_clips/AnimationClip/" +
                        "A_Item_widget_zhuangfy_01_ui_overview_loop_01_" +
                        "p487CFAC7067310BD.json",
                    sourceJsonSha256 =
                        "40F6571DDDEFC45F8A408F323A53DD4EC7CE1D51EF7E93123FC0C4091DDA9504",
                    sourceClipPathId = 5223325400556572861L,
                    sourceSampleRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/samples/" +
                        "A_Item_widget_zhuangfy_01_ui_overview_loop_01.json",
                    sourceSampleSha256 =
                        "DD4967A581C5B9B3542D4AD75547E6F72F62A4F2F865F5C0F043586C08CF3BB1",
                    maintainedAnimationAsset =
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Playable/Zhuangfy/Animations/" +
                        "A_Item_widget_zhuangfy_01_ui_overview_loop_01.anim",
                    generatedAssetName =
                        "A_Item_widget_zhuangfy_01_ui_overview_loop_01",
                    loop = true,
                },
                loopPlayablePathId = 1692175339352590550L,
                loopPlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_p177BD0816FC988D6.json",
                loopPlayableSha256 =
                    "42F3AE14DF9F5D575634F14169DCCF9364F3644CD78BF0FBA48528F4EACABAA3",
            },
            new ActorAnimationTrackSpec
            {
                id = "deco3",
                trackName = "Animation Track (3)",
                sourceTrackPathId = 1566328435452643542L,
                sourceTrackRepoPath =
                    ActorTimelineRepoRoot +
                    "/Animation Track (3)_p15BCB769CCBF88D6.json",
                sourceTrackSha256 =
                    "89900D2706CBBF4BCE95E5C2A03F59C1ED865C071521A3450CD038C211363D4E",
                bindingPath =
                    "Actor/RecoveredProps/chr_0030_zhuangfy_deco_3",
                entrance = new ActorAnimationClipSpec
                {
                    id = "deco3_gacha",
                    clipName = "A_Item_widget_zhuangfy_gacha",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/animation_clips/AnimationClip/" +
                        "A_Item_widget_zhuangfy_gacha_" +
                        "pCD4C948A61BD8D78.json",
                    sourceJsonSha256 =
                        "3B21C534D5EB8893EF22025501E8CE71FABE0DF00DB4ECDD43F93701E0B8A7C4",
                    sourceClipPathId = -3653381875638104712L,
                    sourceSampleRepoPath = Deco3GachaSampleRepoPath,
                    sourceSampleSha256 = Deco3GachaSampleSha256,
                    generatedAssetName =
                        "A_Item_widget_zhuangfy_gacha_deco3",
                    rebuildFromSample = true,
                },
                entrancePlayablePathId = -7392696245755279146L,
                entrancePlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_p9967DDEEC36488D6.json",
                entrancePlayableSha256 =
                    "119D9EFD582E5FE979E6001BB73870D4E1DED331726707F0D2B29C59D871061B",
                loop = new ActorAnimationClipSpec
                {
                    id = "deco3_loop",
                    clipName =
                        "A_Item_widget_zhuangfy_03_ui_overview_loop_01",
                    sourceJsonRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/animation_clips/AnimationClip/" +
                        "A_Item_widget_zhuangfy_03_ui_overview_loop_01_" +
                        "p2DD960767C3D8D78.json",
                    sourceJsonSha256 =
                        "0985CEAE9C43FAE52318F4B1BDE57C6949FFCD65A87ED13EE8218C1411F63182",
                    sourceClipPathId = 3303777863659785592L,
                    sourceSampleRepoPath =
                        "scratch/character_ui_import/characters/" +
                        "chr_0030_zhuangfy/animation_scopes/all-ui/" +
                        "item_widgets/samples/" +
                        "A_Item_widget_zhuangfy_03_ui_overview_loop_01.json",
                    sourceSampleSha256 =
                        "13F9B788E698E2CA6A6C5CBC8871BD2007E5A2D380525C4ACC12FF566C4E9194",
                    maintainedAnimationAsset =
                        "Assets/EndfieldGraphShaderLab/Generated/Characters/" +
                        "Playable/Zhuangfy/Animations/" +
                        "A_Item_widget_zhuangfy_03_ui_overview_loop_01.anim",
                    generatedAssetName =
                        "A_Item_widget_zhuangfy_03_ui_overview_loop_01",
                    loop = true,
                },
                loopPlayablePathId = 5995319719315998934L,
                loopPlayableRepoPath =
                    ActorTimelineRepoRoot +
                    "/AnimationPlayableAsset_p5333A78528B988D6.json",
                loopPlayableSha256 =
                    "97FF9313AAD7DAC3678139F14FC8A00A924CAC326067DAD5F47381FEB2524436",
            },
        };

        private static readonly FollowBoneSpec[] ExpectedFollowBoneSpecs =
        {
            new FollowBoneSpec
            {
                id = "zhuangfy_joint",
                carrierName = "Zhuangfy_F_a_01_jnt",
                carrierGameObjectPathId = 8451546680973110551L,
                carrierTransformPathId = -913870857347420905L,
                actorGameObjectPathId = 5744346418405223703L,
                attachTransformPathId = 7624183373736881431L,
                exactAttachPath =
                    "Actor/RecoveredProps/chr_0030_zhuangfy_deco_1/" +
                    "Root/Zhuangfy_F_a_01_jnt",
                followRotation = false,
                authoredLocalPosition =
                    new Vector3(-0.19478482f, 1.3405979f, 0.37080446f),
                authoredLocalRotation =
                    new Quaternion(
                        0.09331851f,
                        0.5971812f,
                        0.20227137f,
                        0.7705534f),
                children = new[]
                {
                    "P_fxui_zhuangfy_ui_overview_start_01_trail01",
                    "P_fxui_zhuangfy_ui_overview_start_01_jianqiang",
                },
            },
            new FollowBoneSpec
            {
                id = "right_finger_tip",
                carrierName = "Bip001_R_Finger2Nub",
                carrierGameObjectPathId = -746755823431668457L,
                carrierTransformPathId = -5184122023984255721L,
                actorGameObjectPathId = -5190539563904029417L,
                attachTransformPathId = -3000696323737604841L,
                exactAttachPath =
                    "Actor/Root/Bip001/Bip001_Pelvis/Bip001_Spine/" +
                    "Bip001_Spine1/Bip001_Spine2/Bip001_R_Clavicle/" +
                    "Bip001_R_UpperArm/Bip001_R_Forearm/" +
                    "Bip001_R_Hand/Bip001_R_Finger2/" +
                    "Bip001_R_Finger21/Bip001_R_Finger22/" +
                    "Bip001_R_Finger2Nub",
                followRotation = false,
                authoredLocalPosition =
                    new Vector3(0.48810318f, 1.4320793f, 0.08901151f),
                authoredLocalRotation = Quaternion.identity,
                children = new[]
                {
                    "P_fxui_zhuangfy_ui_overview_start_01_finger_lightning",
                },
            },
            new FollowBoneSpec
            {
                id = "external_camera",
                carrierName = "bone",
                carrierGameObjectPathId = 1125235529233902871L,
                carrierTransformPathId = 3112218374680456471L,
                actorGameObjectPathId = -1951525567929471721L,
                attachTransformPathId = -6397228865359794921L,
                exactAttachPath = "ExternalCamera",
                followRotation = true,
                authoredLocalPosition =
                    new Vector3(-0.08372789f, 0.9446196f, 2.0960028f),
                authoredLocalRotation =
                    new Quaternion(
                        -0.1044024f,
                        -0.992523f,
                        -0.062786184f,
                        0.0074885264f),
                children = new[]
                {
                    "P_fxui_gacha_char_guangxiao_rarity6effect_01",
                },
            },
        };

        private static readonly string[] ExpectedDirectEffectParticleChildren =
        {
            "P_fxui_zhuangfy_ui_overview_start_01_01",
            "P_fxui_zhuangfy_ui_overview_start_01_baofa",
        };

        [Serializable]
        private sealed class AffineSnapshot
        {
            public string hierarchy;
            public float[] localPosition;
            public float[] localRotation;
            public float[] localScale;
            public float[] worldPosition;
            public float[] worldRotation;
            public float[] localToWorldRowMajor;
            public float[] worldToLocalRowMajor;
        }

        [Serializable]
        private sealed class ActorZeroAffineOracle
        {
            public string authority;
            public double actorTimelineTime;
            public double effectTimelineTime;
            public int dian904ControlTrackOrder;
            public string dian904ControlTrackName;
            public string dian904ControlClipName;
            public long dian904ControlTrackSourcePathId;
            public long dian904ControlPlayableSourcePathId;
            public long dian904ControlTargetSourceGameObjectPathId;
            public string dian904ControlTargetSourceHierarchy;
            public double dian904ControlClipStart;
            public double dian904ControlClipIn;
            public double dian904ControlClipTimeScale;
            public double dian904ControlLocalTime;
            public float dian904ControlLocalTimeFloat32;
            public string dian904ControlLocalTimeFloat32Bits;
            public long dian904ParticleSystemSourcePathId;
            public long dian904RendererSourcePathId;
            public string dian904ParticleSourceHierarchy;
            public string dian904ClipInRuntimeAuditSha256;
            public string jointSourceSampleSha256;
            public int jointSourceTrackIndex;
            public float[] expectedJointLocalPosition;
            public float[] expectedJointLocalRotation;
            public float[] expectedJointLocalScale;
            public AffineSnapshot runtimeRoot;
            public AffineSnapshot actor;
            public AffineSnapshot deco1;
            public AffineSnapshot joint;
            public AffineSnapshot effect;
            public AffineSnapshot carrier;
            public AffineSnapshot dian904EffectRoot;
            public AffineSnapshot dian904Renderer;
            public bool jointSampleBitsExact;
            public bool carrierWorldPositionExact;
            public bool dian904ChainResolved;
            public bool dian904ControlClipExact;
            public bool dian904ControlBindingExact;
            public bool dian904ParticleDescendantOfControlTarget;
            public bool dian904ClipInSchedulerAuditPinned;
            public bool dian904SameTimeLiveParticleAffineClosed;
            public bool visualAdmission;
        }

        [Serializable]
        private sealed class ValidationReport
        {
            public string schema;
            public string unityVersion;
            public string graphicsDeviceType;
            public string payloadSha256;
            public string timelineContractSha256;
            public string particleContractSha256;
            public string nativeContractSha256;
            public string startOrderContractSha256;
            public string timelineParticleHostAuditSha256;
            public string lightning902RetailRuntimeAuditSha256;
            public string effectFollowAuditSha256;
            public string dian904ClipInRuntimeAuditSha256;
            public string prefabAsset;
            public string timelineAsset;
            public string actorCameraTimelineAsset;
            public string actorCameraClipAsset;
            public string actorCameraReportSha256;
            public string actorCameraFixtureSha256;
            public string actorTimelineSha256;
            public string actorLoopTrackSha256;
            public int trackCount;
            public int controlTrackCount;
            public int animationTrackCount;
            public int entityVFXTrackCount;
            public int generatedAnimationClipCount;
            public int actorAnimationTrackCount;
            public int actorAnimationClipCount;
            public int exactEligibleRendererCount;
            public int additiveHandlerCount;
            public int dissolveHandlerCount;
            public int sourceZeroStartDefinitionCount;
            public int staticRarityMeshRendererCount;
            public int baofaControllableRootCount;
            public int fingerLightningControllableRootCount;
            public int vfxFollowBoneCarrierCount;
            public int[] failClosedAnimationBindingCRCs;
            public string rendererSelectionBoundary;
            public string shaderExecutionBoundary;
            public string baofaTimelineOwnershipBoundary;
            public string fingerLightningTimelineOwnershipBoundary;
            public bool sourceBaofaUpdateParticle;
            public bool recoveredBaofaUpdateParticle;
            public bool baofaTimelineHostPassed;
            public bool sourceFingerLightningUpdateParticle;
            public bool recoveredFingerLightningUpdateParticle;
            public bool fingerLightningTimelineHostPassed;
            public bool vfxFollowBoneSourcePartitionPassed;
            public bool vfxFollowBoneRuntimePassed;
            public bool vfxFollowBoneInitialAuthoredTransformPassed;
            public bool vfxFollowBoneWorldPositionCopyPassed;
            public bool vfxFollowBoneRotationBranchPassed;
            public bool vfxFollowBoneDeterministicPassed;
            public bool vfxFollowBoneMissingBindingFailClosedPassed;
            public bool vfxFollowBoneUnrelatedRootsUnmovedPassed;
            public bool strictWeightGatePassed;
            public bool entityVFXPPtrJoinPassed;
            public bool exactLodGroupPassed;
            public bool parentMetadataPassed;
            public bool initialEvaluatePassed;
            public bool scaledStartGatePassed;
            public bool effectOrdinalMetadataPassed;
            public bool exactRecoveredDirectorSetPassed;
            public bool actorCameraSourceGatePassed;
            public bool actorCameraDeclaredPairPassed;
            public bool actorAnimationSourceGatePassed;
            public bool actorAnimationBindingPassed;
            public bool actorAnimationDeclaredZeroPassed;
            public bool dian904SameTimeLiveParticleAffinePassed;
            public bool externalCameraIsolationPassed;
            public bool additiveLifecyclePassed;
            public bool additiveOverlapCapPassed;
            public bool originalMaterialRestorationPassed;
            public bool dissolveMaterialLifecyclePassed;
            public bool dissolveShadowTimingPassed;
            public ActorZeroAffineOracle actorZeroAffineOracle;
            public bool visualAdmission;
            public bool passed;
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Zhuangfy Gacha Timeline Runtime (Source Closed)")]
        public static void BuildAndValidate()
        {
            // The EntityVFX runtime consumes the generated playable prefab.
            // Rebuild only Zhuangfy from the current source-gated manifest so
            // preserved widget LOD rows and the exact LODGroup cannot be stale.
            EndfieldManifestCharacterSetup.RebuildZhuangfyPrefabForGachaRuntime();
            // Rebuild the strict particle prefabs first because the runtime
            // consumes their exact source hierarchies and rarity mesh bindings.
            EndfieldZhuangfyParticleEffectImporter.BuildAndValidate();
            Dictionary<string, object> payload = LoadPayload();
            Dictionary<string, object> timelineContract = LoadContract(TimelineContractPath, ExpectedTimelineSha256);
            Dictionary<string, object> particleContract = LoadContract(ParticleContractPath, ExpectedParticleSha256);
            Dictionary<string, AnimationClip> clips = BuildAnimationClips(payload);
            Dictionary<string, AnimationClip> actorAnimationClips =
                BuildActorAnimationClips();
            EndfieldRecoveredZhuangfyGachaCameraClip actorCameraClip =
                BuildActorCameraClip(payload);
            AudioClip overviewAudio = ImportRecoveredAudioClip(
                OverviewAudioRepoPath,
                AudioRoot + "/256896424.flac",
                OverviewAudioSha256);
            AudioClip rarityAudio = ImportRecoveredAudioClip(
                RarityAudioRepoPath,
                AudioRoot + "/787269389.flac",
                RarityAudioSha256);
            BuildRuntime(
                payload,
                timelineContract,
                particleContract,
                clips,
                actorAnimationClips,
                actorCameraClip,
                overviewAudio,
                rarityAudio);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ValidateGenerated(payload, timelineContract, particleContract, true);
            // Replacing a generated prefab from a fresh hierarchy can change
            // its internal local file IDs. Rebind and validate the saved
            // resident scene in the same transaction so Zhuang never reverts
            // to a legacy inactive root or loses its horizontal position.
            EndfieldManifestCharacterSetup.UpgradeSharedViewerToAllSourceProfiles();
            EndfieldManifestCharacterSetup.ValidateResidentCharacterLineupCommandLine();
        }

        public static void ValidateBatch()
        {
            Dictionary<string, object> payload = LoadPayload();
            Dictionary<string, object> timelineContract = LoadContract(TimelineContractPath, ExpectedTimelineSha256);
            Dictionary<string, object> particleContract = LoadContract(ParticleContractPath, ExpectedParticleSha256);
            ValidateGenerated(payload, timelineContract, particleContract, true);
        }

        private static Dictionary<string, object> LoadPayload()
        {
            Require(Sha256(AssetPathToAbsolute(PayloadPath)) == ExpectedPayloadSha256,
                "Zhuangfy runtime payload hash changed; rebuild/review its source joins");
            Dictionary<string, object> payload = LoadJson(AssetPathToAbsolute(PayloadPath));
            Require(Str(payload, "schema") == "endfield.zhuangfy-gacha-runtime-payload.v3",
                "Unexpected Zhuangfy runtime payload schema");
            Require(Str(payload, "timelineContractSha256") == ExpectedTimelineSha256,
                "Payload Timeline contract gate changed");
            Require(Str(payload, "particleContractSha256") == ExpectedParticleSha256,
                "Payload particle contract gate changed");
            Require(Str(payload, "nativeContractSha256") == ExpectedNativeSha256,
                "Payload native contract gate changed");
            Require(Str(payload, "startOrderContractSha256") == ExpectedStartOrderSha256,
                "Payload start-order contract gate changed");
            Require(Math.Abs(Double(payload, "nativePlayableMinWeight") -
                EndfieldRecoveredZhuangfyGachaRuntime.NativePlayableMinWeight) < 1.0e-10,
                "Native playable threshold changed");
            Require(Int(payload, "entityVFXRendererMask") == -1 &&
                Str(payload, "entityVFXRendererMaskName") == "All",
                "EntityVFX renderer-mask contract changed");
            Require(IntList(payload["excludedAnimationBindingCRCs"])
                .SequenceEqual(ExpectedExcludedBindingCrcs),
                "Fail-closed animation binding set changed");

            string nativeAbsolute = RepoRelativeToAbsolute(NativeContractRepoPath);
            Require(File.Exists(nativeAbsolute) && Sha256(nativeAbsolute) == ExpectedNativeSha256,
                "Current native contract does not match the runtime gate");
            string startOrderAbsolute = RepoRelativeToAbsolute(StartOrderContractRepoPath);
            Require(File.Exists(startOrderAbsolute) &&
                Sha256(startOrderAbsolute) == ExpectedStartOrderSha256,
                "Current start-order contract does not match the runtime gate");
            string timelineHostAuditAbsolute =
                RepoRelativeToAbsolute(TimelineParticleHostAuditRepoPath);
            Require(
                File.Exists(timelineHostAuditAbsolute) &&
                Sha256(timelineHostAuditAbsolute) ==
                    TimelineParticleHostAuditSha256,
                "Current Timeline particle-host audit does not match " +
                "the runtime gate");
            string dian901AutomaticAuditAbsolute =
                RepoRelativeToAbsolute(
                    Dian901AutomaticRuntimeAuditRepoPath);
            Require(
                File.Exists(dian901AutomaticAuditAbsolute) &&
                Sha256(dian901AutomaticAuditAbsolute) ==
                    Dian901AutomaticRuntimeAuditSha256,
                "Current Dian901 automatic-runtime audit does not match " +
                "the runtime gate");
            string dian901Order4OwnerAuditAbsolute =
                RepoRelativeToAbsolute(
                    Dian901Order4AutomaticOwnerAuditRepoPath);
            Require(
                File.Exists(dian901Order4OwnerAuditAbsolute) &&
                Sha256(dian901Order4OwnerAuditAbsolute) ==
                    Dian901Order4AutomaticOwnerAuditSha256,
                "Current Dian901 order-4 owner audit does not match " +
                "the runtime gate");
            string dian901DynamicCarrierOracleAbsolute =
                RepoRelativeToAbsolute(
                    Dian901DynamicCarrierOracleRepoPath);
            Require(
                File.Exists(dian901DynamicCarrierOracleAbsolute) &&
                Sha256(dian901DynamicCarrierOracleAbsolute) ==
                    Dian901DynamicCarrierOracleSha256,
                "Current Dian901 dynamic-carrier Unity oracle does not " +
                "match the runtime gate");
            string lightning902AuditAbsolute =
                RepoRelativeToAbsolute(
                    Lightning902RetailRuntimeAuditRepoPath);
            Require(
                File.Exists(lightning902AuditAbsolute) &&
                Sha256(lightning902AuditAbsolute) ==
                    Lightning902RetailRuntimeAuditSha256,
                "Current Lightning902 retail-runtime audit does not " +
                "match the runtime gate");
            LoadEffectFollowAudit();
            LoadDian904ClipInRuntimeAudit();
            ValidateStartOrderPayload(payload);
            return payload;
        }

        private static Dictionary<string, object>
            LoadDian904ClipInRuntimeAudit()
        {
            string absolute =
                RepoRelativeToAbsolute(Dian904ClipInRuntimeAuditRepoPath);
            Require(
                File.Exists(absolute) &&
                Sha256(absolute) == Dian904ClipInRuntimeAuditSha256,
                "Current Dian904 clip-in runtime audit does not match " +
                "the runtime gate");
            Dictionary<string, object> audit = LoadJson(absolute);
            Dictionary<string, object> scope = Dict(audit["scope"]);
            Dictionary<string, object> clipInFloat32 =
                Dict(scope["clipInFloat32"]);
            Dictionary<string, object> serialized =
                Dict(audit["serializedContract"]);
            Require(
                Str(audit, "schema") ==
                    "endfield.zhuangfy-dian904-clipin-runtime.v1" &&
                Str(audit, "status") ==
                    "clipin_scheduler_and_initial_state_closed" &&
                Str(scope, "material") == "M_fx_ui_dian_904" &&
                Approximately(
                    Double(scope, "clipInSecondsAuthored"),
                    0.48333333333333334) &&
                Approximately(
                    Double(clipInFloat32, "value"),
                    (double)0.4833333194255829f) &&
                Str(clipInFloat32, "bits") == "0x3EF77777" &&
                Long(serialized, "particleSystemPathId") ==
                    -463413735443550953L &&
                !Bool(scope, "endfieldLaunchedOrAttached") &&
                !Bool(scope, "publicUnityStateUsedAsOracle") &&
                !Bool(scope, "visualAdmission"),
                "Dian904 clip-in runtime audit boundary changed");
            return audit;
        }

        private static Dictionary<string, object> LoadEffectFollowAudit()
        {
            string absolute =
                RepoRelativeToAbsolute(EffectFollowAuditRepoPath);
            Require(
                File.Exists(absolute) &&
                Sha256(absolute) == EffectFollowAuditSha256,
                "Current VFXFollowBoneTool audit does not match the " +
                "runtime gate");
            Dictionary<string, object> audit = LoadJson(absolute);
            Require(
                Str(audit, "schema") ==
                    "endfield.zhuangfy-gacha-vfx-follow-bone-audit.v1" &&
                Bool(audit, "unityPatchJustified") &&
                !Bool(audit, "visualAdmission"),
                "VFXFollowBoneTool audit boundary changed");
            Dictionary<string, object> inputs = Dict(audit["inputs"]);
            Require(
                Str(Dict(inputs["gameAssembly"]), "sha256") ==
                    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce" &&
                Str(Dict(inputs["globalMetadata"]), "sha256") ==
                    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e" &&
                Str(Dict(inputs["particleInventory"]), "sha256")
                    .Equals(
                        ExpectedParticleSha256,
                        StringComparison.OrdinalIgnoreCase) &&
                List(Dict(inputs["ifixAudit"])["relevantTargets"]).Count == 0,
                "VFXFollowBoneTool installed binary/input gate changed");
            Dictionary<string, object>[] nativeMethods =
                List(audit["nativeMethods"]).Cast<object>()
                    .Select(Dict).ToArray();
            Require(
                nativeMethods.Length == 2 &&
                nativeMethods.Any(value =>
                    Str(value, "name") ==
                        "VFXFollowBoneTool.UpdatePosition" &&
                    Str(value, "sha256") ==
                        "805ab49f9e42bef937a3fe5cf1f2e769c5b755105666873fe13ad94210f5ae93") &&
                nativeMethods.Any(value =>
                    Str(value, "name") ==
                        "CutsceneRootComponent.UpdateAllVFXFollowBoneTools" &&
                    Str(value, "sha256") ==
                        "c7d5775e44ad60c673b7fb890edb55b5dc7cf7fa56f4df93cbcdc7d9dfba3dc0"),
                "VFXFollowBoneTool native method gate changed");
            Require(
                StringList(audit["directEffectChildren"])
                    .SequenceEqual(ExpectedDirectEffectParticleChildren),
                "VFXFollowBoneTool direct Effect child set changed");
            Dictionary<string, object>[] followers =
                List(audit["followers"]).Cast<object>()
                    .Select(Dict).ToArray();
            Require(
                followers.Length == ExpectedFollowBoneSpecs.Length,
                "VFXFollowBoneTool source follower count changed");
            foreach (FollowBoneSpec spec in ExpectedFollowBoneSpecs)
            {
                Dictionary<string, object> row = followers.Single(value =>
                    Str(value, "id") == spec.id);
                float[] position = FloatList(
                    row["authoredLocalPosition"]);
                float[] rotation = FloatList(
                    row["authoredLocalRotation"]);
                Require(
                    Long(row, "carrierGameObjectPathId") ==
                        spec.carrierGameObjectPathId &&
                    Long(row, "carrierTransformPathId") ==
                        spec.carrierTransformPathId &&
                    Long(row, "actorGameObjectPathId") ==
                        spec.actorGameObjectPathId &&
                    Long(row, "attachTransformPathId") ==
                        spec.attachTransformPathId &&
                    Bool(row, "followRotation") ==
                        spec.followRotation &&
                    StringList(row["children"])
                        .SequenceEqual(spec.children) &&
                    position.Length == 3 &&
                    rotation.Length == 4 &&
                    FloatBits(position[0]) ==
                        FloatBits(spec.authoredLocalPosition.x) &&
                    FloatBits(position[1]) ==
                        FloatBits(spec.authoredLocalPosition.y) &&
                    FloatBits(position[2]) ==
                        FloatBits(spec.authoredLocalPosition.z) &&
                    FloatBits(rotation[0]) ==
                        FloatBits(spec.authoredLocalRotation.x) &&
                    FloatBits(rotation[1]) ==
                        FloatBits(spec.authoredLocalRotation.y) &&
                    FloatBits(rotation[2]) ==
                        FloatBits(spec.authoredLocalRotation.z) &&
                    FloatBits(rotation[3]) ==
                        FloatBits(spec.authoredLocalRotation.w),
                    "VFXFollowBoneTool source row changed: " + spec.id);
            }
            return audit;
        }

        private static void ValidateStartOrderPayload(Dictionary<string, object> payload)
        {
            Dictionary<string, object> startOrder = Dict(payload["startOrder"]);
            Dictionary<string, object> parent = Dict(startOrder["sourceOuterParent"]);
            Dictionary<string, object> recoveredDirector = Dict(startOrder["recoveredDirector"]);
            Dictionary<string, object> recoveredActorCameraDirector =
                Dict(startOrder["recoveredActorCameraDirector"]);
            Dictionary<string, object> initialSample = Dict(startOrder["initialSample"]);
            Dictionary<string, object> delayedPlay = Dict(startOrder["delayedPlay"]);

            Require(Int(parent, "luaReferenceIndex") == 8 &&
                Str(parent, "hierarchy") == "GachaRoom/TimelineRoot" &&
                Long(parent, "gameObjectPathId") == 964036993266462176L &&
                Long(parent, "transformPathId") == 2033347196788583904L &&
                Bool(parent, "serializedActive") &&
                Str(parent, "serializedLocalTransform") == "identity" &&
                Int(parent, "childCount") == 0,
                "Recovered TimelineRoot parent metadata changed");
            Require(!Bool(startOrder, "instantiateInWorldSpace"),
                "Recovered TimelineRoot must instantiate in local space");
            Require(StringList(startOrder["sourceDirectChildOrder"])
                    .SequenceEqual(ExpectedSourceDirectChildOrder) &&
                StringList(startOrder["sourceHelperDirectorOrder"])
                    .SequenceEqual(ExpectedSourceHelperDirectorOrder),
                "Recovered helper/direct-child order changed");
            Require(Str(recoveredDirector, "role") == "Effect" &&
                Int(recoveredDirector, "sourceOrdinal") == 2 &&
                Long(recoveredDirector, "sourcePathId") == 3160965858571562263L &&
                Str(recoveredDirector, "generatedOwner") == "Effect",
                "Recovered Effect director identity/ordinal changed");
            Require(Str(recoveredActorCameraDirector, "role") == "Actor" &&
                Int(recoveredActorCameraDirector, "sourceOrdinal") == 0 &&
                Long(recoveredActorCameraDirector, "sourcePathId") ==
                    -410748005131375337L &&
                Str(recoveredActorCameraDirector, "generatedOwner") == "Actor" &&
                Str(recoveredActorCameraDirector, "scope") ==
                    "A_actor_zhuangfy_gacha_cam track only",
                "Recovered Actor camera director identity/scope changed");
            Require(StringList(startOrder["unimplementedHelperDirectors"])
                    .SequenceEqual(ExpectedSourceUnimplementedHelperDirectors),
                "Fail-closed helper-director set changed");
            Require(StringList(startOrder["partiallyRecoveredHelperDirectors"])
                    .SequenceEqual(ExpectedPartiallyRecoveredHelperDirectors),
                "Partial helper-director boundary changed");
            Require(Approximately(Double(initialSample, "time"), 0.0) &&
                StringList(initialSample["effectOperations"])
                    .SequenceEqual(new[] { "Stop", "time=0", "Evaluate" }),
                "Recovered initial Effect sample order changed");
            Require(Approximately(Double(delayedPlay, "delaySeconds"), 0.25) &&
                Str(delayedPlay, "clock") == "scaled Unity Time.time" &&
                Str(delayedPlay, "sourceEligibility") ==
                    "first TimerManager Lua Tick whose Time.time is greater than or equal to the stored trigger time" &&
                Str(delayedPlay, "recoveredEligibility") ==
                    "first recovered driver Update with Time.time >= deadline" &&
                StringList(delayedPlay["effectOperations"])
                    .SequenceEqual(new[] { "RebuildGraph", "time=0", "Evaluate", "Play" }),
                "Recovered scaled Effect play gate changed");
            Require(Str(startOrder, "generatedExecutionBoundary") ==
                "Actor camera track then Effect; Actor non-camera tracks, Audio, Light, Others, TailTick, Lua group-6 phase, and same-versus-next rendered-frame ordering are not implemented",
                "Recovered Actor-camera/Effect execution boundary changed");
        }

        private static Dictionary<string, object> LoadContract(string assetPath, string expectedHash)
        {
            string absolute = AssetPathToAbsolute(assetPath);
            Require(File.Exists(absolute) && Sha256(absolute) == expectedHash,
                "Contract hash changed: " + assetPath);
            return LoadJson(absolute);
        }

        private static Dictionary<string, AnimationClip> BuildAnimationClips(
            Dictionary<string, object> payload)
        {
            EnsureFolder(GeneratedRoot);
            EnsureFolder(AnimationRoot);
            var result = new Dictionary<string, AnimationClip>(StringComparer.Ordinal);
            foreach (object clipObject in List(payload["clips"]))
            {
                Dictionary<string, object> clipRecord = Dict(clipObject);
                string name = Str(clipRecord, "name");
                if (clipRecord.TryGetValue("existingAnimationAsset", out object existingObject))
                {
                    AnimationClip existing = AssetDatabase.LoadAssetAtPath<AnimationClip>(Str(existingObject));
                    Require(existing != null, "Missing maintained animation clip " + Str(existingObject));
                    // Character manifests use legacy Animation clips for the
                    // Animation component. Timeline rejects that flag, so keep
                    // the exact curves in a separate non-legacy asset.
                    string timelineAnimationPath = AnimationRoot + "/" + Safe(name) + ".anim";
                    AnimationClip timelineClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(timelineAnimationPath);
                    if (timelineClip == null)
                    {
                        timelineClip = new AnimationClip();
                        AssetDatabase.CreateAsset(timelineClip, timelineAnimationPath);
                    }
                    EditorUtility.CopySerialized(existing, timelineClip);
                    timelineClip.name = name;
                    timelineClip.legacy = false;
                    EditorUtility.SetDirty(timelineClip);
                    result.Add(name, timelineClip);
                    continue;
                }

                var clip = new AnimationClip
                {
                    name = name,
                    frameRate = Float(clipRecord, "sampleRate"),
                    legacy = false,
                    wrapMode = WrapMode.Once,
                };
                IList frames = List(clipRecord["frames"]);
                foreach (object bindingObject in List(clipRecord["bindings"]))
                    AddTransformBinding(clip, Dict(bindingObject), frames);
                foreach (object curveObject in List(clipRecord["eulerCurves"]))
                    AddFloatCurve(clip, Dict(curveObject), typeof(Transform));
                foreach (object curveObject in List(clipRecord["materialFloatCurves"]))
                {
                    Dictionary<string, object> curve = Dict(curveObject);
                    Type rendererType = RendererType(Str(curve, "rendererType"));
                    AddFloatCurve(clip, curve, rendererType);
                }
                clip.EnsureQuaternionContinuity();

                string path = AnimationRoot + "/" + Safe(name) + ".anim";
                AnimationClip existingClip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                if (existingClip == null)
                {
                    AssetDatabase.CreateAsset(clip, path);
                    existingClip = clip;
                }
                else
                {
                    EditorUtility.CopySerialized(clip, existingClip);
                    existingClip.name = name;
                    EditorUtility.SetDirty(existingClip);
                    UnityEngine.Object.DestroyImmediate(clip);
                }
                result.Add(name, existingClip);
            }
            Require(result.Count == 4, "Expected four exact AnimationClip identities");
            AssetDatabase.SaveAssets();
            bool slimmed = false;
            foreach (AnimationClip saved in result.Values)
                slimmed |= EndfieldAnimationClipSlimmer.StripEditorCurves(saved);
            if (slimmed)
                AssetDatabase.SaveAssets();
            return result;
        }

        private static Dictionary<string, AnimationClip>
            BuildActorAnimationClips()
        {
            ValidateActorTimelineSources();
            EnsureFolder(ActorAnimationRoot);
            Dictionary<string, object> manifest =
                LoadJson(AssetPathToAbsolute(ZhuangfyManifestAssetPath));
            IList manifestClips = List(manifest["clips"]);
            var result = new Dictionary<string, AnimationClip>(
                StringComparer.Ordinal);
            foreach (ActorAnimationTrackSpec track in
                ExpectedActorAnimationTracks)
            {
                BuildActorAnimationClip(
                    track,
                    track.entrance,
                    manifestClips,
                    result);
                BuildActorAnimationClip(
                    track,
                    track.loop,
                    manifestClips,
                    result);
            }
            Require(
                result.Count == 6,
                "Expected six exact Actor AnimationClip identities");
            AssetDatabase.SaveAssets();
            bool slimmed = false;
            foreach (AnimationClip clip in result.Values)
                slimmed |=
                    EndfieldAnimationClipSlimmer.StripEditorCurves(clip);
            if (slimmed)
                AssetDatabase.SaveAssets();
            return result;
        }

        private static void BuildActorAnimationClip(
            ActorAnimationTrackSpec track,
            ActorAnimationClipSpec spec,
            IList manifestClips,
            Dictionary<string, AnimationClip> result)
        {
            string sourceJson =
                RepoRelativeToAbsolute(spec.sourceJsonRepoPath);
            string sampleJson =
                RepoRelativeToAbsolute(spec.sourceSampleRepoPath);
            Require(
                File.Exists(sourceJson) &&
                Sha256(sourceJson) == spec.sourceJsonSha256 &&
                File.Exists(sampleJson) &&
                Sha256(sampleJson) == spec.sourceSampleSha256,
                "Actor clip source/sample hash changed: " + spec.id);
            Require(
                Path.GetFileNameWithoutExtension(sourceJson).EndsWith(
                    "_p" + unchecked((ulong)spec.sourceClipPathId)
                        .ToString("X16", CultureInfo.InvariantCulture),
                    StringComparison.OrdinalIgnoreCase),
                "Actor clip source filename no longer pins PathID: " +
                spec.id);
            Dictionary<string, object> source = LoadJson(sourceJson);
            Dictionary<string, object> sample = LoadJson(sampleJson);
            double expectedDuration = spec.loop
                ? 3.3333333333333335
                : 10.7;
            Require(
                Str(source, "m_Name") == spec.clipName &&
                !Bool(source, "m_Legacy") &&
                Approximately(Double(source, "m_SampleRate"), 60.0) &&
                Approximately(
                    Double(Dict(source["m_MuscleClip"]), "m_StopTime"),
                    spec.loop ? 3.333335 : 10.700001) &&
                Bool(sample, "ok") &&
                Bool(sample, "hash_ok") &&
                Str(sample, "clip_name") == spec.clipName &&
                Str(sample, "buffer_name") == "TransformBufferData" &&
                Approximately(Double(sample, "sample_rate"), 60.0) &&
                Approximately(Double(sample, "duration"), expectedDuration),
                "Actor clip source/sample semantics changed: " + spec.id);

            string mappingName =
                spec.id == "deco3_gacha"
                    ? "A_Item_widget_zhuangfy_03_ui_overview_loop_01"
                    : spec.clipName;
            Dictionary<string, object>[] mappingMatches =
                manifestClips.Cast<object>().Select(Dict)
                    .Where(value =>
                        Str(value, "name") == mappingName)
                    .ToArray();
            Require(
                mappingMatches.Length == 1,
                "Actor clip mapping record is not unique: " + spec.id);
            Dictionary<string, object> mapping = mappingMatches[0];
            IList bones = List(mapping["bones"]);
            IList frames = List(sample["frames"]);
            Require(
                frames.Count == Int(sample, "num_samples") &&
                bones.Count == Int(sample, "num_tracks") &&
                bones.Cast<object>().Select(Dict)
                    .Select(value => Int(value, "track_index"))
                    .OrderBy(value => value)
                    .SequenceEqual(Enumerable.Range(0, bones.Count)),
                "Actor clip decoded track mapping changed: " + spec.id);

            var generated = new AnimationClip
            {
                name = spec.generatedAssetName,
                frameRate = 60.0f,
                legacy = false,
                wrapMode = WrapMode.Once,
            };
            string actorRelativeBinding =
                track.bindingPath == "Actor"
                    ? string.Empty
                    : track.bindingPath.Substring("Actor/".Length);
            foreach (object boneObject in bones)
            {
                Dictionary<string, object> bone = Dict(boneObject);
                string path = Str(bone, "path");
                if (actorRelativeBinding.Length > 0)
                {
                    Require(
                        path == actorRelativeBinding ||
                        path.StartsWith(
                            actorRelativeBinding + "/",
                            StringComparison.Ordinal),
                        "Actor clip mapping escaped its exact binding: " +
                        spec.id + " " + path);
                    path = path.Length == actorRelativeBinding.Length
                        ? string.Empty
                        : path.Substring(
                            actorRelativeBinding.Length + 1);
                }
                AddActorTransformCurves(
                    generated,
                    path,
                    Int(bone, "track_index"),
                    frames,
                    Bool(bone, "pos_animated"),
                    Bool(bone, "rot_animated"),
                    Bool(bone, "scale_animated"));
            }
            generated.EnsureQuaternionContinuity();
            AnimationClipSettings settings =
                AnimationUtility.GetAnimationClipSettings(generated);
            settings.loopTime = spec.loop;
            settings.loopBlend = false;
            AnimationUtility.SetAnimationClipSettings(generated, settings);

            string assetPath =
                ActorAnimationRoot + "/" +
                Safe(spec.generatedAssetName) + ".anim";
            AnimationClip existing =
                AssetDatabase.LoadAssetAtPath<AnimationClip>(assetPath);
            if (existing == null)
            {
                AssetDatabase.CreateAsset(generated, assetPath);
                existing = generated;
            }
            else
            {
                EditorUtility.CopySerialized(generated, existing);
                existing.name = spec.generatedAssetName;
                EditorUtility.SetDirty(existing);
                UnityEngine.Object.DestroyImmediate(generated);
            }
            result.Add(spec.id, existing);
        }

        private static void AddActorTransformCurves(
            AnimationClip clip,
            string path,
            int trackIndex,
            IList frames,
            bool positionAnimated,
            bool rotationAnimated,
            bool scaleAnimated)
        {
            var curves = new AnimationCurve[10];
            for (int index = 0; index < curves.Length; ++index)
                curves[index] = new AnimationCurve();
            foreach (object frameObject in frames)
            {
                Dictionary<string, object> frame = Dict(frameObject);
                IList tracks = List(frame["tracks"]);
                Require(
                    trackIndex >= 0 && trackIndex < tracks.Count,
                    "Actor clip sample track index is out of range");
                Dictionary<string, object> value =
                    Dict(tracks[trackIndex]);
                float time = Float(frame, "time");
                IList position = List(value["translation"]);
                IList rotation = List(value["rotation"]);
                IList scale = List(value["scale"]);
                Require(
                    position.Count == 3 &&
                    rotation.Count == 4 &&
                    scale.Count == 3,
                    "Actor clip sample qvvf shape changed");
                if (positionAnimated)
                {
                    curves[0].AddKey(time, Float(position[0]));
                    curves[1].AddKey(time, Float(position[1]));
                    curves[2].AddKey(time, Float(position[2]));
                }
                if (rotationAnimated)
                {
                    curves[3].AddKey(time, Float(rotation[0]));
                    curves[4].AddKey(time, Float(rotation[1]));
                    curves[5].AddKey(time, Float(rotation[2]));
                    curves[6].AddKey(time, Float(rotation[3]));
                }
                if (scaleAnimated)
                {
                    curves[7].AddKey(time, Float(scale[0]));
                    curves[8].AddKey(time, Float(scale[1]));
                    curves[9].AddKey(time, Float(scale[2]));
                }
            }
            if (positionAnimated)
            {
                SetActorTransformCurve(
                    clip, path, "m_LocalPosition.x", curves[0]);
                SetActorTransformCurve(
                    clip, path, "m_LocalPosition.y", curves[1]);
                SetActorTransformCurve(
                    clip, path, "m_LocalPosition.z", curves[2]);
            }
            if (rotationAnimated)
            {
                SetActorTransformCurve(
                    clip, path, "m_LocalRotation.x", curves[3]);
                SetActorTransformCurve(
                    clip, path, "m_LocalRotation.y", curves[4]);
                SetActorTransformCurve(
                    clip, path, "m_LocalRotation.z", curves[5]);
                SetActorTransformCurve(
                    clip, path, "m_LocalRotation.w", curves[6]);
            }
            if (scaleAnimated)
            {
                SetActorTransformCurve(
                    clip, path, "m_LocalScale.x", curves[7]);
                SetActorTransformCurve(
                    clip, path, "m_LocalScale.y", curves[8]);
                SetActorTransformCurve(
                    clip, path, "m_LocalScale.z", curves[9]);
            }
        }

        private static void SetActorTransformCurve(
            AnimationClip clip,
            string path,
            string property,
            AnimationCurve curve)
        {
            Require(
                curve != null && curve.length > 0,
                "Actor transform curve is empty: " +
                path + " " + property);
            SetLinearTangents(curve);
            AnimationUtility.SetEditorCurve(
                clip,
                EditorCurveBinding.FloatCurve(
                    path,
                    typeof(Transform),
                    property),
                curve);
        }

        private static void ValidateActorTimelineSources()
        {
            Require(
                Sha256(RepoRelativeToAbsolute(ActorTimelineRepoPath)) ==
                    ActorTimelineSha256 &&
                Sha256(RepoRelativeToAbsolute(ActorLoopTrackRepoPath)) ==
                    ActorLoopTrackSha256,
                "Actor Timeline/Loop Track source hash changed");
            Dictionary<string, object> timeline =
                LoadJson(RepoRelativeToAbsolute(ActorTimelineRepoPath));
            Require(
                Str(timeline, "m_Name") ==
                    "gacha_char_zhuangfy_Actor" &&
                Approximately(
                    Double(Dict(timeline["m_EditorSettings"]),
                        "m_Framerate"),
                    60.0) &&
                List(timeline["m_Tracks"]).Count == 5,
                "Actor Timeline source semantics changed");
            foreach (ActorAnimationTrackSpec track in
                ExpectedActorAnimationTracks)
            {
                ValidateActorTrackSource(track);
            }
            Dictionary<string, object> loop =
                LoadJson(RepoRelativeToAbsolute(
                    ActorLoopTrackRepoPath));
            IList loopClips = List(loop["m_Clips"]);
            Require(
                Long(Dict(loop["$animestudio"]), "pathId") ==
                    6869818856996505814L &&
                Str(loop, "m_Name") == "Loop Track" &&
                loopClips.Count == 1 &&
                Approximately(
                    Double(Dict(loopClips[0]), "m_Start"),
                    10.7) &&
                Approximately(
                    Double(Dict(loopClips[0]), "m_Duration"),
                    3.333333333333334),
                "Actor Loop Track source semantics changed");
        }

        private static void ValidateActorTrackSource(
            ActorAnimationTrackSpec track)
        {
            string trackPath =
                RepoRelativeToAbsolute(track.sourceTrackRepoPath);
            Require(
                File.Exists(trackPath) &&
                Sha256(trackPath) == track.sourceTrackSha256,
                "Actor AnimationTrack source hash changed: " +
                track.id);
            Dictionary<string, object> source = LoadJson(trackPath);
            IList clips = List(source["m_Clips"]);
            Require(
                Long(Dict(source["$animestudio"]), "pathId") ==
                    track.sourceTrackPathId &&
                Str(source, "m_Name") == track.trackName &&
                clips.Count == 2,
                "Actor AnimationTrack identity changed: " + track.id);
            ValidateActorTimelineClip(
                Dict(clips[0]),
                track.entrancePlayablePathId,
                0.0,
                10.7,
                track.entrance.clipName,
                false);
            ValidateActorTimelineClip(
                Dict(clips[1]),
                track.loopPlayablePathId,
                10.7,
                3.3333333333333335,
                track.loop.clipName,
                true);
            ValidateActorPlayableSource(
                track.entrance,
                track.entrancePlayablePathId,
                track.entrancePlayableRepoPath,
                track.entrancePlayableSha256);
            ValidateActorPlayableSource(
                track.loop,
                track.loopPlayablePathId,
                track.loopPlayableRepoPath,
                track.loopPlayableSha256);
        }

        private static void ValidateActorTimelineClip(
            Dictionary<string, object> clip,
            long playablePathId,
            double start,
            double duration,
            string displayName,
            bool infinitePostTime)
        {
            object postTime = clip["m_PostExtrapolationTime"];
            Require(
                Long(Dict(clip["m_Asset"]), "m_PathID") ==
                    playablePathId &&
                Approximately(Double(clip, "m_Start"), start) &&
                Approximately(Double(clip, "m_Duration"), duration) &&
                Approximately(Double(clip, "m_ClipIn"), 0.0) &&
                Approximately(Double(clip, "m_TimeScale"), 1.0) &&
                Int(clip, "m_PreExtrapolationMode") == 1 &&
                Int(clip, "m_PostExtrapolationMode") == 0 &&
                Approximately(Double(clip, "m_EaseInDuration"), 0.0) &&
                Approximately(Double(clip, "m_EaseOutDuration"), 0.0) &&
                Approximately(Double(clip, "m_BlendInDuration"), -1.0) &&
                Approximately(Double(clip, "m_BlendOutDuration"), -1.0) &&
                Str(clip, "m_DisplayName") == displayName &&
                (infinitePostTime
                    ? postTime is string &&
                        (string)postTime == "Infinity"
                    : Approximately(
                        Convert.ToDouble(
                            postTime,
                            CultureInfo.InvariantCulture),
                        0.0)),
                "Actor TimelineClip timing/asset changed");
        }

        private static void ValidateActorPlayableSource(
            ActorAnimationClipSpec clip,
            long playablePathId,
            string repoPath,
            string expectedSha256)
        {
            string absolute = RepoRelativeToAbsolute(repoPath);
            Require(
                File.Exists(absolute) &&
                Sha256(absolute) == expectedSha256,
                "Actor AnimationPlayableAsset source hash changed: " +
                clip.id);
            Dictionary<string, object> source = LoadJson(absolute);
            Require(
                Long(Dict(source["$animestudio"]), "pathId") ==
                    playablePathId &&
                Long(Dict(source["m_Clip"]), "m_PathID") ==
                    clip.sourceClipPathId &&
                Int(Dict(source["m_Clip"]), "m_FileID") ==
                    (clip.id.StartsWith("body_", StringComparison.Ordinal)
                        ? 4
                        : clip.id.StartsWith(
                            "deco1_",
                            StringComparison.Ordinal)
                            ? 5
                            : 3) &&
                Int(source, "m_RemoveStartOffset") == 1 &&
                Int(source, "m_ApplyFootIK") == 1 &&
                Int(source, "m_Loop") == 0,
                "Actor AnimationPlayableAsset semantics changed: " +
                clip.id);
        }

        private static EndfieldRecoveredZhuangfyGachaCameraClip
            BuildActorCameraClip(Dictionary<string, object> payload)
        {
            Dictionary<string, object> record =
                Dict(payload["actorCameraClip"]);
            Require(Str(record, "schema") ==
                    EndfieldRecoveredZhuangfyGachaCameraClip.ExpectedSchema &&
                Str(record, "clipName") ==
                    EndfieldRecoveredZhuangfyGachaCameraClip.ExpectedClipName &&
                Long(record, "clipPathId") == -2243514871678823781L &&
                Long(record, "actorDirectorPathId") ==
                    -410748005131375337L &&
                Long(record, "cameraTrackPathId") ==
                    -3388511487846872874L &&
                Long(record, "cameraAnimatorPathId") ==
                    8349080795570744599L &&
                Str(record, "cameraReportSha256") ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedCameraReportSha256 &&
                Str(record, "cameraFixtureSha256") ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedCameraFixtureSha256 &&
                Str(record, "clipSourceSha256") ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedClipSourceSha256 &&
                Approximately(Double(record, "sourceDuration"), 10.7) &&
                Approximately(
                    Double(record, "timelineDuration"),
                    14.033333333333333) &&
                Approximately(Double(record, "sampleRate"), 60.0),
                "Actor camera source identity changed");

            EndfieldRecoveredZhuangfyGachaCameraClip clip =
                AssetDatabase.LoadAssetAtPath<
                    EndfieldRecoveredZhuangfyGachaCameraClip>(
                    ActorCameraClipAssetPath);
            if (clip == null)
            {
                clip = ScriptableObject.CreateInstance<
                    EndfieldRecoveredZhuangfyGachaCameraClip>();
                AssetDatabase.CreateAsset(clip, ActorCameraClipAssetPath);
            }
            clip.name = Str(record, "clipName");
            clip.schema = Str(record, "schema");
            clip.authority = Str(record, "authority");
            clip.clipName = Str(record, "clipName");
            clip.clipPathId = Long(record, "clipPathId");
            clip.actorDirectorPathId = Long(record, "actorDirectorPathId");
            clip.cameraTrackPathId = Long(record, "cameraTrackPathId");
            clip.cameraAnimatorPathId =
                Long(record, "cameraAnimatorPathId");
            clip.cameraReportSha256 = Str(record, "cameraReportSha256");
            clip.cameraFixtureSha256 = Str(record, "cameraFixtureSha256");
            clip.clipSourceSha256 = Str(record, "clipSourceSha256");
            clip.sourceDuration = Float(record, "sourceDuration");
            clip.timelineDuration = Double(record, "timelineDuration");
            clip.sampleRate = Float(record, "sampleRate");
            clip.runtimeBoundary = Str(record, "runtimeBoundary");

            string[] semantics =
            {
                "position.x", "position.y", "position.z",
                "rotation.x", "rotation.y", "rotation.z", "rotation.w",
                "verticalFovDegrees",
            };
            IList curveRows = List(record["scalarCurves"]);
            Require(curveRows.Count == semantics.Length,
                "Actor camera scalar curve count changed");
            clip.scalarCurves = curveRows.Cast<object>()
                .Select((curveObject, curveIndex) =>
                {
                    Dictionary<string, object> curve = Dict(curveObject);
                    Require(Str(curve, "semantic") ==
                        semantics[curveIndex],
                        "Actor camera scalar semantic changed at " +
                        curveIndex);
                    IList keyRows = List(curve["keys"]);
                    Require(keyRows.Count > 0,
                        "Actor camera scalar curve is empty at " +
                        curveIndex);
                    return new EndfieldRecoveredCubicCurve
                    {
                        semantic = semantics[curveIndex],
                        keys = keyRows.Cast<object>().Select(keyObject =>
                        {
                            Dictionary<string, object> key =
                                Dict(keyObject);
                            IList coefficients =
                                List(key["coefficients"]);
                            Require(coefficients.Count == 4,
                                "Actor camera cubic coefficient count changed");
                            return new EndfieldRecoveredCubicKey
                            {
                                time = Float(key, "time"),
                                cubic = Float(coefficients[0]),
                                quadratic = Float(coefficients[1]),
                                linear = Float(coefficients[2]),
                                value = Float(coefficients[3]),
                            };
                        }).ToArray(),
                    };
                }).ToArray();
            Require(clip.IsSourceClosed,
                "Generated Actor camera clip failed its runtime gate");
            EditorUtility.SetDirty(clip);
            AssetDatabase.SaveAssets();
            return clip;
        }

        private static void AddTransformBinding(
            AnimationClip clip,
            Dictionary<string, object> binding,
            IList frames)
        {
            string path = Str(binding, "path");
            int trackIndex = Int(binding, "trackIndex");
            bool position = Bool(binding, "position");
            bool rotation = Bool(binding, "rotation");
            bool scale = Bool(binding, "scale");
            var curves = new Dictionary<string, AnimationCurve>(StringComparer.Ordinal);
            if (position)
                foreach (string axis in new[] { "x", "y", "z" }) curves["m_LocalPosition." + axis] = new AnimationCurve();
            if (rotation)
                foreach (string axis in new[] { "x", "y", "z", "w" }) curves["m_LocalRotation." + axis] = new AnimationCurve();
            if (scale)
                foreach (string axis in new[] { "x", "y", "z" }) curves["m_LocalScale." + axis] = new AnimationCurve();

            foreach (object frameObject in frames)
            {
                Dictionary<string, object> frame = Dict(frameObject);
                IList tracks = List(frame["tracks"]);
                Require(trackIndex >= 0 && trackIndex < tracks.Count,
                    "Animation frame omits source track " + trackIndex);
                Dictionary<string, object> track = Dict(tracks[trackIndex]);
                float time = Float(frame, "time");
                if (position)
                    AddVectorKeys(curves, "m_LocalPosition.", time, List(track["translation"]), 3);
                if (rotation)
                    AddVectorKeys(curves, "m_LocalRotation.", time, List(track["rotation"]), 4);
                if (scale)
                    AddVectorKeys(curves, "m_LocalScale.", time, List(track["scale"]), 3);
            }
            foreach (KeyValuePair<string, AnimationCurve> pair in curves)
            {
                SetLinearTangents(pair.Value);
                AnimationUtility.SetEditorCurve(
                    clip,
                    EditorCurveBinding.FloatCurve(path, typeof(Transform), pair.Key),
                    pair.Value);
            }
        }

        private static void AddVectorKeys(
            Dictionary<string, AnimationCurve> curves,
            string prefix,
            float time,
            IList values,
            int dimensions)
        {
            Require(values.Count >= dimensions, "Animation vector has insufficient dimensions");
            const string axes = "xyzw";
            for (int index = 0; index < dimensions; index++)
                curves[prefix + axes[index]].AddKey(time, Float(values[index]));
        }

        private static void AddFloatCurve(
            AnimationClip clip,
            Dictionary<string, object> curveRecord,
            Type targetType)
        {
            string path = Str(curveRecord, "path");
            string property = Str(curveRecord, "property");
            Require(path.Length > 0 && property.Length > 0, "Empty AnimationClip binding");
            var curve = new AnimationCurve();
            foreach (object keyObject in List(curveRecord["keys"]))
            {
                Dictionary<string, object> key = Dict(keyObject);
                curve.AddKey(Float(key, "time"), Float(key, "value"));
            }
            Require(curve.length > 0, "Empty AnimationClip curve " + property);
            SetLinearTangents(curve);
            AnimationUtility.SetEditorCurve(
                clip,
                EditorCurveBinding.FloatCurve(path, targetType, property),
                curve);
        }

        private static void SetLinearTangents(AnimationCurve curve)
        {
            for (int index = 0; index < curve.length; index++)
            {
                AnimationUtility.SetKeyLeftTangentMode(curve, index, AnimationUtility.TangentMode.Linear);
                AnimationUtility.SetKeyRightTangentMode(curve, index, AnimationUtility.TangentMode.Linear);
            }
        }

        private static void BuildRuntime(
            Dictionary<string, object> payload,
            Dictionary<string, object> timelineContract,
            Dictionary<string, object> particleContract,
            Dictionary<string, AnimationClip> clips,
            Dictionary<string, AnimationClip> actorAnimationClips,
            EndfieldRecoveredZhuangfyGachaCameraClip actorCameraClip,
            AudioClip overviewAudio,
            AudioClip rarityAudio)
        {
            GameObject characterPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(CharacterPrefabPath);
            Require(characterPrefab != null, "Missing Zhuangfy character prefab");
            var root = new GameObject("Zhuangfy_Gacha_Recovered");
            GameObject actor = (GameObject)PrefabUtility.InstantiatePrefab(characterPrefab);
            actor.name = "Actor";
            actor.transform.SetParent(root.transform, false);
            Transform deco = actor.transform.Find("RecoveredProps/chr_0030_zhuangfy_deco_1");
            Transform piaodai = actor.transform.Find("RecoveredProps/P_fxui_zhuangfy_ui_overview_start_01_piaodai");
            Require(deco != null && piaodai != null, "Zhuangfy prefab omits exact gacha targets");
            deco.gameObject.SetActive(true);
            piaodai.gameObject.SetActive(false);

            Require(
                overviewAudio != null && rarityAudio != null &&
                Approximately(overviewAudio.length, 9.688) &&
                Approximately(rarityAudio.length, 5.287292),
                "Recovered gacha Audio media failed its decoded-duration gate");

            var effect = new GameObject("Effect");
            effect.transform.SetParent(root.transform, false);
            Dictionary<string, object> cameraRecord =
                Dict(payload["actorCameraClip"]);
            var externalCamera = new GameObject("ExternalCamera");
            externalCamera.transform.SetParent(root.transform, false);
            IList cameraPosition =
                List(cameraRecord["serializedLocalPosition"]);
            IList cameraRotation =
                List(cameraRecord["serializedLocalRotation"]);
            IList cameraScale = List(cameraRecord["serializedLocalScale"]);
            Require(cameraPosition.Count == 3 &&
                cameraRotation.Count == 4 &&
                cameraScale.Count == 3,
                "ExternalCamera serialized transform shape changed");
            externalCamera.transform.localPosition = new Vector3(
                Float(cameraPosition[0]),
                Float(cameraPosition[1]),
                Float(cameraPosition[2]));
            externalCamera.transform.localRotation = new Quaternion(
                Float(cameraRotation[0]),
                Float(cameraRotation[1]),
                Float(cameraRotation[2]),
                Float(cameraRotation[3]));
            externalCamera.transform.localScale = new Vector3(
                Float(cameraScale[0]),
                Float(cameraScale[1]),
                Float(cameraScale[2]));
            Dictionary<string, object> cameraFields =
                Dict(cameraRecord["camera"]);
            Require(!Bool(cameraFields, "enabled") &&
                Int(cameraFields, "projectionMatrixMode") == 1 &&
                !Bool(cameraFields, "orthographic"),
                "ExternalCamera admitted component mode changed");
            Camera sourceCamera = externalCamera.AddComponent<Camera>();
            sourceCamera.enabled = false;
            sourceCamera.clearFlags =
                (CameraClearFlags)Int(cameraFields, "clearFlags");
            IList background = List(cameraFields["backgroundColor"]);
            sourceCamera.backgroundColor = new UnityEngine.Color(
                Float(background[0]),
                Float(background[1]),
                Float(background[2]),
                Float(background[3]));
            sourceCamera.gateFit =
                (Camera.GateFitMode)Int(cameraFields, "gateFitMode");
            IList sensor = List(cameraFields["sensorSize"]);
            sourceCamera.sensorSize = new Vector2(
                Float(sensor[0]), Float(sensor[1]));
            IList lensShift = List(cameraFields["lensShift"]);
            sourceCamera.lensShift = new Vector2(
                Float(lensShift[0]), Float(lensShift[1]));
            sourceCamera.focalLength =
                Float(cameraFields, "focalLength");
            // Setting focalLength can opt a Camera into physical projection
            // in public Unity. Reset this last: physical projection is outside
            // the admitted exact curve scope.
            sourceCamera.usePhysicalProperties = false;
            sourceCamera.fieldOfView =
                Float(cameraFields, "restFovDegrees");
            sourceCamera.nearClipPlane = Float(cameraFields, "near");
            sourceCamera.farClipPlane = Float(cameraFields, "far");
            sourceCamera.orthographic = false;
            sourceCamera.allowHDR = Bool(cameraFields, "allowHDR");
            sourceCamera.allowMSAA = Bool(cameraFields, "allowMSAA");
            sourceCamera.allowDynamicResolution =
                Bool(cameraFields, "allowDynamicResolution");
            var externalPlayback = externalCamera.AddComponent<
                EndfieldRecoveredZhuangfyExternalCameraPlayback>();
            externalPlayback.sourceCamera = sourceCamera;
            externalPlayback.sourceClip = actorCameraClip;
            externalPlayback.keepSourceCameraDisabled = true;
            externalPlayback.physicalCameraBoundary =
                Str(cameraRecord, "runtimeBoundary");
            Dictionary<long, EndfieldRecoveredVFXFollowBoneTool>
                followBoneCarriers = BuildFollowBoneCarriers(
                    root.transform,
                    effect.transform);
            var effectTargets = new Dictionary<string, GameObject>(StringComparer.Ordinal);
            EndfieldRecoveredBaofaTimelineParticleHost
                baofaTimelineHost = null;
            ParticleSystem[] baofaRoots = null;
            long[] baofaPathIds = null;
            uint[] baofaSeeds = null;
            ParticleSystemRenderer baofaLightning902Renderer = null;
            EndfieldRecoveredDian902TimelineParticleHost
                fingerLightningTimelineHost = null;
            EndfieldRecoveredDian901FixedManualPlayback
                fingerLightningDian901Playback = null;
            EndfieldRecoveredDian902ManualPlayback
                fingerLightningPlayback = null;
            ParticleSystem[] fingerLightningRoots = null;
            foreach (object rootObject in List(particleContract["roots"]))
            {
                Dictionary<string, object> effectRecord = Dict(rootObject);
                if (Str(effectRecord, "inventoryKind") != "particle_effect")
                    continue;
                string effectName = Str(effectRecord, "effectRoot");
                string prefabPath = ParticlePrefabRoot + "/" + Safe(effectName) + ".prefab";
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Require(prefab != null, "Missing strict particle prefab " + prefabPath);
                GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                instance.name = effectName;
                long sourceFatherTransformPathId =
                    SourceEffectRootFatherTransformPathId(effectRecord);
                Transform recoveredParent;
                if (sourceFatherTransformPathId ==
                    SourceEffectTransformPathId)
                {
                    Require(
                        ExpectedDirectEffectParticleChildren.Contains(
                            effectName),
                        "Unproved particle root escaped directly under Effect");
                    recoveredParent = effect.transform;
                }
                else
                {
                    Require(
                        followBoneCarriers.TryGetValue(
                            sourceFatherTransformPathId,
                            out EndfieldRecoveredVFXFollowBoneTool carrier) &&
                        carrier.exactSourceChildren.Contains(effectName),
                        "Particle source father is outside the exact " +
                        "VFXFollowBoneTool partition: " + effectName);
                    recoveredParent = carrier.transform;
                }
                instance.transform.SetParent(recoveredParent, false);
                bool isFingerLightning = effectName ==
                    "P_fxui_zhuangfy_ui_overview_start_01_finger_lightning";
                bool isBaofa = effectName ==
                    "P_fxui_zhuangfy_ui_overview_start_01_baofa";
                // ControlPlayableAsset discovers ITimeControl scripts while
                // building the graph and does not include inactive hierarchy.
                // ActivationControlPlayable makes this source-authored active
                // root inactive before clip start on the first evaluation.
                instance.SetActive(isFingerLightning || isBaofa);
                if (isBaofa)
                {
                    EndfieldRecoveredParticleEffectSource marker =
                        instance.GetComponent<
                            EndfieldRecoveredParticleEffectSource>();
                    Require(marker != null,
                        "Baofa exact particle marker missing");
                    baofaPathIds = marker.particleNodes.Select(node =>
                        node.particleSystemPathId).ToArray();
                    Require(
                        baofaPathIds.SequenceEqual(
                            ExpectedBaofaParticleSystemPathIds),
                        "Baofa exact 19-root source identity/order changed");
                    baofaRoots = ResolveMarkerParticleRoots(marker);
                    ParticleSystem[] discovered =
                        DiscoverControllableParticleRoots(instance);
                    Require(
                        discovered.SequenceEqual(baofaRoots),
                        "Baofa recursive root/subemitter exclusion changed");
                    baofaSeeds = baofaRoots.Select(system =>
                        system.randomSeed).ToArray();
                    Require(
                        baofaRoots.Length ==
                            EndfieldRecoveredBaofaTimelineParticleHost
                                .ExactControllableRootCount &&
                        baofaSeeds.SequenceEqual(
                            ExpectedBaofaAuthoredSeeds) &&
                        baofaRoots.All(system =>
                            !system.useAutoRandomSeed &&
                            system.main.playOnAwake &&
                            Approximately(
                                system.main.simulationSpeed,
                                1.0) &&
                            !HasReferencedSubEmitter(system)),
                        "Baofa exact fixed-seed/lifecycle root scope changed");
                    EndfieldRecoveredParticleNodeSource lightning902Node =
                        marker.particleNodes.Single(node =>
                            node.particleRendererPathId ==
                                EndfieldRecoveredBaofaTimelineParticleHost
                                    .Lightning902RendererPathId);
                    Require(
                        lightning902Node.particleSystemPathId ==
                            EndfieldRecoveredBaofaTimelineParticleHost
                                .Lightning902ParticleSystemPathId &&
                        lightning902Node.materialPathIds.SequenceEqual(
                            new[] { -1087199587020585838L }) &&
                        lightning902Node.meshPathIds.SequenceEqual(
                            new[] { 7440796479737110652L }),
                        "Baofa Lightning902 source renderer tuple changed");
                    Transform lightning902Transform =
                        marker.hierarchyNodes.Single(node =>
                            node.transformPathId ==
                                lightning902Node.transformPathId)
                            .generatedTransform;
                    baofaLightning902Renderer =
                        lightning902Transform == null
                            ? null
                            : lightning902Transform.GetComponent<
                                ParticleSystemRenderer>();
                    Require(
                        baofaLightning902Renderer != null &&
                        baofaLightning902Renderer ==
                            baofaRoots[12].GetComponent<
                                ParticleSystemRenderer>(),
                        "Baofa Lightning902 generated renderer scope changed");
                    baofaTimelineHost =
                        instance.AddComponent<
                            EndfieldRecoveredBaofaTimelineParticleHost>();
                }
                if (isFingerLightning)
                {
                    EndfieldRecoveredParticleEffectSource marker =
                        instance.GetComponent<
                            EndfieldRecoveredParticleEffectSource>();
                    fingerLightningPlayback =
                        instance.GetComponent<
                            EndfieldRecoveredDian902ManualPlayback>();
                    fingerLightningDian901Playback =
                        instance.GetComponent<
                            EndfieldRecoveredDian901FixedManualPlayback>();
                    Require(
                        marker != null &&
                        fingerLightningDian901Playback != null &&
                        fingerLightningPlayback != null,
                        "Finger-lightning exact playback/marker missing");
                    long[] expectedRootPathIds =
                    {
                        -7480670352147895017L,
                        -8123539105028854505L,
                        -5045265892246901481L,
                    };
                    Require(
                        marker.particleNodes.Select(node =>
                            node.particleSystemPathId)
                            .SequenceEqual(expectedRootPathIds),
                        "Finger-lightning controllable root order changed");
                    fingerLightningRoots = marker.particleNodes.Select(node =>
                    {
                        Transform generated = marker.hierarchyNodes
                            .Single(item =>
                                item.transformPathId ==
                                node.transformPathId)
                            .generatedTransform;
                        Require(generated != null,
                            "Finger-lightning generated root missing");
                        ParticleSystem system =
                            generated.GetComponent<ParticleSystem>();
                        Require(system != null,
                            "Finger-lightning root lacks ParticleSystem");
                        return system;
                    }).ToArray();
                    Require(
                        fingerLightningRoots.Length == 3 &&
                        fingerLightningRoots.Count(system =>
                            system ==
                            fingerLightningDian901Playback
                                .TargetParticleSystem) == 1 &&
                        fingerLightningRoots.Count(system =>
                            system ==
                            fingerLightningPlayback
                                .TargetParticleSystem) == 1 &&
                        fingerLightningRoots.All(system =>
                            !system.useAutoRandomSeed),
                        "Finger-lightning exact three-root/seed scope changed");
                    fingerLightningTimelineHost =
                        instance.AddComponent<
                            EndfieldRecoveredDian902TimelineParticleHost>();
                }
                effectTargets.Add(effectName, instance);
            }
            Require(effectTargets.Count == 6, "Expected six strict particle targets");
            Require(
                followBoneCarriers.Count ==
                    ExpectedFollowBoneSpecs.Length &&
                ExpectedFollowBoneSpecs.All(spec =>
                {
                    EndfieldRecoveredVFXFollowBoneTool carrier =
                        followBoneCarriers[spec.carrierTransformPathId];
                    return carrier.transform.Cast<Transform>()
                        .Select(value => value.name)
                        .SequenceEqual(spec.children);
                }) &&
                ExpectedDirectEffectParticleChildren.All(name =>
                    effectTargets[name].transform.parent ==
                        effect.transform),
                "Recovered VFXFollowBoneTool child partition changed");
            Require(
                baofaTimelineHost != null &&
                baofaRoots != null &&
                baofaPathIds != null &&
                baofaSeeds != null,
                "Baofa Timeline lifecycle host was not created");
            Require(
                baofaLightning902Renderer != null,
                "Baofa Lightning902 runtime replay target was not resolved");
            Require(
                fingerLightningTimelineHost != null &&
                fingerLightningDian901Playback != null &&
                fingerLightningPlayback != null &&
                fingerLightningRoots != null,
                "Finger-lightning Timeline host was not created");

            EndfieldRecoveredZhuangfyGachaRuntime host = root.AddComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
            host.exactRendererScopeRoot = deco;
            Dictionary<string, object> hostContract = Dict(payload["entityVFXHost"]);
            string[] exactPaths = StringList(hostContract["eligibleRendererPaths"]);
            host.exactEligibleRenderers = exactPaths.Select(path =>
            {
                Transform target = root.transform.Find(path);
                Require(target != null, "Missing exact EntityVFX renderer path " + path);
                Renderer renderer = target.GetComponent<Renderer>();
                Require(renderer != null, "EntityVFX path has no Renderer " + path);
                return renderer;
            }).ToArray();
            Require(host.exactEligibleRenderers.Length == 4,
                "The exact deco-1 host is expected to select four recovered LOD renderers");
            ValidateExactWidgetLodGroup(deco, host.exactEligibleRenderers);
            host.definitions = BuildEntityDefinitions(timelineContract);

            Dictionary<string, object> startOrder = Dict(payload["startOrder"]);
            Dictionary<string, object> sourceOuterParent = Dict(startOrder["sourceOuterParent"]);
            Dictionary<string, object> recoveredDirector = Dict(startOrder["recoveredDirector"]);
            Dictionary<string, object> delayedPlay = Dict(startOrder["delayedPlay"]);
            host.autoStartRecoveredEffect = true;
            host.scaledPlayDelaySeconds = Float(delayedPlay, "delaySeconds");

            EndfieldRecoveredZhuangfyGachaSource source = root.AddComponent<EndfieldRecoveredZhuangfyGachaSource>();
            source.schema = Str(payload, "schema");
            source.timelineContractSha256 = ExpectedTimelineSha256;
            source.particleContractSha256 = ExpectedParticleSha256;
            source.nativeContractSha256 = ExpectedNativeSha256;
            source.runtimePayloadSha256 = ExpectedPayloadSha256;
            source.startOrderContractSha256 = ExpectedStartOrderSha256;
            source.originalTimelineName = "gacha_char_zhuangfy_Effect";
            source.originalTrackCount = 16;
            source.originalTimelineEnd = 14.033333333333333;
            source.boundEntityVFXSourceHierarchy = Str(hostContract, "boundSourceHierarchy");
            source.generatedEntityVFXScopeRoot = Str(hostContract, "generatedScopeRoot");
            source.exactEligibleRendererPaths = exactPaths;
            source.failClosedAnimationBindingCRCs = ExpectedExcludedBindingCrcs;
            source.rendererSelectionBoundary = Str(hostContract, "selection") + "; " + Str(hostContract, "openBoundary");
            source.animationBindingBoundary =
                "Three serialized rarity path CRCs remain unresolved and are not emitted or rebound.";
            source.shaderExecutionBoundary =
                "The exact Actor camera curve track, three non-camera Actor AnimationTracks, and Effect Timeline scheduling/lifecycle execute; the generated ExternalCamera remains disabled and isolated from the viewer. " +
                "Three exact VFXFollowBoneTool carriers update from the active deco-1 joint, body finger tip, and recovered ExternalCamera after Timeline evaluation. " +
                "The four exact additive-material VFX handlers execute through the recovered two-target VFX shader, and the selected four-renderer CharacterNPR dissolve executes through its source-closed replacement-material branch. Audio event-media playback and structural empty Light/Others helpers are recovered; Actor LoopPlayableClip section rewinding, physical-camera/history state, Lua group-6 phase, generic CharacterNPR dissolve/cutoff variants, runtime Wwise onset latency, and unrecovered retail HGRP branches remain fail closed.";
            source.sourceOuterParentHierarchy = Str(sourceOuterParent, "hierarchy");
            source.sourceOuterParentGameObjectPathId = Long(sourceOuterParent, "gameObjectPathId");
            source.sourceOuterParentTransformPathId = Long(sourceOuterParent, "transformPathId");
            source.sourceOuterParentSerializedActive = Bool(sourceOuterParent, "serializedActive");
            source.sourceOuterParentLocalTransform = Str(sourceOuterParent, "serializedLocalTransform");
            source.sourceInstantiateInWorldSpace = Bool(startOrder, "instantiateInWorldSpace");
            source.sourceDirectChildOrder = StringList(startOrder["sourceDirectChildOrder"]);
            source.sourceHelperDirectorOrder = StringList(startOrder["sourceHelperDirectorOrder"]);
            Dictionary<string, object> recoveredActorDirector =
                Dict(startOrder["recoveredActorCameraDirector"]);
            source.recoveredActorCameraSchema =
                Str(cameraRecord, "schema");
            source.recoveredActorDirectorSourcePathId =
                Long(cameraRecord, "actorDirectorPathId");
            source.recoveredActorCameraTrackSourcePathId =
                Long(cameraRecord, "cameraTrackPathId");
            source.recoveredActorCameraClipSourcePathId =
                Long(cameraRecord, "clipPathId");
            source.recoveredActorCameraClipName =
                Str(cameraRecord, "clipName");
            source.recoveredActorCameraReportSha256 =
                Str(cameraRecord, "cameraReportSha256");
            source.recoveredActorCameraFixtureSha256 =
                Str(cameraRecord, "cameraFixtureSha256");
            source.recoveredActorCameraClipSourceSha256 =
                Str(cameraRecord, "clipSourceSha256");
            source.recoveredActorTimelineSha256 =
                ActorTimelineSha256;
            source.recoveredActorLoopTrackSha256 =
                ActorLoopTrackSha256;
            source.recoveredActorAnimationTrackCount =
                ExpectedActorAnimationTracks.Length;
            source.recoveredActorAnimationClipCount =
                ExpectedActorAnimationTracks.Length * 2;
            source.recoveredActorAnimationTrackBindings =
                ExpectedActorAnimationTracks.Select(value =>
                    value.bindingPath).ToArray();
            source.recoveredActorAnimationClipSourceSha256 =
                ExpectedActorAnimationTracks.SelectMany(value =>
                    new[]
                    {
                        value.entrance.sourceJsonSha256,
                        value.loop.sourceJsonSha256,
                    }).ToArray();
            source.actorLoopBoundary =
                "The authored Loop Track/LoopPlayableClip [10.7, " +
                "14.033333333333333] is source-pinned but not emitted: " +
                "the current presentation/validation window does not cross " +
                "the section end, and its custom rewind callback semantics " +
                "are not source-closed in public Unity.";
            source.partiallyRecoveredHelperDirectors =
                RecoveredPartiallyRecoveredHelperDirectors;
            Require(
                Str(recoveredActorDirector, "role") == "Actor" &&
                Int(recoveredActorDirector, "sourceOrdinal") == 0 &&
                Long(recoveredActorDirector, "sourcePathId") ==
                    source.recoveredActorDirectorSourcePathId &&
                Str(recoveredActorDirector, "scope") ==
                    "A_actor_zhuangfy_gacha_cam track only",
                "Recovered Actor camera director payload changed");
            source.recoveredDirectorRole = Str(recoveredDirector, "role");
            source.recoveredDirectorSourceOrdinal = Int(recoveredDirector, "sourceOrdinal");
            source.recoveredDirectorSourcePathId = Long(recoveredDirector, "sourcePathId");
            source.recoveredAudioTimelinePathId =
                EndfieldRecoveredGachaAudioPlayableAsset.SourceTimelinePathId;
            source.recoveredAudioSerializedFile =
                EndfieldRecoveredGachaAudioPlayableAsset.SourceSerializedFile;
            source.recoveredAudioEventNames = new[]
            {
                EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventName,
                EndfieldRecoveredGachaAudioPlayableAsset.RarityEventName,
            };
            source.recoveredAudioEventHashes = new[]
            {
                EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventHash,
                EndfieldRecoveredGachaAudioPlayableAsset.RarityEventHash,
            };
            source.recoveredAudioMediaIds = new[]
            {
                EndfieldRecoveredGachaAudioPlayableAsset.OverviewMediaId,
                EndfieldRecoveredGachaAudioPlayableAsset.RarityMediaId,
            };
            source.recoveredAudioStarts = new[]
            {
                EndfieldRecoveredGachaAudioPlayableAsset.OverviewStart,
                EndfieldRecoveredGachaAudioPlayableAsset.RarityStart,
            };
            source.recoveredAudioDurations = new[]
            {
                EndfieldRecoveredGachaAudioPlayableAsset.OverviewDuration,
                EndfieldRecoveredGachaAudioPlayableAsset.RarityDuration,
            };
            source.recoveredAudioMediaSha256 = new[]
            {
                OverviewAudioSha256,
                RarityAudioSha256,
            };
            source.unimplementedHelperDirectors =
                RecoveredUnimplementedHelperDirectors;
            source.scaledPlayDelaySeconds = Float(delayedPlay, "delaySeconds");
            source.startOrderExecutionBoundary =
                RecoveredExecutionBoundary;
            source.sourceBaofaControlTrackOrder = 3;
            source.sourceBaofaUpdateParticle = true;
            source.sourceBaofaParticleRandomSeed = 3680u;
            source.sourceBaofaForceRuntimeSimulate = false;
            source.sourceBaofaUpdateITimeControl = true;
            source.sourceBaofaSearchHierarchy = true;
            source.recoveredBaofaUpdateParticle = false;
            source.recoveredBaofaControllableRootCount = 19;
            source.baofaTimelineOwnershipBoundary =
                "Serialized Control Track order 3 remains source " +
                "updateParticle=true, forceRuntimeSimulate=false, " +
                "seed=3680, updateITimeControl=true, searchHierarchy=true. " +
                "Recovered Timeline sets only this clip updateParticle=false " +
                "and delegates its exact 19 recursive non-subemitter roots " +
                "to EndfieldRecoveredBaofaTimelineParticleHost. Runtime uses " +
                "ordinary Play/Pause/Stop scheduling and never absolute-time " +
                "Simulate; editor/manual SetTime retains stock " +
                "fixedTimeStep=false preview while the Lightning902 replay " +
                "token remains invalid. Runtime Lightning902 publication is " +
                "conditional on the same caller Time.deltaTime partition.";
            source.sourceFingerLightningControlTrackOrder = 4;
            source.sourceFingerLightningUpdateParticle = true;
            source.sourceFingerLightningParticleRandomSeed = 7420u;
            source.sourceFingerLightningUpdateITimeControl = true;
            source.sourceFingerLightningSearchHierarchy = true;
            source.recoveredFingerLightningUpdateParticle = false;
            source.recoveredFingerLightningControllableRootCount = 3;
            source.timelineParticleHostAuditSha256 =
                TimelineParticleHostAuditSha256;
            source.dian901AutomaticRuntimeAuditSha256 =
                Dian901AutomaticRuntimeAuditSha256;
            source.dian901Order4AutomaticOwnerAuditSha256 =
                Dian901Order4AutomaticOwnerAuditSha256;
            source.dian901DynamicCarrierOracleSha256 =
                Dian901DynamicCarrierOracleSha256;
            source.lightning902RetailRuntimeAuditSha256 =
                Lightning902RetailRuntimeAuditSha256;
            source.fingerLightningTimelineOwnershipBoundary =
                "Serialized Control Track order 4 remains source " +
                "updateParticle=true, seed=7420, updateITimeControl=true, " +
                "searchHierarchy=true. Recovered Timeline sets only this " +
                "clip updateParticle=false and delegates its exact three " +
                "roots to EndfieldRecoveredDian902TimelineParticleHost. " +
                "Dian901 and Dian902 use independent guarded AdvanceExact " +
                "schedulers with one captured LateUpdate delta; flash alone " +
                "retains public scheduling. Editor/manual SetTime routes both " +
                "Dian roots through source-closed SimulateExact states.";
            source.effectFollowAuditSha256 =
                EffectFollowAuditSha256;
            source.recoveredVFXFollowBoneCarrierCount =
                ExpectedFollowBoneSpecs.Length;
            source.vfxFollowBoneExecutionBoundary =
                "Exactly three source-proven carriers update in LateUpdate " +
                "or explicit manual validation after Actor/ExternalCamera " +
                "Timeline evaluation. World position always follows; world " +
                "rotation follows only for the source bone/ExternalCamera " +
                "row. Missing, inactive, or path-mismatched attach nodes " +
                "fail closed without moving the carrier.";

            PlayableDirector actorCameraDirector =
                actor.AddComponent<PlayableDirector>();
            actorCameraDirector.playOnAwake = false;
            actorCameraDirector.timeUpdateMode =
                DirectorUpdateMode.GameTime;
            actorCameraDirector.extrapolationMode =
                DirectorWrapMode.Hold;
            host.actorCameraDirector = actorCameraDirector;
            host.recoveredOverviewAudio = overviewAudio;
            host.recoveredRarityAudio = rarityAudio;
            TimelineAsset actorCameraTimeline =
                RecreateActorCameraTimelineAsset();
            BuildActorCameraTimeline(
                actorCameraTimeline,
                actorCameraDirector,
                externalPlayback,
                cameraRecord,
                root.transform,
                actorAnimationClips);
            actorCameraDirector.playableAsset = actorCameraTimeline;

            PlayableDirector director = effect.AddComponent<PlayableDirector>();
            director.playOnAwake = false;
            director.timeUpdateMode = DirectorUpdateMode.GameTime;
            director.extrapolationMode = DirectorWrapMode.Hold;
            host.director = director;
            baofaTimelineHost.Configure(
                director,
                baofaRoots,
                baofaPathIds,
                baofaSeeds,
                baofaLightning902Renderer);
            fingerLightningTimelineHost.Configure(
                director,
                fingerLightningDian901Playback,
                fingerLightningPlayback,
                fingerLightningRoots);

            TimelineAsset timeline = RecreateTimelineAsset();
            BuildTimelineTracks(
                timeline,
                director,
                host,
                timelineContract,
                clips,
                effectTargets,
                piaodai.gameObject);
            director.playableAsset = timeline;

            PrefabUtility.SaveAsPrefabAsset(root, RuntimePrefabPath);
            UnityEngine.Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
        }

        private static AudioClip ImportRecoveredAudioClip(
            string repoPath,
            string assetPath,
            string expectedSha256)
        {
            string sourcePath = Path.GetFullPath(
                Path.Combine(Directory.GetCurrentDirectory(), "..", repoPath));
            Require(File.Exists(sourcePath), "Missing recovered gacha audio " + repoPath);
            Require(
                Sha256(sourcePath) == expectedSha256,
                "Recovered gacha audio hash changed: " + repoPath);
            string destinationPath = AssetPathToAbsolute(assetPath);
            Directory.CreateDirectory(Path.GetDirectoryName(destinationPath));
            File.Copy(sourcePath, destinationPath, true);
            AssetDatabase.ImportAsset(
                assetPath,
                ImportAssetOptions.ForceSynchronousImport |
                ImportAssetOptions.ForceUpdate);
            AudioClip clip = AssetDatabase.LoadAssetAtPath<AudioClip>(assetPath);
            Require(clip != null, "Unity did not import recovered gacha audio " + assetPath);
            return clip;
        }

        private static Dictionary<long, EndfieldRecoveredVFXFollowBoneTool>
            BuildFollowBoneCarriers(
                Transform runtimeRoot,
                Transform effectRoot)
        {
            Require(
                runtimeRoot != null && effectRoot != null &&
                effectRoot.parent == runtimeRoot,
                "VFXFollowBoneTool generated owner scope changed");
            var result =
                new Dictionary<long, EndfieldRecoveredVFXFollowBoneTool>();
            foreach (FollowBoneSpec spec in ExpectedFollowBoneSpecs)
            {
                Transform attachNode =
                    runtimeRoot.Find(spec.exactAttachPath);
                Require(
                    attachNode != null &&
                    attachNode.gameObject.activeInHierarchy,
                    "Exact active VFXFollowBoneTool attach node is " +
                    "missing: " + spec.exactAttachPath);
                var anchor = new GameObject(spec.carrierName);
                anchor.transform.SetParent(effectRoot, false);
                anchor.transform.localPosition =
                    spec.authoredLocalPosition;
                anchor.transform.localRotation =
                    spec.authoredLocalRotation;
                anchor.transform.localScale = Vector3.one;
                var carrier =
                    anchor.AddComponent<
                        EndfieldRecoveredVFXFollowBoneTool>();
                carrier.bindingRoot = runtimeRoot;
                carrier.attachNode = attachNode;
                carrier.exactAttachPath = spec.exactAttachPath;
                carrier.followRotation = spec.followRotation;
                carrier.sourceCarrierGameObjectPathId =
                    spec.carrierGameObjectPathId;
                carrier.sourceCarrierTransformPathId =
                    spec.carrierTransformPathId;
                carrier.sourceActorGameObjectPathId =
                    spec.actorGameObjectPathId;
                carrier.sourceAttachTransformPathId =
                    spec.attachTransformPathId;
                carrier.exactSourceChildren =
                    (string[])spec.children.Clone();
                result.Add(spec.carrierTransformPathId, carrier);
            }
            return result;
        }

        private static long SourceEffectRootFatherTransformPathId(
            Dictionary<string, object> effectRecord)
        {
            Dictionary<string, object> setting =
                Dict(effectRecord["effectSetting"]);
            long gameObjectPathId =
                Long(setting, "gameObjectPathID");
            Dictionary<string, object> node =
                List(effectRecord["hierarchyNodes"]).Cast<object>()
                    .Select(Dict)
                    .Single(value =>
                        Long(value, "gameObjectPathID") ==
                            gameObjectPathId);
            return Long(
                Dict(Dict(node["transform"])["m_Father"]),
                "m_PathID");
        }

        private static ParticleSystem[] ResolveMarkerParticleRoots(
            EndfieldRecoveredParticleEffectSource marker)
        {
            Require(marker != null && marker.particleNodes != null,
                "Particle marker/root list missing");
            return marker.particleNodes.Select(node =>
            {
                Transform generated = marker.hierarchyNodes
                    .Single(item =>
                        item.transformPathId == node.transformPathId)
                    .generatedTransform;
                Require(generated != null,
                    "Generated particle root missing for source PathID " +
                    node.particleSystemPathId);
                ParticleSystem system =
                    generated.GetComponent<ParticleSystem>();
                Require(system != null,
                    "Generated source particle node lacks ParticleSystem " +
                    node.particleSystemPathId);
                return system;
            }).ToArray();
        }

        private static ParticleSystem[] DiscoverControllableParticleRoots(
            GameObject sourceRoot)
        {
            Require(sourceRoot != null,
                "Controllable particle source root missing");
            ParticleSystem[] recursive =
                sourceRoot.GetComponentsInChildren<ParticleSystem>(true);
            var subEmitters = new HashSet<ParticleSystem>();
            foreach (ParticleSystem system in recursive)
            {
                ParticleSystem.SubEmittersModule module =
                    system.subEmitters;
                for (int index = 0;
                    index < module.subEmittersCount;
                    index++)
                {
                    ParticleSystem subEmitter =
                        module.GetSubEmitterSystem(index);
                    if (subEmitter != null)
                        subEmitters.Add(subEmitter);
                }
            }
            return recursive.Where(system =>
                !subEmitters.Contains(system)).ToArray();
        }

        private static bool HasReferencedSubEmitter(
            ParticleSystem system)
        {
            if (system == null)
                return false;
            ParticleSystem.SubEmittersModule module =
                system.subEmitters;
            for (int index = 0;
                index < module.subEmittersCount;
                index++)
            {
                if (module.GetSubEmitterSystem(index) != null)
                    return true;
            }
            return false;
        }

        private static void ValidateExactWidgetLodGroup(Transform deco, Renderer[] renderers)
        {
            Require(deco != null && renderers != null && renderers.Length == 4,
                "Exact widget LOD inputs changed");
            LODGroup group = deco.GetComponent<LODGroup>();
            Require(group != null && group.enabled && group.fadeMode == LODFadeMode.CrossFade &&
                group.animateCrossFading &&
                Vector3.Distance(group.localReferencePoint,
                    new Vector3(3.7252903e-09f, 2.9802322e-08f, -3.7252903e-09f)) < 1.0e-7f &&
                Mathf.Abs(group.size - 0.13753782f) < 1.0e-7f,
                "Exact widget LODGroup source fields changed");

            float[] thresholds = { 0.4f, 0.1f, 0.02f, 0.01f };
            LOD[] lods = group.GetLODs();
            Require(lods.Length == 4, "Exact widget LODGroup must contain four serialized entries");
            for (int index = 0; index < lods.Length; index++)
            {
                Require(Mathf.Abs(lods[index].screenRelativeTransitionHeight - thresholds[index]) < 1.0e-7f &&
                    Mathf.Abs(lods[index].fadeTransitionWidth - 0.5f) < 1.0e-7f &&
                    lods[index].renderers != null && lods[index].renderers.Length == 1 &&
                    lods[index].renderers[0] == renderers[index],
                    "Exact widget LOD entry changed at index " + index);
            }
        }

        private static EndfieldRecoveredEntityVFXDefinition[] BuildEntityDefinitions(
            Dictionary<string, object> timelineContract)
        {
            var definitions = new List<EndfieldRecoveredEntityVFXDefinition>();
            foreach (object assetObject in List(timelineContract["entityVFXAssets"]))
            {
                Dictionary<string, object> asset = Dict(assetObject);
                Dictionary<string, object> data = Dict(asset["data"]);
                string name = Str(asset, "name");
                string kind = Str(asset, "kind");
                Require(Int(data, "rendererMask") == -1 && !Bool(data, "useScaledTime"),
                    "Zhuang EntityVFX renderer/time semantics changed: " + name);
                var definition = new EndfieldRecoveredEntityVFXDefinition
                {
                    assetName = name,
                    rendererMask = -1,
                    useScaledTime = false,
                    loop = Bool(data, "loop"),
                    duration = Float(data, "duration"),
                };
                if (kind == "additive_material")
                {
                    Require(Bool(data, "enableVertColorIfMeshHasVFXVertColor") &&
                        Bool(data, "useStartCurve") &&
                        !Bool(data, "useDissolveCurve") && !Bool(data, "useScanCurve") &&
                        !Bool(data, "useCutoffPosY") && !Bool(data, "useLoopCurve") &&
                        !Bool(data, "useEndCurve") && !Bool(data, "useAddictiveProperties") &&
                        !Bool(data, "useAddictivePropertiesUpdate") && !Bool(data, "useColorTexture") &&
                        List(data["customCurves"]).Count == 0 &&
                        List(data["customLoopCurves"]).Count == 0 &&
                        List(data["customEndCurves"]).Count == 0 &&
                        List(data["addictiveVectorProperties"]).Count == 0,
                        "Unsupported additive branch became authored: " + name);
                    long materialId = Long(Dict(data["material"]), "m_PathID");
                    definition.kind = EndfieldRecoveredEntityVFXKind.AdditiveMaterial;
                    definition.additiveMaterial = FindGeneratedAssetByPathId<Material>(ParticleMaterialRoot, materialId);
                    definition.enableVertexColorIfMeshHasVFXVertexColor = true;
                    definition.useStartCurve = true;
                    definition.startOpacityCurve = SourceCurve(Dict(data["opacityCurve"]));
                    Require(definition.additiveMaterial != null, "Missing exact additive material " + materialId);
                }
                else if (kind == "dissolve")
                {
                    Require(definition.loop && !Bool(data, "useCutoffPosY") &&
                        !Bool(data, "useLoopCurve") && !Bool(data, "useEndCurve"),
                        "Unsupported dissolve branch became authored");
                    definition.kind = EndfieldRecoveredEntityVFXKind.Dissolve;
                    definition.allowSimultaneous = Bool(data, "allowSimultaneous");
                    definition.dissolveUvSet = Int(data, "uvSet");
                    definition.useCutoffPositionY = false;
                    definition.cutoffUseDissolve = Float(data, "cutoffUseDissolve");
                    definition.stopShadowCasting = Bool(data, "stopShadowCasting");
                    definition.stopRayTracingMeanTime = Bool(data, "stopRayTracingMeanTime");
                    definition.stopShadowCastingDelay = Float(data, "stopShadowCastingDelay");
                    definition.revertShadowCastingDelay = Float(data, "revertShadowCastingDelay");
                    long textureId = Long(Dict(data["dissolveTexture"]), "m_PathID");
                    definition.dissolveTexture = FindGeneratedAssetByPathId<Texture2D>(ParticleTextureRoot, textureId);
                    definition.dissolveTextureST = Vec4(Dict(data["dissolveTextureTillingOffset"]));
                    definition.dissolveEdgeSharp = Float(data, "dissolveEdgeSharp");
                    definition.dissolveEmissiveColor = Color(Dict(data["dissolveEmissiveColor"]));
                    definition.dissolveEmissiveEdge = Float(data, "dissolveEmissiveEdge");
                    definition.useLocalScreenUV = Bool(data, "useLocalScreenUV");
                    definition.startDissolveCurve = SourceCurve(Dict(data["dissolveValueCurve"]));
                    definition.useLoopCurve = false;
                    definition.loopDuration = Float(data, "loopDuration");
                    definition.useEndCurve = false;
                    definition.endDuration = Float(data, "endDuration");
                    Require(definition.dissolveTexture != null, "Missing exact dissolve texture " + textureId);
                }
                else
                {
                    throw new InvalidDataException("Unsupported EntityVFX kind " + kind);
                }
                definitions.Add(definition);
            }
            Require(definitions.Count(definition => definition.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial) == 4,
                "Expected four additive EntityVFX handlers");
            Require(definitions.Count(definition => definition.kind == EndfieldRecoveredEntityVFXKind.Dissolve) == 1,
                "Expected one dissolve EntityVFX handler");
            return definitions.ToArray();
        }

        private static TimelineAsset RecreateTimelineAsset()
        {
            AssetDatabase.DeleteAsset(TimelineAssetPath);
            var timeline = ScriptableObject.CreateInstance<TimelineAsset>();
            timeline.name = "gacha_char_zhuangfy_Effect_Recovered";
            AssetDatabase.CreateAsset(timeline, TimelineAssetPath);
            return timeline;
        }

        private static TimelineAsset RecreateActorCameraTimelineAsset()
        {
            AssetDatabase.DeleteAsset(ActorCameraTimelineAssetPath);
            var timeline = ScriptableObject.CreateInstance<TimelineAsset>();
            timeline.name = "gacha_char_zhuangfy_ActorCamera_Recovered";
            AssetDatabase.CreateAsset(
                timeline,
                ActorCameraTimelineAssetPath);
            return timeline;
        }

        private static void BuildActorCameraTimeline(
            TimelineAsset timeline,
            PlayableDirector director,
            EndfieldRecoveredZhuangfyExternalCameraPlayback playback,
            Dictionary<string, object> cameraRecord,
            Transform runtimeRoot,
            Dictionary<string, AnimationClip> actorAnimationClips)
        {
            Require(
                timeline != null && director != null && playback != null &&
                runtimeRoot != null &&
                actorAnimationClips != null &&
                actorAnimationClips.Count == 6 &&
                playback.sourceCamera != null &&
                !playback.sourceCamera.enabled &&
                playback.sourceClip != null &&
                playback.sourceClip.IsSourceClosed,
                "Actor camera Timeline inputs failed their source gate");
            Require(
                Approximately(Double(cameraRecord, "timelineStart"), 0.0) &&
                Approximately(
                    Double(cameraRecord, "timelineDuration"),
                    14.033333333333333),
                "Actor camera Timeline timing changed");
            foreach (ActorAnimationTrackSpec spec in
                ExpectedActorAnimationTracks)
            {
                Transform binding = runtimeRoot.Find(spec.bindingPath);
                Require(
                    binding != null && binding.gameObject.activeInHierarchy,
                    "Actor AnimationTrack binding is missing/inactive: " +
                    spec.bindingPath);
                // The reusable lab character prefab carries a legacy
                // Animation component for inspector previews. The installed
                // gacha runtime instead drives an Animator whose controller
                // is explicitly cleared before RebuildGraph/Evaluate/Play.
                // Unity forbids Animation and Animator on the same object, so
                // remove the preview-only component on this runtime instance.
                Animation legacyPreview =
                    binding.GetComponent<Animation>();
                if (legacyPreview != null)
                {
                    UnityEngine.Object.DestroyImmediate(legacyPreview);
                }
                Animator animator = binding.GetComponent<Animator>();
                if (animator == null)
                {
                    animator =
                        binding.gameObject.AddComponent<Animator>();
                }
                Require(
                    animator != null,
                    "Actor AnimationTrack Animator could not be created: " +
                    spec.bindingPath);
                animator.runtimeAnimatorController = null;
                animator.applyRootMotion = false;
                animator.cullingMode =
                    AnimatorCullingMode.AlwaysAnimate;
                AnimationTrack animationTrack =
                    timeline.CreateTrack<AnimationTrack>(
                        null,
                        spec.trackName);
                BuildActorTimelineAnimationClip(
                    animationTrack,
                    actorAnimationClips[spec.entrance.id],
                    spec.entrance.clipName,
                    0.0,
                    10.7);
                BuildActorTimelineAnimationClip(
                    animationTrack,
                    actorAnimationClips[spec.loop.id],
                    spec.loop.clipName,
                    10.7,
                    3.3333333333333335);
                director.SetGenericBinding(
                    animationTrack,
                    animator);
            }
            EndfieldRecoveredZhuangfyGachaCameraTrack track =
                timeline.CreateTrack<
                    EndfieldRecoveredZhuangfyGachaCameraTrack>(
                    null,
                    "A_actor_zhuangfy_gacha_cam");
            TimelineClip clip = track.CreateDefaultClip();
            clip.displayName = Str(cameraRecord, "clipName");
            clip.start = Double(cameraRecord, "timelineStart");
            clip.duration = Double(cameraRecord, "timelineDuration");
            clip.clipIn = 0.0;
            clip.timeScale = 1.0;
            SetExtrapolationMode(
                clip,
                "m_PreExtrapolationMode",
                TimelineClip.ClipExtrapolation.Hold);
            SetExtrapolationMode(
                clip,
                "m_PostExtrapolationMode",
                TimelineClip.ClipExtrapolation.None);
            director.SetGenericBinding(track, playback);
        }

        private static void BuildActorTimelineAnimationClip(
            AnimationTrack track,
            AnimationClip animation,
            string displayName,
            double start,
            double duration)
        {
            Require(
                track != null && animation != null &&
                !animation.legacy,
                "Actor Timeline requires a non-legacy exact clip");
            TimelineClip clip =
                track.CreateClip<AnimationPlayableAsset>();
            clip.displayName = displayName;
            clip.start = start;
            clip.duration = duration;
            clip.clipIn = 0.0;
            clip.timeScale = 1.0;
            clip.easeInDuration = 0.0;
            clip.easeOutDuration = 0.0;
            SetExtrapolationMode(
                clip,
                "m_PreExtrapolationMode",
                TimelineClip.ClipExtrapolation.Hold);
            SetExtrapolationMode(
                clip,
                "m_PostExtrapolationMode",
                TimelineClip.ClipExtrapolation.None);
            AnimationPlayableAsset playable =
                (AnimationPlayableAsset)clip.asset;
            playable.clip = animation;
            playable.position = Vector3.zero;
            playable.eulerAngles = Vector3.zero;
            playable.removeStartOffset = true;
            playable.applyFootIK = true;
            // All six serialized Actor AnimationPlayableAssets use m_Loop=0:
            // preserve each source AnimationClip's own loop-time flag.
            playable.loop =
                AnimationPlayableAsset.LoopMode.UseSourceAsset;
        }

        private static void BuildTimelineTracks(
            TimelineAsset timeline,
            PlayableDirector director,
            EndfieldRecoveredZhuangfyGachaRuntime host,
            Dictionary<string, object> timelineContract,
            Dictionary<string, AnimationClip> clips,
            Dictionary<string, GameObject> effectTargets,
            GameObject piaodai)
        {
            IList tracks = List(Dict(timelineContract["timeline"])["tracks"]);
            Require(tracks.Count == 16, "Expected 16 serialized Timeline tracks");
            var initialZeroEntityVFXOrders = new List<int>();
            foreach (object trackObject in tracks)
            {
                Dictionary<string, object> source = Dict(trackObject);
                int order = Int(source, "order");
                string kind = Str(source, "kind");
                string trackName = Str(source, "trackName");
                string displayName = Str(source, "displayName");
                Dictionary<string, object> timing = Dict(source["timing"]);
                if (kind == "control")
                {
                    GameObject target = displayName == "P_fxui_zhuangfy_ui_overview_start_01_piaodai"
                        ? piaodai
                        : effectTargets[displayName];
                    ControlTrack track = timeline.CreateTrack<ControlTrack>(null, trackName);
                    TimelineClip clip = track.CreateDefaultClip();
                    clip.displayName = displayName;
                    ApplyTiming(clip, timing);
                    ControlPlayableAsset asset = (ControlPlayableAsset)clip.asset;
                    var reference = new ExposedReference<GameObject>
                    {
                        exposedName = new PropertyName("zhuangfy_gacha_control_" + order),
                    };
                    asset.sourceGameObject = reference;
                    director.SetReferenceValue(reference.exposedName, target);
                    Dictionary<string, object> control = Dict(source["particleControl"]);
                    bool sourceUpdateParticle =
                        Bool(control, "updateParticle");
                    if (order == 1)
                    {
                        Require(
                            trackName == "Control Track (1)" &&
                            displayName ==
                                "P_fxui_zhuangfy_ui_overview_start_01_trail01" &&
                            Long(Dict(source["trackSource"]), "pathID") ==
                                8970100573188893026L &&
                            Long(Dict(source["playableAssetSource"]), "pathID") ==
                                3794251093511809378L &&
                            Long(
                                Dict(Dict(source["binding"])["target"]),
                                "pathID") ==
                                -4881997161974289129L &&
                            Str(
                                Dict(Dict(source["binding"])["target"]),
                                "hierarchy") ==
                                "gacha_char_zhuangfy/Effect/" +
                                "Zhuangfy_F_a_01_jnt/" +
                                "P_fxui_zhuangfy_ui_overview_start_01_trail01" &&
                            sourceUpdateParticle &&
                            Int(control, "particleRandomSeed") == 2292 &&
                            !Bool(control, "forceRuntimeSimulate") &&
                            Bool(control, "updateDirector") &&
                            Bool(control, "updateTimeControl") &&
                            Bool(control, "searchHierarchy") &&
                            Bool(control, "active") &&
                            Approximately(Double(timing, "start"), 0.0) &&
                            Approximately(
                                Double(timing, "clipIn"),
                                0.48333333333333334) &&
                            Approximately(Double(timing, "timeScale"), 1.0),
                            "Serialized Dian904 Control Track order-1 " +
                            "contract changed");
                        asset.updateParticle = sourceUpdateParticle;
                    }
                    else if (order == 3)
                    {
                        Require(
                            trackName == "Control Track (3)" &&
                            displayName ==
                                "P_fxui_zhuangfy_ui_overview_start_01_baofa" &&
                            sourceUpdateParticle &&
                            Int(control, "particleRandomSeed") == 3680 &&
                            !Bool(control, "forceRuntimeSimulate") &&
                            Bool(control, "updateTimeControl") &&
                            Bool(control, "searchHierarchy") &&
                            Bool(control, "active") &&
                            Int(control, "postPlayback") == 1 &&
                            Approximately(
                                Double(timing, "start"),
                                5.483333333333333) &&
                            Approximately(
                                Double(timing, "duration"),
                                3.916666666666667) &&
                            Approximately(
                                Double(timing, "clipIn"),
                                0.0) &&
                            Approximately(
                                Double(timing, "timeScale"),
                                1.0),
                            "Serialized baofa Control Track order-3 " +
                            "contract changed");
                        asset.updateParticle = false;
                    }
                    else if (order == 4)
                    {
                        Require(
                            trackName == "Control Track (4)" &&
                            displayName ==
                                "P_fxui_zhuangfy_ui_overview_start_01_finger_lightning" &&
                            sourceUpdateParticle &&
                            Int(control, "particleRandomSeed") == 7420 &&
                            Bool(control, "updateTimeControl") &&
                            Bool(control, "searchHierarchy") &&
                            Bool(control, "active") &&
                            Int(control, "postPlayback") == 1,
                            "Serialized finger-lightning Control Track " +
                            "order-4 contract changed");
                        asset.updateParticle = false;
                    }
                    else
                        asset.updateParticle = sourceUpdateParticle;
                    asset.particleRandomSeed = (uint)Int(control, "particleRandomSeed");
                    asset.updateDirector = Bool(control, "updateDirector");
                    asset.updateITimeControl = Bool(control, "updateTimeControl");
                    asset.searchHierarchy = Bool(control, "searchHierarchy");
                    asset.active = Bool(control, "active");
                    asset.postPlayback = (ActivationControlPlayable.PostPlaybackState)Int(control, "postPlayback");
                }
                else if (kind == "animation")
                {
                    Require(clips.TryGetValue(displayName, out AnimationClip animationClip),
                        "Missing recovered animation clip " + displayName);
                    GameObject target;
                    if (displayName.EndsWith("finger_lightning", StringComparison.Ordinal))
                        target = effectTargets["P_fxui_zhuangfy_ui_overview_start_01_finger_lightning"];
                    else if (displayName.EndsWith("piaodai2", StringComparison.Ordinal))
                        target = piaodai;
                    else if (displayName.EndsWith("piaodai", StringComparison.Ordinal))
                    {
                        Transform motion = piaodai.transform.Find("GameObject");
                        Require(motion != null, "Missing piaodai motion root");
                        target = motion.gameObject;
                    }
                    else
                        target = effectTargets["P_fxui_gacha_char_guangxiao_rarity6effect_01"];
                    Animator animator = target.GetComponent<Animator>();
                    if (animator == null)
                        animator = target.AddComponent<Animator>();
                    animator.applyRootMotion = false;
                    animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                    AnimationTrack track = timeline.CreateTrack<AnimationTrack>(null, trackName);
                    TimelineClip clip = track.CreateClip(animationClip);
                    clip.displayName = displayName;
                    ApplyTiming(clip, timing);
                    director.SetGenericBinding(track, animator);
                }
                else if (kind == "entity_vfx")
                {
                    EndfieldRecoveredEntityVFXTrack track =
                        timeline.CreateTrack<EndfieldRecoveredEntityVFXTrack>(null, trackName);
                    TimelineClip clip = track.CreateDefaultClip();
                    clip.displayName = displayName;
                    ApplyTiming(clip, timing);
                    var asset = (EndfieldRecoveredEntityVFXPlayableAsset)clip.asset;
                    Dictionary<string, object> entityVFXAsset = ResolveEntityVFXAssetContract(
                        timelineContract,
                        source);
                    string resolvedAssetName = Str(entityVFXAsset, "name");
                    asset.assetName = resolvedAssetName;
                    Dictionary<string, object> fields = Dict(source["playableAssetFields"]);
                    asset.ending = Bool(fields, "isEnding");
                    asset.clipStartTime = Float(timing, "start");
                    EndfieldRecoveredEntityVFXDefinition definition = host.definitions.Single(item =>
                        item != null && string.Equals(
                            item.assetName,
                            asset.assetName,
                            StringComparison.Ordinal));
                    definition.evaluateAtInitialZero =
                        Approximately(Double(timing, "start"), 0.0);
                    if (definition.evaluateAtInitialZero)
                        initialZeroEntityVFXOrders.Add(order);
                    director.SetGenericBinding(track, host);
                }
                else
                {
                    throw new InvalidDataException("Unsupported Timeline track kind " + kind);
                }
            }
            Require(timeline.GetOutputTracks().Count() == 16, "Generated Timeline track count changed");
            Require(host.definitions.Count(definition =>
                    definition != null && definition.evaluateAtInitialZero) == 3,
                "Expected exactly three source EntityVFX tracks at time zero");
            Require(initialZeroEntityVFXOrders.SequenceEqual(new[] { 9, 10, 11 }),
                "Exact source EntityVFX time-zero track order changed");
            EditorUtility.SetDirty(timeline);
            EditorUtility.SetDirty(director);
        }

        private static Dictionary<string, object> ResolveEntityVFXAssetContract(
            Dictionary<string, object> timelineContract,
            Dictionary<string, object> track)
        {
            int order = Int(track, "order");
            Dictionary<string, object> normalizedReference = Dict(track["entityVFXAsset"]);
            Dictionary<string, object> serializedReference =
                Dict(Dict(track["playableAssetFields"])["asset"]);
            Require(Int(normalizedReference, "fileID") != 0 &&
                Int(normalizedReference, "fileID") == Int(serializedReference, "m_FileID") &&
                Long(normalizedReference, "pathID") == Long(serializedReference, "m_PathID"),
                "EntityVFX normalized/serialized PPtr changed at track " + order);

            Dictionary<string, object> clipReference = Dict(Dict(track["clip"])["m_Asset"]);
            Dictionary<string, object> playableAssetSource = Dict(track["playableAssetSource"]);
            Require(Int(clipReference, "m_FileID") == 0 &&
                Long(clipReference, "m_PathID") == Long(playableAssetSource, "pathID"),
                "EntityVFX clip/playable-asset PPtr changed at track " + order);

            long referencedPathId = Long(normalizedReference, "pathID");
            Dictionary<string, object> asset = List(timelineContract["entityVFXAssets"])
                .Cast<object>()
                .Select(Dict)
                .Single(candidate =>
                    Long(Dict(candidate["source"]), "pathID") == referencedPathId);
            Require(Str(asset, "name") == Str(track, "displayName") &&
                List(asset["timelineTrackOrders"])
                    .Cast<object>()
                    .Select(Int)
                    .SequenceEqual(new[] { order }),
                "EntityVFX PPtr/name/order join changed at track " + order);
            return asset;
        }

        private static void ApplyTiming(TimelineClip clip, Dictionary<string, object> timing)
        {
            clip.start = Double(timing, "start");
            clip.duration = Double(timing, "duration");
            clip.clipIn = Double(timing, "clipIn");
            clip.timeScale = Double(timing, "timeScale");
            SetExtrapolationMode(
                clip,
                "m_PreExtrapolationMode",
                (TimelineClip.ClipExtrapolation)Int(timing, "preExtrapolationMode"));
            SetExtrapolationMode(
                clip,
                "m_PostExtrapolationMode",
                (TimelineClip.ClipExtrapolation)Int(timing, "postExtrapolationMode"));
        }

        private static void SetExtrapolationMode(
            TimelineClip clip,
            string fieldName,
            TimelineClip.ClipExtrapolation value)
        {
            FieldInfo field = typeof(TimelineClip).GetField(
                fieldName,
                BindingFlags.Instance | BindingFlags.NonPublic);
            Require(field != null, "TimelineClip extrapolation backing field changed: " + fieldName);
            field.SetValue(clip, value);
        }

        private static void ValidateGenerated(
            Dictionary<string, object> payload,
            Dictionary<string, object> timelineContract,
            Dictionary<string, object> particleContract,
            bool writeReport)
        {
            Require(Application.unityVersion == "2022.3.62f3",
                "Strict runtime validation requires Unity 2022.3.62f3");
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(RuntimePrefabPath);
            TimelineAsset timeline = AssetDatabase.LoadAssetAtPath<TimelineAsset>(TimelineAssetPath);
            TimelineAsset actorCameraTimeline =
                AssetDatabase.LoadAssetAtPath<TimelineAsset>(
                    ActorCameraTimelineAssetPath);
            EndfieldRecoveredZhuangfyGachaCameraClip actorCameraClip =
                AssetDatabase.LoadAssetAtPath<
                    EndfieldRecoveredZhuangfyGachaCameraClip>(
                    ActorCameraClipAssetPath);
            Require(
                prefab != null && timeline != null &&
                actorCameraTimeline != null && actorCameraClip != null,
                "Missing generated Zhuangfy gacha runtime assets");
            Dictionary<string, object> cameraRecord =
                Dict(payload["actorCameraClip"]);
            EndfieldRecoveredZhuangfyGachaSource source = prefab.GetComponent<EndfieldRecoveredZhuangfyGachaSource>();
            EndfieldRecoveredZhuangfyGachaRuntime host = prefab.GetComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
            EndfieldRecoveredBaofaTimelineParticleHost[]
                baofaTimelineHosts =
                    prefab.GetComponentsInChildren<
                        EndfieldRecoveredBaofaTimelineParticleHost>(true);
            EndfieldRecoveredBaofaTimelineParticleHost
                baofaTimelineHost =
                    baofaTimelineHosts.Length == 1
                        ? baofaTimelineHosts[0]
                        : null;
            EndfieldRecoveredDian902TimelineParticleHost[]
                timelineParticleHosts =
                    prefab.GetComponentsInChildren<
                        EndfieldRecoveredDian902TimelineParticleHost>(true);
            EndfieldRecoveredDian902TimelineParticleHost
                timelineParticleHost =
                    timelineParticleHosts.Length == 1
                        ? timelineParticleHosts[0]
                        : null;
            Transform effectOwner = prefab.transform.Find("Effect");
            Transform actorOwner = prefab.transform.Find("Actor");
            Transform externalCameraOwner =
                prefab.transform.Find("ExternalCamera");
            PlayableDirector[] recoveredDirectors =
                prefab.GetComponentsInChildren<PlayableDirector>(true);
            PlayableDirector director = effectOwner == null
                ? null
                : effectOwner.GetComponent<PlayableDirector>();
            PlayableDirector actorCameraDirector = actorOwner == null
                ? null
                : actorOwner.GetComponent<PlayableDirector>();
            EndfieldRecoveredZhuangfyExternalCameraPlayback cameraPlayback =
                externalCameraOwner == null
                    ? null
                    : externalCameraOwner.GetComponent<
                        EndfieldRecoveredZhuangfyExternalCameraPlayback>();
            Camera externalCamera = externalCameraOwner == null
                ? null
                : externalCameraOwner.GetComponent<Camera>();
            EndfieldRecoveredVFXFollowBoneTool[] followBoneCarriers =
                prefab.GetComponentsInChildren<
                    EndfieldRecoveredVFXFollowBoneTool>(true);
            bool exactRecoveredDirectorSet =
                source != null && host != null &&
                effectOwner != null && actorOwner != null &&
                recoveredDirectors.Length == 2 &&
                director != null &&
                director.gameObject == effectOwner.gameObject &&
                host.director == director &&
                actorCameraDirector != null &&
                actorCameraDirector.gameObject == actorOwner.gameObject &&
                host.actorCameraDirector == actorCameraDirector &&
                actorCameraDirector.playableAsset ==
                    actorCameraTimeline &&
                director.playableAsset == timeline &&
                prefab.GetComponent<PlayableDirector>() == null &&
                prefab.transform.Find("Audio") == null &&
                prefab.transform.Find("Light") == null &&
                prefab.transform.Find("Others") == null;
            Require(
                exactRecoveredDirectorSet,
                "Serialized runtime must contain the Actor-camera and Effect directors; " +
                "the source-closed Audio helper is created by the runtime coordinator");
            bool recoveredAudioSourceGate =
                host.recoveredOverviewAudio != null &&
                host.recoveredRarityAudio != null &&
                Approximately(host.recoveredOverviewAudio.length, 9.688) &&
                Approximately(host.recoveredRarityAudio.length, 5.287292) &&
                source.recoveredAudioTimelinePathId ==
                    EndfieldRecoveredGachaAudioPlayableAsset.SourceTimelinePathId &&
                source.recoveredAudioSerializedFile ==
                    EndfieldRecoveredGachaAudioPlayableAsset.SourceSerializedFile &&
                source.recoveredAudioEventNames.SequenceEqual(new[]
                {
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventName,
                    EndfieldRecoveredGachaAudioPlayableAsset.RarityEventName,
                }) &&
                source.recoveredAudioEventHashes.SequenceEqual(new[]
                {
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventHash,
                    EndfieldRecoveredGachaAudioPlayableAsset.RarityEventHash,
                }) &&
                source.recoveredAudioMediaIds.SequenceEqual(new[]
                {
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewMediaId,
                    EndfieldRecoveredGachaAudioPlayableAsset.RarityMediaId,
                }) &&
                source.recoveredAudioStarts.SequenceEqual(new[] { 0.0, 7.75 }) &&
                source.recoveredAudioDurations.SequenceEqual(new[]
                {
                    5.0,
                    2.366666666666667,
                }) &&
                source.recoveredAudioMediaSha256.SequenceEqual(new[]
                {
                    OverviewAudioSha256,
                    RarityAudioSha256,
                });
            Require(recoveredAudioSourceGate,
                "Recovered Audio Timeline/media source gate changed");
            bool followBoneSourcePartition =
                ValidateFollowBoneSourcePartition(
                    prefab,
                    particleContract,
                    followBoneCarriers);
            Require(
                followBoneSourcePartition,
                "Recovered VFXFollowBoneTool source partition changed");
            bool followBoneMissingBindingFailClosed;
            bool followBoneUnrelatedRootsUnmoved;
            bool followBoneRuntime =
                ValidateFollowBoneRuntime(
                    prefab,
                    out followBoneMissingBindingFailClosed,
                    out followBoneUnrelatedRootsUnmoved);
            Require(
                followBoneRuntime,
                "Recovered VFXFollowBoneTool runtime semantics changed");
            Require(
                followBoneMissingBindingFailClosed,
                "Recovered VFXFollowBoneTool missing/inactive binding did " +
                "not fail closed");
            Require(
                followBoneUnrelatedRootsUnmoved,
                "Recovered VFXFollowBoneTool moved an unrelated Effect root");
            bool actorCameraSourceGate =
                actorCameraClip.IsSourceClosed &&
                cameraPlayback != null &&
                cameraPlayback.sourceClip == actorCameraClip &&
                cameraPlayback.sourceCamera == externalCamera &&
                cameraPlayback.keepSourceCameraDisabled &&
                externalCamera != null &&
                !externalCamera.enabled &&
                !externalCamera.usePhysicalProperties &&
                actorCameraTimeline.GetOutputTracks().Count() == 4 &&
                actorCameraTimeline.GetOutputTracks()
                    .Count(value => value is AnimationTrack) == 3 &&
                actorCameraTimeline.GetOutputTracks()
                    .Count(value => value is
                        EndfieldRecoveredZhuangfyGachaCameraTrack) == 1;
            Require(
                actorCameraSourceGate,
                "Actor camera source gate or disabled-camera boundary changed");
            TrackAsset actorCameraTrack =
                actorCameraTimeline.GetOutputTracks().Single(value =>
                    value is
                        EndfieldRecoveredZhuangfyGachaCameraTrack);
            Require(
                actorCameraTrack is
                    EndfieldRecoveredZhuangfyGachaCameraTrack &&
                actorCameraDirector.GetGenericBinding(actorCameraTrack) ==
                    cameraPlayback &&
                actorCameraTrack.GetClips().Count() == 1,
                "Actor camera Timeline binding changed");
            Require(source.runtimePayloadSha256 == ExpectedPayloadSha256 &&
                source.nativeContractSha256 == ExpectedNativeSha256 &&
                source.startOrderContractSha256 == ExpectedStartOrderSha256,
                "Runtime source marker hash changed");
            bool parentMetadata =
                source.sourceOuterParentHierarchy == "GachaRoom/TimelineRoot" &&
                source.sourceOuterParentGameObjectPathId == 964036993266462176L &&
                source.sourceOuterParentTransformPathId == 2033347196788583904L &&
                source.sourceOuterParentSerializedActive &&
                source.sourceOuterParentLocalTransform == "identity" &&
                !source.sourceInstantiateInWorldSpace &&
                source.sourceDirectChildOrder.SequenceEqual(ExpectedSourceDirectChildOrder) &&
                source.sourceHelperDirectorOrder.SequenceEqual(ExpectedSourceHelperDirectorOrder) &&
                source.unimplementedHelperDirectors.SequenceEqual(RecoveredUnimplementedHelperDirectors) &&
                source.partiallyRecoveredHelperDirectors.SequenceEqual(
                    RecoveredPartiallyRecoveredHelperDirectors) &&
                Approximately(source.scaledPlayDelaySeconds, 0.25) &&
                source.startOrderExecutionBoundary ==
                    RecoveredExecutionBoundary;
            Require(parentMetadata, "Runtime source marker parent/start-order metadata changed");
            bool actorCameraMetadata =
                source.recoveredActorCameraSchema ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedSchema &&
                source.recoveredActorDirectorSourcePathId ==
                    -410748005131375337L &&
                source.recoveredActorCameraTrackSourcePathId ==
                    -3388511487846872874L &&
                source.recoveredActorCameraClipSourcePathId ==
                    -2243514871678823781L &&
                source.recoveredActorCameraClipName ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedClipName &&
                source.recoveredActorCameraReportSha256 ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedCameraReportSha256 &&
                source.recoveredActorCameraFixtureSha256 ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedCameraFixtureSha256 &&
                source.recoveredActorCameraClipSourceSha256 ==
                    EndfieldRecoveredZhuangfyGachaCameraClip
                        .ExpectedClipSourceSha256;
            Require(
                actorCameraMetadata,
                "Runtime source marker Actor camera identity changed");
            bool actorAnimationSourceGate =
                source.recoveredActorTimelineSha256 ==
                    ActorTimelineSha256 &&
                source.recoveredActorLoopTrackSha256 ==
                    ActorLoopTrackSha256 &&
                source.recoveredActorAnimationTrackCount == 3 &&
                source.recoveredActorAnimationClipCount == 6 &&
                source.recoveredActorAnimationTrackBindings
                    .SequenceEqual(
                        ExpectedActorAnimationTracks.Select(value =>
                            value.bindingPath)) &&
                source.recoveredActorAnimationClipSourceSha256
                    .SequenceEqual(
                        ExpectedActorAnimationTracks.SelectMany(value =>
                            new[]
                            {
                                value.entrance.sourceJsonSha256,
                                value.loop.sourceJsonSha256,
                            })) &&
                !string.IsNullOrWhiteSpace(source.actorLoopBoundary);
            Require(
                actorAnimationSourceGate,
                "Runtime source marker Actor animation identity changed");
            ActorZeroAffineOracle actorZeroAffineOracle;
            bool actorAnimationBinding =
                ValidateActorAnimationTimeline(
                    prefab,
                    actorCameraTimeline,
                    out actorZeroAffineOracle);
            Require(
                actorAnimationBinding &&
                actorZeroAffineOracle != null &&
                actorZeroAffineOracle.jointSampleBitsExact &&
                actorZeroAffineOracle.carrierWorldPositionExact &&
                actorZeroAffineOracle.dian904ChainResolved &&
                actorZeroAffineOracle
                    .dian904SameTimeLiveParticleAffineClosed,
                "Actor animation binding/same-time Dian904 affine " +
                "oracle failed");
            bool externalCameraIsolation;
            bool actorCameraDeclaredPair =
                ValidateActorCameraDeclaredPair(
                    prefab,
                    cameraRecord,
                    out externalCameraIsolation);
            Require(
                actorCameraDeclaredPair,
                "Actor camera Timeline failed the exact declared frame pair");
            Require(
                externalCameraIsolation,
                "Actor camera escaped its disabled ExternalCamera boundary");
            bool effectOrdinalMetadata = source.recoveredDirectorRole == "Effect" &&
                source.recoveredDirectorSourceOrdinal == 2 &&
                source.recoveredDirectorSourcePathId == 3160965858571562263L;
            Require(effectOrdinalMetadata, "Runtime source marker Effect ordinal/path identity changed");
            Require(
                source.effectFollowAuditSha256 ==
                    EffectFollowAuditSha256 &&
                source.recoveredVFXFollowBoneCarrierCount ==
                    ExpectedFollowBoneSpecs.Length &&
                !string.IsNullOrWhiteSpace(
                    source.vfxFollowBoneExecutionBoundary),
                "Runtime source marker VFXFollowBoneTool boundary changed");
            Require(source.failClosedAnimationBindingCRCs.SequenceEqual(ExpectedExcludedBindingCrcs),
                "Runtime source marker exclusion set changed");
            bool baofaTimelineOwnershipSourceTruth =
                source.sourceBaofaControlTrackOrder == 3 &&
                source.sourceBaofaUpdateParticle &&
                source.sourceBaofaParticleRandomSeed == 3680u &&
                !source.sourceBaofaForceRuntimeSimulate &&
                source.sourceBaofaUpdateITimeControl &&
                source.sourceBaofaSearchHierarchy &&
                !source.recoveredBaofaUpdateParticle &&
                source.recoveredBaofaControllableRootCount == 19 &&
                !string.IsNullOrWhiteSpace(
                    source.baofaTimelineOwnershipBoundary);
            Require(baofaTimelineOwnershipSourceTruth,
                "Baofa source/recovered ownership marker changed");
            bool baofaTimelineHostScope =
                baofaTimelineHost != null &&
                baofaTimelineHost.OwnerDirector == director &&
                baofaTimelineHost.SourceControlTrackOrder == 3 &&
                baofaTimelineHost.SourceParticleRandomSeedValue == 3680u &&
                baofaTimelineHost.ControllableRoots != null &&
                baofaTimelineHost.ControllableRoots.Length == 19 &&
                baofaTimelineHost.SourceParticleSystemPathIds != null &&
                baofaTimelineHost.SourceParticleSystemPathIds
                    .SequenceEqual(
                        ExpectedBaofaParticleSystemPathIds) &&
                baofaTimelineHost.AuthoredRandomSeeds != null &&
                baofaTimelineHost.AuthoredRandomSeeds
                    .SequenceEqual(ExpectedBaofaAuthoredSeeds) &&
                baofaTimelineHost.Lightning902Renderer != null &&
                baofaTimelineHost.Lightning902Renderer ==
                    baofaTimelineHost.ControllableRoots[12]
                        .GetComponent<ParticleSystemRenderer>() &&
                baofaTimelineHost.Lightning902Mesh != null &&
                baofaTimelineHost.Lightning902Mesh ==
                    baofaTimelineHost.Lightning902Renderer.mesh &&
                baofaTimelineHost.Lightning902ScopedMaterial != null &&
                baofaTimelineHost.Lightning902ScopedMaterial ==
                    baofaTimelineHost.Lightning902Renderer.sharedMaterial &&
                baofaTimelineHost.Lightning902Renderer.sharedMaterials
                    .Length == 1 &&
                baofaTimelineHost.Lightning902Renderer.sharedMaterials[0]
                    .IsKeywordEnabled(
                        EndfieldRecoveredBaofaTimelineParticleHost
                            .Lightning902ReplayKeyword) &&
                baofaTimelineHost.ControllableRoots.Select(system =>
                    system.randomSeed).SequenceEqual(
                        ExpectedBaofaAuthoredSeeds) &&
                baofaTimelineHost.ControllableRoots.All(system =>
                    system != null &&
                    !system.useAutoRandomSeed &&
                    system.main.playOnAwake &&
                    Approximately(
                        system.main.simulationSpeed,
                        1.0) &&
                    !HasReferencedSubEmitter(system)) &&
                DiscoverControllableParticleRoots(
                    baofaTimelineHost.gameObject)
                    .SequenceEqual(
                        baofaTimelineHost.ControllableRoots);
            Require(baofaTimelineHostScope,
                "Baofa exact Timeline host scope changed");
            bool timelineOwnershipSourceTruth =
                source.sourceFingerLightningControlTrackOrder == 4 &&
                source.sourceFingerLightningUpdateParticle &&
                source.sourceFingerLightningParticleRandomSeed == 7420u &&
                source.sourceFingerLightningUpdateITimeControl &&
                source.sourceFingerLightningSearchHierarchy &&
                !source.recoveredFingerLightningUpdateParticle &&
                source.recoveredFingerLightningControllableRootCount == 3 &&
                source.timelineParticleHostAuditSha256 ==
                    TimelineParticleHostAuditSha256 &&
                source.dian901AutomaticRuntimeAuditSha256 ==
                    Dian901AutomaticRuntimeAuditSha256 &&
                source.dian901Order4AutomaticOwnerAuditSha256 ==
                    Dian901Order4AutomaticOwnerAuditSha256 &&
                source.dian901DynamicCarrierOracleSha256 ==
                    Dian901DynamicCarrierOracleSha256 &&
                source.lightning902RetailRuntimeAuditSha256 ==
                    Lightning902RetailRuntimeAuditSha256 &&
                !string.IsNullOrWhiteSpace(
                    source.fingerLightningTimelineOwnershipBoundary);
            Require(timelineOwnershipSourceTruth,
                "Finger-lightning source/recovered ownership marker changed");
            bool timelineParticleHostScope =
                timelineParticleHost != null &&
                timelineParticleHost.OwnerDirector == director &&
                timelineParticleHost.Dian901Playback != null &&
                timelineParticleHost.Dian902Playback != null &&
                timelineParticleHost.SourceControlTrackOrder == 4 &&
                timelineParticleHost.SourceParticleRandomSeedValue == 7420u &&
                timelineParticleHost.ControllableRoots != null &&
                timelineParticleHost.ControllableRoots.Length == 3 &&
                timelineParticleHost.ControllableRoots[0] ==
                    timelineParticleHost.Dian901Playback
                        .TargetParticleSystem &&
                timelineParticleHost.ControllableRoots[1] ==
                    timelineParticleHost.Dian902Playback
                        .TargetParticleSystem &&
                timelineParticleHost.ControllableRoots[2] !=
                    timelineParticleHost.Dian901Playback
                        .TargetParticleSystem &&
                timelineParticleHost.ControllableRoots[2] !=
                    timelineParticleHost.Dian902Playback
                        .TargetParticleSystem &&
                timelineParticleHost.ControllableRoots.Count(system =>
                    system ==
                    timelineParticleHost.Dian901Playback
                        .TargetParticleSystem) == 1 &&
                timelineParticleHost.ControllableRoots.Count(system =>
                    system ==
                    timelineParticleHost.Dian902Playback
                        .TargetParticleSystem) == 1 &&
                timelineParticleHost.ControllableRoots.Select(system =>
                    system.randomSeed).SequenceEqual(new uint[]
                    {
                        373373479u,
                        13889542u,
                        5236u,
                    }) &&
                timelineParticleHost.ControllableRoots.All(system =>
                    !system.useAutoRandomSeed);
            Require(timelineParticleHostScope,
                "Finger-lightning exact Timeline host scope changed");
            Require(host.autoStartRecoveredEffect &&
                Approximately(host.scaledPlayDelaySeconds, 0.25),
                "Runtime scaled Effect start configuration changed");
            Require(host.exactRendererScopeRoot != null && host.exactEligibleRenderers.Length == 4 &&
                host.exactEligibleRenderers.All(renderer => renderer != null &&
                    renderer.transform.IsChildOf(host.exactRendererScopeRoot)),
                "EntityVFX escaped the exact deco-1 renderer scope");
            ValidateExactWidgetLodGroup(host.exactRendererScopeRoot, host.exactEligibleRenderers);
            Require(host.definitions.Length == 5 &&
                host.definitions.Count(item => item.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial) == 4 &&
                host.definitions.Count(item => item.kind == EndfieldRecoveredEntityVFXKind.Dissolve) == 1,
                "EntityVFX handler set changed");
            Require(host.definitions.Where(item => item.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial)
                .All(item => item.additiveMaterial != null && item.enableVertexColorIfMeshHasVFXVertexColor &&
                    item.additiveMaterial.shader != null &&
                    item.additiveMaterial.shader.name ==
                        "Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT" &&
                    item.additiveMaterial.GetTag(
                        "EndfieldSceneMVMRT", false, string.Empty) ==
                        "ExactSelectedFiftyThree"),
                "Additive source material boundary changed");

            List<TrackAsset> generatedTracks = timeline.GetOutputTracks().ToList();
            IList sourceTracks = List(Dict(timelineContract["timeline"])["tracks"]);
            Require(generatedTracks.Count == 16 && sourceTracks.Count == 16,
                "Timeline track count changed");
            var joinedEntityVFXNames = new List<string>();
            var joinedZeroStartOrders = new List<int>();
            bool order3OwnershipTranslated = false;
            bool order4OwnershipTranslated = false;
            for (int index = 0; index < generatedTracks.Count; index++)
            {
                TrackAsset generated = generatedTracks[index];
                Dictionary<string, object> expected = Dict(sourceTracks[index]);
                Require(generated.name == Str(expected, "trackName"), "Timeline track order/name changed at " + index);
                TimelineClip clip = generated.GetClips().Single();
                Dictionary<string, object> timing = Dict(expected["timing"]);
                Require(Approximately(clip.start, Double(timing, "start")) &&
                    Approximately(clip.duration, Double(timing, "duration")) &&
                    Approximately(clip.clipIn, Double(timing, "clipIn")) &&
                    clip.displayName == Str(expected, "displayName"),
                    "Timeline clip timing/identity changed at " + index);
                if (Str(expected, "kind") == "entity_vfx")
                {
                    Dictionary<string, object> assetContract = ResolveEntityVFXAssetContract(
                        timelineContract,
                        expected);
                    string joinedName = Str(assetContract, "name");
                    var generatedAsset = clip.asset as EndfieldRecoveredEntityVFXPlayableAsset;
                    Require(generatedAsset != null && generatedAsset.assetName == joinedName,
                        "Generated EntityVFX clip lost its source PPtr join at " + index);
                    joinedEntityVFXNames.Add(joinedName);
                    if (Approximately(Double(timing, "start"), 0.0))
                        joinedZeroStartOrders.Add(Int(expected, "order"));
                }
                else if (Str(expected, "kind") == "control")
                {
                    var generatedAsset =
                        clip.asset as ControlPlayableAsset;
                    Require(generatedAsset != null,
                        "Generated control asset missing at " + index);
                    Dictionary<string, object> sourceControl =
                        Dict(expected["particleControl"]);
                    int order = Int(expected, "order");
                    bool expectedUpdateParticle =
                        Bool(sourceControl, "updateParticle");
                    Require(
                        generatedAsset.particleRandomSeed ==
                            (uint)Int(
                                sourceControl,
                                "particleRandomSeed") &&
                        generatedAsset.updateDirector ==
                            Bool(sourceControl, "updateDirector") &&
                        generatedAsset.updateITimeControl ==
                            Bool(sourceControl, "updateTimeControl") &&
                        generatedAsset.searchHierarchy ==
                            Bool(sourceControl, "searchHierarchy") &&
                        generatedAsset.active ==
                            Bool(sourceControl, "active") &&
                        (int)generatedAsset.postPlayback ==
                            Int(sourceControl, "postPlayback"),
                        "Generated control source fields changed at " +
                        index);
                    if (order == 3)
                    {
                        order3OwnershipTranslated =
                            expectedUpdateParticle &&
                            !generatedAsset.updateParticle &&
                            !Bool(
                                sourceControl,
                                "forceRuntimeSimulate") &&
                            generated.name == "Control Track (3)" &&
                            clip.displayName ==
                                "P_fxui_zhuangfy_ui_overview_start_01_baofa";
                    }
                    else if (order == 4)
                    {
                        order4OwnershipTranslated =
                            expectedUpdateParticle &&
                            !generatedAsset.updateParticle &&
                            generated.name == "Control Track (4)" &&
                            clip.displayName ==
                                "P_fxui_zhuangfy_ui_overview_start_01_finger_lightning";
                    }
                    else
                    {
                        Require(
                            generatedAsset.updateParticle ==
                                expectedUpdateParticle,
                            "Non-order-3/4 Control Track updateParticle " +
                            "was translated at " + index);
                    }
                }
            }
            Require(order3OwnershipTranslated,
                "Baofa order-3 ownership was not translated");
            Require(order4OwnershipTranslated,
                "Finger-lightning order-4 ownership was not translated");
            Require(generatedTracks.Count(track => track is ControlTrack) == 7 &&
                generatedTracks.Count(track => track is AnimationTrack) == 4 &&
                generatedTracks.Count(track => track is EndfieldRecoveredEntityVFXTrack) == 5,
                "Timeline track type set changed");
            bool entityVFXPPtrJoin = joinedEntityVFXNames.Count == 5 &&
                joinedEntityVFXNames.Distinct(StringComparer.Ordinal).Count() == 5 &&
                joinedEntityVFXNames.OrderBy(name => name, StringComparer.Ordinal).SequenceEqual(
                    host.definitions.Select(definition => definition.assetName)
                        .OrderBy(name => name, StringComparer.Ordinal)) &&
                joinedZeroStartOrders.SequenceEqual(new[] { 9, 10, 11 }) &&
                host.definitions.Count(definition => definition.evaluateAtInitialZero) == 3;
            Require(entityVFXPPtrJoin,
                "EntityVFX source PPtr join or exact zero-start definition set changed");
            Require(AssetDatabase.FindAssets("t:AnimationClip", new[] { AnimationRoot }).Length == 4,
                "Generated runtime AnimationClip asset set changed");
            Require(
                AssetDatabase.FindAssets(
                    "t:AnimationClip",
                    new[] { ActorAnimationRoot }).Length == 6,
                "Generated Actor AnimationClip asset set changed");

            int rarityStaticCount = 0;
            foreach (object rootObject in List(particleContract["roots"]))
            {
                Dictionary<string, object> rootRecord = Dict(rootObject);
                if (Str(rootRecord, "effectRoot") != "P_fxui_gacha_char_guangxiao_rarity6effect_01")
                    continue;
                GameObject rarityPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                    ParticlePrefabRoot + "/P_fxui_gacha_char_guangxiao_rarity6effect_01.prefab");
                Require(rarityPrefab != null, "Missing rarity particle prefab");
                rarityStaticCount = rarityPrefab.GetComponentsInChildren<MeshRenderer>(true).Length;
                int sourceCount = List(rootRecord["hierarchyNodes"]).Cast<object>().Select(Dict).Count(node =>
                {
                    Dictionary<string, object> gameObject = Dict(node["gameObject"]);
                    return Dict(gameObject.TryGetValue("m_MeshRenderer", out object value) ? value : null).Count > 0;
                });
                Require(rarityStaticCount == sourceCount && sourceCount == 9,
                    "Rarity static renderer recovery changed");
            }

            bool strictGate =
                !EndfieldRecoveredZhuangfyGachaRuntime.IsNativeSampleActive(
                    EndfieldRecoveredZhuangfyGachaRuntime.NativePlayableMinWeight) &&
                EndfieldRecoveredZhuangfyGachaRuntime.IsNativeSampleActive(
                    EndfieldRecoveredZhuangfyGachaRuntime.NativePlayableMinWeight + 0.000001f);
            Require(strictGate, "Native strict playable-weight gate failed");

            bool initialEvaluate;
            bool scaledStartGate;
            bool additiveLifecycle;
            bool additiveOverlapCap;
            bool originalMaterialRestoration;
            bool dissolveMaterialLifecycle;
            bool dissolveShadowTiming;
            string initialEvaluateDetail = "not evaluated";
            string scaledStartGateDetail = "not evaluated";
            string dissolveMaterialLifecycleDetail = "not evaluated";
            GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
            try
            {
                EndfieldRecoveredZhuangfyGachaRuntime runtime = instance.GetComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
                runtime.autoStartRecoveredEffect = false;
                {
                    Material[][] startupOriginalMaterials = runtime.exactEligibleRenderers
                        .Select(renderer => (Material[])renderer.sharedMaterials.Clone())
                        .ToArray();
                    bool began = runtime.BeginRecoveredEffectStart(10.0f);
                    initialEvaluate = began && runtime.DelayedPlayPending &&
                        Approximately(runtime.DelayedPlayDeadline, 10.25) &&
                        Approximately(runtime.director.time, 0.0) &&
                        Approximately(
                            runtime.actorCameraDirector.time,
                            0.0) &&
                        runtime.director.state != PlayState.Playing &&
                        runtime.actorCameraDirector.state !=
                            PlayState.Playing &&
                        runtime.ActiveAddedMaterialRecordCount == 3 &&
                        runtime.AppliedAddedMaterialRecordCount == 3 &&
                        runtime.ActiveAddedMaterialInstanceCount == 12;
                    initialEvaluateDetail = string.Format(
                        CultureInfo.InvariantCulture,
                        "began={0}, pending={1}, deadline={2:R}, time={3:R}, state={4}, activeRecords={5}, appliedRecords={6}, instances={7}",
                        began,
                        runtime.DelayedPlayPending,
                        runtime.DelayedPlayDeadline,
                        runtime.director.time,
                        runtime.director.state,
                        runtime.ActiveAddedMaterialRecordCount,
                        runtime.AppliedAddedMaterialRecordCount,
                        runtime.ActiveAddedMaterialInstanceCount);
                    bool beforeGate = !runtime.AdvanceRecoveredEffectStart(10.249f) &&
                        runtime.DelayedPlayPending &&
                        runtime.director.state != PlayState.Playing &&
                        runtime.actorCameraDirector.state !=
                            PlayState.Playing;
                    bool atGate = runtime.AdvanceRecoveredEffectStart(10.25f) &&
                        !runtime.DelayedPlayPending && runtime.director.state == PlayState.Playing &&
                        runtime.actorCameraDirector.state ==
                            PlayState.Playing &&
                        Approximately(runtime.director.time, 0.0) &&
                        Approximately(
                            runtime.actorCameraDirector.time,
                            0.0) &&
                        runtime.ActiveAddedMaterialRecordCount == 3 &&
                        runtime.AppliedAddedMaterialRecordCount == 3 &&
                        runtime.ActiveAddedMaterialInstanceCount == 12;
                    runtime.director.Stop();
                    runtime.actorCameraDirector.Stop();
                    runtime.ResetAllEntityVFX();
                    bool startupRestored = runtime.ActiveAddedMaterialRecordCount == 0 &&
                        runtime.ActiveAddedMaterialInstanceCount == 0 &&
                        runtime.exactEligibleRenderers.Select((renderer, index) =>
                            renderer.sharedMaterials.SequenceEqual(startupOriginalMaterials[index]))
                            .All(value => value);
                    scaledStartGate = beforeGate && atGate && startupRestored;
                    scaledStartGateDetail = string.Format(
                        CultureInfo.InvariantCulture,
                        "before={0}, at={1}, restored={2}, pending={3}, state={4}, activeRecords={5}, appliedRecords={6}, instances={7}",
                        beforeGate,
                        atGate,
                        startupRestored,
                        runtime.DelayedPlayPending,
                        runtime.director.state,
                        runtime.ActiveAddedMaterialRecordCount,
                        runtime.AppliedAddedMaterialRecordCount,
                        runtime.ActiveAddedMaterialInstanceCount);
                }
                runtime.director.time = 0.25;
                string additive = runtime.definitions.First(item =>
                    item.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial).assetName;
                Material[][] originalMaterials = runtime.exactEligibleRenderers
                    .Select(renderer => (Material[])renderer.sharedMaterials.Clone())
                    .ToArray();
                bool[] originalVisibility = runtime.exactEligibleRenderers
                    .Select(renderer => renderer.enabled)
                    .ToArray();
                runtime.SampleEntityVFX(additive, 0.25f, false, 1f, 0f);
                bool appended = runtime.ActiveAddedMaterialRecordCount == 1 &&
                    runtime.ActiveAddedMaterialInstanceCount == 4 &&
                    runtime.exactEligibleRenderers.Select((renderer, index) =>
                        renderer.sharedMaterials.Length == originalMaterials[index].Length * 2 &&
                        renderer.sharedMaterials.Skip(originalMaterials[index].Length)
                            .SequenceEqual(originalMaterials[index]))
                        .All(value => value);
                runtime.director.time = 0.26;
                runtime.SampleEntityVFX(
                    additive,
                    0.26f,
                    false,
                    EndfieldRecoveredZhuangfyGachaRuntime.NativePlayableMinWeight,
                    0f);
                additiveLifecycle = appended && runtime.ActiveAddedMaterialRecordCount == 0 &&
                    runtime.ActiveAddedMaterialInstanceCount == 0 &&
                    runtime.exactEligibleRenderers.Select((renderer, index) =>
                        renderer.sharedMaterials.SequenceEqual(originalMaterials[index]))
                        .All(value => value);

                EndfieldRecoveredEntityVFXDefinition[] additiveDefinitions = runtime.definitions
                    .Where(item => item.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial)
                    .ToArray();
                runtime.director.time = 4.0;
                foreach (EndfieldRecoveredEntityVFXDefinition definition in additiveDefinitions)
                {
                    Dictionary<string, object> sourceTrack = List(Dict(timelineContract["timeline"])["tracks"])
                        .Cast<object>()
                        .Select(Dict)
                        .Where(track => Str(track, "kind") == "entity_vfx")
                        .Single(track => Str(
                            ResolveEntityVFXAssetContract(timelineContract, track),
                            "name") == definition.assetName);
                    float start = Float(Dict(sourceTrack["timing"]), "start");
                    runtime.SampleEntityVFX(definition.assetName, 4.0f - start, false, 1f, start);
                }

                EndfieldRecoveredEntityVFXDefinition[] newestFirst = additiveDefinitions.Reverse().ToArray();
                additiveOverlapCap =
                    EndfieldRecoveredZhuangfyGachaRuntime.NativeMaxAddedMaterialRecords == 4 &&
                    runtime.ActiveAddedMaterialRecordCount == 4 &&
                    runtime.AppliedAddedMaterialRecordCount == 4 &&
                    runtime.ActiveAddedMaterialInstanceCount == 16;
                for (int rendererIndex = 0;
                    rendererIndex < runtime.exactEligibleRenderers.Length && additiveOverlapCap;
                    rendererIndex++)
                {
                    Material[] applied = runtime.exactEligibleRenderers[rendererIndex].sharedMaterials;
                    Material[] originals = originalMaterials[rendererIndex];
                    additiveOverlapCap = applied.Length == originals.Length * 5;
                    for (int recordIndex = 0; recordIndex < newestFirst.Length && additiveOverlapCap; recordIndex++)
                    {
                        string expectedName = newestFirst[recordIndex].additiveMaterial.name +
                            " (Recovered EntityVFX Instance)";
                        for (int slot = 0; slot < originals.Length; slot++)
                        {
                            Material material = applied[recordIndex * originals.Length + slot];
                            additiveOverlapCap = material != null && material.name == expectedName;
                        }
                    }
                    additiveOverlapCap = additiveOverlapCap &&
                        applied.Skip(newestFirst.Length * originals.Length).SequenceEqual(originals) &&
                        runtime.exactEligibleRenderers[rendererIndex].enabled == originalVisibility[rendererIndex];
                }
                foreach (EndfieldRecoveredEntityVFXDefinition definition in additiveDefinitions)
                    runtime.ResetEntityVFX(definition.assetName);
                originalMaterialRestoration = runtime.ActiveAddedMaterialRecordCount == 0 &&
                    runtime.ActiveAddedMaterialInstanceCount == 0 &&
                    runtime.exactEligibleRenderers.Select((renderer, index) =>
                        renderer.sharedMaterials.SequenceEqual(originalMaterials[index]) &&
                        renderer.enabled == originalVisibility[index])
                        .All(value => value);

                EndfieldRecoveredEntityVFXDefinition dissolve = runtime.definitions.Single(item =>
                    item.kind == EndfieldRecoveredEntityVFXKind.Dissolve);
                Material[][] dissolveOriginalMaterials = runtime.exactEligibleRenderers
                    .Select(renderer => (Material[])renderer.sharedMaterials.Clone())
                    .ToArray();
                UnityEngine.Rendering.ShadowCastingMode originalShadow =
                    runtime.exactEligibleRenderers[0].shadowCastingMode;
                runtime.director.time = 5.79;
                runtime.SampleEntityVFX(dissolve.assetName, 0.199f, false, 1f, 5.6f);
                Material[] dissolveReplacements = runtime.exactEligibleRenderers
                    .SelectMany(renderer => renderer.sharedMaterials)
                    .ToArray();
                int dissolveScheduleOffset = Shader.PropertyToID("_DissolveScheduleOffset");
                int dissolveTex = Shader.PropertyToID("_DissolveTex");
                int dissolveTexST = Shader.PropertyToID("_DissolveTex_ST");
                int dissolveEdgeSharp = Shader.PropertyToID("_DissolveEdgeSharp");
                int dissolveEmissiveColor = Shader.PropertyToID("_DissolveEmissiveColor");
                int dissolveEmissiveEdge = Shader.PropertyToID("_DissolveEmissiveEdge");
                int dissolveUseViewUV = Shader.PropertyToID("_DissolveUseViewUV");
                int dissolveUVSet = Shader.PropertyToID("_DissolveUVSet");
                int useDissolve = Shader.PropertyToID("_UseDissolve");
                float expectedSchedule = dissolve.startDissolveCurve.Evaluate(
                    Mathf.Clamp01(0.199f / dissolve.duration));
                int expectedReplacementCount =
                    dissolveOriginalMaterials.Sum(materials => materials.Length);
                int actualReplacementCount = runtime.ActiveDissolveReplacementMaterialCount;
                bool replacementCountPassed =
                    actualReplacementCount == expectedReplacementCount;
                bool replacementArraysPassed =
                    runtime.exactEligibleRenderers.Select((renderer, index) =>
                        renderer.sharedMaterials.Length == dissolveOriginalMaterials[index].Length &&
                        renderer.sharedMaterials.Select((material, materialIndex) =>
                            material != dissolveOriginalMaterials[index][materialIndex] &&
                            material.name.EndsWith(
                                " (Recovered EntityVFX Replacement)",
                                StringComparison.Ordinal))
                            .All(value => value))
                        .All(value => value);
                bool dissolveKeywordObserved = dissolveReplacements.All(material =>
                    material.IsKeywordEnabled(
                        EndfieldRecoveredZhuangfyGachaRuntime.NativeCharacterDissolveKeyword));
                bool dissolvePayloadSupported = dissolveReplacements.All(material =>
                    material.HasProperty(dissolveScheduleOffset) &&
                    material.HasProperty(dissolveTex) &&
                    material.HasProperty(dissolveTexST) &&
                    material.HasProperty(dissolveEdgeSharp) &&
                    material.HasProperty(dissolveEmissiveColor) &&
                    material.HasProperty(dissolveEmissiveEdge) &&
                    material.HasProperty(dissolveUseViewUV) &&
                    material.HasProperty(dissolveUVSet) &&
                    material.HasProperty(useDissolve));
                bool dissolvePropertiesPassed = dissolveReplacements.All(material =>
                        (!material.HasProperty(dissolveScheduleOffset) ||
                            Approximately(material.GetFloat(dissolveScheduleOffset), expectedSchedule)) &&
                        (!material.HasProperty(dissolveTex) ||
                            material.GetTexture(dissolveTex) == dissolve.dissolveTexture) &&
                        (!material.HasProperty(dissolveTexST) ||
                            material.GetVector(dissolveTexST) == dissolve.dissolveTextureST) &&
                        (!material.HasProperty(dissolveEdgeSharp) ||
                            Approximately(
                                material.GetFloat(dissolveEdgeSharp),
                                dissolve.dissolveEdgeSharp)) &&
                        (!material.HasProperty(dissolveEmissiveColor) ||
                            material.GetColor(dissolveEmissiveColor) ==
                                dissolve.dissolveEmissiveColor) &&
                        (!material.HasProperty(dissolveEmissiveEdge) ||
                            Approximately(
                                material.GetFloat(dissolveEmissiveEdge),
                                dissolve.dissolveEmissiveEdge)) &&
                        (!material.HasProperty(dissolveUseViewUV) ||
                            Approximately(
                                material.GetFloat(dissolveUseViewUV),
                                dissolve.useLocalScreenUV ? 1f : 0f)) &&
                        (!material.HasProperty(dissolveUVSet) ||
                            Approximately(material.GetFloat(dissolveUVSet), dissolve.dissolveUvSet)) &&
                        (!material.HasProperty(useDissolve) ||
                            Approximately(material.GetFloat(useDissolve), 1f)));
                bool dissolveVisualFailClosed =
                    runtime.IsDissolveVisualFailClosed(dissolve.assetName);
                // The selected CharacterCloth route is source-closed and must
                // prove both keyword activation and no visual fail-closure.
                // Keep this capability-shaped gate so any future shader that
                // omits the payload still fails closed instead of being
                // admitted by replacement-material ownership alone.
                bool dissolveCapabilityBoundaryPassed = dissolvePayloadSupported
                    ? dissolveKeywordObserved && !dissolveVisualFailClosed
                    : dissolveVisualFailClosed;
                bool replacementInitialization = replacementCountPassed &&
                    replacementArraysPassed && dissolvePropertiesPassed &&
                    dissolveCapabilityBoundaryPassed;
                bool before = !runtime.IsShadowStopped(dissolve.assetName) &&
                    runtime.exactEligibleRenderers[0].shadowCastingMode == originalShadow;
                runtime.director.time = 5.8;
                runtime.SampleEntityVFX(dissolve.assetName, 0.2f, false, 1f, 5.6f);
                bool stopped = runtime.IsShadowStopped(dissolve.assetName) &&
                    runtime.exactEligibleRenderers[0].shadowCastingMode ==
                    UnityEngine.Rendering.ShadowCastingMode.Off;
                runtime.ResetEntityVFX(dissolve.assetName);
                bool replacementResetCountPassed =
                    runtime.ActiveDissolveReplacementMaterialCount == 0;
                bool replacementRestorationPassed =
                    runtime.exactEligibleRenderers.Select((renderer, index) =>
                        renderer.sharedMaterials.SequenceEqual(dissolveOriginalMaterials[index]))
                        .All(value => value);
                bool replacementDestructionPassed =
                    dissolveReplacements.All(material => material == null);
                dissolveMaterialLifecycle = replacementInitialization &&
                    replacementResetCountPassed &&
                    replacementRestorationPassed &&
                    replacementDestructionPassed;
                dissolveMaterialLifecycleDetail = string.Format(
                    CultureInfo.InvariantCulture,
                    "count={0} ({1}/{2}), arrays={3}, payloadSupported={4}, " +
                    "keywordObserved={5}, properties={6}, capabilityBoundary={7}, " +
                    "resetCount={8}, restored={9}, destroyed={10}, visualFailClosed={11}",
                    replacementCountPassed,
                    actualReplacementCount,
                    expectedReplacementCount,
                    replacementArraysPassed,
                    dissolvePayloadSupported,
                    dissolveKeywordObserved,
                    dissolvePropertiesPassed,
                    dissolveCapabilityBoundaryPassed,
                    replacementResetCountPassed,
                    replacementRestorationPassed,
                    replacementDestructionPassed,
                    dissolveVisualFailClosed);
                dissolveShadowTiming = before && stopped &&
                    runtime.exactEligibleRenderers[0].shadowCastingMode == originalShadow;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
            Require(initialEvaluate,
                "Initial Effect Stop/time=0/Evaluate sample validation failed: " + initialEvaluateDetail);
            Require(scaledStartGate,
                "Scaled-time 0.25-second Effect Rebuild/time=0/Evaluate/Play gate failed: " +
                scaledStartGateDetail);
            Require(additiveLifecycle, "Additive per-effect clone lifecycle failed");
            Require(additiveOverlapCap,
                "Native t=4.0 newest-first/original-last four-record overlap validation failed");
            Require(originalMaterialRestoration,
                "Native additive-material restoration or renderer visibility preservation failed");
            Require(dissolveMaterialLifecycle,
                "Native replacement-material dissolve initialization/reset lifecycle failed: " +
                dissolveMaterialLifecycleDetail);
            Require(dissolveShadowTiming, "Dissolve shadow timing/reset failed");

            if (writeReport)
            {
                var report = new ValidationReport
                {
                    schema = "endfield.zhuangfy-gacha-runtime-unity-validation.v8",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType =
                        SystemInfo.graphicsDeviceType.ToString(),
                    payloadSha256 = ExpectedPayloadSha256,
                    timelineContractSha256 = ExpectedTimelineSha256,
                    particleContractSha256 = ExpectedParticleSha256,
                    nativeContractSha256 = ExpectedNativeSha256,
                    startOrderContractSha256 = ExpectedStartOrderSha256,
                    timelineParticleHostAuditSha256 =
                        TimelineParticleHostAuditSha256,
                    lightning902RetailRuntimeAuditSha256 =
                        Lightning902RetailRuntimeAuditSha256,
                    effectFollowAuditSha256 =
                        EffectFollowAuditSha256,
                    dian904ClipInRuntimeAuditSha256 =
                        Dian904ClipInRuntimeAuditSha256,
                    prefabAsset = RuntimePrefabPath,
                    timelineAsset = TimelineAssetPath,
                    actorCameraTimelineAsset =
                        ActorCameraTimelineAssetPath,
                    actorCameraClipAsset = ActorCameraClipAssetPath,
                    actorCameraReportSha256 =
                        EndfieldRecoveredZhuangfyGachaCameraClip
                            .ExpectedCameraReportSha256,
                    actorCameraFixtureSha256 =
                        EndfieldRecoveredZhuangfyGachaCameraClip
                            .ExpectedCameraFixtureSha256,
                    actorTimelineSha256 =
                        ActorTimelineSha256,
                    actorLoopTrackSha256 =
                        ActorLoopTrackSha256,
                    trackCount = 16,
                    controlTrackCount = 7,
                    animationTrackCount = 4,
                    entityVFXTrackCount = 5,
                    generatedAnimationClipCount = 4,
                    actorAnimationTrackCount = 3,
                    actorAnimationClipCount = 6,
                    exactEligibleRendererCount = 4,
                    additiveHandlerCount = 4,
                    dissolveHandlerCount = 1,
                    sourceZeroStartDefinitionCount = 3,
                    staticRarityMeshRendererCount = rarityStaticCount,
                    baofaControllableRootCount = 19,
                    fingerLightningControllableRootCount = 3,
                    vfxFollowBoneCarrierCount =
                        ExpectedFollowBoneSpecs.Length,
                    failClosedAnimationBindingCRCs = ExpectedExcludedBindingCrcs,
                    rendererSelectionBoundary = source.rendererSelectionBoundary,
                    shaderExecutionBoundary = source.shaderExecutionBoundary,
                    baofaTimelineOwnershipBoundary =
                        source.baofaTimelineOwnershipBoundary,
                    fingerLightningTimelineOwnershipBoundary =
                        source.fingerLightningTimelineOwnershipBoundary,
                    sourceBaofaUpdateParticle = true,
                    recoveredBaofaUpdateParticle = false,
                    baofaTimelineHostPassed =
                        baofaTimelineHostScope &&
                        order3OwnershipTranslated,
                    sourceFingerLightningUpdateParticle = true,
                    recoveredFingerLightningUpdateParticle = false,
                    fingerLightningTimelineHostPassed =
                        timelineParticleHostScope &&
                        order4OwnershipTranslated,
                    vfxFollowBoneSourcePartitionPassed =
                        followBoneSourcePartition,
                    vfxFollowBoneRuntimePassed =
                        followBoneRuntime,
                    vfxFollowBoneInitialAuthoredTransformPassed =
                        followBoneSourcePartition &&
                        followBoneRuntime,
                    vfxFollowBoneWorldPositionCopyPassed =
                        followBoneRuntime,
                    vfxFollowBoneRotationBranchPassed =
                        followBoneRuntime,
                    vfxFollowBoneDeterministicPassed =
                        followBoneRuntime,
                    vfxFollowBoneMissingBindingFailClosedPassed =
                        followBoneMissingBindingFailClosed,
                    vfxFollowBoneUnrelatedRootsUnmovedPassed =
                        followBoneUnrelatedRootsUnmoved,
                    strictWeightGatePassed = strictGate,
                    entityVFXPPtrJoinPassed = entityVFXPPtrJoin,
                    exactLodGroupPassed = true,
                    parentMetadataPassed = parentMetadata,
                    initialEvaluatePassed = initialEvaluate,
                    scaledStartGatePassed = scaledStartGate,
                    effectOrdinalMetadataPassed = effectOrdinalMetadata,
                    exactRecoveredDirectorSetPassed =
                        exactRecoveredDirectorSet,
                    actorCameraSourceGatePassed =
                        actorCameraSourceGate && actorCameraMetadata,
                    actorCameraDeclaredPairPassed =
                        actorCameraDeclaredPair,
                    actorAnimationSourceGatePassed =
                        actorAnimationSourceGate,
                    actorAnimationBindingPassed =
                        actorAnimationBinding,
                    actorAnimationDeclaredZeroPassed =
                        actorZeroAffineOracle != null &&
                        actorZeroAffineOracle
                            .jointSampleBitsExact &&
                        actorZeroAffineOracle
                            .carrierWorldPositionExact &&
                        actorZeroAffineOracle
                            .dian904ChainResolved,
                    dian904SameTimeLiveParticleAffinePassed =
                        actorZeroAffineOracle != null &&
                        actorZeroAffineOracle
                            .dian904ControlClipExact &&
                        actorZeroAffineOracle
                            .dian904ControlBindingExact &&
                        actorZeroAffineOracle
                            .dian904ParticleDescendantOfControlTarget &&
                        actorZeroAffineOracle
                            .dian904ClipInSchedulerAuditPinned &&
                        actorZeroAffineOracle
                            .dian904SameTimeLiveParticleAffineClosed,
                    externalCameraIsolationPassed =
                        externalCameraIsolation,
                    additiveLifecyclePassed = additiveLifecycle,
                    additiveOverlapCapPassed = additiveOverlapCap,
                    originalMaterialRestorationPassed = originalMaterialRestoration,
                    dissolveMaterialLifecyclePassed = dissolveMaterialLifecycle,
                    dissolveShadowTimingPassed = dissolveShadowTiming,
                    actorZeroAffineOracle =
                        actorZeroAffineOracle,
                    visualAdmission = false,
                    passed = true,
                };
                string absoluteReport = RepoRelativeToAbsolute(ReportPath);
                Directory.CreateDirectory(Path.GetDirectoryName(absoluteReport));
                File.WriteAllText(absoluteReport, JsonUtility.ToJson(report, true) + "\n", Encoding.UTF8);
            }
            Debug.Log(
                "Validated source-closed Zhuangfy Actor camera/animation plus " +
                "16-track Effect gacha Timeline runtime and three exact " +
                "VFXFollowBoneTool carriers.");
        }

        private static bool ValidateFollowBoneSourcePartition(
            GameObject prefab,
            Dictionary<string, object> particleContract,
            EndfieldRecoveredVFXFollowBoneTool[] carriers)
        {
            if (prefab == null || particleContract == null ||
                carriers == null ||
                carriers.Length != ExpectedFollowBoneSpecs.Length)
                return false;
            Transform effect = prefab.transform.Find("Effect");
            if (effect == null)
                return false;

            string[] expectedEffectChildren =
                ExpectedFollowBoneSpecs.Select(value => value.carrierName)
                    .Concat(ExpectedDirectEffectParticleChildren)
                    .OrderBy(value => value, StringComparer.Ordinal)
                    .ToArray();
            string[] actualEffectChildren = effect.Cast<Transform>()
                .Select(value => value.name)
                .OrderBy(value => value, StringComparer.Ordinal)
                .ToArray();
            if (!actualEffectChildren.SequenceEqual(expectedEffectChildren))
                return false;

            Dictionary<string, Dictionary<string, object>> sourceRoots =
                List(particleContract["roots"]).Cast<object>()
                    .Select(Dict)
                    .Where(value =>
                        Str(value, "inventoryKind") ==
                            "particle_effect")
                    .ToDictionary(
                        value => Str(value, "effectRoot"),
                        StringComparer.Ordinal);
            if (sourceRoots.Count != 6)
                return false;

            foreach (FollowBoneSpec spec in ExpectedFollowBoneSpecs)
            {
                EndfieldRecoveredVFXFollowBoneTool carrier =
                    carriers.SingleOrDefault(value =>
                        value.sourceCarrierTransformPathId ==
                            spec.carrierTransformPathId);
                Transform attach =
                    prefab.transform.Find(spec.exactAttachPath);
                if (carrier == null ||
                    carrier.transform.parent != effect ||
                    carrier.name != spec.carrierName ||
                    carrier.bindingRoot != prefab.transform ||
                    carrier.attachNode != attach ||
                    carrier.exactAttachPath != spec.exactAttachPath ||
                    carrier.followRotation != spec.followRotation ||
                    carrier.sourceCarrierGameObjectPathId !=
                        spec.carrierGameObjectPathId ||
                    carrier.sourceActorGameObjectPathId !=
                        spec.actorGameObjectPathId ||
                    carrier.sourceAttachTransformPathId !=
                        spec.attachTransformPathId ||
                    !carrier.exactSourceChildren.SequenceEqual(
                        spec.children) ||
                    !Approximately(
                        carrier.transform.localPosition,
                        spec.authoredLocalPosition) ||
                    Math.Abs(Quaternion.Dot(
                        carrier.transform.localRotation,
                        spec.authoredLocalRotation)) < 0.9999999f ||
                    carrier.transform.localScale != Vector3.one ||
                    !carrier.transform.Cast<Transform>()
                        .Select(value => value.name)
                        .SequenceEqual(spec.children))
                    return false;
                foreach (string child in spec.children)
                {
                    if (!sourceRoots.TryGetValue(
                            child,
                            out Dictionary<string, object> sourceRoot) ||
                        SourceEffectRootFatherTransformPathId(sourceRoot) !=
                            spec.carrierTransformPathId)
                        return false;
                }
            }
            foreach (string direct in
                ExpectedDirectEffectParticleChildren)
            {
                if (!sourceRoots.TryGetValue(
                        direct,
                        out Dictionary<string, object> sourceRoot) ||
                    SourceEffectRootFatherTransformPathId(sourceRoot) !=
                        SourceEffectTransformPathId ||
                    effect.Find(direct) == null)
                    return false;
            }
            return true;
        }

        private static bool ValidateFollowBoneRuntime(
            GameObject prefab,
            out bool missingBindingFailClosed,
            out bool unrelatedRootsUnmoved)
        {
            missingBindingFailClosed = false;
            unrelatedRootsUnmoved = false;
            GameObject instance =
                UnityEngine.Object.Instantiate(prefab);
            instance.name = "Zhuangfy_Gacha_VFXFollowBone_Validation";
            try
            {
                EndfieldRecoveredZhuangfyGachaRuntime runtime =
                    instance.GetComponent<
                        EndfieldRecoveredZhuangfyGachaRuntime>();
                if (runtime != null)
                    runtime.autoStartRecoveredEffect = false;
                Transform effect = instance.transform.Find("Effect");
                if (effect == null)
                    return false;
                Transform[] unrelated =
                    ExpectedDirectEffectParticleChildren.Select(
                        effect.Find).ToArray();
                if (unrelated.Any(value => value == null))
                    return false;
                Vector3[] unrelatedPositions =
                    unrelated.Select(value => value.position).ToArray();
                Quaternion[] unrelatedRotations =
                    unrelated.Select(value => value.rotation).ToArray();
                Transform[] unrelatedParents =
                    unrelated.Select(value => value.parent).ToArray();

                EndfieldRecoveredVFXFollowBoneTool[] carriers =
                    instance.GetComponentsInChildren<
                        EndfieldRecoveredVFXFollowBoneTool>(true);
                bool runtimePassed =
                    carriers.Length ==
                        ExpectedFollowBoneSpecs.Length;
                for (int index = 0;
                    runtimePassed &&
                    index < ExpectedFollowBoneSpecs.Length;
                    index++)
                {
                    FollowBoneSpec spec =
                        ExpectedFollowBoneSpecs[index];
                    EndfieldRecoveredVFXFollowBoneTool carrier =
                        carriers.SingleOrDefault(value =>
                            value.sourceCarrierTransformPathId ==
                                spec.carrierTransformPathId);
                    Transform attach =
                        instance.transform.Find(spec.exactAttachPath);
                    if (carrier == null || attach == null ||
                        !attach.gameObject.activeInHierarchy ||
                        !Approximately(
                            carrier.transform.localPosition,
                            spec.authoredLocalPosition) ||
                        Math.Abs(Quaternion.Dot(
                            carrier.transform.localRotation,
                            spec.authoredLocalRotation)) <
                            0.9999999f)
                    {
                        runtimePassed = false;
                        break;
                    }

                    attach.position = new Vector3(
                        10.25f + index,
                        -20.5f - index,
                        30.75f + index * 2.0f);
                    attach.rotation = Quaternion.Euler(
                        11.0f + index,
                        37.0f + index * 3.0f,
                        -19.0f - index);
                    Quaternion authoredWorldRotation =
                        carrier.transform.rotation;
                    if (!carrier.UpdatePositionNow() ||
                        !carrier.ContractResolved ||
                        !Approximately(
                            carrier.transform.position,
                            attach.position) ||
                        (spec.followRotation
                            ? Math.Abs(Quaternion.Dot(
                                carrier.transform.rotation,
                                attach.rotation)) < 0.9999999f
                            : Math.Abs(Quaternion.Dot(
                                carrier.transform.rotation,
                                authoredWorldRotation)) < 0.9999999f))
                    {
                        runtimePassed = false;
                        break;
                    }

                    Vector3 firstPosition =
                        carrier.transform.position;
                    Quaternion firstRotation =
                        carrier.transform.rotation;
                    if (!carrier.UpdatePositionNow() ||
                        !SameBits(
                            carrier.transform.position,
                            firstPosition) ||
                        !SameBits(
                            carrier.transform.rotation,
                            firstRotation))
                    {
                        runtimePassed = false;
                        break;
                    }
                }

                EndfieldRecoveredVFXFollowBoneTool missingCarrier =
                    carriers.Single(value =>
                        value.sourceCarrierTransformPathId ==
                            ExpectedFollowBoneSpecs[0]
                                .carrierTransformPathId);
                Transform exactAttach = missingCarrier.attachNode;
                Vector3 beforeMissingPosition =
                    missingCarrier.transform.position;
                Quaternion beforeMissingRotation =
                    missingCarrier.transform.rotation;
                missingCarrier.attachNode = null;
                bool missingPassed =
                    !missingCarrier.UpdatePositionNow() &&
                    missingCarrier.ContractState ==
                        EndfieldRecoveredVFXFollowBoneTool
                            .MissingAttachNodeState &&
                    SameBits(
                        missingCarrier.transform.position,
                        beforeMissingPosition) &&
                    SameBits(
                        missingCarrier.transform.rotation,
                        beforeMissingRotation);
                missingCarrier.attachNode = exactAttach;
                bool activeSelf = exactAttach.gameObject.activeSelf;
                exactAttach.gameObject.SetActive(false);
                Vector3 beforeInactivePosition =
                    missingCarrier.transform.position;
                Quaternion beforeInactiveRotation =
                    missingCarrier.transform.rotation;
                bool inactivePassed =
                    !missingCarrier.UpdatePositionNow() &&
                    missingCarrier.ContractState ==
                        EndfieldRecoveredVFXFollowBoneTool
                            .InactiveAttachNodeState &&
                    SameBits(
                        missingCarrier.transform.position,
                        beforeInactivePosition) &&
                    SameBits(
                        missingCarrier.transform.rotation,
                        beforeInactiveRotation);
                exactAttach.gameObject.SetActive(activeSelf);
                missingBindingFailClosed =
                    missingPassed && inactivePassed;

                unrelatedRootsUnmoved = unrelated
                    .Select((value, index) =>
                        value.parent == unrelatedParents[index] &&
                        SameBits(
                            value.position,
                            unrelatedPositions[index]) &&
                        SameBits(
                            value.rotation,
                            unrelatedRotations[index]))
                    .All(value => value);
                return runtimePassed &&
                    missingBindingFailClosed &&
                    unrelatedRootsUnmoved;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static bool ValidateActorAnimationTimeline(
            GameObject prefab,
            TimelineAsset actorTimeline,
            out ActorZeroAffineOracle oracle)
        {
            oracle = null;
            if (prefab == null || actorTimeline == null)
                return false;
            List<AnimationTrack> tracks =
                actorTimeline.GetOutputTracks()
                    .OfType<AnimationTrack>().ToList();
            if (tracks.Count != ExpectedActorAnimationTracks.Length)
                return false;
            Transform prefabActor = prefab.transform.Find("Actor");
            PlayableDirector prefabDirector = prefabActor == null
                ? null
                : prefabActor.GetComponent<PlayableDirector>();
            if (prefabDirector == null)
                return false;
            foreach (ActorAnimationTrackSpec spec in
                ExpectedActorAnimationTracks)
            {
                AnimationTrack track =
                    tracks.SingleOrDefault(value =>
                        value.name == spec.trackName);
                Transform binding =
                    prefab.transform.Find(spec.bindingPath);
                Animator animator = binding == null
                    ? null
                    : binding.GetComponent<Animator>();
                TimelineClip[] clips = track == null
                    ? Array.Empty<TimelineClip>()
                    : track.GetClips().ToArray();
                if (track == null || binding == null ||
                    animator == null ||
                    animator.runtimeAnimatorController != null ||
                    prefabDirector.GetGenericBinding(track) != animator ||
                    clips.Length != 2 ||
                    !ValidateGeneratedActorTimelineClip(
                        clips[0],
                        spec.entrance,
                        0.0,
                        10.7) ||
                    !ValidateGeneratedActorTimelineClip(
                        clips[1],
                        spec.loop,
                        10.7,
                        3.3333333333333335))
                {
                    return false;
                }
            }

            GameObject instance =
                UnityEngine.Object.Instantiate(prefab);
            instance.name =
                "Zhuangfy_Gacha_ActorAnimation_Validation";
            try
            {
                EndfieldRecoveredZhuangfyGachaRuntime runtime =
                    instance.GetComponent<
                        EndfieldRecoveredZhuangfyGachaRuntime>();
                if (runtime == null)
                    return false;
                runtime.autoStartRecoveredEffect = false;
                if (!runtime.BeginRecoveredEffectStart(10.0f) ||
                    !Approximately(runtime.actorCameraDirector.time, 0.0) ||
                    !Approximately(runtime.director.time, 0.0))
                {
                    return false;
                }
                Transform actor = instance.transform.Find("Actor");
                Transform deco1 = instance.transform.Find(
                    "Actor/RecoveredProps/chr_0030_zhuangfy_deco_1");
                Transform joint = instance.transform.Find(
                    ExpectedFollowBoneSpecs[0].exactAttachPath);
                Transform effect = instance.transform.Find("Effect");
                EndfieldRecoveredVFXFollowBoneTool carrier =
                    instance.GetComponentsInChildren<
                        EndfieldRecoveredVFXFollowBoneTool>(true)
                        .SingleOrDefault(value =>
                            value.sourceCarrierTransformPathId ==
                                ExpectedFollowBoneSpecs[0]
                                    .carrierTransformPathId);
                Transform dianRoot = carrier == null
                    ? null
                    : carrier.transform.Find(
                        "P_fxui_zhuangfy_ui_overview_start_01_trail01");
                ParticleSystemRenderer[] dianRenderers =
                    dianRoot == null
                        ? Array.Empty<ParticleSystemRenderer>()
                        : dianRoot.GetComponentsInChildren<
                            ParticleSystemRenderer>(true)
                            .Where(value =>
                                value.sharedMaterial != null &&
                                value.sharedMaterial.name ==
                                    "M_fx_ui_dian_904")
                            .ToArray();
                TimelineAsset effectTimeline =
                    runtime.director.playableAsset as TimelineAsset;
                ControlTrack dianControlTrack =
                    effectTimeline == null
                        ? null
                        : effectTimeline.GetOutputTracks()
                            .OfType<ControlTrack>()
                            .SingleOrDefault(value =>
                                value.name == "Control Track (1)");
                TimelineClip dianControlClip =
                    dianControlTrack == null
                        ? null
                        : dianControlTrack.GetClips().SingleOrDefault();
                ControlPlayableAsset dianControlAsset =
                    dianControlClip == null
                        ? null
                        : dianControlClip.asset as
                            ControlPlayableAsset;
                GameObject dianControlTarget =
                    dianControlAsset == null
                        ? null
                        : dianControlAsset.sourceGameObject.Resolve(
                            runtime.director);
                if (actor == null || deco1 == null || joint == null ||
                    effect == null || carrier == null ||
                    dianRoot == null || dianRenderers.Length != 1 ||
                    dianControlTrack == null ||
                    dianControlClip == null ||
                    dianControlAsset == null ||
                    dianControlTarget == null ||
                    !carrier.UpdatePositionNow())
                {
                    return false;
                }

                Dictionary<string, object> manifest =
                    LoadJson(AssetPathToAbsolute(
                        ZhuangfyManifestAssetPath));
                Dictionary<string, object> mapping =
                    List(manifest["clips"]).Cast<object>()
                        .Select(Dict).Single(value =>
                            Str(value, "name") ==
                                "A_item_widget_zhuangfy_gacha");
                Dictionary<string, object> jointBone =
                    List(mapping["bones"]).Cast<object>()
                        .Select(Dict).Single(value =>
                            Str(value, "path") ==
                                "RecoveredProps/" +
                                "chr_0030_zhuangfy_deco_1/" +
                                "Root/Zhuangfy_F_a_01_jnt");
                int trackIndex =
                    Int(jointBone, "track_index");
                Dictionary<string, object> sample =
                    LoadJson(RepoRelativeToAbsolute(
                        ExpectedActorAnimationTracks[1]
                            .entrance.sourceSampleRepoPath));
                Dictionary<string, object> firstTrack =
                    Dict(List(Dict(List(sample["frames"])[0])["tracks"])
                        [trackIndex]);
                float[] expectedPosition =
                    FloatList(firstTrack["translation"]);
                float[] expectedRotation =
                    FloatList(firstTrack["rotation"]);
                float[] expectedScale =
                    FloatList(firstTrack["scale"]);
                bool jointBits =
                    expectedPosition.Length == 3 &&
                    expectedRotation.Length == 4 &&
                    expectedScale.Length == 3 &&
                    SameBits(
                        joint.localPosition,
                        new Vector3(
                            expectedPosition[0],
                            expectedPosition[1],
                            expectedPosition[2])) &&
                    SameBits(
                        joint.localRotation,
                        new Quaternion(
                            expectedRotation[0],
                            expectedRotation[1],
                            expectedRotation[2],
                            expectedRotation[3])) &&
                    SameBits(
                        joint.localScale,
                        new Vector3(
                            expectedScale[0],
                            expectedScale[1],
                            expectedScale[2]));
                bool carrierPosition =
                    SameBits(
                        carrier.transform.position,
                        joint.position);
                double dianControlLocalTime =
                    dianControlClip.ToLocalTime(runtime.director.time);
                float dianControlLocalTimeFloat32 =
                    (float)dianControlLocalTime;
                bool dianControlClipExact =
                    dianControlClip.displayName ==
                        "P_fxui_zhuangfy_ui_overview_start_01_trail01" &&
                    Approximately(dianControlClip.start, 0.0) &&
                    Approximately(
                        dianControlClip.clipIn,
                        0.48333333333333334) &&
                    Approximately(dianControlClip.timeScale, 1.0) &&
                    Approximately(
                        dianControlLocalTime,
                        0.48333333333333334) &&
                    FloatBits(dianControlLocalTimeFloat32) ==
                        unchecked((int)0x3EF77777);
                bool dianControlBindingExact =
                    dianControlTarget.transform == dianRoot &&
                    dianControlAsset.updateParticle &&
                    dianControlAsset.particleRandomSeed == 2292u &&
                    dianControlAsset.updateDirector &&
                    dianControlAsset.updateITimeControl &&
                    dianControlAsset.searchHierarchy &&
                    dianControlAsset.active;
                bool dianParticleDescendant =
                    dianRenderers[0].transform.IsChildOf(
                        dianControlTarget.transform);
                bool dianSameTimeAffineClosed =
                    dianControlClipExact &&
                    dianControlBindingExact &&
                    dianParticleDescendant &&
                    jointBits &&
                    carrierPosition;
                oracle = new ActorZeroAffineOracle
                {
                    authority =
                        "At presentation t=0, exact generated Actor and " +
                        "Effect Timeline Evaluate maps Dian904 Control " +
                        "Track order 1 to clip-local 0.48333333333333334 " +
                        "before the source-closed VFXFollowBoneTool " +
                        "position update",
                    actorTimelineTime =
                        runtime.actorCameraDirector.time,
                    effectTimelineTime = runtime.director.time,
                    dian904ControlTrackOrder = 1,
                    dian904ControlTrackName = dianControlTrack.name,
                    dian904ControlClipName =
                        dianControlClip.displayName,
                    dian904ControlTrackSourcePathId =
                        8970100573188893026L,
                    dian904ControlPlayableSourcePathId =
                        3794251093511809378L,
                    dian904ControlTargetSourceGameObjectPathId =
                        -4881997161974289129L,
                    dian904ControlTargetSourceHierarchy =
                        "gacha_char_zhuangfy/Effect/" +
                        "Zhuangfy_F_a_01_jnt/" +
                        "P_fxui_zhuangfy_ui_overview_start_01_trail01",
                    dian904ControlClipStart = dianControlClip.start,
                    dian904ControlClipIn = dianControlClip.clipIn,
                    dian904ControlClipTimeScale =
                        dianControlClip.timeScale,
                    dian904ControlLocalTime =
                        dianControlLocalTime,
                    dian904ControlLocalTimeFloat32 =
                        dianControlLocalTimeFloat32,
                    dian904ControlLocalTimeFloat32Bits =
                        "0x" + unchecked(
                            (uint)FloatBits(
                                dianControlLocalTimeFloat32))
                            .ToString(
                                "X8",
                                CultureInfo.InvariantCulture),
                    dian904ParticleSystemSourcePathId =
                        -463413735443550953L,
                    dian904RendererSourcePathId =
                        -90150296252994281L,
                    dian904ParticleSourceHierarchy =
                        "gacha_char_zhuangfy/Effect/" +
                        "Zhuangfy_F_a_01_jnt/" +
                        "P_fxui_zhuangfy_ui_overview_start_01_trail01/" +
                        "Trail_01/P_dian_100 (1)",
                    dian904ClipInRuntimeAuditSha256 =
                        Dian904ClipInRuntimeAuditSha256,
                    jointSourceSampleSha256 =
                        ExpectedActorAnimationTracks[1]
                            .entrance.sourceSampleSha256,
                    jointSourceTrackIndex = trackIndex,
                    expectedJointLocalPosition = expectedPosition,
                    expectedJointLocalRotation = expectedRotation,
                    expectedJointLocalScale = expectedScale,
                    runtimeRoot = SnapshotAffine(
                        instance.transform,
                        instance.transform),
                    actor = SnapshotAffine(
                        instance.transform,
                        actor),
                    deco1 = SnapshotAffine(
                        instance.transform,
                        deco1),
                    joint = SnapshotAffine(
                        instance.transform,
                        joint),
                    effect = SnapshotAffine(
                        instance.transform,
                        effect),
                    carrier = SnapshotAffine(
                        instance.transform,
                        carrier.transform),
                    dian904EffectRoot = SnapshotAffine(
                        instance.transform,
                        dianRoot),
                    dian904Renderer = SnapshotAffine(
                        instance.transform,
                        dianRenderers[0].transform),
                    jointSampleBitsExact = jointBits,
                    carrierWorldPositionExact =
                        carrierPosition,
                    dian904ChainResolved =
                        dianRenderers[0].transform.IsChildOf(
                            carrier.transform),
                    dian904ControlClipExact =
                        dianControlClipExact,
                    dian904ControlBindingExact =
                        dianControlBindingExact,
                    dian904ParticleDescendantOfControlTarget =
                        dianParticleDescendant,
                    dian904ClipInSchedulerAuditPinned = true,
                    dian904SameTimeLiveParticleAffineClosed =
                        dianSameTimeAffineClosed,
                    visualAdmission = false,
                };
                return jointBits &&
                    carrierPosition &&
                    oracle.dian904ChainResolved &&
                    dianSameTimeAffineClosed;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static bool ValidateGeneratedActorTimelineClip(
            TimelineClip clip,
            ActorAnimationClipSpec spec,
            double start,
            double duration)
        {
            AnimationPlayableAsset playable =
                clip == null
                    ? null
                    : clip.asset as AnimationPlayableAsset;
            return clip != null &&
                playable != null &&
                playable.clip != null &&
                playable.clip.name == spec.generatedAssetName &&
                !playable.clip.legacy &&
                clip.displayName == spec.clipName &&
                Approximately(clip.start, start) &&
                Approximately(clip.duration, duration) &&
                Approximately(clip.clipIn, 0.0) &&
                Approximately(clip.timeScale, 1.0) &&
                Approximately(clip.easeInDuration, 0.0) &&
                Approximately(clip.easeOutDuration, 0.0) &&
                playable.removeStartOffset &&
                playable.applyFootIK &&
                playable.clip.isLooping == spec.loop &&
                playable.loop ==
                    AnimationPlayableAsset.LoopMode.UseSourceAsset;
        }

        private static AffineSnapshot SnapshotAffine(
            Transform root,
            Transform value)
        {
            return new AffineSnapshot
            {
                hierarchy = TransformPath(root, value),
                localPosition = new[]
                {
                    value.localPosition.x,
                    value.localPosition.y,
                    value.localPosition.z,
                },
                localRotation = new[]
                {
                    value.localRotation.x,
                    value.localRotation.y,
                    value.localRotation.z,
                    value.localRotation.w,
                },
                localScale = new[]
                {
                    value.localScale.x,
                    value.localScale.y,
                    value.localScale.z,
                },
                worldPosition = new[]
                {
                    value.position.x,
                    value.position.y,
                    value.position.z,
                },
                worldRotation = new[]
                {
                    value.rotation.x,
                    value.rotation.y,
                    value.rotation.z,
                    value.rotation.w,
                },
                localToWorldRowMajor =
                    MatrixRowMajor(value.localToWorldMatrix),
                worldToLocalRowMajor =
                    MatrixRowMajor(value.worldToLocalMatrix),
            };
        }

        private static float[] MatrixRowMajor(Matrix4x4 value)
        {
            return new[]
            {
                value.m00, value.m01, value.m02, value.m03,
                value.m10, value.m11, value.m12, value.m13,
                value.m20, value.m21, value.m22, value.m23,
                value.m30, value.m31, value.m32, value.m33,
            };
        }

        private static string TransformPath(
            Transform root,
            Transform value)
        {
            var names = new List<string>();
            for (Transform current = value;
                current != null;
                current = current.parent)
            {
                names.Add(current.name);
                if (current == root)
                    break;
            }
            names.Reverse();
            return string.Join("/", names);
        }

        private static bool ValidateActorCameraDeclaredPair(
            GameObject prefab,
            Dictionary<string, object> cameraRecord,
            out bool isolationPassed)
        {
            isolationPassed = false;
            GameObject instance =
                UnityEngine.Object.Instantiate(prefab);
            instance.name =
                "Zhuangfy_Gacha_ActorCamera_Validation";
            try
            {
                Transform actor = instance.transform.Find("Actor");
                Transform external =
                    instance.transform.Find("ExternalCamera");
                PlayableDirector actorDirector = actor == null
                    ? null
                    : actor.GetComponent<PlayableDirector>();
                EndfieldRecoveredZhuangfyExternalCameraPlayback playback =
                    external == null
                        ? null
                        : external.GetComponent<
                            EndfieldRecoveredZhuangfyExternalCameraPlayback>();
                Camera camera = external == null
                    ? null
                    : external.GetComponent<Camera>();
                Camera[] cameras =
                    instance.GetComponentsInChildren<Camera>(true);
                isolationPassed =
                    actorDirector != null &&
                    playback != null &&
                    camera != null &&
                    playback.sourceCamera == camera &&
                    playback.keepSourceCameraDisabled &&
                    !camera.enabled &&
                    cameras.Length == 1 &&
                    cameras[0] == camera;
                if (!isolationPassed)
                    return false;

                Dictionary<string, object> pair =
                    Dict(cameraRecord["declaredProbePair"]);
                actorDirector.RebuildGraph();
                if (!SampleActorCameraBits(
                    actorDirector,
                    playback,
                    external,
                    camera,
                    Double(pair, "previousTime"),
                    StringList(pair["previousPositionBits"]),
                    StringList(pair["previousRotationBits"]),
                    Str(pair, "previousFovBits")))
                    return false;
                if (!SampleActorCameraBits(
                    actorDirector,
                    playback,
                    external,
                    camera,
                    Double(pair, "currentTime"),
                    StringList(pair["currentPositionBits"]),
                    StringList(pair["currentRotationBits"]),
                    Str(pair, "currentFovBits")))
                    return false;
                return !camera.enabled;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static bool SampleActorCameraBits(
            PlayableDirector director,
            EndfieldRecoveredZhuangfyExternalCameraPlayback playback,
            Transform externalCamera,
            Camera camera,
            double time,
            string[] positionBits,
            string[] rotationBits,
            string fovBits)
        {
            if (positionBits.Length != 3 || rotationBits.Length != 4)
                return false;
            if (!playback.sourceClip.Evaluate(
                time,
                out Vector3 expectedPosition,
                out Quaternion expectedRotation,
                out float expectedFov))
                return false;
            bool exactCurveBits =
                FloatBits(expectedPosition.x) ==
                    ParseHexBits(positionBits[0]) &&
                FloatBits(expectedPosition.y) ==
                    ParseHexBits(positionBits[1]) &&
                FloatBits(expectedPosition.z) ==
                    ParseHexBits(positionBits[2]) &&
                FloatBits(expectedRotation.x) ==
                    ParseHexBits(rotationBits[0]) &&
                FloatBits(expectedRotation.y) ==
                    ParseHexBits(rotationBits[1]) &&
                FloatBits(expectedRotation.z) ==
                    ParseHexBits(rotationBits[2]) &&
                FloatBits(expectedRotation.w) ==
                    ParseHexBits(rotationBits[3]) &&
                FloatBits(expectedFov) == ParseHexBits(fovBits);
            if (!exactCurveBits)
                return false;
            director.time = time;
            director.Evaluate();
            Vector3 position = externalCamera.localPosition;
            Quaternion rotation = externalCamera.localRotation;
            // Transform stores rotations through Unity's native normalized
            // quaternion path and may rewrite an already normalized component
            // by one ULP. Exact bit identity is asserted above at the decoded
            // clip boundary; here assert that Timeline applied the same pose.
            return Approximately(position.x, expectedPosition.x) &&
                Approximately(position.y, expectedPosition.y) &&
                Approximately(position.z, expectedPosition.z) &&
                Math.Abs(Quaternion.Dot(
                    rotation,
                    expectedRotation)) >= 0.9999999 &&
                FloatBits(camera.fieldOfView) ==
                    FloatBits(expectedFov) &&
                !camera.enabled;
        }

        private static int FloatBits(float value)
        {
            return BitConverter.ToInt32(
                BitConverter.GetBytes(value),
                0);
        }

        private static bool SameBits(Vector3 a, Vector3 b)
        {
            return FloatBits(a.x) == FloatBits(b.x) &&
                FloatBits(a.y) == FloatBits(b.y) &&
                FloatBits(a.z) == FloatBits(b.z);
        }

        private static bool SameBits(Quaternion a, Quaternion b)
        {
            return FloatBits(a.x) == FloatBits(b.x) &&
                FloatBits(a.y) == FloatBits(b.y) &&
                FloatBits(a.z) == FloatBits(b.z) &&
                FloatBits(a.w) == FloatBits(b.w);
        }

        private static int ParseHexBits(string value)
        {
            Require(
                !string.IsNullOrWhiteSpace(value) &&
                value.StartsWith("0x", StringComparison.Ordinal) &&
                value.Length == 10,
                "Camera probe bit literal changed");
            return unchecked((int)uint.Parse(
                value.Substring(2),
                NumberStyles.AllowHexSpecifier,
                CultureInfo.InvariantCulture));
        }

        private static AnimationCurve SourceCurve(Dictionary<string, object> source)
        {
            var curve = new AnimationCurve();
            foreach (object keyObject in List(source["m_Curve"]))
            {
                Dictionary<string, object> key = Dict(keyObject);
                var frame = new Keyframe(
                    Float(key, "time"),
                    Float(key, "value"),
                    Float(key, "inSlope"),
                    Float(key, "outSlope"),
                    Float(key, "inWeight"),
                    Float(key, "outWeight"))
                {
                    weightedMode = (WeightedMode)Int(key, "weightedMode"),
                };
                curve.AddKey(frame);
            }
            curve.preWrapMode = WrapMode.ClampForever;
            curve.postWrapMode = WrapMode.ClampForever;
            Require(curve.length > 0, "Source curve is empty");
            return curve;
        }

        private static T FindGeneratedAssetByPathId<T>(string root, long pathId)
            where T : UnityEngine.Object
        {
            string suffix = "_p" + unchecked((ulong)pathId).ToString("X16", CultureInfo.InvariantCulture);
            string[] matches = AssetDatabase.FindAssets("t:" + typeof(T).Name, new[] { root })
                .Select(AssetDatabase.GUIDToAssetPath)
                .Where(path => Path.GetFileNameWithoutExtension(path).EndsWith(suffix, StringComparison.Ordinal))
                .ToArray();
            Require(matches.Length == 1, $"Expected one {typeof(T).Name} for PathID {pathId}, found {matches.Length}");
            return AssetDatabase.LoadAssetAtPath<T>(matches[0]);
        }

        private static Type RendererType(string name)
        {
            switch (name)
            {
                case "MeshRenderer": return typeof(MeshRenderer);
                case "ParticleSystemRenderer": return typeof(ParticleSystemRenderer);
                case "SkinnedMeshRenderer": return typeof(SkinnedMeshRenderer);
                default: throw new InvalidDataException("Unsupported renderer binding type " + name);
            }
        }

        private static Vector4 Vec4(Dictionary<string, object> value)
        {
            return new Vector4(Float(value, "x"), Float(value, "y"), Float(value, "z"), Float(value, "w"));
        }

        private static Color Color(Dictionary<string, object> value)
        {
            return new Color(Float(value, "r"), Float(value, "g"), Float(value, "b"), Float(value, "a"));
        }

        private static bool Approximately(double a, double b)
        {
            return Math.Abs(a - b) <= 1.0e-6;
        }

        private static bool Approximately(Vector3 a, Vector3 b)
        {
            return Approximately(a.x, b.x) &&
                Approximately(a.y, b.y) &&
                Approximately(a.z, b.z);
        }

        private static Dictionary<string, object> LoadJson(string path)
        {
            return Dict(ManifestMiniJson.Deserialize(File.ReadAllText(path, Encoding.UTF8)));
        }

        private static string Sha256(string path)
        {
            using (var stream = File.OpenRead(path))
            using (var hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "");
        }

        private static string AssetPathToAbsolute(string assetPath)
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", assetPath));
        }

        private static string RepoRelativeToAbsolute(string relative)
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", relative));
        }

        private static void EnsureFolder(string assetPath)
        {
            string current = "Assets";
            foreach (string segment in assetPath.Split('/').Skip(1))
            {
                string next = current + "/" + segment;
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segment);
                current = next;
            }
        }

        private static string Safe(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
                value = value.Replace(invalid, '_');
            return value;
        }

        private static Dictionary<string, object> Dict(object value)
        {
            return value as Dictionary<string, object> ?? new Dictionary<string, object>();
        }

        private static IList List(object value)
        {
            return value as IList ?? Array.Empty<object>();
        }

        private static string Str(object value)
        {
            return value == null ? "" : Convert.ToString(value, CultureInfo.InvariantCulture) ?? "";
        }

        private static string Str(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) ? Str(item) : "";
        }

        private static int Int(object value)
        {
            return value == null ? 0 : Convert.ToInt32(value, CultureInfo.InvariantCulture);
        }

        private static int Int(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) ? Int(item) : 0;
        }

        private static long Long(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) && item != null
                ? Convert.ToInt64(item, CultureInfo.InvariantCulture)
                : 0L;
        }

        private static float Float(object value)
        {
            return value == null ? 0f : Convert.ToSingle(value, CultureInfo.InvariantCulture);
        }

        private static float Float(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) ? Float(item) : 0f;
        }

        private static double Double(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) && item != null
                ? Convert.ToDouble(item, CultureInfo.InvariantCulture)
                : 0.0;
        }

        private static bool Bool(Dictionary<string, object> value, string key)
        {
            return value.TryGetValue(key, out object item) && item != null &&
                Convert.ToInt32(item, CultureInfo.InvariantCulture) != 0;
        }

        private static int[] IntList(object value)
        {
            return List(value).Cast<object>().Select(Int).ToArray();
        }

        private static float[] FloatList(object value)
        {
            return List(value).Cast<object>().Select(Float).ToArray();
        }

        private static string[] StringList(object value)
        {
            return List(value).Cast<object>().Select(Str).ToArray();
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidDataException(message);
        }
    }
}
