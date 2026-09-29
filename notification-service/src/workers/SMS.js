const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");
const { sendSMS } = require("../services/smsService");
const { publishRetry } = require("../producers/RetryProducer");
const {
  recordNotificationStatus,
} = require("../services/auditService");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const consumer = kafkaClient.consumer({
  groupId: "sms-worker-group",
});
async function startConsumer() {
  await consumer.connect();
  console.log("✅ SMS Worker Connected");
  await consumer.subscribe({
    topic: topics.SMS,
    fromBeginning: false,
  });
  console.log(`📱 Listening on topic: ${topics.SMS}`);
  await consumer.run({
    eachMessage: async ({ message }) => {
      let notification;
      try {
        notification = JSON.parse(message.value.toString());
        console.log("\n📨 SMS Notification Received");
        console.log(notification);
        await sendSMS(notification);
        // Record successful delivery
        recordNotificationStatus(notification, "SENT", {
          recipient: "sms",
        });
        console.log("✅ SMS Processed Successfully\n");
      } catch (err) {
        console.error("❌ SMS Worker Error:", err.message);
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