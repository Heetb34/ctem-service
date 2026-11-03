const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");
const { sendInApp } = require("../services/inAppService");
const { publishRetry } = require("../producers/RetryProducer");
const {
  recordNotificationStatus,
} = require("../services/auditService");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const consumer = kafkaClient.consumer({
  groupId: "inapp-worker-group",
});
consumer.on(consumer.events.CRASH, ({ payload }) => {
  const error = payload.error;
  console.error("❌ In-App Kafka consumer crashed:", error?.message || error);
  // KafkaJS restarts consumers automatically for recoverable failures. If it
  // marks the crash as non-recoverable, exit so Docker can restart the worker.
  if (!payload.restart) {
    process.exitCode = 1;
  }
});
async function startConsumer() {
  await consumer.connect();
  console.log("✅ In-App Worker Connected");
  await consumer.subscribe({
    topic: topics.INAPP,
    fromBeginning: false,
  });
  console.log(`🔔 Listening on topic: ${topics.INAPP}`);
  await consumer.run({
    eachMessage: async ({ message }) => {
      let notification;
      try {
        notification = JSON.parse(message.value.toString());
        await sendInApp(notification);
        recordNotificationStatus(notification, "SENT", {
          recipient: "in-app",
        });
      } catch (err) {
        console.error("❌ In-App Worker Error:", err.message);
        if (notification) {
          recordNotificationStatus(notification, "FAILED", {
            error: err.message,
          });
          if (notification.retry_count < 3) {
            await publishRetry(notification);
          } else {
            recordNotificationStatus(notification, "DLQ", {
              reason: "Maximum retries reached",
            });
          }
        }
      }
    },
  });
}
startConsumer().catch((err) => {
  console.error("❌ In-App Worker could not start:", err);
  process.exitCode = 1;
});
