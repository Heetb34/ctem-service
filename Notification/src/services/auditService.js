const fs = require("fs");
const path = require("path");
const { insertNotification } = require("../database/db");
const auditDirectory = path.join(__dirname, "../../logs");
const auditFile = path.join(auditDirectory, "notifications.log");
/**
 * Make sure the logs directory exists
 */
function ensureAuditDirectory() {
  if (!fs.existsSync(auditDirectory)) {
    fs.mkdirSync(auditDirectory, {
      recursive: true,
    });
  }
}
/**
 * Record notification delivery status
 */
function recordNotificationStatus(notification, status, details = {}) {
  try {
    ensureAuditDirectory();
    const auditRecord = {
      notification_id: notification.notification_id,
      user_id: notification.user_id,
      channel: notification.channel,
      template_id: notification.template_id,
      severity: notification.data?.severity || "Unknown",
      vulnerability:
        notification.data?.vulnerability || "Unknown",
      asset: notification.data?.asset || "Unknown",
      status,
      retry_count: notification.retry_count || 0,
      timestamp: new Date().toISOString(),
      details,
    };
    // Write to flat log file (existing behavior, kept as fallback)
    fs.appendFileSync(
      auditFile,
      JSON.stringify(auditRecord) + "\n",
      "utf8"
    );
    // Write to database
    try {
      insertNotification({
        notification_id: notification.notification_id,
        tenant_id: notification.tenant_id || null,
        user_id: notification.user_id,
        category: notification.template_id || null,
        severity: notification.data?.severity || "Unknown",
        channel: notification.channel,
        template_id: notification.template_id || null,
        recipient: details.recipient || null,
        status,
        attempts: notification.retry_count || 0,
        body: notification.data?.description || null,
        error_message: details.error || null,
        metadata: JSON.stringify(details),
      });
    } catch (dbError) {
      console.error("⚠️ Database audit write failed:", dbError.message);
    }
    console.log(
      `📝 Audit: ${notification.channel.toUpperCase()} → ${status}`
    );
    return auditRecord;
  } catch (error) {
    console.error("❌ Audit logging failed:", error.message);
  }
}
module.exports = {
  recordNotificationStatus,
};