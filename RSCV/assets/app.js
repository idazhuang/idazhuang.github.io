/* 遥感 CV 转型手册 · 站点脚本（纯本地、无外部依赖） */
(function () {
  'use strict';

  /* ---------- 安全存储：localStorage 不可用时退回内存 ---------- */
  var mem = {};
  var LS = (function () {
    try {
      var k = '__t' + Date.now();
      window.localStorage.setItem(k, '1');
      window.localStorage.removeItem(k);
      return window.localStorage;
    } catch (e) {
      return {
        getItem: function (k) { return k in mem ? mem[k] : null; },
        setItem: function (k, v) { mem[k] = String(v); },
        removeItem: function (k) { delete mem[k]; }
      };
    }
  })();
  function get(k, d) {
    try { var v = LS.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; }
  }
  function set(k, v) { try { LS.setItem(k, JSON.stringify(v)); } catch (e) {} }

  var K_PROG = 'rscv.progress.v1';
  var K_THEME = 'rscv.theme';
  var K_LAST = 'rscv.last';
  var K_NOTE = 'rscv.note.';
  var K_OPEN = 'rscv.railopen';

  var prog = get(K_PROG, {});
  function saveProg() { set(K_PROG, prog); }

  var ROOT = document.documentElement.getAttribute('data-root') || '';
  function url(p) { return ROOT + p; }

  /* ---------- 主题 ---------- */
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    var b = document.getElementById('themeBtn');
    if (b) b.textContent = t === 'dark' ? '☀' : '☾';
  }
  applyTheme(get(K_THEME, 'light'));

  /* ---------- 进度模型 ---------- */
  function slotKey(d, k) { return d + ':' + k; }
  function isSlotDone(d, k) { return !!prog[slotKey(d, k)]; }
  function setSlot(d, k, v) {
    if (v) prog[slotKey(d, k)] = 1; else delete prog[slotKey(d, k)];
    saveProg();
  }
  function dayState(d) {
    var n = 0;
    ['am', 'noon', 'pm'].forEach(function (k) { if (isSlotDone(d, k)) n++; });
    return n;
  }
  function weekState(w) {
    var wk = NAVBY[w];
    if (!wk) return { done: 0, total: 0 };
    var done = 0, total = wk.days.length * 3;
    wk.days.forEach(function (dd) { done += dayState(dd.d); });
    return { done: done, total: total };
  }
  function totalState() {
    var done = 0, total = 0;
    (window.NAV ? NAV.weeks : []).forEach(function (wk) {
      var s = weekState(wk.w); done += s.done; total += s.total;
    });
    return { done: done, total: total };
  }

  var NAVBY = {};
  if (window.NAV) NAV.weeks.forEach(function (w) { NAVBY[w.w] = w; });

  /* ---------- 侧栏导航树 ---------- */
  function buildRail() {
    var rail = document.getElementById('rail');
    if (!rail || !window.NAV) return;
    var curW = parseInt(document.documentElement.getAttribute('data-week') || '0', 10);
    var html = ['<div class="rail-head">课程目录</div>'];
    html.push('<a class="wk-link" href="' + url('index.html') + '" style="padding-left:14px"><span class="wid">HOME</span><span class="wtx">总览首页</span></a>');
    html.push('<a class="wk-link" href="' + url('start/rs-basics.html') + '" style="padding-left:14px"><span class="wid">M0</span><span class="wtx">遥感基础知识入门</span></a>');
    html.push('<a class="wk-link" href="' + url('start/prerequisites.html') + '" style="padding-left:14px"><span class="wid">M0</span><span class="wtx">必备前置知识</span></a>');
    html.push('<a class="wk-link" href="' + url('start/rs-basics-deep.html') + '" style="padding-left:14px"><span class="wid">补</span><span class="wtx">遥感名词逐个讲透</span></a>');
    html.push('<a class="wk-link" href="' + url('start/cv-concepts.html') + '" style="padding-left:14px"><span class="wid">补</span><span class="wtx">检测与训练概念详解</span></a>');
    html.push('<a class="wk-link" href="' + url('start/learning-resources.html') + '" style="padding-left:14px"><span class="wid">补</span><span class="wtx">学习资料地图</span></a>');
    html.push('<a class="wk-link" href="' + url('resources-master.html') + '" style="padding-left:14px"><span class="wid">源</span><span class="wtx">全书资源总表</span></a>');
    html.push('<a class="wk-link" href="' + url('standard.html') + '" style="padding-left:14px"><span class="wid">标</span><span class="wtx">详注版标准</span></a>');
    html.push('<a class="wk-link" href="' + url('audit.html') + '" style="padding-left:14px"><span class="wid">检</span><span class="wtx">全书体检报告</span></a>');
    html.push('<a class="wk-link" href="' + url('self-rescue.html') + '" style="padding-left:14px"><span class="wid">救</span><span class="wtx">通用自救手册</span></a>');
    html.push('<a class="wk-link" href="' + url('start/cv-concepts.html') + '" style="padding-left:14px"><span class="wid">基</span><span class="wtx">检测与训练概念详解</span></a>');
    html.push('<a class="wk-link" href="' + url('self-rescue.html') + '" style="padding-left:14px"><span class="wid">救</span><span class="wtx">通用自救手册（6 招）</span></a>');
    html.push('<a class="wk-link" href="' + url('start/learning-resources.html') + '" style="padding-left:14px"><span class="wid">补</span><span class="wtx">学习资料地图</span></a>');

    NAV.stages.forEach(function (st) {
      var mods = NAV.modules.filter(function (m) { return m.stage === st.id; });
      var open = mods.some(function (m) {
        return NAV.weeks.some(function (w) { return w.m === m.m && w.w === curW; });
      });
      html.push('<div class="stage-block' + (open ? ' open' : '') + '" data-stage="' + st.id + '">');
      html.push('<button class="stage-head" type="button"><span class="caret">▶</span>' +
        '<span class="dot" style="background:var(--b' + st.id + ')"></span>' +
        '<span class="nm">' + st.roman + ' · ' + st.name + '</span>' +
        '<span class="rng">M' + st.modules[0] + '–M' + st.modules[1] + '</span></button>');
      html.push('<div class="stage-body">');
      mods.forEach(function (m) {
        var wks = NAV.weeks.filter(function (w) { return w.m === m.m; });
        var mopen = wks.some(function (w) { return w.w === curW; });
        html.push('<div class="mod-block' + (mopen ? ' open' : '') + '">');
        html.push('<button class="mod-head" type="button"><span class="mid">M' + m.m + '</span>' + m.title + '</button>');
        html.push('<div class="mod-body">');
        wks.forEach(function (w) {
          html.push('<a class="wk-link' + (w.w === curW ? ' cur' : '') + '" data-w="' + w.w + '" href="' + url(w.href) + '">' +
            '<span class="tick">○</span><span class="wid">W' + w.w + '</span>' +
            '<span class="wtx">' + esc(w.short || w.title) + '</span></a>');
          if (w.w === 1) {
            html.push('<a class="wk-link" href="' + url('week/w1-d1-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D1 详注版（上午+中午）</span></a>');
            html.push('<a class="wk-link" href="' + url('week/w1-d1-mmrotate.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D1 晚上 · MMRotate 实操</span></a>');
            html.push('<a class="wk-link" href="' + url('week/w1-d2-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D2 详注版 · 论文导读</span></a>');
            html.push('<a class="wk-link" href="' + url('week/w1-d3-d7-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D3–D7 详注版</span></a>');
          }
          if (w.w >= 29 && w.w <= 48) {
            html.push('<a class="wk-link" href="' + url('week/stage2b-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">M8+连接期 · 含附录D</span></a>');
          }
          if (w.w >= 17 && w.w <= 27) {
            html.push('<a class="wk-link" href="' + url('week/stage2-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">阶段二详注版 · 实验+投稿</span></a>');
          }
          if (w.w >= 13 && w.w <= 16) {
            html.push('<a class="wk-link" href="' + url('week/m4-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">M4 详注版 · 论文排版</span></a>');
          }
          if (w.w >= 9 && w.w <= 12) {
            html.push('<a class="wk-link" href="' + url('week/m3-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">M3 详注版 · 显著性判定</span></a>');
          }
          if (w.w === 5) {
            html.push('<a class="wk-link" href="' + url('week/w5-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">W5 详注版 · 变化检测+分割</span></a>');
          }
          if (w.w === 6) {
            html.push('<a class="wk-link" href="' + url('week/w6-w8-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">W6–W8 详注版 · 方向决策</span></a>');
          }
          if (w.w === 4) {
            html.push('<a class="wk-link" href="' + url('week/w4-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">W4 详注版 · 含附录E</span></a>');
          }
          if (w.w === 3) {
            html.push('<a class="wk-link" href="' + url('week/w3-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">W3 详注版 · SAR + 格式转换</span></a>');
          }
          if (w.w === 2) {
            html.push('<a class="wk-link" href="' + url('week/w2-d8-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D8 详注版 · 论文+config</span></a>');
            html.push('<a class="wk-link" href="' + url('week/w2-baseline.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">补</span><span class="wtx">D9/D11 · baseline 实操</span></a>');
            html.push('<a class="wk-link" href="' + url('week/w2-d10-d14-full.html') + '" style="padding-left:34px">' +
              '<span class="tick">·</span><span class="wid">详</span><span class="wtx">D10–D14 详注版</span></a>');
          }
        });
        if (m.buffer) {
          m.buffer.forEach(function (bw) {
            html.push('<a class="wk-link" href="' + url('buffer.html') + '" style="opacity:.55">' +
              '<span class="tick">·</span><span class="wid">W' + bw + '</span><span class="wtx">缓冲周（并入相邻周）</span></a>');
          });
        }
        html.push('</div></div>');
      });
      html.push('</div></div>');
    });
    html.push('<div class="rail-head" style="padding-top:14px">附录</div>');
    [['calendar.html', '104 周进度地图'], ['glossary.html', '术语表'],
     ['buffer.html', '缓冲周怎么用'], ['three-handbooks.html', '三套手册怎么配'],
     ['errata.html', '校订说明'], ['guide.html', '使用指南'],
     ['log.html', '编写接力记录']].forEach(function (x) {
      html.push('<a class="wk-link" href="' + url(x[0]) + '" style="padding-left:14px"><span class="wid">·</span><span class="wtx">' + x[1] + '</span></a>');
    });
    rail.innerHTML = html.join('');

    rail.addEventListener('click', function (e) {
      var sh = e.target.closest('.stage-head');
      if (sh) { sh.parentNode.classList.toggle('open'); return; }
      var mh = e.target.closest('.mod-head');
      if (mh) { mh.parentNode.classList.toggle('open'); }
    });
    refreshRailTicks();
    var cur = rail.querySelector('.wk-link.cur');
    if (cur) {
      var t = cur.offsetTop - rail.clientHeight / 2;
      if (t > 0) rail.scrollTop = t;
    }
  }

  function refreshRailTicks() {
    var rail = document.getElementById('rail');
    if (!rail) return;
    Array.prototype.forEach.call(rail.querySelectorAll('.wk-link[data-w]'), function (a) {
      var s = weekState(parseInt(a.getAttribute('data-w'), 10));
      a.classList.remove('done', 'part');
      var t = a.querySelector('.tick');
      if (s.total && s.done >= s.total) { a.classList.add('done'); t.textContent = '●'; }
      else if (s.done > 0) { a.classList.add('part'); t.textContent = '◐'; }
      else { t.textContent = '○'; }
    });
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ---------- 周页面：勾选、折叠、大纲 ---------- */
  function initWeek() {
    var main = document.querySelector('[data-page="week"]');
    if (!main) return;

    Array.prototype.forEach.call(document.querySelectorAll('.slot'), function (sl) {
      var d = sl.getAttribute('data-d'), k = sl.getAttribute('data-k');
      var cb = sl.querySelector('.chk');
      if (!cb) return;
      cb.checked = isSlotDone(d, k);
      sl.classList.toggle('done', cb.checked);
      cb.addEventListener('change', function () {
        setSlot(d, k, cb.checked);
        sl.classList.toggle('done', cb.checked);
        syncDay(d);
        refreshRailTicks();
        paintSwath();
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.day'), function (day) {
      syncDay(day.getAttribute('data-d'));
      var head = day.querySelector('.day-head');
      head.addEventListener('click', function (e) {
        if (e.target.closest('a') || e.target.closest('.chk')) return;
        day.classList.toggle('collapsed');
      });
    });

    Array.prototype.forEach.call(document.querySelectorAll('.notes textarea'), function (ta) {
      var id = ta.getAttribute('data-note');
      ta.value = get(K_NOTE + id, '') || '';
      var t;
      ta.addEventListener('input', function () {
        clearTimeout(t);
        t = setTimeout(function () { set(K_NOTE + id, ta.value); }, 350);
      });
    });

    paintSwath();
    initOutline();
    var w = document.documentElement.getAttribute('data-week');
    set(K_LAST, { href: location.pathname.split('/').slice(-2).join('/'), w: w, t: Date.now() });
  }

  function syncDay(d) {
    var day = document.querySelector('.day[data-d="' + d + '"]');
    if (!day) return;
    var n = dayState(d);
    day.classList.toggle('done', n === 3);
    var m = day.querySelector('.day-meta .prog');
    if (m) m.textContent = n + '/3';
  }

  function paintSwath() {
    Array.prototype.forEach.call(document.querySelectorAll('.swath i'), function (i) {
      var d = i.getAttribute('data-d'), k = i.getAttribute('data-k');
      i.classList.toggle('on', isSlotDone(d, k));
    });
  }

  /* ---------- 大纲滚动高亮 + 阅读进度 ---------- */
  function initOutline() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.outline a[href^="#"]'));
    if (!links.length) return;
    var targets = links.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    function onScroll() {
      var y = window.scrollY + 120, cur = 0;
      for (var i = 0; i < targets.length; i++) {
        if (targets[i] && targets[i].offsetTop <= y) cur = i;
      }
      links.forEach(function (a, i) { a.classList.toggle('cur', i === cur); });
      var bar = document.querySelector('.readbar i');
      if (bar) {
        var h = document.body.scrollHeight - window.innerHeight;
        bar.style.width = (h > 0 ? Math.min(100, window.scrollY / h * 100) : 0) + '%';
      }
    }
    var tick = false;
    window.addEventListener('scroll', function () {
      if (tick) return; tick = true;
      requestAnimationFrame(function () { onScroll(); tick = false; });
    }, { passive: true });
    onScroll();
  }

  /* ---------- 复制代码 ---------- */
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.copy');
    if (!b) return;
    var code = b.parentNode.querySelector('code');
    var txt = code ? code.innerText : '';
    var ok = function () { b.textContent = '已复制'; setTimeout(function () { b.textContent = '复制'; }, 1400); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(ok, fallback);
    } else { fallback(); }
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = txt; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); ok(); } catch (err) { b.textContent = '请手动复制'; }
      document.body.removeChild(ta);
    }
  });

  /* ---------- 顶栏：主题 / 侧栏 / 搜索 ---------- */
  function initChrome() {
    var tb = document.getElementById('themeBtn');
    if (tb) tb.addEventListener('click', function () {
      var t = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      set(K_THEME, t); applyTheme(t);
    });
    var rt = document.getElementById('railBtn');
    if (rt) rt.addEventListener('click', function () { document.body.classList.toggle('rail-open'); });
    document.addEventListener('click', function (e) {
      if (window.innerWidth > 1000) return;
      if (!document.body.classList.contains('rail-open')) return;
      if (e.target.closest('#rail') || e.target.closest('#railBtn')) return;
      document.body.classList.remove('rail-open');
    });

    var inp = document.getElementById('q');
    if (inp) {
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && inp.value.trim()) {
          location.href = url('search.html?q=') + encodeURIComponent(inp.value.trim());
        }
      });
    }
    document.addEventListener('keydown', function (e) {
      if (e.target.matches('input, textarea')) {
        if (e.key === 'Escape') e.target.blur();
        return;
      }
      if (e.key === '/') { e.preventDefault(); if (inp) inp.focus(); }
      if (e.key === 'ArrowLeft') { var p = document.querySelector('.pager a.prev'); if (p) location.href = p.href; }
      if (e.key === 'ArrowRight') { var n = document.querySelector('.pager a.next'); if (n) location.href = n.href; }
    });
  }

  /* ---------- 首页 / 日历：成像扫描图 ---------- */
  function paintRaster() {
    var r = document.querySelector('.raster');
    if (!r) return;
    Array.prototype.forEach.call(r.querySelectorAll('i[data-d]'), function (i) {
      var d = i.getAttribute('data-d');
      var n = dayState(d);
      i.classList.toggle('lit', n > 0);
      i.style.opacity = n === 0 ? '' : (0.45 + 0.185 * n);
    });
    var t = totalState();
    var pct = t.total ? Math.round(t.done / t.total * 100) : 0;
    Array.prototype.forEach.call(document.querySelectorAll('[data-kpi="pct"]'), function (e) { e.textContent = pct + '%'; });
    Array.prototype.forEach.call(document.querySelectorAll('[data-kpi="slots"]'), function (e) { e.textContent = t.done; });
    Array.prototype.forEach.call(document.querySelectorAll('[data-kpi="days"]'), function (e) {
      var n = 0;
      (window.NAV ? NAV.weeks : []).forEach(function (w) {
        w.days.forEach(function (dd) { if (dayState(dd.d) === 3) n++; });
      });
      e.textContent = n;
    });
    Array.prototype.forEach.call(document.querySelectorAll('.progress-line i'), function (e) { e.style.width = pct + '%'; });
  }

  /* ---------- 进度导入 / 导出 / 清空 ---------- */
  function initTools() {
    var ex = document.getElementById('exportBtn');
    if (ex) ex.addEventListener('click', function () {
      var data = { progress: prog, notes: {}, exported: new Date().toISOString() };
      for (var i = 0; i < 999; i++) {
        try {
          var k = LS.key ? LS.key(i) : null;
          if (!k) break;
          if (k.indexOf(K_NOTE) === 0) data.notes[k.slice(K_NOTE.length)] = JSON.parse(LS.getItem(k));
        } catch (e) { break; }
      }
      var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'rscv-progress-' + new Date().toISOString().slice(0, 10) + '.json';
      a.click();
    });
    var imp = document.getElementById('importFile');
    if (imp) imp.addEventListener('change', function () {
      var f = imp.files[0]; if (!f) return;
      var fr = new FileReader();
      fr.onload = function () {
        try {
          var d = JSON.parse(fr.result);
          if (d.progress) { prog = d.progress; saveProg(); }
          if (d.notes) Object.keys(d.notes).forEach(function (k) { set(K_NOTE + k, d.notes[k]); });
          location.reload();
        } catch (e) { alert('这个文件读不出来，请选择本站导出的 JSON。'); }
      };
      fr.readAsText(f);
    });
    var cl = document.getElementById('clearBtn');
    if (cl) cl.addEventListener('click', function () {
      if (!confirm('清空所有勾选与笔记？此操作不可撤销。')) return;
      prog = {}; saveProg();
      try {
        var ks = [];
        for (var i = 0; i < LS.length; i++) { var k = LS.key(i); if (k && k.indexOf(K_NOTE) === 0) ks.push(k); }
        ks.forEach(function (k) { LS.removeItem(k); });
      } catch (e) {}
      location.reload();
    });
    var cont = document.getElementById('continueBtn');
    if (cont) {
      var last = get(K_LAST, null);
      if (last && last.w) {
        cont.href = url('week/w' + last.w + '.html');
        cont.textContent = '继续学习 · 第 ' + last.w + ' 周';
        cont.style.display = '';
      }
    }
  }

  /* ---------- 搜索 ---------- */
  function initSearch() {
    var box = document.getElementById('results');
    if (!box) return;
    var input = document.getElementById('sq');
    var q = '';
    try { q = new URLSearchParams(location.search).get('q') || ''; } catch (e) {}
    if (!q && location.hash.indexOf('q=') === 1) {
      try { q = decodeURIComponent(location.hash.slice(3)); } catch (e) {}
    }
    if (input) input.value = q;
    var loaded = false;

    function load(cb) {
      if (loaded) { cb(); return; }
      box.innerHTML = '<p style="color:var(--text-3)">正在载入全文索引（约 8 MB，仅首次）…</p>';
      var s = document.createElement('script');
      s.src = url('assets/search-index.js');
      s.onload = function () { loaded = true; cb(); };
      s.onerror = function () { box.innerHTML = '<p>索引文件没能载入。请确认 assets/search-index.js 与页面在同一个文件夹里。</p>'; };
      document.head.appendChild(s);
    }

    function run() {
      var kw = (input ? input.value : q).trim();
      if (!kw) { box.innerHTML = '<p style="color:var(--text-3)">输入关键词开始检索，例如：<code>wandb</code>、<code>冷邮件</code>、<code>消融</code>、<code>SAR</code>。</p>'; return; }
      load(function () {
        var idx = window.SEARCH_INDEX || [];
        var terms = kw.toLowerCase().split(/\s+/).filter(Boolean);
        var hits = [];
        for (var i = 0; i < idx.length; i++) {
          var it = idx[i];
          var hay = (it.t + ' ' + it.x).toLowerCase();
          var score = 0, ok = true;
          for (var j = 0; j < terms.length; j++) {
            var p = hay.indexOf(terms[j]);
            if (p < 0) { ok = false; break; }
            score += (it.t.toLowerCase().indexOf(terms[j]) >= 0 ? 12 : 1);
            score += Math.max(0, 6 - p / 400);
          }
          if (ok) hits.push({ it: it, s: score });
        }
        hits.sort(function (a, b) { return b.s - a.s; });
        var total = hits.length;
        hits = hits.slice(0, 120);
        if (!total) { box.innerHTML = '<p>没有找到「' + esc(kw) + '」。换个词试试，或用更短的关键词。</p>'; return; }
        var out = ['<p style="color:var(--text-3);font-size:13px">命中 ' + total + ' 处' + (total > 120 ? '，显示前 120 处' : '') + '</p>'];
        hits.forEach(function (h) {
          var it = h.it;
          out.push('<div class="hit"><div class="hp">' + esc(it.p) + '</div>' +
            '<h3><a href="' + url(it.u) + '">' + mark(esc(it.t), terms) + '</a></h3>' +
            '<p>' + snippet(it.x, terms) + '</p></div>');
        });
        box.innerHTML = out.join('');
      });
    }

    function mark(s, terms) {
      terms.forEach(function (t) {
        s = s.replace(new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'), '<mark>$1</mark>');
      });
      return s;
    }
    function snippet(x, terms) {
      var low = x.toLowerCase(), p = -1;
      for (var i = 0; i < terms.length; i++) { p = low.indexOf(terms[i]); if (p >= 0) break; }
      if (p < 0) p = 0;
      var st = Math.max(0, p - 60);
      var s = (st ? '…' : '') + x.slice(st, st + 220) + (x.length > st + 220 ? '…' : '');
      return mark(esc(s), terms);
    }

    if (input) {
      var t;
      input.addEventListener('input', function () { clearTimeout(t); t = setTimeout(run, 220); });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
    }
    run();
  }

  /* ---------- 启动 ---------- */
  function boot() {
    buildRail();
    initChrome();
    initWeek();
    paintRaster();
    initTools();
    initSearch();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
