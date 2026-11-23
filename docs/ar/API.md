<div dir="rtl">

# مرجع الـ API

[English](../en/API.md) · [العودة إلى README](../../README.ar.md)

العنوان المحلي: `http://localhost:8080` · التوثيق التفاعلي: `/docs`
نقاط المالك تحتاج الترويسة **`X-Manage-Token`** (تُعاد مرة واحدة عند إنشاء الملف).

## النقاط

| الطريقة | المسار | التوثيق | الغرض |
|---|---|---|---|
| POST | `/v1/files` | – (محدودة المعدل) | تسجيل ملف والحصول على نموذج رفع موقّع |
| POST | `/v1/files/{id}/complete` | توكن | تأكيد الرفع؛ تبدأ المعالجة (202) |
| GET | `/v1/files/{id}` | توكن | الحالة الحالية ونتيجة التحليل |
| GET | `/v1/files/{id}/events` | توكن | الحالة اللحظية (Server-Sent Events) |
| GET | `/v1/files/{id}/thumbnail` | توكن | 302 إلى الصورة المصغّرة (للصور فقط) |
| DELETE | `/v1/files/{id}` | توكن | حذف الملف وروابطه فوراً (204) |
| POST | `/v1/files/{id}/links` | توكن | إنشاء رابط مشاركة |
| GET | `/v1/files/{id}/links` | توكن | قائمة روابط الملف |
| GET | `/v1/links/{slug}` | – | معلومات عامة لصفحة التنزيل |
| DELETE | `/v1/links/{slug}` | توكن ملفه | إلغاء رابط (204) |
| GET | `/d/{slug}` | – (+كلمة مرور) | 302 إلى رابط موقّع صالح 60 ثانية |
| GET | `/health/live`، `/health/ready` | – | الحياة / جاهزية الاعتماديات |

## جولة كاملة

### 1. التسجيل
```bash
curl -s -X POST localhost:8080/v1/files -H 'content-type: application/json' \
  -d '{"filename":"hello.txt","size":6,"content_type":"text/plain"}'
```
```json
{
  "file_id": "9f2c…",
  "manage_token": "Vq3…",
  "upload": {
    "url": "http://localhost:9000/droplink",
    "method": "POST",
    "fields": { "key": "files/9f2c…", "policy": "…", "x-amz-signature": "…" },
    "expires_at": "2026-11-23T12:15:00Z"
  },
  "expires_at": "2026-11-30T12:00:00Z"
}
```

### 2. الرفع مباشرة إلى التخزين
أرسل **كل** عناصر `fields` كحقول نموذج، والملف **أخيراً** باسم `file`:
```bash
curl -X POST "$URL" -F key="$KEY" -F policy="$POLICY" … -F file=@hello.txt
```
(الأمر `python -m labs.dropctl` يفعل هذا كله عنك.) يردّ MinIO بـ `204`. ورفع أكثر من `size` المُعلَن يرفضه MinIO.

### 3. الإكمال والمتابعة
```bash
curl -X POST localhost:8080/v1/files/$ID/complete -H "X-Manage-Token: $TOKEN"
curl -N localhost:8080/v1/files/$ID/events      -H "X-Manage-Token: $TOKEN"
```
```
event: status
data: {"type":"status","file_id":"…","status":"uploaded", …}

event: status
data: {"type":"status","status":"processing", …}

event: status
data: {"type":"status","status":"ready","sha256":"…","detected_type":"text/plain", …}
```
ينتهي البث عند `ready` أو `failed` أو `deleted` (أو بعد 120 ثانية بـ `event: timeout`).

### 4. إنشاء رابط
```bash
curl -X POST localhost:8080/v1/files/$ID/links -H "X-Manage-Token: $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"expires_in_seconds":3600,"max_downloads":1,"password":"secret"}'
```
`max_downloads: 0` تعني بلا حدّ. والرابط لا يعيش أطول من ملفه.

### 5. التنزيل
```bash
curl -i -H "X-Link-Password: secret" localhost:8080/d/$SLUG    # أو ?password=secret
```
الترويسة `302 Location:` هي رابط موقّع صالح 60 ثانية.

## الأخطاء

لكل خطأ الشكل نفسه:
```json
{ "error": { "code": "link_expired", "message": "This link has expired.", "request_id": "a1b2c3d4e5f60718" } }
```
اذكر `request_id` عند الإبلاغ عن مشكلة؛ فهو يوصلك إلى أسطر السجل الدقيقة.

| HTTP | `code` | المعنى |
|---|---|---|
| 401 | `unauthorized`، `password_required` | توكن الإدارة أو كلمة مرور الرابط مفقودة |
| 403 | `invalid_manage_token`، `wrong_password` | بيانات اعتماد خاطئة |
| 404 | `file_not_found`، `link_not_found`، `no_thumbnail` | غير موجود (أو حُذف) |
| 409 | `upload_missing`، `invalid_file_state`، `file_not_ready`، `file_unavailable` | وقت غير مناسب لهذا الإجراء |
| 410 | `link_expired`، `link_exhausted`، `link_revoked` | الرابط لم يعد صالحاً |
| 413 | `file_too_large` | أكبر من `MAX_FILE_SIZE_MB` |
| 422 | `validation_error` | حقول غير صالحة، مفصّلة في `details` |
| 429 | `too_many_requests` | تحديد المعدل؛ انظر `Retry-After` |
| 503 | `database_unavailable`، `cache_unavailable`، `storage_unavailable` | اعتمادية متوقفة |
| 500 | `internal_error` | خطأ من جهتنا؛ التفاصيل في السجلات فقط |

## الإعدادات

كل المتغيرات تبدأ بـ `DROPLINK_`. القائمة الكاملة بقيمها الافتراضية: [`app/platform/shared/config.py`](../../app/platform/shared/config.py). أهمها في البداية:

| المتغير | الافتراضي | الغرض |
|---|---|---|
| `MAX_FILE_SIZE_MB` | 100 | سقف الرفع |
| `FILE_TTL_HOURS` | 168 | أقصى عمر لأي ملف |
| `PUBLIC_BASE_URL` | `http://localhost:8080` | لبناء روابط المشاركة |
| `MINIO_PUBLIC_ENDPOINT` / `_SECURE` | `localhost:9000` / false | المضيف الذي يستخدمه العملاء للروابط الموقّعة |
| `RATE_LIMIT_DOWNLOAD_PER_MINUTE` | 30 | لكل IP |
| `LOG_JSON` | false | سجلات JSON لجامعي السجلات |
| `ENV` | dev | `prod` يُخفي `/docs` |

</div>
