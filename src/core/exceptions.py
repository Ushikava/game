from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    detail: str = "Внутренняя ошибка сервера"


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, resource: str = "Объект"):
        self.detail = f"{resource} не найден"


class ForbiddenError(AppError):
    status_code = 403

    def __init__(self, detail: str = "Недостаточно прав"):
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400

    def __init__(self, detail: str = "Некорректный запрос"):
        self.detail = detail


class UnauthorizedError(AppError):
    status_code = 401

    def __init__(self, detail: str = "Не авторизован"):
        self.detail = detail


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})