import json
import os
from pathlib import Path
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://quiz:quiz@db:5432/quizops",
)

def main():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    file_path = Path("/data/questions/sql_python_de.json")
    payload = json.loads(file_path.read_text(encoding="utf-8"))

    with engine.begin() as conn:
        quiz_id = conn.execute(
                text("INSERT INTO quizzes(title, description) VALUES(:t, :d) RETURNING quiz_id"),
                {"t": payload["title"], "d": payload.get("description")},
                ).scalar_one()
        for q in payload["questions"]:
            conn.execute(
                text("""
                    INSERT INTO questions(quiz_id, prompt, options, correct_index, topic, difficulty)
                    VALUES(:quiz, :prompt, CAST(:options AS jsonb), :correct, :topic, :diff)
                """),
                {
                    "quiz": quiz_id,
                    "prompt": q["prompt"],
                    "options": json.dumps(q["options"], ensure_ascii=False),
                    "correct": q["correct_index"],
                    "topic": q.get("topic"),
                    "diff": q.get("difficulty", 1),
                },
            )
    print(f"Seed OK. quiz_id={quiz_id}")

if __name__ == "__main__":
    main()


