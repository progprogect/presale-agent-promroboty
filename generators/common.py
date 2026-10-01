"""CSPL: общий каркас страниц портала (Tabler, компактный стиль).

Генераторы детерминированы: одна спека -> один и тот же HTML. Без LLM и сети.
"""
from html import escape as esc  # noqa: F401  (реэкспорт для генераторов)

# Небольшие правки поверх Tabler: плотнее таблицы, элементы матрицы WBS.
EXTRA_CSS = """
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 56px}
.pagehead{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline;margin-bottom:4px}
.pagehead h2{margin:0}
.pagehead .chips{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.hint{font-size:12.5px;color:var(--tblr-secondary);margin:0 0 12px}
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
  font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;padding:3px 10px}
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
.savebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:14px}
.savebar input{max-width:200px}
.savebar .status{font-size:12px;color:var(--tblr-secondary)}
"""

ICON_COMMENT = ('<svg class="icon-14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>')
ICON_MIC = ('<svg class="icon-14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>'
            '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>')


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
             for p, n in (("wbs", "Декомпозиция работ"), ("bom", "Компоненты"))
             if p in deal.get("pages", ["wbs", "bom"]))}
  </ul>
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
const edits={hours:{},comments:{},alts:{},added:[]};
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
  edits.hours={};edits.comments={};edits.alts={};edits.added=[];
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
// подсказки
const tipsBtn=document.getElementById('tips-btn'),tips=document.getElementById('tips');
if(tipsBtn&&tips){
  let seen=false;try{seen=!!localStorage.getItem('tips_seen');}catch(e){}
  tips.hidden=seen;
  tipsBtn.onclick=()=>{tips.hidden=!tips.hidden;try{localStorage.setItem('tips_seen','1');}catch(e){}};
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


def savebar() -> str:
    return """
  <div class="savebar">
    <input id="reviewer" class="form-control form-control-sm" placeholder="Ваше имя">
    <button id="btn-save" class="btn btn-sm">Сохранить</button>
    <button id="btn-done" class="btn btn-primary btn-sm">Проверка завершена</button>
    <span class="ms-auto d-flex gap-2 align-items-center">
      <select id="versel" class="form-select form-select-sm" style="width:auto" title="Версии правок"></select>
      <button id="btn-restore" class="btn btn-sm" hidden title="Выбранная версия будет сохранена как новая — ничего не теряется">Восстановить как новую</button>
    </span>
    <span class="status" id="savestatus" style="flex-basis:100%">правки лягут слоем поверх нашей версии — ничего не затирается</span>
  </div>"""
