from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo, available_timezones

from flask import Flask, jsonify, redirect, render_template, request, url_for

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
    "pink",
    "purple",
    "green",
    "orange",
    "none",
}

TIMEZONE_NAMES = sorted(available_timezones())
TIMEZONE_NAME_SET = set(TIMEZONE_NAMES)
SCHEDULE_MINUTES = {0, 10, 20, 30, 40, 50}


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
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                planned_start TEXT NOT NULL,
                planned_end TEXT NOT NULL,
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
            original_ended_at = None
        else:
            ended_at = convert_to_timezone(
                row["ended_at"],
                timezone,
            )
            original_ended_at = ended_at

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
                "edit_start_date": started_at.date().isoformat(),
                "edit_start_hour": started_at.hour,
                "edit_start_minute": started_at.minute,
                "edit_end_date": (
                    None
                    if original_ended_at is None
                    else original_ended_at.date().isoformat()
                ),
                "edit_end_hour": (
                    None
                    if original_ended_at is None
                    else original_ended_at.hour
                ),
                "edit_end_minute": (
                    None
                    if original_ended_at is None
                    else original_ended_at.minute
                ),
            }
        )

    return items


def layout_schedule_group(group):
    """Assign overlapping schedules to horizontal lanes."""
    lane_ends = []

    for item in group:
        lane_index = None

        for index, lane_end in enumerate(lane_ends):
            if item["start_minute"] >= lane_end:
                lane_index = index
                lane_ends[index] = item["end_minute"]
                break

        if lane_index is None:
            lane_index = len(lane_ends)
            lane_ends.append(item["end_minute"])

        item["lane_index"] = lane_index

    lane_count = max(1, len(lane_ends))

    for item in group:
        item["lane_count"] = lane_count
        item["lane_left_percent"] = (
            item["lane_index"] / lane_count * 100
        )
        item["lane_width_percent"] = 100 / lane_count


def build_schedule_items(
    rows,
    day_start,
    day_end,
    timezone,
):
    items = []

    for row in rows:
        planned_start = convert_to_timezone(
            row["planned_start"],
            timezone,
        )
        planned_end = convert_to_timezone(
            row["planned_end"],
            timezone,
        )

        visible_start = max(planned_start, day_start)
        visible_end = min(planned_end, day_end)

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
                "end_minute": end_minutes,
                "start_display": visible_start.strftime("%H:%M"),
                "end_display": visible_end.strftime("%H:%M"),
                "edit_start_date": planned_start.date().isoformat(),
                "edit_start_hour": planned_start.hour,
                "edit_start_minute": planned_start.minute,
                "edit_end_date": planned_end.date().isoformat(),
                "edit_end_hour": planned_end.hour,
                "edit_end_minute": planned_end.minute,
            }
        )

    items.sort(
        key=lambda item: (
            item["start_minute"],
            item["end_minute"],
        )
    )

    current_group = []
    current_group_end = None

    for item in items:
        if (
            current_group
            and item["start_minute"] >= current_group_end
        ):
            layout_schedule_group(current_group)
            current_group = []
            current_group_end = None

        current_group.append(item)

        if current_group_end is None:
            current_group_end = item["end_minute"]
        else:
            current_group_end = max(
                current_group_end,
                item["end_minute"],
            )

    if current_group:
        layout_schedule_group(current_group)

    return items


def get_day_bounds(timezone):
    now = datetime.now(timezone)
    day_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    day_end = day_start + timedelta(days=1)
    return now, day_start, day_end


def get_today_schedule_items():
    settings = get_current_settings()
    timezone = get_configured_timezone(settings)
    _, day_start, day_end = get_day_bounds(timezone)

    with get_db() as connection:
        rows = connection.execute(
            """
            SELECT id, name, planned_start, planned_end, created_at
            FROM plans
            WHERE datetime(planned_start) < datetime(?)
              AND datetime(planned_end) > datetime(?)
            ORDER BY datetime(planned_start) ASC
            """,
            (
                day_end.isoformat(timespec="seconds"),
                day_start.isoformat(timespec="seconds"),
            ),
        ).fetchall()

    return build_schedule_items(
        rows,
        day_start,
        day_end,
        timezone,
    )


def parse_edit_datetime(
    date_value,
    hour_value,
    minute_value,
    timezone,
):
    try:
        target_date = datetime.strptime(
            date_value,
            "%Y-%m-%d",
        ).date()
        hour = int(hour_value)
        minute = int(minute_value)
    except (TypeError, ValueError):
        return None

    if hour not in range(24) or minute not in range(60):
        return None

    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        hour,
        minute,
        tzinfo=timezone,
    )


def preserve_seconds_if_same_minute(
    submitted,
    original,
):
    if submitted is None or original is None:
        return submitted

    if (
        submitted.year == original.year
        and submitted.month == original.month
        and submitted.day == original.day
        and submitted.hour == original.hour
        and submitted.minute == original.minute
    ):
        return submitted.replace(
            second=original.second,
            microsecond=original.microsecond,
        )

    return submitted


@app.get("/")
def index():
    with get_db() as connection:
        settings = load_settings(connection)
        timezone = get_configured_timezone(settings)
        now, day_start, day_end = get_day_bounds(timezone)
        today = now.date().isoformat()

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

        schedule_rows = connection.execute(
            """
            SELECT id, name, planned_start, planned_end, created_at
            FROM plans
            WHERE datetime(planned_start) < datetime(?)
              AND datetime(planned_end) > datetime(?)
            ORDER BY datetime(planned_start) ASC
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

    schedule_items = build_schedule_items(
        schedule_rows,
        day_start,
        day_end,
        timezone,
    )

    return render_template(
        "index.html",
        current_activity=current_activity,
        activity_groups=activity_groups,
        todos=todos,
        timeline_items=timeline_items,
        schedule_items=schedule_items,
        settings=settings,
        timezone_names=TIMEZONE_NAMES,
        today_date=today,
    )


@app.get("/timeline/edit-data.json")
def get_timeline_edit_data():
    settings = get_current_settings()
    timezone = get_configured_timezone(settings)
    now, day_start, day_end = get_day_bounds(timezone)
    today = now.date().isoformat()

    with get_db() as connection:
        activity_rows = connection.execute(
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

        schedule_rows = connection.execute(
            """
            SELECT id, name, planned_start, planned_end, created_at
            FROM plans
            WHERE datetime(planned_start) < datetime(?)
              AND datetime(planned_end) > datetime(?)
            ORDER BY datetime(planned_start) ASC
            """,
            (
                day_end.isoformat(timespec="seconds"),
                day_start.isoformat(timespec="seconds"),
            ),
        ).fetchall()

        todo_rows = connection.execute(
            """
            SELECT id
            FROM todos
            WHERE todo_date = ?
            ORDER BY
                CASE WHEN completed_at IS NULL THEN 0 ELSE 1 END,
                created_at ASC
            """,
            (today,),
        ).fetchall()

    activities = build_timeline_items(
        activity_rows,
        day_start,
        day_end,
        now,
        timezone,
    )
    schedules = build_schedule_items(
        schedule_rows,
        day_start,
        day_end,
        timezone,
    )

    return jsonify(
        {
            "activities": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "is_current": item["is_current"],
                    "start_date": item["edit_start_date"],
                    "start_hour": item["edit_start_hour"],
                    "start_minute": item["edit_start_minute"],
                    "end_date": item["edit_end_date"],
                    "end_hour": item["edit_end_hour"],
                    "end_minute": item["edit_end_minute"],
                }
                for item in activities
            ],
            "schedules": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "is_current": False,
                    "start_date": item["edit_start_date"],
                    "start_hour": item["edit_start_hour"],
                    "start_minute": item["edit_start_minute"],
                    "end_date": item["edit_end_date"],
                    "end_hour": item["edit_end_hour"],
                    "end_minute": item["edit_end_minute"],
                }
                for item in schedules
            ],
            "todos": [
                {"id": row["id"]}
                for row in todo_rows
            ],
        }
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


@app.post("/activity/<int:activity_id>/edit")
def edit_activity(activity_id):
    name = request.form.get("name", "").strip()

    if not name:
        return redirect(url_for("index"))

    settings = get_current_settings()
    timezone = get_configured_timezone(settings)

    with get_db() as connection:
        row = connection.execute(
            """
            SELECT id, name, started_at, ended_at
            FROM activities
            WHERE id = ?
            """,
            (activity_id,),
        ).fetchone()

        if row is None:
            return redirect(url_for("index"))

        original_start = convert_to_timezone(
            row["started_at"],
            timezone,
        )

        start = parse_edit_datetime(
            request.form.get("start_date"),
            request.form.get("start_hour"),
            request.form.get("start_minute"),
            timezone,
        )

        if start is None:
            return redirect(url_for("index"))

        start = preserve_seconds_if_same_minute(
            start,
            original_start,
        )

        if row["ended_at"] is None:
            if start > datetime.now(timezone):
                return redirect(url_for("index"))

            connection.execute(
                """
                UPDATE activities
                SET name = ?, started_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    start.isoformat(timespec="seconds"),
                    activity_id,
                ),
            )
        else:
            original_end = convert_to_timezone(
                row["ended_at"],
                timezone,
            )

            end = parse_edit_datetime(
                request.form.get("end_date"),
                request.form.get("end_hour"),
                request.form.get("end_minute"),
                timezone,
            )

            if end is None:
                return redirect(url_for("index"))

            end = preserve_seconds_if_same_minute(
                end,
                original_end,
            )

            if end <= start:
                return redirect(url_for("index"))

            connection.execute(
                """
                UPDATE activities
                SET name = ?, started_at = ?, ended_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    start.isoformat(timespec="seconds"),
                    end.isoformat(timespec="seconds"),
                    activity_id,
                ),
            )

    return redirect(url_for("index"))


@app.post("/schedule/add")
def add_schedule():
    name = request.form.get("name", "").strip()
    schedule_date = request.form.get("schedule_date", "").strip()
    start_hour = request.form.get("start_hour", "").strip()
    start_minute = request.form.get("start_minute", "").strip()
    end_hour = request.form.get("end_hour", "").strip()
    end_minute = request.form.get("end_minute", "").strip()

    if not all(
        (
            name,
            schedule_date,
            start_hour,
            start_minute,
            end_hour,
            end_minute,
        )
    ):
        return redirect(url_for("index"))

    try:
        target_date = datetime.strptime(
            schedule_date,
            "%Y-%m-%d",
        ).date()

        start_hour_value = int(start_hour)
        start_minute_value = int(start_minute)
        end_hour_value = int(end_hour)
        end_minute_value = int(end_minute)
    except ValueError:
        return redirect(url_for("index"))

    if (
        start_hour_value not in range(24)
        or end_hour_value not in range(24)
        or start_minute_value not in SCHEDULE_MINUTES
        or end_minute_value not in SCHEDULE_MINUTES
    ):
        return redirect(url_for("index"))

    settings = get_current_settings()
    timezone = get_configured_timezone(settings)
    now = datetime.now(timezone)

    planned_start = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        start_hour_value,
        start_minute_value,
        tzinfo=timezone,
    )
    planned_end = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        end_hour_value,
        end_minute_value,
        tzinfo=timezone,
    )

    if planned_end <= planned_start:
        return redirect(url_for("index"))

    with get_db() as connection:
        connection.execute(
            """
            INSERT INTO plans (
                name,
                planned_start,
                planned_end,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                planned_start.isoformat(timespec="seconds"),
                planned_end.isoformat(timespec="seconds"),
                now.isoformat(timespec="seconds"),
            ),
        )

    return redirect(url_for("index"))


@app.post("/schedule/<int:schedule_id>/edit")
def edit_schedule(schedule_id):
    name = request.form.get("name", "").strip()

    if not name:
        return redirect(url_for("index"))

    settings = get_current_settings()
    timezone = get_configured_timezone(settings)

    start = parse_edit_datetime(
        request.form.get("start_date"),
        request.form.get("start_hour"),
        request.form.get("start_minute"),
        timezone,
    )
    end = parse_edit_datetime(
        request.form.get("end_date"),
        request.form.get("end_hour"),
        request.form.get("end_minute"),
        timezone,
    )

    if start is None or end is None or end <= start:
        return redirect(url_for("index"))

    with get_db() as connection:
        connection.execute(
            """
            UPDATE plans
            SET name = ?, planned_start = ?, planned_end = ?
            WHERE id = ?
            """,
            (
                name,
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
                schedule_id,
            ),
        )

    return redirect(url_for("index"))


@app.get("/schedule/today.json")
def get_today_schedules():
    return jsonify(
        [
            {"id": item["id"]}
            for item in get_today_schedule_items()
        ]
    )


@app.post("/schedule/<int:schedule_id>/delete")
def delete_schedule(schedule_id):
    with get_db() as connection:
        connection.execute(
            "DELETE FROM plans WHERE id = ?",
            (schedule_id,),
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


@app.post("/todo/<int:todo_id>/delete")
def delete_todo(todo_id):
    with get_db() as connection:
        connection.execute(
            "DELETE FROM todos WHERE id = ?",
            (todo_id,),
        )

    return redirect(url_for("index"))


init_db()
