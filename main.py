"""Портал валидации ПромРоботы.

v0.2: страницы WBS и компонентов строятся CSPL-генераторами из data/deals/*,
правки валидаторов сохраняются слоем в runtime/ (наша версия не затирается).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from generators.build import BUILD, build_all

BASE_DIR = Path(__file__).resolve().parent
RUNTIME = Path(os.environ.get("RUNTIME_DIR", BASE_DIR / "runtime"))
DB_URL = os.environ.get("DATABASE_URL")

app = FastAPI(title="PromRoboty Validation Portal", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    build_all()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if DB_URL:
        with _db() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS reviews (
                id serial PRIMARY KEY, slug text NOT NULL, page text NOT NULL,
                entry jsonb NOT NULL, ts timestamptz DEFAULT now())""")
            conn.commit()


def _db():
    import psycopg
    return psycopg.connect(DB_URL)


def _get_updates(slug: str, page: str) -> dict:
    """Слои правок: Postgres, если подключён, иначе файлы runtime/."""
    if DB_URL:
        with _db() as conn:
            rows = conn.execute(
                "SELECT entry FROM reviews WHERE slug=%s AND page=%s ORDER BY id",
                (slug, page)).fetchall()
        return {"updates": [r[0] for r in rows]}
    path = RUNTIME / slug / f"{page}.json"
    if not path.exists():
        return {"updates": []}
    return json.loads(path.read_text())


def _add_update(slug: str, page: str, entry: dict) -> int:
    if DB_URL:
        with _db() as conn:
            conn.execute(
                "INSERT INTO reviews (slug, page, entry) VALUES (%s, %s, %s)",
                (slug, page, json.dumps(entry, ensure_ascii=False)))
            conn.commit()
            n = conn.execute(
                "SELECT count(*) FROM reviews WHERE slug=%s AND page=%s",
                (slug, page)).fetchone()[0]
        return n
    path = RUNTIME / slug / f"{page}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {"updates": []}
    data["updates"].append(entry)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return len(data["updates"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.3"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BUILD / "index.html")


@app.get("/d/{slug}/{page}")
def deal_page(slug: str, page: str) -> FileResponse:
    if page not in ("wbs", "bom"):
        raise HTTPException(404)
    path = BUILD / slug / f"{page}.html"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


class Review(BaseModel):
    reviewer: str
    done: bool = False
    hours: dict[str, int] = {}
    comments: dict[str, str] = {}
    alts: dict[str, str] = {}


def _check_ref(slug: str, page: str) -> None:
    if page not in ("wbs", "bom") or "/" in slug or ".." in slug:
        raise HTTPException(404)


@app.get("/api/deals")
def deals() -> FileResponse:
    return FileResponse(BUILD / "deals.json")


@app.get("/api/d/{slug}/review/{page}")
def get_review(slug: str, page: str) -> JSONResponse:
    _check_ref(slug, page)
    return JSONResponse(_get_updates(slug, page))


@app.post("/api/d/{slug}/review/{page}")
def post_review(slug: str, page: str, review: Review) -> dict:
    _check_ref(slug, page)
    entry = review.model_dump()
    entry["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = _add_update(slug, page, entry)
    return {"status": "ok", "updates": n}


@app.post("/api/transcribe")
async def transcribe(file: UploadFile) -> dict:
    """Голосовой комментарий -> текст (OpenAI). Ключ только в env Railway."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise HTTPException(503, "распознавание не настроено")
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "запись длиннее лимита")
    last_err = "нет ответа"
    for model in ("gpt-4o-mini-transcribe", "whisper-1"):
        r = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (file.filename or "rec.webm", data, file.content_type or "audio/webm")},
            data={"model": model, "language": "ru"},
            timeout=90,
        )
        if r.ok:
            return {"text": r.json().get("text", "")}
        last_err = r.text[:200]
    raise HTTPException(502, last_err)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
