# sensitivity.md - one rule at a time, 2015-01-01 to 2026-07-17
Two lenses. EV lens: kill switch off, constant ~$500 sizing, unlimited cash; isolates per-trade economics (n, avg R, win rate, total P/L; 1R = 50% of position cost). Plan lens: full plan rules, $2,100; shows what the account actually experiences (final equity, max DD, kill trips). Engine: code/engine.py, test suite 19/19 (code/test_output.txt). Charts: charts/equity_*.png (6 regime equity curves).

| Variant | n | avg R | win | Total P/L | Plan final | Plan DD | Kills |
|---|---|---|---|---|---|---|---|
| BASE (plan as written) | 400 | -0.101 | 27.5% | -11,477 | $943 | 61% | 2 |
| stop -35% | 437 | -0.193 | 23.8% | -16,095 | $835 | 61% | 2 |
| stop -40% | 426 | -0.174 | 24.6% | -15,862 | $835 | 61% | 2 |
| stop -60% | 390 | -0.088 | 28.5% | -11,509 | $854 | 65% | 2 |
| no invalidation exit | 343 | -0.085 | 33.8% | -8,098 | $853 | 61% | 2 |
| concurrency 2 | 333 | -0.100 | 27.0% | -8,716 | $990 | 53% | 2 |
| concurrency 4 | 435 | -0.096 | 28.0% | -10,993 | $947 | 64% | 2 |
| fixed $500 size | 405 | -0.102 | 27.7% | -10,644 | $802 | 67% | 2 |
| blackout off | 434 | -0.134 | 26.3% | -17,031 | $671 | 68% | 2 |
| IV filter off | 400 | -0.099 | 27.8% | -10,574 | $943 | 61% | 2 |
| IV filter skip (not halve) | 293 | -0.155 | 24.6% | -11,760 | $873 | 63% | 2 |
| [pricing] vol_mult 0.95 | 441 | -0.007 | 29.7% | -2,352 | $536 | 79% | 2 |
| [pricing] vol_mult 1.25 | 352 | -0.195 | 23.9% | -18,413 | $884 | 58% | 2 |
| [cost] zero spread | 400 | -0.003 | 28.5% | -1,018 | $704 | 67% | 2 |
| [cost] 5% half-spread | 400 | -0.193 | 26.5% | -21,936 | $944 | 55% | 2 |

## What materially changes outcomes
1. Transaction costs and premium richness. At zero spread the system is near breakeven gross (-0.003R); at the plan's own 10%-of-mid spread tolerance (5% half-spread) it loses -0.193R per trade. The strategy's economics live entirely inside the bid-ask spread. Same story for the pricing band: if real premiums run 12% cheaper than the calibrated model (vol_mult 0.95), EV is roughly zero; 16% richer and it is strongly negative. Conclusion: the written triggers produce approximately zero gross edge, and any real-world friction makes them net losers.
2. Stop placement, in one direction only. Tightening the premium stop to -35/-40% is clearly harmful (-0.17 to -0.19R): near-ATM options on 1-2% adverse underlying moves routinely mark down 35-50%, so tight premium stops convert noise into realized losses. Loosening to -60% is a wash. The -50% stop is defensible but sits on the harmful side's edge.
3. The thesis-invalidation exit. Dropping it improves total P/L by $3.4k and lifts win rate 27.5% -> 33.8%. Entering two closes above the 50-day MA and exiting on any close back below it guarantees whipsaw: 154 invalidation exits averaged -0.67R each. The rule as written fights the entry it is paired with.
4. The FOMC/CPI blackout. One of the only rules that adds money: removing it costs about $5.6k over the period (avg R -0.101 -> -0.134). Keep it.

## What is decoration
Concurrency cap (2 vs 3 vs 4 changes DD, not EV), fixed vs banded sizing, and the IV-rank filter in halve mode (indistinguishable from off; in skip mode it is harmful because the RV-rank proxy skips post-selloff entries that are the strategy's best trades).

## The kill switch (regime evidence, charts/equity_*.png)
| Regime | Plan: return / DD / kills / sessions to 1st kill | Kill-off diagnostic: return |
|---|---|---|
| 2015-2017 chop | -55% / 61% / 2 / 7 | -91% |
| 2018 vol spike | -52% / 77% / 2 / 57 | -84% |
| 2020 crash+recovery | -60% / 84% / 2 / 182 | -36% |
| 2022 bear | -55% / 55% / 2 / 43 | -81% |
| 2023-24 recovery | -56% / 78% / 2 / 47 | +112% |
| 2025-26 momentum | -60% / 60% / 2 / 35 | -90% |
Every regime trips the kill switch to the account floor. In five of six regimes the kill switch correctly prevented deeper losses (it capped -80/-90% diagnostics at about -55%). In 2023-24 it locked in -56% on a path that would have finished +112%. That is the kill switch doing its job: given a near-zero-EV strategy with 60-90% drawdown paths, capping the left tail is worth surrendering the occasional right tail. The problem is not the switch; it is the expectancy of what is being switched off.

## Caveats binding these numbers
Modeled at daily closes with BS-approximated premiums (see DATA_NOTES.md): stop fills flattered (no intraday gaps), spreads modeled as a flat fraction, IV dynamics proxied by realized vol. Affordability uses split/dividend-adjusted prices: exact for 2026, progressively distorted backward (verdicts on early-year affordability are unaffected because premiums were far below the $700 cap either way). The mechanical triggers exclude the discretionary catalyst layer the plan assumes; results measure the written rules, not the trader.
