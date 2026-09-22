"""Exceptions for credit assessment engines."""


class AssessmentEngineError(Exception):
    """Base exception for all assessment engine related errors."""

    def __init__(self, message: str = "Assessment engine error occurred.") -> None:
        super().__init__(message)
        self.message = message


class AssessmentInputError(AssessmentEngineError):
    """Raised when assessment input is invalid, insufficient, or violates data minimization."""

    def __init__(self, message: str = "Invalid or non-compliant assessment input provided.") -> None:
        super().__init__(message)


class AssessmentNotImplementedError(AssessmentEngineError):
    """Raised when an engine does not implement or support a requested scoring algorithm."""

    def __init__(self, message: str = "Requested assessment capability is not implemented.") -> None:
        super().__init__(message)


class AssessmentOutputError(AssessmentEngineError):
    """Raised when an assessment engine produces malformed or out-of-bounds output."""

    def __init__(self, message: str = "Assessment engine produced invalid output.") -> None:
        super().__init__(message)
