"""
Authentication API Routes - User authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from models.schemas import User, UserCreate, UserLogin, Token, RefreshTokenRequest
from middleware.auth import get_current_user
from dependencies.database import get_db
from dependencies.container import get_container
from middleware.rate_limit import rate_limit, RATE_LIMITS

router = APIRouter(prefix="/api/auth", tags=["auth"])
container = get_container()
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
@rate_limit(RATE_LIMITS["auth"])
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user
    
    Args:
        user_data: User registration data
        db: Database session
    
    Returns:
        Created user (without password)
    """
    try:
        auth_service = container.get("auth_service")
        user = auth_service.create_user(user_data, db)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Don't leak sensitive information in error messages
        from config.settings import get_settings
        settings = get_settings()
        
        error_detail = "Failed to create user"
        if settings.debug:
            error_detail = f"Failed to create user: {str(e)}"
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.post("/login", response_model=Token)
@rate_limit(RATE_LIMITS["auth"])
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Login and get access token
    
    Args:
        credentials: User login credentials
        request: Request object (for IP and user agent)
        db: Database session
    
    Returns:
        Access token and refresh token
    """
    auth_service = container.get("auth_service")
    device_service = container.get("device_service")
    two_fa_service = container.get("two_factor_auth_service")
    
    user = auth_service.authenticate_user(credentials.email, credentials.password, db)
    
    # Log login attempt
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    
    if not user:
        # Log failed login
        device_service.log_login(
            user_id=credentials.email,  # Use email as identifier for failed logins
            ip_address=ip_address,
            user_agent=user_agent,
            login_method="password",
            success=False,
            failure_reason="Invalid credentials",
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if 2FA is enabled
    two_fa_status = two_fa_service.get_2fa_status(user.user_id, db)
    mfa_version = None
    if two_fa_status.get("is_enabled", False):
        if not credentials.verification_token:
            return Token(requires_2fa=True)
        mfa_version = auth_service.get_two_factor_version(user.user_id, db)
        if not mfa_version:
            raise HTTPException(status_code=401, detail="Please sign in again")
        if not two_fa_service.verify_2fa(user.user_id, credentials.verification_token, db):
            device_service.log_login(
                user_id=user.user_id, ip_address=ip_address, user_agent=user_agent,
                login_method="2fa", success=False,
                failure_reason="Invalid second factor", db=db,
            )
            raise HTTPException(status_code=401, detail="Invalid two-factor authentication code")
        if mfa_version != auth_service.get_two_factor_version(user.user_id, db):
            raise HTTPException(status_code=401, detail="Please sign in again")
    
    # Register device
    device = device_service.register_device(
        user_id=user.user_id,
        user_agent=user_agent,
        ip_address=ip_address,
        db=db
    )
    
    # Log successful login
    device_service.log_login(
        user_id=user.user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info={"device_id": device.get("device_id")},
        login_method="2fa" if mfa_version else "password",
        success=True,
        db=db
    )
    
    token_claims = {"sub": user.user_id, "email": user.email, "mfa_version": mfa_version}
    # Create access token only after all required factors have passed.
    access_token_expires = timedelta(minutes=auth_service.access_token_expire)
    access_token = auth_service.create_access_token(
        data=token_claims,
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = auth_service.create_refresh_token(
        data=token_claims
    )
    
    response = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        requires_2fa=False
    )
    
    return response


@router.post("/refresh", response_model=Token)
@rate_limit(RATE_LIMITS["auth"])
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token from JSON body or Authorization header.
    """
    token = None
    if credentials:
        token = credentials.credentials
    elif body.refresh_token:
        token = body.refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth_service = container.get("auth_service")
    token_data = auth_service.verify_token(token, token_type="refresh", db=db)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(token_data.user_id, db)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    token_claims = {"sub": user.user_id, "email": user.email, "mfa_version": token_data.mfa_version}
    # Preserve verified factors when refreshing the session.
    access_token_expires = timedelta(minutes=auth_service.access_token_expire)
    access_token = auth_service.create_access_token(
        data=token_claims,
        expires_delta=access_token_expires
    )
    
    # Create new refresh token
    new_refresh_token = auth_service.create_refresh_token(
        data=token_claims
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=new_refresh_token
    )


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    
    Returns:
        Current authenticated user
    """
    return current_user

