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


# Роли: ключ -> (название, за что отвечает). Правится только здесь.
ROLES = {
    "delivery": ("Delivery-менеджер", "всё по проекту: гейты, финальное «пакет принят»"),
    "tech": ("Технолог", "компоновка ячейки целиком и всё вокруг неё"),
    "electro": ("Электрик", "электрика и электросеть"),
    "robo": ("Подрядчик по роботам", "КД и установка робота"),
    "soft": ("Специалист по ПО", "программное обеспечение"),
    "viewer": ("Наблюдатель", "только просмотр"),
}


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
            conn.execute("""CREATE TABLE IF NOT EXISTS people (
                id serial PRIMARY KEY, name text NOT NULL, email text NOT NULL,
                org text DEFAULT '', role text DEFAULT 'viewer',
                token text UNIQUE NOT NULL, active boolean DEFAULT true,
                created timestamptz DEFAULT now())""")
            conn.execute("""CREATE TABLE IF NOT EXISTS assignments (
                id serial PRIMARY KEY, person_id int NOT NULL REFERENCES people(id),
                slug text NOT NULL, role text NOT NULL, pages jsonb,
                kp boolean DEFAULT false, created timestamptz DEFAULT now(),
                UNIQUE (person_id, slug))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS events (
                id serial PRIMARY KEY, ts timestamptz DEFAULT now(),
                type text NOT NULL, slug text DEFAULT '', payload jsonb,
                done boolean DEFAULT false, done_ts timestamptz)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS kv (
                key text PRIMARY KEY, value jsonb)""")
            conn.execute("""INSERT INTO kv (key, value) VALUES ('tpl_invite', %s)
                ON CONFLICT (key) DO NOTHING""", (json.dumps(TPL_INVITE_DEFAULT, ensure_ascii=False),))
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


# ---------- Люди, назначения, очередь событий (см. docs/ARCHITECTURE-ROLES.md) ----------

# Шаблон приглашения (правится в админке, хранится в kv). Плейсхолдеры:
# {name} {deal_title} {deal_code} {role_name} {link} {kp_note}
TPL_INVITE_DEFAULT = {
    "subject": "Проект «{deal_title}» — нужна ваша проверка",
    "body": """Добрый день!

Подключаем вас к проверке проекта «{deal_title}» в роли «{role_name}».
Ваша персональная страница со списком разделов: {link}

Открывайте разделы, правьте значения и оставляйте комментарии прямо на странице
(есть голосовой ввод); в конце раздела нажмите «Проверка завершена». Правки ложатся
отдельным слоем — ничего не затирается.{kp_note}

Вопросы можно писать прямо в комментариях на странице.""",
}
TEMPLATE_KEYS = ("tpl_invite",)


class _SafeMap(dict):
    def __missing__(self, key):  # незнакомый плейсхолдер не валит рендер
        return "{" + key + "}"


def _kv_get(key: str, default=None):
    with _db() as conn:
        row = conn.execute("SELECT value FROM kv WHERE key=%s", (key,)).fetchone()
    return row[0] if row else default


def _kv_set(key: str, value) -> None:
    with _db() as conn:
        conn.execute("""INSERT INTO kv (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value""",
                     (key, json.dumps(value, ensure_ascii=False)))
        conn.commit()

def _need_db() -> None:
    if not DB_URL:
        raise HTTPException(503, "раздел требует базы данных")


def _admin_auth(request: Request) -> None:
    user = os.environ.get("ADMIN_USER") or os.environ.get("PIPELINE_USER", "")
    pwd = os.environ.get("ADMIN_PASSWORD") or os.environ.get("PIPELINE_PASSWORD", "")
    if not (user and pwd):
        raise HTTPException(503, "админка не настроена")
    hdr = request.headers.get("authorization", "")
    ok = False
    if hdr.startswith("Basic "):
        try:
            got_u, _, got_p = base64.b64decode(hdr[6:]).decode("utf-8").partition(":")
            ok = secrets.compare_digest(got_u, user) and secrets.compare_digest(got_p, pwd)
        except Exception:
            ok = False
    if not ok:
        raise HTTPException(401, "нужен вход", headers={"WWW-Authenticate": 'Basic realm="admin"'})


def _agent_auth(request: Request) -> None:
    key = os.environ.get("AGENT_KEY", "")
    if not key:
        raise HTTPException(503, "агентский доступ не настроен")
    if not secrets.compare_digest(request.headers.get("x-agent-key", ""), key):
        raise HTTPException(403)


def _add_event(etype: str, slug: str = "", payload: dict | None = None) -> int | None:
    if not DB_URL:
        return None
    with _db() as conn:
        row = conn.execute(
            "INSERT INTO events (type, slug, payload) VALUES (%s, %s, %s) RETURNING id",
            (etype, slug, json.dumps(payload or {}, ensure_ascii=False))).fetchone()
        conn.commit()
    return row[0]


def _deal_titles() -> dict:
    try:
        return {d["slug"]: d for d in json.loads((BUILD / "deals.json").read_text())}
    except Exception:
        return {}


class PersonIn(BaseModel):
    name: str
    email: str
    org: str = ""
    role: str = "viewer"


class AssignIn(BaseModel):
    person_id: int
    slug: str
    role: str
    pages: list[str] | None = None
    kp: bool = False


@app.get("/admin")
def admin_page(request: Request) -> FileResponse:
    _admin_auth(request)
    return FileResponse(BASE_DIR / "static" / "admin.html",
                        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


@app.get("/api/admin/overview")
def admin_overview(request: Request) -> JSONResponse:
    _admin_auth(request)
    _need_db()
    deals_map = _deal_titles()
    with _db() as conn:
        people = [dict(zip(("id", "name", "email", "org", "role", "token", "active"), r))
                  for r in conn.execute(
                      "SELECT id, name, email, org, role, token, active FROM people ORDER BY id")]
        assigns = [dict(zip(("id", "person_id", "slug", "role", "pages", "kp"), r))
                   for r in conn.execute(
                       "SELECT id, person_id, slug, role, pages, kp FROM assignments ORDER BY id")]
        pending = conn.execute("SELECT count(*) FROM events WHERE NOT done").fetchone()[0]
        last = conn.execute("SELECT max(id) FROM events").fetchone()[0] or 0
        ping = conn.execute("SELECT value FROM kv WHERE key='agent_ping'").fetchone()
    status = {}
    for slug in deals_map:
        st = {}
        for page in PAGE_IDS:
            ups = _get_updates(slug, page)["updates"]
            if not ups:
                continue
            done = [u for u in ups if u.get("done")]
            st[page] = {"updates": len(ups), "done_by": done[-1]["reviewer"] if done else None}
        status[slug] = st
    return JSONResponse({"deals": list(deals_map.values()), "people": people,
                         "assignments": assigns, "status": status, "roles": ROLES,
                         "pages": PAGE_IDS, "events_pending": pending, "events_last": last,
                         "agent_ping": ping[0] if ping else None})


@app.post("/api/admin/people")
def admin_add_person(request: Request, p: PersonIn) -> dict:
    _admin_auth(request)
    _need_db()
    if p.role not in ROLES:
        raise HTTPException(400, "нет такой роли")
    token = secrets.token_urlsafe(9)
    with _db() as conn:
        row = conn.execute(
            "INSERT INTO people (name, email, org, role, token) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (p.name.strip(), p.email.strip().lower(), p.org.strip(), p.role, token)).fetchone()
        conn.commit()
    return {"id": row[0], "token": token}


@app.post("/api/admin/people/{pid}/active")
def admin_person_active(request: Request, pid: int, body: dict) -> dict:
    _admin_auth(request)
    _need_db()
    with _db() as conn:
        conn.execute("UPDATE people SET active=%s WHERE id=%s", (bool(body.get("active")), pid))
        conn.commit()
    return {"status": "ok"}


@app.post("/api/admin/assign")
def admin_assign(request: Request, a: AssignIn) -> dict:
    _admin_auth(request)
    _need_db()
    if a.role not in ROLES:
        raise HTTPException(400, "нет такой роли")
    pages = [p for p in (a.pages or []) if p in PAGE_IDS] or None
    with _db() as conn:
        person = conn.execute(
            "SELECT name, email, token FROM people WHERE id=%s AND active", (a.person_id,)).fetchone()
        if not person:
            raise HTTPException(404, "нет такого человека")
        conn.execute("""INSERT INTO assignments (person_id, slug, role, pages, kp)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (person_id, slug) DO UPDATE
              SET role=EXCLUDED.role, pages=EXCLUDED.pages, kp=EXCLUDED.kp""",
                     (a.person_id, a.slug, a.role, json.dumps(pages) if pages else None, a.kp))
        conn.commit()
    deal = _deal_titles().get(a.slug, {})
    # письмо рендерится здесь, по шаблону из админки — локальный агент только отправляет
    tpl = _kv_get("tpl_invite", TPL_INVITE_DEFAULT)
    base = os.environ.get("PUBLIC_URL", "https://project.promroboty.by").rstrip("/")
    ctx = _SafeMap(name=person[0], deal_title=deal.get("title", a.slug),
                   deal_code=deal.get("code", ""), role_name=ROLES[a.role][0],
                   link=f"{base}/u/{person[2]}",
                   kp_note=("\nВам также открыт доступ к итоговому коммерческому предложению "
                            "(вкладка «ТКП»)." if a.kp else ""))
    eid = _add_event("assign", a.slug, {
        "person": {"name": person[0], "email": person[1], "token": person[2]},
        "role": a.role, "role_name": ROLES[a.role][0], "pages": pages, "kp": a.kp,
        "deal_title": deal.get("title", a.slug), "deal_code": deal.get("code", ""),
        "mail": {"to": person[1], "subject": tpl["subject"].format_map(ctx),
                 "body": tpl["body"].format_map(ctx)}})
    return {"status": "ok", "event": eid}


@app.get("/api/admin/templates")
def admin_templates(request: Request) -> JSONResponse:
    _admin_auth(request)
    _need_db()
    return JSONResponse({k: _kv_get(k, TPL_INVITE_DEFAULT) for k in TEMPLATE_KEYS})


@app.post("/api/admin/templates/{key}")
def admin_save_template(request: Request, key: str, body: dict) -> dict:
    _admin_auth(request)
    _need_db()
    if key not in TEMPLATE_KEYS:
        raise HTTPException(404)
    subject, text = str(body.get("subject", "")).strip(), str(body.get("body", "")).strip()
    if not subject or not text:
        raise HTTPException(400, "нужны subject и body")
    _kv_set(key, {"subject": subject, "body": text})
    return {"status": "ok"}


@app.delete("/api/admin/assign/{aid}")
def admin_unassign(request: Request, aid: int) -> dict:
    _admin_auth(request)
    _need_db()
    with _db() as conn:
        conn.execute("DELETE FROM assignments WHERE id=%s", (aid,))
        conn.commit()
    return {"status": "ok"}


@app.post("/api/admin/event")
def admin_event(request: Request, body: dict) -> dict:
    _admin_auth(request)
    _need_db()
    etype = str(body.get("type", "note"))
    if etype not in ("check", "note"):
        raise HTTPException(400, "type: check | note")
    eid = _add_event(etype, str(body.get("slug", "")), {"text": str(body.get("text", ""))[:2000]})
    return {"status": "ok", "event": eid}


# ---------- Очередь для локального агента ----------

@app.get("/api/agent/events")
def agent_events(request: Request, after: int = 0, wait: int = 0) -> JSONResponse:
    _agent_auth(request)
    _need_db()
    import time
    deadline = time.monotonic() + min(max(wait, 0), 25)
    while True:
        with _db() as conn:
            rows = conn.execute(
                "SELECT id, ts, type, slug, payload, done FROM events WHERE id > %s ORDER BY id LIMIT 100",
                (after,)).fetchall()
        if rows or time.monotonic() >= deadline:
            evs = [{"id": r[0], "ts": r[1].isoformat(timespec="seconds"), "type": r[2],
                    "slug": r[3], "payload": r[4], "done": r[5]} for r in rows]
            return JSONResponse({"events": evs})
        time.sleep(1.5)


@app.post("/api/agent/events/{eid}/done")
def agent_event_done(request: Request, eid: int) -> dict:
    _agent_auth(request)
    _need_db()
    with _db() as conn:
        conn.execute("UPDATE events SET done=true, done_ts=now() WHERE id=%s", (eid,))
        conn.commit()
    return {"status": "ok"}


@app.post("/api/agent/ping")
def agent_ping(request: Request, body: dict | None = None) -> dict:
    _agent_auth(request)
    _need_db()
    val = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "note": str((body or {}).get("note", ""))[:200]}
    with _db() as conn:
        conn.execute("""INSERT INTO kv (key, value) VALUES ('agent_ping', %s)
            ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value""",
                     (json.dumps(val, ensure_ascii=False),))
        conn.commit()
    return {"status": "ok"}


# ---------- Личный кабинет ----------

@app.get("/u/{token}")
def user_page(token: str) -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "user.html",
                        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})


@app.get("/api/u/{token}")
def user_data(token: str) -> JSONResponse:
    _need_db()
    with _db() as conn:
        person = conn.execute(
            "SELECT id, name, email, role FROM people WHERE token=%s AND active", (token,)).fetchone()
        if not person:
            raise HTTPException(404)
        assigns = conn.execute(
            "SELECT slug, role, pages, kp FROM assignments WHERE person_id=%s ORDER BY id",
            (person[0],)).fetchall()
    deals_map = _deal_titles()
    out = []
    for slug, role, pages, kp in assigns:
        deal = deals_map.get(slug, {})
        avail = [p for p in deal.get("pages", []) if p != "proposal" or kp]
        my_pages = [p for p in (pages or avail) if p in avail]
        st = {}
        for page in my_pages:
            ups = _get_updates(slug, page)["updates"]
            mine = [u for u in ups if u.get("done")]
            st[page] = {"updates": len(ups), "done": bool(mine)}
        out.append({"slug": slug, "title": deal.get("title", slug), "code": deal.get("code", ""),
                    "status": deal.get("status", ""), "role": role,
                    "role_name": ROLES.get(role, (role,))[0], "pages": my_pages, "kp": kp,
                    "page_status": st})
    return JSONResponse({"name": person[1], "role": person[3], "projects": out,
                         "page_names": {p: n for p, n in
                                        [("package", "Обзор"), ("questions", "Вводные"),
                                         ("process", "Процесс"), ("solution", "Решение"),
                                         ("wbs", "Декомпозиция"), ("bom", "Компоненты"),
                                         ("proposal", "ТКП")]}})


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
    if review.done:  # локальный агент узнаёт о завершённой проверке сразу (очередь событий)
        _add_event("review_done", slug, {"page": page, "reviewer": review.reviewer, "layers": n})
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
