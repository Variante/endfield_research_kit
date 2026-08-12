(() => {
  const WebUI = window.WebUI;

  function formatMediaTime(value) {
    const seconds = Number(value);
    if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
    const whole = Math.floor(seconds);
    const minutes = Math.floor(whole / 60);
    const remaining = String(whole % 60).padStart(2, "0");
    return `${minutes}:${remaining}`;
  }

  const MEDIA_ICONS = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 5.5v13a.75.75 0 0 0 1.146.636l11-6.5a.75.75 0 0 0 0-1.272l-11-6.5A.75.75 0 0 0 7 5.5Z"/></svg>',
    pause: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="6.5" y="5" width="3.75" height="14" rx="1"/><rect x="13.75" y="5" width="3.75" height="14" rx="1"/></svg>',
    volume: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 9.5h3.4L12 5.5v13L7.4 14.5H4a.75.75 0 0 1-.75-.75v-3.5A.75.75 0 0 1 4 9.5Z"/><path d="M15.5 8.7a4.5 4.5 0 0 1 0 6.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M17.7 6.3a7.5 7.5 0 0 1 0 11.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    mute: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 9.5h3.4L12 5.5v13L7.4 14.5H4a.75.75 0 0 1-.75-.75v-3.5A.75.75 0 0 1 4 9.5Z"/><path d="M15 9.5l5 5M20 9.5l-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    download: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 4v10m0 0l-4-4m4 4l4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 17.5v1.5a1.5 1.5 0 0 0 1.5 1.5h11A1.5 1.5 0 0 0 19 19v-1.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    popup: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14 4h6v6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M20 4l-8 8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M19 13v6a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    fullscreen: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 9V5a1 1 0 0 1 1-1h4M20 9V5a1 1 0 0 0-1-1h-4M4 15v4a1 1 0 0 0 1 1h4M20 15v4a1 1 0 0 1-1 1h-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    waveform: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 12h2M7 8v8M10 5v14M13 9v6M16 6v12M19 10v4M21 12h0" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    fullscreenExit: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 4v4a1 1 0 0 1-1 1H4M15 4v4a1 1 0 0 0 1 1h4M9 20v-4a1 1 0 0 0-1-1H4M15 20v-4a1 1 0 0 1 1-1h4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function makeMediaButton(iconKey, label) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "media-player-button media-player-icon-button";
    button.innerHTML = MEDIA_ICONS[iconKey] || "";
    button.title = label;
    button.setAttribute("aria-label", label);
    return button;
  }

  function deriveDownloadName(media) {
    const src = String(media.currentSrc || media.src || "");
    if (!src) return "";
    const tail = new URL(src, window.location.href).pathname.split("/").filter(Boolean).pop() || "";
    try {
      return decodeURIComponent(tail);
    } catch (_error) {
      return tail;
    }
  }

  function updateMediaProgress(media, els, dragging = false) {
    const duration = Number(media.duration);
    const current = Number(media.currentTime);
    const hasDuration = Number.isFinite(duration) && duration > 0;
    els.bar.classList.toggle("is-disabled", !hasDuration);
    els.range.disabled = !hasDuration;
    const ratio = hasDuration ? Math.min(1, Math.max(0, current / duration)) : 0;
    const preview = hasDuration && dragging
      ? (Number(els.range.value) / 1000) * duration
      : current;
    const displayRatio = hasDuration && dragging
      ? Math.min(1, Math.max(0, Number(els.range.value) / 1000))
      : ratio;
    els.fill.style.width = `${displayRatio * 100}%`;
    els.thumb.style.left = `${displayRatio * 100}%`;
    if (hasDuration && !dragging) {
      els.range.value = String(Math.round(ratio * 1000));
    }
    let buffered = 0;
    try {
      buffered = hasDuration && media.buffered && media.buffered.length
        ? Math.min(1, Math.max(0, media.buffered.end(media.buffered.length - 1) / duration))
        : 0;
    } catch (_error) {
      buffered = 0;
    }
    els.buffer.style.width = `${buffered * 100}%`;
    els.time.textContent = hasDuration
      ? `${formatMediaTime(preview)} / ${formatMediaTime(duration)}`
      : `${formatMediaTime(current)} / --:--`;
  }

  // Players are created with preload="none" so long lists stay cheap, which leaves
  // the duration unknown until the first play. Pull just the metadata once the
  // player is on screen so the total time shows up without playing anything.
  function probeMediaDuration(media) {
    if (!media || media.dataset.mediaDurationProbe === "1") return;
    if (!(media.currentSrc || media.src)) return;
    const duration = Number(media.duration);
    if (Number.isFinite(duration) && duration > 0) return;
    if (media.readyState >= 1) return;
    if (media.preload !== "none") return; // anything else already fetches metadata on its own
    if (!media.paused || Number(media.currentTime) > 0) return;
    media.dataset.mediaDurationProbe = "1";
    media.preload = "metadata";
    try {
      media.load();
    } catch (_error) {}
  }

  function scheduleDurationProbe(wrap, media) {
    if (typeof IntersectionObserver === "undefined") {
      probeMediaDuration(media);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      probeMediaDuration(media);
    }, { rootMargin: "200px" });
    observer.observe(wrap);
  }

  function updateVolumeUi(media, els) {
    const muted = !!media.muted || media.volume === 0;
    const level = muted ? 0 : Math.min(1, Math.max(0, Number(media.volume) || 0));
    els.volumeRange.value = String(Math.round(level * 1000));
    els.volumeFill.style.width = `${level * 100}%`;
    els.muteButton.innerHTML = MEDIA_ICONS[muted ? "mute" : "volume"];
    els.muteButton.classList.toggle("is-muted", muted);
    const label = muted ? "Unmute" : "Mute";
    els.muteButton.title = label;
    els.muteButton.setAttribute("aria-label", label);
  }

  function openMediaPopup(media) {
    const src = media.currentSrc || media.src;
    if (!src) return;
    const isVideo = media.tagName && media.tagName.toLowerCase() === "video";
    const startTime = Number(media.currentTime) || 0;
    const fileName = deriveDownloadName(media) || (isVideo ? "video" : "audio");
    const popup = window.open("", "_blank", "width=960,height=600,resizable=yes,scrollbars=no");
    if (!popup) return;
    try {
      popup.opener = null;
    } catch (_error) {}
    const safeSrc = WebUI.escapeHtml(String(src));
    const safeName = WebUI.escapeHtml(fileName);
    const tag = isVideo
      ? `<video src="${safeSrc}" controls autoplay playsinline></video>`
      : `<audio src="${safeSrc}" controls autoplay></audio>`;
    popup.document.open();
    popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${safeName}</title>` +
      `<style>html,body{margin:0;padding:0;background:#0b0d12;color:#d7f8df;height:100%;display:flex;` +
      `flex-direction:column;font-family:-apple-system,Segoe UI,system-ui,sans-serif;}` +
      `header{padding:8px 12px;font-size:12px;background:#11151c;border-bottom:1px solid #1f2630;}` +
      `main{flex:1 1 auto;display:flex;align-items:center;justify-content:center;padding:12px;}` +
      `video,audio{width:100%;max-width:100%;max-height:calc(100vh - 80px);background:#000;border-radius:6px;}` +
      `a{color:#9bd3ff;text-decoration:none;}a:hover{text-decoration:underline;}</style></head>` +
      `<body><header><a href="${safeSrc}" download="${safeName}">Download ${safeName}</a></header>` +
      `<main>${tag}</main></body></html>`);
    popup.document.close();
    popup.addEventListener("load", () => {
      const el = popup.document.querySelector(isVideo ? "video" : "audio");
      if (el && startTime > 0) el.currentTime = startTime;
    });
  }

  function triggerMediaDownload(media) {
    const src = media.currentSrc || media.src;
    if (!src) return;
    const name = deriveDownloadName(media);
    const link = document.createElement("a");
    link.href = src;
    if (name) link.download = name;
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function isInFullscreen(element) {
    const fsEl = document.fullscreenElement || document.webkitFullscreenElement;
    return !!fsEl && (fsEl === element || (element && element.contains && element.contains(fsEl)));
  }

  function requestFullscreen(element) {
    const fn = element.requestFullscreen || element.webkitRequestFullscreen;
    if (!fn) return;
    const result = fn.call(element);
    if (result && typeof result.catch === "function") result.catch(() => {});
  }

  function exitFullscreen() {
    const fn = document.exitFullscreen || document.webkitExitFullscreen;
    if (!fn) return;
    const result = fn.call(document);
    if (result && typeof result.catch === "function") result.catch(() => {});
  }

  function createMediaPlayer(media, options = {}) {
    if (!media) return null;
    const type = media.tagName && media.tagName.toLowerCase() === "video" ? "video" : "audio";
    const wrap = document.createElement("div");
    wrap.className = `media-player media-player-${type}`;
    if (options.className) wrap.classList.add(options.className);

    media.controls = false;
    media.classList.add("media-player-element");
    media.dataset.mediaPlayer = "1";
    if (type === "video") media.setAttribute("playsinline", "");

    const stage = document.createElement("div");
    stage.className = "media-player-stage";
    stage.appendChild(media);
    wrap.appendChild(stage);

    const controls = document.createElement("div");
    controls.className = "media-player-controls";

    const bar = document.createElement("div");
    bar.className = "media-player-bar";
    const track = document.createElement("div");
    track.className = "media-player-track";
    const waveformCanvas = type === "audio" ? document.createElement("canvas") : null;
    if (waveformCanvas) {
      waveformCanvas.className = "media-player-waveform";
      track.appendChild(waveformCanvas);
    }
    const buffer = document.createElement("div");
    buffer.className = "media-player-buffer";
    const fill = document.createElement("div");
    fill.className = "media-player-fill";
    const thumb = document.createElement("div");
    thumb.className = "media-player-thumb";
    track.append(buffer, fill, thumb);

    const range = document.createElement("input");
    range.className = "media-player-range";
    range.type = "range";
    range.min = "0";
    range.max = "1000";
    range.step = "1";
    range.value = "0";
    range.disabled = true;
    range.setAttribute("aria-label", "Seek");
    bar.append(track, range);

    const buttons = document.createElement("div");
    buttons.className = "media-player-buttons";
    const playButton = makeMediaButton("play", "Play");
    playButton.classList.add("media-player-play");

    const volumeGroup = document.createElement("div");
    volumeGroup.className = "media-player-volume-group";
    const muteButton = makeMediaButton("volume", "Mute");
    const volumeBar = document.createElement("div");
    volumeBar.className = "media-player-volume";
    const volumeTrack = document.createElement("div");
    volumeTrack.className = "media-player-volume-track";
    const volumeFill = document.createElement("div");
    volumeFill.className = "media-player-volume-fill";
    volumeTrack.appendChild(volumeFill);
    const volumeRange = document.createElement("input");
    volumeRange.className = "media-player-volume-range";
    volumeRange.type = "range";
    volumeRange.min = "0";
    volumeRange.max = "1000";
    volumeRange.step = "1";
    volumeRange.value = "1000";
    volumeRange.setAttribute("aria-label", "Volume");
    volumeBar.append(volumeTrack, volumeRange);

    const time = document.createElement("span");
    time.className = "media-player-time";
    time.textContent = "0:00";
    const spacer = document.createElement("div");
    spacer.className = "media-player-spacer";
    const downloadButton = makeMediaButton("download", "Download");
    const waveformButton = type === "audio" ? makeMediaButton("waveform", "Show waveform") : null;
    const popupButton = type === "video" ? makeMediaButton("popup", "Open in popup window") : null;
    const fullscreenButton = type === "video" ? makeMediaButton("fullscreen", "Fullscreen") : null;

    volumeGroup.append(muteButton, volumeBar);
    buttons.append(playButton, volumeGroup, time, spacer);
    if (waveformButton) buttons.appendChild(waveformButton);
    buttons.appendChild(downloadButton);
    if (popupButton) buttons.appendChild(popupButton);
    if (fullscreenButton) buttons.appendChild(fullscreenButton);
    controls.append(bar, buttons);
    wrap.appendChild(controls);

    const els = { bar, buffer, fill, thumb, range, time, muteButton, volumeRange, volumeFill };
    let dragging = false;

    const waveformState = { peaks: null, promise: null };

    function drawWaveform(progressOverride) {
      if (!waveformCanvas || !waveformState.peaks) return;
      const dpr = window.devicePixelRatio || 1;
      const cssW = waveformCanvas.clientWidth;
      const cssH = waveformCanvas.clientHeight;
      if (!cssW || !cssH) return;
      const pxW = Math.max(1, Math.round(cssW * dpr));
      const pxH = Math.max(1, Math.round(cssH * dpr));
      if (waveformCanvas.width !== pxW) waveformCanvas.width = pxW;
      if (waveformCanvas.height !== pxH) waveformCanvas.height = pxH;
      const ctx = waveformCanvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, pxW, pxH);
      const peaks = waveformState.peaks;
      const bars = peaks.length;
      const duration = Number(media.duration);
      const current = Number(media.currentTime);
      const fallback = Number.isFinite(duration) && duration > 0
        ? Math.min(1, Math.max(0, current / duration))
        : 0;
      const progress = progressOverride != null
        ? Math.min(1, Math.max(0, progressOverride))
        : fallback;
      const playedBars = progress * bars;
      const slot = pxW / bars;
      const gap = Math.max(1, Math.floor(dpr));
      const barW = Math.max(1, Math.floor(slot) - gap);
      const mid = pxH / 2;
      const minH = Math.max(1, Math.floor(dpr));
      const maxH = pxH - minH * 2;
      const styles = window.getComputedStyle(waveformCanvas);
      const fgRgb = (styles.getPropertyValue("--fg-rgb").trim() || "48, 56, 65");
      const accentRgb = (styles.getPropertyValue("--accent-rgb").trim() || "255, 87, 34");
      const playedColor = `rgba(${accentRgb}, 0.95)`;
      const baseColor = `rgba(${fgRgb}, 0.38)`;
      for (let i = 0; i < bars; i++) {
        const peak = peaks[i] || 0;
        const h = Math.max(minH, peak * maxH);
        const x = Math.floor(i * slot);
        ctx.fillStyle = i < playedBars ? playedColor : baseColor;
        ctx.fillRect(x, mid - h / 2, barW, h);
      }
    }

    async function loadWaveformPeaks(targetBars) {
      const src = media.currentSrc || media.src;
      if (!src) throw new Error("audio element has no source");
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) throw new Error("WebAudio API is unavailable");
      const audioCtx = createMediaPlayer._audioCtx || (createMediaPlayer._audioCtx = new Ctx());
      const response = await fetch(src);
      if (!response.ok) throw new Error(`fetch failed: ${response.status}`);
      const bytes = await response.arrayBuffer();
      const decoded = await new Promise((resolve, reject) => {
        const result = audioCtx.decodeAudioData(bytes.slice(0), resolve, reject);
        if (result && typeof result.then === "function") result.then(resolve, reject);
      });
      const channels = decoded.numberOfChannels;
      const length = decoded.length;
      const bars = Math.max(32, Math.min(targetBars || 600, length || 32));
      const samplesPerBar = Math.max(1, Math.floor(length / bars));
      const peaks = new Float32Array(bars);
      for (let ch = 0; ch < channels; ch++) {
        const data = decoded.getChannelData(ch);
        for (let b = 0; b < bars; b++) {
          const start = b * samplesPerBar;
          const end = Math.min(length, start + samplesPerBar);
          let peak = 0;
          for (let i = start; i < end; i++) {
            const v = data[i] < 0 ? -data[i] : data[i];
            if (v > peak) peak = v;
          }
          if (peak > peaks[b]) peaks[b] = peak;
        }
      }
      let max = 0;
      for (let i = 0; i < peaks.length; i++) if (peaks[i] > max) max = peaks[i];
      if (max > 0) {
        for (let i = 0; i < peaks.length; i++) peaks[i] = peaks[i] / max;
      }
      return peaks;
    }

    function renderWaveform(opts = {}) {
      if (!waveformCanvas) return Promise.resolve(null);
      if (waveformState.promise) return waveformState.promise;
      wrap.classList.add("is-waveform-loading");
      const targetBars = opts.bars
        || Math.max(120, Math.floor((waveformCanvas.clientWidth || bar.clientWidth || 600) / 3));
      if (wrap._syncWaveformButton) wrap._syncWaveformButton();
      const promise = loadWaveformPeaks(targetBars).then((peaks) => {
        waveformState.peaks = peaks;
        wrap.classList.add("has-waveform");
        drawWaveform();
        return peaks;
      }).catch((err) => {
        waveformState.promise = null;
        wrap.classList.remove("is-waveform-loading");
        if (wrap._syncWaveformButton) wrap._syncWaveformButton();
        throw err;
      }).then((peaks) => {
        wrap.classList.remove("is-waveform-loading");
        if (wrap._syncWaveformButton) wrap._syncWaveformButton();
        return peaks;
      });
      waveformState.promise = promise;
      return promise;
    }

    function clearWaveform() {
      waveformState.peaks = null;
      waveformState.promise = null;
      wrap.classList.remove("has-waveform", "is-waveform-loading");
      if (waveformCanvas) {
        const ctx = waveformCanvas.getContext("2d");
        if (ctx) ctx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
      }
      if (wrap._syncWaveformButton) wrap._syncWaveformButton();
    }

    const seekFromRange = (commit) => {
      const duration = Number(media.duration);
      if (!Number.isFinite(duration) || duration <= 0) return;
      if (commit) media.currentTime = (Number(range.value) / 1000) * duration;
      updateMediaProgress(media, els, !commit);
      if (waveformState.peaks) {
        drawWaveform(commit ? null : Number(range.value) / 1000);
      }
    };
    const togglePlay = () => {
      if (media.paused) media.play().catch(() => {});
      else media.pause();
    };

    playButton.addEventListener("click", togglePlay);
    if (type === "video") media.addEventListener("click", togglePlay);
    range.addEventListener("pointerdown", () => { dragging = true; });
    range.addEventListener("input", () => seekFromRange(false));
    range.addEventListener("change", () => seekFromRange(true));
    range.addEventListener("pointerup", () => {
      dragging = false;
      seekFromRange(true);
    });
    range.addEventListener("pointercancel", () => {
      dragging = false;
      updateMediaProgress(media, els);
    });

    const applyVolume = () => {
      const value = Number(volumeRange.value) / 1000;
      media.volume = Math.min(1, Math.max(0, value));
      if (value > 0) media.muted = false;
      updateVolumeUi(media, els);
    };
    volumeRange.addEventListener("input", applyVolume);
    volumeRange.addEventListener("change", applyVolume);
    muteButton.addEventListener("click", () => {
      if (media.muted || media.volume === 0) {
        media.muted = false;
        if (media.volume === 0) media.volume = 1;
      } else {
        media.muted = true;
      }
      updateVolumeUi(media, els);
    });

    downloadButton.addEventListener("click", () => triggerMediaDownload(media));
    if (popupButton) popupButton.addEventListener("click", () => openMediaPopup(media));
    if (fullscreenButton) {
      const sync = () => {
        const active = isInFullscreen(wrap);
        wrap.classList.toggle("is-fullscreen", active);
        fullscreenButton.innerHTML = MEDIA_ICONS[active ? "fullscreenExit" : "fullscreen"];
        const label = active ? "Exit fullscreen" : "Fullscreen";
        fullscreenButton.title = label;
        fullscreenButton.setAttribute("aria-label", label);
      };
      fullscreenButton.addEventListener("click", () => {
        if (isInFullscreen(wrap)) exitFullscreen();
        else requestFullscreen(wrap);
      });
      document.addEventListener("fullscreenchange", sync);
      document.addEventListener("webkitfullscreenchange", sync);
    }

    media.addEventListener("loadedmetadata", () => updateMediaProgress(media, els));
    media.addEventListener("durationchange", () => updateMediaProgress(media, els));
    media.addEventListener("timeupdate", () => updateMediaProgress(media, els, dragging));
    media.addEventListener("progress", () => updateMediaProgress(media, els, dragging));
    media.addEventListener("volumechange", () => updateVolumeUi(media, els));
    media.addEventListener("play", () => {
      playButton.innerHTML = MEDIA_ICONS.pause;
      playButton.title = "Pause";
      playButton.setAttribute("aria-label", "Pause");
      wrap.classList.add("is-playing");
    });
    media.addEventListener("pause", () => {
      playButton.innerHTML = MEDIA_ICONS.play;
      playButton.title = "Play";
      playButton.setAttribute("aria-label", "Play");
      wrap.classList.remove("is-playing");
    });
    media.addEventListener("ended", () => {
      playButton.innerHTML = MEDIA_ICONS.play;
      playButton.title = "Play";
      playButton.setAttribute("aria-label", "Play");
      wrap.classList.remove("is-playing");
      updateMediaProgress(media, els);
    });

    if (waveformButton) {
      const syncWaveformButton = () => {
        const active = wrap.classList.contains("has-waveform");
        const loading = wrap.classList.contains("is-waveform-loading");
        waveformButton.classList.toggle("is-active", active);
        waveformButton.classList.toggle("is-loading", loading);
        waveformButton.disabled = loading;
        const label = loading ? "Loading waveform…" : active ? "Hide waveform" : "Show waveform";
        waveformButton.title = label;
        waveformButton.setAttribute("aria-label", label);
        waveformButton.setAttribute("aria-pressed", active ? "true" : "false");
      };
      waveformButton.addEventListener("click", () => {
        if (wrap.classList.contains("is-waveform-loading")) return;
        if (waveformState.peaks) {
          clearWaveform();
          syncWaveformButton();
          return;
        }
        syncWaveformButton();
        renderWaveform().then(syncWaveformButton, (err) => {
          syncWaveformButton();
          console.warn("waveform render failed", err);
        });
        syncWaveformButton();
      });
      wrap._syncWaveformButton = syncWaveformButton;
      syncWaveformButton();
    }

    if (waveformCanvas) {
      const redraw = () => { if (waveformState.peaks && !dragging) drawWaveform(); };
      media.addEventListener("timeupdate", redraw);
      media.addEventListener("seeked", redraw);
      media.addEventListener("durationchange", redraw);
      if (typeof ResizeObserver !== "undefined") {
        const ro = new ResizeObserver(() => { if (waveformState.peaks) drawWaveform(); });
        ro.observe(waveformCanvas);
      } else {
        window.addEventListener("resize", () => { if (waveformState.peaks) drawWaveform(); });
      }
      wrap.renderWaveform = renderWaveform;
      wrap.clearWaveform = clearWaveform;
      if (options.waveform) {
        const opts = typeof options.waveform === "object" ? options.waveform : {};
        const trigger = () => renderWaveform(opts).catch(() => {});
        if (media.readyState >= 1 || (media.currentSrc || media.src)) trigger();
        else media.addEventListener("loadedmetadata", trigger, { once: true });
      }
    }

    updateMediaProgress(media, els);
    updateVolumeUi(media, els);
    if (options.probeDuration !== false) scheduleDurationProbe(wrap, media);
    return wrap;
  }

  function renderAudioWaveform(target, opts = {}) {
    if (!target) return Promise.reject(new Error("no target"));
    if (typeof target.renderWaveform === "function") return target.renderWaveform(opts);
    const wrap = target.closest && target.closest(".media-player-audio");
    if (wrap && typeof wrap.renderWaveform === "function") return wrap.renderWaveform(opts);
    return Promise.reject(new Error("target is not an enhanced audio player"));
  }

  function enhanceMediaPlayers(root = document) {
    root.querySelectorAll("audio:not([data-media-player]), video:not([data-media-player])").forEach((media) => {
      const parent = media.parentNode;
      const next = media.nextSibling;
      const player = createMediaPlayer(media);
      if (!player || !parent) return;
      parent.insertBefore(player, next);
    });
  }

  function mediaSource(media) {
    return String(media?.currentSrc || media?.src || media?.querySelector?.("source")?.src || "");
  }

  function mediaFileName(media) {
    const src = mediaSource(media);
    if (!src) return "Untitled media";
    const tail = new URL(src, window.location.href).pathname.split("/").filter(Boolean).pop() || src;
    try {
      return decodeURIComponent(tail);
    } catch (_error) {
      return tail;
    }
  }

  function activePageMedia() {
    const page = document.querySelector(".page-view.is-active:not([hidden])")
      || Array.from(document.querySelectorAll(".page-view[data-view]")).find(
        (candidate) => candidate.dataset.view === document.body.dataset.activeView && !candidate.hidden
      );
    if (!page) return [];
    return Array.from(page.querySelectorAll("audio, video")).filter((media) => {
      if (!mediaSource(media) || media.hidden || media.closest("[hidden]")) return false;
      return media.getAttribute("aria-hidden") !== "true";
    });
  }

  function exactDurationAudioDefaults(mediaItems) {
    const durationGroups = new Map();
    mediaItems.forEach((media) => {
      if (media.tagName.toLowerCase() !== "audio") return;
      const duration = Number(media.duration);
      if (!Number.isFinite(duration) || duration <= 0) return;
      if (!durationGroups.has(duration)) durationGroups.set(duration, []);
      durationGroups.get(duration).push(media);
    });
    return new Set(Array.from(durationGroups.values()).filter((group) => group.length > 1).flat());
  }

  const MULTI_MEDIA_TEXT = {
    en: {
      trigger: "Play together",
      panelLabel: "Play multiple media files",
      heading: "Play files together",
      close: "Close",
      audio: "audio",
      video: "video",
      durationLoading: "duration loading",
      selected: (selected, total) => `${selected} of ${total} selected`,
      stopped: "Playback stopped.",
      playing: (count) => `${count} files playing together.`,
      failed: (playing, failed) => `${playing} playing; ${failed} could not start.`,
      sequencePlaying: (current, total) => `Playing ${current} of ${total} in sequence.`,
      sequenceFinished: "Sequential playback finished.",
      sequenceFailed: (failed) => `Sequence finished; ${failed} files could not start.`,
      selectAllAudio: "Select all audio",
      unselectAllAudio: "Unselect all audio",
      stop: "Stop all",
      sequence: "Play in sequence",
      play: "Play selected",
    },
    zh: {
      trigger: "\u540c\u65f6\u64ad\u653e",
      panelLabel: "\u540c\u65f6\u64ad\u653e\u591a\u4e2a\u5a92\u4f53\u6587\u4ef6",
      heading: "\u540c\u65f6\u64ad\u653e\u6587\u4ef6",
      close: "\u5173\u95ed",
      audio: "\u97f3\u9891",
      video: "\u89c6\u9891",
      durationLoading: "\u6b63\u5728\u8bfb\u53d6\u65f6\u957f",
      selected: (selected, total) => `\u5df2\u9009\u62e9 ${selected} / ${total}`,
      stopped: "\u5df2\u505c\u6b62\u5168\u90e8\u64ad\u653e\u3002",
      playing: (count) => `${count} \u4e2a\u6587\u4ef6\u6b63\u5728\u540c\u65f6\u64ad\u653e\u3002`,
      failed: (playing, failed) => `${playing} \u4e2a\u6b63\u5728\u64ad\u653e\uff1b${failed} \u4e2a\u65e0\u6cd5\u542f\u52a8\u3002`,
      sequencePlaying: (current, total) => `\u6b63\u5728\u4f9d\u6b21\u64ad\u653e ${current} / ${total}\u3002`,
      sequenceFinished: "\u4f9d\u6b21\u64ad\u653e\u5df2\u5b8c\u6210\u3002",
      sequenceFailed: (failed) => `\u4f9d\u6b21\u64ad\u653e\u5df2\u5b8c\u6210\uff1b${failed} \u4e2a\u6587\u4ef6\u65e0\u6cd5\u542f\u52a8\u3002`,
      selectAllAudio: "\u9009\u62e9\u5168\u90e8\u97f3\u9891",
      unselectAllAudio: "\u53d6\u6d88\u9009\u62e9\u5168\u90e8\u97f3\u9891",
      stop: "\u505c\u6b62\u5168\u90e8",
      sequence: "\u4f9d\u6b21\u64ad\u653e",
      play: "\u64ad\u653e\u6240\u9009",
    },
  };

  function multiMediaStrings() {
    const locale = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "en").toLowerCase();
    return locale.startsWith("zh") ? MULTI_MEDIA_TEXT.zh : MULTI_MEDIA_TEXT.en;
  }

  function installMultiMediaControl() {
    if (document.querySelector("[data-multi-media-control]")) return;

    const control = document.createElement("div");
    control.className = "multi-media-control";
    control.dataset.multiMediaControl = "1";
    control.hidden = true;
    control.innerHTML = `
      <button class="multi-media-trigger" type="button" aria-expanded="false" aria-controls="multi-media-panel">
        <span class="multi-media-trigger-label"></span> <span class="multi-media-count"></span>
      </button>
      <section id="multi-media-panel" class="multi-media-panel" hidden>
        <header>
          <strong class="multi-media-heading"></strong>
          <button class="multi-media-close" type="button">&times;</button>
        </header>
        <div class="multi-media-selection-actions">
          <button class="multi-media-audio-toggle" type="button"></button>
        </div>
        <div class="multi-media-list"></div>
        <footer>
          <span class="multi-media-status" aria-live="polite"></span>
          <button class="multi-media-stop" type="button"></button>
          <button class="multi-media-sequence" type="button"></button>
          <button class="multi-media-play" type="button"></button>
        </footer>
      </section>`;
    document.body.appendChild(control);

    const trigger = control.querySelector(".multi-media-trigger");
    const triggerLabel = control.querySelector(".multi-media-trigger-label");
    const count = control.querySelector(".multi-media-count");
    const panel = control.querySelector(".multi-media-panel");
    const heading = control.querySelector(".multi-media-heading");
    const audioToggleButton = control.querySelector(".multi-media-audio-toggle");
    const list = control.querySelector(".multi-media-list");
    const status = control.querySelector(".multi-media-status");
    const playButton = control.querySelector(".multi-media-play");
    const sequenceButton = control.querySelector(".multi-media-sequence");
    const stopButton = control.querySelector(".multi-media-stop");
    const closeButton = control.querySelector(".multi-media-close");
    let candidates = [];
    let selected = new Set();
    let playing = new Set();
    let selectionTouched = false;
    let candidateSignature = "";
    let refreshFrame = 0;
    let sequenceRunId = 0;
    let statusState = { kind: "selection", selected: 0, total: 0 };

    function renderStatus() {
      const strings = multiMediaStrings();
      if (statusState.kind === "stopped") status.textContent = strings.stopped;
      else if (statusState.kind === "playing") status.textContent = strings.playing(statusState.count);
      else if (statusState.kind === "failed") status.textContent = strings.failed(statusState.playing, statusState.failed);
      else if (statusState.kind === "sequencePlaying") status.textContent = strings.sequencePlaying(statusState.current, statusState.total);
      else if (statusState.kind === "sequenceFinished") status.textContent = strings.sequenceFinished;
      else if (statusState.kind === "sequenceFailed") status.textContent = strings.sequenceFailed(statusState.failed);
      else status.textContent = strings.selected(statusState.selected, statusState.total);
    }

    function applyLocalization() {
      const strings = multiMediaStrings();
      triggerLabel.textContent = strings.trigger;
      panel.setAttribute("aria-label", strings.panelLabel);
      heading.textContent = strings.heading;
      closeButton.setAttribute("aria-label", strings.close);
      closeButton.title = strings.close;
      stopButton.textContent = strings.stop;
      sequenceButton.textContent = strings.sequence;
      playButton.textContent = strings.play;
      renderList(true);
      renderStatus();
    }

    function stopPlaying() {
      sequenceRunId += 1;
      playing.forEach((media) => media.pause());
      playing.clear();
      statusState = { kind: "stopped" };
      renderStatus();
    }

    function closePanel() {
      panel.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
      trigger.focus({ preventScroll: true });
    }

    function renderList(preserveStatus = false) {
      if (panel.hidden) return;
      const strings = multiMediaStrings();
      if (!selectionTouched) selected = exactDurationAudioDefaults(candidates);
      list.replaceChildren();
      candidates.forEach((media, index) => {
        const row = document.createElement("label");
        row.className = "multi-media-option";
        row.title = mediaSource(media);
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selected.has(media);
        checkbox.addEventListener("change", () => {
          selectionTouched = true;
          if (checkbox.checked) selected.add(media);
          else selected.delete(media);
          syncSelectionStatus();
        });
        const description = document.createElement("span");
        const type = media.tagName.toLowerCase() === "video" ? strings.video : strings.audio;
        const duration = Number(media.duration);
        const durationText = Number.isFinite(duration) && duration > 0
          ? formatMediaTime(duration) + ` (${duration.toFixed(3)}s)`
          : strings.durationLoading;
        description.innerHTML = `<b>${WebUI.escapeHtml(mediaFileName(media))}</b><small>${type} ${index + 1} · ${durationText}</small>`;
        row.append(checkbox, description);
        list.appendChild(row);
      });
      if (preserveStatus) renderStatus();
      else syncSelectionStatus();
      updateAudioToggle();
    }

    function updateAudioToggle() {
      const strings = multiMediaStrings();
      const audioItems = candidates.filter((media) => media.tagName.toLowerCase() === "audio");
      const allSelected = audioItems.length > 0 && audioItems.every((media) => selected.has(media));
      audioToggleButton.disabled = audioItems.length === 0;
      audioToggleButton.textContent = allSelected ? strings.unselectAllAudio : strings.selectAllAudio;
      audioToggleButton.setAttribute("aria-pressed", allSelected ? "true" : "false");
    }

    function syncSelectionStatus() {
      const selectedCount = candidates.filter((media) => selected.has(media)).length;
      statusState = { kind: "selection", selected: selectedCount, total: candidates.length };
      renderStatus();
      playButton.disabled = selectedCount < 2;
      sequenceButton.disabled = selectedCount < 2;
      updateAudioToggle();
    }

    function probeCandidateDurations() {
      candidates.forEach((media) => {
        const duration = Number(media.duration);
        if (Number.isFinite(duration) && duration > 0) return;
        media.addEventListener("loadedmetadata", renderList, { once: true });
        if (media.preload === "none") media.preload = "metadata";
        try {
          if (media.readyState < 1) media.load();
        } catch (_error) {}
      });
    }

    function refresh() {
      refreshFrame = 0;
      const next = activePageMedia();
      const nextSignature = next.map((media) => mediaSource(media)).join("\n");
      const changed = nextSignature !== candidateSignature
        || next.length !== candidates.length
        || next.some((media, index) => media !== candidates[index]);
      candidates = next;
      control.hidden = candidates.length < 2;
      count.textContent = candidates.length ? `(${candidates.length})` : "";
      if (changed) {
        sequenceRunId += 1;
        candidateSignature = nextSignature;
        selectionTouched = false;
        selected = new Set();
        Array.from(playing).forEach((media) => {
          if (!candidates.includes(media)) {
            media.pause();
            playing.delete(media);
          }
        });
      }
      if (control.hidden && !panel.hidden) closePanel();
      renderList();
      if (!panel.hidden && changed) probeCandidateDurations();
    }

    function scheduleRefresh() {
      if (refreshFrame) return;
      refreshFrame = window.requestAnimationFrame(refresh);
    }

    trigger.addEventListener("click", () => {
      const opening = panel.hidden;
      panel.hidden = !opening;
      trigger.setAttribute("aria-expanded", opening ? "true" : "false");
      if (!opening) return;
      renderList();
      probeCandidateDurations();
      const first = list.querySelector("input");
      if (first) first.focus({ preventScroll: true });
    });
    closeButton.addEventListener("click", closePanel);
    audioToggleButton.addEventListener("click", () => {
      const audioItems = candidates.filter((media) => media.tagName.toLowerCase() === "audio");
      if (!audioItems.length) return;
      selectionTouched = true;
      const allSelected = audioItems.every((media) => selected.has(media));
      audioItems.forEach((media) => {
        if (allSelected) selected.delete(media);
        else selected.add(media);
      });
      renderList();
    });
    stopButton.addEventListener("click", stopPlaying);
    sequenceButton.addEventListener("click", () => {
      const chosen = candidates.filter((media) => selected.has(media));
      if (chosen.length < 2) return;
      const runId = ++sequenceRunId;
      playing.forEach((media) => media.pause());
      playing = new Set(chosen);
      chosen.forEach((media) => {
        media.pause();
        try { media.currentTime = 0; } catch (_error) {}
      });
      let failures = 0;
      const playNext = (index) => {
        if (runId !== sequenceRunId) return;
        if (index >= chosen.length) {
          playing.clear();
          statusState = failures
            ? { kind: "sequenceFailed", failed: failures }
            : { kind: "sequenceFinished" };
          renderStatus();
          return;
        }
        const media = chosen[index];
        statusState = { kind: "sequencePlaying", current: index + 1, total: chosen.length };
        renderStatus();
        const advance = () => {
          if (runId === sequenceRunId) playNext(index + 1);
        };
        media.addEventListener("ended", advance, { once: true });
        const result = media.play();
        if (result && typeof result.catch === "function") {
          result.catch(() => {
            media.removeEventListener("ended", advance);
            failures += 1;
            advance();
          });
        }
      };
      playNext(0);
    });
    playButton.addEventListener("click", () => {
      const chosen = candidates.filter((media) => selected.has(media));
      if (chosen.length < 2) return;
      sequenceRunId += 1;
      playing.forEach((media) => media.pause());
      playing = new Set(chosen);
      chosen.forEach((media) => {
        media.pause();
        try { media.currentTime = 0; } catch (_error) {}
      });
      Promise.allSettled(chosen.map((media) => media.play())).then((results) => {
        const failed = results.filter((result) => result.status === "rejected").length;
        statusState = failed
          ? { kind: "failed", playing: chosen.length - failed, failed }
          : { kind: "playing", count: chosen.length };
        renderStatus();
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !panel.hidden) closePanel();
    });

    const observer = new MutationObserver((mutations) => {
      const relevant = mutations.some((mutation) => {
        if (control.contains(mutation.target)) return false;
        if (mutation.target.closest?.(".media-player")) return false;
        if (mutation.type === "childList") return true;
        if (mutation.attributeName === "src" || mutation.attributeName === "hidden") return true;
        if (mutation.attributeName === "data-active-view") return true;
        return mutation.attributeName === "class" && mutation.target.matches?.(".page-view");
      });
      if (relevant) scheduleRefresh();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class", "hidden", "src", "data-active-view"],
    });
    window.addEventListener("webui:ui-locale-changed", applyLocalization);
    applyLocalization();
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installMultiMediaControl, { once: true });
  } else {
    installMultiMediaControl();
  }

  Object.assign(WebUI, { createMediaPlayer, enhanceMediaPlayers, renderAudioWaveform, installMultiMediaControl });
})();
