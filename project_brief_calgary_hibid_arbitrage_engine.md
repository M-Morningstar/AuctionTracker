# Project Brief: Calgary HiBid Arbitrage Engine

## 1. Executive Summary
**Project Goal:** To build an automated data pipeline that identifies profitable arbitrage opportunities from local Calgary HiBid auctions. 

Currently, identifying underpriced auction items requires manual browsing and manual price comparison. We are building an automated system that will scrape local auction listings, cross-reference them with current secondary market values (e.g., eBay sold listings), factor in all hidden costs (buyer's premiums, taxes, platform fees), and generate a daily hotlist of items with high profit margins. 

## 2. Project Objectives
*   **Automate Data Extraction:** Reliably scrape HiBid Calgary auction catalogs without triggering anti-bot protections.
*   **Data Normalization:** Clean and structure messy auction titles into queryable product names using LLM-assisted parsing.
*   **Automated Valuation:** Programmatically determine the true market value of an item using secondary market APIs.
*   **Margin Calculation:** Apply a strict business logic formula to calculate net profit, factoring in local taxes (5% GST) and typical HiBid buyer's premiums (12-15%).
*   **Actionable Alerting:** Deliver a filtered list of high-ROI items to the end user via a simple dashboard or notification system.

## 3. Scope of Work
**In-Scope:**
*   Scraping targeted Calgary-based auction houses on the HiBid platform.
*   Integration with Crawl4AI for asynchronous, JavaScript-rendered scraping.
*   Integration with the eBay Finding/Completed API (or similar) for market comps.
*   Database setup (PostgreSQL/SQLite) for tracking items and price history.
*   Basic alerting mechanism (e.g., Discord/Telegram bot or a simple Streamlit dashboard).

**Out-of-Scope (Phase 1):**
*   Automated bidding (this is an analysis tool only; bidding remains manual).
*   Scraping platforms other than HiBid.
*   Logistics tracking (pickup, shipping, or inventory management of purchased items).

## 4. Technical Stack
*   **Scraping:** Python + Crawl4AI (utilizing stealth and JS-rendering capabilities).
*   **Data Structuring:** OpenAI/Gemini API (via Crawl4AI's extraction features) for entity resolution.
*   **Database:** PostgreSQL (for robust transactional integrity) or SQLite (for rapid MVP development).
*   **Market Data:** eBay Developer APIs.
*   **UI / Alerting:** Discord Webhooks (push notifications) OR Streamlit (web dashboard).

## 5. Development Phases & Milestones

| Sprint / Phase | Focus | Deliverables |
| :--- | :--- | :--- |
| **Phase 1: Ingestion** | Crawl4AI Setup | Python script capable of bypassing basic HiBid bot protections to extract Item ID, Title, Current Bid, End Date, and Image URL. |
| **Phase 2: Cleaning** | Entity Resolution | Pipeline step that takes raw titles (e.g., "NIB Dewalt Drill 20v") and normalizes them for search ("Dewalt 20V Drill"). |
| **Phase 3: Valuation** | API Integrations | Integration with eBay API to fetch average *sold* prices for the normalized items. |
| **Phase 4: The Engine** | Business Logic | Implementation of the Arbitrage Formula: `(Market Value * 0.85) - (Current Bid * 1.15 * 1.05) = Estimated Profit`. |
| **Phase 5: Delivery** | User Interface | Functional dashboard or notification bot pushing alerts for items exceeding a 40% ROI threshold. |

## 6. Key Risks & Mitigations
1.  **Risk:** Scraper gets blocked by HiBid.
    *   *Mitigation:* Utilize Crawl4AI's stealth configurations, rotate user agents, and keep request concurrency low to mimic human browsing.
2.  **Risk:** Wildly inaccurate price comparisons due to item condition (e.g., comparing a broken item to a brand-new one).
    *   *Mitigation:* Prompt the LLM during the normalization phase to flag condition keywords ("untested", "parts only", "NIB") and adjust the valuation search queries accordingly.
3.  **Risk:** Bidding wars eliminate margins at the last minute.
    *   *Mitigation:* The system will calculate and display the *Maximum Profitable Bid*. We do not care about the current bid, only whether the current bid has surpassed our maximum threshold.

## 7. Next Steps
*   **Data Engineer:** Begin drafting the initial Crawl4AI script to test extraction on a single live Calgary HiBid auction URL.
*   **Backend Developer:** Set up the local database schema and register for eBay API developer credentials.