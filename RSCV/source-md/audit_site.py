#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站核对：链路一致性 / 断链 / 孤儿页 / 锚点 / 导航 / 搜索索引。"""
import os
import re
import json
import html as H

os.chdir('/home/claude/hb')
CH = json.load(open('/tmp/chains.json'))
MAIN, REF = CH['MAIN'], CH['REF']
fail = 0


def bad(msg):
    global fail
    fail += 1
    print('  ❌ ' + msg)


def ok(msg):
    print('  ✅ ' + msg)


pages = []
for root, _, fs in os.walk('.'):
    for f in fs:
        if f.endswith('.html'):
            pages.append(os.path.normpath(os.path.join(root, f)))
pages.sort()

# 解析每页的 pager
nxt, prv = {}, {}
for p in pages:
    s = open(p, encoding='utf-8').read()
    m = re.search(r'<div class="pager">(.*?)</div>', s, flags=re.S)
    if not m:
        continue
    if len(re.findall(r'<div class="pager">', s)) > 1:
        bad(f'{p} 有多个 pager')
    for cls, d in (('prev', prv), ('next', nxt)):
        mm = re.search(r'<a class="%s" href="([^"]+)"' % cls, m.group(1))
        if mm:
            d[p] = os.path.normpath(os.path.join(os.path.dirname(p), mm.group(1)))

print('【1】链路互指一致性（A.next=B ⟺ B.prev=A）')
for chain, name in ((MAIN, '主线'), (REF, '参考链')):
    errs = 0
    for i, p in enumerate(chain):
        want_prev = chain[i - 1] if i > 0 else None
        want_next = chain[i + 1] if i < len(chain) - 1 else 'index.html'
        if prv.get(p) != want_prev:
            bad(f'{name} {p}: prev 应为 {want_prev}，实际 {prv.get(p)}'); errs += 1
        if nxt.get(p) != want_next:
            bad(f'{name} {p}: next 应为 {want_next}，实际 {nxt.get(p)}'); errs += 1
    if not errs:
        ok(f'{name} {len(chain)} 页全部互指正确')

print('【2】起点无上一篇 / 终点有出口')
for chain, name in ((MAIN, '主线'), (REF, '参考链')):
    head, tail = chain[0], chain[-1]
    (ok if head not in prv else bad)(
        f'{name}起点 {head} ' + ('没有上一篇' if head not in prv else '竟然有上一篇'))
    (ok if nxt.get(tail) == 'index.html' else bad)(
        f'{name}终点 {tail} 指回首页')
(ok if 'index.html' not in prv else bad)('首页没有上一篇')
(ok if nxt.get('index.html') == MAIN[0] else bad)(f'首页下一篇 = {MAIN[0]}')

print('【3】每页都有出口（除搜索页）')
no_pager = [p for p in pages if p not in nxt and p not in prv and p != 'search.html']
(ok if not no_pager else bad)(f'无 pager 的页面: {no_pager or "无（search.html 已排除，属正常）"}')

print('【4】全站断链')
broken = []
for p in pages:
    s = open(p, encoding='utf-8').read()
    for href in re.findall(r'href="([^"#?]+\.(?:html|js|css))', s):
        if href.startswith(('http', 'mailto')):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), href))):
            broken.append((p, href))
(ok if not broken else bad)(f'断链 {len(broken)} 处 {broken[:5]}')

print('【5】孤儿页（没有任何页面链接到它）')
linked = set()
for p in pages:
    s = open(p, encoding='utf-8').read()
    for href in re.findall(r'href="([^"#?]+\.html)', s):
        linked.add(os.path.normpath(os.path.join(os.path.dirname(p), href)))
# 侧栏是 JS 生成的，把 app.js 里的 url('...') 也算上
appjs = open('assets/app.js', encoding='utf-8').read()
for u in re.findall(r"url\('([^']+\.html)'\)", appjs):
    linked.add(os.path.normpath(u))
for w in json.loads(open('assets/nav-data.js', encoding='utf-8')
                    .read()[len('window.NAV='):].rstrip().rstrip(';'))['weeks']:
    linked.add(os.path.normpath(f"week/w{w['w']}.html"))
orphans = [p for p in pages if p not in linked and p != 'index.html']
(ok if not orphans else bad)(f'孤儿页: {orphans or "无"}')

print('【6】页内锚点有效性（目录侧栏指向的 id 存在吗）')
anchor_err = []
for p in pages:
    s = open(p, encoding='utf-8').read()
    ids = set(re.findall(r'id="([^"]+)"', s))
    for a in re.findall(r'href="#([^"]+)"', s):
        if a and a not in ids:
            anchor_err.append((p, a))
(ok if not anchor_err else bad)(f'失效锚点 {len(anchor_err)} 个 {anchor_err[:5]}')

print('【7】搜索索引指向的页面都存在吗')
si = open('assets/search-index.js', encoding='utf-8').read()
data = json.loads(si[len('window.SEARCH_INDEX='):].rstrip().rstrip(';'))
missing = sorted({d['u'].split('#')[0] for d in data
                  if not os.path.exists(d['u'].split('#')[0])})
(ok if not missing else bad)(f'索引指向不存在的页面: {missing or "无"}（共 {len(data)} 条）')

print('【8】导航栏与面包屑')
crumb_err = []
for p in pages:
    if not p.startswith('week') or re.match(r'week[/\\]w\d+\.html$', p):
        continue
    s = open(p, encoding='utf-8').read()
    if '<div class="eyebrow">' in s and 'index.html' not in s[:s.find('</div>', s.find('eyebrow'))]:
        crumb_err.append(p)
(ok if not crumb_err else bad)(f'面包屑缺首页链接: {crumb_err or "无"}')

print('【9】主线顺序抽查')
idx = {p: i for i, p in enumerate(MAIN)}
checks = [('start/rs-basics.html', 'start/prerequisites.html'),
          ('start/prerequisites.html', 'week/w1.html'),
          ('week/w1.html', 'week/w1-d1-full.html'),
          ('week/w1-d3-d7-full.html', 'week/w2.html'),
          ('week/w2-d10-d14-full.html', 'week/w3.html'),
          ('week/w3-full.html', 'week/w4.html'),
          ('week/w29.html', 'week/stage2b-full.html')]
seq_ok = all(idx[a] < idx[b] for a, b in checks if a in idx and b in idx)
(ok if seq_ok else bad)('关键先后关系正确（M0→W1→详注→W2…）')
print('  主线前 8 页:', ' → '.join(MAIN[:8]))

print('\n' + ('全部通过 ✅' if fail == 0 else f'发现 {fail} 个问题 ❌'))
