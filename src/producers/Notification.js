const { Kafka } = require("kafkajs");
const crypto = require("crypto");
const { kafka, topics } = require("../config/config");
const kafkaClient = new Kafka({
  clientId: kafka.clientId,
  brokers: kafka.brokers,
});
const producer = kafkaClient.producer();
let isConnected = false;
const VALID_CHANNELS = [
  "email",
  "sms",
  "push",
  "slack",
  "webhook",
  "teams",
  "in-app",
];
async function connectProducer() {
  if (!isConnected) {
    await producer.connect();
    isConnected = true;
    console.log("✅ Kafka Producer Connected");
  }
}
async function disconnectProducer() {
  if (isConnected) {
    await producer.disconnect();
    isConnected = false;
    console.log("❌ Kafka Producer Disconnected");
  }
}
function buildNotificationPayload(userId, channel, templateId, data = {}) {
  return {
    notification_id: crypto.randomUUID(),
    user_id: userId,
    channel,
    template_id: templateId,
    data,
    timestamp: Date.now(),
    retry_count: 0,
  };
}
function getTopic(channel) {
  switch (channel) {
    case "email":
      return topics.EMAIL;
    case "sms":
      return topics.SMS;
    case "push":
      return topics.PUSH;
    case "slack":
      return topics.SLACK;
    case "webhook":
      return topics.WEBHOOK;
    case "teams":
      return topics.TEAMS;
    case "in-app":
      return topics.INAPP;
    default:
      throw new Error(`Invalid Channel: ${channel}`);
  }
}
async function sendNotification(userId, channel, templateId, data = {}) {
  console.log("==================================");
  console.log("Received Channel :", channel);
  channel = channel.toLowerCase();
  console.log("Lowercase Channel:", channel);
  const topic = getTopic(channel);
  console.log("Kafka Topic :", topic);
  console.log("==================================");
  if (!VALID_CHANNELS.includes(channel)) {
    throw new Error(
      `Invalid Channel '${channel}'. Allowed: ${VALID_CHANNELS.join(", ")}`
    );
  }
  await connectProducer();
  const payload = buildNotificationPayload(userId, channel, templateId, data);
  await producer.send({
    topic,
    messages: [
      {
        key: userId,
        value: JSON.stringify(payload),
      },
    ],
  });
  console.log(`✅ Notification ${payload.notification_id} published to ${topic}`);
  return payload;
}
module.exports = {
  sendNotification,
  connectProducer,
  disconnectProducer,
};