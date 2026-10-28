
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select class_id
from "iwf_hub"."main"."dim_weight_classes"
where class_id is null



  
  
      
    ) dbt_internal_test