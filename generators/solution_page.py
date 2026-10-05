"""CSPL-генератор: solution.yaml -> страница «Решение» (компоновка на один лист).

Структура повторяет обязательный раздел ТКП «Почему именно такая компоновка»
(knowledge/templates/kp-structure.md): что стоит и зачем → почему не альтернативы →
чем подтверждено → границы применимости. Один лист, без воды.

Спека: summary, nodes[{name, what, why}], rejected[{option, why}], proof[строки],
limits[строки], shots[{file, caption}] (необяз.).
"""
from .common import ICON_MIC, REVIEW_JS, esc, savebar, shell


def _cbox(key: str, placeholder: str) -> str:
    return f"""<div class="cbox mt-1" style="max-width:none">
      <textarea class="form-control" data-ckey="{esc(key)}" placeholder="{esc(placeholder)}"></textarea>
      <button class="btn btn-sm mic-btn" data-for="{esc(key)}" title="Надиктовать">{ICON_MIC}</button>
    </div>"""


def render(deal: dict, spec: dict) -> str:
    nodes = "".join(f"""
      <tr>
        <td style="width:20%"><b>{esc(n["name"])}</b></td>
        <td style="width:36%">{esc(n["what"])}</td>
        <td style="width:30%" class="text-secondary">{esc(n["why"])}</td>
        <td><input class="form-control form-control-sm" data-akey="узел · {esc(n["name"])}"
          placeholder="Замечание"></td>
      </tr>""" for n in spec.get("nodes", []))

    rejected = "".join(f'<li><b>{esc(r["option"])}</b> — {esc(r["why"])}</li>'
                       for r in spec.get("rejected", []))
    proof = "".join(f"<li>{esc(x)}</li>" for x in spec.get("proof", []))
    limits = "".join(f"<li>{esc(x)}</li>" for x in spec.get("limits", []))
    shots = "".join(f'<figure><img src="/d/{esc(deal["slug"])}/img/{esc(s["file"])}" alt="">'
                    f'<figcaption>{esc(s.get("caption", ""))}</figcaption></figure>'
                    for s in spec.get("shots", []))

    blocks = [f'<h3>Что предлагаем</h3><p>{esc(spec["summary"])}</p>']
    if shots:
        blocks.append(f'<div class="shots">{shots}</div>'
                      '<p class="meta text-secondary" style="font-size:11px;margin-top:4px">'
                      'Изображения концептуальные.</p>')
    if nodes:
        blocks.append('<h3>Из чего состоит и зачем каждый узел</h3>'
                      '<table class="table table-sm"><thead><tr><th>Узел</th><th>Что делает</th>'
                      '<th>Почему именно так</th><th style="width:22%">Замечание валидатора</th>'
                      f'</tr></thead><tbody>{nodes}</tbody></table>')
    if rejected:
        blocks.append(f'<h3>Почему не альтернативы</h3><ul>{rejected}</ul>'
                      + _cbox("альтернативы", "Какой вариант мы зря отбросили и почему…"))
    if proof:
        blocks.append(f'<h3>Чем подтверждено</h3><ul>{proof}</ul>'
                      + _cbox("подтверждение", "Чему не верите, что надо проверить ещё…"))
    if limits:
        blocks.append(f'<h3>Границы применимости — чего решение не закрывает</h3><ul>{limits}</ul>'
                      + _cbox("границы", "Что ещё не закрывается и всплывёт на приёмке…"))

    body = f"""
  <p class="hint">Компоновочное решение на один лист: что стоит, зачем, почему не иначе и чего оно
  не закрывает. Этот же текст станет разделом ТКП «Почему именно такая компоновка» — замечания
  отсюда попадут прямо туда.</p>
  <div class="card"><div class="card-body sheet">{"".join(blocks)}</div></div>
  <div class="card mt-2"><div class="card-body py-2">
    {_cbox("решение в целом", "Решение в целом: что бы вы сделали иначе…")}
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/solution";\n' + REVIEW_JS
    return shell(deal, "Решение", "solution", body, script)
