# ERRATA

Review date 2026-07-28. Original project run 2026-07-18.

Seven defects found in a line-by-line review of `code/engine.py`, `code/strategies.py` and
`code/test_engine.py`, plus a review of the project's own claims about itself. Three are
material: one changed a headline conclusion, one changed every trade-level number in the
options audit, and one corrects a statement about the held-out data that was simply wrong.

Nothing in this document is a retraction of the method. The pre-registration, the fold
structure and the sealed validation window all held up. What follows is what the code got
wrong inside that structure, and what changed when it was fixed.

Original code is preserved in git at commit `45f7807`. Every number below is reproducible
by checking out that commit and re-running.

---

## E1. Sortino denominator measured the wrong thing (MATERIAL - changed a conclusion)

`perf()` computed the Sortino denominator as `statistics.pstdev` of the negative returns
only. That measures how spread out the losing periods are around their own mean. The
standard downside deviation is the root-mean-square shortfall below the minimum acceptable
return, averaged over ALL periods, with periods at or above the MAR contributing zero.

The two are not close, and they differ most for strategies that spend a lot of time flat:
under the old formula a day out of the market was excluded from the denominator entirely,
so a strategy holding cash got no credit for the risk it did not take, while still being
charged full dispersion on the days it did lose.

**Effect.** Every Sortino in the project was wrong. On the build window:

| | old | corrected |
|---|---|---|
| SPY benchmark | 0.65 | 0.75 |
| S4 IBS QQQ | 0.78 | 1.55 |
| S5 Turn-of-month | 0.50 | 0.90 |
| S3 RSI-2 SPY | 0.20 | 0.40 |
| S9 Gayed SSO 40w | 0.57 | 0.73 |
| S1 GEM | 0.09 | 0.09 |

**Consequence.** Two strategies crossed the registered 3-of-4 fold bar that had previously
missed it: S4 IBS QQQ (2 -> 3) and S5 Turn-of-month (1 -> 3). The original verdict of
"NO FINALIST, best was 2 of 4" was wrong as stated.

This is documented further in E6 and in `gate2_registration.md`.

## E2. perf() inferred bar frequency from array length (MATERIAL)

```python
n_per_year = 252 if len(v) > 600 else (52 if len(v) > 140 else 12)
```

A two-year fold of a daily strategy holds about 504 bars, which falls under the 600
threshold and was annualized as weekly. The heuristic was correct on the full eight-year
window and wrong on exactly the fold slices the robustness gate depends on:

```
fold 2015-2016  daily bars= 504  assumed 52/yr  -> years=9.69 (true 2.0)
fold 2019-2020  daily bars= 505  assumed 52/yr  -> years=9.71 (true 2.0)
```

Weekly strategies in a fold (~104 bars) were annualized as monthly.

**Fix.** `perf()` now takes a required `npy` argument, supplied from a `FREQ` table that
records each strategy's registered bar frequency.

**Effect in isolation.** Fold counts moved for two strategies (S1 GEM 1 -> 0, S9 Gayed
2 -> 1). It did NOT by itself cause the conclusion change in E1; separating the two fixes
shows E1 was responsible.

## E3. The portfolio simulation ran each day backwards (MATERIAL for the options audit)

In `run_backtest`, within one iteration: exits settled at the CLOSE of day i, and then
entries filled at the OPEN of day i. The open precedes the close.

Three consequences, all of which flattered the strategy:

1. Entries at the open were funded by cash from exits that had not yet settled. On a
   $2,100 bankroll carrying $400-700 positions this binds constantly; the run logs 987
   signals skipped for affordability.
2. A `max_positions` slot freed at the close was reused at that same morning's open.
3. The kill switch tripped on close equity and blocked entries that had already filled
   that morning.

**Demonstration.** Perturbing closes from 2016-05-03 onward, then comparing entries on or
before that date, which cannot legitimately depend on them:

```
OLD engine   entries<=cut: base=14 perturbed=13  -> CHANGED
     diff: ('XBI', '2016-05-03', 3.180635)
NEW engine   entries<=cut: base=14 perturbed=14  -> INVARIANT
```

That XBI position existed only because of money that had not arrived yet.

**Fix.** Entries now run first in each iteration, against cash, slots and kill state as of
the previous close. A position opened at the open of day t is now also marked, and can stop
out, at the close of day t.

**Effect on headline options-audit numbers:**

| | before | after |
|---|---|---|
| final equity | $943 | $866 |
| total return | -55.1% | -58.7% |
| average R per trade | -0.44 | -0.54 |
| trades | 12 | 10 |

The correction made the plan look worse. The audit's FAIL verdict is unchanged and better
supported: the pre-fix engine was giving the strategy money and slots it did not have.

## E4. Benchmark sampled at a different frequency from the strategy

Monthly and weekly strategies were compared against a daily SPY curve. Downside deviation
scales with sampling frequency, so those comparisons were not like-for-like.

**Fix.** `resample_eq()` downsamples the benchmark to each strategy's own bar frequency
before comparison.

**Effect.** S9 Gayed SSO 40w, 2 folds -> 1. No other strategy affected.

## E5. run_switcher docstring contradicted the code

The docstring claimed decisions were "applied from bar i+1 open". The code captures the
close(i-1) to close(i) return, which is market-on-close execution at the decision bar.

This is not lookahead: the decision uses only data through the close it executes at. But it
is a more favourable fill convention than the one documented, with no overnight gap. **The
code was not changed.** The docstring was corrected to describe what the code does, and the
discrepancy is disclosed here because the registration doc quotes the wrong convention.

## E6. A test asserted the wrong invariant

`test_engine.py` test 10 required at least 5 trades per calendar year. After the E3 fix the
account survives into 2017 and takes 3 trades there, and the test failed.

Diagnosis: the account is exhausted, not the engine misfiring. Equity falls from $2,100 to
$230 by mid-2017 and flatlines. The test passed before only because the pre-fix engine blew
the account up a year sooner, so 2017 never appeared in the counts at all.

**Fix.** The upper bound stays unconditional. The lower bound now applies only to years
starting with at least `max_positions x target_size`, i.e. enough to carry a full book. The
threshold is derived from config, not chosen to make the assertion pass. An intermediate
attempt using `size_min` ($400) still failed against 2017's $465 opening equity and was not
lowered further.

**Added.** A new regression test asserts that entries through a given day are invariant to
later closes. It fails against the pre-fix engine (see E3) and passes now. Suite: 20 tests,
all passing, up from 19.

## E7. The validation window was described as untouched. It had been used once.

Multiple documents in this project, including the README, stated that the 2023-2026
validation window had never been opened. That is false at the project level.

`charts/phase2_validation.json` contains results computed over 2023-01-03 to 2026-07-17 for
the Phase 2 options-candidate finalist (C12), committed in the original work at `077e810`:

```
finalist "C12 no-inval + take +150", folds_won 2
valid_base: final $925, dd 0.778, sortino -0.236, n 98, avgR +0.051
valid_c12 : final $968, dd 0.886, sortino -0.316, n 74, avgR +0.058
```

**This was not a protocol violation.** `code/phase2.py`'s registered guardrails state that
validation is "untouched by selection" and that the champion "is replaced only if finalist
beats it on VALIDATION". Phase 2 registered a single confirmatory look and took exactly one,
after selection was complete. C12 failed it and the champion was not replaced.

**But the consequence is real and was not disclosed.** The 2023-2026 period is no longer
pristine for this project. It is now known that the period was comparatively favourable for
long-premium equity exposure: average R per trade was positive on validation (+0.051 base,
+0.058 C12) while the same rules were negative across the build window. Any later use of that
period by the 12-strategy study would be a second look at the same data by the same
researcher, which is weaker evidence than a first look.

Scope of what remains unspent, stated precisely:

- The **12-strategy replication study** has not run anything against 2023-2026.
  `charts/strategies_valid.json` does not exist.
- The **Plan C** run did not open it either; only `planc_build.json` exists.
- The **Phase 2 options-candidate search** did open it, once, as registered.

The 2026-07-28 review did not re-open it. `phase2.py`'s `main()` runs the build window only
and writes `phase2_build.json`; the validation path is not invoked by it.

Corrected in README.md, holdout_decision.md and strategies_report.md.

---

## What this did to the project's conclusion

The original standing conclusion was that nothing cleared a pre-registered robustness bar
against SPY buy and hold.

After E1, that was **no longer true as written**: S4 IBS QQQ and S5 Turn-of-month both
cleared 3 of 4 folds. That result stands on the record and is reported in
`strategies_report.md`.

Investigating why raised a question about the metric rather than the strategies. Sortino at
MAR=0 rewards not being in the market, and both new passers are low-exposure: S4 is invested
24% of the time, S5 33%. They were being compared against SPY held 100% of the time.

A second gate controlling for exposure, and nothing else, was specified and committed in
`gate2_registration.md` at commit `6656889` **before** it was computed, with an explicit
disclosure that the registration was not blind. Its written prediction was that low-exposure
strategies would find Gate 2 materially harder and always-invested ones would be roughly
unchanged.

That prediction held. Under Gate 2, **no strategy clears 3 of 4**. S4 falls to 1, S5 to 2,
while the always-invested strategies (S1, S7, S8, S10) are unchanged.

**Both results are reported. Gate 1 is not deleted, amended, or retro-fitted.** The reading
supported by the evidence is that the Gate 1 pass is largely an artifact of comparing
part-time strategies to a full-time benchmark, not evidence of trading edge. That reading is
an interpretation, and a reader is free to weigh Gate 1 differently.

The 2023-2026 validation window remains unspent **by the 12-strategy study**:
`charts/strategies_valid.json` does not exist. It is not pristine at the project level; see
E7 above for the one registered look that Phase 2 took, and what that costs.
