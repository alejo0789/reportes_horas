import os
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

# SECRET_KEY debe ser idéntica a la de api-gestion-usuarios — es lo que valida la firma del JWT
_SECRET_KEY = os.getenv("SECRET_KEY", "")
_ALGORITHM  = "HS256"
_bearer     = HTTPBearer()


class CurrentUser(BaseModel):
    """Payload extraído del JWT emitido por api-gestion-usuarios."""
    id:      int
    email:   str
    name:    str
    role_id: int | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> CurrentUser:
    """
    Dependencia FastAPI — valida el JWT emitido por api-gestion-usuarios.
    No hace consultas a BD; toda la validación es local con SECRET_KEY.

    Uso: current_user: CurrentUser = Depends(get_current_user)
    """
    if not _SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY no configurada en el servidor",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token JWT inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("id")
    email   = payload.get("sub")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token con payload incompleto",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=user_id,
        email=email,
        name=payload.get("name", ""),
        role_id=payload.get("role_id"),
    )
