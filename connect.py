import psycopg2
from psycopg2.extras import DictCursor

from config import POSTGRES_CONFIG


def main() -> None:
    connection = psycopg2.connect(
        host=POSTGRES_CONFIG.get('host', ''),
        port=POSTGRES_CONFIG.get('port', '6432'),
        dbname=POSTGRES_CONFIG.get('database', ''),
        user=POSTGRES_CONFIG.get('user', ''),
        password=POSTGRES_CONFIG.get('password', ''),
        sslmode='verify-full',
        sslrootcert=POSTGRES_CONFIG.get('sslrootcert', ''),
        target_session_attrs='read-write',
        cursor_factory=DictCursor,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()')
            version_row = cursor.fetchone()
            print(version_row[0] if version_row else 'No version returned')
    finally:
        connection.close()


if __name__ == '__main__':
    main()




