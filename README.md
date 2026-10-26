# Atlas Forge — alan-vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


Deterministic HTML/Timeline Composition Engine & Visual Studio

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
export ATLAS_FORGE_DB_PATH=atlas_forge.db
python -m app.main

# Run tests
cd backend
export ATLAS_FORGE_DB_PATH=test_atlas_forge.db
python -m pytest tests/ -v
```

## API Endpoints

- `GET /health` — Health check
- `POST /api/v1/compositions` — Create composition
- `GET /api/v1/compositions` — List compositions (pagination, status filter)
- `GET /api/v1/compositions/{id}` — Get composition with clips, diagnostics, audit log
- `DELETE /api/v1/compositions/{id}` — Delete composition
- `POST /api/v1/clips` — Create clip
- `GET /api/v1/clips?composition_id={id}` — List clips
- `PATCH /api/v1/clips/{id}` — Override clip properties
- `DELETE /api/v1/clips/{id}` — Delete clip
- `GET /api/v1/diagnostics/{id}` — Get composition diagnostics

## Features

- **Compositions**: Store HTML video compositions with timeline metadata in SQLite
- **Clips**: Track-level video elements with transform properties (position, scale, opacity)
- **Diagnostics**: Static analysis of HTML for concurrency, GSAP timeline detection, readiness scoring
- **Audit Log**: Transactional audit trail for all mutations
- **Tests**: 10 passing tests with isolated test database

Maintainer: Alan Vo <alanvo@gmail.com>
