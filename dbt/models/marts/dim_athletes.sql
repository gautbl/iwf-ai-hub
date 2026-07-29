-- Creates a unique list of athletes
CREATE TABLE IF NOT EXISTS dim_athletes AS
SELECT 
    row_number() OVER () as athlete_id, 
    athlete_name as name, 
    'Unknown' as country -- Can be enriched later if source data allows
FROM {{ ref('stg_results') }}
GROUP BY athlete_name;
