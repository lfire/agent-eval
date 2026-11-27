/* ==========================================================================
   toc-nav.js —— 全站「目录 / 顶部导航」交互增强
   依赖：assets/toc-nav.css；图文版 index.html 与 Markdown 阅读页共用
   ========================================================================== */
(function () {
  'use strict';
  var nav = document.querySelector('nav.toc');
  var bar = document.querySelector('.topbar');
  var root = document.documentElement;

  /* 1. 顶栏高度同步：侧栏 sticky 位置与锚点偏移都依赖 --topH */
  function sync() {
    if (bar) root.style.setProperty('--topH', Math.round(bar.getBoundingClientRect().height) + 'px');
  }
  sync();
  window.addEventListener('resize', sync, { passive: true });
  window.addEventListener('load', sync);
  if (bar && window.ResizeObserver) {
    try { new ResizeObserver(sync).observe(bar); } catch (e) { /* 忽略 */ }
  }

  if (!nav) return;

  /* 2. 把 .brand / .sub（图文版）或 .h（阅读页）收进固定头部 */
  try {
    var head = document.createElement('div');
    head.className = 'nav-head';
    var headNodes = [];
    Array.prototype.slice.call(nav.children).forEach(function (el) {
      if (el.classList && (el.classList.contains('brand') ||
          el.classList.contains('sub') || el.classList.contains('h'))) {
        headNodes.push(el);
      }
    });
    if (headNodes.length) {
      nav.insertBefore(head, headNodes[0]);
      headNodes.forEach(function (el) { head.appendChild(el); });
    }
  } catch (e) { /* 结构异常时不影响其余功能 */ }

  /* 3. 长标题补 title，鼠标悬停可看全文 */
  var links = Array.prototype.slice.call(nav.querySelectorAll('ul a'));
  links.forEach(function (a) {
    if (!a.title) a.title = (a.textContent || '').trim();
  });

  /* 4. 窄屏目录抽屉 */
  if (bar) {
    var foot = document.createElement('div');
    foot.className = 'nav-foot';
    Array.prototype.slice.call(bar.querySelectorAll('a.btn')).forEach(function (a) {
      var c = a.cloneNode(true);
      c.title = (c.textContent || '').trim();
      foot.appendChild(c);
    });
    nav.appendChild(foot);
  }
  var mask = document.createElement('div');
  mask.id = 'nav-mask';
  document.body.appendChild(mask);

  var toggle = document.createElement('button');
  toggle.id = 'nav-toggle';
  toggle.type = 'button';
  toggle.setAttribute('aria-label', '打开/关闭目录');
  toggle.setAttribute('aria-expanded', 'false');
  toggle.textContent = '☰ 目录';
  if (bar) bar.insertBefore(toggle, bar.querySelector('a.btn') || null);
  else document.body.appendChild(toggle);

  function closeNav() {
    document.body.classList.remove('nav-open');
    toggle.setAttribute('aria-expanded', 'false');
  }
  toggle.addEventListener('click', function () {
    var open = document.body.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
  mask.addEventListener('click', closeNav);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeNav();
  });
  nav.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.closest && t.closest('a')) closeNav();
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth > 980) closeNav();
  }, { passive: true });

  /* 5. 当前章节高亮项自动滚入侧栏可视区（只在页面主滚动时跟随） */
  var lastActive = null;
  function followActive() {
    var a = nav.querySelector('a.active, a.on');
    if (!a || a === lastActive) return;
    lastActive = a;
    var top = a.offsetTop;
    var h = a.offsetHeight;
    var viewTop = nav.scrollTop;
    var viewBottom = viewTop + nav.clientHeight;
    if (top < viewTop + 32) {
      nav.scrollTop = Math.max(0, top - 56);
    } else if (top + h > viewBottom - 24) {
      nav.scrollTop = top + h - nav.clientHeight + 44;
    }
  }
  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () { followActive(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', followActive, { passive: true });
  setTimeout(followActive, 150);
})();
