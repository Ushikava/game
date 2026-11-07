from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.auth import (
    create_access_token,
    create_refresh_token,
    get_user_from_token,
    require_not_observer,
)
from core.exceptions import BadRequestError, UnauthorizedError
from core.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from db import user as user_db
from db.models import UserData
from db.session import get_db
from models.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ChangeUsernameRequest,
    CreateUserRequest,
    DeleteUserRequest,
    LoginRequest,
    UserOut,
)

pwd_context = CryptContext(schemes=["bcrypt"])

router = APIRouter(tags=["auth"])


@router.get("/users")
def list_users(db: Session = Depends(get_db)):  # noqa: B008
    users = db.query(UserData.id, UserData.username, UserData.role).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: CreateUserRequest, db: Session = Depends(get_db), _: int = Depends(require_not_observer)):  # noqa: B008
    if user_db.get_user_by_username(db, body.username):
        raise BadRequestError("Пользователь с таким именем уже существует")
    hashed = pwd_context.hash(body.password)
    new_user = user_db.create_user(db, body.username, hashed)
    return new_user


@router.post("/login", response_model=AuthResponse)
def user_login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    user = user_db.get_user_by_username(db, body.username)
    if not user:
        raise UnauthorizedError("Неверные учетные данные")
    if user.role != 'observer' and not pwd_context.verify(body.password, user.hashed_password):
        raise UnauthorizedError("Неверные учетные данные")

    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token, expires_at = create_refresh_token()
    current_date = datetime.now(UTC)
    user_db.save_refresh_token(db, user.id, refresh_token, expires_at, current_date)

    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="strict", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="strict", max_age=60*60*24*30)

    return AuthResponse(username=user.username, role=user.role)


@router.post("/refresh", response_model=AuthResponse)
def token_refresh(request: Request, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    rt_value = request.cookies.get("refresh_token")
    if not rt_value:
        raise UnauthorizedError("Refresh token отсутствует")

    rt = user_db.get_refresh_token(db, rt_value)
    if not rt:
        raise UnauthorizedError("Недействительный refresh token")
    if rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        user_db.delete_refresh_token(db, rt_value)
        raise UnauthorizedError("Refresh token истёк")

    user = user_db.get_user_by_id(db, rt.user_id)
    if not user:
        raise UnauthorizedError("Пользователь не найден")

    user_db.delete_refresh_token(db, rt_value)

    access_token = create_access_token(user.id, user.username, user.role)
    new_refresh_token, expires_at = create_refresh_token()
    current_date = datetime.now(UTC)
    user_db.save_refresh_token(db, user.id, new_refresh_token, expires_at, current_date)

    response.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="strict", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie("refresh_token", new_refresh_token, httponly=True, secure=True, samesite="strict", max_age=60*60*24*30)

    return AuthResponse(username=user.username, role=user.role)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):  # noqa: B008
    rt_value = request.cookies.get("refresh_token")
    
    if rt_value:
        user_db.delete_refresh_token(db, rt_value)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    
    return {"status": "ok"}


@router.delete("/users/{username}", status_code=204)
def delete_user(username: str, body: DeleteUserRequest, db: Session = Depends(get_db), _: int = Depends(require_not_observer)):  # noqa: B008
    target = user_db.get_user_by_username(db, username)
    
    if not target:
        raise BadRequestError("Пользователь не найден")
    
    if target.role == "observer":
        raise BadRequestError("Нельзя удалить аккаунт наблюдателя")
    
    if not pwd_context.verify(body.password, target.hashed_password):
        raise UnauthorizedError("Неверный пароль")
    
    user_db.delete_user(db, target.id)


@router.patch("/me/username")
def change_username(body: ChangeUsernameRequest, db: Session = Depends(get_db), user_id: int = Depends(get_user_from_token)):  # noqa: B008
    user = user_db.get_user_by_id(db, user_id)
    
    if not pwd_context.verify(body.password, user.hashed_password):
        raise UnauthorizedError("Неверный пароль")
    
    if user_db.get_user_by_username(db, body.new_username):
        raise BadRequestError("Имя пользователя уже занято")
    
    updated = user_db.update_username(db, user_id, body.new_username)
    return {"username": updated.username}


@router.patch("/me/password")
def change_password(body: ChangePasswordRequest, response: Response, db: Session = Depends(get_db), user_id: int = Depends(get_user_from_token)):  # noqa: B008
    user = user_db.get_user_by_id(db, user_id)
    
    if not pwd_context.verify(body.current_password, user.hashed_password):
        raise UnauthorizedError("Неверный текущий пароль")
    
    new_hash = pwd_context.hash(body.new_password)
    user_db.update_password(db, user_id, new_hash)
    
    user_db.delete_all_refresh_tokens(db, user_id)
    
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return {"status": "ok"}