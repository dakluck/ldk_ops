---
name: sd-weekend-scout
description: >-
  Searches, curates, and emails hyper-local weekend kid-friendly and toddler activities in San Diego
  tailored specifically for the family's daughter (DOB: 10/6/2023). Includes direct 1-click Google Calendar
  integration links. Dispatches to ldobashi@gmail.com and dailey.kluck@gmail.com every Friday at 8:00 PM.
---

# San Diego Weekend Kid-Friendly Activity Scout

This skill curates weekend family events and toddler-appropriate activities in San Diego, tailored to the exact age and development stage of the family's daughter (born October 6, 2023).

## Target Profile & Preferences
- **Child's Birthday:** October 6, 2023 (Toddler / Preschool age)
- **Recipients:** `ldobashi@gmail.com`, `dailey.kluck@gmail.com`
- **Sender:** `leo@ldk-international.com`
- **Schedule:** Recurring weekly on **Friday evenings at 8:00 PM** (`0 20 * * 5`)
- **Key Categories:**
  - Zero-depth splash pads & shaded parks (Waterfront Park, Kellogg Park, Powerhouse Park)
  - Interactive sensory exhibits (The New Children's Museum, Fleet Science Center Kid City)
  - Animals & Nature (SD Zoo Wildlife Explorers Basecamp, Birch Aquarium, Safari Park)
  - Seasonal community festivals & morning farmers markets

---

## Calendar Integration
Every event recommendation includes a direct **1-Click Google Calendar Add Link** pre-populated with:
- Event Title & Category
- Optimized Date & Time window (aligning with toddler wake windows & avoiding midday nap conflicts)
- Location & Address for GPS navigation
- Curated descriptions, parent tips, and parking advice

---

## Execution Procedures

### 1. Dry Run / Preview Recommendations
```bash
python3 /home/dailey/Development/ldk_ops/sd_weekend_scout.py --dry-run
```

### 2. Run & Send Email Dispatch
```bash
python3 /home/dailey/Development/ldk_ops/sd_weekend_scout.py
```
