
    
    

select
    name as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_athletes"
where name is not null
group by name
having count(*) > 1


