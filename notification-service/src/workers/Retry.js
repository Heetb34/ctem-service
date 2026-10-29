const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");
const {
  recordNotificationStatus,
} = require("../services/auditService");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const consumer = kafkaClient.consumer({
  groupId: "retry-worker-group",
});
const producer = kafkaClient.producer();
const MAX_RETRIES = 3;
async function startRetryWorker() {
  await consumer.connect();
  await producer.connect();
  console.log("✅ Retry Worker Connected");
  console.log("✅ Retry Producer Connected");
  await consumer.subscribe({
    topic: topics.RETRY,
    fromBeginning: false,
  });
  console.log(`🔄 Listening on topic: ${topics.RETRY}`);
  await consumer.run({
    eachMessage: async ({ message }) => {
      try {
        const notification = JSON.parse(message.value.toString());
        console.log("\n🔄 Retry Notification Received");
        console.log(notification);
        const retryCount = notification.retry_count || 0;
        console.log(`🔁 Retry Attempt: ${retryCount}`);
        if (retryCount >= MAX_RETRIES) {
          console.log("❌ Maximum retries reached");
          console.log("➡️ Moving notification to DLQ");
          await producer.send({
            topic: topics.DLQ,
            messages: [
              {
                key: notification.user_id,
                value: JSON.stringify(notification),
              },
            ],
          });
          recordNotificationStatus(notification, "DLQ", {
            reason: "Maximum retries reached",
          });
          console.log("💀 Notification moved to DLQ\n");
          return;
        }
        const delay = Math.pow(2, retryCount) * 1000;
        console.log(
          `⏳ Waiting ${delay / 1000} seconds before retry...`
        );
        await new Promise((resolve) => setTimeout(resolve, delay));
        const retryNotification = {
          ...notification,
          retry_count: retryCount + 1,
        };
        let targetTopic;
        switch (notification.channel.toLowerCase()) {
          case "email":
            targetTopic = topics.EMAIL;
            break;
          case "sms":
            targetTopic = topics.SMS;
            break;
          case "push":
            targetTopic = topics.PUSH;
            break;
          case "slack":
            targetTopic = topics.SLACK;
            break;
          case "webhook":
            targetTopic = topics.WEBHOOK;
            break;
          case "teams":
            targetTopic = topics.TEAMS;
            break;
          case "in-app":
            targetTopic = topics.INAPP;
            break;
          default:
            throw new Error(
              `Invalid channel: ${notification.channel}`
            );
        }
        console.log(
          `📤 Sending retry notification to: ${targetTopic}`
        );
        await producer.send({
          topic: targetTopic,
          messages: [
            {
              key: notification.user_id,
              value: JSON.stringify(retryNotification),
            },
          ],
        });
        console.log(
          `✅ Retry ${retryNotification.retry_count} published to ${targetTopic}\n`
        );
      } catch (err) {
        console.error("❌ Retry Worker Error:", err.message);
      }
    },
  });
}
startRetryWorker().catch(console.error);