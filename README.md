# Virtual Ratchet: High-Water Mark Automated Betting System

A 24/7 headless automated betting bot implementing a quantitative High-Water Mark ("Peak Ratchet") position sizing engine on VirtusTec 4-runner Speedway markets (Bristol track).

---

## 1. Quick Start: Windows Desktop

### Step 1: Configure Settings in `.env`
Open the `.env` file in Notepad to customize your settings:
```env
# Execution Mode:
# 'PAPER' = Real-time simulation (tracks live odds & WebSocket results, journals True MDD without risking money)
# 'LIVE'  = Submits real bets to SportyBet betslip
BOT_MODE=PAPER

# Staking Parameters:
STARTING_BALANCE=1000.0
DIVISOR=10.0
TARGET_ODDS_MIN=2.80

# Performance:
HEADLESS=True
MUTE_AUDIO=True
BLOCK_MEDIA=True
```

### Step 2: One-Time Login (If Running LIVE)
1. Double-click `SportyBet_Login.bat` on your Desktop.
2. Log into SportyBet, check **"Keep me signed in"**, and press **[ENTER]**.
3. Your persistent session is permanently stored in `chrome_profile/`.

### Step 3: Run the Bot
Double-click `Run_Virtual_Ratchet.bat` on your Desktop.

### Step 4: View MDD & Strategy Analytics
Double-click `View_MDD_Report.bat` on your Desktop to inspect:
* High-Water Mark Peak achieved
* Maximum Drawdown (MDD) Trough percentage
* Strategy comparison: How the chosen highest odd performed vs the lesser candidate(s) $\ge 2.80$.

---

## 2. Linux VPS Deployment (Ubuntu / Debian)

### 1. Copy the project folder to your VPS
```bash
scp -r "C:\Users\Public\virtual ratchet" user@your_vps_ip:/home/user/virtual_ratchet
```

### 2. Run the automated setup script
```bash
cd /home/user/virtual_ratchet
chmod +x setup_linux.sh run_linux.sh
./setup_linux.sh
```

### 3. Run 24/7 in Background (tmux or screen)
```bash
tmux new -s ratchet
./run_linux.sh
# Press Ctrl+B then D to detach
```

---

## 3. Mathematical Formula Reference

Matching `RatchetEngine.mqh`:
$$\text{Next Stake} = \frac{\text{Peak Balance}}{\text{Divisor}}$$
$$\text{Forex } R\text{-Multiple} = \text{Decimal Odds} - 1.0$$
$$\text{Net PnL on Win} = \text{Stake} \times (\text{Odds} - 1.0)$$

* **Never Scales Down:** During a drawdown from 2,000 to 1,200 (Divisor = 10), stake remains 200.
* **All-In Floor:** If balance drops below 1R target stake, the bot goes all-in with the remaining balance.
* **Liquidated Halt:** If balance reaches 0, the bot immediately halts execution.
