package jobs

import (
	"errors"
	"time"

	"github.com/robfig/cron/v3"
)

func CalculateNextRun(job *Job, from time.Time) (*time.Time, error) {
	var next time.Time

	switch job.ScheduleType {
	case ScheduleCron:
		schedule, err := cron.ParseStandard(job.CronExpression)
		if err != nil {
			return nil, errors.New("invalid cron expression: " + err.Error())
		}
		next = schedule.Next(from)

	case ScheduleInterval:
		if job.IntervalSeconds <= 0 {
			return nil, errors.New("interval_seconds must be greater than zero")
		}
		next = from.Add(time.Duration(job.IntervalSeconds) * time.Second)

	case ScheduleOnce:
		if job.RunAt == nil || !job.RunAt.After(from) {
			return nil, errors.New("run_at must be a future time")
		}
		next = *job.RunAt

	default:
		return nil, errors.New("unsupported schedule type")
	}

	return &next, nil
}
