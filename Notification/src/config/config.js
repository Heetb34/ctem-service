require("dotenv").config();
module.exports = {
  kafka: {
    clientId: "notification-system",
    brokers: process.env.KAFKA_BROKERS
      ? process.env.KAFKA_BROKERS.split(",")
      : ["localhost:9092"]
  },
  sendgrid: {
    apiKey: process.env.SENDGRID_API_KEY
  },
  firebase: {
    serviceAccount: process.env.FIREBASE_SERVICE_ACCOUNT
  },
  slack: {
    webhookUrl: process.env.SLACK_WEBHOOK_URL
  },
  teams: {
    webhookUrl: process.env.TEAMS_WEBHOOK_URL
  },
         topics: {
    EMAIL: "notification.email",
    SMS: "notification.sms",
    PUSH: "notification.push",
    SLACK: "notification.slack",
    WEBHOOK: "notification.webhook",
    TEAMS: "notification.teams",
    INAPP: "notification.inapp",
    RETRY: "notification.retry",
    DLQ: "notification.dlq"
  }
};