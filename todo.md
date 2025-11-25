# TODO для запуска сервера

## 1. База данных и миграции
- Создать БД PostgreSQL и выполнить `postgresql.md` (или провести alembic-миграции).
- Проверить наличие расширения `uuid-ossp`.
- Настроить переменные подключения (`POSTGRES_*` либо `DATABASE_URL` в `.env`).

## 2. S3-хранилище
- Заполнить `.env` значениями `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`, `S3_REGION_NAME`.
- Убедиться, что бакет существует и учётка имеет `PutObject`/`GetObject`.
- Задать префиксы `UPLOADS_PREFIX`, `VIDEOS_PREFIX` при необходимости.

## 3. OAuth-провайдеры
- Google:
  - Зарегистрировать OAuth-клиент, включить `https://developers.google.com` console.
  - В `.env`: `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`.
- VK:
  - Создать standalone-приложение, включить email в scope.
  - Переменные: `OAUTH_VK_CLIENT_ID`, `OAUTH_VK_CLIENT_SECRET`.
- Yandex:
  - Создать приложение в Yandex OAuth, разрешить `login:email login:info`.
  - Переменные: `OAUTH_YANDEX_CLIENT_ID`, `OAUTH_YANDEX_CLIENT_SECRET`.
- Для всех провайдеров указать redirect-uri:  
  - приватный: `https://<backend>/api/v1/auth/oauth/{provider}/callback`  
  - публичный (Яндекс): `https://<backend>/oauth/{provider}/callback`

## 4. Yandex Cloud (OCR + GPT)
- Получить API-ключ и Folder ID в Yandex Cloud.
- `.env`:  
  - `YANDEX_CLOUD_FOLDER_ID`, `YANDEX_OCR_API_KEY`.  
  - `YANDEX_GPT_API_KEY`, `YANDEX_GPT_PROJECT_ID`, `YANDEX_GPT_PROMPT_ID`, `YANDEX_GPT_BASE_URL` (по умолчанию `https://rest-assistant.api.cloud.yandex.net/v1`).
- Проверить квоты OCR и GPT.

## 5. YooKassa
- Настроить магазин, получить `YOOKASSA_SHOP_ID`, `YOOKASSA_API_KEY`.
- Дополнительно: `YOOKASSA_API_BASE`, `YOOKASSA_FALLBACK_RECEIPT_EMAIL`, `YOOKASSA_TAX_SYSTEM_CODE`, `YOOKASSA_VAT_CODE`.
- Прописать webhook URL: `POST https://<backend>/api/v1/webhooks/payments/yookassa`.

## 6. Сессии и фронтенд
- `JWT_SECRET_KEY` — используется SessionMiddleware.
- `FRONTEND_RETURN_URL_BASE` — базовый URL для редиректов после OAuth и YooKassa.
- Включить CORS: при необходимости добавить домены в `app/main.py`.

## 7. API-ключи админских ручек
- `SERVER_API_KEY` — обязателен для /transactions, /payments, /users (кроме `/auth-user`), /data, /tariffs.
- Фронт при обращении к защищённым ручкам должен слать `X-API-Key`.

## 8. Запуск
- Установить зависимости `pip install -r requirements.txt` (включая `openai`).
- Выполнить `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- Проверить `GET /health`.

## 9. Проверка пайплайна
- `POST /api/v1/auth-user` с `x-user-ip`.
- `POST /api/v1/job` с файлом, убедиться в списании токена и появлении записи в БД.
- Проследить логи OCR/GPT, проверить содержимое `detected_text`/`generated_text`.


