const { getUser } = require("./userService");
const { renderTemplate } = require("./templateService");
async function sendPush(notification) {
  try {
    const user = await getUser(notification.user_id);
    const message = renderTemplate(
      "security-alert-push",
      {
        severity: notification.data?.severity || "Unknown",
        vulnerability:
          notification.data?.vulnerability || "Security Vulnerability Detected",
        asset: notification.data?.asset || "Unknown Asset",
      },
      "txt"
    );
    console.log("\n=============== PUSH ===============");
    console.log("📲 PUSH SENT");
    console.log("To Token:", user.pushToken);
    console.log("-----------------------------------");
    console.log(message);
    console.log("===================================\n");
    return {
      success: true,
      channel: "push",
      recipient: user.pushToken,
    };
  } catch (error) {
    console.error("❌ Push Notification Failed:", error.message);
    throw error;
  }
}
module.exports = {
  sendPush,
};