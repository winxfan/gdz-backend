```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE job_status AS ENUM ('waiting_payment', 'queued', 'processing', 'done', 'failed');
CREATE TYPE transaction_type AS ENUM ('charge', 'purchase', 'refund', 'promo', 'gateway_payment');
CREATE TYPE transaction_provider AS ENUM ('yookassa', 'stripe', 'telegram', 'manual');
CREATE TYPE transaction_status AS ENUM ('success', 'failed', 'pending');
CREATE TYPE traffic_type AS ENUM ('landing', 'app', 'bot');

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip TEXT,
    username TEXT,
    avatar_id INTEGER,
    anon_user_id TEXT UNIQUE,
    email TEXT UNIQUE,
    social_id TEXT UNIQUE,
    avatar_url TEXT,
    is_accepted_promo BOOLEAN DEFAULT FALSE,
    balance_tokens NUMERIC(14,4) DEFAULT 5,
    tokens_used_as_anon INTEGER DEFAULT 0,
    is_authorized BOOLEAN DEFAULT FALSE,
    consent_pd BOOLEAN DEFAULT FALSE,
    is_joined_in_channel BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_ip ON users (ip);

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    model_id UUID,
    request_id UUID NOT NULL DEFAULT uuid_generate_v4(),
    anon_user_id TEXT,
    order_id TEXT UNIQUE,
    input_s3_url TEXT,
    input_mime_type TEXT,
    status job_status NOT NULL DEFAULT 'waiting_payment',
    ocr_operation_id TEXT,
    ocr_status TEXT,
    gpt_response_id TEXT,
    tokens_reserved NUMERIC(14,4) DEFAULT 0,
    tokens_consumed NUMERIC(14,4) DEFAULT 0,
    detected_text TEXT,
    generated_text TEXT,
    error_message TEXT,
    payment_info JSONB,
    pipeline_meta JSONB,
    is_ok BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (tokens_reserved >= 0),
    CHECK (tokens_consumed >= 0),
    CHECK (tokens_consumed <= tokens_reserved)
);
CREATE INDEX ix_jobs_request_id ON jobs (request_id);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    type transaction_type NOT NULL,
    provider transaction_provider,
    status transaction_status,
    amount_rub NUMERIC(14,2),
    tokens_delta NUMERIC(14,4),
    currency CHAR(3) DEFAULT 'RUB',
    plan TEXT,
    reference TEXT,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (amount_rub IS NULL OR amount_rub >= 0),
    CHECK (char_length(currency) = 3)
);
CREATE INDEX ix_transactions_user_created ON transactions (user_id, created_at);
CREATE INDEX ix_transactions_user_status_created ON transactions (user_id, status, created_at);
CREATE INDEX ix_transactions_job_id ON transactions (job_id);

CREATE TABLE data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL,
    s3_url TEXT NOT NULL,
    public_s3_url TEXT,
    expired_in NUMERIC(20,0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_data_expired_in ON data (expired_in);

CREATE TABLE webhook_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT,
    payload JSONB,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_webhook_logs_event_type ON webhook_logs (event_type);
CREATE INDEX ix_webhook_logs_processed ON webhook_logs (processed);
CREATE INDEX ix_webhook_logs_created_at ON webhook_logs (created_at);
```

