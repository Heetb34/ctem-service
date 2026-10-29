\# Adding Real Users \& Recipients



This guide explains, step by step, how to move from the single hardcoded test user (`user-123`) to real recipients — real team members' emails, phone numbers, and real Slack/Teams channels.



\## Quick Reference: What Each Channel Needs



| Channel | What you need | Per-person or per-channel? |

|---|---|---|

| Email | Real email address | Per-person |

| SMS | Real phone number | Per-person |

| Push | Real device token (requires a mobile app registered with Firebase) | Per-person |

| Slack | One Incoming Webhook URL | Per-channel (whole team shares one) |

| Teams | One Incoming Webhook URL | Per-channel (whole team shares one) |

| Webhook | A destination URL from the receiving system | Per external system |

| In-App | Just the user's ID (already in your system) | Per-person |



\---



\## Step 1: Add Real People to `userService.js`



This is the file that currently only knows about `user-123`. Open it:



```powershell

notepad src\\services\\userService.js

```



Currently it looks like this:



```javascript

const users = {

&#x20; "user-123": {

&#x20;   userId: "user-123",

&#x20;   name: "test.User",

&#x20;   email: "test.User@gmail.com",

&#x20;   phone: "0000000000",

&#x20;   pushToken: "dummy\_push\_token",

&#x20;   webhookUrl: "https://webhook.site/your-test-url-here",

&#x20;   preferences: {

&#x20;     email: true,

&#x20;     sms: true,

&#x20;     push: true,

&#x20;   },

&#x20; },

};

```



To add a real security team member, add a new entry to the `users` object, following the same shape:



```javascript

const users = {

&#x20; "user-123": {

&#x20;   userId: "user-123",

&#x20;   name: "test.User",

&#x20;   email: "test.User@gmail.com",

&#x20;   phone: "0000000000",

&#x20;   pushToken: "dummy\_push\_token",

&#x20;   webhookUrl: "https://webhook.site/your-test-url-here",

&#x20;   preferences: { email: true, sms: true, push: true },

&#x20; },

&#x20; "user-456": {

&#x20;   userId: "user-456",

&#x20;   name: "Real Team Member Name",

&#x20;   email: "their.real.email@company.com",

&#x20;   phone: "9999999999",

&#x20;   pushToken: "dummy\_push\_token",

&#x20;   webhookUrl: null,

&#x20;   preferences: { email: true, sms: true, push: false },

&#x20; },

};

```



\*\*Notes:\*\*

\- The `userId` (e.g., `"user-456"`) is what you'll pass as `userId` in the `POST /notifications` API call — it's an internal identifier, can be anything unique.

\- `phone` should include country code formatting appropriate for your SMS provider once that's wired up (e.g., `+919999999999` for Twilio).

\- `pushToken` can stay as `"dummy\_push\_token"` for anyone who doesn't have the (currently unbuilt) mobile app — Push will simply simulate for them.

\- `preferences` lets you turn channels on/off per person, though this isn't enforced by the code yet (see "Known Limitations" in the main README) — it's currently just data.



\*\*Important limitation to know:\*\* this file is a plain JavaScript object — every time you restart a worker, it resets to whatever is written here. This is fine for a handful of test users, but is not how a real system would manage hundreds of real users. See "Next Step: Real Database for Users" at the bottom of this guide.



After editing, save and restart every worker (since `userService.js` is shared by all of them):



```powershell

pm2 restart all

```



\---



\## Step 2: Get a Real Slack Webhook URL (Per-Channel, Not Per-Person)



1\. Go to `slack.com`, sign in or create a free workspace

2\. Go to `api.slack.com/apps` → \*\*Create New App\*\* → \*\*From scratch\*\*

3\. Name it, pick your workspace

4\. Left sidebar → \*\*Incoming Webhooks\*\* → toggle \*\*On\*\*

5\. \*\*Add New Webhook to Workspace\*\* → pick the channel your team should see alerts in (e.g., `#security-alerts`)

6\. Copy the URL (`https://hooks.slack.com/services/...`)



Add it to your `.env` file:



```

SLACK\_WEBHOOK\_URL=https://hooks.slack.com/services/your/real/url

```



Restart the Slack worker:



```powershell

pm2 restart slack-worker

```



Every notification sent with `"channel": "slack"` will now post a real message to that Slack channel, visible to everyone in it.



\---



\## Step 3: Get a Real Teams Webhook URL (Same Pattern)



1\. In Microsoft Teams, go to the channel you want alerts in

2\. Click \*\*...\*\* next to the channel name → \*\*Connectors\*\* (or \*\*Workflows\*\*, depending on your Teams version)

3\. Find \*\*Incoming Webhook\*\*, configure it, give it a name

4\. Copy the webhook URL it generates



Add it to `.env`:



```

TEAMS\_WEBHOOK\_URL=https://your-org.webhook.office.com/webhookb2/...

```



Restart:



```powershell

pm2 restart teams-worker

```



\---



\## Step 4: Real Webhook Destination (For Integrating With Another System)



If a specific person or team has a system (a dashboard, a ticketing tool, a SIEM) that should receive raw notification data, get the URL that system expects, and set it on that user's record in `userService.js`:



```javascript

webhookUrl: "https://their-real-system.com/api/webhook-receiver",

```



Restart the Webhook worker after editing:



```powershell

pm2 restart webhook-worker

```



\---



\## Step 5: Real SMS (Requires Code Changes — Not Yet Implemented)



Right now, `smsService.js` only prints to the console — it does not call a real SMS provider. To make this real, you would need to:



1\. Create a Twilio account at `twilio.com`, get an Account SID, Auth Token, and a Twilio phone number

2\. Add these to `.env`:

&#x20;  ```

&#x20;  TWILIO\_ACCOUNT\_SID=your\_sid

&#x20;  TWILIO\_AUTH\_TOKEN=your\_token

&#x20;  TWILIO\_PHONE\_NUMBER=your\_twilio\_number

&#x20;  ```

3\. Install the Twilio SDK: `npm install twilio`

4\. Update `smsService.js` to actually call the Twilio API instead of only logging (this is a real code change — ask if you want help writing it)



\## Step 6: Real Push Notifications (Requires Code Changes — Not Yet Implemented)



Similarly, `pushService.js` only logs — it does not call Firebase. To make this real, you would need to:



1\. Create a Firebase project at `console.firebase.google.com`

2\. Generate a service account key (Project Settings → Service Accounts → Generate new private key)

3\. Add the credentials to `.env` (`FIREBASE\_SERVICE\_ACCOUNT`)

4\. Install the Firebase Admin SDK: `npm install firebase-admin`

5\. Update `pushService.js` to call Firebase Cloud Messaging with a real device token — which also requires a mobile app on the recipient's phone registered to receive pushes (this is a bigger undertaking than the other channels)



\---



\## Next Step: Real Database for Users (Beyond This Guide's Scope)



Editing `userService.js` by hand works for a handful of test users, but does not scale to a real security team. The natural next step — not covered in this guide — would be a `users` table in the same SQLite (or Postgres) database already used for notifications, with a simple way to add/edit users (either directly via SQL, or a small admin API endpoint similar to `POST /notifications`).

