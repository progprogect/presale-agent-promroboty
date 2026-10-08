"""CSPL-генератор: process.yaml -> страница «Процесс» (схема дорожками, по смыслу BPMN).

Формат спеки — общий с генератором картинки для ТКП (knowledge/cspl/generators/process-diagram):
одна спека, два рендера. Линейная цепочка «1 → 2 → 3» не используется (решение Микиты 25.09.2026):
дорожки показывают, кто что делает, что идёт одновременно и где проходит граница нашей поставки.

Спека: lanes[{id, name, sub, kind: ours|client|human}], steps[{n, lane, title, desc, time, parallel, id}],
columns[{n, label}] (необяз.), flows[{from, to, label}] (необяз.), cycle, key_figure, title.

Стрелки (BPMN sequence flow) рисуются поверх сетки: если в спеке есть flows — по ним, иначе
выводятся автоматически цепочкой по порядку шагов. Шаги с parallel в цепочку не включаются —
они идут фоном, и к ним ведёт пунктирная связь от шага той же колонки.
"""
import json

from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

LANE_KIND = {"ours": "ours", "client": "client", "human": ""}

# Отрисовка стрелок потока поверх сетки. Координаты считаются из реальных размеров карточек
# после вёрстки, поэтому схема остаётся верной при любой ширине экрана и при прокрутке.
FLOW_JS = r"""
(function(){
  const grid=document.querySelector('.lanes'),
        svg=document.querySelector('.flowlayer'),
        src=document.getElementById('flows');
  if(!grid||!svg||!src)return;
  let flows=[];try{flows=JSON.parse(src.textContent)||[]}catch(e){return}
  const NS='http://www.w3.org/2000/svg';
  const G=9;      // половина коридора между карточками
  const PAD=5;    // зазор, с которым линия считается задевшей карточку
  const TIP=8;    // на столько не доводим линию до карточки — там рисуется наконечник

  // Линия не должна пересекать чужие карточки. Поэтому для каждой связи перебираем
  // несколько вариантов геометрии и берём первый, который ни во что не упирается.
  function hit(x1,y1,x2,y2,rects,skip){
    const ax=Math.min(x1,x2)-PAD,bx=Math.max(x1,x2)+PAD;
    const ay=Math.min(y1,y2)-PAD,by=Math.max(y1,y2)+PAD;
    for(const r of rects){
      if(r===skip[0]||r===skip[1])continue;
      if(bx>r.l&&ax<r.r&&by>r.t&&ay<r.b)return true;
    }
    return false;
  }
  function clean(pts,rects,skip){
    for(let i=0;i<pts.length-1;i++)
      if(hit(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],rects,skip))return false;
    return true;
  }
  // укорачиваем последний отрезок, чтобы наконечник не налезал на карточку
  function trim(pts){
    const n=pts.length,p1=pts[n-2],p2=pts[n-1];
    const dx=p2[0]-p1[0],dy=p2[1]-p1[1],L=Math.hypot(dx,dy)||1;
    return pts.slice(0,n-1).concat([[p2[0]-dx/L*TIP,p2[1]-dy/L*TIP]]);
  }
  const d=pts=>'M'+pts.map(p=>p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' L');

  function routes(a,b){
    const out=[];
    const sameCol=Math.abs(b.cx-a.cx)<30;
    // 1. соседние по вертикали в одной колонке — прямая линия
    if(sameCol&&b.t>=a.b) out.push([[a.cx,a.b],[a.cx,b.t]]);
    if(sameCol&&b.b<=a.t) out.push([[a.cx,a.t],[a.cx,b.b]]);   // цель выше: выходим вверх
    // 2. вперёд по потоку — колено в коридоре между колонками
    if(b.l>=a.r-1){
      const mx=(a.r+b.l)/2;
      out.push([[a.r,a.cy],[mx,a.cy],[mx,b.cy],[b.l,b.cy]]);
    }
    // 3. обход понизу и поверху — когда прямые пути заняты
    const yb=Math.max(a.b,b.b)+G*2, yt=Math.min(a.t,b.t)-G*2;
    const xr=Math.max(a.r,b.r)+G,  xl=Math.min(a.l,b.l)-G;
    out.push([[a.cx,a.b],[a.cx,yb],[b.cx,yb],[b.cx,b.b]]);
    out.push([[a.cx,a.t],[a.cx,yt],[b.cx,yt],[b.cx,b.t]]);
    out.push([[a.r,a.cy],[xr,a.cy],[xr,b.cy],[b.r,b.cy]]);
    out.push([[a.l,a.cy],[xl,a.cy],[xl,b.cy],[b.l,b.cy]]);
    return out;
  }

  function draw(){
    while(svg.firstChild)svg.removeChild(svg.firstChild);
    const gb=grid.getBoundingClientRect();
    const R=el=>{const r=el.getBoundingClientRect();
      return {el:el,l:r.left-gb.left,t:r.top-gb.top,
              r:r.left-gb.left+r.width,b:r.top-gb.top+r.height,
              cx:r.left-gb.left+r.width/2,cy:r.top-gb.top+r.height/2};};
    const rects=[...grid.querySelectorAll('.pstep')].map(R);
    const byId={};for(const r of rects)byId[r.el.dataset.sid]=r;
    svg.setAttribute('viewBox','0 0 '+grid.scrollWidth+' '+grid.scrollHeight);
    svg.setAttribute('width',grid.scrollWidth);
    svg.setAttribute('height',grid.scrollHeight);
    const defs=document.createElementNS(NS,'defs');
    defs.innerHTML='<marker id="ah" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="6.5"'
      +' markerHeight="6.5" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"/></marker>';
    svg.appendChild(defs);
    for(const f of flows){
      const a=byId[f.a],b=byId[f.b];
      if(!a||!b)continue;
      const cands=routes(a,b);
      let pts=cands.find(c=>clean(c,rects,[a,b]))||cands[0];
      const p=document.createElementNS(NS,'path');
      p.setAttribute('d',d(trim(pts)));
      p.setAttribute('class','fl'+(f.kind==='par'?' par':''));
      p.setAttribute('marker-end','url(#ah)');
      svg.appendChild(p);
      if(f.label){
        const m=pts[Math.floor(pts.length/2)];
        const tx=document.createElementNS(NS,'text');
        tx.setAttribute('x',m[0]);tx.setAttribute('y',m[1]-5);
        tx.setAttribute('class','fllab');tx.textContent=f.label;
        svg.appendChild(tx);
      }
    }
  }
  draw();
  addEventListener('resize',draw);
  if(window.ResizeObserver)new ResizeObserver(draw).observe(grid);
  grid.addEventListener('click',()=>setTimeout(draw,0));
})();
"""



def _step(st: dict, kind: str, uid: str) -> str:
    cls = " " + LANE_KIND.get(kind, "") if LANE_KIND.get(kind) else ""
    if st.get("parallel"):
        cls += " par"
    sid = f'{st["n"]}-{st["lane"]}'
    time = f'<span class="tm badge bg-azure-lt">{esc(str(st["time"]))}</span>' if st.get("time") else ""
    par = (f'<span class="d">одновременно: {esc(st["parallel"])}</span>'
           if st.get("parallel") else "")
    desc = f'<span class="d">{esc(st["desc"])}</span>' if st.get("desc") else ""
    return f"""<div class="pstep{cls}" data-sid="{esc(uid)}">
        <span class="n">{esc(str(st["n"]))}
          <button class="btn btn-ghost-secondary btn-icon cmt-toggle" data-id="s{sid}"
            style="float:right;width:18px;height:18px;min-height:0" title="Комментарий">{ICON_COMMENT}</button>
        </span>
        <span class="t">{esc(st["title"])}</span>{desc}{par}{time}
        <div class="crow" id="crow-s{sid}" hidden><div class="cbox mt-1">
          <textarea class="form-control" data-ckey="шаг {esc(str(st["n"]))} · {esc(st["title"])}"
            placeholder="Что не так с этим шагом…"></textarea>
          <button class="btn btn-sm mic-btn" data-for="шаг {esc(str(st["n"]))} · {esc(st["title"])}"
            title="Надиктовать">{ICON_MIC}</button>
        </div></div>
      </div>"""


def render(deal: dict, spec: dict) -> str:
    lanes = spec["lanes"]
    steps = spec["steps"]
    lane_ids = {l["id"] for l in lanes}
    bad = sorted({s["lane"] for s in steps} - lane_ids)
    if bad:
        raise SystemExit(f"process.yaml ({deal['slug']}): шаг ссылается на несуществующую дорожку: {bad}")
    cols = sorted({s["n"] for s in steps})
    col_label = {c["n"]: c["label"] for c in spec.get("columns", [])}

    cells = []
    if col_label:
        cells.append('<div class="lane-col"></div>')
        cells.extend(f'<div class="lane-col">{esc(col_label.get(n, ""))}</div>' for n in cols)
    # Устойчивый идентификатор каждой карточки: из спеки (поле id) либо порядковый.
    uids = {}
    for i, s in enumerate(steps):
        uids[id(s)] = str(s.get("id") or f'{s["n"]}-{s["lane"]}-{i}')

    for lane in lanes:
        sub = f'<small>{esc(lane["sub"])}</small>' if lane.get("sub") else ""
        kind = lane.get("kind", "")
        cells.append(f'<div class="lane-name {esc(kind)}"><div>{esc(lane["name"])}{sub}</div></div>')
        for n in cols:
            here = [s for s in steps if s["lane"] == lane["id"] and s["n"] == n]
            inner = "".join(_step(s, kind, uids[id(s)]) for s in here)
            cells.append(f'<div class="lane-cell">{inner}</div>')

    # Ширина колонки потока подбирается под число колонок: узкие дорожки лучше читаются,
    # но карточка не должна быть уже своего содержимого — отсюда нижняя граница 176px.
    # Потоки (BPMN sequence flow). Если в спеке заданы flows — берём их; иначе выводим
    # цепочку по порядку шагов, исключая фоновые (parallel): они не в такте, и ставить их
    # в цепочку было бы неправдой. К фоновому шагу ведём пунктир от шага той же колонки.
    flows = []
    if spec.get("flows"):
        by_id = {}
        for s in steps:
            by_id.setdefault(str(s.get("id") or ""), uids[id(s)])
        for f in spec["flows"]:
            a, b = str(f.get("from", "")), str(f.get("to", ""))
            if a in by_id and b in by_id:
                flows.append({"a": by_id[a], "b": by_id[b],
                              "label": f.get("label", ""), "kind": f.get("kind", "seq")})
    else:
        chain = [s for s in sorted(steps, key=lambda s: (s["n"], steps.index(s)))
                 if not s.get("parallel")]
        for a, b in zip(chain, chain[1:]):
            flows.append({"a": uids[id(a)], "b": uids[id(b)], "label": "", "kind": "seq"})
        for s in steps:
            if not s.get("parallel"):
                continue
            host = next((c for c in chain if c["n"] == s["n"]), None)
            if host:
                flows.append({"a": uids[id(host)], "b": uids[id(s)], "label": "", "kind": "par"})

    grid = (f'<div class="lanes-wrap"><div class="lanes" '
            f'style="grid-template-columns:168px repeat({len(cols)},minmax(200px,1fr))">'
            f'{"".join(cells)}'
            f'<svg class="flowlayer" aria-hidden="true"></svg>'
            f'</div></div>'
            f'<script type="application/json" id="flows">{json.dumps(flows, ensure_ascii=False)}</script>')
    cycle = f'<p class="cyc">↻ {esc(spec["cycle"])}</p>' if spec.get("cycle") else ""
    keyfig = f'<p class="keyfig">{esc(spec["key_figure"])}</p>' if spec.get("key_figure") else ""
    head = f'<p class="hint">{esc(spec["title"])}</p>' if spec.get("title") else ""

    body = f"""
  <p class="hint">Как устроен процесс целиком, крупными мазками. Дорожка — участник: человек, наша
  поставка, оборудование заказчика. Блок стоит там, где он реально происходит; пунктир — то, что идёт
  одновременно. Оранжевым отмечена зона заказчика: там проходит граница нашей ответственности.</p>
  {head}
  <div class="card"><div class="card-body py-3">
    {grid}
    {cycle}
    {keyfig}
  </div></div>
  <div class="card mt-2"><div class="card-body py-2">
    <div class="cbox" style="max-width:none">
      <textarea class="form-control" data-ckey="процесс в целом"
        placeholder="Процесс в целом: что происходит не так, чего не хватает, что лишнее…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="процесс в целом" title="Надиктовать">{ICON_MIC}</button>
    </div>
  </div></div>
  {savebar()}"""

    script = (f'const API_URL="/api/d/{deal["slug"]}/review/process";\n'
              + REVIEW_JS + FLOW_JS)
    return shell(deal, "Процесс", "process", body, script)
