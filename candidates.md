# candidates.md - Phase 2 log
Budget: 24 candidates maximum. Used: 21. Every ruleset tested is listed, including discards. Because 21 variants were examined, any apparent winner must be discounted for multiplicity; at this sample size a spurious +0.1R edge appears by chance easily.

Build window: 2015-01-01 to 2022-12-30. Validation window: 2023-01-03 to 2026-07-17, touched exactly once, after finalist selection.

Metrics. "Plan lens" = full plan rules, fresh $2,100 (final equity, max drawdown, kill trips, Sortino of daily equity). "EV lens" = kill switch off, constant ~$500 sizing, no cash constraint (isolates per-trade economics: trade count, average R where 1R = 50% of position cost, total P/L). All runs share the audited engine (code/engine.py, 19/19 tests passing).

BASE (plan as written), build window: final $943, DD 61.3%, 2 kill trips, Sortino -0.075, 302 trades, avg R -0.154, total P/L -$13,294.

## Candidate table (build window only)

| # | Candidate | Cat | +Rules | Final | DD | Sortino | avgR | TotPnl | n | Verdict vs BASE |
|---|---|---|---|---|---|---|---|---|---|---|
| C01 | stop -60% | risk | 0 | $854 | 65% | -0.09 | -0.131 | -12,851 | 295 | Discard: better avgR, worse DD/Sortino |
| C02 | no-invalidation exit | risk | 0 | $853 | 61% | -0.07 | -0.155 | -11,575 | 261 | Keep for combos: -$1.7k less bleed |
| C03 | vol-scaled size (ref 20%) | risk | 1 | $943 | 61% | -0.07 | -0.152 | -13,105 | 302 | Discard: no material change, +1 rule |
| C04 | concurrency 2, sector cap 1 | risk | 0 | $990 | 53% | -0.08 | -0.166 | -11,170 | 241 | Best DD (53%); kept as risk note |
| C05 | drawdown throttle 15% | risk | 1 | $928 | 62% | -0.08 | -0.146 | -13,519 | 302 | Discard: +1 rule, no benefit |
| C06 | blackout extended to 2d | risk | 1 | $928 | 62% | -0.08 | -0.156 | -12,693 | 280 | Discard: +1 rule, no benefit over 1d |
| C07 | stop -60 + no-inval | risk | 0 | $873 | 64% | -0.08 | -0.093 | -8,260 | 238 | Runner-up: best avgR |
| C08 | profit take +75% | exit | 0 | $633 | 73% | -0.09 | -0.171 | -14,556 | 309 | Discard: worst final. Early banking hurts |
| C09 | profit take +150% | exit | 0 | $939 | 63% | -0.07 | -0.140 | -12,487 | 295 | Mild help; folded into C12 |
| C10 | time stop 25 sessions | exit | 0 | $922 | 62% | -0.08 | -0.164 | -15,567 | 311 | Discard: cuts winners that need time |
| C11 | breakeven trail | exit | 1 | $967 | 60% | -0.09 | -0.177 | -15,978 | 321 | Discard: whipsaws winners out |
| C12 | no-inval + take +150% | exit | 0 | $853 | 61% | -0.07 | -0.100 | -7,801 | 253 | FINALIST (least-bad, 0 added rules) |
| C13 | reclaim buffer 1% | entry | 0 | $880 | 64% | -0.08 | -0.137 | -11,528 | 282 | Discard: minor |
| C14 | reclaim hold 3 | entry | 0 | $983 | 59% | -0.07 | -0.155 | -12,939 | 290 | Discard: minor |
| C15 | trend filter MA200 | entry | 1 | $943 | 61% | -0.07 | -0.179 | -12,602 | 236 | Discard: fewer trades, worse avgR |
| C16 | higher-low only | entry | 0 | $927 | 69% | -0.10 | -0.158 | -8,475 | 175 | Discard: less bleed only via fewer trades |
| C17 | XBI breakout 55d | entry | 0 | $864 | 64% | -0.09 | -0.142 | -11,349 | 292 | Discard: minor |
| C18 | C02 + C15 | combo | 1 | $853 | 61% | -0.07 | -0.183 | -10,968 | 210 | Discard: penalty not cleared |
| C19 | C02 + C03 + C15 | combo | 2 | $853 | 61% | -0.07 | -0.182 | -11,266 | 210 | Discard: penalty not cleared |
| C20 | C02 + C15 + take150 | combo | 1 | $853 | 61% | -0.07 | -0.100 | -5,917 | 205 | Discard by complexity penalty (below) |
| C21 | Engine 2 gate 100 trades/60 days | risk | 0 | see below | | | | | | Kept as Engine 2 amendment evidence |

## Complexity penalty (stated formula)
A candidate with k more structural rules than a simpler one must exceed the simpler one's build Sortino by 0.10 x k, otherwise the simpler one wins. Parameter changes to existing rules count as 0 added rules; new mechanisms (throttle, trail, trend filter, vol sizing) count as 1 each.
- C20 (+1 rule, Sortino -0.07) vs C12 (0 added, Sortino -0.07): needs -0.07 >= -0.07 + 0.10. Fails. C12 wins despite C20's better total P/L.
- C18/C19 fail the same test against C02/C12.

## Finalist: C12 (drop invalidation exit, profit take +150% with half-off)
Walk-forward, four 2-year build folds, EV-lens avg R (and total P/L):
| Fold | BASE avgR / P&L | C12 avgR / P&L | Winner |
|---|---|---|---|
| 2015-16 | -0.338 / -8,921 | -0.374 / -7,752 | BASE on avgR (C12 on P/L) |
| 2017-18 | -0.047 / -1,046 | -0.187 / -3,728 | BASE |
| 2019-20 | +0.126 / +2,322 | +0.408 / +6,217 | C12 |
| 2021-22 | -0.388 / -7,055 | -0.338 / -5,598 | C12 |
C12 wins 2/4 folds on avg R (3/4 on total P/L). Requirement was >= 3/4 on avg R. FAILS walk-forward.

Validation window (opened once, after selection):
| | Final | DD | Kills | Sortino | avgR | TotPnl | n |
|---|---|---|---|---|---|---|---|
| BASE | $925 | 77.8% | 2 | -0.236 | +0.051 | +1,567 | 98 |
| C12 | $968 | 88.6% | 2 | -0.316 | +0.058 | +1,697 | 74 |
C12 does NOT beat BASE on max drawdown (88.6% vs 77.8%) or Sortino. Win condition (beat on risk-adjusted return AND max DD) FAILS.

## C21: Engine 2 gate extension (10,000 Monte Carlo paths per cell)
| Edge | P(pass 50 trades/30d) | P(pass 100 trades/60d) |
|---|---|---|
| -0.15R | 0.117 | 0.056 |
| -0.10R | 0.205 | 0.134 |
| -0.05R | 0.330 | 0.281 |
| 0.00R | 0.471 | 0.468 |
| +0.05R | 0.604 | 0.674 |
| +0.10R | 0.733 | 0.834 |
| +0.15R | 0.835 | 0.929 |
Doubling the gate roughly halves the false-pass rate for clearly negative-edge traders while improving true-pass rates for positive-edge traders. This is the only Phase 2 change that clears its evidence bar, and it costs only time, not money.

## Phase 2 verdict
No Engine 1 candidate replaces the current plan. The search found variants that bleed slower (C07, C12, C20 family), but none with positive expectancy on the build window, none clearing walk-forward consistency, and none beating the plan on the validation window's win condition. Selecting the least-negative of 21 variants would be curve-fitting noise. The honest conclusion stands: the written entry triggers carry no reliable edge, so no exit/sizing arrangement on top of them produces a validated positive-EV ruleset.
