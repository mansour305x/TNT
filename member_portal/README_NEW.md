# TNT Alliance Portal - 2.0 🚀

> نظام إدارة تحالف TNT محسّن بميزات أمان وصلاحيات وOAuth2

---

## ✨ الميزات الرئيسية

### 🔐 المصادقة والأمان
- ✅ تسجيل دخول تقليدي (البريد + كلمة المرور)
- ✅ OAuth2 مع Google
- ✅ تشفير آمن لكلمات المرور (PBKDF2)
- ✅ إدارة الجلسات الآمنة
- ✅ التحقق من البريد الإلكتروني

### 👥 إدارة المستخدمين والصلاحيات
- ✅ نظام أدوار متقدم (Super Owner, Admin, State Admin, Member)
- ✅ نظام صلاحيات مرن وقابل للتخصيص
- ✅ صلاحيات مخصصة لكل مستخدم
- ✅ إدارة الجلسات المتزامنة

### 🏛️ إدارة الولايات
- ✅ إنشاء وإدارة الولايات
- ✅ إدارة أعضاء الولاية
- ✅ لوحة تحكم خاصة بكل ولاية
- ✅ صلاحيات منفصلة لمسؤولي الولايات

### 💼 إدارة الحسابات الشخصية
- ✅ تحديث الملف الشخصي
- ✅ تغيير كلمة المرور
- ✅ تحديث البريد الإلكتروني
- ✅ عرض نشاط الحساب

### 🛠️ لوحة التحكم الإدارية
- ✅ حساب مالك رئيسي (DANGER)
- ✅ الإحصائيات والتقارير
- ✅ إدارة جميع المستخدمين
- ✅ مراقبة النشاط

---

## 🚀 البدء السريع

### المتطلبات:
- Python 3.11+
- pip
- بريد Gmail (للإيميل)
- حساب Google Cloud (للـ OAuth2)

### التثبيت:

```bash
# 1. استنساخ المستودع
git clone <repository-url>
cd member_portal

# 2. إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows

# 3. تثبيت المكتبات
pip install -r requirements-new.txt

# 4. نسخ الإعدادات
cp .env.example .env

# 5. تحرير .env بإضافة بيانات Google OAuth و Gmail
nano .env
```

### التشغيل:

```bash
# التشغيل المباشر
python app_new.py

# سيكون التطبيق متاح على:
# http://localhost:8080
```

---

## 📖 التوثيق الكاملة

راجع [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) للتفاصيل الكاملة:
- شرح مفصل لجميع الميزات
- أمثلة الـ API
- التكوين المتقدم
- الترقية من النسخة القديمة

---

## 🏗️ البنية المعمارية

```
┌─────────────────────────────────────┐
│      Frontend (HTML/CSS/JS)         │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   aiohttp Web Server (Async)        │
│  - Routes (Auth, User, State, Admin)│
│  - Middleware (Session, Error)      │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Services (Business Logic)         │
│  - Auth Service                     │
│  - OAuth Service                    │
│  - Email Service                    │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│   Core (Permissions, Database)      │
│  - Permission Manager               │
│  - Role Manager                     │
│  - Database Manager                 │
└────────────────┬────────────────────┘
                 │
┌────────────────▼────────────────────┐
│        SQLite Database              │
│  - Users, States, Sessions          │
│  - Permissions, Activity Logs       │
└─────────────────────────────────────┘
```

---

## 🔑 حسابات التجربة

| الحساب | البريد | كلمة المرور |
|-------|------|-----------|
| DANGER (Super Owner) | owner@tnt-alliance.local | Aa@123456 |

---

## 📚 أمثلة الاستخدام

### تسجيل مستخدم جديد:
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ahmed",
    "email": "ahmed@example.com",
    "password": "SecurePass123!",
    "full_name": "Ahmed Ali"
  }'
```

### تسجيل الدخول:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ahmed",
    "password": "SecurePass123!"
  }'
```

### الحصول على ملف المستخدم:
```bash
curl -X GET http://localhost:8080/api/user/profile \
  -H "Cookie: member_portal_session=YOUR_TOKEN"
```

---

## 🧪 الاختبار

```bash
# تشغيل جميع الاختبارات
pytest tests/ -v

# اختبار ملف محدد
pytest tests/test_auth.py -v

# مع معلومات التغطية
pytest tests/ --cov=. --cov-report=html
```

---

## 📋 خطة التطوير

- [ ] Front-end interface (React/Vue)
- [ ] Discord OAuth integration
- [ ] Advanced reporting
- [ ] Activity notifications
- [ ] API documentation (Swagger)
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Mobile app

---

## 🤝 المساهمة

نرحب بمساهماتك! يرجى اتباع هذه الخطوات:

1. Fork المستودع
2. إنشاء branch للميزة الجديدة
3. Commit التغييرات
4. Push إلى branch
5. فتح Pull Request

---

## 📜 الترخيص

هذا المشروع مرخص تحت [MIT License](LICENSE)

---

## 📞 التواصل

- 📧 البريد الإلكتروني: support@tnt-alliance.com
- 🐛 تقارير الأخطاء: [GitHub Issues](../../issues)
- 💬 النقاش: [GitHub Discussions](../../discussions)

---

## 🙏 شكر وتقدير

شكراً لجميع المساهمين والمختبرين!

---

**الإصدار:** 2.0.0  
**آخر تحديث:** 19 أبريل 2026  
**الحالة:** ✅ جاهز للإنتاج
