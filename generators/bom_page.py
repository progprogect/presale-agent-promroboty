"""CSPL-генератор: bom.yaml -> страница согласования состава комплекта (Tabler).

Поля позиции: pos, model, qty, why, price, conf, price_note (обязательны pos/model/qty).
Необязательные: group (категория — сворачиваемая секция с итогом), range [мин, макс] (вилка цены,
BYN), conf_label (своя подпись уверенности), weeks [мин, макс] (срок поставки, недель).

Если у сделки есть схема компоновки (bom["schematic"]: title, views[{id,title,svg}],
positions[{pos,name,rows[]}]), она показывается над составом: наведение на позицию схемы
подсвечивает её строки состава и наоборот (rows — номера строк, 1-based).
"""
import json

from .common import ICON_MIC, REVIEW_JS, esc, savebar, shell

CONF = {
    "high": ("подтверждена", "bg-green-lt"),
    "mid": ("с сайта", "bg-blue-lt"),
    "low": ("оценка · RFQ", "bg-orange-lt"),
}


def fmt_p(v) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def _price_cell(price, rng) -> str:
    main = fmt_p(price) if price else "—"
    if rng and rng[0] != rng[1]:
        main += f'<span class="rng">{fmt_p(rng[0])}–{fmt_p(rng[1])}</span>'
    return main


def _weeks(w) -> str:
    if not w:
        return "—"
    return str(w[0]) if w[0] == w[1] else f"{w[0]}–{w[1]}"


# Перекрёстная подсветка «схема <-> строки состава»: наведение — временная, клик — закреплённая
# (держится после скролла, пока не кликнуть другую позицию, ту же или Esc).
SCHEMATIC_JS = r"""
const P2R=window.POS2ROWS||{},POSNAME=window.POSNAME||{},R2P={};
Object.entries(P2R).forEach(([p,rows])=>rows.forEach(r=>{(R2P[r]=R2P[r]||[]).push(p);}));
const tip=document.createElement('div');tip.id='postip';document.body.appendChild(tip);
function posSet(p,cls,on){
  document.querySelectorAll('[data-pos="'+p+'"]').forEach(el=>el.classList.toggle(cls,on));
  (P2R[p]||[]).forEach(r=>document.querySelectorAll('tr[data-row="'+r+'"]')
    .forEach(el=>el.classList.toggle(cls,on)));
}
let pinned=null;
function pin(p,scrollRow){
  if(pinned)posSet(pinned,'pin',false);
  if(pinned===p){pinned=null;return;}
  pinned=p;posSet(p,'pin',true);
  if(scrollRow){
    const rows=P2R[p]||[];if(!rows.length)return;
    const tr=document.querySelector('tr[data-row="'+rows[0]+'"]');if(!tr)return;
    document.querySelectorAll('tr.grp.closed').forEach(h=>{
      if(h.dataset.grp===tr.dataset.grp)toggleGroup(h);});
    tr.scrollIntoView({behavior:'smooth',block:'center'});
  }
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&pinned)pin(pinned);});
let cur=null;
document.addEventListener('pointerover',e=>{
  const g=e.target.closest('svg [data-pos], .sref');
  const tr=g?null:e.target.closest('tr[data-row]');
  const key=g?('p'+g.dataset.pos):(tr?('r'+tr.dataset.row):null);
  if(key===cur)return;
  if(cur){cur[0]==='p'?posSet(cur.slice(1),'hl',false):(R2P[cur.slice(1)]||[]).forEach(p=>posSet(p,'hl',false));}
  cur=key;
  if(g){posSet(g.dataset.pos,'hl',true);
    tip.textContent=g.dataset.pos+' — '+(POSNAME[g.dataset.pos]||'');tip.style.opacity=1;}
  else if(tr&&R2P[tr.dataset.row]){(R2P[tr.dataset.row]).forEach(p=>posSet(p,'hl',true));tip.style.opacity=0;}
  else tip.style.opacity=0;
});
document.addEventListener('pointermove',e=>{
  tip.style.left=Math.min(e.clientX+14,innerWidth-340)+'px';
  tip.style.top=(e.clientY+16)+'px';});
document.querySelectorAll('svg [data-pos]').forEach(g=>{
  g.addEventListener('click',()=>pin(g.dataset.pos,true));
});
document.querySelectorAll('.sref').forEach(b=>{
  b.addEventListener('click',e=>{e.stopPropagation();pin(b.dataset.pos,false);
    const v=document.querySelector('.schfig svg [data-pos="'+b.dataset.pos+'"]');
    if(v&&pinned===b.dataset.pos)v.scrollIntoView({behavior:'smooth',block:'center'});});
});
"""

GROUP_JS = r"""
function toggleGroup(h){
  const closed=h.classList.toggle('closed');
  document.querySelectorAll('tr[data-grp="'+h.dataset.grp+'"]:not(.grp)')
    .forEach(r=>r.hidden=closed);
}
document.querySelectorAll('tr.grp').forEach(h=>{h.onclick=()=>toggleGroup(h);});
"""


def _schematic_block(sch: dict) -> tuple[str, str]:
    views = [v for v in sch.get("views", []) if v.get("svg")]
    if not views:
        return "", ""
    figs = "".join(f"""
  <div class="card mt-2"><div class="card-body py-3">
    <h3 class="schv">{esc(v.get("title", v["id"]))}</h3>
    <div class="schfig">{v["svg"]}</div>
  </div></div>""" for v in views)
    block = f"""
  <p class="hint">Сверху — схема компоновки: наведение на номер или объект подсвечивает его строки
  в составе ниже (и наоборот). Клик по схеме закрепляет подсветку и ведёт к строке; синий кружок
  с номером в строке — эта же позиция на схеме, клик по нему ведёт обратно к схеме. Esc снимает выбор.</p>
  {figs}
  <div class="card mt-2"><div class="card-body py-2">
    <div class="cbox" style="max-width:none">
      <textarea class="form-control" data-ckey="компоновка в целом"
        placeholder="Компоновка в целом: что стоит не на месте, где тесно, чего не хватает…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="компоновка в целом" title="Надиктовать">{ICON_MIC}</button>
    </div>
  </div></div>"""
    pos2rows = {str(p["pos"]): p.get("rows", []) for p in sch.get("positions", [])}
    posname = {str(p["pos"]): p.get("name", "") for p in sch.get("positions", [])}
    js = (f"window.POS2ROWS={json.dumps(pos2rows, ensure_ascii=False)};"
          f"window.POSNAME={json.dumps(posname, ensure_ascii=False)};" + SCHEMATIC_JS)
    return block, js


TIER_LABELS = {1: "Основное оборудование", 2: "Обеспечение и вспомогательное",
               3: "Расходники и ЗИП"}


def render(deal: dict, bom: dict) -> str:
    items = bom["items"]
    has_weeks = any(i.get("weeks") for i in items)
    ncols = 7 if has_weeks else 6

    # номера позиций схемы у строк состава (обратный маппинг rows -> pos)
    row2pos: dict[int, list[str]] = {}
    for p in (bom.get("schematic") or {}).get("positions", []):
        for r in p.get("rows", []):
            row2pos.setdefault(r, []).append(str(p["pos"]))

    # категории: позиции группируются по полю group в порядке появления (уже отсортированы по tier)
    groups: list[tuple[str, int, list[tuple[int, dict]]]] = []
    for i, item in enumerate(items, 1):
        g = item.get("group") or "Прочее"
        t = item.get("tier", 1)
        if not groups or groups[-1][0] != g:
            groups.append((g, t, []))
        groups[-1][2].append((i, item))

    tier_labels = {**TIER_LABELS, **{int(k): v for k, v in (bom.get("tier_labels") or {}).items()}}
    show_tiers = len({t for _, t, _ in groups}) > 1
    rows = []
    total = lo_t = hi_t = 0
    cur_tier = None
    for gi, (gname, gtier, gitems) in enumerate(groups):
        if show_tiers and gtier != cur_tier:
            cur_tier = gtier
            rows.append(f'\n      <tr class="tiersep"><td colspan="{ncols}">{esc(tier_labels[gtier])}</td></tr>')
        g_tot = g_lo = g_hi = 0
        g_rows = []
        for i, item in gitems:
            key = f"bom-{i}"
            price = item.get("price")
            rng = item.get("range")
            g_tot += price or 0
            g_lo += rng[0] if rng else (price or 0)
            g_hi += rng[1] if rng else (price or 0)
            conf = item.get("conf")
            label, cls = CONF.get(conf, ("", ""))
            label = item.get("conf_label", label)
            conf_html = (f'<span class="badge {cls}" title="{esc(item.get("price_note", ""))}">{esc(label)}</span>'
                         if conf else "")
            weeks_td = f'<td class="num">{_weeks(item.get("weeks"))}</td>' if has_weeks else ""
            why = f'<span class="res">{esc(item["why"])}</span>' if item.get("why") else ""
            srefs = "".join(f'<span class="sref" data-pos="{p}" title="Позиция {p} на схеме">{p}</span>'
                            for p in row2pos.get(i, []))
            g_rows.append(f"""
      <tr data-row="{i}" data-grp="g{gi}">
        <td class="pkg">{srefs}{esc(item["pos"])}{why}</td>
        <td>{esc(item["model"])}</td>
        <td class="num">{esc(str(item["qty"]))}</td>
        <td class="num">{_price_cell(price, rng)}</td>
        <td>{conf_html}</td>
        {weeks_td}
        <td><input class="form-control form-control-sm" data-akey="{key}"
          placeholder="Дешевле / замена / замечание"></td>
      </tr>""")
        total += g_tot
        lo_t += g_lo
        hi_t += g_hi
        g_sum = fmt_p(g_tot) + (f" ({fmt_p(g_lo)}–{fmt_p(g_hi)})" if round(g_lo) != round(g_hi) else "")
        rows.append(f'\n      <tr class="grp" data-grp="g{gi}"><td colspan="{ncols}">'
                    f'<span class="chev">▾</span> {esc(gname)}'
                    f'<span class="st-sum">{len(gitems)} поз. · {g_sum} BYN</span></td></tr>')
        rows += g_rows

    weeks_th = '<th class="num">Срок, нед</th>' if has_weeks else ""
    total_rng = (f'<span class="rng">{fmt_p(lo_t)}–{fmt_p(hi_t)}</span>'
                 if round(lo_t) != round(hi_t) else "")
    sch_block, sch_js = _schematic_block(bom.get("schematic") or {})
    body = f"""{sch_block}
  <p class="hint">Цены — закупка без наценки, BYN, за позицию целиком; серым под ценой — вилка.
  Заголовок категории сворачивает её строки, рядом — итог категории. Знаете, где дешевле
  или лучше, — впишите в правую колонку: наш выбор не затирается, предложения лягут отдельным слоем.</p>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix" style="min-width:980px">
    <thead><tr>
      <th>Позиция · зачем так</th><th>Модель</th><th class="num">Кол-во</th>
      <th class="num">Цена, BYN</th><th>Цена</th>{weeks_th}<th style="width:26%">Предложение валидатора</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    <tfoot><tr><td colspan="3">Итого закупка и внешние услуги</td>
      <td class="num">{fmt_p(total)}{total_rng}</td><td colspan="{ncols - 4}"></td></tr></tfoot>
  </table>
  </div></div>
  {savebar()}"""

    script = (f'const API_BASE="/api/d/{deal["slug"]}/review/bom";\n'
              + REVIEW_JS + GROUP_JS + sch_js)
    return shell(deal, "Компоненты", "bom", body, script)
