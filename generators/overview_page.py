"""CSPL-генератор: страница «Обзор» карточки проекта — состояние пакета проверки и гейт.

Собирается из deal.yaml и набора спек сделки; статусы разделов подтягиваются с
/api/d/<slug>/status. Здесь delivery-менеджер принимает пакет: до этого ТКП не собирается.
"""
import json

from .common import APPROVE_JS, ICON_MIC, PAGES, REVIEW_JS, esc, savebar, shell

# Что валидатор увидит в строке раздела: зачем этот раздел нужен.
WHY = {
    "questions": "вводные и предположения, на которых стоит всё остальное",
    "process": "как устроен процесс целиком и где граница нашей поставки",
    "solution": "компоновка на один лист: что стоит, зачем и почему не иначе",
    "wbs": "пакеты работ, роли, часы и основание каждой оценки",
    "bom": "состав комплекта, модели, цены закупки и сроки",
    "proposal": "готовое ТКП — последний просмотр перед отправкой заказчику",
}


def render(deal: dict, spec: dict) -> str:
    pages = [p for p in deal.get("pages", []) if p not in ("package",)]
    rows = "".join(f"""
    <div class="secrow" data-page="{esc(p)}">
      <span class="nm"><a href="/d/{esc(deal["slug"])}/{esc(p)}">{esc(label)}</a></span>
      <span class="text-secondary" style="font-size:12px">{esc(WHY.get(p, ""))}</span>
      <span class="st">—</span>
    </div>""" for p, label in PAGES if p in pages)

    tz_files = spec.get("tz_files") or []
    if tz_files:
        links = "".join(
            f'<a class="btn btn-sm btn-outline-primary" '
            f'href="/d/{esc(deal["slug"])}/tz/{esc(name)}" target="_blank" rel="noopener">'
            f'{esc(name)}</a>' for name in tz_files)
        tz_block = f"""
  <div class="card mt-2"><div class="card-body py-3">
    <h3 style="font-size:13px;margin:0 0 4px">Исходное задание заказчика</h3>
    <p class="text-secondary" style="font-size:12px;margin:0 0 8px">То, от чего мы отталкивались.
      Полезно открыть, если показалось, что мы что-то поняли не так. Файл открывается по вашей
      персональной ссылке; если доступа нет — попросите его у ответственного за проект.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">{links}</div>
  </div></div>"""
    else:
        tz_block = ""

    gate_note = spec.get("gate_note") or (
        "Примите пакет, когда вводные, процесс, решение, работы и состав вас устраивают. "
        "После этого собирается ТКП и возвращается сюда на последний просмотр.")

    body = f"""
  <p class="hint">Карточка проекта: всё, что нужно проверить до сборки ТКП. Разделы можно смотреть
  в любом порядке, но начинать стоит с «Вводных» — если предположение неверно, дальше неверно всё.
  Правки в каждом разделе ложатся отдельным слоем, наша версия не затирается.</p>
  <div class="card"><div class="card-body py-2">{rows}</div></div>
  {tz_block}
  <div class="card mt-2"><div class="card-body py-3">
    <h3 style="font-size:13px;margin:0 0 6px">Согласования по ролям</h3>
    <p class="text-secondary" style="font-size:12px;margin:0 0 8px">Каждый согласует свою часть
      пакета; delivery-менеджер принимает пакет целиком — после этого собирается ТКП.
      Кнопки работают по персональной ссылке из вашего кабинета.</p>
    <div id="appr-list" class="text-secondary" style="font-size:13px">…</div>
    <div id="appr-actions" class="mt-2" style="display:flex;gap:8px;flex-wrap:wrap"></div>
  </div></div>
  <div class="gate">
    <h3>Решение delivery-менеджера</h3>
    <p>{esc(gate_note)}</p>
    <div class="verdict" style="margin-left:0">
      <label><input type="radio" class="form-check-input" name="v-gate" data-fkey="пакет"
        value="ok"> пакет годится, можно собирать ТКП</label>
      <label><input type="radio" class="form-check-input" name="v-gate" data-fkey="пакет"
        value="fix"> нужны правки, см. замечания в разделах</label>
      <label><input type="radio" class="form-check-input" name="v-gate" data-fkey="пакет"
        value="rework"> решение надо пересматривать</label>
    </div>
    <div class="cbox mt-2" style="max-width:none">
      <textarea class="form-control" data-ckey="пакет в целом"
        placeholder="Что в пакете в целом не сходится, кого ещё привлечь, на что смотреть при пересборке…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="пакет в целом" title="Надиктовать">{ICON_MIC}</button>
    </div>
  </div>
  {savebar("Пакет принят — собирать ТКП",
           "решение фиксируется слоем; принять пакет может любой проверяющий, мы увидим кто и когда")}"""

    script = (f'const API_URL="/api/d/{deal["slug"]}/review/package";'
              f'const STATUS_URL="/api/d/{deal["slug"]}/status";'
              f'const SLUG="{deal["slug"]}";'
              f'const PAGE_LABELS={json.dumps(dict(PAGES), ensure_ascii=False)};\n'
              + REVIEW_JS + APPROVE_JS + r"""
// матрица согласований по ролям
async function drawApprovals(){
  const a=await getApprovals();if(!a)return;
  const list=document.getElementById('appr-list');
  const done=Object.fromEntries((a.package||[]).map(x=>[x.by,x]));
  let h='';
  if(a.questions_gate)
    h+='<div>Гейт вводных: <span class="badge bg-green-lt">закрыт · '+a.questions_gate.by+' · '+fmtTs(a.questions_gate.ts)+'</span></div>';
  else h+='<div>Гейт вводных: <span class="badge bg-yellow-lt">не закрыт</span></div>';
  for(const p of (a.assigned||[])){
    const d=done[p.name];
    h+='<div style="margin-top:3px">'+p.role_name+' — <b>'+p.name+'</b>: '+
      (d?'<span class="badge bg-green-lt">согласовано · '+fmtTs(d.ts)+'</span>'
        :'<span class="badge bg-yellow-lt">ждём</span>')+'</div>';
  }
  if(a.final)h+='<div style="margin-top:6px"><span class="badge bg-green-lt">ПАКЕТ ПРИНЯТ · '+
    a.final.by+' · '+fmtTs(a.final.ts)+'</span> — можно собирать ТКП</div>';
  list.innerHTML=h||'на проект пока никто не назначен';
  await myRole();
  const act=document.getElementById('appr-actions');act.innerHTML='';
  if(MY_ROLE&&MY_ROLE!=='viewer'){
    const mine=done[MY_NAME];
    const b=document.createElement('button');
    b.className='btn btn-sm '+(MY_ROLE==='delivery'?'btn-primary':'');
    b.textContent=MY_ROLE==='delivery'
      ?(a.final?'Подтвердить пакет заново':'Принять пакет — собирать ТКП')
      :(mine?'Согласовано заново (обновить)':'Согласовать свою часть');
    b.onclick=async()=>{if(await sendApprove('package'))drawApprovals();};
    act.appendChild(b);
  }
}
drawApprovals();
// состояние разделов пакета: сколько слоёв правок и кто завершил проверку
(async()=>{
  try{
    const r=await fetch(STATUS_URL);if(!r.ok)return;
    const st=await r.json();
    document.querySelectorAll('.secrow').forEach(row=>{
      const s=st[row.dataset.page]||{};const el=row.querySelector('.st');
      if(s.done_by)el.innerHTML='<span class="badge bg-green-lt">проверено · '+s.done_by+'</span>';
      else if(s.updates)el.innerHTML='<span class="badge bg-yellow-lt">правок: '+s.updates+'</span>';
      else el.innerHTML='<span class="text-secondary">не смотрели</span>';
    });
  }catch(e){}
})();
""")
    return shell(deal, "Обзор", "package", body, script)
