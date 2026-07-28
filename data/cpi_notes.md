# BLS CPI release dates 2015-2026, sourcing and anomaly notes

Generated 2026-07-18. File: `cpi_dates.csv` (138 rows: release_date, reference_month, source_url).

## Sources
- Attempted https://www.bls.gov/schedule/archives/cpi_nr.htm first, page returned empty content; not usable.
- 2015-2025 rows extracted from BLS archived whole-year schedules:
  https://www.bls.gov/schedule/2015/home.htm ... https://www.bls.gov/schedule/2025/home.htm
  (one fetch per year; only "Consumer Price Index" 8:30 AM ET rows kept, Real Earnings, PPI, and other releases excluded).
- 2025-12-18 and all 2026 rows from the current CPI schedule page:
  https://www.bls.gov/schedule/news_release/cpi.htm

## Row counts per release year
2015-2024: 12 each. 2025: 11. 2026 (through July): 8 scheduled dates carried, of which 7 are 2026-dated (2025-12-18 counted under 2025).

## Anomalies
1. **2025 government shutdown (fall 2025):**
   - The September 2025 CPI was released late on **Friday, 2025-10-24** (normally would have been ~Oct 15). This is the only CPI release shown on the archived October 2025 schedule.
   - **No CPI for reference month October 2025 was ever published**, there is no row with reference_month "October 2025"; the schedule jumps from September 2025 data (released 2025-10-24) to November 2025 data (released 2025-12-18).
   - No CPI release occurred in calendar November 2025.
   - Hence 2025 has 11 releases instead of 12.
2. **2024-05-15 (April 2024 CPI):** released on the 15th, slightly later in the month than typical (10th-14th); as scheduled by BLS, not a delay.
3. All 138 release dates are weekdays; reference-month-to-release lag is 1 month for every row (validated programmatically).
4. All times are 8:30 AM ET per the schedule pages ("All times on calendar are Eastern Time").

## Notes on interpretation
- reference_month is the data month the release covers (e.g., release 2015-01-16 covers December 2014).
- Rows are the CPI-U monthly "Consumer Price Index" news release only; the companion "Real Earnings" release published the same day at the same time is excluded.
