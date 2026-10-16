"""Unit tests for extraction input validation (Task C01 · RF-06, RF-30, RF-31)."""

import pytest
from backend.app.extraction.exceptions import (
    BlankTextError,
    ConfirmationRequiredError,
    InvalidFileFormatError,
    UnicodeLimitExceededError,
    Utf8DecodeError,
)
from backend.app.extraction.models import ExtractionInputRequest
from backend.app.extraction.validator import (
    MAX_UNICODE_CODE_POINTS,
    count_unicode_code_points,
    validate_confirmed_text,
    validate_extraction_request,
    validate_txt_file,
)


class TestUnicodeCodePointCounting:
    """Tests that verify exact Unicode code point counting (RF-31)."""

    def test_ascii_and_spanish_text_counting(self):
        text = "Limpieza de 8 oficinas de 35 m² c/u"
        # Verify length matches expected Python code point count
        assert count_unicode_code_points(text) == len(text)

    def test_single_emoji_counts_as_one_code_point(self):
        """RF-31 / C01: un emoji cuenta como un punto."""
        emoji = "🏢"  # U+1F3E2
        assert count_unicode_code_points(emoji) == 1

        emoji_broom = "🧹"  # U+1F9F9
        assert count_unicode_code_points(emoji_broom) == 1

        emoji_smile = "😀"  # U+1F600
        assert count_unicode_code_points(emoji_smile) == 1

    def test_mixed_text_with_emojis(self):
        text = "Edificio 🏢 piso 2 🧹"
        # "Edificio " (9) + "🏢" (1) + " piso 2 " (8) + "🧹" (1) = 19
        assert count_unicode_code_points(text) == 19


class TestBlankTextValidation:
    """Tests rejecting empty or whitespace-only inputs (RF-31)."""

    @pytest.mark.parametrize(
        "blank_input",
        [
            "",
            "   ",
            "\t\t",
            "\n\n\r\n",
            "  \t \n \r  ",
        ],
    )
    def test_blank_text_raises_error_and_preserves_text(self, blank_input):
        with pytest.raises(BlankTextError) as exc_info:
            validate_confirmed_text(blank_input, strict=True)
        assert exc_info.value.code == "BLANK_TEXT"
        assert exc_info.value.original_text == blank_input
        assert "no puede estar vacío" in exc_info.value.message

    def test_blank_text_non_strict_returns_invalid_result(self):
        result = validate_confirmed_text("   \n\t  ", strict=False)
        assert result.is_valid is False
        assert result.error_code == "BLANK_TEXT"
        assert result.text == "   \n\t  "


class TestUnicodeCodePointLimit:
    """Tests the 50,000 Unicode code points limit (RF-31)."""

    def test_boundary_exactly_50000_code_points_is_valid(self):
        text_50k = "a" * MAX_UNICODE_CODE_POINTS
        result = validate_confirmed_text(text_50k, strict=True)
        assert result.is_valid is True
        assert result.code_point_count == 50_000
        assert result.text == text_50k

    def test_boundary_50001_code_points_raises_limit_exceeded(self):
        text_50k_plus_1 = "a" * (MAX_UNICODE_CODE_POINTS + 1)
        with pytest.raises(UnicodeLimitExceededError) as exc_info:
            validate_confirmed_text(text_50k_plus_1, strict=True)
        assert exc_info.value.code == "UNICODE_LIMIT_EXCEEDED"
        assert exc_info.value.actual_count == 50_001
        assert exc_info.value.limit == 50_000
        # Preserves original text for correction (RF-31)
        assert exc_info.value.original_text == text_50k_plus_1

    def test_emojis_at_boundary(self):
        # 49,999 'x' + 1 emoji = 50,000 -> valid
        text_valid = ("x" * 49_999) + "🏢"
        result = validate_confirmed_text(text_valid, strict=True)
        assert result.is_valid is True
        assert result.code_point_count == 50_000

        # 50,000 'x' + 1 emoji = 50,001 -> invalid
        text_invalid = ("x" * 50_000) + "🏢"
        with pytest.raises(UnicodeLimitExceededError) as exc_info:
            validate_confirmed_text(text_invalid, strict=True)
        assert exc_info.value.actual_count == 50_001


class TestTxtFileValidation:
    """Tests for TXT file validation and UTF-8 decoding (RF-31)."""

    def test_valid_utf8_txt_file_decoding(self):
        content = "Cotización: 5 aulas de 40 m² con piso de cerámica."
        raw_bytes = content.encode("utf-8")
        result = validate_txt_file(raw_bytes, filename="espacios.txt", strict=True)
        assert result.is_valid is True
        assert result.text == content
        assert result.code_point_count == len(content)

    def test_invalid_file_extension_rejected(self):
        content = "Edificio principal"
        raw_bytes = content.encode("utf-8")
        with pytest.raises(InvalidFileFormatError) as exc_info:
            validate_txt_file(raw_bytes, filename="espacios.pdf", strict=True)
        assert exc_info.value.code == "INVALID_FILE_FORMAT"
        assert exc_info.value.filename == "espacios.pdf"

    def test_invalid_utf8_encoding_raises_error(self):
        # Invalid UTF-8 byte sequence
        invalid_bytes = b"\xff\xfe\x00\x12Invalid"
        with pytest.raises(Utf8DecodeError) as exc_info:
            validate_txt_file(invalid_bytes, filename="espacios.txt", strict=True)
        assert exc_info.value.code == "UTF8_DECODE_ERROR"

    def test_blank_content_in_txt_file_rejected(self):
        blank_bytes = "   \n\t  ".encode("utf-8")
        with pytest.raises(BlankTextError):
            validate_txt_file(blank_bytes, filename="espacios.txt", strict=True)


class TestExtractionRequestConfirmation:
    """Tests enforcing user confirmation before Gemini extraction (RF-30)."""

    def test_unconfirmed_request_rejected(self):
        request = ExtractionInputRequest(
            text="8 oficinas de 35 m²",
            confirmed=False,
        )
        with pytest.raises(ConfirmationRequiredError) as exc_info:
            validate_extraction_request(request, strict=True)
        assert exc_info.value.code == "CONFIRMATION_REQUIRED"
        assert exc_info.value.original_text == "8 oficinas de 35 m²"

    def test_confirmed_request_accepted(self):
        request = ExtractionInputRequest(
            text="8 oficinas de 35 m²",
            confirmed=True,
            personal_data_warning_acknowledged=True,
        )
        result = validate_extraction_request(request, strict=True)
        assert result.is_valid is True
        assert result.text == "8 oficinas de 35 m²"
