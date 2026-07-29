-- This model will be populated by your Ingestion pipeline 
-- but managed as a table by dbt.
SELECT 
    id, 
    content, 
    embedding 
FROM {{ ref('stg_rules') }} -- Assuming you create a staging model for PDFs
