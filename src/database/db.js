const Database = require("better-sqlite3");
const path = require("path");
const dbPath = path.join(__dirname, "..", "..", "notifications.db");
const db = new Database(dbPath);
db.pragma("journal_mode = WAL");
db.exec(`
  CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    tenant_id TEXT,
    user_id TEXT NOT NULL,
    category TEXT,
    severity TEXT,
    channel TEXT NOT NULL,
    template_id TEXT,
    recipient TEXT,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    body TEXT,
    error_message TEXT,
    metadata TEXT,
    read_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  )
`);
function insertNotification(record) {
  const stmt = db.prepare(`
    INSERT INTO notifications (
      notification_id, tenant_id, user_id, category, severity,
      channel, template_id, recipient, status, attempts,
      body, error_message, metadata, updated_at
    ) VALUES (
      @notification_id, @tenant_id, @user_id, @category, @severity,
      @channel, @template_id, @recipient, @status, @attempts,
      @body, @error_message, @metadata, datetime('now')
    )
    ON CONFLICT(notification_id) DO UPDATE SET
      status = excluded.status,
      attempts = excluded.attempts,
      error_message = excluded.error_message,
      metadata = excluded.metadata,
      updated_at = datetime('now')
  `);
  return stmt.run(record);
}
function getNotificationsByUser(userId) {
  return db
    .prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC")
    .all(userId);
}
function getInAppNotifications(userId) {
  return db
    .prepare(
      "SELECT * FROM notifications WHERE user_id = ? AND channel = 'in-app' ORDER BY created_at DESC"
    )
    .all(userId);
}
function markAsRead(notificationId) {
  return db
    .prepare(
      "UPDATE notifications SET read_at = datetime('now') WHERE notification_id = ?"
    )
    .run(notificationId);
}
function getAllNotifications(limit = 100) {
  return db
    .prepare("SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?")
    .all(limit);
}
module.exports = {
  db,
  insertNotification,
  getNotificationsByUser,
  getInAppNotifications,
  markAsRead,
  getAllNotifications,
};