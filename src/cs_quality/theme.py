"""OLED 操作台主题：黄铜单强调、错开入场、尊重 reduced-motion。"""

from __future__ import annotations

import html


FONT_LINKS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;600&family=Fira+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
""".strip()

CSS = r"""
:root {
  --bg: #07090c;
  --bg-2: #0c1016;
  --surface: #121821;
  --surface-2: #171f2a;
  --line: rgba(232, 184, 109, 0.16);
  --line-strong: rgba(232, 184, 109, 0.38);
  --ink: #e9eef4;
  --muted: #8b96a8;
  --brass: #e8b86d;
  --brass-2: #f3d08a;
  --ok: #5ee0c5;
  --bad: #ff7a7a;
  --warn: #f0c27a;
  --shadow: 0 18px 48px rgba(0, 0, 0, 0.35);
  --ease: cubic-bezier(.16, 1, .3, 1);
  color-scheme: dark;
}
* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
  margin: 0;
  background:
    radial-gradient(1100px 520px at 8% -18%, rgba(232, 184, 109, 0.14), transparent 58%),
    radial-gradient(800px 380px at 92% 0%, rgba(94, 224, 197, 0.05), transparent 52%),
    var(--bg);
  color: var(--ink);
  font: 15px/1.55 "Fira Sans", "Segoe UI", "Microsoft YaHei", sans-serif;
  letter-spacing: 0.01em;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 50;
  opacity: 0.04;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
}
a { color: var(--brass); }
a:focus-visible, button:focus-visible {
  outline: 2px solid var(--brass);
  outline-offset: 3px;
}
.top {
  position: relative;
  padding: 52px max(6vw, 24px) 92px;
  overflow: hidden;
}
.top::after {
  content: "";
  position: absolute;
  left: max(6vw, 24px);
  bottom: 36px;
  width: 88px;
  height: 2px;
  background: var(--brass);
  transform: scaleX(0);
  transform-origin: left center;
  animation: ruleIn 1.1s var(--ease) .15s forwards;
}
.eyebrow {
  color: var(--brass);
  letter-spacing: 0.22em;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
h1 {
  font-size: clamp(28px, 4vw, 42px);
  margin: 10px 0 8px;
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.15;
}
.top p { color: var(--muted); margin: 0; max-width: 46rem; }
.nav { margin: 18px 0 0; display: flex; gap: 8px; flex-wrap: wrap; }
.nav a {
  color: var(--ink);
  text-decoration: none;
  padding: 8px 12px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(18, 24, 33, 0.55);
  cursor: pointer;
  transition: border-color 200ms var(--ease), color 200ms var(--ease), background 200ms var(--ease);
}
.nav a:hover { border-color: var(--line-strong); color: var(--brass-2); }
main { max-width: 1180px; margin: -42px auto 72px; padding: 0 24px; position: relative; z-index: 1; }
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.metric, .panel {
  background: linear-gradient(180deg, rgba(255,255,255,0.03), transparent 42%), var(--surface);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: var(--shadow);
}
.metric {
  padding: 22px 20px 18px;
  position: relative;
  overflow: hidden;
  transition: border-color 200ms var(--ease), transform 220ms var(--ease);
}
.metric::before {
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: var(--brass);
  transform: scaleY(0);
  transform-origin: top;
  animation: ruleIn .6s var(--ease) calc(var(--d, 0) * 80ms + 280ms) forwards;
}
.metric:hover { border-color: var(--line-strong); transform: translateY(-2px); }
.metric span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.metric strong {
  display: block;
  margin-top: 8px;
  font: 600 30px/1.1 "Fira Code", "Fira Sans", monospace;
  color: var(--ink);
  letter-spacing: -0.04em;
}
.grid { display: grid; gap: 14px; margin-top: 14px; align-items: start; }
.two { grid-template-columns: 1fr 1fr; }
.panel { padding: 24px; }
.panel ul { margin: 0; padding-left: 1.15em; }
.panel li { margin: 8px 0; }
h2 {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin: 0 0 16px;
}
.bar-row {
  display: grid;
  grid-template-columns: 150px 1fr 48px;
  gap: 10px;
  align-items: center;
  margin: 11px 0;
  font-size: 13px;
}
.bar-row b { font-family: "Fira Code", monospace; font-weight: 500; text-align: right; }
.track {
  height: 7px;
  background: #1c2430;
  border-radius: 99px;
  overflow: hidden;
}
.track i {
  display: block;
  height: 100%;
  width: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #b8893e, var(--brass-2));
  transform: scaleX(0);
  transform-origin: left center;
  animation: fillBar .95s var(--ease) calc(var(--i, 0) * 70ms + 420ms) forwards;
}
.wide { margin-top: 14px; }
table { width: 100%; border-collapse: collapse; }
th, td {
  padding: 12px 10px;
  text-align: left;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  vertical-align: top;
}
tbody tr { transition: background 180ms var(--ease); }
tbody tr:hover { background: rgba(232, 184, 109, 0.05); }
th {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
}
code { color: var(--brass); font-family: "Fira Code", monospace; font-size: 12px; }
.pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 2px;
  background: rgba(232, 184, 109, 0.12);
  color: var(--brass-2);
  font-size: 12px;
}
.pill.critical { background: rgba(255, 122, 122, 0.16); color: #ffb4b4; }
.pill.high { background: rgba(240, 194, 122, 0.16); color: var(--warn); }
.pill.none { background: rgba(94, 224, 197, 0.12); color: var(--ok); }
.bad, .fp, .fn { color: var(--bad); font-weight: 700; }
.ok, .tp, .tn { color: var(--ok); font-weight: 700; }
.matrix { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.matrix div {
  padding: 16px;
  border-radius: 3px;
  background: var(--surface-2);
  border: 1px solid var(--line);
}
.matrix b { display: block; font: 600 26px/1.1 "Fira Code", monospace; margin-top: 6px; }
.foot { color: var(--muted); font-size: 12px; margin-top: 22px; }
.reveal {
  animation: rise .75s var(--ease) both;
  animation-delay: calc(var(--d, 0) * 70ms);
}
.index-wrap { max-width: 880px; margin: 0 auto; padding: 72px 24px 96px; position: relative; z-index: 1; }
.index-wrap h1 { font-size: clamp(36px, 6vw, 58px); }
.index-wrap > p { color: var(--muted); margin: 0 0 36px; max-width: 36rem; }
.task {
  display: grid;
  grid-template-columns: 72px 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 22px 8px;
  border-top: 1px solid var(--line);
  text-decoration: none;
  color: inherit;
  cursor: pointer;
  min-height: 88px;
  transition: background 200ms var(--ease), padding-left 220ms var(--ease), border-color 200ms var(--ease);
}
.task:last-child { border-bottom: 1px solid var(--line); }
.task:hover, .task:focus-visible {
  background: rgba(232, 184, 109, 0.05);
  padding-left: 10px;
  outline: none;
}
.task:focus-visible { box-shadow: inset 0 0 0 2px var(--brass); }
.task .code {
  font: 600 13px/1 "Fira Code", monospace;
  color: var(--brass);
  letter-spacing: 0.08em;
}
.task b { display: block; font-size: 18px; font-weight: 600; }
.task span { display: block; color: var(--muted); font-size: 14px; margin-top: 4px; }
.task svg { width: 18px; height: 18px; color: var(--brass); opacity: 0.55; transition: opacity 200ms, transform 220ms var(--ease); }
.task:hover svg { opacity: 1; transform: translateX(4px); }
@keyframes rise {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: none; }
}
@keyframes fillBar {
  to { transform: scaleX(var(--fill, 0)); }
}
@keyframes ruleIn {
  to { transform: scaleX(1); }
}
@media (max-width: 760px) {
  .metrics, .two, .matrix { grid-template-columns: 1fr 1fr; }
  .bar-row { grid-template-columns: 1fr; gap: 4px; }
  .task { grid-template-columns: 64px 1fr; }
  .task svg { display: none; }
}
@media (max-width: 500px) {
  .metrics, .two, .matrix { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
  .track i { transform: scaleX(var(--fill, 0)); }
  .metric::before, .top::after { transform: none; }
}
""".strip()

JS = r"""
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce) return;
  var nodes = document.querySelectorAll("[data-count]");
  nodes.forEach(function (el) {
    var target = Number(el.getAttribute("data-count"));
    if (!isFinite(target)) return;
    var suffix = el.getAttribute("data-suffix") || "";
    var prefix = el.getAttribute("data-prefix") || "";
    var decimals = Number(el.getAttribute("data-decimals") || 0);
    var start = null;
    var dur = 900;
    function tick(now) {
      if (start === null) start = now;
      var t = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
})();
""".strip()


def page_head(title: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n"
        f"{FONT_LINKS}\n"
        f"<style>\n{CSS}\n</style>\n"
        "</head>\n<body>\n"
    )


def page_foot() -> str:
    return f"<script>\n{JS}\n</script>\n</body></html>"
