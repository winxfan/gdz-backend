# Frontend API (Swagger-style)

Ниже перечислены публичные ручки, доступные фронтенду. Формат — краткая выдержка из OpenAPI: метод, путь, основные параметры и пример ответа. После каждого блока — пояснение.

---

## `POST /api/v1/auth-user`

```yaml
summary: Авторизация/регистрация анонимного пользователя
headers:
  x-user-ip:
    required: true
    description: Реальный IP пользователя
responses:
  200:
    application/json:
      schema:
        id: string (uuid)
        username: string
        avatarId: integer (1..5)
        tokens: number
        tokensUsedAsAnon: integer
        isAuthorized: boolean
```

**Пояснение:** сервер ищет пользователя по IP; если не найден — создаёт с детерминированным именем и аватаром. Можно звать при каждом визите, чтобы получить актуальные токены.

---

## `GET /api/v1/auth/oauth/{provider}/login`

```yaml
summary: Начало OAuth-авторизации
path params:
  provider: enum[google, vk, yandex]
responses:
  302: redirect to provider consent page
```

**Пояснение:** фронт редиректит пользователя на эту ручку, далее происходит стандартный OAuth flow. Завершение — см. публичный callback `/oauth/{provider}/callback`, куда перенаправит провайдер.

---

## `POST /api/v1/job`

```yaml
summary: Создание задачи распознавания
consumes: multipart/form-data
formData:
  image: file (required) - JPG/PNG/PDF ≤ 50MB
  userId: string (optional) - идентификатор авторизованного пользователя
headers:
  x-user-ip: string (required для анонимов)
responses:
  200:
    schema:
      jobId: string
      status: string (queued|processing|done|failed)
      tokensLeft: number
  402: Not enough tokens
  403: Anonymous quota exceeded
```

**Пояснение:** списывает 1 токен, загружает изображение в S3 и запускает пайплайн: Yandex OCR → Yandex GPT. Возвращает `jobId`, по которому можно получать статус.

---

## `GET /api/v1/job/{jobId}`

```yaml
summary: Получение информации о задаче
path params:
  jobId: string (uuid)
responses:
  200:
    schema:
      id: string
      status: string
      inputS3Url: string
      detectedText: string
      generatedText: string
      errorMessage: string|null
      user:
        id: string
        username: string
        avatarId: integer
        isAuthorized: boolean
  404: Job not found
```

**Пояснение:** фронт опрашивает до тех пор, пока `status != done`. После `done` доступен полный текст из OCR и ответ GPT. Лимит запросов с фронтенда - 15 раз, далее выкидывается ошибка и отображается на фронтенде

---

## `POST /api/v1/payments/intents`

```yaml
summary: Создание платежного намерения (YooKassa)
body:
  userId: string (uuid) - required
  amountRub: number - required
  provider: string (default yookassa)
  plan: string (optional)
responses:
  200:
    schema:
      id: string (transaction id)
      provider: string
      amountRub: number
      currency: string
      paymentUrl: string|null
      reference: string
      paymentId: string|null
  400/404: ошибки валидации
```

**Пояснение:** создаёт транзакцию, обращается в YooKassa, возвращает ссылку на оплату. Используется только для авторизованных пользователей.

---

## `POST /api/v1/webhooks/payments/{provider}`

```yaml
summary: Вебхук оплат (вызывается провайдером)
```

**Пояснение:** фронт не вызывает напрямую, но должен знать, что пополнение баланса завершится только после webhook-а.
