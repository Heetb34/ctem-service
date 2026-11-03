CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('http', 'kafka')),
    target_url TEXT,
    kafka_topic VARCHAR(255),
    payload JSONB,
    schedule_type VARCHAR(20) NOT NULL CHECK (schedule_type IN ('cron', 'interval', 'once')),
    cron_expression VARCHAR(255),
    interval_seconds BIGINT,
    run_at TIMESTAMPTZ,
    max_retries INT NOT NULL DEFAULT 3,
    backoff_seconds INT NOT NULL DEFAULT 60,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    CHECK (
        (target_type = 'http' AND target_url IS NOT NULL AND kafka_topic IS NULL)
        OR
        (target_type = 'kafka' AND kafka_topic IS NOT NULL AND target_url IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_next_run
ON scheduled_jobs (next_run_at)
WHERE enabled = TRUE;

CREATE TABLE IF NOT EXISTS job_history (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    status VARCHAR(30) NOT NULL,
    attempt INT NOT NULL DEFAULT 1,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms BIGINT NOT NULL DEFAULT 0,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_history_job_id
ON job_history (job_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_history_retention
ON job_history (completed_at);
