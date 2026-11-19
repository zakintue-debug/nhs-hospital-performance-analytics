-- Session-local helper. Dates are inclusive reporting month starts.
-- Apply the period before counting positive months. Names never define identity.
CREATE OR REPLACE FUNCTION pg_temp.provider_metrics(first_month date, last_month date, minimum_months integer)
RETURNS TABLE (cohort text, org_code text, months bigint, attendances numeric,
               breaches numeric, mean_volume numeric, performance_pct numeric)
LANGUAGE sql STABLE AS $$
    WITH activity AS (
        SELECT 'all' AS department, a.org_code::text AS code, a.month::date AS period,
               a.total_ae_attendances AS volume, a.total_over_four_hours AS over4
        FROM ae_provider_month a
        WHERE a.total_ae_attendances > 0
        UNION ALL
        SELECT 'type1', t.org_code::text, t.month::date,
               t.type_1_attendances, t.type_1_over_four_hours
        FROM ae_type1_provider_month t
        WHERE t.type_1_attendances > 0
    ), periods AS (
        SELECT *, COUNT(*) OVER (PARTITION BY code, period) AS series
        FROM activity WHERE period BETWEEN first_month AND last_month
    ), cohorts AS (
        SELECT department AS label, code, volume, over4 FROM periods
        UNION ALL
        SELECT 'matched_' || department, code, volume, over4 FROM periods WHERE series = 2
    )
    SELECT label, code, COUNT(*), SUM(volume)::numeric, SUM(over4)::numeric,
           AVG(volume), 100 * (SUM(volume) - SUM(over4))::numeric / SUM(volume)
    FROM cohorts GROUP BY label, code HAVING COUNT(*) >= minimum_months
$$;
