# strategies_report.md - 12 published strategies, build-window test
Run 2026-07-18. **Revised 2026-07-28 after a code review; see ERRATA.md.** All Sortino values
and fold counts below differ from the 2026-07-18 version of this file, because the Sortino
denominator was being computed incorrectly (ERRATA E1). CAGR, drawdown and multiples are
unchanged. The original file is in git at commit `45f7807`.

Rules were registered in strategies_registration.md BEFORE any simulation.
Build window 2015-01-01..2022-12-30, costs 2bp/side, cash = SHY yield (monthly strategies) or 0.
Benchmark SPY buy & hold: CAGR 10.1%, max DD 33.7%, Sortino 0.75.

Two gates are reported. Neither replaces the other.
- **Gate 1** (registered 2026-07-18): beats SPY buy & hold on Sortino AND max drawdown in
  >= 3 of 4 two-year folds.
- **Gate 2** (registered 2026-07-28, `gate2_registration.md`): same test, but against a
  benchmark holding the strategy's own average exposure in SPY and the rest in the
  strategy's registered cash asset. Controls for capital exposure and nothing else.

| Strategy | CAGR | Max DD | Sortino | Multiple | Exposure | Gate 1 | Gate 2 |
|---|---|---|---|---|---|---|---|
| S12 BTC 40w trend | +85.5% | 64.0% | 2.39 | 82.2x | 0.66 | 0 | 0 |
| S4 IBS QQQ | +10.7% | 10.9% | 1.55 | 2.25x | 0.24 | **3** | 1 |
| S8 VAA-G4 | +4.7% | 17.4% | 0.92 | 1.44x | 1.00 | 2 | 2 |
| S5 Turn-of-month | +6.4% | 9.5% | 0.90 | 1.64x | 0.33 | **3** | 2 |
| S11 Vol-managed SPY | +8.0% | 25.6% | 0.78 | 1.85x | 0.88 | 2 | 2 |
| S9 Gayed SSO 40w | +12.5% | 29.5% | 0.73 | 2.57x | 0.79 | 1 | 0 |
| S2 GTAA-5 | +2.7% | 12.8% | 0.68 | 1.24x | 0.62 | 1 | 1 |
| S7 Accel dual momentum | +5.5% | 36.9% | 0.60 | 1.53x | 1.00 | 2 | 2 |
| S6 Halloween | +4.7% | 33.7% | 0.44 | 1.44x | 0.49 | 1 | 0 |
| S3 RSI-2 SPY | +2.7% | 18.4% | 0.40 | 1.24x | 0.24 | 2 | 0 |
| S10 HFEA | +7.6% | 67.5% | 0.34 | 1.81x | 1.00 | 0 | 0 |
| S1 GEM | +0.9% | 30.6% | 0.09 | 1.08x | 1.00 | 0 | 0 |
| SPY buy & hold | +10.1% | 33.7% | 0.75 | 2.16x | 1.00 | - | - |

Exposure is the mean fraction of capital in a risk asset across the build window.

## Gate 1 verdict: TWO PASSES
S4 IBS QQQ and S5 Turn-of-month both cleared 3 of 4 folds. This corrects the 2026-07-18
verdict of "NO FINALIST, best was 2 of 4", which was produced by the defective Sortino
denominator.

## Gate 2 verdict: NO PASSES
Against an exposure-matched benchmark, nothing clears 3 of 4. S4 falls to 1 fold, S5 to 2.
The strategies that are always invested (S1, S7, S8, S10) are unaffected, exactly as the
Gate 2 registration predicted before it was run.

## Reading the two together
S4 is invested 24% of the time and S5 33%. Sortino at MAR=0 credits periods spent flat,
because a day out of the market contributes no shortfall. Gate 1 compares those strategies
against SPY held 100% of the time, so a large part of their apparent risk-adjusted advantage
is bought with cash rather than earned by trading. Gate 2 removes that advantage and the
passes do not survive.

The interpretation supported by the evidence is that the Gate 1 passes are an exposure
artifact. That is an interpretation, not a fact: Gate 1 was the registered gate, it was
cleared, and Gate 2 was specified after that was known (disclosed in full in
`gate2_registration.md`). A reader who weighs the registered gate more heavily than a
later-added control would reasonably reach a different conclusion, and has the numbers to
do so.

Per protocol the 2023-2026 validation window has NOT been opened by this study and remains
unspent for it. It is not untouched at the project level: the Phase 2 options-candidate
search took one registered look at the same dates (ERRATA E7). The decision on whether the
Gate 1 passes trigger spending it is logged in holdout_decision.md; the decision is not to
spend it. Relaxing or rewriting Gate 1 after seeing results would be the exact overfitting
move this protocol exists to prevent, and has not been done: Gate 1 stands as registered and
its result is reported above.

## Honest observations (not selections)
- Several strategies beat SPY on the FULL build window on both metrics (S4 IBS: Sortino 1.55
  vs 0.75 with a third of the drawdown; S9 Gayed: higher CAGR and lower DD). S9 still fails
  the fold bar because its edge concentrates in specific regimes (nothing before 2019).
  Full-window wins with fold inconsistency is what regime luck looks like; that is why the
  bar is folds, not totals. S4 now passes Gate 1 on folds as well, and then fails Gate 2.
- The defensive allocators (S2 GTAA, S8 VAA) did their job in 2018 and 2020 (fold wins) and
  gave it back in 2015-16 chop and the 2022 dual stock/bond bear (VAA fold-4 Sortino -1.29).
  2022 broke every bonds-as-airbag design on the roster, including S1 GEM (+0.9% CAGR overall,
  its TLT escape hatch lost ~30% in 2022) and S10 HFEA (-67% fold-4 drawdown, matching its
  real-world 2022 blowup, a good realism check for the simulator).
- S12 BTC trend returned 82x, and still won zero folds because its drawdowns (49-64% per
  fold) never got under SPY's. It is a different risk class, not a better strategy. At the
  registered live cap (5-10% of account) its contribution would be meaningful but modest.
- S3 RSI-2 and S5 TOM: the classic short-term anomalies still trail SPY badly on CAGR (+2.7%
  and +6.4% against +10.1%), which is the decay you would expect post-publication. Their
  risk-adjusted scores look better than their returns purely because they are out of the
  market 76% and 67% of the time. S5 clears Gate 1 on that basis and fails Gate 2. Treat a
  high Sortino on a part-time strategy as a question, not an answer. S6 Halloween added
  nothing on either gate.

## Caveats binding these numbers
S9/S10/S12 simulated on weekly bars (registered approximation); S3/S4 assume market-on-close
fills on the signal bar; BTC data begins 2015-02 so S12's first fold is ~10 months short;
monthly ETF files carry a partial July-2026 bar (irrelevant to the build window); TLT monthly
series is resampled from weekly closes (registered). All strategy P/L is index-level: no
tracking error, no bid-ask beyond 2bp, no taxes. Real results would be modestly worse.

## Standing conclusion
Across 35 rulesets tested (23 audit-phase + 12 here), two have now cleared a pre-registered
robustness bar against SPY buy & hold: S4 IBS QQQ and S5 Turn-of-month, both under Gate 1.
Neither survives Gate 2's exposure control, and neither beats SPY on absolute return.

The passive-core plan stands, on the following reasoning: a strategy that wins on
risk-adjusted terms only because it sits in cash two-thirds of the time is not a reason to
stop holding the index, particularly at this account size where the cash leg earns nothing
in the simulation and commissions and taxes are not modelled.

S4 IBS, S5 TOM, S8 VAA and S11 vol-managed are candidates for FORWARD paper-tracking, which
costs nothing, touches no held-out data, and would build the only kind of evidence left:
out-of-sample-in-time. The validation window remains reserved and unspent.
