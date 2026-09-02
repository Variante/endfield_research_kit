using System;
using System.Globalization;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-authenticated owner for the selected Endminf M27 c26.xy pair.
    /// The Resource is intentionally absent until a raw inventoried retail
    /// session passes the maintained Python promoter.
    /// </summary>
    public sealed class EndfieldRecoveredM27GlobalMipBiasSource
    {
        public const string ResourceName =
            "EndfieldRecoveredM27/endminf_m27_global_mip_bias_source";
        public const string PayloadSchema =
            "endfield.endminf-m27-global-mip-bias-unity-source.v1";
        public const string PayloadStatus = "source_authenticated_for_c26_only";
        public const string StaticContractSha256 =
            "3206c46847f98c7821b800aa52b3792ebf8cf7622ab1054ce21f51f872a7e1d3";
        public const string RendererPathId = "59284134265994738";

        private const uint ExpectedGlobalMipBiasBits = 0xbf800000u;
        private const uint ExpectedGlobalMipBiasPow2Bits = 0x3f000000u;

        [Serializable]
        private sealed class Payload
        {
            public string schema;
            public string status;
            public string sourceSession;
            public string sourceReportSha256;
            public string receiptSha256;
            public string runtimePackageSha256;
            public string staticContractSha256;
            public string rendererPathId;
            public string materialMipBiasBits;
            public string dynamicTermBits;
            public string globalMipBiasBits;
            public string publishedC26YBits;
            public bool canPopulatePhysicalCameraMipBiasSource;
            public bool presentationAuthority;
        }

        private bool loaded;
        private bool ready;
        private float globalMipBias;
        private string diagnostic;

        public bool TryGetGlobalMipBias(
            out float value,
            out string failure)
        {
            EnsureLoaded();
            value = ready ? globalMipBias : 0.0f;
            failure = ready ? null : diagnostic;
            return ready;
        }

        private void EnsureLoaded()
        {
            if (loaded)
                return;
            loaded = true;
            TextAsset source = Resources.Load<TextAsset>(ResourceName);
            if (source == null)
            {
                diagnostic =
                    "authenticated Endminf M27 global-mip-bias Resource is absent";
                return;
            }
            ready = TryValidatePayloadJson(
                source.text,
                out globalMipBias,
                out diagnostic);
        }

        public static bool TryValidatePayloadJson(
            string json,
            out float value,
            out string failure)
        {
            value = 0.0f;
            failure = null;
            if (string.IsNullOrWhiteSpace(json))
            {
                failure = "M27 global-mip-bias source payload is empty";
                return false;
            }
            Payload payload;
            try
            {
                payload = JsonUtility.FromJson<Payload>(json);
            }
            catch (Exception exception)
            {
                failure =
                    "M27 global-mip-bias source JSON is invalid: " +
                    exception.Message;
                return false;
            }
            if (payload == null ||
                !string.Equals(payload.schema, PayloadSchema,
                    StringComparison.Ordinal) ||
                !string.Equals(payload.status, PayloadStatus,
                    StringComparison.Ordinal))
            {
                failure = "M27 global-mip-bias source schema/status mismatch";
                return false;
            }
            if (string.IsNullOrWhiteSpace(payload.sourceSession) ||
                !IsLowerHex(payload.sourceReportSha256, 64) ||
                !IsLowerHex(payload.receiptSha256, 64) ||
                !IsLowerHex(payload.runtimePackageSha256, 64) ||
                !string.Equals(
                    payload.staticContractSha256,
                    StaticContractSha256,
                    StringComparison.Ordinal) ||
                !string.Equals(
                    payload.rendererPathId,
                    RendererPathId,
                    StringComparison.Ordinal))
            {
                failure = "M27 global-mip-bias source identity/hash gate failed";
                return false;
            }
            if (!payload.canPopulatePhysicalCameraMipBiasSource ||
                payload.presentationAuthority)
            {
                failure = "M27 global-mip-bias source authority gate failed";
                return false;
            }
            if (!TryParseBits(payload.materialMipBiasBits, out uint materialBits) ||
                !TryParseBits(payload.dynamicTermBits, out uint dynamicBits) ||
                !TryParseBits(payload.globalMipBiasBits, out uint globalBits) ||
                !TryParseBits(payload.publishedC26YBits, out uint pow2Bits))
            {
                failure = "M27 global-mip-bias source word encoding is invalid";
                return false;
            }
            float material = BitConverter.Int32BitsToSingle(
                unchecked((int)materialBits));
            float dynamicTerm = BitConverter.Int32BitsToSingle(
                unchecked((int)dynamicBits));
            float global = BitConverter.Int32BitsToSingle(
                unchecked((int)globalBits));
            float publishedPow2 = BitConverter.Int32BitsToSingle(
                unchecked((int)pow2Bits));
            if (!IsFinite(material) || !IsFinite(dynamicTerm) ||
                !IsFinite(global) || !IsFinite(publishedPow2) ||
                FloatBits(material + dynamicTerm) != globalBits ||
                FloatBits(Mathf.Pow(2.0f, global)) != pow2Bits ||
                globalBits != ExpectedGlobalMipBiasBits ||
                pow2Bits != ExpectedGlobalMipBiasPow2Bits)
            {
                failure = "M27 global-mip-bias source equation/selected pair failed";
                return false;
            }
            value = global;
            return true;
        }

        private static bool TryParseBits(string encoded, out uint value)
        {
            value = 0;
            return IsLowerHex(encoded, 8) && uint.TryParse(
                encoded,
                NumberStyles.AllowHexSpecifier,
                CultureInfo.InvariantCulture,
                out value);
        }

        private static bool IsLowerHex(string value, int length)
        {
            if (value == null || value.Length != length)
                return false;
            for (int index = 0; index < value.Length; index++)
            {
                char character = value[index];
                if (!((character >= '0' && character <= '9') ||
                      (character >= 'a' && character <= 'f')))
                    return false;
            }
            return true;
        }

        private static bool IsFinite(float value) =>
            !float.IsNaN(value) && !float.IsInfinity(value);

        private static uint FloatBits(float value) =>
            unchecked((uint)BitConverter.SingleToInt32Bits(value));
    }
}
