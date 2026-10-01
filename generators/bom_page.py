"""CSPL-генератор: bom.yaml -> страница согласования состава комплекта (Tabler)."""
from .common import REVIEW_JS, esc, savebar, shell

CONF = {
    "high": ("подтверждена", "bg-green-lt"),
    "mid": ("с сайта", "bg-blue-lt"),
    "low": ("оценка · RFQ", "bg-orange-lt"),
}


def fmt_p(v) -> str:
    return f"{int(v):,}".replace(",", " ")


def render(deal: dict, bom: dict) -> str:
    rows = []
    total = 0
    for i, item in enumerate(bom["items"], 1):
        key = f"bom-{i}"
        price = item.get("price")
        total += price or 0
        conf = item.get("conf")
        label, cls = CONF.get(conf, ("", ""))
        conf_html = (f'<span class="badge {cls}" title="{esc(item.get("price_note", ""))}">{label}</span>'
                     if conf else "")
        rows.append(f"""
      <tr>
        <td class="pkg">{esc(item["pos"])}
          <span class="res">{esc(item.get("why", ""))}</span></td>
        <td>{esc(item["model"])}</td>
        <td class="num">{esc(str(item["qty"]))}</td>
        <td class="num">{fmt_p(price) if price else "—"}</td>
        <td>{conf_html}</td>
        <td><input class="form-control form-control-sm" data-akey="{key}"
          placeholder="Дешевле / замена / замечание"></td>
      </tr>""")

    body = f"""
  <p class="hint">Цены — закупка без наценки, BYN. Знаете, где дешевле или лучше, — впишите в правую колонку:
  наш выбор не затирается, предложения лягут отдельным слоем.</p>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix" style="min-width:980px">
    <thead><tr>
      <th>Позиция · зачем так</th><th>Модель</th><th class="num">Кол-во</th>
      <th class="num">Цена, BYN</th><th>Цена</th><th style="width:26%">Предложение валидатора</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    <tfoot><tr><td colspan="3">Итого закупка и внешние услуги</td>
      <td class="num">{fmt_p(total)}</td><td colspan="2"></td></tr></tfoot>
  </table>
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/bom";\n' + REVIEW_JS
    return shell(deal, "Компоненты", "bom", body, script)
