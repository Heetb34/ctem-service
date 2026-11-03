package jobs

import "time"

type ScheduleType string

const (
	ScheduleCron     ScheduleType = "cron"
	ScheduleInterval ScheduleType = "interval"
	ScheduleOnce     ScheduleType = "once"
)

type Job struct {
	ID              string       `json:"id"`
	Name            string       `json:"name"`
	Description     string       `json:"description,omitempty"`
	TargetType      string       `json:"target_type"`
	TargetURL       string       `json:"target_url,omitempty"`
	KafkaTopic      string       `json:"kafka_topic,omitempty"`
	Payload         []byte       `json:"payload,omitempty"`
	ScheduleType    ScheduleType `json:"schedule_type"`
	CronExpression  string       `json:"cron_expression,omitempty"`
	IntervalSeconds int64        `json:"interval_seconds,omitempty"`
	RunAt           *time.Time   `json:"run_at,omitempty"`
	MaxRetries      int          `json:"max_retries"`
	BackoffSeconds  int          `json:"backoff_seconds"`
	Enabled         bool         `json:"enabled"`
	CreatedAt       time.Time    `json:"created_at"`
	UpdatedAt       time.Time    `json:"updated_at"`
	NextRunAt       *time.Time   `json:"next_run_at,omitempty"`
	LastRunAt       *time.Time   `json:"last_run_at,omitempty"`
}

type JobHistory struct {
	ID          string     `json:"id"`
	JobID       string     `json:"job_id"`
	Status      string     `json:"status"`
	Attempt     int        `json:"attempt"`
	StartedAt   time.Time  `json:"started_at"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	DurationMs  int64      `json:"duration_ms"`
	Error       string     `json:"error,omitempty"`
}
