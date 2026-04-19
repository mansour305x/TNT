# TNT Alliance Portal - API Documentation

## نقطة الدخول الرئيسية

```
Base URL: http://localhost:8080
Response Format: JSON
```

---

## 🔐 Authentication Endpoints

### 1. التسجيل (Register)

**Endpoint:** `POST /api/auth/register`

**Body:**
```json
{
  "username": "string (min: 3)",
  "email": "string (valid email)",
  "password": "string (min: 8, must contain uppercase, lowercase, digit, special char)",
  "full_name": "string (optional)"
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "تم إنشاء الحساب بنجاح",
  "user_id": 1
}
```

**Errors:**
- `400`: بيانات غير صحيحة
- `400`: اسم مستخدم أو بريد موجود مسبقاً

---

### 2. تسجيل الدخول (Login)

**Endpoint:** `POST /api/auth/login`

**Body:**
```json
{
  "username": "string or email",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم تسجيل الدخول بنجاح",
  "user_id": 1
}
```

**Cookies:** 
- `member_portal_session`: جلسة المستخدم

**Errors:**
- `401`: بيانات دخول غير صحيحة
- `401`: الحساب معطل

---

### 3. تسجيل الخروج (Logout)

**Endpoint:** `POST /api/auth/logout`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم تسجيل الخروج"
}
```

---

### 4. OAuth Google

**Endpoint:** `GET /auth/google`

**Response:** `302 Redirect` إلى Google OAuth

---

### 5. OAuth Google Callback

**Endpoint:** `GET /auth/google/callback?code=CODE&state=STATE`

**Response:** `200 OK` (Redirects to /dashboard)

---

## 👤 User Endpoints

### 1. الحصول على ملف المستخدم

**Endpoint:** `GET /api/user/profile`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "ahmed",
  "email": "ahmed@example.com",
  "full_name": "Ahmed Ali",
  "role": "member",
  "is_email_verified": true,
  "is_active": true,
  "avatar_url": null,
  "created_at": "2024-04-19T10:30:00",
  "updated_at": "2024-04-19T10:30:00",
  "last_login": "2024-04-19T15:45:00"
}
```

---

### 2. تحديث ملف المستخدم

**Endpoint:** `PUT /api/user/profile`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "full_name": "Ahmed Ali Smith"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم التحديث"
}
```

---

### 3. تغيير كلمة المرور

**Endpoint:** `POST /api/user/password`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "current_password": "string",
  "new_password": "string (must meet requirements)"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم تغيير كلمة المرور"
}
```

**Errors:**
- `400`: كلمة المرور الحالية غير صحيحة
- `400`: كلمة المرور الجديدة ضعيفة

---

### 4. طلب بريد التحقق

**Endpoint:** `POST /api/user/email/request-verification`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم إرسال بريد التحقق"
}
```

---

### 5. التحقق من البريد الإلكتروني

**Endpoint:** `POST /api/user/email/verify`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "code": "123456"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم التحقق من البريد الإلكتروني بنجاح"
}
```

---

## 🏛️ State Endpoints

### 1. الحصول على الولايات

**Endpoint:** `GET /api/states`

**Response:** `200 OK`
```json
{
  "states": [
    {
      "id": 1,
      "state_name": "State 1",
      "state_number": "1"
    }
  ]
}
```

---

### 2. إنشاء ولاية جديدة

**Endpoint:** `POST /api/states`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "state_name": "State 1",
  "state_number": "1",
  "password": "string (for state login)"
}
```

**Required Permissions:** `state.create`

**Response:** `201 Created`
```json
{
  "success": true,
  "message": "تم إنشاء الولاية",
  "state_id": 1
}
```

---

### 3. الحصول على ولاية

**Endpoint:** `GET /api/states/{state_id}`

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "State 1",
  "state_number": "1",
  "admin_user_id": 1,
  "description": "State description",
  "is_active": true,
  "created_at": "2024-04-19T10:00:00",
  "updated_at": "2024-04-19T10:00:00"
}
```

---

### 4. تحديث الولاية

**Endpoint:** `PUT /api/states/{state_id}`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "description": "New description"
}
```

**Required Permissions:** `state.update` + State Admin

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم التحديث"
}
```

---

### 5. حذف الولاية

**Endpoint:** `DELETE /api/states/{state_id}`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Required Permissions:** `state.delete`

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم الحذف"
}
```

---

## 🛠️ Admin Endpoints

### 1. لوحة التحكم الإدارية

**Endpoint:** `GET /api/admin/dashboard`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Required Role:** `super_owner`

**Response:** `200 OK`
```json
{
  "stats": {
    "total_users": 10,
    "total_states": 3,
    "active_states": 2,
    "total_admins": 2
  }
}
```

---

### 2. الحصول على قائمة المستخدمين

**Endpoint:** `GET /api/admin/users`

**Headers:**
```
Cookie: member_portal_session=TOKEN
```

**Required Permissions:** `user.read`

**Response:** `200 OK`
```json
{
  "users": [
    {
      "id": 1,
      "username": "ahmed",
      "email": "ahmed@example.com",
      "role": "member",
      "is_admin": false,
      "is_active": true
    }
  ]
}
```

---

### 3. تغيير دور المستخدم

**Endpoint:** `POST /api/admin/users/{user_id}/role`

**Headers:**
```
Cookie: member_portal_session=TOKEN
Content-Type: application/json
```

**Body:**
```json
{
  "role": "admin" // super_owner, admin, state_admin, member, guest
}
```

**Required Permissions:** `user.update`

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "تم تغيير الدور"
}
```

---

## 📊 Status Codes

| Code | الوصف |
|------|------|
| 200 | نجح |
| 201 | تم الإنشاء |
| 400 | طلب غير صحيح |
| 401 | غير موثق |
| 403 | لا صلاحية |
| 404 | غير موجود |
| 500 | خطأ في الخادم |

---

## 🔒 الأمان

### Headers المهمة:
```
Cookie: member_portal_session=TOKEN  # إلزامي لمعظم الطلبات
Content-Type: application/json       # إلزامي للطلبات POST/PUT
```

### التحقق من الصلاحيات:
- جميع الطلبات تتطلب جلسة صحيحة (ما عدا التسجيل والتحميل)
- بعض الطلبات تتطلب صلاحيات محددة
- يتم التحقق التلقائي من صلاحيات المستخدم

---

## 📝 نماذج البيانات

### User
```json
{
  "id": "integer",
  "username": "string (unique)",
  "email": "string (unique)",
  "password_hash": "string",
  "full_name": "string",
  "role": "string (super_owner, admin, state_admin, member, guest)",
  "is_email_verified": "boolean",
  "is_active": "boolean",
  "is_admin": "boolean",
  "avatar_url": "string (optional)",
  "created_at": "datetime",
  "updated_at": "datetime",
  "last_login": "datetime (optional)"
}
```

### State
```json
{
  "id": "integer",
  "state_name": "string (unique)",
  "state_number": "string",
  "admin_user_id": "integer (FK users.id)",
  "description": "string (optional)",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Session
```json
{
  "id": "integer",
  "user_id": "integer (FK users.id)",
  "session_token": "string (unique)",
  "ip_address": "string",
  "user_agent": "string",
  "created_at": "datetime",
  "expires_at": "datetime"
}
```

---

## 🧪 أمثلة باستخدام JavaScript

```javascript
// التسجيل
async function register() {
  const response = await fetch('http://localhost:8080/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'ahmed',
      email: 'ahmed@example.com',
      password: 'SecurePass123!',
      full_name: 'Ahmed Ali'
    })
  });
  return await response.json();
}

// تسجيل الدخول
async function login() {
  const response = await fetch('http://localhost:8080/api/auth/login', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'ahmed',
      password: 'SecurePass123!'
    })
  });
  return await response.json();
}

// الحصول على الملف الشخصي
async function getProfile() {
  const response = await fetch('http://localhost:8080/api/user/profile', {
    method: 'GET',
    credentials: 'include'
  });
  return await response.json();
}
```

---

اخر تحديث: 19 أبريل 2026
