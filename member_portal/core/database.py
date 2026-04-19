"""
Database Management Module
===========================
إدارة قاعدة البيانات والجداول والعمليات الأساسية
"""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple

from core.config import Config

logger = logging.getLogger(__name__)


class Database:
    """إدارة قاعدة البيانات"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def execute(self, query: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        """تنفيذ استعلام"""
        try:
            with self.get_connection() as conn:
                return conn.execute(query, params)
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return None
    
    def executescript(self, script: str) -> bool:
        """تنفيذ نص برنامج متعدد الأسطر"""
        try:
            with self.get_connection() as conn:
                conn.executescript(script)
            return True
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            return False
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """جلب صف واحد"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching one: {e}")
            return None
    
    def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """جلب جميع الصفوف"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching all: {e}")
            return []
    
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """إدراج صف جديد"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join('?' * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, tuple(data.values()))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting into {table}: {e}")
            return None
    
    def update(self, table: str, data: Dict[str, Any], where: Dict[str, Any]) -> bool:
        """تحديث صف"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        values = list(data.values()) + list(where.values())
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating {table}: {e}")
            return False
    
    def delete(self, table: str, where: Dict[str, Any]) -> bool:
        """حذف صف (Soft Delete أو Hard Delete)"""
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, tuple(where.values()))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting from {table}: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """التحقق من وجود جدول"""
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetchone(query, (table_name,))
        return result is not None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        """التحقق من وجود عمود داخل جدول."""
        rows = self.fetchall(f"PRAGMA table_info({table_name})")
        return any(row.get("name") == column_name for row in rows)

    def ensure_column(self, table_name: str, column_name: str, column_type_sql: str) -> bool:
        """إضافة عمود بشكل آمن إن لم يكن موجوداً."""
        if self.column_exists(table_name, column_name):
            return True

        return self.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_sql}") is not None
    
    def init_tables(self) -> bool:
        """إنشاء جميع الجداول"""
        schema = """
        -- ── جدول المستخدمين ──
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            oauth_provider TEXT,  -- 'google', 'discord', NULL للتقليدي
            oauth_id TEXT UNIQUE,
            full_name TEXT,
            avatar_url TEXT,
            is_email_verified INTEGER NOT NULL DEFAULT 0,
            email_verified_at TEXT,
            role TEXT NOT NULL DEFAULT 'member',
            is_active INTEGER NOT NULL DEFAULT 1,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        );

        -- ── جدول الولايات ──
        CREATE TABLE IF NOT EXISTS states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_name TEXT NOT NULL UNIQUE,
            state_number TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            admin_user_id INTEGER,
            description TEXT,
            logo_url TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(admin_user_id) REFERENCES users(id)
        );

        -- ── جدول أعضاء الولاية ──
        CREATE TABLE IF NOT EXISTS state_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            state_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(state_id) REFERENCES states(id) ON DELETE CASCADE,
            UNIQUE(user_id, state_id)
        );

        -- ── جدول الصلاحيات ──
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            permission_key TEXT NOT NULL,
            is_granted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(role, permission_key)
        );

        -- ── جدول الصلاحيات المخصصة للمستخدمين ──
        CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_key TEXT NOT NULL,
            is_granted INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, permission_key)
        );

        -- ── جدول محاولات تسجيل الدخول ──
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ip_address TEXT,
            success INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- ── جدول جلسات المستخدمين ──
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- ── جدول جلسات الولاية ──
        CREATE TABLE IF NOT EXISTS state_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(state_id) REFERENCES states(id) ON DELETE CASCADE
        );

        -- ── جدول رموز التحقق من البريد الإلكتروني ──
        CREATE TABLE IF NOT EXISTS email_verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            is_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- ── جدول رموز إعادة تعيين كلمة المرور ──
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            is_used INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- ── جدول رموز OAuth ──
        CREATE TABLE IF NOT EXISTS oauth_identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            email TEXT,
            name TEXT,
            avatar_url TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(provider, provider_id)
        );

        -- ── جدول سجل النشاط ──
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        -- ── جدول الأعضاء ──
        CREATE TABLE IF NOT EXISTS member_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            member_uid TEXT NOT NULL,
            alliance TEXT DEFAULT '',
            rank TEXT DEFAULT '',
            power TEXT DEFAULT '',
            furnace TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(state_id) REFERENCES states(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id),
            UNIQUE(state_id, member_uid)
        );

        -- ── جدول سجلات التحويل ──
        CREATE TABLE IF NOT EXISTS transfer_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER NOT NULL,
            member_name TEXT NOT NULL,
            member_uid TEXT NOT NULL,
            power TEXT DEFAULT '',
            furnace TEXT DEFAULT '',
            current_state TEXT NOT NULL,
            invite_type TEXT DEFAULT '',
            future_alliance TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(state_id) REFERENCES states(id) ON DELETE CASCADE,
            FOREIGN KEY(created_by) REFERENCES users(id)
        );

        -- ── إعدادات النظام العامة ──
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- ── معاملات الحاسبات ──
        CREATE TABLE IF NOT EXISTS calculator_modifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculator_type TEXT NOT NULL,
            target_key TEXT NOT NULL,
            resource_key TEXT NOT NULL,
            multiplier REAL NOT NULL DEFAULT 1.0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(calculator_type, target_key, resource_key)
        );

        -- ── قاعدة معرفة اللعبة ──
        CREATE TABLE IF NOT EXISTS knowledge_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            entry_name TEXT NOT NULL,
            tags TEXT DEFAULT '',
            summary TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            source TEXT DEFAULT 'seed',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, entry_name)
        );

        -- ── توزيع الأعضاء على الماب ──
        CREATE TABLE IF NOT EXISTS member_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_id INTEGER,
            user_id INTEGER,
            member_record_id INTEGER,
            slot_label TEXT NOT NULL,
            shape TEXT NOT NULL,
            pos_x REAL NOT NULL,
            pos_y REAL NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            assigned_power INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(state_id) REFERENCES states(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(member_record_id) REFERENCES member_records(id) ON DELETE CASCADE
        );

        -- ── سجل محادثة المساعد الذكي ──
        CREATE TABLE IF NOT EXISTS ai_chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            context_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        );

        -- ── الفهارس للأداء ──
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
        CREATE INDEX IF NOT EXISTS idx_states_name ON states(state_name);
        CREATE INDEX IF NOT EXISTS idx_state_members_user ON state_members(user_id);
        CREATE INDEX IF NOT EXISTS idx_state_members_state ON state_members(state_id);
        CREATE INDEX IF NOT EXISTS idx_state_sessions_state ON state_sessions(state_id);
        CREATE INDEX IF NOT EXISTS idx_state_sessions_token ON state_sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_member_records_state ON member_records(state_id);
        CREATE INDEX IF NOT EXISTS idx_member_positions_state ON member_positions(state_id);
        CREATE INDEX IF NOT EXISTS idx_member_positions_user ON member_positions(user_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category ON knowledge_entries(category);
        CREATE INDEX IF NOT EXISTS idx_ai_chat_logs_user ON ai_chat_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at);
        """

        if not self.executescript(schema):
            return False

        # Migration: keep old databases compatible with new state session fields.
        if not self.ensure_column("state_sessions", "ip_address", "TEXT"):
            logger.error("Failed to ensure state_sessions.ip_address column")
            return False
        if not self.ensure_column("state_sessions", "user_agent", "TEXT"):
            logger.error("Failed to ensure state_sessions.user_agent column")
            return False

        user_columns = [
            ("state", "TEXT DEFAULT ''"),
            ("state_id", "INTEGER REFERENCES states(id)"),
            ("game_name", "TEXT DEFAULT ''"),
            ("player_power", "INTEGER NOT NULL DEFAULT 0"),
            ("specialization", "TEXT DEFAULT ''"),
            ("discord_id", "TEXT DEFAULT ''"),
            ("alliance_role", "TEXT DEFAULT ''"),
            ("is_banned", "INTEGER NOT NULL DEFAULT 0"),
            ("building_levels_json", "TEXT DEFAULT '{}'"),
            ("research_levels_json", "TEXT DEFAULT '{}'"),
            ("academy_level", "INTEGER NOT NULL DEFAULT 0"),
        ]
        for column_name, column_type in user_columns:
            if not self.ensure_column("users", column_name, column_type):
                logger.error("Failed to ensure users.%s column", column_name)
                return False

        state_columns = [
            ("contact_email", "TEXT DEFAULT ''"),
            ("contact_discord", "TEXT DEFAULT ''"),
        ]
        for column_name, column_type in state_columns:
            if not self.ensure_column("states", column_name, column_type):
                logger.error("Failed to ensure states.%s column", column_name)
                return False

        oauth_columns = [
            ("access_token", "TEXT DEFAULT ''"),
            ("refresh_token", "TEXT DEFAULT ''"),
            ("token_expires_at", "TEXT"),
        ]
        for column_name, column_type in oauth_columns:
            if not self.ensure_column("oauth_identities", column_name, column_type):
                logger.error("Failed to ensure oauth_identities.%s column", column_name)
                return False

        return True


# إنشاء instance من قاعدة البيانات
db = Database()
