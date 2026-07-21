// © 2026 Juan Pazmino B — Claude Code Digest chat widget (frontend).
// Builds the whole widget DOM; the page only loads this script and chatbot.css.
// Security: model text enters the DOM ONLY via textContent — never innerHTML.
(function () {
  'use strict';

  var API = '/api/chat';
  var MAX_TURNS = 10, MAX_LEN = 1000;

  // Single language-neutral site (no /es/ split like juanpazminob.com), so
  // the chrome copy is bilingual-neutral; the assistant itself replies in
  // whatever language the visitor types in, per the system prompt.
  var T = {
    opener: 'Hola — soy el asistente del Claude Code Daily Digest. Ask me about Claude Code features, guides, or news — pregunta en español o inglés.',
    chips: ['¿Qué hay de nuevo en Claude Code?', 'How do Claude Code hooks work?', 'Muéstrame una guía reciente'],
    label: 'Asistente IA', name: 'Claude Code Digest',
    placeholder: 'Ask about Claude Code…', closed: 'Session complete',
    open: 'Open AI assistant', close: 'Close', send: 'Send',
    limit: "That's the last question for this session — refresh the page to start a new one.",
    error: "I'm not available right now. Try again in a moment.",
  };

  var URL_SPLIT = /(https?:\/\/[^\s)>\]"']+)/g;
  // Labeled link from the model: [Title](https://...). Bounded label, no
  // line breaks; the URL admits no spaces or ')'.
  var MD_LINK = /\[([^\]\n]{1,200})\]\((https?:\/\/[^\s)]+)\)/g;

  // ── Session state (survives navigation, dies with the tab) ──
  var state;
  try { state = JSON.parse(sessionStorage.getItem('cb-history')); } catch (e) { state = null; }
  if (!state || !Array.isArray(state.messages)) {
    state = { messages: [], turns: 0 };
  }
  function save() { try { sessionStorage.setItem('cb-history', JSON.stringify(state)); } catch (e) {} }

  // ── DOM helpers (text always via textContent) ──
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  // ── Structure ──
  var root = el('div'); root.id = 'cb-widget';

  var bubble = el('button', 'cb-bubble');
  bubble.setAttribute('aria-label', T.open);
  bubble.setAttribute('aria-expanded', 'false');
  // Icon: chat balloon with the golden spiral from the favicon inside.
  // Built with createElementNS — zero innerHTML anywhere in this widget.
  (function () {
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 100 100');
    svg.setAttribute('aria-hidden', 'true');

    var balloon = document.createElementNS(NS, 'path');
    balloon.setAttribute('d', 'M50 12 C73.2 12 92 25.4 92 42 C92 58.6 73.2 72 50 72 C45.3 72 40.8 71.4 36.7 70.4 L20 80 L25.4 65.6 C14.8 60.1 8 51.6 8 42 C8 25.4 26.8 12 50 12 Z');
    balloon.setAttribute('fill', 'none');
    balloon.setAttribute('stroke', '#D4B068');
    balloon.setAttribute('stroke-width', '4.5');
    balloon.setAttribute('stroke-linecap', 'round');
    balloon.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(balloon);

    // Golden spiral (same geometry as the favicon), scaled inside the balloon
    var wrap = document.createElementNS(NS, 'g');
    wrap.setAttribute('transform', 'translate(50,42) scale(0.42) translate(-50,-50)');
    var g = document.createElementNS(NS, 'g');
    g.setAttribute('transform', 'translate(-12.5,-8.3)');
    var path = document.createElementNS(NS, 'path');
    path.setAttribute('d', 'M47.68,50.00 L47.57,50.65 L47.64,51.36 L47.91,52.09 L48.40,52.77 L49.10,53.35 L50.00,53.76 L51.05,53.94 L52.21,53.82 L53.39,53.39 L54.48,52.59 L55.43,51.45 L56.09,50.00 L56.37,48.29 L56.19,46.42 L55.48,44.52 L54.20,42.73 L52.35,41.21 L50.00,40.15 L47.24,39.68 L44.22,39.98 L41.14,41.14 L38.25,43.22 L35.79,46.19 L34.07,50.00 L33.70,51.43 L33.45,52.92 L33.32,54.47 L33.34,56.06 L33.49,57.69 L33.82,59.34 L34.26,61.02 L34.89,62.68 L35.67,64.33 L36.63,65.94 L37.73,67.52 L39.03,69.00 L40.47,70.44 L42.08,71.76 L43.84,72.99 L45.76,74.06 L47.81,75.01 L50.00,75.75 L52.31,76.39 L54.72,76.77 L57.23,76.99 L59.81,76.95 L62.46,76.73 L65.11,76.19 L67.84,75.47 L70.50,74.43 L73.19,73.19 L75.78,71.63 L78.35,69.85 L80.72,67.74 L83.10,65.43 L85.18,62.80 L87.19,59.96 L88.89,56.85 L90.46,53.54 L91.74,50.00');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#D4B068');
    path.setAttribute('stroke-width', '9');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    g.appendChild(path);
    wrap.appendChild(g);
    svg.appendChild(wrap);
    bubble.appendChild(svg);
  })();

  var panel = el('div', 'cb-panel');
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', T.label + ' ' + T.name);

  var header = el('div', 'cb-header');
  var title = el('div');
  title.appendChild(el('span', 'cb-ai-label', T.label));
  title.appendChild(el('span', 'cb-name', T.name));
  var closeBtn = el('button', 'cb-close', '×');
  closeBtn.setAttribute('aria-label', T.close);
  header.appendChild(title); header.appendChild(closeBtn);

  var msgs = el('div', 'cb-msgs');
  msgs.setAttribute('aria-live', 'polite');

  var chipsRow = el('div', 'cb-chips');
  T.chips.forEach(function (c) {
    var b = el('button', 'cb-chip', c);
    b.addEventListener('click', function () { send(c); });
    chipsRow.appendChild(b);
  });

  var inputRow = el('div', 'cb-inputrow');
  var input = el('input', 'cb-input');
  input.type = 'text'; input.maxLength = MAX_LEN; input.placeholder = T.placeholder;
  var sendBtn = el('button', 'cb-send', '→');
  sendBtn.setAttribute('aria-label', T.send);
  inputRow.appendChild(input); inputRow.appendChild(sendBtn);

  var footer = el('div', 'cb-footer', 'Powered by Claude');

  // Chips live INSIDE the message scroller (renderHistory appends them after
  // the opener) so they never overlap the text when the panel shrinks.
  panel.appendChild(header); panel.appendChild(msgs);
  panel.appendChild(inputRow); panel.appendChild(footer);
  root.appendChild(bubble); root.appendChild(panel);
  document.body.appendChild(root);
  requestAnimationFrame(function () { requestAnimationFrame(function () { bubble.classList.add('cb-in'); }); });

  // ── Render ──
  function addMsg(role, text) {
    var m = el('div', 'cb-msg cb-msg-' + role, text);
    msgs.appendChild(m);
    msgs.scrollTop = msgs.scrollHeight;
    return m;
  }

  // Text for a bare or labeled link: the model's title if given, else the
  // page slug or hostname.
  function anchorLabel(url) {
    try {
      var u = new URL(url);
      var seg = u.pathname.split('/').filter(Boolean).pop() || '';
      seg = seg.replace(/\.html$/, '').replace(/-/g, ' ');
      return seg || u.hostname.replace(/^www\./, '');
    } catch (e) { return url; }
  }

  // Shared safe anchor: label via textContent (el), href via property —
  // never innerHTML. Without a label, falls back to anchorLabel's slug.
  function appendLink(div, url, label) {
    url = url.replace(/[.,;:]+$/, '');
    var a = el('a', 'cb-link', label || anchorLabel(url));
    a.href = url;
    a.target = '_blank'; a.rel = 'noopener';
    div.appendChild(a);
  }

  // Segment with no labeled links: bare URLs become hyperlinks, rest is text.
  function renderPlainSegment(div, text) {
    text.split(URL_SPLIT).forEach(function (part) {
      if (!part) return;
      if (part.indexOf('http') === 0) appendLink(div, part);
      else div.appendChild(document.createTextNode(part));
    });
  }

  // Renders the bot's text: the model's [Title](url) links first, then any
  // bare URLs. Only text nodes + <a> elements built by code — never innerHTML.
  function renderBotText(div, fullText) {
    div.textContent = '';
    var last = 0, m;
    MD_LINK.lastIndex = 0;
    while ((m = MD_LINK.exec(fullText)) !== null) {
      if (m.index > last) renderPlainSegment(div, fullText.slice(last, m.index));
      appendLink(div, m[2], m[1]);
      last = m.index + m[0].length;
    }
    if (last < fullText.length) renderPlainSegment(div, fullText.slice(last));
  }

  function showError() { addMsg('bot', T.error); }

  function lockSession() {
    input.disabled = true; sendBtn.disabled = true;
    input.placeholder = T.closed;
    addMsg('bot', T.limit);
  }

  function renderHistory() {
    msgs.textContent = '';
    addMsg('bot', T.opener); // Art. 50: the bot identifies itself as AI before anything else
    state.messages.forEach(function (m) {
      if (m.role === 'user') { addMsg('user', m.content); }
      else { renderBotText(addMsg('bot', ''), m.content); }
    });
    if (state.turns >= MAX_TURNS) { lockSession(); }
    else if (state.turns === 0) { chipsRow.style.display = ''; msgs.appendChild(chipsRow); }
    if (state.messages.length === 0) msgs.scrollTop = 0;
  }

  // ── Send + streaming ──
  var streaming = false;

  function send(text) {
    text = (text || '').trim().slice(0, MAX_LEN);
    if (!text || streaming || state.turns >= MAX_TURNS) return;
    streaming = true;
    input.disabled = true; sendBtn.disabled = true;
    chipsRow.style.display = 'none';

    state.messages.push({ role: 'user', content: text });
    state.turns++;
    save();
    addMsg('user', text);

    var typing = el('div', 'cb-typing');
    typing.appendChild(el('span')); typing.appendChild(el('span')); typing.appendChild(el('span'));
    msgs.appendChild(typing);
    msgs.scrollTop = msgs.scrollHeight;

    fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: state.messages.slice(-20) })
    }).then(function (res) {
      if (!res.ok || !res.body) throw new Error('bad status');
      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var full = '', div = null;
      function pump() {
        return reader.read().then(function (r) {
          if (r.done) return full;
          var chunk = decoder.decode(r.value, { stream: true });
          full += chunk;
          if (!div) { typing.remove(); div = addMsg('bot', ''); }
          div.textContent = full.replace('[[ERROR]]', '');
          msgs.scrollTop = msgs.scrollHeight;
          return pump();
        });
      }
      return pump().then(function (full) {
        typing.remove();
        if (full.indexOf('[[ERROR]]') !== -1) {
          var visible = full.replace('[[ERROR]]', '').trim();
          if (div) div.remove();
          if (visible) { div = addMsg('bot', ''); renderBotText(div, visible); state.messages.push({ role: 'assistant', content: visible }); save(); }
          showError();
        } else if (full.trim()) {
          renderBotText(div || addMsg('bot', ''), full);
          state.messages.push({ role: 'assistant', content: full });
          save();
        } else {
          showError();
        }
      });
    }).catch(function () {
      typing.remove();
      showError();
    }).then(function () {
      streaming = false;
      if (state.turns >= MAX_TURNS) { lockSession(); }
      else { input.disabled = false; sendBtn.disabled = false; input.focus(); }
    });
  }

  // ── Open / close ──
  // Mobile (≤600px): the panel fits the VISUAL viewport (the area the
  // keyboard leaves free) so the input always stays visible, and the page
  // behind is scroll-locked while the chat is open.
  var mqMobile = window.matchMedia('(max-width: 600px)');
  var vv = window.visualViewport;
  var lockY = 0; // page scroll at open time — restored on close
  function fitPanel() {
    if (!mqMobile.matches || !vv || !panel.classList.contains('cb-open')) return;
    // Follow the user to the bottom if they were already there; leave their
    // scroll position alone if they were reading further up.
    var nearBottom = state.messages.length > 0 &&
      msgs.scrollHeight - msgs.scrollTop - msgs.clientHeight < 60;
    // iOS "pans" the viewport when the keyboard opens even with the body
    // frozen: cancel that pan so the panel exactly fills the visible area.
    window.scrollTo(0, 0);
    panel.style.top = '0px';
    panel.style.height = vv.height + 'px';
    if (nearBottom) msgs.scrollTop = msgs.scrollHeight;
  }
  function openPanel() {
    renderHistory();
    panel.classList.add('cb-open');
    bubble.classList.add('cb-hidden');
    bubble.setAttribute('aria-expanded', 'true');
    if (mqMobile.matches) {
      // Freeze the background page (iOS ignores overflow:hidden for touch:
      // needs position:fixed on body, saving and restoring the scroll)
      lockY = window.scrollY || 0;
      document.documentElement.classList.add('cb-lock');
      document.body.classList.add('cb-lock');
      document.body.style.top = -lockY + 'px';
      if (vv) {
        vv.addEventListener('resize', fitPanel);
        vv.addEventListener('scroll', fitPanel);
        fitPanel();
      }
    }
    requestAnimationFrame(function () { requestAnimationFrame(function () { panel.classList.add('cb-in'); }); });
    if (state.turns < MAX_TURNS) input.focus();
  }
  function closePanel() {
    panel.classList.remove('cb-open', 'cb-in');
    bubble.classList.remove('cb-hidden');
    bubble.setAttribute('aria-expanded', 'false');
    document.documentElement.classList.remove('cb-lock');
    document.body.classList.remove('cb-lock');
    document.body.style.top = '';
    if (mqMobile.matches) window.scrollTo(0, lockY);
    if (vv) {
      vv.removeEventListener('resize', fitPanel);
      vv.removeEventListener('scroll', fitPanel);
    }
    panel.style.top = '';
    panel.style.height = '';
    bubble.focus();
  }
  // Focusing the input on mobile opens the keyboard with an animation
  // (~350ms) and iOS adjusts the viewport in several steps — refit twice.
  input.addEventListener('focus', function () {
    setTimeout(fitPanel, 300);
    setTimeout(fitPanel, 650);
  });

  // iOS rubber-band: any scroll gesture outside the message scroller (or
  // when it doesn't overflow) is blocked so it never reaches the page
  // behind. passive:false is required for preventDefault.
  panel.addEventListener('touchmove', function (e) {
    if (!mqMobile.matches) return;
    var scroller = e.target.closest ? e.target.closest('.cb-msgs') : null;
    if (!scroller || scroller.scrollHeight <= scroller.clientHeight) e.preventDefault();
  }, { passive: false });

  bubble.addEventListener('click', openPanel);
  closeBtn.addEventListener('click', closePanel);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && panel.classList.contains('cb-open')) closePanel();
  });
  sendBtn.addEventListener('click', function () { var v = input.value; input.value = ''; send(v); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { var v = input.value; input.value = ''; send(v); }
  });
})();
