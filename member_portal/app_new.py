"""TNT-2 main entrypoint (aiohttp)."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from aiohttp import web
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from core.config import Config
from core.database import db
from core.permissions import PermissionManager, RoleManager, StatePermissionManager
from middleware import error_handler_middleware, logging_middleware, session_middleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    enable_async=True,
)


class TNTPortalApp:
    def __init__(self):
        self.app = web.Application(
            middlewares=[error_handler_middleware, logging_middleware, session_middleware]
        )
        self.setup_routes()

    def setup_routes(self) -> None:
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/register-page", self.register_page)
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/api/stats", self.public_stats)

        self.app.router.add_post("/api/auth/register", self.register)
        self.app.router.add_post("/api/auth/login", self.login)
        self.app.router.add_post("/api/auth/logout", self.logout)
        self.app.router.add_post("/api/auth/forgot-password", self.forgot_password)
        self.app.router.add_post("/api/auth/reset-password", self.reset_password)

        self.app.router.add_get("/auth/google", self.google_auth)
        self.app.router.add_get("/auth/google/callback", self.google_callback)
        self.app.router.add_get("/auth/discord", self.discord_auth)
        self.app.router.add_get("/auth/discord/callback", self.discord_callback)

        # Aliases to keep old links compatible
        self.app.router.add_get("/oauth/google/start", self.google_auth)
        self.app.router.add_get("/oauth/google/callback", self.google_callback)
        self.app.router.add_get("/oauth/discord/start", self.discord_auth)
        self.app.router.add_get("/oauth/discord/callback", self.discord_callback)

        self.app.router.add_get("/api/user/profile", self.get_user_profile)
        self.app.router.add_put("/api/user/profile", self.update_user_profile)
        self.app.router.add_post("/api/user/password", self.change_password)
        self.app.router.add_post("/api/user/email/request-verification", self.request_email_verification)
        self.app.router.add_post("/api/user/email/verify", self.verify_email)
        self.app.router.add_post("/api/user/email/change", self.change_email)

        self.app.router.add_get("/api/states", self.get_states)
        self.app.router.add_post("/api/states", self.create_state)
        self.app.router.add_get("/api/states/{state_id}", self.get_state)
        self.app.router.add_put("/api/states/{state_id}", self.update_state)
        self.app.router.add_delete("/api/states/{state_id}", self.delete_state)

        # State auth/dashboard
        self.app.router.add_get("/state-auth", self.state_auth_page)
        self.app.router.add_get("/state-register", self.state_register_page)
        self.app.router.add_post("/api/state/register", self.state_register)
        self.app.router.add_post("/api/state/login", self.state_login)
        self.app.router.add_post("/api/state/logout", self.state_logout)
        self.app.router.add_get("/api/state/dashboard", self.state_dashboard)
        self.app.router.add_get("/api/state/stats", self.state_stats)
        self.app.router.add_get("/api/state/members", self.state_members)
        self.app.router.add_post("/api/state/members", self.state_add_member)
        self.app.router.add_put("/api/state/members/{record_id}", self.state_update_member)
        self.app.router.add_delete("/api/state/members/{record_id}", self.state_delete_member)

        # Owner/admin
        self.app.router.add_get("/api/admin/dashboard", self.admin_dashboard)
        self.app.router.add_get("/api/admin/users", self.get_admin_users)
        self.app.router.add_post("/api/admin/users/{user_id}/role", self.change_user_role)
        self.app.router.add_post("/api/admin/permissions/grant", self.grant_user_permission)
        self.app.router.add_post("/api/admin/permissions/revoke", self.revoke_user_permission)

        # ── Form-compatible aliases (HTML form submit) ──
        self.app.router.add_post("/login", self.form_login)
        self.app.router.add_post("/register", self.form_register)
        self.app.router.add_post("/logout", self.form_logout)
        self.app.router.add_post("/state-login", self.form_state_login)
        self.app.router.add_post("/set-language", self.set_language)

        # ── Page routes ──
        self.app.router.add_get("/portal", self.portal_page)
        self.app.router.add_get("/dashboard", self.dashboard_page)
        self.app.router.add_get("/members", self.members_page)
        self.app.router.add_get("/profile", self.profile_page)
        self.app.router.add_get("/owner", self.owner_page)
        self.app.router.add_get("/transfers", self.transfers_page)
        self.app.router.add_get("/wars", self.wars_page)
        self.app.router.add_get("/teams", self.teams_page)
        self.app.router.add_get("/missions", self.missions_page)
        self.app.router.add_get("/resources", self.resources_page)
        self.app.router.add_get("/export", self.export_page)
        self.app.router.add_get("/discord-settings", self.discord_settings_page)
        self.app.router.add_get("/rally-leaders", self.rally_leaders_page)
        self.app.router.add_get("/forgot-password", self.forgot_password_page)

        if STATIC_DIR.exists():
            self.app.router.add_static("/static", path=STATIC_DIR)

    async def _render_template(self, template_name: str, context: dict | None = None, request: web.Request | None = None) -> web.Response:
        context = context or {}
        if request is not None and "current_user" not in context:
            context.setdefault("current_user", request.get("current_user"))
            context.setdefault("request_path", request.path)
        try:
            template = jinja_env.get_template(template_name)
            html = await template.render_async(**context)
            return web.Response(text=html, content_type="text/html")
        except TemplateNotFound:
            return web.Response(text=f"Template missing: {template_name}", status=404)

    async def index(self, request: web.Request) -> web.StreamResponse:
        return await self._render_template("auth.html", {"lang": self._lang(request), "title": "TNT-2 Login"}, request)

    async def register_page(self, request: web.Request) -> web.StreamResponse:
        return await self._render_template("register.html", {"lang": self._lang(request), "title": "TNT-2 Register"}, request)

    async def state_auth_page(self, request: web.Request) -> web.StreamResponse:
        return await self._render_template("state_auth.html", {"lang": "en", "title": "State Login"}, request)

    async def state_register_page(self, request: web.Request) -> web.StreamResponse:
        return await self._render_template("state_register.html", {"lang": "en", "title": "State Register"}, request)

    async def health_check(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "version": Config.PROJECT_VERSION})

    async def public_stats(self, request: web.Request) -> web.Response:
        total_users = db.fetchone("SELECT COUNT(*) AS count FROM users") or {"count": 0}
        total_states = db.fetchone("SELECT COUNT(*) AS count FROM states") or {"count": 0}
        owner = db.fetchone(
            "SELECT id, username, role FROM users WHERE username = ?",
            (Config.OWNER_USERNAME,),
        )
        return web.json_response(
            {
                "users": total_users["count"],
                "states": total_states["count"],
                "owner": owner,
                "version": Config.PROJECT_VERSION,
            }
        )

    async def register(self, request: web.Request) -> web.Response:
        from services.auth_service import AuthService

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        success, message, user_id = AuthService.register_user(
            payload.get("username", "").strip(),
            payload.get("email", "").strip(),
            payload.get("password", ""),
            payload.get("full_name", "").strip(),
        )
        status = 201 if success else 400
        body = {"success": success, "message": message}
        if user_id:
            body["user_id"] = user_id
        if not success:
            body = {"success": False, "error": message}
        return web.json_response(body, status=status)

    async def login(self, request: web.Request) -> web.Response:
        from services.auth_service import AuthService

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        success, message, user_id = AuthService.login(
            payload.get("username", "").strip(),
            payload.get("password", ""),
            request.remote,
        )
        if not success or not user_id:
            return web.json_response({"success": False, "error": message}, status=401)

        session_token = self._create_user_session(user_id, request)
        if not session_token:
            return web.json_response({"success": False, "error": "فشل إنشاء جلسة المستخدم"}, status=500)

        response = web.json_response({"success": True, "message": message, "user_id": user_id})
        response.set_cookie(
            Config.SESSION_COOKIE_NAME,
            session_token,
            max_age=Config.SESSION_TTL_SECONDS,
            httponly=True,
            secure=self._is_secure_cookie_enabled(),
            samesite="Lax",
        )
        return response

    async def logout(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"success": False, "error": "لم تقم بتسجيل الدخول"}, status=401)

        session_token = request.cookies.get(Config.SESSION_COOKIE_NAME)
        if session_token:
            db.delete("sessions", {"session_token": session_token})

        response = web.json_response({"success": True, "message": "تم تسجيل الخروج"})
        response.del_cookie(Config.SESSION_COOKIE_NAME)
        return response

    async def forgot_password(self, request: web.Request) -> web.Response:
        from services.auth_service import AuthService

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        success, message = AuthService.request_password_reset(payload.get("email", "").strip())
        status = 200 if success else 400
        key = "message" if success else "error"
        return web.json_response({"success": success, key: message}, status=status)

    async def reset_password(self, request: web.Request) -> web.Response:
        from services.auth_service import AuthService

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        success, message = AuthService.reset_password(
            payload.get("token", "").strip(),
            payload.get("new_password", ""),
        )
        status = 200 if success else 400
        key = "message" if success else "error"
        return web.json_response({"success": success, key: message}, status=status)

    async def google_auth(self, request: web.Request) -> web.StreamResponse:
        from services.oauth_service import OAuthManager

        oauth_manager = OAuthManager(Config.SECRET_KEY)
        auth_url, state = oauth_manager.create_google_auth_url()
        if not auth_url:
            return web.json_response({"error": "Google OAuth غير مفعل"}, status=400)

        response = web.HTTPFound(auth_url)
        response.set_cookie(
            "oauth_state",
            state,
            max_age=Config.OAUTH_STATE_TTL_SECONDS,
            httponly=True,
            secure=self._is_secure_cookie_enabled(),
            samesite="Lax",
        )
        return response

    async def google_callback(self, request: web.Request) -> web.StreamResponse:
        return await self._oauth_callback(request, provider="google")

    async def discord_auth(self, request: web.Request) -> web.StreamResponse:
        from services.oauth_service import OAuthManager

        oauth_manager = OAuthManager(Config.SECRET_KEY)
        auth_url, state = oauth_manager.create_discord_auth_url()
        if not auth_url:
            return web.json_response({"error": "Discord OAuth غير مفعل"}, status=400)

        response = web.HTTPFound(auth_url)
        response.set_cookie(
            "oauth_state",
            state,
            max_age=Config.OAUTH_STATE_TTL_SECONDS,
            httponly=True,
            secure=self._is_secure_cookie_enabled(),
            samesite="Lax",
        )
        return response

    async def discord_callback(self, request: web.Request) -> web.StreamResponse:
        return await self._oauth_callback(request, provider="discord")

    async def _oauth_callback(self, request: web.Request, provider: str) -> web.StreamResponse:
        from services.oauth_service import OAuthManager

        state = request.query.get("state")
        code = request.query.get("code")
        stored_state = request.cookies.get("oauth_state")

        if not state or not code or state != stored_state:
            return web.Response(text="Invalid OAuth state", status=400)

        oauth_manager = OAuthManager(Config.SECRET_KEY)
        if not oauth_manager.verify_state(state):
            return web.Response(text="Expired OAuth state", status=400)

        if provider == "google":
            success, message, user_id = await oauth_manager.handle_google_callback(code)
        else:
            success, message, user_id = await oauth_manager.handle_discord_callback(code)

        if not success or not user_id:
            return web.Response(text=message, status=400)

        session_token = self._create_user_session(user_id, request)
        response = web.HTTPFound("/")
        response.set_cookie(
            Config.SESSION_COOKIE_NAME,
            session_token,
            max_age=Config.SESSION_TTL_SECONDS,
            httponly=True,
            secure=self._is_secure_cookie_enabled(),
            samesite="Lax",
        )
        response.del_cookie("oauth_state")
        return response

    async def get_user_profile(self, request: web.Request) -> web.Response:
        from models.user_model import User

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        user = User(request["user_id"])
        if not user.load():
            return web.json_response({"error": "المستخدم غير موجود"}, status=404)

        return web.json_response(user.to_dict())

    async def update_user_profile(self, request: web.Request) -> web.Response:
        from models.user_model import User

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        user = User(request["user_id"])
        if not user.load():
            return web.json_response({"error": "المستخدم غير موجود"}, status=404)

        new_name = payload.get("full_name", "").strip()
        if not new_name:
            return web.json_response({"error": "الاسم مطلوب"}, status=400)

        if not user.update(full_name=new_name):
            return web.json_response({"error": "فشل التحديث"}, status=400)

        return web.json_response({"success": True, "message": "تم تحديث الاسم"})

    async def change_password(self, request: web.Request) -> web.Response:
        from models.user_model import User
        from utils.security import PasswordValidator, SecurityManager

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        user = User(request["user_id"])
        if not user.load():
            return web.json_response({"error": "المستخدم غير موجود"}, status=404)

        if not SecurityManager.verify_password(payload.get("current_password", ""), user.data.get("password_hash", "")):
            return web.json_response({"error": "كلمة المرور الحالية غير صحيحة"}, status=400)

        is_valid, message = PasswordValidator.validate(payload.get("new_password", ""))
        if not is_valid:
            return web.json_response({"error": message}, status=400)

        new_password_hash = SecurityManager.hash_password(payload["new_password"])
        user.update(password_hash=new_password_hash)

        return web.json_response({"success": True, "message": "تم تغيير كلمة المرور"})

    async def request_email_verification(self, request: web.Request) -> web.Response:
        from models.user_model import User
        from services.auth_service import AuthService

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        user = User(request["user_id"])
        if not user.load() or not user.email:
            return web.json_response({"error": "المستخدم غير موجود"}, status=404)

        success, message = AuthService.send_verification_email(user.id, user.email)
        status = 200 if success else 400
        key = "message" if success else "error"
        return web.json_response({"success": success, key: message}, status=status)

    async def verify_email(self, request: web.Request) -> web.Response:
        from services.auth_service import AuthService

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        success, message = AuthService.verify_email(request["user_id"], payload.get("code", ""))
        status = 200 if success else 400
        key = "message" if success else "error"
        return web.json_response({"success": success, key: message}, status=status)

    async def change_email(self, request: web.Request) -> web.Response:
        from models.user_model import User
        from services.auth_service import AuthService

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        new_email = payload.get("new_email", "").strip().lower()
        if not new_email or "@" not in new_email:
            return web.json_response({"error": "بريد إلكتروني غير صالح"}, status=400)

        existing = db.fetchone("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, request["user_id"]))
        if existing:
            return web.json_response({"error": "البريد مستخدم بالفعل"}, status=400)

        user = User(request["user_id"])
        if not user.load():
            return web.json_response({"error": "المستخدم غير موجود"}, status=404)

        success, message = AuthService.send_verification_email(user.id, new_email)
        if not success:
            return web.json_response({"error": message}, status=400)

        user.update(is_email_verified=0)
        return web.json_response(
            {
                "success": True,
                "message": "تم إرسال رمز التحقق إلى البريد الجديد. أكمل التحقق لتفعيل البريد.",
                "email": new_email,
            }
        )

    async def get_states(self, request: web.Request) -> web.Response:
        states = db.fetchall(
            "SELECT id, state_name, state_number, admin_user_id, is_active, created_at FROM states ORDER BY state_name"
        )
        return web.json_response({"states": states})

    async def create_state(self, request: web.Request) -> web.Response:
        from utils.security import SecurityManager

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "state.create"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        state_name = payload.get("state_name", "").strip()
        state_number = payload.get("state_number", "").strip()
        password = payload.get("password", "").strip()
        if not state_name or not password:
            return web.json_response({"error": "اسم الولاية وكلمة المرور مطلوبان"}, status=400)

        state_id = db.insert(
            "states",
            {
                "state_name": state_name,
                "state_number": state_number or None,
                "password_hash": SecurityManager.hash_password(password),
                "admin_user_id": request["user_id"],
                "description": payload.get("description", "").strip(),
            },
        )
        if not state_id:
            return web.json_response({"error": "فشل إنشاء الولاية"}, status=400)

        StatePermissionManager.add_state_member(request["user_id"], state_id, "admin")
        return web.json_response(
            {"success": True, "message": "تم إنشاء الولاية", "state_id": state_id},
            status=201,
        )

    async def get_state(self, request: web.Request) -> web.Response:
        from models.user_model import State

        try:
            state_id = int(request.match_info["state_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "معرف الولاية غير صالح"}, status=400)

        state = State(state_id)
        if not state.load():
            return web.json_response({"error": "الولاية غير موجودة"}, status=404)
        return web.json_response(state.to_dict())

    async def update_state(self, request: web.Request) -> web.Response:
        from models.user_model import State

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        try:
            state_id = int(request.match_info["state_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "معرف الولاية غير صالح"}, status=400)

        if not StatePermissionManager.is_state_admin(request["user_id"], state_id):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        update_data = {}
        for field in ("description", "logo_url", "state_name", "state_number"):
            if field in payload:
                update_data[field] = payload[field]

        if not update_data:
            return web.json_response({"error": "لا توجد بيانات للتحديث"}, status=400)

        state = State(state_id)
        if not state.load():
            return web.json_response({"error": "الولاية غير موجودة"}, status=404)

        if not state.update(**update_data):
            return web.json_response({"error": "فشل التحديث"}, status=400)

        return web.json_response({"success": True, "message": "تم التحديث"})

    async def delete_state(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "state.delete"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            state_id = int(request.match_info["state_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "معرف الولاية غير صالح"}, status=400)

        deleted = db.delete("states", {"id": state_id})
        if not deleted:
            return web.json_response({"error": "فشل الحذف"}, status=400)

        return web.json_response({"success": True, "message": "تم الحذف"})

    async def state_register(self, request: web.Request) -> web.Response:
        from utils.security import SecurityManager

        if not request.get("authenticated"):
            return web.json_response({"error": "تسجيل دخول المستخدم مطلوب"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        state_name = payload.get("state_name", "").strip()
        state_number = payload.get("state_number", "").strip()
        password = payload.get("password", "").strip()

        if not state_name or not password:
            return web.json_response({"error": "اسم الولاية وكلمة المرور مطلوبان"}, status=400)

        exists = db.fetchone("SELECT id FROM states WHERE state_name = ?", (state_name,))
        if exists:
            return web.json_response({"error": "اسم الولاية مستخدم مسبقاً"}, status=400)

        state_id = db.insert(
            "states",
            {
                "state_name": state_name,
                "state_number": state_number or None,
                "password_hash": SecurityManager.hash_password(password),
                "admin_user_id": request["user_id"],
                "description": payload.get("description", "").strip(),
            },
        )
        if not state_id:
            return web.json_response({"error": "فشل إنشاء الولاية"}, status=400)

        StatePermissionManager.add_state_member(request["user_id"], state_id, "admin")
        return web.json_response(
            {"success": True, "message": "تم إنشاء الولاية", "state_id": state_id},
            status=201,
        )

    async def state_login(self, request: web.Request) -> web.Response:
        from utils.security import SecurityManager

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        state_name = payload.get("state_name", "").strip()
        password = payload.get("password", "")

        state = db.fetchone(
            "SELECT id, password_hash FROM states WHERE state_name = ? AND is_active = 1",
            (state_name,),
        )
        if not state:
            return web.json_response({"error": "الولاية غير موجودة"}, status=404)

        if not SecurityManager.verify_password(password, state["password_hash"]):
            return web.json_response({"error": "بيانات دخول الولاية غير صحيحة"}, status=401)

        token = SecurityManager.generate_token()
        expires_at = (datetime.now() + timedelta(seconds=Config.SESSION_TTL_SECONDS)).isoformat()
        inserted_id = db.insert(
            "state_sessions",
            {
                "state_id": state["id"],
                "session_token": token,
                "ip_address": request.remote,
                "user_agent": request.headers.get("User-Agent", ""),
                "expires_at": expires_at,
            },
        )
        if not inserted_id:
            return web.json_response({"error": "فشل إنشاء جلسة الولاية"}, status=500)

        response = web.json_response({"success": True, "message": "تم تسجيل دخول الولاية"})
        response.set_cookie(
            Config.STATE_SESSION_COOKIE_NAME,
            token,
            max_age=Config.SESSION_TTL_SECONDS,
            httponly=True,
            secure=self._is_secure_cookie_enabled(),
            samesite="Lax",
        )
        return response

    async def state_logout(self, request: web.Request) -> web.Response:
        token = request.cookies.get(Config.STATE_SESSION_COOKIE_NAME)
        if token:
            db.delete("state_sessions", {"session_token": token})

        response = web.json_response({"success": True, "message": "تم تسجيل خروج الولاية"})
        response.del_cookie(Config.STATE_SESSION_COOKIE_NAME)
        return response

    async def state_dashboard(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        state = db.fetchone(
            "SELECT id, state_name, state_number, description FROM states WHERE id = ?",
            (request["state_id"],),
        )
        if not state:
            return web.json_response({"error": "الولاية غير موجودة"}, status=404)

        members_count = db.fetchone(
            "SELECT COUNT(*) AS count FROM member_records WHERE state_id = ?",
            (request["state_id"],),
        ) or {"count": 0}

        return web.json_response(
            {
                "state": state,
                "members_count": members_count["count"],
            }
        )

    async def state_stats(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        state_id = request["state_id"]
        stats = {
            "members": (db.fetchone("SELECT COUNT(*) AS count FROM member_records WHERE state_id = ?", (state_id,)) or {"count": 0})["count"],
            "transfers": (db.fetchone("SELECT COUNT(*) AS count FROM transfer_records WHERE state_id = ?", (state_id,)) or {"count": 0})["count"],
            "active_memberships": (db.fetchone("SELECT COUNT(*) AS count FROM state_members WHERE state_id = ?", (state_id,)) or {"count": 0})["count"],
        }
        return web.json_response({"state_id": state_id, "stats": stats})

    async def state_members(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        members = db.fetchall(
            "SELECT * FROM member_records WHERE state_id = ? ORDER BY created_at DESC",
            (request["state_id"],),
        )
        return web.json_response({"members": members})

    async def state_add_member(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        member_name = payload.get("member_name", "").strip()
        member_uid = payload.get("member_uid", "").strip()
        if not member_name or not member_uid:
            return web.json_response({"error": "اسم ومعرف العضو مطلوبان"}, status=400)

        member_id = db.insert(
            "member_records",
            {
                "state_id": request["state_id"],
                "member_name": member_name,
                "member_uid": member_uid,
                "alliance": payload.get("alliance", "").strip(),
                "rank": payload.get("rank", "").strip(),
                "power": payload.get("power", "").strip(),
                "furnace": payload.get("furnace", "").strip(),
                "notes": payload.get("notes", "").strip(),
            },
        )
        if not member_id:
            return web.json_response({"error": "فشل إضافة العضو"}, status=400)

        return web.json_response({"success": True, "member_id": member_id}, status=201)

    async def state_update_member(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        try:
            record_id = int(request.match_info["record_id"])
            payload = await request.json()
        except ValueError:
            return web.json_response({"error": "معرف السجل غير صالح"}, status=400)
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        allowed_fields = {"member_name", "alliance", "rank", "power", "furnace", "notes"}
        update_data = {k: v for k, v in payload.items() if k in allowed_fields}
        if not update_data:
            return web.json_response({"error": "لا توجد بيانات تحديث"}, status=400)

        update_data["updated_at"] = datetime.now().isoformat()
        ok = db.update(
            "member_records",
            update_data,
            {"id": record_id, "state_id": request["state_id"]},
        )
        if not ok:
            return web.json_response({"error": "فشل تحديث العضو"}, status=400)

        return web.json_response({"success": True, "message": "تم التحديث"})

    async def state_delete_member(self, request: web.Request) -> web.Response:
        if not request.get("state_authenticated"):
            return web.json_response({"error": "جلسة ولاية غير صالحة"}, status=401)

        try:
            record_id = int(request.match_info["record_id"])
        except ValueError:
            return web.json_response({"error": "معرف السجل غير صالح"}, status=400)

        ok = db.delete("member_records", {"id": record_id, "state_id": request["state_id"]})
        if not ok:
            return web.json_response({"error": "فشل حذف العضو"}, status=400)

        return web.json_response({"success": True, "message": "تم الحذف"})

    async def admin_dashboard(self, request: web.Request) -> web.Response:
        from models.user_model import User

        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)

        user = User(request["user_id"])
        if not user.load() or not user.is_super_owner():
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        stats = {
            "total_users": (db.fetchone("SELECT COUNT(*) AS count FROM users") or {"count": 0})["count"],
            "total_states": (db.fetchone("SELECT COUNT(*) AS count FROM states") or {"count": 0})["count"],
            "active_states": (db.fetchone("SELECT COUNT(*) AS count FROM states WHERE is_active = 1") or {"count": 0})["count"],
            "total_admins": (db.fetchone("SELECT COUNT(*) AS count FROM users WHERE role IN ('super_owner', 'admin')") or {"count": 0})["count"],
        }
        return web.json_response({"stats": stats})

    async def get_admin_users(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "user.read"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        users = db.fetchall(
            "SELECT id, username, email, role, is_admin, is_active, created_at FROM users ORDER BY created_at DESC"
        )
        return web.json_response({"users": users})

    async def change_user_role(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "user.update"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            target_user_id = int(request.match_info["user_id"])
            payload = await request.json()
        except ValueError:
            return web.json_response({"error": "معرف المستخدم غير صالح"}, status=400)
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)

        new_role = payload.get("role", "")
        if new_role not in Config.ROLES:
            return web.json_response({"error": "دور غير صحيح"}, status=400)

        if not RoleManager.change_user_role(target_user_id, new_role):
            return web.json_response({"error": "فشل تغيير الدور"}, status=400)

        return web.json_response({"success": True, "message": "تم تغيير الدور"})

    async def grant_user_permission(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "settings.manage"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            payload = await request.json()
            target_user_id = int(payload.get("user_id"))
            permission = payload.get("permission", "").strip()
        except Exception:
            return web.json_response({"error": "بيانات غير صالحة"}, status=400)

        if not permission:
            return web.json_response({"error": "الصلاحية مطلوبة"}, status=400)

        if not PermissionManager.grant_permission(target_user_id, permission):
            return web.json_response({"error": "فشل منح الصلاحية"}, status=400)

        return web.json_response({"success": True, "message": "تم منح الصلاحية"})

    async def revoke_user_permission(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        if not PermissionManager.has_permission(request["user_id"], "settings.manage"):
            return web.json_response({"error": "ليس لديك صلاحية"}, status=403)

        try:
            payload = await request.json()
            target_user_id = int(payload.get("user_id"))
            permission = payload.get("permission", "").strip()
        except Exception:
            return web.json_response({"error": "بيانات غير صالحة"}, status=400)

        if not permission:
            return web.json_response({"error": "الصلاحية مطلوبة"}, status=400)

        if not PermissionManager.revoke_permission(target_user_id, permission):
            return web.json_response({"error": "فشل سحب الصلاحية"}, status=400)

        return web.json_response({"success": True, "message": "تم سحب الصلاحية"})

    # ──────────────────────────────────────────────────────────
    # Form-compatible handlers (HTML form submit → redirect)
    # ──────────────────────────────────────────────────────────
    def _lang(self, request: web.Request) -> str:
        return request.cookies.get("lang", "ar")

    async def form_login(self, request: web.Request) -> web.StreamResponse:
        from services.auth_service import AuthService

        data = await request.post()
        login_id = data.get("login_id", "").strip()
        password = data.get("password", "")
        lang = self._lang(request)
        success, message, user_id = AuthService.login(login_id, password, request.remote)
        if not success or not user_id:
            return await self._render_template("auth.html", {
                "lang": lang, "title": "TNT Login",
                "flash": {"level": "error", "text": message},
            })
        session_token = self._create_user_session(user_id, request)
        if not session_token:
            return await self._render_template("auth.html", {
                "lang": lang, "title": "TNT Login",
                "flash": {"level": "error", "text": "فشل إنشاء الجلسة"},
            })
        response = web.HTTPFound("/portal")
        response.set_cookie(
            Config.SESSION_COOKIE_NAME, session_token,
            max_age=Config.SESSION_TTL_SECONDS, httponly=True,
            secure=self._is_secure_cookie_enabled(), samesite="Lax",
        )
        return response

    async def form_register(self, request: web.Request) -> web.StreamResponse:
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        success, message, user_id = AuthService.register_user(
            data.get("username", "").strip(),
            data.get("email", "").strip(),
            data.get("password", ""),
            data.get("full_name", data.get("username", "")).strip(),
        )
        if not success:
            return await self._render_template("register.html", {
                "lang": lang, "title": "Register",
                "flash": {"level": "error", "text": message},
            })
        return web.HTTPFound("/?registered=1")

    async def form_logout(self, request: web.Request) -> web.StreamResponse:
        session_token = request.cookies.get(Config.SESSION_COOKIE_NAME)
        if session_token:
            db.delete("sessions", {"session_token": session_token})
        response = web.HTTPFound("/")
        response.del_cookie(Config.SESSION_COOKIE_NAME)
        return response

    async def form_state_login(self, request: web.Request) -> web.StreamResponse:
        from utils.security import SecurityManager

        data = await request.post()
        state_name = data.get("state_name", "").strip()
        password = data.get("password", "")
        state = db.fetchone(
            "SELECT id, password_hash FROM states WHERE state_name = ? AND is_active = 1",
            (state_name,),
        )
        if not state or not SecurityManager.verify_password(password, state["password_hash"]):
            return await self._render_template("state_auth.html", {
                "lang": "en", "title": "State Login",
                "flash": {"level": "error", "text": "Invalid state name or password"},
            })
        token = SecurityManager.generate_token()
        expires_at = (datetime.now() + timedelta(seconds=Config.SESSION_TTL_SECONDS)).isoformat()
        inserted_id = db.insert("state_sessions", {
            "state_id": state["id"], "session_token": token,
            "ip_address": request.remote,
            "user_agent": request.headers.get("User-Agent", ""),
            "expires_at": expires_at,
        })
        if not inserted_id:
            return await self._render_template("state_auth.html", {
                "lang": "en", "title": "State Login",
                "flash": {"level": "error", "text": "Session creation failed"},
            })
        response = web.HTTPFound("/api/state/dashboard")
        response.set_cookie(
            Config.STATE_SESSION_COOKIE_NAME, token,
            max_age=Config.SESSION_TTL_SECONDS, httponly=True,
            secure=self._is_secure_cookie_enabled(), samesite="Lax",
        )
        return response

    async def set_language(self, request: web.Request) -> web.StreamResponse:
        data = await request.post()
        lang = data.get("lang", "ar")
        if lang not in ("ar", "en"):
            lang = "ar"
        next_url = data.get("next", "/")
        response = web.HTTPFound(next_url)
        response.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
        return response

    # ──────────────────────────────────────────────────────────
    # Page routes (server-rendered HTML pages)
    # ──────────────────────────────────────────────────────────
    def _base_ctx(self, request: web.Request, lang: str | None = None) -> dict:
        return {
            "lang": lang or self._lang(request),
            "current_user": request.get("current_user"),
            "request_path": request.path,
            "flash": None,
        }

    async def _require_auth_page(self, request: web.Request):
        """Return redirect if not authenticated, else None."""
        if not request.get("authenticated"):
            return web.HTTPFound("/")
        return None

    async def portal_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        states = db.fetchall("SELECT * FROM states WHERE is_active = 1") or []
        ctx = self._base_ctx(request)
        ctx.update({"title": "Operations Lists", "alliances": states, "state_number": None})
        return await self._render_template("portal_home.html", ctx)

    async def dashboard_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Dashboard", "state_number": None})
        return await self._render_template("dashboard.html", ctx)

    async def members_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        records = db.fetchall("SELECT * FROM users ORDER BY created_at DESC") or []
        ctx = self._base_ctx(request)
        ctx.update({"title": "Members", "records": records})
        return await self._render_template("members.html", ctx)

    async def profile_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Profile"})
        return await self._render_template("profile.html", ctx)

    async def owner_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        cu = request.get("current_user")
        if not (cu and getattr(cu, "role", "") == "super_owner"):
            return web.HTTPFound("/portal")
        users = db.fetchall("SELECT id, username, email, role, is_admin, created_at FROM users ORDER BY created_at DESC") or []
        ctx = self._base_ctx(request)
        ctx.update({"title": "Owner Panel", "users": users})
        return await self._render_template("owner_panel.html", ctx)

    async def transfers_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Transfers", "transfers": []})
        return await self._render_template("transfers.html", ctx)

    async def wars_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Wars", "wars": []})
        return await self._render_template("wars.html", ctx)

    async def teams_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Teams", "teams": []})
        return await self._render_template("teams.html", ctx)

    async def missions_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Missions", "missions": []})
        return await self._render_template("missions.html", ctx)

    async def resources_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Resources", "resources": []})
        return await self._render_template("resources.html", ctx)

    async def export_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Export Center"})
        return await self._render_template("export_center.html", ctx)

    async def discord_settings_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Discord Settings"})
        return await self._render_template("discord_settings.html", ctx)

    async def rally_leaders_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        ctx = self._base_ctx(request)
        ctx.update({"title": "Rally Leaders", "leaders": []})
        return await self._render_template("rally_leaders.html", ctx)

    async def forgot_password_page(self, request: web.Request) -> web.StreamResponse:
        lang = self._lang(request)
        return await self._render_template("forgot_password.html", {"lang": lang, "title": "Forgot Password"})

    def _create_user_session(self, user_id: int, request: web.Request) -> str | None:
        from utils.security import SecurityManager

        session_token = SecurityManager.generate_token()
        expires_at = (datetime.now() + timedelta(seconds=Config.SESSION_TTL_SECONDS)).isoformat()
        inserted_id = db.insert(
            "sessions",
            {
                "user_id": user_id,
                "session_token": session_token,
                "ip_address": request.remote,
                "user_agent": request.headers.get("User-Agent", ""),
                "expires_at": expires_at,
            },
        )
        if not inserted_id:
            return None
        return session_token

    @staticmethod
    def _is_secure_cookie_enabled() -> bool:
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


def create_super_owner() -> None:
    from utils.security import SecurityManager

    existing = db.fetchone("SELECT id FROM users WHERE username = ?", (Config.OWNER_USERNAME,))
    if existing:
        return

    password_hash = SecurityManager.hash_password(Config.OWNER_PASSWORD)
    db.insert(
        "users",
        {
            "username": Config.OWNER_USERNAME,
            "email": "owner@tnt-alliance.local",
            "password_hash": password_hash,
            "full_name": "مالك النظام",
            "role": "super_owner",
            "is_admin": 1,
            "is_email_verified": 1,
        },
    )
    logger.info("Created super owner account: %s", Config.OWNER_USERNAME)


async def init_app() -> web.Application:
    logger.info("Initializing database tables")
    db.init_tables()
    logger.info("Initializing default permissions")
    PermissionManager.init_default_permissions()
    logger.info("Ensuring owner account exists")
    create_super_owner()
    return TNTPortalApp().app


if __name__ == "__main__":
    web.run_app(asyncio.run(init_app()), host="0.0.0.0", port=8080)
