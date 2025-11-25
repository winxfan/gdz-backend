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
        Index('ix_users_email', 'email'),
        Index('ix_users_ip', 'ip'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=default_uuid)
    ip = Column(Text)
    username = Column(Text)
    avatar_id = Column(Integer)
    anon_user_id = Column(Text, unique=True)
    email = Column(Text, unique=True)
    social_id = Column(Text, unique=True)
    avatar_url = Column(Text)
    is_accepted_promo = Column(Boolean, default=False)

    balance_tokens = Column(Numeric(14, 4), default=5)
    tokens_used_as_anon = Column(Integer, default=0)
    is_authorized = Column(Boolean, default=False)

    consent_pd = Column(Boolean, default=False)
    is_joined_in_channel = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
        Index('ix_jobs_request_id', 'request_id'),
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
    input_s3_url = Column(Text)
    input_mime_type = Column(Text)

    # Основная логика
    status = Column(JobStatusEnum, default='waiting_payment', nullable=False)
    ocr_operation_id = Column(Text)
    ocr_status = Column(Text)
    gpt_response_id = Column(Text)

    # Экономика
    tokens_reserved = Column(Numeric(14, 4), default=0)
    tokens_consumed = Column(Numeric(14, 4), default=0)

    # Контент
    detected_text = Column(Text)
    generated_text = Column(Text)
    error_message = Column(Text)

    # Вспомогательные данные
    payment_info = Column(JSONB)
    pipeline_meta = Column(JSONB)
    is_ok = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
