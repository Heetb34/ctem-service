const axios = require("axios");
const { getUser } = require("./userService");
const { renderTemplate } = require("./templateService");
const { slack } = require("../config/config");
async function sendSlack(notification) {
  await getUser(notification.user_id);
  const message = renderTemplate(
    "security-alert-slack",
    {
      severity: notification.data?.severity || "Unknown",
      vulnerability:
        notification.data?.vulnerability || "Security Vulnerability Detected",
      asset: notification.data?.asset || "Unknown Asset",
      status: notification.data?.status || "Unknown",
      description:
        notification.data?.description ||
        "A security vulnerability has been detected in the monitored system.",
    },
    "txt"
  );
  console.log("\n=============== SLACK ===============");
  console.log("💬 SLACK SENT");
  console.log("--------------------------------------");
  console.log(message);
  console.log("======================================\n");
  if (slack.webhookUrl) {
    await axios.post(slack.webhookUrl, { text: message });
  } else {
    console.log("⚠️ SLACK_WEBHOOK_URL not configured — simulated send only");
  }
  return {
    success: true,
    channel: "slack",
  };
}
module.exports = {
  sendSlack,
};