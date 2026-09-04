#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重建全站「上一篇 / 下一篇」，并做一致性核对。

站点其实有两条动线，之前我错误地把它们混成了一条：
  链A 主线（学习）：M0 → W1…W104 →（末尾回首页）
  链B 参考（工具）：使用指南 → … → 缓冲说明 →（末尾回首页）
详注版页面必须插进链A 对应周次之后，而不是另起一条平行链。
"""
import os
import re
import json
import html

SITE = '/home/claude/hb'
os.chdir(SITE)

# 详注版页面挂在哪一周之后
AFTER_WEEK = {
    1:  ['w1-d1-full.html', 'w1-d1-mmrotate.html', 'w1-d2-full.html', 'w1-d3-d7-full.html'],
    2:  ['w2-d8-full.html', 'w2-baseline.html', 'w2-d10-d14-full.html'],
    3:  ['w3-full.html'],
    4:  ['w4-full.html'],
    5:  ['w5-full.html'],
    6:  ['w6-w8-full.html'],
    9:  ['m3-full.html'],
    13: ['m4-full.html'],
    17: ['stage2-full.html'],
    29: ['stage2b-full.html'],
}

TITLE = {
    'index.html': '首页',
    'guide.html': '使用指南',
    'three-handbooks.html': '三本手册的关系',
    'standard.html': '详注版标准',
    'audit.html': '全书体检报告',
    'self-rescue.html': '通用自救手册',
    'resources-master.html': '全书资源总表',
    'glossary.html': '全书术语表',
    'calendar.html': '进度地图',
    'log.html': '学习日志',
    'errata.html': '勘误与更新',
    'buffer.html': '缓冲与调整',
    'start/rs-basics.html': 'M0 遥感基础知识入门',
    'start/rs-basics-deep.html': 'M0 补充 · 遥感名词逐个讲透',
    'start/cv-concepts.html': 'M0 补充 · 检测与训练核心概念',
    'start/learning-resources.html': 'M0 补充 · 学习资料地图',
    'start/prerequisites.html': 'M0 必备前置知识',
    'week/w1-d1-full.html': 'W1-D1 详注版',
    'week/w1-d1-mmrotate.html': 'W1-D1 晚上 · MMRotate 实操',
    'week/w1-d2-full.html': 'W1-D2 详注版 · 论文导读',
    'week/w1-d3-d7-full.html': 'W1-D3~D7 详注版',
    'week/w2-d8-full.html': 'W2-D8 详注版',
    'week/w2-baseline.html': 'W2 · DOTA baseline 实操',
    'week/w2-d10-d14-full.html': 'W2-D10~D14 详注版',
    'week/w3-full.html': 'W3 详注版 · SAR',
    'week/w4-full.html': 'W4 详注版 · 含附录 E',
    'week/w5-full.html': 'W5 详注版',
    'week/w6-w8-full.html': 'W6–W8 详注版 · 方向决策',
    'week/m3-full.html': 'M3 详注版（W9–W12）',
    'week/m4-full.html': 'M4 详注版（W13–W16）',
    'week/stage2-full.html': '阶段二详注版（W17–W27）',
    'week/stage2b-full.html': 'M8+连接期详注版（W29–W48）',
}

# 周次页标题从 nav-data 取
nav = json.loads(open('assets/nav-data.js', encoding='utf-8')
                 .read()[len('window.NAV='):].rstrip().rstrip(';'))
for w in nav['weeks']:
    p = f"week/w{w['w']}.html"
    if os.path.exists(p):
        TITLE[p] = f"W{w['w']} " + (w.get('short') or w['title']).split('——')[0].strip()[:22]

# ── 链A：主线 ──────────────────────────────────────────────
MAIN = ['start/rs-basics.html', 'start/rs-basics-deep.html',
        'start/cv-concepts.html', 'start/learning-resources.html',
        'start/prerequisites.html']
for w in sorted(int(re.match(r'w(\d+)\.html', f).group(1))
                for f in os.listdir('week') if re.match(r'w\d+\.html$', f)):
    MAIN.append(f'week/w{w}.html')
    for extra in AFTER_WEEK.get(w, []):
        MAIN.append('week/' + extra)

# ── 链B：参考 ──────────────────────────────────────────────
REF = ['guide.html', 'three-handbooks.html', 'standard.html', 'audit.html',
       'self-rescue.html', 'resources-master.html', 'glossary.html',
       'calendar.html', 'log.html', 'errata.html', 'buffer.html']

A = ('<a class="{cls}" href="{href}"><span class="dir">{dir}</span>'
     '<span class="nm">{nm}</span></a>')


def rel(frm, to):
    return os.path.relpath(to, os.path.dirname(frm) or '.').replace(os.sep, '/')


def strip_pager(s):
    return re.sub(r'\n?\s*<div class="pager">.*?</div>\s*\n?', '\n', s, flags=re.S)


def write_pager(path, prev, nxt, prev_label='← 上一篇', next_label='下一篇 →'):
    s = strip_pager(open(path, encoding='utf-8').read())
    parts = []
    if prev:
        parts.append(A.format(cls='prev', href=rel(path, prev), dir=prev_label,
                              nm=html.escape(TITLE.get(prev, prev))))
    if nxt:
        parts.append(A.format(cls='next', href=rel(path, nxt), dir=next_label,
                              nm=html.escape(TITLE.get(nxt, nxt))))
    if not parts:
        open(path, 'w', encoding='utf-8').write(s)
        return
    pager = '<div class="pager">' + ''.join(parts) + '</div>\n'
    m = re.search(r'(\n?\s*</div>\s*\n\s*</main>)', s) or re.search(r'(\s*</main>)', s)
    s = s[:m.start()] + '\n' + pager + s[m.start():]
    open(path, 'w', encoding='utf-8').write(s)


# 先清掉所有旧 pager（含 search.html 之外的每一页）
for root, _, fs in os.walk('.'):
    for f in fs:
        if f.endswith('.html'):
            p = os.path.normpath(os.path.join(root, f))
            t = open(p, encoding='utf-8').read()
            if '<div class="pager">' in t:
                open(p, 'w', encoding='utf-8').write(strip_pager(t))

# 链A
for i, p in enumerate(MAIN):
    prev = MAIN[i - 1] if i > 0 else None            # ★ 首页起点无上一篇
    nxt = MAIN[i + 1] if i < len(MAIN) - 1 else 'index.html'
    write_pager(p, prev, nxt,
                next_label='下一篇 →' if i < len(MAIN) - 1 else '全部读完 →')

# 链B
for i, p in enumerate(REF):
    prev = REF[i - 1] if i > 0 else None
    nxt = REF[i + 1] if i < len(REF) - 1 else 'index.html'
    write_pager(p, prev, nxt,
                next_label='下一篇 →' if i < len(REF) - 1 else '返回首页 →')

# 首页：只给「开始阅读」，没有上一篇
write_pager('index.html', None, MAIN[0], next_label='开始阅读 →')

print(f'链A 主线 {len(MAIN)} 页；链B 参考 {len(REF)} 页；首页单独处理')
json.dump({'MAIN': MAIN, 'REF': REF}, open('/tmp/chains.json', 'w'), ensure_ascii=False)
