package storage

import (
	"database/sql"
	"embed"
)

//go:embed schema.sql
var schemaFiles embed.FS

func Migrate(db *sql.DB) error {
	schema, err := schemaFiles.ReadFile("schema.sql")
	if err != nil {
		return err
	}

	_, err = db.Exec(string(schema))
	return err
}
