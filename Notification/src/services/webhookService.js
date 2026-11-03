const axios = require("axios");
const crypto = require("crypto");
const { getUser } = require("./userService");
function signPayload(payload, secret) {
  return crypto
    .createHmac("sha256", secret)
    .update(JSON.stringify(payload))
    .digest("hex");
}
async function sendWebhook(notification) {
  const user = await getUser(notification.user_id);
  const payload = {
    notification_id: notification.notification_id,
    severity: notification.data?.severity || "Unknown",
    vulnerability:
      notification.data?.vulnerability || "Security Vulnerability Detected",
    asset: notification.data?.asset || "Unknown Asset",
    status: notification.data?.status || "Unknown",
    description:
      notification.data?.description ||
      "A security vulnerability has been detected in the monitored system.",
    timestamp: notification.timestamp,
  };
  const secret = process.env.WEBHOOK_SIGNING_SECRET || "dev-secret";
  const signature = signPayload(payload, secret);
  console.log("\n============== WEBHOOK ==============");
  console.log("🔗 WEBHOOK SENT");
  console.log("To URL:", user.webhookUrl);
  console.log("Signature:", signature);
  console.log("Payload:", payload);
  console.log("======================================\n");
  if (user.webhookUrl && !user.webhookUrl.includes("your-test-url-here")) {
    await axios.post(user.webhookUrl, payload, {
      headers: {
        "X-Signature": signature,
        "Content-Type": "application/json",
      },
    });
  } else {
    console.log("⚠️ No real webhook URL configured — simulated send only");
  }
  return {
    success: true,
    channel: "webhook",
  };
}
module.exports = {
  sendWebhook,
};