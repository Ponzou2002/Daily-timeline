from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo, available_timezones

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

DB_PATH = Path(__file__).with_name("daily_timeline.db")

DEFAULT_SETTINGS = {
    "texture": "glass",
    "main_theme": "dark",
    "accent_color": "cyan",
    "timezone": "Asia/Tokyo",
}

TEXTURE_OPTIONS = {"glass", "flat", "neumorphism"}
MAIN_THEME_OPTIONS = {"dark", "light"}
ACCENT_COLOR_OPTIONS = {
    "cyan",
    "purple",
    "green",
    "orange",
    "none",
}

TIMEZONE_NAMES = sorted(available_timezones())
TIMEZONE_NAME_SET = set(TIMEZONE_NAMES)


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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        connection.executemany(
            """
            INSERT OR IGNORE INTO app_settings (key, value)
            VALUES (?, ?)
            """,
            DEFAULT_SETTINGS.items(),
        )


def load_settings(connection):
    settings = dict(DEFAULT_SETTINGS)

    rows = connection.execute(
        """
        SELECT key, value
        FROM app_settings
        """
    ).fetchall()

    for row in rows:
        settings[row["key"]] = row["value"]

    return settings


def get_configured_timezone(settings):
    timezone_name = settings.get(
        "timezone",
        DEFAULT_SETTINGS["timezone"],
    )

    try:
        return ZoneInfo(timezone_name)
    except Exception:
        return ZoneInfo(DEFAULT_SETTINGS["timezone"])


def get_current_settings():
    with get_db() as connection:
        return load_settings(connection)


def convert_to_timezone(value, timezone):
    moment = datetime.fromisoformat(value)

    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone)

    return moment.astimezone(timezone)


def add_display_values(activity, timezone):
    if activity is None:
        return None

    result = dict(activity)

    started_at = convert_to_timezone(
        result["started_at"],
        timezone,
    )

    result["started_at_display"] = started_at.strftime(
        "%Y/%m/%d %H:%M:%S"
    )

    result["date_key"] = started_at.date().isoformat()
    result["date_display"] = (
        f"{started_at.month}月{started_at.day}日"
    )

    result["started_time_display"] = started_at.strftime(
        "%H:%M:%S"
    )

    if result["ended_at"]:
        ended_at = convert_to_timezone(
            result["ended_at"],
            timezone,
        )

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


def build_timeline_items(
    rows,
    day_start,
    day_end,
    now,
    timezone,
):
    items = []

    for row in rows:
        started_at = convert_to_timezone(
            row["started_at"],
            timezone,
        )

        is_current = row["ended_at"] is None

        if is_current:
            ended_at = now
        else:
            ended_at = convert_to_timezone(
                row["ended_at"],
                timezone,
            )

        visible_start = max(started_at, day_start)
        visible_end = min(ended_at, day_end)

        if visible_end <= visible_start:
            continue

        start_minutes = (
            visible_start - day_start
        ).total_seconds() / 60

        end_minutes = (
            visible_end - day_start
        ).total_seconds() / 60

        duration_minutes = end_minutes - start_minutes

        items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "start_percent": start_minutes / 1440 * 100,
                "height_percent": duration_minutes / 1440 * 100,
                "start_minute": start_minutes,
                "start_display": visible_start.strftime("%H:%M"),
                "end_display": (
                    None
                    if is_current
                    else visible_end.strftime("%H:%M")
                ),
                "is_current": is_current,
            }
        )

    return items


@app.get("/")
def index():
    with get_db() as connection:
        settings = load_settings(connection)
        timezone = get_configured_timezone(settings)
        now = datetime.now(timezone)
        today = now.date().isoformat()

        day_start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        day_end = day_start + timedelta(days=1)

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

        timeline_rows = connection.execute(
            """
            SELECT id, name, started_at, ended_at
            FROM activities
            WHERE datetime(started_at) < datetime(?)
              AND (
                  ended_at IS NULL
                  OR datetime(ended_at) > datetime(?)
              )
            ORDER BY datetime(started_at) ASC
            """,
            (
                day_end.isoformat(timespec="seconds"),
                day_start.isoformat(timespec="seconds"),
            ),
        ).fetchall()

    current_activity = add_display_values(
        current_activity_row,
        timezone,
    )

    recent_activities = [
        add_display_values(activity, timezone)
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

    timeline_items = build_timeline_items(
        timeline_rows,
        day_start,
        day_end,
        now,
        timezone,
    )

    return render_template(
        "index.html",
        current_activity=current_activity,
        activity_groups=activity_groups,
        todos=todos,
        timeline_items=timeline_items,
        settings=settings,
        timezone_names=TIMEZONE_NAMES,
    )


@app.post("/settings")
def update_settings():
    texture = request.form.get("texture", "")
    main_theme = request.form.get("main_theme", "")
    accent_color = request.form.get("accent_color", "")
    timezone_name = request.form.get("timezone", "")

    updates = {}

    if texture in TEXTURE_OPTIONS:
        updates["texture"] = texture

    if main_theme in MAIN_THEME_OPTIONS:
        updates["main_theme"] = main_theme

    if accent_color in ACCENT_COLOR_OPTIONS:
        updates["accent_color"] = accent_color

    if timezone_name in TIMEZONE_NAME_SET:
        updates["timezone"] = timezone_name

    with get_db() as connection:
        for key, value in updates.items():
            connection.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key)
                DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    return redirect(url_for("index"))


@app.post("/start")
def start_activity():
    task_name = request.form.get("task_name", "").strip()

    if not task_name:
        return redirect(url_for("index"))

    now = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_db() as connection:
        connection.execute(
            """
            UPDATE activities
            SET ended_at = ?
            WHERE ended_at IS NULL
            """,
            (now,),
        )

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

    settings = get_current_settings()
    timezone = get_configured_timezone(settings)
    now = datetime.now(timezone)
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
