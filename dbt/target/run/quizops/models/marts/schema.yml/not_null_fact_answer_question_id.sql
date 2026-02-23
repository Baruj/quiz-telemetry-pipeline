select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select question_id
from "quizops"."analytics_marts"."fact_answer"
where question_id is null



      
    ) dbt_internal_test