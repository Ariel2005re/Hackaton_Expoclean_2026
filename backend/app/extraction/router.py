"""FastAPI router for assisted extraction and proposal review (Task C06 · RF-06, RF-09–RF-11, RF-29–RF-31)."""

from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.extraction.models import (
    AnalyzeSpacesPayload,
    ConfirmGroupRequest,
    CorrectAttributeRequest,
    DiscardGroupRequest,
    ExtractionInputRequest,
    ExtractionServiceResponse,
    MergeGroupsRequest,
    ProposedSpaceGroup,
    SplitGroupRequest,
    TextValidationResult,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.service import ExtractionService
from backend.app.extraction.validator import (
    validate_confirmed_text,
    validate_txt_file,
)

extraction_router = APIRouter(prefix="/extraction", tags=["extraction"])

_global_service = ExtractionService()


def get_extraction_service() -> ExtractionService:
    return _global_service


@extraction_router.post(
    "/analyze",
    response_model=ExtractionServiceResponse,
    summary="Analizar texto confirmado con Gemini (RF-06, RF-29, RF-30)",
)
def analyze_spaces(
    payload: AnalyzeSpacesPayload,
) -> ExtractionServiceResponse:
    """Analyze confirmed space description using Gemini with fallback and distinguishable statuses."""
    service = get_extraction_service()
    req = ExtractionInputRequest(
        text=payload.text,
        confirmed=payload.confirmed,
        personal_data_warning_acknowledged=payload.personal_data_warning_acknowledged,
    )
    return service.analyze_description(req, existing_confirmed_groups=payload.existing_confirmed)


class ValidateTextPayload(BaseModel):
    text: str


@extraction_router.post(
    "/validate-text",
    response_model=TextValidationResult,
    summary="Validar texto antes de confirmar envío (RF-30, RF-31)",
)
def validate_text(payload: ValidateTextPayload) -> TextValidationResult:
    """Check text length, blanks, and Unicode code points without sending to Gemini."""
    return validate_confirmed_text(payload.text, strict=False)


@extraction_router.post(
    "/upload-txt",
    response_model=TextValidationResult,
    summary="Cargar y validar archivo TXT UTF-8 (RF-31)",
)
async def upload_txt(file: UploadFile = File(...)) -> TextValidationResult:
    """Read TXT file bytes, ensure UTF-8 encoding, and validate content limits."""
    content_bytes = await file.read()
    return validate_txt_file(content_bytes, filename=file.filename, strict=False)
