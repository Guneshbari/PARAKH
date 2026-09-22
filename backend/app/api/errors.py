"""Centralized exception handlers mapping domain exceptions to standard HTTP responses."""
import logging
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.assessment.exceptions import (
    AssessmentEngineError,
    AssessmentInputError,
    AssessmentNotImplementedError,
    AssessmentOutputError,
)
from app.services.exceptions import (
    AuditLoggingError,
    AuthenticationError,
    AuthorizationError,
    ConsentRequiredError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    ServiceError,
    ValidationError as ServiceValidationError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain, engine, and unhandled exception handlers onto the FastAPI application."""

    @app.exception_handler(EntityNotFoundError)
    async def handle_entity_not_found(request: Request, exc: EntityNotFoundError) -> JSONResponse:
        logger.info(f"Entity not found: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message},
        )

    @app.exception_handler(DuplicateEntityError)
    async def handle_duplicate_entity(request: Request, exc: DuplicateEntityError) -> JSONResponse:
        logger.info(f"Duplicate entity conflict: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(InvalidStateTransitionError)
    async def handle_invalid_state_transition(
        request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        logger.info(f"Invalid state transition: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message},
        )

    @app.exception_handler(ConsentRequiredError)
    async def handle_consent_required(request: Request, exc: ConsentRequiredError) -> JSONResponse:
        logger.warning(f"Consent required violation: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )

    @app.exception_handler(ServiceValidationError)
    async def handle_service_validation(request: Request, exc: ServiceValidationError) -> JSONResponse:
        logger.info(f"Service validation error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    @app.exception_handler(AssessmentInputError)
    async def handle_assessment_input_error(
        request: Request, exc: AssessmentInputError
    ) -> JSONResponse:
        logger.info(f"Assessment input error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.message},
        )

    @app.exception_handler(AssessmentOutputError)
    async def handle_assessment_output_error(
        request: Request, exc: AssessmentOutputError
    ) -> JSONResponse:
        logger.error(f"Assessment output error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": exc.message},
        )

    @app.exception_handler(AssessmentNotImplementedError)
    async def handle_assessment_not_implemented(
        request: Request, exc: AssessmentNotImplementedError
    ) -> JSONResponse:
        logger.warning(f"Assessment feature not implemented: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={"detail": exc.message},
        )

    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        logger.info(f"Authentication error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def handle_authorization_error(
        request: Request, exc: AuthorizationError
    ) -> JSONResponse:
        logger.warning(f"Authorization error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message},
        )

    @app.exception_handler(AuditLoggingError)
    async def handle_audit_logging_error(
        request: Request, exc: AuditLoggingError
    ) -> JSONResponse:
        logger.error(f"Audit logging error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal audit recording error occurred."},
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        if isinstance(exc, (HTTPException, StarletteHTTPException)):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        if isinstance(exc, RequestValidationError):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={"detail": exc.errors()},
            )
        logger.exception("Unhandled server exception processing %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred. Please try again later."},
        )

