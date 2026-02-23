select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select quiz_id
from "quizops"."analytics_marts"."fact_attempt"
where quiz_id is null



      
    ) dbt_internal_test