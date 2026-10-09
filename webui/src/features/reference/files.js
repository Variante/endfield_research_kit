// Text Tables keeps network reads and retained payloads bounded. Preview reads
// stop at the byte limit without parsing a partial JSON document; full reads
// reject oversized files even when Content-Length is missing or inaccurate.
(() => {
  const MAX_TABLE_BYTES = 32 * 1024 * 1024;
  const MAX_PREVIEW_BYTES = 256 * 1024;
  const MAX_PREVIEW_CHARS = 256 * 1024;

  function fileTooLarge() {
    const error = new Error("Table exceeds the rendered-view size limit");
    error.code = "REFERENCE_FILE_TOO_LARGE";
    return error;
  }

  async function readText(response, { preview = false, signal, maxBytes = MAX_TABLE_BYTES } = {}) {
    const reader = response.body?.getReader();
    if (!reader) return { text: "", bytes: 0, truncated: false };
    const declaredBytes = Number(response.headers.get("Content-Length"));
    const decoder = new TextDecoder();
    const parts = [];
    let bytes = 0;
    let complete = false;
    const checkAbort = () => {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
    };
    const abort = () => { reader.cancel().catch(() => {}); };
    signal?.addEventListener("abort", abort, { once: true });
    try {
      checkAbort();
      if (!preview && declaredBytes > maxBytes) throw fileTooLarge();
      while (true) {
        checkAbort();
        const { value, done } = await reader.read();
        checkAbort();
        if (done) {
          complete = true;
          parts.push(decoder.decode());
          return { text: parts.join(""), bytes, truncated: false };
        }
        const remaining = maxBytes - bytes;
        if (value.byteLength > remaining) {
          if (!preview) throw fileTooLarge();
          parts.push(decoder.decode(value.subarray(0, remaining), { stream: true }));
          // Do not flush an incomplete UTF-8 code point at a preview boundary.
          return { text: parts.join(""), bytes: maxBytes, truncated: true };
        }
        bytes += value.byteLength;
        parts.push(decoder.decode(value, { stream: true }));
      }
    } finally {
      signal?.removeEventListener("abort", abort);
      if (!complete) await reader.cancel().catch(() => {});
      reader.releaseLock();
    }
  }

  // A byte budget is based on downloaded JSON sizes, with an entry ceiling for
  // tiny tables. Parsed objects have overhead; neither budget is a heap claim.
  function createCache(maxBytes, maxEntries) {
    const entries = new Map();
    let bytes = 0;
    const remove = (key) => {
      const entry = entries.get(key);
      if (!entry) return;
      bytes -= entry.bytes;
      entries.delete(key);
    };
    return {
      get(key) {
        const entry = entries.get(key);
        if (!entry) return undefined;
        entries.delete(key);
        entries.set(key, entry);
        return entry.value;
      },
      set(key, value, size) {
        remove(key);
        const weight = Math.max(1, Number(size) || 1);
        if (weight > maxBytes) return;
        while (entries.size && (bytes + weight > maxBytes || entries.size >= maxEntries)) {
          remove(entries.keys().next().value);
        }
        entries.set(key, { value, bytes: weight });
        bytes += weight;
      },
      clear() { entries.clear(); bytes = 0; },
    };
  }

  window.WebUI.referenceFiles = {
    readText, createCache, MAX_TABLE_BYTES, MAX_PREVIEW_BYTES, MAX_PREVIEW_CHARS,
  };
})();
