import os
import logging
import pymysql
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("login_db_users")

# Query de login (copiada de autenticacion-y-usuarios: buscar_usuario_login.sql)
_BUSCAR_USUARIO_SQL = """
SELECT
    u.id,
    u.name,
    u.email,
    u.password,
    u.id_estado,
    u.ldap,
    ru.role_id
FROM per_users u
LEFT JOIN per_role_user ru ON u.id = ru.user_id
WHERE u.email = %(email)s
"""


def _get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOSTNAME_SAMAN_DEV"),
        port=int(os.getenv("DB_PORTSAMAN_DEV", "3306")),
        user=os.getenv("DB_USERNAME_SAMAN_DEV"),
        password=os.getenv("DB_PASSWORD_SAMAN_DEV"),
        database=os.getenv("DB_NAME_SAMAN_DEV"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=8,
        read_timeout=8,
    )


def buscar_usuario_por_email(email: str) -> dict | None:
    """Busca el usuario en per_users por email para el flujo de login."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_BUSCAR_USUARIO_SQL, {"email": email})
            return cur.fetchone()
    finally:
        conn.close()
