# HireLink Release v1.0.0 🚀

**Date:** Jan 15, 2026
**Status:** Stable / Production Ready

## 🌟 Core Features
1.  **Job Discovery**:
    *   Unified scraping engine via `portal_spider.py` and `scraper_utils.py`.
    *   Supports: LinkedIn, Naukri, Indeed, Glassdoor (Login/Public modes).
2.  **AI Intelligence**:
    *   `LLMClient` integrated with Google Gemini Flash.
    *   Capabilities: Resume Parsing, Job Matching, Cover Letter Generation, Form Filling.
3.  **Monetization & Payments**:
    *   Razorpay Integration (Live/Mock modes).
    *   Plans: FREE, STARTER, PRO.
    *   **New**: Subscription Auto-Expiry logic (30 days / 365 days).
    *   **New**: Detailed Payment Modal (Discounts, Coupons, Clean UI).
4.  **User System**:
    *   Secure Authentication (Password Hashing).
    *   Affiliate Dashboard (Referral Codes, Earnings Tracking).
    *   Admin Dashboard (Metrics, User Management).

## 🛠 Critical Fixes in this Release
*   **Deployment Stability**: Fixed `st.dialog` crash for older Streamlit versions on Render.
*   **Database**: Added `subscription_expiry` column and fixed `SessionLocal` scope bugs.
*   **UI**: Cleaned up Payment Modal (removed debug buttons and redundant separators).
*   **Free Plan**: "Start Free" now grants non-expiring basic access.

## 📦 Verification
Run the verification suite to check health at any time:
```bash
python3 verify_core_capabilities.py
```
*   Expected Score: **4/4** (DB, AI, Pay, Discovery)

## 🚀 Deployment
*   **Branch**: `main`
*   **Tag**: `v1.0.0`
*   **Env Vars Required**:
    *   `GEMINI_API_KEY`
    *   `RAZORPAY_KEY_ID`
    *   `RAZORPAY_KEY_SECRET`
    *   `DATABASE_URL` (Optional, defaults to SQLite)
