from datetime import datetime
from pathlib import Path
import sqlite3

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

DB_PATH = Path(__file__).with_name("daily_timeline.db")


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
            """
        )


@app.get("/")
def index():
    with get_db() as connection:
        current_activity = connection.execute(
            """
            SELECT id, name, started_at, ended_at
            FROM activities
            WHERE ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()

    return render_template(
        "index.html",
        current_activity=current_activity,
    )


@app.post("/start")
def start_activity():
    task_name = request.form.get("task_name", "").strip()

    if not task_name:
        return redirect(url_for("index"))

    now = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_db() as connection:
        # 現在進行中のタスクを終了する
        connection.execute(
            """
            UPDATE activities
            SET ended_at = ?
            WHERE ended_at IS NULL
            """,
            (now,),
        )

        # 新しいタスクを開始する
        connection.execute(
            """
            INSERT INTO activities (name, started_at)
            VALUES (?, ?)
            """,
            (task_name, now),
        )

    return redirect(url_for("index"))


init_db()