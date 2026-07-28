# Registered Backtests

A pre-registered replication study of 12 published trading strategies, run by a college student, in the open, with the discipline most backtests skip.

**Headline result: nothing survives once capital exposure is controlled for.** Across 35 rulesets tested against a bar registered before any simulation ran, two strategies cleared the original bar and neither survived a follow-up control. The held-out validation window (2023-2026) has never been opened by this study. I kept my passive portfolio.

**This repo was revised on 2026-07-28 after a code review found seven defects, three of them material, one of which changed a headline conclusion.** That review, what it broke, and what it did not, is in [`ERRATA.md`](ERRATA.md). If you only read one file, read that one.

If a study that corrects itself in public sounds more interesting than one that doesn't, this repo is for you.

## Why pre-registration

Every retail backtest you've ever seen was tuned after looking at the results. Pick the window that flatters the strategy, relax the threshold that kills it, quietly drop the variants that didn't work. None of it feels like cheating from the inside, and all of it produces strategies that die the moment real money touches them.

The fix is the one experimental science landed on: write down the rules first. Before running anything, [`strategies_registration.md`](strategies_registration.md) fixed:

- every strategy's exact rules, as published, with no parameter tuning
- the build window (2015-2022, four 2-year folds) and a held-out validation window (2023-2026) that at most one finalist would ever touch, once
- costs (2bp slippage per side), idle-cash treatment, and data-granularity approximations
- the pass bar: beat SPY on Sortino ratio **and** max drawdown in at least 3 of 4 folds
- a multiplicity note: with 35 total rulesets examined, a marginal build-window win is noise by construction

After the run, nothing changes. The bar does not move because the results were disappointing, and it does not move because they were encouraging either. Both directions are tested here.

## The strategies

GEM dual momentum (Antonacci), GTAA-5 (Faber), RSI-2 (Connors), IBS mean reversion, turn-of-month, Halloween effect, Accelerating Dual Momentum, VAA-G4 (Keller-Keuning), Leverage for the Long Run (Gayed), HFEA, volatility-managed SPY (Moreira-Muir), and a BTC 40-week trend rule. Full specifications in the registration doc.

## Results

Two gates, both reported. Neither replaces the other.

**Gate 1** (registered 2026-07-18) compares each strategy to SPY buy-and-hold. Two strategies clear it: S4 IBS QQQ and S5 Turn-of-month, at 3 of 4 folds.

**Gate 2** ([`gate2_registration.md`](gate2_registration.md), registered and committed 2026-07-28 *before* being computed) runs the identical test against a benchmark holding each strategy's own average exposure in SPY and the rest in cash. Under it, nothing clears 3 of 4. S4 falls to 1 fold, S5 to 2.

The reason is that the Sortino ratio gives no penalty for sitting in cash: a day out of the market contributes no downside. S4 is invested 24% of the time and S5 33%, and both were being compared against SPY held 100% of the time. A large part of their apparent risk-adjusted advantage was bought with cash rather than earned by trading. Neither beats SPY on absolute return.

That is an interpretation, not a fact. Gate 1 was the registered gate, it was cleared, and Gate 2 was specified after that was known. The registration document says so explicitly, because a control written after seeing the result it controls for is worth less than a blind one and pretending otherwise would defeat the point.

Full tables in [`strategies_report.md`](strategies_report.md).

## The validation window

Sealed for this study. `charts/strategies_valid.json` does not exist; the 12 strategies have never been run against 2023-2026.

It is **not** pristine at the project level, and an earlier version of this README wrongly said it was. A separate component of the project, the Phase 2 options-candidate search, registered a single confirmatory look at that period and took it. Its finalist failed. The full accounting, including what that costs in terms of a second look being weaker than a first, is [`ERRATA.md`](ERRATA.md) E7.

Under a strict reading of the protocol, the Gate 1 passes were a trigger to spend the window on S4 and S5. The decision not to, the reasoning, and what would reopen it are written down in [`holdout_decision.md`](holdout_decision.md) rather than left implicit.

## Reproducing

The core has no third-party dependencies.

```bash
python3 code/test_engine.py        # 20 tests
python3 code/strategies.py build   # 12 strategies, Gate 1 and Gate 2
python3 code/engine.py             # the options-plan audit
```

Only `code/regimes.py` needs anything installed; see [`requirements.txt`](requirements.txt). Data provenance, cross-validation and known approximation error are documented in [`DATA_NOTES.md`](DATA_NOTES.md).

## A note on this repo's history

This is a clean repository. The work was done in a private one, and the git history there is what establishes that the Gate 2 registration was committed before Gate 2 was computed. That ordering is load-bearing for the claim, and reconstructing a fake commit history here to imitate it would have been worse than saying this plainly.

## Caveats

Index-level P/L: no tracking error, no taxes, fills at close on signal bars, some strategies simulated at weekly granularity (registered up front). The options-audit component prices contracts from a calibrated Black-Scholes model because historical implied-volatility surfaces are paywalled, carrying an estimated 10-20% uncertainty documented in `DATA_NOTES.md`. Real results would be modestly worse than shown. The caveats section of the report is not fine print, it is part of the result.

## Not investment advice

This is a research study, not advice, not a recommendation to trade anything, and not an offer of any financial product. I'm a student, not a licensed adviser. Every result here is simulated, carries the modelling limits documented in [`DATA_NOTES.md`](DATA_NOTES.md) and [`ERRATA.md`](ERRATA.md), and is not actual trading. Past performance says nothing about future results.

The study's own conclusion is that 35 rulesets failed to beat holding an index fund. Read it as a reason to be skeptical of strategies, including any you find here.

## License

- **Code** (`code/`): MIT, see [`LICENSE`](LICENSE)
- **Written material** (the .md files): CC BY 4.0, see [`LICENSE-DOCS`](LICENSE-DOCS)
- **Data** (`data/`): not mine to license. Third-party market data and public calendars, included so the results can be reproduced. Per-file provenance is in [`DATA_NOTES.md`](DATA_NOTES.md); if you redistribute this repo, the provider's terms are your responsibility.

## Citation

```
Adil, M. (2026). Registered Backtests: a pre-registered replication of 12
published trading strategies. https://github.com/mayherprog/registered-backtests
```

Please cite the version, since [`ERRATA.md`](ERRATA.md) records that one headline conclusion changed after review.

## Author

Mayher Adil, Connecticut College '29. I trade a small live commodities and FX account under written risk rules. This study is why the core of my portfolio is a passive index fund.
