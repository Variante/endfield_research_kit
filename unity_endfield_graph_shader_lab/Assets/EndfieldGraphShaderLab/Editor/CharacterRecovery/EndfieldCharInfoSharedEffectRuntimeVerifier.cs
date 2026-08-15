using System;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldCharInfoSharedEffectRuntimeVerifier
    {
        private const string StageName =
            "SingleEffects__RecoveredCharacterInfoSharedStage";

        [MenuItem("Endfield/Character Recovery Lab/Verify CharInfo Shared Effect Runtime")]
        public static void Verify()
        {
            GameObject sharedParent = new GameObject("CharInfoSceneRoot__Probe");
            GameObject actor = new GameObject("SelectedActor__Probe");
            GameObject host = new GameObject("Viewer__Probe");
            try
            {
                actor.transform.SetParent(sharedParent.transform, false);
                EndfieldRecoveredCharInfoSharedEffect playback =
                    host.AddComponent<EndfieldRecoveredCharInfoSharedEffect>();
                playback.PlayAfterOverviewAnimator(actor.transform);

                Require(playback.IsSourceClosedAndPlaying,
                    "shared CharEffect did not enter its source-closed playing state");
                Transform stage = sharedParent.transform.Find(StageName);
                Require(stage != null, "shared SingleEffects stage was not created");
                Require(Nearly(stage.localPosition, new Vector3(-0.3f, 0f, 0.05f)),
                    "SingleEffects position drifted");
                Require(Nearly(stage.localScale, new Vector3(0.5f, 1f, 0.5f)),
                    "SingleEffects scale drifted");
                Require(Quaternion.Angle(stage.localRotation, Quaternion.identity) <= 1e-5f,
                    "SingleEffects rotation drifted");

                ParticleSystem[] systems =
                    stage.GetComponentsInChildren<ParticleSystem>(true);
                ParticleSystemRenderer[] renderers =
                    stage.GetComponentsInChildren<ParticleSystemRenderer>(true);
                Require(systems.Length == 2 && renderers.Length == 2,
                    "runtime CharEffect particle topology drifted");
                ParticleSystemRenderer visible =
                    renderers.SingleOrDefault(renderer => renderer.enabled);
                Require(visible != null && visible.sharedMaterials.Length == 1,
                    "runtime trail renderer is not uniquely source-visible");
                Material material = visible.sharedMaterials[0];
                Require(material != null && material.shader != null &&
                    material.shader.name ==
                        "Hidden/Endfield/Recovered/Zhuangfy/VFXRefractMRT" &&
                    material.renderQueue == 3000 &&
                    material.shaderKeywords.SequenceEqual(
                        new[] { "_USE_RBOFFSET" },
                        StringComparer.Ordinal),
                    "runtime trail material gate drifted");

                playback.ClearSharedEffect();
                UnityEngine.Object.DestroyImmediate(host);
                host = null;
                Require(sharedParent.transform.Find(StageName) == null,
                    "shared stage leaked after viewer teardown");
                Debug.Log(
                    "[Endfield CharInfo] shared effect runtime verification passed: " +
                    "stage=(-0.3,0,0.05)/(0.5,1,0.5), particles=2, " +
                    "visibleTrail=1, shader=VFXRefractMRT+_USE_RBOFFSET");
            }
            finally
            {
                if (host != null)
                    UnityEngine.Object.DestroyImmediate(host);
                UnityEngine.Object.DestroyImmediate(actor);
                UnityEngine.Object.DestroyImmediate(sharedParent);
            }
        }

        private static bool Nearly(Vector3 left, Vector3 right) =>
            (left - right).sqrMagnitude <= 1e-10f;

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
