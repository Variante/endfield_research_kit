using System;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// One explicit selector for the source-backed deferred-resolver input
    /// probe.  It opts the already recovered b30/b35/b31/b34 publishers into
    /// the same frame without enabling the retail pass-0 draw.
    /// </summary>
    internal static class EndfieldRecoveredDeferredResolverBindingPolicy
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_INPUT_PROBE";
        internal const string ResourceProbeEnvironmentVariable =
            "ENDFIELD_RECOVERED_DEFERRED_RESOLVER_RESOURCE_PROBE";
        internal const string ExactConsumerEnvironmentVariable =
            "ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER";

        internal static bool IsRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(EnvironmentVariable);
                string resourceValue = Environment.GetEnvironmentVariable(
                    ResourceProbeEnvironmentVariable);
                string exactValue = Environment.GetEnvironmentVariable(
                    ExactConsumerEnvironmentVariable);
                return IsEnabled(value) || IsEnabled(resourceValue) ||
                    IsEnabled(exactValue);
            }
        }

        internal static bool IsExactConsumerRequested
        {
            get
            {
                return IsEnabled(Environment.GetEnvironmentVariable(
                    ExactConsumerEnvironmentVariable));
            }
        }

        internal static bool IsResourceProbeRequested
        {
            get
            {
                return IsEnabled(Environment.GetEnvironmentVariable(
                    ResourceProbeEnvironmentVariable));
            }
        }

        private static bool IsEnabled(string value)
        {
            return value == "1" ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }
    }
}
