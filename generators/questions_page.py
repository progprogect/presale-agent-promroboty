"""CSPL-генератор: questions.yaml -> страница «Вводные» (ключевые вопросы и предположения).

Смысл страницы: предположение, принятое молча, дороже всего стоит на приёмке. Валидатор
видит каждое вводное вместе с основанием и ценой ошибки и может его оспорить.

Поля вопроса: id, topic, q, status (answered|assumed|ask), risk (high|mid|low), impact.
Необязательные: need, answer, source (для answered), basis (для assumed), ask_text (для ask).
"""
from .common import ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

STATUS = {
    "answered": ("ответ есть", "bg-green-lt"),
    "assumed": ("предположение", "bg-yellow-lt"),
    "ask": ("спросить заказчика", "bg-red-lt"),
}
RISK = {
    "high": ("цена ошибки высокая", "bg-red-lt"),
    "mid": ("цена ошибки средняя", "bg-orange-lt"),
    "low": ("цена ошибки низкая", "bg-blue-lt"),
}


def _meta(label: str, value: str) -> str:
    return f'<p class="meta"><b>{label}:</b> {esc(value)}</p>' if value else ""


def render(deal: dict, spec: dict) -> str:
    qs = spec["questions"]
    counts = {k: sum(1 for q in qs if q["status"] == k) for k in STATUS}
    blocking = [q for q in qs if q["status"] == "ask" and q.get("risk") == "high"]

    rows = []
    for q in qs:
        s_label, s_cls = STATUS[q["status"]]
        r_label, r_cls = RISK.get(q.get("risk", "mid"), ("", ""))
        qid = esc(q["id"])
        answer = q.get("answer") or q.get("ask_text") or "—"
        body = [f'<p class="ans">{esc(answer)}</p>']
        body.append(_meta("Нужно", q.get("need", "")))
        body.append(_meta("Источник", q.get("source", "")))
        body.append(_meta("Основание предположения", q.get("basis", "")))
        body.append(_meta("Влияет на", q.get("impact", "")))
        rows.append(f"""
    <div class="qrow">
      <div class="qhead">
        <span class="qid">{qid}</span>
        <span class="qt">{esc(q["topic"])} — {esc(q["q"])}</span>
        <span class="ms-auto d-flex gap-1 align-items-center">
          <span class="badge {s_cls}">{s_label}</span>
          <span class="badge {r_cls}">{r_label}</span>
          <button class="btn btn-ghost-secondary btn-icon cmt-toggle" data-id="{qid}"
            title="Комментарий">{ICON_COMMENT}</button>
        </span>
      </div>
      <div class="qbody">{"".join(body)}</div>
      <div class="verdict">
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="ok"> согласен</label>
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="doubt"> спорно</label>
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="wrong"> неверно, так нельзя</label>
      </div>
      <div class="crow" id="crow-{qid}" hidden><div class="cbox">
        <textarea class="form-control" data-ckey="{qid}"
          placeholder="Что не так с вводным {qid} и как правильно…"></textarea>
        <button class="btn btn-sm mic-btn" data-for="{qid}" title="Надиктовать">{ICON_MIC}</button>
      </div></div>
    </div>""")

    warn = ""
    if blocking:
        ids = ", ".join(q["id"] for q in blocking)
        warn = (f'<div class="alert alert-warning py-2" style="font-size:12.5px">Компоновка не '
                f'считается подтверждённой, пока не закрыты вводные с высокой ценой ошибки: '
                f'<b>{esc(ids)}</b>. До ответа заказчика всё ниже — рабочая гипотеза.</div>')

    body = f"""
  <p class="hint">Вводные, от которых зависит решение. <b>Ответ есть</b> — взято из материалов заказчика,
  источник указан. <b>Предположение</b> — ответа нет, работаем на основании и пишем это в ТКП оговоркой.
  <b>Спросить</b> — предполагать дорого, вопрос уходит заказчику. Оспорьте любое вводное: ошибка здесь
  дешевле всего исправляется.</p>
  <div class="d-flex flex-wrap gap-2 align-items-center mb-2">
    <span class="badge bg-green-lt">ответ есть: {counts["answered"]}</span>
    <span class="badge bg-yellow-lt">предположений: {counts["assumed"]}</span>
    <span class="badge bg-red-lt">спросить: {counts["ask"]}</span>
    <button class="btn btn-sm ms-auto" id="tips-btn">Как работать?</button>
  </div>
  <div class="alert alert-info" id="tips" hidden>
    <ul>
      <li>По каждому вводному отметьте <b>согласен / спорно / неверно</b> и, если не согласны, напишите как правильно (можно надиктовать).</li>
      <li>Особое внимание — жёлтым: это то, что мы <b>предположили</b>. Если предположение неверно, дальше неверно всё.</li>
      <li>«Сохранить» фиксирует вашу версию, наша не затирается. Закончили — «Проверка завершена».</li>
    </ul>
  </div>
  {warn}
  <div class="card"><div class="card-body py-2">{"".join(rows)}</div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/questions";\n' + REVIEW_JS
    return shell(deal, "Вводные", "questions", body, script)
