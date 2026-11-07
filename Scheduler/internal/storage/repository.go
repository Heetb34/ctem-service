package storage

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"cyart/scheduler/internal/jobs"

	"github.com/google/uuid"
)

type JobRepository struct {
	DB *sql.DB
}

func NewJobRepository(db *sql.DB) *JobRepository {
	return &JobRepository{DB: db}
}

func (r *JobRepository) Create(ctx context.Context, job *jobs.Job) error {
	if job.ID == "" {
		job.ID = uuid.NewString()
	}

	now := time.Now().UTC()
	job.CreatedAt = now
	job.UpdatedAt = now

	if job.Enabled {
		nextRun, err := jobs.CalculateNextRun(job, now)
		if err != nil {
			return fmt.Errorf("calculate next run: %w", err)
		}
		job.NextRunAt = nextRun
	} else {
		job.NextRunAt = nil
	}

	payload, err := json.Marshal(job.Payload)
	if err != nil {
		return fmt.Errorf("encode job payload: %w", err)
	}

	_, err = r.DB.ExecContext(ctx, `
        INSERT INTO scheduled_jobs (
            id, name, description, target_type, target_url,
            kafka_topic, payload, schedule_type, cron_expression,
            interval_seconds, run_at, max_retries, backoff_seconds,
            enabled, created_at, updated_at, next_run_at
        )
        VALUES (
            $1, $2, $3, $4, NULLIF($5, ''),
            NULLIF($6, ''), $7, $8, NULLIF($9, ''),
            NULLIF($10, 0), $11, $12, $13, $14, $15, $16, $17
        )`,
		job.ID, job.Name, job.Description, job.TargetType,
		job.TargetURL, job.KafkaTopic, payload, job.ScheduleType,
		job.CronExpression, job.IntervalSeconds, job.RunAt,
		job.MaxRetries, job.BackoffSeconds, job.Enabled,
		job.CreatedAt, job.UpdatedAt, job.NextRunAt,
	)
	if err != nil {
		return fmt.Errorf("create scheduled job: %w", err)
	}

	return nil
}

func (r *JobRepository) GetByID(ctx context.Context, id string) (*jobs.Job, error) {
	var job jobs.Job
	var payload []byte

	err := r.DB.QueryRowContext(ctx, `
        SELECT id, name, COALESCE(description, ''), target_type, COALESCE(target_url, ''),
		       COALESCE(kafka_topic, ''), payload, schedule_type, COALESCE(cron_expression, ''),
		       COALESCE(interval_seconds, 0), run_at, max_retries, backoff_seconds,
               enabled, created_at, updated_at, next_run_at, last_run_at
        FROM scheduled_jobs
        WHERE id = $1`, id,
	).Scan(
		&job.ID, &job.Name, &job.Description, &job.TargetType,
		&job.TargetURL, &job.KafkaTopic, &payload, &job.ScheduleType,
		&job.CronExpression, &job.IntervalSeconds, &job.RunAt,
		&job.MaxRetries, &job.BackoffSeconds, &job.Enabled,
		&job.CreatedAt, &job.UpdatedAt, &job.NextRunAt, &job.LastRunAt,
	)
	if err != nil {
		return nil, err
	}

	if len(payload) > 0 {
		if err := json.Unmarshal(payload, &job.Payload); err != nil {
			return nil, fmt.Errorf("decode job payload: %w", err)
		}
	}

	return &job, nil
}

func (r *JobRepository) List(ctx context.Context) ([]jobs.Job, error) {
	rows, err := r.DB.QueryContext(ctx, `
        SELECT id, name, COALESCE(description, ''), target_type, COALESCE(target_url, ''),
		       COALESCE(kafka_topic, ''), payload, schedule_type, COALESCE(cron_expression, ''),
		       COALESCE(interval_seconds, 0), run_at, max_retries, backoff_seconds,
               enabled, created_at, updated_at, next_run_at, last_run_at
        FROM scheduled_jobs
        ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	result := make([]jobs.Job, 0)

	for rows.Next() {
		var job jobs.Job
		var payload []byte

		err := rows.Scan(
			&job.ID, &job.Name, &job.Description, &job.TargetType,
			&job.TargetURL, &job.KafkaTopic, &payload, &job.ScheduleType,
			&job.CronExpression, &job.IntervalSeconds, &job.RunAt,
			&job.MaxRetries, &job.BackoffSeconds, &job.Enabled,
			&job.CreatedAt, &job.UpdatedAt, &job.NextRunAt, &job.LastRunAt,
		)
		if err != nil {
			return nil, err
		}

		if len(payload) > 0 {
			if err := json.Unmarshal(payload, &job.Payload); err != nil {
				return nil, err
			}
		}

		result = append(result, job)
	}

	return result, rows.Err()
}

func (r *JobRepository) Update(ctx context.Context, job *jobs.Job) error {
	now := time.Now().UTC()
	job.UpdatedAt = now

	if job.Enabled {
		nextRun, err := jobs.CalculateNextRun(job, now)
		if err != nil {
			return fmt.Errorf("calculate next run: %w", err)
		}
		job.NextRunAt = nextRun
	} else {
		job.NextRunAt = nil
	}

	payload, err := json.Marshal(job.Payload)
	if err != nil {
		return fmt.Errorf("encode job payload: %w", err)
	}

	result, err := r.DB.ExecContext(ctx, `
        UPDATE scheduled_jobs SET
            name = $2, description = $3, target_type = $4,
            target_url = NULLIF($5, ''), kafka_topic = NULLIF($6, ''),
            payload = $7, schedule_type = $8,
            cron_expression = NULLIF($9, ''), interval_seconds = NULLIF($10, 0),
            run_at = $11, max_retries = $12, backoff_seconds = $13,
            enabled = $14, updated_at = $15, next_run_at = $16
        WHERE id = $1`,
		job.ID, job.Name, job.Description, job.TargetType,
		job.TargetURL, job.KafkaTopic, payload, job.ScheduleType,
		job.CronExpression, job.IntervalSeconds, job.RunAt,
		job.MaxRetries, job.BackoffSeconds, job.Enabled,
		job.UpdatedAt, job.NextRunAt,
	)
	if err != nil {
		return fmt.Errorf("update scheduled job: %w", err)
	}

	count, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if count == 0 {
		return sql.ErrNoRows
	}

	return nil
}

func (r *JobRepository) Delete(ctx context.Context, id string) error {
	result, err := r.DB.ExecContext(ctx,
		`DELETE FROM scheduled_jobs WHERE id = $1`, id)
	if err != nil {
		return err
	}

	count, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if count == 0 {
		return sql.ErrNoRows
	}

	return nil
}

func (r *JobRepository) DueJobs(ctx context.Context, limit int, instanceID string) ([]jobs.Job, error) {
	if limit <= 0 {
		return nil, fmt.Errorf("limit must be greater than zero")
	}

	if instanceID == "" {
		return nil, fmt.Errorf("instance ID must not be empty")
	}

	tx, err := r.DB.BeginTx(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("begin job claim transaction: %w", err)
	}
	defer tx.Rollback()

	rows, err := tx.QueryContext(ctx, `
        SELECT id, name, COALESCE(description, ''), target_type,
               COALESCE(target_url, ''), COALESCE(kafka_topic, ''),
               payload, schedule_type, COALESCE(cron_expression, ''),
               COALESCE(interval_seconds, 0), run_at, max_retries,
               backoff_seconds, enabled, created_at, updated_at,
               next_run_at, last_run_at
        FROM scheduled_jobs
        WHERE enabled = TRUE
          AND next_run_at <= NOW()
          AND (claimed_until IS NULL OR claimed_until <= NOW())
        ORDER BY next_run_at ASC
        LIMIT $1
        FOR UPDATE SKIP LOCKED
    `, limit)
	if err != nil {
		return nil, fmt.Errorf("select due jobs: %w", err)
	}

	result := make([]jobs.Job, 0)

	for rows.Next() {
		var job jobs.Job
		var payload []byte

		err := rows.Scan(
			&job.ID, &job.Name, &job.Description, &job.TargetType,
			&job.TargetURL, &job.KafkaTopic, &payload, &job.ScheduleType,
			&job.CronExpression, &job.IntervalSeconds, &job.RunAt,
			&job.MaxRetries, &job.BackoffSeconds, &job.Enabled,
			&job.CreatedAt, &job.UpdatedAt, &job.NextRunAt, &job.LastRunAt,
		)
		if err != nil {
			rows.Close()
			return nil, fmt.Errorf("scan due job: %w", err)
		}

		if len(payload) > 0 {
			if err := json.Unmarshal(payload, &job.Payload); err != nil {
				rows.Close()
				return nil, fmt.Errorf("decode job payload: %w", err)
			}
		}

		result = append(result, job)
	}

	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}

	if err := rows.Close(); err != nil {
		return nil, err
	}

	for _, job := range result {
		_, err := tx.ExecContext(ctx, `
            UPDATE scheduled_jobs
            SET claimed_until = NOW() + INTERVAL '30 seconds',
                claimed_by = $2
            WHERE id = $1
        `, job.ID, instanceID)
		if err != nil {
			return nil, fmt.Errorf("claim job %s: %w", job.ID, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return nil, fmt.Errorf("commit job claims: %w", err)
	}

	return result, nil
}

func (r *JobRepository) CreateJobHistory(ctx context.Context, history *jobs.JobHistory) error {
	if history.ID == "" {
		history.ID = uuid.NewString()
	}

	_, err := r.DB.ExecContext(ctx, `
        INSERT INTO job_history (
            id, job_id, status, attempt, started_at,
            completed_at, duration_ms, error
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `,
		history.ID,
		history.JobID,
		history.Status,
		history.Attempt,
		history.StartedAt,
		history.CompletedAt,
		history.DurationMs,
		history.Error,
	)
	if err != nil {
		return fmt.Errorf("create job history: %w", err)
	}

	return nil
}

func (r *JobRepository) CompleteJob(ctx context.Context, jobID string, instanceID string, history *jobs.JobHistory) error {
	tx, err := r.DB.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	var job jobs.Job
	var enabled bool

	err = tx.QueryRowContext(ctx, `
        SELECT id, schedule_type, COALESCE(cron_expression, ''),
               COALESCE(interval_seconds, 0), run_at, enabled
        FROM scheduled_jobs
        WHERE id = $1 AND claimed_by = $2
        FOR UPDATE
    `, jobID, instanceID).Scan(
		&job.ID, &job.ScheduleType, &job.CronExpression,
		&job.IntervalSeconds, &job.RunAt, &enabled,
	)
	if err != nil {
		return fmt.Errorf("load claimed job: %w", err)
	}

	now := time.Now().UTC()
	job.Enabled = enabled && job.ScheduleType != jobs.ScheduleOnce

	var nextRun *time.Time
	if job.Enabled {
		nextRun, err = jobs.CalculateNextRun(&job, now)
		if err != nil {
			return fmt.Errorf("calculate next run: %w", err)
		}
	}

	history.ID = uuid.NewString()
	history.JobID = jobID
	history.Status = "success"
	history.CompletedAt = &now

	_, err = tx.ExecContext(ctx, `
        INSERT INTO job_history (
            id, job_id, status, attempt, started_at,
            completed_at, duration_ms, error
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `,
		history.ID, history.JobID, history.Status, history.Attempt,
		history.StartedAt, history.CompletedAt, history.DurationMs,
		history.Error,
	)
	if err != nil {
		return fmt.Errorf("save successful job history: %w", err)
	}

	result, err := tx.ExecContext(ctx, `
        UPDATE scheduled_jobs
        SET last_run_at = $3,
            next_run_at = $4,
            enabled = $5,
            claimed_until = NULL,
            claimed_by = NULL,
            updated_at = $3
        WHERE id = $1 AND claimed_by = $2
    `, jobID, instanceID, now, nextRun, job.Enabled)
	if err != nil {
		return err
	}

	count, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if count == 0 {
		return sql.ErrNoRows
	}

	return tx.Commit()
}

func (r *JobRepository) FailJob(ctx context.Context, jobID string, instanceID string, history *jobs.JobHistory) (bool, error) {
	tx, err := r.DB.BeginTx(ctx, nil)
	if err != nil {
		return false, err
	}
	defer tx.Rollback()

	var maxRetries int
	var backoffSeconds int
	var enabled bool

	err = tx.QueryRowContext(ctx, `
        SELECT max_retries, backoff_seconds, enabled
        FROM scheduled_jobs
        WHERE id = $1 AND claimed_by = $2
        FOR UPDATE
    `, jobID, instanceID).Scan(
		&maxRetries, &backoffSeconds, &enabled,
	)
	if err != nil {
		return false, fmt.Errorf("load claimed job: %w", err)
	}

	now := time.Now().UTC()

	history.ID = uuid.NewString()
	history.JobID = jobID
	history.Status = "failed"
	history.CompletedAt = &now

	_, err = tx.ExecContext(ctx, `
        INSERT INTO job_history (
            id, job_id, status, attempt, started_at,
            completed_at, duration_ms, error
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `,
		history.ID, history.JobID, history.Status, history.Attempt,
		history.StartedAt, history.CompletedAt, history.DurationMs,
		history.Error,
	)
	if err != nil {
		return false, fmt.Errorf("save failed job history: %w", err)
	}

	retry := enabled && history.Attempt <= maxRetries

	var nextRun *time.Time
	if retry {
		retryAt := now.Add(time.Duration(backoffSeconds) * time.Second)
		nextRun = &retryAt
	}

	_, err = tx.ExecContext(ctx, `
        UPDATE scheduled_jobs
        SET last_run_at = $3,
            next_run_at = $4,
            enabled = $5,
            claimed_until = NULL,
            claimed_by = NULL,
            updated_at = $3
        WHERE id = $1 AND claimed_by = $2
    `, jobID, instanceID, now, nextRun, retry)
	if err != nil {
		return false, err
	}

	if err := tx.Commit(); err != nil {
		return false, err
	}

	return retry, nil
}

func (r *JobRepository) GetNextAttempt(ctx context.Context, jobID string) (int, error) {
	var attempt int

	err := r.DB.QueryRowContext(ctx, `
        SELECT COUNT(*) + 1
        FROM job_history
        WHERE job_id = $1
          AND status = 'failed'
          AND started_at > COALESCE(
              (
                  SELECT MAX(completed_at)
                  FROM job_history
                  WHERE job_id = $1 AND status = 'success'
              ),
              '-infinity'::timestamptz
          )
    `, jobID).Scan(&attempt)

	if err != nil {
		return 0, fmt.Errorf("get next job attempt: %w", err)
	}

	return attempt, nil
}
