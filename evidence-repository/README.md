# Evidence Repository (Pod Gamma · Service 6)

Immutable, hash-chained evidence storage for the AEV Platform CTEM lifecycle.

Implements **FR-EVID-001/002/003** from the Pod Gamma Build Guide:
- **Storage:** S3 Object Lock (COMPLIANCE) + append-only Postgres + per-tenant hash chain.
- **Upload:** multipart upload, SHA-256 content hash, chain-linked, exposure/workflow linked.
- **Verification:** per-record and full-chain verification, tamper alerts via Kafka.

## Prereqs
- Docker + Docker Compose v2
- (for local dev without Docker) Python 3.12, make

## Quick start (5 minutes)

cp .env.example .env
docker compose up -d --build       # starts postgres, localstack, redpanda, api
docker compose exec api alembic upgrade head
docker compose exec api pytest -q  # run test suite inside container

# smoke test
TOKEN=$(docker compose exec -T api python -c "from evidence_repo.auth import mint_dev_token; print(mint_dev_token('11111111-1111-1111-1111-111111111111','22222222-2222-2222-2222-222222222222'))")

# upload
echo "hello evidence" > /tmp/ev.txt
curl -s -X POST http://localhost:8000/evidence \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/ev.txt" \
  -F "content_type=text/plain" \
  -F "metadata={\"source\":\"smoke\"}" | tee /tmp/up.json

EID=$(python -c "import json;print(json.load(open('/tmp/up.json'))['evidence_id'])")

# fetch metadata + verify
curl -s http://localhost:8000/evidence/$EID -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s http://localhost:8000/evidence/$EID/verify -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s http://localhost:8000/chains/verify -H "Authorization: Bearer $TOKEN" | python -m json.tool

# download (presigned URL)
curl -s http://localhost:8000/evidence/$EID/download -H "Authorization: Bearer $TOKEN" | python -m json.tool

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /evidence | Upload evidence (multipart: file, exposure_id?, workflow_execution_id?, content_type?, metadata?, Idempotency-Key header) |
| GET | /evidence/{id} | Fetch metadata |
| GET | /evidence/{id}/download | Presigned download URL (60s TTL) |
| GET | /evidence/{id}/verify | Verify single record against chain + S3 |
| GET | /evidence?exposure_id=…&workflow_execution_id=… | List, paginated |
| GET | /chains/verify | Verify entire tenant chain |
| GET | /healthz, /readyz | Liveness / readiness |

All endpoints require Authorization: Bearer <JWT>.

## Commands

make up         # docker compose up -d --build
make migrate    # alembic upgrade head (inside container)
make test       # pytest with coverage
make lint       # ruff + mypy
make verify     # run full-chain verification against running stack
make down       # docker compose down -v

## How to verify my claims

| Claim | Proof |
|---|---|
| FR-EVID-001 immutable storage | tests/test_upload.py::test_s3_object_lock_retention, bucket policy in docker/localstack-init/01-create-bucket.sh |
| FR-EVID-002 upload + hash + linkage | tests/test_upload.py (upload happy path, exposure/workflow refs) |
| FR-EVID-003 verify + tamper alert | tests/test_verify.py::test_db_tamper_detected, ::test_s3_tamper_detected |
| No chain forks under concurrency | tests/test_concurrency.py::test_concurrent_appends_no_fork |
| Idempotent re-upload | tests/test_upload.py::test_idempotent_upload |
| Tenant isolation | tests/test_tenant_isolation.py |
| End-to-end against LocalStack | tests/test_integration.py |
