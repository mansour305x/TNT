# TNT Alliance Portal - Database Schema

## نظرة عامة على قاعدة البيانات

```
┌──────────────────┐
│      users       │
├──────────────────┤
│ id (PK)          │
│ username         │
│ email            │
│ password_hash    │
│ role             │
│ is_email_verified│
│ oauth_provider   │
│ oauth_id         │
└──────────────────┘
        │
        ├─────────────────┐
        │                 │
┌───────▼──────────┐  ┌──►────────────────────┐
│  state_members   │  │  oauth_identities    │
├──────────────────┤  ├──────────────────────┤
│ id (PK)          │  │ id (PK)              │
│ user_id (FK)     │  │ user_id (FK)         │
│ state_id (FK)    │  │ provider             │
│ role             │  │ provider_id          │
└──────────────────┘  │ email                │
        ▲             │ name                 │
        │             │ avatar_url           │
        │             └──────────────────────┘
        │
┌───────┴─────────┐
│     states      │
├─────────────────┤
│ id (PK)         │
│ state_name      │
│ state_number    │
│ password_hash   │
│ admin_user_id   │
│ description     │
│ is_active       │
└─────────────────┘
        │
        ├─────────────────────┬──────────────────┐
        │                     │                  │
┌───────▼──────────┐  ┌──────▼────────┐  ┌─────▼────────┐
│ member_records   │  │transfer_records│  │permissions   │
├──────────────────┤  ├─────────────────┤  ├──────────────┤
│ id (PK)          │  │ id (PK)         │  │ id (PK)      │
│ state_id (FK)    │  │ state_id (FK)   │  │ role         │
│ member_name      │  │ member_name     │  │ permission_key
│ member_uid       │  │ member_uid      │  │ is_granted   │
│ alliance         │  │ power           │  └──────────────┘
│ rank             │  │ furnace         │
│ power            │  │ current_state   │
│ furnace          │  │ invite_type     │
│ notes            │  │ future_alliance │
│ created_at       │  │ notes           │
└──────────────────┘  │ created_at      │
                      └─────────────────┘

┌─────────────────────────────────────────┐
│ Other Tables                            │
├─────────────────────────────────────────┤
│ - sessions                              │
│ - email_verification_codes              │
│ - password_reset_tokens                 │
│ - login_attempts                        │
│ - activity_logs                         │
│ - user_permissions                      │
└─────────────────────────────────────────┘
```

---

## 📋 تفاصيل الجداول

### 1. users

**الوصف:** جدول المستخدمين الأساسي

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| username | TEXT | NOT NULL, UNIQUE | اسم المستخدم الفريد |
| email | TEXT | UNIQUE | البريد الإلكتروني الفريد |
| password_hash | TEXT | NOT NULL | تجزئة كلمة المرور |
| oauth_provider | TEXT | - | مزود OAuth (google, discord) |
| oauth_id | TEXT | UNIQUE | معرف OAuth من المزود |
| full_name | TEXT | - | الاسم الكامل |
| avatar_url | TEXT | - | رابط الصورة الرمزية |
| is_email_verified | INTEGER | DEFAULT 0 | هل البريد موثق؟ |
| email_verified_at | TEXT | - | تاريخ التحقق |
| role | TEXT | DEFAULT 'member' | الدور (super_owner, admin, etc) |
| is_active | INTEGER | DEFAULT 1 | هل الحساب نشط؟ |
| is_admin | INTEGER | DEFAULT 0 | هل المستخدم مسؤول؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| updated_at | TEXT | DEFAULT NOW | تاريخ آخر تحديث |
| last_login | TEXT | - | آخر تسجيل دخول |

**الفهارس:**
```sql
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

---

### 2. states

**الوصف:** جدول الولايات

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| state_name | TEXT | NOT NULL, UNIQUE | اسم الولاية الفريد |
| state_number | TEXT | UNIQUE | رقم الولاية |
| password_hash | TEXT | NOT NULL | كلمة مرور الولاية |
| admin_user_id | INTEGER | FK users(id) | معرف مسؤول الولاية |
| description | TEXT | - | وصف الولاية |
| logo_url | TEXT | - | رابط الشعار |
| is_active | INTEGER | DEFAULT 1 | هل الولاية نشطة؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| updated_at | TEXT | DEFAULT NOW | تاريخ آخر تحديث |

**الفهارس:**
```sql
CREATE INDEX idx_states_name ON states(state_name);
```

---

### 3. state_members

**الوصف:** جدول عضوية الولايات (Many-to-Many)

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| state_id | INTEGER | NOT NULL, FK | معرف الولاية |
| role | TEXT | DEFAULT 'member' | دور العضو (admin, member) |
| joined_at | TEXT | DEFAULT NOW | تاريخ الانضمام |

**القيد الفريد:**
```sql
UNIQUE(user_id, state_id)
```

**الفهارس:**
```sql
CREATE INDEX idx_state_members_user ON state_members(user_id);
CREATE INDEX idx_state_members_state ON state_members(state_id);
```

---

### 4. permissions

**الوصف:** جدول الصلاحيات حسب الدور

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| role | TEXT | NOT NULL | الدور |
| permission_key | TEXT | NOT NULL | مفتاح الصلاحية |
| is_granted | INTEGER | DEFAULT 1 | هل الصلاحية ممنوحة؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |

**القيد الفريد:**
```sql
UNIQUE(role, permission_key)
```

---

### 5. user_permissions

**الوصف:** جدول الصلاحيات المخصصة للمستخدمين

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| permission_key | TEXT | NOT NULL | مفتاح الصلاحية |
| is_granted | INTEGER | DEFAULT 1 | هل الصلاحية ممنوحة؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |

**القيد الفريد:**
```sql
UNIQUE(user_id, permission_key)
```

---

### 6. sessions

**الوصف:** جدول جلسات المستخدمين

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| session_token | TEXT | NOT NULL, UNIQUE | رمز الجلسة |
| ip_address | TEXT | - | عنوان IP |
| user_agent | TEXT | - | متصفح المستخدم |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| expires_at | TEXT | NOT NULL | تاريخ انتهاء الصلاحية |

**الفهارس:**
```sql
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(session_token);
```

---

### 7. email_verification_codes

**الوصف:** جدول أكواد التحقق من البريد

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| email | TEXT | NOT NULL | البريد الإلكتروني |
| code | TEXT | NOT NULL, UNIQUE | رمز التحقق |
| is_used | INTEGER | DEFAULT 0 | هل تم استخدامه؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| expires_at | TEXT | NOT NULL | تاريخ انتهاء الصلاحية |

---

### 8. password_reset_tokens

**الوصف:** جدول رموز إعادة تعيين كلمة المرور

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| token | TEXT | NOT NULL, UNIQUE | رمز إعادة التعيين |
| is_used | INTEGER | DEFAULT 0 | هل تم استخدامه؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| expires_at | TEXT | NOT NULL | تاريخ انتهاء الصلاحية |

---

### 9. oauth_identities

**الوصف:** جدول هويات OAuth المرتبطة

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | NOT NULL, FK | معرف المستخدم |
| provider | TEXT | NOT NULL | مزود OAuth (google, discord) |
| provider_id | TEXT | NOT NULL | معرف المزود للمستخدم |
| email | TEXT | - | البريد من المزود |
| name | TEXT | - | الاسم من المزود |
| avatar_url | TEXT | - | الصورة من المزود |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| updated_at | TEXT | DEFAULT NOW | تاريخ آخر تحديث |

**القيد الفريد:**
```sql
UNIQUE(provider, provider_id)
```

---

### 10. member_records

**الوصف:** جدول سجلات الأعضاء

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| state_id | INTEGER | NOT NULL, FK | معرف الولاية |
| member_name | TEXT | NOT NULL | اسم العضو |
| member_uid | TEXT | NOT NULL | معرف العضو الفريد |
| alliance | TEXT | DEFAULT '' | التحالف |
| rank | TEXT | DEFAULT '' | الرتبة |
| power | TEXT | DEFAULT '' | القوة |
| furnace | TEXT | DEFAULT '' | الفرن |
| notes | TEXT | DEFAULT '' | ملاحظات |
| created_by | INTEGER | FK users(id) | من أنشأ السجل |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |
| updated_at | TEXT | DEFAULT NOW | تاريخ آخر تحديث |

**القيد الفريد:**
```sql
UNIQUE(state_id, member_uid)
```

**الفهارس:**
```sql
CREATE INDEX idx_member_records_state ON member_records(state_id);
```

---

### 11. transfer_records

**الوصف:** جدول سجلات التحويل

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| state_id | INTEGER | NOT NULL, FK | معرف الولاية |
| member_name | TEXT | NOT NULL | اسم العضو |
| member_uid | TEXT | NOT NULL | معرف العضو |
| power | TEXT | DEFAULT '' | القوة |
| furnace | TEXT | DEFAULT '' | الفرن |
| current_state | TEXT | NOT NULL | الولاية الحالية |
| invite_type | TEXT | DEFAULT '' | نوع الدعوة |
| future_alliance | TEXT | NOT NULL | التحالف المستقبلي |
| notes | TEXT | DEFAULT '' | ملاحظات |
| created_by | INTEGER | FK users(id) | من أنشأ السجل |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |

---

### 12. activity_logs

**الوصف:** جدول سجل النشاط

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| user_id | INTEGER | FK users(id) | معرف المستخدم |
| action | TEXT | NOT NULL | الإجراء |
| resource_type | TEXT | - | نوع المورد |
| resource_id | INTEGER | - | معرف المورد |
| details | TEXT | - | التفاصيل |
| ip_address | TEXT | - | عنوان IP |
| created_at | TEXT | DEFAULT NOW | تاريخ الإنشاء |

**الفهارس:**
```sql
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created ON activity_logs(created_at);
```

---

### 13. login_attempts

**الوصف:** جدول محاولات تسجيل الدخول

| Column | Type | Constraints | الوصف |
|--------|------|-------------|--------|
| id | INTEGER | PRIMARY KEY | معرف فريد |
| username | TEXT | NOT NULL | اسم المستخدم |
| ip_address | TEXT | - | عنوان IP |
| success | INTEGER | DEFAULT 0 | هل نجحت؟ |
| created_at | TEXT | DEFAULT NOW | تاريخ المحاولة |

---

## 🔍 الاستعلامات الشائعة

### الحصول على صلاحيات المستخدم:
```sql
SELECT DISTINCT p.permission_key
FROM permissions p
WHERE p.role = (SELECT role FROM users WHERE id = ?)
  AND p.is_granted = 1

UNION

SELECT up.permission_key
FROM user_permissions up
WHERE up.user_id = ?
  AND up.is_granted = 1;
```

### التحقق من عضوية الولاية:
```sql
SELECT sm.*, u.username
FROM state_members sm
JOIN users u ON sm.user_id = u.id
WHERE sm.state_id = ?
ORDER BY sm.role DESC;
```

### سجل النشاط الأخير:
```sql
SELECT *
FROM activity_logs
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT 50;
```

### عدد المستخدمين النشطين:
```sql
SELECT COUNT(*) as active_users
FROM users
WHERE is_active = 1
  AND last_login > datetime('now', '-30 days');
```

---

## 🔗 العلاقات

### One-to-Many:
- users → state_members (1:N)
- users → sessions (1:N)
- users → activity_logs (1:N)
- states → member_records (1:N)
- states → transfer_records (1:N)

### Many-to-Many:
- users ← → states (via state_members)

### One-to-One:
- users ← → oauth_identities (1:1 per provider)

---

## 💾 النسخ الاحتياطية والصيانة

### النسخ الاحتياطية:
```bash
# النسخ الاحتياطية اليومية
0 2 * * * sqlite3 /path/to/portal.db ".backup '/backups/portal-$(date +\%Y\%m\%d).db'"
```

### تنظيف الجلسات المنتهية:
```sql
DELETE FROM sessions WHERE expires_at < datetime('now');
DELETE FROM email_verification_codes WHERE expires_at < datetime('now');
DELETE FROM password_reset_tokens WHERE expires_at < datetime('now');
```

---

آخر تحديث: 19 أبريل 2026
