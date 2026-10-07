"""Чек-скрипт портала: заказчик не назван, внутренние деньги не утекли.

Запуск:
  python -m generators.check_confidential <rules.yaml> [--live https://project.promroboty.by]

rules.yaml — тот же файл правил, что у from_lead.py (лежит в папке сделки, в репозитории его нет):
берёт slug и список forbid (имена заказчика и чужих сделок). Проверяет собранные страницы build/<slug>/
(и, с --live, те же страницы по адресу портала), а также build/deals.json и build/index.html.

Общие проверки (не зависят от сделки): слова про себестоимость, маржу, ставки, наценку (кроме «без наценки»); ставки «BYN/час»;
любые крупные числа (≥100 000), которых нет среди цен закупки BOM сделки (суммы вилок и итога — допустимы).
Код возврата 1, если что-то найдено.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

from .common import PAGE_IDS

BASE = Path(__file__).resolve().parent.parent
MONEY = [r"себестоим", r"\bмарж", r"\bставк", r"(?<!без )\bнаценк", r"\bрентабельн", r"\bприбыл",
         r"BYN\s*/\s*(?:ч\b|час)", r"руб\w*\s*/\s*(?:ч\b|час)", r"\bоклад", r"зарплат"]
BIG = re.compile(r"\d{1,3}(?:[  ]\d{3})+|\d{6,}")


def allowed_numbers(slug: str) -> set[int]:
    bom = BASE / "data" / "deals" / slug / "bom.yaml"
    out: set[int] = set()
    if not bom.exists():
        return out
    items = yaml.safe_load(bom.read_text())["items"]
    lo = hi = tot = 0
    for it in items:
        p = it.get("price") or 0
        r = it.get("range") or [p, p]
        tot += p
        lo += r[0]
        hi += r[1]
        out.update({round(p), round(r[0]), round(r[1])})
    out.update({round(tot), round(lo), round(hi)})
    return out


def scan(name: str, text: str, forbid: list[str], allowed: set[int]) -> list[str]:
    problems = []
    for rx in forbid + MONEY:
        m = re.search(rx, text, re.I)
        if m:
            problems.append(f"{name}: найдено «{m.group(0)}» (правило {rx})")
    # крупные числа ищем по видимому тексту: из разметки (атрибуты тегов, координаты SVG)
    # деньги не утекают, а слитные координаты фигур дают ложные срабатывания
    visible = re.sub(r"<[^>]*>", "\n", text)  # \n, не пробел: иначе числа соседних ячеек слипаются в «разряды»
    for m in BIG.finditer(visible):
        n = int(re.sub(r"\D", "", m.group(0)))
        if n >= 100_000 and n not in allowed:
            problems.append(f"{name}: крупное число «{m.group(0)}» не из цен BOM")
    return problems


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.4.0"})  # python-urllib режет защита Railway
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    rules = yaml.safe_load(Path(args[0]).read_text(encoding="utf-8"))
    slug, forbid = rules["slug"], rules.get("forbid") or []
    allowed = allowed_numbers(slug)
    built = [p for p in PAGE_IDS if (BASE / "build" / slug / f"{p}.html").exists()]
    if not built:
        sys.exit(f"страницы сделки {slug} не собраны — сначала python -m generators.build")
    texts = {f"build/{slug}/{p}.html": (BASE / "build" / slug / f"{p}.html").read_text(encoding="utf-8")
             for p in built}
    texts["build/deals.json"] = (BASE / "build" / "deals.json").read_text(encoding="utf-8")
    texts["build/index.html"] = (BASE / "build" / "index.html").read_text(encoding="utf-8")
    if "--live" in sys.argv:
        host = sys.argv[sys.argv.index("--live") + 1].rstrip("/")
        for path in [f"/d/{slug}/{p}" for p in built] + ["/api/deals", "/"]:
            texts[host + path] = fetch(host + path)
    problems = []
    for name, text in texts.items():
        problems += scan(name, text, forbid, allowed)
        print(f"проверено {name}: {len(text)} знаков")
    if problems:
        print("\nПРОБЛЕМЫ:")
        print("\n".join(problems))
        sys.exit(1)
    print("Чисто: заказчик и чужие сделки не названы, слов и чисел про внутренние деньги нет.")


if __name__ == "__main__":
    main()
