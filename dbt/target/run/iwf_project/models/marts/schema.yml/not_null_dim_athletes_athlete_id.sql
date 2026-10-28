
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select athlete_id
from "iwf_hub"."main"."dim_athletes"
where athlete_id is null



  
  
      
    ) dbt_internal_test