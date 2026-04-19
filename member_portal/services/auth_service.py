"""
Authentication Service Module
==============================
خدمة التحقق والمصادقة والدخول والتسجيل
"""

import logging
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta

from core.database import db
from core.config import Config
from utils.security import SecurityManager, PasswordValidator
from services.email_service import EmailService

logger = logging.getLogger(__name__)


class AuthService:
    """خدمة المصادقة والتحقق"""
    
    @staticmethod
    def register_user(
        username: str,
        email: str,
        password: str,
        full_name: str = ""
    ) -> Tuple[bool, str, Optional[int]]:
        """
        تسجيل مستخدم جديد
        
        Parameters:
            username: اسم المستخدم
            email: البريد الإلكتروني
            password: كلمة المرور
            full_name: الاسم الكامل (اختياري)
            
        Returns:
            tuple: (نجح/فشل، الرسالة، معرف المستخدم)
        """
        # التحقق من صحة المدخلات
        if len(username) < 3:
            return False, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل", None
        
        if not email or "@" not in email:
            return False, "البريد الإلكتروني غير صحيح", None
        
        # التحقق من قوة كلمة المرور
        is_valid, msg = PasswordValidator.validate(password)
        if not is_valid:
            return False, msg, None
        
        # التحقق من عدم وجود اسم مستخدم مماثل
        existing_user = db.fetchone(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        )
        
        if existing_user:
            return False, "اسم المستخدم أو البريد الإلكتروني مستخدم مسبقاً", None
        
        try:
            # تشفير كلمة المرور
            password_hash = SecurityManager.hash_password(password)
            
            # إدراج المستخدم الجديد
            user_id = db.insert(
                "users",
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "full_name": full_name,
                    "role": "member",  # الدور الافتراضي
                    "is_email_verified": 0
                }
            )
            
            if not user_id:
                return False, "حدث خطأ في إنشاء الحساب", None
            
            # إرسال بريد الترحيب
            EmailService.send_welcome_email(email, username)
            
            logger.info(f"User {username} registered successfully")
            return True, "تم إنشاء الحساب بنجاح", user_id
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False, "حدث خطأ أثناء التسجيل", None
    
    @staticmethod
    def login(username_or_email: str, password: str, ip_address: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        تسجيل دخول المستخدم
        
        Parameters:
            username_or_email: اسم المستخدم أو البريد الإلكتروني
            password: كلمة المرور
            ip_address: عنوان IP
            
        Returns:
            tuple: (نجح/فشل، الرسالة، معرف المستخدم)
        """
        try:
            # البحث عن المستخدم
            user = db.fetchone(
                "SELECT id, password_hash, is_active FROM users WHERE username = ? OR email = ?",
                (username_or_email, username_or_email)
            )
            
            if not user:
                # تسجيل محاولة فاشلة
                db.insert(
                    "login_attempts",
                    {
                        "username": username_or_email,
                        "ip_address": ip_address,
                        "success": 0
                    }
                )
                return False, "بيانات الدخول غير صحيحة", None
            
            # التحقق من أن المستخدم نشط
            if not user["is_active"]:
                return False, "الحساب معطل", None
            
            # التحقق من كلمة المرور
            if not SecurityManager.verify_password(password, user["password_hash"]):
                db.insert(
                    "login_attempts",
                    {
                        "username": username_or_email,
                        "ip_address": ip_address,
                        "success": 0
                    }
                )
                return False, "بيانات الدخول غير صحيحة", None
            
            # تحديث آخر تسجيل دخول
            db.update(
                "users",
                {"last_login": datetime.now().isoformat()},
                {"id": user["id"]}
            )
            
            # تسجيل محاولة ناجحة
            db.insert(
                "login_attempts",
                {
                    "username": username_or_email,
                    "ip_address": ip_address,
                    "success": 1
                }
            )
            
            logger.info(f"User {user['id']} logged in successfully")
            return True, "تم تسجيل الدخول بنجاح", user["id"]
            
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False, "حدث خطأ أثناء تسجيل الدخول", None
    
    @staticmethod
    def request_password_reset(email: str) -> Tuple[bool, str]:
        """
        طلب إعادة تعيين كلمة المرور
        
        Parameters:
            email: البريد الإلكتروني
            
        Returns:
            tuple: (نجح/فشل، الرسالة)
        """
        try:
            user = db.fetchone("SELECT id, username FROM users WHERE email = ?", (email,))
            
            if not user:
                # لا نكشف ما إذا كان البريد موجوداً أم لا
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True, "إذا كان البريد موجوداً، ستتلقى رسالة إعادة تعيين"
            
            # إنشاء رمز إعادة التعيين
            token = SecurityManager.generate_token()
            expires_at = (datetime.now() + timedelta(seconds=Config.RESET_TOKEN_TTL_SECONDS)).isoformat()
            
            # حفظ الرمز
            db.insert(
                "password_reset_tokens",
                {
                    "user_id": user["id"],
                    "token": token,
                    "expires_at": expires_at,
                    "is_used": 0
                }
            )
            
            # إرسال البريد
            reset_link = f"https://tnt-alliance.com/reset-password?token={token}"
            EmailService.send_password_reset_email(email, reset_link)
            
            logger.info(f"Password reset email sent to {email}")
            return True, "تم إرسال بريد إعادة التعيين"
            
        except Exception as e:
            logger.error(f"Error requesting password reset: {e}")
            return False, "حدث خطأ أثناء طلب إعادة التعيين"
    
    @staticmethod
    def reset_password(token: str, new_password: str) -> Tuple[bool, str]:
        """
        إعادة تعيين كلمة المرور
        
        Parameters:
            token: رمز إعادة التعيين
            new_password: كلمة المرور الجديدة
            
        Returns:
            tuple: (نجح/فشل، الرسالة)
        """
        try:
            # البحث عن الرمز
            reset_token = db.fetchone(
                "SELECT id, user_id, is_used, expires_at FROM password_reset_tokens WHERE token = ?",
                (token,)
            )
            
            if not reset_token:
                return False, "رمز إعادة التعيين غير صحيح"
            
            if reset_token["is_used"]:
                return False, "هذا الرمز تم استخدامه مسبقاً"

            if reset_token.get("expires_at") and reset_token["expires_at"] <= datetime.now().isoformat():
                return False, "رمز إعادة التعيين منتهي الصلاحية"
            
            # التحقق من صحة كلمة المرور
            is_valid, msg = PasswordValidator.validate(new_password)
            if not is_valid:
                return False, msg
            
            # تشفير كلمة المرور الجديدة
            password_hash = SecurityManager.hash_password(new_password)
            
            # تحديث كلمة المرور
            db.update(
                "users",
                {"password_hash": password_hash},
                {"id": reset_token["user_id"]}
            )
            
            # تعليم الرمز كمستخدم
            db.update(
                "password_reset_tokens",
                {"is_used": 1},
                {"id": reset_token["id"]}
            )
            
            logger.info(f"Password reset successfully for user {reset_token['user_id']}")
            return True, "تم إعادة تعيين كلمة المرور بنجاح"
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False, "حدث خطأ أثناء إعادة التعيين"
    
    @staticmethod
    def verify_email(user_id: int, code: str) -> Tuple[bool, str]:
        """
        التحقق من البريد الإلكتروني
        
        Parameters:
            user_id: معرف المستخدم
            code: كود التحقق
            
        Returns:
            tuple: (نجح/فشل، الرسالة)
        """
        try:
            # البحث عن الكود
            verification = db.fetchone(
                "SELECT id, email, is_used, expires_at FROM email_verification_codes WHERE user_id = ? AND code = ?",
                (user_id, code)
            )
            
            if not verification:
                return False, "كود التحقق غير صحيح"
            
            if verification["is_used"]:
                return False, "هذا الكود تم استخدامه مسبقاً"

            if verification.get("expires_at") and verification["expires_at"] <= datetime.now().isoformat():
                return False, "كود التحقق منتهي الصلاحية"
            
            # تحديث حالة المستخدم
            db.update(
                "users",
                {
                    "email": verification["email"],
                    "is_email_verified": 1,
                    "email_verified_at": datetime.now().isoformat()
                },
                {"id": user_id}
            )
            
            # تعليم الكود كمستخدم
            db.update(
                "email_verification_codes",
                {"is_used": 1},
                {"id": verification["id"]}
            )
            
            logger.info(f"Email verified for user {user_id}")
            return True, "تم التحقق من البريد الإلكتروني بنجاح"
            
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return False, "حدث خطأ أثناء التحقق"
    
    @staticmethod
    def send_verification_email(user_id: int, email: str) -> Tuple[bool, str]:
        """
        إرسال بريد التحقق
        
        Parameters:
            user_id: معرف المستخدم
            email: البريد الإلكتروني
            
        Returns:
            tuple: (نجح/فشل، الرسالة)
        """
        try:
            # إنشاء كود التحقق
            code = SecurityManager.generate_code()
            expires_at = (datetime.now() + timedelta(seconds=Config.EMAIL_VERIFY_TOKEN_TTL_SECONDS)).isoformat()
            
            # حفظ الكود
            db.insert(
                "email_verification_codes",
                {
                    "user_id": user_id,
                    "email": email,
                    "code": code,
                    "expires_at": expires_at,
                    "is_used": 0
                }
            )
            
            # إرسال البريد
            verification_link = f"https://tnt-alliance.com/verify-email?code={code}"
            EmailService.send_verification_email(email, verification_link, code)
            
            logger.info(f"Verification email sent to {email}")
            return True, "تم إرسال بريد التحقق"
            
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False, "حدث خطأ أثناء إرسال البريد"
