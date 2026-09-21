"""Domain and service-level exceptions for the PARAKH application.

Isolates raw database and ORM errors from reaching API consumers.
"""


class ServiceError(Exception):
    """Base exception for all domain service errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EntityNotFoundError(ServiceError):
    """Raised when a requested entity does not exist."""

    pass


class DuplicateEntityError(ServiceError):
    """Raised when an operation would violate entity uniqueness constraints."""

    pass


class InvalidStateTransitionError(ServiceError):
    """Raised when an illegal status/state lifecycle transition is requested."""

    pass


class ValidationError(ServiceError):
    """Raised when business logic validation constraints are violated."""

    pass


class ConsentRequiredError(ServiceError):
    """Raised when an operation lacks valid, active applicant consent."""

    pass

