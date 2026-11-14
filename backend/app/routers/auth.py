from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import httpx
from app.database import get_db
from app.models.user import User
from app.schemas.auth import GoogleAuthRequest, TokenResponse, UserOut
from app.utils.helpers import create_access_token, get_current_user, get_or_create_dev_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Verifies Google ID token, creates or updates user in DB, returns JWT.
    If testing locally with a mock or invalid token, falls back gracefully to demo user.
    """
    email = None
    name = "User"
    avatar = None

    if req.id_token and req.id_token != "mock-token":
        try:
            # Verify with Google OAuth tokeninfo endpoint
            async with httpx.AsyncClient() as client:
                res = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={req.id_token}")
                if res.status_code == 200:
                    data = res.json()
                    email = data.get("email")
                    name = data.get("name", name)
                    avatar = data.get("picture")
        except Exception:
            pass

    if not email:
        # Fallback to dev user for smooth local hackathon flow
        user = await get_or_create_dev_user(db)
        token = create_access_token({"sub": user.id, "email": user.email})
        return TokenResponse(access_token=token, user=UserOut.model_validate(user))

    # Query or create user
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        user = User(email=email, name=name, avatar_url=avatar)
        db.add(user)
    else:
        user.name = name
        user.avatar_url = avatar
        user.last_login = datetime.utcnow()

    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the currently authenticated user's profile.
    """
    return UserOut.model_validate(current_user)

@router.post("/dev-login", response_model=TokenResponse)
async def dev_login(db: AsyncSession = Depends(get_db)):
    """
    Convenience endpoint for local testing: issues a valid JWT for the dev persona.
    """
    user = await get_or_create_dev_user(db)
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))
