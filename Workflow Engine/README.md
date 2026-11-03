# Workflow Service – Pod Gamma

Automation backbone for AEV Platform. Executes multi‑step workflows with retry, rollback, approvals, and event triggers.

## Quick Start
```bash
# Clone and set up
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start dependencies
docker-compose up -d

# Run migrations (auto on startup)
uvicorn src.main:app --reload

# Run tests
pytest
```

## API Endpoints
- `POST /workflows` – create workflow
- `GET /workflows/{id}` – get definition
- `PATCH /workflows/{id}` – new version
- `POST /executions/workflows/{id}/execute` – trigger
- `GET /executions/{id}` – execution status
- `POST /approvals/{id}/decide` – approve/reject

See full OpenAPI docs at `/docs`.
