
  create view "quizops"."analytics_staging"."stg_answers__dbt_tmp"
    
    
  as (
    select
  answer_id,
  attempt_id,
  question_id,
  chosen_index,
  created_at
from public.answers
  );