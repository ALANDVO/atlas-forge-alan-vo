"""Core configuration and SQLite persistence layer for Atlas Forge."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class Settings:
    app_name: str = "atlas-forge-alan-vo"
    version: str = "0.1.0"
    db_path: str = "atlas_forge.db"
    environment: str = "development"
    demo_mode: bool = True


def get_settings() -> Settings:
    db_path = os.environ.get("ATLAS_FORGE_DB_PATH", "atlas_forge.db")
    env = os.environ.get("ATLAS_FORGE_ENV", "development").strip().lower()
    demo_raw = os.environ.get("ATLAS_FORGE_DEMO_MODE", "true").strip().lower()
    demo_mode = demo_raw in {"1", "true", "yes", "on"}
    if env == "production" and demo_mode:
        raise RuntimeError("Demo mode cannot be enabled when ATLAS_FORGE_ENV=production")
    return Settings(
        db_path=db_path,
        environment=env,
        demo_mode=demo_mode,
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS compositions (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    entry_path TEXT NOT NULL,
    scaffold_root_path TEXT NOT NULL,
    html_source TEXT NOT NULL,
    composition_attr_id TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    fps INTEGER NOT NULL,
    duration_sec REAL NOT NULL,
    total_frames INTEGER NOT NULL,
    readiness_score INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    composition_id TEXT NOT NULL,
    element_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    track_index INTEGER NOT NULL,
    start_sec REAL NOT NULL,
    duration_sec REAL NOT NULL,
    label TEXT NOT NULL,
    x_offset REAL NOT NULL DEFAULT 0.0,
    y_offset REAL NOT NULL DEFAULT 0.0,
    scale REAL NOT NULL DEFAULT 1.0,
    opacity REAL NOT NULL DEFAULT 1.0,
    color_grading TEXT NOT NULL DEFAULT '',
    src_path TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (composition_id) REFERENCES compositions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    composition_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_db(db_path: str | None = None) -> None:
    target = db_path or get_settings().db_path
    if target != ":memory:":
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    with get_connection(target) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def get_connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    target = db_path or get_settings().db_path
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()
