---
name: inbox-triage
description: >-
  Scans, triages, and cleans connected Google/Gmail inboxes (dailey@ldk-international.com,
  dailey.kluck@gmail.com, leo@ldk-international.com) to archive or trash marketing clutter,
  newsletters, and automated notifications while preserving transactional, financial, and personal emails.
  Use when the user asks to clean up, triage, or audit their inboxes, or on recurring schedules.
---

# Inbox Triage & Cleanup Workflow

This skill executes automated and on-demand triage for connected Google Workspace and personal Gmail accounts in LDK Ops.

## Connected Accounts
- `dailey@ldk-international.com` (LDK Corporate)
- `dailey.kluck@gmail.com` (Personal)
- `leo@ldk-international.com` (LDK Shared / Operations)

Credentials are configured in `~/.config/himalaya/config.toml`.

---

## Triage Rules & Classification

### 🛡️ Preserved in INBOX (Never Trashed)
- **Financial & Banking:** Mercury, USAA, Chase, Wells Fargo, Stripe charges, transfers, and statements.
- **Corporate & Legal:** ZenBusiness receipts, refunds, and support inquiries.
- **Orders & Tracking:** Amazon, Ubiquiti, ReserveBar, shipping confirmations, delivery notices, invoices.
- **Security & Infrastructure:** Cloudflare Access alerts, Apple App Review notices, Vercel notifications, GitHub notices, password resets.
- **Direct Contacts:** Personal correspondence and non-marketing 1-on-1 threads.

### 🧹 Cleaned Out (Moved to Trash)
- **Marketing & Retail:** Sales, promos, discount codes, retail newsletters (Nike, Patagonia, Lucky8, etc.).
- **Automated Digests:** USPS Informed Delivery daily digests, Word Genius / Word Smarts trivia emails, social media notification pings.
- **Surveys & Solicitations:** Vendor survey requests, cold outreach, and marketing blasts with `List-Unsubscribe` headers.

---

## Execution Procedures

### 1. Dry Run (Preview Changes)
Run the fast batch cleaner in dry-run mode to inspect message counts and samples without modifying mailboxes:

```bash
python3 /home/dailey/Development/ldk_ops/inbox_cleaner.py
```

### 2. Apply Cleanup
Execute the cleanup to move identified noise/clutter directly to `[Gmail]/Trash` and expunge:

```bash
python3 /home/dailey/Development/ldk_ops/inbox_cleaner.py --apply
```

### 3. Verify INBOX Counts
Verify remaining messages and unread counts across all accounts:

```bash
python3 -c "
import imaplib
from email_sender import load_credentials

creds = load_credentials()
for key in ['dailey_ldk', 'dailey_personal']:
    acc = creds[key]
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(acc['email'], acc['password'])
    mail.select('INBOX')
    _, data = mail.search(None, 'ALL')
    total = len(data[0].split()) if data[0] else 0
    _, unr = mail.search(None, 'UNSEEN')
    unread = len(unr[0].split()) if unr[0] else 0
    mail.logout()
    print(f\"{acc['email']}: Total={total}, Unread={unread}\")
"
```
