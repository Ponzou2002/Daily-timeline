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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                todo_date TEXT NOT NULL,
                completed_at TEXT,
                created_at TEXT NOT NULL
            )
            """
)


@app.get("/")
def index():
    today = datetime.now().astimezone().date().isoformat()

    with get_db() as connection:
        current_activity_row = connection.execute(
            """
            SELECT id, name, started_at, ended_at
            FROM activities
            WHERE ended_at IS NULL
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()

        recent_activity_rows = connection.execute(
            """
            SELECT id, name, started_at, ended_at
            FROM activities
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 50
            """
        ).fetchall()
        
        todo_rows = connection.execute(
            """
            SELECT id, title, todo_date, completed_at, created_at
            FROM todos
            WHERE todo_date = ?
            ORDER BY
                CASE WHEN completed_at IS NULL THEN 0 ELSE 1 END,
                created_at ASC
            """,
            (today,),
        ).fetchall()

    current_activity = add_display_values(
        current_activity_row
    )

    recent_activities = [
        add_display_values(activity)
        for activity in recent_activity_rows
    ]

    activity_groups = []

    for activity in recent_activities:
        is_new_date = (
            not activity_groups
            or activity_groups[-1]["date_key"]
            != activity["date_key"]
        )

        if is_new_date:
            activity_groups.append(
                {
                    "date_key": activity["date_key"],
                    "date_display": activity["date_display"],
                    "activities": [],
                }
            )

        activity_groups[-1]["activities"].append(activity)
        todos = [dict(todo) for todo in todo_rows]

    return render_template(
        "index.html",
        current_activity=current_activity,
        activity_groups=activity_groups,
        todos=todos,
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

@app.post("/todo/add")
def add_todo():
    title = request.form.get("title", "").strip()

    if not title:
        return redirect(url_for("index"))

    now = datetime.now().astimezone()
    today = now.date().isoformat()

    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO todos (
                title,
                todo_date,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (
                title,
                today,
                now.isoformat(timespec="seconds"),
            ),
        )

    return redirect(url_for("index"))

@app.post("/todo/<int:todo_id>/complete")
def complete_todo(todo_id):
    is_completed = "completed" in request.form

    completed_at = None

    if is_completed:
        completed_at = (
            datetime.now()
            .astimezone()
            .isoformat(timespec="seconds")
        )

    with get_db() as connection:
        connection.execute(
            """
            UPDATE todos
            SET completed_at = ?
            WHERE id = ?
            """,
            (completed_at, todo_id),
        )

    return redirect(url_for("index"))

init_db()

def add_display_values(activity):
    if activity is None:
        return None

    result = dict(activity)

    started_at = datetime.fromisoformat(result["started_at"])

    # 現在のタスク表示などで使う日時
    result["started_at_display"] = started_at.strftime(
        "%Y/%m/%d %H:%M:%S"
    )

    # アクティビティログの日付グループ用
    result["date_key"] = started_at.date().isoformat()
    result["date_display"] = (
        f"{started_at.month}月{started_at.day}日"
    )

    # ログ内では時刻だけを表示する
    result["started_time_display"] = started_at.strftime(
        "%H:%M:%S"
    )

    if result["ended_at"]:
        ended_at = datetime.fromisoformat(result["ended_at"])

        result["ended_at_display"] = ended_at.strftime(
            "%Y/%m/%d %H:%M:%S"
        )

        result["ended_time_display"] = ended_at.strftime(
            "%H:%M:%S"
        )

        total_seconds = max(
            0,
            int((ended_at - started_at).total_seconds()),
        )

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        result["duration_display"] = (
            f"{hours:02}:{minutes:02}:{seconds:02}"
        )
    else:
        result["ended_at_display"] = None
        result["ended_time_display"] = None
        result["duration_display"] = None

    return result