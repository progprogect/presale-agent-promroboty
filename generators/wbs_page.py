"""CSPL-генератор: wbs.yaml -> страница валидации декомпозиции работ (Tabler)."""
from collections import defaultdict

from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

BASIS_BADGE = {
    "analog": ("по аналогу", "bg-green-lt"),
    "norm": ("по нормативу", "bg-blue-lt"),
    "expert": ("экспертно", "bg-purple-lt"),
    "new": ("новое", "bg-orange-lt"),
}


def fmt_h(v) -> str:
    """Часы по-русски: 8, 1,5, 0,75."""
    return (str(int(v)) if float(v) == int(v) else str(round(float(v), 2)).replace(".", ","))


def _basis_cell(basis: dict) -> str:
    label, cls = BASIS_BADGE[basis["type"]]
    tip = basis.get("ref") or ""
    extra = f' · {esc(basis["est"])}' if basis.get("est") else ""
    return f'<span class="badge {cls}" title="{esc(tip)}">{label}{extra}</span>'


def task_prefix(stage: dict) -> str:
    return stage["name"].split("·")[0].strip()


def render(deal: dict, wbs: dict) -> str:
    roles = wbs["roles"]
    role_tot: dict = defaultdict(int)
    grand = 0
    opt_grand = 0
    bodies = []
    opt_sep_done = False

    for si, stage in enumerate(wbs["stages"], 1):
        opt = bool(stage.get("option"))  # опция: вне итога, показывается отдельным блоком
        st_tot = 0
        rows = []
        hid = "" if si == 1 else " hidden"
        cur_group = None
        for task in stage["tasks"]:
            if task.get("group") and task["group"] != cur_group:
                cur_group = task["group"]
                rows.append(f'\n      <tr class="task grp"{hid}><td colspan="{len(roles) + 4}">'
                            f'{esc(cur_group)}</td></tr>')
            hours = task.get("hours", {})
            locked = task.get("lock", False)
            t_sum = sum(hours.values())
            st_tot += t_sum
            cells = []
            for role in roles:
                if role in hours:
                    v = hours[role]
                    if not opt:
                        role_tot[role] += v
                    key = f'{task["id"]}|{role}'
                    if locked:
                        cells.append(f'<td class="num locked" title="Оценка на нашей стороне (CV/ПО)">'
                                     f'{fmt_h(v)}</td>')
                    else:
                        cells.append(
                            f'<td class="num"><span class="step" data-key="{esc(key)}" data-base="{v}">'
                            f'<button class="btn btn-icon">−</button><span class="val">{fmt_h(v)}</span>'
                            f'<button class="btn btn-icon">+</button></span></td>')
                elif locked:
                    cells.append('<td class="none">—</td>')
                else:
                    key = f'{task["id"]}|{role}'
                    cells.append(
                        f'<td class="num"><span class="step zero" data-key="{esc(key)}" data-base="0" '
                        f'title="Добавить часы роли {esc(role)}">'
                        f'<button class="btn btn-icon">−</button><span class="val">0</span>'
                        f'<button class="btn btn-icon">+</button></span></td>')
            tid = task["id"].replace(".", "-")
            rows.append(f"""
      <tr class="task"{hid}>
        <td class="pkg">{esc(task["id"])} {esc(task["name"])}
          <span class="res">{esc(task["result"])}</span></td>
        <td>{_basis_cell(task["basis"])}</td>
        {"".join(cells)}
        <td class="sum">{fmt_h(t_sum)}</td>
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
        io_html = ""
        if stage.get("deliverables") or stage.get("inputs"):
            dl = "".join(f"<li>{esc(x)}</li>" for x in stage.get("deliverables", []))
            inp = "".join(f"<li>{esc(x)}</li>" for x in stage.get("inputs", []))
            skey = f"stage:{task_prefix(stage)}"
            io_html = f'''
      <tr class="task stageio"{hid}><td colspan="{len(roles) + 4}">
        <div class="io2">
          <div><b>Выход этапа — что физически получим</b><ul>{dl}</ul></div>
          <div><b>Вход — что нужно до старта</b><ul>{inp}</ul></div>
        </div>
        <div class="cbox">
          <textarea class="form-control" data-ckey="{esc(skey)}"
            placeholder="Комментарий к составу этапа…"></textarea>
          <button class="btn btn-sm mic-btn" data-for="{esc(skey)}" title="Надиктовать">{ICON_MIC}</button>
        </div></td></tr>'''
        add_html = (f'\n      <tr class="task addrow"{hid}><td colspan="{len(roles) + 4}">'
                    f'<button class="btn btn-sm btn-ghost-secondary add-task" data-stage="{si}">'
                    f'+ Добавить задачу в этап</button></td></tr>')
        if opt:
            opt_grand += st_tot
        else:
            grand += st_tot
        closed = "" if si == 1 else " closed"
        rows_html = "".join(rows) + io_html + add_html
        sep = ""
        if opt and not opt_sep_done:
            opt_sep_done = True
            sep = (f'<tbody><tr class="optsep"><td colspan="{len(roles) + 4}">'
                   f'Опции — вне базового объёма и итога; заказчик выбирает отдельно</td></tr></tbody>')
        badge = '<span class="badge bg-orange-lt me-2">опция</span>' if opt else ""
        bodies.append(f"""{sep}
    <tbody>
      <tr class="stage{closed}" onclick="toggleStage(this)">
        <td colspan="{len(roles) + 4}"><span class="chev">▾</span> {esc(stage["name"])}
          <span class="st-sum">{badge}{fmt_h(st_tot)} ч · {len(stage["tasks"])} пак.</span></td>
      </tr>{rows_html}
    </tbody>""")

    role_names = wbs.get("role_names", {})
    # Шапка подписывается самой ролью (КД, АСУ, ПО…), а не буквой: иначе расшифровку
    # приходится держать в голове или искать в легенде, которая уезжает за край экрана.
    legend = "".join(f"<li><b>{esc(r)}</b> {esc(role_names.get(r, '?'))}</li>" for r in roles)
    role_th = "".join(
        f'<th class="num role" title="{esc(role_names.get(r, ""))}">{esc(r)}</th>' for r in roles)
    role_tf = "".join(f"<td>{fmt_h(role_tot[r])}</td>" for r in roles)
    opt_note = f" · опции вне итога: {fmt_h(opt_grand)} ч" if opt_grand else ""
    tf_label = "Итого по ролям (без опций)" if opt_grand else "Итого по ролям"

    body = f"""
  <ul class="legend">{legend}</ul>
  <div class="d-flex flex-wrap gap-2 align-items-center mb-2">
    <button class="btn btn-sm" onclick="toggleAll(true)">Развернуть</button>
    <button class="btn btn-sm" onclick="toggleAll(false)">Свернуть</button>
    <button class="btn btn-sm" id="tips-btn">Как работать?</button>
    <span class="ms-auto text-secondary">Итого: <b class="text-dark">{fmt_h(grand)} ч</b>{opt_note}</span>
  </div>
  <div class="alert alert-info" id="tips" hidden>
    <ul>
      <li><b>Этапы</b> сворачиваются кликом по серой строке; «Развернуть/Свернуть» — все сразу.</li>
      <li><b>Часы</b> меняются кнопками − / + (шаг по ряду Фибоначчи: 1, 2, 3, 5, 8…). Правка подсвечивается синим с пометкой «было». Пустая ячейка: нажмите «+», чтобы добавить роль в задачу.</li>
      <li><b>Новая задача</b> — кнопка «+ Добавить задачу» в конце каждого этапа: впишите название и часы по ролям.</li>
      <li><b>Комментарий</b> к задаче — иконка 💬 справа; можно надиктовать голосом (кнопка с микрофоном). Комментарий к составу этапа — в блоке «Выход / Вход» под этапом.</li>
      <li><b>Сохранение:</b> «Сохранить» фиксирует вашу версию правок; наша исходная не затирается. Переключатель версий справа внизу показывает любую прошлую версию, «Восстановить как новую» вернёт её без потери истории. Закончили — жмите «Проверка завершена».</li>
    </ul>
  </div>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix">
    <thead><tr>
      <th>Пакет работ</th><th>Основание</th>{role_th}<th class="num">Σ</th><th class="num"></th>
    </tr></thead>
    {"".join(bodies)}
    <tfoot><tr><td colspan="2">{tf_label}</td>{role_tf}<td>{fmt_h(grand)}</td><td></td></tr></tfoot>
  </table>
  </div></div>
  {savebar()}"""

    import json
    script = (f'const API_BASE="/api/d/{deal["slug"]}/review/wbs";'
              f'window.PAGE_ROLES={json.dumps(roles, ensure_ascii=False)};\n') + REVIEW_JS
    return shell(deal, "Декомпозиция работ", "wbs", body, script)
