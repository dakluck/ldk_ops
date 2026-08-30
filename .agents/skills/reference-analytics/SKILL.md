---
name: reference-analytics
description: >-
  Audits and inspects The Reference App Firebase/Firestore database (project: reference-482005)
  to generate user growth statistics, premium subscriber counts, cataloged watch totals,
  brand distributions, and customer feedback submissions.
  Use when the user asks for Reference App stats, feedback, or database metrics.
---

# The Reference App — Analytics & Database Audit

This skill connects to the live Cloud Firestore database for **The Reference App** (`reference-482005`) to extract and summarize user statistics, engagement metrics, and feedback.

## Firestore Architecture
- **`/users`** &mdash; User accounts and premium flags.
- **`/users/{userId}/watches`** &mdash; Cataloged watch items in user watchboxes.
- **`/users/{userId}/collections`** &mdash; User-defined watch collections.
- **`/feedback`** &mdash; In-app user feedback reports and screenshots.
- **`/public_showcase`** &mdash; Publicly shared showcase watches.
- **`/shared_links`** &mdash; Active collection share URLs.

---

## Execution Procedures

### 1. Run Live Analytics Audit
```bash
python3 /home/dailey/Development/ldk_ops/reference_analytics.py
```

### 2. Remote OAuth Reauthentication (If ADC Token Expires)
If the Google Cloud Application Default Credentials expire:
```bash
python3 /home/dailey/Development/ldk_ops/firebase_oauth_helper.py
```
Open the generated link in any browser, approve, and run:
```bash
python3 /home/dailey/Development/ldk_ops/firebase_oauth_helper.py "<redirect_url_or_code>"
```
