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

  Object.assign(WebUI, { storageGet, storageSet });
})();
