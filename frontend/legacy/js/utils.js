export function $(id) {
  return document.getElementById(id);
}

export function pickId(...ids) {
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el) return el;
  }
  return null;
}

export function show(el, isVisible) {
  if (!el) return;
  el.style.display = isVisible ? "block" : "none";
}

export function setText(el, text) {
  if (!el) return;
  el.textContent = text;
}

export function safeNumber(val) {
  const n = Number(val);
  return Number.isFinite(n) ? n : null;
}

export function go(page) {
  window.location.href = page;
}