# strategies_registration.md
Registered 2026-07-18 BEFORE any simulation run. No parameter below changes after results exist.
Build window 2015-01-01..2022-12-30 (four folds: 2015-16, 2017-18, 2019-20, 2021-22).
Validation window 2023-01-03..2026-07-17, spent once, by at most one finalist.
Benchmark: SPY buy & hold. Costs: 2bp slippage per side, zero commission. Idle cash earns the
SHY total return (monthly strategies) or 0 (daily strategies; conservative, disclosed).
Finalist rule: must beat SPY risk-adjusted (Sortino) AND on max drawdown in >= 3 of 4 folds;
ties broken toward fewer rules. Post-2023-published strategies were removed from the roster
by Mayher's decision (untestable by backtest; see chat log).

Data granularity approximations (registered up front):
- S1, S2, S7, S8 run on MONTHLY closes (as published).
- S3, S4, S5, S6, S11 run on DAILY closes (existing audited daily data).
- S9, S10, S12 run on WEEKLY closes because full daily history for SSO/UPRO/TMF/TLT/BTC
  exceeds the ingestion budget; 200-day MA becomes 40-week MA, quarterly rebalance = every
  13 weeks, 200-day BTC MA = 40-week. Published robustness sections of the respective papers
  cover these horizons. Flagged in every result table.

## S1 GEM dual momentum (Antonacci 2013) [monthly]
At each month-end: r12(SPY), r12(EFA), r12(SHY) = 12-month total returns.
If max(r12 SPY, r12 EFA) > r12(SHY): hold the higher of SPY/EFA. Else hold TLT.
One position, whole account.

## S2 GTAA-5 (Faber 2007) [monthly]
Sleeves SPY, EFA, TLT, GLD, VNQ at 20% each. At month-end: sleeve invested if monthly close
> 10-month SMA of monthly closes, else that 20% to cash (SHY return).

## S3 RSI-2 (Connors 2008) [daily, SPY]
RSI(2) on daily closes. Enter long at close when RSI2 < 5 AND close > 200d SMA.
Exit at close when close > 5d SMA. All-in position (100% of sleeve).

## S4 IBS (Pagonidis ~2014) [daily, QQQ]
IBS = (close - low) / (high - low). Enter long at close when IBS < 0.20 AND close > 200d SMA.
Exit at close when IBS > 0.80. All-in.

## S5 Turn-of-month [daily, SPY]
Long from the close of the 4th-to-last trading day of each month through the close of the
3rd trading day of the next month. Cash otherwise.

## S6 Halloween (Bouman-Jacobsen 2002) [daily, SPY]
Long SPY from the last October close through the last April close. Cash May-October.

## S7 Accelerating Dual Momentum (EngineeredPortfolio 2018) [monthly]
Score = (r1 + r3 + r6)/3 on SPY and SCZ. If max score > 0: hold higher scorer. Else TLT.

## S8 VAA-G4 (Keller-Keuning 2017) [monthly]
Momentum score 13612W: (12*r1 + 4*r3 + 2*r6 + 1*r12) on SPY, EFA, EEM, AGG (offensive)
and SHY, IEF, LQD (defensive). If ALL four offensive scores > 0: hold the top offensive.
Else: hold the top defensive.

## S9 Leverage for the Long Run (Gayed 2016) [weekly]
Hold SSO (2x S&P) while SPY weekly close > 40-week SMA of SPY weekly closes; else cash.
(2x chosen over 3x per the paper's risk-adjusted sweet spot at longer MAs.)

## S10 HFEA (Bogleheads 2019) [weekly]
55% UPRO / 45% TMF, rebalanced every 13 weeks. No timing. Buy and hold otherwise.

## S11 Volatility-managed SPY (Moreira-Muir 2017) [daily]
Weight_t = min(1, 0.15 / RV21_t) where RV21 = annualized 21-day realized vol of SPY,
recomputed and applied at each month-end close (monthly rebalance of the weight; avoids
daily churn; paper's monthly implementation). Remainder in cash.

## S12 BTC 40-week trend [weekly]
Hold BTC while weekly close > 40-week SMA, else cash. Informational sizing note: live
allocation would be capped at 5-10% of account; simulated standalone on its own sleeve.

Multiplicity note: 12 strategies here + 23 prior rulesets = 35 total looks at this history.
Fold-consistency selection and the untouched validation window are the only defenses; a
marginal build-window win is noise by construction at this count.

---

## Appended 2026-07-28 (registration above is UNCHANGED)

Nothing above this line has been edited. A registration that gets rewritten after results
exist is not a registration, so corrections are recorded here and in ERRATA.md instead.

1. **The Sortino ratio used to score this registration was computed incorrectly.** The
   denominator measured dispersion among losing periods rather than downside deviation over
   all periods. See ERRATA E1. Corrected, S4 IBS QQQ and S5 Turn-of-month clear the
   "Finalist rule" stated above at 3 of 4 folds. The 2026-07-18 report claimed no strategy
   cleared it; that claim was wrong and is withdrawn.

2. **The execution convention quoted above for monthly and weekly strategies is wrong.**
   This document and the code docstring both described "decide at bar t close, execute at
   bar t+1 open". The code has always captured the close(t) to close(t+1) return, i.e.
   market-on-close execution at the decision bar. This is not lookahead, but it is a more
   favourable fill assumption than the one registered. The code was NOT changed; the
   discrepancy is disclosed. See ERRATA E5.

3. **A second gate exists.** `gate2_registration.md`, registered and committed 2026-07-28
   before being computed, repeats the finalist rule against an exposure-matched benchmark.
   It does not replace the rule above. Both results are reported in strategies_report.md.

4. **The validation window remains unspent.** The finalist rule firing is a trigger to
   spend it; that decision is logged as open in PLAN_STATE.md and has not been made.
