(function () {
  const navFilter = document.getElementById("navFilter");
  const navItems = Array.from(document.querySelectorAll("[data-nav-item]"));

  if (navFilter && navItems.length) {
    navFilter.addEventListener("input", () => {
      const query = navFilter.value.trim().toLowerCase();
      navItems.forEach((item) => {
        const haystack = (item.getAttribute("data-search") || "").toLowerCase();
        item.classList.toggle("hidden", Boolean(query) && !haystack.includes(query));
      });
    });
  }

  async function replaceCatalog(url, pushState) {
    const response = await fetch(url, { headers: { "X-Requested-With": "fetch" } });
    if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
    const text = await response.text();
    const doc = new DOMParser().parseFromString(text, "text/html");
    const nextCatalog = doc.querySelector("#catalog");
    const currentCatalog = document.querySelector("#catalog");
    if (!nextCatalog || !currentCatalog) return false;
    const currentTop = currentCatalog.getBoundingClientRect().top;
    const currentHeight = currentCatalog.offsetHeight;
    nextCatalog.style.minHeight = `${currentHeight}px`;
    currentCatalog.replaceWith(nextCatalog);
    const nextTop = nextCatalog.getBoundingClientRect().top;
    const previousScrollBehavior = document.documentElement.style.scrollBehavior;
    document.documentElement.style.scrollBehavior = "auto";
    window.scrollBy(0, nextTop - currentTop);
    document.documentElement.style.scrollBehavior = previousScrollBehavior;
    if (pushState) {
      const nextUrl = new URL(url, window.location.href);
      history.pushState({ catalog: true }, "", `${nextUrl.pathname}${nextUrl.search}`);
    }
    return true;
  }

  document.addEventListener("click", (event) => {
    const filter = event.target.closest('[data-filter-link="catalog"]');
    if (!filter) return;
    event.preventDefault();
    replaceCatalog(filter.href, true).catch(() => {
      window.location.href = filter.href;
    });
  });

  window.addEventListener("popstate", () => {
    replaceCatalog(window.location.href, false).catch(() => {
      window.location.reload();
    });
  });

  document.addEventListener("click", (event) => {
    const action = event.target.closest("[data-doc-action]");
    if (!action) return;
    const sections = Array.from(document.querySelectorAll(".doc-section"));
    const shouldOpen = action.getAttribute("data-doc-action") === "expand";
    sections.forEach((section) => {
      const title = section.querySelector("summary span")?.textContent || "";
      const isFocusSection = /summary|key claims|creative impact mapping|first signal|domain-level synthesis|special analysis layer/i.test(title);
      section.open = shouldOpen || isFocusSection;
    });
  });

  document.addEventListener("click", (event) => {
    const anchor = event.target.closest('a[href*="#"]');
    if (!anchor) return;
    const href = anchor.getAttribute("href");
    const url = new URL(anchor.href, window.location.href);
    if (url.pathname === window.location.pathname && url.hash) {
      const target = document.querySelector(url.hash);
      if (!target) return;
      event.preventDefault();
      if (target.matches("details")) {
        target.open = true;
      }
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", url.hash);
    }
  });
})();
