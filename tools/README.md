# 每日岗位 → 概念卡片 · 流水线

把「BOSS 上今天新出的岗位要求」变成「明天要背的卡片」。

**这条流水线和站点在同一个仓库里**（`ccccty/study`），不再有第二个仓库：

```
抓取 → 抽词 → 写卡 → merge_cards.py 写入 ../cards.json → git push
```

push 之后 Pages 自动重建，手机打开 `https://ccccty.github.io/study/` 就是最新题库。

---

## 为什么只有这一个仓库

站点文件（`index.html` / `cards.json` / `sw.js` / `icons/`）和产生数据的脚本放在一起，好处很实际：

- 卡片数据的写入方和读取方在同一棵树里，不会出现「脚本改了路径、站点还读老数据」
- 每天只有**一次** commit、一次 push，不用在两个仓库之间同步
- 换领域时改 `config.json` + `cards.json`，代码一行不动

---

## 目录

```
tools/
  config.json          城市、岗位方向、检索关键词、阈值
  jd_to_cards.md       抽词与写卡规范（人机共用的八字段标准）
  merge_cards.py       候选卡 → ../cards.json（校验 + 幂等 + 按术语去重）
  make_qr.py           生成 ../qr.png（手机直达二维码）
  make_icons.py        生成 ../icons/（PWA 图标）
  tests/
    test_persist.py    Playwright：评分写入 / IndexedDB 恢复 / PWA 生效
    test_layout.py     Playwright：320-430px 多宽度横向溢出检查
../candidates/         每天的候选卡（YYYY-MM-DD.json），写卡的中间产物
```

`merge_cards.py` 的校验是**拒收**而不是修补：字段不全、太长太短、`pts` 条数不对、`cat` 不在白名单、术语重复——任一条命中就整条丢弃并打印原因，不带病入库。

去重同时比对两处：`../index.html` 里 `RAW` 数组的内置卡（129 张），以及 `../cards.json` 已有的增量卡。术语归一化规则是「去空白 + 去括号注释 + 转小写」，所以 `TF2`、`TF 2`、`TF2（坐标变换）` 视为同一张。

---

## 每日流程

```bash
# 0. 在仓库根目录（E:/工作/个人简介/study）执行下面所有命令

# 1. 抓取：交给 boss-scrape 技能，两阶段（先翻列表、再按相关性取详情）
#    产出带正文的岗位 JSON，放在 ../data/ 或任意临时目录

# 2. 抽词：交给 boss-study 技能的 extract_terms.py
python ~/.workbuddy/skills/boss-study/scripts/extract_terms.py \
    --input data/xxx_detail.json --out data/terms.json \
    --known cards.json --top 60

# 3. 写卡：按 jd_to_cards.md 的八字段，产出 candidates/YYYY-MM-DD.json

# 4. 合并：先看会新增什么、拒收什么
python tools/merge_cards.py candidates/2026-10-27.json --dry-run

# 5. 正式写入
python tools/merge_cards.py candidates/2026-10-27.json

# 6. 一次 commit 一次 push（数据和候选记录都在这个仓库里）
git add cards.json candidates/ && git commit -m "cards: 2026-10-27 新增 5 张" && git push

# 7. 顺手出一份岗位市场报告（本地，不入库）
cd E:/工作/boss-jobs && .venv/Scripts/python.exe \
  C:/Users/50357/.workbuddy/skills/boss-analyze/scripts/analyze.py \
  --input data/study_2026-10-27_detail.json \
  --out "reports/岗位市场报告_2026-10-27.html" --top 40
```

报告是自包含 HTML（KPI / 城市分布 / 岗位类型 / 薪资区间 / 经验学历 / JD 高频词 / 公司 Top10 / 可展开的岗位明细），断网也能看。

**报告只留在本地 `E:/工作/boss-jobs/reports/`，不提交进本仓库** —— 它含公司名、薪资与 JD 原文，放到公开的 GitHub Pages 等于对外分发抓取数据。

### 参数

| 参数 | 说明 |
|---|---|
| `--dry-run` | 只报告，不写文件 |
| `--max=8` | 本次最多写入几张，配合「宁少勿滥」 |

`tools/config.json` 里的 `minMentions`（默认 3）控制「一个概念被几个不同岗位提到才值得做卡」；`maxPagesPerKeyword`（3 页）与 `maxDetailsPerDay`（60 条）控制抓取量——60 条详情约 9 分钟，120 条约 19 分钟。改城市或方向只改这个文件。

---

## 写卡的硬标准（摘要，全文见 `jd_to_cards.md`）

| 字段 | 回答什么 | 会被拒收的写法 |
|---|---|---|
| `term` | 叫什么 | 带括号注释（英文放 `en`） |
| `one` | 是什么，一句话 | 写成用途 |
| `jd` | **为什么考它** | 「该岗位要求掌握本概念」这类空话 |
| `pts` | 3–4 条原理，至少一条带数值 | 全是定性描述 |
| `use` | 工程上怎么用 | 和 `one` 重复 |
| `trap` | 具体可验证的坑 | 「注意安全」「参数要调好」 |

写 `jd` / `trap` 的唯一信息源是抽词结果里的 `samples`（岗位原文片段），不许凭印象编。

---

## 测试怎么跑

改完 `index.html`（界面或内置卡）后跑一遍，这两件事最容易悄悄坏掉：

```bash
# 在仓库根目录起静态服务（测试脚本默认 8771 端口）
python -m http.server 8771

# 另开一个终端
python tools/tests/test_persist.py   # 评分 4 张 → 抹掉 localStorage → 刷新 → 看能否从 IndexedDB 恢复
python tools/tests/test_layout.py    # 320/375/420 三档宽度下检查横向溢出
```

> 用 Playwright 拍真实时钟。**不要用 `chrome --headless --virtual-time-budget`**：虚拟时钟下 IndexedDB 的异步回调永远不触发，会把「能恢复」误测成「恢复不了」。

---

## 首次抓取要扫码

`boss-scrape` 复用登录态，第一次跑会开浏览器等你扫码。扫一次，之后靠 cookie 静默运行几十天。环境没配好就先跑 `boss-setup`。

---

## 风控清单

- 每个关键词每天只翻 3 页列表，别贪
- 请求间隔不要压到 1 秒以内，详情页尤其
- 只在**一个**设备上跑，多台并发登录同一账号是明显的异常信号
- cookie 失效时不要反复重试，停下来重新扫码
- 一天 30–50 个岗位的 JD 已经够写了，抓多了也消化不了

---

## 常见问题

**Q：卡片加错了想删？**
删掉 `cards.json` 里那个对象，push。手机上那条进度记录还在浏览器里，不影响其他卡。

**Q：能不能只加我感兴趣的？**
可以。`candidates/` 里的 JSON 随便删减，`merge_cards.py` 只认留下来的。

**Q：想换领域（比如只做数据安全）？**
改 `config.json` 的 `cities` / `domains`，`jd_to_cards.md` 的八字段不变，`cards.json` 继续追加。要全新起一个站，用 `boss-study` 技能的 `build_site.py`，别在这里改。
