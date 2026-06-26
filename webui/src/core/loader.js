(() => {
  const WebUI = window.WebUI;

  const LOADER_TEXT = {
    zh: { loading: "加载中…" },
    en: { loading: "Loading…" },
  };

  function loaderLocale() {
    const raw = String(window.WEBUI_UI_LOCALE || "zh").toLowerCase();
    return raw === "en" ? "en" : "zh";
  }

  function loaderText(key) {
    return (LOADER_TEXT[loaderLocale()] || LOADER_TEXT.en)[key] || key;
  }

  function viewContainer(view) {
    if (view instanceof HTMLElement) return view;
    return document.querySelector(`#${view}-view`);
  }

  function ensureLoader(view) {
    const container = viewContainer(view);
    if (!container) return null;
    let loader = container.querySelector(":scope > .view-loader");
    if (loader) return loader;

    loader = document.createElement("div");
    loader.className = "view-loader";
    loader.hidden = true;
    loader.setAttribute("role", "status");
    loader.setAttribute("aria-live", "polite");
    loader.innerHTML =
      `<div class="view-loader-card">` +
        `<div class="view-loader-label"></div>` +
        `<div class="view-loader-track is-indeterminate"><div class="view-loader-fill"></div></div>` +
        `<div class="view-loader-pct"></div>` +
      `</div>`;
    container.appendChild(loader);
    return loader;
  }

  // Show the loading overlay for a view, resetting it to an indeterminate state.
  function showLoader(view, label) {
    const loader = ensureLoader(view);
    if (!loader) return;
    const labelNode = loader.querySelector(".view-loader-label");
    if (labelNode) labelNode.textContent = label || loaderText("loading");
    const track = loader.querySelector(".view-loader-track");
    const fill = loader.querySelector(".view-loader-fill");
    const pct = loader.querySelector(".view-loader-pct");
    if (track) track.classList.add("is-indeterminate");
    if (fill) fill.style.width = "";
    if (pct) pct.textContent = "";
    loader.hidden = false;
    loader.classList.remove("is-hiding");
  }

  // Update progress. `ratio` in [0, 1] shows a determinate bar; null/undefined
  // keeps the indeterminate animation.
  function updateLoader(view, ratio, label) {
    const loader = ensureLoader(view);
    if (!loader || loader.hidden) return;
    if (label) {
      const labelNode = loader.querySelector(".view-loader-label");
      if (labelNode) labelNode.textContent = label;
    }
    const track = loader.querySelector(".view-loader-track");
    const fill = loader.querySelector(".view-loader-fill");
    const pct = loader.querySelector(".view-loader-pct");
    if (ratio == null || !Number.isFinite(ratio)) {
      if (track) track.classList.add("is-indeterminate");
      // Clear the inline width so the indeterminate CSS (40% sweeping block)
      // applies; otherwise a stale width keeps the bar looking ~full with no
      // matching number.
      if (fill) fill.style.width = "";
      if (pct) pct.textContent = "";
      return;
    }
    const clamped = Math.max(0, Math.min(1, ratio));
    if (track) track.classList.remove("is-indeterminate");
    if (fill) fill.style.width = `${(clamped * 100).toFixed(1)}%`;
    if (pct) pct.textContent = `${Math.round(clamped * 100)}%`;
  }

  // Resolve after the browser has had a chance to paint, so a just-set progress
  // value is actually shown before the next blocking step runs. Falls back to a
  // timeout when frames are not firing (e.g. a backgrounded tab) so callers that
  // await this never stall.
  function nextPaint() {
    return new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        resolve();
      };
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(() => requestAnimationFrame(finish));
      }
      setTimeout(finish, 60);
    });
  }

  // Hide the overlay with a short fade.
  function hideLoader(view) {
    const container = viewContainer(view);
    const loader = container && container.querySelector(":scope > .view-loader");
    if (!loader || loader.hidden) return;
    loader.classList.add("is-hiding");
    const finish = () => {
      loader.hidden = true;
      loader.classList.remove("is-hiding");
    };
    let done = false;
    const onEnd = () => {
      if (done) return;
      done = true;
      loader.removeEventListener("transitionend", onEnd);
      finish();
    };
    loader.addEventListener("transitionend", onEnd);
    // Fallback in case the transition does not fire (e.g. reduced motion).
    setTimeout(onEnd, 320);
  }

  // fetch() wrapper that reports download progress via `init.onProgress(ratio,
  // loaded, total)`. `ratio` is null when the total size is unknown so callers
  // can fall back to an indeterminate bar. Returns a normal Response.
  async function fetchWithProgress(url, init = {}) {
    const onProgress = typeof init.onProgress === "function" ? init.onProgress : null;
    const opts = { ...init };
    delete opts.onProgress;

    const res = await fetch(url, opts);
    if (!onProgress || !res.ok || !res.body || typeof ReadableStream === "undefined") {
      return res;
    }

    // When the response is compressed (gzip/br), Content-Length is the encoded
    // size while the stream yields decoded bytes, so `loaded` overshoots and the
    // ratio is meaningless. Treat the total as unknown in that case.
    const encoded = String(res.headers.get("Content-Encoding") || "").trim();
    let total = encoded ? 0 : Number(res.headers.get("Content-Length")) || 0;
    let loaded = 0;
    const reader = res.body.getReader();

    const stream = new ReadableStream({
      async pull(controller) {
        try {
          const { done, value } = await reader.read();
          if (done) {
            controller.close();
            return;
          }
          loaded += value.byteLength;
          // If we ever exceed the advertised length the header was unreliable
          // (e.g. proxy-applied compression); drop to indeterminate.
          if (total && loaded > total) total = 0;
          onProgress(total ? loaded / total : null, loaded, total);
          controller.enqueue(value);
        } catch (error) {
          controller.error(error);
        }
      },
      cancel(reason) {
        reader.cancel(reason);
      },
    });

    return new Response(stream, {
      headers: res.headers,
      status: res.status,
      statusText: res.statusText,
    });
  }

  Object.assign(WebUI, { showLoader, updateLoader, hideLoader, nextPaint, fetchWithProgress });
})();
