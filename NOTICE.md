# Notice: what is licensed, what is not, and what this is not

## Scope of the licenses

**Code** (`code/`) is licensed under the MIT License. See `LICENSE`.

**Written material** (the Markdown documents: registrations, reports, ERRATA, data
notes, README) is licensed under Creative Commons Attribution 4.0 International.
See `LICENSE-DOCS`.

**Data** (`data/`) is **not** covered by either license and is not the copyright
holder's to license. It is third-party market data and public calendars, included so
that the results can be reproduced. Per-file provenance is documented in
`DATA_NOTES.md`. In summary:

| File group | Source |
|---|---|
| Daily and weekly OHLC price files | Yahoo Finance chart API, cross-validated against a broker market-data feed. Subject to that provider's terms of use. |
| `fomc_dates.csv` | Decision dates transcribed from federalreserve.gov |
| `cpi_dates.csv` | Release dates transcribed from bls.gov schedules |
| `calibration.json` | Option prices observed 2026-07-17 via OPRA-sourced quotes, recorded as calibration inputs |

Anyone redistributing this repository is responsible for their own compliance with the
market data provider's terms.

## Not investment advice

This repository is a research study. It is not investment advice, not a recommendation
to buy, sell, or hold any security, and not an offer of any financial product or
service. The author is a student, not a licensed financial adviser.

Simulated results are hypothetical. They carry the modelling limitations documented in
`DATA_NOTES.md` and `ERRATA.md`, and they do not represent actual trading. Past
performance does not indicate future results. Anyone acting on anything in this
repository does so entirely at their own risk.

The study's own conclusion is that 35 rulesets failed to beat holding an index fund.
Read it as a reason for skepticism about trading strategies, including any found here.

## On the results themselves

Facts and data are not copyrightable, so the numerical findings may be cited freely
regardless of the license on the prose. Attribution is requested for the same reason it
is requested of any research: so a reader can check the method, including `ERRATA.md`,
which records that one headline conclusion changed after review.
