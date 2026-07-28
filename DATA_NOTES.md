# DATA_NOTES.md
Run date: 2026-07-18 (Saturday). All data as of Friday 2026-07-17 close.

## 1. Price history (data/spy.csv, qqq.csv, smh.csv, xbi.csv, iwm.csv)
- Coverage: 2014-01-02 through 2026-07-17, 3,153 daily rows per symbol, no gaps > 5 weekdays, no duplicate dates, OHLC sanity checks passed.
- Prices are split- and dividend-adjusted (backward-adjusted as of 2026-07-18).
- Provenance: bulk history was fetched by a data worker from Yahoo Finance's chart API because full-size responses from the Webull market-data MCP tool overflowed the worker's transport at count=1200. The Webull MCP feed was used to cross-validate both ends of the range for all 5 symbols: 13 of 14 sampled bars matched within 0.003%; QQQ 2014-01-02 differed by 0.15% (vendor adjustment rounding). Spot check: SPY 2026-07-17 close 743.29 matches the MCP feed exactly. Cross-check against the plan file: SMH Friday low 536.81 matches trading-plan-hybrid.md.
- Consequence of backward adjustment: absolute price levels before ~2020 differ from prices quoted at the time. Percent returns, MA crossovers, and swing structure are unaffected. Option strikes in the backtest are set relative to the adjusted spot, which is the correct treatment for a returns-based simulation.

## 2. Macro calendar (data/fomc_dates.csv, data/cpi_dates.csv)
- FOMC: 97 decision dates 2015-2026 (95 scheduled; 2020's March 17-18 meeting was cancelled and replaced by the 2020-03-03 and 2020-03-15 unscheduled meetings, both included). Decision dates taken from statement URLs on federalreserve.gov (fomccalendars.htm for 2021-2027; fomchistorical2015.htm through fomchistorical2020.htm for earlier years). Excluded as un-front-runnable: the 2019-10-04 unscheduled videoconference (statement released 10-11) and the March 2020 notation votes (3/19, 3/23, 3/31). This slightly flatters the blackout rule around those dates and is noted in the report.
- CPI: 138 releases 2015-01 through 2026-07 from BLS archived yearly schedules (bls.gov/schedule/2015/home.htm ... /2025/home.htm) and the current CPI schedule page. Anomaly: no October 2025 reference-month CPI was ever published (2025 government shutdown); September 2025 data released late on 2025-10-24; November 2025 data on 2025-12-18. All dates validated as weekdays. See data/cpi_notes.md.

## 3. Options pricing approximation (data/calibration.json)
Long-run historical option IV surfaces are paywalled. Historical option P/L is therefore approximated:
- Model: Black-Scholes, sigma_t = m x RV63_t (63-day realized vol of the underlying), risk-free r = 4% assumed (not verified for the whole window; IV solutions for 30-75 DTE near-ATM options move < 1 vol point across r = 2-5%).
- Calibration to the live surface, Friday 2026-07-17 last-trade prices from OPRA via TradingView:
  | Contract | Last | Implied vol | IV/RV63 |
  |---|---|---|---|
  | XBI Sep18'26 160C (62 DTE) | 6.09 | 31.9% | 1.05 |
  | XBI Dec18'26 160C (153 DTE) | 11.97 | 33.5% | 1.11 |
  | SMH Aug21'26 555C (34 DTE) | 40.15 | 56.8% | 1.08 |
  | SMH Sep18'26 555C (62 DTE) | 53.57 | 56.0% | 1.06 |
  | SPY Sep18'26 745C (62 DTE) | 19.74 | 14.8% | 1.13 |
  m = 1.08 (mean). VIX 18.77 vs SPY RV21 12.7% (ratio 1.47) confirms a normal-width vol risk premium regime.
- Stated approximation error: the five calibration ratios span 1.05-1.13 (about +/-4% around m) in current conditions. Historically the vol risk premium is unstable: in stress regimes IV/RV can compress below 0.9 (RV spikes faster than IV) and in calm regimes exceed 1.3. Every options P/L number in this project therefore carries an estimated +/-10-20% premium-level uncertainty, worse in regime transitions (2018 vol spike, March 2020). Headline results are re-run at m = 0.95 and m = 1.25 and reported as bands.
- Known omissions, all of which make live results WORSE than modeled: bid-ask spread (plan allows up to 10% of mid; modeled at mid), slippage on 5-wide markets, early assignment (none; long options only), weekend/overnight gap through stops (stop fills modeled at the daily close mark, but a gap through -50% fills lower), IV-rank entry filter uses an RV-rank proxy because historical IV rank is unavailable.
- Calibration prices are last trades, not mids; on illiquid strikes (volume 23-73 on the XBI/SMH quotes) last can sit anywhere in the spread. This adds roughly +/-3-5% to the calibration constant itself.

## 4. Not available / not testable
- VIX daily history: not available from the connected MCP feed (INVALID_SYMBOL). IV-rank filter simulated via RV-rank proxy, flagged in every result that uses it.
- Historical option chains (strike grids, OI, spreads): unavailable. Contract affordability is modeled from BS prices; OI > 500 and spread < 10% filters are NOT testable historically.
- Webull fill quality, fractional-share transition mechanics, futures microstructure: out of scope of data; treated qualitatively in the report.
