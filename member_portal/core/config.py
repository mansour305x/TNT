"""
TNT Portal Configuration
========================
تحديد جميع الإعدادات والثوابت الأساسية للمشروع
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# تحميل متغيرات البيئة
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


class Config:
    """الإعدادات الأساسية للتطبيق"""

    # ── قاعدة البيانات ──
    DB_PATH = Path(os.getenv("PORTAL_DB_PATH", BASE_DIR / "portal.db"))
    
    # ── معلومات السر ──
    SECRET_KEY = os.getenv("PORTAL_SECRET_KEY", "change-me-in-production").encode("utf-8")
    
    # ── جلسات المستخدم ──
    SESSION_COOKIE_NAME = "member_portal_session"
    STATE_SESSION_COOKIE_NAME = "state_portal_session"
    SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 أيام
    
    # ── الرموز والانتهاء ──
    RESET_TOKEN_TTL_SECONDS = 60 * 30  # 30 دقيقة
    EMAIL_VERIFY_TOKEN_TTL_SECONDS = 60 * 60 * 24  # 24 ساعة
    OAUTH_STATE_TTL_SECONDS = 60 * 10  # 10 دقائق
    
    # ── حساب المالك الرئيسي ──
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "DANGER")
    OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "Aa@123456")
    OWNER_ROLE = "super_owner"
    
    # ── OAuth2 Configuration ──
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/google/callback")
    
    DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
    DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
    DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/auth/discord/callback")
    
    # ── إعدادات البريد الإلكتروني (Gmail SMTP) ──
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USERNAME)
    FROM_NAME = os.getenv("FROM_NAME", "TNT Alliance")
    
    # ── اللغات المدعومة ──
    SUPPORTED_LANGUAGES = ["en", "ar"]
    DEFAULT_LANGUAGE = "ar"
    LANGUAGE_COOKIE_NAME = "portal_lang"
    
    # ── أدوار المستخدمين (Roles) ──
    ROLES = {
        "super_owner": {"level": 100, "description": "مالك النظام الرئيسي"},
        "admin": {"level": 50, "description": "مسؤول عام"},
        "state_admin": {"level": 40, "description": "مسؤول الولاية"},
        "moderator": {"level": 30, "description": "مشرف"},
        "member": {"level": 10, "description": "عضو"},
        "guest": {"level": 1, "description": "ضيف"},
    }
    
    # ── الصلاحيات (Permissions) ──
    PERMISSIONS = {
        # إدارة المستخدمين
        "user.create": "إنشاء مستخدم جديد",
        "user.read": "عرض بيانات المستخدمين",
        "user.update": "تعديل بيانات المستخدمين",
        "user.delete": "حذف المستخدمين",
        
        # إدارة الولايات
        "state.create": "إنشاء ولاية جديدة",
        "state.read": "عرض بيانات الولايات",
        "state.update": "تعديل بيانات الولايات",
        "state.delete": "حذف الولايات",
        "state.members": "إدارة أعضاء الولاية",
        
        # إدارة الأعضاء
        "member.create": "إضافة عضو جديد",
        "member.read": "عرض بيانات الأعضاء",
        "member.update": "تعديل بيانات الأعضاء",
        "member.delete": "حذف الأعضاء",
        "member.export": "تصدير بيانات الأعضاء",
        
        # الإعدادات
        "settings.manage": "إدارة إعدادات النظام",
        "settings.smtp": "تكوين إعدادات البريد",
        
        # السجلات
        "logs.view": "عرض السجلات",
    }
    
    # ── الجداول والقوائم الافتراضية ──
    DEFAULT_LISTS = [
        {"list_key": "member_registry", "label": "Member Registry", "sort_order": 10, "is_enabled": 1},
        {"list_key": "transfers", "label": "Transfers List", "sort_order": 20, "is_enabled": 1},
    ]
    
    # ── معلومات المشروع ──
    PROJECT_NAME = "TNT Alliance Portal"
    PROJECT_VERSION = "2.0.0"
    
    @staticmethod
    def init_db_dir():
        """إنشاء مجلد قاعدة البيانات إذا كان غير موجود"""
        Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# تهيئة مجلد قاعدة البيانات
Config.init_db_dir()
