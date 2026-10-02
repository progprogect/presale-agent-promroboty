"""CSPL-генератор: bom.yaml -> страница согласования состава комплекта (Tabler).

Поля позиции: pos, model, qty, why, price, conf, price_note (обязательны pos/model/qty).
Необязательные: group (раздел — строка-заголовок), range [мин, макс] (вилка цены, BYN),
conf_label (своя подпись уверенности), weeks [мин, макс] (срок поставки, недель).
"""
from .common import REVIEW_JS, esc, savebar, shell

CONF = {
    "high": ("подтверждена", "bg-green-lt"),
    "mid": ("с сайта", "bg-blue-lt"),
    "low": ("оценка · RFQ", "bg-orange-lt"),
}


def fmt_p(v) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def _price_cell(price, rng) -> str:
    main = fmt_p(price) if price else "—"
    if rng and rng[0] != rng[1]:
        main += f'<span class="rng">{fmt_p(rng[0])}–{fmt_p(rng[1])}</span>'
    return main


def _weeks(w) -> str:
    if not w:
        return "—"
    return str(w[0]) if w[0] == w[1] else f"{w[0]}–{w[1]}"


def render(deal: dict, bom: dict) -> str:
    items = bom["items"]
    has_weeks = any(i.get("weeks") for i in items)
    ncols = 7 if has_weeks else 6
    rows = []
    total = lo_t = hi_t = 0
    cur_group = None
    for i, item in enumerate(items, 1):
        group = item.get("group")
        if group and group != cur_group:
            cur_group = group
            rows.append(f'\n      <tr class="grp"><td colspan="{ncols}">{esc(group)}</td></tr>')
        key = f"bom-{i}"
        price = item.get("price")
        rng = item.get("range")
        total += price or 0
        lo_t += rng[0] if rng else (price or 0)
        hi_t += rng[1] if rng else (price or 0)
        conf = item.get("conf")
        label, cls = CONF.get(conf, ("", ""))
        label = item.get("conf_label", label)
        conf_html = (f'<span class="badge {cls}" title="{esc(item.get("price_note", ""))}">{esc(label)}</span>'
                     if conf else "")
        weeks_td = f'<td class="num">{_weeks(item.get("weeks"))}</td>' if has_weeks else ""
        why = f'<span class="res">{esc(item["why"])}</span>' if item.get("why") else ""
        rows.append(f"""
      <tr>
        <td class="pkg">{esc(item["pos"])}{why}</td>
        <td>{esc(item["model"])}</td>
        <td class="num">{esc(str(item["qty"]))}</td>
        <td class="num">{_price_cell(price, rng)}</td>
        <td>{conf_html}</td>
        {weeks_td}
        <td><input class="form-control form-control-sm" data-akey="{key}"
          placeholder="Дешевле / замена / замечание"></td>
      </tr>""")

    weeks_th = '<th class="num">Срок, нед</th>' if has_weeks else ""
    total_rng = (f'<span class="rng">{fmt_p(lo_t)}–{fmt_p(hi_t)}</span>'
                 if round(lo_t) != round(hi_t) else "")
    body = f"""
  <p class="hint">Цены — закупка без наценки, BYN, за позицию целиком; серым под ценой — вилка. Знаете, где дешевле
  или лучше, — впишите в правую колонку: наш выбор не затирается, предложения лягут отдельным слоем.</p>
  <div class="card"><div class="tablebox">
  <table class="table table-vcenter card-table matrix" style="min-width:980px">
    <thead><tr>
      <th>Позиция · зачем так</th><th>Модель</th><th class="num">Кол-во</th>
      <th class="num">Цена, BYN</th><th>Цена</th>{weeks_th}<th style="width:26%">Предложение валидатора</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
    <tfoot><tr><td colspan="3">Итого закупка и внешние услуги</td>
      <td class="num">{fmt_p(total)}{total_rng}</td><td colspan="{ncols - 4}"></td></tr></tfoot>
  </table>
  </div></div>
  {savebar()}"""

    script = f'const API_URL="/api/d/{deal["slug"]}/review/bom";\n' + REVIEW_JS
    return shell(deal, "Компоненты", "bom", body, script)
