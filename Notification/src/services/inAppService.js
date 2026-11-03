const { getUser } = require("./userService");
async function sendInApp(notification) {
  await getUser(notification.user_id);
  console.log("\n=============== IN-APP ===============");
  console.log("🔔 IN-APP NOTIFICATION STORED");
  console.log("User:", notification.user_id);
  console.log("Severity:", notification.data?.severity || "Unknown");
  console.log("Vulnerability:", notification.data?.vulnerability || "Unknown");
  console.log("========================================\n");
  return {
    success: true,
    channel: "in-app",
  };
}
module.exports = {
  sendInApp,
};