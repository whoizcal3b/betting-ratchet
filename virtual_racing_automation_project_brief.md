# Project Brief: High-Water Mark Automated Betting System

## 1. Executive Summary
This project outlines the development of a fully automated, headless Python bot designed to execute a high-risk, high-reward staking strategy on virtual racing markets. The system relies on a strict "peak ratchet" (high-water mark) mathematical formula to force rapid compounding or a fast failure, completely eliminating traditional stake-scaling during drawdowns.

## 2. The Math Engine: Peak Ratchet Staking
The core of this system is the risk management formula. The bot does not use a flat percentage of the *current* balance; it uses a flat percentage of the *peak* balance achieved. 

### The Formula Base
$$ Peak Balance \times \left(1 + \frac{Odds - 1}{Divisor}\right)^{Target Wins} $$

*   **Starting Balance:** 1000 units.
*   **Target Odds:** ~2.80 (Minimum).
*   **Divisor (Loss Buffer):** 10. (We risk exactly 1/10th of our peak balance per bet).

### The Execution Rule ("Never Go Down")
1.  The bot checks the **Highest Logged Balance (Peak)**.
2.  The stake is ALWAYS calculated as: `Peak Balance / 10`.
3.  **During a Drawdown:** If the balance drops from 2000 to 1200, the stake remains 200 (2000 / 10). We do not scale down stakes to protect capital. 
4.  **The Result:** A win at 2.80 odds yields an 18% growth on the peak balance (profit factor: `(2.8 - 1) / 10 = 0.18`). The system enforces a hard limit: 10 consecutive losses from a peak will blow the account. The goal is exponential breakout or fast failure.

## 3. Betting Algorithm & Target Market
The bot will target the VirtusTec 4-runner virtual racing markets (specifically the "Bristol" track), which run on a continuous 2-minute cycle (720 races/day). 

**Market Type:** "Place" market (Runner must finish 1st or 2nd).

**Trigger Logic (The "Odd Algo"):**
Every 2 minutes, the bot scrapes the upcoming race odds and applies this strict logic:
*   Scan the "Place" odds for all 4 runners.
*   **Condition A:** Are there ANY runners with Place odds $\ge 2.80$? (If NO -> Skip race).
*   **Condition B:** Are there MULTIPLE runners with Place odds $\ge 2.80$? (If YES -> choose the odd with the highest value, while recording what happen between the two, just in case we decide to see how the lesser perform in the future).
*   **Action:** If EXACTLY ONE runner has Place odds $\ge 2.80$, the bot calculates the stake via the Peak Ratchet formula and executes a single Place bet on that runner.

## 4. Technical Architecture
The bot must be built for 24/7 continuous deployment with minimal resource overhead.

*   **Language:** Python.
*   **Core Automation Library:** `playwright` (essential for bypassing SportyBet's main DOM and natively interacting with the cross-domain VirtusTec iframe)(not sure please recheck).
*   **Environment:** Headless Linux VPS (Ubuntu) and windows, any of them it should work with any system( currently we would work with windows, but we would be running in the cloud with linux.
*   ** we would most likely be using a vpn to connect to sportybbet as its a sportybet nigeria account and the vps is most certainly a london vps.
*   **Authentication:** Session state/cookie injection. The bot will load a saved `auth.json` file to bypass the login screen and avoid triggering Captchas/Cloudflare checks.
*   **Error Handling:** Strict `try/except` wrapping. If an element fails to load or the network drops, the bot must log the error, skip the bet, and sleep until the next 2-minute race cycle. 

## 5. Data Logging & True MDD Tracking
To ensure the divisor(e.g 10,50,100) is mathematically safe, the bot must log all actions to a local SQLite database or CSV. 

**Required logged data points per bet:**
*   Timestamp & Race ID
*   Target Runner & Target Odds
*   Peak Balance & Current Balance
*   Calculated Stake
*   Result (Win/Loss)

**MDD Calculation Goal:** 
The database must be queryable to track the **Maximum Drawdown (MDD) Trough**. We need to track the cumulative net deficit before a new peak is established (e.g., dropping 70% from the peak through intermittent wins and losses before recovering). This data will dictate if we need to adjust our divisor from 10 to 15 or 20 for safety.
yes, we need to also keep journal so we know how mdd be defined, but for now im ok with trying some few.