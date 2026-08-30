---
name: growth-scout
description: >-
  Audits The Reference App acquisition funnels, tracks free-to-premium conversion economics,
  calculates paid user acquisition (Apple Search Ads & Google App Campaigns) targets, and
  generates ready-to-post community showcase content for Reddit and watch forums.
---

# Growth Scout Workflow

This skill tracks app growth, multi-platform conversion health, and manages marketing automations for The Reference App.

## Key Files
- Growth Engine: [`growth_engine.py`](file:///home/dailey/Development/ldk_ops/growth_engine.py)
- Apple Search Ads Client: [`growth/asa_client.py`](file:///home/dailey/Development/ldk_ops/growth/asa_client.py)
- Google App Campaigns Client: [`growth/google_ads_client.py`](file:///home/dailey/Development/ldk_ops/growth/google_ads_client.py)
- App Store Metadata: [`ios/fastlane/metadata/`](file:///home/dailey/Development/reference/ios/fastlane/metadata/)
- Play Store Metadata: [`android/fastlane/metadata/`](file:///home/dailey/Development/reference/android/fastlane/metadata/)
- Web Landing SEO: [`web/index.html`](file:///home/dailey/Development/reference/web/index.html)

---

## Execution Procedures

### 1. Run Growth & Marketing Audit
```bash
python3 /home/dailey/Development/ldk_ops/growth_engine.py
```

### 2. Output Analysis
- Verify free-to-premium conversion rate (target > 8%).
- Review break-even and target Cost Per Install (CPI) for Apple Search Ads ($1.82) and Google App Campaigns ($1.20).
- Copy generated community showcase posts for weekly distribution.

