const { getUser } = require("./userService");
const { renderTemplate } = require("./templateService");
async function sendSMS(notification) {
  const user = await getUser(notification.user_id);
  const message = renderTemplate(
    "security-alert-sms",
    {
      name: user.name,
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
  console.log("\n================ SMS =================");
  console.log("📱 SMS SENT");
  console.log("To:", user.phone);
  console.log("--------------------------------------");
  console.log(message);
  console.log("======================================\n");
  return {
    success: true,
  };
}
module.exports = {
  sendSMS,
};