package main

import (
	"context"
	"net/http"
	"time"

	"cyart/scheduler/internal/config"
	"cyart/scheduler/internal/storage"

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

	e := echo.New()

	e.GET("/health", func(c echo.Context) error {
		ctx, cancel := context.WithTimeout(c.Request().Context(), 3*time.Second)
		defer cancel()

		if err := db.PingContext(ctx); err != nil {
			return c.JSON(http.StatusServiceUnavailable, map[string]string{
				"service":  "Scheduler",
				"status":   "unhealthy",
				"database": "disconnected",
			})
		}

		return c.JSON(http.StatusOK, map[string]string{
			"service":  "Scheduler",
			"status":   "healthy",
			"database": "connected",
		})
	})

	e.Logger.Fatal(e.Start(":" + cfg.HTTPPort))
}
