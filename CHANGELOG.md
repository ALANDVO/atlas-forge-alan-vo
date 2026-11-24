# Changelog

## 1.7.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.6.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.5.1 — work-in-progress checkpoint

### Added (this round)
- GPU capture diagnostics module in `backend/app/api/diagnostics.py`:
  - `detect_render_environment()`: WSL2 /dev/dri/renderD128 permission detection, GPU vendor identification, WSL2 distro detection, Docker container awareness
  - `analyze_quantization()`: 8-bit vs 10-bit ProRes 4444 quantization error analysis, gradient fill ratios, flat-run contour length computation, debanding and supersampling recommendations
  - `assess_docker_capture_contention()`: Multi-worker capture connection contention risk assessment with recommended worker count limits

### Fixed
- None (new feature implementation)

Known issues: STATUS.md.

## 1.5.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed (this round)
- Concurrency window computation in diagnostics engine now correctly tracks active clip count changes across timeline events, producing accurate per-frame concurrency windows for overlapping, nested, and sequential video elements

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Added (this round)
- Persisted diagnostics storage in `composition_diagnostics` table
- Diagnostics endpoint now stores results (readiness_score, issues, concurrency_windows, has_gsap_timeline)
- Composition `readiness_score` updated on diagnostics computation
- `diagnostics_computed` audit event for traceability

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

### Fixed
- Diagnostics engine now uses composition's actual FPS instead of hardcoded 30 fps
- Fixed `has_gsap_timeline` boolean logic in diagnostics response (was inverted)
- `NO_GSAP_TIMELINE` info issue now correctly generated when GSAP/timeline absent
- `get_composition` endpoint updated to pass FPS and consume fixed analyzer return values

## [0.1.0] - 2026-10-26

### Added
- FastAPI backend with health check endpoint
- SQLite persistence layer (compositions, clips, audit_events)
- Pydantic models for Composition, Clip, Diagnostics, AuditEvent
- Compositions API: CRUD + pagination + status filtering
- Clips API: CRUD + filtering + property overrides
- Diagnostics API: Static HTML analysis with concurrency detection
- Transactional audit logging
- 10 passing integration tests
- Demo mode guard (refuses startup in production with demo_mode=true)

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
