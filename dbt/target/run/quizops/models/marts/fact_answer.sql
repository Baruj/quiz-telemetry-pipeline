
  create view "quizops"."analytics_marts"."fact_answer__dbt_tmp"
    
    
  as (
    select
  ans.attempt_id,
  ans.question_id,
  ans.chosen_index,
  q.correct_index,
  case when ans.chosen_index = q.correct_index then 1 else 0 end as is_correct
from public.answers ans
join public.questions q
  on q.question_id = ans.question_id
  );