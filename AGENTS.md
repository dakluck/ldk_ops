# LDK Ops — Antigravity & Agent Operations Guide

## 1. Project Mission & Overview

**LDK Ops** is the central operational command, automation hub, and intelligence engine for:
1. **The Business (LDK International LLC & The Reference App / Web):** Managing infrastructure, finances, app analytics, developer ops, customer feedback, and revenue metrics for [The Reference App](file:///home/dailey/Development/reference) and web properties.
2. **The Family:** Streamlining daily life, calendar coordination, email management, and curated family/toddler activities in San Diego for Dailey Kluck, Lauren Dobashi, and their daughter (born October 6, 2023).

---

## 2. Core Operational Pillars

### 💼 Pillar 1: Business Operations (The Reference App & LDK International)
- **Financial Intelligence & P&L:** Direct integration with Mercury API (`finance_agent/`) to track revenue, categorize expenses, detect anomalies, and generate monthly P&L reports.
- **Product & Database Analytics:** Live Firestore monitoring (`reference-482005`) for user registration counts, premium subscriber conversions, watch collection aggregates, and in-app customer feedback.
- **Cloud & DNS Infrastructure:** Monitoring Cloudflare tunnels/DNS (`ldk-international.com`, `photos.ldk-international.com`), Google Cloud Platform, and app deployment pipelines.

### 🏡 Pillar 2: Family Operations & Lifestyle
- **San Diego Weekend Scout (`sd-weekend-scout`):** Automated curation of hyper-local toddler activities (parks, splash pads, sensory exhibits, SD Zoo) tailored specifically for daughter's age (DOB: 10/6/2023). Dispatched Friday evenings at 8:00 PM with 1-click Google Calendar integration.
- **Unified Inbox Triage (`inbox-triage`):** Weekly Sunday night sweep across all connected inboxes (`dailey@ldk-international.com`, `dailey.kluck@gmail.com`, `leo@ldk-international.com`) to purge marketing and newsletter clutter while strictly preserving banking, orders, and personal threads.
- **Family Calendar & Communications:** Centralized dispatching to `lmdobashi@gmail.com` and `dailey.kluck@gmail.com` via verified SMTP (`email_sender.py`).

---

## 3. The Antigravity Scheduled Tasks Paradigm (Primary Execution Engine)

All recurring and autonomous background operations in **LDK Ops** are executed via **Antigravity Scheduled Tasks** (`https://antigravity.google/docs/features/#scheduled-tasks`).

### Why Antigravity Scheduled Tasks Over Headless Cron:
1. **Multimodal Agent Intelligence:** Tasks run as Gemini Flash autonomous agents with full filesystem, Python, CLI, and multimodal vision capabilities (e.g. reading photo flyers, analyzing attachments).
2. **Contextual Error Recovery:** If an API endpoint times out, authentication expires, or an email schema shifts, the agent self-diagnoses and retries rather than silently failing.
3. **Live Execution Transcripts & Visibility:** Every run produces a complete, auditable transcript and operational log visible in the AGY management console.
4. **Direct Tool Integration:** Full access to web search, calendar generation, and SMTP dispatch (`email_sender.py`).

### Active Scheduled Tasks Catalog:

| Task Name | Cron Schedule | Target Script / Flow | Description |
| :--- | :--- | :--- | :--- |
| **Leo Inbox Monitor** | `0 8,20 * * *` (Twice Daily 8 AM & 8 PM) | `leo_inbox_monitor.py` | Monitors `leo@ldk-international.com` for incoming family requests, flyer attachments, and school forms. Automatically parses dates/times, dispatches calendar invites, replies with confirmation, and sweeps INBOX to maintain Inbox Zero. |
| **MBMA School Calendar Sync** | `0 7 * * *` (Daily 7:00 AM) | `mbma_calendar_sync.py` | Scans `dailey.kluck@gmail.com` for MBMA newsletters & notices. Updates state in `.mbma_events_state.json` and sends RFC 5545 calendar invites to Dailey & Lauren. |
| **Daily Folio Worksheet** | `0 6 * * *` (Daily 6:00 AM) | `daily_worksheet.py --upload` | Renders bespoke 1404x1872 vector e-ink daily organizer with live San Diego weather & schedule, pushing to reMarkable 2 `/Daily/`. |
| **SD Weekend Scout** | `0 20 * * 5` (Friday 8:00 PM) | `sd_weekend_scout.py` | Curates 3 hyper-local toddler activities in San Diego tailored for daughter (born 10/6/2023), with 1-click Google Calendar links sent to `lmdobashi@gmail.com` and `dailey.kluck@gmail.com`. |
| **Trash & Recycling Staging** | `0 19 * * 0` (Sunday 7:00 PM) | `trash_schedule.py --send-invite --push-calendar` | Evaluates City of SD collection schedule for 5522 Bloch St, verifies holiday delays and biweekly recycling, pushes to Google Family Calendar, and dispatches reminder. |
| **Reference App Rundown** | `0 20 * * 0` (Sunday 8:00 PM) | `reference_rundown.py` | Pulls live Firestore user metrics, weekly signups, premium conversions, catalog totals, customer feedback, and paid acquisition CPI targets, emailing executive digest to Dailey. |
| **Unified Inbox Triage** | `0 21 * * 0` (Sunday 9:00 PM) | `inbox_cleaner.py --apply` | Purges newsletters, marketing promotions, and automated clutter across connected inboxes while strictly preserving banking, receipts, and personal threads. |
| **Monthly LDK P&L Report** | `0 9 1 * *` (1st of Month 9:00 AM) | `finance_agent/reports/monthly_report.py` | Analyzes Mercury bank transactions, categorizes expenses, calculates net income, and dispatches executive P&L statement. |

---

## 4. Registered Antigravity Skills

Agents operating in `ldk_ops` have access to the following native skills in [`.agents/skills/`](file:///home/dailey/Development/ldk_ops/.agents/skills/):

| Skill | Description | Primary Scripts |
| :--- | :--- | :--- |
| **`reference-analytics`** | Live Firestore user metrics, conversion rates, and feedback. | `reference_analytics.py`, `reference_rundown.py` |
| **`growth-scout`** | App growth auditing, conversion economics, and community content generation. | `growth_engine.py` |
| **`inbox-triage`** | High-speed batch triage and cleanup of connected mailboxes. | `inbox_cleaner.py` |
| **`sd-weekend-scout`** | Curated toddler weekend ideas with 1-click Google Calendar links. | `sd_weekend_scout.py` |
| **`monthly-pnl-report`** | Real-time Mercury bank financial analysis and monthly P&L. | `finance_agent/reports/monthly_report.py` |
| **`daily-worksheet`** | reMarkable 2 Daily Folio worksheet generator & cloud sync. | `daily_worksheet.py`, `setup_rmapi.sh` |
| **`trash-schedule`** | SD Get It Done portal sync, biweekly recycling tracking, & Google Family Calendar auto-push. | `trash_schedule.py`, `calendar_oauth_helper.py`, `cron_trash_schedule.sh` |
| **`mbma-calendar-sync`** | Daily sync of MBMA school communications & automated Google Calendar invite updates. | `mbma_calendar_sync.py`, `cron_mbma_sync.sh` |
| **`leo-inbox-monitor`** | 24/7 monitoring of `leo@ldk-international.com` to action family calendar requests & flyer attachments. | `leo_inbox_monitor.py`, `cron_leo_inbox_monitor.sh` |
| **`google-drive`** | Full programmatic access, folder organization, and file sync for `dailey@ldk-international.com`. | `drive_manager.py`, `drive_oauth_helper.py` |

---

## 5. Operational Guardrails & Execution Rules

1. **Strict Secret Hygiene & Cloud Vaulting:**
   - **Never Git:** NEVER hardcode or commit passwords, API tokens, recovery keys, or credentials into Git. All local secrets must reside exclusively in `.env` (git-ignored) or local configuration paths (`~/.config/himalaya/`, `~/.config/gcloud/`).
   - **Cloud Source of Truth:** All `.env` secrets and wallet recovery inventories must be mirrored to **GCP Secret Manager** (project: `ldk-international`).
   - **Sync Workflow:** Use `python3 sync_secrets.py --push` immediately after adding or rotating local secrets, and `python3 sync_secrets.py --pull` when restoring or re-hydrating the environment on a new machine.
2. **Recipient Email Accuracy:** Always verify family recipients are set to `lmdobashi@gmail.com` and `dailey.kluck@gmail.com`.
3. **Safety-First Mailbox Triage:** Always safeguard personal correspondence, banking/credit notices, tax documents, and purchase/delivery confirmations during inbox cleanups.
4. **Age-Appropriate Scouting:** Keep weekend recommendations matched to toddler wake windows (morning / late afternoon) and developmentally engaging for a toddler born in October 2023.
5. **Mandatory Verification (Pre-Commit / Pre-Push):**
   - Lint / Syntax Check: `python3 -m py_compile *.py`
   - Run live or dry-run execution checks prior to pushing changes.
6. **Recurring Automations Paradigm:** Whenever creating or updating recurring routines, always deploy them directly as **Antigravity Scheduled Tasks** via `~/.gemini/config/sidecars/<slug>/sidecar.json`. Never fall back to headless Linux cron or systemd timers unless explicitly requested.
