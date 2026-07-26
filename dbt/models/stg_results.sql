-- dbt/models/stg_results.sql
SELECT 
    lifter_name as athlete_name, 
    CAST(date AS DATE) as event_date,
    CAST(total AS DOUBLE) as total_weight, 
    category as weight_class
FROM raw_ow_event_117
-- Filter out athletes who didn't finish (e.g., total = 0)
WHERE total > 0 
