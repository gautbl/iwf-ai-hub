
    
    

select
    athlete_id as unique_field,
    count(*) as n_records

from "iwf_hub"."main"."dim_athletes"
where athlete_id is not null
group by athlete_id
having count(*) > 1


