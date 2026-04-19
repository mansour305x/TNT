"""
Email Service Module
====================
خدمة إرسال البريد الإلكتروني عبر Gmail SMTP
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from core.config import Config

logger = logging.getLogger(__name__)


class EmailService:
    """خدمة إرسال البريد الإلكتروني"""
    
    @staticmethod
    def send_email(
        recipient: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        إرسال بريد إلكتروني
        
        Parameters:
            recipient: بريد المستقبل
            subject: موضوع البريد
            html_content: محتوى البريد بـ HTML
            text_content: محتوى البريد بـ Text (اختياري)
            
        Returns:
            bool: True إذا نجح الإرسال
        """
        if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
            logger.error("SMTP credentials not configured")
            return False
        
        try:
            # إنشاء الرسالة
            message = MIMEMultipart("alternative")
            message["From"] = f"{Config.FROM_NAME} <{Config.FROM_EMAIL}>"
            message["To"] = recipient
            message["Subject"] = subject
            
            # إضافة المحتوى
            if text_content:
                message.attach(MIMEText(text_content, "plain", "utf-8"))
            message.attach(MIMEText(html_content, "html", "utf-8"))
            
            # إرسال البريد
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                server.send_message(message)
            
            logger.info(f"Email sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def send_verification_email(email: str, verification_link: str, code: str = None) -> bool:
        """
        إرسال بريد التحقق من البريد الإلكتروني
        
        Parameters:
            email: البريد الإلكتروني
            verification_link: رابط التحقق
            code: كود التحقق (اختياري)
            
        Returns:
            bool: True إذا نجح الإرسال
        """
        subject = "تحقق من بريدك الإلكتروني | Verify Your Email"
        
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                .footer {{ background-color: #ecf0f1; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>مرحباً بك في تحالف TNT</h1>
                </div>
                <div class="content">
                    <p>شكراً لتسجيلك معنا!</p>
                    <p>يرجى التحقق من بريدك الإلكتروني بالنقر على الزر أدناه:</p>
                    <br>
                    <a href="{verification_link}" class="button">تحقق من بريدي</a>
                    <br><br>
                    {f"<p>أو أدخل هذا الكود: <strong>{code}</strong></p>" if code else ""}
                    <p>إذا لم تقم بهذا الطلب، يمكنك تجاهل هذا البريد.</p>
                </div>
                <div class="footer">
                    <p>© 2024 تحالف TNT. جميع الحقوق محفوظة.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        مرحباً بك في تحالف TNT
        
        شكراً لتسجيلك معنا!
        يرجى النقر على الرابط أدناه للتحقق من بريدك الإلكتروني:
        {verification_link}
        
        {f"أو أدخل هذا الكود: {code}" if code else ""}
        
        إذا لم تقم بهذا الطلب، يمكنك تجاهل هذا البريد.
        
        © 2024 تحالف TNT. جميع الحقوق محفوظة.
        """
        
        return EmailService.send_email(email, subject, html_content, text_content)
    
    @staticmethod
    def send_password_reset_email(email: str, reset_link: str) -> bool:
        """
        إرسال بريد إعادة تعيين كلمة المرور
        
        Parameters:
            email: البريد الإلكتروني
            reset_link: رابط إعادة التعيين
            
        Returns:
            bool: True إذا نجح الإرسال
        """
        subject = "إعادة تعيين كلمة المرور | Password Reset"
        
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .button {{ background-color: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                .warning {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>إعادة تعيين كلمة المرور</h1>
                </div>
                <div class="content">
                    <p>تم طلب إعادة تعيين كلمة المرور لحسابك.</p>
                    <p>انقر على الزر أدناه لإعادة تعيين كلمة المرور:</p>
                    <br>
                    <a href="{reset_link}" class="button">إعادة تعيين كلمة المرور</a>
                    <br><br>
                    <div class="warning">
                        ⚠️ لا تشارك هذا الرابط مع أحد. هذا الرابط ينتهي صلاحيته خلال 30 دقيقة.
                    </div>
                    <p>إذا لم تطلب هذا، فيمكنك تجاهل هذا البريد.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        إعادة تعيين كلمة المرور
        
        تم طلب إعادة تعيين كلمة المرور لحسابك.
        انقر على الرابط أدناه:
        {reset_link}
        
        ⚠️ لا تشارك هذا الرابط مع أحد. هذا الرابط ينتهي صلاحيته خلال 30 دقيقة.
        
        إذا لم تطلب هذا، فيمكنك تجاهل هذا البريد.
        """
        
        return EmailService.send_email(email, subject, html_content, text_content)
    
    @staticmethod
    def send_welcome_email(email: str, username: str) -> bool:
        """
        إرسال بريد الترحيب
        
        Parameters:
            email: البريد الإلكتروني
            username: اسم المستخدم
            
        Returns:
            bool: True إذا نجح الإرسال
        """
        subject = "مرحباً بك في تحالف TNT | Welcome to TNT Alliance"
        
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #27ae60; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>مرحباً بك! 👋</h1>
                </div>
                <div class="content">
                    <p>مرحباً {username}!</p>
                    <p>تم إنشاء حسابك بنجاح في تحالف TNT.</p>
                    <p>يمكنك الآن تسجيل الدخول واستكشاف جميع الميزات المتاحة.</p>
                    <br>
                    <p>إذا كانت لديك أي أسئلة، لا تتردد في التواصل معنا.</p>
                    <br>
                    <p>شكراً لك!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        مرحباً بك في تحالف TNT!
        
        مرحباً {username}!
        
        تم إنشاء حسابك بنجاح في تحالف TNT.
        يمكنك الآن تسجيل الدخول واستكشاف جميع الميزات المتاحة.
        
        شكراً لك!
        """
        
        return EmailService.send_email(email, subject, html_content, text_content)
    
    @staticmethod
    def send_admin_notification(admin_email: str, subject: str, message: str) -> bool:
        """
        إرسال إشعار للمسؤول
        
        Parameters:
            admin_email: بريد المسؤول
            subject: موضوع البريد
            message: محتوى الرسالة
            
        Returns:
            bool: True إذا نجح الإرسال
        """
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; direction: rtl; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2980b9; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #ecf0f1; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>إشعار إداري</h1>
                </div>
                <div class="content">
                    {message}
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(admin_email, subject, html_content, message)
