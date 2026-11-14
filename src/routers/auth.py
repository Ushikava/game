from fastapi import APIRouter, Depends, status

from db.models import User
from routers.dependencies import AuthServiceDep, ClientIp, limit_register
from schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from schemas.users import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_register)],
)
async def register(body: RegisterRequest, auth_service: AuthServiceDep) -> User:
    return await auth_service.register(body.username, body.password)


@router.post("/login")
async def login(body: LoginRequest, ip: ClientIp, auth_service: AuthServiceDep) -> TokenPair:
    return await auth_service.login(body.username, body.password, ip)


@router.post("/refresh")
async def refresh(body: RefreshRequest, auth_service: AuthServiceDep) -> TokenPair:
    return await auth_service.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshRequest, auth_service: AuthServiceDep) -> None:
    await auth_service.logout(body.refresh_token)
