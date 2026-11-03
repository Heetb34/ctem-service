const { Kafka } = require("kafkajs");

const { kafka, topics } = require("../config/config");

const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});

const consumer = kafkaClient.consumer({
  groupId: "dlq-worker-group",
});

async function startDLQWorker() {
  await consumer.connect();

  console.log("✅ DLQ Worker Connected");

  await consumer.subscribe({
    topic: topics.DLQ,
    fromBeginning: false,
  });

  console.log(`💀 Listening on topic: ${topics.DLQ}`);

  await consumer.run({
    eachMessage: async ({ message }) => {
      try {
        const notification = JSON.parse(message.value.toString());

        console.log("\n================================");
        console.log("💀 DLQ NOTIFICATION RECEIVED");
        console.log("================================");

        console.log("Notification ID :", notification.notification_id);
        console.log("User ID         :", notification.user_id);
        console.log("Channel         :", notification.channel);
        console.log("Retry Count     :", notification.retry_count);
        console.log("Template        :", notification.template_id);

        console.log("--------------------------------");

        console.log(
          "Reason: Maximum retry attempts exceeded"
        );

        console.log("================================\n");

      } catch (err) {
        console.error("❌ DLQ Worker Error:", err.message);
      }
    },
  });
}

startDLQWorker().catch(console.error);