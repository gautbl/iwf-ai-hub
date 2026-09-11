-- dbt/models/marts/fct_results.sql

{{ config(
    materialized='table',
    unique_key='result_id' 
) }}

-- The fact table contains the quantitative metrics of the event.
-- It links the Athlete, the Weight Class, and the Date.

SELECT 
    -- Generate a unique ID for each result since the raw data might lack one
    row_number() OVER (ORDER BY event_date, athlete_id) as result_id, 
    
    -- Foreign Key to dim_athletes (via ref)
    a.athlete_id, 
    
    -- The date of the competition
    s.event_date, 
    
    -- Foreign Key to dim_weight_classes (via ref)
    wc.class_id, 
    
    -- The actual weight lifted (The quantitative metrics)
    s.snatch_total, 
    s.clean_jerk_total, 
    s.combined_total
    
FROM {{ ref('stg_results') }} s
-- We join with dimensions to transform the descriptive names from 
-- the CSV into consistent IDs.
JOIN {{ ref('dim_athletes') }} a 
    ON s.athlete_name = a.name
JOIN {{ ref('dim_weight_classes') }} wc 
    ON s.category_name = wc.category_name