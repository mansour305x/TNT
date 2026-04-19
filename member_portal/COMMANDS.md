# 🔧 دليل الأوامر الكاملة

---

## 🚀 تشغيل التطبيق:

### الطريقة 1: النص البسيط (Linux/Mac):
```bash
chmod +x run.sh
./run.sh
```

### الطريقة 2: اليدوية:
```bash
# الذهاب للمجلد
cd /workspaces/TNT/member_portal

# تثبيت المكتبات
pip install -r requirements-new.txt

# نسخ الإعدادات
cp .env.example .env

# تشغيل التطبيق
python app_new.py
```

### الطريقة 3: Docker:
```bash
docker-compose -f docker/docker-compose.yml up
```

### الطريقة 4: Python 3.11+:
```bash
# التأكد من إصدار Python
python --version  # يجب أن يكون 3.11 أو أحدث

# إذا لديك عدة إصدارات، استخدم:
python3.11 app_new.py
```

---

## 📦 إدارة المكتبات:

### تثبيت المكتبات:
```bash
pip install -r requirements-new.txt
```

### تثبيت مكتبة واحدة:
```bash
pip install aiohttp
pip install python-dotenv
pip install Jinja2
```

### تحديث المكتبات:
```bash
pip install --upgrade -r requirements-new.txt
```

### قائمة المكتبات المثبتة:
```bash
pip list
```

---

## ⚙️ إدارة البيئة:

### نسخ الإعدادات:
```bash
cp .env.example .env
```

### تحرير الإعدادات (Ubuntu/Linux):
```bash
nano .env
```

### تحرير الإعدادات (macOS):
```bash
vim .env
```

### تحرير الإعدادات (Windows - PowerShell):
```powershell
notepad .env
```

---

## 🗄️ إدارة قاعدة البيانات:

### حذف قاعدة البيانات (لإعادة تعيين):
```bash
rm database.db
```

### الوصول لقاعدة البيانات (مع sqlite3):
```bash
sqlite3 database.db
```

### عرض جميع الجداول:
```sql
.tables
```

### عرض بنية جدول:
```sql
.schema users
```

### عرض جميع المستخدمين:
```sql
SELECT * FROM users;
```

### الخروج من sqlite3:
```sql
.quit
```

---

## 🔗 الوصول للتطبيق:

### عبر المتصفح:
```
http://localhost:8080
```

### اختبار API:
```bash
curl http://localhost:8080/api/stats
```

### اختبار تسجيل الدخول (curl):
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"DANGER","password":"Aa@123456"}'
```

---

## 🧪 اختبار البريد الإلكتروني:

### تشغيل الخادم مع توقيع البريد:
```bash
# تأكد من أن .env يحتوي على:
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-app-password

python app_new.py
```

### إنشاء App Password (Gmail):
1. اذهب إلى: https://myaccount.google.com/apppasswords
2. اختر Gmail
3. انسخ Password الناتج
4. ضعه في .env

---

## 🐛 استكشاف الأخطاء:

### اختبار الاتصال:
```bash
python -c "import aiohttp; print('aiohttp OK')"
```

### اختبار قاعدة البيانات:
```bash
python -c "import sqlite3; print('SQLite OK')"
```

### اختبار Jinja2:
```bash
python -c "from jinja2 import Template; print('Jinja2 OK')"
```

### عرض الأخطاء المفصلة:
```bash
# في .env، غيّر:
DEBUG=True
LOGLEVEL=DEBUG

# ثم شغّل:
python app_new.py
```

---

## 📊 عرض السجلات:

### بحث في السجلات (Linux/Mac):
```bash
# السجلات الأخيرة
tail -f /tmp/tnt_portal.log

# آخر 100 سطر
tail -n 100 /tmp/tnt_portal.log

# البحث عن أخطاء
grep ERROR /tmp/tnt_portal.log
```

### تنظيف السجلات:
```bash
rm /tmp/tnt_portal.log
```

---

## 🌐 اختبار API الكامل:

### تسجيل مستخدم جديد:
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "Test@12345"
  }'
```

### تسجيل الدخول:
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "Test@12345"
  }'
```

### عرض الملف الشخصي:
```bash
curl http://localhost:8080/api/user/profile \
  -H "Cookie: session=YOUR_SESSION_TOKEN"
```

### عرض الإحصائيات:
```bash
curl http://localhost:8080/api/stats
```

---

## 🔄 إعادة تشغيل التطبيق:

### إيقاف التطبيق:
```bash
Ctrl + C
```

### قتل العملية (إذا علقت):
```bash
# على Linux/Mac:
lsof -i :8080
kill -9 <PID>

# على Windows:
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

### إعادة تشغيل:
```bash
# بعد الإيقاف:
python app_new.py
```

---

## 📤 النشر:

### على Render:
```bash
# 1. push إلى GitHub
git push origin main

# 2. اتبع الخطوات في DEPLOYMENT.md
```

### على Railway:
```bash
# 1. تثبيت Railway CLI
npm install -g @railway/cli

# 2. إنشاء مشروع
railway init

# 3. النشر
railway up
```

### Docker:
```bash
# بناء الصورة
docker build -t tnt-portal -f docker/Dockerfile .

# تشغيل الحاوية
docker run -p 8080:8080 tnt-portal

# أو استخدم Docker Compose:
docker-compose -f docker/docker-compose.yml up
```

---

## 🧹 تنظيف وإعادة تعيين:

### حذف قاعدة البيانات:
```bash
rm database.db
```

### حذف جميع ملفات Python المترجمة:
```bash
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

### إعادة تشغيل كاملة:
```bash
# 1. حذف الملفات المؤقتة
rm -rf __pycache__
rm database.db

# 2. حذف المكتبات (اختياري)
pip uninstall -r requirements-new.txt -y

# 3. تثبيت من جديد
pip install -r requirements-new.txt

# 4. تشغيل
python app_new.py
```

---

## 📝 تحرير الملفات:

### تحرير الملفات (Linux/Mac):
```bash
# استخدام nano
nano app_new.py

# أو استخدام vim
vim app_new.py

# أو استخدام VS Code
code .
```

### تحرير الملفات (Windows - CMD):
```cmd
# استخدام Notepad++
notepad++ app_new.py

# أو VS Code
code .
```

---

## 🔍 البحث والاستكشاف:

### البحث عن ملف:
```bash
find . -name "*.py" -type f
```

### البحث عن مجلد:
```bash
find . -name "core" -type d
```

### البحث عن كلمة في الملفات:
```bash
grep -r "SECRET_KEY" .
```

### عد أسطر الكود:
```bash
wc -l app_new.py
wc -l core/*.py
```

---

## 📊 الإحصائيات:

### عدد الملفات Python:
```bash
find . -name "*.py" -type f | wc -l
```

### إجمالي أسطر الكود:
```bash
find . -name "*.py" -type f -exec wc -l {} + | tail -1
```

### حجم المشروع:
```bash
du -sh .
```

---

## 🎯 الأوامر الشائعة:

| الأمر | الغرض |
|------|------|
| `python app_new.py` | تشغيل التطبيق |
| `pip install -r requirements-new.txt` | تثبيت المكتبات |
| `cp .env.example .env` | نسخ الإعدادات |
| `rm database.db` | حذف قاعدة البيانات |
| `sqlite3 database.db` | فتح قاعدة البيانات |
| `curl http://localhost:8080/api/stats` | اختبار API |
| `Ctrl + C` | إيقاف التطبيق |

---

## 🔥 الأوامر المتقدمة:

### تشغيل مع إعادة تحميل تلقائية:
```bash
# تثبيت watchdog
pip install watchdog

# أو استخدام nodemon (إذا كان مثبت):
nodemon --exec python app_new.py --ext py
```

### تشغيل مع Logging:
```bash
# إعادة توجيه السجلات لملف
python app_new.py > app.log 2>&1 &
```

### اختبار الأداء:
```bash
# استخدام Apache Bench
ab -n 1000 -c 10 http://localhost:8080/api/stats
```

---

## 💡 نصائح سريعة:

1. **دائماً ثبّت المكتبات أولاً:**
   ```bash
   pip install -r requirements-new.txt
   ```

2. **انسخ .env قبل التشغيل:**
   ```bash
   cp .env.example .env
   ```

3. **اختبر بـ curl قبل الواجهة:**
   ```bash
   curl http://localhost:8080/api/stats
   ```

4. **اقتل العملية إذا علقت:**
   ```bash
   Ctrl + C
   ```

5. **أعد تشغيل كامل عند المشاكل:**
   ```bash
   rm -rf database.db __pycache__
   python app_new.py
   ```

---

## ✅ قائمة الفحص قبل الإطلاق:

- [ ] تثبيت Python 3.11+
- [ ] تثبيت pip
- [ ] تثبيت المكتبات: `pip install -r requirements-new.txt`
- [ ] نسخ .env: `cp .env.example .env`
- [ ] تشغيل التطبيق: `python app_new.py`
- [ ] فتح: `http://localhost:8080`
- [ ] دخول بـ: `DANGER / Aa@123456`
- [ ] اختبار جميع الميزات
- [ ] جاهز للإنتاج! 🎉

---

**استمتع بتطبيقك! 🚀**
