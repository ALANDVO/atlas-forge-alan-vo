"""Diagnostics API endpoints."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_connection, get_settings
from app.models.schemas import (
    CompositionDiagnostics,
    ConcurrencyWindow,
    DiagnosticIssue,
)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def analyze_html_composition(html_source: str) -> tuple[int, list[ConcurrencyWindow], list[DiagnosticIssue]]:
    """Static analysis of HTML composition for timeline diagnostics."""
    issues: list[DiagnosticIssue] = []
    concurrency_windows: list[ConcurrencyWindow] = []

    # Check for GSAP timeline
    has_gsap_timeline = "gsap" in html_source.lower() or "timeline" in html_source.lower()

    # Extract video elements and their timing
    video_pattern = r'<video[^>]*>'
    video_matches = list(re.finditer(video_pattern, html_source, re.IGNORECASE))

    # Simple frame-based concurrency analysis (30 fps assumption)
    fps = 30
    max_concurrent = 0
    active_intervals: list[tuple[float, float, str]] = []

    for match in video_matches:
        video_tag = match.group(0)
        element_id_match = re.search(r'id=["\']([^"\']+)["\']', video_tag)
        element_id = element_id_match.group(1) if element_id_match else f"video_{match.start()}"

        # Check for data attributes for timing
        start_match = re.search(r'data-start=["\']([^"\']+)["\']', video_tag)
        duration_match = re.search(r'data-duration=["\']([^"\']+)["\']', video_tag)

        start_sec = float(start_match.group(1)) if start_match else 0.0
        duration_sec = float(duration_match.group(1)) if duration_match else 10.0

        start_frame = int(start_sec * fps)
        end_frame = int((start_sec + duration_sec) * fps)

        active_intervals.append((start_sec, start_sec + duration_sec, element_id))

    # Compute concurrency windows
    if active_intervals:
        # Create timeline events
        events: list[tuple[float, int, str]] = []
        for start, end, eid in active_intervals:
            events.append((start, 1, eid))
            events.append((end, -1, eid))

        events.sort(key=lambda x: (x[0], -x[1]))

        current_count = 0
        current_clips: list[str] = []
        window_start_frame = 0

        for time, delta, eid in events:
            frame = int(time * fps)

            if delta == 1:
                if current_count == 0:
                    window_start_frame = frame
                current_count += 1
                current_clips.append(eid)
                max_concurrent = max(max_concurrent, current_count)
            else:
                if current_count > 0:
                    concurrency_windows.append(ConcurrencyWindow(
                        start_frame=window_start_frame,
                        end_frame=frame,
                        active_video_count=current_count,
                        active_clip_ids=current_clips.copy(),
                        docker_stall_risk=current_count > 2,
                    ))
                current_count = max(0, current_count - 1)
                if eid in current_clips:
                    current_clips.remove(eid)

    # Check for entry path mismatch indicators
    entry_path_mismatch = "entry" not in html_source.lower() and "index.html" not in html_source.lower()

    # Add diagnostic issues based on findings
    if max_concurrent > 3:
        issues.append(DiagnosticIssue(
            code="HIGH_CONCURRENCY",
            severity="warning",
            element_id=None,
            message=f"Maximum concurrent videos: {max_concurrent}. May cause render stalls.",
            remediation="Stagger video start times or reduce simultaneous video tracks."
        ))

    if not has_gsap_timeline:
        issues.append(DiagnosticIssue(
            code="NO_GSAP_TIMELINE",
            severity="info",
            element_id=None,
            message="No GSAP timeline detected. Timeline synchronization may be imprecise.",
            remediation="Add GSAP timeline for deterministic frame-accurate control."
        ))

    if entry_path_mismatch:
        issues.append(DiagnosticIssue(
            code="ENTRY_PATH_MISMATCH",
            severity="warning",
            element_id=None,
            message="Entry path reference not found in HTML source.",
            remediation="Ensure composition entry path matches the HTML entry point."
        ))

    # Calculate readiness score
    score = 100
    for issue in issues:
        if issue.severity == "error":
            score -= 25
        elif issue.severity == "warning":
            score -= 10
        elif issue.severity == "info":
            score -= 5
    score = max(0, score)

    status: Literal["ready", "warning", "blocked"] = "ready"
    if any(i.severity == "error" for i in issues):
        status = "blocked"
    elif any(i.severity == "warning" for i in issues):
        status = "warning"

    return score, concurrency_windows, issues


@router.get("/{comp_id}", response_model=CompositionDiagnostics)
async def get_diagnostics(comp_id: str):
    settings = get_settings()

    with get_connection(settings.db_path) as conn:
        cursor = conn.execute(
            "SELECT html_source, width, height, fps, duration_sec, total_frames FROM compositions WHERE id = ?",
            (comp_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Composition not found")

        html_source = row[0]
        width = row[1]
        height = row[2]
        fps = row[3]
        duration_sec = row[4]
        total_frames = row[5]

    readiness_score, concurrency_windows, issues = analyze_html_composition(html_source)

    return CompositionDiagnostics(
        composition_id=comp_id,
        readiness_score=readiness_score,
        status="ready" if readiness_score >= 80 else "warning" if readiness_score >= 50 else "blocked",
        entry_path_mismatch=any(i.code == "ENTRY_PATH_MISMATCH" for i in issues),
        has_gsap_timeline=any(i.code == "NO_GSAP_TIMELINE" for i in issues) is False,
        max_concurrent_videos=max((w.active_video_count for w in concurrency_windows), default=0),
        peak_concurrency_windows=concurrency_windows,
        issues=issues,
    )
