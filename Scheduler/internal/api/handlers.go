package api

import (
	"context"
	"database/sql"
	"errors"
	"net/http"
	"time"

	"cyart/scheduler/internal/jobs"
	"cyart/scheduler/internal/storage"

	"github.com/labstack/echo/v4"
)

type Handler struct {
	Repository *storage.JobRepository
}

func NewHandler(repository *storage.JobRepository) *Handler {
	return &Handler{Repository: repository}
}

func (h *Handler) RegisterRoutes(e *echo.Echo) {
	e.POST("/jobs", h.CreateJob)
	e.GET("/jobs", h.ListJobs)
	e.GET("/jobs/:id", h.GetJob)
	e.PUT("/jobs/:id", h.UpdateJob)
	e.DELETE("/jobs/:id", h.DeleteJob)
}

func (h *Handler) CreateJob(c echo.Context) error {
	var job jobs.Job
	if err := c.Bind(&job); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid job request"})
	}

	if err := validateJob(&job); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}

	ctx, cancel := requestContext(c)
	defer cancel()

	if err := h.Repository.Create(ctx, &job); err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusCreated, job)
}

func (h *Handler) ListJobs(c echo.Context) error {
	ctx, cancel := requestContext(c)
	defer cancel()

	result, err := h.Repository.List(ctx)
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, result)
}

func (h *Handler) GetJob(c echo.Context) error {
	ctx, cancel := requestContext(c)
	defer cancel()

	job, err := h.Repository.GetByID(ctx, c.Param("id"))
	if errors.Is(err, sql.ErrNoRows) {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Job not found"})
	}
	if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, job)
}

func (h *Handler) UpdateJob(c echo.Context) error {
	var job jobs.Job
	if err := c.Bind(&job); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Invalid job request"})
	}

	job.ID = c.Param("id")

	if err := validateJob(&job); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": err.Error()})
	}

	ctx, cancel := requestContext(c)
	defer cancel()

	if err := h.Repository.Update(ctx, &job); errors.Is(err, sql.ErrNoRows) {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Job not found"})
	} else if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, job)
}

func (h *Handler) DeleteJob(c echo.Context) error {
	ctx, cancel := requestContext(c)
	defer cancel()

	if err := h.Repository.Delete(ctx, c.Param("id")); errors.Is(err, sql.ErrNoRows) {
		return c.JSON(http.StatusNotFound, map[string]string{"error": "Job not found"})
	} else if err != nil {
		return c.JSON(http.StatusInternalServerError, map[string]string{"error": err.Error()})
	}

	return c.NoContent(http.StatusNoContent)
}

func validateJob(job *jobs.Job) error {
	if job.Name == "" {
		return errors.New("job name is required")
	}

	if job.TargetType != "http" && job.TargetType != "kafka" {
		return errors.New("target_type must be http or kafka")
	}

	if job.TargetType == "http" && (job.TargetURL == "" || job.KafkaTopic != "") {
		return errors.New("HTTP jobs require target_url and must not specify kafka_topic")
	}

	if job.TargetType == "kafka" && (job.KafkaTopic == "" || job.TargetURL != "") {
		return errors.New("Kafka jobs require kafka_topic and must not specify target_url")
	}

	switch job.ScheduleType {
	case jobs.ScheduleCron:
		if job.CronExpression == "" {
			return errors.New("cron_expression is required for cron jobs")
		}
	case jobs.ScheduleInterval:
		if job.IntervalSeconds <= 0 {
			return errors.New("interval_seconds must be greater than zero")
		}
	case jobs.ScheduleOnce:
		if job.RunAt == nil || !job.RunAt.After(time.Now()) {
			return errors.New("run_at must be a future time for one-time jobs")
		}
	default:
		return errors.New("schedule_type must be cron, interval, or once")
	}

	if job.MaxRetries < 0 || job.BackoffSeconds < 0 {
		return errors.New("retry and backoff values cannot be negative")
	}

	return nil
}

func requestContext(c echo.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(c.Request().Context(), 10*time.Second)
}
