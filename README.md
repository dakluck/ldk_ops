# LDK Ops

Operations and internal automation toolkit for LDK International.

## 🧠 Antigravity Agent Workflows & Skills

The repository includes native Antigravity skills located in [`.agents/skills/`](file:///home/dailey/Development/ldk_ops/.agents/skills/):

- **[`inbox-triage`](file:///home/dailey/Development/ldk_ops/.agents/skills/inbox-triage/SKILL.md):** Scans and cleans connected inboxes (`dailey@ldk-international.com`, `dailey.kluck@gmail.com`, `leo@ldk-international.com`), preserving transactional and personal emails while trashing marketing and automated noise.
- **[`sd-weekend-scout`](file:///home/dailey/Development/ldk_ops/.agents/skills/sd-weekend-scout/SKILL.md):** Searches and curates hyper-local weekend activities in San Diego tailored specifically for daughter (born 10/6/2023), with direct 1-click Google Calendar integration links sent to `lmdobashi@gmail.com` and `dailey.kluck@gmail.com`.
- **[`monthly-pnl-report`](file:///home/dailey/Development/ldk_ops/.agents/skills/monthly-pnl-report/SKILL.md):** Connects to the Mercury API to generate categorized monthly profit and loss statements.
- **[`reference-analytics`](file:///home/dailey/Development/ldk_ops/.agents/skills/reference-analytics/SKILL.md):** Connects to The Reference App Firestore database (`reference-482005`) to audit user growth, watchbox collections, brand metrics, and in-app feedback.

---

## 📅 Antigravity Scheduled Tasks Paradigm
 
All background automation in **LDK Ops** runs autonomously via **Antigravity Scheduled Tasks** (`https://antigravity.google/docs/features/#scheduled-tasks`), executing as autonomous Gemini Flash agents:
 
| Task Name | Cron Schedule | Target Script / Flow | Description |
| :--- | :--- | :--- | :--- |
| **Leo Inbox Monitor** | `*/15 * * * *` (Every 15 min) | `leo_inbox_monitor.py` | 24/7 monitoring of `leo@ldk-international.com` for incoming family emails/flyers. Automatically sends calendar invites and replies. |
| **MBMA School Calendar Sync** | `0 7 * * *` (Daily 7:00 AM) | `mbma_calendar_sync.py` | Scans MBMA school emails, maintains calendar sync state, and dispatches invites to `lmdobashi@gmail.com` and `dailey.kluck@gmail.com`. |
| **Daily Folio Worksheet** | `0 6 * * *` (Daily 6:00 AM) | `daily_worksheet.py --upload` | Renders 1404x1872 vector e-ink daily organizer with live San Diego weather & agenda, pushing to reMarkable 2 `/Daily/`. |
| **SD Weekend Scout** | `0 20 * * 5` (Friday 8:00 PM) | `sd_weekend_scout.py` | Curates 3 hyper-local toddler activities in San Diego tailored for daughter (born 10/6/2023), with 1-click Google Calendar links. |
| **Trash & Recycling Staging** | `0 19 * * 0` (Sunday 7:00 PM) | `trash_schedule.py --send-invite --push-calendar` | Evaluates City of SD collection schedule for 5522 Bloch St, pushes to Google Family Calendar, and dispatches reminder invite. |
| **Reference App Rundown** | `0 20 * * 0` (Sunday 8:00 PM) | `reference_rundown.py` | Live Firestore audit of weekly signups, conversions, catalog volume, and customer feedback, emailed to Dailey. |
| **Unified Inbox Triage** | `0 21 * * 0` (Sunday 9:00 PM) | `inbox_cleaner.py --apply` | Purges marketing/promotional clutter from connected inboxes while safeguarding transactional and banking mail. |
| **Monthly LDK P&L Report** | `0 9 1 * *` (1st of Month 9:00 AM) | `finance_agent/reports/monthly_report.py` | Analyzes Mercury bank transactions, categorizes expenses, and dispatches monthly financial statement. |
 
---
 
## 🛠️ Verification & Maintenance Rules
 
Before committing or pushing changes to `ldk_ops`, run syntax verification:
 
```bash
python3 -m py_compile *.py
```
