# ⚠️ استكشاف الأخطاء الشائعة والحلول

## 1. خطأ: "ModuleNotFoundError: No module named 'aiohttp'"

### ✅ الحل:
```bash
pip install -r requirements-new.txt
```

أو يدويًا:
```bash
pip install aiohttp python-dotenv Jinja2
```

---

## 2. خطأ: "FileNotFoundError: database.db"

### ✅ الحل:
هذا طبيعي في التشغيل الأول. سيتم إنشاء قاعدة البيانات تلقائيًا.

تأكد من أن:
```
✓ .env موجود
✓ DB_PATH في .env موجود
✓ المجلد member_portal قابل للكتابة
```

---

## 3. خطأ: "RuntimeError: event loop"

### ✅ الحل:
احذف `database.db` والمحاولة مرة أخرى:
```bash
rm database.db 2>/dev/null
python app_new.py
```

---

## 4. خطأ: "SMTP Authentication Failed"

### ✅ الحل:
تأكد من أن:
```
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  (NOT regular password!)
```

لإنشاء App Password:
1. ادخل: https://myaccount.google.com/apppasswords
2. اختر Gmail
3. انسخ Password الناتج
4. ضعه في .env

---

## 5. خطأ: "No such table: users"

### ✅ الحل:
سيتم إنشاء الجداول تلقائيًا عند البدء الأول.

إذا استمرت المشكلة:
```bash
rm database.db
python app_new.py
```

---

## 6. خطأ: "Connection refused: 127.0.0.1:8080"

### ✅ الحل:
تأكد من:
```bash
# 1. السيرفر يعمل
python app_new.py

# 2. الانتظار 2-3 ثواني للبدء

# 3. الوصول الصحيح
http://localhost:8080

# 4. ليس http://127.0.0.1:8080 (قد لا يعمل)
```

---

## 7. خطأ: "DANGER account not created"

### ✅ الحل:
الحساب يُنشأ تلقائيًا عند إنشاء قاعدة البيانات الأولى.

تأكد من:
```bash
# 1. اقتل السيرفر (Ctrl+C)
# 2. احذف database.db
rm database.db

# 3. شغّل من جديد
python app_new.py
```

ثم سجّل دخول بـ:
```
Username: DANGER
Password: Aa@123456
```

---

## 8. خطأ: "Port 8080 already in use"

### ✅ الحل:

#### الخيار 1: استخدم port مختلف
```bash
# عدّل في app_new.py:
# ابحث عن: web.run_app(app, port=8080)
# غيّر إلى: web.run_app(app, port=8081)
```

#### الخيار 2: اقتل البرنامج السابق
```bash
# على Linux/Mac:
lsof -i :8080
kill -9 <PID>

# على Windows:
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

---

## 9. خطأ: "Permission denied: database.db"

### ✅ الحل:
```bash
# على Linux/Mac:
chmod 644 database.db
chmod 755 .

# تأكد من أن المستخدم لديه صلاحيات الكتابة
```

---

## 10. خطأ: "Invalid JSON response"

### ✅ الحل:
تأكد من:
```
✓ Python code بدون أخطاء syntax
✓ استخدام response JSON صحيح
✓ عدم خلط HTML مع JSON
```

اختبر:
```bash
curl -v http://localhost:8080/api/stats
```

---

## 11. خطأ: "OAuth redirect_uri_mismatch"

### ✅ الحل:
تأكد من أن `OAUTH_REDIRECT_URI` في .env وفي Google Console متطابقة:

```
❌ خطأ: http://localhost:8080/auth/google/callback
✅ صحيح: http://localhost:8080/auth/google/callback
```

---

## 12. خطأ: "Email not sent"

### ✅ الحل:
تحقق من:
```
✓ SMTP_USERNAME صحيح
✓ SMTP_PASSWORD صحيح (App Password)
✓ 2FA enabled على Gmail
✓ البريد المرسل إليه صحيح
✓ الاتصال بالإنترنت موجود
```

---

## 13. خطأ: "User not found" مع DANGER

### ✅ الحل:
```bash
# 1. زيارة
http://localhost:8080/

# 2. اختر "Create DANGER Account" (إن ظهر)

# أو:

# 3. ابحث عن /api/admin/create-admin في CODE
# 4. استدعيه قبل التسجيل
```

---

## 14. خطأ: "Static files not found (CSS/JS)"

### ✅ الحل:
تأكد من أن:
```
✓ الملفات في: member_portal/static/
✓ App محدث بـ static_folder
✓ المسارات صحيحة
```

في app_new.py:
```python
app['static_files'] = web.StaticRoute('/static', 'static')
```

---

## 15. خطأ: "Invalid password"

### ✅ الحل:
كلمة المرور يجب أن:
```
✓ 8+ أحرف
✓ حرف كبير واحد على الأقل
✓ حرف صغير واحد على الأقل
✓ رقم واحد على الأقل
✓ علامة خاصة واحدة (!@#$%^&*)
```

مثال صحيح:
```
✅ Aa@123456
✅ MySecurePass1!
✅ Test@Secure123
```

---

## ✅ اختبارات سريعة:

### تأكد من التثبيت:
```bash
python app_new.py
# انتظر "======== Running on http://0.0.0.0:8080 ========"
```

### اختبر API:
```bash
curl http://localhost:8080/api/stats
# يجب أن ترى JSON مع إحصائيات
```

### اختبر قاعدة البيانات:
```bash
# يجب أن يكون ملف database.db موجود
ls -la database.db
```

### اختبر البريد الإلكتروني:
```bash
# في dashbboard الإدارية، اطلب تحقق من بريد
# يجب أن يصل إليك بريد
```

---

## 📞 للمساعدة الإضافية:

1. **اقرأ الملف:** `DEPLOYMENT.md` (للمشاكل على الخادم)
2. **اقرأ الملف:** `API_DOCUMENTATION.md` (لمشاكل API)
3. **اقرأ الملف:** `DATABASE_SCHEMA.md` (لمشاكل قاعدة البيانات)
4. **تحقق من:** `app_new.py` (للمشاكل العامة)

---

## 🎯 ملخص سريع:

| المشكلة | الحل السريع |
|--------|----------|
| No module | `pip install -r requirements-new.txt` |
| No database | حذف `database.db` وشغّل من جديد |
| SMTP failed | استخدم Gmail App Password |
| Port in use | اقتل البرنامج أو غيّر Port |
| DANGER notfound | احذف db وشغّل من جديد |
| Static files | تحقق من مسار `static/` |
| Permission denied | استخدم `chmod` |

---

## ✨ كل شيء جاهز الآن!

إذا كانت لديك مشكلة أخرى:
1. ابحث هنا أولاً
2. ثم اقرأ الوثائق ذات الصلة
3. ثم اسأل عن مساعدة تقنية

استمتع بتطبيقك! 🚀
