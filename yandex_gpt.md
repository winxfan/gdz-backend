Использование Yandex GPT через `openai` 2.8.1:

```python
from openai import OpenAI

client = OpenAI(
    api_key=YANDEX_OCR_API_KEY,
    base_url="https://rest-assistant.api.cloud.yandex.net/v1",
    project="b1g957vlfr8c7rme0vie",
)

response = client.responses.create(
    prompt={"id": "fvt83nnd92j82fhqmrvh"},
    input="сюда передаем текст который прочитали с изображения",
)

print(response.output_text.strip())
print(f"response_id={response.id} usage={response.usage}")
```
