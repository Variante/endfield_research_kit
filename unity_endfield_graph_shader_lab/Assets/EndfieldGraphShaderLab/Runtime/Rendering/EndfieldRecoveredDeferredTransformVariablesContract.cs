using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-built subset of the original pass-0 b30 / M27 b0
    /// _TransformVariables constant buffer. Unknown registers remain zero;
    /// the non-jittered camera-relative current/previous rows are produced
    /// from camera matrices and explicit temporal history, never from a
    /// captured constant-buffer payload.
    /// </summary>
    public static class EndfieldRecoveredDeferredTransformVariablesContract
    {
        public const int SizeBytes = 1312;
        public const int VectorCount = 82;
        public const int D3D11SelectedSizeBytes = 720;
        public const int ViewFirstVector = 0;
        public const int InverseViewFirstVector = 4;
        public const int InverseViewProjectionFirstVector = 24;
        public const int NonJitteredViewNoTranslationProjectionFirstVector = 32;
        public const int CameraPositionVector = 44;
        public const int PreviousNonJitteredViewNoTranslationProjectionFirstVector =
            57;
        public const int PreviousCameraPositionVector = 81;

        public static readonly int[] SelectedUsedVectors =
        {
            0, 1, 2, 3,
            4, 5, 6, 7,
            24, 25, 26, 27,
            32, 33, 34, 35,
            44,
            57, 58, 59, 60,
            81,
        };

        /// <summary>
        /// Exact vector-level M27 b0 read inventory from the hash-pinned
        /// subprogram-113 VS/PS pair. The PS reads only .z from c0-c2, and the
        /// shaders read only .xyz from c44/c81, but the producer publishes
        /// whole float4 registers so the transport remains ABI-shaped.
        /// </summary>
        public static readonly int[] M27ReadVectors =
        {
            0, 1, 2,
            24, 25, 26, 27,
            32, 33, 34, 35,
            44,
            57, 58, 59, 60,
            81,
        };

        /// <summary>
        /// Per-camera temporal source state shared by the runtime owner and
        /// deterministic validation. It stores source-built values, never a
        /// captured constant-buffer payload.
        /// </summary>
        public sealed class CameraHistoryState
        {
            public Matrix4x4 nonJitteredViewNoTranslationProjection;
            public Vector3 cameraPosition;
            public int lastPublishedFrame = -1;
            public int width;
            public int height;
            public bool renderIntoTexture;
        }

        public static bool TryEvaluateHistory(
            CameraHistoryState history,
            int frame,
            int width,
            int height,
            bool renderIntoTexture,
            out bool previousFrameHistoryReady,
            out string failure)
        {
            previousFrameHistoryReady = false;
            failure = null;
            if (frame < 0)
            {
                failure = "frame serial must be non-negative";
                return false;
            }
            if (width <= 0 || height <= 0)
            {
                failure = "render dimensions must be positive";
                return false;
            }
            if (history != null && history.lastPublishedFrame == frame)
            {
                failure =
                    "the same camera cannot publish TransformVariables twice " +
                    "in one frame";
                return false;
            }
            previousFrameHistoryReady = history != null &&
                history.lastPublishedFrame >= 0 &&
                history.lastPublishedFrame == frame - 1 &&
                history.width == width &&
                history.height == height &&
                history.renderIntoTexture == renderIntoTexture;
            return true;
        }

        public static void CommitHistory(
            CameraHistoryState history,
            Matrix4x4 currentNonJitteredViewNoTranslationProjection,
            Vector3 currentCameraPosition,
            int frame,
            int width,
            int height,
            bool renderIntoTexture)
        {
            if (history == null)
                throw new ArgumentNullException(nameof(history));
            history.nonJitteredViewNoTranslationProjection =
                currentNonJitteredViewNoTranslationProjection;
            history.cameraPosition = currentCameraPosition;
            history.lastPublishedFrame = frame;
            history.width = width;
            history.height = height;
            history.renderIntoTexture = renderIntoTexture;
        }

        public static bool TryBuild(
            Camera camera,
            bool renderIntoTexture,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (camera == null)
            {
                failure = "physical camera is required";
                return false;
            }
            return TryBuild(
                camera.worldToCameraMatrix,
                GL.GetGPUProjectionMatrix(
                    camera.projectionMatrix,
                    renderIntoTexture),
                GL.GetGPUProjectionMatrix(
                    camera.nonJitteredProjectionMatrix,
                    renderIntoTexture),
                camera.transform.position,
                Matrix4x4.identity,
                Vector3.zero,
                false,
                destination,
                out failure);
        }

        /// <summary>
        /// Builds the complete M27-read b0 subset with explicit temporal
        /// inputs. On a history reset, retail HGCamera semantics initialize the
        /// previous rows from the current frame instead of inventing a prior
        /// transform.
        /// </summary>
        public static bool TryBuild(
            Camera camera,
            bool renderIntoTexture,
            Matrix4x4 previousNonJitteredViewNoTranslationProjection,
            Vector3 previousCameraPosition,
            bool previousFrameHistoryReady,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (camera == null)
            {
                failure = "physical camera is required";
                return false;
            }
            return TryBuild(
                camera.worldToCameraMatrix,
                GL.GetGPUProjectionMatrix(
                    camera.projectionMatrix,
                    renderIntoTexture),
                GL.GetGPUProjectionMatrix(
                    camera.nonJitteredProjectionMatrix,
                    renderIntoTexture),
                camera.transform.position,
                previousNonJitteredViewNoTranslationProjection,
                previousCameraPosition,
                previousFrameHistoryReady,
                destination,
                out failure);
        }

        public static bool TryBuild(
            Matrix4x4 view,
            Matrix4x4 gpuProjection,
            Vector3 cameraPosition,
            Vector4[] destination,
            out string failure)
        {
            return TryBuild(
                view,
                gpuProjection,
                gpuProjection,
                cameraPosition,
                Matrix4x4.identity,
                Vector3.zero,
                false,
                destination,
                out failure);
        }

        public static bool TryBuild(
            Matrix4x4 view,
            Matrix4x4 gpuProjection,
            Matrix4x4 nonJitteredGpuProjection,
            Vector3 cameraPosition,
            Matrix4x4 previousNonJitteredViewNoTranslationProjection,
            Vector3 previousCameraPosition,
            bool previousFrameHistoryReady,
            Vector4[] destination,
            out string failure)
        {
            failure = null;
            if (destination == null || destination.Length != VectorCount)
            {
                failure = "destination must contain exactly 82 float4 vectors";
                return false;
            }
            if (!IsFinite(view))
            {
                failure = "view matrix must contain only finite values";
                return false;
            }
            if (!IsFinite(gpuProjection))
            {
                failure = "GPU projection matrix must contain only finite values";
                return false;
            }
            if (!IsFinite(nonJitteredGpuProjection))
            {
                failure =
                    "non-jittered GPU projection matrix must contain only finite values";
                return false;
            }
            if (!IsFinite(cameraPosition))
            {
                failure = "camera position must contain only finite values";
                return false;
            }
            if (previousFrameHistoryReady &&
                !IsFinite(previousNonJitteredViewNoTranslationProjection))
            {
                failure =
                    "previous non-jittered view-no-translation projection " +
                    "matrix must contain only finite values";
                return false;
            }
            if (previousFrameHistoryReady && !IsFinite(previousCameraPosition))
            {
                failure =
                    "previous camera position must contain only finite values";
                return false;
            }
            if (Mathf.Abs(view.determinant) <= 1.0e-8f)
            {
                failure = "view matrix must be invertible";
                return false;
            }
            Matrix4x4 viewProjection = gpuProjection * view;
            if (!IsFinite(viewProjection) ||
                Mathf.Abs(viewProjection.determinant) <= 1.0e-8f)
            {
                failure = "GPU view-projection matrix must be finite and invertible";
                return false;
            }

            Matrix4x4 viewNoTranslation = view;
            viewNoTranslation.m03 = 0.0f;
            viewNoTranslation.m13 = 0.0f;
            viewNoTranslation.m23 = 0.0f;
            viewNoTranslation.m33 = 1.0f;
            Matrix4x4 currentNonJitteredViewNoTranslationProjection =
                nonJitteredGpuProjection * viewNoTranslation;
            if (!IsFinite(currentNonJitteredViewNoTranslationProjection))
            {
                failure =
                    "non-jittered view-no-translation projection matrix must " +
                    "contain only finite values";
                return false;
            }

            Matrix4x4 previousProjection = previousFrameHistoryReady
                ? previousNonJitteredViewNoTranslationProjection
                : currentNonJitteredViewNoTranslationProjection;
            Vector3 previousPosition = previousFrameHistoryReady
                ? previousCameraPosition
                : cameraPosition;

            Array.Clear(destination, 0, destination.Length);
            PackD3DColumnRegisters(view, destination, ViewFirstVector);
            PackD3DColumnRegisters(
                view.inverse,
                destination,
                InverseViewFirstVector);
            PackD3DColumnRegisters(
                viewProjection.inverse,
                destination,
                InverseViewProjectionFirstVector);
            PackD3DColumnRegisters(
                currentNonJitteredViewNoTranslationProjection,
                destination,
                NonJitteredViewNoTranslationProjectionFirstVector);
            destination[CameraPositionVector] = new Vector4(
                cameraPosition.x,
                cameraPosition.y,
                cameraPosition.z,
                0.0f);
            PackD3DColumnRegisters(
                previousProjection,
                destination,
                PreviousNonJitteredViewNoTranslationProjectionFirstVector);
            destination[PreviousCameraPositionVector] = new Vector4(
                previousPosition.x,
                previousPosition.y,
                previousPosition.z,
                0.0f);
            return true;
        }

        public static uint[] BuildExpectedWords(Vector4[] vectors)
        {
            if (vectors == null || vectors.Length != VectorCount)
            {
                throw new ArgumentException(
                    "Expected exactly 82 vectors.",
                    nameof(vectors));
            }
            var words = new uint[VectorCount * 4];
            for (int vectorIndex = 0; vectorIndex < vectors.Length; vectorIndex++)
            {
                Vector4 value = vectors[vectorIndex];
                int word = vectorIndex * 4;
                words[word + 0] = FloatBits(value.x);
                words[word + 1] = FloatBits(value.y);
                words[word + 2] = FloatBits(value.z);
                words[word + 3] = FloatBits(value.w);
            }
            return words;
        }

        private static void PackD3DColumnRegisters(
            Matrix4x4 matrix,
            Vector4[] destination,
            int firstVector)
        {
            for (int column = 0; column < 4; column++)
            {
                destination[firstVector + column] = new Vector4(
                    matrix[0, column],
                    matrix[1, column],
                    matrix[2, column],
                    matrix[3, column]);
            }
        }

        private static bool IsFinite(Matrix4x4 matrix)
        {
            for (int row = 0; row < 4; row++)
            {
                for (int column = 0; column < 4; column++)
                {
                    if (!IsFinite(matrix[row, column]))
                        return false;
                }
            }
            return true;
        }

        private static bool IsFinite(Vector3 value)
        {
            return IsFinite(value.x) &&
                IsFinite(value.y) &&
                IsFinite(value.z);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }
    }
}
