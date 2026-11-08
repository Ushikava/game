from fastapi import APIRouter, Depends, status

from db.models import User
from models.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from models.users import UserOut
from routers.dependencies import AuthServiceDep, limit_login, limit_register

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_register)],
)
async def register(body: RegisterRequest, auth_service: AuthServiceDep) -> User:
    return await auth_service.register(body.username, body.password)


@router.post("/login", dependencies=[Depends(limit_login)])
async def login(body: LoginRequest, auth_service: AuthServiceDep) -> TokenPair:
    return await auth_service.login(body.username, body.password)


@router.post("/refresh")
async def refresh(body: RefreshRequest, auth_service: AuthServiceDep) -> TokenPair:
    return await auth_service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.logout(body.refresh_token)
