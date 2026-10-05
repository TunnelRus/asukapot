# asukaPot

An intelligent Discord honeypot bot designed to catch and clean up self-bots, token loggers, and compromised accounts before they spread scam links across your server.

Most Discord moderation bots rely on static keyword blacklists. Scammers work around those daily using zero-width unicode spaces, typosquatted links, and fresh throwaway accounts. asukaPot takes a different approach: it creates a dedicated trap channel that legitimate members know to avoid, then intercepts and isolates anyone who posts in it.

---

### How It Works

1. **The Trap Channel:** You set up a channel like `#do-not-type` and arm it with `/honeypot setup`. Real members read the warnings and scroll past.
2. **Instant Interception:** When a bot or compromised user account joins and immediately blasts spam across your channel list, the bot deletes their message in less than 50 milliseconds.
3. **Deception Personas:** Instead of responding like an obvious automated script, the bot can simulate human operator typing delays (0.8 to 2.4 seconds) or send a temporary decoy verification error before removing the account.
4. **Heuristic Threat Scoring:** The engine evaluates join velocity, account age, invisible character padding, and typosquatted domains to assign a threat rating from 0 to 100.
5. **Account Recovery (Softban + 1-Use Invite):** When a regular member gets their account hacked, you usually want to wipe their spam without permanently losing them. For softbans and kicks, asukaPot sends the user recovery instructions and a **single-use, 7-day rejoin link** so they can return once they change their password and enable 2FA.
6. **Staff Incident Logs:** Full telemetry (risk rating, join-to-trigger speed, detected evasion tricks, and message content) is sent to your moderation log channel.

---

### Commands

Everything is managed through the `/honeypot` slash command group:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/honeypot setup` | `channel: #channel` | Arms the channel, pins the live trap card, and starts monitoring. |
| `/honeypot disarm` | *None* | Disarms the channel and updates the embed so it is safe to chat in. |
| `/honeypot action` | `action`, `cleanup_hours` | Sets punishment (`Softban`, `Ban`, `Kick`, `Timeout`) and message purge window (1 to 168 hours). |
| `/honeypot scenario` | `mode` | Chooses deception behavior: `decoy_operator`, `canary_leak`, or `silent`. |
| `/honeypot logs` | `channel: #channel` | Sets the channel where detailed incident reports are sent. |
| `/honeypot incident view` | `incident_id` | Opens full forensic evidence card and case notes for an incident. |
| `/honeypot incident resolve` | `incident_id`, `note` | Marks an incident resolved with a staff audit note. |
| `/honeypot user lookup` | `user: @member` | Checks an account's cross-server reputation score and penalty history. |
| `/honeypot test rule` | `text: "sample"` | Sandbox command to test how the threat engine scores a message. |
| `/honeypot health` | *None* | Shows gateway latency, database response times, and cache integrity. |
| `/honeypot whitelist add` | `target: @role/@user` | Grants immunity to a role or user. |
| `/honeypot whitelist remove` | `target: @role/@user` | Revokes immunity from a role or user. |
| `/honeypot status` | *None* | Displays current server configuration and catch statistics. |
| `/honeypot sync` | *None* | Refreshes and re-registers slash commands if your Discord client shows duplicates. |
| `/honeypot help` | *None* | Displays the in-discord staff manual. |

---

### Threat Scoring Breakdown

When a message hits the trap channel, the heuristic engine calculates an objective risk rating based on behavioral signals:

* **Join-to-Trigger Velocity (+45 points):** The account posted within 10 seconds of joining the server (the single strongest indicator of a self-bot script).
* **Disposable Alt (+30 points):** The account was created within the last 24 hours.
* **Deceptive Domains (+45 points):** The message includes typosquatted links (e.g., `discorcl.gift`, `steamcommunilty.com`).
* **Discord Token Pattern (+60 points):** The message contains a valid-format base64 Discord user token.
* **Invisible Obfuscation (+25 points):** The message contains zero-width spaces or hidden unicode characters used to bypass simple text filters.

**Verdict Categories:**
* `0 to 24` : **LOW** (Accidental trigger or curious regular member)
* `25 to 49` : **MEDIUM** (Suspicious activity or fresh alternate account)
* `50 to 74` : **HIGH** (Compromised user account or session hijack)
* `75 to 100` : **CRITICAL** (Automated raid client or self-bot)

---

### Local Setup & Installation

#### Requirements
* Python 3.10 or higher
* A Discord Bot Token from the [Discord Developer Portal](https://discord.com/developers/applications)

#### 1. Clone and Install Dependencies
```bash
git clone https://github.com/your-username/asukaPot.git
cd asukaPot

# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Linux / macOS
source venv/bin/activate

pip install -r requirements.txt