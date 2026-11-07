package main

import (
	"context"
	"errors"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"cyart/scheduler/internal/api"
	"cyart/scheduler/internal/config"
	"cyart/scheduler/internal/locking"
	"cyart/scheduler/internal/storage"
	"cyart/scheduler/internal/worker"

	"github.com/labstack/echo/v4"
)

func main() {
	cfg := config.Load()

	db, err := storage.Connect(cfg.DatabaseURL)
	if err != nil {
		panic("Scheduler database connection failed: " + err.Error())
	}
	defer db.Close()

	if err := storage.Migrate(db); err != nil {
		panic("Scheduler database migration failed: " + err.Error())
	}

	redisLocker := locking.NewRedisLocker(
		cfg.RedisAddress,
		cfg.RedisPassword,
	)
	defer redisLocker.Close()

	redisCtx, redisCancel := context.WithTimeout(
		context.Background(),
		5*time.Second,
	)
	defer redisCancel()

	if err := redisLocker.Ping(redisCtx); err != nil {
		panic("Scheduler Redis connection failed: " + err.Error())
	}

	e := echo.New()

	repository := storage.NewJobRepository(db)
	handler := api.NewHandler(repository)
	handler.RegisterRoutes(e)

	e.GET("/health", func(c echo.Context) error {
		ctx, cancel := context.WithTimeout(
			c.Request().Context(),
			3*time.Second,
		)
		defer cancel()

		if err := db.PingContext(ctx); err != nil {
			return c.JSON(http.StatusServiceUnavailable, map[string]string{
				"service":  "Scheduler",
				"status":   "unhealthy",
				"database": "disconnected",
				"redis":    "unknown",
			})
		}

		if err := redisLocker.Ping(ctx); err != nil {
			return c.JSON(http.StatusServiceUnavailable, map[string]string{
				"service":  "Scheduler",
				"status":   "unhealthy",
				"database": "connected",
				"redis":    "disconnected",
			})
		}

		return c.JSON(http.StatusOK, map[string]string{
			"service":  "Scheduler",
			"status":   "healthy",
			"database": "connected",
			"redis":    "connected",
		})
	})

	ctx, stop := signal.NotifyContext(
		context.Background(),
		os.Interrupt,
		syscall.SIGTERM,
	)
	defer stop()

	schedulerWorker := worker.New(repository, redisLocker)
	go schedulerWorker.Start(ctx)

	serverErrors := make(chan error, 1)

	go func() {
		serverErrors <- e.Start(":" + cfg.HTTPPort)
	}()

	select {
	case <-ctx.Done():
		e.Logger.Info("Shutting down Scheduler...")
	case err := <-serverErrors:
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			e.Logger.Error("Scheduler server failed: ", err)
		}
		stop()
	}

	shutdownCtx, cancel := context.WithTimeout(
		context.Background(),
		5*time.Second,
	)
	defer cancel()

	if err := e.Shutdown(shutdownCtx); err != nil {
		e.Logger.Error("Scheduler shutdown failed: ", err)
	}
}
