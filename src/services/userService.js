const users = {
  "user-123": {
    userId: "user-123",
    name: "Test User",
    // Testing recipient
    email: "test.user@example.com",
    phone: "0000000000",
    // Push notification token
    pushToken: "dummy_push_token",
    // Webhook URL for integrations
    webhookUrl: "https://webhook.site/your-test-url-here",
    // Notification preferences
    preferences: {
      email: true,
      sms: true,
      push: true,
    },
  },
};
async function getUser(userId) {
  const user = users[userId];
  if (!user) {
    throw new Error(`User not found: ${userId}`);
  }
  return user;
}
module.exports = {
  getUser,
};