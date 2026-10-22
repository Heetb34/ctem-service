# Engineering Decisions (ADR-lite)

## D1. One hash chain per tenant (not per workspace)
The spec says "hash-chained" without scope. Per-tenant is the smallest unit that
still lets one tenant prove integrity without leaking another tenant's ordering.
Alternative (per-workspace) rejected: makes cross-workspace remediation reports
require walking N chains. Alternative (global) rejected: tenant isolation.

## D2. COMPLIANCE mode over GOVERNANCE
GOVERNANCE allows privileged users to remove the lock. COMPLIANCE does not — not even
root. For an evidence repository used in audits, COMPLIANCE is the correct default.
Retention default 30 days; configurable via S3_RETENTION_DAYS. Production should
set this to your audit retention (typically 1–7 years).

## D3. SHA-256 over SHA-3/BLAKE3
Universal, fast enough (S3 egress dominates), and every language/librarian supports it.
BLAKE3 would be faster but adds a dependency and interoperability risk.

## D4. Canonical JSON serialization
sort_keys=True, separators=(",", ":"), ensure_ascii=True. This is the smallest
well-defined subset that's identical across Python/Go/JS. Floating point is excluded
from metadata (validated in schema: only str/int/bool/null/nested dict/list).

## D5. aiokafka over confluent-kafka
Async-native, pure-Python dependency for our async FastAPI stack; confluent-kafka
requires librdkafka and its own thread/event-loop bridge. Perf is not the bottleneck
here (evidence uploads are low-QPS).

## D6. LocalStack for S3 Object Lock in tests
Real AWS costs money and needs network; LocalStack free tier supports Object Lock
with OBJECT_LOCK_ENABLED (see docker-compose.yml). Tested against LocalStack; the
code path is identical to real S3 (boto3).
