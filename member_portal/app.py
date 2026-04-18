import hashlib
import hmac
import io
import csv
import json
import logging
import os
import secrets
import sqlite3
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from aiohttp import ClientSession, web
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


def resolve_db_path() -> Path:
    explicit_path = os.getenv("PORTAL_DB_PATH", "").strip()
    if explicit_path:
        p = Path(explicit_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
        except OSError:
            pass  # fall through to defaults
    if os.getenv("RENDER", "").lower() == "true":
        # Try the persistent disk path first, fallback to project dir
        candidates = [
            Path("/var/data/portal.db"),
            BASE_DIR / "portal.db",
            Path("/tmp/portal.db"),
        ]
        for candidate in candidates:
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                return candidate
            except OSError:
                continue

    return BASE_DIR / "portal.db"


DB_PATH = resolve_db_path()
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

SESSION_COOKIE = "member_portal_session"
LANG_COOKIE = "portal_lang"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
_raw_secret = os.getenv("PORTAL_SECRET_KEY", "")
if not _raw_secret:
    import warnings
    warnings.warn(
        "PORTAL_SECRET_KEY is not set. Using an insecure default — set this env var in production!",
        RuntimeWarning,
        stacklevel=1,
    )
    _raw_secret = "change-me-in-production"
SECRET_KEY = _raw_secret.encode("utf-8")
RESET_TOKEN_TTL_SECONDS = 60 * 30
EMAIL_VERIFY_TOKEN_TTL_SECONDS = 60 * 60

DEFAULT_FULL_ADMIN_USERNAME = os.getenv("PORTAL_FULL_ADMIN_USERNAME", "mn9@hotmail.com")
DEFAULT_FULL_ADMIN_PASSWORD = os.getenv("PORTAL_FULL_ADMIN_PASSWORD", "DANGER")

# ── Owner account (immutable super-admin) ─────────────────────────────────────
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "danger")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "Aa123456")

# ── State-account session cookie ──────────────────────────────────────────────
STATE_SESSION_COOKIE = "state_portal_session"

DEFAULT_LIST_CONFIGS = [
    {"list_key": "member_registry", "label": "Member Registry", "sort_order": 10, "is_enabled": 1},
    {"list_key": "transfers", "label": "Transfers List", "sort_order": 20, "is_enabled": 1},
]

TRANSLATIONS = {
    "en": {
        "login_required": "Please sign in first",
        "admin_required": "Admin access is required",
        "username_password_min": "Username must be at least 3 characters and password at least 6 characters",
        "username_exists": "Username already exists",
        "account_created": "Account created. You can sign in now",
        "invalid_login": "Invalid username or password",
        "invalid_email": "Please enter a valid email",
        "email_exists": "Email already exists",
        "email_or_username_required": "Enter username or email",
        "username_email_conflict": "Username cannot be an existing email",
        "email_username_conflict": "Email cannot match an existing username",
        "login_success": "Signed in successfully",
        "logout_success": "Signed out successfully",
        "oauth_unavailable": "This login provider is not configured yet",
        "oauth_google_missing": "Google login is not configured. Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI",
        "oauth_discord_missing": "Discord login is not configured. Add DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_REDIRECT_URI",
        "oauth_failed": "Social login failed. Please try again",
        "forgot_title": "TNT Alliance | Forgot Password",
        "forgot_success": "If the email exists, password reset instructions have been sent",

        "reset_invalid": "Invalid or expired reset link",
        "reset_password_min": "New password must be at least 6 characters",
        "reset_password_success": "Password has been reset. You can sign in now",
        "role_updated": "User role updated",
        "all_sessions_reset": "All users have been logged out successfully",
        "profile_title": "TNT Alliance | Profile",
        "profile_saved": "Profile updated successfully",
        "password_changed": "Password changed successfully",
        "email_verification_sent": "Verification email sent. Please confirm your new email",
        "email_verification_code_sent": "Verification code sent to your email",
        "email_saved_unverified": "Profile updated successfully",

        "email_verified_success": "Email verified successfully",
        "email_verify_invalid": "Invalid or expired verification link",
        "email_verify_code_invalid": "Invalid or expired verification code",
        "email_service_unavailable": "Email service is unavailable. Configure SMTP first",
        "smtp_settings_saved": "SMTP settings saved",
        "verify_email_title": "TNT Alliance | Verify Email",
        "current_password_required": "Current password is required",
        "current_password_invalid": "Current password is incorrect",
        "cannot_downgrade_full_admin": "Cannot remove admin role from the main full admin account",
        "member_required": "Player ID, Current Name, Alliance, and Rank are required",
        "required_missing": "Missing required fields: {fields}",
        "member_exists": "This member name is already registered",
        "member_saved": "Member record saved",
        "member_updated": "Member record updated",
        "member_deleted": "Member record deleted",
        "member_not_found": "Member record not found",
        "field_required": "Field label and key are required",
        "field_key_exists": "Field key already exists",
        "field_added": "Field added successfully",
        "field_deleted": "Field deleted",
        "option_required": "Choose a field and enter an option",
        "option_exists": "This option already exists",
        "option_added": "Option added successfully",
        "option_invalid": "Enter a valid option",
        "field_not_found": "Field not found",
        "state_number_required": "State number is required first",
        "alliance_tag_required": "Alliance tag is required",
        "alliance_tag_exists": "This alliance tag already exists for the selected state",
        "alliance_tag_added": "Alliance tag saved successfully",
        "alliance_tag_deleted": "Alliance tag deleted",
        "settings_saved": "Settings saved successfully",
        "list_updated": "List availability updated",
        "transfer_required": "Member name, member ID, power, furnace, current state, invite type, and future alliance are required",
        "transfer_saved": "Transfer record saved",
        "all_members_deleted": "All member records deleted",
        "all_transfers_deleted": "All transfer records deleted",
        "user_deleted": "User account deleted",
        "cannot_delete_self": "You cannot delete your own account",
        "cannot_delete_admin": "Cannot delete a protected admin account",
        "transfer_deleted": "Transfer record deleted",
        "code_resent": "Verification code has been resent to your email",
        "portal_title": "TNT Alliance | Portal",
        "lists_title": "TNT Alliance | Lists",
        "transfers_title": "TNT Alliance | Transfers",
        "members_title": "TNT Alliance | Members",
        "auth_title": "TNT Alliance | Login",
        "admin_title": "TNT Alliance | Admin",
    },
    "ar": {
        "login_required": "سجل الدخول أولاً",
        "admin_required": "صلاحية الأدمن مطلوبة",
        "username_password_min": "اسم المستخدم 3 أحرف وكلمة المرور 6 أحرف على الأقل",
        "username_exists": "اسم المستخدم مستخدم مسبقًا",
        "account_created": "تم إنشاء الحساب، سجل دخولك الآن",
        "invalid_login": "بيانات الدخول غير صحيحة",
        "invalid_email": "يرجى إدخال بريد إلكتروني صحيح",
        "email_exists": "البريد الإلكتروني مستخدم مسبقًا",
        "email_or_username_required": "أدخل اسم المستخدم أو البريد الإلكتروني",
        "username_email_conflict": "اسم المستخدم لا يمكن أن يطابق بريدًا إلكترونيًا موجودًا",
        "email_username_conflict": "البريد الإلكتروني لا يمكن أن يطابق اسم مستخدم موجودًا",
        "login_success": "تم تسجيل الدخول",
        "logout_success": "تم تسجيل الخروج",
        "oauth_unavailable": "موفر تسجيل الدخول هذا غير مُعد بعد",
        "oauth_google_missing": "تسجيل Google غير مُعد. أضف GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET و GOOGLE_REDIRECT_URI",
        "oauth_discord_missing": "تسجيل Discord غير مُعد. أضف DISCORD_CLIENT_ID و DISCORD_CLIENT_SECRET و DISCORD_REDIRECT_URI",
        "oauth_failed": "فشل تسجيل الدخول الاجتماعي، حاول مرة أخرى",
        "forgot_title": "تحالف TNT | نسيت كلمة المرور",
        "forgot_success": "إذا كان البريد موجودًا فسيتم إرسال تعليمات إعادة التعيين",

        "reset_invalid": "رابط إعادة التعيين غير صالح أو منتهي",
        "reset_password_min": "كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل",
        "reset_password_success": "تمت إعادة تعيين كلمة المرور، يمكنك تسجيل الدخول الآن",
        "role_updated": "تم تحديث صلاحية المستخدم",
        "all_sessions_reset": "تم تسجيل خروج جميع المستخدمين بنجاح",
        "profile_title": "تحالف TNT | الملف الشخصي",
        "profile_saved": "تم تحديث الملف الشخصي بنجاح",
        "password_changed": "تم تغيير كلمة المرور بنجاح",
        "email_verification_sent": "تم إرسال رسالة تحقق، يرجى تأكيد بريدك الجديد",
        "email_verification_code_sent": "تم إرسال رمز التحقق إلى بريدك",
        "email_saved_unverified": "تم تحديث الملف الشخصي بنجاح",

        "email_verified_success": "تم توثيق البريد الإلكتروني بنجاح",
        "email_verify_invalid": "رابط التحقق غير صالح أو منتهي",
        "email_verify_code_invalid": "رمز التحقق غير صالح أو منتهي",
        "email_service_unavailable": "خدمة البريد غير متاحة. اضبط إعدادات SMTP أولاً",
        "smtp_settings_saved": "تم حفظ إعدادات SMTP",
        "verify_email_title": "تحالف TNT | توثيق البريد",
        "current_password_required": "كلمة المرور الحالية مطلوبة",
        "current_password_invalid": "كلمة المرور الحالية غير صحيحة",
        "cannot_downgrade_full_admin": "لا يمكن سحب صلاحية الأدمن من حساب الأدمن الرئيسي",
        "member_required": "Player ID و Current Name و Alliance و Rank مطلوبة",
        "required_missing": "حقول مطلوبة ناقصة: {fields}",
        "member_exists": "اسم العضو مسجل مسبقًا",
        "member_saved": "تم حفظ سجل العضو",
        "member_updated": "تم تحديث سجل العضو",
        "member_deleted": "تم حذف سجل العضو",
        "member_not_found": "سجل العضو غير موجود",
        "field_required": "عنوان ومفتاح الحقل مطلوبان",
        "field_key_exists": "مفتاح الحقل مستخدم",
        "field_added": "تمت إضافة الحقل",
        "field_deleted": "تم حذف الحقل",
        "option_required": "اختر الحقل واكتب الخيار",
        "option_exists": "الخيار موجود مسبقًا",
        "option_added": "تمت إضافة الخيار",
        "option_invalid": "اكتب خيارًا صالحًا",
        "field_not_found": "الحقل غير موجود",
        "state_number_required": "يجب تسجيل رقم الولاية أولاً",
        "alliance_tag_required": "شعار أو اختصار التحالف مطلوب",
        "alliance_tag_exists": "شعار التحالف مسجل مسبقًا في هذه الولاية",
        "alliance_tag_added": "تم حفظ شعار التحالف",
        "alliance_tag_deleted": "تم حذف شعار التحالف",
        "settings_saved": "تم حفظ الإعدادات بنجاح",
        "list_updated": "تم تحديث حالة القائمة",
        "transfer_required": "اسم العضو ومعرف العضو والقوة والفرن والولاية الحالية ونوع الدعوة والتحالف المستقبلي مطلوبة",
        "transfer_saved": "تم حفظ سجل التحويل",
        "all_members_deleted": "تم حذف جميع سجلات الأعضاء",
        "all_transfers_deleted": "تم حذف جميع سجلات التحويلات",
        "user_deleted": "تم حذف حساب المستخدم",
        "cannot_delete_self": "لا يمكنك حذف حسابك الخاص",
        "cannot_delete_admin": "لا يمكن حذف حساب الأدمن المحمي",
        "transfer_deleted": "تم حذف سجل التحويل",
        "code_resent": "تم إعادة إرسال رمز التحقق إلى بريدك",
        "portal_title": "تحالف TNT | التسجيل",
        "lists_title": "تحالف TNT | القوائم",
        "transfers_title": "تحالف TNT | التحويلات",
        "members_title": "تحالف TNT | الأعضاء",
        "auth_title": "تحالف TNT | الدخول",
        "admin_title": "تحالف TNT | الإدارة",
    },
}

TROOP_OPTIONS = [
    "FC1",
    "FC2",
    "FC3",
    "FC4",
    "FC5",
    "FC6",
    "FC7",
    "FC8",
    "FC9",
    "FC10",
    "T11",
    "T12",
]

DEFAULT_DROPDOWN_FIELDS = [
    {
        "field_key": "infantry",
        "label": "Infantry",
        "sort_order": 10,
        "is_required": 1,
        "options": TROOP_OPTIONS,
    },
    {
        "field_key": "lancer",
        "label": "Lancer",
        "sort_order": 20,
        "is_required": 1,
        "options": TROOP_OPTIONS,
    },
    {
        "field_key": "marksman",
        "label": "Marksman",
        "sort_order": 30,
        "is_required": 1,
        "options": TROOP_OPTIONS,
    },
    {
        "field_key": "status",
        "label": "Status",
        "sort_order": 40,
        "is_required": 1,
        "options": ["Active", "Inactive"],
    },
]


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
                alliance TEXT NOT NULL DEFAULT '',
                rank TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS portal_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS state_alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_number TEXT NOT NULL,
                alliance_tag TEXT NOT NULL,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(state_number, alliance_tag),
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS list_configs (
                list_key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 100,
                is_enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS transfer_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_name TEXT NOT NULL,
                member_uid TEXT NOT NULL,
                power TEXT NOT NULL,
                furnace TEXT NOT NULL,
                current_state TEXT NOT NULL,
                invite_type TEXT NOT NULL DEFAULT '',
                future_alliance TEXT NOT NULL,
                created_by INTEGER,
                state_account_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS state_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state_name TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feature_key TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                feature_type TEXT NOT NULL DEFAULT 'function',
                is_enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        migrate_member_record_columns(conn)
        migrate_user_state_column(conn)
        migrate_user_auth_columns(conn)
        ensure_user_session_nonces(conn)
        migrate_transfer_record_columns(conn)
        migrate_state_account_id_columns(conn)
        migrate_user_is_owner_column(conn)
        create_oauth_identities_table(conn)
        create_password_resets_table(conn)
        create_email_verifications_table(conn)
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
        ensure_owner_account(conn)
        ensure_default_dropdown_fields(conn)
        ensure_default_list_configs(conn)


def migrate_member_record_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(member_records)").fetchall()
    }
    if "alliance" not in columns:
        conn.execute("ALTER TABLE member_records ADD COLUMN alliance TEXT NOT NULL DEFAULT ''")
    if "rank" not in columns:
        conn.execute("ALTER TABLE member_records ADD COLUMN rank TEXT NOT NULL DEFAULT ''")
    if "notes" not in columns:
        conn.execute("ALTER TABLE member_records ADD COLUMN notes TEXT NOT NULL DEFAULT ''")


def migrate_user_state_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "state" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN state TEXT NOT NULL DEFAULT ''")


def migrate_user_auth_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT NOT NULL DEFAULT ''")
    if "auth_provider" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email'")
    if "email_verified" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
    if "session_nonce" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN session_nonce TEXT NOT NULL DEFAULT ''")


def ensure_user_session_nonces(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id FROM users WHERE session_nonce = '' OR session_nonce IS NULL"
    ).fetchall()
    for row in rows:
        conn.execute(
            "UPDATE users SET session_nonce = ? WHERE id = ?",
            (generate_session_nonce(), row["id"]),
        )


def create_oauth_identities_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS oauth_identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, provider_user_id),
            UNIQUE(user_id, provider),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def create_password_resets_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at INTEGER NOT NULL,
            used_at INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def create_email_verifications_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            new_email TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at INTEGER NOT NULL,
            used_at INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def migrate_transfer_record_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(transfer_records)").fetchall()}
    if "invite_type" not in columns:
        conn.execute("ALTER TABLE transfer_records ADD COLUMN invite_type TEXT NOT NULL DEFAULT ''")


def migrate_state_account_id_columns(conn: sqlite3.Connection) -> None:
    tr_cols = {row["name"] for row in conn.execute("PRAGMA table_info(transfer_records)").fetchall()}
    if "state_account_id" not in tr_cols:
        conn.execute("ALTER TABLE transfer_records ADD COLUMN state_account_id INTEGER")
    mr_cols = {row["name"] for row in conn.execute("PRAGMA table_info(member_records)").fetchall()}
    if "state_account_id" not in mr_cols:
        conn.execute("ALTER TABLE member_records ADD COLUMN state_account_id INTEGER")


def migrate_user_is_owner_column(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "is_owner" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_owner INTEGER NOT NULL DEFAULT 0")


def ensure_default_dropdown_fields(conn: sqlite3.Connection) -> None:
    for field in DEFAULT_DROPDOWN_FIELDS:
        existing = conn.execute(
            "SELECT id FROM dropdown_fields WHERE field_key = ? LIMIT 1",
            (field["field_key"],),
        ).fetchone()

        if existing:
            field_id = int(existing["id"])
            conn.execute(
                "UPDATE dropdown_fields SET label = ?, sort_order = ?, is_required = ? WHERE id = ?",
                (field["label"], field["sort_order"], field["is_required"], field_id),
            )
        else:
            cur = conn.execute(
                "INSERT INTO dropdown_fields (field_key, label, sort_order, is_required) VALUES (?, ?, ?, ?)",
                (field["field_key"], field["label"], field["sort_order"], field["is_required"]),
            )
            field_id = int(cur.lastrowid)

        for sort_order, option_value in enumerate(field["options"], start=1):
            conn.execute(
                """
                INSERT INTO dropdown_options (field_id, value, sort_order)
                VALUES (?, ?, ?)
                ON CONFLICT(field_id, value) DO UPDATE SET sort_order = excluded.sort_order
                """,
                (field_id, option_value, sort_order),
            )


def ensure_default_list_configs(conn: sqlite3.Connection) -> None:
    for item in DEFAULT_LIST_CONFIGS:
        conn.execute(
            """
            INSERT INTO list_configs (list_key, label, sort_order, is_enabled)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(list_key) DO UPDATE SET label = excluded.label, sort_order = excluded.sort_order
            """,
            (item["list_key"], item["label"], item["sort_order"], item["is_enabled"]),
        )


def ensure_admin_account(conn: sqlite3.Connection, username: str, password: str) -> None:
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? LIMIT 1",
        (username,),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE users SET password_hash = ?, is_admin = 1, auth_provider = 'email', session_nonce = ? WHERE id = ?",
            (hash_password(password), generate_session_nonce(), existing["id"]),
        )
        return

    conn.execute(
        "INSERT INTO users (username, password_hash, is_admin, email, auth_provider, session_nonce) VALUES (?, ?, 1, '', 'email', ?)",
        (username, hash_password(password), generate_session_nonce()),
    )


def ensure_owner_account(conn: sqlite3.Connection) -> None:
    """Create or update the immutable owner account 'danger'."""
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? LIMIT 1",
        (OWNER_USERNAME,),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE users SET is_admin = 1, is_owner = 1, auth_provider = 'email' WHERE id = ?",
            (existing["id"],),
        )
    else:
        conn.execute(
            "INSERT INTO users (username, password_hash, is_admin, is_owner, email, auth_provider, session_nonce) VALUES (?, ?, 1, 1, '', 'email', ?)",
            (OWNER_USERNAME, hash_password(OWNER_PASSWORD), generate_session_nonce()),
        )


def normalize_email(raw_email: str) -> str:
    return raw_email.strip().lower()


def is_valid_email(raw_email: str) -> bool:
    email = normalize_email(raw_email)
    return "@" in email and "." in email.split("@")[-1] and len(email) >= 6


def get_user_for_login(conn: sqlite3.Connection, login_id: str) -> sqlite3.Row | None:
    # If input looks like email, try email column first then fall back to
    # username column. The fallback handles admin accounts whose username
    # contains '@' but whose email column is empty (e.g. mn9@hotmail.com).
    if "@" in login_id:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ? LIMIT 1",
            (normalize_email(login_id),),
        ).fetchone()
        if row:
            return row
        # Fallback: admin/system accounts may use an email-like string as username
        return conn.execute(
            "SELECT id, password_hash FROM users WHERE username = ? LIMIT 1",
            (login_id,),
        ).fetchone()
    return conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ? LIMIT 1",
        (login_id,),
    ).fetchone()


def is_full_admin_username(username: str) -> bool:
    return username.strip().lower() in {
        "admin",
        DEFAULT_FULL_ADMIN_USERNAME.strip().lower(),
        OWNER_USERNAME.strip().lower(),
    }


# ── State account helpers ─────────────────────────────────────────────────────

def issue_state_session_cookie(state_account_id: int) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"state:{state_account_id}:{expires_at}"
    signature = sign_session(payload)
    return f"{payload}:{signature}"


def parse_state_session_cookie(cookie_value: str | None) -> int | None:
    """Return state_account_id or None."""
    if not cookie_value:
        return None
    try:
        prefix, state_id_s, expires_s, signature = cookie_value.split(":", 3)
        if prefix != "state":
            return None
        payload = f"state:{state_id_s}:{expires_s}"
        if not hmac.compare_digest(signature, sign_session(payload)):
            return None
        if int(expires_s) < int(time.time()):
            return None
        return int(state_id_s)
    except (ValueError, TypeError):
        return None


def get_current_state_account(request: web.Request) -> dict[str, Any] | None:
    state_id = parse_state_session_cookie(request.cookies.get(STATE_SESSION_COOKIE))
    if not state_id:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, state_name, created_at FROM state_accounts WHERE id = ?",
            (state_id,),
        ).fetchone()
    if not row:
        return None
    return dict(row)


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


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_session_nonce() -> str:
    return secrets.token_hex(16)


def rotate_session_nonce(conn: sqlite3.Connection, user_id: int) -> str:
    nonce = generate_session_nonce()
    conn.execute("UPDATE users SET session_nonce = ? WHERE id = ?", (nonce, user_id))
    return nonce


def build_public_origin(request: web.Request) -> str:
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    return f"{request.scheme}://{request.host}"


def issue_oauth_state(provider: str) -> str:
    expires_at = int(time.time()) + 600
    nonce = secrets.token_hex(12)
    payload = f"{provider}:{expires_at}:{nonce}"
    signature = sign_session(payload)
    return f"{payload}:{signature}"


def parse_oauth_state(state_token: str | None) -> str | None:
    if not state_token:
        return None
    try:
        provider, expires_s, nonce, signature = state_token.split(":", 3)
        payload = f"{provider}:{expires_s}:{nonce}"
        if not hmac.compare_digest(signature, sign_session(payload)):
            return None
        if int(expires_s) < int(time.time()):
            return None
        return provider
    except (TypeError, ValueError):
        return None


def sign_session(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_session_cookie(user_id: int, session_nonce: str) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}:{expires_at}:{session_nonce}"
    signature = sign_session(payload)
    return f"{payload}:{signature}"


def parse_session_cookie(cookie_value: str | None) -> tuple[int, str] | None:
    if not cookie_value:
        return None
    try:
        user_id_s, expires_s, nonce, signature = cookie_value.split(":", 3)
        payload = f"{user_id_s}:{expires_s}:{nonce}"
        if not hmac.compare_digest(signature, sign_session(payload)):
            return None
        if int(expires_s) < int(time.time()):
            return None
        return (int(user_id_s), nonce)
    except (ValueError, TypeError):
        return None


def get_current_user(request: web.Request) -> dict[str, Any] | None:
    session_data = parse_session_cookie(request.cookies.get(SESSION_COOKIE))
    if not session_data:
        return None
    user_id, cookie_nonce = session_data

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username, email, email_verified, is_admin, is_owner, created_at, state, session_nonce FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return None

    if str(row["session_nonce"] or "") != cookie_nonce:
        return None

    return dict(row)


def get_lang(request: web.Request) -> str:
    lang = str(request.cookies.get(LANG_COOKIE, "en")).lower()
    if lang not in {"ar", "en"}:
        return "en"
    return lang


def translate_text(lang: str, key: str, **kwargs: Any) -> str:
    text = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text


def translate_request(request: web.Request, key: str, **kwargs: Any) -> str:
    return translate_text(get_lang(request), key, **kwargs)


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
    context["lang"] = get_lang(request)
    context["request_path"] = request.path_qs
    context["tr"] = lambda key, **kwargs: translate_text(context["lang"], key, **kwargs)
    html = env.get_template(template_name).render(**context)
    response = web.Response(text=html, content_type="text/html")
    if context["flash"]:
        response.del_cookie("flash")
    return response


def get_oauth_config(provider: str) -> dict[str, str] | None:
    p = provider.lower().strip()
    if p == "google":
        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
        if not all([client_id, client_secret, redirect_uri]):
            return None
        return {
            "provider": "google",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "scope": "openid email profile",
        }

    if p == "discord":
        client_id = os.getenv("DISCORD_CLIENT_ID", "").strip()
        client_secret = os.getenv("DISCORD_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv("DISCORD_REDIRECT_URI", "").strip()
        if not all([client_id, client_secret, redirect_uri]):
            return None
        return {
            "provider": "discord",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "authorize_url": "https://discord.com/api/oauth2/authorize",
            "token_url": "https://discord.com/api/oauth2/token",
            "userinfo_url": "https://discord.com/api/users/@me",
            "scope": "identify email",
        }

    return None


def ensure_unique_username(conn: sqlite3.Connection, base_username: str) -> str:
    candidate = base_username
    for i in range(1, 2000):
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ? LIMIT 1",
            (candidate,),
        ).fetchone()
        if not exists:
            return candidate
        candidate = f"{base_username}{i}"
    return f"{base_username}_{secrets.token_hex(2)}"


def upsert_oauth_user(
    conn: sqlite3.Connection,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str,
) -> int:
    identity = conn.execute(
        """
        SELECT u.id
        FROM oauth_identities oi
        JOIN users u ON u.id = oi.user_id
        WHERE oi.provider = ? AND oi.provider_user_id = ?
        LIMIT 1
        """,
        (provider, provider_user_id),
    ).fetchone()
    if identity:
        return int(identity["id"])

    user_row = None
    if email:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ? LIMIT 1",
            (email,),
        ).fetchone()

    if user_row:
        user_id = int(user_row["id"])
    else:
        safe_seed = "".join(ch for ch in display_name.lower() if ch.isalnum())[:14] or provider
        if len(safe_seed) < 3:
            safe_seed = f"{provider}user"
        username = ensure_unique_username(conn, f"{safe_seed}_{provider}"[:20])
        password_hash = hash_password(secrets.token_urlsafe(24))
        cur = conn.execute(
            """
            INSERT INTO users (username, password_hash, is_admin, state, email, auth_provider, session_nonce)
            VALUES (?, ?, 0, '', ?, ?, ?)
            """,
            (username, password_hash, email, provider, generate_session_nonce()),
        )
        user_id = int(cur.lastrowid)

    conn.execute(
        """
        INSERT INTO oauth_identities (user_id, provider, provider_user_id)
        VALUES (?, ?, ?)
        ON CONFLICT(provider, provider_user_id) DO NOTHING
        """,
        (user_id, provider, provider_user_id),
    )
    return user_id


def send_smtp_message(subject: str, target_email: str, body: str) -> bool:
    cfg = get_smtp_config()
    smtp_host = cfg["host"]
    smtp_port = cfg["port"]
    smtp_user = cfg["user"]
    smtp_password = cfg["password"]
    smtp_from = cfg["from"] or smtp_user

    # Debug: Print configuration status

    if not smtp_host:
        print("[SMTP ERROR] Missing SMTP_HOST", flush=True)
        return False
    if not smtp_user:
        print("[SMTP ERROR] Missing SMTP_USER", flush=True)
        return False
    if not smtp_password:
        print("[SMTP ERROR] Missing SMTP_PASSWORD", flush=True)
        return False
    if not smtp_from:
        print("[SMTP ERROR] Missing SMTP_FROM", flush=True)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = target_email
    msg.set_content(body)

    try:
        import logging; logging.info(f"[SMTP] Attempting to send to {target_email} via {smtp_host}:{smtp_port}")
        # Port 465 typically requires implicit SSL, while 587 uses STARTTLS.
        if int(smtp_port) == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(smtp_user, smtp_password)
                smtp.send_message(msg)
        import logging; logging.info(f"[SMTP] Message sent to {target_email}")
        return True
    except Exception as exc:
        import logging; logging.warning(f"[SMTP] send failed to {target_email}: {type(exc).__name__}: {exc}")
        return False


def send_password_reset_email(target_email: str, reset_link: str) -> bool:
    return send_smtp_message(
        subject="TNT Portal Password Reset",
        target_email=target_email,
        body=(
            "Use this link to reset your password:\n"
            f"{reset_link}\n\n"
            "If you did not request this, ignore this email."
        ),
    )


def send_email_verification_email(target_email: str, verify_code: str) -> bool:
    return send_smtp_message(
        subject="TNT Portal Email Verification",
        target_email=target_email,
        body=(
            "Use this verification code to confirm your email:\n"
            f"{verify_code}\n\n"
            "This code expires in 60 minutes. If you did not request this, ignore this email."
        ),
    )


def get_smtp_config() -> dict[str, Any]:
    env_host = os.getenv("SMTP_HOST", "").strip()
    env_port_raw = os.getenv("SMTP_PORT", "587").strip() or "587"
    env_user = os.getenv("SMTP_USER", "").strip()
    env_password = os.getenv("SMTP_PASSWORD", "").strip()
    env_from = os.getenv("SMTP_FROM", env_user).strip()

    try:
        env_port = int(env_port_raw)
    except ValueError:
        env_port = 587


    with get_db() as conn:
        host = get_setting(conn, "smtp_host", env_host).strip()
        port_raw = get_setting(conn, "smtp_port", str(env_port)).strip() or str(env_port)
        user = get_setting(conn, "smtp_user", env_user).strip()
        password = get_setting(conn, "smtp_password", env_password).strip()
        sender = get_setting(conn, "smtp_from", env_from or user).strip()

    try:
        port = int(port_raw)
    except ValueError:
        port = env_port

    if not sender:
        sender = user


    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from": sender,
    }


def is_smtp_configured() -> bool:
    cfg = get_smtp_config()
    return bool(cfg["host"] and cfg["user"] and cfg["password"])


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


def get_setting(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute(
        "SELECT setting_value FROM portal_settings WHERE setting_key = ? LIMIT 1",
        (key,),
    ).fetchone()
    if not row:
        return default
    value = str(row["setting_value"])
    return value


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO portal_settings (setting_key, setting_value)
        VALUES (?, ?)
        ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
        """,
        (key, value),
    )


def fetch_state_alliances(conn: sqlite3.Connection, state_number: str) -> list[dict[str, Any]]:
    rows = conn.execute(
    """
        SELECT a.id, a.state_number, a.alliance_tag, a.created_at, u.username
        FROM state_alliances a
        LEFT JOIN users u ON u.id = a.created_by
        WHERE a.state_number = ?
        ORDER BY a.alliance_tag COLLATE NOCASE ASC, a.id ASC
        """,
        (state_number,),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_list_configs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT list_key, label, sort_order, is_enabled FROM list_configs ORDER BY sort_order, list_key"
    ).fetchall()
    return [dict(row) for row in rows]


def is_list_enabled(conn: sqlite3.Connection, list_key: str) -> bool:
    row = conn.execute(
        "SELECT is_enabled FROM list_configs WHERE list_key = ? LIMIT 1",
        (list_key,),
    ).fetchone()
    if not row:
        return False
    return bool(row["is_enabled"])


def build_portal_cards(lang: str, configs: list[dict[str, Any]]) -> list[dict[str, str]]:
    metadata = {
        "member_registry": {
            "title_en": "Member Registry",
            "title_ar": "سجل الأعضاء",
            "desc_en": "Register alliance members with fixed fields and troop levels.",
            "desc_ar": "تسجيل أعضاء التحالف مع الحقول الثابتة ومستويات القوات.",
            "href": "/member-records/new",
        },
        "transfers": {
            "title_en": "Transfers List",
            "title_ar": "قائمة التحويلات",
            "desc_en": "Track transfer requests using the state alliances dropdown.",
            "desc_ar": "تسجيل التحويلات باستخدام قائمة تحالفات الولاية المنسدلة.",
            "href": "/transfers",
        },
    }
    cards: list[dict[str, str]] = []
    for item in configs:
        if not item["is_enabled"] or item["list_key"] not in metadata:
            continue
        meta = metadata[item["list_key"]]
        cards.append(
            {
                "list_key": item["list_key"],
                "title": meta["title_en"] if lang == "en" else meta["title_ar"],
                "description": meta["desc_en"] if lang == "en" else meta["desc_ar"],
                "href": meta["href"],
            }
        )
    return cards


async def auth_page(request: web.Request) -> web.Response:
    if get_current_user(request):
        raise web.HTTPFound(location="/portal")
    return render_template(
        request,
        "auth.html",
        {
            "title": translate_request(request, "auth_title"),
        },
    )


async def register_page(request: web.Request) -> web.Response:
    if get_current_user(request):
        raise web.HTTPFound(location="/portal")
    lang = get_lang(request)
    return render_template(
        request,
        "register.html",
        {
            "title": "TNT Alliance | Register" if lang == "en" else "تحالف TNT | التسجيل",
        },
    )


async def forgot_password_page(request: web.Request) -> web.Response:
    if get_current_user(request):
        raise web.HTTPFound(location="/portal")
    return render_template(
        request,
        "forgot_password.html",
        {
            "title": translate_request(request, "forgot_title"),
        },
    )


async def reset_password_page(request: web.Request) -> web.Response:
    token = str(request.query.get("token", "")).strip()
    if not token:
        return flash_response("/forgot-password", translate_request(request, "reset_invalid"), "error")

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM password_resets
            WHERE token_hash = ? AND used_at IS NULL AND expires_at >= ?
            LIMIT 1
            """,
            (hash_reset_token(token), int(time.time())),
        ).fetchone()

    if not row:
        return flash_response("/forgot-password", translate_request(request, "reset_invalid"), "error")

    return render_template(
        request,
        "reset_password.html",
        {
            "title": "TNT Alliance | Reset Password" if get_lang(request) == "en" else "تحالف TNT | إعادة تعيين كلمة المرور",
            "token": token,
        },
    )


async def portal_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        list_configs = fetch_list_configs(conn)
        state_number = get_setting(conn, "state_number")
        alliances = fetch_state_alliances(conn, state_number) if state_number else []

    return render_template(
        request,
        "portal_home.html",
        {
            "title": translate_request(request, "lists_title"),
            "cards": build_portal_cards(get_lang(request), list_configs),
            "state_number": state_number,
            "alliances": alliances,
        },
    )


async def member_registry_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)

    return render_template(
        request,
        "index.html",
        {
            "title": translate_request(request, "portal_title"),
            "fields": fields,
        },
    )


async def members_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        records = conn.execute(
            """
            SELECT r.id, r.member_name, r.member_uid, r.alliance, r.rank, r.notes, r.created_at, u.username
            FROM member_records r
            LEFT JOIN users u ON u.id = r.created_by
            WHERE r.state_account_id IS NULL
            ORDER BY r.id DESC
            LIMIT 100
            """
        ).fetchall()
        values = conn.execute(
            """
            SELECT v.record_id, f.label, v.option_value
            FROM member_record_values v
            JOIN dropdown_fields f ON f.id = v.field_id
            WHERE v.record_id IN (
                SELECT id FROM member_records WHERE state_account_id IS NULL
            )
            ORDER BY v.id ASC
            """
        ).fetchall()

    records_list = [dict(r) for r in records]
    values_by_record: dict[int, list[dict[str, str]]] = {}
    for row in values:
        values_by_record.setdefault(row["record_id"], []).append(
            {"label": row["label"], "value": row["option_value"]}
        )

    for rec in records_list:
        dv_list = values_by_record.get(rec["id"], [])
        rec["dynamic_values"] = dv_list
        rec["dv_by_label"] = {item["label"]: item["value"] for item in dv_list}

    return render_template(
        request,
        "members.html",
        {
            "title": translate_request(request, "members_title"),
            "records": records_list,
            "fields": fields,
        },
    )


async def transfers_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        if not is_list_enabled(conn, "transfers") and not user["is_admin"]:
            return flash_response("/portal", translate_request(request, "admin_required"), "error")

        state_number = get_setting(conn, "state_number")
        alliances = fetch_state_alliances(conn, state_number) if state_number else []
        records = conn.execute(
            """
            SELECT t.id, t.member_name, t.member_uid, t.power, t.furnace, t.current_state, t.invite_type, t.future_alliance, t.created_at, u.username
            FROM transfer_records t
            LEFT JOIN users u ON u.id = t.created_by
            WHERE t.state_account_id IS NULL
            ORDER BY t.id DESC
            LIMIT 100
            """
        ).fetchall()

    return render_template(
        request,
        "transfers.html",
        {
            "title": translate_request(request, "transfers_title"),
            "state_number": state_number,
            "alliances": alliances,
            "records": [dict(row) for row in records],
        },
    )


async def profile_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        pending_verification = conn.execute(
            """
            SELECT 1
            FROM email_verifications
            WHERE user_id = ? AND used_at IS NULL AND expires_at >= ?
            LIMIT 1
            """,
            (user["id"], int(time.time())),
        ).fetchone()

    smtp_configured = is_smtp_configured()

    return render_template(
        request,
        "profile.html",
        {
            "title": translate_request(request, "profile_title"),
            "has_pending_email_verification": bool(pending_verification) and smtp_configured,
            "smtp_configured": smtp_configured,
        },
    )


async def verify_profile_email_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    with get_db() as conn:
        pending = conn.execute(
            """
            SELECT new_email, expires_at
            FROM email_verifications
            WHERE user_id = ? AND used_at IS NULL AND expires_at >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"], int(time.time())),
        ).fetchone()

    if not pending:
        return flash_response("/profile", translate_request(request, "email_verify_code_invalid"), "error")

    return render_template(
        request,
        "verify_email_code.html",
        {
            "title": translate_request(request, "verify_email_title"),
            "pending_email": pending["new_email"],
        },
    )


async def set_language(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    selected_lang = str(data.get("lang", "en")).strip().lower()
    next_path = str(data.get("next", "/")).strip() or "/"

    if selected_lang not in {"ar", "en"}:
        selected_lang = "en"

    resp = web.HTTPFound(location=next_path)
    resp.set_cookie(LANG_COOKIE, selected_lang, max_age=31536000, samesite="Lax")
    return resp


async def register_user(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()
    email = normalize_email(str(data.get("email", "")))
    state = str(data.get("state", "")).strip()

    if len(username) < 3 or len(password) < 6:
        return flash_response("/register-page", translate_request(request, "username_password_min"), "error")
    if not is_valid_email(email):
        return flash_response("/register-page", translate_request(request, "invalid_email"), "error")

    with get_db() as conn:
        username_conflicts_email = conn.execute(
            "SELECT 1 FROM users WHERE email = ? LIMIT 1",
            (normalize_email(username),),
        ).fetchone()
        if username_conflicts_email:
            return flash_response("/register-page", translate_request(request, "username_email_conflict"), "error")

        email_conflicts_username = conn.execute(
            "SELECT 1 FROM users WHERE username = ? LIMIT 1",
            (email,),
        ).fetchone()
        if email_conflicts_username:
            return flash_response("/register-page", translate_request(request, "email_username_conflict"), "error")

        email_exists = conn.execute("SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
        if email_exists:
            return flash_response("/register-page", translate_request(request, "email_exists"), "error")
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, is_admin, state, email, auth_provider, session_nonce) VALUES (?, ?, 0, ?, ?, 'email', ?)",
                (username, hash_password(password), state, email, generate_session_nonce()),
            )
        except sqlite3.IntegrityError:
            return flash_response("/register-page", translate_request(request, "username_exists"), "error")

    return flash_response("/", translate_request(request, "account_created"), "success")


async def login_user(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    login_id = str(data.get("login_id", "")).strip()
    password = str(data.get("password", "")).strip()

    if not login_id:
        return flash_response("/", translate_request(request, "email_or_username_required"), "error")

    with get_db() as conn:
        user = get_user_for_login(conn, login_id)

    if not user or not verify_password(password, user["password_hash"]):
        # Prevent stale sessions from showing another account after a failed login attempt.
        existing_session = parse_session_cookie(request.cookies.get(SESSION_COOKIE))
        if existing_session:
            with get_db() as conn:
                rotate_session_nonce(conn, existing_session[0])

        resp = flash_response("/", translate_request(request, "invalid_login"), "error")
        resp.del_cookie(SESSION_COOKIE)
        return resp

    with get_db() as conn:
        new_nonce = rotate_session_nonce(conn, int(user["id"]))

    resp = web.HTTPFound(location="/portal")
    resp.set_cookie(
        SESSION_COOKIE,
        issue_session_cookie(int(user["id"]), new_nonce),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
    )
    resp.set_cookie("flash", f"success|{translate_request(request, 'login_success')}", max_age=12, httponly=True, samesite="Lax")
    return resp


async def logout_user(request: web.Request) -> web.StreamResponse:
    session_data = parse_session_cookie(request.cookies.get(SESSION_COOKIE))
    if session_data:
        with get_db() as conn:
            rotate_session_nonce(conn, session_data[0])
    resp = web.HTTPFound(location="/")
    resp.del_cookie(SESSION_COOKIE)
    resp.set_cookie("flash", f"info|{translate_request(request, 'logout_success')}", max_age=12, httponly=True, samesite="Lax")
    return resp


async def logout_user_post(request: web.Request) -> web.StreamResponse:
    """POST /logout — preferred over GET for CSRF safety."""
    return await logout_user(request)


async def update_profile(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    email = normalize_email(str(data.get("email", "")))
    state = str(data.get("state", "")).strip()

    current_email = normalize_email(str(user.get("email", "")))

    # Allow state-only update when both submitted and stored emails are empty
    if email and not is_valid_email(email):
        return flash_response("/profile", translate_request(request, "invalid_email"), "error")

    # If no email submitted and user has no email, allow state-only save
    if not email and not current_email:
        with get_db() as conn:
            conn.execute("UPDATE users SET state = ? WHERE id = ?", (state, user["id"]))
        return flash_response("/profile", translate_request(request, "profile_saved"), "success")

    # Require valid email when submitting one
    if not email:
        email = current_email

    if not is_valid_email(email):
        return flash_response("/profile", translate_request(request, "invalid_email"), "error")

    with get_db() as conn:
        email_conflicts_username = conn.execute(
            "SELECT 1 FROM users WHERE username = ? AND id != ? LIMIT 1",
            (email, user["id"]),
        ).fetchone()
        if email_conflicts_username:
            return flash_response("/profile", translate_request(request, "email_username_conflict"), "error")

        email_exists = conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ? LIMIT 1",
            (email, user["id"]),
        ).fetchone()
        if email_exists:
            return flash_response("/profile", translate_request(request, "email_exists"), "error")

        # Keep state update immediate, but require email verification when email changes.
        conn.execute("UPDATE users SET state = ? WHERE id = ?", (state, user["id"]))

        if email == current_email:
            if not is_smtp_configured() and not int(user.get("email_verified", 0)):
                conn.execute(
                    "UPDATE email_verifications SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                    (int(time.time()), user["id"]),
                )
            return flash_response("/profile", translate_request(request, "profile_saved"), "success")

        smtp_ready = is_smtp_configured()

        conn.execute(
            "UPDATE email_verifications SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
            (int(time.time()), user["id"]),
        )

        if not smtp_ready:
            conn.execute(
                "UPDATE users SET email = ?, email_verified = 0 WHERE id = ?",
                (email, user["id"]),
            )
            return flash_response("/profile", translate_request(request, "profile_saved"), "success")

        verify_code = f"{secrets.randbelow(1000000):06d}"
        token_hash = hash_reset_token(verify_code)
        expires_at = int(time.time()) + EMAIL_VERIFY_TOKEN_TTL_SECONDS

        conn.execute(
            "UPDATE users SET email = ?, email_verified = 0 WHERE id = ?",
            (email, user["id"]),
        )
        conn.execute(
            "INSERT INTO email_verifications (user_id, new_email, token_hash, expires_at) VALUES (?, ?, ?, ?)",
            (user["id"], email, token_hash, expires_at),
        )

    sent = send_email_verification_email(email, verify_code)
    if sent:
        return flash_response("/profile/verify-email", translate_request(request, "email_verification_code_sent"), "success")
    with get_db() as conn:
        conn.execute(
            "UPDATE email_verifications SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
            (int(time.time()), user["id"]),
        )
    return flash_response("/profile", translate_request(request, "profile_saved"), "success")


async def verify_profile_email(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    verify_code = str(data.get("verify_code", "")).strip()
    if not verify_code or not verify_code.isdigit():
        return flash_response("/profile/verify-email", translate_request(request, "email_verify_code_invalid"), "error")

    now_ts = int(time.time())
    token_hash = hash_reset_token(verify_code)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, user_id, new_email
            FROM email_verifications
            WHERE token_hash = ? AND used_at IS NULL AND expires_at >= ?
            LIMIT 1
            """,
            (token_hash, now_ts),
        ).fetchone()
        if not row or int(row["user_id"]) != int(user["id"]):
            return flash_response("/profile/verify-email", translate_request(request, "email_verify_code_invalid"), "error")

        email_exists = conn.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ? LIMIT 1",
            (row["new_email"], user["id"]),
        ).fetchone()
        if email_exists:
            return flash_response("/profile", translate_request(request, "email_exists"), "error")

        conn.execute(
            "UPDATE users SET email = ?, email_verified = 1 WHERE id = ?",
            (row["new_email"], user["id"]),
        )
        conn.execute("UPDATE email_verifications SET used_at = ? WHERE id = ?", (now_ts, row["id"]))

    return flash_response("/profile", translate_request(request, "email_verified_success"), "success")


async def change_profile_password(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    current_password = str(data.get("current_password", "")).strip()
    new_password = str(data.get("new_password", "")).strip()

    if not current_password:
        return flash_response("/profile", translate_request(request, "current_password_required"), "error")
    if len(new_password) < 6:
        return flash_response("/profile", translate_request(request, "username_password_min"), "error")

    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = ? LIMIT 1",
            (user["id"],),
        ).fetchone()
        if not row or not verify_password(current_password, row["password_hash"]):
            return flash_response("/profile", translate_request(request, "current_password_invalid"), "error")

        conn.execute(
            "UPDATE users SET password_hash = ?, auth_provider = 'email' WHERE id = ?",
            (hash_password(new_password), user["id"]),
        )

    return flash_response("/profile", translate_request(request, "password_changed"), "success")


async def forgot_password_request(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    email = normalize_email(str(data.get("email", "")))
    if not is_valid_email(email):
        return flash_response("/forgot-password", translate_request(request, "invalid_email"), "error")

    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ? LIMIT 1", (email,)).fetchone()
        reset_link = ""
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = int(time.time()) + RESET_TOKEN_TTL_SECONDS
            conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
                (user["id"], hash_reset_token(token), expires_at),
            )
            origin = f"{request.scheme}://{request.host}"
            reset_link = f"{origin}/reset-password?token={token}"
            sent = send_password_reset_email(email, reset_link)
            if not sent:
                return flash_response(
                    "/forgot-password",
                    translate_request(request, "email_service_unavailable"),
                    "error",
                )

    return flash_response("/forgot-password", translate_request(request, "forgot_success"), "success")


async def reset_password_submit(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    token = str(data.get("token", "")).strip()
    new_password = str(data.get("new_password", "")).strip()

    if len(new_password) < 6:
        return flash_response(f"/reset-password?token={token}", translate_request(request, "reset_password_min"), "error")

    token_hash = hash_reset_token(token)
    now_ts = int(time.time())

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, user_id
            FROM password_resets
            WHERE token_hash = ? AND used_at IS NULL AND expires_at >= ?
            LIMIT 1
            """,
            (token_hash, now_ts),
        ).fetchone()
        if not row:
            return flash_response("/forgot-password", translate_request(request, "reset_invalid"), "error")

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), row["user_id"]),
        )
        conn.execute(
            "UPDATE password_resets SET used_at = ? WHERE id = ?",
            (now_ts, row["id"]),
        )

    return flash_response("/", translate_request(request, "reset_password_success"), "success")


async def oauth_start(request: web.Request) -> web.StreamResponse:
    provider = str(request.match_info.get("provider", "")).strip().lower()
    cfg = get_oauth_config(provider)
    if not cfg:
        if provider == "google":
            return flash_response("/", translate_request(request, "oauth_google_missing"), "error")
        if provider == "discord":
            return flash_response("/", translate_request(request, "oauth_discord_missing"), "error")
        return flash_response("/", translate_request(request, "oauth_unavailable"), "error")

    state = issue_oauth_state(provider)
    query = urlencode(
        {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": cfg["scope"],
            "state": state,
            "prompt": "select_account" if provider == "google" else "consent",
        }
    )
    auth_url = f"{cfg['authorize_url']}?{query}"
    resp = web.HTTPFound(location=auth_url)
    resp.set_cookie("oauth_state", state, max_age=600, httponly=True, samesite="Lax")
    return resp


async def oauth_callback(request: web.Request) -> web.StreamResponse:
    provider = str(request.match_info.get("provider", "")).strip().lower()
    cfg = get_oauth_config(provider)
    code = str(request.query.get("code", "")).strip()
    state_q = str(request.query.get("state", "")).strip()
    state_cookie = request.cookies.get("oauth_state")

    parsed_provider = parse_oauth_state(state_q)
    if not cfg or not code or not state_cookie or state_q != state_cookie or parsed_provider != provider:
        return flash_response("/", translate_request(request, "oauth_failed"), "error")

    try:
        async with ClientSession() as session:
            token_resp = await session.post(
                cfg["token_url"],
                data={
                    "client_id": cfg["client_id"],
                    "client_secret": cfg["client_secret"],
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": cfg["redirect_uri"],
                },
                headers={"Accept": "application/json"},
                timeout=20,
            )
            token_data = await token_resp.json(content_type=None)
            access_token = str(token_data.get("access_token", ""))
            if not access_token:
                raise RuntimeError("No access token")

            user_resp = await session.get(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
            )
            user_data = await user_resp.json(content_type=None)

        if provider == "google":
            provider_uid = str(user_data.get("sub", "")).strip()
            email = normalize_email(str(user_data.get("email", "")))
            display_name = str(user_data.get("name", "google_user")).strip()
        else:
            provider_uid = str(user_data.get("id", "")).strip()
            email = normalize_email(str(user_data.get("email", "")))
            display_name = str(user_data.get("username", "discord_user")).strip()

        if not provider_uid:
            raise RuntimeError("No provider user id")

        with get_db() as conn:
            user_id = upsert_oauth_user(conn, provider, provider_uid, email, display_name)
            new_nonce = rotate_session_nonce(conn, user_id)

        resp = web.HTTPFound(location="/portal")
        resp.set_cookie(
            SESSION_COOKIE,
            issue_session_cookie(user_id, new_nonce),
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            samesite="Lax",
        )
        resp.del_cookie("oauth_state")
        resp.set_cookie("flash", f"success|{translate_request(request, 'login_success')}", max_age=12, httponly=True, samesite="Lax")
        return resp
    except Exception:
        return flash_response("/", translate_request(request, "oauth_failed"), "error")


async def create_record(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    member_name = str(data.get("current_name", "")).strip()
    member_uid = str(data.get("player_id", "")).strip()
    alliance = str(data.get("alliance", "")).strip()
    rank = str(data.get("rank", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not member_name or not member_uid or not alliance or not rank:
        return flash_response("/member-records/new", translate_request(request, "member_required"), "error")

    with get_db() as conn:
        duplicate = conn.execute(
            "SELECT 1 FROM member_records WHERE member_name = ? COLLATE NOCASE LIMIT 1",
            (member_name,),
        ).fetchone()
        if duplicate:
            return flash_response("/member-records/new", translate_request(request, "member_exists"), "error")

        fields = fetch_fields_and_options(conn)
        missing_required = [
            f["label"]
            for f in fields
            if f["is_required"] and not str(data.get(f"field_{f['id']}", "")).strip()
        ]
        if missing_required:
            return flash_response(
                "/member-records/new",
                translate_request(request, "required_missing", fields=", ".join(missing_required)),
                "error",
            )

        cur = conn.execute(
            """
            INSERT INTO member_records (member_name, member_uid, alliance, rank, notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (member_name, member_uid, alliance, rank, notes, user["id"]),
        )
        record_id = int(cur.lastrowid)

        for field in fields:
            selected_value = str(data.get(f"field_{field['id']}", "")).strip()
            if selected_value:
                conn.execute(
                    "INSERT INTO member_record_values (record_id, field_id, option_value) VALUES (?, ?, ?)",
                    (record_id, field["id"], selected_value),
                )

    return flash_response("/member-records/new", translate_request(request, "member_saved"), "success")


async def save_transfer(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    member_name = str(data.get("member_name", "")).strip()
    member_uid = str(data.get("member_uid", "")).strip()
    power = str(data.get("power", "")).strip()
    furnace = str(data.get("furnace", "")).strip()
    current_state = str(data.get("current_state", "")).strip()
    invite_type = str(data.get("invite_type", "")).strip()
    future_alliance = str(data.get("future_alliance", "")).strip()

    if not all([member_name, member_uid, power, furnace, current_state, invite_type, future_alliance]):
        return flash_response("/transfers", translate_request(request, "transfer_required"), "error")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO transfer_records (member_name, member_uid, power, furnace, current_state, invite_type, future_alliance, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (member_name, member_uid, power, furnace, current_state, invite_type, future_alliance, user["id"]),
        )

    return flash_response("/transfers", translate_request(request, "transfer_saved"), "success")


async def edit_record_page(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    record_id = int(request.match_info["record_id"])

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        record = conn.execute(
            """
            SELECT id, member_name, member_uid, alliance, rank, notes
            FROM member_records
            WHERE id = ?
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()
        if not record:
            return flash_response("/members", translate_request(request, "member_not_found"), "error")

        values = conn.execute(
            "SELECT field_id, option_value FROM member_record_values WHERE record_id = ?",
            (record_id,),
        ).fetchall()

    selected_by_field = {int(v["field_id"]): str(v["option_value"]) for v in values}

    return render_template(
        request,
        "edit_member.html",
        {
            "title": "Edit Member" if get_lang(request) == "en" else "تعديل عضو",
            "record": dict(record),
            "fields": fields,
            "selected_by_field": selected_by_field,
        },
    )


async def update_record(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    record_id = int(request.match_info["record_id"])
    data = await request.post()

    member_name = str(data.get("current_name", "")).strip()
    member_uid = str(data.get("player_id", "")).strip()
    alliance = str(data.get("alliance", "")).strip()
    rank = str(data.get("rank", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not member_name or not member_uid or not alliance or not rank:
        return flash_response(f"/records/{record_id}/edit", translate_request(request, "member_required"), "error")

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM member_records WHERE id = ? LIMIT 1", (record_id,)).fetchone()
        if not existing:
            return flash_response("/members", translate_request(request, "member_not_found"), "error")

        duplicate = conn.execute(
            """
            SELECT 1 FROM member_records
            WHERE member_name = ? COLLATE NOCASE AND id != ?
            LIMIT 1
            """,
            (member_name, record_id),
        ).fetchone()
        if duplicate:
            return flash_response(f"/records/{record_id}/edit", translate_request(request, "member_exists"), "error")

        fields = fetch_fields_and_options(conn)
        missing_required = [
            f["label"]
            for f in fields
            if f["is_required"] and not str(data.get(f"field_{f['id']}", "")).strip()
        ]
        if missing_required:
            return flash_response(
                f"/records/{record_id}/edit",
                translate_request(request, "required_missing", fields=", ".join(missing_required)),
                "error",
            )

        conn.execute(
            """
            UPDATE member_records
            SET member_name = ?, member_uid = ?, alliance = ?, rank = ?, notes = ?
            WHERE id = ?
            """,
            (member_name, member_uid, alliance, rank, notes, record_id),
        )

        conn.execute("DELETE FROM member_record_values WHERE record_id = ?", (record_id,))
        for field in fields:
            selected_value = str(data.get(f"field_{field['id']}", "")).strip()
            if selected_value:
                conn.execute(
                    "INSERT INTO member_record_values (record_id, field_id, option_value) VALUES (?, ?, ?)",
                    (record_id, field["id"], selected_value),
                )

    return flash_response("/members", translate_request(request, "member_updated"), "success")


async def delete_record(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    record_id = int(request.match_info["record_id"])

    with get_db() as conn:
        exists = conn.execute("SELECT id FROM member_records WHERE id = ? AND state_account_id IS NULL LIMIT 1", (record_id,)).fetchone()
        if not exists:
            return flash_response("/members", translate_request(request, "member_not_found"), "error")

        conn.execute("DELETE FROM member_records WHERE id = ? AND state_account_id IS NULL", (record_id,))

    return flash_response("/members", translate_request(request, "member_deleted"), "info")


async def delete_all_records(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    with get_db() as conn:
        conn.execute("DELETE FROM member_records WHERE state_account_id IS NULL")

    return flash_response("/members", translate_request(request, "all_members_deleted"), "info")


async def delete_all_transfers(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    with get_db() as conn:
        conn.execute("DELETE FROM transfer_records WHERE state_account_id IS NULL")

    return flash_response("/transfers", translate_request(request, "all_transfers_deleted"), "info")


async def dashboard(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        state_number = get_setting(conn, "state_number")
        alliances = fetch_state_alliances(conn, state_number) if state_number else []
        list_configs = fetch_list_configs(conn)
        smtp_settings = {
            "host": get_setting(conn, "smtp_host", os.getenv("SMTP_HOST", "")),
            "port": get_setting(conn, "smtp_port", os.getenv("SMTP_PORT", "587")),
            "user": get_setting(conn, "smtp_user", os.getenv("SMTP_USER", "")),
            "from": get_setting(conn, "smtp_from", os.getenv("SMTP_FROM", "")),
        }
        users = conn.execute(
            "SELECT id, username, email, auth_provider, is_admin, state, created_at FROM users ORDER BY id DESC LIMIT 50"
        ).fetchall()

    full_admin_lower = {DEFAULT_FULL_ADMIN_USERNAME.strip().lower(), "admin"}
    users_list = []
    for u in users:
        u_dict = dict(u)
        u_dict["is_deletable"] = (
            str(u_dict["username"]).strip().lower() not in full_admin_lower
            and u_dict["id"] != user["id"]
        )
        users_list.append(u_dict)

    return render_template(
        request,
        "dashboard.html",
        {
            "title": translate_request(request, "admin_title"),
            "fields": fields,
            "state_number": state_number,
            "alliances": alliances,
            "list_configs": list_configs,
            "smtp_settings": smtp_settings,
            "users": users_list,
        },
    )


async def save_smtp_settings(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    data = await request.post()
    smtp_host = str(data.get("smtp_host", "")).strip()
    smtp_port = str(data.get("smtp_port", "587")).strip() or "587"
    smtp_user = str(data.get("smtp_user", "")).strip()
    smtp_password = str(data.get("smtp_password", "")).strip()
    smtp_from = str(data.get("smtp_from", "")).strip()

    with get_db() as conn:
        set_setting(conn, "smtp_host", smtp_host)
        set_setting(conn, "smtp_port", smtp_port)
        set_setting(conn, "smtp_user", smtp_user)
        if smtp_password:
            set_setting(conn, "smtp_password", smtp_password)
        set_setting(conn, "smtp_from", smtp_from)

    return flash_response("/dashboard", translate_request(request, "smtp_settings_saved"), "success")


async def test_smtp_connection(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/dashboard", translate_request(request, "admin_required"), "error")

    # Test email is the logged-in user's email or a test email
    test_email = str(user.get("email", "")).strip() or "test@example.com"
    
    success = send_smtp_message(
        subject="TNT Portal SMTP Test",
        target_email=test_email,
        body="This is a test message from TNT Portal SMTP configuration.\n\nIf you received this, SMTP is working correctly!"
    )
    
    if success:
        return flash_response("/dashboard", f"Test email sent to {test_email}", "success")
    return flash_response("/dashboard", "SMTP test failed. Check the logs for details.", "error")


async def reset_all_sessions(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    current_admin_nonce = ""
    with get_db() as conn:
        users = conn.execute("SELECT id FROM users").fetchall()
        for row in users:
            new_nonce = rotate_session_nonce(conn, int(row["id"]))
            if int(row["id"]) == int(user["id"]):
                current_admin_nonce = new_nonce

        if not current_admin_nonce:
            current_admin_nonce = rotate_session_nonce(conn, int(user["id"]))

    resp = flash_response("/dashboard", translate_request(request, "all_sessions_reset"), "success")
    resp.set_cookie(
        SESSION_COOKIE,
        issue_session_cookie(int(user["id"]), current_admin_nonce),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
    )
    return resp


async def save_state_settings(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    data = await request.post()
    state_number = str(data.get("state_number", "")).strip()
    if not state_number:
        return flash_response("/dashboard", translate_request(request, "state_number_required"), "error")

    with get_db() as conn:
        set_setting(conn, "state_number", state_number)

    return flash_response("/dashboard", translate_request(request, "settings_saved"), "success")


async def add_state_alliance(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    data = await request.post()

    with get_db() as conn:
        state_number = get_setting(conn, "state_number")
        alliance_tag = str(data.get("alliance_tag", "")).strip().upper()
        if not state_number:
            return flash_response("/dashboard", translate_request(request, "state_number_required"), "error")
        if not alliance_tag:
            return flash_response("/dashboard", translate_request(request, "alliance_tag_required"), "error")
        try:
            conn.execute(
                "INSERT INTO state_alliances (state_number, alliance_tag, created_by) VALUES (?, ?, ?)",
                (state_number, alliance_tag, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/dashboard", translate_request(request, "alliance_tag_exists"), "error")

    return flash_response("/dashboard", translate_request(request, "alliance_tag_added"), "success")


async def delete_state_alliance(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    alliance_id = int(request.match_info["alliance_id"])
    with get_db() as conn:
        conn.execute("DELETE FROM state_alliances WHERE id = ?", (alliance_id,))

    return flash_response("/dashboard", translate_request(request, "alliance_tag_deleted"), "info")


async def update_list_config(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    list_key = request.match_info["list_key"]
    data = await request.post()
    is_enabled = 1 if str(data.get("is_enabled", "")).strip() == "1" else 0

    with get_db() as conn:
        conn.execute("UPDATE list_configs SET is_enabled = ? WHERE list_key = ?", (is_enabled, list_key))

    return flash_response("/dashboard", translate_request(request, "list_updated"), "success")


async def add_field(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    data = await request.post()
    label = str(data.get("label", "")).strip()
    field_key = str(data.get("field_key", "")).strip().lower().replace(" ", "_")
    sort_order = int(str(data.get("sort_order", "100")).strip() or "100")
    is_required = 1 if str(data.get("is_required", "")).strip() == "on" else 0

    if not label or not field_key:
        return flash_response("/dashboard", translate_request(request, "field_required"), "error")

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
            return flash_response("/dashboard", translate_request(request, "field_key_exists"), "error")

    return flash_response("/dashboard", translate_request(request, "field_added"), "success")


async def delete_field(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    field_id = int(request.match_info["field_id"])

    with get_db() as conn:
        conn.execute("DELETE FROM dropdown_fields WHERE id = ?", (field_id,))

    return flash_response("/dashboard", translate_request(request, "field_deleted"), "info")


async def add_option_admin(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    data = await request.post()
    field_id = int(str(data.get("field_id", "0")).strip() or "0")
    value = str(data.get("value", "")).strip()
    sort_order = int(str(data.get("sort_order", "100")).strip() or "100")

    if not field_id or not value:
        return flash_response("/dashboard", translate_request(request, "option_required"), "error")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO dropdown_options (field_id, value, sort_order, created_by) VALUES (?, ?, ?, ?)",
                (field_id, value, sort_order, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/dashboard", translate_request(request, "option_exists"), "error")

    return flash_response("/dashboard", translate_request(request, "option_added"), "success")


async def contribute_option(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    data = await request.post()
    field_id = int(str(data.get("field_id", "0")).strip() or "0")
    value = str(data.get("value", "")).strip()

    if not field_id or len(value) < 2:
        return flash_response("/portal", translate_request(request, "option_invalid"), "error")

    with get_db() as conn:
        exists = conn.execute("SELECT 1 FROM dropdown_fields WHERE id = ?", (field_id,)).fetchone()
        if not exists:
            return flash_response("/portal", translate_request(request, "field_not_found"), "error")

        try:
            conn.execute(
                "INSERT INTO dropdown_options (field_id, value, sort_order, created_by) VALUES (?, ?, 100, ?)",
                (field_id, value, user["id"]),
            )
        except sqlite3.IntegrityError:
            return flash_response("/portal", translate_request(request, "option_exists"), "error")

    return flash_response("/portal", translate_request(request, "option_added"), "success")


async def update_user_role(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    target_user_id = int(request.match_info["user_id"])
    data = await request.post()
    is_admin = 1 if str(data.get("is_admin", "")).strip() == "1" else 0

    with get_db() as conn:
        target = conn.execute(
            "SELECT id, username FROM users WHERE id = ? LIMIT 1",
            (target_user_id,),
        ).fetchone()
        if not target:
            return flash_response("/dashboard", translate_request(request, "member_not_found"), "error")

        if is_admin == 0 and is_full_admin_username(str(target["username"])):
            return flash_response("/dashboard", translate_request(request, "cannot_downgrade_full_admin"), "error")

        conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (is_admin, target_user_id))

    return flash_response("/dashboard", translate_request(request, "role_updated"), "success")


async def delete_user(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    target_user_id = int(request.match_info["user_id"])

    if target_user_id == user["id"]:
        return flash_response("/dashboard", translate_request(request, "cannot_delete_self"), "error")

    with get_db() as conn:
        target = conn.execute(
            "SELECT id, username FROM users WHERE id = ? LIMIT 1",
            (target_user_id,),
        ).fetchone()
        if not target:
            return flash_response("/dashboard", translate_request(request, "member_not_found"), "error")

        if is_full_admin_username(str(target["username"])):
            return flash_response("/dashboard", translate_request(request, "cannot_delete_admin"), "error")

        conn.execute("DELETE FROM users WHERE id = ?", (target_user_id,))

    return flash_response("/dashboard", translate_request(request, "user_deleted"), "info")


async def delete_transfer(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    transfer_id = int(request.match_info["transfer_id"])

    with get_db() as conn:
        conn.execute("DELETE FROM transfer_records WHERE id = ?", (transfer_id,))

    return flash_response("/transfers", translate_request(request, "transfer_deleted"), "info")


async def resend_email_verification_otp(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user:
        return flash_response("/", translate_request(request, "login_required"), "error")

    if not is_smtp_configured():
        with get_db() as conn:
            conn.execute(
                "UPDATE email_verifications SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                (int(time.time()), user["id"]),
            )
        return flash_response("/profile", translate_request(request, "profile_saved"), "success")

    with get_db() as conn:
        pending = conn.execute(
            """
            SELECT id, new_email
            FROM email_verifications
            WHERE user_id = ? AND used_at IS NULL AND expires_at >= ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user["id"], int(time.time())),
        ).fetchone()

        if not pending:
            return flash_response("/profile", translate_request(request, "email_verify_code_invalid"), "error")

        verify_code = f"{secrets.randbelow(1000000):06d}"
        token_hash = hash_reset_token(verify_code)
        expires_at = int(time.time()) + EMAIL_VERIFY_TOKEN_TTL_SECONDS

        conn.execute(
            "UPDATE email_verifications SET token_hash = ?, expires_at = ? WHERE id = ?",
            (token_hash, expires_at, pending["id"]),
        )
        new_email = pending["new_email"]

    sent = send_email_verification_email(new_email, verify_code)
    if sent:
        return flash_response("/profile/verify-email", translate_request(request, "code_resent"), "success")
    return flash_response("/profile", translate_request(request, "email_service_unavailable"), "error")


async def export_members_csv(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    with get_db() as conn:
        fields = fetch_fields_and_options(conn)
        records = conn.execute(
            """
            SELECT r.id, r.member_name, r.member_uid, r.alliance, r.rank, r.notes, r.created_at, u.username
            FROM member_records r
            LEFT JOIN users u ON u.id = r.created_by
            WHERE r.state_account_id IS NULL
            ORDER BY r.id ASC
            """
        ).fetchall()
        values = conn.execute(
            """
            SELECT v.record_id, f.field_key, v.option_value
            FROM member_record_values v
            JOIN dropdown_fields f ON f.id = v.field_id
            WHERE v.record_id IN (
                SELECT id FROM member_records WHERE state_account_id IS NULL
            )
            """
        ).fetchall()

    values_by_record: dict[int, dict[str, str]] = {}
    for row in values:
        values_by_record.setdefault(int(row["record_id"]), {})[str(row["field_key"])] = str(row["option_value"])

    output = io.StringIO()
    field_keys = [f["field_key"] for f in fields]
    field_labels = [f["label"] for f in fields]
    writer = csv.writer(output)
    writer.writerow(["ID", "Member Name", "Member UID", "Alliance", "Rank", "Notes"] + field_labels + ["Registered By", "Created At"])

    for rec in records:
        dv = values_by_record.get(int(rec["id"]), {})
        writer.writerow(
            [rec["id"], rec["member_name"], rec["member_uid"], rec["alliance"], rec["rank"], rec["notes"]]
            + [dv.get(fk, "") for fk in field_keys]
            + [rec["username"] or "", rec["created_at"]]
        )

    return web.Response(
        text=output.getvalue(),
        content_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=members.csv"},
    )


async def export_transfers_csv(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user["is_admin"]:
        return flash_response("/portal", translate_request(request, "admin_required"), "error")

    with get_db() as conn:
        records = conn.execute(
            """
            SELECT t.id, t.member_name, t.member_uid, t.power, t.furnace, t.current_state,
                   t.invite_type, t.future_alliance, t.created_at, u.username
            FROM transfer_records t
            LEFT JOIN users u ON u.id = t.created_by
            WHERE t.state_account_id IS NULL
            ORDER BY t.id ASC
            """
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Member Name", "Member UID", "Power", "Furnace", "Current State", "Invite Type", "Future Alliance", "Registered By", "Created At"])

    for rec in records:
        writer.writerow([
            rec["id"], rec["member_name"], rec["member_uid"],
            rec["power"], rec["furnace"], rec["current_state"],
            rec["invite_type"], rec["future_alliance"],
            rec["username"] or "", rec["created_at"],
        ])

    return web.Response(
        text=output.getvalue(),
        content_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transfers.csv"},
    )


async def healthz(request: web.Request) -> web.Response:
    return web.Response(text="ok", content_type="text/plain")


# ═══════════════════════════════════════════════════════════════════════════════
# STATE ACCOUNT routes
# ═══════════════════════════════════════════════════════════════════════════════

async def state_login_page(request: web.Request) -> web.Response:
    if get_current_state_account(request):
        raise web.HTTPFound(location="/state/portal")
    return render_template(request, "state_auth.html", {
        "title": "State Login | TNT Alliance",
    })


async def state_login_post(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    state_name = str(data.get("state_name", "")).strip()
    password = str(data.get("password", "")).strip()

    if not state_name or not password:
        return flash_response("/state-login", "State name and password are required", "error")

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM state_accounts WHERE state_name = ? LIMIT 1",
            (state_name,),
        ).fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        return flash_response("/state-login", "Invalid state name or password", "error")

    resp = web.HTTPFound(location="/state/portal")
    resp.set_cookie(
        STATE_SESSION_COOKIE,
        issue_state_session_cookie(int(row["id"])),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="Lax",
    )
    resp.set_cookie("flash", "success|Welcome back!", max_age=12, httponly=True, samesite="Lax")
    return resp


async def state_register_page(request: web.Request) -> web.Response:
    if get_current_state_account(request):
        raise web.HTTPFound(location="/state/portal")
    return render_template(request, "state_register.html", {
        "title": "Create State Account | TNT Alliance",
    })


async def state_register_post(request: web.Request) -> web.StreamResponse:
    data = await request.post()
    state_name = str(data.get("state_name", "")).strip()
    password = str(data.get("password", "")).strip()

    if len(state_name) < 2 or len(password) < 6:
        return flash_response("/state-register", "State name must be ≥2 chars and password ≥6 chars", "error")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO state_accounts (state_name, password_hash) VALUES (?, ?)",
                (state_name, hash_password(password)),
            )
        except sqlite3.IntegrityError:
            return flash_response("/state-register", "A state account with this name already exists", "error")

    return flash_response("/state-login", "State account created. You can now sign in.", "success")


async def state_logout(request: web.Request) -> web.StreamResponse:
    resp = web.HTTPFound(location="/state-login")
    resp.del_cookie(STATE_SESSION_COOKIE)
    resp.set_cookie("flash", "info|State session ended", max_age=12, httponly=True, samesite="Lax")
    return resp


async def state_portal(request: web.Request) -> web.Response:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in to your state account first", "error")
    with get_db() as conn:
        members = conn.execute(
            "SELECT id, member_name, member_uid, alliance, rank, created_at FROM member_records WHERE state_account_id = ? ORDER BY id DESC LIMIT 100",
            (sa["id"],),
        ).fetchall()
        transfers = conn.execute(
            "SELECT id, member_name, member_uid, power, furnace, current_state, future_alliance, created_at FROM transfer_records WHERE state_account_id = ? ORDER BY id DESC LIMIT 100",
            (sa["id"],),
        ).fetchall()
        fields = fetch_fields_and_options(conn)
        alliances = conn.execute(
            "SELECT alliance_tag FROM state_alliances WHERE state_number = ? ORDER BY alliance_tag",
            (sa["state_name"],),
        ).fetchall()
    return render_template(request, "state_portal.html", {
        "title": f"State Portal — {sa['state_name']}",
        "sa": sa,
        "members": [dict(r) for r in members],
        "transfers": [dict(r) for r in transfers],
        "fields": fields,
        "alliances": [r["alliance_tag"] for r in alliances],
    })


async def state_add_member(request: web.Request) -> web.StreamResponse:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in first", "error")

    data = await request.post()
    member_name = str(data.get("current_name", "")).strip()
    member_uid = str(data.get("player_id", "")).strip()
    alliance = str(data.get("alliance", "")).strip()
    rank = str(data.get("rank", "")).strip()
    notes = str(data.get("notes", "")).strip()

    if not member_name or not member_uid or not alliance or not rank:
        return flash_response("/state/portal", "Player ID, Name, Alliance and Rank are required", "error")

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO member_records (member_name, member_uid, alliance, rank, notes, state_account_id) VALUES (?, ?, ?, ?, ?, ?)",
            (member_name, member_uid, alliance, rank, notes, sa["id"]),
        )
        record_id = int(cur.lastrowid)
        fields = fetch_fields_and_options(conn)
        for field in fields:
            val = str(data.get(f"field_{field['id']}", "")).strip()
            if val:
                conn.execute(
                    "INSERT INTO member_record_values (record_id, field_id, option_value) VALUES (?, ?, ?)",
                    (record_id, field["id"], val),
                )

    return flash_response("/state/portal", "Member added successfully", "success")


async def state_add_transfer(request: web.Request) -> web.StreamResponse:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in first", "error")

    data = await request.post()
    member_name = str(data.get("member_name", "")).strip()
    member_uid = str(data.get("member_uid", "")).strip()
    power = str(data.get("power", "")).strip()
    furnace = str(data.get("furnace", "")).strip()
    current_state = str(data.get("current_state", "")).strip()
    invite_type = str(data.get("invite_type", "")).strip()
    future_alliance = str(data.get("future_alliance", "")).strip()

    if not all([member_name, member_uid, power, furnace, current_state, future_alliance]):
        return flash_response("/state/portal", "All fields are required", "error")

    with get_db() as conn:
        conn.execute(
            "INSERT INTO transfer_records (member_name, member_uid, power, furnace, current_state, invite_type, future_alliance, state_account_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (member_name, member_uid, power, furnace, current_state, invite_type, future_alliance, sa["id"]),
        )

    return flash_response("/state/portal", "Transfer added successfully", "success")


async def state_delete_member(request: web.Request) -> web.StreamResponse:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in first", "error")

    record_id = int(request.match_info["record_id"])
    with get_db() as conn:
        # Only allow deletion of records belonging to this state
        conn.execute(
            "DELETE FROM member_records WHERE id = ? AND state_account_id = ?",
            (record_id, sa["id"]),
        )
    return flash_response("/state/portal", "Member deleted", "info")


async def state_delete_transfer(request: web.Request) -> web.StreamResponse:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in first", "error")

    transfer_id = int(request.match_info["transfer_id"])
    with get_db() as conn:
        conn.execute(
            "DELETE FROM transfer_records WHERE id = ? AND state_account_id = ?",
            (transfer_id, sa["id"]),
        )
    return flash_response("/state/portal", "Transfer deleted", "info")


async def state_change_password(request: web.Request) -> web.StreamResponse:
    sa = get_current_state_account(request)
    if not sa:
        return flash_response("/state-login", "Please sign in first", "error")

    data = await request.post()
    current_pw = str(data.get("current_password", "")).strip()
    new_pw = str(data.get("new_password", "")).strip()

    if len(new_pw) < 6:
        return flash_response("/state/portal", "New password must be at least 6 characters", "error")

    with get_db() as conn:
        row = conn.execute(
            "SELECT password_hash FROM state_accounts WHERE id = ?",
            (sa["id"],),
        ).fetchone()
        if not row or not verify_password(current_pw, row["password_hash"]):
            return flash_response("/state/portal", "Current password is incorrect", "error")
        conn.execute(
            "UPDATE state_accounts SET password_hash = ? WHERE id = ?",
            (hash_password(new_pw), sa["id"]),
        )

    return flash_response("/state/portal", "Password changed successfully", "success")


# ═══════════════════════════════════════════════════════════════════════════════
# OWNER PANEL routes — features management
# ═══════════════════════════════════════════════════════════════════════════════

async def owner_panel(request: web.Request) -> web.Response:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    with get_db() as conn:
        features = conn.execute(
            "SELECT id, feature_key, label, description, feature_type, is_enabled, config_json, created_at FROM features ORDER BY id DESC"
        ).fetchall()
        state_accounts = conn.execute(
            "SELECT id, state_name, created_at FROM state_accounts ORDER BY id ASC"
        ).fetchall()
        all_users = conn.execute(
            "SELECT id, username, email, is_admin, is_owner, state, created_at FROM users ORDER BY id DESC"
        ).fetchall()

    return render_template(request, "owner_panel.html", {
        "title": "Owner Panel | TNT Alliance",
        "features": [dict(f) for f in features],
        "state_accounts": [dict(s) for s in state_accounts],
        "all_users": [dict(u) for u in all_users],
    })


async def owner_add_feature(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    data = await request.post()
    feature_key = str(data.get("feature_key", "")).strip().lower().replace(" ", "_")
    label = str(data.get("label", "")).strip()
    description = str(data.get("description", "")).strip()
    feature_type = str(data.get("feature_type", "function")).strip()
    is_enabled = 1 if str(data.get("is_enabled", "1")).strip() == "1" else 0
    config_json = str(data.get("config_json", "{}")).strip() or "{}"

    if not feature_key or not label:
        return flash_response("/owner", "Feature key and label are required", "error")

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO features (feature_key, label, description, feature_type, is_enabled, config_json) VALUES (?, ?, ?, ?, ?, ?)",
                (feature_key, label, description, feature_type, is_enabled, config_json),
            )
        except sqlite3.IntegrityError:
            return flash_response("/owner", "Feature key already exists", "error")

    return flash_response("/owner", "Feature added successfully", "success")


async def owner_toggle_feature(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    feature_id = int(request.match_info["feature_id"])
    data = await request.post()
    is_enabled = 1 if str(data.get("is_enabled", "1")).strip() == "1" else 0

    with get_db() as conn:
        conn.execute("UPDATE features SET is_enabled = ? WHERE id = ?", (is_enabled, feature_id))

    return flash_response("/owner", "Feature updated", "success")


async def owner_delete_feature(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    feature_id = int(request.match_info["feature_id"])
    with get_db() as conn:
        conn.execute("DELETE FROM features WHERE id = ?", (feature_id,))

    return flash_response("/owner", "Feature deleted", "info")


async def owner_delete_state_account(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    sa_id = int(request.match_info["sa_id"])
    with get_db() as conn:
        conn.execute("DELETE FROM state_accounts WHERE id = ?", (sa_id,))

    return flash_response("/owner", "State account deleted", "info")


async def owner_reset_state_password(request: web.Request) -> web.StreamResponse:
    user = get_current_user(request)
    if not user or not user.get("is_owner"):
        return flash_response("/portal", "Owner access required", "error")

    sa_id = int(request.match_info["sa_id"])
    data = await request.post()
    new_pw = str(data.get("new_password", "")).strip()

    if len(new_pw) < 6:
        return flash_response("/owner", "Password must be at least 6 characters", "error")

    with get_db() as conn:
        conn.execute(
            "UPDATE state_accounts SET password_hash = ? WHERE id = ?",
            (hash_password(new_pw), sa_id),
        )

    return flash_response("/owner", "State account password reset successfully", "success")


async def api_features(request: web.Request) -> web.Response:
    """Public JSON endpoint listing enabled features."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT feature_key, label, description, feature_type, config_json FROM features WHERE is_enabled = 1"
        ).fetchall()
    features = []
    for r in rows:
        try:
            cfg = json.loads(r["config_json"])
        except Exception:
            cfg = {}
        features.append({
            "feature_key": r["feature_key"],
            "label": r["label"],
            "description": r["description"],
            "feature_type": r["feature_type"],
            "config": cfg,
        })
    return web.json_response({"features": features})


@web.middleware
async def security_headers_middleware(request: web.Request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


def build_app() -> web.Application:
    init_db()

    app = web.Application(middlewares=[security_headers_middleware])
    app["jinja_env"] = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    app.router.add_static("/static/", path=str(STATIC_DIR), name="static")
    app.router.add_get("/healthz", healthz)

    app.router.add_get("/", auth_page)
    app.router.add_get("/register-page", register_page)
    app.router.add_get("/forgot-password", forgot_password_page)
    app.router.add_get("/reset-password", reset_password_page)
    app.router.add_get("/portal", portal_page)
    app.router.add_get("/portal/", portal_page)
    app.router.add_get("/member-records/new", member_registry_page)
    app.router.add_get("/members", members_page)
    app.router.add_get("/transfers", transfers_page)
    app.router.add_get("/profile", profile_page)
    app.router.add_get("/profile/verify-email", verify_profile_email_page)

    app.router.add_post("/register", register_user)
    app.router.add_post("/login", login_user)
    app.router.add_post("/forgot-password/request", forgot_password_request)
    app.router.add_post("/reset-password", reset_password_submit)
    app.router.add_get("/oauth/{provider}/start", oauth_start)
    app.router.add_get("/oauth/{provider}/callback", oauth_callback)
    app.router.add_get("/logout", logout_user)
    app.router.add_post("/logout", logout_user_post)
    app.router.add_post("/profile", update_profile)
    app.router.add_post("/profile/verify-email", verify_profile_email)
    app.router.add_post("/profile/password", change_profile_password)
    app.router.add_post("/set-language", set_language)

    app.router.add_post("/records/create", create_record)
    app.router.add_post("/transfers/create", save_transfer)
    app.router.add_get("/records/{record_id}/edit", edit_record_page)
    app.router.add_post("/records/delete-all", delete_all_records)
    app.router.add_post("/transfers/delete-all", delete_all_transfers)
    app.router.add_post("/records/{record_id}/edit", update_record)
    app.router.add_post("/records/{record_id}/delete", delete_record)
    app.router.add_post("/options/contribute", contribute_option)

    app.router.add_get("/dashboard", dashboard)
    app.router.add_post("/dashboard/settings/state", save_state_settings)
    app.router.add_post("/dashboard/settings/smtp", save_smtp_settings)
    app.router.add_post("/dashboard/settings/smtp/test", test_smtp_connection)
    app.router.add_post("/dashboard/sessions/reset", reset_all_sessions)
    app.router.add_post("/dashboard/state-alliances", add_state_alliance)
    app.router.add_post("/dashboard/state-alliances/{alliance_id}/delete", delete_state_alliance)
    app.router.add_post("/dashboard/lists/{list_key}", update_list_config)
    app.router.add_post("/dashboard/fields", add_field)
    app.router.add_post("/dashboard/fields/{field_id}/delete", delete_field)
    app.router.add_post("/dashboard/options", add_option_admin)
    app.router.add_post("/dashboard/users/{user_id}/role", update_user_role)
    app.router.add_post("/dashboard/users/{user_id}/delete", delete_user)
    app.router.add_post("/transfers/{transfer_id}/delete", delete_transfer)
    app.router.add_post("/profile/resend-verify-email", resend_email_verification_otp)
    app.router.add_get("/members/export", export_members_csv)
    app.router.add_get("/transfers/export", export_transfers_csv)

    # ── State Account routes ───────────────────────────────────────────────────
    app.router.add_get("/state-login", state_login_page)
    app.router.add_post("/state-login", state_login_post)
    app.router.add_get("/state-register", state_register_page)
    app.router.add_post("/state-register", state_register_post)
    app.router.add_get("/state-logout", state_logout)
    app.router.add_get("/state/portal", state_portal)
    app.router.add_post("/state/members/create", state_add_member)
    app.router.add_post("/state/transfers/create", state_add_transfer)
    app.router.add_post("/state/members/{record_id}/delete", state_delete_member)
    app.router.add_post("/state/transfers/{transfer_id}/delete", state_delete_transfer)
    app.router.add_post("/state/change-password", state_change_password)

    # ── Owner Panel routes ─────────────────────────────────────────────────────
    app.router.add_get("/owner", owner_panel)
    app.router.add_post("/owner/features/add", owner_add_feature)
    app.router.add_post("/owner/features/{feature_id}/toggle", owner_toggle_feature)
    app.router.add_post("/owner/features/{feature_id}/delete", owner_delete_feature)
    app.router.add_post("/owner/state-accounts/{sa_id}/delete", owner_delete_state_account)
    app.router.add_post("/owner/state-accounts/{sa_id}/reset-password", owner_reset_state_password)
    app.router.add_get("/api/features", api_features)

    return app


if __name__ == "__main__":
    app = build_app()
    port = int(os.getenv("PORT", "8080"))
    web.run_app(app, host="0.0.0.0", port=port)
