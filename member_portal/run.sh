#!/bin/bash
# 🚀 نص بسيط لتشغيل التطبيق فوراً

echo "═══════════════════════════════════════════════════════════"
echo "    TNT Alliance Portal - نظام إدارة التحالف"
echo "═══════════════════════════════════════════════════════════"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت!"
    echo "الرجاء تثبيت Python 3.11+"
    exit 1
fi

echo "✅ Python موجود"

# الذهاب للمجلد الصحيح
cd "$(dirname "$0")" || exit 1

# التحقق من requirements
echo "📦 التحقق من المكتبات..."
if [ ! -f "requirements-new.txt" ]; then
    echo "❌ ملف requirements-new.txt غير موجود!"
    exit 1
fi

# تثبيت المكتبات
pip install -q -r requirements-new.txt 2>/dev/null

echo "✅ المكتبات مثبتة"

# التحقق من .env
if [ ! -f ".env" ]; then
    echo "⚠️  ملف .env غير موجود"
    echo "📝 يتم نسخ .env.example → .env"
    
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ تم إنشاء .env (تأكد من إضافة بيانات Gmail والـ OAuth)"
    else
        echo "❌ ملف .env.example غير موجود!"
        exit 1
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🚀 جاري تشغيل التطبيق..."
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🌐 الوصول: http://localhost:8080"
echo "👤 حساب الاختبار:"
echo "   Username: DANGER"
echo "   Password: Aa@123456"
echo ""
echo "⌨️  لإيقاف التطبيق: اضغط Ctrl+C"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

# تشغيل التطبيق
python3 app_new.py
