export function qs(selector, root = document) {
  return root.querySelector(selector);
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function on(target, eventName, handler, options) {
  target.addEventListener(eventName, handler, options);
  return () => target.removeEventListener(eventName, handler, options);
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function setHtml(node, html) {
  node.innerHTML = html;
  return node;
}

export function showToast(message, tone = "success") {
  const root = qs("#toast-root");
  if (!root) return;
  const toast = document.createElement("div");
  toast.className = `toast ${tone}`;
  toast.setAttribute("role", tone === "error" ? "alert" : "status");
  toast.textContent = message;
  root.append(toast);
  window.setTimeout(() => toast.remove(), 5200);
}

export function emptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

export function loadingSkeleton() {
  return `
    <div class="skeleton skeleton-row"></div>
    <div class="skeleton skeleton-row short"></div>
    <div class="skeleton skeleton-row"></div>
  `;
}

export function trapDialogFocus(dialog) {
  const selectors = [
    "a[href]",
    "button:not([disabled])",
    "textarea:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
  ].join(",");

  function handleKeydown(event) {
    if (event.key !== "Tab") return;
    const focusable = qsa(selectors, dialog);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  dialog.addEventListener("keydown", handleKeydown);
  return () => dialog.removeEventListener("keydown", handleKeydown);
}
