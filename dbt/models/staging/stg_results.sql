-- stg_results.sql
-- Cleaning and casting raw data from the CSV import
-- Note: raw_ow_events is the unified table created by the extract_results.py script

SELECT 
    -- Discriminant of the source event
    event_id,
    -- Human readable event name from the CSV
    event AS event_name,
    -- Ensure athlete names are trimmed and consistent
    TRIM(lifter_name) AS athlete_name, 
    -- Cast date to proper DATE type
    CAST(date AS DATE) AS event_date,
    -- Standardize category for joins with dim_weight_classes
    TRIM(category) AS category_name,
    -- Cast weights to DOUBLE for mathematical operations
    CAST(best_snatch AS DOUBLE) AS snatch_total, 
    CAST(best_cj AS DOUBLE) AS clean_jerk_total, 
    CAST(total AS DOUBLE) AS combined_total
FROM {{ source('openweightlifting', 'raw_ow_events') }}
-- Intentionally NO WHERE clause: all results are valid data, including
-- 'out' lifters (total = 0). They are retained in the Fact table for
-- completeness rather than filtered out at the staging layer.
