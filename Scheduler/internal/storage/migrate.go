package storage

import (
	"database/sql"
	"embed"
	"fmt"
	"strings"
)

//go:embed schema.sql
var schemaFiles embed.FS

func Migrate(db *sql.DB) error {
	schema, err := schemaFiles.ReadFile("schema.sql")
	if err != nil {
		return err
	}

	statements := strings.Split(string(schema), ";")

	for i, statement := range statements {
		statement = strings.TrimSpace(statement)
		if statement == "" {
			continue
		}

		if _, err := db.Exec(statement); err != nil {
			return fmt.Errorf("migration statement %d failed: %w\nSQL: %s", i+1, err, statement)
		}
	}

	return nil
}
