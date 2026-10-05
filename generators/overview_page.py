"""CSPL-генератор: страница «Обзор» карточки проекта — состояние пакета проверки и гейт.

Собирается из deal.yaml и набора спек сделки; статусы разделов подтягиваются с
/api/d/<slug>/status. Здесь delivery-менеджер принимает пакет: до этого ТКП не собирается.
"""
import json

from .common import ICON_MIC, PAGES, REVIEW_JS, esc, savebar, shell

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

    gate_note = spec.get("gate_note") or (
        "Примите пакет, когда вводные, процесс, решение, работы и состав вас устраивают. "
        "После этого собирается ТКП и возвращается сюда на последний просмотр.")

    body = f"""
  <p class="hint">Карточка проекта: всё, что нужно проверить до сборки ТКП. Разделы можно смотреть
  в любом порядке, но начинать стоит с «Вводных» — если предположение неверно, дальше неверно всё.
  Правки в каждом разделе ложатся отдельным слоем, наша версия не затирается.</p>
  <div class="card"><div class="card-body py-2">{rows}</div></div>
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
              f'const PAGE_LABELS={json.dumps(dict(PAGES), ensure_ascii=False)};\n'
              + REVIEW_JS + r"""
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
