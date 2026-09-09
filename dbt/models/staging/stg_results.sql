-- stg_results.sql
-- Cleaning and casting raw data from the CSV import
-- Note: raw_ow_event_117 is the table created by the extract_results.py script

SELECT 
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
FROM {{ source('openweightlifting', 'raw_ow_event_117') }}
-- Filter out 'out' lifters (total 0) to keep the Fact table clean
