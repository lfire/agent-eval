/* ============================================================
   code-blocks.js — 全站代码块增强（零外部依赖）
   提供：语法高亮 / 行号 / 折叠 / 一键复制 / 语言标签
   仅处理 <pre><code>；纯文本 <pre> 与 <pre class="mermaid"> 自动跳过。
   ============================================================ */
(function () {
  'use strict';

  var KEYWORDS = {
    python: ['def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'in', 'not',
      'and', 'or', 'is', 'import', 'from', 'as', 'with', 'try', 'except', 'finally',
      'raise', 'lambda', 'yield', 'async', 'await', 'pass', 'break', 'continue',
      'global', 'nonlocal', 'del', 'assert'],
    typescript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
      'class', 'extends', 'new', 'import', 'export', 'from', 'default', 'async', 'await',
      'try', 'catch', 'finally', 'throw', 'typeof', 'interface', 'type', 'enum',
      'public', 'private', 'static', 'void', 'switch', 'case', 'break', 'continue'],
    javascript: ['const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
      'class', 'extends', 'new', 'import', 'export', 'from', 'default', 'async', 'await',
      'try', 'catch', 'finally', 'throw', 'typeof', 'void', 'switch', 'case', 'break'],
    bash: ['if', 'then', 'else', 'elif', 'fi', 'for', 'do', 'done', 'case', 'esac',
      'function', 'in', 'while', 'until', 'select', 'export', 'source', 'return', 'local'],
    mermaid: ['flowchart', 'graph', 'subgraph', 'end', 'classDef', 'class', 'style',
      'sequenceDiagram', 'participant', 'stateDiagram', 'direction', 'click', 'linkStyle'],
    json: [], yaml: [], text: []
  };
  var BUILTINS = {
    python: ['True', 'False', 'None', 'self', 'print', 'len', 'range', 'str', 'int',
      'float', 'dict', 'list', 'set', 'tuple', 'open', 'super', 'object', 'Exception'],
    typescript: ['true', 'false', 'null', 'undefined', 'this', 'console'],
    javascript: ['true', 'false', 'null', 'undefined', 'this', 'console'],
    bash: ['echo', 'cd', 'set', 'exit'],
    mermaid: ['LR', 'TB', 'TD', 'RL', 'BT'],
    json: ['true', 'false', 'null'],
    yaml: ['true', 'false', 'null', 'yes', 'no'],
    text: []
  };
  var LABEL = {
    python: 'PYTHON', typescript: 'TYPESCRIPT', javascript: 'JAVASCRIPT', bash: 'BASH',
    json: 'JSON', yaml: 'YAML', mermaid: 'MERMAID', text: 'TEXT'
  };
  var ALIAS = {
    py: 'python', python3: 'python', js: 'javascript', jsx: 'javascript',
    ts: 'typescript', tsx: 'typescript', sh: 'bash', shell: 'bash', zsh: 'bash',
    console: 'bash', yml: 'yaml', mmd: 'mermaid', txt: 'text'
  };

  function esc(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function detect(code, className, pre, codeEl) {
    var m = /language-([\w+-]+)/.exec(className || '');
    var lang = m ? m[1].toLowerCase() : '';
    if (ALIAS[lang]) lang = ALIAS[lang];
    if (KEYWORDS[lang]) return lang;
    var forced = (pre && pre.getAttribute('data-lang')) ||
      (codeEl && codeEl.getAttribute('data-lang')) || '';
    if (forced) { forced = forced.toLowerCase(); return ALIAS[forced] || forced; }
    // Python 特征优先于 JSON/YAML：字典字面量与三引号字符串也属于 Python
    if (/\b(?:def|class)\s+\w+|^\s*(?:from\s+[\w.]+\s+import|import\s+\w+)|__name__|\bprint\(|=\s*\{[\s\S]*?"\w+"\s*:|"""|'''/m.test(code)) return 'python';
    if (/^\s*(?:\/\/|export\s+(?:const|function|class)|import\s+.*\bfrom\b|const\s+\w+\s*=|let\s+\w+\s*=)/m.test(code)) return 'typescript';
    if (/^\s*(?:\$\s|npm\s|pip\s|git\s|curl\s|python3?\s|openclaw\s|yarn\s|pnpm\s)/m.test(code)) return 'bash';
    if (/^\s*[{[]/.test(code) && /"\w+"\s*:/.test(code)) return 'json';
    if (/^\s*(?:flowchart|graph\s+(?:LR|TB|TD|RL|BT)|sequenceDiagram|stateDiagram)/m.test(code)) return 'mermaid';
    if (/^\s*[\w.-]+:\s*\S/m.test(code)) return 'yaml';
    return 'text';
  }

  var wordReCache = {};
  function wordRe(lang) {
    if (wordReCache[lang]) return wordReCache[lang];
    var kw = KEYWORDS[lang] || [], bi = BUILTINS[lang] || [];
    var never = '(?!)';
    var parts = [
      '(\\b\\d+(?:\\.\\d+)?\\b)',
      '(\\b(?:' + (kw.length ? kw.join('|') : never) + ')\\b)',
      '(\\b(?:' + (bi.length ? bi.join('|') : never) + ')\\b)',
      '(\\b[A-Za-z_]\\w*(?=\\())'
    ];
    wordReCache[lang] = new RegExp(parts.join('|'), 'g');
    return wordReCache[lang];
  }

  function highlightWords(buf, lang) {
    var re = wordRe(lang), out = '', last = 0, m;
    re.lastIndex = 0;
    while ((m = re.exec(buf)) !== null) {
      out += esc(buf.slice(last, m.index));
      var cls = m[1] ? 'nu' : m[2] ? 'kw' : m[3] ? 'bi' : 'fn';
      out += '<span class="tok-' + cls + '">' + esc(m[0]) + '</span>';
      last = m.index + m[0].length;
      if (m[0].length === 0) re.lastIndex++;
    }
    return out + esc(buf.slice(last));
  }

  function tokenizeLine(line, lang) {
    var i = 0, out = '', buf = '';
    function flush() { if (buf) { out += highlightWords(buf, lang); buf = ''; } }
    while (i < line.length) {
      var c = line[i];
      var isComment = false;
      if (lang === 'mermaid') isComment = (c === '%' && line[i + 1] === '%');
      else if (lang === 'python' || lang === 'bash' || lang === 'yaml') isComment = (c === '#');
      else if (lang === 'typescript' || lang === 'javascript' || lang === 'json') isComment = (c === '/' && line[i + 1] === '/');
      if (isComment) {
        flush();
        out += '<span class="tok-cm">' + esc(line.slice(i)) + '</span>';
        return out;
      }
      if (c === '"' || c === "'" || c === '`') {
        flush();
        var q = c, j = i + 1;
        while (j < line.length) {
          if (line[j] === '\\') { j += 2; continue; }
          if (line[j] === q) { j++; break; }
          j++;
        }
        out += '<span class="tok-st">' + esc(line.slice(i, j)) + '</span>';
        i = j;
        continue;
      }
      buf += c;
      i++;
    }
    flush();
    return out;
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function makeTextarea(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;left:0;top:0;width:1px;height:1px;' +
      'opacity:0.01;border:0;padding:0;z-index:-1;';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { ta.setSelectionRange(0, text.length); } catch (e) { /* noop */ }
    return ta;
  }

  function fallbackCopy(text) {
    var ta = makeTextarea(text), ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  // 最后一级兜底：剪贴板 API 均不可用时，把原文放进已选中的 textarea，
  // 用户按 Cmd/Ctrl+C 即可复制；离开焦点或 15 秒后自动清理。
  function selectForManualCopy(text) {
    var ta = makeTextarea(text);
    function cleanup() { if (ta.parentNode) ta.parentNode.removeChild(ta); }
    ta.addEventListener('blur', cleanup);
    setTimeout(cleanup, 15000);
  }

  function doCopy(text, btn) {
    function done(ok) {
      btn.textContent = ok ? '已复制 ✓' : '已选中 · 按 ⌘/Ctrl+C';
      btn.className = 'cb-btn cb-copy ' + (ok ? 'ok' : 'fail');
      if (!ok) selectForManualCopy(text);
      setTimeout(function () {
        btn.textContent = '复制';
        btn.className = 'cb-btn cb-copy';
      }, 2200);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        function () { done(true); },
        function () { done(fallbackCopy(text)); }
      );
    } else {
      done(fallbackCopy(text));
    }
  }

  function enhance(pre) {
    if (pre.getAttribute('data-cb-done')) return;
    if (pre.classList.contains('mermaid')) return;
    var code = pre.querySelector('code');
    if (!code) return;
    pre.setAttribute('data-cb-done', '1');

    var raw = code.textContent.replace(/\r\n/g, '\n').replace(/\s+$/, '');
    var lang = detect(raw, code.className, pre, code);
    var lines = raw.split('\n');
    var html = [];
    for (var i = 0; i < lines.length; i++) {
      html.push('<span class="cb-line">' + tokenizeLine(lines[i], lang) + '</span>');
    }
    code.innerHTML = html.join('');

    var inDetails = !!pre.closest('details.mermaid-src');
    var wrap = el('div', 'cb-wrap');
    wrap.setAttribute('data-lang', lang);
    var head = el('div', 'cb-head');
    head.appendChild(el('span', 'cb-lang', LABEL[lang] || lang.toUpperCase()));
    head.appendChild(el('span', 'cb-meta', lines.length + ' 行'));
    head.appendChild(el('span', 'cb-spacer'));

    var copy = el('button', 'cb-btn cb-copy', '复制');
    copy.type = 'button';
    copy.title = '复制代码到剪贴板';
    copy.setAttribute('aria-label', '复制代码');
    head.appendChild(copy);

    var toggle = null;
    if (!inDetails) {
      toggle = el('button', 'cb-btn cb-toggle', '收起');
      toggle.type = 'button';
      toggle.title = '折叠 / 展开代码块';
      toggle.setAttribute('aria-label', '折叠或展开代码块');
      toggle.setAttribute('aria-expanded', 'true');
      head.appendChild(toggle);
    }

    var body = el('div', 'cb-body');
    pre.parentNode.insertBefore(wrap, pre);
    wrap.appendChild(head);
    wrap.appendChild(body);
    body.appendChild(pre);

    copy.addEventListener('click', function () { doCopy(raw, copy); });
    if (toggle) {
      toggle.addEventListener('click', function () {
        var collapsed = wrap.classList.toggle('collapsed');
        toggle.textContent = collapsed ? '展开' : '收起';
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
      });
    }
  }

  function init() {
    var pres = document.querySelectorAll('pre');
    for (var i = 0; i < pres.length; i++) enhance(pres[i]);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
