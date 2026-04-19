"""
Permissions & Roles Management System
======================================
نظام متكامل للصلاحيات والأدوار
"""

import logging
from typing import List, Dict, Set, Optional
from core.config import Config
from core.database import db

logger = logging.getLogger(__name__)


class PermissionManager:
    """إدارة الصلاحيات"""
    
    # الصلاحيات الافتراضية لكل دور
    DEFAULT_ROLE_PERMISSIONS = {
        "super_owner": [
            # إدارة المستخدمين - كل الصلاحيات
            "user.create", "user.read", "user.update", "user.delete",
            # إدارة الولايات - كل الصلاحيات
            "state.create", "state.read", "state.update", "state.delete",
            "state.members",
            # إدارة الأعضاء - كل الصلاحيات
            "member.create", "member.read", "member.update", "member.delete",
            "member.export",
            # الإعدادات - كل الصلاحيات
            "settings.manage", "settings.smtp", "logs.view"
        ],
        
        "admin": [
            # إدارة المستخدمين - محدود
            "user.read", "user.update",
            # إدارة الولايات - كل الصلاحيات
            "state.create", "state.read", "state.update", "state.delete",
            "state.members",
            # إدارة الأعضاء - كل الصلاحيات
            "member.create", "member.read", "member.update", "member.delete",
            "member.export",
            # الإعدادات
            "settings.manage", "logs.view"
        ],
        
        "state_admin": [
            # إدارة الولاية الخاصة
            "state.read", "state.update",
            # إدارة أعضاء الولاية
            "state.members",
            # إدارة الأعضاء في الولاية
            "member.create", "member.read", "member.update", "member.delete",
            "member.export",
        ],
        
        "member": [
            # قراءة البيانات فقط
            "member.read",
        ],
        
        "guest": []  # لا صلاحيات
    }
    
    @staticmethod
    def init_default_permissions() -> bool:
        """تهيئة الصلاحيات الافتراضية"""
        try:
            for role, permissions in PermissionManager.DEFAULT_ROLE_PERMISSIONS.items():
                for permission in permissions:
                    existing = db.fetchone(
                        "SELECT id FROM permissions WHERE role = ? AND permission_key = ?",
                        (role, permission),
                    )
                    if existing:
                        continue

                    db.insert(
                        "permissions",
                        {
                            "role": role,
                            "permission_key": permission,
                            "is_granted": 1,
                        },
                    )
            logger.info("Default permissions initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing permissions: {e}")
            return False
    
    @staticmethod
    def has_permission(user_id: int, permission: str) -> bool:
        """
        التحقق من امتلاك المستخدم لصلاحية معينة
        
        Parameters:
            user_id: معرف المستخدم
            permission: مفتاح الصلاحية
            
        Returns:
            bool: True إذا كان المستخدم يمتلك الصلاحية
        """
        # احصل على دور المستخدم
        user = db.fetchone("SELECT role FROM users WHERE id = ?", (user_id,))
        if not user:
            return False
        
        role = user["role"]
        
        # تحقق من الصلاحيات المخصصة للمستخدم
        custom_perm = db.fetchone(
            "SELECT is_granted FROM user_permissions WHERE user_id = ? AND permission_key = ?",
            (user_id, permission)
        )
        
        if custom_perm:
            return custom_perm["is_granted"] == 1
        
        # تحقق من صلاحيات الدور
        role_perm = db.fetchone(
            "SELECT is_granted FROM permissions WHERE role = ? AND permission_key = ?",
            (role, permission)
        )
        
        return role_perm and role_perm["is_granted"] == 1
    
    @staticmethod
    def get_user_permissions(user_id: int) -> Set[str]:
        """الحصول على جميع صلاحيات المستخدم"""
        user = db.fetchone("SELECT role FROM users WHERE id = ?", (user_id,))
        if not user:
            return set()
        
        permissions = set()
        
        # الصلاحيات من الدور
        role_perms = db.fetchall(
            "SELECT permission_key FROM permissions WHERE role = ? AND is_granted = 1",
            (user["role"],)
        )
        permissions.update([p["permission_key"] for p in role_perms])
        
        # الصلاحيات المخصصة للمستخدم
        user_perms = db.fetchall(
            "SELECT permission_key FROM user_permissions WHERE user_id = ? AND is_granted = 1",
            (user_id,)
        )
        permissions.update([p["permission_key"] for p in user_perms])
        
        return permissions
    
    @staticmethod
    def grant_permission(user_id: int, permission: str) -> bool:
        """منح صلاحية مخصصة للمستخدم"""
        try:
            existing = db.fetchone(
                "SELECT id FROM user_permissions WHERE user_id = ? AND permission_key = ?",
                (user_id, permission),
            )
            if existing:
                db.update(
                    "user_permissions",
                    {"is_granted": 1},
                    {"id": existing["id"]},
                )
            else:
                db.insert(
                    "user_permissions",
                    {
                        "user_id": user_id,
                        "permission_key": permission,
                        "is_granted": 1
                    }
                )
            logger.info(f"Permission {permission} granted to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error granting permission: {e}")
            return False
    
    @staticmethod
    def revoke_permission(user_id: int, permission: str) -> bool:
        """إلغاء صلاحية مخصصة عن المستخدم"""
        try:
            existing = db.fetchone(
                "SELECT id FROM user_permissions WHERE user_id = ? AND permission_key = ?",
                (user_id, permission),
            )
            if existing:
                db.update(
                    "user_permissions",
                    {"is_granted": 0},
                    {"id": existing["id"]},
                )
            else:
                db.insert(
                    "user_permissions",
                    {
                        "user_id": user_id,
                        "permission_key": permission,
                        "is_granted": 0,
                    },
                )
            logger.info(f"Permission {permission} revoked from user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error revoking permission: {e}")
            return False


class RoleManager:
    """إدارة الأدوار"""
    
    @staticmethod
    def change_user_role(user_id: int, new_role: str) -> bool:
        """
        تغيير دور المستخدم
        
        Parameters:
            user_id: معرف المستخدم
            new_role: الدور الجديد
            
        Returns:
            bool: True إذا نجح التغيير
        """
        # التحقق من أن الدور موجود
        if new_role not in Config.ROLES:
            logger.error(f"Invalid role: {new_role}")
            return False
        
        # لا يمكن تغيير دور المالك الرئيسي
        current_user = db.fetchone("SELECT role FROM users WHERE id = ?", (user_id,))
        if current_user and current_user["role"] == "super_owner":
            logger.error("Cannot change super_owner role")
            return False
        
        return db.update("users", {"role": new_role}, {"id": user_id})
    
    @staticmethod
    def get_all_roles() -> Dict[str, Dict]:
        """الحصول على جميع الأدوار المتاحة"""
        return Config.ROLES
    
    @staticmethod
    def get_role_permissions(role: str) -> List[str]:
        """الحصول على صلاحيات دور معين"""
        perms = db.fetchall(
            "SELECT permission_key FROM permissions WHERE role = ? AND is_granted = 1",
            (role,)
        )
        return [p["permission_key"] for p in perms]


class StatePermissionManager:
    """إدارة صلاحيات الولاية"""
    
    @staticmethod
    def is_state_admin(user_id: int, state_id: int) -> bool:
        """التحقق من أن المستخدم مسؤول الولاية"""
        user = db.fetchone(
            "SELECT role FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not user:
            return False
        
        # المالك الرئيسي له صلاحيات مسؤول الولاية في كل مكان
        if user["role"] == "super_owner":
            return True
        
        # تحقق من عضوية الولاية والدور
        member = db.fetchone(
            "SELECT role FROM state_members WHERE user_id = ? AND state_id = ? AND role = 'admin'",
            (user_id, state_id)
        )
        
        return member is not None
    
    @staticmethod
    def is_state_member(user_id: int, state_id: int) -> bool:
        """التحقق من أن المستخدم عضو في الولاية"""
        member = db.fetchone(
            "SELECT id FROM state_members WHERE user_id = ? AND state_id = ?",
            (user_id, state_id)
        )
        return member is not None
    
    @staticmethod
    def add_state_member(user_id: int, state_id: int, role: str = "member") -> bool:
        """إضافة عضو إلى الولاية"""
        try:
            db.insert(
                "state_members",
                {
                    "user_id": user_id,
                    "state_id": state_id,
                    "role": role
                }
            )
            logger.info(f"User {user_id} added to state {state_id} as {role}")
            return True
        except Exception as e:
            logger.error(f"Error adding state member: {e}")
            return False
    
    @staticmethod
    def remove_state_member(user_id: int, state_id: int) -> bool:
        """إزالة عضو من الولاية"""
        try:
            return db.delete("state_members", {"user_id": user_id, "state_id": state_id})
        except Exception as e:
            logger.error(f"Error removing state member: {e}")
            return False
    
    @staticmethod
    def change_state_member_role(user_id: int, state_id: int, new_role: str) -> bool:
        """تغيير دور عضو الولاية"""
        try:
            return db.update(
                "state_members",
                {"role": new_role},
                {"user_id": user_id, "state_id": state_id}
            )
        except Exception as e:
            logger.error(f"Error changing state member role: {e}")
            return False
    
    @staticmethod
    def get_state_members(state_id: int) -> List[Dict]:
        """الحصول على أعضاء الولاية"""
        return db.fetchall(
            """
            SELECT u.id, u.username, u.email, sm.role, sm.joined_at
            FROM state_members sm
            JOIN users u ON sm.user_id = u.id
            WHERE sm.state_id = ?
            ORDER BY sm.role DESC, u.username
            """,
            (state_id,)
        )
