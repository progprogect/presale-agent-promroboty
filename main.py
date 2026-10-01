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

app = FastAPI(title="PromRoboty Validation Portal", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def startup() -> None:
    build_all()
    RUNTIME.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.2"}


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


def _review_file(slug: str, page: str) -> Path:
    if page not in ("wbs", "bom") or "/" in slug or ".." in slug:
        raise HTTPException(404)
    return RUNTIME / slug / f"{page}.json"


@app.get("/api/d/{slug}/review/{page}")
def get_review(slug: str, page: str) -> JSONResponse:
    path = _review_file(slug, page)
    if not path.exists():
        return JSONResponse({"updates": []})
    return JSONResponse(json.loads(path.read_text()))


@app.post("/api/d/{slug}/review/{page}")
def post_review(slug: str, page: str, review: Review) -> dict:
    path = _review_file(slug, page)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text()) if path.exists() else {"updates": []}
    entry = review.model_dump()
    entry["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    data["updates"].append(entry)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    return {"status": "ok", "updates": len(data["updates"])}


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
