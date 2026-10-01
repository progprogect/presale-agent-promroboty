"""CSPL-генератор: bom.yaml -> страница согласования списка компонентов (Tabler)."""
from .common import REVIEW_JS, esc, savebar, shell


def render(deal: dict, bom: dict) -> str:
    rows = []
    for i, item in enumerate(bom["items"], 1):
        key = f"bom-{i}"
        rows.append(f"""
      <tr>
        <td class="pkg">{esc(item["pos"])}
          <span class="res">{esc(item.get("why", ""))}</span></td>
        <td>{esc(item["model"])}</td>
        <td class="num">{esc(str(item["qty"]))}</td>
        <td><input class="form-control form-control-sm" data-akey="{key}"
          placeholder="Ваш вариант / замечание"></td>
      </tr>""")

    body = f"""
  <p class="hint">Наш выбор не затирается: впишите свой вариант или замечание в правой колонке.</p>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix" style="min-width:860px">
    <thead><tr>
      <th>Позиция · зачем так</th><th>Модель</th><th class="num">Кол-во</th><th style="width:30%">Предложение валидатора</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/bom";\n' + REVIEW_JS
    return shell(deal, "Компоненты", "bom", body, script)
