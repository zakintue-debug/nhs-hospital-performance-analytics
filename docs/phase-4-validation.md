# A&E technical validation · 19 November 2026

The portfolio inputs are the provider-month CSVs at baseline commit `ed8525063f9b43ed23ca2027951e3cdf1b8f32c5`. Keep that vintage when reproducing the dashboard references. Source releases indexed later can change past counts.

## Source reconciliation

The [monthly ledger](source-reconciliation.csv) records the portfolio filename, official release label and URL, SHA-256 of the downloaded CSV, provider-code coverage, and counts and differences for each of 29 months. Releases were selected from the NHS England [2024–25](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2024-25/), [2025–26](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2025-26/) and [2026–27](https://www.england.nhs.uk/statistics/statistical-work-areas/ae-waiting-times-and-activity/ae-attendances-and-emergency-admissions-2026-27/) provider tables.

Use the period in the CSV and the provider's organisation code. Exclude the national total row by trimmed, case-insensitive “Total” in Period, Org Code or Org name, and use it as a separate check. Provider codes agreed between sources for every month. This is a code-based comparison; it does not link predecessor/successor organisations. The [source checker](../scripts/check_source_releases.py) names every contributing column.

- **Attendances and breaches:** sum the ordinary Type 1, Type 2 and Other columns in each family. Booked appointments have separate attendance and over-four-hour columns. The ledger records them separately. For revised April 2024, the official non-booked total of 2,163,149 exactly matches the portfolio. Adding 77,519 booked attendances gives 2,240,668 across both sets of columns for that release.
- **Admissions:** sum emergency admissions via each of the three A&E department categories. Exclude other emergency admissions. Dividing this count by non-booked attendances produces an aggregate ratio; there is no matched encounter population or patient-level probability.
- **Agreement:** all 29 official provider subtotals agreed with their published total rows. April 2024–March 2026 (24 months) matched the committed counts at every provider code for attendances, over-four-hours, admissions via A&E, Type 1 attendances and Type 1 over-four-hours. The five April–August 2026 releases revised on 12 November 2026 differ for two or three codes per month. Across these five months, portfolio minus revised totals are −4,549 attendances, +443 over four hours, +868 admissions via A&E, +3,427 Type 1 attendances and +515 Type 1 over four hours. See the ledger for signed monthly differences. Original untracked downloads cannot be authenticated from their filenames alone.

To repeat the source check, download each ledger URL to a local directory as `YYYY-MM.csv`, then run `python scripts/check_source_releases.py /path/to/releases`. It checks the file hashes, dates, keys, column definitions, official total rows, monthly summary and recorded provider differences. The provider-month inputs remain at their original vintage.

## Calculations and actual tests

The corrected Python notebook groups by code, uses name only for display, counts positive-attendance months, and calculates four-hour performance from summed counts before rounding. The refreshed portfolio summaries have one row per code, including inactive codes. Legacy summaries had 219 code/name rows for 207 codes. Use the eligibility threshold before interpreting provider comparisons.

The original scatterplots used code plus name (about −0.568 and +0.028). The following are Pearson correlations of provider mean monthly attendance with weighted within-four-hour performance. A provider with zero activity in a month contributes no eligible month. Matched series use only keys positive in both extracts before applying the threshold.

| Portfolio window | All departments (providers / months / r) | Type 1 | Matched all | Matched Type 1 |
|---|---|---|---|---|
| Apr 2024–Aug 2026, minimum 24 months | 180 / 5,174 / −0.573521 | 121 / 3,507 / +0.037781 | 121 / 3,507 / +0.158820 | 121 / 3,507 / +0.037781 |
| Apr 2024 only, minimum 1 month | 185 / 185 / −0.580885 | 122 / 122 / +0.011632 | 122 / 122 / +0.116974 | 122 / 122 / +0.011632 |

**SQL reference for Power BI:** rank eligible Type 1 provider codes by total Type 1 attendances in the selected window, descending, then code ascending. The full-period top ten are RRK, RAJ, RM3, RYR, R0A, R1H, RAL, RDU, RWE, RTG. For April 2024 alone they are RRK, RAJ, RM3, R0A, R1H, RDU, RWE, RYR, RTG, RQM. The minimum of one is intentional for this single-month reference.

Executed on a disposable PostgreSQL **16.2** database with the committed inputs. All three files in [sql](../sql) ran on the PostgreSQL engine. For both windows the test checked every eligible code in order, positive months, attendance, breaches, mean monthly volume and weighted percentage against an independently aggregated pandas reference. Counts and ranking matched exactly; numeric comparisons used absolute tolerance 1e−9. The SQL notebook also completed two consecutive reloads with its provider dimension present. The loader refreshes the five tables in one transaction.

From the repository root:

```bash
python -m unittest discover -s tests -v
python scripts/validate_provider_cohorts.py --min-months 24
# Set PGHOST, PGPORT, PGDATABASE and PGUSER for your disposable local database.
# The test uses pandas, psycopg2 and temporary tables.
python tests/validate_postgres.py
```

Three Python regression tests cover the portfolio reference, renamed providers, weighting, zero months, ties, matched eligibility, duplicate keys and invalid counts. The preparation notebook code ran against the 29 official releases in an isolated directory; both independent notebook correlations agreed with its validator within 1e−9. On that revised vintage the matched all-department correlation is +0.158640 and Type 1 is +0.037520. The corrected summary and correlation cells were separately executed against the committed provider-month inputs to produce the portfolio summaries.

## Power BI validation boundary

Static inspection of the original PBIX Report/Layout found two Type 1 Top N filters with Top = 10 ordered by an aggregation of `latest_org_name`. A query returning the expected ten codes does not change that saved filter. Power BI Desktop or an authorised compatible report editor, data source connection and refresh environment are required to correct the filters, group by stable code, exercise the selected period and validate DAX, relationships, slicers and chart membership against the references above. No PBIX, DAX or preview change is included.
