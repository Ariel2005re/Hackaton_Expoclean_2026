"""Exceptions for extraction and input validation (RF-06, RF-30, RF-31)."""

class ExtractionError(Exception):
    """Base exception for all extraction-related operations."""
    pass


class ExtractionValidationError(ExtractionError):
    """Base validation error for extraction input."""
    def __init__(self, message: str, code: str, original_text: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.original_text = original_text


class BlankTextError(ExtractionValidationError):
    """Raised when text is empty or contains only whitespace characters (RF-31)."""
    def __init__(self, original_text: str = ""):
        message = (
            "El texto no puede estar vacío ni contener únicamente "
            "espacios en blanco, tabulaciones o saltos de línea."
        )
        super().__init__(message=message, code="BLANK_TEXT", original_text=original_text)


class UnicodeLimitExceededError(ExtractionValidationError):
    """Raised when text exceeds the 50,000 Unicode code points limit (RF-31)."""
    def __init__(self, actual_count: int, limit: int = 50000, original_text: str = ""):
        message = (
            f"El texto supera el límite máximo de {limit:,} puntos de código Unicode "
            f"(actual: {actual_count:,} puntos de código)."
        )
        super().__init__(message=message, code="UNICODE_LIMIT_EXCEEDED", original_text=original_text)
        self.actual_count = actual_count
        self.limit = limit


class InvalidFileFormatError(ExtractionValidationError):
    """Raised when an uploaded file is not a TXT file (RF-31)."""
    def __init__(self, filename: str = "", original_text: str = ""):
        message = "La entrada asistida por archivo admite únicamente archivos TXT UTF-8."
        super().__init__(message=message, code="INVALID_FILE_FORMAT", original_text=original_text)
        self.filename = filename


class Utf8DecodeError(ExtractionValidationError):
    """Raised when a TXT file cannot be decoded as UTF-8 (RF-31)."""
    def __init__(self, original_text: str = ""):
        message = "El archivo TXT no puede leerse como UTF-8."
        super().__init__(message=message, code="UTF8_DECODE_ERROR", original_text=original_text)


class ConfirmationRequiredError(ExtractionValidationError):
    """Raised when text extraction is requested without user confirmation (RF-30)."""
    def __init__(self, original_text: str = ""):
        message = "Se requiere confirmación explícita del usuario sobre el texto exacto antes del envío."
        super().__init__(message=message, code="CONFIRMATION_REQUIRED", original_text=original_text)


class GeminiError(ExtractionError):
    """Base exception for Gemini service failures (RF-11, RF-29).
    
    Guarantees that sensitive information such as API keys is never exposed
    in the exception message or attributes.
    """
    def __init__(self, message: str, code: str = "GEMINI_ERROR", original_text: str = "", api_key_to_redact: str = ""):
        if api_key_to_redact and len(api_key_to_redact) > 4:
            message = message.replace(api_key_to_redact, "[REDACTED_API_KEY]")
        super().__init__(message)
        self.message = message
        self.code = code
        self.original_text = original_text


class GeminiTimeoutError(GeminiError):
    """Raised when the Gemini request exceeds the timeout limit (RF-11)."""
    def __init__(self, timeout_seconds: float, original_text: str = "", api_key_to_redact: str = ""):
        message = f"La solicitud a Gemini excedió el tiempo de espera ({timeout_seconds}s). Se conserva el borrador para continuar manualmente."
        super().__init__(message=message, code="GEMINI_TIMEOUT", original_text=original_text, api_key_to_redact=api_key_to_redact)
        self.timeout_seconds = timeout_seconds


class GeminiUnavailableError(GeminiError):
    """Raised when Gemini service is unavailable or network fails (RF-11)."""
    def __init__(self, detail: str = "", original_text: str = "", api_key_to_redact: str = ""):
        clean_detail = detail.replace(api_key_to_redact, "[REDACTED_API_KEY]") if api_key_to_redact else detail
        message = f"El servicio de Gemini no está disponible ({clean_detail}). Se conserva el borrador para continuar manualmente."
        super().__init__(message=message, code="GEMINI_UNAVAILABLE", original_text=original_text, api_key_to_redact=api_key_to_redact)


class GeminiQuotaExceededError(GeminiError):
    """Raised when Gemini quota or rate limits are exceeded (RF-11)."""
    def __init__(self, original_text: str = "", api_key_to_redact: str = ""):
        message = "Se ha excedido el límite de solicitudes a la API de Gemini. Se conserva el borrador para continuar manualmente."
        super().__init__(message=message, code="GEMINI_QUOTA_EXCEEDED", original_text=original_text, api_key_to_redact=api_key_to_redact)


class GeminiRejectionError(GeminiError):
    """Raised when Gemini safety filters or content policies reject the prompt (RF-11)."""
    def __init__(self, reason: str = "Bloqueo por filtros de seguridad", original_text: str = "", api_key_to_redact: str = ""):
        message = f"Gemini rechazó procesar el texto ({reason}). Se conserva el borrador para continuar manualmente."
        super().__init__(message=message, code="GEMINI_REJECTED", original_text=original_text, api_key_to_redact=api_key_to_redact)


class GeminiUnusableResponseError(GeminiError):
    """Raised when Gemini returns an empty, corrupted, or unusable response (RF-11)."""
    def __init__(self, detail: str = "Respuesta vacía o formato inválido", original_text: str = "", api_key_to_redact: str = ""):
        message = f"Gemini devolvió una respuesta inutilizable ({detail}). Se conserva el borrador para continuar manualmente."
        super().__init__(message=message, code="GEMINI_UNUSABLE_RESPONSE", original_text=original_text, api_key_to_redact=api_key_to_redact)

