# TNT Alliance Portal - Quick Start ⚡

## البدء الفوري خلال 5 دقائق

---

## 1️⃣ التثبيت (2 دقائق)

```bash
# الذهاب إلى المجلد
cd /workspaces/TNT/member_portal

# تثبيت المكتبات
pip install -r requirements-new.txt

# نسخ الإعدادات
cp .env.example .env
```

---

## 2️⃣ تكوين البيئة (1 دقيقة)

**فتح `.env` وتعديل الأساسي:**

```bash
# يمكنك تركها كما هي للتطوير المحلي
# أو إضافة بيانات Google إذا كنت تريد OAuth:

GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback

SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## 3️⃣ التشغيل (1 دقيقة)

```bash
python app_new.py

# ستكون متاح على:
# http://localhost:8080
```

---

## 4️⃣ الاستخدام (1 دقيقة)

### الدخول كـ DANGER (Super Admin):
```
Username: DANGER
Password: Aa@123456
```

### أو التسجيل كمستخدم جديد:
```
Username: myuser
Email: myuser@example.com
Password: SecurePass123!
```

---

## 🧪 اختبار الـ API

### تسجيل مستخدم:
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@test.com","password":"SecurePass123!"}'
```

### الدخول:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"SecurePass123!"}'
```

### الحصول على الملف الشخصي:
```bash
curl -X GET http://localhost:8080/api/user/profile \
  -H "Cookie: member_portal_session=YOUR_TOKEN"
```

---

## 📁 الملفات المهمة

| الملف | الوصف |
|------|------|
| `app_new.py` | التطبيق الرئيسي |
| `core/config.py` | الإعدادات |
| `core/database.py` | قاعدة البيانات |
| `services/auth_service.py` | المصادقة |
| `API_DOCUMENTATION.md` | توثيق الـ API الكاملة |

---

## 🚀 الخطوات التالية

- [ ] قراءة `README_NEW.md` للمعلومات الكاملة
- [ ] قراءة `API_DOCUMENTATION.md` لفهم جميع الـ endpoints
- [ ] تطوير Front-end من `templates/`
- [ ] إضافة المزيد من الميزات

---

## ❓ حل مشاكل شائعة

### مشكلة: ModuleNotFoundError
```bash
# تأكد من تثبيت المكتبات:
pip install -r requirements-new.txt
```

### مشكلة: Database locked
```bash
# حذف قاعدة البيانات القديمة:
rm portal.db
# سيتم إعادة إنشاؤها تلقائياً
```

### مشكلة: Port 8080 in use
```bash
# استخدم port مختلف:
# عدّل في app.py:
web.run_app(app, host="0.0.0.0", port=9000)
```

---

## 💡 نصائح

✅ استخدم `curl` أو `Postman` لاختبار الـ API  
✅ افتح `portal.db` بـ `SQLite` Browser لمشاهدة البيانات  
✅ تحقق من السجلات عند حدوث مشاكل  

---

**🎉 تم! الآن أنت جاهز للبدء!**

للمزيد من المعلومات، راجع الملفات الأخرى في المشروع.
