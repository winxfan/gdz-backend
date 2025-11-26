# OAuth авторизация в gdz-backend

## Провайдеры

Поддерживаются три провайдера (`app/services/oauth.py`):
- Google (OpenID Connect, scope `openid email profile`);
- VK (OAuth2, scope `email`);
- Yandex (OAuth2, scope `login:email login:info`).

Все клиенты регистрируются один раз при старте приложения через `OAuthService`.

## Конфигурация

Параметры задаются в `.env` (см. `app/core/config.py`):
- `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`
- `OAUTH_VK_CLIENT_ID`, `OAUTH_VK_CLIENT_SECRET`
- `OAUTH_YANDEX_CLIENT_ID`, `OAUTH_YANDEX_CLIENT_SECRET`

Redirect URI:
- для Google/VK – `https://<backend>/api/v1/auth/oauth/{provider}/callback`;
- для Yandex – публичный маршрут `https://<backend>/oauth/{provider}/callback` (без `/api/v1`), т.к. Яндекс требует точное совпадение URL.

## Поток авторизации

1. **Старт:** фронт делает `GET /api/v1/auth/oauth/{provider}/login`.
   - Сервис проверяет провайдера, подготавливает callback URL и вызывает `authorize_redirect`.
   - Сессия Starlette используется для хранения промежуточных данных (state/redirect_uri) – дополнительный `anon_user_id` больше не создаётся на этом шаге.

2. **Callback:** провайдер перенаправляет пользователя на `/api/v1/auth/oauth/{provider}/callback` (или публичный `/oauth/...` для Яндекса).
   - `_handle_oauth_callback` получает `code`, обменивает на access token (через `authorize_access_token`).
   - Для Google используется `userinfo` из токена, для Яндекса выполняется отдельный запрос `https://login.yandex.ru/info`, для VK данные берутся из токена (`user_id`, `email`).

3. **Идентификация и merge** (`app/api/v1/auth.py`):
   - Из токена формируется `social_id` вида `{provider}:{id}`, собирается email и имя.
   - Параллельно читается IP из заголовка `x-user-ip` (если фронт пробросил) или cookie `user_ip` – используется как подсказка для поиска анонимного аккаунта.
   - `_link_user`:
     - пытается найти пользователя по `social_id`;
     - если не нашёл – ищет по email;
     - если передан IP, ищет анонимного пользователя по `ip` и в случае успеха **сливает** его с найденным авторизованным:
       - складывает балансы токенов;
       - переносит `username`, `avatar_id`, `ip`;
       - перепривязывает все `Job` и `Transaction` (через `UPDATE ... WHERE user_id = source.id`);
       - удаляет анонимную запись.
     - если ни один пользователь не найден – создаёт нового (`username/avatar` генерируются детерминированно на основе IP/емейла/соц-id).
   - Итоговый пользователь получает `social_id`, `email`, `is_authorized = True`.

4. **Редирект на фронтенд:** после успешного merge пользователь отправляется на `FRONTEND_RETURN_URL_BASE/profile?userId=<uuid>` (или с параметром `auth_error=...` при ошибках).

## Ошибки и логирование

- Любая ошибка авторизации (`OAuthError`, проблемы с userinfo, merge) логируется через `structlog`.
- Фронтенд получает редирект с `auth_error` + `provider`, чтобы показать сообщение.

## Связанные данные

- Модель `User` (`app/db/models.py`) содержит поля `social_id`, `email`, `is_authorized`, `balance_tokens`.
- При объединении анонимного и авторизованного пользователя переносятся транзакции и задания, чтобы история не терялась.

## Требования фронтенду

- Передавать реальный IP в заголовке `x-user-ip` при вызове OAuth callback (нужно для поиска анонимного пользователя).
- Хранить cookie `user_ip` только для резервного канала; сервер доверяет **только заголовку**.
- После редиректа с `userId` фронт может вызвать `/api/v1/auth-user` или другие API уже по `userId`.


