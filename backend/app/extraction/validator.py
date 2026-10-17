"""Input validator for text and TXT files for Gemini extraction (RF-06, RF-30, RF-31).

Requirements satisfied:
- RF-06: Assumes user confirms valid text or TXT.
- RF-30: Verifies confirmation of exact text without automatic customer metadata.
- RF-31: Evaluates exact confirmed text:
  * Rejects whitespace-only content (spaces, tabs, newlines).
  * Enforces maximum of 50,000 Unicode code points (1 emoji = 1 code point).
  * Validates UTF-8 encoding for TXT files.
  * Preserves original text/draft for correction upon validation errors.
"""

from typing import Optional
from backend.app.extraction.exceptions import (
    BlankTextError,
    ConfirmationRequiredError,
    InvalidFileFormatError,
    UnicodeLimitExceededError,
    Utf8DecodeError,
)
from backend.app.extraction.models import (
    ExtractionInputRequest,
    TextValidationResult,
)

MAX_UNICODE_CODE_POINTS: int = 50_000


def count_unicode_code_points(text: str) -> int:
    """Return the exact number of Unicode code points in the string.
    
    In Python 3, `len(str)` evaluates the number of Unicode code points.
    Emojis (e.g. 🏢, 🧹, 😀) count as 1 code point each.
    """
    return len(text)


def validate_confirmed_text(text: str, strict: bool = True) -> TextValidationResult:
    """Validate confirmed text according to RF-31 rules.
    
    Args:
        text: The confirmed text to validate.
        strict: If True, raises exceptions on validation failure.
                If False, returns a TextValidationResult with is_valid=False.
                
    Returns:
        TextValidationResult with character count and validity.
        
    Raises:
        BlankTextError: If text is empty or only whitespace.
        UnicodeLimitExceededError: If code point count > 50,000.
    """
    code_point_count = count_unicode_code_points(text)
    
    # Check for empty or whitespace-only text (RF-31)
    if not text or not text.strip():
        if strict:
            raise BlankTextError(original_text=text)
        return TextValidationResult(
            is_valid=False,
            code_point_count=code_point_count,
            text=text,
            error_message=(
                "El texto no puede estar vacío ni contener únicamente "
                "espacios en blanco, tabulaciones o saltos de línea."
            ),
            error_code="BLANK_TEXT",
        )
    
    # Check for Unicode code point limit (RF-31)
    if code_point_count > MAX_UNICODE_CODE_POINTS:
        if strict:
            raise UnicodeLimitExceededError(
                actual_count=code_point_count,
                limit=MAX_UNICODE_CODE_POINTS,
                original_text=text,
            )
        return TextValidationResult(
            is_valid=False,
            code_point_count=code_point_count,
            text=text,
            error_message=(
                f"El texto supera el límite máximo de {MAX_UNICODE_CODE_POINTS:,} "
                f"puntos de código Unicode (actual: {code_point_count:,} puntos de código)."
            ),
            error_code="UNICODE_LIMIT_EXCEEDED",
        )
    
    return TextValidationResult(
        is_valid=True,
        code_point_count=code_point_count,
        text=text,
    )


def validate_txt_file(
    file_bytes: bytes,
    filename: Optional[str] = None,
    strict: bool = True,
) -> TextValidationResult:
    """Validate an uploaded TXT file for UTF-8 encoding and content limits (RF-31).
    
    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Optional filename to check file extension (.txt required).
        strict: If True, raises exceptions on failure; else returns invalid result.
        
    Returns:
        TextValidationResult with decoded text and validation status.
        
    Raises:
        InvalidFileFormatError: If filename does not end in .txt.
        Utf8DecodeError: If bytes cannot be decoded as valid UTF-8.
        BlankTextError / UnicodeLimitExceededError: If decoded text violates RF-31.
    """
    if filename is not None and not filename.lower().endswith(".txt"):
        if strict:
            raise InvalidFileFormatError(filename=filename, original_text="")
        return TextValidationResult(
            is_valid=False,
            code_point_count=0,
            text="",
            error_message="La entrada asistida por archivo admite únicamente archivos TXT UTF-8.",
            error_code="INVALID_FILE_FORMAT",
        )
        
    try:
        decoded_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        if strict:
            raise Utf8DecodeError(original_text="")
        return TextValidationResult(
            is_valid=False,
            code_point_count=0,
            text="",
            error_message="El archivo TXT no puede leerse como UTF-8.",
            error_code="UTF8_DECODE_ERROR",
        )
        
    return validate_confirmed_text(decoded_text, strict=strict)


def validate_extraction_request(
    request: ExtractionInputRequest,
    strict: bool = True,
) -> TextValidationResult:
    """Validate a full user extraction request before sending to Gemini (RF-30, RF-31).
    
    Args:
        request: ExtractionInputRequest with text, confirmed flag, and warning ack.
        strict: If True, raises exceptions on validation failure.
        
    Returns:
        TextValidationResult with validation status.
        
    Raises:
        ConfirmationRequiredError: If user has not confirmed the text.
        BlankTextError / UnicodeLimitExceededError: If text violates RF-31.
    """
    if not request.confirmed:
        if strict:
            raise ConfirmationRequiredError(original_text=request.text)
        return TextValidationResult(
            is_valid=False,
            code_point_count=count_unicode_code_points(request.text),
            text=request.text,
            error_message="Se requiere confirmación explícita del usuario sobre el texto exacto antes del envío.",
            error_code="CONFIRMATION_REQUIRED",
        )
        
    return validate_confirmed_text(request.text, strict=strict)
