const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");
const { sendWebhook } = require("../services/webhookService");
const { publishRetry } = require("../producers/RetryProducer");
const {
  recordNotificationStatus,
} = require("../services/auditService");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const consumer = kafkaClient.consumer({
  groupId: "webhook-worker-group",
});
async function startConsumer() {
  await consumer.connect();
  console.log("✅ Webhook Worker Connected");
  await consumer.subscribe({
    topic: topics.WEBHOOK,
    fromBeginning: false,
  });
  console.log(`🔗 Listening on topic: ${topics.WEBHOOK}`);
  await consumer.run({
    eachMessage: async ({ message }) => {
      let notification;
      try {
        notification = JSON.parse(message.value.toString());
        console.log("\n📨 Webhook Notification Received");
        console.log(notification);
        await sendWebhook(notification);
        // Record successful delivery
        recordNotificationStatus(notification, "SENT", {
          recipient: "webhook",
        });
        console.log("✅ Webhook Processed Successfully\n");
      } catch (err) {
        console.error("❌ Webhook Worker Error:", err.message);
        if (notification) {
          // Record failure
          recordNotificationStatus(notification, "FAILED", {
            error: err.message,
          });
          if (notification.retry_count < 3) {
            console.log(
              `🔄 Sending notification to Retry Queue. Attempt: ${
                notification.retry_count + 1
              }`
            );
            await publishRetry(notification);
          } else {
            console.log(
              "❌ Maximum retries reached. Notification should go to DLQ."
            );
            recordNotificationStatus(notification, "DLQ", {
              reason: "Maximum retries reached",
            });
          }
        }
      }
    },
  });
}
startConsumer().catch(console.error);