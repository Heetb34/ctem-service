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
        console.log("\n📨 In-App Notification Received");
        console.log(notification);
        await sendInApp(notification);
        recordNotificationStatus(notification, "SENT", {
          recipient: "in-app",
        });
        console.log("✅ In-App Processed Successfully\n");
      } catch (err) {
        console.error("❌ In-App Worker Error:", err.message);
        if (notification) {
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