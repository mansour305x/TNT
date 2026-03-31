import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "portal.db"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSION_COOKIE = "member_portal_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
SECRET_KEY = os.getenv("PORTAL_SECRET_KEY", "change-me-in-production").encode("utf-8")

DEFAULT_FULL_ADMIN_USERNAME = os.getenv("PORTAL_FULL_ADMIN_USERNAME", "mn9@hotmail.com")
DEFAULT_FULL_ADMIN_PASSWORD = os.getenv("PORTAL_FULL_ADMIN_PASSWORD", "DANGER")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dropdown_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_key TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_required INTEGER NOT NULL DEFAULT 0,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS dropdown_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_id INTEGER NOT NULL,
                value TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 100,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(field_id, value),
                FOREIGN KEY(field_id) REFERENCES dropdown_fields(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS member_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL,
                member_uid TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS member_record_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                field_id INTEGER NOT NULL,
                option_value TEXT NOT NULL,
                FOREIGN KEY(record_id) REFERENCES member_records(id) ON DELETE CASCADE,
                FOREIGN KEY(field_id) REFERENCES dropdown_fields(id)
            );
            """
        )

        ensure_admin_account(
            conn,
            username="admin",
            password=os.getenv("PORTAL_ADMIN_PASSWORD", "admin123"),
        )
        ensure_admin_account(
            conn,
            username=DEFAULT_FULL_ADMIN_USERNAME,
            password=DEFAULT_FULL_ADMIN_PASSWORD,
        )


def ensure_admin_account(conn: sqlite3.Connection, username: str, password: str) -> None:
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? LIMIT 1",
        (username,),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE users SET password_hash = ?, is_admin = 1 WHERE id = ?",
            (hash_password(password), existing["id"]),
        )
        return

    conn.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
        (username, hash_password(password)),
    )


def hash_password(raw_password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), 130000
    ).hex()
    return f"{salt}${digest}"


def verify_password(raw_password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac(
        "sha256", raw_password.encode("utf-8"), salt.encode("utf-8"), 130000
    ).hex()
    return hmac.compare_digest(check, digest)


def sign_session(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session_cookie(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}:{expires_at}"
    signature = sign_session(payload)
    return f"{payload}:{signature}"


def parse_session_cookie(cookie_value: str | None) -> int | None:
    if not cookie_value:
        return None
    try:
        user_id_s, expires_s, signature = cookie_value.split(":", 2)
        payload = f"{user_id_s}:{expires_s}"
        if not hmac.compare_digest(signature, sign_session(payload)):
            return None
        if int(expires_s) < int(time.time()):
            return None
        return int(user_id_s)
    except (ValueError, TypeError):
        return None


def get_current_user(request: web.Request) -> dict[str, Any] | None:
    user_id = parse_session_cookie(request.cookies.get(SESSION_COOKIE))
    if not user_id:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, is_admin, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return None

    return dict(row)


def flash_response(location: str, message: str, level: str = "info") -> web.Response:
    resp = web.HTTPFound(location=location)
    safe_message = message.replace("|", " ")
    resp.set_cookie("flash", f"{level}|{safe_message}", max_age=12, httponly=True, samesite="Lax")
    return resp


def pop_flash(request: web.Request) -> dict[str, str] | None:
    data = request.cookies.get("flash")
    if not data or "|" not in data:
        return None
    level, text = data.split("|", 1)
    return {"level": level, "text": text}


def render_template(request: web.Request, template_name: str, context: dict[str, Any]) -> web.Response:
    env: Environment = request.app["jinja_env"]
    context["current_user"] = get_current_user(request)
    context["flash"] = pop_flash(request)
    html = env.get_template(template_name).render(**context)
    response = web.Response(text=html, content_type="text/html")
    if context["flash"]:
        response.del_cookie("flash")
    return response


def fetch_fields_and_options(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    fields = conn.execute(
        "SELECT id, field_key, label, sort_order, is_required FROM dropdown_fields ORDER BY sort_order, id"
    ).fetchall()

    result: list[dict[str, Any]] = []
    for field in fields:
        options = conn.execute(
            "SELECT id, value, sort_order FROM dropdown_options WHERE field_id = ? ORDER BY sort_order, id",
            (field["id"],),
        ).fetchall()
        result.append(
            {
                "id": field["id"],
                "field_key": field["field_key"],
                "label": field["label"],
                "sort_order": field["sort_order"],
                "is_required": bool(field["is_required"]),
                "options": [dict(opt) for opt in options],
            }
        )
    return result


async def index(request: web.Request) -> web.Response:
    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        records = conn.execute(
            """
            SELECT r.id, r.member_name, r.member_uid, r.created_at, u.username
            FROM member_records r
            LEFT JOIN users u ON u.id = r.created_by
            ORDER BY r.id DESC
            LIMIT 25
            """
        ).fetchall()

    records_list = [dict(r) for r in records]

    with get_db() as conn:
        values = conn.execute(
            """
            SELECT v.record_id, f.label, v.option_value
            FROM member_record_values v
            JOIN dropdown_fields f ON f.id = v.field_id
            ORDER BY v.id ASC
            """
        ).fetchall()

    values_by_record: dict[int, list[dict[str, str]]] = {}
    for row in values:
        values_by_record.setdefault(row["record_id"], []).append(
            {"label": row["label"], "value": row["option_value"]}
        )

    for rec in records_list:
        rec["dynamic_values"] = values_by_record.get(rec["id"], [])

    return render_template(
        request,
        "index.html",
        {
            "title": "Member Portal",
            "fields": fields,
            "records": records_list,
        },
    )


async def register_user(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if len(username) < 3 or len(password) < 6:
        return flash_response("/", "Username >= 3 chars and password >= 6 chars", "error")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 0)",
                (username, hash_password(password)),
            )
        except sqlite3.IntegrityError:
            return flash_response("/", "Username already exists", "error")

    return flash_response("/", "Account created. You can login now.", "success")


async def login_user(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        return flash_response("/", "Invalid username or password", "error")

    resp = web.HTTPFound(location="/")
    resp.set_cookie(
        SESSION_COOKIE,
        issue_session_cookie(user["id"]),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
    )
    resp.set_cookie("flash", "success|Logged in successfully", max_age=12, httponly=True, samesite="Lax")
    return resp


async def logout_user(request: web.Request) -> web.StreamResponse:
    resp = web.HTTPFound(location="/")
    resp.del_cookie(SESSION_COOKIE)
    resp.set_cookie("flash", "info|Logged out", max_age=12, httponly=True, samesite="Lax")
    return resp


async def create_record(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    member_name = str(data.get("member_name", "")).strip()
    member_uid = str(data.get("member_uid", "")).strip()

    if not member_name or not member_uid:
        return flash_response("/", "Member name and ID are required", "error")

    user = get_current_user(request)

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        missing_required = [
            f["label"]
            for f in fields
            if f["is_required"] and not str(data.get(f"field_{f['id']}", "")).strip()
        ]
        if missing_required:
            return flash_response("/", f"Required dropdowns missing: {', '.join(missing_required)}", "error")

        cur = conn.execute(
            "INSERT INTO member_records (member_name, member_uid, created_by) VALUES (?, ?, ?)",
            (member_name, member_uid, user["id"] if user else None),
        )
        record_id = int(cur.lastrowid)

        for field in fields:
            selected_value = str(data.get(f"field_{field['id']}", "")).strip()
            if selected_value:
                conn.execute(
                    "INSERT INTO member_record_values (record_id, field_id, option_value) VALUES (?, ?, ?)",
                    (record_id, field["id"], selected_value),
                )

    return flash_response("/", "Member record created", "success")


async def dashboard(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/", "Admin access required", "error")

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        users = conn.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY id DESC LIMIT 50"
        ).fetchall()

    return render_template(
        request,
        "dashboard.html",
        {
            "title": "Control Panel",
            "fields": fields,
            "users": [dict(u) for u in users],
        },
    )


async def add_field(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/", "Admin access required", "error")

    data = await request.post()
    label = str(data.get("label", "")).strip()
    field_key = str(data.get("field_key", "")).strip().lower().replace(" ", "_")
    sort_order = int(str(data.get("sort_order", "100")).strip() or "100")
    is_required = 1 if str(data.get("is_required", "")).strip() == "on" else 0

    if not label or not field_key:
        return flash_response("/dashboard", "Label and key are required", "error")

    with get_db() as conn:
        try:
            conn.execute(
                """
                INSERT INTO dropdown_fields (field_key, label, sort_order, is_required, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (field_key, label, sort_order, is_required, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/dashboard", "Field key already exists", "error")

    return flash_response("/dashboard", "Dropdown field added", "success")


async def delete_field(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/", "Admin access required", "error")

    field_id = int(request.match_info["field_id"])

    with get_db() as conn:
        conn.execute("DELETE FROM dropdown_fields WHERE id = ?", (field_id,))

    return flash_response("/dashboard", "Field deleted", "info")


async def add_option_admin(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/", "Admin access required", "error")

    data = await request.post()
    field_id = int(str(data.get("field_id", "0")).strip() or "0")
    value = str(data.get("value", "")).strip()
    sort_order = int(str(data.get("sort_order", "100")).strip() or "100")

    if not field_id or not value:
        return flash_response("/dashboard", "Field and value are required", "error")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO dropdown_options (field_id, value, sort_order, created_by) VALUES (?, ?, ?, ?)",
                (field_id, value, sort_order, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/dashboard", "Option already exists", "error")

    return flash_response("/dashboard", "Option added", "success")


async def contribute_option(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", "Login required to add options", "error")

    data = await request.post()
    field_id = int(str(data.get("field_id", "0")).strip() or "0")
    value = str(data.get("value", "")).strip()

    if not field_id or len(value) < 2:
        return flash_response("/", "Choose field and write valid option", "error")

    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM dropdown_fields WHERE id = ?", (field_id,)).fetchone()
        if not exists:
            return flash_response("/", "Dropdown field not found", "error")

        try:
            conn.execute(
                "INSERT INTO dropdown_options (field_id, value, sort_order, created_by) VALUES (?, ?, 100, ?)",
                (field_id, value, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/", "Option already exists", "error")

    return flash_response("/", "Option submitted successfully", "success")


def build_app() -> web.Application:
    init_db()

    app = web.Application()
    app["jinja_env"] = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    app.router.add_static("/static/", path=str(STATIC_DIR), name="static")
    app.router.add_get("/", index)
    app.router.add_post("/register", register_user)
    app.router.add_post("/login", login_user)
    app.router.add_get("/logout", logout_user)

    app.router.add_post("/records/create", create_record)

    app.router.add_get("/dashboard", dashboard)
    app.router.add_post("/dashboard/fields", add_field)
    app.router.add_post("/dashboard/fields/{field_id}/delete", delete_field)
    app.router.add_post("/dashboard/options", add_option_admin)

    app.router.add_post("/options/contribute", contribute_option)

    return app


if __name__ == "__main__":
    app = build_app()
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)
