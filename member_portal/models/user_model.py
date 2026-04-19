"""Lightweight data models used by the member portal."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.database import db
from core.permissions import PermissionManager, StatePermissionManager


class User:
    """Simple active-record style wrapper around the users table."""

    def __init__(self, user_id: int):
        self.id = user_id
        self._data: Optional[Dict[str, Any]] = None

    def load(self) -> bool:
        self._data = db.fetchone("SELECT * FROM users WHERE id = ?", (self.id,))
        return self._data is not None

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        if self._data is None:
            self.load()
        return self._data

    @property
    def username(self) -> Optional[str]:
        return self.data.get("username") if self.data else None

    @property
    def email(self) -> Optional[str]:
        return self.data.get("email") if self.data else None

    @property
    def full_name(self) -> Optional[str]:
        return self.data.get("full_name") if self.data else None

    @property
    def role(self) -> Optional[str]:
        return self.data.get("role") if self.data else None

    @property
    def is_admin(self) -> bool:
        return bool(self.data and self.data.get("is_admin"))

    @property
    def is_email_verified(self) -> bool:
        return bool(self.data and self.data.get("is_email_verified"))

    @property
    def is_active(self) -> bool:
        return bool(self.data and self.data.get("is_active"))

    def is_super_owner(self) -> bool:
        return self.role == "super_owner"

    @property
    def is_owner(self) -> bool:
        return self.role == "super_owner"

    @property
    def state(self) -> Optional[str]:
        return self.data.get("state") if self.data else None

    @property
    def created_at(self) -> Optional[str]:
        return self.data.get("created_at") if self.data else None

    def update(self, **kwargs) -> bool:
        if not kwargs:
            return True
        kwargs.setdefault("updated_at", datetime.now().isoformat())
        updated = db.update("users", kwargs, {"id": self.id})
        if updated:
            self._data = None
        return updated

    def get_permissions(self) -> List[str]:
        return sorted(PermissionManager.get_user_permissions(self.id))

    def has_permission(self, permission: str) -> bool:
        return PermissionManager.has_permission(self.id, permission)

    def get_states(self) -> List[Dict[str, Any]]:
        return db.fetchall(
            """
            SELECT s.id, s.state_name, s.state_number, sm.role AS member_role
            FROM states s
            JOIN state_members sm ON sm.state_id = s.id
            WHERE sm.user_id = ?
            ORDER BY s.state_name
            """,
            (self.id,),
        )

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        if not self.data:
            return {}

        result = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_admin": self.is_admin,
            "is_email_verified": self.is_email_verified,
            "is_active": self.is_active,
            "avatar_url": self.data.get("avatar_url"),
            "created_at": self.data.get("created_at"),
            "updated_at": self.data.get("updated_at"),
            "last_login": self.data.get("last_login"),
        }
        if include_sensitive:
            result["password_hash"] = self.data.get("password_hash")
        return result


class State:
    """Simple wrapper around the states table."""

    def __init__(self, state_id: int):
        self.id = state_id
        self._data: Optional[Dict[str, Any]] = None

    def load(self) -> bool:
        self._data = db.fetchone("SELECT * FROM states WHERE id = ?", (self.id,))
        return self._data is not None

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        if self._data is None:
            self.load()
        return self._data

    @property
    def name(self) -> Optional[str]:
        return self.data.get("state_name") if self.data else None

    @property
    def state_number(self) -> Optional[str]:
        return self.data.get("state_number") if self.data else None

    @property
    def admin_user_id(self) -> Optional[int]:
        return self.data.get("admin_user_id") if self.data else None

    def update(self, **kwargs) -> bool:
        if not kwargs:
            return True
        kwargs.setdefault("updated_at", datetime.now().isoformat())
        updated = db.update("states", kwargs, {"id": self.id})
        if updated:
            self._data = None
        return updated

    def get_members(self) -> List[Dict[str, Any]]:
        return StatePermissionManager.get_state_members(self.id)

    def get_member_records(self) -> List[Dict[str, Any]]:
        return db.fetchall(
            "SELECT * FROM member_records WHERE state_id = ? ORDER BY created_at DESC",
            (self.id,),
        )

    def get_transfer_records(self) -> List[Dict[str, Any]]:
        return db.fetchall(
            "SELECT * FROM transfer_records WHERE state_id = ? ORDER BY created_at DESC",
            (self.id,),
        )

    def to_dict(self) -> Dict[str, Any]:
        if not self.data:
            return {}
        return {
            "id": self.id,
            "name": self.name,
            "state_number": self.state_number,
            "admin_user_id": self.admin_user_id,
            "description": self.data.get("description"),
            "is_active": self.data.get("is_active"),
            "created_at": self.data.get("created_at"),
            "updated_at": self.data.get("updated_at"),
        }


class MemberRecord:
    """Wrapper around the member_records table."""

    def __init__(self, record_id: int):
        self.id = record_id
        self._data: Optional[Dict[str, Any]] = None

    def load(self) -> bool:
        self._data = db.fetchone("SELECT * FROM member_records WHERE id = ?", (self.id,))
        return self._data is not None

    @property
    def data(self) -> Optional[Dict[str, Any]]:
        if self._data is None:
            self.load()
        return self._data

    def update(self, **kwargs) -> bool:
        if not kwargs:
            return True
        kwargs.setdefault("updated_at", datetime.now().isoformat())
        updated = db.update("member_records", kwargs, {"id": self.id})
        if updated:
            self._data = None
        return updated

    def delete(self) -> bool:
        return db.delete("member_records", {"id": self.id})

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data or {})