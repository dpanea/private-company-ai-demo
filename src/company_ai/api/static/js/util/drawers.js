const SIDES = { left: "drawer-left-open", right: "drawer-right-open" };
const MOBILE_MAX_PX = 768;
let globalsBound = false;

function isMobile() {
  return window.matchMedia(`(max-width: ${MOBILE_MAX_PX}px)`).matches;
}

export function closeDrawers() {
  document.body.classList.remove(SIDES.left, SIDES.right);
  document.querySelectorAll("[data-app-drawer-toggle]").forEach((btn) => {
    btn.setAttribute("aria-expanded", "false");
  });
}

export function toggleDrawer(side) {
  const cls = SIDES[side];
  if (!cls) return;
  const opening = !document.body.classList.contains(cls);
  document.body.classList.remove(SIDES.left, SIDES.right);
  if (opening) document.body.classList.add(cls);
  document.querySelectorAll("[data-app-drawer-toggle]").forEach((btn) => {
    const isThisOpen = opening && btn.dataset.appDrawerToggle === side;
    btn.setAttribute("aria-expanded", isThisOpen ? "true" : "false");
  });
}

export function bindDrawerHandlers(root) {
  root.querySelectorAll("[data-app-drawer-toggle]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      toggleDrawer(btn.dataset.appDrawerToggle);
    });
  });

  root.querySelectorAll(".control-panel, .source-panel").forEach((panel) => {
    panel.addEventListener("click", (event) => {
      if (!isMobile()) return;
      const target = event.target.closest("button, a");
      if (!target) return;
      setTimeout(closeDrawers, 0);
    });
    panel.addEventListener("change", (event) => {
      if (!isMobile()) return;
      if (event.target.matches("select")) setTimeout(closeDrawers, 0);
    });
  });

  bindGlobalHandlers();
}

function bindGlobalHandlers() {
  if (globalsBound) return;
  globalsBound = true;

  document.getElementById("mobile-drawer-backdrop")?.addEventListener("click", closeDrawers);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDrawers();
  });

  window.addEventListener("resize", () => {
    if (!isMobile()) closeDrawers();
  });
}
