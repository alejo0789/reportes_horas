import os
import secrets
import logging
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Response, status
from jose import jwt
from dotenv import load_dotenv

from . import db_users, ldap_service
from .security import verify_password

load_dotenv()

logger = logging.getLogger("login_service")

_SECRET_KEY = os.getenv("SECRET_KEY", "")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in ("1", "true", "yes")


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
    Autentica email+password contra per_users (MariaDB) y emite un JWT.
    - ldap=1 → valida contra Active Directory
    - ldap=0 → valida contra bcrypt en per_users
    Setea la cookie HttpOnly device_id (mismo origen) para el device binding.
    """
    if not _SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY no configurada en el servidor",
        )

    usuario = db_users.buscar_usuario_por_email(email)
    if not usuario:
        logger.warning("Login fallido: email no encontrado — %s", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    if usuario.get("id_estado") != 1:
        logger.warning("Login fallido: usuario inactivo — %s", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta de usuario inactiva")

    es_ldap = usuario.get("ldap") == 1
    if es_ldap:
        auth_ok = ldap_service.autenticar_usuario(email, password)
    else:
        auth_ok = verify_password(password, usuario.get("password") or "")

    if not auth_ok:
        logger.warning(
            "Login fallido: credenciales rechazadas (%s) — %s",
            "LDAP" if es_ldap else "bcrypt", email,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    device_id = secrets.token_hex(32)
    jwt_token = _generar_jwt(usuario, device_id)

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

    logger.info(
        "Login exitoso (%s) — user_id=%s email=%s",
        "LDAP" if es_ldap else "bcrypt", usuario["id"], email,
    )

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "usuario": {
            "id": usuario["id"],
            "name": usuario.get("name", ""),
            "email": usuario["email"],
            "role_id": usuario.get("role_id"),
        },
        "message": "Success",
    }
