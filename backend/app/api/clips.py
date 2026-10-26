"""Clips API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.core.database import get_connection, get_settings
from app.models.schemas import ClipModel, ClipOverrideRequest, ClipOverrideResponse

router = APIRouter(prefix="/clips", tags=["clips"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("", response_model=list[ClipModel])
async def list_clips(
    composition_id: str = Query(...),
    track_index: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        if track_index is not None:
            cursor = conn.execute(
                """
                SELECT id, composition_id, element_id, tag_name, track_index,
                       start_sec, duration_sec, label, x_offset, y_offset,
                       scale, opacity, color_grading, src_path, updated_at
                FROM clips
                WHERE composition_id = ? AND track_index = ?
                ORDER BY start_sec
                LIMIT ? OFFSET ?
                """,
                (composition_id, track_index, limit, offset),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, composition_id, element_id, tag_name, track_index,
                       start_sec, duration_sec, label, x_offset, y_offset,
                       scale, opacity, color_grading, src_path, updated_at
                FROM clips
                WHERE composition_id = ?
                ORDER BY track_index, start_sec
                LIMIT ? OFFSET ?
                """,
                (composition_id, limit, offset),
            )
        rows = cursor.fetchall()

    return [
        ClipModel(
            id=row[0],
            composition_id=row[1],
            element_id=row[2],
            tag_name=row[3],
            track_index=row[4],
            start_sec=row[5],
            duration_sec=row[6],
            label=row[7],
            x_offset=row[8],
            y_offset=row[9],
            scale=row[10],
            opacity=row[11],
            color_grading=row[12],
            src_path=row[13],
            updated_at=row[14],
        )
        for row in rows
    ]


@router.post("", response_model=ClipModel, status_code=status.HTTP_201_CREATED)
async def create_clip(clip: ClipModel):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        # Verify composition exists
        comp_cursor = conn.execute(
            "SELECT id FROM compositions WHERE id = ?", (clip.composition_id,)
        )
        if not comp_cursor.fetchone():
            raise HTTPException(status_code=404, detail="Composition not found")

        conn.execute(
            """
            INSERT INTO clips (
                id, composition_id, element_id, tag_name, track_index,
                start_sec, duration_sec, label, x_offset, y_offset,
                scale, opacity, color_grading, src_path, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clip.id,
                clip.composition_id,
                clip.element_id,
                clip.tag_name,
                clip.track_index,
                clip.start_sec,
                clip.duration_sec,
                clip.label,
                clip.x_offset,
                clip.y_offset,
                clip.scale,
                clip.opacity,
                clip.color_grading,
                clip.src_path,
                _now(),
            ),
        )
        conn.commit()

    return clip


@router.patch("/{clip_id}", response_model=ClipOverrideResponse)
async def override_clip(clip_id: str, override: ClipOverrideRequest):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Clip not found")

        # Build update query dynamically based on provided fields
        updates = []
        params = []
        if override.label is not None:
            updates.append("label = ?")
            params.append(override.label)
        if override.x_offset is not None:
            updates.append("x_offset = ?")
            params.append(override.x_offset)
        if override.y_offset is not None:
            updates.append("y_offset = ?")
            params.append(override.y_offset)
        if override.scale is not None:
            updates.append("scale = ?")
            params.append(override.scale)
        if override.opacity is not None:
            updates.append("opacity = ?")
            params.append(override.opacity)

        if not updates:
            raise HTTPException(status_code=400, detail="No valid override fields provided")

        updates.append("updated_at = ?")
        params.append(_now())
        params.append(clip_id)

        query = f"UPDATE clips SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()

        # Fetch updated clip
        cursor = conn.execute(
            """
            SELECT id, composition_id, element_id, tag_name, track_index,
                   start_sec, duration_sec, label, x_offset, y_offset,
                   scale, opacity, color_grading, src_path, updated_at
            FROM clips WHERE id = ?
            """,
            (clip_id,),
        )
        updated_row = cursor.fetchone()

        # Add audit event
        conn.execute(
            """
            INSERT INTO audit_events (composition_id, action, actor, summary, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                updated_row[1],
                "override",
                "user",
                f"Overrode clip {clip_id} properties",
                str(override.model_dump(exclude_none=True)),
                _now(),
            ),
        )
        conn.commit()

    return ClipOverrideResponse(
        clip=ClipModel(
            id=updated_row[0],
            composition_id=updated_row[1],
            element_id=updated_row[2],
            tag_name=updated_row[3],
            track_index=updated_row[4],
            start_sec=updated_row[5],
            duration_sec=updated_row[6],
            label=updated_row[7],
            x_offset=updated_row[8],
            y_offset=updated_row[9],
            scale=updated_row[10],
            opacity=updated_row[11],
            color_grading=updated_row[12],
            src_path=updated_row[13],
            updated_at=updated_row[14],
        ),
        applied_fields=list(override.model_dump(exclude_none=True).keys()),
    )


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clip(clip_id: str):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute("SELECT id FROM clips WHERE id = ?", (clip_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Clip not found")

        conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
        conn.commit()

    return None
