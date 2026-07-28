# Gate 2 registration - exposure-matched robustness test

Registered: 2026-07-28. Status: REGISTERED, NOT YET RUN.

This document is written and committed BEFORE Gate 2 is computed against any data.
It is not revised after results are seen. If the specification below turns out to be
awkward or badly chosen, that is reported as a finding, not fixed retroactively.

## Why a second gate exists

Gate 1 (strategies_registration.md) asks: in each of four two-year folds, does the
strategy beat SPY on BOTH Sortino ratio and maximum drawdown, in at least 3 of 4?

On 2026-07-28 a defect was found in how the Sortino ratio was computed. The
denominator used the dispersion among losing periods only, instead of the standard
downside deviation (root-mean-square shortfall below the minimum acceptable return,
averaged over ALL periods). Correcting it exposed a property of the metric itself:

  Sortino at MAR = 0 rewards not being in the market. A period spent flat contributes
  a zero shortfall, so a strategy that holds cash most of the time has a small
  downside deviation by construction, regardless of whether its trading has any edge.

Gate 1 compares such a strategy against SPY held 100% of the time. That is not a
like-for-like comparison. A strategy in the market 30% of the time is being credited
for risk it did not take rather than for skill it demonstrated.

Gate 2 controls for that, and only that.

## What was known when this was written (full disclosure)

This registration is NOT blind, and pretending otherwise would defeat the point.

At the time of writing it was already known that, under the corrected Sortino,
S4 (IBS QQQ) and S5 (Turn-of-month) clear Gate 1 at 3 of 4 folds, and that both are
low-exposure strategies. The metric property above was identified while diagnosing
exactly that result.

Mitigations, in place of blindness:

1. The gate is specified here in complete, executable detail, with all thresholds
   fixed, before it is run against anything.
2. The control is derived from the named defect (unmatched capital exposure), not
   from the identity of any strategy. No threshold was chosen by checking what any
   particular strategy scores.
3. Results are reported in full regardless of outcome, including the case where
   Gate 2 changes nothing, and the case where it admits strategies Gate 1 rejected.
4. Gate 1 is NOT replaced or deleted. Both gates are reported side by side.

## Specification

**Exposure.** For strategy S at bar t, exposure x_t is the fraction of capital held in
a risk asset, in [0, 1]. Flat or fully-in-cash is 0.0. Fully invested is 1.0. Partial
allocations (GTAA-5 sleeves, vol-managed weight) take their actual fractional value.
HFEA is 1.0 throughout by registration, and its internal leverage is not rescaled.

For fold f, the fold exposure e_f is the mean of x_t over the bars in that fold.

**Benchmark.** For fold f, the exposure-matched benchmark earns, at each bar:

    r_bench,t = e_f * r_SPY,t + (1 - e_f) * r_cash,t

where r_SPY is sampled at the strategy's native frequency and r_cash is the SAME cash
series the strategy itself is registered to use: SHY total return for monthly
strategies, 0.0 for daily and weekly strategies. e_f is held constant across the fold.

**Fold win condition.** Unchanged in structure from Gate 1. A fold is won when BOTH:

    strategy Sortino    >  benchmark Sortino
    strategy max drawdown  <  benchmark max drawdown

**Pass condition.** Gate 2 is passed when at least 3 of the 4 folds are won.

**Sortino.** MAR = 0. Downside deviation = sqrt(mean(min(r - MAR, 0)^2)) over all
periods, annualized by sqrt(npy) at the strategy's native bar frequency. This is the
corrected definition adopted 2026-07-28.

**Folds.** Unchanged: 2015-2016, 2017-2018, 2019-2020, 2021-2022.

## Scope, and what stays sealed

Gate 2 is applied to the BUILD window (2015-01-01 to 2022-12-30) ONLY.

The validation window (2023-01-03 to 2026-07-17) remains UNSPENT. Nothing in this
registration authorizes touching it. Running a re-screen on already-spent build data
costs nothing; the holdout is a separate decision, to be logged separately, and it has
not been made.

## Predicted outcome

Recorded before running, so the prediction can be scored:

Low-exposure strategies (S3, S4, S5) should find Gate 2 materially harder than Gate 1,
because their benchmark drops toward their own exposure level and loses most of the
drawdown advantage they were winning on. Always-invested strategies (S1, S6, S7, S8,
S9, S10, S12) should be close to unchanged, since e_f near 1.0 makes the matched
benchmark nearly identical to SPY. S11 (vol-managed) is the uncertain one: its weight
floats, so its benchmark moves with it.

If S4 and S5 still pass Gate 2, that is evidence their edge is not purely a
low-exposure artifact, and it is a real result.
