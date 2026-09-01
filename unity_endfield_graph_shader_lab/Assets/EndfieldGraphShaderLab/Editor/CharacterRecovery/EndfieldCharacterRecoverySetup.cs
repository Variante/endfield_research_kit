using System;
using UnityEditor;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldCharacterRecoverySetup
    {
        private const string WidgetActorsArgument = "-endfield-widget-actors";
        private const string CharacterActorsArgument = "-endfield-character-actors";

        [MenuItem("Endfield/Character Recovery Lab/Build Shared Character Viewer")]
        public static void Build()
        {
            EndfieldManifestCharacterSetup.BuildSharedViewer();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build All Playable Characters (UI Only)")]
        public static void BuildPlayableUi()
        {
            EndfieldManifestCharacterSetup.BuildPlayableCharacterUiViewer();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build All Canonical Characters")]
        public static void BuildAllCharacters()
        {
            // The all-character viewer intentionally reuses existing playable
            // prefabs. Rebuild Endminf's source-owned assets first so that
            // reuse cannot preserve stale body ACL, particle, material, or
            // direct-reference state.
            EndfieldManifestCharacterSetup.RebuildEndminfSourceRecovery();
            EndfieldManifestCharacterSetup.BuildAllCharacterModelViewer();
            EndfieldPlayableCharInfoProfileBuilder.VerifyPortraitOrientation();
        }

        [MenuItem("Endfield/Character Recovery Lab/Import All Generic Actor Prefabs")]
        public static void ImportAllGenericActorPrefabs()
        {
            EndfieldManifestCharacterSetup.ImportAllGenericActorPrefabs();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Canonical Enemy Galleries")]
        public static void BuildEnemyActorGalleries()
        {
            EndfieldManifestCharacterSetup.BuildEnemyActorGalleries();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Ability and Prop Galleries")]
        public static void BuildAbilityPropActorGalleries()
        {
            EndfieldManifestCharacterSetup.BuildAbilityPropActorGalleries();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Ambient NPC Archetype Galleries")]
        public static void BuildAmbientNpcArchetypeGalleries()
        {
            EndfieldManifestCharacterSetup.BuildAmbientNpcArchetypeGalleries();
        }

        [MenuItem("Endfield/Character Recovery Lab/Build All Generic Actor Galleries")]
        public static void BuildAllGenericActorGalleries()
        {
            EndfieldManifestCharacterSetup.BuildAllGenericActorGalleries();
        }

        [MenuItem("Endfield/Character Recovery Lab/Import and Build All Generic Actor Galleries")]
        public static void ImportAndBuildAllGenericActorGalleries()
        {
            EndfieldManifestCharacterSetup.ImportAndBuildAllGenericActorGalleries();
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Generic Actor Source Catalogs")]
        public static void ValidateGenericActorCatalogContracts()
        {
            EndfieldManifestCharacterSetup.ValidateGenericActorCatalogContracts();
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Generic Texture Import Batch")]
        public static void ValidateGenericTextureImportBatchContract()
        {
            EndfieldManifestCharacterSetup.ValidateGenericTextureImportBatchContract();
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Built-in Cube Mesh Recovery")]
        public static void ValidateExplicitBuiltinCubeMeshContract()
        {
            EndfieldManifestCharacterSetup.ValidateExplicitBuiltinCubeMeshContract();
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate All Generic Actor Gallery Scenes")]
        public static void ValidateAllGenericActorGalleryScenes()
        {
            EndfieldManifestCharacterSetup.ValidateAllGenericActorGalleryScenes();
        }

        public static void RefreshSelectedPlayableCharacters()
        {
            string actors = ReadArgument(Environment.GetCommandLineArgs(), CharacterActorsArgument);
            if (string.IsNullOrWhiteSpace(actors))
            {
                throw new ArgumentException(
                    $"Missing {CharacterActorsArgument} <actor[,actor...]>; " +
                    "for example Lizhiyan,Lastrite,Zhuangfy.");
            }
            EndfieldManifestCharacterSetup.RefreshPlayableCharacterAssets(
                actors.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries));
            EndfieldManifestCharacterSetup.UpgradeSharedViewerToAllSourceProfiles();
        }

        [MenuItem("Endfield/Character Recovery Lab/Refresh Selected Playable Widget Animations")]
        public static void RefreshSelectedPlayableWidgetAnimations()
        {
            string actors = ReadArgument(Environment.GetCommandLineArgs(), WidgetActorsArgument);
            if (string.IsNullOrWhiteSpace(actors))
            {
                throw new ArgumentException(
                    $"Missing {WidgetActorsArgument} <actor[,actor...]>; " +
                    "for example pelica,yvonne,dapan.");
            }
            EndfieldManifestCharacterSetup.RefreshPlayableWidgetAnimationAssets(
                actors.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries));
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Shared Viewer Preview")]
        public static void RenderPreview()
        {
            EndfieldManifestCharacterSetup.RenderSharedViewerPreview();
        }

        private static string ReadArgument(string[] arguments, string name)
        {
            for (int index = 0; index + 1 < arguments.Length; index++)
            {
                if (string.Equals(arguments[index], name, StringComparison.OrdinalIgnoreCase))
                    return arguments[index + 1];
            }
            return null;
        }
    }
}
