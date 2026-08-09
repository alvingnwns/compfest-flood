from typing import Any


class DomainError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


def not_found(resource: str, resource_id: str) -> DomainError:
    return DomainError(
        status_code=404,
        code=f"{resource}_not_found",
        message=f"{resource.replace('_', ' ').capitalize()} not found.",
        details={f"{resource}Id": resource_id},
    )


def conflict(code: str, message: str, details: dict[str, Any] | None = None) -> DomainError:
    return DomainError(status_code=409, code=code, message=message, details=details)
