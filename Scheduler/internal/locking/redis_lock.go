package locking

import (
	"context"
	"fmt"
	"time"

	"github.com/go-redsync/redsync/v4"
	goredis "github.com/go-redsync/redsync/v4/redis/goredis/v9"
	"github.com/redis/go-redis/v9"
)

type RedisLocker struct {
	client  *redis.Client
	redsync *redsync.Redsync
}

func NewRedisLocker(address, password string) *RedisLocker {
	client := redis.NewClient(&redis.Options{
		Addr:     address,
		Password: password,
	})

	pool := goredis.NewPool(client)

	return &RedisLocker{
		client:  client,
		redsync: redsync.New(pool),
	}
}

func (l *RedisLocker) Ping(ctx context.Context) error {
	return l.client.Ping(ctx).Err()
}

func (l *RedisLocker) Acquire(
	ctx context.Context,
	key string,
	expiry time.Duration,
) (*redsync.Mutex, error) {
	mutex := l.redsync.NewMutex(
		key,
		redsync.WithExpiry(expiry),
		redsync.WithTries(1),
	)

	if err := mutex.LockContext(ctx); err != nil {
		return nil, fmt.Errorf("failed to acquire lock %s: %w", key, err)
	}

	return mutex, nil
}

func (l *RedisLocker) Release(
	ctx context.Context,
	mutex *redsync.Mutex,
) error {
	released, err := mutex.UnlockContext(ctx)
	if err != nil {
		return fmt.Errorf("failed to release lock: %w", err)
	}

	if !released {
		return fmt.Errorf("lock was not released")
	}

	return nil
}

func (l *RedisLocker) Close() error {
	return l.client.Close()
}
