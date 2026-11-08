from typing import ClassVar

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: ClassVar[int] = 500
    default_detail: ClassVar[str] = "Внутренняя ошибка сервера"
    default_headers: ClassVar[dict[str, str] | None] = None

    def __init__(self, detail: str | None = None, headers: dict[str, str] | None = None):
        self.detail = detail or self.default_detail
        self.headers = headers or self.default_headers
        super().__init__(self.detail)


class BadRequestError(AppError):
    status_code = 400
    default_detail = "Некорректный запрос"


class UnauthorizedError(AppError):
    status_code = 401
    default_detail = "Не авторизован"
    default_headers: ClassVar[dict[str, str] | None] = {"WWW-Authenticate": "Bearer"}


class ForbiddenError(AppError):
    status_code = 403
    default_detail = "Недостаточно прав"


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, resource: str = "Объект"):
        super().__init__(f"{resource} не найден")


class ConflictError(AppError):
    status_code = 409
    default_detail = "Конфликт данных"


class ServiceUnavailableError(AppError):
    status_code = 503
    default_detail = "Сервер перегружен, попробуйте позже"


class TooManyRequestsError(AppError):
    status_code = 429
    default_detail = "Слишком много попыток, попробуйте позже"

    def __init__(self, retry_after_seconds: int):
        super().__init__(headers={"Retry-After": str(retry_after_seconds)})


# ------------------------------


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
