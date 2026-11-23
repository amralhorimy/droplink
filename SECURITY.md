# Security · الأمان

## English

**Reporting a vulnerability.** Please do not open a public issue. Use GitHub's *Security → Report a vulnerability* (private advisory) on this repository, and include steps to reproduce.

**Before deploying anything real**

- The values in `docker-compose.yml` and `.env.example` are **development defaults**. Set strong secrets in `.env`; never commit `.env`.
- Create a dedicated MinIO service account limited to the bucket instead of using root credentials.
- Put MinIO and the API behind TLS and set `DROPLINK_ENV=prod`, `DROPLINK_MINIO_PUBLIC_SECURE=true`, `DROPLINK_PUBLIC_BASE_URL=https://…`.
- Do not publish Mongo or Redis ports to the internet.
- This project has no user accounts and no antivirus scanning; read [docs/en/DECISIONS.md](docs/en/DECISIONS.md) §3 and §13.

**Built-in protections:** hashed management tokens, scrypt-hashed link passwords, constant-time comparisons, signed expiring URLs, upload size enforced by storage, forced `attachment` downloads, rate limits (app + Nginx), non-root containers, no internal details in error responses.

## العربية

**الإبلاغ عن ثغرة.** من فضلك لا تفتح Issue عاماً. استخدم *Security ← Report a vulnerability* (تنبيه خاص) في GitHub لهذا المستودع، واذكر خطوات إعادة الإنتاج.

**قبل نشر أي شيء حقيقي**

- القيم في `docker-compose.yml` و`.env.example` **افتراضيات للتطوير**. ضع أسراراً قوية في `.env` ولا ترفع `.env` أبداً.
- أنشئ حساب خدمة مخصصاً في MinIO محصوراً بالـ bucket بدل بيانات الجذر.
- ضع MinIO والـ API خلف TLS واضبط `DROPLINK_ENV=prod` و`DROPLINK_MINIO_PUBLIC_SECURE=true` و`DROPLINK_PUBLIC_BASE_URL=https://…`.
- لا تنشر منافذ Mongo أو Redis على الإنترنت.
- لا توجد حسابات مستخدمين ولا فحص فيروسات؛ اقرأ [docs/ar/DECISIONS.md](docs/ar/DECISIONS.md) البندين 3 و13.

**الحمايات المضمّنة:** توكنات إدارة مجزّأة، وكلمات مرور روابط بـ scrypt، ومقارنات بزمن ثابت، وروابط موقّعة منتهية، وحدّ حجم يفرضه التخزين، وتنزيل إجباري كـ `attachment`، وتحديد معدل (التطبيق + Nginx)، وحاويات بلا صلاحيات جذر، ولا تفاصيل داخلية في ردود الأخطاء.
