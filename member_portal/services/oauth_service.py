"""OAuth helpers for Google and optional Discord login."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

import aiohttp

from core.config import Config
from core.database import db
from utils.security import TokenManager

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USER_INFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

    @staticmethod
    def is_enabled() -> bool:
        return bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET)

    @staticmethod
    def get_authorization_url(state: str) -> Optional[str]:
        if not GoogleOAuthService.is_enabled():
            return None
        query = urlencode(
            {
                "client_id": Config.GOOGLE_CLIENT_ID,
                "redirect_uri": Config.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": "openid profile email",
                "state": state,
                "prompt": "select_account",
            }
        )
        return f"{GoogleOAuthService.GOOGLE_AUTH_URL}?{query}"

    @staticmethod
    async def get_access_token(code: str) -> Optional[Dict]:
        payload = {
            "client_id": Config.GOOGLE_CLIENT_ID,
            "client_secret": Config.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": Config.GOOGLE_REDIRECT_URI,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(GoogleOAuthService.GOOGLE_TOKEN_URL, data=payload) as response:
                if response.status != 200:
                    logger.error("Google token exchange failed with status %s", response.status)
                    return None
                return await response.json()

    @staticmethod
    async def get_user_info(access_token: str) -> Optional[Dict]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(GoogleOAuthService.GOOGLE_USER_INFO_URL, headers=headers) as response:
                if response.status != 200:
                    logger.error("Google user info fetch failed with status %s", response.status)
                    return None
                return await response.json()

    @staticmethod
    def _unique_username(email: str) -> str:
        base = (email or "google_user").split("@")[0] or "google_user"
        candidate = base
        suffix = 1
        while db.fetchone("SELECT id FROM users WHERE username = ?", (candidate,)):
            suffix += 1
            candidate = f"{base}_{suffix}"
        return candidate

    @staticmethod
    async def handle_callback(code: str) -> Tuple[bool, str, Optional[int]]:
        token_data = await GoogleOAuthService.get_access_token(code)
        if not token_data or "access_token" not in token_data:
            return False, "فشل الحصول على رمز الوصول", None

        user_info = await GoogleOAuthService.get_user_info(token_data["access_token"])
        if not user_info:
            return False, "فشل الحصول على معلومات المستخدم", None

        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name", "")
        avatar_url = user_info.get("picture")

        existing_identity = db.fetchone(
            "SELECT user_id FROM oauth_identities WHERE provider = ? AND provider_id = ?",
            ("google", google_id),
        )
        if existing_identity:
            db.update(
                "users",
                {"last_login": datetime.now().isoformat()},
                {"id": existing_identity["user_id"]},
            )
            return True, "تم تسجيل الدخول بنجاح", existing_identity["user_id"]

        existing_user = db.fetchone("SELECT id FROM users WHERE email = ?", (email,)) if email else None
        if existing_user:
            user_id = existing_user["id"]
            db.update(
                "users",
                {
                    "oauth_provider": "google",
                    "oauth_id": google_id,
                    "avatar_url": avatar_url,
                    "last_login": datetime.now().isoformat(),
                    "is_email_verified": 1,
                },
                {"id": user_id},
            )
        else:
            user_id = db.insert(
                "users",
                {
                    "username": GoogleOAuthService._unique_username(email or "google_user"),
                    "email": email,
                    "password_hash": "oauth-login",
                    "full_name": name,
                    "avatar_url": avatar_url,
                    "oauth_provider": "google",
                    "oauth_id": google_id,
                    "role": "member",
                    "is_email_verified": 1,
                    "last_login": datetime.now().isoformat(),
                },
            )

        if not user_id:
            return False, "فشل إنشاء أو ربط الحساب", None

        identity_exists = db.fetchone(
            "SELECT id FROM oauth_identities WHERE provider = ? AND provider_id = ?",
            ("google", google_id),
        )
        if not identity_exists:
            db.insert(
                "oauth_identities",
                {
                    "user_id": user_id,
                    "provider": "google",
                    "provider_id": google_id,
                    "email": email,
                    "name": name,
                    "avatar_url": avatar_url,
                },
            )

        return True, "تم تسجيل الدخول بنجاح", user_id


class DiscordOAuthService:
    DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
    DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
    DISCORD_USER_INFO_URL = "https://discord.com/api/users/@me"

    @staticmethod
    def is_enabled() -> bool:
        return bool(Config.DISCORD_CLIENT_ID and Config.DISCORD_CLIENT_SECRET)

    @staticmethod
    def get_authorization_url(state: str) -> Optional[str]:
        if not DiscordOAuthService.is_enabled():
            return None
        query = urlencode(
            {
                "client_id": Config.DISCORD_CLIENT_ID,
                "redirect_uri": Config.DISCORD_REDIRECT_URI,
                "response_type": "code",
                "scope": "identify email",
                "state": state,
                "prompt": "consent",
            }
        )
        return f"{DiscordOAuthService.DISCORD_AUTH_URL}?{query}"

    @staticmethod
    async def get_access_token(code: str) -> Optional[Dict]:
        payload = {
            "client_id": Config.DISCORD_CLIENT_ID,
            "client_secret": Config.DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": Config.DISCORD_REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with aiohttp.ClientSession() as session:
            async with session.post(DiscordOAuthService.DISCORD_TOKEN_URL, data=payload, headers=headers) as response:
                if response.status != 200:
                    logger.error("Discord token exchange failed with status %s", response.status)
                    return None
                return await response.json()

    @staticmethod
    async def get_user_info(access_token: str) -> Optional[Dict]:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(DiscordOAuthService.DISCORD_USER_INFO_URL, headers=headers) as response:
                if response.status != 200:
                    logger.error("Discord user info fetch failed with status %s", response.status)
                    return None
                return await response.json()

    @staticmethod
    def _unique_username(base_name: str) -> str:
        base = (base_name or "discord_user").replace(" ", "_")
        candidate = base
        suffix = 1
        while db.fetchone("SELECT id FROM users WHERE username = ?", (candidate,)):
            suffix += 1
            candidate = f"{base}_{suffix}"
        return candidate

    @staticmethod
    async def handle_callback(code: str) -> Tuple[bool, str, Optional[int]]:
        token_data = await DiscordOAuthService.get_access_token(code)
        if not token_data or "access_token" not in token_data:
            return False, "فشل الحصول على رمز Discord", None

        user_info = await DiscordOAuthService.get_user_info(token_data["access_token"])
        if not user_info:
            return False, "فشل الحصول على معلومات Discord", None

        discord_id = user_info.get("id")
        email = user_info.get("email")
        username = user_info.get("username", "discord_user")
        avatar = user_info.get("avatar")
        avatar_url = (
            f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png"
            if avatar and discord_id
            else None
        )

        existing_identity = db.fetchone(
            "SELECT user_id FROM oauth_identities WHERE provider = ? AND provider_id = ?",
            ("discord", discord_id),
        )
        if existing_identity:
            db.update(
                "users",
                {"last_login": datetime.now().isoformat()},
                {"id": existing_identity["user_id"]},
            )
            return True, "تم تسجيل الدخول بنجاح", existing_identity["user_id"]

        existing_user = db.fetchone("SELECT id FROM users WHERE email = ?", (email,)) if email else None
        if existing_user:
            user_id = existing_user["id"]
            db.update(
                "users",
                {
                    "oauth_provider": "discord",
                    "oauth_id": discord_id,
                    "avatar_url": avatar_url,
                    "last_login": datetime.now().isoformat(),
                    "is_email_verified": 1 if email else 0,
                },
                {"id": user_id},
            )
        else:
            user_id = db.insert(
                "users",
                {
                    "username": DiscordOAuthService._unique_username(username),
                    "email": email,
                    "password_hash": "oauth-login",
                    "full_name": username,
                    "avatar_url": avatar_url,
                    "oauth_provider": "discord",
                    "oauth_id": discord_id,
                    "role": "member",
                    "is_email_verified": 1 if email else 0,
                    "last_login": datetime.now().isoformat(),
                },
            )

        if not user_id:
            return False, "فشل إنشاء أو ربط حساب Discord", None

        identity_exists = db.fetchone(
            "SELECT id FROM oauth_identities WHERE provider = ? AND provider_id = ?",
            ("discord", discord_id),
        )
        if not identity_exists:
            db.insert(
                "oauth_identities",
                {
                    "user_id": user_id,
                    "provider": "discord",
                    "provider_id": discord_id,
                    "email": email,
                    "name": username,
                    "avatar_url": avatar_url,
                },
            )

        return True, "تم تسجيل الدخول بنجاح", user_id


class OAuthManager:
    """Coordinator for provider-specific OAuth logic."""

    def __init__(self, secret_key: bytes):
        self.token_manager = TokenManager(secret_key)

    def create_google_auth_url(self) -> Tuple[Optional[str], str]:
        state = self.token_manager.create_oauth_state()
        return GoogleOAuthService.get_authorization_url(state), state

    def create_discord_auth_url(self) -> Tuple[Optional[str], str]:
        state = self.token_manager.create_oauth_state()
        return DiscordOAuthService.get_authorization_url(state), state

    def verify_state(self, state: str) -> bool:
        return self.token_manager.verify_oauth_state(state)

    async def handle_google_callback(self, code: str) -> Tuple[bool, str, Optional[int]]:
        return await GoogleOAuthService.handle_callback(code)

    async def handle_discord_callback(self, code: str) -> Tuple[bool, str, Optional[int]]:
        return await DiscordOAuthService.handle_callback(code)