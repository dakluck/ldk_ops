---
name: daily-worksheet
description: Generates a bespoke 1404x1872 vector Daily Folio worksheet for reMarkable 2, aggregating San Diego weather, schedule, critical priorities, and metrics, and uploads it directly via rmapi.
---

# reMarkable 2 Daily Worksheet ("Folio")

Generates a distraction-free, analog-compatible daily worksheet tailored for the reMarkable 2 e-ink tablet.

## Usage

### 1. Daily Generation
Generate today's worksheet PDF & preview:
```bash
python3 daily_worksheet.py
```

### 2. Direct Sync to reMarkable 2
Push today's worksheet into `/Daily/` on the reMarkable tablet over Wi-Fi:
```bash
python3 daily_worksheet.py --upload
```

### 3. First-Time reMarkable Pairing
Pair the machine with your reMarkable Cloud account using a one-time code from https://my.remarkable.com/device/desktop/connect:
```bash
./setup_rmapi.sh
```

### 4. Custom Daily Agenda
To supply custom schedule items or priorities for a specific day, create `daily_input.json`:
```json
{
  "day_summary": "Focus on Reference App Search & Indexing",
  "schedule": [
    {"time": "09:00", "title": "Team Sync", "tag": "CALL", "has_event": true},
    {"time": "10:30", "title": "Deep Work Block", "tag": "DEV", "has_event": true}
  ],
  "priorities": [
    {"title": "Ship Search V2", "tag": "DEV", "desc": "Optimize Algolia/Firestore query latency"}
  ],
  "waiting": [
    {"item": "App Store review confirmation", "target": "Apple"}
  ]
}
```
