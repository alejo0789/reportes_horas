from pydantic import BaseModel


class CurrentUser(BaseModel):
    """Usuario fijo — autenticación simplificada sin JWT."""
    id:      int = 1
    email:   str = "Dash_BETPLAY"
    name:    str = "Dash BETPLAY"
    role_id: int | None = None


def get_current_user() -> CurrentUser:
    """
    Dependencia FastAPI — autenticación simplificada.

    No hay JWT ni cookies: el acceso se controla en el frontend con el login
    de usuario/contraseña quemados. Los endpoints mantienen la firma
    `Depends(get_current_user)` para no tener que modificarlos uno a uno.
    """
    return CurrentUser()
