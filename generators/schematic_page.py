"""CSPL-генератор: schematic.yaml -> страница «Схема» (компоновка: изометрия, план, бок).

Спека приходит из сделки (iso-scheme пишет portal.spec.yaml, from_lead переносит его
как schematic.yaml + SVG-файлы в data/deals/<slug>/schematic/):
  title, views[{id, title, file, svg}], positions[{pos, name, bom[]}].
SVG размечены группами .pobj/.pnum с data-pos — наведение подсвечивает позицию на всех
видах и в экспликации; клик открывает комментарий к позиции. Комментарии уходят тем же
слоем правок, что на остальных страницах.
"""
from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

HOVER_JS = r"""
const POSNAME={};document.querySelectorAll('tr[data-pos]').forEach(tr=>{
  POSNAME[tr.dataset.pos]=tr.dataset.name||'';});
const tip=document.createElement('div');tip.id='postip';document.body.appendChild(tip);
function setHL(p,on){document.querySelectorAll('[data-pos="'+p+'"]').forEach(el=>el.classList.toggle('hl',on));}
let curhl=null;
document.addEventListener('pointerover',e=>{
  const g=e.target.closest('[data-pos]');
  if(g===curhl)return;
  if(curhl)setHL(curhl.dataset.pos,false);
  curhl=g;
  if(g){setHL(g.dataset.pos,true);
    tip.textContent=g.dataset.pos+' — '+(POSNAME[g.dataset.pos]||'');
    tip.style.opacity=1;
  }else tip.style.opacity=0;
});
document.addEventListener('pointermove',e=>{
  tip.style.left=Math.min(e.clientX+14,innerWidth-340)+'px';
  tip.style.top=(e.clientY+16)+'px';});
// клик по объекту или номеру на схеме -> строка экспликации + комментарий
document.querySelectorAll('svg [data-pos]').forEach(g=>{
  g.addEventListener('click',()=>{
    const tr=document.querySelector('tr[data-pos="'+g.dataset.pos+'"]');if(!tr)return;
    tr.scrollIntoView({behavior:'smooth',block:'center'});
    const c=document.getElementById('crow-p'+g.dataset.pos);if(c)c.hidden=false;
    setHL(g.dataset.pos,true);
  });
});
"""


def render(deal: dict, spec: dict) -> str:
    views = [v for v in spec.get("views", []) if v.get("svg")]
    figs = "".join(f"""
  <div class="card mt-2"><div class="card-body py-3">
    <h3 class="schv">{esc(v.get("title", v["id"]))}</h3>
    <div class="schfig">{v["svg"]}</div>
  </div></div>""" for v in views)

    has_bom = any(p.get("bom") for p in spec.get("positions", []))
    rows = []
    for p in spec.get("positions", []):
        n, name = p["pos"], p.get("name", "")
        bomcell = f'<td class="bomref">{esc(", ".join(p.get("bom") or []))}</td>' if has_bom else ""
        ckey = f"поз. {n} · {name}"
        rows.append(f"""
    <tr data-pos="{n}" data-name="{esc(name)}">
      <td class="num">{n}</td><td>{esc(name)}</td>{bomcell}
      <td class="num"><button class="btn btn-ghost-secondary btn-icon cmt-toggle" data-id="p{n}"
        title="Комментарий">{ICON_COMMENT}</button></td>
    </tr>
    <tr class="crow" id="crow-p{n}" hidden><td colspan="{4 if has_bom else 3}"><div class="cbox">
      <textarea class="form-control" data-ckey="{esc(ckey)}"
        placeholder="Что не так с этой позицией: место, габарит, подход, лишнее/не хватает…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="{esc(ckey)}" title="Надиктовать">{ICON_MIC}</button>
    </div></td></tr>""")
    bom_th = "<th>BOM</th>" if has_bom else ""

    body = f"""
  <p class="hint">Компоновка условными объёмами — где что стоит и как связано с составом:
  наименования позиций совпадают с вкладкой «Компоненты». Наведите на номер, объект или строку
  экспликации — позиция подсветится на всех видах; клик по схеме открывает комментарий к позиции.</p>
  {figs}
  <div class="card mt-2"><div class="card-body py-3">
    <h3 class="schv">Экспликация</h3>
    <div class="tablebox"><table class="table table-sm expl">
      <thead><tr><th class="num">№</th><th>Наименование</th>{bom_th}<th></th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>
  </div></div>
  <div class="card mt-2"><div class="card-body py-2">
    <div class="cbox" style="max-width:none">
      <textarea class="form-control" data-ckey="компоновка в целом"
        placeholder="Компоновка в целом: что мешает обслуживанию, где тесно, чего не хватает…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="компоновка в целом" title="Надиктовать">{ICON_MIC}</button>
    </div>
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/schematic";\n' + REVIEW_JS + HOVER_JS
    return shell(deal, "Схема", "schematic", body, script)
