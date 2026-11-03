const axios = require("axios");
const { getUser } = require("./userService");
const { renderTemplate } = require("./templateService");
const { teams } = require("../config/config");
async function sendTeams(notification) {
  await getUser(notification.user_id);
  const message = renderTemplate(
    "security-alert-teams",
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
  console.log("\n=============== TEAMS ===============");
  console.log("💼 TEAMS SENT");
  console.log("--------------------------------------");
  console.log(message);
  console.log("======================================\n");
  if (teams.webhookUrl) {
    await axios.post(teams.webhookUrl, { text: message });
  } else {
    console.log("⚠️ TEAMS_WEBHOOK_URL not configured — simulated send only");
  }
  return {
    success: true,
    channel: "teams",
  };
}
module.exports = {
  sendTeams,
};