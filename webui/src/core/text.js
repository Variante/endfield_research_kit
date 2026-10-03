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

  // Index nested file references without stringifying unrelated record fields.
  // Keep both the path and basename, including decoded URL spellings.
  function linkedFileSearchText(...values) {
    const files = new Set();
    const seen = new Set();
    function visit(value) {
      if (typeof value === "string") {
        let decoded = value;
        try { decoded = decodeURIComponent(value); } catch (_error) { /* Keep malformed URLs searchable. */ }
        for (const text of new Set([value, decoded])) {
          const normalized = text.replace(/\\/g, "/");
          const paths = normalized.match(/[^\s<>"'?#=]+\.[a-z][a-z0-9]{0,11}(?=$|[\s<>"'?#&])/gi) || [];
          // A scalar path may contain spaces (unlike paths embedded in markup).
          if (!/[\n<>"']/.test(normalized) && /^[^?#]+\.[a-z][a-z0-9]{0,11}(?:[?#].*)?$/i.test(normalized)) {
            paths.push(normalized.split(/[?#]/)[0]);
          }
          for (const path of paths) {
            files.add(path);
            files.add(path.split("/").pop());
          }
        }
      } else if (value && typeof value === "object" && !seen.has(value)) {
        seen.add(value);
        for (const child of Object.values(value)) visit(child);
      }
    }
    values.forEach(visit);
    return [...files].join("\n");
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

  // ---- Shared search: split a query on whitespace, then OR-match its regex tokens ----

  // Turn a raw query into distinct whitespace-separated regex tokens. A
  // single word yields a one-element list, so callers can treat every query
  // uniformly. Duplicates are dropped so a repeated word neither double-counts in
  // queryScore nor trips the multi-word ("more than one token") ranking path.
  function parseQuery(query) {
    return [...new Set(String(query || "").trim().split(/\s+/).filter(Boolean))];
  }

  function queryRegex(token) {
    try {
      return new RegExp(String(token || ""), "i");
    } catch (_error) {
      // A malformed expression remains usable as a literal search instead of
      // making the entire filter unusable while the user is still typing.
      return new RegExp(String(token || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
    }
  }

  // Count how many distinct query tokens appear in `haystack` (a string, or an
  // array of strings that are joined first). This doubles as the OR filter test
  // (score > 0) and the ranking key (more tokens matched sorts higher).
  function queryScore(haystack, tokens) {
    if (!tokens || !tokens.length) return 0;
    const text = Array.isArray(haystack) ? haystack.join("\n") : String(haystack || "");
    let matched = 0;
    for (const token of tokens) {
      if (queryRegex(token).test(text)) matched += 1;
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
  // wrapping hits in <mark>. Query tokens are regular expressions. Invalid
  // tokens are treated as literals, matching queryScore/queryMatches.
  function highlightRegex(tokensOrQuery) {
    const tokens = Array.isArray(tokensOrQuery) ? tokensOrQuery : parseQuery(tokensOrQuery);
    if (!tokens.length) return null;
    const patterns = tokens
      .map((token) => {
        try { return new RegExp(String(token || ""), "i").source; }
        catch (_error) { return queryRegex(token).source; }
      })
      .sort((a, b) => b.length - a.length); // prefer longer patterns first
    try { return new RegExp(`(${patterns.join("|")})`, "ig"); }
    catch (_error) { return queryRegex(tokens[0]); }
  }

  Object.assign(WebUI, {
    escapeHtml,
    textIncludes,
    linkedFileSearchText,
    formatNumber,
    formatSignedNumber,
    applyTemplate,
    parseQuery,
    queryRegex,
    queryScore,
    queryMatches,
    highlightRegex,
  });
})();
