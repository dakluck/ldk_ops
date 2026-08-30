---
name: growth-scout
description: >-
  Audits The Reference App acquisition funnels, tracks free-to-premium conversion economics,
  calculates paid user acquisition (Apple Search Ads) targets, and generates ready-to-post
  community showcase content for Reddit and watch forums.
---

# Growth Scout Workflow

This skill tracks app growth, conversion health, and generates organic marketing assets for The Reference App.

## Key Files
- Script: [`growth_engine.py`](file:///home/dailey/Development/ldk_ops/growth_engine.py)
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
- Review break-even and target Cost Per Install (CPI) for Apple Search Ads.
- Copy generated community showcase posts for weekly distribution.
