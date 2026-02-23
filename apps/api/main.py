from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from db import get_db
import uuid

app = FastAPI(title="QuizOps API", version="0.1.0")


app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)

class AttemptCreate(BaseModel):
    quiz_id: uuid.UUID
    username: str | None = Field(default=None, min_length=2, max_length=40)

class AnswerUpsert(BaseModel):
    question_id: uuid.UUID
    chosen_index: int = Field(ge=0)

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/quizzes")
def list_quizzes(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
          SELECT quiz_id, title, description, created_at
          FROM quizzes
          ORDER BY created_at DESC
          LIMIT :limit OFFSET :offset
        """),
        {"limit": limit, "offset": offset},
    ).mappings().all()
    return {"items": list(rows), "limit": limit, "offset": offset}

@app.get("/quizzes/{quiz_id}/questions")
def get_questions(quiz_id: uuid.UUID, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
            SELECT question_id, prompt, options, topic, difficulty
            FROM questions
            WHERE quiz_id = :quiz_id
            ORDER BY created_at ASC
        """),
        {"quiz_id": quiz_id},
    ).mappings().all()
    if not rows:
        raise HTTPException(404, "Quiz not found or has no questions")
    return {"quiz_id": str(quiz_id), "questions": list(rows)}

@app.post("/attempts")
def create_attempt(payload: AttemptCreate, db: Session = Depends(get_db)):
    user_id = None
    if payload.username:
        row = db.execute(
            text("SELECT user_id FROM users WHERE username=:u"),
            {"u": payload.username},
        ).mappings().first()
        if row:
            user_id = row["user_id"]
        else:
            user_id = db.execute(
                text("INSERT INTO users(username) VALUES(:u) RETURNING user_id"),
                {"u": payload.username},
            ).scalar_one()

    attempt_id = db.execute(
        text("""
            INSERT INTO attempts(quiz_id, user_id)
            VALUES(:q, :u)
            RETURNING attempt_id
        """),
        {"q": payload.quiz_id, "u": user_id},
    ).scalar_one()
    db.commit()
    return {"attempt_id": str(attempt_id)}

@app.post("/attempts/{attempt_id}/answers")
def upsert_answer(attempt_id: uuid.UUID, payload: AnswerUpsert, db: Session = Depends(get_db)):
    # It's validated the existance of the attempt
    exists = db.execute(
        text("SELECT 1 FROM attempts WHERE attempt_id=:a"),
        {"a": attempt_id},
    ).first()
    if not exists:
        raise HTTPException(404, "Attempt not found")

    db.execute(
        text("""
          INSERT INTO answers(attempt_id, question_id, chosen_index)
          VALUES(:a, :q, :c)
          ON CONFLICT (attempt_id, question_id)
          DO UPDATE SET chosen_index = EXCLUDED.chosen_index
        """),
        {"a": attempt_id, "q": payload.question_id, "c": payload.chosen_index},
    )
    db.commit()
    return {"ok": True}

@app.post("/attempts/{attempt_id}/submit")
def submit_attempt(attempt_id: uuid.UUID, db: Session = Depends(get_db)):
    #The score is calculated
    row = db.execute(
        text("""
          SELECT a.attempt_id, a.quiz_id
          FROM attempts a
          WHERE a.attempt_id = :a
        """),
        {"a": attempt_id},
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Attempt not found")

    score_row = db.execute(
        text("""
          SELECT
            SUM(CASE WHEN ans.chosen_index = q.correct_index THEN 1 ELSE 0 END) AS score,
            COUNT(q.question_id) AS max_score
          FROM questions q
          LEFT JOIN answers ans
            ON ans.question_id = q.question_id
           AND ans.attempt_id = :a
          WHERE q.quiz_id = :quiz
        """),
        {"a": attempt_id, "quiz": row["quiz_id"]},
    ).mappings().first()

    db.execute(
        text("""
          UPDATE attempts
          SET submitted_at = NOW(),
              score = :s,
              max_score = :m
          WHERE attempt_id = :a
        """),
        {"s": int(score_row["score"] or 0), "m": int(score_row["max_score"] or 0), "a": attempt_id},
    )
    db.commit()
    return {"attempt_id": str(attempt_id), "score": int(score_row["score"] or 0), "max_score": int(score_row["max_score"] or 0)}

