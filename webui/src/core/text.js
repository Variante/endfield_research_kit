(() => {
  const WebUI = window.WebUI;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  function textIncludes(value, q) {
    return String(value || "").toLowerCase().includes(q);
  }

  function formatNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toLocaleString() : "";
  }

  function formatSignedNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "";
    return `${number > 0 ? "+" : ""}${number.toLocaleString()}`;
  }

  function applyTemplate(template, replacements = {}) {
    return String(template || "").replace(/\{(\w+)\}/g, (_, name) => String(replacements[name] ?? ""));
  }

  // ---- Shared search: split a query on whitespace, then OR-match its tokens ----

  // Turn a raw query into distinct lowercased, whitespace-separated tokens. A
  // single word yields a one-element list, so callers can treat every query
  // uniformly. Duplicates are dropped so a repeated word neither double-counts in
  // queryScore nor trips the multi-word ("more than one token") ranking path.
  function parseQuery(query) {
    return [...new Set(String(query || "").trim().toLowerCase().split(/\s+/).filter(Boolean))];
  }

  // Count how many distinct query tokens appear in `haystack` (a string, or an
  // array of strings that are joined first). This doubles as the OR filter test
  // (score > 0) and the ranking key (more tokens matched sorts higher).
  function queryScore(haystack, tokens) {
    if (!tokens || !tokens.length) return 0;
    const text = (Array.isArray(haystack) ? haystack.join("\n") : String(haystack || "")).toLowerCase();
    let matched = 0;
    for (const token of tokens) {
      if (text.includes(token)) matched += 1;
    }
    return matched;
  }

  // OR-semantics membership test: no tokens keeps everything, otherwise at least
  // one token must be present.
  function queryMatches(haystack, tokens) {
    if (!tokens || !tokens.length) return true;
    return queryScore(haystack, tokens) > 0;
  }

  // Build a global, case-insensitive regex that matches any query token, for
  // wrapping hits in <mark>. Accepts a token array or a raw string. Returns null
  // when there is nothing to highlight.
  function highlightRegex(tokensOrQuery) {
    const tokens = Array.isArray(tokensOrQuery) ? tokensOrQuery : parseQuery(tokensOrQuery);
    if (!tokens.length) return null;
    const escaped = tokens
      .map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
      .sort((a, b) => b.length - a.length); // prefer longer matches first
    return new RegExp(`(${escaped.join("|")})`, "ig");
  }

  Object.assign(WebUI, {
    escapeHtml,
    textIncludes,
    formatNumber,
    formatSignedNumber,
    applyTemplate,
    parseQuery,
    queryScore,
    queryMatches,
    highlightRegex,
  });
})();
