/* Геометрия схемы процесса: прогоняется в браузере на открытой странице /d/<slug>/process.
   Проверяет то, что глазами ловится плохо: стрелки друг через друга, стрелки сквозь карточки,
   карточки внахлёст, подписи внахлёст, уехавшую вёрстку. Всё должно быть нулями.
   Как запускать — docs/README-checks.md. */
(async () => {
  await new Promise(r => setTimeout(r, 900));
  const layer = document.querySelector('.flowlayer');
  if (!layer) return { error: 'нет .flowlayer', page: location.pathname };
  const grid = document.querySelector('.lanes') || layer.parentElement;
  const gr = grid.getBoundingClientRect();
  const paths = [...layer.querySelectorAll('path')];
  const segs = d => { const p = [...d.matchAll(/(-?\d+(?:\.\d+)?)[ ,](-?\d+(?:\.\d+)?)/g)].map(m => [+m[1], +m[2]]);
    const o = []; for (let i = 1; i < p.length; i++) o.push([p[i - 1], p[i]]); return o; };
  const sgn = (p, q, r) => Math.sign((q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0]));
  // Строго: общая точка (линия выходит из порта, мимо которого идёт другая) — не пересечение,
  // иначе чек гоняется за фантомами. Настоящее наложение ловится отдельно, ниже.
  const cross = (a, b, c, d) => { const d1=sgn(a,b,c), d2=sgn(a,b,d), d3=sgn(c,d,a), d4=sgn(c,d,b);
    return d1 && d2 && d3 && d4 && d1 !== d2 && d3 !== d4; };
  const all = []; paths.forEach((p, i) => segs(p.getAttribute('d') || '').forEach(s => all.push({ i, s })));
  let n = 0;
  for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++)
    if (all[i].i !== all[j].i && cross(all[i].s[0], all[i].s[1], all[j].s[0], all[j].s[1])) n++;
  const cards = [...document.querySelectorAll('.pstep[data-sid]')];
  const rects = cards.map(c => { const r = c.getBoundingClientRect();
    return { l: r.left-gr.left, t: r.top-gr.top, r: r.right-gr.left, b: r.bottom-gr.top, id: c.dataset.sid }; });
  const inR = (p, R) => p[0] > R.l+3 && p[0] < R.r-3 && p[1] > R.t+3 && p[1] < R.b-3;
  let thru = 0; const thruEx = [];
  all.forEach(({ i, s }) => rects.forEach(R => {
    const mid = [(s[0][0]+s[1][0])/2, (s[0][1]+s[1][1])/2];
    if (inR(mid, R)) { thru++; if (thruEx.length < 5) thruEx.push({ arrow: i, card: R.id }); } }));
  let cardOvl = 0; const cardEx = [];
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.l < b.r-1 && b.l < a.r-1 && a.t < b.b-1 && b.t < a.b-1) {
      cardOvl++; if (cardEx.length < 4) cardEx.push([a.id, b.id]); } }
  // Коллинеарное наложение: две стрелки лежат друг на друге — то, что видно как «налазят».
  let onTop = 0;
  for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++) {
    if (all[i].i === all[j].i) continue;
    const [a, b] = all[i].s, [c, d] = all[j].s;
    const ovl = (p, q, r, s2) => Math.min(Math.max(p, q), Math.max(r, s2)) - Math.max(Math.min(p, q), Math.min(r, s2));
    if (a[0] === b[0] && c[0] === d[0] && Math.abs(a[0]-c[0]) < 2 && ovl(a[1],b[1],c[1],d[1]) > 10) onTop++;
    if (a[1] === b[1] && c[1] === d[1] && Math.abs(a[1]-c[1]) < 2 && ovl(a[0],b[0],c[0],d[0]) > 10) onTop++;
  }
  let turns = 0, len = 0;
  paths.forEach(p => { const sg = segs(p.getAttribute('d') || ''); turns += Math.max(0, sg.length - 1);
    sg.forEach(([a, b]) => len += Math.abs(a[0]-b[0]) + Math.abs(a[1]-b[1])); });
  const txt = [...layer.querySelectorAll('text')].map(t => t.getBoundingClientRect());
  let ovl = 0;
  for (let i = 0; i < txt.length; i++) for (let j = i + 1; j < txt.length; j++) {
    const a = txt[i], b = txt[j];
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) ovl++; }
  return { page: location.pathname, arrows: paths.length - 1, crossings: n, onTopOfEachOther: onTop,
    cards: cards.length, throughCards: thru, thruEx, cardOverlaps: cardOvl, cardEx,
    labels: txt.length, labelOverlaps: ovl, turns, length: Math.round(len),
    pageHScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth };
})()
