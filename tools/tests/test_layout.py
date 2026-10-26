"""检查 320/375/420 宽度下是否横向溢出，并定位溢出元素"""
import os

from playwright.sync_api import sync_playwright

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8771/index.html"

PROBE = """() => {
  const doc = document.documentElement;
  const over = [];
  document.querySelectorAll('*').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.width > 0 && r.right > doc.clientWidth + 1) {
      over.push(e.tagName + '.' + (e.className || '').toString().split(' ')[0] + '@' + Math.round(r.right));
    }
  });
  return { sw: doc.scrollWidth, cw: doc.clientWidth, over: over.slice(0, 8) };
}"""

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-proxy-server"])
    for w, h, label in [(320, 780, "SE"), (375, 812, "iPhone"), (420, 900, "Android")]:
        ctx = b.new_context(viewport={"width": w, "height": h})
        pg = ctx.new_page()
        pg.goto(URL, wait_until="load")
        pg.wait_for_timeout(900)
        for view in ["today", "bank", "data"]:
            pg.evaluate(f"() => document.querySelector('nav.tabs button[data-v={view}]').click()")
            pg.wait_for_timeout(250)
            r = pg.evaluate(PROBE)
            flag = "OVERFLOW" if r["sw"] > r["cw"] + 1 else "ok"
            print(f"{label} {w}px {view:5s} sw={r['sw']} cw={r['cw']} {flag} {r['over'] if r['over'] else ''}")
        ctx.close()
    b.close()
