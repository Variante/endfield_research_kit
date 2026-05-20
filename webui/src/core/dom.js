(() => {
  const WebUI = window.WebUI;

  function $(sel, root = document) {
    return root.querySelector(sel);
  }

  function $$(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function rebuildSelect(select, values, labeler) {
    if (!select) return;
    const current = select.value;
    const all = select.querySelector("option[value='']");
    select.replaceChildren();
    if (all) select.appendChild(all);
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labeler ? labeler(value) : value;
      select.appendChild(option);
    }
    select.value = Array.from(select.options).some((option) => option.value === current) ? current : "";
  }

  Object.assign(WebUI, { $, $$, rebuildSelect });
})();
