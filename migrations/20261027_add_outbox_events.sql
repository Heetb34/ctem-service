CREATE TABLE IF NOT EXISTS outbox_events (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL UNIQUE,
    topic VARCHAR(100) NOT NULL,
    payload JSON NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    next_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lease_until DATETIME NULL,
    published_at DATETIME NULL,
    last_error TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX ix_outbox_events_event_id (event_id),
    INDEX ix_outbox_events_pending (published_at, next_attempt_at, lease_until)
);
