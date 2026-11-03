# Security Model — Evidence Repository

## What immutability guarantees

**S3 Object Lock (COMPLIANCE mode, 30-day retention by default)**: objects cannot be overwritten or deleted by *any* principal (including root) until the retention expires. Versioning is enabled; every PUT creates a new version.
**Postgres append-only**: the evidence and chain_heads tables are write-once. The application role (evidence_app) has only SELECT, INSERT. A separate migration role (evidence_migrate) owns DDL. REVOKE UPDATE, DELETE is applied in the initial migration. See alembic/versions/0001_initial.py.
**Hash chain**: each record commits to the previous record's digest. Any change to metadata, content hash, linkage, or ordering is detectable by GET /chains/verify.

## Threat model

| Threat | Mitigated? | By |
|---|---|---|
| App-layer bug corrupts a row | ✅ | Append-only grants; hash chain verification catches any write that slips through |
| Attacker with app credentials mutates evidence | ✅ | No UPDATE/DELETE grant; hash mismatch on verify |
| Attacker deletes S3 object | ✅ | Object Lock COMPLIANCE |
| Attacker with DB **and** S3 write **and** lock bypass rewrites entire chain | ❌ | Requires out-of-band anchoring (transparency log) — out of scope v1 |
| Replay of an old presigned URL | ✅ | 60s TTL, signed per-object, per-tenant key check on URL issuance |
| Cross-tenant read | ✅ | Every query filters tenant_id at the SQL layer, not just the API |
| Stolen JWT | ⚠️ | Out of scope here; Alpha owns token TTL/rotation |

## RBAC matrix (enforced via JWT claim roles)

| Role | Upload | Read meta | Download | Verify |
|---|---|---|---|---|
| evidence_writer | ✅ | ✅ | ✅ | ✅ |
| evidence_reader | ❌ | ✅ | ✅ | ✅ |
| auditor | ❌ | ✅ | ✅ | ✅ (read-only) |

Roles are checked in auth.require_roles. Adjust to your Alpha contract.

## Secrets

No secrets in git. .env.example has placeholders. Production reads from Vault/SSM.
S3 credentials in local dev come from LocalStack defaults — never use in prod.

## Presigned URL TTL

60 seconds. Rationale: long enough for a browser to follow the redirect, short enough that
a leaked URL in a log has negligible blast radius. The URL is generated only after the
caller passes RBAC + tenant check.

## Known limitations

Chain head is stored in the DB; if the DB is fully restored from a snapshot taken before a tamper event, verification passes. Mitigation: out-of-band anchoring (roadmap).
Single chain per tenant (not per workspace). Simplify v1; document as such in DECISIONS.
