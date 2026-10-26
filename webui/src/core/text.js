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
  function stringFilePaths(text) {
    const normalized = text.includes("\\") ? text.replace(/\\/g, "/") : text;
    // Without a delimiter a match can only end at the string's end, so the
    // whole string is the one path; skip the per-position regex retries.
    if (!/[\s<>"'?#=&]/.test(normalized)) {
      return /\.[a-z][a-z0-9]{0,11}$/i.test(normalized) ? [normalized] : [];
    }
    const paths =normalized.match(/[^\s<>"'?#=]+\.[a-z][a-z0-9]{0,11}(?=$|[\s<>"'?#&])/gi) || [];
    // A scalar path may contain spaces (unlike paths embedded in markup).
    if (!/[\n<>"']/.test(normalized) && /^[^?#]+\.[a-z][a-z0-9]{0,11}(?:[?#].*)?$/i.test(normalized)) {
      paths.push(normalized.split(/[?#]/)[0]);
    }
    return paths;
  }

  // Page indexes repeat the same strings (directories, kinds, shared paths)
  // across tens of thousands of rows; cache each string's file names.
  const FILE_NAME_CACHE = new Map();
  const FILE_NAME_CACHE_LIMIT = 200000;
  const NO_FILE_NAMES = [];

  function stringFileNames(value) {
    // Both patterns need ".ext", so a string without a dot names no file.
    if (!value.includes(".")) return NO_FILE_NAMES;
    let names = FILE_NAME_CACHE.get(value);
    if (names) return names;
    const found = new Set();
    const add = (paths) => {
      for (const path of paths) {
        found.add(path);
        found.add(path.split("/").pop());
      }
    };
    add(stringFilePaths(value));
    if (value.includes("%")) {
      let decoded = value;
      try { decoded = decodeURIComponent(value); } catch (_error) { /* Keep malformed URLs searchable. */ }
      if (decoded !== value) add(stringFilePaths(decoded));
    }
    names = found.size ? [...found] : NO_FILE_NAMES;
    if (FILE_NAME_CACHE.size >= FILE_NAME_CACHE_LIMIT) FILE_NAME_CACHE.clear();
    FILE_NAME_CACHE.set(value, names);
    return names;
  }

  function linkedFileSearchText(...values) {
    const files = new Set();
    const seen = new Set();
    function visit(value) {
      if (typeof value === "string") {
        for (const name of stringFileNames(value)) files.add(name);
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

  // Compiled token regexes, reused across rows and keystrokes. Search loops call
  // queryScore once per row, so compiling per call dominated filter time on
  // large pages; the cache is cleared wholesale once it grows past a bound.
  const QUERY_REGEX_CACHE = new Map();
  const QUERY_REGEX_CACHE_LIMIT = 512;

  function compileQueryRegex(token) {
    try {
      return new RegExp(token, "i");
    } catch (_error) {
      // A malformed expression remains usable as a literal search instead of
      // making the entire filter unusable while the user is still typing.
      return new RegExp(token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
    }
  }

  // The returned regex has no global flag, so `test` keeps no lastIndex state
  // and the shared instance is safe to reuse.
  function queryRegex(token) {
    const key = String(token || "");
    let regex = QUERY_REGEX_CACHE.get(key);
    if (!regex) {
      if (QUERY_REGEX_CACHE.size >= QUERY_REGEX_CACHE_LIMIT) QUERY_REGEX_CACHE.clear();
      regex = compileQueryRegex(key);
      QUERY_REGEX_CACHE.set(key, regex);
    }
    return regex;
  }

  // Count how many distinct query tokens appear in `haystack` (a string, or an
  // array of strings that are joined first). This doubles as the OR filter test
  // (score > 0) and the ranking key (more tokens matched sorts higher).
  // Filter loops pass the same tokens array for every row, so the regexes
  // compiled for the last array are reused without any per-row lookup.
  let scoredTokens = null;
  let scoredRegexes = [];

  function queryScore(haystack, tokens) {
    if (!tokens || !tokens.length) return 0;
    if (tokens !== scoredTokens) {
      scoredTokens = tokens;
      scoredRegexes = tokens.map((token) => queryRegex(token));
    }
    const text = typeof haystack === "string" ? haystack
      : Array.isArray(haystack) ? haystack.join("\n") : String(haystack || "");
    let matched = 0;
    for (let index = 0; index < scoredRegexes.length; index += 1) {
      if (scoredRegexes[index].test(text)) matched += 1;
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
