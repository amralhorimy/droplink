<div dir="rtl">

# مسار التعلّم

[English](../en/LEARNING_PATH.md) · [العودة إلى README](../../README.ar.md)

اقرأ المشروع بهذا الترتيب. كل خطوة تقول **ماذا تقرأ** و**ماذا تلاحظ** و**تمريناً صغيراً**.

## الخطوة 0 — شغّله (15 دقيقة)
شغّل `make up`، وافتح `/docs`، وارفع ملفاً بـ `python -m labs.dropctl upload <file>`، ثم راقب `make logs`.
*لاحظ:* نفس الـ `request_id` يظهر في كل سطر لوغ للطلب الواحد.

## الخطوة 1 — الإعدادات والأخطاء (30 دقيقة)
اقرأ `app/platform/shared/config.py` و`errors.py` و`handlers.py`.
*لاحظ:* للخطأ رسالتان: واحدة للسجلات وواحدة للعميل.
*تمرين:* أضف خطأ جديداً `FileLocked(Conflict)` بـ `code` خاص به وارفعه من service.

## الخطوة 2 — ميزة واحدة من أولها لآخرها (ساعة)
اقرأ `app/modules/links/` بهذا الترتيب: `schemas.py ← routes.py ← service.py ← repo.py ← policy.py`.
*لاحظ:* `policy.py` بلا I/O، لذلك `tests/unit/test_policy.py` لا يحتاج قاعدة بيانات.
*تمرين:* أضف قاعدة «لا يجوز إنشاء رابط لملف ما زال `processing`» واكتب اختبارها.

## الخطوة 3 — أغلفة البنية التحتية (ساعة)
اقرأ `app/platform/mongo/` و`redis/` و`minio/`، ثم `infra.py` و`container.py`.
*لاحظ:* نمط `with translate_mongo_errors("…"):`، وأن لا شيء ينشئ clients كمتغيرات عامة خفيّة.
*تمرين:* أوقف Redis (`docker compose stop redis`) ونادِ الـ API. اقرأ السجل ورد العميل جنباً إلى جنب.

## الخطوة 4 — آلة الحالات والذرّية (ساعة)
اقرأ `app/modules/files/domain.py` و`repo.transition`. ثم `app/platform/redis/scripts.py` وشغّل **`make race`**.
*لاحظ:* لماذا تنتج 200 طلباً متزامناً 10 تنزيلات بالضبط.
*تمرين:* في `scripts.py` استبدل Lua بـ «GET، قارن في Python، INCR» وشغّل `make race` مجدداً. شاهده يفشل.

## الخطوة 5 — العمل الخلفي (ساعة ونصف)
اقرأ `app/platform/redis/jobs.py` و`workers/processor/` ثم `workers/janitor/`.
*لاحظ:* المهمة تُنسخ إلى قائمة «processing» قبل بدء العمل ولا تُحذف إلا بعد انتهائه.
*تمرين:* اقتل الـ processor أثناء مهمة (`docker compose kill processor`)، أعد تشغيله، وشاهد المهمة تُسترجع.

## الخطوة 6 — الوقت الحقيقي (45 دقيقة)
اقرأ `app/modules/events/service.py` و`labs/client.py ← wait_until_done`.
*لاحظ:* اشترك أولاً، ثم خذ اللقطة.
*تمرين:* نادِ نقطة events بـ `curl -N -H "X-Manage-Token: …"` أثناء رفع ملف آخر.

## الخطوة 7 — النشر (45 دقيقة)
اقرأ `deploy/docker/Dockerfile` و`docker-compose.yml` و`deploy/nginx/nginx.conf`.
*لاحظ:* الـ healthchecks، والمستخدم غير الجذر، وصورة واحدة بثلاثة أوامر، وإعدادات Nginx الخاصة بـ SSE.

## تحديات
1. أضف نقطة `GET /v1/files/{id}/links/{slug}/stats`.
2. أضف `DROPLINK_ALLOWED_TYPES` وارفض الأنواع الأخرى في الـ processor (وسمها `failed`).
3. استبدل محدّد النافذة الثابتة بنافذة منزلقة.
4. أضف مقاييس Prometheus (`/metrics`) لطول الطابور وعدد التنزيلات.
5. أضف مفتاحاً لاختيار مزوّد متوافق مع `s3` (MinIO ↔ AWS S3).

</div>
