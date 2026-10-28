
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select athlete_id
from "iwf_hub"."main"."fct_results"
where athlete_id is null



  
  
      
    ) dbt_internal_test