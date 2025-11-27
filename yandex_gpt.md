Использование Yandex GPT через `openai` 2.8.1:

```python
from openai import OpenAI

client = OpenAI(
    api_key=YANDEX_OCR_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project="b1g957vlfr8c7rme0vie",
)

stream = client.responses.create(
    prompt={"id": "fvt83nnd92j82fhqmrvh"},
    input="сюда передаем текст который прочитали с изображения",
    stream=True,
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.error":
        raise RuntimeError(event.error)

final_response = stream.get_final_response()
print(f"\nresponse_id={final_response.id} usage={final_response.usage}")
```
