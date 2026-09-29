const { Kafka } = require("kafkajs");
const { kafka, topics } = require("../config/config");

const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});

const producer = kafkaClient.producer();

let connected = false;

async function publishRetry(notification) {
  if (!connected) {
    await producer.connect();
    connected = true;
  }

  notification.retry_count++;

  await producer.send({
    topic: topics.RETRY,
    messages: [
      {
        key: notification.user_id,
        value: JSON.stringify(notification),
      },
    ],
  });

  console.log("🔄 Notification moved to Retry Queue");
}

module.exports = {
  publishRetry,
};