"""Diagnostics API endpoints."""

from __future__ import annotations
import os

import json
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Literal

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_connection, get_settings
from app.models.schemas import (
    CompositionDiagnostics,
    ConcurrencyWindow,
    DiagnosticIssue,
)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


class BitDepth(str, Enum):
    """Supported bit depths for capture/quantization analysis."""

    BIT_8 = "8-bit"
    BIT_10 = "10-bit"


class RenderVendor(str, Enum):
    """GPU vendor identifiers."""

    INTEL = "intel"
    NVIDIA = "nvidia"
    AMD = "amd"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def analyze_html_composition(html_source: str, fps: int = 30) -> tuple[int, list[ConcurrencyWindow], list[DiagnosticIssue], bool]:
    """Static analysis of HTML composition for timeline diagnostics.
    Returns (readiness_score, concurrency_windows, issues, has_gsap_timeline)
    """
    issues: list[DiagnosticIssue] = []
    concurrency_windows: list[ConcurrencyWindow] = []

    # Check for GSAP timeline
    has_gsap_timeline = "gsap" in html_source.lower() or "timeline" in html_source.lower()

    # Extract video elements and their timing
    video_pattern = r'<video[^>]*>'
    video_matches = list(re.finditer(video_pattern, html_source, re.IGNORECASE))

    # Frame-based concurrency analysis using provided fps
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
        prev_time = 0.0

        for time, delta, eid in events:
            frame = int(time * fps)

            # When count changes, close previous window and start new one
            if current_count > 0 and time > prev_time:
                concurrency_windows.append(ConcurrencyWindow(
                    start_frame=window_start_frame,
                    end_frame=frame,
                    active_video_count=current_count,
                    active_clip_ids=current_clips.copy(),
                    docker_stall_risk=current_count > 2,
                ))
                window_start_frame = frame

            if delta == 1:
                current_count += 1
                current_clips.append(eid)
                max_concurrent = max(max_concurrent, current_count)
            else:
                current_count = max(0, current_count - 1)
                if eid in current_clips:
                    current_clips.remove(eid)

            prev_time = time

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

    return score, concurrency_windows, issues, has_gsap_timeline


def detect_render_environment() -> dict:
    """Detect render environment profile from /dev/dri, sysfs, and WSL2 indicators.

    Returns render environment info for WSL2 /dev/dri/renderD128 permissions
    and GPU vendor detection.
    """
    result: dict = {
        "has_render_dri": False,
        "render_dri_devices": [],
        "render_dri128_access": "unknown",
        "is_wsl2": False,
        "wsl2_distro": "",
        "gpu_vendor": RenderVendor.UNKNOWN,
        "driver_version": "",
        "docker_containers": [],
    }

    dri_dir = "/dev/dri"
    if os.path.exists(dri_dir):
        result["has_render_dri"] = True
        try:
            for entry in os.listdir(dri_dir):
                result["render_dri_devices"].append(entry)
        except Exception:
            pass

        # Check renderD128 specifically
        if "renderD128" in result["render_dri_devices"]:
            # Try to get GPU vendor info
            try:
                with open("/proc/driver/gpu/drm/card0/name", "r") as f:
                    name = f.read().strip().lower()
                    if "intel" in name:
                        result["gpu_vendor"] = RenderVendor.INTEL
                    elif "nvidia" in name or "geforce" in name:
                        result["gpu_vendor"] = RenderVendor.NVIDIA
                    elif "amd" in name or "radeon" in name:
                        result["gpu_vendor"] = RenderVendor.AMD
            except Exception:
                result["gpu_vendor"] = RenderVendor.VIRTUAL

            # Check for WSL2 indicators
            try:
                with open("/proc/version", "r") as f:
                    version_text = f.read().lower()
                    if "microsoft" in version_text or "wsl" in version_text:
                        result["is_wsl2"] = True
                        # Try to find distro name
                        try:
                            with open("/etc/os-release", "r") as f:
                                for line in f:
                                    if line.startswith("PRETTY_NAME="):
                                        result["wsl2_distro"] = line.split("=")[1].strip('"')
                                        break
                        except Exception:
                            pass
            except Exception:
                pass

            # Set access level
            result["render_dri128_access"] = "read-write"
        elif os.path.exists("/dev/dri/card0"):
            result["render_dri128_access"] = "read"

    # Check Docker containers
    try:
        with open("/proc/1/cgroup", "r") as f:
            cgroup_content = f.read()
            if "docker" in cgroup_content.lower():
                result["docker_containers"].append("main-process")
    except Exception:
        pass

    return result


def analyze_quantization(
    bit_depth: BitDepth,
    gradient_samples: Optional[list[float]] = None,
) -> dict:
    """Analyze 8-bit vs 10-bit ProRes 4444 quantization.

    Evaluates:
    - Quantization error vs ideal continuous values
    - Gradient fill ratios (proportion of gradient steps affected)
    - Flat-run contour lengths (consecutive flat pixels)
    - Debanding/supersample recommendations
    - ProRes 4444 compatibility

    Returns dict with analysis results.
    """
    if bit_depth == BitDepth.BIT_8:
        quantization_error = 1.0 / 255.0
        gradient_fill_ratio = 1.0
        flat_run_contour_length = 0
        deband_recommended = True
        supersample_recommended = True
        prores_4444_compatible = False
    else:  # BIT_10
        quantization_error = 1.0 / 1023.0
        gradient_fill_ratio = 0.0
        flat_run_contour_length = 0
        deband_recommended = False
        supersample_recommended = False
        prores_4444_compatible = True

    # If we have gradient samples, compute detailed analysis
    if gradient_samples is not None and len(gradient_samples) > 0:
        errors = []
        for sample in gradient_samples:
            if bit_depth == BitDepth.BIT_8:
                quantized = round(sample * 255.0) / 255.0
            else:
                quantized = round(sample * 1023.0) / 1023.0
            errors.append(abs(sample - quantized))

        # Gradient fill ratio: proportion of samples with error > threshold
        threshold = 0.5 / (255.0 if bit_depth == BitDepth.BIT_8 else 1023.0)
        errors_above_threshold = sum(1 for e in errors if e > threshold)
        gradient_fill_ratio = errors_above_threshold / len(errors)

        # Flat-run contour length
        if len(gradient_samples) > 1:
            quantized_values = []
            for sample in gradient_samples:
                if bit_depth == BitDepth.BIT_8:
                    qv = round(sample * 255.0) / 255.0
                else:
                    qv = round(sample * 1023.0) / 1023.0
                quantized_values.append(qv)

            longest_run = 1
            current_run = 1
            for i in range(1, len(quantized_values)):
                if quantized_values[i] == quantized_values[i - 1]:
                    current_run += 1
                    longest_run = max(longest_run, current_run)
                else:
                    current_run = 1

            flat_run_contour_length = longest_run

        # Debanding recommendation
        if flat_run_contour_length > 3:
            deband_recommended = bit_depth == BitDepth.BIT_8
            if bit_depth == BitDepth.BIT_10 and flat_run_contour_length > 10:
                deband_recommended = True

        # Supersample recommendation
        if gradient_fill_ratio > 0.1:
            supersample_recommended = bit_depth == BitDepth.BIT_8
            if bit_depth == BitDepth.BIT_10 and gradient_fill_ratio > 0.3:
                supersample_recommended = True
    else:
        flat_run_contour_length = 0

    return {
        "bit_depth": bit_depth,
        "quantization_error": quantization_error,
        "gradient_fill_ratio": gradient_fill_ratio,
        "flat_run_contour_length": flat_run_contour_length,
        "deband_recommended": deband_recommended,
        "supersample_recommended": supersample_recommended,
        "prores_4444_compatible": prores_4444_compatible,
    }


def assess_docker_capture_contention(
    container_count: int, has_dual_video: bool = False
) -> dict:
    """Assess Docker multi-worker capture connection contention.

    Evaluates:
    - Number of concurrent capture workers
    - Dual-video stall risk
    - Recommended worker count limits
    """
    risk_level = "low"
    max_recommended = 4

    if container_count >= 4:
        risk_level = "high"
        max_recommended = 2
    elif container_count >= 2:
        risk_level = "medium"
        max_recommended = 3

    if has_dual_video:
        # Upgrade risk to high when dual-video stall risk is present
        # Using numeric comparison to avoid lexicographic string comparison bugs
        # ("medium" > "high" lexicographically since 'm' > 'h', so max() would be incorrect)
        if risk_level != "high":
            risk_level = "high"
        max_recommended = min(max_recommended, 2)

    return {
        "container_count": container_count,
        "risk_level": risk_level,
        "max_recommended_workers": max_recommended,
        "dual_video_stall_risk": has_dual_video,
        "recommendation": (
            f"Limit to {max_recommended} concurrent capture workers"
            if risk_level != "low"
            else "No significant contention detected"
        ),
    }


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

    readiness_score, concurrency_windows, issues, has_gsap_timeline = analyze_html_composition(html_source, fps)

    # Persist diagnostics results
    issues_json = json.dumps([issue.model_dump() for issue in issues])
    concurrency_windows_json = json.dumps([window.model_dump() for window in concurrency_windows])

    with get_connection(settings.db_path) as conn:
        # Store diagnostics
        conn.execute(
            """INSERT OR REPLACE INTO composition_diagnostics 
               (composition_id, readiness_score, issues_json, concurrency_windows_json, has_gsap_timeline, computed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (comp_id, readiness_score, issues_json, concurrency_windows_json, 1 if has_gsap_timeline else 0, _now()),
        )
        # Update composition readiness_score
        conn.execute(
            "UPDATE compositions SET readiness_score = ?, updated_at = ? WHERE id = ?",
            (readiness_score, _now(), comp_id),
        )
        # Add audit event
        conn.execute(
            """INSERT INTO audit_events (composition_id, action, actor, summary, details_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (comp_id, "diagnostics_computed", "system", "Computed composition diagnostics",
             json.dumps({"readiness_score": readiness_score, "issue_count": len(issues), "has_gsap_timeline": has_gsap_timeline}), _now()),
        )
        conn.commit()

    return CompositionDiagnostics(
        composition_id=comp_id,
        readiness_score=readiness_score,
        status="ready" if readiness_score >= 80 else "warning" if readiness_score >= 50 else "blocked",
        entry_path_mismatch=any(i.code == "ENTRY_PATH_MISMATCH" for i in issues),
        has_gsap_timeline=has_gsap_timeline,
        max_concurrent_videos=max((w.active_video_count for w in concurrency_windows), default=0),
        peak_concurrency_windows=concurrency_windows,
        issues=issues,
    )
