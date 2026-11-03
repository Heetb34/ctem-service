const express = require("express");
const {
  sendNotification,
  connectProducer,
} = require("../producers/Notification");
const {
  getAllNotifications,
  getNotificationsByUser,
  getInAppNotifications,
  markAsRead,
} = require("../database/db");
const app = express();
app.use(express.json());
// POST /notifications - send a new notification
app.post("/notifications", async (req, res) => {
  try {
    const { userId, channel, templateId, data } = req.body;
    if (!userId || !channel || !templateId) {
      return res.status(400).json({
        error: "userId, channel, and templateId are required",
      });
    }
    const result = await sendNotification(userId, channel, templateId, data || {});
    res.status(201).json(result);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});
// GET /notifications - list all notifications (admin/debug)
app.get("/notifications", (req, res) => {
  const limit = parseInt(req.query.limit) || 100;
  res.json(getAllNotifications(limit));
});
// GET /notifications/user/:userId - list a user's notifications
app.get("/notifications/user/:userId", (req, res) => {
  res.json(getNotificationsByUser(req.params.userId));
});
// GET /notifications/inapp/:userId - in-app notifications for the bell icon
app.get("/notifications/inapp/:userId", (req, res) => {
  res.json(getInAppNotifications(req.params.userId));
});
// POST /notifications/:id/read - mark an in-app notification as read
app.post("/notifications/:id/read", (req, res) => {
  markAsRead(req.params.id);
  res.json({ success: true });
});
// GET /health - basic health check
app.get("/health", (req, res) => {
  res.json({ status: "ok" });
});
const PORT = process.env.API_PORT || 3000;
async function startServer() {
  await connectProducer();
  app.listen(PORT, () => {
    console.log(`✅ Notification API listening on port ${PORT}`);
  });
}
startServer().catch(console.error);