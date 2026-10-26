#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把「候选卡片」合并进 cards.json（本仓库就是站点仓库 ccccty/study）。

用法（在仓库根目录执行）：
    python tools/merge_cards.py candidates/2026-10-27.json
    python tools/merge_cards.py candidates/*.json --dry-run
    python tools/merge_cards.py candidates/today.json --max=8

设计原则：
  1. 只做合并与校验，不做内容生成 —— 生成那一步可以是 LLM、也可以是人。
  2. 幂等：同一份候选重复跑不会产生重复卡片。
  3. 去重同时对比内置题库（index.html 的 RAW）和已有的 cards.json。
  4. 不合格的条目跳过并打印原因，不中断整批。
"""

import sys
import json
import re
import io
import os
import datetime

# 脚本在 tools/ 下，仓库根就是站点根（https://ccccty.github.io/study/）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'index.html')
JSONF = os.path.join(ROOT, 'cards.json')

VALID_CATS = ['sens', 'radar', 'fusion', 'est', 'mcu', 'bus',
              'deploy', 'auto', 'ml', 'embodied', 'quant', 'ros2']

LIMITS = {
    'term': (1, 40),
    'en':   (0, 80),
    'one':  (8, 120),
    'use':  (8, 160),
    'trap': (8, 160),
    'jd':   (8, 220),
}
POINT_MIN, POINT_MAX = 2, 5
POINT_LEN = 160


def norm(s):
    """术语归一化：去空白、去括号补充说明、小写。用于去重。"""
    s = re.sub(r'\s+', '', str(s or ''))
    s = re.sub(r'[（(][^）)]*[）)]', '', s)
    return s.lower()


def load_existing_terms():
    """内置题库的术语从 index.html 的 RAW 数组里抓，避两份数据漂移。"""
    terms = set()
    try:
        with io.open(HTML, 'r', encoding='utf-8') as f:
            html = f.read()
        for m in re.finditer(r"^\['([a-z]+)','([^']+)','", html, re.M):
            terms.add(norm(m.group(2)))
    except IOError:
        sys.stderr.write('[warn] 读不到 %s，只按 cards.json 去重\n' % HTML)
    return terms


def load_cards():
    if not os.path.exists(JSONF):
        return {'version': 1, 'updated': '', 'cards': []}
    with io.open(JSONF, 'r', encoding='utf-8') as f:
        d = json.load(f)
    d.setdefault('cards', [])
    return d


def check(item):
    """返回 (ok, reason)。任何一条不合格就整条丢弃，不带病入库。"""
    if not isinstance(item, dict):
        return False, 'not an object'
    for key, (lo, hi) in LIMITS.items():
        v = item.get(key, '')
        if not isinstance(v, str):
            return False, '%s 不是字符串' % key
        v = v.strip()
        if len(v) < lo:
            return False, '%s 太短（%d < %d）' % (key, len(v), lo)
        if len(v) > hi:
            return False, '%s 太长（%d > %d）' % (key, len(v), hi)
    pts = item.get('pts')
    if not isinstance(pts, list) or not (POINT_MIN <= len(pts) <= POINT_MAX):
        return False, 'pts 需 %d-%d 条' % (POINT_MIN, POINT_MAX)
    for p in pts:
        if not isinstance(p, str) or len(p.strip()) < 8:
            return False, 'pts 里有空条目'
        if len(p.strip()) > POINT_LEN:
            return False, 'pts 单条超过 %d 字' % POINT_LEN
    cat = item.get('cat')
    if cat not in VALID_CATS:
        return False, 'cat 不在白名单：%s' % cat
    return True, ''


def main(argv):
    files = [a for a in argv[1:] if not a.startswith('--')]
    dry = '--dry-run' in argv
    maxn = None
    for a in argv[1:]:
        if a.startswith('--max'):
            maxn = int(a.split('=', 1)[1]) if '=' in a else None
    if not files:
        print('用法：python tools/merge_cards.py <候选卡 json> [--dry-run] [--max=8]')
        return 1

    data = load_cards()
    seen = load_existing_terms()
    for c in data['cards']:
        seen.add(norm(c.get('term')))

    added, skipped = [], []
    for path in files:
        if not os.path.exists(path):
            sys.stderr.write('[warn] 文件不存在：%s\n' % path)
            continue
        with io.open(path, 'r', encoding='utf-8') as f:
            try:
                payload = json.load(f)
            except ValueError as e:
                sys.stderr.write('[warn] %s 不是合法 JSON：%s\n' % (path, e))
                continue
        items = payload.get('cards') if isinstance(payload, dict) else payload
        if not isinstance(items, list):
            sys.stderr.write('[warn] %s 里没有 cards 数组\n' % path)
            continue

        for it in items:
            if maxn is not None and len(added) >= maxn:
                skipped.append((it.get('term', '?'), '超过本次上限 %d' % maxn))
                continue
            ok, reason = check(it)
            if not ok:
                skipped.append((it.get('term', '?'), reason))
                continue
            key = norm(it['term'])
            if key in seen:
                skipped.append((it['term'], '已存在'))
                continue
            seen.add(key)
            added.append({
                'cat': it['cat'],
                'term': it['term'].strip(),
                'en': it.get('en', '').strip(),
                'one': it['one'].strip(),
                'pts': [p.strip() for p in it['pts']],
                'use': it['use'].strip(),
                'trap': it['trap'].strip(),
                'jd': it['jd'].strip(),
                'added': it.get('added') or datetime.date.today().isoformat(),
            })

    if not dry:
        data['cards'].extend(added)
        data['updated'] = datetime.date.today().isoformat()
        with io.open(JSONF, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

    print('=' * 52)
    print('%s新增 %d 张，跳过 %d 张；cards.json 现有 %d 张'
          % ('[dry-run] ' if dry else '', len(added),
             len(skipped), len(data['cards'])))
    for c in added:
        print('  + [%s] %s' % (c['cat'], c['term']))
    if skipped:
        print('-- 跳过 --')
        for t, r in skipped[:20]:
            print('  - %s：%s' % (t, r))
        if len(skipped) > 20:
            print('  ... 另有 %d 条' % (len(skipped) - 20))
    print('=' * 52)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
