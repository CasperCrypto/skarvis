// SKARVIS build console — gate, navigation, buy-list state, lazy 3D.
//
// SECURITY NOTE: the passphrase below is a SOFT GATE. It is checked in the
// browser and can be read from this file, so it is not real access control.
// It only keeps casual eyes out while the console runs locally. For a real
// lock on a hosted link, serve this behind Cloudflare Access (edge auth) and
// treat this check as a convenience, not a security boundary.
const PASSPHRASE = 'casper33';

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const gate = document.querySelector('[data-gate]');
const app = document.querySelector('[data-app]');

if (sessionStorage.getItem('skv-admin') === 'ok') {
  unlock();
} else {
  initGate();
}

function initGate() {
  const form = gate.querySelector('[data-gate-form]');
  const input = gate.querySelector('[data-gate-input]');
  const err = gate.querySelector('[data-gate-err]');
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (input.value === PASSPHRASE) {
      try { sessionStorage.setItem('skv-admin', 'ok'); } catch (_) {}
      unlock();
    } else {
      err.textContent = 'Wrong passphrase.';
      input.setAttribute('aria-invalid', 'true');
      input.select();
    }
  });
  input.addEventListener('input', () => {
    err.textContent = '';
    input.removeAttribute('aria-invalid');
  });
}

function unlock() {
  gate.hidden = true;
  app.hidden = false;
  initNav();
  initBuyList();
  initNode();
}

/* ---------------- navigation ---------------- */

function initNav() {
  const side = document.querySelector('[data-side]');
  const burger = document.querySelector('[data-burger]');
  const links = [...document.querySelectorAll('[data-nav] a')];
  const title = document.querySelector('[data-topbar-title]');
  const byId = new Map(links.map((a) => [a.getAttribute('href').slice(1), a]));

  burger?.addEventListener('click', () => side.classList.toggle('open'));
  document.querySelector('[data-nav]')?.addEventListener('click', (e) => {
    if (e.target.closest('a')) side.classList.remove('open');
  });

  document.querySelector('[data-logout]')?.addEventListener('click', (e) => {
    e.preventDefault();
    try { sessionStorage.removeItem('skv-admin'); } catch (_) {}
    location.reload();
  });

  const sections = [...document.querySelectorAll('section.block')];
  if (!('IntersectionObserver' in window)) return;
  const io = new IntersectionObserver((entries) => {
    for (const en of entries) {
      if (!en.isIntersecting) continue;
      const id = en.target.id;
      links.forEach((a) => a.classList.remove('active'));
      byId.get(id)?.classList.add('active');
      const sec = en.target.getAttribute('data-sec');
      if (sec && title) title.innerHTML = sec;
    }
  }, { rootMargin: '-45% 0px -50% 0px' });
  sections.forEach((s) => io.observe(s));
}

/* ---------------- buy-list ---------------- */

function initBuyList() {
  const boxes = [...document.querySelectorAll('[data-buy-item]')];
  const count = document.querySelector('[data-buy-count]');
  if (!boxes.length) return;
  let saved = [];
  try { saved = JSON.parse(localStorage.getItem('skv-buy') || '[]'); } catch (_) {}

  const render = () => {
    let n = 0;
    boxes.forEach((b, i) => {
      const on = b.checked;
      b.closest('tr').classList.toggle('done', on);
      if (on) n++;
    });
    if (count) count.textContent = `${n} / ${boxes.length}`;
  };

  boxes.forEach((b, i) => {
    b.checked = saved.includes(i);
    b.addEventListener('change', () => {
      const picked = boxes.map((x, j) => (x.checked ? j : -1)).filter((j) => j >= 0);
      try { localStorage.setItem('skv-buy', JSON.stringify(picked)); } catch (_) {}
      render();
    });
  });
  render();
}

/* ---------------- 3D node (lazy) ---------------- */

function initNode() {
  const root = document.querySelector('[data-node]');
  if (!root) return;
  const stage = root.querySelector('[data-node-stage]');
  const start = () =>
    Promise.all([
      import('../site/assets/js/node3d.js'),
      import('../site/assets/js/strings.js')
    ])
      .then(([mod, s]) => mod.initNode(root, { reduceMotion, T: s.STRINGS.en.node }))
      .catch((err) => {
        console.warn('3D model unavailable:', err);
        stage.classList.add('no-gl');
      });

  if (!('IntersectionObserver' in window)) { start(); return; }
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      io.disconnect();
      start();
    }
  }, { rootMargin: '400px 0px' });
  io.observe(stage);
}
