// Shared draggable splitter helper used by every view (pane dividers + filter dividers).
// One generic controller handles both axes; callers supply axis-specific callbacks.
//
// Smoothness notes (the previous per-view implementations were janky):
//   * Bounds are measured once at drag start and reused for the whole drag, instead
//     of running getComputedStyle()/natural-height reflows on every pointermove.
//   * Pointer moves are coalesced into a single style write per animation frame.
//   * The global "resize" event (which forces every other splitter + virtualized list
//     to reconcile) is NOT dispatched during a drag -- it fires once on release.
(() => {
  const { $, storageGet, storageSet } = window.WebUI;
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";

  function isMobileLayout() {
    return !!(window.matchMedia && window.matchMedia(MOBILE_LAYOUT_QUERY).matches);
  }

  function parseCssPixels(value, fallback = 0) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function clampNumber(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function readStoredNumber(key) {
    if (!key) return null;
    const raw = storageGet(key);
    const parsed = Number.parseFloat(raw || "");
    return Number.isFinite(parsed) ? parsed : null;
  }

  function resolveEl(ref) {
    return typeof ref === "string" ? $(ref) : ref;
  }

  // opts:
  //   handle        element or selector for the drag handle (required)
  //   storageKey    localStorage key for the persisted size (optional)
  //   bodyDragClass class toggled on <body> while dragging
  //   client(event) -> clientX | clientY for the active axis
  //   keys          { decrease: [...keys], increase: [...keys] } for keyboard resize
  //   enabled()     -> whether dragging/resizing is currently allowed
  //   bounds()      -> { min, max } pixel range (may do layout reads; called once per drag)
  //   read()        -> current size in px
  //   write(px)     -> apply the size (pure style write; no clamp/aria/persist)
  //   clear()       -> remove the inline size (disabled/mobile/hidden state)
  //   sync(ctrl)    -> reconcile size on init + window resize, using the returned ctrl
  function setupSplitter(opts) {
    const handle = resolveEl(opts.handle);
    if (!handle) return null;

    const storageKey = opts.storageKey || "";
    const bodyDragClass = opts.bodyDragClass || "";
    const client = opts.client;
    const keys = opts.keys || {};
    const enabled = opts.enabled || (() => true);
    const measureBounds = opts.bounds;
    const read = opts.read;
    const write = opts.write;
    const clearSize = opts.clear || (() => {});
    const syncFn = opts.sync || (() => {});
    const round = Math.round;

    let activePointerId = null;
    let startClient = 0;
    let startSize = 0;
    let latestClient = 0;
    let moveFrame = 0;
    let dragBounds = null;
    let resizeQueued = false;
    let syncQueued = false;

    const scheduleResize = () => {
      if (resizeQueued) return;
      resizeQueued = true;
      requestAnimationFrame(() => {
        resizeQueued = false;
        window.dispatchEvent(new Event("resize"));
      });
    };

    const setAria = (min, max, value) => {
      handle.setAttribute("aria-valuemin", String(round(min)));
      handle.setAttribute("aria-valuemax", String(round(max)));
      handle.setAttribute("aria-valuenow", String(round(value)));
    };

    const clearAria = () => {
      handle.removeAttribute("aria-valuemin");
      handle.removeAttribute("aria-valuemax");
      handle.removeAttribute("aria-valuenow");
    };

    const ctrl = {};

    // During a drag the bounds are cached at pointerdown so we never reflow per frame.
    const activeBounds = () => (activePointerId !== null && dragBounds ? dragBounds : measureBounds());

    ctrl.set = (px, { persist = true, commit = true } = {}) => {
      if (!enabled()) {
        clearSize();
        clearAria();
        if (commit) scheduleResize();
        return;
      }
      const bounds = activeBounds();
      const value = clampNumber(px, bounds.min, bounds.max);
      write(value);
      setAria(bounds.min, bounds.max, value);
      if (persist && storageKey) storageSet(storageKey, String(round(value)));
      if (commit) scheduleResize();
    };

    ctrl.clear = ({ commit = true } = {}) => {
      clearSize();
      clearAria();
      if (commit) scheduleResize();
    };

    ctrl.syncAria = () => {
      if (!enabled()) {
        clearAria();
        return;
      }
      const bounds = measureBounds();
      const value = clampNumber(read(), bounds.min, bounds.max);
      setAria(bounds.min, bounds.max, value);
    };

    ctrl.sync = () => syncFn(ctrl);
    ctrl.requestSync = () => {
      if (syncQueued) return;
      syncQueued = true;
      requestAnimationFrame(() => {
        syncQueued = false;
        ctrl.sync();
      });
    };

    const flushMove = () => {
      moveFrame = 0;
      if (activePointerId === null) return;
      // commit:false -> do not dispatch a global resize per frame (that is the jank source).
      ctrl.set(startSize + (latestClient - startClient), { persist: false, commit: false });
    };

    const onPointerMove = (event) => {
      if (event.pointerId !== activePointerId) return;
      latestClient = client(event);
      if (moveFrame) return;
      moveFrame = requestAnimationFrame(flushMove);
    };

    const stopDragging = () => {
      if (activePointerId === null) return;
      const pointerId = activePointerId;
      activePointerId = null;
      dragBounds = null;
      if (moveFrame) {
        cancelAnimationFrame(moveFrame);
        moveFrame = 0;
      }
      handle.classList.remove("is-dragging");
      if (bodyDragClass) document.body.classList.remove(bodyDragClass);
      try {
        handle.releasePointerCapture(pointerId);
      } catch (_error) {
        // Ignore capture cleanup failures.
      }
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      if (storageKey && enabled()) storageSet(storageKey, String(round(read())));
      // One reconcile after the drag settles, so lists/aria catch up exactly once.
      scheduleResize();
    };

    const onPointerUp = (event) => {
      if (activePointerId !== null && event.pointerId !== activePointerId) return;
      stopDragging();
    };

    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || !enabled()) return;
      event.preventDefault();
      activePointerId = event.pointerId;
      startClient = client(event);
      latestClient = startClient;
      startSize = read();
      dragBounds = measureBounds();
      handle.classList.add("is-dragging");
      if (bodyDragClass) document.body.classList.add(bodyDragClass);
      handle.setPointerCapture?.(event.pointerId);
      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
      window.addEventListener("pointercancel", onPointerUp);
    });

    handle.addEventListener("keydown", (event) => {
      if (!enabled()) return;
      const bounds = measureBounds();
      const current = clampNumber(read(), bounds.min, bounds.max);
      const step = event.shiftKey ? 48 : 16;
      if ((keys.decrease || []).includes(event.key)) {
        event.preventDefault();
        ctrl.set(current - step);
      } else if ((keys.increase || []).includes(event.key)) {
        event.preventDefault();
        ctrl.set(current + step);
      } else if (event.key === "Home") {
        event.preventDefault();
        ctrl.set(bounds.min);
      } else if (event.key === "End") {
        event.preventDefault();
        ctrl.set(bounds.max);
      }
    });

    window.addEventListener("resize", ctrl.requestSync);
    ctrl.sync();
    return ctrl;
  }

  window.WebUI.setupSplitter = setupSplitter;
  window.WebUI.splitterUtils = { isMobileLayout, parseCssPixels, clampNumber, readStoredNumber };
})();
