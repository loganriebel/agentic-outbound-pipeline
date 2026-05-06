# Agentic Outbound Pipeline

**Disclaimer: This repo is a nerfed version of what I use to build prospects lists to cold email/call. Think of this repo as a way to understand the basic process and pipeline. This agent becomes significantly more powerful when you add business context and detailed listings of your ICP. **

Every weekday at 8am, this pipeline finds new HVAC prospects in Chicago and sends them a cold email from ConnectFirst. Built for outreach, the agent adds to the prospect list, fills email templates, and schedules the email sends based on historical open and reply rates from previous cold emails.

```
Claude Agent (Google Maps)  →  prospects.csv  →  email_sender.py  →  inbox
                                                          ↑
                                               GitHub Actions cron
```

---

## How it works

**Stage 1 — Prospecting** ([`.claude/skills/hvac-chicago-prospector.md`](.claude/skills/hvac-chicago-prospector.md))

A Claude Code skill that searches Google Maps for small HVAC shops in Chicago neighborhoods: Irving Park, Albany Park, Dunning, Belmont Cragin, and others. It targets owner-operated companies with 1-5 trucks and no real web presence just a Google My Business listing.

For each new find, it checks for duplicates, then adds a row to `data/prospects.csv` with the business name, owner name, email, phone, address, and notes. Leaves `Contacted?` blank, which is the trigger for the next stage.

**Stage 2 — Prospect database** ([`data/prospects_example.csv`](data/prospects_example.csv))

A CSV with one row per prospect. The `Contacted?` column is the state machine. Blank means the email sender will pick it up, `X` means it's done.

| Column | Purpose |
|---|---|
| `Contacted?` | Blank = not yet emailed. `X` = sent. |
| `Biz Name` | Used in the UTM campaign tag |
| `Owner Name` | Personalizes the email greeting |
| `Email Address` | Where the email goes |
| `Phone #`, `Physical Address` | For manual follow-up |

**Stage 3 — Email sender** ([`email_sender.py`](email_sender.py))

Reads the CSV, finds every row with a blank `Contacted?` and a valid email address, renders the template with the owner's name and business, sends via SMTP, then marks each row as contacted before moving to the next. If a send fails, it skips that row and logs it. The agent doesn't mark it as contacted.

The template ([`templates/cold_email.txt`](templates/cold_email.txt)) uses Jinja2 variables so the UTM link is auto-slugified per business.

Run it without a `.env` file and it goes into demo mode: logs what it would send, touches nothing.

---

## Sample output

```
$ python email_sender.py --dry-run

2025-05-05 08:00:01  INFO      No .env found — running in demo mode (no emails will be sent).
2025-05-05 08:00:01  INFO      DRY RUN — emails will be previewed but not sent.
2025-05-05 08:00:01  INFO      Loaded 5 total prospects, 3 uncontacted.
2025-05-05 08:00:01  INFO      [DRY RUN] Would send → Brandon Johnson <brandon@chitownheating.com> (chitown heating)
2025-05-05 08:00:01  INFO        Subject : missed a call?
2025-05-05 08:00:01  INFO        Preview : Hello Brandon, The first company to respond wins the job. Miss one call, and that customer is...
2025-05-05 08:00:01  INFO      [DRY RUN] Would send → Maria Sanchez <maria@midwestcomforthvac.com> (midwest comfort hvac)
2025-05-05 08:00:01  INFO        Subject : missed a call?
2025-05-05 08:00:01  INFO        Preview : Hello Maria, The first company to respond wins the job. Miss one call, and that customer is...
2025-05-05 08:00:01  INFO      Skipping bungalow air & heat — no email address.
2025-05-05 08:00:01  INFO      
2025-05-05 08:00:01  INFO      Run complete — sent: 2 | skipped (no email): 1 | failed: 0
```

---

## Scheduling

The GitHub Actions workflow ([`.github/workflows/daily_outreach.yml`](.github/workflows/daily_outreach.yml)) runs Monday through Friday at 8am CT. There's also a "Run workflow" button in the Actions tab for manual triggers.

After each run, logs are saved as a downloadable artifact (30-day retention).

**To set it up**, add these secrets in your repo's Settings > Secrets > Actions:

| Secret | Value |
|---|---|
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | `info@connectfirst.today` |
| `SMTP_PASSWORD` | App password (not account password) |
| `FROM_NAME` | `Logan / ConnectFirst` |
| `FROM_EMAIL` | `info@connectfirst.today` |
| `EMAIL_SUBJECT` | `missed a call?` |

---

## Setup

```bash
git clone https://github.com/loganriebel/prospecting-coldemail-agent
cd prospecting-coldemail-agent
pip install -r requirements.txt

cp .env.example .env
# fill in your SMTP credentials

python email_sender.py --dry-run   # preview without sending
python email_sender.py             # send for real
```

The script auto-detects a missing `.env` and falls back to dry-run mode, so cloning and running it immediately shows exactly what it would do.

---

## Configuration

All settings live in `.env`. See [`.env.example`](.env.example) for the full reference.

| Variable | Default | Notes |
|---|---|---|
| `SMTP_HOST` | — | Your outgoing mail server |
| `SMTP_PORT` | — | `587` for STARTTLS, `465` for SSL |
| `SMTP_USERNAME` | — | Auth username |
| `SMTP_PASSWORD` | — | App password, not account password |
| `FROM_EMAIL` | — | The address prospects see |
| `EMAIL_SUBJECT` | `missed a call?` | Subject line |
| `PROSPECTS_FILE` | `data/prospects_example.csv` | Path to your prospect list |
| `EMAIL_TEMPLATE` | `templates/cold_email.txt` | Jinja2 template path |
| `DAILY_SEND_LIMIT` | `20` | Hard cap per run |
| `DRY_RUN` | `false` | Set to `true` to log without sending |

---

## Project structure

```
.
├── .claude/skills/
│   └── hvac-chicago-prospector.md  # Claude Code skill — runs the prospecting step
├── .github/workflows/
│   └── daily_outreach.yml          # GitHub Actions cron (weekdays, 8am CT)
├── data/
│   └── prospects_example.csv       # Dummy prospect data — shows the schema
├── logs/                           # Run logs (gitignored, uploaded as CI artifacts)
├── templates/
│   └── cold_email.txt              # Jinja2 email template
├── email_sender.py                 # Reads CSV, sends emails, marks contacted
├── requirements.txt
├── .env.example
└── .gitignore
```

---

Built for [ConnectFirst](https://connectfirst.today) — a missed-call auto-texting tool for small HVAC companies.
