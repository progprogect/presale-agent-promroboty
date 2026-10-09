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
  // Веса маршрутизации. Подобраны прогоном чек-скрипта (docs/check_flow.js) по всем
  // карточкам пайплайна; window.FLOW_TUNE позволяет подобрать заново без пересборки.
  // ПРАВИЛО ЗАЗОРА. Линия не касается карточки нигде: ни началом, ни наконечником,
  // ни боком по дороге. Поэтому вокруг каждой карточки на расстоянии GAP проложены
  // «обводные» коридоры, точки подключения стоят на них, а сами грани карточек
  // коридорами больше не являются — ехать по грани нельзя в принципе.
  // Зазор по дороге (GAP) и зазор на конце (END) — разные вещи: мимо чужой карточки
  // надо проходить широко, а в свою стрелка должна упираться, иначе она целится мимо.
  const T={
    GAP:11,     // зазор от карточки: ближе этого не проходит ни одна линия
    END:5,      // зазор в точке подключения: стрелка доводится до карточки, но не касается
    NEAR:7,     // ближе этого параллельные стрелки сливаются в одну линию
    NEARPEN:0,  // штраф за это соседство (0 — выключено, см. docs/README-checks.md)
    TURN:60,    // штраф за поворот: прямая читается лучше ломаной
    BUSY:400,   // штраф за коридор, где уже лежит другая стрелка — чтобы расходились
    CROSS:420,  // штраф за пересечение чужой стрелки поперёк
  };
  let GAP,END,NEAR,NEARPEN,TURN,BUSY,CROSS;
  function tune(){ const t=Object.assign({},T,window.FLOW_TUNE||{});
    GAP=t.GAP;END=t.END;NEAR=t.NEAR;NEARPEN=t.NEARPEN;TURN=t.TURN;BUSY=t.BUSY;CROSS=t.CROSS; }
  tune();

  // Карточки — препятствия. Коридоры ищем в щелях между ними: по построению
  // линия, идущая по щели, ни во что не упирается. Раньше коридор был один на всех,
  // поэтому стрелки ложились друг на друга — теперь их столько, сколько влезает.
  function lanesOf(ivals, lo, hi){
    const m=ivals.slice().sort((a,b)=>a[0]-b[0]), merged=[];
    for(const s of m){
      const last=merged[merged.length-1];
      if(last && s[0]<=last[1]+1) last[1]=Math.max(last[1],s[1]); else merged.push([s[0],s[1]]);
    }
    const out=[]; let cur=lo;
    const put=(a,b)=>{const w=b-a; if(w<7)return;
      const k = w>70?3 : w>28?2 : 1;
      for(let i=1;i<=k;i++) out.push(a+w*i/(k+1));};
    for(const [a,b] of merged){ put(cur,a); cur=Math.max(cur,b); }
    put(cur,hi);
    return out;
  }
  const uniq=a=>[...new Set(a.map(v=>Math.round(v)))].sort((x,y)=>x-y);

  function build(rects,W,H){
    // в сетку входят и линии самих карточек: на них лежат порты, иначе стрелке
    // неоткуда выйти и некуда прийти
    // Коридоры: в щелях между карточками плюс «обводка» каждой карточки на расстоянии
    // GAP от её граней — именно к обводке подключаются стрелки. Сами грани (l, r, t, b)
    // в сетку не входят: по грани ехать нельзя, иначе линия липнет к карточке.
    const lanesX=lanesOf(rects.map(r=>[r.l,r.r]),0,W);
    const lanesY=lanesOf(rects.map(r=>[r.t,r.b]),0,H);
    const xs=uniq(lanesX.concat(rects.map(r=>r.cx),
      rects.map(r=>r.l-GAP), rects.map(r=>r.r+GAP)).filter(v=>v>=0&&v<=W));
    const ys=uniq(lanesY.concat(rects.map(r=>r.cy),
      rects.map(r=>r.t-GAP), rects.map(r=>r.b+GAP)).filter(v=>v>=0&&v<=H));
    const xi={},yi={}; xs.forEach((v,i)=>xi[v]=i); ys.forEach((v,i)=>yi[v]=i);
    const id=(i,j)=>i*ys.length+j;
    // Отрезок свободен, если держит зазор GAP от каждой карточки. Допуск в 1 пиксель —
    // на округление координат: обводной коридор сам стоит ровно на GAP.
    const free=(x1,y1,x2,y2)=>{
      const g=GAP-1;
      const ax=Math.min(x1,x2),bx=Math.max(x1,x2),ay=Math.min(y1,y2),by=Math.max(y1,y2);
      for(const r of rects)
        if(bx>r.l-g&&ax<r.r+g&&by>r.t-g&&ay<r.b+g) return false;
      return true;
    };
    const adj=new Map(), segOf=new Map();
    const link=(a,b,len,dir,key,x1,y1,x2,y2)=>{
      if(!adj.has(a))adj.set(a,[]);
      adj.get(a).push({to:b,len:len,dir:dir,key:key});
      if(!segOf.has(key))segOf.set(key,{x1:x1,y1:y1,x2:x2,y2:y2,dir:dir});
    };
    for(let i=0;i<xs.length;i++)for(let j=0;j<ys.length;j++){
      if(i+1<xs.length && free(xs[i],ys[j],xs[i+1],ys[j])){
        const k='h'+j+':'+i, L=xs[i+1]-xs[i];
        link(id(i,j),id(i+1,j),L,'h',k,xs[i],ys[j],xs[i+1],ys[j]);
        link(id(i+1,j),id(i,j),L,'h',k,xs[i],ys[j],xs[i+1],ys[j]);
      }
      if(j+1<ys.length && free(xs[i],ys[j],xs[i],ys[j+1])){
        const k='v'+i+':'+j, L=ys[j+1]-ys[j];
        link(id(i,j),id(i,j+1),L,'v',k,xs[i],ys[j],xs[i],ys[j+1]);
        link(id(i,j+1),id(i,j),L,'v',k,xs[i],ys[j],xs[i],ys[j+1]);
      }
    }
    return {xs:xs,ys:ys,xi:xi,yi:yi,id:id,adj:adj,free:free,segOf:segOf,rects:rects};
  }

  // Порты — точки подключения, вынесенные от граней на GAP: линия начинается и
  // заканчивается в стороне от карточки, а не на её кромке.
  function ports(g,r){
    const out=[]; const cx=Math.round(r.cx), cy=Math.round(r.cy);
    const put=(x,y,dir)=>{ if(g.xi[x]!==undefined&&g.yi[y]!==undefined)
      out.push({n:g.id(g.xi[x],g.yi[y]),x:x,y:y,dir:dir}); };
    put(cx,Math.round(r.t-GAP),'v'); put(cx,Math.round(r.b+GAP),'v');
    put(Math.round(r.l-GAP),cy,'h'); put(Math.round(r.r+GAP),cy,'h');
    return out;
  }

  // Пересечение считаем честно: вертикаль одной стрелки через горизонталь другой —
  // разные рёбра сетки, пометкой «занято» их не поймать. Соседние коридоры в узкой щели
  // стоят в 2–4 px друг от друга: формально это разные пути, а на экране — одна жирная
  // линия, поэтому параллельная стрелка ближе NEAR штрафуется как занятый коридор.
  function penalties(g,busy,laid){
    const olap=(a1,a2,b1,b2)=>Math.min(Math.max(a1,a2),Math.max(b1,b2))
                             -Math.max(Math.min(a1,a2),Math.min(b1,b2));
    const pen=new Map();
    g.segOf.forEach((s,k)=>{
      let p=(busy.get(k)||0)*BUSY;
      for(const o of laid){
        if(o.dir===s.dir){
          const d=s.dir==='v'?Math.abs(s.x1-o.x1):Math.abs(s.y1-o.y1);
          const ov=s.dir==='v'?olap(s.y1,s.y2,o.y1,o.y2):olap(s.x1,s.x2,o.x1,o.x2);
          if(d<NEAR&&ov>10)p+=NEARPEN;
          continue;
        }
        const v=s.dir==='v'?s:o, h=s.dir==='v'?o:s;
        if(v.x1>Math.min(h.x1,h.x2)&&v.x1<Math.max(h.x1,h.x2)&&
           h.y1>Math.min(v.y1,v.y2)&&h.y1<Math.max(v.y1,v.y2)) p+=CROSS;
      }
      if(p)pen.set(k,p);
    });
    return pen;
  }

  // Прямая связь соседних карточек. Если грани смотрят друг на друга и между ними
  // свободно — линия идёт напрямую, без сетки: маршрут по коридорам на такой щели давал
  // излом на пустом месте и 4 px линии на 6,5 px наконечника.
  const MINRUN=2*T.END+6;   // короче этого прямая не читается — тогда идём сеткой
  function direct(g,a,b){
    const ov=(l1,r1,l2,r2)=>Math.min(r1,r2)-Math.max(l1,l2);
    const clear=(x1,y1,x2,y2)=>{ const c=GAP-1;
      return !g.rects.some(r=>r!==a&&r!==b&&
        Math.max(x1,x2)>r.l-c&&Math.min(x1,x2)<r.r+c&&
        Math.max(y1,y2)>r.t-c&&Math.min(y1,y2)<r.b+c); };
    const try_=(p,q)=>clear(p[0],p[1],q[0],q[1])?[p,q]:null;
    if(ov(a.t,a.b,b.t,b.b)>24){
      const y=Math.round((Math.max(a.t,b.t)+Math.min(a.b,b.b))/2);
      if(b.l-a.r>=MINRUN)return try_([a.r+END,y],[b.l-END,y]);
      if(a.l-b.r>=MINRUN)return try_([a.l-END,y],[b.r+END,y]);
    }
    if(ov(a.l,a.r,b.l,b.r)>24){
      const x=Math.round((Math.max(a.l,b.l)+Math.min(a.r,b.r))/2);
      if(b.t-a.b>=MINRUN)return try_([x,a.b+END],[x,b.t-END]);
      if(a.t-b.b>=MINRUN)return try_([x,a.t-END],[x,b.b+END]);
    }
    return null;
  }

  // Концы маршрута по сетке стоят на обводном коридоре, в GAP от карточки, и крайний
  // отрезок часто идёт ВДОЛЬ её грани — наконечник тогда смотрит мимо. Поэтому к пути
  // достраивается короткий заход перпендикулярно грани, до END от неё.
  function stub(pt,r){
    const [x,y]=pt, d=GAP-END, inside=(v,lo,hi)=>v>lo&&v<hi;
    if(Math.abs(y-(r.t-GAP))<1.5&&inside(x,r.l-GAP,r.r+GAP))return [x,y+d];
    if(Math.abs(y-(r.b+GAP))<1.5&&inside(x,r.l-GAP,r.r+GAP))return [x,y-d];
    if(Math.abs(x-(r.l-GAP))<1.5&&inside(y,r.t-GAP,r.b+GAP))return [x+d,y];
    if(Math.abs(x-(r.r+GAP))<1.5&&inside(y,r.t-GAP,r.b+GAP))return [x-d,y];
    return null;
  }
  // Заход не достраивается, если он налезет на уже проложенную стрелку: лучше
  // короткий конец в GAP от карточки, чем лишнее пересечение.
  function ends(pts,a,b,other){
    const axis=(p,q)=>p[0]===q[0]?'v':'h';
    const ok=(p,q)=>!other.some(o=>
      Math.max(p[0],q[0])>=Math.min(o.x1,o.x2)&&Math.min(p[0],q[0])<=Math.max(o.x1,o.x2)&&
      Math.max(p[1],q[1])>=Math.min(o.y1,o.y2)&&Math.min(p[1],q[1])<=Math.max(o.y1,o.y2));
    const s=stub(pts[0],a);
    if(s&&ok(s,pts[0])){ if(axis(pts[0],s)===axis(pts[0],pts[1]))pts[0]=s; else pts.unshift(s); }
    const n=pts.length-1, e=stub(pts[n],b);
    if(e&&ok(pts[n],e)){ if(axis(pts[n],e)===axis(pts[n-1],pts[n]))pts[n]=e; else pts.push(e); }
    return pts;
  }

  function route(g,a,b,busy,laid){
    const before=laid.length;   // что было проложено до нас — мимо этого ведём концы
    const d=direct(g,a,b);
    if(d){ laid.push({x1:d[0][0],y1:d[0][1],x2:d[1][0],y2:d[1][1],
                      dir:d[0][0]===d[1][0]?'v':'h'}); return d; }
    const A=ports(g,a), B=ports(g,b);
    if(!A.length||!B.length)return null;
    const pen=penalties(g,busy,laid);
    const goal={}; B.forEach(p=>goal[p.n]=p);
    const dist=new Map(), prev=new Map();
    const key=(n,d)=>n+'|'+d;
    const pq=[];
    const push=(n,d,cost,from)=>{
      const k=key(n,d);
      if(dist.has(k)&&dist.get(k)<=cost)return;
      dist.set(k,cost); prev.set(k,from); pq.push({n:n,d:d,c:cost});
    };
    A.forEach(p=>push(p.n,p.dir,0,null));
    let best=null,bestC=Infinity;
    while(pq.length){
      pq.sort((x,y)=>x.c-y.c);
      const cur=pq.shift(), k=key(cur.n,cur.d);
      if(dist.get(k)<cur.c)continue;
      if(goal[cur.n]!==undefined && cur.c<bestC){ bestC=cur.c; best=k; continue; }
      for(const e of (g.adj.get(cur.n)||[])){
        let c=cur.c+e.len;
        if(e.dir!==cur.d)c+=TURN;
        if(pen.has(e.key))c+=pen.get(e.key);
        push(e.to,e.dir,c,k);
      }
    }
    if(!best)return null;
    const chain=[]; let k=best;
    while(k){ chain.push(k); k=prev.get(k); }
    chain.reverse();
    const nodes=chain.map(s=>+s.split('|')[0]);
    const pts=nodes.map(n=>[g.xs[Math.floor(n/g.ys.length)], g.ys[n%g.ys.length]]);
    // отмечаем занятые рёбра, чтобы следующая стрелка выбрала соседний коридор,
    // и запоминаем сам путь — по нему считается штраф за пересечение поперёк
    for(let i=1;i<pts.length;i++){
      const [x1,y1]=pts[i-1],[x2,y2]=pts[i];
      if(x1===x2){
        const i0=g.xi[x1], j0=Math.min(g.yi[y1],g.yi[y2]), j1=Math.max(g.yi[y1],g.yi[y2]);
        for(let j=j0;j<j1;j++){const k='v'+i0+':'+j; busy.set(k,(busy.get(k)||0)+1);}
      }else{
        const j0=g.yi[y1], i0=Math.min(g.xi[x1],g.xi[x2]), i1=Math.max(g.xi[x1],g.xi[x2]);
        for(let i2=i0;i2<i1;i2++){const k='h'+j0+':'+i2; busy.set(k,(busy.get(k)||0)+1);}
      }
      laid.push({x1:x1,y1:y1,x2:x2,y2:y2,dir:x1===x2?'v':'h'});
    }
    return ends(simplify(pts),a,b,laid.slice(0,before));
  }
  // убираем промежуточные точки на одной прямой — путь из сетки идёт мелкими шагами
  function simplify(pts){
    const out=[pts[0]];
    for(let i=1;i<pts.length-1;i++){
      const p=out[out.length-1],c=pts[i],n=pts[i+1];
      const col=(p[0]===c[0]&&c[0]===n[0])||(p[1]===c[1]&&c[1]===n[1]);
      if(!col)out.push(c);
    }
    out.push(pts[pts.length-1]);
    return out;
  }
  const dstr=pts=>'M'+pts.map(p=>p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' L');

  function draw(){
    tune();
    while(svg.firstChild)svg.removeChild(svg.firstChild);
    const gb=grid.getBoundingClientRect();
    const R=el=>{const r=el.getBoundingClientRect();
      return {el:el,l:r.left-gb.left,t:r.top-gb.top,
              r:r.left-gb.left+r.width,b:r.top-gb.top+r.height,
              cx:r.left-gb.left+r.width/2,cy:r.top-gb.top+r.height/2};};
    const rects=[...grid.querySelectorAll('.pstep')].map(R);
    if(!rects.length)return;
    const byId={};for(const r of rects)byId[r.el.dataset.sid]=r;
    const W=grid.scrollWidth,H=grid.scrollHeight;
    svg.setAttribute('viewBox','0 0 '+W+' '+H);
    svg.setAttribute('width',W); svg.setAttribute('height',H);
    const defs=document.createElementNS(NS,'defs');
    defs.innerHTML='<marker id="ah" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="6.5"'
      +' markerHeight="6.5" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"/></marker>';
    svg.appendChild(defs);
    const g=build(rects,W,H);
    const busy=new Map(), laid=[];
    // короткие связи прокладываем первыми: они занимают прямые пути, длинные обходят
    const list=flows.map((f,i)=>({f:f,i:i})).filter(o=>byId[o.f.a]&&byId[o.f.b]);
    list.sort((p,q)=>{
      const m=o=>Math.abs(byId[o.f.a].cx-byId[o.f.b].cx)+Math.abs(byId[o.f.a].cy-byId[o.f.b].cy);
      return m(p)-m(q);
    });
    for(const o of list){
      const f=o.f, a=byId[f.a], b=byId[f.b];
      const pts=route(g,a,b,busy,laid);
      if(!pts||pts.length<2)continue;
      const p=document.createElementNS(NS,'path');
      p.setAttribute('d',dstr(pts));
      p.setAttribute('class','fl'+(f.kind==='par'?' par':''));
      p.setAttribute('marker-end','url(#ah)');
      svg.appendChild(p);
      if(f.label){
        // подпись — на самом длинном отрезке, там она не налезает на соседние
        let bi=1,bl=-1;
        for(let i=1;i<pts.length;i++){
          const L=Math.abs(pts[i][0]-pts[i-1][0])+Math.abs(pts[i][1]-pts[i-1][1]);
          if(L>bl){bl=L;bi=i;}
        }
        const mx=(pts[bi][0]+pts[bi-1][0])/2, my=(pts[bi][1]+pts[bi-1][1])/2;
        const tx=document.createElementNS(NS,'text');
        tx.setAttribute('x',mx);tx.setAttribute('y',my-5);
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

    script = (f'const API_BASE="/api/d/{deal["slug"]}/review/process";\n'
              + REVIEW_JS + FLOW_JS)
    return shell(deal, "Процесс", "process", body, script)
