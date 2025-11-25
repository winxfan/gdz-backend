подключиться к yandex gpt

import openai

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project="b1g957vlfr8c7rme0vie"
)

with client.responses.stream(
        prompt={
            "id": "fvt83nnd92j82fhqmrvh",
        },
        input="сюда передаем текст который прочитали с изображения",
) as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
