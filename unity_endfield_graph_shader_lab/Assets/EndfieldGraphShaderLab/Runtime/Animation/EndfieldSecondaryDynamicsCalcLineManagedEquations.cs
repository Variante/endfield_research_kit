using System;
using System.Runtime.CompilerServices;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Value-only transcription of the pinned client's CalcLineNormalTangent
    /// equations for one parent and its children. It carries separate unpatched
    /// managed and common dual-CPU Burst acos paths. This helper is deliberately
    /// not scheduled or connected to scene state; the selected retail route and
    /// managed FromToRotation IFix state remain open.
    /// </summary>
    public static class EndfieldSecondaryDynamicsCalcLineManagedEquations
    {
        public enum BurstCpuVariant
        {
            X64Sse2,
            Avx2,
        }

        public const byte FlagMove = 0x02;
        public const uint ChildLocalStartMask = 0x000fffffU;
        public const int ChildCountShift = 20;

        private const double ParallelEpsilon = 9.999999974752427e-07;
        private const double SourcePi = 3.1415927410125732;

        public readonly struct ChildIndex
        {
            public readonly int localStart;
            public readonly int count;

            public ChildIndex(int localStart, int count)
            {
                this.localStart = localStart;
                this.count = count;
            }
        }

        public readonly struct ParentSource
        {
            public readonly K.Double3 position;
            public readonly K.Float4 rotation;
            public readonly K.Float3 negativeScaleDirection;
            public readonly K.Float4 negativeScaleQuaternionValue;
            public readonly byte attribute;
            public readonly double rotationalInterpolation;
            public readonly double rootRotation;

            public ParentSource(
                K.Double3 position,
                K.Float4 rotation,
                K.Float3 negativeScaleDirection,
                K.Float4 negativeScaleQuaternionValue,
                byte attribute,
                double rotationalInterpolation,
                double rootRotation)
            {
                this.position = position;
                this.rotation = rotation;
                this.negativeScaleDirection = negativeScaleDirection;
                this.negativeScaleQuaternionValue = negativeScaleQuaternionValue;
                this.attribute = attribute;
                this.rotationalInterpolation = rotationalInterpolation;
                this.rootRotation = rootRotation;
            }
        }

        public readonly struct ChildSource
        {
            public readonly K.Double3 position;
            public readonly K.Float3 localPosition;
            public readonly K.Float4 localRotation;
            public readonly byte attribute;

            public ChildSource(
                K.Double3 position,
                K.Float3 localPosition,
                K.Float4 localRotation,
                byte attribute)
            {
                this.position = position;
                this.localPosition = localPosition;
                this.localRotation = localRotation;
                this.attribute = attribute;
            }
        }

        public readonly struct ChildValue
        {
            public readonly K.Double3 restVector;
            public readonly K.Double3 childDirection;
            public readonly K.Float4 rotation;

            public ChildValue(
                K.Double3 restVector,
                K.Double3 childDirection,
                K.Float4 rotation)
            {
                this.restVector = restVector;
                this.childDirection = childDirection;
                this.rotation = rotation;
            }
        }

        public readonly struct ParentValue
        {
            public readonly bool hasChildren;
            public readonly K.Double3 restSum;
            public readonly K.Double3 directionAccumulator;
            public readonly K.Float4 rotation;
            public readonly ChildValue[] children;

            public ParentValue(
                bool hasChildren,
                K.Double3 restSum,
                K.Double3 directionAccumulator,
                K.Float4 rotation,
                ChildValue[] children)
            {
                this.hasChildren = hasChildren;
                this.restSum = restSum;
                this.directionAccumulator = directionAccumulator;
                this.rotation = rotation;
                this.children = children;
            }
        }

        public static ChildIndex DecodeChildIndex(uint packed)
        {
            return new ChildIndex(
                (int)(packed & ChildLocalStartMask),
                (int)(packed >> ChildCountShift));
        }

        /// <summary>
        /// Computes one source parent iteration. False means a source-undefined
        /// zero/non-finite FromToRotation input was reached; no output is claimed.
        /// An empty child array succeeds with hasChildren=false and preserves the
        /// incoming parent rotation, matching the no-write source branch.
        /// </summary>
        public static bool TryCalculateParent(
            ParentSource parent,
            ChildSource[] children,
            out ParentValue value)
        {
            return TryCalculateParentCore(parent, children, false, out value);
        }

        /// <summary>
        /// Computes the same CalcLine iteration with the exact scalar equations
        /// shared by the pinned SSE2 and AVX2 Burst cores. The variant is kept
        /// explicit so a caller cannot silently guess the live CPU route. Both
        /// admitted variants execute the same source-closed value path.
        /// </summary>
        public static bool TryCalculateParentBurst(
            BurstCpuVariant variant,
            ParentSource parent,
            ChildSource[] children,
            out ParentValue value)
        {
            RequireBurstVariant(variant);
            return TryCalculateParentCore(parent, children, true, out value);
        }

        private static bool TryCalculateParentCore(
            ParentSource parent,
            ChildSource[] children,
            bool useBurstAcos,
            out ParentValue value)
        {
            if (children == null)
                throw new ArgumentNullException(nameof(children));
            RequireFinite(parent.position, nameof(parent));
            RequireFinite(parent.rotation, nameof(parent));
            RequireFinite(parent.negativeScaleDirection, nameof(parent));
            RequireFinite(parent.negativeScaleQuaternionValue, nameof(parent));
            RequireFinite(parent.rotationalInterpolation, nameof(parent));
            RequireFinite(parent.rootRotation, nameof(parent));

            if (children.Length == 0)
            {
                value = new ParentValue(
                    false,
                    default,
                    default,
                    parent.rotation,
                    Array.Empty<ChildValue>());
                return true;
            }

            K.Double3 restSum = default;
            K.Double3 directionAccumulator = default;
            var childValues = new ChildValue[children.Length];
            for (int index = 0; index < children.Length; index++)
            {
                ChildSource child = children[index];
                RequireFinite(child.position, nameof(children));
                RequireFinite(child.localPosition, nameof(children));
                RequireFinite(child.localRotation, nameof(children));

                K.Float3 signedLocalPosition = MultiplyComponents(
                    child.localPosition,
                    parent.negativeScaleDirection);
                K.Double3 restVector = ToDouble3(
                    RotateQuaternionBinary32(parent.rotation, signedLocalPosition));
                restSum = Add(restSum, restVector);

                K.Double3 childDirection = (child.attribute & FlagMove) != 0
                    ? Subtract(child.position, parent.position)
                    : restVector;
                directionAccumulator = Add(directionAccumulator, childDirection);

                if (!TryFromToRotationCore(
                        restVector,
                        childDirection,
                        1.0,
                        useBurstAcos,
                        out K.Float4 childFromTo))
                {
                    value = default;
                    return false;
                }

                K.Float4 signedLocalRotation = MultiplyComponents(
                    child.localRotation,
                    parent.negativeScaleQuaternionValue);
                K.Float4 childRotation = MultiplyQuaternionBinary32(
                    MultiplyQuaternionBinary32(parent.rotation, signedLocalRotation),
                    childFromTo);
                childValues[index] = new ChildValue(
                    restVector,
                    childDirection,
                    childRotation);
            }

            double interpolation = (parent.attribute & FlagMove) != 0
                ? parent.rotationalInterpolation
                : parent.rootRotation;
            if (!TryFromToRotationCore(
                    restSum,
                    directionAccumulator,
                    interpolation,
                    useBurstAcos,
                    out K.Float4 parentFromTo))
            {
                value = default;
                return false;
            }

            value = new ParentValue(
                true,
                restSum,
                directionAccumulator,
                MultiplyQuaternionBinary32(parentFromTo, parent.rotation),
                childValues);
            return true;
        }

        /// <summary>
        /// Unpatched managed MathUtility.FromToRotation equation. It deliberately
        /// fails closed for zero/non-finite inputs, for which the recovered method
        /// has no explicit guard and the contract makes no output claim.
        /// </summary>
        public static bool TryFromToRotation(
            K.Double3 from,
            K.Double3 to,
            double interpolation,
            out K.Float4 rotation)
        {
            return TryFromToRotationCore(from, to, interpolation, false, out rotation);
        }

        /// <summary>
        /// Exact value path shared by the pinned CalcLine SSE2 and AVX2 cores.
        /// The native cores use their own double-precision acos polynomial
        /// instead of the managed fallback's System.Math.Acos call.
        /// </summary>
        public static bool TryFromToRotationBurst(
            BurstCpuVariant variant,
            K.Double3 from,
            K.Double3 to,
            double interpolation,
            out K.Float4 rotation)
        {
            RequireBurstVariant(variant);
            return TryFromToRotationCore(from, to, interpolation, true, out rotation);
        }

        private static bool TryFromToRotationCore(
            K.Double3 from,
            K.Double3 to,
            double interpolation,
            bool useBurstAcos,
            out K.Float4 rotation)
        {
            if (!IsFinite(from) || !IsFinite(to) || !IsFinite(interpolation) ||
                !TryNormalize(from, out K.Double3 u) ||
                !TryNormalize(to, out K.Double3 v))
            {
                rotation = default;
                return false;
            }

            double dot = Clamp(Dot(u, v), -1.0, 1.0);
            double angle = useBurstAcos ? AcosBurstBinary64(dot) : Math.Acos(dot);
            K.Double3 axis = Cross(u, v);
            if (Math.Abs(dot + 1.0) < ParallelEpsilon)
            {
                angle = SourcePi;
                K.Double3 reference = u.x > u.y && u.x > u.z
                    ? new K.Double3(0.0, 1.0, 0.0)
                    : new K.Double3(1.0, 0.0, 0.0);
                axis = Cross(u, reference);
            }
            else if (Math.Abs(1.0 - dot) < ParallelEpsilon)
            {
                rotation = Identity();
                return true;
            }

            if (!TryNormalize(axis, out axis))
            {
                rotation = default;
                return false;
            }

            // quaternion.AxisAngle receives float(angle * t) in the recovered
            // managed equation. Its helper then rounds the multiplication by
            // 0.5 to binary32 before evaluating the pinned float sin/cos path.
            float scaledAngle = (float)(angle * interpolation);
            float halfAngle = MultiplyBinary32(scaledAngle, 0.5f);
            K.FloatSinCosBinary32(halfAngle, out float sine, out float cosine);
            rotation = new K.Float4(
                MultiplyBinary32((float)axis.x, sine),
                MultiplyBinary32((float)axis.y, sine),
                MultiplyBinary32((float)axis.z, sine),
                cosine);
            return IsFinite(rotation);
        }

        // Exact instruction grouping and coefficients shared by the pinned
        // x64_sse2 0xf4100 and avx2 0x284c50 CalcLine cores. Explicit
        // no-inline arithmetic boundaries prevent a runtime from contracting
        // the recovered multiply/add grouping into fused operations.
        private static double AcosBurstBinary64(double value)
        {
            double absolute = DoubleFromBits(
                unchecked((ulong)BitConverter.DoubleToInt64Bits(value)) &
                0x7fffffffffffffffUL);
            double z;
            double root;
            if (absolute < 0.5)
            {
                z = MultiplyBinary64(value, value);
                root = absolute;
            }
            else
            {
                z = MultiplyBinary64(0.5, SubtractBinary64(1.0, absolute));
                root = absolute == 1.0 ? 0.0 : Math.Sqrt(z);
            }

            const double c0 = 0.031615876506539346;
            const double c1 = 0.012153605255773773;
            const double c2 = -0.015819182433299966;
            const double c3 = 0.013887151845016092;
            const double c4 = 0.019290454772679107;
            const double c5 = 0.017359569912236146;
            const double c6 = 0.006606077476277171;
            const double c7 = 0.022371761819320483;
            const double c8 = 0.030381959280381322;
            const double c9 = 0.044642856813771024;
            const double c10 = 0.07500000000378582;
            const double c11 = 0.16666666666664975;

            double z2 = MultiplyBinary64(z, z);
            double even0 = AddBinary64(
                MultiplyBinary64(z2, AddBinary64(MultiplyBinary64(z, c0), c2)),
                AddBinary64(MultiplyBinary64(z, c4), c6));
            double even1 = AddBinary64(
                MultiplyBinary64(z2, AddBinary64(MultiplyBinary64(z, c1), c3)),
                AddBinary64(MultiplyBinary64(z, c5), c7));
            double polynomialBase = AddBinary64(
                MultiplyBinary64(z2, AddBinary64(MultiplyBinary64(z, c8), c9)),
                AddBinary64(MultiplyBinary64(z, c10), c11));
            double z4 = MultiplyBinary64(z2, z2);
            double polynomial = AddBinary64(
                AddBinary64(polynomialBase, MultiplyBinary64(z4, even1)),
                MultiplyBinary64(MultiplyBinary64(z4, z4), even0));
            double term = MultiplyBinary64(MultiplyBinary64(z, root), polynomial);

            ulong sign = unchecked((ulong)BitConverter.DoubleToInt64Bits(value)) &
                0x8000000000000000UL;
            double signedRoot = DoubleFromBits(
                unchecked((ulong)BitConverter.DoubleToInt64Bits(root)) ^ sign);
            double signedTerm = DoubleFromBits(
                unchecked((ulong)BitConverter.DoubleToInt64Bits(term)) ^ sign);
            double asin = AddBinary64(signedRoot, signedTerm);
            if (absolute < 0.5)
                return SubtractBinary64(Math.PI * 0.5, asin);

            double rootPlusTerm = AddBinary64(root, term);
            double doubled = AddBinary64(rootPlusTerm, rootPlusTerm);
            return value < 0.0 ? SubtractBinary64(Math.PI, doubled) : doubled;
        }

        private static void RequireBurstVariant(BurstCpuVariant variant)
        {
            if (variant != BurstCpuVariant.X64Sse2 && variant != BurstCpuVariant.Avx2)
                throw new ArgumentOutOfRangeException(nameof(variant));
        }

        private static double DoubleFromBits(ulong bits)
        {
            return BitConverter.Int64BitsToDouble(unchecked((long)bits));
        }

        private static K.Float4 Identity()
        {
            return new K.Float4(0.0f, 0.0f, 0.0f, 1.0f);
        }

        private static K.Float3 MultiplyComponents(K.Float3 left, K.Float3 right)
        {
            return new K.Float3(
                MultiplyBinary32(left.x, right.x),
                MultiplyBinary32(left.y, right.y),
                MultiplyBinary32(left.z, right.z));
        }

        private static K.Float4 MultiplyComponents(K.Float4 left, K.Float4 right)
        {
            return new K.Float4(
                MultiplyBinary32(left.x, right.x),
                MultiplyBinary32(left.y, right.y),
                MultiplyBinary32(left.z, right.z),
                MultiplyBinary32(left.w, right.w));
        }

        /// <summary>
        /// Pinned quaternion Hamilton-product grouping. Each helper call is a
        /// binary32 rounding boundary; changing parentheses can change a bit.
        /// </summary>
        public static K.Float4 MultiplyQuaternionBinary32(K.Float4 left, K.Float4 right)
        {
            float xFirst = AddBinary32(
                MultiplyBinary32(left.w, right.x),
                MultiplyBinary32(left.x, right.w));
            float xCross = SubtractBinary32(
                MultiplyBinary32(left.y, right.z),
                MultiplyBinary32(left.z, right.y));
            float yFirst = AddBinary32(
                MultiplyBinary32(left.w, right.y),
                MultiplyBinary32(left.y, right.w));
            float yCross = SubtractBinary32(
                MultiplyBinary32(left.z, right.x),
                MultiplyBinary32(left.x, right.z));
            float zFirst = AddBinary32(
                MultiplyBinary32(left.w, right.z),
                MultiplyBinary32(left.z, right.w));
            float zCross = SubtractBinary32(
                MultiplyBinary32(left.x, right.y),
                MultiplyBinary32(left.y, right.x));
            float w = SubtractBinary32(
                SubtractBinary32(
                    SubtractBinary32(
                        MultiplyBinary32(left.w, right.w),
                        MultiplyBinary32(left.x, right.x)),
                    MultiplyBinary32(left.y, right.y)),
                MultiplyBinary32(left.z, right.z));
            return new K.Float4(
                AddBinary32(xFirst, xCross),
                AddBinary32(yFirst, yCross),
                AddBinary32(zFirst, zCross),
                w);
        }

        /// <summary>
        /// Pinned quaternion-vector helper grouping with explicit binary32
        /// intermediates. This does not normalize the input quaternion.
        /// </summary>
        public static K.Float3 RotateQuaternionBinary32(K.Float4 rotation, K.Float3 value)
        {
            float tx = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(rotation.y, value.z),
                MultiplyBinary32(rotation.z, value.y)));
            float ty = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(rotation.z, value.x),
                MultiplyBinary32(rotation.x, value.z)));
            float tz = MultiplyBinary32(2.0f, SubtractBinary32(
                MultiplyBinary32(rotation.x, value.y),
                MultiplyBinary32(rotation.y, value.x)));
            float cx = SubtractBinary32(
                MultiplyBinary32(rotation.y, tz),
                MultiplyBinary32(rotation.z, ty));
            float cy = SubtractBinary32(
                MultiplyBinary32(rotation.z, tx),
                MultiplyBinary32(rotation.x, tz));
            float cz = SubtractBinary32(
                MultiplyBinary32(rotation.x, ty),
                MultiplyBinary32(rotation.y, tx));
            return new K.Float3(
                AddBinary32(
                    AddBinary32(value.x, MultiplyBinary32(rotation.w, tx)), cx),
                AddBinary32(
                    AddBinary32(value.y, MultiplyBinary32(rotation.w, ty)), cy),
                AddBinary32(
                    AddBinary32(value.z, MultiplyBinary32(rotation.w, tz)), cz));
        }

        private static K.Double3 ToDouble3(K.Float3 value)
        {
            return new K.Double3(value.x, value.y, value.z);
        }

        private static K.Double3 Add(K.Double3 left, K.Double3 right)
        {
            return new K.Double3(
                AddBinary64(left.x, right.x),
                AddBinary64(left.y, right.y),
                AddBinary64(left.z, right.z));
        }

        private static K.Double3 Subtract(K.Double3 left, K.Double3 right)
        {
            return new K.Double3(
                SubtractBinary64(left.x, right.x),
                SubtractBinary64(left.y, right.y),
                SubtractBinary64(left.z, right.z));
        }

        private static K.Double3 Cross(K.Double3 left, K.Double3 right)
        {
            return new K.Double3(
                SubtractBinary64(
                    MultiplyBinary64(left.y, right.z),
                    MultiplyBinary64(left.z, right.y)),
                SubtractBinary64(
                    MultiplyBinary64(left.z, right.x),
                    MultiplyBinary64(left.x, right.z)),
                SubtractBinary64(
                    MultiplyBinary64(left.x, right.y),
                    MultiplyBinary64(left.y, right.x)));
        }

        private static double Dot(K.Double3 left, K.Double3 right)
        {
            return AddBinary64(
                AddBinary64(
                    MultiplyBinary64(left.x, right.x),
                    MultiplyBinary64(left.y, right.y)),
                MultiplyBinary64(left.z, right.z));
        }

        private static bool TryNormalize(K.Double3 value, out K.Double3 normalized)
        {
            double lengthSquared = Dot(value, value);
            if (!(lengthSquared > 0.0) || !IsFinite(lengthSquared))
            {
                normalized = default;
                return false;
            }

            double inverseLength = DivideBinary64(1.0, Math.Sqrt(lengthSquared));
            normalized = new K.Double3(
                MultiplyBinary64(value.x, inverseLength),
                MultiplyBinary64(value.y, inverseLength),
                MultiplyBinary64(value.z, inverseLength));
            return IsFinite(normalized);
        }

        private static double Clamp(double value, double minimum, double maximum)
        {
            return value < minimum ? minimum : value > maximum ? maximum : value;
        }

        private static void RequireFinite(K.Double3 value, string name)
        {
            if (!IsFinite(value))
                throw new ArgumentOutOfRangeException(name, "A vector component is non-finite.");
        }

        private static void RequireFinite(K.Float3 value, string name)
        {
            if (!IsFinite(value.x) || !IsFinite(value.y) || !IsFinite(value.z))
                throw new ArgumentOutOfRangeException(name, "A vector component is non-finite.");
        }

        private static void RequireFinite(K.Float4 value, string name)
        {
            if (!IsFinite(value))
                throw new ArgumentOutOfRangeException(name, "A quaternion component is non-finite.");
        }

        private static void RequireFinite(double value, string name)
        {
            if (!IsFinite(value))
                throw new ArgumentOutOfRangeException(name, "A scalar is non-finite.");
        }

        private static bool IsFinite(K.Double3 value)
        {
            return IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);
        }

        private static bool IsFinite(K.Float4 value)
        {
            return IsFinite(value.x) && IsFinite(value.y) &&
                IsFinite(value.z) && IsFinite(value.w);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        // Explicit no-inline float ABI boundaries prevent a Mono backend from
        // retaining an intermediate expression at wider precision.
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float AddBinary32(float left, float right)
        {
            return left + right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float SubtractBinary32(float left, float right)
        {
            return left - right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float MultiplyBinary32(float left, float right)
        {
            return left * right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double AddBinary64(double left, double right)
        {
            return left + right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double SubtractBinary64(double left, double right)
        {
            return left - right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double MultiplyBinary64(double left, double right)
        {
            return left * right;
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static double DivideBinary64(double left, double right)
        {
            return left / right;
        }
    }

    /// <summary>
    /// Inert admission boundary for CalcLine execution. A caller may select a
    /// value kernel only from a separately validated live resolver trace. This
    /// class has no scene, PlayerLoop, solver, or Transform-writeback hook.
    /// </summary>
    public static class EndfieldSecondaryDynamicsCalcLineRouteSelection
    {
        public enum ExecutionRoute
        {
            Unselected,
            ManagedUnpatched,
            BurstX64Sse2,
            BurstAvx2,
        }

        public readonly struct Observation
        {
            public readonly bool traceValidated;
            public readonly int burstGateObservationCount;
            public readonly bool burstEnabled;
            public readonly bool directCallTargetObserved;
            public readonly int cpuSelectionObservationCount;
            public readonly string cpuVariant;
            public readonly int ifixGateObservationCount;
            public readonly bool ifixPatched;
            public readonly string ifixCalcLineRoute;

            public Observation(
                bool traceValidated,
                int burstGateObservationCount,
                bool burstEnabled,
                bool directCallTargetObserved,
                int cpuSelectionObservationCount,
                string cpuVariant,
                int ifixGateObservationCount,
                bool ifixPatched,
                string ifixCalcLineRoute)
            {
                this.traceValidated = traceValidated;
                this.burstGateObservationCount = burstGateObservationCount;
                this.burstEnabled = burstEnabled;
                this.directCallTargetObserved = directCallTargetObserved;
                this.cpuSelectionObservationCount = cpuSelectionObservationCount;
                this.cpuVariant = cpuVariant;
                this.ifixGateObservationCount = ifixGateObservationCount;
                this.ifixPatched = ifixPatched;
                this.ifixCalcLineRoute = ifixCalcLineRoute;
            }
        }

        public static bool TrySelect(Observation observation, out ExecutionRoute route)
        {
            route = ExecutionRoute.Unselected;
            if (!observation.traceValidated ||
                observation.burstGateObservationCount != 1)
                return false;

            if (observation.burstEnabled)
            {
                if (!observation.directCallTargetObserved ||
                    observation.cpuSelectionObservationCount != 1 ||
                    observation.ifixGateObservationCount != 0 ||
                    observation.ifixPatched ||
                    !string.IsNullOrEmpty(observation.ifixCalcLineRoute))
                    return false;
                if (string.Equals(observation.cpuVariant, "x64_sse2",
                        StringComparison.Ordinal))
                {
                    route = ExecutionRoute.BurstX64Sse2;
                    return true;
                }
                if (string.Equals(observation.cpuVariant, "avx2",
                        StringComparison.Ordinal))
                {
                    route = ExecutionRoute.BurstAvx2;
                    return true;
                }
                return false;
            }

            // The Invoke null-pointer fallback is statically unreachable after
            // a normal GetILPPMethodFunctionPointer2 return. A disabled Burst
            // route therefore admits only the observed direct-call fallback,
            // and only when its FromToRotation IFix gate is explicitly false.
            if (observation.directCallTargetObserved ||
                observation.cpuSelectionObservationCount != 0 ||
                !string.IsNullOrEmpty(observation.cpuVariant) ||
                observation.ifixGateObservationCount != 1 ||
                observation.ifixPatched ||
                !string.Equals(observation.ifixCalcLineRoute,
                    "direct_call_fallback", StringComparison.Ordinal))
            {
                return false;
            }
            route = ExecutionRoute.ManagedUnpatched;
            return true;
        }

        public static bool TryCalculateParent(
            ExecutionRoute route,
            EndfieldSecondaryDynamicsCalcLineManagedEquations.ParentSource parent,
            EndfieldSecondaryDynamicsCalcLineManagedEquations.ChildSource[] children,
            out EndfieldSecondaryDynamicsCalcLineManagedEquations.ParentValue value)
        {
            switch (route)
            {
                case ExecutionRoute.ManagedUnpatched:
                    return EndfieldSecondaryDynamicsCalcLineManagedEquations.TryCalculateParent(
                        parent, children, out value);
                case ExecutionRoute.BurstX64Sse2:
                    return EndfieldSecondaryDynamicsCalcLineManagedEquations.TryCalculateParentBurst(
                        EndfieldSecondaryDynamicsCalcLineManagedEquations.BurstCpuVariant.X64Sse2,
                        parent, children, out value);
                case ExecutionRoute.BurstAvx2:
                    return EndfieldSecondaryDynamicsCalcLineManagedEquations.TryCalculateParentBurst(
                        EndfieldSecondaryDynamicsCalcLineManagedEquations.BurstCpuVariant.Avx2,
                        parent, children, out value);
                default:
                    value = default;
                    return false;
            }
        }
    }
}
