const { Kafka } = require("kafkajs");

const { kafka, topics } = require("../config/config");
const { sendEmail } = require("../services/notificationService");
const { publishRetry } = require("../producers/RetryProducer");
const {
  recordNotificationStatus,
} = require("../services/auditService");

const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});

const consumer = kafkaClient.consumer({
  groupId: "email-worker-group",
});

async function startConsumer() {
  await consumer.connect();

  console.log("✅ Email Worker Connected");

  await consumer.subscribe({
    topic: topics.EMAIL,
    fromBeginning: false,
  });

  console.log(`📩 Listening on topic: ${topics.EMAIL}`);

  await consumer.run({
    eachMessage: async ({ message }) => {
      let notification;

      try {
        notification = JSON.parse(message.value.toString());

        console.log("\n📨 Email Notification Received");
        console.log(notification);

        await sendEmail(notification);

        // Record successful delivery
        recordNotificationStatus(notification, "SENT", {
          recipient: "email",
        });

        console.log("✅ Email Processed Successfully\n");

      } catch (err) {
        console.error("❌ Email Worker Error:", err.message);

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

            // Record DLQ status
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