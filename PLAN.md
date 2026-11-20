# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

core-composition-studio

## Roadmap

### core-composition-studio — Deterministic HTML/Timeline Composition Engine & Visual Studio

Status: done

Acceptance:
- Create, import, filter, paginate, and inspect HTML/timeline video compositions stored in SQLite with transactional audit logs
- Deterministic DOM/timeline static analyzer and frame-step simulation engine computing track bounds, concurrency overlaps, bit-depth quantization diagnostics, and export readiness
- React + TypeScript studio UI with live composition creation, timeline diagnostics, in-place element property overrides, and JSON/manifest export

Implementation: `backend/app/main.py`, `backend/app/api/compositions.py`, `backend/app/api/clips.py`, `backend/app/api/diagnostics.py`, `backend/app/api/health.py`, `backend/app/core/database.py`, `backend/app/models/schemas.py`

Tests: `backend/tests/test_compositions.py`, `backend/tests/test_clips.py`

### gpu-capture-diagnostics — WSL2 / Multi-Worker Capture & ProRes 10-bit Precision Analyzer

Status: in_progress

Acceptance:
- Analyze render environment profiles (WSL2 /dev/dri/renderD128 permissions, Windows multi-worker segmented capture connection contention, Docker dual-video stalls)
- Evaluate 8-bit capture quantization vs 10-bit ProRes 4444 container levels, computing gradient fill ratios, flat-run contour lengths, and deband/supersample recommendations

Implementation: `backend/app/api/diagnostics.py: GPU environment detection (detect_render_environment),`, `8-bit/10-bit quantization analysis (analyze_quantization),`, `Docker multi-worker capture contention assessment (assess_docker_capture_contention)`

Tests: `Verified detect_render_environment() returns render DRI info, WSL2 detection, GPU vendor`, `Verified analyze_quantization(BitDepth.BIT_8) vs analyze_quantization(BitDepth.BIT_10) produces correct`, `          error rates, gradient fill ratios, deband/supersample recommendations`, `Verified assess_docker_capture_contention() correctly assesses risk levels and worker limits`

### agent-scene-refinement-eval — Agentic Scene Refinement & Reproducible ML Evaluation Benchmark

Status: planned

Acceptance:
- Deterministic benchmark dataset of agent-authored HTML video scenes with labeled timeline, layout, and capture hazards
- Reproducible CLI/API evaluation scoring precision, recall, and frame-time compliance across baseline and heuristic/LLM-assisted scene repair
- Opt-in server-side LLM advisory adapter supporting OpenAI-compatible, Anthropic, Gemini, and Ollama providers via LLM_API_KEY

### oidc-keycloak-auth — OIDC PKCE Authentication & Role-Based Access Control

Status: planned

Acceptance:
- Keycloak OIDC authorization-code + PKCE + state/nonce flow with viewer, analyst, and admin role enforcement
- Explicit localhost-only demo mode guard that refuses startup in production environments

---

Alan Vo · [alanvo.net](https://alanvo.net) · [X: @alanvoasi](https://x.com/alanvoasi)
