package jobs

import (
	"testing"
	"time"
)

func TestCalculateNextRun(t *testing.T) {
	from := time.Date(2026, 11, 3, 10, 0, 0, 0, time.UTC)

	tests := []struct {
		name    string
		job     Job
		want    time.Time
		wantErr bool
	}{
		{
			name: "cron schedule",
			job: Job{
				ScheduleType:   ScheduleCron,
				CronExpression: "*/5 * * * *",
			},
			want: time.Date(2026, 11, 3, 10, 5, 0, 0, time.UTC),
		},
		{
			name: "interval schedule",
			job: Job{
				ScheduleType:    ScheduleInterval,
				IntervalSeconds: 60,
			},
			want: from.Add(60 * time.Second),
		},
		{
			name: "one-time schedule",
			job: Job{
				ScheduleType: ScheduleOnce,
				RunAt: func() *time.Time {
					value := from.Add(time.Hour)
					return &value
				}(),
			},
			want: from.Add(time.Hour),
		},
		{
			name: "invalid cron",
			job: Job{
				ScheduleType:   ScheduleCron,
				CronExpression: "invalid",
			},
			wantErr: true,
		},
		{
			name: "invalid interval",
			job: Job{
				ScheduleType:    ScheduleInterval,
				IntervalSeconds: 0,
			},
			wantErr: true,
		},
		{
			name: "invalid one-time schedule",
			job: Job{
				ScheduleType: ScheduleOnce,
			},
			wantErr: true,
		},
		{
			name: "unsupported schedule",
			job: Job{
				ScheduleType: "unknown",
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := CalculateNextRun(&tt.job, from)

			if (err != nil) != tt.wantErr {
				t.Fatalf("error = %v, wantErr = %v", err, tt.wantErr)
			}

			if tt.wantErr {
				return
			}

			if got == nil {
				t.Fatal("expected next run time, got nil")
			}

			if !got.Equal(tt.want) {
				t.Errorf("got %v, want %v", *got, tt.want)
			}
		})
	}
}
