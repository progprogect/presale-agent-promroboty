"""CSPL-генератор: proposal.yaml -> страница «ТКП» (последний просмотр перед отправкой).

Показывает уже собранное ТКП (PDF или HTML лежит в data/deals/<slug>/proposal/) и даёт
покомментировать его по разделам. Кнопка «ТКП одобрено» — последний гейт перед письмом
заказчику; само письмо всё равно уходит только после «да» Микиты.

Спека: file, kind (pdf|html), version (необяз.), sections[{id, name}] (необяз.), note (необяз.).
"""
from .common import ICON_MIC, REVIEW_JS, esc, savebar, shell


def render(deal: dict, spec: dict) -> str:
    src = f'/d/{esc(deal["slug"])}/proposal/{esc(spec["file"])}'
    if spec.get("kind") == "pdf":
        frame = f'<embed class="embed" src="{src}#view=FitH" type="application/pdf">'
    else:
        frame = f'<iframe class="embed" src="{src}" title="ТКП"></iframe>'

    secs = "".join(f"""
    <div class="qrow">
      <div class="qhead"><span class="qt">{esc(s["name"])}</span></div>
      <div class="cbox mt-1" style="max-width:none;margin-left:0">
        <textarea class="form-control" data-ckey="раздел · {esc(s["name"])}"
          placeholder="Что поправить в разделе…"></textarea>
        <button class="btn btn-sm mic-btn" data-for="раздел · {esc(s["name"])}"
          title="Надиктовать">{ICON_MIC}</button>
      </div>
    </div>""" for s in spec.get("sections", []))
    secs_block = (f'<div class="card mt-2"><div class="card-body py-2">{secs}</div></div>'
                  if secs else "")
    ver = f'<span class="badge bg-azure-lt">{esc(spec["version"])}</span>' if spec.get("version") else ""
    note = f'<p class="hint">{esc(spec["note"])}</p>' if spec.get("note") else ""

    body = f"""
  <p class="hint">Готовое ТКП в том виде, в каком его увидит заказчик. {ver} Замечания по разделам —
  ниже. «ТКП одобрено» означает: можно отправлять.</p>
  {note}
  {frame}
  <div class="mt-2"><a class="btn btn-sm" href="{src}" target="_blank">Открыть в отдельной вкладке</a></div>
  {secs_block}
  <div class="card mt-2"><div class="card-body py-2">
    <div class="cbox" style="max-width:none">
      <textarea class="form-control" data-ckey="ТКП в целом"
        placeholder="ТКП в целом: что мешает отправить…"></textarea>
      <button class="btn btn-sm mic-btn" data-for="ТКП в целом" title="Надиктовать">{ICON_MIC}</button>
    </div>
  </div></div>
  {savebar("ТКП одобрено — можно отправлять",
           "одобрение фиксируется слоем; письмо заказчику уходит отдельным решением")}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/proposal";\n' + REVIEW_JS
    return shell(deal, "ТКП", "proposal", body, script)
