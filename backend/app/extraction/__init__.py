"""Extraction module for assisted space extraction using Gemini."""

from backend.app.extraction.client import (
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    GeminiConfig,
    GeminiExtractionClient,
    redact_api_key,
)
from backend.app.extraction.exceptions import (
    BlankTextError,
    ConfirmationRequiredError,
    ExtractionError,
    ExtractionValidationError,
    GeminiError,
    GeminiQuotaExceededError,
    GeminiRejectionError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUnusableResponseError,
    InvalidFileFormatError,
    UnicodeLimitExceededError,
    Utf8DecodeError,
)
from backend.app.extraction.models import (
    ExtractionInputRequest,
    TextValidationResult,
)
from backend.app.extraction.validator import (
    MAX_UNICODE_CODE_POINTS,
    count_unicode_code_points,
    validate_confirmed_text,
    validate_extraction_request,
    validate_txt_file,
)

__all__ = [
    "BlankTextError",
    "ConfirmationRequiredError",
    "ExtractionError",
    "ExtractionValidationError",
    "GeminiError",
    "GeminiQuotaExceededError",
    "GeminiRejectionError",
    "GeminiTimeoutError",
    "GeminiUnavailableError",
    "GeminiUnusableResponseError",
    "InvalidFileFormatError",
    "UnicodeLimitExceededError",
    "Utf8DecodeError",
    "ExtractionInputRequest",
    "TextValidationResult",
    "MAX_UNICODE_CODE_POINTS",
    "count_unicode_code_points",
    "validate_confirmed_text",
    "validate_extraction_request",
    "validate_txt_file",
    "DEFAULT_MODEL",
    "DEFAULT_TIMEOUT_SECONDS",
    "GeminiConfig",
    "GeminiExtractionClient",
    "redact_api_key",
]
