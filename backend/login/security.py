import logging
import bcrypt as _bcrypt

logger = logging.getLogger("login_security")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # $2y$ es el prefijo PHP; Python espera $2b$ — son equivalentes pero checkpw
    # falla sin la sustitución.
    try:
        if hashed_password.startswith("$2y$"):
            hashed_password = "$2b$" + hashed_password[4:]
        return _bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error("verify_password error — %s: %s", type(e).__name__, e)
        return False
