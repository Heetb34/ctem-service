# Local integrated system

The repository root `docker-compose.yml` is the canonical local stack. It starts
CTEM, Workflow, Notification API, in-app/retry/DLQ workers, Kafka, MySQL, PostgreSQL,
Redis, Kafka UI, and Mailpit. Kafka topics for all notification channels, retry,
and dead-letter delivery are initialized on startup. MySQL is published on host port 3307, PostgreSQL
on 5433, Redis on 6380, and Mailpit on 1026/8026 to avoid the earlier local
MySQL and Mailpit containers. Mailpit stores its mailbox in a named volume.

## Start and inspect

From the repository root:

```powershell
docker compose config
docker compose up --build -d
docker compose ps
```

Open CTEM at `http://localhost:8000/docs`, Workflow at
`http://localhost:8001/docs`, Notification at `http://localhost:3000/health`,
Kafka UI at `http://localhost:8080`, and Mailpit at `http://localhost:8026`.
The containers use their internal service ports; the alternate ports above are
only for host access.

## CTEM to Workflow to Notification

Create a Workflow through `POST /workflows` with a tenant UUID and an event
trigger. For example, use this `triggers` value:

```json
[{"type":"event","event":"ExposureDetected","filter":"severity == 'critical'"}]
```

Set its definition to include one action step:

```json
{"steps":[{"id":"notify","name":"Notify owner","type":"action","action":"send_notification","input":{"channel":"in-app","recipient":"local-test-user","template":"security-alert"}}],"connections":[]}
```

Then create an exposure using the same `tenant_id` at
`POST /ctem/cycles/1/exposures`. Include `user_id` if the action should use the
trigger's user as its recipient; a recipient in the step input takes priority.
The exposure and its outbox event are saved in one database transaction. CTEM
publishes outbox events to Kafka with retries; Workflow consumes only active
workflows for the same tenant, applies the event filter, and starts an
idempotent execution. The Notification API publishes the in-app notification
and the worker records its delivery status. Check `GET /notifications` or
`GET /notifications/inapp/local-test-user` for the result.

## Email report check

The stack routes report email to Mailpit (`mailpit:1025`, no TLS). Open
`http://localhost:8026` to inspect messages. The named volume preserves the
inbox across container restarts. This verifies SMTP delivery to the local test
mail server, not delivery through Gmail.

For Gmail delivery, configure the ignored root `.env` with a Gmail App Password
and the account address as `SMTP_FROM` and `SMTP_USERNAME`. Keep the password
only in `.env`; do not paste it into chat or commit it. Start the Gmail-specific
configuration with:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gmail.yml up -d --force-recreate ctem-api
```

Create a one-time report schedule addressed to the `SMTP_FROM` mailbox. After
the check, return the CTEM API to Mailpit configuration with:

```powershell
docker compose up -d --force-recreate ctem-api
```

## Current boundaries

- Exposure events are emitted only when the CTEM request includes `tenant_id`;
  this preserves existing requests while ensuring workflow routing is tenant
  scoped.
- Other notification channels still depend on their external providers and
  credentials. This stack only demonstrates the in-app channel and local report
  email capture.
- The Evidence Repository source directory in this checkout is empty, so the
  CTEM-to-Evidence integration cannot be verified here.
- This is a single-node development stack; it does not provide production Kafka,
  database, secret-management, or multi-instance guarantees.

## Verification notes (2026-10-30)

- Offline suite: 36 tests passed. Combined measured line coverage was 64% for
  CTEM and Workflow together; separately CTEM measured 76% and Workflow 43%.
- Scheduler retry recovery: schedule 5 persisted across a CTEM API restart with
  `enabled=false`, `attempts=0`, and exactly one matching Mailpit message.
- Workflow API checks passed for create/retrieve, execute, duplicate-trigger
  reuse, pause/resume, approval, and rejection. Unit tests cover transient retry
  and rollback invocation.
- A fresh tenant-scoped CTEM exposure was saved, its outbox event was published,
  a matching Workflow completed, and the in-app Notification was recorded as
  `SENT` for the seeded test user.
- Notification API and in-app worker passed a seeded-user delivery check. A
  controlled missing-user case retried three times and reached the DLQ.
- Twenty local requests per service were measured as a latency smoke check
  (not a load test or a proposal-target assessment): CTEM median/p95 27.8/109.6ms,
  Workflow 24.6/95.4ms, Notification 39.9/66.3ms, and Mailpit 32.5/64.6ms.
- The proposal document was not present in this checkout, so proposal-specific
  scheduler architecture and performance targets remain unverified. The Evidence
  Repository source is also absent, so its integration remains blocked.
