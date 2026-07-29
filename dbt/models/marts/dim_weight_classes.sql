-- Standardizes the weight classes for cleaner LLM querying
CREATE TABLE IF NOT EXISTS dim_weight_classes AS
SELECT DISTINCT 
    row_number() OVER () as class_id, 
    category_name 
FROM {{ ref('stg_results') }};
