from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from config import POSTGRES_CONFIG

# Получаем список хостов
hosts = POSTGRES_CONFIG['host'].split(',')
# Формируем URL для каждого хоста
database_urls = [
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{host}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
    for host in hosts
]

# Путь к сертификату
SSL_ROOT_CERT_PATH = POSTGRES_CONFIG.get("sslrootcert", "/certs/root.crt")

# Создание движка с поддержкой SSL и явным указанием подключения к мастер-узлу
engine = create_engine(
    database_urls[0],  # Используем первый хост
    connect_args={
        "sslmode": "verify-full",
        "sslrootcert": SSL_ROOT_CERT_PATH,
        "target_session_attrs": "primary",  # Явно указываем, что хотим подключиться к мастер-узлу
        "application_name": "visual_search_public_api",  # Обновленное имя приложения
        "connect_timeout": 30,  # Увеличиваем таймаут подключения
        "keepalives_idle": 600,  # TCP keepalive
        "keepalives_interval": 30,
        "keepalives_count": 3
    },
    poolclass=QueuePool,
    pool_size=10,  # Увеличиваем размер пула
    max_overflow=20,  # Увеличиваем максимальное переполнение
    pool_timeout=60,  # Увеличиваем таймаут пула
    pool_recycle=3600,  # Увеличиваем время жизни соединения
    pool_pre_ping=True,  # Проверка соединений перед использованием
    echo=False,
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()