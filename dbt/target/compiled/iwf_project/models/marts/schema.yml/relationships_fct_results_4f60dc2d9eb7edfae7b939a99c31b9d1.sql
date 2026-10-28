
    
    

with child as (
    select athlete_id as from_field
    from "iwf_hub"."main"."fct_results"
    where athlete_id is not null
),

parent as (
    select athlete_id as to_field
    from "iwf_hub"."main"."dim_athletes"
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null


