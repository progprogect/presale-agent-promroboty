"""CSPL-конвертер: смета сделки -> спеки портала (data/deals/<slug>/wbs.yaml, bom.yaml).

Запуск:  python -m generators.from_lead <rules.yaml> [--diff]

rules.yaml лежит В ПАПКЕ СДЕЛКИ (не в репозитории: репозиторий публичный, а правила содержат
имена, которые на портале показывать нельзя). Поля:
  slug:        слаг сделки на портале
  wbs:         wbs.yaml сметы (формат wbs-from-estimate); пути — от папки rules.yaml или абсолютные
  wbs_options: wbs_options.yaml (необязательно) — этапы-опции, уходят на портал вне итога
  bom:         плоская выгрузка BOM для портала (items: pos, model, qty, why, price, conf, price_note)
  bom_source:  полная спека BOM (необязательно) — только ради сроков поставки (lead_weeks)
  bom_totals:  bom.totals.json (необязательно) — сверка суммы вилок
  bom_variant: вариант в bom_source/bom_totals (по умолчанию V2)
  lock_groups: группы WBS, закрытые от правок валидаторов (CV/ПО — оценивает Микита)
  replace:     [[regex, замена], ...] — замены текста (имена, коды чужих сделок, внутренние слова)
  forbid:      регулярные выражения, которых не должно остаться в результате (без учёта регистра)

Что делает: чистит тексты (внутренние пути, ссылки на аудит и допущения, replace), помечает
опции, превращает раздел BOM в группу, разбирает вилку цены из price_note, подтягивает сроки,
сверяет итоги с источником и пишет спеки. Детерминирован, без LLM и сети.
"""
import json
import re
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent.parent

# Общие правила чистки: внутренние ссылки нашей системы, которые валидатору ничего не говорят.
GENERIC = [
    (r"\s*\(аудит [^)]*\)", ""),                      # «(аудит 02.10.2026, находки …)»
    (r"[;.]\s*находка аудита № \d+", ""),
    (r"[;.]\s*находка № \d+", ""),
    (r"\s*;?\s*находка № \d+", ""),
    (r"([.;])\s*аудит № \d+:\s*", r"\1 "),            # «. аудит № 6: ≈3 мин» -> «. ≈3 мин»
    (r"\s*[;.]\s*аудит № \d+(?=\s*[;.)]|\s*$)", ""),   # «; аудит № 7», «. аудит № 1»
    (r"[;.]\s*аудит(?=\s*$)", ""),                    # хвостовое «; аудит»
    (r"\s*\((?:knowledge|leads)/[^)]*\)", ""),        # (knowledge/norms/….md)
    (r"knowledge/normy-vremeni\.md", "базы норм времени"),
    (r"в knowledge/components/docs-inovance", "в нашей базе документов"),
    (r"\s*;\s*разд\.\s*9\s*spec\.md", ""),
    (r"\s*\(05_sim\)", " (по симуляции)"),
    (r"sim-report", "отчёт симуляции"),
    (r"\s*\((?:допущение\s+)?A\d+(?:\s*,\s*A\d+)*\)", ""),   # (A2), (допущение A2), (A19, A21)
    (r",\s*A\d+\)", ")"),                             # «…, A19)»
    (r"\s*\(X\d+\)", ""),
    (r"\s*допущения\s+A\d+(?:\s*,\s*A\d+)*", ""),
    (r"\s+A\d+(?:,\s*A\d+)+$", ""),                   # хвост «A5, A10, A11»
]


def _load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _p(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p)


class Cleaner:
    def __init__(self, replace):
        self.rules = [(re.compile(a), b) for a, b in replace] + [(re.compile(a), b) for a, b in GENERIC]
        self.changes = []

    def s(self, text: str) -> str:
        out = re.sub(r"\s+", " ", text).strip()
        for rx, repl in self.rules:
            out = rx.sub(repl, out)
        out = re.sub(r"\s+", " ", out).strip()
        if out != re.sub(r"\s+", " ", text).strip():
            self.changes.append((text, out))
        return out

    def walk(self, node):
        if isinstance(node, str):
            return self.s(node)
        if isinstance(node, list):
            return [self.walk(x) for x in node]
        if isinstance(node, dict):
            return {k: self.walk(v) for k, v in node.items()}
        return node


def _num(text: str) -> float:
    return float(re.sub(r"[\s  ]", "", text).replace(",", "."))


RANGE = re.compile(r"вилка\s+([\d\s  .,]+?)\s*(?:[–-]\s*([\d\s  .,]+?))?\s*BYN")


def convert_wbs(rules: dict, base: Path, cl: Cleaner) -> tuple[dict, dict]:
    wbs = _load(_p(base, rules["wbs"]))
    lock = set(rules.get("lock_groups") or [])
    roles = wbs["roles"]
    stages = []
    for st in wbs["stages"]:
        stages.append(st)
    n_base = sum(len(s["tasks"]) for s in stages)
    h_base = sum(sum(t["hours"].values()) for s in stages for t in s["tasks"])
    n_opt = h_opt = 0
    if rules.get("wbs_options"):
        opts = _load(_p(base, rules["wbs_options"]))
        if opts["roles"] != roles:
            sys.exit("роли в wbs_options не совпадают с wbs")
        for st in opts["stages"]:
            st["option"] = True
            st["name"] = re.sub(r"^([А-ЯA-Z]+\d+)\.\s+", r"\1 · ", st["name"])
            n_opt += len(st["tasks"])
            h_opt += sum(sum(t["hours"].values()) for t in st["tasks"])
            stages.append(st)
    ids = [t["id"] for s in stages for t in s["tasks"]]
    if len(ids) != len(set(ids)):
        sys.exit("повторяющиеся id пакетов")
    for st in stages:
        for t in st["tasks"]:
            if t.get("group") in lock:
                t["lock"] = True
    out = {"roles": roles, "role_names": wbs["role_names"], "stages": stages}
    out = cl.walk(out)
    # сверка с шапкой источника: «# Пакетов: 432, часов: 10367»
    head = _p(base, rules["wbs"]).read_text(encoding="utf-8").splitlines()[:3]
    m = re.search(r"Пакетов:\s*(\d+),\s*часов:\s*(\d+)", " ".join(head))
    if m and (int(m.group(1)), int(m.group(2))) != (n_base, round(h_base)):
        sys.exit(f"не сходится с шапкой источника: {m.groups()} против {(n_base, round(h_base))}")
    return out, {"packages": n_base, "hours": h_base, "opt_packages": n_opt, "opt_hours": h_opt}


def convert_bom(rules: dict, base: Path, cl: Cleaner) -> tuple[dict, dict]:
    items = _load(_p(base, rules["bom"]))["items"]
    weeks = {}
    if rules.get("bom_source"):
        src = _load(_p(base, rules["bom_source"]))
        var = [v for v in src["variants"] if v["id"] == rules.get("bom_variant", "V2")][0]
        norm = lambda t: re.sub(r"\s+", " ", t).strip()[:50]  # noqa: E731
        flat = [it for sec in var["sections"] for it in sec["items"]]
        j = 0
        for it in flat:  # выгрузка = те же позиции по порядку без позиций «не в сумме»
            if j < len(items) and norm(it["item"]) == norm(items[j]["pos"]):
                if it.get("lead_weeks"):
                    weeks[j] = list(it["lead_weeks"])
                j += 1
        if j != len(items):
            sys.exit(f"не удалось сопоставить сроки: {j} из {len(items)}")
    out, lo_t, hi_t, tot = [], 0.0, 0.0, 0.0
    for idx, it in enumerate(items):
        # группа: явное поле item приоритетно; иначе (формат tor-bal) выводится из why,
        # и тогда why — это группа, а не пояснение
        explicit_group = it.get("group")
        new = {
            "pos": it["pos"], "model": it["model"], "qty": str(it["qty"]),
            "group": explicit_group or (
                re.split(r"\s+\(", it["why"], maxsplit=1)[0].strip() if it.get("why") else None),
            "why": it.get("why") if explicit_group else None,
            "price": it.get("price"), "conf": it.get("conf"), "price_note": it.get("price_note", ""),
        }
        if it.get("range"):
            new["range"] = list(it["range"])
            lo, hi = it["range"]
        else:
            m = RANGE.search(it.get("price_note", ""))
            if m:
                lo = _num(m.group(1))
                hi = _num(m.group(2)) if m.group(2) else lo
                new["range"] = [int(lo) if lo == int(lo) else lo, int(hi) if hi == int(hi) else hi]
            else:
                lo = hi = it.get("price") or 0
        if new.get("range"):
            price = it.get("price") or 0
            if not (lo - 1 <= price <= hi + 1):
                print(f"  ! цена вне вилки: {it['pos'][:50]} {price} не в {lo}–{hi}")
        lo_t += lo
        hi_t += hi
        tot += it.get("price") or 0
        status = it.get("price_note", "").split(";")[-1].strip()
        if status == "не найдено":
            new["conf_label"] = "не найдено"
        elif it.get("conf") == "high":
            new["conf_label"] = "подтверждена"
        elif it.get("conf") == "mid":
            new["conf_label"] = "оценка · есть ориентир"
        else:
            new["conf_label"] = "оценка · RFQ"
        if it.get("conf_label"):
            new["conf_label"] = it["conf_label"]
        if idx in weeks:
            new["weeks"] = weeks[idx]
        elif it.get("weeks"):
            new["weeks"] = list(it["weeks"])
            weeks[idx] = new["weeks"]
        out.append({k: v for k, v in new.items() if v not in (None, "")})
    out = cl.walk(out)
    if rules.get("bom_totals"):
        t = json.loads(_p(base, rules["bom_totals"]).read_text())[rules.get("bom_variant", "V2")]
        # в сумме вилок выгрузки нет двух позиций «не в сумме»; сверяем с допуском 0,5 %
        for name, mine, theirs in (("мин", lo_t, t["min"]), ("макс", hi_t, t["max"])):
            if abs(mine - theirs) > 0.005 * theirs:
                sys.exit(f"сумма вилок ({name}) не сходится: {mine:.0f} против {theirs:.0f}")
    return {"items": out}, {"items": len(out), "total": tot, "lo": lo_t, "hi": hi_t,
                            "weeks": len(weeks)}


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    rules_path = Path(args[0]).resolve()
    rules = _load(rules_path)
    base = rules_path.parent
    cl = Cleaner(rules.get("replace") or [])
    out_dir = BASE / "data" / "deals" / rules["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)

    wbs, ws = convert_wbs(rules, base, cl)
    bom, bs = convert_bom(rules, base, cl)

    head = ("# Сгенерировано generators/from_lead.py из сметы сделки. Правка = правка источника + пересборка.\n"
            "# Деньги (ставки, себестоимость, маржа) сюда не попадают: только часы и цены закупки.\n")
    dump = lambda d: yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=100)  # noqa: E731
    wtxt, btxt = dump(wbs), dump(bom)

    bad = [w for w in (rules.get("forbid") or []) if re.search(w, wtxt + btxt, re.I)]
    if bad:
        sys.exit(f"в результате остались запрещённые слова: {bad}")

    (out_dir / "wbs.yaml").write_text(head + wtxt, encoding="utf-8")
    (out_dir / "bom.yaml").write_text(head + btxt, encoding="utf-8")
    print(f"WBS: {ws['packages']} пакетов, {ws['hours']:.0f} ч; опции: {ws['opt_packages']} пак., "
          f"{ws['opt_hours']:.0f} ч")
    print(f"BOM: {bs['items']} позиций, сумма {bs['total']:.0f}, вилка {bs['lo']:.0f}–{bs['hi']:.0f} BYN, "
          f"сроки у {bs['weeks']} позиций")
    print(f"Чистка текстов: изменено строк {len(cl.changes)}; запрещённых слов нет")
    if "--diff" in sys.argv:
        for old, new in cl.changes:
            print(f"- {old}\n+ {new}\n")


if __name__ == "__main__":
    main()
