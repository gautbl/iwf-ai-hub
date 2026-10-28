
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with child as (
    select class_id as from_field
    from "iwf_hub"."main"."fct_results"
    where class_id is not null
),

parent as (
    select class_id as to_field
    from "iwf_hub"."main"."dim_weight_classes"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null



  
  
      
    ) dbt_internal_test