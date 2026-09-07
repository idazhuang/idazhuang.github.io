#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把详注内容并回原文——不另起标题块，而是按 ①–⑥ 续写进原有的六块里。

上一版两个 bug：
  1. split 后 ''.join(行) 把换行丢了 → markdown 没被解析 → 整段挤成一坨
  2. 额外包了一层"详注 · xxx"标题块，用户要的是"哪缺了就在哪补"
"""
import os
import re
import html
import json
import markdown as md

SITE = '/home/claude/v3'
MD = os.path.join(SITE, 'source-md')
os.chdir(SITE)

PLAN = [
    ('补充08-W1D1详注版.md', 'week/w1.html', 1, 'am'),
    ('补充01-W1D1晚上段-MMRotate保姆级实操.md', 'week/w1.html', 1, 'pm'),
    ('补充10-W1D2详注版.md', 'week/w1.html', 2, 'am'),
    ('补充11-W1D3至D7详注版.md', 'week/w1.html', 3, 'am'),
    ('补充12-W2D8详注版.md', 'week/w2.html', 8, 'am'),
    ('补充04-W2-DOTA-baseline保姆级实操.md', 'week/w2.html', 9, 'noon'),
    ('补充13-W2D10至D14详注版.md', 'week/w2.html', 10, 'am'),
    ('补充14-W3详注版.md', 'week/w3.html', 15, 'am'),
    ('补充15-W4详注版.md', 'week/w4.html', 22, 'am'),
    ('补充16-W5详注版.md', 'week/w5.html', 29, 'am'),
    ('补充17-W6至W8详注版.md', 'week/w6.html', 36, 'am'),
    ('补充18-M3详注版.md', 'week/w9.html', 57, 'am'),
    ('补充19-M4详注版.md', 'week/w13.html', 85, 'am'),
    ('补充20-阶段二详注版.md', 'week/w17.html', 113, 'am'),
    ('补充21-M8与连接期详注版.md', 'week/w29.html', 190, 'am'),
    ('补充02-遥感基础名词逐个讲透.md', 'start/rs-basics.html', None, None),
    ('补充03-学习资料地图.md', 'start/rs-basics.html', None, None),
    ('补充06-检测与训练核心概念详解.md', 'start/prerequisites.html', None, None),
]
SLOT_KEY = {'上午段': 'am', '中午段': 'noon', '晚上段': 'pm'}
# 详注里的 ①–⑥ → 原文对应的块
CIRCLE = {'①': 'blk-concept', '②': 'blk-do', '③': 'blk-check',
          '④': 'blk-pit', '⑤': 'blk-rescue', '⑥': 'blk-gain'}

DAY2PAGE, DAY_SLOTS, SLOT_TITLE = {}, {}, {}
for f in os.listdir('week'):
    if not re.match(r'w\d+\.html$', f):
        continue
    p = 'week/' + f
    t = open(p, encoding='utf-8').read()
    for m in re.finditer(r'<section class="slot" id="d(\d+)-(am|noon|pm)".*?'
                         r'<h3 class="slot-t">(.*?)</h3>', t, flags=re.S):
        d, k = int(m.group(1)), m.group(2)
        DAY2PAGE[d] = p
        DAY_SLOTS.setdefault(d, set()).add(k)
        SLOT_TITLE[(d, k)] = re.sub(r'<[^>]+>', '', m.group(3))


def smart_quotes(t):
    parts = re.split(r'(```.*?```|`[^`\n]*`)', t, flags=re.S)
    for i in range(0, len(parts), 2):
        out, op = [], True
        for ch in parts[i]:
            if ch == '"':
                out.append('\u201c' if op else '\u201d'); op = not op
            else:
                out.append(ch)
        parts[i] = ''.join(out)
    return ''.join(parts)


def to_html(text, idbase):
    """★ text 必须保留换行，否则 markdown 解析不出标题/列表/表格。"""
    h = md.markdown(smart_quotes(text.strip()),
                    extensions=['tables', 'fenced_code', 'sane_lists'])
    h = h.replace('<table>', '<div class="table-wrap"><table>') \
         .replace('</table>', '</table></div>')

    def code(m):
        lang = 'text'
        lm = re.search(r'class="language-([^"]+)"', m.group(1) or '')
        if lm:
            lang = lm.group(1)
        return ('<figure class="code" data-lang="%s"><pre><code>%s</code></pre>'
                '<button class="copy" type="button" aria-label="复制代码">复制</button>'
                '</figure>' % (lang, m.group(2)))
    h = re.sub(r'<pre><code([^>]*)>(.*?)</code></pre>', code, h, flags=re.S)
    h = h.replace('<blockquote>', '<blockquote class="quote">')
    n = [0]

    def head(m):
        n[0] += 1
        lv = min(int(m.group(1)) + 4, 6)     # 降级，避免和原文 h3/h4 抢层级
        return '<h%d id="%s-%d">%s</h%d>' % (lv, idbase, n[0], m.group(2), lv)
    return re.sub(r'<h([123])>(.*?)</h\1>', head, h, flags=re.S)


def split_chunks(text):
    """按 D 天号 / 时段 切块。★ 用 '\\n'.join 保留换行。"""
    out, day, slot, buf = [], None, None, []

    def flush():
        body = '\n'.join(buf)
        if body.strip():
            out.append((day, slot, body))
    for line in text.split('\n'):
        dm = re.match(r'^#{1,3}\s*(?:第[一二三四五六七八九十]+部分\s*·\s*)?.*?\bD(\d+)\b', line)
        sm = re.match(r'^#{1,4}\s*(?:[\d.]+\s*)?(?:★\s*)?(上午段|中午段|晚上段)', line)
        if dm or sm:
            flush(); buf = []
            if dm:
                day = int(dm.group(1))
                if not sm:
                    slot = None
            if sm:
                slot = SLOT_KEY[sm.group(1)]
                d2 = re.search(r'\bD(\d+)\b', line)
                if d2:
                    day = int(d2.group(1))
        buf.append(line)
    flush()
    return out


def split_by_circle(body):
    """把一段详注按 ①②③④⑤⑥ 再拆开，返回 {blkclass: 文本} + 无标记的剩余。"""
    parts, cur, buf = {}, None, []

    def flush():
        b = '\n'.join(buf)
        if b.strip():
            parts.setdefault(cur, []).append(b)
    for line in body.split('\n'):
        m = re.match(r'^#{1,4}\s*([①②③④⑤⑥])', line)
        if m:
            flush(); buf = []
            cur = CIRCLE[m.group(1)]
        buf.append(line)
    flush()
    return {k: '\n'.join(v) for k, v in parts.items()}


def pick_slot(day, text):
    cand = [k for k in ('am', 'noon', 'pm') if k in DAY_SLOTS.get(day, ())]
    if not cand:
        return None
    probe = re.sub(r'[\s#*`>|-]', '', text[:400])
    best, sc = cand[0], -1
    for k in cand:
        t = re.sub(r'[\s#*`>|-]', '', SLOT_TITLE.get((day, k), ''))
        g = {t[i:i + 2] for i in range(len(t) - 1)}
        v = sum(1 for x in g if x in probe)
        if v > sc:
            best, sc = k, v
    return best


def slot_span(page, sid):
    m = re.search(r'<section class="slot" id="%s"' % re.escape(sid), page)
    if not m:
        return None
    st = m.start()
    nx = page.find('<section class="slot"', st + 10)
    if nx < 0:
        nx = page.find('<div class="pager">', st)
    if nx < 0:
        nx = len(page)
    return st, nx


def append_into_blk(page, sid, blkcls, htm):
    """把内容续写进某个 slot 的某一块正文末尾——不加任何新标题。"""
    sp = slot_span(page, sid)
    if not sp:
        return page, False
    st, en = sp
    seg = page[st:en]
    m = re.search(r'(<section class="blk %s">.*?<div class="blk-b">)(.*?)(</div></section>)'
                  % re.escape(blkcls), seg, flags=re.S)
    if not m:
        return page, False
    seg2 = seg[:m.end(2)] + htm + seg[m.end(2):]
    return page[:st] + seg2 + page[en:], True


def append_tail_of_slot(page, sid, htm):
    """没有 ①–⑥ 标记的内容：续写进该时段最后一块的正文末尾。"""
    sp = slot_span(page, sid)
    if not sp:
        return page, False
    st, en = sp
    seg = page[st:en]
    ms = list(re.finditer(r'<div class="blk-b">(.*?)</div></section>', seg, flags=re.S))
    if not ms:
        return page, False
    last = ms[-1]
    seg2 = seg[:last.end(1)] + htm + seg[last.end(1):]
    return page[:st] + seg2 + page[en:], True


def append_sec(page, body, title, sid):
    sec = f'<section class="deep-sec" id="{sid}"><h2 class="deep-h">{title}</h2>{body}</section>'
    m = re.search(r'(\n?\s*<div class="pager">)', page) or \
        re.search(r'(\n?\s*</div>\s*\n\s*</main>)', page)
    return page[:m.start()] + '\n' + sec + page[m.start():]


pages, outline_add = {}, {}
def load(p):
    if p not in pages:
        pages[p] = open(p, encoding='utf-8').read()
    return pages[p]


stat = {'blk': 0, 'tail': 0, 'sec': 0}
for fn, deft, defday, defslot in PLAN:
    path = os.path.join(MD, fn)
    if not os.path.exists(path):
        continue
    raw = re.sub(r'\A# [^\n]*\n(## [^\n]*\n)?', '', open(path, encoding='utf-8').read())
    base = re.sub(r'[^a-z0-9]', '', fn.lower())[:12]

    if not deft.startswith('week'):
        t = fn.split('-', 1)[1].replace('.md', '')
        sid = 'deep-' + base
        pages[deft] = append_sec(load(deft), to_html(raw, base), html.escape(t), sid)
        outline_add.setdefault(deft, []).append((sid, t))
        stat['sec'] += 1
        continue

    chunks = split_chunks(raw)
    for k, (day, slot, body) in enumerate(chunks):
        d = day if day in DAY2PAGE else defday
        target = DAY2PAGE.get(d, deft)
        page = load(target)
        use = slot if (slot and slot in DAY_SLOTS.get(d, ())) else \
            (pick_slot(d, body) if day is not None else defslot)
        placed = False
        if use and d in DAY_SLOTS:
            sid = f'd{d}-{use}'
            circ = split_by_circle(body)
            keyed = {kk: vv for kk, vv in circ.items() if kk}
            lead = circ.get(None, '')
            if keyed:
                if lead.strip():
                    page, okk = append_tail_of_slot(page, sid,
                                                    to_html(lead, f'{base}{k}L'))
                for blkcls, txt in keyed.items():
                    page, okk = append_into_blk(page, sid, blkcls,
                                                to_html(txt, f'{base}{k}{blkcls[-4:]}'))
                    stat['blk'] += okk
                placed = True
            else:
                page, placed = append_tail_of_slot(page, sid, to_html(body, f'{base}{k}'))
                stat['tail'] += placed
        if not placed:
            hm = re.search(r'^#{1,4}\s*(.+)$', body, flags=re.M)
            t = html.escape(re.sub(r'^[#★\s]*', '', hm.group(1) if hm else '')[:44] or '补充说明')
            sid = f'deep-{base}{k}'
            page = append_sec(page, to_html(body, f'{base}{k}'), t, sid)
            outline_add.setdefault(target, []).append((sid, t))
            stat['sec'] += 1
        pages[target] = page
    print(f'  {fn[:30]:<32} 已并入')

for p, s in pages.items():
    open(p, 'w', encoding='utf-8').write(s)
json.dump(outline_add, open('/tmp/outline_add.json', 'w'), ensure_ascii=False)
print(f"\n续写进原有六块 {stat['blk']} 处，续写到时段末尾 {stat['tail']} 处，"
      f"周级区块 {stat['sec']} 个，改动 {len(pages)} 页")
