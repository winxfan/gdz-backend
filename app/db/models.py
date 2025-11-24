from sqlalchemy import (
    Column, Text, Numeric, String, DateTime, ForeignKey,
    Boolean, Integer, JSON, func, Enum as SAEnum,
    Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from app.utils import default_uuid

Base = declarative_base()

# Enum types
JobStatusEnum = SAEnum(
    'waiting_payment', 'queued', 'processing', 'done', 'failed',
    name='job_status', native_enum=True
)

TransactionTypeEnum = SAEnum(
    'charge', 'purchase', 'refund', 'promo', 'gateway_payment',
    name='transaction_type', native_enum=True
)

TransactionProviderEnum = SAEnum(
    'yookassa', 'stripe', 'telegram', 'manual',
    name='transaction_provider', native_enum=True
)

TransactionStatusEnum = SAEnum(
    'success', 'failed', 'pending',
    name='transaction_status', native_enum=True
)

TrafficTypeEnum = SAEnum(
    'landing', 'app', 'bot',
    name='traffic_type', native_enum=True
)

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index('ix_users_username', 'username'),
        Index('ix_users_referrer_id', 'referrer_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    anon_user_id = Column(Text, unique=True)
    email = Column(Text, unique=True)
    avatar_url = Column(Text)

    balance_tokens = Column(Numeric(14, 4), default=0)
    ref_code = Column(Text, unique=True)
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='SET NULL'))

    has_left_review = Column(Boolean, default=False)
    consent_pd = Column(Boolean, default=False)
    is_joined_in_channel = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint('slug', name='uq_categories_slug'),
        Index('ix_categories_title', 'title'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    slug = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Format(Base):
    __tablename__ = "formats"
    __table_args__ = (
        UniqueConstraint('code', name='uq_formats_code'),
        Index('ix_formats_code', 'code'),
    )

    # Используем понятный стабильный ключ вместо UUID, чтобы FKs в Model оставались читаемыми
    code = Column(Text, primary_key=True)  # audio | video | image | text | speech | json
    title = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Model(Base):
    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint('name', name='uq_models_name'),
        Index('ix_models_category_id', 'category_id'),
        CheckConstraint("char_length(currency) = 3", name='ck_models_currency_len_3'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    title = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete='SET NULL'), nullable=True)

    cost_unit = Column(Text, default="second")  
    cost_per_unit_tokens = Column(Numeric(14, 4), default=0)
    currency = Column(String(3), default="USD")

    # Форматы вынесены в справочник formats (по коду)
    format_from = Column(Text, ForeignKey("formats.code", ondelete='RESTRICT'), nullable=False)
    format_to = Column(Text, ForeignKey("formats.code", ondelete='RESTRICT'), nullable=False)

    banner_image_url = Column(Text)
    hint = Column(Text)
    max_file_count = Column(Integer, default=1)

    options = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index('ix_transactions_user_created', 'user_id', 'created_at'),
        Index('ix_transactions_user_status_created', 'user_id', 'status', 'created_at'),
        Index('ix_transactions_job_id', 'job_id'),
        CheckConstraint('amount_rub IS NULL OR amount_rub >= 0', name='ck_transactions_amount_nonneg'),
        CheckConstraint("char_length(currency) = 3", name='ck_transactions_currency_len_3'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete='SET NULL'), nullable=True)

    type = Column(TransactionTypeEnum, nullable=False)
    provider = Column(TransactionProviderEnum)
    status = Column(TransactionStatusEnum)
    amount_rub = Column(Numeric(14, 2))
    tokens_delta = Column(Numeric(14, 4))
    currency = Column(String(3), default="RUB")
    plan = Column(Text)
    reference = Column(Text)
    meta = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index('ix_jobs_user_status_created', 'user_id', 'status', 'created_at'),
        Index('ix_jobs_model_created', 'model_id', 'created_at'),
        Index('ix_jobs_is_paid', 'is_paid'),
        Index('ix_jobs_request_id', 'request_id'),
        Index('ix_jobs_input_gin', 'input', postgresql_using='gin'),
        Index('ix_jobs_output_gin', 'output', postgresql_using='gin'),
        CheckConstraint('price_rub IS NULL OR price_rub >= 0', name='ck_jobs_price_nonneg'),
        CheckConstraint('tokens_reserved >= 0', name='ck_jobs_tokens_reserved_nonneg'),
        CheckConstraint('tokens_consumed >= 0', name='ck_jobs_tokens_consumed_nonneg'),
        CheckConstraint('tokens_consumed <= tokens_reserved', name='ck_jobs_tokens_consumed_lte_reserved'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'))
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id", ondelete='SET NULL'), nullable=True)
    request_id = Column(UUID(as_uuid=True), nullable=False, default=default_uuid)

    # Источники и идентификаторы
    anon_user_id = Column(Text)
    order_id = Column(Text, unique=True)
    email = Column(Text)
    generation_source = Column(Text, default="bot")  # bot | site | api
    traffic_type = Column(TrafficTypeEnum)

    # Основная логика
    service_type = Column(Text)       # animate | restore | text_to_image | etc.
    status = Column(JobStatusEnum, default='waiting_payment', nullable=False)

    # Экономика
    price_rub = Column(Numeric(10, 2))
    tokens_reserved = Column(Numeric(14, 4), default=0)
    tokens_consumed = Column(Numeric(14, 4), default=0)
    cost_unit = Column(Text)
    cost_per_unit_tokens = Column(Numeric(14, 4))

    # Контент
    input = Column(JSONB)    # list[IOObject]
    output = Column(JSONB)   # list[IOObject]
    result_url = Column(Text)
    meta = Column(JSONB)

    # Вспомогательные данные
    payment_info = Column(JSONB)
    email_delivery_status = Column(Text, default="not_sent")
    is_ok = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='uq_reviews_user_message'),
        Index('ix_reviews_message_id', 'message_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'))
    message_id = Column(Text)
    reward_given = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint('inviter_id', 'invitee_id', name='uq_referrals_pair'),
        Index('ix_referrals_inviter', 'inviter_id'),
        Index('ix_referrals_invitee', 'invitee_id'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'))
    invitee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'))
    invitee_paid = Column(Boolean, default=False)
    reward_given = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Data(Base):
    __tablename__ = "data"
    __table_args__ = (
        Index('ix_data_expired_in', 'expired_in'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    type = Column(Text, nullable=False)  # image | video | text | audio
    s3_url = Column(Text, nullable=False)
    public_s3_url = Column(Text)
    expired_in = Column(Numeric(20, 0))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    __table_args__ = (
        Index('ix_webhook_logs_event_type', 'event_type'),
        Index('ix_webhook_logs_processed', 'processed'),
        Index('ix_webhook_logs_created_at', 'created_at'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    event_type = Column(Text)
    payload = Column(JSONB)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
