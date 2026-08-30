# LDK Ops

Operations and internal automation toolkit for LDK International.

## 🧠 Antigravity Agent Workflows & Skills

The repository includes native Antigravity skills located in [`.agents/skills/`](file:///home/dailey/Development/ldk_ops/.agents/skills/):

- **[`inbox-triage`](file:///home/dailey/Development/ldk_ops/.agents/skills/inbox-triage/SKILL.md):** Scans and cleans connected inboxes (`dailey@ldk-international.com`, `dailey.kluck@gmail.com`, `leo@ldk-international.com`), preserving transactional and personal emails while trashing marketing and automated noise.
- **[`sd-weekend-scout`](file:///home/dailey/Development/ldk_ops/.agents/skills/sd-weekend-scout/SKILL.md):** Searches and curates hyper-local weekend activities in San Diego tailored specifically for daughter (born 10/6/2023), with direct 1-click Google Calendar integration links sent to `ldobashi@gmail.com` and `dailey.kluck@gmail.com`.
- **[`monthly-pnl-report`](file:///home/dailey/Development/ldk_ops/.agents/skills/monthly-pnl-report/SKILL.md):** Connects to the Mercury API to generate categorized monthly profit and loss statements.

---

## 📅 Antigravity Scheduled Tasks

The following recurring tasks for `ldk_ops` are configured as **Scheduled Tasks** in Antigravity:

| Task Name | Schedule | Description & Action |
| :--- | :--- | :--- |
| **SD Weekend Kid-Friendly Ideas** | Weekly (`0 20 * * 5` - Fridays 8:00 PM) | Curates 3 toddler-friendly weekend activities in San Diego tailored for daughter (born 10/6/2023) with 1-click Google Calendar links, emailed to `ldobashi@gmail.com` and `dailey.kluck@gmail.com`. |
| **Sunday Night Inbox Triage** | Weekly (`0 23 * * 0` - Sundays 11:00 PM) | Scans connected inboxes for non-critical noise to clean up and trash, keeping important receipts, bank statements, and personal correspondence. |
| **LDK Monthly P&L Report** | Monthly (`1 9 1 * *`) | Executes `monthly_report.py` in `~/Development/ldk_ops` to analyze monthly financials and dispatches the summary report via email. |
| **Job Scout** | Weekly (`0 5 * * 1` - Mondays 5:00 AM) | Searches for relevant job opportunities based on target background/preferences and emails leads report. |
| **SD Concert Watch** | Monthly (`0 9 1 * *`) | Searches web for upcoming Sleep Token / Chris Stapleton concerts in San Diego over the next 3 months and emails findings. |

---

## 🛠️ Verification & Maintenance Rules

Before committing or pushing changes to `ldk_ops`, run syntax verification:

```bash
python3 -m py_compile *.py
```
