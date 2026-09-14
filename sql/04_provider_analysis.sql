
-- ============================================================
-- NHS A&E PROVIDER ANALYSIS
-- PostgreSQL analytical queries
-- ============================================================


-- ------------------------------------------------------------
-- Top 10 busiest providers
-- ------------------------------------------------------------

WITH provider_totals AS (
    SELECT
        org_code,
        SUM(total_ae_attendances) AS total_attendances
    FROM ae_provider_month
    WHERE total_ae_attendances > 0
    GROUP BY org_code
)

SELECT
    org_code,
    total_attendances,
    RANK() OVER (
        ORDER BY total_attendances DESC
    ) AS attendance_rank
FROM provider_totals
ORDER BY attendance_rank
LIMIT 10;


-- ------------------------------------------------------------
-- Type 1 demand vs performance correlation
-- ------------------------------------------------------------

WITH provider_metrics AS (
    SELECT
        org_code,
        COUNT(DISTINCT month) AS months_reported,
        SUM(type_1_attendances) AS total_attendances,
        SUM(type_1_over_four_hours) AS total_over_four_hours
    FROM ae_type1_provider_month
    WHERE type_1_attendances > 0
    GROUP BY org_code
),

calculated_metrics AS (
    SELECT
        org_code,
        total_attendances::NUMERIC / months_reported
            AS average_monthly_attendances,
        (
            (
                total_attendances
                - total_over_four_hours
            )::NUMERIC
            / total_attendances
        ) * 100 AS performance_pct
    FROM provider_metrics
    WHERE months_reported >= 24
)

SELECT
    COUNT(*) AS providers_included,
    CORR(
        average_monthly_attendances,
        performance_pct
    ) AS demand_performance_correlation
FROM calculated_metrics;
