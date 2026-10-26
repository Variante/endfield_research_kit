(() => {
  const WebUI = window.WebUI;

  function storageGet(key) {
    try {
      return localStorage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_error) {
      // Storage is optional; defaults still keep the app usable.
    }
  }

  // A direct link supplies the page state; ordinary visits restore local choices.
  const initialParams = new URLSearchParams(window.location.search);
  const isReload = window.performance?.getEntriesByType?.("navigation")?.[0]?.type === "reload";
  const linkedState = !isReload && [...initialParams.keys()].some((key) => !["ui", "uiLang", "lang"].includes(key));
  const CONTROL_PREFIX = "endfield.control.v1:";
  const restored = new WeakSet();
  const controlSelector = 'input[type="search"][id], input[type="checkbox"][id]:not(#inline-tag-mode), select[id$="-sort"], select#sort';
  function restoreControl(control, notify = false) {
    if (linkedState || restored.has(control) || !control.matches(controlSelector)) return;
    const saved = storageGet(CONTROL_PREFIX + control.id);
    if (saved === null) { restored.add(control); return; }
    if (control.tagName === "SELECT" && ![...control.options].some((option) => option.value === saved)) return;
    restored.add(control);
    const before = control.type === "checkbox" ? control.checked : control.value;
    if (control.type === "checkbox") control.checked = saved === "1";
    else control.value = saved;
    const after = control.type === "checkbox" ? control.checked : control.value;
    if (notify && (notify === "initial" || before !== after)) control.dispatchEvent(new Event(control.tagName === "SELECT" || control.type === "checkbox" ? "change" : "input", { bubbles: true }));
  }
  function saveControl(control) {
    if (control.tagName === "SELECT" && !control.options.length) return;
    storageSet(CONTROL_PREFIX + control.id, control.type === "checkbox" ? (control.checked ? "1" : "0") : control.value);
  }
  function saveControls() {
    document.querySelectorAll(controlSelector).forEach(saveControl);
  }
  Object.assign(WebUI, { storageGet, storageSet, linkedState });
  document.querySelectorAll(controlSelector).forEach((control) => restoreControl(control));
  for (const type of ["input", "change"]) document.addEventListener(type, (event) => {
    if (event.target.matches?.(controlSelector)) saveControl(event.target);
  });
  // Dynamic sidebar controls are restored once their options exist.
  new MutationObserver((records) => {
    const controls = new Set();
    for (const record of records) {
      if (record.target.matches?.(controlSelector)) controls.add(record.target);
      for (const node of record.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches(controlSelector)) controls.add(node);
        node.querySelectorAll(controlSelector).forEach((control) => controls.add(control));
      }
    }
    controls.forEach((control) => restoreControl(control, true));
  }).observe(document.body, { childList: true, subtree: true });
  document.addEventListener("click", (event) => {
    if (event.target.closest('button[id$="reset"],button[id$="reset-filters"]')) queueMicrotask(saveControls);
  });
  document.addEventListener("DOMContentLoaded", () => {
    // Page controllers have now bound their handlers and can receive defaults.
    document.querySelectorAll(controlSelector).forEach((control) => {
      restored.delete(control);
      restoreControl(control, "initial");
    });
  });
  window.addEventListener("pagehide", saveControls);
})();
