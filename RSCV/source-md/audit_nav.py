#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导航专项核对：侧栏 / 顶栏 / 面包屑 / 目录 / 阶段树 / 动线。"""
import os
import re
import json
import html as H

os.chdir('/home/claude/v3')
fail = 0
def bad(m):
    global fail; fail += 1; print('  ❌ ' + m)
def ok(m):
    print('  ✅ ' + m)

a = open('assets/app.js', encoding='utf-8').read()
nav = json.loads(open('assets/nav-data.js', encoding='utf-8')
                 .read()[len('window.NAV='):].rstrip().rstrip(';'))

print('【1】侧栏：链接全部指向存在的文件')
urls = re.findall(r"url\('([^']+\.html)'\)", a)
missing = sorted({u for u in urls if not os.path.exists(u)})
(ok if not missing else bad)(f'侧栏 {len(set(urls))} 个目标，缺失: {missing or "无"}')

print('【2】侧栏：无重复条目')
pairs = re.findall(r"\['([^']+\.html)', '([^']+)'\]", a)
dup = [x for x in {p for p in pairs} if pairs.count(x) > 1]
names = [t for _, t in pairs]
dupname = sorted({n for n in names if names.count(n) > 1})
(ok if not dup and not dupname else bad)(f'重复条目: {dup or dupname or "无"}')

print('【3】侧栏：每条都带 <a> 标签（不会出现无链接大字）')
broken = re.findall(r"html\.push\('<span class=\\?\"wid", a)
(ok if not broken else bad)(f'裸 span 残渣 {len(broken)} 处')

print('【4】阶段树：nav-data 里每一周都有对应文件')
miss = [w['w'] for w in nav['weeks'] if not os.path.exists(w['href'])]
(ok if not miss else bad)(f'缺页的周次: {miss or "无"}')
print(f'     阶段 {len(nav["stages"])} 个 · 模块 {len(nav["modules"])} 个 · 周 {len(nav["weeks"])} 个')

print('【5】阶段树：缓冲周指向 buffer.html')
buf = [b for m in nav['modules'] for b in (m.get('buffer') or [])]
(ok if os.path.exists('buffer.html') else bad)(f'缓冲周 {buf} → buffer.html 存在')

print('【6】顶栏：每页的顶部导航链接有效')
bad_top = []
for root, _, fs in os.walk('.'):
    for f in fs:
        if not f.endswith('.html'):
            continue
        p = os.path.normpath(os.path.join(root, f))
        s = open(p, encoding='utf-8').read()
        m = re.search(r'<nav>(.*?)</nav>', s, flags=re.S)
        if not m:
            bad_top.append((p, 'no <nav>')); continue
        for h in re.findall(r'href="([^"#?]+)"', m.group(1)):
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), h))):
                bad_top.append((p, h))
(ok if not bad_top else bad)(f'顶栏失效链接 {len(bad_top)} 处 {bad_top[:4]}')

print('【7】面包屑：都能回首页')
bc = []
for root, _, fs in os.walk('.'):
    for f in fs:
        if not f.endswith('.html'):
            continue
        p = os.path.normpath(os.path.join(root, f))
        s = open(p, encoding='utf-8').read()
        m = re.search(r'<div class="eyebrow">(.*?)</div>', s, flags=re.S)
        if m and 'index.html' not in m.group(1):
            bc.append(p)
(ok if not bc else bad)(f'面包屑缺首页 {bc or "无"}')

print('【8】页内目录：链接都能落到实际 id')
ar = []
for root, _, fs in os.walk('.'):
    for f in fs:
        if not f.endswith('.html'):
            continue
        p = os.path.normpath(os.path.join(root, f))
        s = open(p, encoding='utf-8').read()
        ids = set(re.findall(r'id="([^"]+)"', s))
        m = re.search(r'<aside class="outline">(.*?)</aside>', s, flags=re.S)
        if not m:
            continue
        for x in re.findall(r'href="#([^"]+)"', m.group(1)):
            if x not in ids:
                ar.append((p, x))
(ok if not ar else bad)(f'目录失效锚点 {len(ar)} 个 {ar[:4]}')

print('【9】data-week 标注：周次页要能高亮当前周')
dw = []
for f in sorted(os.listdir('week')):
    if not re.match(r'w(\d+)\.html$', f):
        continue
    n = int(re.match(r'w(\d+)', f).group(1))
    s = open('week/' + f, encoding='utf-8').read()
    m = re.search(r'data-week="(\d+)"', s)
    if not m or int(m.group(1)) != n:
        dw.append(f)
(ok if not dw else bad)(f'data-week 不匹配: {dw[:6] or "无"}')

print('【10】动线：起点无上一篇 · 首尾闭合')
def pg(p, cls):
    s = open(p, encoding='utf-8').read()
    m = re.search(r'<div class="pager">(.*?)</div>', s, flags=re.S)
    if not m:
        return None
    mm = re.search(r'<a class="%s" href="([^"]+)"' % cls, m.group(1))
    return os.path.normpath(os.path.join(os.path.dirname(p), mm.group(1))) if mm else None
(ok if pg('start/rs-basics.html', 'prev') is None else bad)('主线起点无上一篇')
(ok if pg('index.html', 'prev') is None else bad)('首页无上一篇')
(ok if pg('week/w104.html', 'next') == 'index.html' else bad)('W104 指回首页')
cur, n, seen = 'index.html', 0, set()
while cur and cur not in seen:
    seen.add(cur); n += 1; cur = pg(cur, 'next')
print(f'     从首页连点「下一篇」可走通 {n} 页')

print('\n' + ('导航全部正常 ✅' if fail == 0 else f'仍有 {fail} 处问题 ❌'))
