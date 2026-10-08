"""CSPL-сборщик: обходит data/deals/*, строит карточки проектов в build/.

Запуск: python -m generators.build  (также вызывается при старте сервера).
Карточка = набор страниц; страница собирается, если у сделки есть её спека.
«Обзор» (package) есть всегда.
"""
import json
from pathlib import Path

import yaml

from . import (bom_page, overview_page, process_page, proposal_page, questions_page,
               solution_page, wbs_page)
from .common import PAGES, esc

BASE = Path(__file__).resolve().parent.parent
DEALS = BASE / "data" / "deals"
BUILD = BASE / "build"

# Страница -> генератор. Порядок вкладок задаёт common.PAGES.
SPEC_PAGES = {
    "questions": questions_page,
    "process": process_page,
    "solution": solution_page,
    "wbs": wbs_page,
    "bom": bom_page,
    "proposal": proposal_page,
}


def _index(deals: list[dict]) -> str:
    labels = dict(PAGES)
    cards = "".join(f"""
    <div class="col-md-6 col-lg-4 d-flex">
      <div class="card flex-fill"><div class="card-body d-flex flex-column">
        <div class="d-flex align-items-start justify-content-between gap-2 mb-1">
          <span class="dcode">{esc(d["code"])}</span>
          <span class="badge bg-yellow-lt flex-shrink-0">{esc(d["status"])}</span>
        </div>
        <b class="dtitle">{esc(d["title"])}</b>
        <div class="text-secondary mt-1" style="font-size:12px">{esc(d["version"])} · {esc(str(d["updated"]))}</div>
        <div class="text-secondary mt-1" style="font-size:11.5px">
          {esc(" · ".join(labels[p] for p in d.get("pages", []) if p != "package"))}</div>
        <a class="btn btn-sm btn-primary mt-3 mt-auto" href="/d/{esc(d["slug"])}/">Открыть карточку</a>
      </div></div>
    </div>""" for d in deals)
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Портал валидации · ПромРоботы</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/static/tabler.min.css">
<style>.wrap{{max-width:1180px;margin:0 auto;padding:24px 16px}}
.dcode{{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--tblr-secondary)}}
.dtitle{{font-size:15px;line-height:1.3;display:block}}
.card-body{{min-height:150px}}</style></head>
<body><div class="wrap">
  <h2 class="page-title mb-3">Проекты на проверке</h2>
  <div class="row g-3">{cards}</div>
</div></body></html>"""


def _load_schematic(deal_dir: Path) -> dict | None:
    """Спека схемы + инлайн SVG-видов из data/deals/<slug>/schematic/*.svg (для вкладки «Компоненты»)."""
    if not (deal_dir / "schematic.yaml").exists():
        return None
    spec = yaml.safe_load((deal_dir / "schematic.yaml").read_text())
    for v in spec.get("views", []):
        f = deal_dir / v["file"]
        if f.exists():
            v["svg"] = f.read_text(encoding="utf-8")
        else:
            print(f"! schematic ({deal_dir.name}): нет файла вида {v['file']}")
    return spec


def _load_wbs(deal_dir: Path) -> dict:
    """WBS + содержимое блоков «Выход / Вход» этапов из соседнего stage_io.yaml."""
    wbs = yaml.safe_load((deal_dir / "wbs.yaml").read_text())
    io_file = deal_dir / "stage_io.yaml"
    if io_file.exists():
        io = yaml.safe_load(io_file.read_text()) or {}
        unknown = set(io) - {st["name"] for st in wbs["stages"]}
        if unknown:
            print(f"! stage_io.yaml ({deal_dir.name}): нет такого этапа: {sorted(unknown)}")
        for st in wbs["stages"]:
            st.update(io.get(st["name"], {}))
    return wbs


def build_all() -> list[str]:
    built: list[str] = []
    deals: list[dict] = []
    BUILD.mkdir(exist_ok=True)
    for deal_dir in sorted(DEALS.iterdir()):
        if not (deal_dir / "deal.yaml").exists():
            continue
        deal = yaml.safe_load((deal_dir / "deal.yaml").read_text())
        deal["pages"] = ["package"] + [p for p in SPEC_PAGES if (deal_dir / f"{p}.yaml").exists()]
        deals.append(deal)
        out = BUILD / deal["slug"]
        out.mkdir(parents=True, exist_ok=True)
        for page, module in SPEC_PAGES.items():
            if page not in deal["pages"]:
                continue
            if page == "wbs":
                spec = _load_wbs(deal_dir)
            else:
                spec = yaml.safe_load((deal_dir / f"{page}.yaml").read_text())
            if page == "bom":
                sch = _load_schematic(deal_dir)
                if sch:
                    spec["schematic"] = sch
            (out / f"{page}.html").write_text(module.render(deal, spec))
            built.append(f"{deal['slug']}/{page}.html")
        pkg_spec = {}
        if (deal_dir / "package.yaml").exists():
            pkg_spec = yaml.safe_load((deal_dir / "package.yaml").read_text()) or {}
        (out / "package.html").write_text(overview_page.render(deal, pkg_spec))
        built.append(f"{deal['slug']}/package.html")
    (BUILD / "index.html").write_text(_index(deals))
    (BUILD / "deals.json").write_text(json.dumps(deals, ensure_ascii=False, indent=1))
    built += ["index.html", "deals.json"]
    return built


if __name__ == "__main__":
    for page in build_all():
        print("built", page)
