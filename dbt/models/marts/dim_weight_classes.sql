{{ config(materialized='table') }}

-- Standardizes the weight classes for cleaner LLM querying
SELECT DISTINCT 
    row_number() OVER () as class_id, 
    category_name 
FROM {{ ref('stg_results') }};
