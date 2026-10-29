const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");
const { sendTeams } = require("../services/teamsService");
const { publishRetry } = require("../producers/RetryProducer");
const {
  recordNotificationStatus,
} = require("../services/auditService");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const consumer = kafkaClient.consumer({
  groupId: "teams-worker-group",
});
async function startConsumer() {
  await consumer.connect();
  console.log("✅ Teams Worker Connected");
  await consumer.subscribe({
    topic: topics.TEAMS,
    fromBeginning: false,
  });
  console.log(`💼 Listening on topic: ${topics.TEAMS}`);
  await consumer.run({
    eachMessage: async ({ message }) => {
      let notification;
      try {
        notification = JSON.parse(message.value.toString());
        console.log("\n📨 Teams Notification Received");
        console.log(notification);
        await sendTeams(notification);
        recordNotificationStatus(notification, "SENT", {
          recipient: "teams",
        });
        console.log("✅ Teams Processed Successfully\n");
      } catch (err) {
        console.error("❌ Teams Worker Error:", err.message);
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