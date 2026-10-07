import os
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
DATABASE_URL = os.getenv("DATABASE_URL")


class Todo(BaseModel):
    title: str


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS todos (id SERIAL PRIMARY KEY, title TEXT NOT NULL)")
    conn.commit()
    return conn


@app.get("/")
def home():
    return {"message": "Todo API is running"}


@app.post("/todos")
def add_todo(todo: Todo):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO todos (title) VALUES (%s) RETURNING id", (todo.title,))
            new_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
    return {"id": new_id, "title": todo.title}


@app.get("/todos")
def list_todos():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM todos ORDER BY id")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [{"id": r[0], "title": r[1]} for r in rows]
