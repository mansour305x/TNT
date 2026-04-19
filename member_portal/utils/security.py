"""
Security & Encryption Module
=============================
توفير دوال الأمان والتشفير وإنشاء الرموز
"""

import hashlib
import hmac
import secrets
import string
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json


class SecurityManager:
    """إدارة الأمان والتشفير"""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """
        تشفير كلمة المرور باستخدام SHA-256
        
        Parameters:
            password: كلمة المرور المراد تشفيرها
            salt: ملح اختياري (يتم إنشاء واحد جديد إذا لم يتم توفير)
            
        Returns:
            str: كلمة المرور المشفرة مع الملح
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # عدد التكرارات
        )
        
        return f"{salt}${password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        التحقق من كلمة المرور
        
        Parameters:
            password: كلمة المرور المدخلة
            password_hash: كلمة المرور المشفرة المخزنة
            
        Returns:
            bool: True إذا كانت كلمة المرور صحيحة
        """
        try:
            parts = password_hash.split('$')
            if len(parts) != 2:
                return False
            
            salt = parts[0]
            stored_hash = parts[1]
            
            new_hash = SecurityManager.hash_password(password, salt)
            return hmac.compare_digest(new_hash, password_hash)
        except Exception:
            return False
    
    @staticmethod
    def generate_token(length: int = 64) -> str:
        """
        إنشاء رمز عشوائي آمن
        
        Parameters:
            length: طول الرمز
            
        Returns:
            str: رمز عشوائي آمن
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_code(length: int = 6) -> str:
        """
        إنشاء كود رقمي (للتحقق من البريد الإلكتروني)
        
        Parameters:
            length: طول الكود
            
        Returns:
            str: كود رقمي
        """
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def create_session_token(user_id: int, secret_key: bytes) -> str:
        """
        إنشاء رمز جلسة آمن
        
        Parameters:
            user_id: معرف المستخدم
            secret_key: المفتاح السري
            
        Returns:
            str: رمز الجلسة
        """
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}"
        signature = hmac.new(
            secret_key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{signature}"
    
    @staticmethod
    def verify_session_token(token: str, secret_key: bytes, max_age_seconds: int = 604800) -> Optional[int]:
        """
        التحقق من رمز الجلسة
        
        Parameters:
            token: رمز الجلسة
            secret_key: المفتاح السري
            max_age_seconds: أقصى عمر للرمز بالثواني
            
        Returns:
            int: معرف المستخدم أو None إذا كان الرمز غير صالح
        """
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return None
            
            user_id = int(parts[0])
            timestamp = int(parts[1])
            signature = parts[2]
            
            # التحقق من انتهاء الصلاحية
            if time.time() - timestamp > max_age_seconds:
                return None
            
            # التحقق من التوقيع
            data = f"{user_id}:{timestamp}"
            expected_signature = hmac.new(
                secret_key,
                data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                return user_id
            
            return None
        except Exception:
            return None
    
    @staticmethod
    def create_verification_token(email: str, secret_key: bytes) -> str:
        """
        إنشاء رمز التحقق من البريد الإلكتروني
        
        Parameters:
            email: البريد الإلكتروني
            secret_key: المفتاح السري
            
        Returns:
            str: رمز التحقق
        """
        timestamp = str(int(time.time()))
        data = f"{email}:{timestamp}"
        signature = hmac.new(
            secret_key,
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{signature}"
    
    @staticmethod
    def verify_verification_token(token: str, email: str, secret_key: bytes, max_age_seconds: int = 86400) -> bool:
        """
        التحقق من رمز التحقق من البريد الإلكتروني
        
        Parameters:
            token: رمز التحقق
            email: البريد الإلكتروني
            secret_key: المفتاح السري
            max_age_seconds: أقصى عمر للرمز
            
        Returns:
            bool: True إذا كان الرمز صحيحاً
        """
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False
            
            stored_email = parts[0]
            timestamp = int(parts[1])
            signature = parts[2]
            
            # التحقق من البريد الإلكتروني
            if stored_email != email:
                return False
            
            # التحقق من انتهاء الصلاحية
            if time.time() - timestamp > max_age_seconds:
                return False
            
            # التحقق من التوقيع
            data = f"{email}:{timestamp}"
            expected_signature = hmac.new(
                secret_key,
                data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False


class PasswordValidator:
    """التحقق من قوة كلمة المرور"""
    
    @staticmethod
    def validate(password: str) -> tuple[bool, str]:
        """
        التحقق من قوة كلمة المرور
        
        Parameters:
            password: كلمة المرور
            
        Returns:
            tuple: (صحيح/خطأ، الرسالة)
        """
        if len(password) < 8:
            return False, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"
        
        if not any(c.isupper() for c in password):
            return False, "كلمة المرور يجب أن تحتوي على حرف كبير"
        
        if not any(c.islower() for c in password):
            return False, "كلمة المرور يجب أن تحتوي على حرف صغير"
        
        if not any(c.isdigit() for c in password):
            return False, "كلمة المرور يجب أن تحتوي على رقم"
        
        if not any(c in "!@#$%^&*" for c in password):
            return False, "كلمة المرور يجب أن تحتوي على علامة خاصة (!@#$%^&*)"
        
        return True, "كلمة المرور قوية"


class TokenManager:
    """إدارة الرموز والتحقق"""
    
    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
        self.tokens: Dict[str, Dict[str, Any]] = {}
    
    def create_oauth_state(self) -> str:
        """إنشاء رمز state لـ OAuth"""
        state = SecurityManager.generate_token()
        self.tokens[state] = {
            "created_at": datetime.now(),
            "type": "oauth_state"
        }
        return state
    
    def verify_oauth_state(self, state: str, max_age_seconds: int = 600) -> bool:
        """التحقق من رمز state لـ OAuth"""
        if state not in self.tokens:
            return False
        
        token_data = self.tokens[state]
        if (datetime.now() - token_data["created_at"]).total_seconds() > max_age_seconds:
            del self.tokens[state]
            return False
        
        if token_data["type"] != "oauth_state":
            return False
        
        del self.tokens[state]
        return True
    
    def cleanup_expired_tokens(self):
        """تنظيف الرموز المنتهية الصلاحية"""
        current_time = datetime.now()
        expired = [
            state for state, data in self.tokens.items()
            if (current_time - data["created_at"]).total_seconds() > 3600  # ساعة واحدة
        ]
        for state in expired:
            del self.tokens[state]
