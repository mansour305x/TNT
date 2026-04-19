# TNT Alliance Portal - Deployment Guide

## نشر التطبيق على الخوادم

---

## 🚀 نشر على Render

### الخطوة 1: إعداد Render

1. اذهب إلى [render.com](https://render.com)
2. سجل دخول أو أنشئ حساب
3. قم بربط حسابك مع GitHub

### الخطوة 2: إنشاء خدمة جديدة

```bash
# في مجلد المشروع
git add .
git commit -m "Deploy to Render"
git push origin main
```

### الخطوة 3: تكوين Render

**ملف `render.yaml` (موجود بالفعل):**

```yaml
services:
  - type: web
    name: tnt-portal
    runtime: python
    buildCommand: ". venv/bin/activate && pip install -r requirements-new.txt"
    startCommand: "python app_new.py"
    envVars:
      - key: PORTAL_SECRET_KEY
        value: # set from dashboard
      - key: GOOGLE_CLIENT_ID
        value: # set from dashboard
      - key: GOOGLE_CLIENT_SECRET
        value: # set from dashboard
      - key: SMTP_USERNAME
        value: # set from dashboard
      - key: SMTP_PASSWORD
        value: # set from dashboard
```

### الخطوة 4: تعيين المتغيرات البيئية

في لوحة تحكم Render:

1. اذهب إلى "Environment"
2. أضف المتغيرات التالية:
   - `PORTAL_SECRET_KEY`: مفتاح سري قوي
   - `GOOGLE_CLIENT_ID`: من Google Cloud Console
   - `GOOGLE_CLIENT_SECRET`: من Google Cloud Console
   - `GOOGLE_REDIRECT_URI`: `https://your-app.onrender.com/auth/google/callback`
   - `SMTP_USERNAME`: بريد Gmail
   - `SMTP_PASSWORD`: App Password
   - `FROM_EMAIL`: بريد Gmail
   - `FROM_NAME`: اسم التطبيق

### الخطوة 5: نشر

```bash
git push origin main
# سيتم النشر تلقائياً على Render
```

---

## 🚀 نشر على Railway

### الخطوة 1: إعداد Railway

1. اذهب إلى [railway.app](https://railway.app)
2. سجل دخول أو أنشئ حساب
3. قم بربط GitHub

### الخطوة 2: إنشاء مشروع جديد

```bash
# تثبيت CLI
npm i -g @railway/cli

# تسجيل الدخول
railway login

# ربط المشروع
railway link
```

### الخطوة 3: تكوين Railway

**ملف `railway.toml` (موجود بالفعل):**

```toml
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements-new.txt"

[deploy]
startCommand = "python app_new.py"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5
```

### الخطوة 4: تعيين المتغيرات البيئية

```bash
railway variable set PORTAL_SECRET_KEY=your-secret-key
railway variable set GOOGLE_CLIENT_ID=your-client-id
railway variable set GOOGLE_CLIENT_SECRET=your-client-secret
railway variable set GOOGLE_REDIRECT_URI=https://your-app.up.railway.app/auth/google/callback
railway variable set SMTP_USERNAME=your-email@gmail.com
railway variable set SMTP_PASSWORD=your-app-password
railway variable set FROM_EMAIL=your-email@gmail.com
railway variable set FROM_NAME="TNT Alliance"
```

### الخطوة 5: نشر

```bash
railway deploy
```

---

## 🐳 نشر مع Docker

### الخطوة 1: بناء صورة Docker

```bash
# بناء الصورة
docker build -f docker/Dockerfile -t tnt-portal:latest .

# الوسوم الاختيارية
docker tag tnt-portal:latest your-registry/tnt-portal:latest
```

### الخطوة 2: تشغيل الحاوية

```bash
# التشغيل المحلي
docker run -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -e PORTAL_SECRET_KEY=your-secret \
  -e GOOGLE_CLIENT_ID=your-id \
  tnt-portal:latest

# أو باستخدام docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

### الخطوة 3: دفع إلى Docker Hub

```bash
# تسجيل الدخول
docker login

# دفع الصورة
docker push your-registry/tnt-portal:latest
```

---

## 🔐 إعدادات الإنتاج

### 1. الأمان

```python
# في app.py
SECURE_COOKIES = True
SECURE_HSTS = True
SECURE_SSL_REDIRECT = True

# في .env
ENVIRONMENT=production
```

### 2. قاعدة البيانات

```bash
# استخدام مسار ثابت
PORTAL_DB_PATH=/var/data/portal.db

# أو استخدام PostgreSQL (للمستقبل)
DATABASE_URL=postgresql://user:pass@localhost/portal
```

### 3. البريد الإلكتروني

```bash
# استخدام Service مخصص
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # App Password بدلاً من كلمة السر
```

### 4. التسجيل

```bash
# تسجيل شامل
LOG_LEVEL=INFO
LOG_FILE=/var/log/portal/app.log

# تدوير السجلات
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

### 5. الأداء

```bash
# عدد العمليات
WORKERS=4

# حد أقصى للاتصالات
MAX_CONNECTIONS=100

# Timeout
REQUEST_TIMEOUT=30
```

---

## 🔄 التحديثات والصيانة

### تحديث الكود

```bash
# سحب آخر التغييرات
git pull origin main

# تثبيت المكتبات الجديدة
pip install -r requirements-new.txt

# تشغيل الهجرات (إن وجدت)
python scripts/migrate.py

# إعادة تشغيل الخدمة
systemctl restart tnt-portal
```

### النسخ الاحتياطية

```bash
# نسخة يومية من قاعدة البيانات
0 2 * * * sqlite3 /var/data/portal.db ".backup '/backups/portal-$(date +\%Y\%m\%d).db'"

# تنظيف النسخ القديمة
0 3 * * * find /backups -name "portal-*.db" -mtime +30 -delete
```

### المراقبة

```bash
# فحص صحة التطبيق
curl http://localhost:8080/health

# عرض السجلات
tail -f /var/log/portal/app.log

# مراقبة الموارد
top -p $(pgrep -f app_new.py)
```

---

## 🚨 استكشاف الأخطاء

### المشكلة: الخطأ 502 Bad Gateway

**الحل:**
```bash
# تحقق من السجلات
tail -f /var/log/portal/app.log

# تحقق من الاتصال بقاعدة البيانات
sqlite3 /var/data/portal.db "SELECT COUNT(*) FROM users;"

# أعد تشغيل الخدمة
systemctl restart tnt-portal
```

### المشكلة: عدم وصول البريد الإلكتروني

**الحل:**
```python
# اختبر إعدادات SMTP
python -c "
import smtplib
from core.config import Config
try:
    with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        print('SMTP config is valid')
except Exception as e:
    print(f'Error: {e}')
"
```

### المشكلة: بطء التطبيق

**الحل:**
```bash
# تحقق من استخدام الموارد
ps aux | grep app_new.py
free -h
df -h

# زيادة عدد العمليات
WORKERS=8

# تنظيف السجلات القديمة
python scripts/cleanup_logs.py
```

---

## 📊 المراقبة والتقارير

### Uptime Monitoring

```bash
# استخدام service مثل Uptimerobot
# https://uptimerobot.com

# أو استخدام healthcheck مدمج
curl http://your-app.com/health
```

### Error Tracking

```bash
# استخدام Sentry (اختياري)
pip install sentry-sdk
```

### Performance Monitoring

```bash
# استخدام New Relic أو Datadog
# أو تحليل السجلات
python scripts/analyze_logs.py
```

---

## 🔒 الأمان في الإنتاج

### Checklist الأمان

- [ ] تغيير `PORTAL_SECRET_KEY`
- [ ] استخدام HTTPS فقط
- [ ] تمكين HSTS
- [ ] إنشاء firewall rules
- [ ] تحديث المكتبات بانتظام
- [ ] تفعيل 2FA للمسؤولين
- [ ] نسخ احتياطية دورية
- [ ] مراقبة السجلات
- [ ] اختبار الاختراق بانتظام

### SSL/TLS

```bash
# استخدام Let's Encrypt
sudo certbot certonly --webroot -w /var/www/html -d your-domain.com

# أو استخدام service مثل Cloudflare
# https://cloudflare.com
```

---

## 📝 ملفات التكوين

### `.env.production`

```bash
ENVIRONMENT=production
PORTAL_SECRET_KEY=generate-a-strong-key-here
LOG_LEVEL=INFO
SECURE_COOKIES=true
SECURE_SSL_REDIRECT=true
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# ... بقية المتغيرات
```

### `nginx.conf` (اختياري)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

آخر تحديث: 19 أبريل 2026
