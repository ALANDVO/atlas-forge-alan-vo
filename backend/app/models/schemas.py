"""Pydantic models for HTML video compositions, timeline clips, diagnostics, and overrides."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class ClipModel(BaseModel):
    id: str
    composition_id: str
    element_id: str
    tag_name: str
    track_index: int
    start_sec: float
    duration_sec: float
    label: str
    x_offset: float = 0.0
    y_offset: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0
    color_grading: str = ""
    src_path: str = ""
    updated_at: str


class DiagnosticIssue(BaseModel):
    code: str
    severity: Literal["error", "warning", "info"]
    element_id: str | None = None
    message: str
    remediation: str


class ConcurrencyWindow(BaseModel):
    start_frame: int
    end_frame: int
    active_video_count: int
    active_clip_ids: list[str]
    docker_stall_risk: bool


class CompositionDiagnostics(BaseModel):
    composition_id: str
    readiness_score: int
    status: Literal["ready", "warning", "blocked"]
    entry_path_mismatch: bool
    has_gsap_timeline: bool
    max_concurrent_videos: int
    peak_concurrency_windows: list[ConcurrencyWindow]
    issues: list[DiagnosticIssue]


class CompositionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    entry_path: str = Field(default="index.html", min_length=1, max_length=240)
    scaffold_root_path: str = Field(default="index.html", min_length=1, max_length=240)
    html_source: str = Field(..., min_length=16)

    @field_validator("title", "entry_path", "scaffold_root_path")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field must not be blank")
        return cleaned


class ClipOverrideRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    start_sec: float | None = Field(default=None, ge=0.0, le=3600.0)
    duration_sec: float | None = Field(default=None, gt=0.0, le=3600.0)
    track_index: int | None = Field(default=None, ge=0, le=64)
    x_offset: float | None = Field(default=None, ge=-10000.0, le=10000.0)
    y_offset: float | None = Field(default=None, ge=-10000.0, le=10000.0)
    scale: float | None = Field(default=None, gt=0.05, le=20.0)
    opacity: float | None = Field(default=None, ge=0.0, le=1.0)


class AuditEventModel(BaseModel):
    id: int
    composition_id: str
    action: str
    actor: str
    summary: str
    details: dict[str, Any]
    created_at: str


class CompositionSummary(BaseModel):
    id: str
    title: str
    entry_path: str
    scaffold_root_path: str
    composition_attr_id: str
    width: int
    height: int
    fps: int
    duration_sec: float
    total_frames: int
    readiness_score: int
    status: Literal["ready", "warning", "blocked"]
    clip_count: int
    created_at: str
    updated_at: str


class CompositionDetail(CompositionSummary):
    html_source: str
    clips: list[ClipModel]
    diagnostics: CompositionDiagnostics
    audit_events: list[AuditEventModel]


class PaginatedCompositions(BaseModel):
    items: list[CompositionSummary]
    total: int
    limit: int
    offset: int
