Авторизация VK id через SDK с обменом кода на бэкенде
￼
Схема работы авторизации через SDK для Web с обменом кода на бэкенде

Обратите внимание
Генерировать параметры PKCE нужно на фронтенде, а передавать на бэкенд — только при обмене кода на токены. Полученные токены рекомендуем оставить на бэкенде.
1. Пользователь инициирует процесс авторизации: нажимает кнопку Войти через VK ID.
2. Frontend Партнёра генерирует набор параметров PKCE, необходимых для защиты передаваемых данных, а также state и scopes:
    * code_verifier — случайно сгенерированная строка, новая на каждый запрос авторизации. Может состоять из следующих символов: a-z, A-Z, 0-9, _, -. Длина от 43 до 128 символов;
    * code_challenge — зашифрованный code_verifier;
    * code_challenge_method — метод шифрования code_verifier, константа. Всегда принимает значение S256;
    * state — произвольная строка состояния приложения;
    * scopes — список названий прав доступа, которые необходимы приложению в процессе получения токена. Если параметр не указан, то берётся минимальное значение прав доступа по умолчанию — vkid.personal_info.
3. Frontend Партнёра передаёт code_challenge и state в VK ID SDK через инициализацию VKID.Config.init().
4. Партнер вызывает метод VKID.Auth.login() из VK ID SDK.
5. VK ID SDK открывает ссылку https://id.vk.ru/authorize во вкладке браузера, используя несколько параметров. Основные из них:
    * response_type=code — требуемый ответ. При запросе кода подтверждения следует указать значение code;
    * client_id — ID приложения, полученный при создании приложения;
    * redirect_uri — адрес для возврата в приложение Партнёра.
6. Также используются параметры code_challenge, code_challenge_method и state.
7. Пользователь проходит аутентификацию.
8. Пользователю отображается форма с разрешением на предоставление доступов приложению, и он разрешает доступ.
9. Запрос на предоставление доступов приложению Партнёра передается в VK ID.
10. VK ID генерирует код авторизации.
11. VK ID передаёт через postMessage код авторизации, state, созданный на шаге 3, а также device_id.
12. VK ID SDK проверяет полученный state.
13. VK ID SDK возвращает на Frontend партнёра параметры code, state и device_id.
14. Frontend Партнёра передаёт code, state, code_verifier, device_id на свой Backend.
15. Чтобы обменять авторизационный код на токены, Backend Партнёра использует метод API id.vk.ru/oauth2/auth, где grant_type = authorization_code. В качестве аргументов использует code, code_verifier и device_id, которые получены после авторизации.
16. В ответ на код авторизации VK ID возвращает набор токенов: Access token + Refresh token + ID token.
17. Партнер получает Access token — авторизация успешно завершается.
<div>
  <script nonce="csp_nonce" src="https://unpkg.com/@vkid/sdk@<3.0.0/dist-sdk/umd/index.js"></script>
  <script nonce="csp_nonce" type="text/javascript">
    if ('VKIDSDK' in window) {
      const VKID = window.VKIDSDK;

      VKID.Config.init({
        app: 54356531,
        redirectUrl: 'https://апи.гдз-по-фото.рф/api/v1/auth/oauth/vk/callback',
        responseMode: VKID.ConfigResponseMode.Callback,
        source: VKID.ConfigSource.LOWCODE,
        scope: '', // Заполните нужными доступами по необходимости
      });

      const oneTap = new VKID.OneTap();

      oneTap.render({
        container: document.currentScript.parentElement,
        showAlternativeLogin: true
      })
      .on(VKID.WidgetEvents.ERROR, vkidOnError)
      .on(VKID.OneTapInternalEvents.LOGIN_SUCCESS, function (payload) {
        const code = payload.code;
        const deviceId = payload.device_id;

        VKID.Auth.exchangeCode(code, deviceId)
          .then(vkidOnSuccess)
          .catch(vkidOnError);
      });
    
      function vkidOnSuccess(data) {
        // Обработка полученного результата
      }
    
      function vkidOnError(error) {
        // Обработка ошибки
      }
    }
  </script>
</div>