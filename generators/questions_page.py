"""CSPL-генератор: questions.yaml -> страница «Вводные» (ключевые вопросы и предположения).

Смысл страницы: предположение, принятое молча, дороже всего стоит на приёмке. Валидатор
видит каждое вводное вместе с основанием и ценой ошибки и может его оспорить.

Поля вопроса: id, topic, q, status (answered|assumed|ask), risk (high|mid|low), impact.
Необязательные: need, answer, source (для answered), basis (для assumed), ask_text (для ask).

Контекст для проверяющего (добавлено 09.10.2026) — чтобы человек понимал, КАК отвечать:
  why     — почему вопрос вообще возник, одной фразой («чертежей нет, а от толщины зависят режимы»)
  options — варианты решения [{label, note}]: label короткий, note — последствие выбора.
            Если варианты заданы, проверяющий выбирает из них, а не отвечает «согласен/спорно».
  auto    — true, если решение приняли сами и дёргать проверяющего незачем. Такие вводные
            уходят вниз в свёрнутый блок, чтобы на виду осталось только то, где нужен человек.
"""
from .common import APPROVE_JS, ICON_COMMENT, ICON_MIC, REVIEW_JS, esc, savebar, shell

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


def _verdict(q: dict, qid: str) -> str:
    """Блок решения. Если у вводного заданы варианты — выбираем из них: это конкретнее,
    чем «согласен / спорно», и сразу говорит, какие вообще развилки есть."""
    opts = q.get("options") or []
    if opts:
        items = []
        for o in opts:
            lab = str(o.get("label", "")).strip()
            note = str(o.get("note", "")).strip()
            if not lab:
                continue
            val = lab[:70]
            items.append(
                f'<label class="opt"><input type="radio" class="form-check-input" name="v-{qid}" '
                f'data-fkey="{qid}" value="{esc(val)}">'
                f'<span><b>{esc(lab)}</b>'
                + (f'<small>{esc(note)}</small>' if note else "") + "</span></label>")
        items.append(
            f'<label class="opt other"><input type="radio" class="form-check-input" name="v-{qid}" '
            f'data-fkey="{qid}" value="иначе"><span><b>иначе — напишу свой</b></span></label>')
        return f'<div class="verdict opts"><span class="vlab">Что выбираем</span>{"".join(items)}</div>'
    return f"""<div class="verdict">
        <span class="vlab">Ваш ответ</span>
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="ok"> согласен</label>
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="doubt"> спорно</label>
        <label><input type="radio" class="form-check-input" name="v-{qid}"
          data-fkey="{qid}" value="wrong"> неверно, так нельзя</label>
      </div>"""


def render(deal: dict, spec: dict) -> str:
    qs = spec["questions"]
    counts = {k: sum(1 for q in qs if q["status"] == k) for k in STATUS}
    blocking = [q for q in qs if q["status"] == "ask" and q.get("risk") == "high"]

    rows, auto_rows = [], []
    for q in qs:
        s_label, s_cls = STATUS[q["status"]]
        r_label, r_cls = RISK.get(q.get("risk", "mid"), ("", ""))
        qid = esc(q["id"])
        answer = q.get("answer") or q.get("ask_text") or "—"
        # Видно сразу — только сам ответ или предположение. Служебные поля (откуда взято,
        # на что влияет) прячем: они нужны при споре, а не при беглом просмотре.
        details = "".join(filter(None, [
            _meta("Нужно", q.get("need", "")),
            _meta("Источник", q.get("source", "")),
            _meta("Основание предположения", q.get("basis", "")),
            _meta("Влияет на", q.get("impact", "")),
        ]))
        # Контекст наверху: почему это вообще вопрос. Без него проверяющий видит
        # утверждение и не понимает, на основании чего ему соглашаться или спорить.
        body = []
        if q.get("why"):
            body.append(f'<p class="qwhy"><b>почему спросили</b> {esc(q["why"])}</p>')
        body.append(f'<p class="ans">{esc(answer)}</p>')
        if q.get("impact"):
            body.append(f'<p class="qrisk"><b>если ошибёмся</b> {esc(q["impact"])}</p>')
        if details:
            body.append(f'<details class="qmeta"><summary>откуда это и на что влияет</summary>'
                        f'{details}</details>')
        verdict = _verdict(q, qid)
        (auto_rows if q.get("auto") else rows).append(f"""
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
      {verdict}
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

    # Вводные, которые мы закрыли сами и где человек не нужен, убираем вниз под раскрытие:
    # иначе они разбавляют список и проверяющий тратит внимание не на то.
    auto_block = ""
    if auto_rows:
        auto_block = (
            f'<details class="autoq"><summary>Решили сами — {len(auto_rows)} '
            f'{"вводное" if len(auto_rows) == 1 else "вводных"}: типовые вещи, где ваш ответ '
            f'ничего не меняет. Откройте, если хотите проверить и их</summary>'
            f'<div class="card mt-2"><div class="card-body py-2">{"".join(auto_rows)}</div></div>'
            f'</details>')

    body = f"""
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
      <li>Что значат пометки: <b>ответ есть</b> — взято из материалов заказчика, источник указан;
        <b>предположение</b> — ответа нет, работаем на основании и пишем это в ТКП оговоркой;
        <b>спросить</b> — предполагать дорого, вопрос уходит заказчику.</li>
    </ul>
  </div>
  {warn}
  <div class="card"><div class="card-body py-2">{"".join(rows)}</div></div>
  {auto_block}
  <div class="gate">
    <h3>Гейт вводных</h3>
    <p id="qgate-st" class="text-secondary" style="font-size:12.5px">…</p>
    <div id="qgate-btn" hidden>
      <button class="btn btn-primary btn-sm"
        onclick="closeQGate()">Вводные согласованы — двигаемся к пакету</button>
      <span class="text-secondary" style="font-size:12px">кнопка delivery-менеджера; после неё
        собирается пакет (схема, работы, состав)</span>
    </div>
  </div>
  {savebar()}"""

    script = (f'const API_BASE="/api/d/{deal["slug"]}/review/questions";'
              f'const SLUG="{deal["slug"]}";\n' + REVIEW_JS + APPROVE_JS + r"""
async function drawQGate(){
  const a=await getApprovals();const st=document.getElementById('qgate-st');
  if(a&&a.questions_gate){
    st.innerHTML='<span class="badge bg-green-lt">согласовано · '+a.questions_gate.by+' · '+fmtTs(a.questions_gate.ts)+'</span>';
  }else st.textContent='ещё не закрыт: delivery-менеджер закрывает гейт, когда блокирующих вопросов не осталось.';
  await myRole();
  document.getElementById('qgate-btn').hidden=(MY_ROLE!=='delivery');
}
async function closeQGate(){
  if(await sendApprove('questions'))drawQGate();
}
drawQGate();
""")
    return shell(deal, "Вводные", "questions", body, script)
