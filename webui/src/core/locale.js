(() => {
  const WebUI = window.WebUI;

  function normalizeUiLocale(locale) {
    const value = String(locale || "").toLowerCase();
    return value === "zh" || value === "en" ? value : "";
  }

  Object.assign(WebUI, { normalizeUiLocale });
})();
