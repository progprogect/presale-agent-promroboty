"""CSPL-генератор: process.yaml -> страница «Процесс» (схема дорожками, по смыслу BPMN).

Формат спеки — общий с генератором картинки для ТКП (knowledge/cspl/generators/process-diagram):
одна спека, два рендера. Линейная цепочка «1 → 2 → 3» не используется (решение Микиты 25.09.2026):
дорожки показывают, кто что делает, что идёт одновременно и где проходит граница нашей поставки.

Спека: lanes[{id, name, sub, kind: ours|client|human}], steps[{n, lane, title, desc, time, parallel}],
columns[{n, label}] (необяз.), cycle, key_figure, title.
"""
from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

LANE_KIND = {"ours": "ours", "client": "client", "human": ""}


def _step(st: dict, kind: str) -> str:
    cls = " " + LANE_KIND.get(kind, "") if LANE_KIND.get(kind) else ""
    if st.get("parallel"):
        cls += " par"
    sid = f'{st["n"]}-{st["lane"]}'
    time = f'<span class="tm badge bg-azure-lt">{esc(str(st["time"]))}</span>' if st.get("time") else ""
    par = (f'<span class="d">одновременно: {esc(st["parallel"])}</span>'
           if st.get("parallel") else "")
    desc = f'<span class="d">{esc(st["desc"])}</span>' if st.get("desc") else ""
    return f"""<div class="pstep{cls}">
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
    for lane in lanes:
        sub = f'<small>{esc(lane["sub"])}</small>' if lane.get("sub") else ""
        kind = lane.get("kind", "")
        cells.append(f'<div class="lane-name {esc(kind)}"><div>{esc(lane["name"])}{sub}</div></div>')
        for n in cols:
            here = [s for s in steps if s["lane"] == lane["id"] and s["n"] == n]
            inner = "".join(_step(s, kind) for s in here)
            cells.append(f'<div class="lane-cell">{inner}</div>')

    # Ширина колонки потока подбирается под число колонок: узкие дорожки лучше читаются,
    # но карточка не должна быть уже своего содержимого — отсюда нижняя граница 176px.
    grid = (f'<div class="lanes-wrap"><div class="lanes" '
            f'style="grid-template-columns:168px repeat({len(cols)},minmax(176px,1fr))">'
            f'{"".join(cells)}</div></div>')
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

    script = f'const API_URL="/api/d/{deal["slug"]}/review/process";\n' + REVIEW_JS
    return shell(deal, "Процесс", "process", body, script)
