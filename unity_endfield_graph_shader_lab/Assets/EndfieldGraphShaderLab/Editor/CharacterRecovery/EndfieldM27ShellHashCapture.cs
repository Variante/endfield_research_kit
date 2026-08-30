using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Captures and validates the dedicated M27 shell's Unity-compiled D3D11
    /// stage hashes. The native callback substitutes only stage+SHA identities
    /// pinned from a reserved-variant callback-inventory delta.
    /// </summary>
    public static class EndfieldM27ShellHashCapture
    {
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string ShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM27ExactAbiShell.shader";
        private const string OutputEnvironment =
            "ENDFIELD_M27_SHELL_HASH_OUTPUT";
        private const string GenerativeShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM27GenerativeExactAbiShell.shader";
        private const string GenerativeOutputEnvironment =
            "ENDFIELD_M27_GENERATIVE_SHELL_HASH_OUTPUT";
        private const string GenerativePinOutputEnvironment =
            "ENDFIELD_M27_GENERATIVE_SHELL_PIN_OUTPUT";
        private const string ImmutablePacketShellVertexSha256 =
            "b6ffa6a650c43fa86cfed1a146ecdfb046d6c92c7e866ff6f51ac79a6c7d4833";
        private const string ImmutablePacketShellPixelSha256 =
            "9a6803527679aa4d4822ca38a4257c2dafcbce2748a67c7e3387f63e3ee54707";
        private const string M14ShaderAsset =
            "Assets/EndfieldGraphShaderLab/Shaders/Diagnostics/" +
            "EndfieldEndminfM14ExactAbiShell.shader";
        private const string M14OutputEnvironment =
            "ENDFIELD_M14_SHELL_HASH_OUTPUT";

        public static void PreparePinnedRuntimeVariant()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Exact M27 runtime preparation requires Direct3D11.");
            if (Native.GetContractVersion() != 2 ||
                Native.GetM27RegistryReady() != 1)
            {
                throw new InvalidOperationException(
                    "The exact M27 stage+SHA registry is not ready.");
            }
            if (Native.SetM27SubstitutionArmed(1) != 1)
                throw new InvalidOperationException(
                    "The exact M27 compiler route could not be armed.");
            try
            {
                ForceRecompileWhileArmed();
                ForceLoadReservedVariant();
                uint matches = Native.GetM27MatchCount();
                uint vertexSwaps = Native.GetVertexSwapCount();
                uint pixelSwaps = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                // Asset import can request the same reserved variant more
                // than once in a process (for example after a script reload).
                // Validate balanced, complete VS/PS pairs instead of assuming
                // Unity will compile exactly one pair per preparation call.
                if (matches < 2 || vertexSwaps == 0 ||
                    vertexSwaps != pixelSwaps ||
                    matches != vertexSwaps + pixelSwaps || failures != 0)
                {
                    throw new InvalidOperationException(
                        "Exact M27 runtime variant preparation failed: " +
                        $"matches={matches}, vertexSwaps={vertexSwaps}, " +
                        $"pixelSwaps={pixelSwaps}, failures={failures}.");
                }
                Debug.Log(
                    "Prepared exact Endminf M27 runtime variant: " +
                    $"stage+SHA substitutions={matches}, " +
                    $"balancedPairs={vertexSwaps}, VS=10/9, PS=10/5.");
            }
            finally
            {
                Native.SetM27SubstitutionArmed(0);
            }
        }

        public static void PrepareRawRuntimeVariant()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Raw M27 shell preparation requires Direct3D11.");
            Native.SetM27SubstitutionArmed(0);
            ForceRecompileWhileArmed();
            ForceLoadReservedVariant();
            uint matches = Native.GetM27MatchCount();
            uint vertexSwaps = Native.GetVertexSwapCount();
            uint pixelSwaps = Native.GetPixelSwapCount();
            if (matches != 0 || vertexSwaps != 0 || pixelSwaps != 0)
            {
                throw new InvalidOperationException(
                    "Raw M27 shell preparation unexpectedly substituted a " +
                    $"stage: matches={matches}, vertexSwaps={vertexSwaps}, " +
                    $"pixelSwaps={pixelSwaps}.");
            }
            Debug.Log(
                "Prepared unsubstituted Endminf M27 ABI shell control: " +
                "stage+SHA substitutions=0.");
        }

        public static void PrepareGenerativeRawRuntimeVariant()
        {
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                throw new InvalidOperationException(
                    "Raw generative M27 shell preparation requires Direct3D11.");
            Native.SetM27SubstitutionArmed(0);
            uint vertexSwaps = Native.GetVertexSwapCount();
            uint pixelSwaps = Native.GetPixelSwapCount();
            ForceRecompileWhileArmed(GenerativeShaderAsset);
            ForceLoadReservedVariant(GenerativeShaderAsset);
            if (Native.GetVertexSwapCount() != vertexSwaps ||
                Native.GetPixelSwapCount() != pixelSwaps)
            {
                throw new InvalidOperationException(
                    "The unpinned generative M27 shell unexpectedly changed " +
                    "compiler-substitution counters.");
            }
            Debug.Log(
                "Prepared unsubstituted generative Endminf M27 ABI shell: " +
                "registry unchanged, substitutions=0.");
        }

        [Serializable]
        private sealed class Report
        {
            public string schema;
            public string status;
            public string unityVersion;
            public string graphicsDeviceType;
            public string shaderAsset;
            public string shaderSourceSha256;
            public uint contractVersion;
            public uint registryReady;
            public uint callbackCount;
            public uint mismatchCount;
            public uint matchCount;
            public uint variantHashConflictCount;
            public uint maximumVertexInputs;
            public uint maximumVertexOutputs;
            public uint maximumPixelInputs;
            public uint maximumPixelOutputs;
            public string vertexShellSha256;
            public string pixelShellSha256;
            public CallbackObservation[] callbackObservations;
        }

        [Serializable]
        private sealed class GenerativeObservationReport
        {
            public string schema;
            public string status;
            public string unityVersion;
            public string graphicsDeviceType;
            public string shaderAsset;
            public string shaderSourceSha256;
            public uint contractVersion;
            public uint registryReady;
            public uint callbackCountBefore;
            public uint callbackCountAfter;
            public uint callbackObservationCountBefore;
            public uint callbackObservationCountAfter;
            public uint vertexSwapCountBefore;
            public uint vertexSwapCountAfter;
            public uint pixelSwapCountBefore;
            public uint pixelSwapCountAfter;
            public uint failureCountBefore;
            public uint failureCountAfter;
            public bool variantWarmupSucceeded;
            public string variantWarmupFailure;
            public string variantWarmupPassType;
            public bool setPassActivated;
            public string setPassFailure;
            public int vertexAbiMatchCount;
            public int pixelAbiMatchCount;
            public string vertexShellSha256;
            public string pixelShellSha256;
            public CallbackObservation[] callbackObservations;
        }

        [Serializable]
        private sealed class GenerativePinReport
        {
            public string schema;
            public string status;
            public string unityVersion;
            public string graphicsDeviceType;
            public string shaderAsset;
            public string shaderSourceSha256;
            public uint contractVersion;
            public uint registryReady;
            public uint callbackCountBefore;
            public uint callbackCountAfter;
            public uint callbackObservationCountBefore;
            public uint callbackObservationCountAfter;
            public uint vertexSwapCountBefore;
            public uint vertexSwapCountAfter;
            public uint pixelSwapCountBefore;
            public uint pixelSwapCountAfter;
            public uint failureCountBefore;
            public uint failureCountAfter;
            public bool setPassActivated;
            public string setPassFailure;
            public int vertexAbiMatchCount;
            public int pixelAbiMatchCount;
            public string vertexShellSha256;
            public string pixelShellSha256;
            public CallbackObservation[] callbackObservations;
        }

        [Serializable]
        private sealed class CallbackObservation
        {
            public uint stage;
            public uint byteCodeSize;
            public uint inputParameters;
            public uint outputParameters;
            public uint boundResources;
            public uint constantBuffer0Bytes;
            public uint constantBuffer1Bytes;
            public uint constantBuffer2Bytes;
            public uint constantBuffer3Bytes;
            public uint constantBuffer4Bytes;
            public string textureSlotMask;
            public string samplerSlotMask;
            public string sha256;
        }

        /// <summary>
        /// Safe callback observation for the unpinned named-binding shell.
        /// It never arms substitution and never writes registry identities.
        /// Invoke in a fresh D3D11 batch editor with -executeMethod.
        /// </summary>
        public static void RunGenerativeObservation()
        {
            string output = Environment.GetEnvironmentVariable(
                GenerativeOutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m27_hgbuffer",
                    "generative_shell_hashes.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "Generative M27 shell observation requires Direct3D11; " +
                        "actual=" + SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2)
                    throw new InvalidOperationException(
                        "Original DXBC plugin contract version drifted.");
                Native.SetM27SubstitutionArmed(0);
                Native.SetM27ObservationArmed(0);
                // Settle the project import and this exact asset while the
                // observer is disarmed. A fresh editor may otherwise compile
                // unrelated diagnostic shells during the first synchronous
                // import, making an ABI-only target delta ambiguous.
                ForceRecompileWhileArmed(GenerativeShaderAsset);
                ForceLoadReservedVariant(GenerativeShaderAsset);
                if (Native.SetM27ObservationArmed(1) != 1)
                    throw new InvalidOperationException(
                        "M27 observation-only compiler route could not be armed.");
                // Arming starts a new epoch and resets all diagnostic counters.
                // Baselines must therefore be sampled after ownership is acquired.
                uint callbacksBefore = Native.GetCallbackCount();
                uint observationsBefore =
                    Native.GetM27CallbackObservationCount();
                uint vertexSwapsBefore = Native.GetVertexSwapCount();
                uint pixelSwapsBefore = Native.GetPixelSwapCount();
                uint failuresBefore = Native.GetFailureCount();
                ForceRecompileWhileArmed(GenerativeShaderAsset);
                bool variantWarmupSucceeded = true;
                string variantWarmupFailure = string.Empty;
                string variantWarmupPassType = string.Empty;
                bool setPassActivated = true;
                string setPassFailure = string.Empty;
                try
                {
                    ForceLoadReservedVariant(GenerativeShaderAsset);
                    variantWarmupPassType = "Material.SetPass(0)";
                }
                catch (Exception exception)
                {
                    variantWarmupSucceeded = false;
                    variantWarmupFailure = exception.Message;
                    setPassActivated = false;
                    setPassFailure = exception.Message;
                    Debug.LogWarning(
                        "Generative M27 shell keyword variant did not warm: " +
                        variantWarmupFailure);
                }
                uint callbacksAfter = Native.GetCallbackCount();
                uint observationsAfter =
                    Native.GetM27CallbackObservationCount();
                uint vertexSwapsAfter = Native.GetVertexSwapCount();
                uint pixelSwapsAfter = Native.GetPixelSwapCount();
                uint failuresAfter = Native.GetFailureCount();
                CallbackObservation[] callbackObservations =
                    ReadCallbackObservations();
                CallbackObservation[] newObservations = callbackObservations
                    .Skip((int)observationsBefore)
                    .ToArray();
                CallbackObservation[] vertexMatches = newObservations
                    .Where(MatchesGenerativeVertexAbi)
                    .ToArray();
                CallbackObservation[] pixelMatches = newObservations
                    .Where(MatchesGenerativePixelAbi)
                    .ToArray();
                bool bothStagesObserved =
                    vertexMatches.Length == 1 && pixelMatches.Length == 1;
                bool observationValid = Native.GetConfigureCount() != 0 &&
                    callbacksAfter >= callbacksBefore + 2 &&
                    observationsAfter >= observationsBefore + 2 &&
                    bothStagesObserved &&
                    variantWarmupSucceeded &&
                    setPassActivated &&
                    vertexSwapsAfter == vertexSwapsBefore &&
                    pixelSwapsAfter == pixelSwapsBefore &&
                    failuresAfter == failuresBefore;

                string shaderPath = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    GenerativeShaderAsset));
                var report = new GenerativeObservationReport
                {
                    schema =
                        "endfield.m27-generative-unity-shell-observation.v1",
                    status = observationValid
                        ? "observed_unpinned_fail_closed"
                        : bothStagesObserved &&
                          (!variantWarmupSucceeded || !setPassActivated)
                            ? "observed_unpinned_setpass_unproven_fail_closed"
                            : "raw_callback_abi_mismatch_fail_closed",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = GenerativeShaderAsset,
                    shaderSourceSha256 = HashFile(shaderPath),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = Native.GetM27RegistryReady(),
                    callbackCountBefore = callbacksBefore,
                    callbackCountAfter = callbacksAfter,
                    callbackObservationCountBefore = observationsBefore,
                    callbackObservationCountAfter = observationsAfter,
                    vertexSwapCountBefore = vertexSwapsBefore,
                    vertexSwapCountAfter = vertexSwapsAfter,
                    pixelSwapCountBefore = pixelSwapsBefore,
                    pixelSwapCountAfter = pixelSwapsAfter,
                    failureCountBefore = failuresBefore,
                    failureCountAfter = failuresAfter,
                    variantWarmupSucceeded = variantWarmupSucceeded,
                    variantWarmupFailure = variantWarmupFailure,
                    variantWarmupPassType = variantWarmupPassType,
                    setPassActivated = setPassActivated,
                    setPassFailure = setPassFailure,
                    vertexAbiMatchCount = vertexMatches.Length,
                    pixelAbiMatchCount = pixelMatches.Length,
                    vertexShellSha256 = vertexMatches.Length == 1
                        ? vertexMatches[0].sha256
                        : string.Empty,
                    pixelShellSha256 = pixelMatches.Length == 1
                        ? pixelMatches[0].sha256
                        : string.Empty,
                    callbackObservations = newObservations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                if (!observationValid)
                {
                    throw new InvalidOperationException(
                        "Unpinned generative shell callback observation failed " +
                        "closed: callbacks=" + callbacksBefore + "->" +
                        callbacksAfter + ", swaps=" + vertexSwapsBefore + "/" +
                        pixelSwapsBefore + "->" + vertexSwapsAfter + "/" +
                        pixelSwapsAfter + ", failures=" + failuresBefore + "->" +
                        failuresAfter + ", ABI matches=" +
                        vertexMatches.Length + "/" + pixelMatches.Length +
                        ". Raw report=" + output + ".");
                }
                Debug.Log(
                    "Observed unpinned generative M27 Unity shell hashes: VS=" +
                    report.vertexShellSha256 + ", PS=" +
                    report.pixelShellSha256 + ", output=" + output + ".");
                Native.SetM27ObservationArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27ObservationArmed(0);
                }
                catch
                {
                    // Preserve the original actionable observation failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        /// <summary>
        /// Validates the independently observed generative shell hashes against
        /// the native stage+SHA registry. This remains compiler-only: it does
        /// not submit the retained ParticleSystemRenderer draw.
        /// </summary>
        public static void RunGenerativePinValidation()
        {
            string output = Environment.GetEnvironmentVariable(
                GenerativePinOutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m27_hgbuffer",
                    "generative_shell_pin_validation.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "Generative M27 pin validation requires Direct3D11; " +
                        "actual=" + SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2 ||
                    Native.GetM27RegistryReady() != 1)
                {
                    throw new InvalidOperationException(
                        "The exact M27 stage+SHA registry is not ready.");
                }
                Native.SetM27ObservationArmed(0);
                Native.SetM27SubstitutionArmed(0);
                // Settle imports and prove the raw shell can load before the
                // fresh owned substitution epoch begins.
                ForceRecompileWhileArmed(GenerativeShaderAsset);
                ForceLoadReservedVariant(GenerativeShaderAsset);
                if (Native.SetM27SubstitutionArmed(1) != 1)
                {
                    throw new InvalidOperationException(
                        "M27 hash-pinned compiler route could not be armed.");
                }

                uint callbacksBefore = Native.GetCallbackCount();
                uint observationsBefore =
                    Native.GetM27CallbackObservationCount();
                uint vertexSwapsBefore = Native.GetVertexSwapCount();
                uint pixelSwapsBefore = Native.GetPixelSwapCount();
                uint failuresBefore = Native.GetFailureCount();
                ForceRecompileWhileArmed(GenerativeShaderAsset);
                bool setPassActivated = true;
                string setPassFailure = string.Empty;
                try
                {
                    ForceLoadReservedVariant(GenerativeShaderAsset);
                }
                catch (Exception exception)
                {
                    setPassActivated = false;
                    setPassFailure = exception.Message;
                }

                uint callbacksAfter = Native.GetCallbackCount();
                uint observationsAfter =
                    Native.GetM27CallbackObservationCount();
                uint vertexSwapsAfter = Native.GetVertexSwapCount();
                uint pixelSwapsAfter = Native.GetPixelSwapCount();
                uint failuresAfter = Native.GetFailureCount();
                CallbackObservation[] callbackObservations =
                    ReadCallbackObservations();
                CallbackObservation[] newObservations = callbackObservations
                    .Skip((int)observationsBefore)
                    .ToArray();
                CallbackObservation[] vertexMatches = newObservations
                    .Where(MatchesGenerativeVertexAbi)
                    .ToArray();
                CallbackObservation[] pixelMatches = newObservations
                    .Where(MatchesGenerativePixelAbi)
                    .ToArray();
                bool valid = Native.GetConfigureCount() != 0 &&
                    callbacksAfter >= callbacksBefore + 2 &&
                    observationsAfter >= observationsBefore + 2 &&
                    vertexMatches.Length == 1 && pixelMatches.Length == 1 &&
                    // Unity may refresh other already-pinned reserved shaders
                    // in the same import transaction. The unique ABI+hash
                    // observations above identify this shell; any failed
                    // replacement increments the shared failure counter.
                    vertexSwapsAfter > vertexSwapsBefore &&
                    pixelSwapsAfter > pixelSwapsBefore &&
                    failuresAfter == failuresBefore &&
                    setPassActivated;

                string shaderPath = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    GenerativeShaderAsset));
                var report = new GenerativePinReport
                {
                    schema = "endfield.endminf-m27-generative-shell-pin.v1",
                    status = valid
                        ? "independently_pinned_d3d11_callback"
                        : "pin_validation_failed_closed",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = GenerativeShaderAsset,
                    shaderSourceSha256 = HashFile(shaderPath),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = Native.GetM27RegistryReady(),
                    callbackCountBefore = callbacksBefore,
                    callbackCountAfter = callbacksAfter,
                    callbackObservationCountBefore = observationsBefore,
                    callbackObservationCountAfter = observationsAfter,
                    vertexSwapCountBefore = vertexSwapsBefore,
                    vertexSwapCountAfter = vertexSwapsAfter,
                    pixelSwapCountBefore = pixelSwapsBefore,
                    pixelSwapCountAfter = pixelSwapsAfter,
                    failureCountBefore = failuresBefore,
                    failureCountAfter = failuresAfter,
                    setPassActivated = setPassActivated,
                    setPassFailure = setPassFailure,
                    vertexAbiMatchCount = vertexMatches.Length,
                    pixelAbiMatchCount = pixelMatches.Length,
                    vertexShellSha256 = vertexMatches.Length == 1
                        ? vertexMatches[0].sha256
                        : string.Empty,
                    pixelShellSha256 = pixelMatches.Length == 1
                        ? pixelMatches[0].sha256
                        : string.Empty,
                    callbackObservations = newObservations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                if (!valid)
                {
                    throw new InvalidOperationException(
                        "Generative M27 shell pin validation failed closed: " +
                        "callbacks=" + callbacksBefore + "->" + callbacksAfter +
                        ", swaps=" + vertexSwapsBefore + "/" + pixelSwapsBefore +
                        "->" + vertexSwapsAfter + "/" + pixelSwapsAfter +
                        ", failures=" + failuresBefore + "->" + failuresAfter +
                        ", ABI matches=" + vertexMatches.Length + "/" +
                        pixelMatches.Length + ", SetPass=" + setPassActivated +
                        ". Raw report=" + output + ".");
                }
                Debug.Log(
                    "Validated generative M27 stage+SHA substitution: VS=" +
                    report.vertexShellSha256 + ", PS=" +
                    report.pixelShellSha256 + ", output=" + output + ".");
                Native.SetM27SubstitutionArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27SubstitutionArmed(0);
                }
                catch
                {
                    // Preserve the original actionable validation failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        public static void Run()
        {
            string output = Environment.GetEnvironmentVariable(
                OutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m27_hgbuffer",
                    "shell_hashes.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "M27 shell hash capture requires Direct3D11; actual=" +
                        SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2)
                    throw new InvalidOperationException(
                        "Original DXBC plugin contract version drifted.");
                if (Native.SetM27SubstitutionArmed(1) != 1)
                    throw new InvalidOperationException(
                        "M27 substitution callback could not be armed.");

                ForceRecompileWhileArmed();
                ForceLoadReservedVariant();

                uint configureCount = Native.GetConfigureCount();
                uint callbackCountBeforeRead = Native.GetCallbackCount();
                uint mismatchCountBeforeRead = Native.GetM27MismatchCount();
                uint vertexSignature = Native.GetM27MaximumSignatureCounts(1);
                uint pixelSignature = Native.GetM27MaximumSignatureCounts(2);
                Debug.Log(
                    "M27 shell compiler-extension counters after import: " +
                    $"configure={configureCount}, " +
                    $"callbacks={callbackCountBeforeRead}, " +
                    $"mismatches={mismatchCountBeforeRead}, " +
                    $"maxVS={vertexSignature >> 16}/{vertexSignature & 0xffff}, " +
                    $"maxPS={pixelSignature >> 16}/{pixelSignature & 0xffff}.");
                if (configureCount == 0)
                {
                    throw new InvalidOperationException(
                        "Unity did not configure the native shader compiler " +
                        "extension in this editor process; a shader reimport " +
                        "cannot observe M27 shell hashes.");
                }
                if (callbackCountBeforeRead < 2)
                {
                    throw new InvalidOperationException(
                        "Unity configured the shader compiler extension but " +
                        "did not request both reserved M27 shader stages " +
                        "during import: callbacks=" +
                        callbackCountBeforeRead + ".");
                }

                byte[] vertex = ReadObservedHash(1);
                byte[] pixel = ReadObservedHash(2);
                uint callbackCount = Native.GetCallbackCount();
                uint mismatchCount = Native.GetM27MismatchCount();
                uint matchCount = Native.GetM27MatchCount();
                uint variantHashConflictCount =
                    Native.GetM27VariantHashConflictCount();
                uint registryReady = Native.GetM27RegistryReady();
                CallbackObservation[] callbackObservations =
                    ReadCallbackObservations();
                bool bothStagesObserved =
                    vertex.Any(value => value != 0) &&
                    pixel.Any(value => value != 0);
                bool validState = registryReady != 0
                    ? bothStagesObserved && matchCount >= 2 &&
                        mismatchCount == 0 &&
                        variantHashConflictCount == 0 && callbackCount >= 2
                    : matchCount == 0 &&
                        (!bothStagesObserved || variantHashConflictCount == 0) &&
                        callbackCount >= 2;
                if (!validState)
                {
                    throw new InvalidOperationException(
                        "M27 shell substitution state failed validation: " +
                        $"ready={registryReady}, matches={matchCount}, " +
                        $"mismatches={mismatchCount}, callbacks={callbackCount}, " +
                        $"variantHashConflicts={variantHashConflictCount}.");
                }

                string shaderPath = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    ShaderAsset));
                var report = new Report
                {
                    schema = "endfield.m27-unity-shell-hashes.v1",
                    status = registryReady != 0 && bothStagesObserved
                        ? "pinned_substitution_activated"
                        : bothStagesObserved
                            ? "observed_unpinned_fail_closed"
                            : "unity_shell_abi_mismatch_fail_closed",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = ShaderAsset,
                    shaderSourceSha256 = HashFile(shaderPath),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = registryReady,
                    callbackCount = callbackCount,
                    mismatchCount = mismatchCount,
                    matchCount = matchCount,
                    variantHashConflictCount = variantHashConflictCount,
                    maximumVertexInputs = vertexSignature >> 16,
                    maximumVertexOutputs = vertexSignature & 0xffff,
                    maximumPixelInputs = pixelSignature >> 16,
                    maximumPixelOutputs = pixelSignature & 0xffff,
                    vertexShellSha256 = vertex.Any(value => value != 0)
                        ? Hex(vertex)
                        : string.Empty,
                    pixelShellSha256 = pixel.Any(value => value != 0)
                        ? Hex(pixel)
                        : string.Empty,
                    callbackObservations = callbackObservations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log(
                    "Validated M27 Unity shell state: status=" +
                    report.status + ", VS=" +
                    report.vertexShellSha256 + ", PS=" +
                    report.pixelShellSha256 + ", output=" + output + ".");
                Native.SetM27SubstitutionArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27SubstitutionArmed(0);
                }
                catch
                {
                    // Preserve the original actionable capture failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        public static void RunM14Observation()
        {
            string output = Environment.GetEnvironmentVariable(
                M14OutputEnvironment);
            if (string.IsNullOrWhiteSpace(output))
            {
                output = Path.GetFullPath(Path.Combine(
                    Application.dataPath,
                    "..",
                    "scratch",
                    "character_recovery",
                    "m14_vfxbasev2",
                    "shell_hash_observation.json"));
            }
            else
            {
                output = Path.GetFullPath(output);
            }

            try
            {
                if (SystemInfo.graphicsDeviceType !=
                    GraphicsDeviceType.Direct3D11)
                {
                    throw new InvalidOperationException(
                        "M14 shell observation requires Direct3D11; actual=" +
                        SystemInfo.graphicsDeviceType + ".");
                }
                if (Native.GetContractVersion() != 2)
                    throw new InvalidOperationException(
                        "Original DXBC plugin contract version drifted.");
                if (Native.SetM27SubstitutionArmed(1) != 1)
                    throw new InvalidOperationException(
                        "The reserved exact-stage callback could not be armed.");

                ForceRecompileWhileArmed(M14ShaderAsset);
                ForceLoadReservedVariant(M14ShaderAsset);
                CallbackObservation[] observations = ReadCallbackObservations();
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(
                    output + ".callbacks.json",
                    JsonUtility.ToJson(new Report
                    {
                        schema = "endfield.m14-unity-shell-callbacks.v1",
                        status = "raw_callback_inventory",
                        callbackObservations = observations,
                    }, true));
                CallbackObservation[] vertexCandidates = observations.Where(value =>
                    value.stage == 1 && value.inputParameters == 8 &&
                    value.outputParameters == 7).ToArray();
                CallbackObservation[] pixelCandidates = observations.Where(value =>
                    value.stage == 2 && value.inputParameters == 7 &&
                    value.outputParameters == 2).ToArray();
                CallbackObservation vertex = vertexCandidates.Single(value =>
                    value.byteCodeSize == 1424 && value.sha256 ==
                    "0dc6bf259f8510c1e280160543cab0b591485a34bf226c048bf3f245fdad6714");
                CallbackObservation pixel = pixelCandidates.Single(value =>
                    value.byteCodeSize == 3192 && value.sha256 ==
                    "465a86bc25083537c7cfa6d8f481253d907a29e4097fc5ce378d080083e25b57");
                uint matchCount = Native.GetM27MatchCount();
                uint vertexSwaps = Native.GetVertexSwapCount();
                uint pixelSwaps = Native.GetPixelSwapCount();
                uint failures = Native.GetFailureCount();
                if (matchCount < 2 || vertexSwaps == 0 ||
                    vertexSwaps != pixelSwaps ||
                    matchCount != vertexSwaps + pixelSwaps || failures != 0)
                {
                    throw new InvalidOperationException(
                        "Pinned M14 shell substitution failed validation: " +
                        $"matches={matchCount}, vertexSwaps={vertexSwaps}, " +
                        $"pixelSwaps={pixelSwaps}, failures={failures}.");
                }
                var report = new Report
                {
                    schema = "endfield.m14-unity-shell-hashes.v1",
                    status = "pinned_substitution_activated",
                    unityVersion = Application.unityVersion,
                    graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                    shaderAsset = M14ShaderAsset,
                    shaderSourceSha256 = HashFile(Path.GetFullPath(Path.Combine(
                        Application.dataPath, "..", M14ShaderAsset))),
                    contractVersion = Native.GetContractVersion(),
                    registryReady = Native.GetM27RegistryReady(),
                    callbackCount = Native.GetCallbackCount(),
                    mismatchCount = Native.GetM27MismatchCount(),
                    matchCount = matchCount,
                    variantHashConflictCount =
                        Native.GetM27VariantHashConflictCount(),
                    maximumVertexInputs = vertex.inputParameters,
                    maximumVertexOutputs = vertex.outputParameters,
                    maximumPixelInputs = pixel.inputParameters,
                    maximumPixelOutputs = pixel.outputParameters,
                    vertexShellSha256 = vertex.sha256,
                    pixelShellSha256 = pixel.sha256,
                    callbackObservations = observations,
                };
                Directory.CreateDirectory(Path.GetDirectoryName(output));
                File.WriteAllText(output, JsonUtility.ToJson(report, true));
                Debug.Log(
                    "Validated pinned M14 Unity shell hashes: VS=" +
                    vertex.sha256 + ", PS=" + pixel.sha256 +
                    ", output=" + output + ".");
                Native.SetM27SubstitutionArmed(0);
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                try
                {
                    Native.SetM27SubstitutionArmed(0);
                }
                catch
                {
                    // Preserve the original actionable observation failure.
                }
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static byte[] ReadObservedHash(uint stage)
        {
            byte[] value = new byte[32];
            uint written = Native.GetM27ObservedShellSha256(
                    stage,
                    value,
                    (uint)value.Length);
            if (written != value.Length)
            {
                throw new InvalidOperationException(
                    "Could not read observed M27 stage " + stage +
                    " hash: bytesWritten=" + written + ".");
            }
            return value;
        }

        private static void ForceRecompileWhileArmed()
        {
            ForceRecompileWhileArmed(ShaderAsset);
        }

        private static void ForceRecompileWhileArmed(string shaderAsset)
        {
            string shaderPath = Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "..",
                shaderAsset));
            byte[] original = File.ReadAllBytes(shaderPath);
            byte[] touch = System.Text.Encoding.ASCII.GetBytes(
                "\n// ENDFIELD_M27_ARMED_CAPTURE_REIMPORT\n");
            var modified = new byte[original.Length + touch.Length];
            Buffer.BlockCopy(original, 0, modified, 0, original.Length);
            Buffer.BlockCopy(touch, 0, modified, original.Length, touch.Length);
            try
            {
                File.WriteAllBytes(shaderPath, modified);
                AssetDatabase.ImportAsset(
                    shaderAsset,
                    ImportAssetOptions.ForceUpdate |
                    ImportAssetOptions.ForceSynchronousImport);
            }
            finally
            {
                File.WriteAllBytes(shaderPath, original);
            }
        }

        private static void ForceLoadReservedVariant()
        {
            ForceLoadReservedVariant(ShaderAsset);
        }

        private static void ForceLoadReservedVariant(string shaderAsset)
        {
            Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(shaderAsset);
            if (shader == null)
                throw new InvalidOperationException(
                    "Could not load the dedicated M27 shell shader.");
            ShaderUtil.ClearCachedData(shader);
            var material = new Material(shader)
            {
                hideFlags = HideFlags.HideAndDontSave,
            };
            try
            {
                material.EnableKeyword("ENDFIELD_ORIGINAL_DXBC_M27_EXACT");
                if (!material.SetPass(0))
                {
                    string messages = string.Join(
                        " | ",
                        ShaderUtil.GetShaderMessages(shader).Select(value =>
                            value.severity + ": " + value.message +
                            " (" + value.file + ":" + value.line + ")"));
                    throw new InvalidOperationException(
                        "Could not activate the reserved exact shell variant " +
                        shaderAsset + ". Import messages: " + messages);
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(material);
            }
        }

        private static string WarmReservedVariant(string shaderAsset)
        {
            Shader shader = AssetDatabase.LoadAssetAtPath<Shader>(shaderAsset);
            if (shader == null)
                throw new InvalidOperationException(
                    "Could not load the dedicated M27 shell shader.");
            ShaderUtil.ClearShaderMessages(shader);
            ShaderUtil.ClearCachedData(shader);
            foreach (PassType passType in Enum.GetValues(typeof(PassType)))
            {
                try
                {
                    var variants = new ShaderVariantCollection();
                    var variant = new ShaderVariantCollection.ShaderVariant(
                        shader,
                        passType,
                        "ENDFIELD_ORIGINAL_DXBC_M27_EXACT");
                    if (!variants.Add(variant))
                        continue;
                    variants.WarmUp();
                    if (variants.isWarmedUp && shader.isSupported)
                        return passType.ToString();
                }
                catch (ArgumentException)
                {
                    // This pass type has no snippet in the selected SubShader.
                }
            }
            string messages = string.Join(
                " | ",
                ShaderUtil.GetShaderMessages(shader).Select(value =>
                    value.severity + ": " + value.message +
                    " (" + value.file + ":" + value.line + ")"));
            throw new InvalidOperationException(
                "Could not warm any pass type for the reserved generative " +
                "M27 variant. Import messages: " + messages);
        }

        private static CallbackObservation[] ReadCallbackObservations()
        {
            uint count = Native.GetM27CallbackObservationCount();
            var values = new CallbackObservation[count];
            for (uint index = 0; index < count; ++index)
            {
                var metadata = new uint[12];
                var digest = new byte[32];
                uint written = Native.GetM27CallbackObservation(
                    index,
                    metadata,
                    (uint)metadata.Length,
                    digest,
                    (uint)digest.Length);
                if (written != metadata.Length)
                {
                    throw new InvalidOperationException(
                        "Could not read M27 callback observation " + index +
                        ": metadataWritten=" + written + ".");
                }
                values[index] = new CallbackObservation
                {
                    stage = metadata[0],
                    byteCodeSize = metadata[1],
                    inputParameters = metadata[2],
                    outputParameters = metadata[3],
                    boundResources = metadata[4],
                    constantBuffer0Bytes = metadata[5],
                    constantBuffer1Bytes = metadata[6],
                    constantBuffer2Bytes = metadata[7],
                    constantBuffer3Bytes = metadata[8],
                    constantBuffer4Bytes = metadata[9],
                    textureSlotMask = "0x" + metadata[10].ToString("x8"),
                    samplerSlotMask = "0x" + metadata[11].ToString("x8"),
                    sha256 = Hex(digest),
                };
            }
            return values;
        }

        private static bool MatchesGenerativeVertexAbi(
            CallbackObservation value)
        {
            return value != null &&
                value.stage == 1u &&
                !string.Equals(
                    value.sha256,
                    ImmutablePacketShellVertexSha256,
                    StringComparison.OrdinalIgnoreCase) &&
                value.inputParameters == 10u &&
                value.outputParameters == 9u &&
                value.boundResources == 4u &&
                value.constantBuffer0Bytes == 1312u &&
                value.constantBuffer1Bytes == 320u &&
                value.constantBuffer2Bytes == 65456u &&
                value.constantBuffer3Bytes == 0u &&
                value.constantBuffer4Bytes == 0u &&
                value.textureSlotMask == "0x00000001" &&
                value.samplerSlotMask == "0x00000000";
        }

        private static bool MatchesGenerativePixelAbi(
            CallbackObservation value)
        {
            return value != null &&
                value.stage == 2u &&
                !string.Equals(
                    value.sha256,
                    ImmutablePacketShellPixelSha256,
                    StringComparison.OrdinalIgnoreCase) &&
                value.inputParameters == 10u &&
                value.outputParameters == 5u &&
                value.boundResources == 17u &&
                value.constantBuffer0Bytes == 720u &&
                value.constantBuffer1Bytes == 1696u &&
                value.constantBuffer2Bytes == 65456u &&
                value.constantBuffer3Bytes == 496u &&
                value.constantBuffer4Bytes == 16u &&
                value.textureSlotMask == "0x0000003f" &&
                value.samplerSlotMask == "0x0000003f";
        }

        private static string HashFile(string path)
        {
            using (SHA256 sha = SHA256.Create())
                return Hex(sha.ComputeHash(File.ReadAllBytes(path)));
        }

        private static string Hex(byte[] value)
        {
            return string.Concat(value.Select(item => item.ToString("x2")));
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetContractVersion")]
            internal static extern uint GetContractVersion();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetConfigureCount")]
            internal static extern uint GetConfigureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM27SubstitutionArmed")]
            internal static extern uint SetM27SubstitutionArmed(uint armed);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM27ObservationArmed")]
            internal static extern uint SetM27ObservationArmed(uint armed);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27RegistryReady")]
            internal static extern uint GetM27RegistryReady();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MatchCount")]
            internal static extern uint GetM27MatchCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MismatchCount")]
            internal static extern uint GetM27MismatchCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27VariantHashConflictCount")]
            internal static extern uint GetM27VariantHashConflictCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27MaximumSignatureCounts")]
            internal static extern uint GetM27MaximumSignatureCounts(uint stage);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27ObservedShellSha256")]
            internal static extern uint GetM27ObservedShellSha256(
                uint stage,
                [Out] byte[] output,
                uint outputSize);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetCallbackCount")]
            internal static extern uint GetCallbackCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetVertexSwapCount")]
            internal static extern uint GetVertexSwapCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetPixelSwapCount")]
            internal static extern uint GetPixelSwapCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27CallbackObservationCount")]
            internal static extern uint GetM27CallbackObservationCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM27CallbackObservation")]
            internal static extern uint GetM27CallbackObservation(
                uint index,
                [Out] uint[] metadata,
                uint metadataCount,
                [Out] byte[] sha256,
                uint sha256Size);
        }
    }
}
