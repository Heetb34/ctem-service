const {
  sendNotification,
  disconnectProducer,
} = require("./src/producers/Notification");

async function main() {
  try {
    console.log("==================================");
    console.log("Sending Security Vulnerability Alert");
    console.log("Channel: SMS");
    console.log("==================================");

    const result = await sendNotification(
      "user-123",
      "sms",
      "security-alert",
      {
        severity: "Critical",
        vulnerability: "SQL Injection",
        asset: "Production Web Server",
        status: "Open",
        description:
          "A SQL Injection vulnerability was detected on the production web server.",
      }
    );

    console.log(result);
  } catch (error) {
    console.error("❌ Error:", error.message);
  } finally {
    await disconnectProducer();
  }
}

main();