//+------------------------------------------------------------------+
//|                                               RatchetEngine.mqh  |
//|          Peak-Pegged Ratchet (Anti-Martingale) Position Sizing    |
//|          SHARED PORTFOLIO MODE — One state across all pairs       |
//+------------------------------------------------------------------+
#property copyright "CandleEntryEA_x"
#property strict

//+------------------------------------------------------------------+
//| CRatchetEngine — Shared portfolio ratchet for position sizing     |
//|                                                                   |
//| Core Formula:                                                     |
//|   riskDollars = anchorBalance × Peak / Divisor                    |
//|                                                                   |
//| After each trade close:                                           |
//|   balance += PnL / anchorBalance                                  |
//|   peak    = max(peak, balance)                                    |
//|                                                                   |
//| ALL EA instances share ONE state file. A win on any pair raises   |
//| the portfolio peak. The peak NEVER decreases — it is frozen       |
//| during drawdowns. Risk ONLY increases at new high-water marks.    |
//+------------------------------------------------------------------+
class CRatchetEngine
{
private:
    double   m_anchorBalance;    // Portfolio anchor $ (fixed reference, user-configured)
    double   m_balance;          // Current portfolio equity multiplier (starts 1.0)
    double   m_peak;             // Portfolio high-water mark multiplier (starts 1.0)
    double   m_divisor;          // Total divisor (D + B), user-configured
    string   m_stateFile;        // Shared persistence file path
    bool     m_initialized;      // Safety flag
    int      m_tradeCount;       // Total portfolio trades processed

public:
    CRatchetEngine()
    {
        m_anchorBalance = 0;
        m_balance = 1.0;
        m_peak = 1.0;
        m_divisor = 10.0;
        m_stateFile = "";
        m_initialized = false;
        m_tradeCount = 0;
    }

    //+------------------------------------------------------------------+
    //| Initialize the ratchet engine                                     |
    //| anchorBalance: 0 = use current AccountBalance()                  |
    //| divisor: total D+B value                                         |
    //|                                                                   |
    //| SHARED: All EA instances use the same state file.                |
    //| First EA to initialize creates the file. All others load it.     |
    //+------------------------------------------------------------------+
    void Init(double divisor, double anchorBalance = 0)
    {
        m_divisor = MathMax(divisor, 1.0);  // Safety: never divide by < 1

        // SHARED: Single portfolio state file for ALL pairs
        m_stateFile = "ratchet_state_portfolio.csv";

        // Try to load persisted state first
        if(LoadState())
        {
            Print(">> RATCHET ENGINE [", _Symbol, "]: Loaded SHARED portfolio state from ", m_stateFile);
            PrintState();
            m_initialized = true;
            return;
        }

        // No persisted state — fresh start (first EA to initialize creates it)
        if(anchorBalance > 0)
            m_anchorBalance = anchorBalance;
        else
            m_anchorBalance = AccountInfoDouble(ACCOUNT_BALANCE);

        m_balance = 1.0;
        m_peak = 1.0;
        m_tradeCount = 0;

        Print(">> RATCHET ENGINE [", _Symbol, "]: Fresh portfolio initialization");
        PrintState();
        SaveState();
        m_initialized = true;
    }

    //+------------------------------------------------------------------+
    //| Get the dollar risk for the next trade                            |
    //| riskDollars = anchorBalance x Peak / Divisor                     |
    //|                                                                   |
    //| SHARED: Re-reads the latest portfolio state before calculating   |
    //| so this EA always uses the most current peak, even if another    |
    //| pair just updated it.                                            |
    //+------------------------------------------------------------------+
    double GetRiskDollars()
    {
        if(!m_initialized)
        {
            Print("X RATCHET [", _Symbol, "]: Not initialized! Returning 0");
            return 0;
        }

        // Re-read shared state to get the latest peak from any pair's update
        RefreshFromSharedState();

        double risk = m_anchorBalance * m_peak / m_divisor;

        Print(">> RATCHET RISK [", _Symbol, "]: $", DoubleToString(risk, 2),
              " (Anchor=$", DoubleToString(m_anchorBalance, 2),
              " x Peak=", DoubleToString(m_peak, 6),
              " / Div=", DoubleToString(m_divisor, 2), ")");

        return risk;
    }

    //+------------------------------------------------------------------+
    //| Called after a trade closes — update shared portfolio state       |
    //|                                                                   |
    //| SHARED: Reads the latest state FIRST (another pair may have      |
    //| updated it since we last read), applies this trade's PnL,        |
    //| then writes back.                                                |
    //|                                                                   |
    //| pnl: the dollar profit/loss of the closed trade                  |
    //| (positive = win, negative = loss, includes commission+swap)      |
    //+------------------------------------------------------------------+
    void OnTradeClosed(double pnl)
    {
        if(!m_initialized)
        {
            Print("X RATCHET [", _Symbol, "]: Not initialized! Ignoring trade close.");
            return;
        }

        // CRITICAL: Read the latest shared state before modifying
        // Another pair may have closed a trade and updated the file
        RefreshFromSharedState();

        double oldBalance = m_balance;
        double oldPeak = m_peak;

        // Core update: balance changes proportional to anchor
        m_balance += pnl / m_anchorBalance;
        m_tradeCount++;

        // Update peak (high-water mark) — only moves up, never down
        if(m_balance > m_peak)
            m_peak = m_balance;

        // Log the update
        string outcomeStr = pnl >= 0 ? "WIN" : "LOSS";
        Print(">> RATCHET UPDATE [", _Symbol, " ", outcomeStr, " #", m_tradeCount, "]:",
              " PnL=$", DoubleToString(pnl, 2),
              " | Balance: ", DoubleToString(oldBalance, 6), " -> ", DoubleToString(m_balance, 6),
              " | Peak: ", DoubleToString(oldPeak, 6), " -> ", DoubleToString(m_peak, 6));

        if(m_balance > oldPeak)
            Print("   NEW PEAK! Risk will increase on next trade across ALL pairs.");
        else
            Print("   Peak frozen at ", DoubleToString(m_peak, 6), " -- risk unchanged across ALL pairs.");

        // Persist shared state
        SaveState();
    }

    //+------------------------------------------------------------------+
    //| Getters for UI / logging                                          |
    //+------------------------------------------------------------------+
    double GetBalance()       const { return m_balance; }
    double GetPeak()          const { return m_peak; }
    double GetAnchorBalance() const { return m_anchorBalance; }
    double GetDivisor()       const { return m_divisor; }
    int    GetTradeCount()    const { return m_tradeCount; }
    bool   IsInitialized()    const { return m_initialized; }

    double GetDrawdownPct() const
    {
        if(m_peak <= 0) return 0;
        return (1.0 - m_balance / m_peak) * 100.0;
    }

    double GetReturnPct() const
    {
        return (m_balance - 1.0) * 100.0;
    }

    //+------------------------------------------------------------------+
    //| Print current state to Experts log                                |
    //+------------------------------------------------------------------+
    void PrintState()
    {
        Print("   [SHARED PORTFOLIO STATE]");
        Print("   Anchor Balance: $", DoubleToString(m_anchorBalance, 2));
        Print("   Divisor (D+B):  ", DoubleToString(m_divisor, 2));
        Print("   Balance:        ", DoubleToString(m_balance, 6), "x (",
              DoubleToString(GetReturnPct(), 2), "%)");
        Print("   Peak:           ", DoubleToString(m_peak, 6), "x");
        Print("   Current Risk:   $", DoubleToString(m_anchorBalance * m_peak / m_divisor, 2));
        Print("   Trades:         ", m_tradeCount);
        if(m_balance < m_peak)
            Print("   Drawdown:       ", DoubleToString(GetDrawdownPct(), 2), "%");
    }

private:
    //+------------------------------------------------------------------+
    //| Refresh local state from shared file                              |
    //| Called before GetRiskDollars() and OnTradeClosed() to ensure     |
    //| this EA instance has the latest portfolio state                   |
    //+------------------------------------------------------------------+
    void RefreshFromSharedState()
    {
        if(!FileIsExist(m_stateFile))
            return;

        int handle = FileOpen(m_stateFile, FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
        if(handle == INVALID_HANDLE)
            return;

        // Skip header line
        if(!FileIsEnding(handle))
        {
            FileReadString(handle); FileReadString(handle); FileReadString(handle);
            FileReadString(handle); FileReadString(handle); FileReadString(handle);
        }

        // Read data line
        if(!FileIsEnding(handle))
        {
            double fileAnchor = StringToDouble(FileReadString(handle));
            double fileBalance = StringToDouble(FileReadString(handle));
            double filePeak = StringToDouble(FileReadString(handle));
            string fileDivisor = FileReadString(handle);
            int    fileTradeCount = (int)StringToInteger(FileReadString(handle));
            string ts = FileReadString(handle);

            FileClose(handle);

            // Validate before accepting
            if(fileAnchor > 0 && filePeak > 0)
            {
                m_anchorBalance = fileAnchor;
                m_balance = fileBalance;
                m_peak = filePeak;
                m_tradeCount = fileTradeCount;
            }
            return;
        }

        FileClose(handle);
    }

    //+------------------------------------------------------------------+
    //| Save state to shared file (survives restart, visible to all EAs) |
    //+------------------------------------------------------------------+
    void SaveState()
    {
        int handle = FileOpen(m_stateFile, FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_WRITE, ',');
        if(handle == INVALID_HANDLE)
        {
            Print("X RATCHET [", _Symbol, "]: Failed to save shared state to ", m_stateFile);
            return;
        }

        // Header
        FileWrite(handle, "anchor_balance", "balance", "peak", "divisor", "trade_count", "timestamp");
        // Data
        FileWrite(handle,
            DoubleToString(m_anchorBalance, 8),
            DoubleToString(m_balance, 8),
            DoubleToString(m_peak, 8),
            DoubleToString(m_divisor, 4),
            IntegerToString(m_tradeCount),
            TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS)
        );

        FileClose(handle);
    }

    //+------------------------------------------------------------------+
    //| Load state from shared file (returns true if loaded successfully)|
    //+------------------------------------------------------------------+
    bool LoadState()
    {
        if(!FileIsExist(m_stateFile))
            return false;

        int handle = FileOpen(m_stateFile, FILE_READ | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ',');
        if(handle == INVALID_HANDLE)
            return false;

        // Skip header line
        if(!FileIsEnding(handle))
        {
            FileReadString(handle); FileReadString(handle); FileReadString(handle);
            FileReadString(handle); FileReadString(handle); FileReadString(handle);
        }

        // Read data line
        if(!FileIsEnding(handle))
        {
            m_anchorBalance = StringToDouble(FileReadString(handle));
            m_balance       = StringToDouble(FileReadString(handle));
            m_peak          = StringToDouble(FileReadString(handle));
            // Note: divisor comes from input parameter, not from file
            // (user may want to change it between restarts)
            string fileDivisor = FileReadString(handle);
            m_tradeCount    = (int)StringToInteger(FileReadString(handle));
            string ts       = FileReadString(handle);

            FileClose(handle);

            // Validate
            if(m_anchorBalance <= 0 || m_peak <= 0)
            {
                Print("!! RATCHET [", _Symbol, "]: Invalid shared state file -- will reinitialize");
                return false;
            }

            Print("   State loaded from: ", ts);
            return true;
        }

        FileClose(handle);
        return false;
    }
};
//+------------------------------------------------------------------+
