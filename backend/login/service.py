import os
import secrets
import hmac
import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Response, status
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("login_service")

_SECRET_KEY = os.getenv("SECRET_KEY", "")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")

# Credenciales quemadas (solución temporal — sin BD ni LDAP).
_USUARIO = {
    "id": 1,
    "name": "Dash BETPLAY",
    "email": "Dash_BETPLAY",
    "role_id": None,
}
_USERNAME = "Dash_BETPLAY"
_PASSWORD = "BET_26*_PLAY"


def _generar_jwt(usuario: dict, device_id: str) -> str:
    # Emite un JWT firmado con SECRET_KEY — incluye device_id para binding al navegador.
    # Mismo payload que valida backend/auth.py.
    now = datetime.now(timezone.utc)
    payload = {
        "id": usuario["id"],
        "sub": usuario["email"],
        "name": usuario.get("name", ""),
        "role_id": usuario.get("role_id"),
        "device_id": device_id,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def login(email: str, password: str, response: Response) -> dict:
    """
    Valida contra el usuario quemado y emite un JWT.
    Setea la cookie HttpOnly device_id (mismo origen) para el device binding.
    """
    if not _SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY no configurada en el servidor",
        )

    # compare_digest evita filtrar información por tiempo de comparación.
    usuario_ok = hmac.compare_digest((email or "").strip(), _USERNAME)
    password_ok = hmac.compare_digest(password or "", _PASSWORD)
    if not (usuario_ok and password_ok):
        logger.warning("Login fallido: credenciales inválidas — %s", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    device_id = secrets.token_hex(32)
    jwt_token = _generar_jwt(_USUARIO, device_id)

    # Cookie HttpOnly mismo-origen — auth.py valida device_id contra el claim del JWT.
    response.set_cookie(
        key="device_id",
        value=device_id,
        httponly=True,
        samesite="lax",
        secure=_COOKIE_SECURE,
        max_age=_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    logger.info("Login exitoso (quemado) — %s", _USERNAME)

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "usuario": {
            "id": _USUARIO["id"],
            "name": _USUARIO["name"],
            "email": _USUARIO["email"],
            "role_id": _USUARIO["role_id"],
        },
        "message": "Success",
    }
