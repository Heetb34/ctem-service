package config

import "os"

type Config struct {
	HTTPPort      string
	DatabaseURL   string
	RedisAddress  string
	RedisPassword string
	KafkaBrokers  string
}

func Load() Config {
	return Config{
		HTTPPort:      getEnv("HTTP_PORT", "8004"),
		DatabaseURL:   getEnv("DATABASE_URL", "postgres://user:pass@localhost:5433/scheduler?sslmode=disable"),
		RedisAddress:  getEnv("REDIS_ADDRESS", "localhost:6380"),
		RedisPassword: getEnv("REDIS_PASSWORD", ""),
		KafkaBrokers:  getEnv("KAFKA_BROKERS", "localhost:29092"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
