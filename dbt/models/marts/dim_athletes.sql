{{ config(materialized='table') }}

-- Creates a unique list of athletes
SELECT 
    row_number() OVER (ORDER BY athlete_name) as athlete_id, 
    athlete_name as name, 
    'Unknown' as country -- Can be enriched later if source data allows
FROM {{ ref('stg_results') }}
GROUP BY athlete_name;
