# Holdout decision - the 2023-2026 validation window

Decided 2026-07-28. Status: **NOT SPENT by the 12-strategy study. Sealed.**

Scope note, because a blanket "untouched" claim would be false: the Phase 2 options-candidate
search took one registered confirmatory look at this same date range in the original work.
See `ERRATA.md` E7. The window is unspent by the replication study and by Plan C; it is not
unseen by the project.

## What triggered a decision

The original registration (`strategies_registration.md`) reserved 2023-01-03 to 2026-07-17
as a validation window, to be spent once, by at most one finalist, where a finalist is a
strategy beating SPY on Sortino and max drawdown in at least 3 of 4 build-window folds.

On 2026-07-18 nothing qualified, so there was nothing to decide.

On 2026-07-28 a code review found the Sortino denominator was computed incorrectly
(`ERRATA.md`, E1). Corrected, two strategies clear that bar:

| | folds won | exposure | CAGR | SPY CAGR |
|---|---|---|---|---|
| S4 IBS QQQ | 3 of 4 | 24% | +10.7% | +10.1% |
| S5 Turn-of-month | 3 of 4 | 33% | +6.4% | +10.1% |

On a strict reading of the registered protocol, that is a trigger to spend the window.

## Decision

**The window is not being spent. It stays sealed.**

## Reasoning

1. **The passes are not yet interpretable.** Sortino at MAR=0 gives no penalty for periods
   spent out of the market, so a strategy holding cash most of the time scores well against
   a fully-invested benchmark without demonstrating any trading edge. Both qualifying
   strategies are low-exposure: S4 is invested 24% of the time, S5 33%.

2. **A control was registered and run, and they do not survive it.** `gate2_registration.md`
   was specified and committed before computation, and repeats the identical test against a
   benchmark matched to each strategy's own exposure. Under it, no strategy clears 3 of 4:
   S4 falls to 1 fold, S5 to 2. The strategies that are always invested are unchanged, which
   is the pattern the registration predicted in writing beforehand.

3. **Neither passer beats SPY on money.** S4 by 0.6 percentage points of CAGR, S5 trailing by
   3.7. Spending a one-shot resource to further examine a strategy that makes less money than
   the benchmark it is being compared to is a poor use of it.

4. **The holdout is scarce and the build window is not.** Re-screening on already-spent build
   data costs nothing. Running 2023-2026 can be done exactly once, and doing it on a candidate
   whose qualification is probably a measurement artifact wastes the cleanest out-of-sample
   test this project has left.

5. **The period is already one look down.** The Phase 2 options-candidate search took a
   single registered confirmatory look at 2023-2026 (see `ERRATA.md` E7). That was within its
   protocol, but it means the period is no longer unseen by this project: it is known to have
   been comparatively favourable for long-premium equity exposure. A look by the 12-strategy
   study would therefore be a second look at the same data by the same researcher, and is
   worth less than the registration assumed. That lowers the value of spending it now and
   raises the bar for what should be worth spending it on.

## What this decision is not

It is **not** a retroactive amendment to the registered bar. Gate 1 stands exactly as written,
it was cleared by S4 and S5, and that result is published in `strategies_report.md` and
`ERRATA.md` rather than buried. A reader who weighs the original registered gate more heavily
than a control specified afterwards is entitled to conclude that the window should have been
spent. The full disclosure needed to make that judgment, including the fact that the Gate 2
registration was not blind, is in `gate2_registration.md`.

## What would reopen this

Any one of:

- A strategy clears **both** Gate 1 and Gate 2 at 3 of 4 folds.
- Forward paper-tracking (see `ROADMAP.md`) produces a genuinely out-of-sample-in-time result
  for a candidate, making the held-out period a confirmation rather than a first look.
- A defect is found in Gate 2 itself that materially changes the exposure-matched result.

Any future look at 2023-2026 is logged here first, with its reason, before it is run.
