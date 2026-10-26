"""真实浏览器验证：
1. 评分后 localStorage 与 IndexedDB 是否都写进去了
2. 清掉 localStorage 后刷新，进度能否从 IndexedDB 恢复
3. PWA 的 manifest 与 Service Worker 是否生效
4. 题库的状态徽标与筛选
"""
import os

from playwright.sync_api import sync_playwright

# tests/ -> tools/ -> 仓库根（站点根）
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8771/index.html"

RATE = """() => {
  let n = 0;
  for (let i = 0; i < 4; i++) {
    if (!document.querySelector('#card')) break;
    reveal();
    const b = document.querySelector('.rate button[data-q="4"]');
    if (!b) break;
    b.click(); n++;
  }
  return n;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-proxy-server"])
    ctx = browser.new_context(viewport={"width": 420, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_timeout(1200)

    rated = page.evaluate(RATE)
    page.wait_for_timeout(900)

    ls_n = page.evaluate("() => { try { return Object.keys(JSON.parse(localStorage.getItem('engdrill.v1')).cards).length; } catch(e) { return -1; } }")
    idb_n = page.evaluate("() => idbGet('engdrill.v1').then(v => v && v.cards ? Object.keys(v.cards).length : -1)")
    print(f"rated={rated}  localStorage={ls_n}  indexedDB={idb_n}")

    page.evaluate("() => localStorage.removeItem('engdrill.v1')")
    page.reload(wait_until="load")
    page.wait_for_timeout(1800)
    print("recovered_after_reload =", page.evaluate("() => Object.keys(S.cards).length"))

    manifest = page.evaluate("() => fetch('./manifest.webmanifest').then(r => r.json()).then(d => d.name + ' / ' + d.icons.length + ' icons').catch(e => 'ERR')")
    sw = page.evaluate("() => navigator.serviceWorker.getRegistration().then(r => r ? 'registered:' + (r.active ? 'active' : 'installing') : 'none')")
    print(f"manifest={manifest}  sw={sw}")

    # 题库：状态徽标
    page.evaluate("() => document.querySelector('nav.tabs button[data-v=bank]').click()")
    page.wait_for_timeout(400)
    badges = page.evaluate("""() => {
      const out = {};
      document.querySelectorAll('.item__h .st').forEach(function(e){ out[e.textContent] = (out[e.textContent]||0)+1; });
      return out;
    }""")
    counts = page.evaluate("() => Array.from(document.querySelectorAll('.filters button')).slice(0,4).map(b => b.textContent)")
    print("badges =", badges)
    print("state filters =", counts)

    # 点「未学」筛选
    page.evaluate("""() => {
      const b = Array.from(document.querySelectorAll('.filters button')).find(x => x.dataset.state === 'new');
      b.click();
    }""")
    page.wait_for_timeout(300)
    items_new = page.evaluate("() => document.querySelectorAll('.item').length")
    print("筛选未学后条目数 =", items_new)

    # 展开第一张，看复习计划行
    page.evaluate("() => { const b = Array.from(document.querySelectorAll('.filters button')).find(x => x.dataset.state === 'all'); b.click(); }")
    page.wait_for_timeout(200)
    page.evaluate("() => document.querySelector('.item__h').click()")
    page.wait_for_timeout(300)
    first_body = page.evaluate("() => document.querySelector('.item__b').innerText.includes('复习计划') ? 'has-plan' : (document.querySelector('.item__b').innerText.includes('未学') ? 'no-plan' : 'unknown')")
    print("首条展开含复习计划 =", first_body)

    page.screenshot(path=os.path.join(ROOT, "_s_bank.png"), full_page=False)
    print("pageerrors =", errs if errs else "none")
    browser.close()
