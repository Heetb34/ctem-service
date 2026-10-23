# Report scheduler operations

The API supports `once`, `daily`, `weekly`, `monthly`, and `quarterly` report schedules. Times with an explicit UTC offset are converted to UTC before storage. Times without an offset are interpreted as UTC. The API checks for due work every 30 seconds.

Cron expressions are not listed as a requirement in the current project proposal/docs, so this module accepts the named frequencies above.

## Install and configure

Install the API dependencies into the same Python environment used to start FastAPI:

```powershell
.\.venv-win\Scripts\python.exe -m pip install -r app\requirements.txt
```

The API loads the root `.env` file on startup. `.env` is ignored by Git; `.env.example` is the safe template. For Gmail, use:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_FROM=your-sender@gmail.com
SMTP_USE_TLS=true
SMTP_USERNAME=your-sender@gmail.com
SMTP_PASSWORD=your-16-character-google-app-password
```

Use a Google App Password, not the account password. Keep the real values only in the ignored `.env` file.

## Existing database migration

New databases get all scheduler columns from SQLAlchemy. For an existing MySQL database, run [20261023_add_delivered_recipients.sql](migrations/20261023_add_delivered_recipients.sql) once before deploying this version. The column tracks recipients that already accepted a message if SMTP partially refuses a delivery, so retries target only the remaining recipients.

## Check the scheduler

Run the offline automated checks:

```powershell
.\.venv-win\Scripts\python.exe -m pytest tests -v --basetemp .pytest-work
```

For real delivery, start the API, create a one-time schedule for a mailbox you control with a start time one or two minutes in the future (UTC, e.g. `2026-10-23T12:15:00Z`), and check the recipient inbox and the schedule response. A successful run has `last_run_at` set, `attempts` equal to `0`, and `last_error` empty. To test recovery, temporarily stop the SMTP service before a due run, confirm `attempts` and `last_error`, then restore SMTP and confirm the message arrives after retry. Avoid using a shared or production mailbox for failure tests.
