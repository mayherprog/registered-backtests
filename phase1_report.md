# phase1_report.md - Audit of trading-plan-hybrid.md
Run: 2026-07-18. Engine: code/engine.py (19/19 verification tests, code/test_output.txt, published before any result was read). Data and approximations: DATA_NOTES.md. The plan file was treated as frozen and is unmodified.

## VERDICT: FAIL
The written plan fails historical simulation on three independent grounds.

1. The entry triggers show no reliable edge. Mechanically reconstructed and run 2015-2026 with constant ~$500 sizing and no bankroll constraint (to isolate signal quality): 400 trades, 27.5% win rate, average -0.101R per trade, cumulative -$11,477. Every trigger is negative: reclaim50 (n=176, -0.11R), higher_low (n=132, -0.05R), xbi_breakout (n=18, -0.21R), xbi_support (n=74, -0.14R). Winners average +1.6R (time exits) to +2.2R (full targets), which meets the journal's 2:1 payoff test, but at a 27% win rate the arithmetic is negative. At zero transaction costs the system is approximately breakeven (-0.003R): the triggers generate zero gross edge, and spread costs plus premium richness make them net losers. The plan's value is its risk control, not its signals.

2. Under its own risk rules the plan does not survive any tested regime. Fresh $2,100 in each window, plan rules live: every one of six regimes (2015-17 chop, 2018 vol spike, 2020 crash, 2022 bear, 2023-24 recovery, 2025-26 momentum) tripped the -30% kill switch twice and reached the account-floor stop, ending between -52% and -60%. Time to first kill ranged from 7 sessions (Jan 2015) to 182 sessions (2020). Full-period run: dead by April 2015 at $943. Even the strongest bull window (2023-24, +112% with the kill switch disabled) ends at -56% under plan rules because an early drawdown trips the switch before the favorable stretch. Details and equity curves: sensitivity.md, charts/.

3. The plan's marquee setups cannot be executed at its own position sizes. A 0.50-delta, 45-60 DTE contract on Friday's closes costs approximately: SMH $4,000 (Aug 555C traded $40.15), SPY $1,970, QQQ $2,600, NVDA roughly $1,100-1,400, IWM $1,000-1,200, XBI $430-610. The plan's sizing band is $400-700 per position. Candidate setup #1 (SMH or NVDA calls) is unbuyable at 1 contract; of the whole stated universe only XBI fits the band today. This is arithmetic, not simulation, and it binds Monday morning.

Secondary findings.
- The thesis-invalidation exit as written is harmful: 154 invalidation exits averaging -0.67R; removing it improves P/L by $3.4k and win rate by 6 points. Entering 2 closes above the 50-day MA and exiting on 1 close below it is a whipsaw machine.
- The -50% premium stop is on the harmful edge: tightening to -35/-40% is clearly worse; near-ATM options routinely mark -35/-50% on ordinary 1-2% adverse moves. Stops fired at an average of -1.10R (worse than the theoretical -1.0R) because closes gap through the level.
- The FOMC/CPI blackout adds real money (removing it costs about $5.6k over 11.5 years). Keep it.
- Concurrency caps, sizing band vs fixed $500, and the IV-rank filter (halve mode) are decoration: no measurable EV effect. The sector cap barely binds because SPY/QQQ/SMH/IWM positions are one trade in beta terms anyway (that correlation is why -30% equity moves happen in a week).

## Engine 2: the futures gate (Monte Carlo, 10,000 paths per edge level, seeded)
Simulated trader: MES 1 lot, risk $20-40/trade, max 3 trades/day, disciplined -$100 daily stop, $1,000 bankroll, live kill at $670. Edge = per-trade expectancy in R.

| Edge | P(pass gate 50t/30d) | P(no kill in 6m live) | P(>=$1,000 at 6m) | Median final [p5, p95] |
|---|---|---|---|---|
| -0.15R | 0.117 | 0.005 | 0.002 | $647 [603, 668] |
| -0.10R | 0.201 | 0.040 | 0.021 | $649 [604, 670] |
| -0.05R | 0.326 | 0.189 | 0.128 | $654 [607, 1358] |
| 0.00R | 0.466 | 0.461 | 0.392 | $667 [613, 1942] |
| +0.05R | 0.603 | 0.739 | 0.700 | $1,481 [626, 2497] |
| +0.10R | 0.735 | 0.904 | 0.894 | $2,083 [653, 3054] |
| +0.15R | 0.838 | 0.966 | 0.966 | $2,643 [1,489, 3612] |

Reading: as a skill filter the gate is leaky. A trader with a clearly negative -0.10R edge passes 20% of the time; a marginally negative -0.05R trader passes 33%; a zero-edge trader passes almost half the time and then has a 54% chance of hitting the live kill switch within 6 months. As capital protection the system works: the kill switch bounds the median bad outcome near -$350, so the cost of a false pass is capped. Doubling the gate to 100 trades / 60 days roughly halves false passes at strongly negative edges while raising true passes (see candidates.md, C21). Separate defect: the gate requires average risk at or under 2% of $1,000 ($20/trade) while the live rules specify $20-40/trade (average $30). A trader following the live sizing on paper fails the gate's own arithmetic. One of the two numbers must change.

## The strongest argument against this verdict
This audit tested a mechanical caricature of the plan. The written triggers ("reclaim and hold of the 50-day", "higher low", "breakout") were reconstructed as literal daily-bar rules and fired about 35 times per year, but the plan clearly intends a discretionary layer: a human takes perhaps 10 of those 35, selected on catalysts (M&A tape, FOMC positioning, earnings), which no OHLCV backtest can reproduce. The five-question journal is precisely the selection mechanism this simulation lacks. If Mayher's judgment adds even +0.15R of selection edge over the mechanical baseline, the system is positive-EV and the risk architecture starts protecting a winner instead of slowly liquidating a loser. Three rebuttals keep the verdict at FAIL despite this. First, the burden of proof: nothing in the plan or its history demonstrates that selection edge exists; assuming it is exactly what the account floor exists to prevent. Second, even with a positive edge, the affordability contradiction (finding 3) still blocks the plan's primary expression, and that is not a modeling artifact. Third, the options pricing band (vol_mult 0.95-1.25) brackets the EV verdict: at the most favorable calibration the mechanical system reaches breakeven, not profit. FAIL here does not mean "Mayher cannot trade"; it means "these written rules, executed as written, lose money in expectation and the plan text needs the amendments in final_recommendation.md before capital goes behind it."

## What was not testable, and the direction of the error
All of these make live results worse than simulated, except the last.
- Option fills: modeled at mid plus a 2.5% half-spread. The plan tolerates spreads to 10% of mid; at 5% half-spread the per-trade EV roughly doubles its bleed (-0.19R).
- Intraday gap risk: stops fill at the daily close mark; real gaps through -50% fill lower. Stop exits already average -1.10R even at closes.
- Historical IV surfaces: paywalled; premiums are realized-vol-anchored Black-Scholes calibrated to the live 2026-07-17 surface (five contracts, ratios 1.05-1.13, m=1.08). All EV numbers carry a +/-10-20% premium-level band; headline conclusions were re-run at m=0.95 and 1.25 and survive.
- IV-rank filter: simulated with an RV-rank proxy; the real filter might behave differently around vol spikes.
- OI > 500 and strike-grid availability: not verifiable historically; assumed satisfied.
- The discretionary catalyst layer: excluded, and it is the one omission that could make live results better than simulated (addressed above).
