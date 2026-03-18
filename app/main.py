from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.collector.runner import run as collector_run
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.routers import auth, collect, festivals, notification_settings, search_keywords

logger = logging.getLogger(__name__)
settings = get_settings()


def _scheduled_collect() -> None:
    """スケジューラから呼び出される収集バッチ。"""
    logger.info("定期収集バッチ 開始")
    with SessionLocal() as db:
        summary = collector_run(db)
    logger.info(
        "定期収集バッチ 完了 — %d件新規登録 / %d サイト",
        summary.total_new_festivals,
        summary.total_sites,
    )


def _keepalive() -> None:
    """Supabase が非アクティブで停止しないよう 15 分ごとに DB へアクセスする。"""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.debug("Supabase keepalive: OK")
    except Exception:
        logger.warning("Supabase keepalive: failed", exc_info=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    scheduler = BackgroundScheduler(timezone="Asia/Tokyo")
    # 毎日 8:00 JST に収集バッチを実行
    scheduler.add_job(_scheduled_collect, "cron", hour=8, minute=0)
    # 15 分ごとに Supabase へアクセスして停止を防ぐ
    scheduler.add_job(_keepalive, "interval", minutes=15)
    scheduler.start()
    logger.info("スケジューラ起動: 毎日 08:00 JST に収集バッチを実行、15 分ごとに DB keepalive")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        logger.info("スケジューラ停止")


app = FastAPI(
    title="Music Festival Manager API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(festivals.router, prefix=API_PREFIX)
app.include_router(notification_settings.router, prefix=API_PREFIX)
app.include_router(collect.router, prefix=API_PREFIX)
app.include_router(search_keywords.router, prefix=API_PREFIX)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ping")
def health_ping() -> dict[str, str]:
    """cron-job.org から呼び出される DB 疎通確認エンドポイント。"""
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok"}
