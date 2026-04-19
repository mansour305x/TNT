"""TNT-2 main entrypoint (aiohttp)."""

from __future__ import annotations

import asyncio
import json
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
from services.game_portal_service import GamePortalService

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
        self.app.router.add_get("/state-portal", self.state_portal_page)

        self.app.router.add_post("/api/auth/register", self.register)
        self.app.router.add_post("/api/auth/login", self.login)
        self.app.router.add_post("/api/auth/logout", self.logout)
        self.app.router.add_post("/api/auth/forgot-password", self.forgot_password)
        self.app.router.add_post("/api/auth/reset-password", self.reset_password)
        self.app.router.add_post("/api/calculators/{calculator_type}", self.calculate_api)
        self.app.router.add_get("/api/map", self.map_api)
        self.app.router.add_post("/api/ai/chat", self.ai_chat_api)

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
        self.app.router.add_post("/state-logout", self.form_state_logout)
        self.app.router.add_post("/set-language", self.set_language)
        self.app.router.add_post("/owner/states/create", self.owner_create_state)
        self.app.router.add_post("/owner/states/{state_id}/update", self.owner_update_state)
        self.app.router.add_post("/owner/states/{state_id}/toggle", self.owner_toggle_state)
        self.app.router.add_post("/owner/members/{user_id}/update", self.owner_update_member)
        self.app.router.add_post("/owner/members/{user_id}/ban", self.owner_toggle_member_ban)
        self.app.router.add_post("/owner/settings/map", self.owner_map_settings)
        self.app.router.add_post("/owner/settings/calculators", self.owner_calculator_settings)
        self.app.router.add_post("/owner/knowledge", self.owner_save_knowledge)

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
        self.app.router.add_post("/forgot-password/request", self.form_forgot_password)
        self.app.router.add_get("/reset-password", self.reset_password_page)
        self.app.router.add_post("/reset-password", self.form_reset_password)

        # Profile form routes
        self.app.router.add_post("/profile", self.form_update_profile)
        self.app.router.add_post("/profile/password", self.form_change_password)
        self.app.router.add_get("/profile/verify-email", self.verify_email_page)
        self.app.router.add_post("/profile/verify-email", self.form_verify_email)
        self.app.router.add_post("/profile/resend-verify-email", self.form_resend_verify_email)

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
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        success, message, user_id = GamePortalService.register_member(payload)
        status = 201 if success else 400
        body = {"success": success, "message": message}
        if user_id:
            body["user_id"] = user_id
        if not success:
            body = {"success": False, "error": message}
        return web.json_response(body, status=status)

    async def login(self, request: web.Request) -> web.Response:
        try:
            payload = await request.json()
        except Exception:
            return web.json_response({"success": False, "error": "بيانات JSON غير صالحة"}, status=400)

        login_type = payload.get("login_type", "member").strip().lower()
        login_id = payload.get("email", payload.get("username", "")).strip()
        password = payload.get("password", "")

        if login_type == "state":
            success, message, state_id = GamePortalService.authenticate_state(login_id, password)
            if not success or not state_id:
                return web.json_response({"success": False, "error": message}, status=401)
            token = self._create_state_session(state_id, request)
            if not token:
                return web.json_response({"success": False, "error": "فشل إنشاء جلسة الولاية"}, status=500)
            response = web.json_response({"success": True, "message": message, "state_id": state_id, "redirect": "/state-portal"})
            response.set_cookie(
                Config.STATE_SESSION_COOKIE_NAME,
                token,
                max_age=Config.SESSION_TTL_SECONDS,
                httponly=True,
                secure=self._is_secure_cookie_enabled(),
                samesite="Lax",
            )
            return response

        success, message, user_id = GamePortalService.authenticate_member(login_id, password, request.remote)
        if not success or not user_id:
            return web.json_response({"success": False, "error": message}, status=401)

        session_token = self._create_user_session(user_id, request)
        if not session_token:
            return web.json_response({"success": False, "error": "فشل إنشاء جلسة المستخدم"}, status=500)

        current_user = db.fetchone("SELECT role FROM users WHERE id = ?", (user_id,)) or {}
        response = web.json_response(
            {
                "success": True,
                "message": message,
                "user_id": user_id,
                "redirect": "/owner" if current_user.get("role") == "super_owner" else "/portal",
            }
        )
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
        data = await request.post()
        login_id = data.get("email", data.get("login_id", "")).strip()
        password = data.get("password", "")
        login_type = data.get("login_type", "member").strip().lower()
        lang = self._lang(request)
        if login_type == "state":
            success, message, state_id = GamePortalService.authenticate_state(login_id, password)
            if not success or not state_id:
                return await self._render_template("auth.html", {
                    "lang": lang,
                    "title": "TNT Login",
                    "flash": {"level": "error", "text": message},
                })
            token = self._create_state_session(state_id, request)
            if not token:
                return await self._render_template("auth.html", {
                    "lang": lang,
                    "title": "TNT Login",
                    "flash": {"level": "error", "text": "فشل إنشاء جلسة الولاية"},
                })
            response = web.HTTPFound("/state-portal")
            response.set_cookie(
                Config.STATE_SESSION_COOKIE_NAME,
                token,
                max_age=Config.SESSION_TTL_SECONDS,
                httponly=True,
                secure=self._is_secure_cookie_enabled(),
                samesite="Lax",
            )
            return response

        success, message, user_id = GamePortalService.authenticate_member(login_id, password, request.remote)
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
        role_row = db.fetchone("SELECT role FROM users WHERE id = ?", (user_id,)) or {}
        response = web.HTTPFound("/owner" if role_row.get("role") == "super_owner" else "/portal")
        response.set_cookie(
            Config.SESSION_COOKIE_NAME, session_token,
            max_age=Config.SESSION_TTL_SECONDS, httponly=True,
            secure=self._is_secure_cookie_enabled(), samesite="Lax",
        )
        return response

    async def form_register(self, request: web.Request) -> web.StreamResponse:
        data = await request.post()
        lang = self._lang(request)
        success, message, user_id = GamePortalService.register_member(dict(data))
        if not success:
            return await self._render_template("register.html", {
                "lang": lang, "title": "Register",
                "flash": {"level": "error", "text": message},
            })
        response = web.HTTPFound("/portal")
        session_token = self._create_user_session(user_id, request) if user_id else None
        if session_token:
            response.set_cookie(
                Config.SESSION_COOKIE_NAME,
                session_token,
                max_age=Config.SESSION_TTL_SECONDS,
                httponly=True,
                secure=self._is_secure_cookie_enabled(),
                samesite="Lax",
            )
        return response

    async def form_logout(self, request: web.Request) -> web.StreamResponse:
        session_token = request.cookies.get(Config.SESSION_COOKIE_NAME)
        if session_token:
            db.delete("sessions", {"session_token": session_token})
        response = web.HTTPFound("/")
        response.del_cookie(Config.SESSION_COOKIE_NAME)
        return response

    async def form_state_login(self, request: web.Request) -> web.StreamResponse:
        data = await request.post()
        state_name = data.get("state_name", data.get("email", "")).strip()
        password = data.get("password", "")
        success, message, state_id = GamePortalService.authenticate_state(state_name, password)
        if not success or not state_id:
            return await self._render_template("state_auth.html", {
                "lang": "en", "title": "State Login",
                "flash": {"level": "error", "text": message},
            })
        token = self._create_state_session(state_id, request)
        if not token:
            return await self._render_template("state_auth.html", {
                "lang": "en", "title": "State Login",
                "flash": {"level": "error", "text": "Session creation failed"},
            })
        response = web.HTTPFound("/state-portal")
        response.set_cookie(
            Config.STATE_SESSION_COOKIE_NAME, token,
            max_age=Config.SESSION_TTL_SECONDS, httponly=True,
            secure=self._is_secure_cookie_enabled(), samesite="Lax",
        )
        return response

    async def form_state_logout(self, request: web.Request) -> web.StreamResponse:
        token = request.cookies.get(Config.STATE_SESSION_COOKIE_NAME)
        if token:
            db.delete("state_sessions", {"session_token": token})
        response = web.HTTPFound("/")
        response.del_cookie(Config.STATE_SESSION_COOKIE_NAME)
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
        dashboard = GamePortalService.member_dashboard_data(request["user_id"])
        ctx = self._base_ctx(request)
        ctx.update(
            {
                "title": "بوابة الأعضاء",
                "dashboard": dashboard,
                "profile": dashboard["profile"],
                "map_data": dashboard["map_data"],
                "knowledge_highlights": dashboard["knowledge_highlights"],
                "calculator_catalog": dashboard["calculator_catalog"],
            }
        )
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
        records = db.fetchall(
            """
            SELECT id, email, username, game_name, state, player_power, specialization, alliance_role,
                   is_banned, role, created_at
            FROM users
            WHERE role IN ('member', 'admin', 'state_admin')
            ORDER BY player_power DESC, created_at DESC
            """
        ) or []
        ctx = self._base_ctx(request)
        ctx.update({"title": "Members", "records": records})
        return await self._render_template("members.html", ctx)

    async def profile_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        smtp_ok = bool(Config.SMTP_USERNAME and Config.SMTP_PASSWORD)
        cu = request.get("current_user")
        has_pending = False
        if cu and cu.email and smtp_ok:
            row = db.fetchone(
                "SELECT id FROM email_verification_codes WHERE user_id = ? AND is_used = 0 ORDER BY id DESC LIMIT 1",
                (cu.id,)
            )
            has_pending = row is not None
        ctx = self._base_ctx(request)
        ctx.update({"title": "Profile", "smtp_configured": smtp_ok,
                    "has_pending_email_verification": has_pending})
        return await self._render_template("profile.html", ctx)

    async def owner_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        cu = request.get("current_user")
        if not (cu and getattr(cu, "role", "") == "super_owner"):
            return web.HTTPFound("/portal")
        owner_data = GamePortalService.owner_dashboard_data()
        ctx = self._base_ctx(request)
        ctx.update({"title": "Owner Panel", **owner_data})
        return await self._render_template("owner_panel.html", ctx)

    async def state_portal_page(self, request: web.Request) -> web.StreamResponse:
        if not request.get("state_authenticated"):
            return web.HTTPFound("/")
        state_row = db.fetchone(
            "SELECT id, state_name, state_number, description, contact_email, contact_discord FROM states WHERE id = ?",
            (request["state_id"],),
        )
        if not state_row:
            return web.HTTPFound("/")
        members = db.fetchall(
            "SELECT id, member_name, member_uid, alliance, rank, power, created_at FROM member_records WHERE state_id = ? ORDER BY created_at DESC",
            (request["state_id"],),
        )
        transfers = db.fetchall(
            "SELECT id, member_name, member_uid, power, furnace, current_state, future_alliance, created_at FROM transfer_records WHERE state_id = ? ORDER BY created_at DESC",
            (request["state_id"],),
        )
        return await self._render_template(
            "state_portal.html",
            {
                "lang": self._lang(request),
                "title": "State Portal",
                "sa": state_row,
                "members": members,
                "transfers": transfers,
                "alliances": [state_row["state_name"], state_row["state_number"]],
                "fields": [],
                "request_path": request.path,
                "current_user": request.get("current_user"),
            },
        )

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

    async def reset_password_page(self, request: web.Request) -> web.StreamResponse:
        token = request.rel_url.query.get("token", "")
        lang = self._lang(request)
        return await self._render_template("reset_password.html", {"lang": lang, "title": "Reset Password", "token": token})

    async def form_forgot_password(self, request: web.Request) -> web.StreamResponse:
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        email = data.get("email", "").strip()
        ok, msg = AuthService.request_password_reset(email)
        level = "success" if ok else "error"
        return await self._render_template("forgot_password.html", {
            "lang": lang, "title": "Forgot Password",
            "flash": {"level": level, "text": msg},
        })

    async def form_reset_password(self, request: web.Request) -> web.StreamResponse:
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        token = data.get("token", "").strip()
        new_password = data.get("new_password", "")
        ok, msg = AuthService.reset_password(token, new_password)
        if ok:
            return await self._render_template("auth.html", {
                "lang": lang, "title": "Sign In",
                "flash": {"level": "success", "text": "تم تغيير كلمة المرور. يمكنك تسجيل الدخول الآن." if lang == "ar" else "Password changed. You can sign in now."},
            })
        return await self._render_template("reset_password.html", {
            "lang": lang, "title": "Reset Password", "token": token,
            "flash": {"level": "error", "text": msg},
        })

    async def form_update_profile(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        user_id = request["user_id"]
        email = data.get("email", "").strip()
        state = data.get("state", "").strip()

        cu = request.get("current_user")
        # Update profile
        from core.database import db as _db
        _db.update("users", {"email": email or None, "state": state or None}, {"id": user_id})
        # If email changed and SMTP configured, send verification
        smtp_ok = bool(Config.SMTP_USERNAME and Config.SMTP_PASSWORD)
        flash_text = "تم حفظ البيانات." if lang == "ar" else "Profile saved."
        if email and smtp_ok and cu and cu.email != email:
            ok, msg = AuthService.request_email_verification(user_id, email)
            if ok:
                flash_text = ("تم حفظ البيانات وإرسال رمز التحقق." if lang == "ar"
                              else "Profile saved. A verification code was sent.")
        ctx = self._base_ctx(request)
        ctx.update({"title": "Profile", "smtp_configured": smtp_ok,
                    "has_pending_email_verification": False,
                    "flash": {"level": "success", "text": flash_text}})
        return await self._render_template("profile.html", ctx)

    async def form_change_password(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        user_id = request["user_id"]
        current_pw = data.get("current_password", "")
        new_pw = data.get("new_password", "")
        ok, msg = AuthService.change_password(user_id, current_pw, new_pw)
        smtp_ok = bool(Config.SMTP_USERNAME and Config.SMTP_PASSWORD)
        ctx = self._base_ctx(request)
        ctx.update({"title": "Profile", "smtp_configured": smtp_ok,
                    "has_pending_email_verification": False,
                    "flash": {"level": "success" if ok else "error", "text": msg}})
        return await self._render_template("profile.html", ctx)

    async def verify_email_page(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        lang = self._lang(request)
        cu = request.get("current_user")
        pending_email = cu.email if cu else ""
        return await self._render_template("verify_email_code.html", {
            "lang": lang, "title": "Verify Email", "pending_email": pending_email,
            "current_user": cu, "request_path": request.path,
        })

    async def form_verify_email(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        from services.auth_service import AuthService

        data = await request.post()
        lang = self._lang(request)
        user_id = request["user_id"]
        code = data.get("verify_code", "").strip()
        ok, msg = AuthService.verify_email(user_id, code)
        smtp_ok = bool(Config.SMTP_USERNAME and Config.SMTP_PASSWORD)
        ctx = self._base_ctx(request)
        ctx.update({"title": "Profile", "smtp_configured": smtp_ok,
                    "has_pending_email_verification": not ok,
                    "flash": {"level": "success" if ok else "error", "text": msg}})
        return await self._render_template("profile.html", ctx)

    async def form_resend_verify_email(self, request: web.Request) -> web.StreamResponse:
        redir = await self._require_auth_page(request)
        if redir:
            return redir
        from services.auth_service import AuthService

        lang = self._lang(request)
        user_id = request["user_id"]
        cu = request.get("current_user")
        email = cu.email if cu else ""
        ok, msg = AuthService.request_email_verification(user_id, email)
        return await self._render_template("verify_email_code.html", {
            "lang": lang, "title": "Verify Email",
            "pending_email": email,
            "current_user": cu, "request_path": request.path,
            "flash": {"level": "success" if ok else "error", "text": msg},
        })

    async def calculate_api(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        try:
            payload = await request.json()
            calculator_type = request.match_info["calculator_type"]
            if calculator_type == "troops":
                result = GamePortalService.calculate_training(
                    payload.get("troop_type", "infantry"),
                    int(payload.get("tier", 1)),
                    int(payload.get("count", 1)),
                    float(payload.get("speed_bonus_percent", 0)),
                )
            elif calculator_type in {"building", "research", "academy"}:
                result = GamePortalService.calculate_upgrade(
                    calculator_type,
                    payload.get("target_key", "hq" if calculator_type == "building" else "academy"),
                    int(payload.get("current_level", 0)),
                    int(payload.get("target_level", 1)),
                    float(payload.get("speed_bonus_percent", 0)),
                )
            else:
                return web.json_response({"error": "نوع الحاسبة غير مدعوم"}, status=400)
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception:
            return web.json_response({"error": "بيانات الحاسبة غير صالحة"}, status=400)
        return web.json_response({"success": True, "result": result})

    async def map_api(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        user_row = db.fetchone("SELECT state FROM users WHERE id = ?", (request["user_id"],)) or {}
        return web.json_response({"success": True, "map": GamePortalService.compute_bear_map(user_row.get("state"))})

    async def ai_chat_api(self, request: web.Request) -> web.Response:
        if not request.get("authenticated"):
            return web.json_response({"error": "غير موثق"}, status=401)
        try:
            payload = await request.json()
            question = payload.get("question", "").strip()
        except Exception:
            return web.json_response({"error": "بيانات JSON غير صالحة"}, status=400)
        if not question:
            return web.json_response({"error": "السؤال مطلوب"}, status=400)
        answer = GamePortalService.ai_answer(request["user_id"], question)
        return web.json_response({"success": True, **answer})

    async def owner_create_state(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        data = await request.post()
        success, message, _ = GamePortalService.create_state_account(dict(data), request["user_id"])
        response = web.HTTPFound("/owner")
        response.set_cookie("owner_flash", json.dumps({"level": "success" if success else "error", "text": message}, ensure_ascii=False), max_age=10)
        return response

    async def owner_update_state(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        try:
            state_id = int(request.match_info["state_id"])
        except ValueError:
            return web.HTTPFound("/owner")
        data = await request.post()
        GamePortalService.update_state_account(state_id, dict(data))
        return web.HTTPFound("/owner")

    async def owner_toggle_state(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        try:
            state_id = int(request.match_info["state_id"])
        except ValueError:
            return web.HTTPFound("/owner")
        data = await request.post()
        GamePortalService.toggle_state(state_id, data.get("is_active", "1") == "1")
        return web.HTTPFound("/owner")

    async def owner_update_member(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        try:
            user_id = int(request.match_info["user_id"])
        except ValueError:
            return web.HTTPFound("/owner")
        data = await request.post()
        GamePortalService.update_member_account(user_id, dict(data))
        return web.HTTPFound("/owner")

    async def owner_toggle_member_ban(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        try:
            user_id = int(request.match_info["user_id"])
        except ValueError:
            return web.HTTPFound("/owner")
        data = await request.post()
        GamePortalService.set_member_ban(user_id, data.get("is_banned", "1") == "1")
        return web.HTTPFound("/owner")

    async def owner_map_settings(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        data = await request.post()
        custom_layout_raw = data.get("custom_layout", "").strip()
        custom_layout = []
        if custom_layout_raw:
            try:
                custom_layout = json.loads(custom_layout_raw)
            except json.JSONDecodeError:
                custom_layout = []
        GamePortalService.set_map_settings(
            data.get("shape", "circle"),
            int(data.get("layers", 3)),
            int(data.get("spacing", 130)),
            data.get("sort_by", "power"),
            custom_layout,
        )
        return web.HTTPFound("/owner")

    async def owner_calculator_settings(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        data = await request.post()
        try:
            multiplier = float(data.get("multiplier", 1))
        except ValueError:
            multiplier = 1.0
        GamePortalService.upsert_calculator_modifier(
            data.get("calculator_type", "building"),
            data.get("target_key", "hq"),
            data.get("resource_key", "food"),
            multiplier,
        )
        return web.HTTPFound("/owner")

    async def owner_save_knowledge(self, request: web.Request) -> web.StreamResponse:
        owner = request.get("current_user")
        if not (owner and owner.is_owner):
            return web.HTTPFound("/portal")
        data = await request.post()
        GamePortalService.upsert_knowledge_entry(
            data.get("category", "events").strip(),
            data.get("entry_name", "").strip(),
            data.get("tags", "").split(","),
            data.get("summary", "").strip(),
            data.get("best_use", "").strip(),
        )
        return web.HTTPFound("/owner")

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

    def _create_state_session(self, state_id: int, request: web.Request) -> str | None:
        from utils.security import SecurityManager

        session_token = SecurityManager.generate_token()
        expires_at = (datetime.now() + timedelta(seconds=Config.SESSION_TTL_SECONDS)).isoformat()
        inserted_id = db.insert(
            "state_sessions",
            {
                "state_id": state_id,
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
    logger.info("Bootstrapping gameplay data")
    GamePortalService.bootstrap()
    logger.info("Initializing default permissions")
    PermissionManager.init_default_permissions()
    logger.info("Ensuring owner account exists")
    create_super_owner()
    return TNTPortalApp().app


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    web.run_app(asyncio.run(init_app()), host="0.0.0.0", port=port)
