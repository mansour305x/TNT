"""
# TNT Alliance Portal - نظام محسّن جديد 2.0
## Migration & Setup Guide

---

## 📋 نظرة عامة على الميزات الجديدة

### ✅ الميزات المضافة:

1. **OAuth2 Authentication**
   - تسجيل دخول مع Google
   - إمكانية إضافة Discord لاحقاً
   - الحفاظ على التسجيل التقليدي

2. **نظام الصلاحيات المتكامل**
   - Roles: Super Owner, Admin, State Admin, Member, Guest
   - Permissions: نظام صلاحيات مرن وقابل للتخصيص
   - صلاحيات مخصصة لكل مستخدم

3. **إدارة الحسابات الشخصية**
   - تغيير الاسم والبريد والكلمة السرية
   - التحقق من البريد الإلكتروني عبر كود
   - إدارة الجلسات

4. **نظام الولايات المحسّن**
   - إنشاء وإدارة الولايات
   - إدارة أعضاء الولاية
   - صلاحيات منفصلة لمسؤولي الولايات

5. **لوحة التحكم الإدارية**
   - حساب مالك رئيسي: DANGER / Aa@123456
   - إدارة جميع المستخدمين والولايات
   - عرض الإحصائيات

6. **أمان محسّن**
   - تشفير كلمات المرور بـ PBKDF2
   - Secure Session Management
   - Email Verification
   - SQL Injection Protection

---

## 🚀 التثبيت والتشغيل

### الخطوة 1: تجهيز البيئة

\`\`\`bash
# استنساخ المستودع
cd /workspaces/TNT/member_portal

# تثبيت المكتبات
pip install -r requirements-new.txt

# نسخ ملف الإعدادات
cp .env.example .env
\`\`\`

### الخطوة 2: تكوين الإعدادات (.env)

\`\`\`bash
# Google OAuth2
# 1. اذهب إلى https://console.cloud.google.com/
# 2. أنشئ مشروع جديد
# 3. فعّل Google+ API
# 4. أنشئ OAuth2 credentials (Desktop application)
# 5. احصل على Client ID و Secret

GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback

# Gmail SMTP (للبريد الإلكتروني)
# 1. فعّل 2-Step Verification في حسابك
# 2. أنشئ App Password
# 3. استخدم App Password هنا

SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
\`\`\`

### الخطوة 3: تشغيل التطبيق

\`\`\`bash
# اختر واحداً من الخيارات:

# الخيار 1: تشغيل مباشر
python app_new.py

# الخيار 2: تشغيل مع Gunicorn (للإنتاج)
gunicorn --workers 4 --worker-class aiohttp.web.GunicornWebWorker app_new:app

# الخيار 3: تشغيل مع Docker
docker build -f docker/Dockerfile -t tnt-portal .
docker run -p 8080:8080 -v $(pwd):/app tnt-portal
\`\`\`

---

## 🔄 الترقية من النسخة القديمة

### البيانات التاريخية:
إذا كان لديك بيانات قديمة:

\`\`\`Python
# تشغيل سكريبت الترقية
python scripts/migrate_data.py

# هذا سيقوم بـ:
# 1. نسخ المستخدمين القدماء
# 2. تحويل الحسابات إلى النظام الجديد
# 3. الحفاظ على البيانات التاريخية
\`\`\`

---

## 📝 استخدام الـ API

### 1. التسجيل والدخول

\`\`\`bash
# التسجيل
curl -X POST http://localhost:8080/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"username":"user1","email":"user@example.com","password":"SecurePass123!","full_name":"Ahmed Ali"}'

# الدخول
curl -X POST http://localhost:8080/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"user1","password":"SecurePass123!"}'

# الخروج
curl -X POST http://localhost:8080/api/auth/logout \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"
\`\`\`

### 2. إدارة الحساب الشخصي

\`\`\`bash
# الحصول على ملف المستخدم
curl -X GET http://localhost:8080/api/user/profile \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"

# تحديث الملف
curl -X PUT http://localhost:8080/api/user/profile \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"full_name":"Ahmed Ali Smith"}'

# تغيير كلمة المرور
curl -X POST http://localhost:8080/api/user/password \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"current_password":"SecurePass123!","new_password":"NewPassword456!"}'

# طلب تحقق البريد
curl -X POST http://localhost:8080/api/user/email/request-verification \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"

# التحقق من البريد
curl -X POST http://localhost:8080/api/user/email/verify \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"code":"123456"}'
\`\`\`

### 3. إدارة الولايات

\`\`\`bash
# الحصول على الولايات
curl -X GET http://localhost:8080/api/states

# إنشاء ولاية جديدة
curl -X POST http://localhost:8080/api/states \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"state_name":"State 1","state_number":"1","password":"StatePass123!"}'

# الحصول على ولاية
curl -X GET http://localhost:8080/api/states/1 \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"

# تحديث الولاية
curl -X PUT http://localhost:8080/api/states/1 \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"description":"وصف الولاية"}'

# حذف الولاية
curl -X DELETE http://localhost:8080/api/states/1 \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"
\`\`\`

### 4. لوحة التحكم الإدارية

\`\`\`bash
# الدخول كـ DANGER
curl -X POST http://localhost:8080/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"DANGER","password":"Aa@123456"}'

# الحصول على لوحة التحكم
curl -X GET http://localhost:8080/api/admin/dashboard \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"

# الحصول على قائمة المستخدمين
curl -X GET http://localhost:8080/api/admin/users \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN"

# تغيير دور المستخدم
curl -X POST http://localhost:8080/api/admin/users/2/role \\
  -H "Content-Type: application/json" \\
  -H "Cookie: member_portal_session=YOUR_SESSION_TOKEN" \\
  -d '{"role":"state_admin"}'
\`\`\`

---

## 🔐 الصلاحيات والأدوار

### الأدوار المتاحة:

| الدور | المستوى | الصلاحيات |
|------|--------|---------|
| **super_owner** | 100 | جميع الصلاحيات |
| **admin** | 50 | إدارة الولايات والمستخدمين والأعضاء |
| **state_admin** | 40 | إدارة الولاية والأعضاء |
| **member** | 10 | قراءة البيانات فقط |
| **guest** | 1 | لا صلاحيات |

### قائمة الصلاحيات:

```
# إدارة المستخدمين
- user.create (إنشاء مستخدم جديد)
- user.read (عرض البيانات)
- user.update (تعديل البيانات)
- user.delete (حذف المستخدمين)

# إدارة الولايات
- state.create (إنشاء دولة)
- state.read (عرض البيانات)
- state.update (تعديل البيانات)
- state.delete (حذف الدول)
- state.members (إدارة الأعضاء)

# إدارة الأعضاء
- member.create
- member.read
- member.update
- member.delete
- member.export

# الإعدادات
- settings.manage
- settings.smtp
- logs.view
```

---

## 📂 هيكلة المشروع الجديدة

```
member_portal/
├── core/
│   ├── __init__.py
│   ├── config.py              # الإعدادات الرئيسية
│   ├── database.py            # إدارة قاعدة البيانات
│   └── permissions.py         # نظام الصلاحيات
├── services/
│   ├── __init__.py
│   ├── auth_service.py        # خدمة المصادقة
│   ├── email_service.py       # خدمة البريد
│   └── oauth_service.py       # خدمة OAuth2
├── models/
│   ├── __init__.py
│   └── user_model.py          # نماذج البيانات
├── utils/
│   ├── __init__.py
│   └── security.py            # الأمان والتشفير
├── routes/                    # (سيتم الإضافة)
│   ├── __init__.py
│   ├── auth.py
│   ├── user.py
│   └── admin.py
├── templates/                 # (ملفات HTML)
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── ...
├── static/                    # (ملفات CSS, JS, الصور)
│   ├── styles.css
│   ├── bootstrap.min.css
│   └── ...
├── app_new.py                 # التطبيق الرئيسي الجديد
├── middleware.py              # Middleware
├── requirements-new.txt       # المكتبات
├── .env.example              # ملف الإعدادات
└── README.md
```

---

## 🧪 الاختبار

### تشغيل الاختبارات:

```bash
pytest tests/ -v

# اختبار محدد
pytest tests/test_auth.py -v

# اختبار مع coverage
pytest tests/ --cov=. --cov-report=html
```

---

## ⚠️ ملاحظات مهمة

### الأمان:
- ✅ تغيير `PORTAL_SECRET_KEY` في الإنتاج
- ✅ استخدام HTTPS في الإنتاج
- ✅ عدم حفظ كلمات المرور في الكود
- ✅ تحديث المكتبات بانتظام

### الأداء:
- ✅ استخدام الفهارس (Indexes) في البيانات الضخمة
- ✅ استخدام async/await لتحسين الأداء
- ✅ تخزين الجلسات بكفاءة

### النسخ الاحتياطية:
```bash
# النسخ الاحتياطية من قاعدة البيانات
sqlite3 portal.db \".backup portal-backup.db\"

# استعادة النسخة الاحتياطية
sqlite3 portal.db \".restore portal-backup.db\"
```

---

## 📞 الدعم والمساعدة

للتواصل بخصوص أي مشاكل أو استفسارات:
- راجع الـ logs: `/tmp/portal.log`
- تحقق من الإعدادات: `.env`
- اختبر الاتصال بالبريد: `python -m smtplib`

---

آخر تحديث: 19 أبريل 2026
الإصدار: 2.0.0
"""
