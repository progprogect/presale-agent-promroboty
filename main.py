"""Пресейл ПромРоботы — веб-приложение для проверки декомпозиций работ.

v0.1-test: отдаёт статическую демо-страницу (проверка связки GitHub -> Railway).
"""
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="PromRoboty Presale Review", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": "0.1-test"}


# Статика монтируется последней: /health объявлен выше и имеет приоритет.
app.mount("/", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
