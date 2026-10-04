(() => {
  const WebUI = window.WebUI;

  const LOADER_TEXT = {
    zh: { loading: "加载中…", downloading: "正在下载数据…", parsing: "正在解析数据…", preparing: "正在整理数据…", rendering: "正在显示内容…" },
    en: { loading: "Loading…", downloading: "Downloading data…", parsing: "Reading data…", preparing: "Preparing data…", rendering: "Displaying content…" },
  };
  const pendingHides = new WeakMap();

  function loaderLocale() {
    const raw = String(window.WEBUI_UI_LOCALE || "zh").toLowerCase();
    return raw === "en" ? "en" : "zh";
  }

  function loaderText(key) {
    return LOADER_TEXT[loaderLocale()][key] || key;
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
    pendingHides.get(loader)?.();
    const labelNode = loader.querySelector(".view-loader-label");
    labelNode.textContent = label || loaderText("loading");
    const track = loader.querySelector(".view-loader-track");
    const fill = loader.querySelector(".view-loader-fill");
    const pct = loader.querySelector(".view-loader-pct");
    track.classList.add("is-indeterminate");
    fill.style.width = "";
    pct.textContent = "";
    track.setAttribute("role", "progressbar");
    track.setAttribute("aria-label", label || loaderText("loading"));
    track.removeAttribute("aria-valuenow");
    loader.hidden = false;
    loader.classList.remove("is-hiding");
  }

  // Update progress. `ratio` in [0, 1] shows a determinate bar; null/undefined
  // keeps the indeterminate animation.
  function updateLoader(view, ratio, label) {
    const loader = ensureLoader(view);
    if (!loader || loader.hidden) return;
    const track = loader.querySelector(".view-loader-track");
    if (label) {
      const labelNode = loader.querySelector(".view-loader-label");
      labelNode.textContent = label;
      track.setAttribute("aria-label", label);
    }
    const fill = loader.querySelector(".view-loader-fill");
    const pct = loader.querySelector(".view-loader-pct");
    if (ratio == null || !Number.isFinite(ratio)) {
      track.classList.add("is-indeterminate");
      // Clear the inline width so the indeterminate CSS (40% sweeping block)
      // applies; otherwise a stale width keeps the bar looking ~full with no
      // matching number.
      fill.style.width = "";
      pct.textContent = "";
      track.removeAttribute("aria-valuenow");
      return;
    }
    const clamped = Math.max(0, Math.min(1, ratio));
    track.classList.remove("is-indeterminate");
    fill.style.width = `${(clamped * 100).toFixed(1)}%`;
    pct.textContent = `${Math.round(clamped * 100)}%`;
    track.setAttribute("aria-valuenow", String(Math.round(clamped * 100)));
  }

  // Percentages describe this named phase, never an estimated share of total
  // load time. CPU work and requests with unknown sizes stay indeterminate.
  function updateLoaderPhase(view, phase, ratio = null) {
    updateLoader(view, ratio, loaderText(phase));
  }

  function loaderProgress(view, isCurrent = () => true) {
    return (ratio, _loaded, _total, phase = "downloading") => {
      if (!isCurrent()) return;
      updateLoaderPhase(view, phase, ratio);
      if (phase === "parsing") return nextPaint();
    };
  }

  // Resolve after the browser has had a chance to paint, so a just-set progress
  // value is actually shown before the next blocking step runs. Falls back to a
  // timeout when frames are not firing (e.g. a backgrounded tab) so callers that
  // await this never stall.
  function nextPaint() {
    return new Promise((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(resolve));
      setTimeout(resolve, 60);
    });
  }

  // Hide the overlay with a short fade.
  function hideLoader(view) {
    const container = viewContainer(view);
    const loader = container && container.querySelector(":scope > .view-loader");
    if (!loader || loader.hidden) return;
    pendingHides.get(loader)?.();
    loader.classList.add("is-hiding");
    const finish = () => {
      loader.hidden = true;
      loader.classList.remove("is-hiding");
    };
    let done = false;
    const cleanup = () => {
      done = true;
      clearTimeout(timer);
      loader.removeEventListener("transitionend", onEnd);
      pendingHides.delete(loader);
    };
    const onEnd = (event) => {
      if (event && (event.target !== loader || event.propertyName !== "opacity")) return;
      if (done) return;
      cleanup();
      finish();
    };
    loader.addEventListener("transitionend", onEnd);
    // Fallback in case the transition does not fire (e.g. reduced motion).
    const timer = setTimeout(onEnd, 320);
    pendingHides.set(loader, cleanup);
  }

  // fetch() wrapper that reports download progress via `init.onProgress(ratio,
  // loaded, total)`. `ratio` is null when the total size is unknown so callers
  // can fall back to an indeterminate bar. A fourth argument names the phase;
  // the final `parsing` callback may yield a paint before JSON decoding blocks.
  // Returns a normal Response.
  async function fetchWithProgress(url, init = {}) {
    const onProgress = typeof init.onProgress === "function" ? init.onProgress : null;
    const opts = { ...init };
    delete opts.onProgress;

    let res = await fetch(url, opts);

    // Some responses (notably 304 Not Modified under conditional caching) may
    // have an empty body and would otherwise produce unexpected JSON parse
    // errors on callers that expect JSON. Force a no-store refresh in that case.
    if (!res.body && res.status === 304) {
      res = await fetch(url, {
        ...opts,
        cache: "no-store",
      });
    }

    if (!onProgress || !res.ok || !res.body || typeof ReadableStream === "undefined") {
      return res;
    }

    // When the response is compressed (gzip/br), Content-Length is the encoded
    // size while the stream yields decoded bytes, so `loaded` overshoots and the
    // ratio is meaningless. Treat the total as unknown in that case.
    const encoded = String(res.headers.get("Content-Encoding") || "").trim().toLowerCase();
    const length = Number(res.headers.get("Content-Length"));
    let total = (!encoded || encoded === "identity") && Number.isFinite(length) && length > 0 ? length : 0;
    let loaded = 0;
    const reader = res.body.getReader();
    onProgress(total ? 0 : null, loaded, total, "downloading");

    let failed = false;
    const stream = new ReadableStream({
      async pull(controller) {
        // Once the consumer errors the stream (e.g. response.json() gives up on
        // an oversized body) the controller rejects close()/enqueue(); that
        // DOMException would otherwise mask the real failure.
        if (failed) return;
        try {
          const { done, value } = await reader.read();
          if (failed) return;
          if (done) {
            await onProgress(null, loaded, total, "parsing");
            if (failed) return;
            controller.close();
            return;
          }
          loaded += value.byteLength;
          // If we ever exceed the advertised length the header was unreliable
          // (e.g. proxy-applied compression); drop to indeterminate.
          if (total && loaded > total) total = 0;
          onProgress(total ? loaded / total : null, loaded, total, "downloading");
          controller.enqueue(value);
        } catch (error) {
          failed = true;
          try {
            controller.error(error);
          } catch (_ignored) {
            // The controller was already errored/closed by the consumer.
          }
        }
      },
      cancel(reason) {
        failed = true;
        return reader.cancel(reason);
      },
    });

    return new Response(stream, {
      headers: res.headers,
      status: res.status,
      statusText: res.statusText,
    });
  }

  Object.assign(WebUI, { showLoader, updateLoader, updateLoaderPhase, loaderProgress, hideLoader, nextPaint, fetchWithProgress });
})();
