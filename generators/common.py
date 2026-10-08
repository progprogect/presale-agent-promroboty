"""CSPL: общий каркас страниц портала (Tabler, компактный стиль).

Генераторы детерминированы: одна спека -> один и тот же HTML. Без LLM и сети.
"""
from html import escape as esc  # noqa: F401  (реэкспорт для генераторов)

# Карточка проекта: порядок вкладок и подписи. Вкладка показывается, если у сделки есть её спека.
PAGES = [
    ("package", "Обзор"),
    ("questions", "Вводные"),
    ("process", "Процесс"),
    ("solution", "Решение"),
    ("wbs", "Декомпозиция"),
    ("bom", "Компоненты"),
    ("proposal", "ТКП"),
]
PAGE_IDS = [p for p, _ in PAGES]

# Небольшие правки поверх Tabler: плотнее таблицы, элементы матрицы WBS.
EXTRA_CSS = """
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 56px}
.pagehead{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;margin-bottom:4px}
.pagehead h2{margin:0}
.pagehead .chips{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.hint{font-size:12.5px;color:var(--tblr-secondary);margin:0 0 12px}
/* Атрибут hidden обязан скрывать: у Tabler .alert{display:block} перебивал его,
   из-за чего памятка «Как работать?» висела открытой всегда */
[hidden]{display:none!important}
.tablebox{overflow-x:auto}
table.matrix{min-width:980px;font-variant-numeric:tabular-nums;font-size:13px}
table.matrix th,table.matrix td{padding:6px 8px}
th.num,td.num{text-align:center;white-space:nowrap}
td.sum{text-align:center;font-weight:600}
tr.stage>td{background:var(--tblr-bg-surface-secondary);font-weight:600;cursor:pointer;user-select:none;font-size:12.5px}
tr.stage .chev{display:inline-block;width:13px;transition:transform .15s;color:var(--tblr-secondary)}
tr.stage.closed .chev{transform:rotate(-90deg)}
tr.stage .st-sum{float:right;color:var(--tblr-secondary);font-weight:500}
td.pkg{min-width:210px;font-weight:500}
td.pkg .res{display:block;font-weight:400;color:var(--tblr-secondary);font-size:11.5px;max-width:34ch}
.step{display:inline-flex;align-items:center;gap:1px}
.step .val{min-width:26px;text-align:center;font-weight:500}
.step .btn-icon{width:20px;height:20px;min-height:0;font-size:12px;padding:0}
tr.grp td{background:var(--tblr-bg-surface-tertiary);color:var(--tblr-secondary);
  font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;padding:3px 10px;
  cursor:pointer;user-select:none}
tr.grp .chev{display:inline-block;width:13px;transition:transform .15s}
tr.grp.closed .chev{transform:rotate(-90deg)}
tr.grp .st-sum{float:right;font-weight:500;text-transform:none;letter-spacing:0}
td.locked{background:var(--tblr-bg-surface-secondary);color:var(--tblr-secondary);font-weight:500}
td.changed{background:var(--tblr-blue-lt)}
td.changed .was{display:block;font-size:10px;color:var(--tblr-blue)}
td.none{color:var(--tblr-border-color);text-align:center}
tr.crow td{padding:8px 10px;background:var(--tblr-bg-surface-tertiary)}
.cbox{display:flex;gap:6px;align-items:flex-start;max-width:680px}
.cbox textarea{min-height:44px;font-size:12.5px}
tfoot td{font-weight:600;text-align:center}
tfoot td:first-child{text-align:left;color:var(--tblr-secondary);font-weight:500}
.icon-14{width:14px;height:14px;stroke-width:1.75}
.step.zero .val,.step.zero button:first-child{display:none}
.step.zero button:last-child{color:var(--tblr-border-color)}
.step.zero button:last-child:hover{color:var(--tblr-primary)}
tr.newtask td{background:var(--tblr-orange-lt)}
tr.newtask input[type=number]{padding:2px 4px;text-align:center}
tr.stageio td{background:var(--tblr-bg-surface-tertiary);padding:10px 12px}
.io2{display:flex;gap:18px;flex-wrap:wrap;font-size:12px}
.io2>div{flex:1;min-width:240px}
.io2 b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--tblr-secondary);margin-bottom:3px}
.io2 ul{margin:0;padding-left:16px}
.io2 li{margin:1px 0}
.io2 .cbox{margin-top:6px;max-width:none}
.legend{font-size:12px;color:var(--tblr-secondary);margin:0 0 10px}
.legend b{color:var(--tblr-body-color)}
#tips{font-size:12.5px}
#tips ul{margin:4px 0 0;padding-left:18px}
#tips li{margin:2px 0}
.ctx{margin:0 0 14px;font-size:12.5px}
.ctx .ask{border:1px solid var(--tblr-border-color);border-left:3px solid var(--tblr-primary);
  border-radius:6px;background:var(--tblr-bg-surface);padding:10px 14px}
.ctx b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--tblr-secondary);margin-bottom:4px}
.ctx ul{margin:0;padding-left:18px}
.ctx li{margin:2px 0;line-height:1.45}
.ctx .more{margin-top:6px}
.ctx .more summary{cursor:pointer;color:var(--tblr-secondary);font-size:11.5px;
  padding:4px 2px;list-style:none;user-select:none}
.ctx .more summary::marker,.ctx .more summary::-webkit-details-marker{display:none}
.ctx .more summary::before{content:"▸ ";display:inline-block;transition:transform .15s}
.ctx .more[open] summary::before{content:"▾ "}
.ctx .more summary:hover{color:var(--tblr-primary)}
.ctx .more p{margin:4px 0 6px;color:var(--tblr-secondary);line-height:1.5}
.ctx .note{color:var(--tblr-secondary);font-size:11.5px}
/* Служебные поля вводного — под раскрытием: при беглом просмотре они только мешают */
.qmeta{margin-top:4px}
.qmeta summary{cursor:pointer;color:var(--tblr-secondary);font-size:11px;padding:2px 0;
  list-style:none;user-select:none}
.qmeta summary::marker,.qmeta summary::-webkit-details-marker{display:none}
.qmeta summary::before{content:"▸ "}
.qmeta[open] summary::before{content:"▾ "}
.qmeta summary:hover{color:var(--tblr-primary)}
/* Решение проверяющего — главное действие на карточке, его видно сразу */
.verdict{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;padding-top:8px;
  border-top:1px dashed var(--tblr-border-color)}
.verdict label{display:flex;align-items:center;gap:6px;font-size:12.5px;cursor:pointer;margin:0}
tr.optsep td{background:var(--tblr-orange-lt);color:var(--tblr-orange);font-size:11.5px;font-weight:600;
  padding:5px 10px;border-top:2px solid var(--tblr-border-color)}
.rng{display:block;font-size:10.5px;color:var(--tblr-secondary);font-weight:400}
.savebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:14px}
.savebar input{max-width:200px}
.savebar .status{font-size:12px;color:var(--tblr-secondary)}

/* Вводные: вопрос = карточка-строка с вердиктом валидатора */
.qrow{border-top:1px solid var(--tblr-border-color);padding:9px 0}
.qrow:first-child{border-top:0}
.qhead{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
.qhead .qid{font-weight:600;font-size:12px;color:var(--tblr-secondary);min-width:30px}
.qhead .qt{font-weight:600;font-size:13px}
.qbody{margin:3px 0 0 38px;font-size:12.5px}
.qbody .ans{margin:0}
.qbody .meta{color:var(--tblr-secondary);font-size:11.5px;margin:2px 0 0}
.qbody .meta b{color:var(--tblr-body-color);font-weight:600}
.verdict{display:flex;gap:10px;align-items:center;margin:5px 0 0 38px;flex-wrap:wrap}
.verdict label{font-size:12px;display:inline-flex;gap:4px;align-items:center;cursor:pointer;margin:0}

/* Процесс: дорожки участников, шаги по колонкам потока (swimlane) */
.lanes-wrap{overflow-x:auto;padding-bottom:8px}
.lanes{display:grid;gap:0;min-width:100%}
/* заголовки колонок потока */
.lane-col{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.04em;
  color:var(--tblr-secondary);text-align:center;padding:0 8px 8px;align-self:end}
/* имя дорожки — прилипает слева при горизонтальной прокрутке */
.lane-name{display:flex;align-items:center;font-size:11.5px;font-weight:600;padding:10px 10px;
  background:var(--tblr-bg-surface-secondary);min-width:0;position:sticky;left:0;z-index:3;
  border-right:1px solid var(--tblr-border-color);
  box-shadow:3px 0 6px -4px rgba(0,0,0,.18)}
.lane-name small{display:block;font-weight:400;color:var(--tblr-secondary);font-size:10.5px;
  margin-top:2px}
.lane-name.ours{box-shadow:inset 3px 0 0 var(--tblr-primary),3px 0 6px -4px rgba(0,0,0,.18)}
.lane-name.client{box-shadow:inset 3px 0 0 var(--tblr-orange),3px 0 6px -4px rgba(0,0,0,.18)}
.lane-name.human{box-shadow:inset 3px 0 0 var(--tblr-secondary),3px 0 6px -4px rgba(0,0,0,.18)}
/* полоса дорожки: ячейки одной строки образуют сплошную ленту */
.lane-cell{display:flex;flex-direction:column;align-items:stretch;justify-content:flex-start;gap:10px;
  min-width:0;padding:14px 13px;border-bottom:1px solid var(--tblr-border-color)}
.lane-name{border-bottom:1px solid var(--tblr-border-color)}
.lanes .lane-row-alt{background:var(--tblr-bg-surface-secondary);opacity:.35}
.pstep{border:1px solid var(--tblr-border-color);border-radius:6px;padding:7px 9px;font-size:11.5px;
  background:var(--tblr-bg-surface);min-width:0;width:100%;box-sizing:border-box;
  box-shadow:0 1px 2px rgba(0,0,0,.04)}
.pstep .n{font-weight:600;font-size:10.5px;color:var(--tblr-secondary)}
.pstep .t{font-weight:600;display:block;margin:2px 0;line-height:1.25}
.pstep .d{color:var(--tblr-secondary);font-size:10.5px;display:block;line-height:1.35}
.pstep .tm{display:inline-block;margin-top:5px;font-size:10.5px;font-weight:600;
  background:var(--tblr-primary-lt);color:var(--tblr-primary);border-radius:4px;padding:1px 6px}
.pstep.par{border-style:dashed;background:repeating-linear-gradient(135deg,
  transparent,transparent 7px,rgba(0,0,0,.015) 7px,rgba(0,0,0,.015) 14px),var(--tblr-bg-surface)}
.pstep.ours{border-color:var(--tblr-primary)}
.pstep.client{border-color:var(--tblr-orange);background:var(--tblr-orange-lt)}
.pstep.client .tm{background:var(--tblr-orange);color:#fff}
/* Слой стрелок потока: лежит под карточками, кликам не мешает */
.lanes{position:relative}
.flowlayer{position:absolute;left:0;top:0;pointer-events:none;overflow:visible;z-index:0;
  color:var(--tblr-primary)}
.lane-cell,.lane-name{position:relative;z-index:1}
.flowlayer .fl{fill:none;stroke:var(--tblr-primary);stroke-width:1.8;opacity:.9;
  stroke-linejoin:round;stroke-linecap:round}
.flowlayer .fl.par{stroke-dasharray:3 4;opacity:.55}
.flowlayer .fllab{font-size:10.5px;fill:var(--tblr-secondary);text-anchor:middle;
  paint-order:stroke;stroke:var(--tblr-bg-surface);stroke-width:3px}
.cyc{font-size:11.5px;color:var(--tblr-secondary);margin:6px 0 0;padding-left:2px}
.keyfig{font-size:12.5px;font-weight:600;margin:8px 0 0}

/* Решение: лист на одну страницу */
.sheet{font-size:12.5px}
.sheet h3{font-size:13px;margin:14px 0 5px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--tblr-secondary)}
.sheet h3:first-child{margin-top:0}
.sheet p{margin:0 0 6px}
.sheet table{font-size:12px;width:100%}
.sheet table td,.sheet table th{padding:5px 8px;vertical-align:top}
.sheet ul{margin:0;padding-left:18px}
.sheet li{margin:1px 0}
.sheet .shots{display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 0}
.sheet .shots figure{margin:0;max-width:300px}
.sheet .shots img{width:100%;border-radius:5px;border:1px solid var(--tblr-border-color)}
.sheet .shots figcaption{font-size:10.5px;color:var(--tblr-secondary);margin-top:2px}

/* Схема компоновки: инлайн-SVG с подсветкой позиций */
.schv{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--tblr-secondary);margin:0 0 8px}
.schfig{overflow-x:auto}
.schfig svg{display:block;width:100%;height:auto;min-width:700px}
svg g.pobj,svg g.pnum{cursor:pointer}
svg g.pobj.hl,svg g.pobj.pin{filter:drop-shadow(0 0 3px #1f66c4) drop-shadow(0 0 6px rgba(31,102,196,.55))}
svg g.pnum.hl circle,svg g.pnum.pin circle{fill:#1f66c4}
svg g.pnum.hl text,svg g.pnum.pin text{fill:#fff}
tr[data-row].hl>td,tr[data-row].pin>td{background:var(--tblr-blue-lt)}
.sref{display:inline-flex;align-items:center;justify-content:center;min-width:19px;height:19px;
  padding:0 3px;border-radius:50%;border:1.2px solid #1f66c4;color:#1f66c4;background:var(--tblr-bg-surface);
  font:600 10px var(--tblr-font-monospace,monospace);margin:0 4px 2px 0;cursor:pointer;vertical-align:middle}
tr.hl .sref,tr.pin .sref,.sref.hl,.sref.pin{background:#1f66c4;color:#fff}
tr.tiersep td{background:var(--tblr-blue-lt);color:var(--tblr-primary);font-size:11.5px;font-weight:700;
  text-transform:uppercase;letter-spacing:.06em;padding:6px 10px;border-top:2px solid var(--tblr-border-color)}
#postip{position:fixed;pointer-events:none;background:var(--tblr-body-color);color:var(--tblr-bg-surface);
  font-size:12px;padding:4px 9px;border-radius:6px;opacity:0;transition:opacity .12s;z-index:9;max-width:320px}

/* Обзор карточки */
.secrow{display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--tblr-border-color);
  font-size:13px}
.secrow:first-child{border-top:0}
.secrow .nm{font-weight:600;min-width:140px}
.secrow .st{margin-left:auto;font-size:11.5px;color:var(--tblr-secondary);text-align:right}
.gate{border:1px solid var(--tblr-border-color);border-radius:6px;padding:12px 14px;margin-top:14px;
  background:var(--tblr-bg-surface)}
.gate h3{font-size:13px;margin:0 0 4px}
.gate p{font-size:12.5px;margin:0 0 8px;color:var(--tblr-secondary)}
.embed{width:100%;height:78vh;border:1px solid var(--tblr-border-color);border-radius:6px}
"""

ICON_COMMENT = ('<svg class="icon-14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>')
ICON_MIC = ('<svg class="icon-14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>'
            '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>')


def context_block(deal: dict, active: str) -> str:
    """Шапка для валидатора: суть проекта и вопросы к странице (поля context/questions/notes в deal.yaml)."""
    ctx = deal.get("context")
    qs = (deal.get("questions") or {}).get(active) or []
    note = (deal.get("notes") or {}).get(active)
    if not (ctx or qs or note):
        return ""
    # Сверху — только то, что требуется от проверяющего: страница должна начинаться
    # с действия, а не со стены текста. Описание проекта и примечания убраны под раскрытие.
    parts = []
    if qs:
        parts.append('<div class="ask"><b>Что от вас нужно</b><ul>'
                     + "".join(f"<li>{esc(q)}</li>" for q in qs) + "</ul></div>")
    more = []
    if ctx:
        more.append(f"<p>{esc(ctx)}</p>")
    if note:
        more.append(f'<p class="note">{esc(note)}</p>')
    if more:
        parts.append('<details class="more"><summary>О проекте и деталях этой страницы</summary>'
                     + "".join(more) + "</details>")
    return f'<div class="ctx">{"".join(parts)}</div>'


def shell(deal: dict, page_title: str, active: str, body: str, script: str = "") -> str:
    """Каркас страницы: Tabler + шапка сделки + навигация WBS/BOM."""
    def tab(name: str, label: str) -> str:
        cls = " active" if active == name else ""
        return f'<a class="nav-link{cls}" href="/d/{esc(deal["slug"])}/{name}">{label}</a>'

    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{esc(deal["code"])} · {esc(page_title)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/static/tabler.min.css">
<style>{EXTRA_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="pagehead">
    <h2 class="page-title">{esc(deal["title"])}</h2>
    <span class="text-secondary">{esc(deal["code"])}</span>
    <div class="chips">
      <span class="badge bg-azure-lt">{esc(deal["version"])}</span>
      <span class="badge bg-azure-lt">{esc(str(deal["updated"]))}</span>
      <span class="badge bg-yellow-lt">{esc(deal["status"])}</span>
    </div>
  </div>
  <ul class="nav nav-pills mb-2" style="gap:4px">
    {"".join(f'<li class="nav-item">{tab(p, n)}</li>'
             for p, n in PAGES if p in deal.get("pages", PAGE_IDS))}
  </ul>
  {context_block(deal, active)}
  {body}
</div>
<script>{script}</script>
</body>
</html>"""


# Общий JS: степперы Фибоначчи, сворачивание этапов, слой правок и отправка.
REVIEW_JS = r"""
const FIB=[1,2,3,5,8,13,21,34,55,89];
const num=t=>+String(t).replace(',','.');
const fmtH=v=>String(Math.round(v*100)/100).replace('.',',');
function snap(v,dir){
  if(dir>0){if(v<1)return 1;for(const f of FIB)if(f>v)return f;return v+55}
  if(v<=1)return 0;
  for(let i=FIB.length-1;i>=0;i--)if(FIB[i]<v)return FIB[i];return 0;
}
const edits={hours:{},comments:{},alts:{},fields:{},added:[]};
const statusEl=document.getElementById('savestatus');
function setDirty(){statusEl.textContent='есть несохранённые правки';}
function rowSum(tr){
  let t=0;tr.querySelectorAll('.step').forEach(s=>t+=num(s.querySelector('.val').textContent));
  const c=tr.querySelector('.sum');if(c)c.textContent=fmtH(t);
}
function markCell(td,base){
  const s=td.querySelector('.step'),val=s.querySelector('.val');
  const cur=num(val.textContent);
  s.classList.toggle('zero',cur===0);
  td.classList.toggle('changed',cur!==base);
  let was=td.querySelector('.was');
  if(cur!==base){
    if(!was){was=document.createElement('span');was.className='was';td.appendChild(was);}
    was.textContent='было '+fmtH(base);
  }else if(was){was.remove();}
}
document.querySelectorAll('.step').forEach(s=>{
  const td=s.closest('td'),base=num(s.dataset.base),key=s.dataset.key;
  const[minus,plus]=s.querySelectorAll('button'),val=s.querySelector('.val');
  function upd(dir){
    const cur=snap(num(val.textContent),dir);
    val.textContent=fmtH(cur);
    if(cur!==base)edits.hours[key]=cur;else delete edits.hours[key];
    markCell(td,base);rowSum(td.closest('tr'));setDirty();
  }
  minus.onclick=e=>{e.stopPropagation();upd(-1)};
  plus.onclick=e=>{e.stopPropagation();upd(1)};
});
function toggleStage(row){const closed=row.classList.toggle('closed');
  row.parentElement.querySelectorAll('tr.task').forEach(r=>r.hidden=closed);
  if(closed)row.parentElement.querySelectorAll('tr.crow').forEach(r=>r.hidden=true);}
function toggleAll(open){document.querySelectorAll('tr.stage').forEach(r=>{
  r.classList.toggle('closed',!open);
  r.parentElement.querySelectorAll('tr.task').forEach(x=>x.hidden=!open);
  if(!open)r.parentElement.querySelectorAll('tr.crow').forEach(x=>x.hidden=true);});}
document.querySelectorAll('.cmt-toggle').forEach(b=>{
  b.onclick=()=>{const c=document.getElementById('crow-'+b.dataset.id);c.hidden=!c.hidden;};
});
document.querySelectorAll('textarea[data-ckey]').forEach(t=>{
  t.oninput=()=>{if(t.value.trim())edits.comments[t.dataset.ckey]=t.value.trim();
    else delete edits.comments[t.dataset.ckey];setDirty();};
});
document.querySelectorAll('input[data-akey]').forEach(t=>{
  t.oninput=()=>{if(t.value.trim())edits.alts[t.dataset.akey]=t.value.trim();
    else delete edits.alts[t.dataset.akey];setDirty();};
});
// вердикты валидатора: радио «согласен / не согласен», селекты
document.querySelectorAll('[data-fkey]').forEach(el=>{
  el.onchange=()=>{
    const k=el.dataset.fkey;
    if(el.type==='radio'){if(el.checked)edits.fields[k]=el.value;}
    else if(el.value)edits.fields[k]=el.value;else delete edits.fields[k];
    const row=el.closest('.qrow');if(row)row.dataset.verdict=edits.fields[k]||'';
    setDirty();
  };
});
// --- добавление новых задач валидатором ---
const ROLES=(window.PAGE_ROLES||[]);
function addTaskRow(stageIdx, btnRow, data){
  const entry=data||{stage:stageIdx,name:'',hours:{}};
  if(!data)edits.added.push(entry);
  const tr=document.createElement('tr');tr.className='task newtask';
  let cells=`<td class="pkg"><div class="d-flex gap-1">
      <input class="form-control form-control-sm nt-name" placeholder="Новая задача → результат" value="${(entry.name||'').replace(/"/g,'&quot;')}">
      <button class="btn btn-icon btn-ghost-danger nt-del" title="Убрать">×</button></div></td>
    <td><span class="badge bg-orange-lt">новое</span></td>`;
  for(const r of ROLES){
    const v=entry.hours[r]||'';
    cells+=`<td class="num"><input type="number" min="0" step="0.5" class="form-control form-control-sm nt-h" data-role="${r}" value="${v}" style="width:58px;display:inline-block"></td>`;
  }
  cells+='<td class="sum nt-sum"></td><td></td>';
  tr.innerHTML=cells;
  btnRow.parentElement.insertBefore(tr,btnRow);
  const recalc=()=>{let t=0;tr.querySelectorAll('.nt-h').forEach(i=>{
      const v=num(i.value||0);if(v>0)entry.hours[i.dataset.role]=v;else delete entry.hours[i.dataset.role];t+=v;});
    tr.querySelector('.nt-sum').textContent=t?fmtH(t):'';};
  tr.querySelector('.nt-name').oninput=e=>{entry.name=e.target.value;setDirty();};
  tr.querySelectorAll('.nt-h').forEach(i=>i.oninput=()=>{recalc();setDirty();});
  tr.querySelector('.nt-del').onclick=()=>{
    const i=edits.added.indexOf(entry);if(i>=0)edits.added.splice(i,1);tr.remove();setDirty();};
  recalc();
}
document.querySelectorAll('.add-task').forEach(b=>{
  b.onclick=()=>addTaskRow(+b.dataset.stage,b.closest('tr'));
});
// --- версии слоёв ---
let LAYERS=[];
const versel=document.getElementById('versel'),btnRestore=document.getElementById('btn-restore');
function resetAll(){
  document.querySelectorAll('.step').forEach(s=>{
    s.querySelector('.val').textContent=fmtH(num(s.dataset.base));
    markCell(s.closest('td'),num(s.dataset.base));rowSum(s.closest('tr'));});
  document.querySelectorAll('textarea[data-ckey]').forEach(t=>t.value='');
  document.querySelectorAll('input[data-akey]').forEach(t=>t.value='');
  document.querySelectorAll('tr.newtask').forEach(t=>t.remove());
  document.querySelectorAll('[data-fkey]').forEach(el=>{
    if(el.type==='radio')el.checked=false;else el.value='';
    const row=el.closest('.qrow');if(row)row.dataset.verdict='';});
  edits.hours={};edits.comments={};edits.alts={};edits.fields={};edits.added=[];
}
function applyLayer(i){
  resetAll();
  if(i>=0&&LAYERS[i]){
    const L=LAYERS[i];
    Object.entries(L.hours||{}).forEach(([key,v])=>{
      const s=document.querySelector(`.step[data-key="${key}"]`);if(!s)return;
      s.querySelector('.val').textContent=fmtH(v);edits.hours[key]=v;
      markCell(s.closest('td'),num(s.dataset.base));rowSum(s.closest('tr'));});
    Object.entries(L.comments||{}).forEach(([k,v])=>{
      const t=document.querySelector(`textarea[data-ckey="${k}"]`);
      if(t){t.value=v;edits.comments[k]=v;const row=t.closest('tr.crow');if(row)row.hidden=false;}});
    Object.entries(L.alts||{}).forEach(([k,v])=>{
      const t=document.querySelector(`input[data-akey="${k}"]`);if(t){t.value=v;edits.alts[k]=v;}});
    Object.entries(L.fields||{}).forEach(([k,v])=>{
      const els=document.querySelectorAll(`[data-fkey="${k}"]`);
      els.forEach(el=>{if(el.type==='radio')el.checked=(el.value===v);else el.value=v;
        const row=el.closest('.qrow');if(row)row.dataset.verdict=v;});
      if(els.length)edits.fields[k]=v;});
    (L.added||[]).forEach(a=>{
      const b=document.querySelector(`.add-task[data-stage="${a.stage}"]`);
      const entry={stage:a.stage,name:a.name,hours:{...a.hours}};edits.added.push(entry);
      if(b)addTaskRow(a.stage,b.closest('tr'),entry);});
  }
  if(btnRestore)btnRestore.hidden=!(LAYERS.length&&i<LAYERS.length-1);
  statusEl.textContent=i<0?(LAYERS.length?'показана исходная версия':'исходная версия — правки лягут слоем, ничего не затирается')
    :'версия '+(i+1)+' от '+(LAYERS[i].reviewer||'?')+' · '+(LAYERS[i].ts||'').slice(0,16).replace('T',' ');
}
function fillVersel(sel){
  if(!versel)return;
  versel.innerHTML='<option value="-1">Исходная</option>'+LAYERS.map((l,i)=>
    `<option value="${i}">v${i+1} · ${(l.reviewer||'?')} · ${(l.ts||'').slice(5,16).replace('T',' ')}${l.done?' ✓':''}</option>`).join('');
  versel.value=String(sel);
}
if(versel)versel.onchange=()=>applyLayer(+versel.value);
if(btnRestore)btnRestore.onclick=()=>send(false,' (восстановление v'+(+versel.value+1)+')');
async function send(done,note){
  const reviewer=document.getElementById('reviewer').value.trim();
  if(!reviewer){statusEl.textContent='укажите имя';return;}
  try{localStorage.setItem('reviewer',reviewer);}catch(e){}
  const body={reviewer:reviewer+(note||''),done,...edits,
    added:edits.added.filter(a=>a.name&&Object.keys(a.hours).length)};
  const r=await fetch(API_URL,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)});
  if(r.ok){
    LAYERS.push({...body,ts:new Date().toISOString()});
    fillVersel(LAYERS.length-1);if(btnRestore)btnRestore.hidden=true;
    statusEl.textContent=done?'проверка завершена — спасибо!':'сохранено как v'+LAYERS.length;
  }else statusEl.textContent='ошибка сохранения';
}
document.getElementById('btn-save').onclick=()=>send(false);
document.getElementById('btn-done').onclick=()=>send(true);
try{const n=localStorage.getItem('reviewer');if(n)document.getElementById('reviewer').value=n;}catch(e){}
// персональная ссылка (?u=<токен>): имя валидатора подставляется само
const uTok=new URLSearchParams(location.search).get('u');
if(uTok)fetch('/api/u/'+uTok).then(r=>r.ok?r.json():null).then(d=>{
  if(d&&d.name){const el=document.getElementById('reviewer');
    if(el)el.value=d.name;try{localStorage.setItem('reviewer',d.name);}catch(e){}}});
// подсказки
const tipsBtn=document.getElementById('tips-btn'),tips=document.getElementById('tips');
if(tipsBtn&&tips){
  // Свёрнута по умолчанию: главное («Что от вас нужно») и так наверху страницы,
  // а механика сохранения нужна по запросу и раньше занимала первый экран.
  let open=false;try{open=localStorage.getItem('tips_open')==='1';}catch(e){}
  tips.hidden=!open;
  tipsBtn.onclick=()=>{
    tips.hidden=!tips.hidden;
    try{localStorage.setItem('tips_open',tips.hidden?'0':'1');}catch(e){}
  };
}
// загрузка слоёв
(async()=>{
  try{
    const r=await fetch(API_URL);if(!r.ok)return;
    LAYERS=(await r.json()).updates||[];
    fillVersel(LAYERS.length-1);
    applyLayer(LAYERS.length-1);
  }catch(e){}
})();
// голосовой комментарий: клик — запись, второй клик — стоп и расшифровка
let rec=null;
document.querySelectorAll('.mic-btn').forEach(b=>{
  b.onclick=async()=>{
    if(rec){rec.stop();return;}
    let stream;
    try{stream=await navigator.mediaDevices.getUserMedia({audio:true});}
    catch(e){statusEl.textContent='нет доступа к микрофону';return;}
    const chunks=[];
    rec=new MediaRecorder(stream);
    b.classList.add('btn-danger');b.title='Остановить запись';
    rec.ondataavailable=e=>chunks.push(e.data);
    rec.onstop=async()=>{
      stream.getTracks().forEach(t=>t.stop());
      const blob=new Blob(chunks,{type:rec.mimeType||'audio/webm'});
      rec=null;b.classList.remove('btn-danger');b.title='Надиктовать';
      statusEl.textContent='распознаю…';
      const fd=new FormData();fd.append('file',blob,'rec.webm');
      try{
        const r=await fetch('/api/transcribe',{method:'POST',body:fd});
        if(!r.ok){statusEl.textContent='распознавание: '+(r.status===503?'не настроено на сервере':'ошибка '+r.status);return;}
        const {text}=await r.json();
        const t=document.querySelector(`textarea[data-ckey="${b.dataset.for}"]`);
        if(t&&text){t.value=(t.value?t.value+' ':'')+text;t.dispatchEvent(new Event('input'));}
        statusEl.textContent='распознано';
      }catch(e){statusEl.textContent='распознавание: сеть недоступна';}
    };
    rec.start();statusEl.textContent='идёт запись — нажмите кнопку ещё раз, чтобы остановить';
  };
});
"""


# Гейты и согласования по ролям (фаза 2): статус с /api/d/<slug>/approvals,
# кнопки работают по персональной ссылке (?u=<токен>), роль берётся с /api/u/<токен>.
APPROVE_JS = r"""
const U_TOKEN=new URLSearchParams(location.search).get('u');
let MY_ROLE=null,MY_NAME=null;
async function myRole(){
  if(!U_TOKEN)return null;
  try{const r=await fetch('/api/u/'+U_TOKEN);if(!r.ok)return null;const d=await r.json();
    MY_NAME=d.name;const p=(d.projects||[]).find(x=>x.slug===SLUG);MY_ROLE=p?p.role:null;}catch(e){}
  return MY_ROLE;
}
async function getApprovals(){
  try{const r=await fetch('/api/d/'+SLUG+'/approvals');return r.ok?await r.json():null;}catch(e){return null;}
}
async function sendApprove(kind,note){
  const r=await fetch('/api/d/'+SLUG+'/approve',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({token:U_TOKEN,kind,note:note||''})});
  if(!r.ok){statusEl.textContent='не получилось: '+(await r.text()).slice(0,140);return false;}
  return true;
}
function fmtTs(ts){return (ts||'').slice(0,16).replace('T',' ');}
"""


def savebar(done_label: str = "Проверка завершена", note: str = "") -> str:
    hint = note or "правки лягут слоем поверх нашей версии — ничего не затирается"
    return f"""
  <div class="savebar">
    <input id="reviewer" class="form-control form-control-sm" placeholder="Ваше имя">
    <button id="btn-save" class="btn btn-sm">Сохранить</button>
    <button id="btn-done" class="btn btn-primary btn-sm">{done_label}</button>
    <span class="ms-auto d-flex gap-2 align-items-center">
      <select id="versel" class="form-select form-select-sm" style="width:auto" title="Версии правок"></select>
      <button id="btn-restore" class="btn btn-sm" hidden title="Выбранная версия будет сохранена как новая — ничего не теряется">Восстановить как новую</button>
    </span>
    <span class="status" id="savestatus" style="flex-basis:100%">{hint}</span>
  </div>"""
