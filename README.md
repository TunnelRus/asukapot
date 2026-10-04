# asukaPot

A no-nonsense Discord honeypot bot built to catch and purge spam self-bots, token loggers, and compromised user accounts before they can blast scam links across your server.

---

### How It Works

Spam bots and hijacked Discord accounts scan servers and blindly send phishing links (free Nitro, Steam scams, airdrops) into every single channel they can see. They don't read channel names and they don't read warnings.

**asukaPot** sets up a designated trap channel (e.g. `#do-not-type`). Real members see the name, read the warning, and scroll past. Automated bots and compromised accounts immediately post in it and get caught.

When someone sends a message in the honeypot:
1. **Instant Wipe:** The message is deleted in milliseconds.
2. **Punishment:** The user is softbanned (kicked and message history wiped), banned, or timed out depending on your config.
3. **1-Use Recovery Invite:** If an account was genuinely compromised and gets softbanned, the bot DMs them recovery steps and a temporary single-use invite link so they can rejoin once their account is secure.
4. **Staff Log:** An incident report is sent to your mod channel showing account age, join speed, and risk assessment.
5. **Live Counter:** The pinned embed in the trap channel updates its counter in real time.

---

### Key Features

* **Zero-Latency Trap:** Cached in memory so incoming messages are validated without querying a database every time.
* **Anti-Raid Spike Protection:** If 3 or more accounts hit the trap within 12 seconds (mass token wave), staff are alerted instantly.
* **Whitelist System:** Exempt specific mod roles or test accounts so staff never accidentally trigger the trap.
* **Role Hierarchy Safeguards:** Validates permissions before taking action to prevent bot crashes.
* **Cloud Database Persistence:** Backs up the SQLite database to a private Discord channel automatically, allowing free 24/7 hosting on Render without losing settings on restart.
* **Clean Staff Interface:** Intuitive `/honeypot` slash commands with zero command clutter.

---

### Commands

All management is handled under the `/honeypot` command group:

| Command | Description |
| :--- | :--- |
| `/honeypot setup #channel` | Arms a channel as the trap and deploys the counter embed. |
| `/honeypot disarm` | Deactivates the trap and safely marks the channel safe to chat in. |
| `/honeypot action [type] [hours]` | Sets punishment (`Softban`, `Ban`, `Kick`, `Timeout`) and wipe window (1–168 hrs). |
| `/honeypot logs #channel` | Sets the staff channel where incident reports are sent. |
| `/honeypot whitelist add [role/user]` | Grants immunity to a role or user. |
| `/honeypot whitelist remove [role/user]`| Removes someone from the whitelist. |
| `/honeypot status` | Displays active settings, catch totals, and recent incidents. |
| `/honeypot sync` | Fixes duplicate slash command previews in your Discord client. |
| `/honeypot help` | Opens the full in-discord staff manual. |

---

### Setup & Installation

#### 1. Discord Developer Portal Setup
1. Create an application at [discord.com/developers](https://discord.com/developers/applications).
2. Under the **Bot** tab, enable both:
   * **Server Members Intent**
   * **Message Content Intent**
3. Under **OAuth2 → URL Generator**, select `bot` and `applications.commands`.
4. Required permissions:
   * `Manage Messages`
   * `Ban Members`
   * `Kick Members`
   * `Moderate Members`
   * `Create Instant Invite`
   * `View Channels`, `Send Messages`, `Embed Links`, `Read Message History`
5. Invite the bot to your server.

> **CRITICAL - Role Hierarchy Rule:**
> Open **Server Settings → Roles** in Discord and drag **asukaPot's role above regular member roles**. Discord strictly forbids bots from kicking or banning users with higher or equal roles.

---

#### 2. Local Environment Setup

Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/asukaPot.git
cd asukaPot
pip install -r requirements.txt
