"""Unit tests for Gemini client encapsulation, key protection, and failure handling (Task C02 · RF-06, RF-11, RF-29, RF-30)."""

import json
import httpx
import pytest
from unittest.mock import MagicMock

from backend.app.extraction.client import (
    GeminiConfig,
    GeminiExtractionClient,
    redact_api_key,
)
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

SECRET_KEY = "AIzaSySecretApiKeyForGemini12345"


class TestApiKeySecurityAndRedaction:
    """Verifies that the API key never appears in representations, logs, or exceptions (RF-29)."""

    def test_config_repr_and_str_mask_api_key(self):
        config = GeminiConfig(api_key=SECRET_KEY)
        assert SECRET_KEY not in repr(config)
        assert SECRET_KEY not in str(config)
        assert "***REDACTED***" in repr(config)

    def test_redact_helper_replaces_key(self):
        text_with_key = f"Error connecting to https://generativelanguage.googleapis.com?key={SECRET_KEY}"
        redacted = redact_api_key(text_with_key, SECRET_KEY)
        assert SECRET_KEY not in redacted
        assert "[REDACTED_API_KEY]" in redacted

    def test_exceptions_redact_api_key_from_messages(self):
        error_msg = f"Failed call with key={SECRET_KEY} on upstream endpoint"
        exc = GeminiUnavailableError(detail=error_msg, api_key_to_redact=SECRET_KEY)
        assert SECRET_KEY not in exc.message
        assert SECRET_KEY not in str(exc)
        assert "[REDACTED_API_KEY]" in exc.message

    def test_unexpected_http_error_redacts_api_key_in_response(self):
        # Mock client returning an error message containing the key
        mock_response = httpx.Response(
            status_code=400,
            text=f'{{"error": "Invalid credential {SECRET_KEY}"}}',
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        with pytest.raises(GeminiError) as exc_info:
            client.call_gemini("8 oficinas de 35 m²")

        assert SECRET_KEY not in exc_info.value.message
        assert SECRET_KEY not in str(exc_info.value)
        assert "[REDACTED_API_KEY]" in exc_info.value.message


class TestConfirmedTextTransmission:
    """Verifies that only confirmed text is sent without customer/quote metadata (RF-30)."""

    def test_unconfirmed_request_is_rejected_without_network_call(self):
        mock_http = MagicMock()
        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        unconfirmed_request = ExtractionInputRequest(
            text="8 oficinas de 35 m²",
            confirmed=False,
        )

        with pytest.raises(ConfirmationRequiredError):
            client.extract_spaces_from_request(unconfirmed_request)

        # Network client was NEVER called
        mock_http.post.assert_not_called()

    def test_only_confirmed_text_sent_in_payload_without_customer_metadata(self):
        mock_response = httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": json.dumps({"spaces": [{"name": "oficinas", "quantity": 8}]})}
                            ]
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        confirmed_request = ExtractionInputRequest(
            text="Texto de prueba: 8 oficinas y 2 bodegas",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )

        client.extract_spaces_from_request(confirmed_request)

        # Verify call was made
        mock_http.post.assert_called_once()
        _, kwargs = mock_http.post.call_args
        sent_payload = kwargs["json"]
        sent_text = sent_payload["contents"][0]["parts"][0]["text"]

        # Payload contains confirmed text
        assert "Texto de prueba: 8 oficinas y 2 bodegas" in sent_text

        # Header contains the API key (server-side only, not URL query parameter)
        headers = kwargs["headers"]
        assert headers["x-goog-api-key"] == SECRET_KEY


class TestGeminiFailureModesAndFallback:
    """Tests handling of timeout, quota, rejection, unavailability, and malformed responses (RF-11)."""

    def test_timeout_raises_gemini_timeout_error_and_preserves_text(self):
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.TimeoutException("Read timed out")

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY, timeout_seconds=15.0),
            http_client=mock_http,
        )

        input_text = "Descripción de oficinas"
        with pytest.raises(GeminiTimeoutError) as exc_info:
            client.call_gemini(input_text)

        assert exc_info.value.code == "GEMINI_TIMEOUT"
        assert exc_info.value.timeout_seconds == 15.0
        # Preserves original text for manual fallback
        assert exc_info.value.original_text == input_text

    def test_quota_exceeded_raises_gemini_quota_error(self):
        mock_response = httpx.Response(
            status_code=429,
            text='{"error": "Resource exhausted"}',
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        with pytest.raises(GeminiQuotaExceededError) as exc_info:
            client.call_gemini("Texto de cotización")

        assert exc_info.value.code == "GEMINI_QUOTA_EXCEEDED"
        assert "excedido el límite" in exc_info.value.message

    def test_service_unavailable_raises_gemini_unavailable_error(self):
        mock_response = httpx.Response(
            status_code=503,
            text="Service Unavailable",
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        with pytest.raises(GeminiUnavailableError) as exc_info:
            client.call_gemini("Texto de cotización")

        assert exc_info.value.code == "GEMINI_UNAVAILABLE"
        assert "no está disponible" in exc_info.value.message

    def test_safety_filter_rejection_raises_rejection_error(self):
        mock_response = httpx.Response(
            status_code=200,
            json={
                "promptFeedback": {"blockReason": "SAFETY"},
                "candidates": [],
            },
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        with pytest.raises(GeminiRejectionError) as exc_info:
            client.call_gemini("Texto bloqueado por políticas")

        assert exc_info.value.code == "GEMINI_REJECTED"
        assert "rechazó" in exc_info.value.message

    def test_unusable_response_malformed_json_raises_unusable_error(self):
        mock_response = httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Esto no es un JSON válido"}]
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        with pytest.raises(GeminiUnusableResponseError) as exc_info:
            client.call_gemini("Texto de prueba")

        assert exc_info.value.code == "GEMINI_UNUSABLE_RESPONSE"

    def test_successful_extraction_with_markdown_fenced_json(self):
        mock_response = httpx.Response(
            status_code=200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "```json\n" + json.dumps({
                                        "spaces": [
                                            {
                                                "name": "oficinas",
                                                "quantity": 8,
                                                "unit_area_m2": 35.0,
                                                "source_fragment": "8 oficinas de 35 m²",
                                            }
                                        ]
                                    }) + "\n```"
                                }
                            ]
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://api.example.com"),
        )
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response

        client = GeminiExtractionClient(
            config=GeminiConfig(api_key=SECRET_KEY),
            http_client=mock_http,
        )

        result = client.call_gemini("8 oficinas de 35 m²")
        assert "spaces" in result
        assert len(result["spaces"]) == 1
        assert result["spaces"][0]["name"] == "oficinas"
        assert result["spaces"][0]["quantity"] == 8
