package worker

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"

	"cyart/scheduler/internal/jobs"
	"cyart/scheduler/internal/locking"
	"cyart/scheduler/internal/storage"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
)

const jobLockTTL = 30 * time.Second

type Worker struct {
	Repository   *storage.JobRepository
	Locker       *locking.RedisLocker
	InstanceID   string
	Client       *http.Client
	BatchSize    int
	PollInterval time.Duration
	KafkaBrokers string
}

func New(repository *storage.JobRepository, locker *locking.RedisLocker) *Worker {
	brokers := os.Getenv("KAFKA_BROKERS")
	if brokers == "" {
		brokers = "localhost:29092"
	}

	return &Worker{
		Repository: repository,
		Locker:     locker,
		InstanceID: uuid.NewString(),
		Client: &http.Client{
			Timeout: 25 * time.Second,
		},
		BatchSize:    10,
		PollInterval: 5 * time.Second,
		KafkaBrokers: brokers,
	}
}

func (w *Worker) Start(ctx context.Context) {
	ticker := time.NewTicker(w.PollInterval)
	defer ticker.Stop()

	fmt.Printf("Worker started. Instance ID: %s\n", w.InstanceID)

	w.processDueJobs(ctx)

	for {
		select {
		case <-ctx.Done():
			fmt.Println("Worker stopped.")
			return
		case <-ticker.C:
			w.processDueJobs(ctx)
		}
	}
}

func (w *Worker) processDueJobs(ctx context.Context) {
	jobsToRun, err := w.Repository.DueJobs(ctx, w.BatchSize, w.InstanceID)
	if err != nil {
		fmt.Printf("Worker: unable to fetch due jobs: %v\n", err)
		return
	}

	for _, job := range jobsToRun {
		if ctx.Err() != nil {
			return
		}
		w.executeJob(ctx, job)
	}
}

func (w *Worker) executeJob(ctx context.Context, job jobs.Job) {
	lockKey := "scheduler:job:" + job.ID

	mutex, err := w.Locker.Acquire(ctx, lockKey, jobLockTTL)
	if err != nil {
		fmt.Printf("Worker: skipping job %s; unable to acquire Redis lock: %v\n", job.ID, err)
		return
	}

	defer func() {
		releaseCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		if err := w.Locker.Release(releaseCtx, mutex); err != nil {
			fmt.Printf("Worker: unable to release lock for job %s: %v\n", job.ID, err)
		}
	}()

	startedAt := time.Now().UTC()

	attempt, err := w.Repository.GetNextAttempt(ctx, job.ID)
	if err != nil {
		fmt.Printf("Worker: unable to get attempt count for job %s: %v\n", job.ID, err)
		return
	}

	history := &jobs.JobHistory{
		JobID:     job.ID,
		Attempt:   attempt,
		StartedAt: startedAt,
	}

	fmt.Printf(
		"Executing job %s, attempt %d, target %s\n",
		job.ID,
		attempt,
		job.TargetType,
	)

	err = w.dispatch(ctx, job)
	history.DurationMs = time.Since(startedAt).Milliseconds()

	if err != nil {
		history.Error = err.Error()

		_, failErr := w.Repository.FailJob(ctx, job.ID, w.InstanceID, history)
		if failErr != nil {
			fmt.Printf("Worker: failed to record job failure %s: %v\n", job.ID, failErr)
			return
		}

		fmt.Printf("Worker: job %s failed: %v\n", job.ID, err)
		return
	}

	err = w.Repository.CompleteJob(ctx, job.ID, w.InstanceID, history)
	if err != nil {
		fmt.Printf("Worker: failed to record job completion %s: %v\n", job.ID, err)
		return
	}

	fmt.Printf("Worker: job %s completed successfully\n", job.ID)
}

func (w *Worker) dispatch(ctx context.Context, job jobs.Job) error {
	switch job.TargetType {
	case "http":
		return w.dispatchHTTP(ctx, job)
	case "kafka":
		return w.dispatchKafka(ctx, job)
	default:
		return fmt.Errorf("unsupported target type: %s", job.TargetType)
	}
}

func (w *Worker) dispatchHTTP(ctx context.Context, job jobs.Job) error {
	if job.TargetURL == "" {
		return fmt.Errorf("HTTP target URL is empty")
	}

	var body io.Reader
	if len(job.Payload) > 0 {
		body = bytes.NewReader(job.Payload)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, job.TargetURL, body)
	if err != nil {
		return fmt.Errorf("create HTTP request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Scheduler-Job-ID", job.ID)

	resp, err := w.Client.Do(req)
	if err != nil {
		return fmt.Errorf("execute HTTP request: %w", err)
	}
	defer resp.Body.Close()

	responseBody, readErr := io.ReadAll(io.LimitReader(resp.Body, 4096))
	if readErr != nil {
		return fmt.Errorf("read HTTP response: %w", readErr)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf(
			"HTTP target returned status %d: %s",
			resp.StatusCode,
			string(responseBody),
		)
	}

	return nil
}

func (w *Worker) dispatchKafka(ctx context.Context, job jobs.Job) error {
	if job.KafkaTopic == "" {
		return fmt.Errorf("Kafka topic is empty")
	}

	if w.KafkaBrokers == "" {
		return fmt.Errorf("Kafka broker address is empty")
	}

	writer := &kafka.Writer{
		Addr:         kafka.TCP(w.KafkaBrokers),
		Topic:        job.KafkaTopic,
		Balancer:     &kafka.LeastBytes{},
		RequiredAcks: kafka.RequireAll,
		Async:        false,
	}

	err := writer.WriteMessages(ctx, kafka.Message{
		Key:   []byte(job.ID),
		Value: job.Payload,
	})

	closeErr := writer.Close()

	if err != nil {
		return fmt.Errorf("publish Kafka message: %w", err)
	}
	if closeErr != nil {
		return fmt.Errorf("close Kafka writer: %w", closeErr)
	}

	fmt.Printf("Worker: published job %s to Kafka topic %s\n", job.ID, job.KafkaTopic)

	return nil
}
