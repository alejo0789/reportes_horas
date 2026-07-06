import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("login_ldap")


def _ldap_host() -> str | None:
    return os.getenv("LDAP_HOST") or None


def _ldap_domain() -> str:
    """Extrae 'lafortuna.local' de 'dc=lafortuna,dc=local'."""
    base_dn = os.getenv("LDAP_BASE_DN", "")
    return ".".join(
        part.split("=")[1]
        for part in base_dn.split(",")
        if part.lower().startswith("dc=")
    )


def autenticar_usuario(email_o_sam: str, password: str) -> bool:
    """
    Valida credenciales contra AD haciendo bind como el usuario.
    Acepta email completo o sAMAccountName — siempre construye UPN limpio:
      joan.londono@empresa.com  ->  joan.londono@lafortuna.local
    """
    host = _ldap_host()
    if not host:
        logger.warning("LDAP no configurado — no se puede autenticar a %s por LDAP", email_o_sam)
        return False

    from ldap3 import Server, Connection, NONE as GET_INFO_NONE
    from ldap3.core.exceptions import LDAPBindError

    port = int(os.getenv("LDAP_PORT", "389"))
    use_ssl = os.getenv("LDAP_USE_SSL", "false").lower() in ("1", "true", "yes")

    sam_account = email_o_sam.split("@")[0]
    upn = f"{sam_account}@{_ldap_domain()}"
    server = Server(host, port=port, use_ssl=use_ssl, get_info=GET_INFO_NONE, connect_timeout=5)

    for attempt in range(2):  # 2 intentos: 1 original + 1 retry con 0.5s de espera
        try:
            conn = Connection(server, user=upn, password=password, auto_bind=True, receive_timeout=4)
            result = conn.bound
            logger.info("LDAP autenticación %s — %s", "exitosa" if result else "fallida", upn)
            return result
        except LDAPBindError:
            logger.warning("LDAP credenciales rechazadas — %s", upn)
            return False
        except Exception as e:
            if attempt == 0:
                logger.warning("LDAP intento 1 fallido para %s: %s — reintentando en 0.5s", upn, e)
                time.sleep(0.5)
            else:
                logger.error("LDAP error definitivo para %s: %s", sam_account, e)
                return False
    return False
