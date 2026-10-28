
    
    

select
    category_name as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_weight_classes"
where category_name is not null
group by category_name
having count(*) > 1


