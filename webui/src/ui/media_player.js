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
      : formatMediaTime(current);
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
    const popup = window.open("", "_blank", "noopener,width=960,height=600,resizable=yes,scrollbars=no");
    if (!popup) return;
    const safeSrc = String(src).replace(/"/g, "&quot;");
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
    const popupButton = type === "video" ? makeMediaButton("popup", "Open in popup window") : null;
    const fullscreenButton = type === "video" ? makeMediaButton("fullscreen", "Fullscreen") : null;

    volumeGroup.append(muteButton, volumeBar);
    buttons.append(playButton, volumeGroup, time, spacer, downloadButton);
    if (popupButton) buttons.appendChild(popupButton);
    if (fullscreenButton) buttons.appendChild(fullscreenButton);
    controls.append(bar, buttons);
    wrap.appendChild(controls);

    const els = { bar, buffer, fill, thumb, range, time, muteButton, volumeRange, volumeFill };
    let dragging = false;

    const seekFromRange = (commit) => {
      const duration = Number(media.duration);
      if (!Number.isFinite(duration) || duration <= 0) return;
      if (commit) media.currentTime = (Number(range.value) / 1000) * duration;
      updateMediaProgress(media, els, !commit);
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

    updateMediaProgress(media, els);
    updateVolumeUi(media, els);
    return wrap;
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

  Object.assign(WebUI, { createMediaPlayer, enhanceMediaPlayers });
})();
