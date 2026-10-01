"""CSPL-сборщик: обходит data/deals/*, строит страницы в build/.

Запуск: python -m generators.build  (также вызывается при старте сервера).
"""
from pathlib import Path

import yaml

from . import bom_page, wbs_page
from .common import esc

BASE = Path(__file__).resolve().parent.parent
DEALS = BASE / "data" / "deals"
BUILD = BASE / "build"


def _index(deals: list[dict]) -> str:
    cards = "".join(f"""
    <div class="col-md-5 col-lg-4">
      <div class="card"><div class="card-body">
        <div class="d-flex align-items-baseline gap-2">
          <b>{esc(d["title"])}</b><span class="text-secondary">{esc(d["code"])}</span>
          <span class="badge bg-yellow-lt ms-auto">{esc(d["status"])}</span>
        </div>
        <div class="text-secondary" style="font-size:12px">{esc(d["version"])} · {esc(str(d["updated"]))}</div>
        <div class="mt-2 d-flex gap-2">
          <a class="btn btn-sm" href="/d/{esc(d["slug"])}/wbs">Декомпозиция</a>
          <a class="btn btn-sm" href="/d/{esc(d["slug"])}/bom">Компоненты</a>
        </div>
      </div></div>
    </div>""" for d in deals)
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Портал валидации · ПромРоботы</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/static/tabler.min.css">
<style>.wrap{{max-width:1180px;margin:0 auto;padding:24px 16px}}</style></head>
<body><div class="wrap">
  <h2 class="page-title mb-3">Проекты на проверке</h2>
  <div class="row g-3">{cards}</div>
</div></body></html>"""


def build_all() -> list[str]:
    built = []
    deals = []
    BUILD.mkdir(exist_ok=True)
    for deal_dir in sorted(DEALS.iterdir()):
        if not (deal_dir / "deal.yaml").exists():
            continue
        deal = yaml.safe_load((deal_dir / "deal.yaml").read_text())
        deals.append(deal)
        out = BUILD / deal["slug"]
        out.mkdir(parents=True, exist_ok=True)
        wbs_file = deal_dir / "wbs.yaml"
        if wbs_file.exists():
            wbs = yaml.safe_load(wbs_file.read_text())
            (out / "wbs.html").write_text(wbs_page.render(deal, wbs))
            built.append(f"{deal['slug']}/wbs.html")
        bom_file = deal_dir / "bom.yaml"
        if bom_file.exists():
            bom = yaml.safe_load(bom_file.read_text())
            (out / "bom.html").write_text(bom_page.render(deal, bom))
            built.append(f"{deal['slug']}/bom.html")
    (BUILD / "index.html").write_text(_index(deals))
    built.append("index.html")
    return built


if __name__ == "__main__":
    for page in build_all():
        print("built", page)
