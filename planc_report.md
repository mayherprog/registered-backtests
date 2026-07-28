# planc_report.md - Pre-registered Plan C test, 2026-07-18
Design was registered in chat, parameters fixed before any run (see code/planc.py header).
Two designs reported as registered: A (core only) and C (core + satellite). Build window
2015-01-01 to 2022-12-30. Benchmark: SPY buy & hold. Win condition (registered): beat SPY
on risk-adjusted return AND max drawdown, or the answer is "hold SPY."

## Build-window results
| | Final ($ from base) | CAGR | Max DD | Sortino |
|---|---|---|---|---|
| A core only ($1,600) | $2,430 (+52%) | 5.4% | 41.3% | 0.31 |
| Satellite ($500) | $45 (-91%) | -25.9% | 96% | -0.27 |
| C combined ($2,100) | $2,476 (+18%) | 2.1% | 59.7% | 0.10 |
| SPY buy & hold ($2,100) | $4,504 (+114%) | 10.0% | 33.7% | 0.64 |

VERDICT: FAIL on the build window. C (and A) lose to SPY on return, drawdown, and Sortino.
The 2023-2026 validation window was NOT opened; the single registered look remains unspent
for any future, genuinely new design.

## Why it failed (diagnostics, logged as diagnostics)
1. The -15% core kill sold at market lows seven times (2015-08-31, 2015-09-25, 2018-12-04,
   2019-06-03, 2020-03-09, 2022-01-25, 2022-11-03), each time re-entering higher. A -15%
   equity kill is mis-calibrated for an asset class with routine 15-35% drawdowns.
2. But the kill was not the main problem: with the kill disabled (diagnostic run,
   charts/planc_diagnostic.json), the core still made only +38% (CAGR 4.1%, DD 38.3%,
   Sortino 0.21) vs SPY +114%. The rotation itself underperformed: top-2-of-5 momentum
   among five highly correlated equity ETFs, with MA200 exits, systematically missed
   V-shaped recoveries (2016, 2019, 2020, 2023-era analogues) and paid the timing cost
   without collecting enough crash protection.
3. The satellite's four AND-conditions (trend up, RV-rank < 40%, contract <= $500,
   outside blackout) were rarely simultaneously true after 2016, and its $500 bankroll
   had no refill rule: it bled out on 10 trades by mid-2016 (-$455) and sat dead for six
   years. Structurally, small-account long options keep failing for the same reason
   Engine 1 failed: spread + theta on near-ATM premium consumes any weak edge.

## Standing conclusion across both phases
Twenty-one Phase 2 candidates, plus two pre-registered Phase 3 designs, all fail to beat
either zero (options engines) or SPY buy & hold (share engines) on the build era. The
evidence consistently supports: passive core exposure beats every tested active ruleset
at this account size; the futures gate (doubled) remains the legitimate path for
developing and verifying discretionary edge with bounded cost; any options sleeve should
be treated as pre-accepted lottery budget, not expectancy.

Multiplicity note: with 23 total rulesets now examined against this history, any future
backtest "winner" on the same data needs an extraordinary margin to be believable.
