
    
    

select
    class_id as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_weight_classes"
where class_id is not null
group by class_id
having count(*) > 1


