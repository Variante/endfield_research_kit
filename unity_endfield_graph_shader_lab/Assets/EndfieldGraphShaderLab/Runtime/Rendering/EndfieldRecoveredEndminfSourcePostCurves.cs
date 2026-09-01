using System;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Evaluates the original streamed scalar curves owned by
    /// A_fx_endminf_ui_overview_02/post (1). The payload is generated from the
    /// hash-gated serialized AnimationClip; no reference-video curve or timing
    /// samples are accepted here.
    /// </summary>
    internal static class EndfieldRecoveredEndminfSourcePostCurves
    {
        internal const string ResourceName =
            "EndfieldEndminfSourcePost/endminf_overview_02_source_post_curves";
        internal const string ExpectedSchema =
            "endfield.endminf-overview-02-source-post-curves.v1";
        internal const string ExpectedSourceClipSha256 =
            "9814b9de92d5af7902b1967c295f98d29327824bdd7b478984527c5ccccd076c";
        internal const string ExpectedPayloadSha256 =
            "044017968e8d7cfe1f291274f29700a9d7bffc2bc18e333fa262d961b5385ace";

        private static SourcePostContract contract;
        private static string contractFailure = string.Empty;
        private static bool loadAttempted;

        [Serializable]
        private sealed class SourcePostContract
        {
            public string schema;
            public SourceClip sourceClip;
            public Target target;
            public Curve[] curves;
            public string runtimeBoundary;
        }

        [Serializable]
        private sealed class SourceClip
        {
            public string name;
            public string path;
            public string sha256;
            public float sampleRate;
            public float startSeconds;
            public float stopSeconds;
            public bool loop;
        }

        [Serializable]
        private sealed class Target
        {
            public string name;
            public long pathCrc32;
        }

        [Serializable]
        private sealed class Curve
        {
            public string role;
            public string storage;
            public string scriptType;
            public long scriptPathId;
            public long pathCrc32;
            public long attributeCrc32;
            public Key[] keys;
        }

        [Serializable]
        private sealed class Key
        {
            public float time;
            public float a;
            public float b;
            public float c;
            public float d;
        }

        public static bool TryEvaluate(
            float elapsed,
            out float chromaticIntensity,
            out float radialIntensity,
            out float radialPower,
            out string failure)
        {
            chromaticIntensity = 0.0f;
            radialIntensity = 0.0f;
            radialPower = 1.0f;
            if (!TryLoad(out failure))
                return false;
            if (!IsFinite(elapsed))
            {
                failure = "source-post elapsed time is not finite";
                return false;
            }

            float time = Mathf.Clamp(
                elapsed,
                contract.sourceClip.startSeconds,
                contract.sourceClip.stopSeconds);
            chromaticIntensity = Evaluate(contract.curves[0], time);
            radialIntensity = Evaluate(contract.curves[1], time);
            radialPower = Evaluate(contract.curves[2], time);
            if (!IsFinite(chromaticIntensity) ||
                !IsFinite(radialIntensity) ||
                !IsFinite(radialPower) ||
                chromaticIntensity < 0.0f ||
                radialIntensity < 0.0f ||
                radialPower <= 0.0f)
            {
                chromaticIntensity = 0.0f;
                radialIntensity = 0.0f;
                radialPower = 1.0f;
                failure = "source-post curve evaluation produced an invalid value";
                return false;
            }
            failure = string.Empty;
            return true;
        }

        private static bool TryLoad(out string failure)
        {
            if (contract != null)
            {
                failure = string.Empty;
                return true;
            }
            if (loadAttempted)
            {
                failure = contractFailure;
                return false;
            }
            loadAttempted = true;

            TextAsset source = Resources.Load<TextAsset>(ResourceName);
            if (source == null)
                return Fail("generated source-post curve payload is unavailable", out failure);
            string normalizedPayload = source.text
                .Replace("\r\n", "\n")
                .Replace("\r", "\n");
            string payloadHash;
            using (SHA256 sha = SHA256.Create())
            {
                payloadHash = BitConverter.ToString(
                        sha.ComputeHash(Encoding.UTF8.GetBytes(normalizedPayload)))
                    .Replace("-", string.Empty)
                    .ToLowerInvariant();
            }
            if (!string.Equals(
                    payloadHash,
                    ExpectedPayloadSha256,
                    StringComparison.Ordinal))
            {
                return Fail(
                    "source-post curve payload hash drifted: " + payloadHash,
                    out failure);
            }

            SourcePostContract parsed =
                JsonUtility.FromJson<SourcePostContract>(normalizedPayload);
            if (!Validate(parsed, out contractFailure))
            {
                failure = contractFailure;
                return false;
            }
            contract = parsed;
            failure = string.Empty;
            return true;
        }

        private static bool Validate(SourcePostContract value, out string failure)
        {
            if (value == null ||
                !string.Equals(value.schema, ExpectedSchema, StringComparison.Ordinal) ||
                value.sourceClip == null ||
                !string.Equals(
                    value.sourceClip.name,
                    "A_fx_endminf_ui_overview_02",
                    StringComparison.Ordinal) ||
                !string.Equals(
                    value.sourceClip.sha256,
                    ExpectedSourceClipSha256,
                    StringComparison.Ordinal) ||
                value.sourceClip.sampleRate != 30.0f ||
                value.sourceClip.startSeconds != 0.0f ||
                value.sourceClip.stopSeconds != 4.6f ||
                value.sourceClip.loop ||
                value.target == null ||
                !string.Equals(value.target.name, "post (1)", StringComparison.Ordinal) ||
                value.target.pathCrc32 != 669740077L ||
                value.curves == null ||
                value.curves.Length != 3)
            {
                failure = "source-post curve payload identity/layout drifted";
                return false;
            }

            if (!ValidateCurve(
                    value.curves[0],
                    "chromaticIntensity",
                    "streamed-cubic-polynomial",
                    "HG.Rendering.Runtime.VFXPPChromaticAberration",
                    6948449919205830506L,
                    2754484623L,
                    5,
                    out failure) ||
                !ValidateCurve(
                    value.curves[1],
                    "radialIntensity",
                    "streamed-cubic-polynomial",
                    "HG.Rendering.Runtime.VFXPPRadialBlur",
                    317588138045017993L,
                    2754484623L,
                    5,
                    out failure) ||
                !ValidateCurve(
                    value.curves[2],
                    "radialPower",
                    "constant",
                    "HG.Rendering.Runtime.VFXPPRadialBlur",
                    317588138045017993L,
                    565374268L,
                    1,
                    out failure))
            {
                return false;
            }
            failure = string.Empty;
            return true;
        }

        private static bool ValidateCurve(
            Curve curve,
            string role,
            string storage,
            string scriptType,
            long scriptPathId,
            long attributeCrc32,
            int keyCount,
            out string failure)
        {
            if (curve == null ||
                !string.Equals(curve.role, role, StringComparison.Ordinal) ||
                !string.Equals(curve.storage, storage, StringComparison.Ordinal) ||
                !string.Equals(curve.scriptType, scriptType, StringComparison.Ordinal) ||
                curve.scriptPathId != scriptPathId ||
                curve.pathCrc32 != 669740077L ||
                curve.attributeCrc32 != attributeCrc32 ||
                curve.keys == null ||
                curve.keys.Length != keyCount)
            {
                failure = "source-post curve identity/layout drifted: " + role;
                return false;
            }
            float previousTime = float.NegativeInfinity;
            foreach (Key key in curve.keys)
            {
                if (key == null ||
                    !IsFinite(key.time) ||
                    !IsFinite(key.a) ||
                    !IsFinite(key.b) ||
                    !IsFinite(key.c) ||
                    !IsFinite(key.d) ||
                    key.time <= previousTime)
                {
                    failure = "source-post curve key drifted: " + role;
                    return false;
                }
                previousTime = key.time;
            }
            failure = string.Empty;
            return true;
        }

        private static float Evaluate(Curve curve, float time)
        {
            Key[] keys = curve.keys;
            if (time <= keys[0].time)
                return keys[0].d;
            if (time >= keys[keys.Length - 1].time)
                return keys[keys.Length - 1].d;
            int index = 0;
            for (int candidate = 1; candidate < keys.Length; candidate++)
            {
                if (time < keys[candidate].time)
                    break;
                index = candidate;
            }
            Key key = keys[index];
            float delta = time - key.time;
            return ((key.a * delta + key.b) * delta + key.c) * delta + key.d;
        }

        private static bool Fail(string message, out string failure)
        {
            contract = null;
            contractFailure = message;
            failure = message;
            return false;
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }
    }
}
