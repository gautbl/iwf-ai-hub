
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select category_name
from "iwf_hub"."main"."dim_weight_classes"
where category_name is null



  
  
      
    ) dbt_internal_test