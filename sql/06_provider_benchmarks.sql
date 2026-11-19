-- Run 05_period_cohorts.sql first in the same session.
SELECT cohort, COUNT(*) AS providers, SUM(months) AS provider_months,
       CORR(mean_volume, performance_pct) AS pearson_r
FROM pg_temp.provider_metrics('2024-04-01', '2026-08-01', 24)
GROUP BY cohort ORDER BY cohort;

-- Exactly ten eligible provider codes. Break equal attendance totals by code.
SELECT org_code, months, attendances, performance_pct
FROM pg_temp.provider_metrics('2024-04-01', '2026-08-01', 24)
WHERE cohort = 'type1'
ORDER BY attendances DESC, org_code LIMIT 10;
