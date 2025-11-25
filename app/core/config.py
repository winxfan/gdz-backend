from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("backend/.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    # Core
    environment: str = Field(default="local")

    # DB / Queue
    database_url: str = Field(default="postgresql://neurolib:neurolib@postgres:5432/neurolibrary", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # S3
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key_id: str | None = Field(default=None, alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str | None = Field(default=None, alias="S3_SECRET_ACCESS_KEY")
    s3_bucket_name: str | None = Field(default=None, alias="S3_BUCKET_NAME")
    s3_region_name: str | None = Field(default=None, alias="S3_REGION_NAME")
    s3_presign_ttl_seconds: int = Field(default=3600, alias="S3_PRESIGN_TTL_SECONDS")
    # S3 key prefixes
    uploads_prefix: str = Field(default="uploads/", alias="UPLOADS_PREFIX")
    videos_prefix: str = Field(default="videos/", alias="VIDEOS_PREFIX")

    # Payments
    yookassa_shop_id: str | None = Field(default=None, alias="YOOKASSA_SHOP_ID")
    yookassa_api_key: str | None = Field(default=None, alias="YOOKASSA_API_KEY")
    yookassa_api_base: str = Field(default="https://api.yookassa.ru", alias="YOOKASSA_API_BASE")
    # Реквизиты для чеков
    yookassa_fallback_receipt_email: str | None = Field(default=None, alias="YOOKASSA_FALLBACK_RECEIPT_EMAIL")
    yookassa_tax_system_code: int = Field(default=1, alias="YOOKASSA_TAX_SYSTEM_CODE")
    yookassa_vat_code: int = Field(default=1, alias="YOOKASSA_VAT_CODE")

    # OAuth
    oauth_yandex_client_id: str | None = Field(default=None, alias="OAUTH_YANDEX_CLIENT_ID")
    oauth_yandex_client_secret: str | None = Field(default=None, alias="OAUTH_YANDEX_CLIENT_SECRET")
    oauth_google_client_id: str | None = Field(default=None, alias="OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str | None = Field(default=None, alias="OAUTH_GOOGLE_CLIENT_SECRET")
    oauth_vk_client_id: str | None = Field(default=None, alias="OAUTH_VK_CLIENT_ID")
    oauth_vk_client_secret: str | None = Field(default=None, alias="OAUTH_VK_CLIENT_SECRET")

    # JWT
    jwt_secret_key: str = Field(default="dev-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=60, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")

    # Email
    smtp_server: str | None = Field(default=None, alias="SMTP_SERVER")
    smtp_port: int | None = Field(default=None, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_email: str | None = Field(default=None, alias="SMTP_EMAIL")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")

    # URLs
    frontend_return_url_base: str | None = Field(default=None, alias="FRONTEND_RETURN_URL_BASE")
    backend_public_base_url: str | None = Field(default=None, alias="BACKEND_PUBLIC_BASE_URL")

    # Yandex Cloud
    yandex_cloud_folder_id: str | None = Field(default=None, alias="YANDEX_CLOUD_FOLDER_ID")
    yandex_ocr_api_key: str | None = Field(default=None, alias="YANDEX_OCR_API_KEY")
    yandex_gpt_api_key: str | None = Field(default=None, alias="YANDEX_GPT_API_KEY")
    yandex_gpt_project_id: str | None = Field(default=None, alias="YANDEX_GPT_PROJECT_ID")
    yandex_gpt_prompt_id: str | None = Field(default=None, alias="YANDEX_GPT_PROMPT_ID")
    yandex_gpt_base_url: str = Field(default="https://rest-assistant.api.cloud.yandex.net/v1", alias="YANDEX_GPT_BASE_URL")

    # FAL.AI
    fal_key: str | None = Field(default=None, alias="FAL_KEY")
    fal_endpoint: str | None = Field(
        default="fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
        alias="FAL_ENDPOINT",
    )
    fal_webhook_token: str | None = Field(default=None, alias="FAL_WEBHOOK_TOKEN")
    # Для обратной ссылки вебхука; если PUBLIC_API_BASE_URL не задан, используем BACKEND_PUBLIC_BASE_URL
    public_api_base_url: str | None = Field(default=None, alias="PUBLIC_API_BASE_URL")
    fal_poll_interval_seconds: int = Field(default=20, alias="FAL_POLL_INTERVAL_SECONDS")

    # Misc
    server_api_key: str | None = Field(default=None, alias="SERVER_API_KEY")

    # Pricing
    usd_to_rub: float = Field(default=100.0, alias="USD_TO_RUB")


settings = Settings()

