"""CSPL-генератор: wbs.yaml -> страница валидации декомпозиции работ (Tabler)."""
from collections import defaultdict

from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

BASIS_BADGE = {
    "analog": ("по аналогу", "bg-green-lt"),
    "norm": ("по нормативу", "bg-blue-lt"),
    "expert": ("экспертно", "bg-purple-lt"),
}


def _basis_cell(basis: dict) -> str:
    label, cls = BASIS_BADGE[basis["type"]]
    tip = basis.get("ref") or ""
    extra = f' · {esc(basis["est"])}' if basis.get("est") else ""
    return f'<span class="badge {cls}" title="{esc(tip)}">{label}{extra}</span>'


def render(deal: dict, wbs: dict) -> str:
    roles = wbs["roles"]
    role_tot: dict = defaultdict(int)
    grand = 0
    bodies = []

    for si, stage in enumerate(wbs["stages"], 1):
        st_tot = 0
        rows = []
        hid = "" if si == 1 else " hidden"
        for task in stage["tasks"]:
            hours = task.get("hours", {})
            t_sum = sum(hours.values())
            st_tot += t_sum
            cells = []
            for role in roles:
                if role in hours:
                    v = hours[role]
                    role_tot[role] += v
                    key = f'{task["id"]}|{role}'
                    cells.append(
                        f'<td class="num"><span class="step" data-key="{esc(key)}" data-base="{v}">'
                        f'<button class="btn btn-icon">−</button><span class="val">{v}</span>'
                        f'<button class="btn btn-icon">+</button></span></td>')
                else:
                    cells.append('<td class="none">—</td>')
            tid = task["id"].replace(".", "-")
            rows.append(f"""
      <tr class="task"{hid}>
        <td class="pkg">{esc(task["id"])} {esc(task["name"])}
          <span class="res">{esc(task["result"])}</span></td>
        <td>{_basis_cell(task["basis"])}</td>
        {"".join(cells)}
        <td class="sum">{t_sum}</td>
        <td class="num"><button class="btn btn-ghost-secondary btn-icon cmt-toggle" data-id="{tid}"
          title="Комментарий">{ICON_COMMENT}</button></td>
      </tr>
      <tr class="crow" id="crow-{tid}" hidden>
        <td colspan="{len(roles) + 4}"><div class="cbox">
          <textarea class="form-control" data-ckey="{esc(task["id"])}"
            placeholder="Комментарий к пакету {esc(task["id"])}…"></textarea>
          <button class="btn btn-sm mic-btn" data-for="{esc(task["id"])}" title="Надиктовать">{ICON_MIC}</button>
        </div></td>
      </tr>""")
        grand += st_tot
        closed = "" if si == 1 else " closed"
        rows_html = "".join(rows)
        bodies.append(f"""
    <tbody>
      <tr class="stage{closed}" onclick="toggleStage(this)">
        <td colspan="{len(roles) + 4}"><span class="chev">▾</span> Этап {si} · {esc(stage["name"])}
          <span class="st-sum">{st_tot} ч · {len(stage["tasks"])} пак.</span></td>
      </tr>{rows_html}
    </tbody>""")

    role_th = "".join(f'<th class="num">{esc(r)}</th>' for r in roles)
    role_tf = "".join(f"<td>{role_tot[r]}</td>" for r in roles)

    body = f"""
  <p class="hint">Этапы сворачиваются кликом. Часы: − / + (шаг по Фибоначчи). Комментарий — иконка справа.</p>
  <div class="d-flex flex-wrap gap-2 align-items-center mb-2">
    <button class="btn btn-sm" onclick="toggleAll(true)">Развернуть</button>
    <button class="btn btn-sm" onclick="toggleAll(false)">Свернуть</button>
    <span class="ms-auto text-secondary">Итого: <b class="text-dark">{grand} ч</b></span>
  </div>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix">
    <thead><tr>
      <th>Пакет работ</th><th>Основание</th>{role_th}<th class="num">Σ</th><th class="num"></th>
    </tr></thead>
    {"".join(bodies)}
    <tfoot><tr><td colspan="2">Итого по ролям</td>{role_tf}<td>{grand}</td><td></td></tr></tfoot>
  </table>
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/wbs";\n' + REVIEW_JS
    return shell(deal, "Декомпозиция работ", "wbs", body, script)
