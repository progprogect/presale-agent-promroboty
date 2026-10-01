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
td.changed{background:var(--tblr-blue-lt)}
td.changed .was{display:block;font-size:10px;color:var(--tblr-blue)}
td.none{color:var(--tblr-border-color);text-align:center}
tr.crow td{padding:8px 10px;background:var(--tblr-bg-surface-tertiary)}
.cbox{display:flex;gap:6px;align-items:flex-start;max-width:680px}
.cbox textarea{min-height:44px;font-size:12.5px}
tfoot td{font-weight:600;text-align:center}
tfoot td:first-child{text-align:left;color:var(--tblr-secondary);font-weight:500}
.icon-14{width:14px;height:14px;stroke-width:1.75}
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
    <li class="nav-item">{tab("wbs", "Декомпозиция работ")}</li>
    <li class="nav-item">{tab("bom", "Компоненты")}</li>
  </ul>
  {body}
</div>
<script>{script}</script>
</body>
</html>"""


# Общий JS: степперы Фибоначчи, сворачивание этапов, слой правок и отправка.
REVIEW_JS = r"""
const FIB=[1,2,3,5,8,13,21,34,55,89];
function snap(v,dir){
  if(dir>0){for(const f of FIB)if(f>v)return f;return v+55}
  for(let i=FIB.length-1;i>=0;i--)if(FIB[i]<v)return FIB[i];return 1;
}
const edits={hours:{},comments:{},alts:{}};
function markCell(td,base){
  const val=td.querySelector('.val');
  const cur=+val.textContent;
  td.classList.toggle('changed',cur!==base);
  let was=td.querySelector('.was');
  if(cur!==base){
    if(!was){was=document.createElement('span');was.className='was';td.appendChild(was);}
    was.textContent='было '+base;
  }else if(was){was.remove();}
}
document.querySelectorAll('.step').forEach(s=>{
  const td=s.closest('td'),base=+s.dataset.base,key=s.dataset.key;
  const[minus,plus]=s.querySelectorAll('button'),val=s.querySelector('.val');
  function upd(dir){
    val.textContent=snap(+val.textContent,dir);
    const cur=+val.textContent;
    if(cur!==base)edits.hours[key]=cur;else delete edits.hours[key];
    markCell(td,base);setDirty();
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
const statusEl=document.getElementById('savestatus');
function setDirty(){statusEl.textContent='есть несохранённые правки';}
async function send(done){
  const reviewer=document.getElementById('reviewer').value.trim();
  if(!reviewer){statusEl.textContent='укажите имя';return;}
  try{localStorage.setItem('reviewer',reviewer);}catch(e){}
  const r=await fetch(API_URL,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({reviewer,done,...edits})});
  statusEl.textContent=r.ok?(done?'проверка завершена — спасибо!':'сохранено '+new Date().toLocaleTimeString()):'ошибка сохранения';
}
document.getElementById('btn-save').onclick=()=>send(false);
document.getElementById('btn-done').onclick=()=>send(true);
try{const n=localStorage.getItem('reviewer');if(n)document.getElementById('reviewer').value=n;}catch(e){}
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
// показать ранее сохранённые правки (последняя версия слоя)
(async()=>{
  try{
    const r=await fetch(API_URL);if(!r.ok)return;
    const data=await r.json();const last=data.updates&&data.updates[data.updates.length-1];
    if(!last)return;
    Object.entries(last.hours||{}).forEach(([key,v])=>{
      const s=document.querySelector(`.step[data-key="${key}"]`);if(!s)return;
      s.querySelector('.val').textContent=v;edits.hours[key]=v;markCell(s.closest('td'),+s.dataset.base);
    });
    Object.entries(last.comments||{}).forEach(([k,v])=>{
      const t=document.querySelector(`textarea[data-ckey="${k}"]`);
      if(t){t.value=v;edits.comments[k]=v;const row=t.closest('tr');if(row)row.hidden=false;}
    });
    Object.entries(last.alts||{}).forEach(([k,v])=>{
      const t=document.querySelector(`input[data-akey="${k}"]`);if(t){t.value=v;edits.alts[k]=v;}
    });
    statusEl.textContent='показан слой правок от '+(last.reviewer||'?')+' ('+(last.ts||'').slice(0,16).replace('T',' ')+')';
  }catch(e){}
})();
"""


def savebar() -> str:
    return """
  <div class="savebar">
    <input id="reviewer" class="form-control form-control-sm" placeholder="Ваше имя">
    <button id="btn-save" class="btn btn-sm">Сохранить</button>
    <button id="btn-done" class="btn btn-primary btn-sm">Проверка завершена</button>
    <span class="status" id="savestatus">правки лягут слоем поверх нашей версии — ничего не затирается</span>
  </div>"""
