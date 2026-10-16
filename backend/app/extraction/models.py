"""Data models for text extraction input and validation (RF-06, RF-30, RF-31)."""

from typing import Optional
from pydantic import BaseModel, Field


class TextValidationResult(BaseModel):
    """Result of validating confirmed text or uploaded TXT content."""
    is_valid: bool
    code_point_count: int = Field(ge=0, description="Unicode code points count")
    text: str = Field(default="", description="Original preserved text")
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class ExtractionInputRequest(BaseModel):
    """Request payload containing confirmed text to send to Gemini (RF-30)."""
    text: str = Field(description="Exact text to analyze")
    confirmed: bool = Field(
        default=False,
        description="Explicit user confirmation after review and personal data warning"
    )
    personal_data_warning_acknowledged: bool = Field(
        default=False,
        description="Acknowledged warning that text may contain personal data"
    )
