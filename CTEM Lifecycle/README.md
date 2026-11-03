\# Notification Framework



Event-driven security notification service, built as Pod Gamma's Notification Framework component (FR-NOTIF) for the AEV Platform. Receives security/vulnerability events and delivers them across 7 channels, with automatic retry, dead-letter handling, persistent audit logging, and a REST API.



\## Architecture



```

&#x20;                   POST /notifications

&#x20;                           |

&#x20;                           v

&#x20;                 Notification API (Express)

&#x20;                           |

&#x20;                           v

&#x20;                   Kafka Producer

&#x20;                           |

&#x20;                           v

&#x20;                         Kafka

&#x20;      +------+------+------+------+------+------+------+

&#x20;      |      |      |      |      |      |      |      |

&#x20;    Email   SMS    Push   Slack Webhook Teams  In-App

&#x20;    Worker Worker Worker Worker Worker Worker  Worker

&#x20;      |      |      |      |      |      |      |

&#x20;      +------+------+------+------+------+------+

&#x20;                           |

&#x20;                           v

&#x20;                    Audit Service

&#x20;                    /            \\

&#x20;             logs/\*.log      SQLite DB

&#x20;                           |

&#x20;                   (on failure) -> Retry Worker -> exponential backoff -> retry

&#x20;                                         |

&#x20;                                  (after 3 attempts)

&#x20;                                         v

&#x20;                                   DLQ Worker

```



All 10 processes (9 workers + API) run under PM2 with automatic restart on crash.



\## Channels (FR-NOTIF-001)



| Channel | Status | Delivery mechanism |

|---|---|---|

| Email | Working | SendGrid, HTML template rendering |

| SMS | Working | Console-simulated (Twilio-shaped), plain-text template |

| Push | Working | Console-simulated (Firebase config present, not wired), short-form template |

| Slack | Working | Incoming Webhook (HMAC not required by Slack), simulated unless `SLACK\_WEBHOOK\_URL` is set |

| Webhook | Working | Generic HTTP POST, HMAC-SHA256 signed payload, simulated unless a real per-user URL is set |

| Teams | Working | Incoming Webhook, simulated unless `TEAMS\_WEBHOOK\_URL` is set |

| In-App | Working | Persisted to database, exposed via `GET /notifications/inapp/:userId`, supports mark-as-read |



Every channel shares the same reliability pipeline: on failure, the worker records a `FAILED` audit entry, then either republishes to `notification.retry` (if under 3 attempts) or marks the notification `DLQ` (if attempts are exhausted). This has been tested live on multiple channels, including the full retry -> backoff -> DLQ path.



\## Reliability



\- \*\*Retry\*\*: exponential backoff (1s, 2s, 4s), max 3 attempts, implemented in `Retry.js`

\- \*\*DLQ\*\*: permanently failed notifications are published to `notification.dlq` and consumed by a dedicated `DLQ.js` worker

\- \*\*Audit trail\*\*: every SENT / FAILED / DLQ transition is recorded to both a flat log file (`logs/notifications.log`) and a SQLite database (`notifications.db`), with the database using upsert semantics so each notification's row reflects its current state

\- \*\*Process management\*\*: PM2 manages all 10 processes with `autorestart: true`; verified live by force-killing a running worker and confirming automatic recovery



\## REST API



| Method | Endpoint | Description |

|---|---|---|

| POST | `/notifications` | Send a notification (`userId`, `channel`, `templateId`, `data`) |

| GET | `/notifications` | List all notifications (admin/debug) |

| GET | `/notifications/user/:userId` | List a user's notifications |

| GET | `/notifications/inapp/:userId` | In-app notification feed |

| POST | `/notifications/:id/read` | Mark an in-app notification as read |

| GET | `/health` | Health check |



\## Tech Stack



\- Node.js + KafkaJS

\- Apache Kafka 4.0.0 (Docker)

\- Express (REST API)

\- better-sqlite3 (persistence)

\- PM2 (process management)

\- SendGrid (email)



\## Setup



```bash

npm install

docker compose up -d

pm2 start ecosystem.config.js

```



API available at `http://localhost:3000`. Kafka UI at `http://localhost:8080`.



\## Manual test



```bash

curl -X POST http://localhost:3000/notifications \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d '{"userId":"user-123","channel":"email","templateId":"security-alert","data":{"severity":"Critical","vulnerability":"SQL Injection","asset":"Production Web Server","status":"Open","description":"Test alert"}}'

```



\## Integration Guide (For Other Teams / Pods)



If another service (e.g., the Workflow Service per the AEV Platform architecture) needs to send a notification through this framework, it only needs to call one endpoint:



\### `POST /notifications`



\*\*Request body:\*\*

```json

{

&#x20; "userId": "user-123",

&#x20; "channel": "email",

&#x20; "templateId": "security-alert",

&#x20; "data": {

&#x20;   "severity": "Critical",

&#x20;   "vulnerability": "SQL Injection",

&#x20;   "asset": "Production Web Server",

&#x20;   "status": "Open",

&#x20;   "description": "A SQL Injection vulnerability was detected on the production web server."

&#x20; }

}

```



\*\*Field reference:\*\*



| Field | Required | Notes |

|---|---|---|

| `userId` | Yes | Must correspond to a known user (currently backed by `userService.js`; would be Pod Alpha's user service in the full platform) |

| `channel` | Yes | One of: `email`, `sms`, `push`, `slack`, `webhook`, `teams`, `in-app` |

| `templateId` | Yes | Currently `security-alert` is the only implemented template; the field is designed to support additional templates without code changes to the caller |

| `data` | No (but expected in practice) | Free-form object merged into the template. The `security-alert` template expects `severity`, `vulnerability`, `asset`, `status`, `description` |



\*\*Response (201 Created):\*\*

```json

{

&#x20; "notification\_id": "8bd1e464-37b5-470a-a895-8f8bf78e98f0",

&#x20; "user\_id": "user-123",

&#x20; "channel": "email",

&#x20; "template\_id": "security-alert",

&#x20; "data": { "...": "..." },

&#x20; "timestamp": 1789020443017,

&#x20; "retry\_count": 0

}

```



This response confirms the notification was \*\*accepted and queued\*\*, not that it was delivered — delivery happens asynchronously through Kafka. To check delivery status, poll:



\### `GET /notifications/user/:userId`



Returns all notifications for that user, each with a `status` field (`SENT`, `FAILED`, or `DLQ`) reflecting current delivery state.



\### Checking a specific notification's outcome



There is currently no `GET /notifications/:id` single-record lookup — callers should filter the `GET /notifications/user/:userId` response by `notification\_id`, or use `GET /notifications` (admin/debug) for a global view. This would be a natural first addition if another team needs precise status polling per notification.



\### What integrators do NOT need to worry about



\- Channel-specific delivery mechanics (SendGrid, Twilio, webhook signing, etc.) — fully handled internally

\- Retry logic — failed deliveries are retried automatically up to 3 times with exponential backoff before landing in the DLQ

\- Audit logging — every notification's lifecycle is recorded automatically



\### Deployment note for integrators



This service currently runs on `localhost:3000` for local development. Before another team can call it from outside your machine, it needs to be deployed somewhere network-reachable (a shared dev server, staging environment, etc.) and that URL shared in place of `localhost`. The service itself has no code changes required to support this — it's purely a deployment/networking step.



\## Known Limitations / Explicit Scope



This is a working prototype demonstrating the full architecture, not a hardened production deployment. Deliberately out of scope for this phase:



\- \*\*Single Kafka broker, replication factor 1\*\* — not fault-tolerant; a multi-broker cluster would be required for production

\- \*\*SQLite instead of Postgres\*\* — functionally equivalent for this phase; the spec's `notifications` table (section 7.4) implies Postgres with `JSONB`/`TIMESTAMPTZ`, which SQLite approximates with `TEXT` columns

\- \*\*No preferences system\*\* (FR-NOTIF-003) — no per-user channel/category matrix, quiet hours, or overrides yet

\- \*\*No deduplication\*\* (FR-NOTIF-005) — the same alert firing twice within 5 minutes would currently send twice

\- \*\*No digest/scheduled delivery\*\* (FR-NOTIF-004) — only immediate delivery is implemented

\- \*\*Slack/Teams/Webhook sends are simulated\*\* unless real webhook URLs are configured via environment variables — the integration code is complete and correct, but no live external endpoint has been exercised

\- \*\*Push uses a placeholder token\*\*, not a real Firebase Cloud Messaging integration, though `firebase.serviceAccount` config is present for this to be wired in

\- \*\*No automated test suite\*\* — all behavior in this document was verified through live, manual end-to-end testing during development, not through CI



\## What Was Actually Tested



Every claim above under "Working" was verified live during development, not assumed:

\- Each channel's success path was triggered and confirmed via worker logs and database rows

\- The failure path (bad recipient -> FAILED -> retry -> backoff -> DLQ) was tested end-to-end on Push, SMS, and Slack, with database rows confirming the final `DLQ` status and `attempts: 3`

\- The REST API was tested with real HTTP requests (not just internal function calls), confirming the full loop: HTTP POST -> Kafka -> worker processing -> database -> HTTP GET

\- PM2's crash recovery was tested by force-killing a live worker process and confirming automatic restart

