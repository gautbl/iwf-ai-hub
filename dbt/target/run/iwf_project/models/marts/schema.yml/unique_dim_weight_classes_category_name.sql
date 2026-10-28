
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    category_name as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_weight_classes"
where category_name is not null
group by category_name
having count(*) > 1



  
  
      
    ) dbt_internal_test