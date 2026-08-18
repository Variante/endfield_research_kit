using System;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Shared parsing for the recovered-feature environment selectors.
    ///
    /// Components that also carry a serialized request previously OR-ed the
    /// serialized value with the environment value, so a scene saved by an
    /// earlier diagnostic run kept that feature on and no selector value could
    /// turn it back off. Diagnostics that set a selector to <c>0</c> to request
    /// the disabled control silently got the enabled state instead.
    ///
    /// The selector is therefore tri-state: unset leaves the serialized default
    /// in charge, a truthy value forces the feature on, and a falsey value
    /// forces it off. Unrecognized text is treated as unset so a typo cannot
    /// silently enable a recovered path.
    /// </summary>
    public static class EndfieldRecoveredSelector
    {
        /// <summary>
        /// Returns the explicit request carried by <paramref name="variable"/>,
        /// or null when it is unset, empty, or unrecognized.
        /// </summary>
        public static bool? Explicit(string variable)
        {
            if (string.IsNullOrEmpty(variable))
                return null;

            string value = Environment.GetEnvironmentVariable(variable);
            if (string.IsNullOrEmpty(value))
                return null;

            value = value.Trim();
            if (string.Equals(value, "1", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "yes", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase))
                return true;

            if (string.Equals(value, "0", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "false", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "no", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "off", StringComparison.OrdinalIgnoreCase))
                return false;

            return null;
        }

        /// <summary>
        /// Resolves a feature request from its selector and the serialized
        /// value saved in the scene.
        /// </summary>
        public static bool Resolve(string variable, bool serializedDefault)
        {
            return Explicit(variable) ?? serializedDefault;
        }
    }
}
