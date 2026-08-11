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

        internal static bool IsRequested
        {
            get
            {
                string value = Environment.GetEnvironmentVariable(
                    EnvironmentVariable);
                return value == "1" ||
                    string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
            }
        }
    }
}
