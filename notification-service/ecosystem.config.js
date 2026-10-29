module.exports = {
  apps: [
    {
      name: "email-worker",
      script: "src/workers/Email.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "sms-worker",
      script: "src/workers/SMS.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "push-worker",
      script: "src/workers/Push.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "slack-worker",
      script: "src/workers/Slack.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "webhook-worker",
      script: "src/workers/Webhook.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "teams-worker",
      script: "src/workers/Teams.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "inapp-worker",
      script: "src/workers/InApp.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "retry-worker",
      script: "src/workers/Retry.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "dlq-worker",
      script: "src/workers/DLQ.js",
      autorestart: true,
      max_restarts: 10,
    },
    {
      name: "notification-api",
      script: "src/api/server.js",
      autorestart: true,
      max_restarts: 10,
    },
  ],
};