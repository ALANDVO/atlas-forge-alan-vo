# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

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
