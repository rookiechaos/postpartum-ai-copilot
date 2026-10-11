"""
Authentication Service - User authentication and authorization
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.database import UserDB, TwoFactorAuthDB
from models.schemas import User, UserCreate, TokenData
from config.settings import get_settings
from exceptions import ValidationError
import secrets

# Password hashing
# Use pbkdf2_sha256 to avoid bcrypt version compatibility issues
# bcrypt has 72 byte limit and version detection issues in some environments
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# JWT Configuration - Now loaded from Settings in AuthService.__init__


class AuthService:
    """Authentication service for user management"""
    
    def __init__(self):
        settings = get_settings()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire = settings.access_token_expire_minutes
        self.refresh_token_expire = settings.refresh_token_expire_days
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        try:
            # Truncate password if too long for bcrypt
            if len(plain_password.encode('utf-8')) > 72:
                plain_password = plain_password[:72]
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            # Log error but don't print to console (security best practice)
            from services.logging_service import logger
            logger.log_error(e, context={"action": "password_verification"})
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        # Bcrypt has a 72 byte limit, truncate if necessary
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    
    def create_user(self, user_data: UserCreate, db: Session) -> User:
        """
        Create a new user
        
        Args:
            user_data: User creation data
            db: Database session
        
        Returns:
            Created user
        """
        try:
            # Check if user already exists
            existing_user = db.query(UserDB).filter(
                UserDB.email == user_data.email
            ).first()
            
            if existing_user:
                raise ValidationError("User with this email already exists")
            
            # Public signup cannot select an identity, including a provisioned
            # administrator ID. Legacy user_id input is deliberately ignored.
            user_id = f"user_{secrets.token_urlsafe(24)}"
            while db.query(UserDB).filter(UserDB.user_id == user_id).first():
                user_id = f"user_{secrets.token_urlsafe(24)}"
            
            # Create user
            hashed_password = self.get_password_hash(user_data.password)
            db_user = UserDB(
                user_id=user_id,
                email=user_data.email,
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            return User(
                id=db_user.id,
                user_id=db_user.user_id,
                email=db_user.email,
                is_active=db_user.is_active,
                created_at=db_user.created_at
            )
        except Exception as e:
            db.rollback()
            raise
    
    def authenticate_user(self, email: str, password: str, db: Session) -> Optional[User]:
        """
        Authenticate a user
        
        Args:
            email: User email
            password: User password
            db: Database session
        
        Returns:
            User if authenticated, None otherwise
        """
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            return None
        
        if not self.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        return User(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
        
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token
        
        Args:
            data: Data to encode in token
        
        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def get_two_factor_version(self, user_id: str, db: Session) -> Optional[str]:
        """Bind second-factor proof to the currently enabled authenticator."""
        factor = db.query(TwoFactorAuthDB).filter(
            TwoFactorAuthDB.user_id == user_id,
            TwoFactorAuthDB.is_enabled == True,
        ).first()
        if not factor:
            return None
        if not factor.secret_key:
            raise ValidationError("Two-factor authentication is unavailable")
        return hashlib.sha256(factor.secret_key.encode()).hexdigest()

    def verify_token(self, token: str, token_type: str = "access", db: Optional[Session] = None) -> Optional[TokenData]:
        """
        Verify a JWT token
        
        Args:
            token: JWT token to verify
            token_type: Type of token (access or refresh)
        
        Returns:
            TokenData if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            
            if user_id is None:
                return None
            mfa_version = payload.get("mfa_version")
            if db is not None:
                expected_version = self.get_two_factor_version(user_id, db)
                if mfa_version != expected_version:
                    return None
            return TokenData(user_id=user_id, email=email, mfa_version=mfa_version)
        except JWTError:
            return None
    
    def get_user_by_id(self, user_id: str, db: Session) -> Optional[User]:
        """Get user by user_id"""
        user = db.query(UserDB).filter(UserDB.user_id == user_id).first()
        if not user:
            return None
        
        return User(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )
    
    def get_user_by_email(self, email: str, db: Session) -> Optional[User]:
        """Get user by email"""
        user = db.query(UserDB).filter(UserDB.email == email).first()
        if not user:
            return None
        
        return User(
            id=user.id,
            user_id=user.user_id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at
        )

