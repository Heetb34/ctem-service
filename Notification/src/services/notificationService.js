const sgMail = require("@sendgrid/mail");
const { getUser } = require("./userService");
const { renderTemplate } = require("./templateService");
const { sendgrid } = require("../config/config");
sgMail.setApiKey(sendgrid.apiKey);
/**
 * Send vulnerability notification through Email
 */
async function sendEmail(notification) {
  try {
    // Get recipient details
    const user = await getUser(notification.user_id);
    // Vulnerability information
    const severity = notification.data?.severity || "Unknown";
    const asset = notification.data?.asset || "Unknown Asset";
    const status = notification.data?.status || "Unknown";
    const vulnerability =
      notification.data?.vulnerability || "Security Vulnerability Detected";
    const description =
      notification.data?.description ||
      "A security vulnerability has been detected in the monitored system.";
    // Render HTML template
    const html = renderTemplate(notification.template_id, {
      name: user.name,
      severity,
      asset,
      status,
      vulnerability,
      description,
    });
    const msg = {
      to: user.email,
      from: process.env.SENDGRID_FROM_EMAIL || "alerts@example.com",
      subject: `🚨 ${severity} Security Vulnerability Detected`,
      html,
    };
    await sgMail.send(msg);
    console.log("================================");
    console.log("✅ Vulnerability Email Sent");
    console.log(`📧 Sent To: ${user.email}`);
    console.log(`🚨 Severity: ${severity}`);
    console.log(`🖥️ Asset: ${asset}`);
    console.log(`🔍 Vulnerability: ${vulnerability}`);
    console.log(`📌 Status: ${status}`);
    console.log("================================");
    return {
      success: true,
      channel: "email",
      recipient: user.email,
    };
  } catch (err) {
    console.error("❌ Email Notification Failed");
    if (err.response) {
      console.error(err.response.body);
    } else {
      console.error(err.message);
    }
    throw err;
  }
}
module.exports = {
  sendEmail,
};