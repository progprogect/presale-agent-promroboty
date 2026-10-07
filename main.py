"""Портал валидации ПромРоботы.

v0.2: страницы WBS и компонентов строятся CSPL-генераторами из data/deals/*,
правки валидаторов сохраняются слоем в runtime/ (наша версия не затирается).
"""
import base64
import json
import mimetypes
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from generators.build import BUILD, DEALS, build_all
from generators.common import PAGE_IDS

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
            conn.execute("""CREATE TABLE IF NOT EXISTS pipeline_files (
                path text PRIMARY KEY, content bytea NOT NULL,
                content_type text NOT NULL, updated timestamptz DEFAULT now())""")
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
    return {"status": "ok", "version": "0.6"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BUILD / "index.html")


@app.get("/d/{slug}")
@app.get("/d/{slug}/")
def deal_card(slug: str) -> FileResponse:
    """Корень карточки проекта — страница «Обзор»."""
    return deal_page(slug, "package")


@app.get("/d/{slug}/{page}")
def deal_page(slug: str, page: str) -> FileResponse:
    if page not in PAGE_IDS:
        raise HTTPException(404)
    path = BUILD / slug / f"{page}.html"
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path)


def _deal_file(slug: str, folder: str, name: str) -> FileResponse:
    """Файл сделки (кадр компоновки, собранное ТКП) из data/deals/<slug>/<folder>/."""
    if "/" in slug or ".." in slug or "/" in name or ".." in name:
        raise HTTPException(404)
    path = DEALS / slug / folder / name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.get("/d/{slug}/img/{name}")
def deal_img(slug: str, name: str) -> FileResponse:
    return _deal_file(slug, "img", name)


@app.get("/d/{slug}/proposal/{name}")
def deal_proposal_file(slug: str, name: str) -> FileResponse:
    return _deal_file(slug, "proposal", name)


# ---------- Пайплайн: полный внутренний дашборд под паролем ----------
# Файлы (index.html + ТЗ сделок) выгружаются с машины Микиты скриптом
# tools/push_pipeline.py НАПРЯМУЮ в Postgres — в публичный репозиторий не попадают.
# Доступ на чтение — HTTP Basic (PIPELINE_USER / PIPELINE_PASSWORD в env Railway),
# выгрузка — токен PIPELINE_UPLOAD_TOKEN.

def _pipeline_auth(request: Request) -> None:
    user = os.environ.get("PIPELINE_USER", "")
    pwd = os.environ.get("PIPELINE_PASSWORD", "")
    if not (user and pwd):
        raise HTTPException(503, "раздел не настроен")
    hdr = request.headers.get("authorization", "")
    ok = False
    if hdr.startswith("Basic "):
        try:
            got_u, _, got_p = base64.b64decode(hdr[6:]).decode("utf-8").partition(":")
            ok = secrets.compare_digest(got_u, user) and secrets.compare_digest(got_p, pwd)
        except Exception:
            ok = False
    if not ok:
        raise HTTPException(401, "нужен вход",
                            headers={"WWW-Authenticate": 'Basic realm="pipeline"'})


def _pipeline_path_ok(path: str) -> bool:
    return bool(path.strip()) and ".." not in path and not path.startswith("/") and "\\" not in path


def _pipeline_ct(path: str) -> str:
    if path.endswith(".md"):
        return "text/plain; charset=utf-8"
    if path.endswith(".html"):
        return "text/html; charset=utf-8"
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _pipeline_get(path: str):
    if DB_URL:
        with _db() as conn:
            row = conn.execute(
                "SELECT content, content_type FROM pipeline_files WHERE path=%s",
                (path,)).fetchone()
        return (bytes(row[0]), row[1]) if row else None
    f = RUNTIME / "pipeline" / path
    if not f.is_file():
        return None
    return f.read_bytes(), _pipeline_ct(path)


def _pipeline_put(path: str, data: bytes, ct: str) -> None:
    if DB_URL:
        with _db() as conn:
            conn.execute("""INSERT INTO pipeline_files (path, content, content_type, updated)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (path) DO UPDATE SET content = EXCLUDED.content,
                  content_type = EXCLUDED.content_type, updated = now()""",
                         (path, data, ct))
            conn.commit()
        return
    f = RUNTIME / "pipeline" / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)


@app.get("/pipeline")
@app.get("/pipeline/{path:path}")
def pipeline_view(request: Request, path: str = "") -> Response:
    _pipeline_auth(request)
    path = path or "index.html"
    if not _pipeline_path_ok(path):
        raise HTTPException(404)
    row = _pipeline_get(path)
    if row is None:
        raise HTTPException(404, "файл ещё не выгружен (tools/push_pipeline.py)")
    content, ct = row
    return Response(content=content, media_type=ct,
                    headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


@app.post("/api/pipeline/upload")
async def pipeline_upload(request: Request, path: str) -> dict:
    token = os.environ.get("PIPELINE_UPLOAD_TOKEN", "")
    if not token:
        raise HTTPException(503, "выгрузка не настроена")
    if not secrets.compare_digest(request.headers.get("x-pipeline-token", ""), token):
        raise HTTPException(403)
    if not _pipeline_path_ok(path):
        raise HTTPException(400, "плохой путь")
    data = await request.body()
    if len(data) > 30 * 1024 * 1024:
        raise HTTPException(413, "файл больше 30 МБ")
    _pipeline_put(path, data, _pipeline_ct(path))
    return {"status": "ok", "path": path, "bytes": len(data)}


class Review(BaseModel):
    reviewer: str
    done: bool = False
    hours: dict[str, float] = {}
    comments: dict[str, str] = {}
    alts: dict[str, str] = {}
    fields: dict[str, str] = {}
    added: list[dict] = []


def _check_ref(slug: str, page: str) -> None:
    if page not in PAGE_IDS or "/" in slug or ".." in slug:
        raise HTTPException(404)


@app.get("/api/deals")
def deals() -> FileResponse:
    return FileResponse(BUILD / "deals.json")


@app.get("/api/d/{slug}/review/{page}")
def get_review(slug: str, page: str) -> JSONResponse:
    _check_ref(slug, page)
    return JSONResponse(_get_updates(slug, page))


@app.get("/api/d/{slug}/status")
def deal_status(slug: str) -> JSONResponse:
    """Состояние разделов карточки: сколько слоёв правок и кто завершил проверку."""
    if "/" in slug or ".." in slug:
        raise HTTPException(404)
    out = {}
    for page in PAGE_IDS:
        ups = _get_updates(slug, page)["updates"]
        if not ups:
            continue
        done = [u for u in ups if u.get("done")]
        out[page] = {"updates": len(ups), "done_by": done[-1]["reviewer"] if done else None,
                     "ts": ups[-1].get("ts")}
    return JSONResponse(out)


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
