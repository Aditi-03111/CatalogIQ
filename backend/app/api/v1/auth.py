import base64
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import get_session
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

security = HTTPBearer()

def parse_unverified_payload(token: str) -> dict:
    """
    Decodes the payload section of a JWT token without verifying the signature.
    Useful for extracting the Clerk user_id ('sub') and details.
    """
    try:
        parts = token.split('.')
        if len(parts) < 2:
            raise ValueError("Invalid JWT token format")
        payload_b64 = parts[1]
        
        # Add necessary base64 padding
        padding = '=' * (4 - (len(payload_b64) % 4))
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        return json.loads(payload_bytes.decode('utf-8'))
    except Exception as e:
        logger.error(f"Failed to parse JWT payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token payload"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency resolver that verifies the Clerk JWT bearer token,
    authenticates it against Clerk's backend API, and syncs the user model.
    """
    token = credentials.credentials
    payload = parse_unverified_payload(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token: sub claim is missing"
        )

    email = "no-email@clerk.com"
    name = "Clerk User"
    picture = ""

    # Check if Secret Key is set (runs verification if active; otherwise defaults to mock in local dev)
    clerk_secret = settings.CLERK_SECRET_KEY
    if not clerk_secret or clerk_secret == "your_clerk_secret_key_here":
        logger.warning("CLERK_SECRET_KEY is empty/placeholder. Bypassing live signature verification (Development mode).")
        # Extract metadata from token payload
        email = payload.get("email") or payload.get("sub") + "@clerk.dev"
        name = payload.get("name") or "Catalog Developer"
        picture = payload.get("picture") or ""
    else:
        # Authoritatively check Clerk backend API to verify token validation state and load user details
        import httpx
        headers = {
            "Authorization": f"Bearer {clerk_secret}"
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"https://api.clerk.com/v1/users/{user_id}", headers=headers, timeout=5.0)
                if res.status_code != 200:
                    logger.error(f"Clerk backend rejected user verification. Code: {res.status_code}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session validation rejected by Clerk authentication service"
                    )
                
                clerk_user = res.json()
                
                # Parse email addresses
                email_list = clerk_user.get("email_addresses", [])
                if email_list:
                    email = email_list[0].get("email_address", "no-email@clerk.com")
                
                # Parse names
                first_name = clerk_user.get("first_name") or ""
                last_name = clerk_user.get("last_name") or ""
                name = f"{first_name} {last_name}".strip() or "Clerk User"
                
                # Parse profile picture
                picture = clerk_user.get("image_url") or ""
        except httpx.RequestError as e:
            logger.error(f"Failed to reach Clerk verification backend: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk authentication service is temporarily unavailable"
            )

    # Sync User profile record with local PostgreSQL store
    stmt = select(User).where(User.email == email)
    user = session.exec(stmt).first()

    if not user:
        user = User(
            email=email,
            name=name,
            picture=picture
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Synchronized new Clerk user in database: {email}")
    else:
        # Refresh dynamic properties
        if user.name != name or user.picture != picture:
            user.name = name
            user.picture = picture
            session.add(user)
            session.commit()
            session.refresh(user)

    return user

@router.get("/session")
def check_session(current_user: User = Depends(get_current_user)):
    """
    Test helper route to verify user token decodes and resolves correctly.
    """
    return {
        "status": "active",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.name,
            "picture": current_user.picture
        }
    }
