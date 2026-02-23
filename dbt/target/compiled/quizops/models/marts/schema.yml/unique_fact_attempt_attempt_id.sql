
    
    

select
    attempt_id as unique_field,
    count(*) as n_records

from "quizops"."analytics_marts"."fact_attempt"
where attempt_id is not null
group by attempt_id
having count(*) > 1


