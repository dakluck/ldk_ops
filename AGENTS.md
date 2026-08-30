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
- **Family Calendar & Communications:** Centralized dispatching to `ldobashi@gmail.com` and `dailey.kluck@gmail.com` via verified SMTP (`email_sender.py`).

---

## 3. Registered Antigravity Skills

Agents operating in `ldk_ops` have access to the following native skills in [`.agents/skills/`](file:///home/dailey/Development/ldk_ops/.agents/skills/):

| Skill | Description | Primary Scripts |
| :--- | :--- | :--- |
| **`reference-analytics`** | Live Firestore user metrics, conversion rates, and feedback. | `reference_analytics.py`, `firebase_oauth_helper.py` |
| **`inbox-triage`** | High-speed batch triage and cleanup of connected mailboxes. | `inbox_cleaner.py` |
| **`sd-weekend-scout`** | Curated toddler weekend ideas with 1-click Google Calendar links. | `sd_weekend_scout.py` |
| **`monthly-pnl-report`** | Real-time Mercury bank financial analysis and monthly P&L. | `finance_agent/reports/monthly_report.py` |

---

## 4. Operational Guardrails & Execution Rules

1. **Strict Secret Hygiene:** NEVER hardcode or commit passwords, API tokens, or service account credentials into Git. All secrets must reside exclusively in `.env` (git-ignored) or local configuration paths (`~/.config/himalaya/`, `~/.config/gcloud/`).
2. **Safety-First Mailbox Triage:** Always safeguard personal correspondence, banking/credit notices, tax documents, and purchase/delivery confirmations during inbox cleanups.
3. **Age-Appropriate Scouting:** Keep weekend recommendations matched to toddler wake windows (morning / late afternoon) and developmentally engaging for a toddler born in October 2023.
4. **Mandatory Verification (Pre-Commit / Pre-Push):**
   - Lint / Syntax Check: `python3 -m py_compile *.py`
   - Run live or dry-run execution checks prior to pushing changes.
