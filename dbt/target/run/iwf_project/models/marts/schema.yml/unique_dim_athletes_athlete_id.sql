
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    athlete_id as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_athletes"
where athlete_id is not null
group by athlete_id
having count(*) > 1



  
  
      
    ) dbt_internal_test