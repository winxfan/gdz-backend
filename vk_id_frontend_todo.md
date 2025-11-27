# Интеграция VK ID SDK (Frontend)

1. **Подключить SDK**  
   ```html
   <script src="https://unpkg.com/@vkid/sdk@<3.0.0/dist-sdk/umd/index.js"></script>
   ```  
   Создать `VKID.Config.init` с параметрами:
   - `app`: ваш `OAUTH_VK_CLIENT_ID`;
   - `redirectUrl`: `https://<backend-domain>/api/v1/auth/oauth/vk/callback` (нужен для SDK, даже если backend обменивает код);
   - `responseMode`: `VKID.ConfigResponseMode.Callback`;
   - `scope`: по потребности (минимум `vkid.personal_info`);
   - `codeChallenge`, `codeChallengeMethod = S256`, `state` — генерировать на фронтенде (PKCE).

2. **Отрендерить OneTap / кнопку**  
   ```ts
   const widget = new VKID.OneTap();
   widget.render({ container, showAlternativeLogin: true })
     .on(VKID.WidgetEvents.ERROR, handleError)
     .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, ({ code, device_id }) => {
        exchangeCode(code, device_id);
     });
   ```
   Сохранить `codeVerifier`, `state`, `device_id` для дальнейшего запроса.

3. **Обмен кода на backend**  
   Вызвать `POST /api/v1/auth/oauth/vk-id/exchange`:
   ```json
   {
     "code": "<code>",
     "deviceId": "<device_id>",
     "codeVerifier": "<pkce_code_verifier>"
   }
   ```
   Заголовок `x-user-ip` обязателен (как и в остальных auth-запросах).  
   Backend:
   - вызывает VK ID API `https://id.vk.ru/oauth2/auth`;
   - декодирует `id_token` и при необходимости запрашивает профиль через service-key;
   - линкует / создаёт пользователя, выставляя `isAuthorized = true`;
   - отвечает публичным объектом пользователя (`id`, `username`, `avatarId`, `tokens`, и т.д.).

4. **Обработать ответ**  
   Хранить `userId` из ответа и `isAuthorized=true`. При ошибке (HTTP 400) показать сообщение; detail содержит причину (например, неверный код, просроченный verifier и т.п.).

5. **Безопасность**  
   - `codeVerifier` должен генерироваться заново на каждую попытку; не логировать его и `code`.
   - Проверять `state` на фронтенде (SDK возвращает то, что вы передали).
   - Запрос `POST /oauth/vk-id/exchange` должен выполняться только из доверенного фронтенда (CORS + HTTPS).

6. **Fallback**  
   Если обмен не удался, можно повторно вызвать `VKID.Auth.login()` и обновить PKCE.  
   В случае успеха фронт больше не обязан использовать старый OAuth `GET /auth/oauth/vk/login`.


