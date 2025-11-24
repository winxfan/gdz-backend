import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки PostgreSQL
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', ''),
    'port': os.getenv('POSTGRES_PORT', '6432'),
    'database': os.getenv('POSTGRES_DB', 'visual-search'),
    'user': os.getenv('POSTGRES_USER', 'danya'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    # В контейнерах по умолчанию ожидаем сертификат по пути /certs/root.crt (см. docker-compose.yml)
    'sslrootcert': os.getenv('POSTGRES_SSLROOTCERT', '/certs/root.crt'),
}

# Настройки Yandex S3
S3_CONFIG = {
    'endpoint_url': os.getenv('S3_ENDPOINT_URL', ''),
    'aws_access_key_id': os.getenv('S3_ACCESS_KEY_ID', ''),
    'aws_secret_access_key': os.getenv('S3_SECRET_ACCESS_KEY', ''),
    'bucket_name': os.getenv('S3_BUCKET_NAME', ''),
    'region_name': os.getenv('S3_REGION_NAME', 'ru-central1'),
}

# Настройки SMTP для Yandex
SMTP_CONFIG = {
    'server': os.getenv('SMTP_SERVER', 'smtp.yandex.ru'),
    'port': os.getenv('SMTP_PORT', '465'),
    'username': os.getenv('SMTP_USERNAME', ''),
    'password': os.getenv('SMTP_PASSWORD', ''),
}

# Настройки приложения
APP_CONFIG = {
    'frontend_url': os.getenv('FRONTEND_URL', 'https://xn--b1ahgb0aea5aq.online'),
    'api_url': os.getenv('API_URL', 'http://localhost:8000'),
}

# Публичные URL-ы приложения (из .env)
APP_PUBLIC_CONFIG = {
    'frontend_return_url_base': os.getenv('FRONTEND_RETURN_URL_BASE', ''),
    'backend_public_base_url': os.getenv('BACKEND_PUBLIC_BASE_URL', ''),
}

# Секреты вебхуков (из .env)
WEBHOOK_CONFIG = {
    'fal_webhook_secret': os.getenv('FAL_WEBHOOK_SECRET', ''),
}

# OAuth провайдеры (из .env)
OAUTH_CONFIG = {
    'google': {
        'client_id': os.getenv('OAUTH_GOOGLE_CLIENT_ID', ''),
        'client_secret': os.getenv('OAUTH_GOOGLE_CLIENT_SECRET', ''),
    },
    'vk': {
        'client_id': os.getenv('OAUTH_VK_CLIENT_ID', ''),
        'client_secret': os.getenv('OAUTH_VK_CLIENT_SECRET', ''),
    },
    'yandex': {
        'client_id': os.getenv('OAUTH_YANDEX_CLIENT_ID', ''),
        'client_secret': os.getenv('OAUTH_YANDEX_CLIENT_SECRET', ''),
    },
}

# JWT (из .env)
JWT_CONFIG = {
    'secret_key': os.getenv('JWT_SECRET_KEY', ''),
    'algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
    'access_token_expire_minutes': int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '60')),
}

# Настройки RabbitMQ
RABBITMQ_CONFIG = {
    'host': os.getenv('RABBITMQ_HOST', 'rabbitmq'),
    'port': os.getenv('RABBITMQ_PORT', '5672'),
    'user': os.getenv('RABBITMQ_USER', 'guest'),
    'password': os.getenv('RABBITMQ_PASSWORD', 'guest'),
    'vhost': os.getenv('RABBITMQ_VHOST', '/'),
}

# Настройки Redis
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'redis'),
    'port': os.getenv('REDIS_PORT', '6379'),
    'db': os.getenv('REDIS_DB', '0'),
}

# Настройки Celery
CELERY_CONFIG = {
    'broker_url': f"amqp://{RABBITMQ_CONFIG['user']}:{RABBITMQ_CONFIG['password']}@{RABBITMQ_CONFIG['host']}:{RABBITMQ_CONFIG['port']}/{RABBITMQ_CONFIG['vhost']}",
    'result_backend': f"redis://{REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}/{REDIS_CONFIG['db']}",
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'timezone': 'UTC',
    'enable_utc': True,
    'task_track_started': True,
    'task_time_limit': 3600 * 24,  # 24 часа
    'worker_max_tasks_per_child': 1,
    'worker_prefetch_multiplier': 1,
}

# Настройки шифрования
ENCRYPTION_CONFIG = {
    'key': os.getenv('ENCRYPTION_KEY', 'dGhpc2lzYXRlc3RrZXlmb3JkZXZlbG9wbWVudA=='),  # Временный ключ для разработки
    'algorithm': 'AES-256-CBC',
}

# Настройки Triton Inference Server
TRITON_CONFIG = {
    'url': os.getenv('TRITON_URL', 'http://localhost:8000'),
    'model_name': os.getenv('TRITON_MODEL_NAME', 'yolov8'),
    'model_version': os.getenv('TRITON_MODEL_VERSION', '1'),
    'timeout_seconds': int(os.getenv('TRITON_TIMEOUT_SECONDS', '30')),
    'input_name': os.getenv('TRITON_INPUT_NAME', 'images'),
    'output_name': os.getenv('TRITON_OUTPUT_NAME', 'output0'),
    'input_width': int(os.getenv('TRITON_INPUT_WIDTH', '640')),
    'input_height': int(os.getenv('TRITON_INPUT_HEIGHT', '640')),
    'conf_threshold': float(os.getenv('TRITON_CONF_THRESHOLD', '0.25')),
    'iou_threshold': float(os.getenv('TRITON_IOU_THRESHOLD', '0.45')),
}

# Настройки Triton для CLIP (эмбеддинги)
TRITON_CLIP_CONFIG = {
    'url': os.getenv('TRITON_URL', 'http://localhost:8000'),
    'model_name': os.getenv('TRITON_CLIP_MODEL_NAME', 'clip-vit-b32'),
    'model_version': os.getenv('TRITON_CLIP_MODEL_VERSION', '1'),
    'timeout_seconds': int(os.getenv('TRITON_TIMEOUT_SECONDS', '30')),
    'input_name': os.getenv('TRITON_CLIP_INPUT_NAME', 'pixel_values'),
    'output_name': os.getenv('TRITON_CLIP_OUTPUT_NAME', 'image_embeds'),
    'input_size': int(os.getenv('TRITON_CLIP_INPUT_SIZE', '224')),
}