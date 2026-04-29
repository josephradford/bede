from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bede_data.config import settings

bearer_scheme = HTTPBearer()


def verify_ingest_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if not settings.ingest_write_token or credentials.credentials != settings.ingest_write_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        )
    return credentials.credentials
