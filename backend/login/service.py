import hmac
import logging
from fastapi import HTTPException, status

logger = logging.getLogger("login_service")

# Credenciales quemadas (solución temporal — sin BD, LDAP, JWT ni cookies).
_USERNAME = "Dash_BETPLAY"
_PASSWORD = "BET_26*_PLAY"


def login(email: str, password: str) -> dict:
    """
    Valida contra el usuario quemado. No emite token ni setea cookies:
    el control de acceso es únicamente el login de usuario/contraseña.
    """
    # compare_digest evita filtrar información por tiempo de comparación.
    usuario_ok = hmac.compare_digest((email or "").strip(), _USERNAME)
    password_ok = hmac.compare_digest(password or "", _PASSWORD)
    if not (usuario_ok and password_ok):
        logger.warning("Login fallido: credenciales inválidas — %s", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    logger.info("Login exitoso — %s", _USERNAME)
    return {"message": "Success"}
