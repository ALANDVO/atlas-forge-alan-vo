"""Compositions API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.database import get_connection, get_settings
from app.models.schemas import (
    AuditEventModel,
    CompositionCreateRequest,
    CompositionDetail,
    CompositionSummary,
    PaginatedCompositions,
)

router = APIRouter(prefix="/compositions", tags=["compositions"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post(
    "",
    response_model=CompositionSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_composition(request: CompositionCreateRequest):
    settings = get_settings()
    comp_id = str(uuid.uuid4())
    now = _now()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO compositions (
                id, title, entry_path, scaffold_root_path, html_source,
                composition_attr_id, width, height, fps, duration_sec,
                total_frames, readiness_score, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comp_id,
                request.title,
                request.entry_path,
                request.scaffold_root_path,
                request.html_source,
                request.composition_attr_id,
                request.width,
                request.height,
                request.fps,
                request.duration_sec,
                request.total_frames,
                request.readiness_score,
                "ready",
                now,
                now,
            ),
        )
        conn.commit()

        # Add audit event
        conn.execute(
            """
            INSERT INTO audit_events (composition_id, action, actor, summary, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                comp_id,
                "create",
                "system",
                f"Created composition '{request.title}'",
                '{"title": "' + request.title + '"}',
                now,
            ),
        )
        conn.commit()

    return CompositionSummary(
        id=comp_id,
        title=request.title,
        entry_path=request.entry_path,
        scaffold_root_path=request.scaffold_root_path,
        composition_attr_id=request.composition_attr_id,
        width=request.width,
        height=request.height,
        fps=request.fps,
        duration_sec=request.duration_sec,
        total_frames=request.total_frames,
        readiness_score=request.readiness_score,
        status="ready",
        clip_count=0,
        created_at=now,
        updated_at=now,
    )


@router.get("", response_model=PaginatedCompositions)
async def list_compositions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        if status_filter:
            cursor = conn.execute(
                """
                SELECT id, title, entry_path, scaffold_root_path, composition_attr_id,
                       width, height, fps, duration_sec, total_frames,
                       readiness_score, status, created_at, updated_at
                FROM compositions
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (status_filter, limit, offset),
            )
            total_cursor = conn.execute(
                "SELECT COUNT(*) FROM compositions WHERE status = ?", (status_filter,)
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, title, entry_path, scaffold_root_path, composition_attr_id,
                       width, height, fps, duration_sec, total_frames,
                       readiness_score, status, created_at, updated_at
                FROM compositions
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            total_cursor = conn.execute("SELECT COUNT(*) FROM compositions")

        rows = cursor.fetchall()
        total = total_cursor.fetchone()[0]

    items = [
        CompositionSummary(
            id=row[0],
            title=row[1],
            entry_path=row[2],
            scaffold_root_path=row[3],
            composition_attr_id=row[4],
            width=row[5],
            height=row[6],
            fps=row[7],
            duration_sec=row[8],
            total_frames=row[9],
            readiness_score=row[10],
            status=row[11],
            clip_count=0,
            created_at=row[12],
            updated_at=row[13],
        )
        for row in rows
    ]

    return PaginatedCompositions(items=items, total=total, limit=limit, offset=offset)


@router.get("/{comp_id}", response_model=CompositionDetail)
async def get_composition(comp_id: str):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, entry_path, scaffold_root_path, html_source,
                   composition_attr_id, width, height, fps, duration_sec,
                   total_frames, readiness_score, status, created_at, updated_at
            FROM compositions WHERE id = ?
            """,
            (comp_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Composition not found")

        # Get clips
        clips_cursor = conn.execute(
            """
            SELECT id, composition_id, element_id, tag_name, track_index,
                   start_sec, duration_sec, label, x_offset, y_offset,
                   scale, opacity, color_grading, src_path, updated_at
            FROM clips WHERE composition_id = ?
            ORDER BY track_index, start_sec
            """,
            (comp_id,),
        )
        clips_rows = clips_cursor.fetchall()

        # Get audit events
        audit_cursor = conn.execute(
            """
            SELECT id, composition_id, action, actor, summary, details_json, created_at
            FROM audit_events WHERE composition_id = ?
            ORDER BY created_at DESC
            """,
            (comp_id,),
        )
        audit_rows = audit_cursor.fetchall()

        # Get diagnostics
        diag_cursor = conn.execute(
            "SELECT html_source FROM compositions WHERE id = ?", (comp_id,)
        )
        html_source = diag_cursor.fetchone()[0]

    clips_data = [
        {
            "id": r[0],
            "composition_id": r[1],
            "element_id": r[2],
            "tag_name": r[3],
            "track_index": r[4],
            "start_sec": r[5],
            "duration_sec": r[6],
            "label": r[7],
            "x_offset": r[8],
            "y_offset": r[9],
            "scale": r[10],
            "opacity": r[11],
            "color_grading": r[12],
            "src_path": r[13],
            "updated_at": r[14],
        }
        for r in clips_rows
    ]

    audit_data = [
        AuditEventModel(
            id=r[0],
            composition_id=r[1],
            action=r[2],
            actor=r[3],
            summary=r[4],
            details_json=r[5],
            created_at=r[6],
        )
        for r in audit_rows
    ]

    # Simple diagnostics computation
    from app.api.diagnostics import analyze_html_composition
    readiness_score, concurrency_windows, issues = analyze_html_composition(html_source)

    from app.models.schemas import CompositionDiagnostics
    diagnostics = CompositionDiagnostics(
        composition_id=comp_id,
        readiness_score=readiness_score,
        status="ready" if readiness_score >= 80 else "warning" if readiness_score >= 50 else "blocked",
        entry_path_mismatch=any(i.code == "ENTRY_PATH_MISMATCH" for i in issues),
        has_gsap_timeline=any(i.code == "NO_GSAP_TIMELINE" for i in issues) is False,
        max_concurrent_videos=max((w.active_video_count for w in concurrency_windows), default=0),
        peak_concurrency_windows=concurrency_windows,
        issues=issues,
    )

    return CompositionDetail(
        id=row[0],
        title=row[1],
        entry_path=row[2],
        scaffold_root_path=row[3],
        html_source=row[4],
        composition_attr_id=row[5],
        width=row[6],
        height=row[7],
        fps=row[8],
        duration_sec=row[9],
        total_frames=row[10],
        readiness_score=row[11],
        status=row[12],
        clip_count=len(clips_data),
        created_at=row[13],
        updated_at=row[14],
        clips=clips_data,
        diagnostics=diagnostics,
        audit_events=audit_data,
    )


@router.delete("/{comp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_composition(comp_id: str):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute("SELECT id FROM compositions WHERE id = ?", (comp_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Composition not found")

        conn.execute("DELETE FROM compositions WHERE id = ?", (comp_id,))
        conn.commit()

    return None
