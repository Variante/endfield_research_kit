(() => {
  const WebUI = window.WebUI = window.WebUI || {};
  const PAGE_SIZES = [50, 100, 200, 500];
  const MIN_PAGE_SIZE = 1;
  const MAX_PAGE_SIZE = 10000;
  let pagerSequence = 0;

  function localeText() {
    const zh = String(window.WEBUI_UI_LOCALE || document.documentElement.lang || "zh")
      .toLowerCase().startsWith("zh");
    return zh
      ? { previous: "上一页", next: "下一页", page: "页", perPage: "每页" }
      : { previous: "Previous", next: "Next", page: "Page", perPage: "Per page" };
  }

  function normalizePageSize(value, fallback) {
    const parsed = Number(value);
    if (!Number.isInteger(parsed) || parsed < MIN_PAGE_SIZE) return fallback;
    return Math.min(parsed, MAX_PAGE_SIZE);
  }

  function storedPageSize(storageKey, fallback) {
    return normalizePageSize(WebUI.storageGet?.(storageKey), fallback);
  }

  function createPager({ container, storageKey, defaultPageSize = 100, onChange }) {
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    const fallbackPageSize = normalizePageSize(defaultPageSize, 100);
    const suggestionsId = `list-pager-size-suggestions-${++pagerSequence}`;
    const state = {
      page: 0,
      pageSize: storedPageSize(storageKey, fallbackPageSize),
      total: 0,
    };

    host.classList.add("list-pager");
    host.innerHTML = `
      <button class="list-pager-prev" type="button"></button>
      <label class="list-pager-page"><span class="list-pager-page-prefix"></span><input type="number" min="1" step="1" inputmode="numeric"><span class="list-pager-page-total" aria-live="polite"></span></label>
      <label class="list-pager-size"><span></span><input type="number" min="${MIN_PAGE_SIZE}" max="${MAX_PAGE_SIZE}" step="1" inputmode="numeric" list="${suggestionsId}"></label>
      <datalist id="${suggestionsId}">${PAGE_SIZES.map((value) => `<option value="${value}"></option>`).join("")}</datalist>
      <button class="list-pager-next" type="button"></button>`;
    const previous = host.querySelector(".list-pager-prev");
    const next = host.querySelector(".list-pager-next");
    const pagePrefix = host.querySelector(".list-pager-page-prefix");
    const pageInput = host.querySelector(".list-pager-page input");
    const pageTotal = host.querySelector(".list-pager-page-total");
    const sizeLabel = host.querySelector(".list-pager-size span");
    const sizeInput = host.querySelector(".list-pager-size input");
    sizeInput.value = String(state.pageSize);

    const pageCount = () => Math.max(1, Math.ceil(state.total / state.pageSize));
    const render = () => {
      state.page = Math.min(state.page, pageCount() - 1);
      const text = localeText();
      previous.textContent = text.previous;
      next.textContent = text.next;
      sizeLabel.textContent = text.perPage;
      pagePrefix.textContent = `${text.page} `;
      pageInput.setAttribute("aria-label", text.page);
      pageInput.max = String(pageCount());
      pageInput.value = String(state.page + 1);
      pageTotal.textContent = ` / ${pageCount()}`;
      sizeInput.value = String(state.pageSize);
      previous.disabled = state.page <= 0;
      next.disabled = state.page + 1 >= pageCount();
    };
    const changed = () => {
      render();
      onChange?.();
    };
    previous.addEventListener("click", () => {
      if (state.page <= 0) return;
      state.page -= 1;
      changed();
    });
    next.addEventListener("click", () => {
      if (state.page + 1 >= pageCount()) return;
      state.page += 1;
      changed();
    });
    const commitPage = () => {
      const requested = Number(pageInput.value);
      if (!Number.isInteger(requested)) {
        pageInput.value = String(state.page + 1);
        return;
      }
      const page = Math.min(Math.max(requested, 1), pageCount()) - 1;
      pageInput.value = String(page + 1);
      if (page === state.page) return;
      state.page = page;
      changed();
    };
    pageInput.addEventListener("change", commitPage);
    pageInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      commitPage();
      pageInput.blur();
    });
    const commitPageSize = () => {
      const pageSize = normalizePageSize(sizeInput.value, state.pageSize);
      sizeInput.value = String(pageSize);
      if (pageSize === state.pageSize) return;
      state.pageSize = pageSize;
      state.page = 0;
      WebUI.storageSet?.(storageKey, String(state.pageSize));
      changed();
    };
    sizeInput.addEventListener("change", commitPageSize);
    sizeInput.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      commitPageSize();
      sizeInput.blur();
    });

    const api = {
      get page() { return state.page; },
      get pageSize() { return state.pageSize; },
      setTotal(total, { reset = false } = {}) {
        state.total = Math.max(0, Number(total) || 0);
        if (reset) state.page = 0;
        render();
      },
      reset() {
        if (!state.page) return false;
        state.page = 0;
        render();
        return true;
      },
      slice(items) {
        const start = state.page * state.pageSize;
        return items.slice(start, start + state.pageSize);
      },
      showIndex(index) {
        if (index < 0) return false;
        const page = Math.floor(index / state.pageSize);
        if (page === state.page) return false;
        state.page = page;
        render();
        return true;
      },
      refresh: render,
    };
    render();
    window.addEventListener("webui:ui-locale-changed", render);
    return api;
  }

  WebUI.pagination = { createPager, PAGE_SIZES, MIN_PAGE_SIZE, MAX_PAGE_SIZE };
})();
