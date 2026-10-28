
    

    create  table
      "iwf_hub"."main"."dim_weight_classes__dbt_tmp"
  
    
    as (
      

-- Standardizes the weight classes for cleaner LLM querying
SELECT DISTINCT 
    row_number() OVER (ORDER BY category_name) as class_id, 
    category_name 
FROM "iwf_hub"."main"."stg_results"
GROUP BY category_name
    );
    
  