"""Gemini server-side extraction client with credential protection and failure handling (RF-06, RF-11, RF-29, RF-30).

Guarantees:
- Calls Gemini strictly from the backend server.
- The API key is loaded from the environment and NEVER exposed to clients, repositories, or logs.
- Transmits ONLY the confirmed text to extract spaces (no customer metadata attached).
- Implements timeouts and handles timeouts, rate limits, network unavailability, and content rejection.
- Formats exceptions so the API key never leaks in error messages.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional
import httpx

from backend.app.extraction.exceptions import (
    ConfirmationRequiredError,
    GeminiError,
    GeminiQuotaExceededError,
    GeminiRejectionError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUnusableResponseError,
)
from backend.app.extraction.models import ExtractionInputRequest
from backend.app.extraction.validator import validate_extraction_request

logger = logging.getLogger("extraction.gemini")

DEFAULT_TIMEOUT_SECONDS: float = 60.0
DEFAULT_MODEL: str = "gemini-3.8-flash"
GEMINI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """Eres un asistente especializado en extracción de datos para cotizaciones de empresas de limpieza comercial en Ecuador.
Analiza únicamente el texto provisto y extrae los espacios descritos en grupos de espacios.
Reglas estrictas:
1. Extrae únicamente datos explícitos del texto. No inventes superficies, cantidades, frecuencias ni estados.
2. Si un atributo no está presente en el texto, asígnalo como null y condición "absent".
3. Si un dato se deriva directamente de operaciones explícitas (por ejemplo, superficie total y cantidad de oficinas), calcula el valor por unidad y marca la condición como "derived", indicando los valores y la operación (ejemplo: "280 m² ÷ 8 oficinas").
4. Si hay valores contradictorios para un atributo, marca la condición como "contradictory" y lista los valores en conflicto.
5. Cada espacio DEBE tener un fragmento exacto del texto original como respaldo (source_fragment).
6. Responde ÚNICAMENTE en formato JSON válido con el esquema indicado.

Esquema JSON requerido:
{
  "spaces": [
    {
      "name": "nombre o tipo de espacio (ej. oficinas, baños, aulas)",
      "quantity": 8,
      "unit_area_m2": 35.0,
      "total_area_m2": 280.0,
      "condition": "bueno" | "regular" | "malo" | null,
      "cleaning_type": "general" | "especializado" | null,
      "service_days": ["lunes", "miércoles"] | null,
      "visits_per_day": 1 | null,
      "source_fragment": "fragmento exacto del texto de origen",
      "attributes": {
        "name": {"value": "...", "source_fragment": "...", "condition": "explicit" | "derived" | "absent" | "contradictory"},
        "quantity": {"value": 8, "source_fragment": "...", "condition": "explicit"},
        "unit_area_m2": {"value": 35.0, "source_fragment": "...", "condition": "derived", "operation": "280 m² ÷ 8 oficinas"},
        "condition": {"value": "regular", "source_fragment": "...", "condition": "contradictory", "conflicting_values": ["bueno", "regular"]}
      }
    }
  ]
}
"""


def redact_api_key(text: str, key: str) -> str:
    """Safely redact any occurrence of the API key from a string."""
    if not key or len(key) < 5 or not text:
        return text
    return text.replace(key, "[REDACTED_API_KEY]")


class GeminiConfig:
    """Configuration for Gemini client. Masks API key in representations."""
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else float(os.getenv("GEMINI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
        if self.timeout_seconds <= 0:
            raise ValueError("GEMINI_TIMEOUT_SECONDS debe ser positivo")

    def __repr__(self) -> str:
        # Guarantee key is never shown in repr
        masked_key = "***REDACTED***" if self.api_key else "<not-set>"
        return f"GeminiConfig(model='{self.model_name}', timeout={self.timeout_seconds}s, api_key='{masked_key}')"

    def __str__(self) -> str:
        return self.__repr__()


class GeminiExtractionClient:
    """Client for invoking Gemini with confirmed text strictly from the server."""

    def __init__(
        self,
        config: Optional[GeminiConfig] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.config = config or GeminiConfig()
        self._http_client = http_client

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is not None:
            return self._http_client
        return httpx.Client(timeout=self.config.timeout_seconds)

    def extract_spaces_from_request(
        self,
        request: ExtractionInputRequest,
    ) -> Dict[str, Any]:
        """Validate confirmed request and perform extraction with Gemini (RF-06, RF-30)."""
        # Validate that the request was explicitly confirmed by user (RF-30)
        validate_extraction_request(request, strict=True)
        return self.call_gemini(request.text)

    def call_gemini(self, confirmed_text: str) -> Dict[str, Any]:
        """Execute extraction call to Gemini API for confirmed text (RF-06, RF-11, RF-29)."""
        api_key = self.config.api_key
        url = GEMINI_API_URL.format(model=self.config.model_name)

        # Prepare payload - ONLY confirmed text is passed, never client/quote metadata (RF-30)
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\nTexto a analizar:\n\"\"\"{confirmed_text}\"\"\""}
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        # Header with api-key instead of URL query parameter to avoid key leaking in access logs
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        client = self._get_http_client()

        try:
            response = client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
        except httpx.TimeoutException:
            raise GeminiTimeoutError(
                timeout_seconds=self.config.timeout_seconds,
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            safe_error_msg = redact_api_key(str(exc), api_key)
            raise GeminiUnavailableError(
                detail=safe_error_msg,
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )
        except Exception as exc:
            safe_error_msg = redact_api_key(str(exc), api_key)
            raise GeminiUnavailableError(
                detail=f"Fallo de conexión: {safe_error_msg}",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        return self._process_gemini_response(response, confirmed_text, api_key)

    def _process_gemini_response(
        self,
        response: httpx.Response,
        confirmed_text: str,
        api_key: str,
    ) -> Dict[str, Any]:
        """Process HTTP response from Gemini and convert into domain representation."""
        status_code = response.status_code

        if status_code == 429:
            raise GeminiQuotaExceededError(
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        if status_code in (500, 502, 503, 504):
            raise GeminiUnavailableError(
                detail=f"Error del servidor HTTP {status_code}",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        if status_code != 200:
            safe_body = redact_api_key(response.text[:300], api_key)
            raise GeminiError(
                message=f"Respuesta inesperada de Gemini (HTTP {status_code}): {safe_body}",
                code=f"GEMINI_HTTP_{status_code}",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        try:
            data = response.json()
        except Exception:
            raise GeminiUnusableResponseError(
                detail="El cuerpo de respuesta no es un JSON válido",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        # Check for safety filter blocks / content rejection
        prompt_feedback = data.get("promptFeedback", {})
        if prompt_feedback.get("blockReason"):
            block_reason = prompt_feedback.get("blockReason")
            raise GeminiRejectionError(
                reason=f"Bloqueo por política: {block_reason}",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        candidates = data.get("candidates", [])
        if not candidates:
            raise GeminiUnusableResponseError(
                detail="Respuesta sin candidatos de extracción",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        first_candidate = candidates[0]
        finish_reason = first_candidate.get("finishReason")
        if finish_reason == "SAFETY":
            raise GeminiRejectionError(
                reason="Bloqueo de contenido por filtros de seguridad",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        content = first_candidate.get("content", {})
        parts = content.get("parts", [])
        if not parts or "text" not in parts[0]:
            raise GeminiUnusableResponseError(
                detail="Candidato no contiene texto de salida",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )

        generated_text = parts[0]["text"].strip()
        parsed_spaces = self._parse_json_content(generated_text, confirmed_text, api_key)
        return parsed_spaces

    def _parse_json_content(
        self,
        raw_text: str,
        confirmed_text: str,
        api_key: str,
    ) -> Dict[str, Any]:
        """Extract and parse JSON payload from response text."""
        # Strip potential markdown code blocks (```json ... ```)
        cleaned_text = raw_text
        if "```" in raw_text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
            if match:
                cleaned_text = match.group(1).strip()

        try:
            parsed = json.loads(cleaned_text)
            if not isinstance(parsed, dict):
                raise ValueError("La respuesta JSON raíz debe ser un objeto")
            return parsed
        except Exception as exc:
            safe_detail = redact_api_key(str(exc), api_key)
            raise GeminiUnusableResponseError(
                detail=f"Error al decodificar JSON propuesto: {safe_detail}",
                original_text=confirmed_text,
                api_key_to_redact=api_key,
            )
